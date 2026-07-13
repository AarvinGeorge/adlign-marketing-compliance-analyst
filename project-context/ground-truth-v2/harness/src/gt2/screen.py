# ---------------------------------------------------------------------------
# screen.py — semantic relevance screen: which rules could apply to each page.
# Contract: one cheap-LLM call per page covering all 4 rules. "Not relevant"
#   becomes an honest not_applicable record downstream (judgment_source
#   semantic_screen) and is NEVER panel-judged (cost control). Errs toward
#   relevant. Output: data/screen.json {page_id: [4 rule results]}.
# Deps: llm, rules, capture, config.
# ---------------------------------------------------------------------------
from __future__ import annotations

import json

from .config import PAGE_TEXT_CAP, SCREEN_MODEL, Paths
from .capture import load_snapshot_bodies
from .llm import invoke_structured
from .models import ScreenVerdict
from .rules import load_rules


def screen(paths: Paths, limit: int | None = None) -> None:
    rules = load_rules(paths)
    pages = load_snapshot_bodies(paths)
    done: dict = {}
    if paths.screen.exists():
        done = json.loads(paths.screen.read_text())

    rule_block = "\n\n".join(f"{r.id}: {r.verbatim_text}" for r in rules)
    system = (
        "You are a marketing-compliance screener for Intuit. For each of the "
        "four scorecard rules below, decide whether THIS page contains any "
        "language the rule could plausibly govern (its trigger). You are a "
        "recall-oriented screen: when in doubt, mark relevant=true and let "
        "the full judging panel decide. Think about what each rule GOVERNS "
        "semantically, not keyword presence: a violation may be phrased "
        "without the obvious trigger words.\n\nScorecard (verbatim):\n\n"
        + rule_block
    )

    todo = [pid for pid in pages if pid not in done]
    if limit:
        todo = todo[:limit]
    for i, pid in enumerate(sorted(todo), 1):
        body = pages[pid]["body"][:PAGE_TEXT_CAP]
        verdict = invoke_structured(
            paths.cache, SCREEN_MODEL, ScreenVerdict, system,
            f"Page {pid} ({pages[pid]['url']}):\n\n{body}",
        )
        done[pid] = [r.model_dump() for r in verdict.results]
        rel = [r.rule_id for r in verdict.results if r.relevant]
        print(f"  [{i}/{len(todo)}] {pid}: relevant {rel or 'none'}")
        paths.screen.write_text(json.dumps(done, indent=1))
    print(f"  screened {len(done)} pages -> {paths.screen}")
