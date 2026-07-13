# trace-analysis — checker confusion matrix vs ground truth (side project)

Standalone analysis tool, outside the product. Derives a per-record confusion
matrix for the Shiboleth checker against the FROZEN ground truth
(`../ground-truth/ground_truth.json`, 460 records, approved 2026-07-09).
Nothing in `code/` is modified; the product is imported as a library.

## Data source decision (evaluated 2026-07-10)

| Candidate | Finding | Usable? |
|---|---|---|
| LangSmith root runs (e.g. `e3-iter-11-rulings`) | outputs are aggregates only (`strict_accuracy`, `per_class`, ...); `misses` deliberately excluded | no |
| LangSmith child traces | raw `ChatAnthropic` calls, no page/rule metadata to join on | no |
| Local trace dump `code/apps/api/src/shiboleth/evals/.cache/e3_cache.json` | every checker LLM call from the certification runs, keyed `sha256(model+prompt)` | **yes** |

The script replays the dump through the PRODUCTION corpus pipeline
(`corpus_outcomes` from the E3 harness) — the same mechanism as the E5
regression check — so (page, rule, scope) alignment is exact and no live LLM
call is ever made (`CacheOnlyInvoke` raises on a cache miss instead of
calling a model).

## Honesty gate

Before printing any matrix, the script recomputes the certification metric
(strict accuracy, needs_review = half credit) from its own derived pairs and
compares it to the official results file
(`code/.../evals/results/e3-iter-11-rulings.json`). Mismatch = exit 1, no
matrix. Reconciled on 2026-07-10: 0.9799 (n=199) both sides.

## Run

```bash
cd marketing-compliance-checker
code/apps/api/.venv/bin/python trace-analysis/confusion_matrix.py
# options: --model anthropic:claude-haiku-4-5   (trace dump's model key)
#          --name  e3-iter-11-rulings           (official results to reconcile)
```

Output: matrices to stdout + `results/confusion_<name>.json` (matrices,
per-label precision/recall/F1, binary violation view, full disagreement list).

## Reading the output

Four cohorts, each a 4x4 matrix (rows = ground truth, cols = predicted) over
`pass | flag | not_applicable | needs_review`:

- **ALL 460** — the whole dataset, context only (dominated by the 195 GT
  needs_review records that strict scoring excludes by design).
- **strict cohort (n=199)** — analyst + footer_inherited records with a
  definitive GT verdict. This is the certified set; its accuracy reconciles
  with the LangSmith experiment.
- **synthetics (n=17)** — must be diagonal (17/17).
- **ambiguity set (n=195)** — GT says needs_review; the row shows how the
  checker resolves ambiguity (definitive answers here are expected, not
  errors; `flag` = conservative direction).

The **binary violation view** collapses to the analyst's question — "does it
catch violations?": flag = positive class; reports sensitivity (catch rate),
specificity, precision.

## Results snapshot (e3-iter-11 condition, 2026-07-10)

Strict cohort: 199 records, 4 real misses — 1 flag→pass (P02 pair,
multi-finding runner is day-2), 1 pass→flag (P09 quote-block placement,
conservative direction), 2 not_applicable→flag (P03/P20 trigger-scope,
Aarvin ruling C: kept conservative). Binary view: catch rate 0.98,
specificity 0.98, precision 0.94. Synthetics 17/17 diagonal.
