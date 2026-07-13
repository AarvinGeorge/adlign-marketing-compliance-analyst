# ---------------------------------------------------------------------------
# config.py — paths, model roster, politeness, env loading.
# Contract: keys come from <project>/code/.env READ-ONLY (never written, never
#   logged). All models env-overridable (GT2_JUDGE_A etc.). Paths resolve
#   relative to this file so the CLI works from any CWD.
# Deps: python-dotenv.
# ---------------------------------------------------------------------------
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import dotenv_values

# --- model roster (Aarvin 2026-07-13: Anthropic + OpenAI paid only; no
# Gemini, no Groq; 3 varied judges + a 4th arbiter for the final call) ------
JUDGE_MODELS = [
    os.environ.get("GT2_JUDGE_A", "anthropic:claude-sonnet-5"),
    os.environ.get("GT2_JUDGE_B", "openai:gpt-5.1"),
    os.environ.get("GT2_JUDGE_C", "openai:gpt-5"),
]
ARBITER_MODEL = os.environ.get("GT2_ARBITER", "anthropic:claude-opus-4-8")
SCREEN_MODEL = os.environ.get("GT2_SCREEN", "anthropic:claude-haiku-4-5-20251001")
RANK_MODEL = os.environ.get("GT2_RANK", "anthropic:claude-sonnet-5")

# --- discovery / capture ----------------------------------------------------
SITEMAP_URLS = [
    "https://turbotax.intuit.com/sitemap.xml",
    "https://blog.turbotax.intuit.com/sitemap_index.xml",
]
ALLOW_HOSTS = {"turbotax.intuit.com", "blog.turbotax.intuit.com"}
DENY_SUBSTR = (
    "/search", "/login", "/sign-in", "javascript:", "/legal/", ".pdf", ".svg",
    ".png", ".jpg", ".css", ".js", "/account", "myturbotax", "/es/",  # es later
    "/tax-tools/calculator",  # calculators: thin interactive shells
)
DEFAULT_TARGET_PAGES = 80          # capture budget for the full run
PAGE_TEXT_CAP = 60_000             # chars of page text a judge sees (full-page
                                   # judging is the v1 iter-6 lesson; cap only
                                   # guards degenerate mega-pages)
# politeness: mirror the proven v1 capture tool
MAX_CONCURRENCY = 2
REQUEST_SPACING_S = 2.5
PAGE_TIMEOUT_MS = 60_000
THIN_WORD_THRESHOLD = 150
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 "
    "shiboleth-gt2-harness/0.1 (+contact: tomgrg8@gmail.com)"
)

# --- split discipline --------------------------------------------------------
TEST_FRACTION = 0.30               # sha256(page_id) → 70 train / 30 test
SPLIT_SALT = "gt2-v1"              # frozen; changing it reshuffles the split

# --- consensus ---------------------------------------------------------------
EVIDENCE_OVERLAP_THRESHOLD = 0.55  # token-Jaccard to group judge findings


@dataclass(frozen=True)
class Paths:
    root: Path                      # ground-truth-v2/
    project_root: Path              # marketing-compliance-checker/
    data: Path
    cache: Path
    snapshots: Path
    candidates: Path
    manifest: Path
    screen: Path
    judgments: Path
    records: Path                   # ground_truth_v2.json
    synthetics_dir: Path
    v1_ground_truth: Path
    v1_curated: Path
    scorecard_doc: Path
    env_file: Path                  # code/.env (read-only)


def resolve_paths() -> Paths:
    here = Path(__file__).resolve()
    root = here.parents[3]                       # ground-truth-v2/
    project_root = root.parent
    data = root / "data"
    return Paths(
        root=root,
        project_root=project_root,
        data=data,
        cache=data / ".cache",
        snapshots=data / "snapshots",
        candidates=data / "candidates.json",
        manifest=data / "manifest.json",
        screen=data / "screen.json",
        judgments=data / "judgments",
        records=data / "ground_truth_v2.json",
        synthetics_dir=data / "synthetics",
        v1_ground_truth=project_root / "ground-truth" / "ground_truth.json",
        v1_curated=project_root / "ground-truth" / "curated_pages.json",
        scorecard_doc=project_root
        / "05_shibboleth_problem_context_and_scorecard_2026-07-09.md",
        env_file=project_root / "code" / ".env",
    )


def load_env(paths: Paths) -> None:
    """Export ANTHROPIC/OPENAI keys (+ optional LangSmith) into the process
    env for LangChain. Values are never logged."""
    values = dotenv_values(paths.env_file) if paths.env_file.exists() else {}
    wanted = ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "LANGSMITH_API_KEY",
              "LANGSMITH_TRACING")
    for key in wanted:
        if not os.environ.get(key) and values.get(key):
            os.environ[key] = values[key]  # type: ignore[assignment]
    # langsmith's check is case-sensitive: TRUE (as in code/.env) silently
    # disables tracing. Normalize, and set the legacy flag too.
    if os.environ.get("LANGSMITH_TRACING", "").lower() in ("true", "1"):
        os.environ["LANGSMITH_TRACING"] = "true"
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ.setdefault("LANGSMITH_PROJECT", "shiboleth-gt2")


def ensure_dirs(paths: Paths) -> None:
    for p in (paths.data, paths.cache, paths.snapshots, paths.judgments,
              paths.synthetics_dir):
        p.mkdir(parents=True, exist_ok=True)
