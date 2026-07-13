# ---------------------------------------------------------------------------
# cli.py — gt2 <stage> [--limit N] entrypoint. Stages are resumable; every
#   LLM call is disk-cached, so re-running a stage never re-spends.
# Deps: all gt2 modules.
# ---------------------------------------------------------------------------
from __future__ import annotations

import argparse
import json

from .config import DEFAULT_TARGET_PAGES, ensure_dirs, load_env, resolve_paths


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="gt2",
        description="Ground truth v2: semantic discovery + 3-LLM judge panel")
    sub = parser.add_subparsers(dest="stage", required=True)
    for name in ("discover", "capture", "screen", "judge", "consensus",
                 "assemble", "synthetics", "status"):
        p = sub.add_parser(name)
        p.add_argument("--limit", type=int, default=None,
                       help="process at most N items (pilot runs)")
        if name == "discover":
            p.add_argument("--target", type=int, default=DEFAULT_TARGET_PAGES)
        if name == "synthetics":
            p.add_argument("--count", type=int, default=100)

    args = parser.parse_args()
    paths = resolve_paths()
    load_env(paths)
    ensure_dirs(paths)

    if args.stage == "discover":
        from .discover import discover
        discover(paths, target=args.target, limit=args.limit)
    elif args.stage == "capture":
        from .capture import capture
        capture(paths, limit=args.limit)
    elif args.stage == "screen":
        from .screen import screen
        screen(paths, limit=args.limit)
    elif args.stage == "judge":
        from .judge import judge
        judge(paths, limit=args.limit)
    elif args.stage == "consensus":
        from .consensus import consensus
        consensus(paths, limit=args.limit)
    elif args.stage == "assemble":
        from .assemble import assemble
        assemble(paths)
    elif args.stage == "synthetics":
        from .synthetics import synthetics
        synthetics(paths, count=args.count, limit=args.limit)
    elif args.stage == "status":
        _status(paths)


def _status(paths) -> None:
    def count(path, key=None):
        if not path.exists():
            return "-"
        data = json.loads(path.read_text())
        return len(data[key]) if key else len(data)

    print(f"candidates : {count(paths.candidates, 'candidates')}")
    print(f"snapshots  : {count(paths.manifest, 'pages')} manifest entries, "
          f"{len(list(paths.snapshots.glob('*.md')))} files")
    print(f"screened   : {count(paths.screen)}")
    print(f"judged     : {len(list(paths.judgments.glob('*.json')))} pairs")
    print(f"consensus  : {count(paths.data / 'consensus.json')}")
    syn = paths.synthetics_dir / "synthetics_validated.json"
    print(f"synthetics : {count(syn, 'records')} validated, "
          f"{count(paths.synthetics_dir / 'quarantine.json')} quarantined")
    if paths.records.exists():
        meta = json.loads(paths.records.read_text())["_meta"]
        print(f"records    : {meta['counts']['records']} "
              f"({meta['counts']['by_split']})")
    else:
        print("records    : -")


if __name__ == "__main__":
    main()
