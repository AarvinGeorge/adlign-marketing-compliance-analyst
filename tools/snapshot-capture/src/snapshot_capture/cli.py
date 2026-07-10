# ---------------------------------------------------------------------------
# cli.py — orchestration + entry point for snapshot-capture.
# Contract:
#   read curated_pages.json -> for each page decide (skip | refetch | fetch) ->
#   run the fetcher chain (crawl4ai -> hyperbrowser -> apify, 1 retry each,
#   advancing only on thin/blocked/failed) -> classify -> write snapshot ->
#   rebuild the deterministic manifest -> print the summary table.
# Idempotency (spec rule 3, per Aarvin's override):
#   - default: refetch ALL curated pages with crawl4ai (homogenize corpus).
#     For a page that already has a `good` snapshot, if the crawl4ai refetch
#     degrades (thin/failed), KEEP the old body and label fetcher accordingly
#     (legacy `webfetch` bodies stay `webfetch`).
#   - --skip-good: classic idempotent mode (skip existing `good`, fill/refetch
#     thin/failed/missing).
#   - --refetch-all: force overwrite even when the refetch degrades.
# Politeness: Semaphore(2), >=2.5s between request starts, honest UA (config).
# Deps: all sibling modules + crawl4ai (via fetcher).
# ---------------------------------------------------------------------------
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from . import config
from .config import Paths, load_keys, resolve_paths
from .discover import discover_urls
from .fetchers.apify_fetcher import ApifyFetcher
from .fetchers.crawl4ai_fetcher import Crawl4aiFetcher
from .fetchers.hyperbrowser_fetcher import HyperbrowserFetcher
from .manifest import build_manifest, write_manifest
from .models import PageSpec, Snapshot
from .quality import classify
from .snapshot_io import (
    body_sha256,
    parse_front_matter,
    snapshot_filename,
    word_count,
    write_snapshot,
)
from .triggers import compute_triggers


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---- input / existing-state helpers ---------------------------------------

def load_curated(paths: Paths) -> list[PageSpec]:
    data = json.loads(paths.curated_pages.read_text(encoding="utf-8"))
    return [
        PageSpec(id=p["id"], url=p["url"], discovery=p.get("src", ""))
        for p in data["pages"]
    ]


def find_existing_snapshot(paths: Paths, page_id: str) -> Path | None:
    matches = sorted(paths.snapshots.glob(f"{page_id}_*.md"))
    return matches[0] if matches else None


def read_existing(path: Path) -> tuple[dict | None, str]:
    fm, body = parse_front_matter(path.read_text(encoding="utf-8"))
    return fm, body


# ---- the fetcher chain -----------------------------------------------------

class FetcherChain:
    """crawl4ai (primary) -> hyperbrowser -> apify. One retry per fetcher.
    Advances to the next fetcher only when the current result is thin/failed."""

    def __init__(self, crawl4ai: Crawl4aiFetcher, fallbacks: list) -> None:
        self._primary = crawl4ai
        self._fallbacks = [f for f in fallbacks if f.available()]

    async def run(self, url: str) -> tuple[str, str, bool, list[str]]:
        """Return (fetcher_name, body, ok, trace) for the best result.
        `ok` means good-quality text was produced by that fetcher."""
        trace: list[str] = []
        best_name, best_text = "crawl4ai", ""
        for fetcher in [self._primary, *self._fallbacks]:
            body, produced = await self._attempt(fetcher, url, trace)
            if produced:
                quality, _ = classify(body, True)
                if len(best_text.split()) < word_count(body):
                    best_name, best_text = fetcher.name, body
                if quality == "good":
                    return fetcher.name, body, True, trace
        # Nothing reached good; return the longest text we saw (may be thin/empty).
        return best_name, best_text, False, trace

    async def _attempt(self, fetcher, url: str, trace: list[str]) -> tuple[str, bool]:
        for attempt in (1, 2):  # one retry
            result = await fetcher.fetch(url)
            if result.ok and result.text.strip():
                trace.append(f"{fetcher.name}:ok(try{attempt},{word_count(result.text)}w)")
                return result.text, True
            trace.append(f"{fetcher.name}:fail(try{attempt}:{result.error})")
            if attempt == 1:
                await asyncio.sleep(config.REQUEST_SPACING_S)
        return "", False


# ---- per-page processing ---------------------------------------------------

