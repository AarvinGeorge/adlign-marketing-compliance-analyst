# ---------------------------------------------------------------------------
# textnorm.py — normalization, quote validation, finding overlap.
# Contract: mirrors the product's hard-won conventions (v1 M3 lessons):
#   markdown links unwrapped ([text](url) -> text), emphasis chars stripped,
#   curly punctuation straightened, whitespace collapsed. A quote is VALID
#   only if its normalized form is a contiguous substring of the normalized
#   body. Never loosened on content.
# Deps: stdlib.
# ---------------------------------------------------------------------------
from __future__ import annotations

import hashlib
import re

_CURLY = {
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "–": "-", "—": "-", " ": " ",
}
_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")


def normalize(text: str) -> str:
    for k, v in _CURLY.items():
        text = text.replace(k, v)
    text = _LINK_RE.sub(r"\1", text)          # unwrap markdown links
    text = re.sub(r"[*_`#>]", "", text)       # strip markdown emphasis/headers
    text = re.sub(r"\s+", " ", text)          # collapse all whitespace
    return text.strip().lower()


def quote_is_valid(quote: str, body: str) -> bool:
    q = normalize(quote)
    return bool(q) and q in normalize(body)


def token_jaccard(a: str, b: str) -> float:
    ta, tb = set(normalize(a).split()), set(normalize(b).split())
    if not ta or not tb:
        return 1.0 if ta == tb else 0.0
    return len(ta & tb) / len(ta | tb)


def body_sha256(body: str) -> str:
    """v1 hash convention: sha256 of the whitespace-stripped body."""
    return hashlib.sha256(body.strip().encode()).hexdigest()


def split_for(page_id: str, salt: str, test_fraction: float) -> str:
    """Deterministic page-level train/test assignment."""
    h = hashlib.sha256(f"{salt}:{page_id}".encode()).digest()
    return "test" if (h[0] / 255.0) < test_fraction else "train"
