# ---------------------------------------------------------------------------
# capture.py — snapshot candidate pages with the PROVEN v1 crawl4ai config.
# Contract: identical fetch semantics to code/tools/snapshot-capture (raw
#   markdown, domcontentloaded + settle delay + full-page scan; TurboTax never
#   reaches networkidle). Same file format as v1 snapshots: front matter +
#   body; hash = sha256 of whitespace-stripped body. Polite: sequential with
#   spacing. Thin/failed pages recorded in the manifest, not judged.
#   Page ids: V01, V02, ... (v2 namespace).
# Deps: crawl4ai, config, textnorm.
# ---------------------------------------------------------------------------
from __future__ import annotations

import asyncio
import json
import re
from datetime import UTC, datetime
from urllib.parse import urlparse

from .config import (PAGE_TIMEOUT_MS, REQUEST_SPACING_S, THIN_WORD_THRESHOLD,
                     USER_AGENT, Paths)
from .textnorm import body_sha256


def _slug(url: str) -> str:
    path = urlparse(url).path.strip("/") or urlparse(url).netloc
    return re.sub(r"[^a-z0-9]+", "-", path.lower()).strip("-")[:60] or "page"


async def _capture_async(paths: Paths, candidates: list[dict],
                         limit: int | None) -> list[dict]:
    from crawl4ai import (AsyncWebCrawler, BrowserConfig, CacheMode,
                          CrawlerRunConfig)

    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        wait_until="domcontentloaded",
        page_timeout=PAGE_TIMEOUT_MS,
        delay_before_return_html=3.0,
        scan_full_page=True,
        scroll_delay=0.3,
        remove_overlay_elements=True,
    )
    manifest: list[dict] = []
    existing = {}
    if paths.manifest.exists():
        existing = {p["url"]: p for p in json.loads(paths.manifest.read_text())["pages"]}

    todo = [c for c in candidates if c["url"] not in existing]
    if limit:
        todo = todo[:limit]
    print(f"  to capture: {len(todo)} (already have {len(existing)})")

    n = len(existing)
    async with AsyncWebCrawler(config=BrowserConfig(
            headless=True, user_agent=USER_AGENT)) as crawler:
        for c in todo:
            url = c["url"]
            n += 1
            page_id = f"V{n:02d}"
            try:
                result = await crawler.arun(url=url, config=run_config)
                md = getattr(result, "markdown", None)
                body = (getattr(md, "raw_markdown", None)
                        or (md if isinstance(md, str) else "") or "")
                ok = bool(getattr(result, "success", False)) and bool(body.strip())
                err = None if ok else getattr(result, "error_message", "empty markdown")
            except Exception as exc:
                body, ok, err = "", False, f"{type(exc).__name__}: {exc}"

            words = len(body.split())
            quality = ("good" if ok and words >= THIN_WORD_THRESHOLD
                       else "thin" if ok else "failed")
            entry = {
                "id": page_id, "url": url, "quality": quality,
                "word_count": words, "fetcher": "crawl4ai",
                "quota_src": c.get("quota_src"),
                "rule_relevance": c.get("rule_relevance"),
                "error": err,
            }
            if quality == "good":
                sha = body_sha256(body)
                entry["content_sha256"] = sha
                fname = f"{page_id}_{_slug(url)}.md"
                front = (
                    f"---\nid: {page_id}\nurl: {url}\n"
                    f"discovery: semantic:{c.get('quota_src')}\n"
                    f"fetched_at: {datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')}\n"
                    f"fetcher: crawl4ai\ncontent_sha256: {sha}\n"
                    f"quality: good\nnotes: {words} words; gt2 capture\n---\n\n"
                )
                (paths.snapshots / fname).write_text(front + body)
                entry["file"] = fname
            else:
                n -= 1  # don't burn a page id on a failed capture
                entry["id"] = None
            manifest.append(entry)
            print(f"  {entry['id'] or '--'} {quality:6s} {words:6d}w  {url}")
            await asyncio.sleep(REQUEST_SPACING_S)

    all_pages = list(existing.values()) + manifest
    paths.manifest.write_text(json.dumps(
        {"pages": all_pages,
         "snapshot_count": sum(1 for p in all_pages if p.get("quality") == "good")},
        indent=1))
    return manifest


def capture(paths: Paths, limit: int | None = None) -> None:
    candidates = json.loads(paths.candidates.read_text())["candidates"]
    asyncio.run(_capture_async(paths, candidates, limit))


def load_snapshot_bodies(paths: Paths) -> dict[str, dict]:
    """page_id -> {url, body, sha} for every good snapshot."""
    out: dict[str, dict] = {}
    if not paths.manifest.exists():
        return out
    pages = json.loads(paths.manifest.read_text())["pages"]
    for p in pages:
        if p.get("quality") != "good" or not p.get("file"):
            continue
        raw = (paths.snapshots / p["file"]).read_text()
        body = raw.split("---\n", 2)[2] if raw.startswith("---\n") else raw
        out[p["id"]] = {"url": p["url"], "body": body.strip(),
                        "sha": p["content_sha256"]}
    return out
