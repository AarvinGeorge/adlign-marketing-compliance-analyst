# ---------------------------------------------------------------------------
# hyperbrowser_fetcher.py — FALLBACK #1. Cloud render for pages crawl4ai can't.
# Contract: available() iff HYPERBROWSER_API_KEY present. fetch() returns the
#   scrape's markdown. Uses stealth + full-page main content so disclosures
#   survive. Never raises for a fetch failure; never logs the key.
# Deps: hyperbrowser SDK (lazy import), config, models.
# ---------------------------------------------------------------------------
from __future__ import annotations

from ..models import FetchResult

_NAME = "hyperbrowser"


class HyperbrowserFetcher:
    name = _NAME

    def __init__(self, api_key: str | None) -> None:
        self._api_key = api_key or None

    def available(self) -> bool:
        return bool(self._api_key)

    async def fetch(self, url: str) -> FetchResult:
        if not self._api_key:
            return FetchResult(_NAME, "", ok=False, error="no HYPERBROWSER_API_KEY")
        try:
            from hyperbrowser import AsyncHyperbrowser
            from hyperbrowser.models import (
                CreateSessionParams,
                ScrapeOptions,
                StartScrapeJobParams,
            )
        except Exception as exc:  # SDK not installed
            return FetchResult(_NAME, "", ok=False, error=f"import failed: {exc}")

        try:
            async with AsyncHyperbrowser(api_key=self._api_key) as client:
                result = await client.scrape.start_and_wait(
                    StartScrapeJobParams(
                        url=url,
                        scrape_options=ScrapeOptions(
                            formats=["markdown"],
                            only_main_content=True,
                            wait_for=1500,
                        ),
                        session_options=CreateSessionParams(use_stealth=True),
                    )
                )
        except Exception as exc:
            return FetchResult(_NAME, "", ok=False, error=f"{type(exc).__name__}: {exc}")

        data = getattr(result, "data", None)
        text = getattr(data, "markdown", None) if data else None
        if not text or not text.strip():
            status = getattr(result, "status", "unknown")
            return FetchResult(_NAME, "", ok=False, error=f"empty markdown (status={status})")
        return FetchResult(_NAME, text, ok=True)
