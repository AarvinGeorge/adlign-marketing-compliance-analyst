# ---------------------------------------------------------------------------
# crawl4ai_fetcher.py — PRIMARY fetcher. Local Playwright render, $0.
# This is the product's locked production crawler, so extraction parity matters.
# Contract: returns result.markdown.raw_markdown (NOT fit_markdown — the fit
#   variant's pruning filter strips exactly the low-density asterisked footnotes
#   and disclosures that are the payload here). CacheMode.BYPASS for fresh text.
# A single AsyncWebCrawler is reused across pages (one browser, many arun calls).
# Deps: crawl4ai, config, models.
# ---------------------------------------------------------------------------
from __future__ import annotations

from ..config import PAGE_TIMEOUT_MS, USER_AGENT
from ..models import FetchResult

_NAME = "crawl4ai"


class Crawl4aiFetcher:
    """Wraps one long-lived AsyncWebCrawler. Use as an async context manager."""

    name = _NAME

    def __init__(self) -> None:
        self._crawler = None
        self._run_config = None

    def available(self) -> bool:
        return True  # no key needed; renders locally

    async def __aenter__(self) -> "Crawl4aiFetcher":
        # Imported lazily so `--help` and unit tests don't require the browser.
        from crawl4ai import (
            AsyncWebCrawler,
            BrowserConfig,
            CacheMode,
            CrawlerRunConfig,
        )

        browser_config = BrowserConfig(
            headless=True,
            user_agent=USER_AGENT,
        )
        self._run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            # NOT networkidle: TurboTax runs continuous analytics beacons, so the
            # network never idles and the page times out. domcontentloaded + a
            # settle delay + full-page scan reliably renders the disclosures.
            wait_until="domcontentloaded",
            page_timeout=PAGE_TIMEOUT_MS,
            delay_before_return_html=3.0,   # let lazy content/footnotes settle
            scan_full_page=True,            # trigger lazy-loaded disclosure blocks
            scroll_delay=0.3,
            remove_overlay_elements=True,
        )
        self._crawler = AsyncWebCrawler(config=browser_config)
        await self._crawler.__aenter__()
        return self

    async def __aexit__(self, *exc) -> None:
        if self._crawler is not None:
            await self._crawler.__aexit__(*exc)
            self._crawler = None

    async def fetch(self, url: str) -> FetchResult:
        if self._crawler is None:
            return FetchResult(_NAME, "", ok=False, error="crawler not started")
        try:
            result = await self._crawler.arun(url=url, config=self._run_config)
        except Exception as exc:  # never raise for a fetch failure
            return FetchResult(_NAME, "", ok=False, error=f"{type(exc).__name__}: {exc}")

        if not getattr(result, "success", False):
            return FetchResult(
                _NAME, "", ok=False,
                error=getattr(result, "error_message", "unknown crawl failure"),
            )

        text = _extract_raw_markdown(result)
        if not text.strip():
            return FetchResult(_NAME, "", ok=False, error="empty markdown")
        return FetchResult(_NAME, text, ok=True)


def _extract_raw_markdown(result) -> str:
    """Prefer raw_markdown; fall back across crawl4ai version shapes.
    Deliberately avoids fit_markdown (it prunes disclosures)."""
    md = getattr(result, "markdown", None)
    if md is None:
        return ""
    # MarkdownGenerationResult object
    raw = getattr(md, "raw_markdown", None)
    if isinstance(raw, str) and raw.strip():
        return raw
    # Some versions expose markdown as a plain string
    if isinstance(md, str):
        return md
    return ""
