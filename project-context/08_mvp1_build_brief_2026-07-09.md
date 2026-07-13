# 08_mvp1_build_brief (2026-07-09)

> The scoped-down MVP1 build definition. Supersedes the SCOPE (not the content) of `06_prd_shiboleth_v1` and `02_handoff_to_claude_code_v1` for this first build: everything in those documents still governs HOW we build (doctrine, guardrails, env, repo, phases discipline); THIS document narrows WHAT gets built and adds the ground-truth acceptance contract. Read with `01_spec_v1` (§4 nodes, §5 data model, §6 API, §10 metrics), `07_architecture_v1` (choreography, contracts, autonomy dial), `DESIGN.md`, `05` (VERBATIM scorecard), `ground-truth/` (the acceptance target).

## 1. What MVP1 is

One backend service + four UI surfaces that make this sentence true: **"The analyst enters the TurboTax marketing properties, the system checks them against the preloaded scorecard, and the flags shown in the UI match the approved ground truth, by cluster and by property, investigable down to highlighted evidence."**

Layering (fixed vocabulary): FastAPI **service** (the application) exposes **endpoints** (the API doors) wrapping the LangGraph **agent harness** (nodes wrapping LLM calls) measured by **LangSmith evals** against `ground-truth/ground_truth.json`.

## 2. Scope

**In (backend):** FastAPI app; Postgres (docker) per 01_spec §5 including runs.scores, events, lifecycle enum, `modality` + `media_ref` on materials/flags (future-proofing: text now; image/post/video later); seeded data: the VERBATIM 4-rule scorecard, its APPROVED decomposition (from ground-truth reasoning: trigger+requirement binary checks per rule), library entry D-01, product TurboTax Free with its three properties; LangGraph harness nodes N1 (extract-properties, also serves the modal's live chips), N2 (ingest via crawl4ai + cache/dedup + paste fallback + run inventory), N4 (checker sub-agent per material×rule, structured output, evidence substring validation), N5 (reconciliation vs D-01: drift/unapproved), N6 (clustering: embeddings + label), N7 (scoring, draft/verified); SSE events; disposition endpoint with verified-score recompute; **two run modes: `corpus` (input = ground-truth snapshots by hash; deterministic acceptance) and `live` (crawl4ai fetch)**. LangSmith tracing from first commit + the E3 checker harness scoring corpus-mode runs against ground truth.

**In (frontend, exactly four surfaces per DESIGN.md):** U2 dashboard (hero metric cards + product cards incl. checking-progress state + New check button), U3 New check modal (product create-or-pick, freeform links → live chips, crawl/timeframe selects), U6 product detail (metric row; flags list with BOTH groupings: by cluster and by property; cluster bulk actions; per-flag Dismiss/Confirm+assign+note; lifecycle chips; three verdict tags), U7 flag detail (extracted text with the evidence span highlighted, three tags + one-line explainer, lifecycle strip, Disposition panel, flag facts, compact why-flagged chain from persisted events).

**Out of MVP1 (data modeled where already locked; no UI):** Customize studio (scorecard is seeded), report/PDF export, screenshots tab and region highlights, insights tab, Missing-flag UI, audit-the-library, daily cron, auto-verify closure, full run-lanes view (stretch: allowed if the gates are green early), MCP server, social live-fetch beyond the paste fallback, email (never), multimodal rendering (schema-ready only).

## 3. The acceptance contract (ground truth)

Precondition: Aarvin has approved `ground-truth/ground_truth.json` (status FROZEN). Then MVP1 is DONE when:

1. **Corpus-mode reproduction:** a corpus-mode run over the 54 snapshots + 17 synthetics, scored by the LangSmith E3 harness, meets: (a) verdict agreement ≥90% on `analyst` + `footer_inherited` records (pass/flag/not_applicable exact-match; a system `needs_review` against a ground-truth pass/flag counts half); (b) 100% on `synthetic_author` records including S17's exemption; (c) evidence validity 100% programmatic (every quote substring-matches its snapshot); (d) `screened_policy needs_review` records are excluded from accuracy and reported separately as an ambiguity-recognition rate.
2. **Live-mode E2E:** a live run on the three TurboTax properties completes (paste fallback for Meta), produces flags rendered in U6 (both groupings) and U7 (highlight working), dispositions recompute the verified score, all events persisted and traced.
3. **UI fidelity:** the four surfaces match DESIGN.md (three-tag verdicts, lifecycle chips, metric cards with intent tooltips); impeccable UI-audit gate run.
4. Zero TurboTax-specific logic in code (seed data only); all tests green; meta-snippets current.

## 4. Build order (gates, TDD)

**Eval scope for MVP1:** LangSmith tracing from first commit; **E3 checker harness = the acceptance instrument** (built at M3, rerun at M7); E1-light = live-mode coverage counts vs run inventory (M6). E2 decomposition-quality deferred (scorecard ships pre-decomposed; E2 returns with the Customize studio).

M0 scaffold (repo layout per 07 §5 minus web pieces not needed; env per 02 §2 with an explicit pause for Aarvin to fill `code/.env`; LangSmith smoke) → M1 domain core + seeds (migrations, scoring unit tests, seed script loads scorecard/decomposition/D-01/product; corpus loader binds snapshots by hash) → M2 checker harness (N4+N5 on synthetics first: all 17 must score correctly before touching real pages; recorded cassettes for CI) → M3 corpus-mode pipeline (N6, N7, events; E3 harness; hit acceptance §3.1) → M4 API + SSE (endpoints per 01_spec §6; disposition + recompute) → M5 frontend four surfaces (primitives per DESIGN.md) → M6 live mode (N1, N2 with cache; paste fallback; acceptance §3.2) → M7 UI audit + full acceptance run + tag `mvp1-base-condition`.

Note the deliberate order: the checker must beat the synthetics (M2) before it earns real pages, and corpus mode must match ground truth (M3) before live mode exists (M6). Correctness inward-out. M3 is an iterate-until-match loop (tune prompts / few-shots from ground-truth reasoning / retrieval / model → rerun E3 → compare experiments in LangSmith) until §3 thresholds are met. Frontend layout/composition source: the prototype in `design-files/Shiboleth-marketing-compliance-checker-v1/` (UX Version 2), with DESIGN.md as the binding contract and the v2.2 delta PDF winning on verdict tags, lifecycle chips, and metric contents.

## 4b. Parallelization plan (approved 2026-07-09)

Two lanes, worktree-isolated. **Lane A (mainline, the critical path):** M2 recording → gate → M3 iterate-until-match → M4. **Lane B (spawn immediately, no waiting on M2):** M5 frontend: primitives then the four surfaces, built against the frozen contracts (types.ts, DESIGN.md, prototype) with fixture data DERIVED from ground_truth.json records (realistic shapes, not invented; fixtures are dev-time stand-ins, swapped for live API data at integration, components stay pure). Lane B rules: zero LLM calls (all quota belongs to Lane A's E3 loop); never alters contracts, schemas, or DESIGN.md; merges reviewed by the integrator against DESIGN.md + schemas. Gate evidence stays strictly in §4 order: M5's gate is declared only after integration with real M4 endpoints. An optional Lane C (M4 plumbing: SSE envelope, disposition endpoint on M1's schema, pipeline stubbed) may be proposed after Lane B's first clean merge.

## 5. Future-modality note (architecture only, no build)

Flags and materials carry `modality` (text|image|social_post|video) and `media_ref` (nullable) plus `location` already; a future video finding deep-links via media_ref + timestamp in location. Frontend evidence panel is a swappable component keyed on modality. No other MVP1 accommodation.
