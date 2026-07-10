# ---------------------------------------------------------------------------
# config.py — paths, politeness constants, and .env loading.
# Contract: resolve_paths() locates ground-truth/ relative to this tool, no
#   matter the CWD. load_keys() reads fallback creds from the tool-local .env
#   ONLY (never the app-level code/.env). Keys are never logged.
# Deps: python-dotenv.
# ---------------------------------------------------------------------------
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values

# Politeness (spec rule 4).
MAX_CONCURRENCY = 2
REQUEST_SPACING_S = 2.5  # seconds between request *starts*
PAGE_TIMEOUT_MS = 60_000

# Honest UA: a real Chrome UA (so Akamai renders) with an identifying suffix
# naming the tool and a contact. Truthful about who is crawling.
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 "
    "shiboleth-snapshot-capture/0.1 (+contact: tomgrg8@gmail.com)"
)

# Quality thresholds (spec rule 2).
THIN_WORD_THRESHOLD = 150

# Valid fetcher labels. "webfetch" is a legacy-only value (the 14 pre-existing
# snapshots were captured with a WebFetch-style tool); the production ingestion
# service never emits it. See README.
FETCHERS = ("crawl4ai", "hyperbrowser", "apify", "webfetch")


@dataclass(frozen=True)
class Paths:
    tool_root: Path
    project_root: Path
    ground_truth: Path
    curated_pages: Path
    snapshots: Path
    manifest: Path
    env_file: Path


def resolve_paths() -> Paths:
    """Locate project directories relative to this file, independent of CWD.

    Layout: <project>/code/tools/snapshot-capture/src/snapshot_capture/config.py
    so the project root is five parents up from this file.
    """
    here = Path(__file__).resolve()
    tool_root = here.parents[2]          # .../code/tools/snapshot-capture
    project_root = here.parents[5]       # .../marketing-compliance-checker
    ground_truth = project_root / "ground-truth"
    return Paths(
        tool_root=tool_root,
        project_root=project_root,
        ground_truth=ground_truth,
        curated_pages=ground_truth / "curated_pages.json",
        snapshots=ground_truth / "snapshots",
        manifest=ground_truth / "snapshot_manifest.json",
        env_file=tool_root / ".env",
    )


def load_keys(env_file: Path) -> dict[str, str]:
    """Read fallback creds from the tool-local .env only. Returns a dict with
    HYPERBROWSER_API_KEY / APIFY_TOKEN when present (empty string if absent).
    Values are never logged; callers check truthiness only.
    """
    values: dict[str, str] = {}
    if env_file.exists():
        values = {k: v for k, v in dotenv_values(env_file).items() if v}
    # Environment overrides file, but we still never touch the app-level .env.
    for key in ("HYPERBROWSER_API_KEY", "APIFY_TOKEN"):
        if os.environ.get(key):
            values[key] = os.environ[key]
    return values
