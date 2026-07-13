"""
meta:
  purpose: Side project (outside the product): derive a confusion matrix for
           the Shiboleth checker against the FROZEN ground truth (460
           records). Data source: the local E3 trace dump
           (evals/.cache/e3_cache.json — every checker LLM call from the
           certification runs, keyed sha256(model+prompt)), replayed through
           the PRODUCTION corpus pipeline for exact (page, rule, scope)
           alignment. LangSmith traces were evaluated and rejected as the
           source: root runs carry aggregates only, child LLM runs carry no
           page/rule join key.
  contract: <api-venv-python> confusion_matrix.py [--model STR] [--name STR]
            [--allow-live]. Prints matrices, writes results/<name>.json.
            Exits 1 if the derived pairs do NOT reconcile with the official
            certification accuracy (evals/results/<name>-source.json).
  deps: the product's api venv (imports shiboleth as a library; nothing in
        the product is modified). Default model matches e3-iter-11
        certification: anthropic:claude-haiku-4-5.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
API_SRC = HERE.parent / "code" / "apps" / "api" / "src"
sys.path.insert(0, str(API_SRC))

from shiboleth.evals.harnesses.e3 import (  # noqa: E402
    CACHE_PATH,
    GROUND_TRUTH_DIR,
    RESULTS_DIR,
    _evidence_overlap,
    corpus_outcomes,
    system_verdict,
)
from shiboleth.pipeline.nodes.check import CheckerVerdict  # noqa: E402
from shiboleth.services.ingestion.corpus import load_corpus  # noqa: E402
from shiboleth.services.ingestion.windows import detect_shared_block  # noqa: E402

LABELS = ["pass", "flag", "not_applicable", "needs_review"]


class ReplayMiss(RuntimeError):
    """A prompt was not in the trace dump: the replay would need a live LLM
    call, meaning the condition being scored is NOT the certified one."""


class CacheOnlyInvoke:
    """Replay invoke: serves checker verdicts from the E3 trace dump only.
    Same cache key convention as PacedCachedInvoke; never calls a model."""

    def __init__(self, model_string: str):
        self.model_string = model_string
        if not CACHE_PATH.exists():
            raise SystemExit(f"trace dump not found: {CACHE_PATH}")
        self.cache: dict[str, dict] = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        self.hits = 0
        self.misses: list[str] = []

    def __call__(self, prompt: str) -> CheckerVerdict:
        key = hashlib.sha256(f"{self.model_string}\n{prompt}".encode()).hexdigest()
        if key not in self.cache:
            self.misses.append(prompt[:120])
            raise ReplayMiss(
                f"prompt not in trace dump (model={self.model_string}); "
                "wrong --model, or the corpus/windowing changed since certification"
            )
        self.hits += 1
        return CheckerVerdict.model_validate(self.cache[key])


def derive_pairs(outcomes, records, footer_text: str) -> list[dict]:
    """Mirror of e3.score()'s alignment rules, but returning per-record
    (expected, predicted) pairs instead of aggregate credit. Every one of the
    460 records yields exactly one pair. Alignment rules mirrored:
    - _footer canonical records compare against the once-judged footer verdict
    - footer_inherited records inherit that verdict per page
    - synthetics match their standalone outcome
    - page records fall back to the footer verdict when their GT evidence
      lives in the footer TEXT (Aarvin ruling B, 2026-07-10)
    - multi-record (page,rule) pass records are not charged for a system flag
      whose evidence targets the sibling flag record
    """
    pairs = []
    for rec in records:
        page, rule_id, source = rec["page_id"], rec["rule_id"], rec["judgment_source"]
        if page == "_footer":
            candidates = [
                v for (p, r, s), v in outcomes.items() if r == rule_id and s == "footer"
            ]
            outcome = candidates[0] if candidates else None
            got = system_verdict(outcome)
        elif source == "footer_inherited":
            outcome = outcomes.get((page, rule_id, "footer"))
            got = system_verdict(outcome)
        elif source == "synthetic_author":
            outcome = outcomes.get((page, rule_id, "synthetic"))
            got = system_verdict(outcome)
        else:
            outcome = outcomes.get((page, rule_id, "page"))
            got = system_verdict(outcome)
            if got == "not_applicable" and rec.get("evidence_quote") and footer_text:
                footer_outcome = outcomes.get((page, rule_id, "footer"))
                if footer_outcome is not None and _evidence_overlap(
                    rec["evidence_quote"], footer_text
                ):
                    outcome = footer_outcome
                    got = system_verdict(footer_outcome)

        expected = rec["verdict_status"]
        # checker confidence for THIS pair's verdict; None when the verdict is
        # deterministic (no windows -> N/A without an LLM call)
        confidence = getattr(outcome, "confidence", None)

        if (
            source == "analyst"
            and expected == "pass"
            and outcome is not None
            and getattr(outcome, "verdict_status", None) == "flag"
        ):
            siblings = [
                r for r in records
                if r["page_id"] == page and r["rule_id"] == rule_id
                and r["id"] != rec["id"] and r["verdict_status"] == "flag"
            ]
            if siblings and not _evidence_overlap(
                outcome.evidence_quote, rec.get("evidence_quote", "")
            ):
                got = "pass"
                # the outcome's confidence belongs to the sibling's flag, not
                # to this derived pass judgment
                confidence = None

        pairs.append({
            "id": rec["id"], "page_id": page, "rule_id": rule_id,
            "source": source, "expected": expected, "got": got,
            "confidence": confidence,
        })
    return pairs


def confusion(pairs: list[dict]) -> dict[str, dict[str, int]]:
    """rows = ground truth (expected), cols = checker prediction (got)."""
    m = {e: {g: 0 for g in LABELS} for e in LABELS}
    for p in pairs:
        m[p["expected"]][p["got"]] += 1
    return m


def confidence_matrix(pairs: list[dict]) -> dict[str, dict[str, dict]]:
    """Per-cell checker-confidence stats: n (all pairs in the cell), n_conf
    (pairs whose verdict carries an LLM confidence), mean and population std
    dev over those. Deterministic N/A verdicts have no confidence."""
    cells: dict[str, dict[str, list[float]]] = {
        e: {g: [] for g in LABELS} for e in LABELS
    }
    counts = {e: {g: 0 for g in LABELS} for e in LABELS}
    for p in pairs:
        counts[p["expected"]][p["got"]] += 1
        if p["confidence"] is not None:
            cells[p["expected"]][p["got"]].append(p["confidence"])
    out: dict[str, dict[str, dict]] = {}
    for e in LABELS:
        out[e] = {}
        for g in LABELS:
            vals = cells[e][g]
            out[e][g] = {
                "n": counts[e][g],
                "n_conf": len(vals),
                "mean": round(statistics.mean(vals), 4) if vals else None,
                "std": round(statistics.pstdev(vals), 4) if vals else None,
            }
    return out


def render_confidence_matrix(cm: dict[str, dict[str, dict]], title: str) -> str:
    """Cells as mean±std (population); '·' = empty cell, 'det' = only
    deterministic verdicts (no LLM confidence to average)."""
    width = 22
    lines = [f"\n{title}  (checker confidence: mean±std, rows = ground truth)"]
    lines.append(" " * width + "".join(f"{g:>{width}}" for g in LABELS))
    for e in LABELS:
        row = [f"{e:>{width}}"]
        for g in LABELS:
            c = cm[e][g]
            if c["n"] == 0:
                cell = "·"
            elif c["n_conf"] == 0:
                cell = f"det n={c['n']}"
            else:
                cell = f"{c['mean']:.2f}±{c['std']:.2f} n={c['n_conf']}"
                if c["n"] != c["n_conf"]:
                    cell += f"/{c['n']}"
            row.append(f"{cell:>{width}}")
        lines.append("".join(row))
    return "\n".join(lines)


def per_label_metrics(m: dict[str, dict[str, int]]) -> dict[str, dict]:
    out = {}
    total = sum(sum(row.values()) for row in m.values())
    for label in LABELS:
        tp = m[label][label]
        fn = sum(m[label][g] for g in LABELS) - tp
        fp = sum(m[e][label] for e in LABELS) - tp
        prec = tp / (tp + fp) if tp + fp else None
        rec = tp / (tp + fn) if tp + fn else None
        f1 = (2 * prec * rec / (prec + rec)) if prec and rec else None
        out[label] = {
            "support": tp + fn,
            "precision": round(prec, 4) if prec is not None else None,
            "recall": round(rec, 4) if rec is not None else None,
            "f1": round(f1, 4) if f1 is not None else None,
        }
    out["_accuracy"] = round(
        sum(m[label][label] for label in LABELS) / total, 4
    ) if total else None
    return out


def binary_violation_view(pairs: list[dict]) -> dict:
    """The analyst's question: did the checker catch violations? flag = the
    positive class; everything else (pass/na/needs_review) = negative."""
    tp = sum(1 for p in pairs if p["expected"] == "flag" and p["got"] == "flag")
    fn = sum(1 for p in pairs if p["expected"] == "flag" and p["got"] != "flag")
    fp = sum(1 for p in pairs if p["expected"] != "flag" and p["got"] == "flag")
    tn = sum(1 for p in pairs if p["expected"] != "flag" and p["got"] != "flag")
    return {
        "tp": tp, "fn": fn, "fp": fp, "tn": tn,
        "sensitivity_catch_rate": round(tp / (tp + fn), 4) if tp + fn else None,
        "specificity": round(tn / (tn + fp), 4) if tn + fp else None,
        "precision": round(tp / (tp + fp), 4) if tp + fp else None,
    }


def strict_accuracy_from_pairs(pairs: list[dict]) -> tuple[float, int]:
    """Recompute the certification metric from the derived pairs (same rule:
    strict cohort = analyst + footer_inherited + _footer records with GT
    verdict != needs_review; system needs_review counts half)."""
    hits, total = 0.0, 0
    for p in pairs:
        strict_cohort = p["source"] in ("analyst", "footer_inherited") or (
            p["page_id"] == "_footer"
        )
        if not strict_cohort or p["expected"] == "needs_review":
            continue
        total += 1
        hits += 1.0 if p["got"] == p["expected"] else (
            0.5 if p["got"] == "needs_review" else 0.0
        )
    return (hits / total if total else 0.0), total


def render_matrix(m: dict[str, dict[str, int]], title: str) -> str:
    width = max(len(label) for label in LABELS) + 2
    lines = [f"\n{title}  (rows = ground truth, cols = predicted)"]
    lines.append(" " * width + "".join(f"{g:>{width}}" for g in LABELS))
    for e in LABELS:
        lines.append(f"{e:>{width}}" + "".join(f"{m[e][g]:>{width}}" for g in LABELS))
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="anthropic:claude-haiku-4-5",
                        help="model string the trace dump was recorded with")
    parser.add_argument("--name", default="e3-iter-11-rulings",
                        help="official results file to reconcile against")
    args = parser.parse_args()

    gt = json.loads((GROUND_TRUTH_DIR / "ground_truth.json").read_text(encoding="utf-8"))
    records = gt["records"]
    print(f"ground truth: {len(records)} records "
          f"({Counter(r['verdict_status'] for r in records)})")

    invoke = CacheOnlyInvoke(args.model)
    print(f"replaying production pipeline from trace dump ({len(invoke.cache)} "
          f"cached verdicts, model={args.model}) ...")
    outcomes = corpus_outcomes(invoke)
    snapshots = load_corpus(GROUND_TRUTH_DIR / "snapshots")
    footer_text = "\n\n".join(detect_shared_block([d.body for d in snapshots],
                                                  min_pages=20))
    print(f"replay complete: {invoke.hits} verdicts served, 0 live LLM calls")

    pairs = derive_pairs(outcomes, records, footer_text)
    assert len(pairs) == len(records), "every GT record must yield one pair"

    # ---- reconciliation gate: the parse must reproduce the certification ----
    strict_acc, strict_n = strict_accuracy_from_pairs(pairs)
    official_path = RESULTS_DIR / f"{args.name}.json"
    official = json.loads(official_path.read_text(encoding="utf-8"))
    print(f"\nreconciliation vs {args.name}: derived strict accuracy "
          f"{strict_acc:.4f} (n={strict_n}) vs official "
          f"{official['strict_accuracy']} (n={official['strict_n']})")
    if round(strict_acc, 4) != official["strict_accuracy"] or strict_n != official["strict_n"]:
        print("MISMATCH: derived pairs do not reproduce the certified metric; "
              "matrix would not represent the certified condition. Aborting.")
        return 1
    print("RECONCILED: matrix is derived from the certified condition.")

    # ---- matrices ----
    cohorts = {
        "ALL 460 records": pairs,
        "strict cohort (analyst + footer_inherited, GT != needs_review)": [
            p for p in pairs
            if (p["source"] in ("analyst", "footer_inherited") or p["page_id"] == "_footer")
            and p["expected"] != "needs_review"
        ],
        "synthetics (17 authored fixtures)": [
            p for p in pairs if p["source"] == "synthetic_author"
        ],
        "ambiguity set (GT needs_review)": [
            p for p in pairs if p["expected"] == "needs_review"
        ],
    }
    report: dict = {"model": args.model, "reconciled_against": args.name,
                    "strict_accuracy": round(strict_acc, 4), "cohorts": {}}
    for title, cohort_pairs in cohorts.items():
        m = confusion(cohort_pairs)
        cm = confidence_matrix(cohort_pairs)
        print(render_matrix(m, f"{title}  [n={len(cohort_pairs)}]"))
        print(render_confidence_matrix(cm, f"{title}  [n={len(cohort_pairs)}]"))
        report["cohorts"][title] = {
            "n": len(cohort_pairs), "matrix": m,
            "confidence_matrix": cm,
            "per_label": per_label_metrics(m),
        }

    bin_view = binary_violation_view(cohorts["strict cohort (analyst + footer_inherited, GT != needs_review)"])
    print("\nbinary violation view (strict cohort, flag = positive class):")
    print(json.dumps(bin_view, indent=1))
    report["binary_violation_view_strict"] = bin_view

    disagreements = [p for p in pairs if p["expected"] != p["got"]]
    real_misses = [p for p in disagreements if p["expected"] != "needs_review"]
    report["disagreements"] = disagreements
    report["real_misses"] = real_misses
    print(f"\nreal misses (GT has a definitive verdict): {len(real_misses)}")
    for p in real_misses:
        print(f"  {p['id']}: expected {p['expected']}, got {p['got']} "
              f"({p['page_id']} {p['rule_id']}, {p['source']})")
    print(f"needs_review records resolved definitively by the checker: "
          f"{len(disagreements) - len(real_misses)} of 195 (by design; "
          f"excluded from strict scoring, full list in the report)")

    out_dir = HERE / "results"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"confusion_{args.name}.json"
    out_path.write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(f"report written: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