def _decide(mode: str, fm: dict | None) -> str:
    """Return 'skip' | 'fetch' | 'refetch-keep-on-degrade' | 'refetch-force'."""
    existing_good = bool(fm) and fm.get("quality") == "good"
    if fm is None:
        return "fetch"  # missing
    if mode == "skip-good":
        return "skip" if existing_good else "fetch"
    if mode == "refetch-all":
        return "refetch-force"
    # default homogenize mode
    return "refetch-keep-on-degrade" if existing_good else "fetch"


async def process_page(
    spec: PageSpec,
    paths: Paths,
    chain: FetcherChain,
    mode: str,
    sem: asyncio.Semaphore,
    pacer: "Pacer",
) -> Snapshot:
    existing_path = find_existing_snapshot(paths, spec.id)
    fm, existing_body = (read_existing(existing_path) if existing_path else (None, ""))
    decision = _decide(mode, fm)

    if decision == "skip":
        body = existing_body
        quality, _ = classify(body, bool(body.strip()))
        return _snapshot_from_existing(spec, fm, body, quality, existing_path, paths)

    async with sem:
        await pacer.wait()
        fetcher_name, body, ok, trace = await chain.run(spec.url)

    quality, note = classify(body, ok or bool(body.strip()))

    # Degrade protection: keep prior good body if the refetch came back worse.
    if decision == "refetch-keep-on-degrade" and quality != "good":
        old_quality, _ = classify(existing_body, bool(existing_body.strip()))
        if old_quality == "good":
            old_fetcher = (fm or {}).get("fetcher") or "webfetch"
            note = f"kept prior {old_fetcher} body; crawl4ai refetch degraded ({quality})"
            return _finalize(spec, old_fetcher, existing_body, "good", note, paths)

    note = f"{note}; chain={'>'.join(trace)}" if trace else note
    return _finalize(spec, fetcher_name, body, quality, note, paths)


def _snapshot_from_existing(spec, fm, body, quality, path, paths) -> Snapshot:
    """Skip path: recompute hash/fetcher fields without refetching, rewrite file
    so missing fetcher/content_sha256 fields get backfilled."""
    fetcher = (fm or {}).get("fetcher") or "webfetch"
    return _finalize(spec, fetcher, body, quality,
                     (fm or {}).get("notes", "existing good snapshot; unchanged"),
                     paths, fetched_at=(fm or {}).get("fetched_at"))


def _finalize(spec, fetcher, body, quality, note, paths, fetched_at=None) -> Snapshot:
    sha = body_sha256(body)
    snap = Snapshot(
        spec=spec,
        fetcher=fetcher,
        body=body,
        quality=quality,
        content_sha256=sha,
        word_count=word_count(body),
        fetched_at=fetched_at or _utc_now_iso(),
        notes=note,
        triggers=compute_triggers(body),
    )
    _write(snap, paths)
    return snap


def _write(snap: Snapshot, paths: Paths) -> None:
    # Remove any stale file for this id with a different slug, then write.
    for old in paths.snapshots.glob(f"{snap.spec.id}_*.md"):
        if old.name != snapshot_filename(snap.spec.id, snap.spec.url):
            old.unlink()
    fields = {
        "id": snap.spec.id,
        "url": snap.spec.url,
        "discovery": snap.spec.discovery,
        "fetched_at": snap.fetched_at,
        "fetcher": snap.fetcher,
        "content_sha256": snap.content_sha256,
        "quality": snap.quality,
        "notes": snap.notes,
    }
    path = paths.snapshots / snapshot_filename(snap.spec.id, snap.spec.url)
    write_snapshot(path, fields, snap.body)


class Pacer:
    """Enforce >= REQUEST_SPACING_S between successive request starts."""

    def __init__(self, spacing: float) -> None:
        self._spacing = spacing
        self._lock = asyncio.Lock()
        self._last = 0.0

    async def wait(self) -> None:
        async with self._lock:
            now = time.monotonic()
            delta = now - self._last
            if delta < self._spacing:
                await asyncio.sleep(self._spacing - delta)
            self._last = time.monotonic()


# ---- discover --------------------------------------------------------------

def append_discovered(paths: Paths, discovered: list[tuple[str, str]]) -> list[PageSpec]:
    if not discovered:
        return []
    data = json.loads(paths.curated_pages.read_text(encoding="utf-8"))
    existing_ids = [p["id"] for p in data["pages"]]
    max_n = max((int(pid[1:]) for pid in existing_ids if pid[1:].isdigit()), default=0)
    new_specs = []
    for i, (url, term) in enumerate(discovered, start=1):
        pid = f"P{max_n + i}"
        data["pages"].append(
            {"id": pid, "url": url, "why": f"discovered via search '{term}'", "src": term}
        )
        new_specs.append(PageSpec(id=pid, url=url, discovery=term))
    paths.curated_pages.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return new_specs


