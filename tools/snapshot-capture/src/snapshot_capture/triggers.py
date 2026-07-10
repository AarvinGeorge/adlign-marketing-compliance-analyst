# ---------------------------------------------------------------------------
# triggers.py — case-insensitive keyword hit detection for the manifest.
# Contract: compute_triggers(body) -> {free, apr_finance, fdic_deposit,
#   bonus_reward}, each a bool. Word-boundary matching so "freedom" != "free".
# These map to the four demo rules (R-01 free, R-02 APR/finance, R-03 FDIC/
# deposit, R-04 bonus/rewards). Deterministic: pure function of the body text.
# Deps: stdlib only.
# ---------------------------------------------------------------------------
from __future__ import annotations

import re

# Each trigger: a compiled alternation, case-insensitive, word-bounded.
_PATTERNS = {
    "free": r"free",
    "apr_finance": r"apr|finance charge",
    "fdic_deposit": r"fdic|deposit|checking|savings",
    "bonus_reward": r"bonus|reward|referral",
}
_COMPILED = {
    name: re.compile(rf"\b(?:{pat})\b", re.IGNORECASE)
    for name, pat in _PATTERNS.items()
}


def compute_triggers(body: str) -> dict[str, bool]:
    return {name: bool(rx.search(body)) for name, rx in _COMPILED.items()}
