# 09 — MVP1 build report and handoff (2026-07-10)

> Audience: solution architect, system designer, project manager. Status at
> writing: M0-M6 gates passed, M7 in progress (manual acceptance testing by
> Aarvin; tag `mvp-v1-base-condition` pending his green light). Repo:
> github.com/AarvinGeorge/shiboleth-marketing-compliance-analyst (private),
> remote HEAD 320d626 at last push; local main ahead by the M6 gate, UI
> audit, and model-attribution commits (push batched with the tag).
> Companion docs: 08 (scope contract), 01 (spec), 07 (architecture),
> DESIGN.md (UI contract), ground-truth/README.md (acceptance dataset).

## 1. Executive summary

Shiboleth MVP1 is a marketing-compliance monitoring product: enter a
product's marketing properties (website, Instagram, Facebook), the system
ingests the material, checks every artifact against a seeded 4-rule
scorecard plus a pre-approved disclosure library, and presents flags with
verbatim evidence, two-axis verdicts, clustering, human disposition, and
severity-weighted scoring, in four UI surfaces.

The acceptance posture is the differentiator: before the product was built,
a frozen 54-page TurboTax corpus and a 460-record expert answer key
(approved by Aarvin) were established. The checker was then iterated until
a full certification run agreed with the strict subset of that answer key at
**97.99%** (threshold 90%), with **17/17** synthetic fixtures correct and
**100%** programmatically-verified evidence quotes. A live end-to-end run
(real crawl of turbotax.intuit.com, paste fallback for Meta properties)
completed through the identical pipeline. Total LLM spend for all
certification and live runs: ~$5.

Nothing in the codebase is TurboTax-specific (grep-verifiable guardrail);
the product under scan, its properties, the scorecard, and the library are
runtime data.

## 2. Architecture as built

```
Next.js 15 (App Router, TanStack Query, zustand, shadcn/ui + DESIGN.md tokens)
   │ REST + SSE (localhost:3000 -> :8000, CORS)
   ▼
FastAPI (apps/api, Python 3.12, uv)
   │  POST /checks {mode: corpus|live}   POST /flags/{id}/disposition
   │  GET /products[/{id}]               GET /runs/{id}/events[.json]
   │  POST /runs/{id}/paste-content | skip-property   GET /extract-properties
   ▼
Pipeline (deterministic flow, LLM only inside the checker + labeler)
   corpus mode: frozen snapshots (hash-verified) ────┐
   live mode:   crawl4ai BFS (depth 2, cap 20) ──────┤
                Meta properties -> needs_input ──────┤   BARRIER (07 §2 pinned):
                paste/skip endpoints resume ─────────┘   any needs_input ends the
   ▼                                                     graph run; DB is the
   shared-block (footer) dedup -> judged ONCE, inherited per page as flags
   rule-relevant windowing (keyword + library-anchor retrieval, prod code)
   N4 checker (LLM, structured output) + N5 axis-B reconcile (deterministic)
   N6 clustering (normalized-evidence grouping + LLM labeler)
   N7 scoring (pure functions; severity weights H3/M2/L1; N/A + needs_review
   excluded; draft vs verified; outcome rows persisted for exact recompute)
   ▼
Postgres 16 + pgvector image (SQL + JSONB; 13 tables per 01_spec §5)
   materials are content-addressed (sha256 of stripped text) and REUSED
   across runs (cache/dedup refinement); events persisted before SSE
LangSmith: every LLM call traced; every E3 iteration a named experiment
```

**The two-axis verdict, mechanically:** axis A (compliant with the rule) is
the LLM's judgment with mandatory verbatim evidence, validated by code
(quote must substring-match the stored material after whitespace/markdown
normalization, else the verdict degrades to needs_review). Axis B (matches
approval) is NOT the LLM: it is a deterministic containment test of the
library entry's approved text against the stored material. Intersection
tags (all_good / drifted_but_compliant / approved_but_non_compliant /
unapproved_violation) derive from one pure function. Drift raises a flag
even when axis A passes (the reconciliation differentiator).

## 3. Phase record (all gates evidence-backed; commits on main)