# ---- summary table ---------------------------------------------------------

def print_summary(snapshots: list[Snapshot]) -> None:
    from collections import Counter

    by_quality = Counter(s.quality for s in snapshots)
    by_fetcher = Counter(s.fetcher for s in snapshots)

    def _tbl(title: str, counter: Counter, order: tuple) -> str:
        keys = [k for k in order if k in counter] + [k for k in counter if k not in order]
        width = max([len(title)] + [len(k) for k in keys] + [5])
        lines = [f"  {title.ljust(width)}  count", f"  {'-' * width}  -----"]
        for k in keys:
            lines.append(f"  {k.ljust(width)}  {str(counter[k]).rjust(5)}")
        lines.append(f"  {'TOTAL'.ljust(width)}  {str(sum(counter.values())).rjust(5)}")
        return "\n".join(lines)

    print("\n" + "=" * 48)
    print("  SNAPSHOT CAPTURE — SUMMARY")
    print("=" * 48)
    print("\nBy quality:")
    print(_tbl("quality", by_quality, ("good", "thin", "failed")))
    print("\nBy fetcher:")
    print(_tbl("fetcher", by_fetcher, config.FETCHERS))
    print("=" * 48 + "\n")


# ---- main ------------------------------------------------------------------

async def run(args: argparse.Namespace) -> int:
    paths = resolve_paths()
    paths.snapshots.mkdir(parents=True, exist_ok=True)
    if not paths.curated_pages.exists():
        print(f"ERROR: {paths.curated_pages} not found", file=sys.stderr)
        return 2

    mode = "skip-good" if args.skip_good else ("refetch-all" if args.refetch_all else "default")
    keys = load_keys(paths.env_file)
    fallbacks = [
        HyperbrowserFetcher(keys.get("HYPERBROWSER_API_KEY")),
        ApifyFetcher(keys.get("APIFY_TOKEN")),
    ]
    active_fallbacks = [f.name for f in fallbacks if f.available()]
    print(f"Mode: {mode} | fallbacks available: {active_fallbacks or 'none (crawl4ai-only)'}")

    specs = load_curated(paths)
    sem = asyncio.Semaphore(config.MAX_CONCURRENCY)
    pacer = Pacer(config.REQUEST_SPACING_S)

    async with Crawl4aiFetcher() as crawl4ai:
        chain = FetcherChain(crawl4ai, fallbacks)

        if args.discover:
            print("Discovering new URLs via search terms...")
            existing_urls = {s.url for s in specs}
            discovered = await discover_urls(crawl4ai, existing_urls)
            print(f"  discovered {len(discovered)} new URL(s)")
            specs += append_discovered(paths, discovered)

        if args.limit:
            specs = specs[: args.limit]

        print(f"Processing {len(specs)} page(s)...\n")
        tasks = [process_page(s, paths, chain, mode, sem, pacer) for s in specs]
        snapshots: list[Snapshot] = []
        for coro in asyncio.as_completed(tasks):
            snap = await coro
            snapshots.append(snap)
            print(f"  [{snap.quality:6}] {snap.spec.id:5} {snap.fetcher:11} "
                  f"{snap.word_count:6}w  {snap.spec.url}")

    # Rebuild manifest deterministically from disk (source of truth = files).
    manifest = build_manifest(paths.snapshots)
    write_manifest(paths.manifest, manifest)
    print(f"\nManifest written: {paths.manifest} ({manifest['snapshot_count']} pages)")

    snapshots.sort(key=lambda s: int(s.spec.id[1:]) if s.spec.id[1:].isdigit() else 0)
    print_summary(snapshots)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="snapshot-capture",
        description="Capture ground-truth snapshots of curated TurboTax pages.",
    )
    p.add_argument("--skip-good", action="store_true",
                   help="Classic idempotent mode: skip existing 'good' snapshots.")
    p.add_argument("--refetch-all", action="store_true",
                   help="Force overwrite every page with crawl4ai, even on degrade.")
    p.add_argument("--discover", action="store_true",
                   help="Harvest up to 10 new marketing URLs via TT search, then snapshot them.")
    p.add_argument("--limit", type=int, default=0,
                   help="Process only the first N pages (debugging).")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return asyncio.run(run(args))
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
