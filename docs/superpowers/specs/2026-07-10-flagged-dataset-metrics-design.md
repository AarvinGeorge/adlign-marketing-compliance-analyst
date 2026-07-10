# Flagged-dataset metrics + placeholder elimination — design

Date: 2026-07-10. Approved by Aarvin (scope, placement, breakdowns,
approach A, backend contract incl. "Caught" rename, frontend + testing).

## Goal

Display real metrics of the flagged dataset on the product page and remove
every remaining placeholder/synthetic display value, so that every visible
number, timestamp, and provenance line traces to a Postgres row. No value is
ever fabricated; where no data exists, the element is removed or shows an
honest empty state.

## Context (audit result, 2026-07-10)

Already real: the five dashboard hero KPIs (GET /metrics, SQL-traceable,
tested), product-detail metric row, clusters, verdicts, scores.

Placeholder/synthetic today, all in `apps/web/src/lib/data.ts`:

1. Flag detail `foundAt: "latest run"` (hardcoded string).
2. Why-flagged chain steps 1-4 (synthesized wording, not persisted events).
3. `missingRequirement: null` and `postDate: null` (dead props, no data
   captured anywhere).
4. Model label fallback for pre-attribution runs (honest; stays).
5. Dashboard card title "Caught this week" (data is per-run).
6. Scorecard rule text served from `fixtures.ts` (correct byte-for-byte but
   not API-served; no rules endpoint).
7. `SEVERITY_BY_RULE` hardcoded twice (web `data.ts`, API `metrics.py`).

Missing entirely: breakdowns of the flagged dataset (by rule, property,
verdict tag, disposition outcome). The data exists in `flags`.

## Decisions (locked)

- Scope: both new flag analytics AND placeholder elimination.
- Placement: product detail page (U6) only; dashboard stays the 5-KPI hero.
- Breakdowns: by rule, by property, by verdict tag, disposition outcomes.
- Architecture: approach A — server-computed `analytics` block on
  GET /products/{id} + new GET /rules as the single rule-text/severity
  source. No client-side math. (Rejected: separate analytics endpoint —
  needless round trip; frontend computation — breaks zero-client-math and
  SQL traceability.)
- "Caught this week" card renamed "Caught" (sublabel already carries the
  honest window, "this run"). Deviation from spec §10.5's name: approved.
- `postDate` and `missingRequirement` removed, not faked.

## Backend

### 1. `analytics` block on GET /products/{id}

Route does the SQL; a new pure function formats (pattern: `scoring/kpis.py`).

```json
"analytics": {
  "by_rule":     [{"rule_id": "R-01", "severity": "High",
                   "open": 44, "confirmed": 3, "dismissed": 1, "total": 48}],
  "by_property": [{"property_id": "tt-website", "kind": "website",
                   "open": 120, "total": 130}],
  "by_tag":      [{"tag": "unapproved_violation", "count": 90}],
  "disposition": {"pending": 130, "confirmed": 5, "dismissed": 2,
                  "fp_rate": 0.29}
}
```

- Scope: flags of the product's displayed (latest) run — same population the
  page already shows.
- "open" = state not in (dismissed, closed); "confirmed" = confirmed or any
  post-confirm lifecycle state (assigned, fix_pending_verification, closed);
  "dismissed" = dismissed; "pending" = open.
- `fp_rate` = dismissed / (dismissed + confirmed), rounded to 2 decimals;
  `null` until at least one disposition exists.
- Severity joined from the `rules` table, not a hardcoded map.
- Pure function `flag_analytics(flag_rows, rules, properties) -> dict` in
  `apps/api/src/shiboleth/services/scoring/analytics.py`; no DB, no I/O.
- by_rule ordered by rule position; by_property by property id; by_tag by
  severity rank of tag (unapproved_violation first); zero-count entries
  included for seeded rules and tracked properties (honest zeros).

### 2. GET /rules

Serves seeded rules from Postgres: `[{id, verbatim_text, severity,
position}]`, ordered by position. Becomes the single severity + rule-text
source. Both hardcoded `SEVERITY_BY_RULE` maps are deleted:
`api/routes/metrics.py` reads the rules table (or seed RULES, which the DB
verbatim test already pins); `web/lib/data.ts` reads GET /rules.

### 3. Flag provenance

- Product-payload flags gain `found_at`: ISO timestamp of the flag's run
  `started_at`.
- New GET /flags/{flag_id}: the flag plus a `trace` assembled from persisted
  rows only:
  - `ingested`: the material's `material_fetched` event (timestamp, ref,
    cache_hit) — matched by run + material ref; null if no event row exists.
  - `checked`: the run's `check_result` event timestamp for this
    material/check; null if absent.
  - `verdict`: fields already stored on the flag (check_id, axes, tag,
    confidence, reason, model from run.model_config).
  Steps with no persisted evidence are omitted by the API (no synthesized
  wording).

### 4. Dashboard label

`HERO_ORDER` label "Caught this week" -> "Caught" (web copy change only;
API sublabel unchanged).

## Frontend (render-only, zero math)

- `lib/api.ts`: types + fetchers for `analytics`, `GET /rules`,
  `GET /flags/{id}`.
- `lib/data.ts`: `useRules()` (static cache), `severityOf()` from rules
  data, analytics passthrough view-model, `found_at` mapped into FlagMeta.
- `lib/fixtures.ts`: rules array deleted; file becomes view-model types
  only. Scorecard surface (U7) renders rule text from `useRules()` through
  the existing `render-rule-text.tsx` path (markdown link rendering
  unchanged).
- Product page (U6): new "Flagged dataset" section under the metric row.
  Four compact panels from existing primitives only (severity badge,
  property chip, verdict-tag chips, proportional count bars via styled divs;
  no new chart components): by rule, by property, by verdict tag,
  disposition outcomes + FP rate. Empty state when the run has zero flags:
  "no flags in this run".
- Flag detail (U7): why-flagged chain renders the API trace (real
  timestamps, ref, cache_hit, verdict); `foundAt` shows `found_at`
  formatted; `postDate` + `missingRequirement` props and their render paths
  removed.
- MetricCard and hero wiring untouched except the "Caught" label.

## Testing (tests before implementation, guardrail 6)

- Unit: `flag_analytics` pure-function tests (counts, ordering, honest
  zeros, fp_rate null/rounding, confirmed-family states).
- Integration (docker Postgres, `test_api_metrics.py` pattern): every
  analytics number equals an independent SQL aggregate computed by the test
  over a known-state DB; GET /rules byte-for-byte vs doc 05 §1 seed (R-03
  double-space canary); GET /flags/{id} trace matches persisted event rows;
  fresh-DB empty states.
- Web: build + lint green; Playwright journey extended to assert the
  analytics section renders counts matching the run and the chain shows a
  real timestamp.
- Regression: full pytest suite; certification replay (no checker-path
  changes by construction — read paths and UI only; no schema migrations,
  no LLM in any new code).

## Guardrails carried

No TurboTax-specific logic (analytics generic over seeded rules/properties);
rule text verbatim from the DB seed; shadcn/ui primitives + DESIGN.md tokens
only; sentence case, no em-dashes in product copy; $0 (no LLM calls);
confirm-first before any push.