| Phase | Result | Key evidence / commits |
|---|---|---|
| M0 scaffold, env, tracing | PASS | Traced hello-world in LangSmith; caught env-propagation bug + dead gemini-2.5-flash (baac46a, 09053f3) |
| M1 domain core + seeds | PASS | 13 tables (alembic be61a6f8ddf0); scorecard extracted BYTE-FOR-BYTE from doc 05 §1 by script, asserted from Postgres read-back; corpus loader hash-verifies 71 docs (6d6a62a) |
| M2 checker vs synthetics | PASS + Aarvin approved | 17/17 incl. S17 exemption; deterministic CI via recorded cassettes; caught TurboTax-specific leak in R-01 trigger (f6c029b) |
| M3 corpus certification | PASS 96.23% -> 97.99% post-rulings | Loop 73.1 -> 84.9 -> 96.2 -> 98.0 as LangSmith experiments (f0b63bf, bea3bc9); details §4 |
| M4 API + SSE + disposition | PASS | 88/88 suite; lifecycle-validated dispositions, FP labels to eval_items, verified recompute over persisted outcome rows (f51ade6, bbc20ae) |
| M5 four surfaces on live API | PASS | Lane B subagent built + wired; integrator review caught 1 guardrail violation + 3 backend bugs; disposition round-trip proven, verified score moves (2ffd730, 8379509, 320d626) |
| M6 live mode | PASS | Real crawl (20 pages), barrier + partial-paste hold verified, paste resume, 50 flags/4 clusters; bare IG free claim flagged, disclosed FB post passed (a32765e) |
| M7 audit + acceptance + tag | IN PROGRESS | impeccable-style audit done (P1 one-blue fix, P2 token fix, both DOM-verified, 293d83e); model attribution fixed after Aarvin's manual review (570515c); awaiting his green light to tag |

## 4. The certification loop (the acceptance instrument)

Scoring: strict set = 199 analyst + footer-inherited records with GT verdict
pass/flag/na (GT needs_review excluded per dataset README; system
needs_review vs GT pass/flag earns half credit). Synthetics scored
separately (must be 100%). Evidence validity programmatic. Every iteration
is a named LangSmith experiment; full-run certification only.

| Iter | Score | Root cause fixed |
|---|---|---|
| 6 | 73.1% | Retrieval windows truncated the footer's drifted disclosure (45 records failed on text the checker never saw) -> library-anchor keywords (digit tokens of approved text) rank first in windowing |
| 7/8 | 84.9% | Correct footer verdict degraded: model stitched a quote from two paragraphs; validator rightly refused -> contiguous-quote prompt discipline (validator never loosened) + markdown-emphasis normalization + evidence-overlap matching for pages carrying two GT records on one rule |
| 9 | 96.23% | Threshold passed; 8 residual disagreements surfaced to Aarvin (never silently retargeted) |
| 11 | 97.99% | Aarvin's rulings applied: R-01 placement judgment calls -> needs_review (ambiguous field); footer-evidence records matched to footer verdict; markdown links unwrapped ([text](url) is rendering, not drift); P03/P20 conservative flags kept by his choice |

Remaining 4 misses, all disposed: 2 kept-by-ruling conservative flags, 1
model strictness in the conservative direction, 1 structural (one outcome
per page-rule cannot satisfy a GT pass+flag pair; multi-finding runner is
day-2).

Synthetics were re-qualified 17/17 after EVERY prompt or model change.

## 5. Model policy and cost (learned the hard way, all in decision log)

- check stage: **anthropic:claude-haiku-4-5** (paid, Aarvin-approved;
  ~$1 per full 171-call certification; measured 10M input TPM). Reason:
  Google free tier is project-wide and small on new keys (both flashes
  404/429); Groq free tier hides a 100k tokens/DAY cap visible only in 429
  bodies, which cannot carry corpus-scale runs.
- extract / cluster_label / report stages: groq:llama-3.3-70b-versatile ($0).
- All model ids pinned (never -latest) for eval reproducibility; per-stage
  env overrides (DEFAULT_MODEL_*); runs persist their model in
  runs.model_config and the UI attributes verdicts to it.
- LLM response cache keyed sha256(model+prompt): tuning iterations re-call
  only changed prompts; unchanged re-scores are $0/seconds.
