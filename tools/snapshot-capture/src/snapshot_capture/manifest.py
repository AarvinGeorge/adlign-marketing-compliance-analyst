# ---------------------------------------------------------------------------
# manifest.py — deterministic manifest built FROM the snapshots on disk.
# Contract: build_manifest(snapshots_dir, curated) reads every *.md snapshot,
#   recomputes hash/word_count/triggers from the stored body, and returns a
#   dict sorted by id with NO timestamp. Re-running on unchanged files yields
#   byte-identical JSON (the determinism guarantee). Ordering: id numeric asc.
# Deps: snapshot_io, triggers.
# ---------------------------------------------------------------------------
from __future__ import annotations

import json
import re
from pathlib import Path

from .snapshot_io import body_sha256, parse_front_matter, word_count
from .triggers import compute_triggers


def _id_sort_key(page_id: str) -> tuple[int, str]:
    m = re.match(r"[A-Za-z]*(\d+)", page_id)
    return (int(m.group(1)) if m else 0, page_id)


def build_manifest(snapshots_dir: Path) -> dict:
    entries = []
    for path in snapshots_dir.glob("*.md"):
        text = path.read_text(encoding="utf-8")
        fm, body = parse_front_matter(text)
        if fm is None:
            continue
        entries.append(
            {
                "id": fm.get("id", path.stem.split("_")[0]),
                "url": fm.get("url", ""),
                "fetcher": fm.get("fetcher", "unknown"),
                "quality": fm.get("quality", "unknown"),
                "word_count": word_count(body),
                "content_sha256": body_sha256(body),
                "triggers": compute_triggers(body),
            }
        )
    entries.sort(key=lambda e: _id_sort_key(e["id"]))
    return {"snapshot_count": len(entries), "pages": entries}


def write_manifest(manifest_path: Path, manifest: dict) -> None:
    # Sorted keys + trailing newline => stable, diffable, deterministic bytes.
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
