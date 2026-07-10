# ---------------------------------------------------------------------------
# base.py — the Fetcher protocol.
# Contract: every fetcher exposes `name` and an async `fetch(url) -> FetchResult`
#   that NEVER raises for a fetch failure (returns ok=False instead) and NEVER
#   logs credentials. `available()` reports whether the fetcher is usable
#   (e.g. its API key is present).
# Deps: models.
# ---------------------------------------------------------------------------
from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..models import FetchResult


@runtime_checkable
class Fetcher(Protocol):
    name: str

    def available(self) -> bool: ...

    async def fetch(self, url: str) -> FetchResult: ...