- Ops lessons institutionalized: check telemetry (LangSmith) before
  theorizing; retries never sleep silently; verify ALL provider quota
  dimensions, not just the ones in response headers.

## 6. Deviations from spec, all logged in code/CLAUDE.md decision log

1. gemini-2.5-flash (spec §4) unavailable to new keys -> 3.5-flash, then the
   check stage moved to Haiku (above). 2. Embedding-based N6 clustering
   deferred: v1 clusters by (check_id, normalized evidence) which natively
   captures template propagation (the 44-page footer cluster); pgvector
   semantic clustering + retrieval are day-2 (materials.embedding column
   deferred with them). 3. Schema additions: runs.mode (corpus|live),
   events.event_type/property_id (SSE envelope must persist),
   runs.scores.outcome_rows (exact verified recompute), deterministic natural
   PKs for seeds. 4. E2 decomposition eval out of MVP1 (scorecard ships
   pre-decomposed; returns with the Customize studio). 5. Live POST /checks
   returns run_id from a synchronously-committed row; ingest runs as one
   in-process async task (07 §3), resume executes inside the paste/skip
   request (async task is a day-2 nicety).

## 7. Known limitations and day-2 backlog (also in code/CLAUDE.md)

- Multi-finding runner (one outcome per page-rule today; GT pairs like P02
  need finding-per-aspect).
- pgvector semantic retrieval + clustering (keyword-recall bound today).
  Clustering example noted by Aarvin 2026-07-10: same-meaning different-
  wording flags stay separate ("File 100% free with TurboTax" vs "File your
  taxes for $0 with TurboTax" = two clusters today, one analyst issue).
  Plan: embedding similarity within check_id on top of the deterministic
  exact-match pass; detailed note in code/CLAUDE.md backlog.
- Social checker accuracy presumed, not certified (answer key is web-only;
  dispositions feed the golden set to close this).
- Meta properties always via paste fallback (industry reality; time-boxed
  crawl attempt is wired for the day scraping works).
- UI fixture fallbacks, each documented in apps/web/src/lib/data.ts header:
  portfolio hero metrics (no /metrics endpoint yet), demo product cards
  (DESIGN.md demo dataset), rule text served from fixtures byte-identical to
  the DB seeds. Real data (products, flags, clusters, scores, evidence,
  dispositions, model) is API-served.
- Axis-B diff view (approved vs published, highlighted) recommended for flag
  detail. Undo/reverse lifecycle transitions not modeled. UI audit P3s:
  skip-link, tooltip keyboard access, recharts bundle weight.
- Day-2 from the locked backlog: screenshots + pins, audit accordion,
  insights tab, daily cron, auto-verify lifecycle, MCP server, PDF export.

## 8. Operational runbook (dev)

- `make db-up` (Postgres 16 + pgvector, docker), `make dev-api` (:8000),
  `make dev-web` (:3000), `make test`, `make smoke`.
- Secrets only in code/.env (gitignored; .env.example committed): minimum
  DATABASE_URL, LANGSMITH_API_KEY, GOOGLE_API_KEY, GROQ_API_KEY,
  ANTHROPIC_API_KEY for the check stage.
- Seed: `uv run python -m shiboleth.db.seed` (idempotent; byte-for-byte
  scorecard). Corpus run: POST /checks {mode: corpus} (cached, ~$0).
  Certification: `python -m shiboleth.evals.harnesses.e3 --name <exp>`.
- LangSmith project: shiboleth-marketing-compliance-analyst-project.
- Test suite: 103 api tests (unit + integration incl. API round-trips) +
  web build/lint; checker tests replay recorded cassettes (no network in CI).

## 9. What remains before the freeze

1. Aarvin's manual test green light (in progress; two findings from his
   review already fixed: model attribution, and the axis-B explanation
   validated against the DB).
2. Final acceptance sweep: full suite + cached E3 re-run as the frozen
   record + staged corpus run latest (done: 9ec08659) + click-through.
3. Tag `mvp-v1-base-condition`, push tag + remaining commits (confirm-first).

After the freeze, every future change (models, prompts, features, new
customers) re-runs E3 against this baseline; dispositions accumulate into
the golden set; the day-2 backlog is prioritized in 04/08 and
code/CLAUDE.md.
