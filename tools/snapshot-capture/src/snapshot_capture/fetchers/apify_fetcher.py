# ---------------------------------------------------------------------------
# apify_fetcher.py — FALLBACK #2. Apify Website Content Crawler actor.
# Contract: available() iff APIFY_TOKEN present. fetch() runs the actor for a
#   single URL (maxCrawlPages=1) and returns the item's `text` (its cleaned
#   full-page text). Never raises for a fetch failure; never logs the token.
#   The blocking apify-client call runs in a thread so we stay async-friendly.
# Deps: apify-client (lazy import), config, models.
# ---------------------------------------------------------------------------
from __future__ import annotations

import asyncio

from ..models import FetchResult

_NAME = "apify"
_ACTOR = "apify/website-content-crawler"


class ApifyFetcher:
    name = _NAME

    def __init__(self, token: str | None) -> None:
        self._token = token or None

    def available(self) -> bool:
        return bool(self._token)

    async def fetch(self, url: str) -> FetchResult:
        if not self._token:
            return FetchResult(_NAME, "", ok=False, error="no APIFY_TOKEN")
        try:
            return await asyncio.to_thread(self._run_sync, url)
        except Exception as exc:
            return FetchResult(_NAME, "", ok=False, error=f"{type(exc).__name__}: {exc}")

    def _run_sync(self, url: str) -> FetchResult:
        from apify_client import ApifyClient

        client = ApifyClient(self._token)
        run_input = {
            "startUrls": [{"url": url}],
            "maxCrawlPages": 1,
            "maxCrawlDepth": 0,
            "crawlerType": "playwright:firefox",
            "saveMarkdown": True,
        }
        run = client.actor(_ACTOR).call(run_input=run_input)
        if not run or not run.get("defaultDatasetId"):
            return FetchResult(_NAME, "", ok=False, error="no dataset in run")

        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        if not items:
            return FetchResult(_NAME, "", ok=False, error="empty dataset")

        item = items[0]
        # Prefer markdown, fall back to the cleaned text field.
        text = item.get("markdown") or item.get("text") or ""
        if not text.strip():
            return FetchResult(_NAME, "", ok=False, error="empty text/markdown")
        return FetchResult(_NAME, text, ok=True)
