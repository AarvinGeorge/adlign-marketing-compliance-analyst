# ---------------------------------------------------------------------------
# models.py — plain dataclasses for the pipeline.
# Contract: PageSpec = one curated input row. FetchResult = one fetcher's
#   attempt output. Snapshot = the fully classified result ready to serialize.
# Deps: none (stdlib only).
# ---------------------------------------------------------------------------
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class PageSpec:
    id: str
    url: str
    discovery: str  # the "src" field from curated_pages.json


@dataclass
class FetchResult:
    """One fetcher attempt. `text` is the extracted body (may be empty)."""
    fetcher: str
    text: str
    ok: bool
    error: Optional[str] = None
    attempts: int = 1


@dataclass
class Snapshot:
    spec: PageSpec
    fetcher: str            # which fetcher's body we kept
    body: str               # verbatim visible text
    quality: str            # good | thin | failed
    content_sha256: str
    word_count: int
    fetched_at: str         # ISO UTC
    notes: str
    triggers: dict = field(default_factory=dict)
