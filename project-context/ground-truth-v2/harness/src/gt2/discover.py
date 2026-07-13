# ---------------------------------------------------------------------------
# discover.py — semantic, rule-driven URL discovery over the TurboTax estate.
# Contract: harvest ALL urls from the sitemaps (no JS needed), drop noise and
#   the 54 v1 pages, then have an LLM score every URL's likely relevance to
#   the MEANING of each rule (0-3) from its path. Selection takes the top
#   pages with PER-RULE QUOTAS so rare rules (APR, FDIC, bonus) get corpus
#   variety instead of drowning under free-claim pages.
#   Output: data/candidates.json (url, page_type, per-rule scores, quota src).
# Deps: httpx, llm, rules, config.
# ---------------------------------------------------------------------------
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

import httpx

from .config import (ALLOW_HOSTS, DEFAULT_TARGET_PAGES, DENY_SUBSTR,
                     RANK_MODEL, SITEMAP_URLS, USER_AGENT, Paths)
from .llm import invoke_structured
from .models import UrlRanking
from .rules import load_rules

_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
# quotas: fraction of the target reserved per rule's best candidates
_QUOTAS = {"R-01": 0.35, "R-02": 0.25, "R-03": 0.20, "R-04": 0.20}


def _fetch_xml(client: httpx.Client, url: str) -> ET.Element | None:
    try:
        r = client.get(url, timeout=30)
        r.raise_for_status()
        return ET.fromstring(r.content)
    except Exception as exc:
        print(f"  ! sitemap fetch failed {url}: {type(exc).__name__}: {exc}")
        return None


def harvest_sitemap_urls() -> list[str]:
    urls: list[str] = []
    with httpx.Client(headers={"User-Agent": USER_AGENT},
                      follow_redirects=True) as client:
        queue = list(SITEMAP_URLS)
        seen_maps: set[str] = set()
        while queue:
            sm_url = queue.pop(0)
            if sm_url in seen_maps:
                continue
            seen_maps.add(sm_url)
            root = _fetch_xml(client, sm_url)
            if root is None:
                continue
            tag = root.tag.split("}")[-1]
            if tag == "sitemapindex":
                queue.extend(
                    loc.text.strip() for loc in root.findall(".//sm:loc", _NS)
                    if loc.text
                )
            else:
                urls.extend(
                    loc.text.strip() for loc in root.findall(".//sm:loc", _NS)
                    if loc.text
                )
    return urls


def _keep(url: str, exclude: set[str]) -> bool:
    try:
        p = urlparse(url)
    except ValueError:
        return False
    if p.scheme != "https" or p.netloc not in ALLOW_HOSTS:
        return False
    low = url.lower()
    if any(s in low for s in DENY_SUBSTR):
        return False
    return url.rstrip("/") not in exclude


def _v1_urls(paths: Paths) -> set[str]:
    pages = json.loads(paths.v1_curated.read_text())["pages"]
    return {p["url"].rstrip("/") for p in pages}


def _rank_batch(paths: Paths, rules, batch: list[str]) -> list[dict]:
    rule_block = "\n".join(f"{r.id}: {r.verbatim_text}" for r in rules)
    system = (
        "You are a senior marketing-compliance analyst working for Intuit. "
        "You are selecting TurboTax web pages worth auditing against a "
        "4-rule compliance scorecard. You will see only URLs. From each "
        "URL's path, infer what the page likely contains and score its "
        "relevance to EACH rule 0-3 (0 = almost certainly nothing the rule "
        "governs; 3 = almost certainly contains language the rule governs). "
        "Think semantically about what each rule GOVERNS, not keywords: "
        "R-01 governs free-product claims and their eligibility disclosure; "
        "R-02 governs any stated rate or finance charge (loans, refund "
        "advances, pay-later); R-03 governs deposit/banking products and "
        "FDIC language; R-04 governs bonus/reward/referral offers and their "
        "account-terms disclosures.\n\nThe scorecard (verbatim):\n"
        + rule_block
    )
    user = ("Score every URL. Return one entry per URL, same order.\n\n"
            + "\n".join(batch))
    ranking = invoke_structured(paths.cache, RANK_MODEL, UrlRanking, system, user)
    return [{"url": s.url, "rule_relevance": s.relevance(),
             "page_type": s.page_type} for s in ranking.scores]


def discover(paths: Paths, target: int = DEFAULT_TARGET_PAGES,
             limit: int | None = None) -> dict:
    rules = load_rules(paths)
    exclude = _v1_urls(paths)
    raw = harvest_sitemap_urls()
    urls = sorted({u.rstrip("/") for u in raw if _keep(u, exclude)})
    print(f"  sitemap urls: {len(raw)} raw -> {len(urls)} kept "
          f"(v1's {len(exclude)} excluded)")
    if limit:
        urls = urls[:limit]

    from concurrent.futures import ThreadPoolExecutor, as_completed
    batches = [urls[i:i + 60] for i in range(0, len(urls), 60)]
    scored: list[dict] = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(_rank_batch, paths, rules, b): n
                   for n, b in enumerate(batches)}
        for done, fut in enumerate(as_completed(futures), 1):
            scored.extend(fut.result())
            if done % 8 == 0 or done == len(batches):
                print(f"  ranked {done}/{len(batches)} batches")

    # per-rule quota selection: rare-rule variety beats raw score order
    chosen: dict[str, dict] = {}
    for rule_id, frac in _QUOTAS.items():
        want = max(1, int(target * frac))
        pool = sorted(scored,
                      key=lambda s: s["rule_relevance"].get(rule_id, 0),
                      reverse=True)
        picked = 0
        for s in pool:
            if picked >= want:
                break
            if s["rule_relevance"].get(rule_id, 0) < 1:
                break
            if s["url"] not in chosen:
                chosen[s["url"]] = {**s, "quota_src": rule_id}
                picked += 1
            elif chosen[s["url"]]["quota_src"] != rule_id:
                picked += 1  # already in via another rule; counts for both

    out = {
        "discovered_at_note": "sitemap harvest + LLM semantic ranking",
        "rank_model": RANK_MODEL,
        "target": target,
        "total_sitemap_urls": len(raw),
        "total_ranked": len(scored),
        "candidates": sorted(chosen.values(), key=lambda s: s["url"]),
    }
    paths.candidates.write_text(json.dumps(out, indent=1))
    print(f"  candidates: {len(out['candidates'])} -> {paths.candidates}")
    return out
