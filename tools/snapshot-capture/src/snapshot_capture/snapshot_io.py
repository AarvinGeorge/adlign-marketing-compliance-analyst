# ---------------------------------------------------------------------------
# snapshot_io.py — the on-disk snapshot format is defined HERE and nowhere else.
# Contract:
#   - body_sha256(text): canonical hash = sha256 of the body after normalize().
#   - normalize_body(text): strip leading/trailing newlines; the stored form.
#   - slug(url): short kebab slug for the filename.
#   - write_snapshot / parse_front_matter: exact front-matter round-trip.
# The hash binds ground truth. New files are written already-normalized so a
# later recompute from disk is byte-identical (determinism guarantee).
# Deps: stdlib only.
# ---------------------------------------------------------------------------
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

# Front-matter field order (fixed, for stable diffs).
_FIELD_ORDER = (
    "id", "url", "discovery", "fetched_at", "fetcher",
    "content_sha256", "quality", "notes",
)


def normalize_body(text: str) -> str:
    """The canonical stored body form: no leading/trailing blank lines."""
    return text.strip("\n").rstrip() + "\n" if text.strip() else ""


def _body_for_hash(text: str) -> str:
    """Body form that the hash is taken over: fully stripped (no trailing NL).
    Independent of trailing-whitespace churn so recompute always agrees."""
    return text.strip()


def body_sha256(text: str) -> str:
    return hashlib.sha256(_body_for_hash(text).encode("utf-8")).hexdigest()


def word_count(text: str) -> int:
    return len(text.split())


def slug(url: str, maxlen: int = 40) -> str:
    """Short kebab slug from the URL's last meaningful path segment."""
    path = urlparse(url).path.strip("/")
    segments = [s for s in path.split("/") if s]
    tail = segments[-1] if segments else urlparse(url).netloc
    tail = re.sub(r"\.(jsp|html?|php|aspx)$", "", tail, flags=re.I)
    tail = re.sub(r"[^a-zA-Z0-9]+", "-", tail).strip("-").lower()
    if not tail:
        tail = "page"
    return tail[:maxlen].rstrip("-")


def snapshot_filename(page_id: str, url: str) -> str:
    return f"{page_id}_{slug(url)}.md"


def render_front_matter(fields: dict) -> str:
    lines = ["---"]
    for key in _FIELD_ORDER:
        if key in fields and fields[key] is not None:
            lines.append(f"{key}: {fields[key]}")
    lines.append("---")
    return "\n".join(lines)


def write_snapshot(path: Path, fields: dict, body: str) -> None:
    front = render_front_matter(fields)
    content = f"{front}\n\n{normalize_body(body)}"
    path.write_text(content, encoding="utf-8")


def parse_front_matter(text: str) -> tuple[Optional[dict], str]:
    """Return (front_matter_dict, body). If no valid front matter, (None, text).
    Only splits on the first two '---' fence lines; body is verbatim after."""
    if not text.startswith("---"):
        return None, text
    lines = text.split("\n")
    if lines[0].strip() != "---":
        return None, text
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return None, text
    fm: dict = {}
    for line in lines[1:end]:
        if not line.strip():
            continue
        m = re.match(r"^([a-zA-Z0-9_]+):\s?(.*)$", line)
        if m:
            fm[m.group(1)] = m.group(2)
    body = "\n".join(lines[end + 1:]).lstrip("\n")
    return fm, body
