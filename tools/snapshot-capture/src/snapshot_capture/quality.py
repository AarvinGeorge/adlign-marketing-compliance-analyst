# ---------------------------------------------------------------------------
# quality.py — classify an extracted body as good | thin | failed.
# Contract: classify(text, fetch_ok) -> (quality, note_fragment).
#   failed  = no fetcher produced usable text.
#   thin    = usable text but < THIN_WORD_THRESHOLD words (nav-only / blocked).
#   good    = substantive content.
# Never fabricates; only inspects the given text. Deps: config.
# ---------------------------------------------------------------------------
from __future__ import annotations

from .config import THIN_WORD_THRESHOLD
from .snapshot_io import word_count


def classify(text: str, fetch_ok: bool) -> tuple[str, str]:
    wc = word_count(text)
    if not fetch_ok or wc == 0:
        return "failed", "all fetchers failed"
    if wc < THIN_WORD_THRESHOLD:
        return "thin", f"thin content ({wc} words, < {THIN_WORD_THRESHOLD})"
    return "good", f"substantive content ({wc} words)"
