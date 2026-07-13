"""
eval_v2.py — measure the PRODUCTION checker against frozen ground truth v2.

meta:
  purpose: the held-out measurement the MVP1 certification could not give:
           how the shipped checker performs on pages it never iterated on.
           Runs the exact production code path (windows.py -> check.py) over
           ground-truth-v2/data (78 pages + 27 synthetics), scores against
           ground_truth_v2.json, and reports TRAIN and TEST splits
           separately. Iterate on train ONLY; test is the quarantine.
  contract: nothing in code/ is modified; the product is imported as a
            library (trace-analysis pattern). LLM calls cached in
            data/.cache-eval/ keyed sha256(model+prompt) so re-runs are $0.
            Scoring conventions ported from e3.py: strict set = panel
            records (judge_panel / judge_panel_arbiter); system needs_review
            vs definitive GT = half credit; semantic_screen records reported
            as screen-agreement, never in strict accuracy; sibling rule for
            multi-record (page, rule) pairs.
  deps: the product api venv:
        code/apps/api/.venv/bin/python ground-truth-v2/eval_v2.py \
            --name e5v2-baseline [--subset V02,V03] [--split test|train|all]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
API_SRC = HERE.parent / "code" / "apps" / "api" / "src"
sys.path.insert(0, str(API_SRC))

from shiboleth.config import load_settings  # noqa: E402
from shiboleth.main import propagate_env  # noqa: E402
from shiboleth.db.seed import CHECKS  # noqa: E402
from shiboleth.db.seed_rules import D01_APPROVED_TEXT, RULES  # noqa: E402
from shiboleth.pipeline.nodes.check import (  # noqa: E402
    CheckerVerdict, production_invoke, run_check,
)
from shiboleth.services.ingestion.corpus import load_corpus  # noqa: E402
from shiboleth.services.ingestion.windows import (  # noqa: E402
    extract_windows, library_anchor_keywords,
)

DATA = HERE / "data"
GT_PATH = DATA / "ground_truth_v2.json"
CACHE_DIR = DATA / ".cache-eval"
RESULTS_DIR = HERE / "results"
RULE_IDS = ["R-01", "R-02", "R-03", "R-04"]


def rule_bundle(rule_id: str):
    row = next(r for r in RULES if r[0] == rule_id)
    rule = {"id": row[0], "verbatim_text": row[1], "severity": row[2]}
    checks = [c for c in CHECKS if c["rule_id"] == rule_id]
    library = None
    if any(c.get("library_entry_id") == "D-01" for c in checks):
        library = {"id": "D-01", "approved_text": D01_APPROVED_TEXT}
    return rule, checks, library


class CachedInvoke:
    """Disk-cached invoke(prompt) -> CheckerVerdict with loud retries."""

    def __init__(self, model_string: str):
        self.model = model_string
        self._invoke = None
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self.live = 0
        self.cached = 0

    def __call__(self, prompt: str) -> CheckerVerdict:
        key = hashlib.sha256(f"{self.model}\n{prompt}".encode()).hexdigest()
        f = CACHE_DIR / f"{key}.json"
        if f.exists():
            self.cached += 1
            return CheckerVerdict.model_validate_json(f.read_text())
        if self._invoke is None:
            self._invoke = production_invoke(self.model)
        last = None
        for attempt in range(1, 4):
            try:
                verdict = self._invoke(prompt)
                f.write_text(verdict.model_dump_json())
                self.live += 1
                return verdict
            except Exception as exc:
                last = exc
                wait = 15 * attempt
                print(f"    ! {self.model} attempt {attempt}/3: "
                      f"{type(exc).__name__}: {str(exc)[:150]} — wait {wait}s")
                time.sleep(wait)
        raise RuntimeError(f"{self.model} failed 3x") from last


def load_synthetic_fixtures() -> dict[str, dict]:
    """v2 fixtures have no content hash; parse front matter manually."""
    out = {}
    for f in sorted((DATA / "synthetics").glob("S*.md")):
        text = f.read_text()
        _, front, body = text.split("---\n", 2)
        meta = dict(line.split(": ", 1) for line in front.strip().splitlines())
        out[meta["id"]] = {"rule_id": meta["rule"], "body": body.strip()}
    return out


def corpus_outcomes_v2(invoke, subset: set[str] | None = None) -> dict:
    """(page_id, rule_id) -> CheckOutcome | None (None = no window signal).
    No footer judged-once pass: v2 records judge full pages (footers were
    judged inline by the panel), so the system sees full bodies too."""
    outcomes: dict[tuple[str, str], object] = {}
    docs = {d.page_id: d for d in load_corpus(DATA / "snapshots")}
    fixtures = load_synthetic_fixtures()

    todo_pages = [p for p in sorted(docs) if not subset or p in subset]
    for n, pid in enumerate(todo_pages, 1):
        body = docs[pid].body
        for rid in RULE_IDS:
            rule, checks, library = rule_bundle(rid)
            anchors = (library_anchor_keywords(library["approved_text"])
                       if library else None)
            windows = extract_windows(body, rid, extra_keywords=anchors,
                                      fallback_chars=24_000)
            if not windows:
                outcomes[(pid, rid)] = None
                continue
            outcomes[(pid, rid)] = run_check(
                "\n\n".join(windows), rule, checks, library, invoke)
        print(f"  [{n}/{len(todo_pages)}] {pid}: "
              f"{[outcomes[(pid, r)].verdict_status if outcomes[(pid, r)] else 'na(window)' for r in RULE_IDS]}")

    for sid, fx in sorted(fixtures.items()):
        if subset and sid not in subset:
            continue
        rid = fx["rule_id"]
        rule, checks, library = rule_bundle(rid)
        anchors = (library_anchor_keywords(library["approved_text"])
                   if library else None)
        windows = extract_windows(fx["body"], rid, extra_keywords=anchors)
        outcomes[(sid, rid)] = run_check(
            "\n\n".join(windows) if windows else fx["body"],
            rule, checks, library, invoke)
        print(f"  [syn] {sid} {rid}: {outcomes[(sid, rid)].verdict_status}")
    return outcomes


def _overlap(a: str, b: str) -> float:
    ta = set(re.findall(r"[a-z0-9%$]+", a.lower()))
    tb = set(re.findall(r"[a-z0-9%$]+", b.lower()))
    return len(ta & tb) / len(ta) if ta else 0.0


def score_v2(outcomes: dict, split_filter: str = "all") -> dict:
    gt = json.loads(GT_PATH.read_text())
    records = [r for r in gt["records"]
               if split_filter == "all" or r["split"] == split_filter]
    by_pair = defaultdict(list)
    for r in gt["records"]:
        by_pair[(r["page_id"], r["rule_id"])].append(r)

    def verdict_of(pair):
        if pair not in outcomes:
            return None  # not run (subset)
        o = outcomes[pair]
        return "not_applicable" if o is None else o.verdict_status

    strict = {"hits": 0.0, "n": 0}
    per_rule = defaultdict(lambda: [0.0, 0])
    per_split = defaultdict(lambda: [0.0, 0])
    screen_agree = [0, 0]
    synth = [0, 0]
    misses = []
    ev_ok = ev_seen = flags = 0

    for r in records:
        pair = (r["page_id"], r["rule_id"])
        got = verdict_of(pair)
        if got is None:
            continue
        out = outcomes.get(pair)
        if out is not None and out.verdict_status == "flag":
            pass  # flags counted once per pair below
        src = r["judgment_source"]
        expected = r["verdict_status"]

        if src == "semantic_screen":
            screen_agree[1] += 1
            screen_agree[0] += int(got == "not_applicable")
            continue
        if src == "synthetic_intended":
            synth[1] += 1
            if got == expected:
                synth[0] += 1
            else:
                misses.append({"id": r["id"], "split": r["split"],
                               "expected": expected, "got": got,
                               "cohort": "synthetic"})
            continue

        # panel records = strict set
        credit = 0.0
        if got == expected:
            credit = 1.0
        elif got == "needs_review":
            credit = 0.5
        elif (expected in ("pass", "not_applicable") and got == "flag"
              and any(s["verdict_status"] == "flag" and s["id"] != r["id"]
                      and out is not None
                      and _overlap(s["evidence_quote"], out.evidence_quote) > 0.4
                      for s in by_pair[pair])):
            # v1 sibling convention: multi-record (page, rule) pairs where a
            # single outcome cannot express both records; the system's flag
            # provably targeted the SIBLING flag record (evidence overlap),
            # so this record is not a real error
            credit = 1.0
        strict["hits"] += credit
        strict["n"] += 1
        per_rule[r["rule_id"]][0] += credit
        per_rule[r["rule_id"]][1] += 1
        per_split[r["split"]][0] += credit
        per_split[r["split"]][1] += 1
        if credit < 1.0:
            misses.append({"id": r["id"], "split": r["split"],
                           "rule": r["rule_id"], "expected": expected,
                           "got": got, "credit": credit,
                           "source": src, "cohort": "panel"})

    seen_pairs = set()
    for pair, o in outcomes.items():
        if o is not None and pair not in seen_pairs:
            seen_pairs.add(pair)
            if o.verdict_status == "flag":
                flags += 1
                ev_seen += 1
                ev_ok += int(o.evidence_valid)

    return {
        "strict_accuracy": round(strict["hits"] / strict["n"], 4) if strict["n"] else None,
        "strict_n": strict["n"],
        "per_split": {k: {"accuracy": round(v[0] / v[1], 4), "n": v[1]}
                      for k, v in sorted(per_split.items())},
        "per_rule": {k: round(v[0] / v[1], 4)
                     for k, v in sorted(per_rule.items())},
        "screen_agreement": (f"{screen_agree[0]}/{screen_agree[1]} "
                             f"({screen_agree[0] / screen_agree[1]:.0%})"
                             if screen_agree[1] else "n/a"),
        "synthetics": f"{synth[0]}/{synth[1]}",
        "evidence_validity": round(ev_ok / ev_seen, 4) if ev_seen else None,
        "flags_emitted": flags,
        "misses": misses,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--subset", default=None,
                    help="comma-separated page ids (pilot)")
    ap.add_argument("--split", default="all", choices=["all", "train", "test"])
    args = ap.parse_args()

    settings = load_settings()
    propagate_env(settings)
    model = settings.model_for("check")
    invoke = CachedInvoke(model)
    subset = set(args.subset.split(",")) if args.subset else None

    from langsmith import trace
    t0 = time.time()
    with trace(name=args.name, project_name=settings.langsmith_project,
               inputs={"gt": "v2", "split": args.split, "model": model,
                       "subset": args.subset or "FULL"}) as run:
        outcomes = corpus_outcomes_v2(invoke, subset)
        result = score_v2(outcomes, args.split)
        run.end(outputs={k: v for k, v in result.items() if k != "misses"})

    result.update({"model": model, "split": args.split,
                   "run_seconds": round(time.time() - t0, 1),
                   "llm_calls_live": invoke.live,
                   "llm_calls_cached": invoke.cached,
                   "full_run": subset is None})
    RESULTS_DIR.mkdir(exist_ok=True)
    out = RESULTS_DIR / f"{args.name}.json"
    out.write_text(json.dumps(result, indent=1))
    for k, v in result.items():
        if k != "misses":
            print(f"{k}: {v}")
    print(f"misses: {len(result['misses'])} -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
