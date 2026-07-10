# ---------------------------------------------------------------------------
# discover.py — OPTIONAL (--discover). Render the TurboTax search results page
#   for a fixed set of rule-relevant terms and harvest new marketing URLs.
# Contract: discover_urls(fetcher, existing_urls) -> list[(url, term)] of up to
#   MAX_NEW_URLS new marketing URLs not already curated. Uses the same crawl4ai
#   fetcher (its links, when available) plus a markdown link scrape. Best-effort:
#   the search page is JS-heavy and may yield nothing; that is acceptable.
# Deps: crawl4ai fetcher, stdlib.
# ---------------------------------------------------------------------------
from __future__ import annotations

import re
from urllib.parse import urlparse

SEARCH_TERMS = [
    "free", "refund advance", "APR", "FDIC",
    "checking", "bonus", "referral", "guarantee",
]
MAX_NEW_URLS = 10
_SEARCH_URL = "https://turbotax.intuit.com/search/?q={term}"

# Only keep marketing pages on the main TT domains; drop nav/legal/asset noise.
_ALLOW_HOSTS = {"turbotax.intuit.com", "blog.turbotax.intuit.com"}
_DENY_SUBSTR = (
    "/search", "/login", "/sign-in", "javascript:", "#", "/legal/",
    ".pdf", ".svg", ".png", ".jpg", ".css", ".js", "/account", "myturbotax",
)


def _is_marketing_url(url: str) -> bool:
    try:
        p = urlparse(url)
    except ValueError:
        return False
    if p.scheme not in ("http", "https"):
        return False
    if p.netloc not in _ALLOW_HOSTS:
        return False
    low = url.lower()
    return not any(s in low for s in _DENY_SUBSTR)


_MD_LINK = re.compile(r"\]\((https?://[^)\s]+)\)")


async def discover_urls(fetcher, existing_urls: set[str]) -> list[tuple[str, str]]:
    """Best-effort discovery. Returns [(url, source_term), ...], deduped,
    capped at MAX_NEW_URLS, deterministic order (term order, then first-seen)."""
    found: list[tuple[str, str]] = []
    seen = set(existing_urls)
    for term in SEARCH_TERMS:
        if len(found) >= MAX_NEW_URLS:
            break
        url = _SEARCH_URL.format(term=term.replace(" ", "+"))
        result = await fetcher.fetch(url)
        if not result.ok:
            continue
        for m in _MD_LINK.finditer(result.text):
            candidate = m.group(1).rstrip(".,)")
            if candidate in seen or not _is_marketing_url(candidate):
                continue
            seen.add(candidate)
            found.append((candidate, term))
            if len(found) >= MAX_NEW_URLS:
                break
    return found
