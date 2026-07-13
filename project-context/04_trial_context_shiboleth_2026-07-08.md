# Shiboleth trial context — the living source of truth (started 2026-07-08)

> This document is the running context for the 3-day trial build. It supersedes the hackathon framing. Read this plus `CLAUDE.md` to be fully oriented. Update this file as decisions land.

## 1. The real situation

Not a hackathon. A **3-day work trial in San Francisco with Shibboleth**, a company potentially hiring Aarvin. The brief: build something useful for **marketing compliance analysts** who check marketing materials put out by a fintech, in the fintech-and-bank-partnership wedge (the bank requires the fintech's marketing to comply with a defined scorecard; the fintech's analyst enforces it continuously).

Timeline: **basic MVP by end of day 1, iterate day 2, showcase first half of day 3.** The audience judges product thinking as much as the build.

## 2. Validated analyst pain points (researched 2026-07-08)

Priority P1 = must be visibly addressed by the product. Coverage target met: all five P1 and three P2 pains are addressed.

| # | Pain point | Priority | Real-world evidence | Addressed by |
|---|---|---|---|---|
| 1 | Volume and manual overwhelm: 35% of compliance/legal staff overwhelmed by content volume; manual review is repetitive and falls behind | P1 | IntelligenceBank 2023 survey of 550 pros; Wolters Kluwer | Automated checks; clusters; dashboard |
| 2 | Post-publication drift: approved material edited after the fact; nobody re-reviews live content | P1 | Real-time monitoring products exist precisely to "detect unapproved edits to live accounts" and capture "every website update including edits and deletions" (Pagefreezer, Luthor) | Daily monitoring; reconciliation vs library (Drift) |
| 3 | Bypass: content ships without pre-approval (social, campaigns); FINRA 2210 requires pre-approval of static content, interactive content is only supervised after the fact | P1 | FINRA guidance; consent orders on unapproved third-party marketing | Reconciliation (Unapproved); continuous social monitoring |
| 4 | Evidence and audit burden: regulators and bank partners demand documented, retrievable proof (what was live, when, findings, decisions); FINRA 3-year retention | P1 | FINRA archiving rules; consent-order documentation demands | Per-flag audit trail of all LLM steps; evidence snippets; triage notes; PDF report |
| 5 | Bank-partner oversight pressure: FDIC consent orders force banks to police fintech partners' marketing (UDAP, misrepresented FDIC insurance); fintechs must prove compliance to keep the partnership | P1 | FDIC consent orders 2023-2024 (Morrison Foerster, Consumer Finance Monitor, Nat'l Law Review) | Verified score; exportable report; scorecard mirrors bank requirements |
| 6 | Setup fatigue and repetition: same ruleset re-checked across every product and channel | P2 | Implied by volume stats; workflow-tool market | One global scorecard, defined once in Customize |
| 7 | Slow, convoluted review loop with marketing: 79% say review is too long; feedback friction | P2 | IntelligenceBank survey | Clusters (batch review); inline flags on material (clear fixes) |
| 8 | False positives and judgment calls: automation without triage creates alert walls | P2 | Analyst practice; "clear and conspicuous" judgment in Reg DD | Per-flag confirm/dismiss + note; draft vs verified score |
| 9 | No live inventory of what marketing is live where | P3 | Implied by monitoring-product market | Dashboard cards per product (partial) |
| 10 | New-platform ambiguity (20% cite unclear rules for new platforms) | P3 | IntelligenceBank survey | Roadmap only |

Sources: [Wolters Kluwer](https://www.wolterskluwer.com/en/expert-insights/marketing-compliance-in-financial-services), [IntelligenceBank challenges](https://intelligencebank.com/insights/what-are-the-top-marketing-compliance-challenges/), [Morrison Foerster FDIC consent order](https://www.mofo.com/resources/insights/230504-fdic-enters-into-consent-order), [Consumer Finance Monitor on FDIC scrutiny](https://www.consumerfinancemonitor.com/2024/04/09/recent-fdic-consent-orders-show-increased-regulation-scrutiny-of-bank-relationships-with-fintech-partners/), [FINRA social media](https://www.finra.org/rules-guidance/key-topics/social-media), [Pagefreezer](https://www.pagefreezer.com/financial-services/), [Luthor](https://www.luthor.ai/resources/social-media-compliance-platforms-wealth-management).

## 3. The product (information architecture)

**Level 0 — Dashboard (home).** Grid of product cards, one per fintech product (demo: TurboTax Free). Card shows: compliance score, short AI summary note, trend, open flags, last checked. Loading state while a check runs (pipeline observable one click deep, abstracted by default). New check button top right: URLs + handles + assign to product, nothing else.

**Level 1 — Product detail (click card).** Score breakdown + compliance flags list (clustered, severity, triage state). Per-flag confirm/dismiss with optional note; bulk actions per cluster; draft vs verified score.

**Level 2 — Flag detail (click flag).** Multimodal evidence view: the actual material with the violation inline-highlighted (day 1: extracted text with highlights; day 2: Playwright screenshots / social screen grabs with positioned highlight regions, click-to-focus). Plus the audit trail: every intermediate LLM step behind this flag (crawled, retrieved, check, reasoning, model, timestamp).

**Standing surfaces.** Sidebar: **Customize** (above New check, Cowork-style) opens the scorecard studio = the old Stage 2 screen standalone: upload once, LLM decomposes into trigger+requirement binary checks, edit/delete/add/severity, disclosure and substantiation library companion (async observable synthesis, LLM auto-linking). Sidebar also lists recent checks/products; user chip at bottom.

**Old three-stage check flow** remains the under-the-hood pipeline and the watchable run view; scorecard review is removed from the per-check path (done once in Customize).

## 4. Locked decisions (running log for the trial)

- Card = one product. One **global scorecard** for all products (per-product overrides = roadmap).
- Scorecard rules are **conditional**: decomposition = trigger check + requirement check; untriggered = N/A, not pass.
- Flag detail day 1 = extracted text with inline highlights; day 2 = Playwright screenshots with positioned pins.
- Persist **every pipeline event per flag from day 1**; audit-trail UI tab is day 2.
- Real re-run button day 1; true daily cron day 2; card trend seeded with history for the demo.
- Process: build now (updated Claude Code handoff), Claude Design runs in parallel for day-2 polish.
- Database: **Postgres** (local Docker; Neon/Supabase free tier if hosted) — one DB for everything: relational core (products, checks, rules, flags), **JSONB** for high-volume unstructured payloads (crawled content, pipeline events, LLM I/O), **pgvector** for embeddings (finding clustering, content retrieval). SQLite explicitly rejected: high-volume unstructured writes + vector similarity + concurrent pipeline workers.
- Carried from earlier: shadcn/ui foundation; fintech-trust minimal aesthetic; per-stage model dropdown (Gemini free first, Groq, OpenAI, Anthropic) behind a provider-agnostic layer (Vercel AI SDK); LangSmith tracing day 1; two eval harnesses (decomposition quality; checker quality), triage notes feed the golden set; needs-review score treatment parked; email out of scope; crawl depth 2 / cap 20 / post timeframe filter; Instagram + Facebook with paste fallback; no em-dashes in product copy.

## 5. The demo scorecard (provided by Aarvin, seed for Customize)

1. If TurboTax Free is mentioned, the following must be disclosed right underneath: "~37% of filers qualify. Simple Form 1040 returns only (no schedules, except for EITC, CTC, student loan interest, and Schedule 1-A)."
2. If a rate of finance charge was stated, was the finance charge stated as an APR?
3. If the product advertised is a deposit product, does the FDIC insurance language state: deposit product is FDIC-insured up to $250,000 through [Bank]?
4. If an institution states a bonus in an advertisement, does it state clearly and conspicuously, if applicable: (1) "Annual percentage yield" using that term; (2) time requirement to obtain the bonus; (3) minimum balance required to obtain the bonus; (4) minimum balance to open the account if greater; (5) when the bonus will be provided. General statements such as "bonus checking" do not trigger the disclosures.

(These map to real regimes: FTC deceptive-advertising, TILA/Reg Z APR, FDIC insurance representation, Reg DD 1030.8(d) bonus disclosures. Rule 4 is the judgment-heavy one: "clearly and conspicuously".)

## 6. Three-day plan

**Day 1 (today) — MVP spine:** app shell (sidebar with Customize + New check + product list), dashboard with TurboTax card (seeded trend), scorecard studio seeded with the 4 rules + D-03 library entry, New check → pipeline (crawl website live, paste social) → flags list with triage → flag detail (text highlights) → draft vs verified score. Postgres + event persistence + LangSmith from the start. Re-run button.
**Day 2 — differentiation and polish:** Playwright screenshots with positioned flag pins; clustering + reconciliation (Drift/Unapproved); audit-trail tab; live IG/FB fetch attempt (time-boxed); daily cron; eval harness v0 (golden set from triage notes); Claude Design polish applied.
**Day 3 (first half) — showcase:** seeded demo data; narrative = pain points 1-5 → dashboard as the answer → drill to flag detail → audit trail; dry runs; fallback paths. Nothing new built.

## 6b. Disposition, audit accordion, and metrics (locked 2026-07-08, late)

**Disposition component (replaces "triage").** One component handles review + routing. Actions: Dismiss (false positive, optional note) or Confirm (violation) → then Assign to owning team (Social, Web, Growth, Legal) with the note carried. Flag lifecycle: open → confirmed → assigned → resolved (dismissed is terminal). Assignment enables per-team remediation metrics. Rationale: "disposition" is the standard compliance term for a documented review outcome.

**Audit trail = accordion inside "Why this was flagged".** Not a separate timestamp log. Expandable sections per pipeline stage (Crawled → Extracted → Trigger check → Requirement check → Verdict); each explains what happened, what it produced, and what it consumed from the preceding stage (explicit causal chain). Events persisted per flag from day 1; accordion UI day 2 (day 1 shows the compact chain).

**Dashboard hero metrics (portfolio-wide, day 1), each evidence-backed and mapped to a P1 pain:**
1. Portfolio compliance score (verified, severity-weighted, 7-day trend) — the number reported to the bank partner (PerformLine-style scoring/risk-ranking).
2. Open confirmed violations by severity + aging (oldest N days) — governance KPI; escalation driver.
3. Awaiting triage + median time to disposition — the volume/overwhelm pain made visible (alert volume + MTTD are standard monitoring ops metrics).
4. Coverage: % of tracked live assets checked in last 24h + assets discovered — the bypass/inventory answer.
5. Caught this week: unapproved + drift counts — the differentiator; detection of unapproved/edited live content.

**Secondary metrics (day 2, product detail / insights):** time to remediation per assigned team; false-positive rate per rule (feeds evals + scorecard tuning); violations by rule and by channel; recurrence rate after fix; audit readiness (% findings with documented disposition + evidence, target 100).

Sources: PerformLine fintech/partner-oversight pages, Alessa AML KPIs, AccountableHQ compliance monitoring KPIs, Sprinto compliance metrics, GAN Integrity, Salus GRC, Pagefreezer.

**Reprioritization note:** volume/overwhelm, bypass, and evidence/audit are hero-level concerns; the hero metrics row is their permanent home on screen one.

**FINALIZED 2026-07-09:** metric definitions, per-metric intent (question answered → decision driven), data requirements (runs.scores JSONB as the sparkline/trend time series), and the chart library (shadcn/ui Charts on Recharts v3, nothing else) are locked in `01_spec_v1` §10. Second research round (MetricStream, AuditBoard, Freshworks-adjacent SLA sources) confirmed the five hero metrics and added the insights-tab formulas (remediation cycle time, repeat violations). UI layouts unchanged: the prototype's card sparkline and hero strip already match; no re-mock needed.

## 6c. Design deliverables (v2, 2026-07-08, late)

- `03_design_handoff_shiboleth_v2_2026-07-08.pdf` — supersedes v1. Eight print-faithful mockups with UI + under-the-hood captions: 1 Dashboard (hero metrics, 3 card states), 2 New check modal, 3 Scorecard studio synthesizing, 4 Scorecard studio ready (real 4-rule scorecard, trigger+requirement decomposition, D-01 library entry), 5 Watchable run view (no stage tracker), 6 Product detail (metrics mirror, clustered flags, lifecycle chips, Insights tab reserved), 7 Flag detail (inline highlight, causal accordion, Disposition with assign), 8 Report export preview. Plus v1-to-v2 change list, shadcn mapping delta, prototype requirements, demo dataset.
- `_HANDOFF_PROMPT_claude_design_v2_2026-07-08.md` — paste-ready; frames v2 as an update to the v1 design and demands a clickable prototype (wired navigation, disposition click-through, simulated streaming), not static frames.
- Reconciliation note: the v1 three-stage flow and stage tracker are retired; scorecard review removed from the check path (now the Customize feature); v1 run screen lives on as the watchable run view.
- **DESIGN.md format (2026-07-09):** rewritten to conform to the Google Labs DESIGN.md spec (github.com/google-labs-code/design.md): YAML front matter with machine-readable tokens (18 colors, 6 typography scales, rounded, spacing, 13 components with token references) + canonical prose sections (Overview, Colors, Typography, Layout, Components, Do's and Don'ts) + our surface contracts preserved. Lints clean: 0 errors, 0 warnings (`npx -p @google/design.md designmd lint DESIGN.md`). Tokens exportable to Tailwind via the same CLI if the build wants them.

## 6d. Roles locked (2026-07-09)

Claude (Cowork steward) wears these expert roles for the rest of the trial, mapped to installed skills:

**Decide:** technology consultant (`cowork-advisory-playbook`) — evaluates libraries and stacks, recommends the lean option, buy-not-build except compliance logic; solutions architect + system designer (`solution-architect`, `engineering:system-design`) — architecture, data flow, trade-offs, drift watch; data engineer (`data-engineer-scientist`) — ingestion pipeline, schema, batch storage, vectors; compliance domain expert (`compliance-domain-expert`) — what a violation is, demo-vs-production line, worn throughout as the correctness conscience.

**Build:** AI engineer / SDE (`ai-engineer`) — clean testable code, LLM integration behind one interface; build handoff author (`build-agent-handoff`) — self-contained prompts for Claude Code; evaluations engineer (`ai-agent-evaluations`) — two eval harnesses, LangSmith, golden set from dispositions.

**Verify (after every build round, correctness is the north star):** QA / SDET (`qa-verifier`, `engineering:testing-strategy`) — verifies claims against the real repo, tests, contract stability; release shipper (`release-shipper`) — push-readiness, deploy, smoke test; demo director (hat, no skill) — day-3 narrative, seeded data, dry runs, fallbacks.

**Operating principles locked with the roles:** correctness end to end over feature count; lean prototype, one use case running end to end = success; iterate fast; prefer pre-made libraries; ingestion-first architecture (batch service lands website + social content in the store; analysis reads only from the store, never live). Database direction (one Postgres playing SQL + JSONB-NoSQL + pgvector roles) is the standing recommendation, NOT yet locked; stack evaluation awaits Aarvin's green light.

## 6e. Verdict model, coverage findings, lifecycle (locked 2026-07-09)

From the company problem statement in doc 05, three model upgrades, all in the database from day 1, UI moments day 2:

**Missing findings (coverage as a finding).** Every crawl stores its page/post inventory. The next run diffs against it; anything that existed and is now gone raises a flag of type Missing (a finding with no material attached, e.g. a vanished disclosure page). Day 1: inventory storage + flag type in the model. Day 2: the badge in the flags list, demoed via a seeded prior run.

**Two-axis verdict with named intersection (three tags per material).** Axis A: compliant with the rules, yes/no. Axis B: matches pre-approved library material, yes/no. Plus the intersection cell as its own display tag: "All good" (A yes, B yes), "Drifted but compliant" (A yes, B no; process failure), "Approved but non-compliant" (A no, B yes; the approval itself was wrong, requires running rules against library entries, build day 2 if time), "Unapproved violation" (A no, B no; worst cell). All three tags render on each material. Replaces Fail/Drift/Unapproved as separate flag types; those become derived views.

**Incident lifecycle with system verification.** Flag states: open → confirmed → assigned (fix in progress) → fix pending verification → closed. Dismissed is terminal from open. A flag closes only when a later crawl re-checks the exact spot and the fix holds. Day 1: all states in the model, manual transitions. Day 2: the auto-verify re-check wired to the crawl.

**Email: completely out of scope (2026-07-09, Aarvin), despite the company demo narrative mentioning it. No .eml handling until reopened.**

## 6f. V1 intent and development doctrine (locked 2026-07-09, the reference for all build work; do not stray)

**V1 definition of done (the base case).** The generic system, pointed at Intuit TurboTax (turbotax.intuit.com with domain link discovery, depth 2, cap 20; instagram.com/turbotax; facebook.com/turbotax; the VERBATIM 4-rule scorecard from doc 05; library entry D-01), runs ONE compliance scan end to end, correctly, producing: the report, per-property analysis, two-axis three-tag scoring, and the defined metrics. That successful run freezes as the **base condition**: the regression baseline every future change is measured against. Nothing hardcoded to TurboTax; it is the first runtime input to a product-agnostic, scorecard-agnostic system whose architecture, flow, and UI are fixed and opinionated.

**Doctrine (in force for every build step):**
1. Intent-driven: this section is the root artifact; everything traces to it.
2. Spec-driven: specs written and evaluated before code (essential UI, backend, agent architecture, data model, tests).
3. Test-driven: test cases defined with the specs; TDD in the build.
4. Reusability and appropriate abstraction: components and services built once, reused (one flag row, one metric card, one lifecycle chip, one lane component; shared backend services).
5. Smart agent architecture: sub-agents under an orchestrator. Direction: a LangGraph-style graph as orchestrator, each sub-agent a node with a defined contract (extraction, decomposition, checker, clustering, reconciliation, summary). Deterministic flow, intelligence inside nodes.
6. MCP servers: adopt well-recognized ones where they genuinely accelerate; consider building our own per industry standards where the use case deserves it.
7. Minimum cost: free tiers, cheap models first. End goal: completeness and correctness.
8. Code hygiene: every code file carries a metadata snippet describing its functionality, updated with every change.
9. Data-driven enhancement: three eval harnesses in LangSmith from day one: retrieval quality (completeness + extraction fidelity of ingested web material), decomposition quality (coverage, atomicity, faithfulness), checker quality (verdict accuracy, evidence validity, reason quality). Dispositions feed the golden set.

**Architecture skeleton:** batch retrieval/ingestion service (crawl + social, paste fallback) → unstructured store (Postgres JSONB; run inventory per crawl) → graph pipeline (nodes above) → scoring/metrics (SQL aggregates) → disposition lifecycle. Analysis never touches the live web.

**V1 UI scope (from the design-files/ prototype):** shell (sidebar: Customize, New check, products), dashboard (hero metrics; flagged + checking card states), New check modal, Customize studio (upload → decompose → edit + library), watchable run view, product detail (metrics row + flags + disposition), flag detail (highlighted extract, compact why-flagged chain, disposition with assign). Deferred with data modeled day 1: PDF export, screenshots tab, insights tab, view toggle, full audit accordion UI, Missing-flag UI, audit-the-library.

**Stack under evaluation (locked only after Aarvin approves the evaluation):** Next.js + shadcn (locked); crawl bake-off: Playwright (free, MIT) vs Firecrawl vs Tavily extract vs crawl4ai, or a combo (API for bulk text, Playwright for rendering/screenshots); Postgres = SQL + JSONB + pgvector (verify where pgvector earns its place); LangGraph/LangChain sized to need + LangSmith (non-negotiable); Tavily on merit; MCP adopt-vs-build; supporting libraries (xlsx, extraction, structured outputs, Postgres-native jobs).

**Reference project (learning source only, never mixed with this project):** `Self-Learning/LangSmith/lca-lc-foundations` (connected to the session). Study its LangChain/LangGraph/LangSmith patterns; apply lessons here.

**Execution order (step by step, no straying):** 1 log intent (this section) → 2 study reference project → 3 stack evaluation with evidence → Aarvin locks stack → 4 `01_spec_v1` (intent, specs, essential UI, architecture, data model, test cases, eval plan, base condition) → 5 `02_handoff_to_claude_code`.

## 6g. Stack locked + two refinements (2026-07-09)

**Stack locked by Aarvin:** Next.js + shadcn frontend; Python + FastAPI backend; LangGraph 1.x StateGraph orchestrator with create_agent sub-agents inside nodes; crawl4ai primary crawler (Playwright underneath, screenshots day 2), Firecrawl free tier fallback; Tavily not in v1; Postgres (Docker) + JSONB + pgvector, SQLAlchemy 2 + Alembic; in-process async job per run, SSE streaming; LangChain init_chat_model provider strings for the model dropdown (Gemini 2.5 Flash + Groq free first); LangSmith tracing + three eval harnesses; dev-time MCPs for Claude Code: Postgres, Playwright, shadcn, Context7.

**Model pin deviation (2026-07-09, M0):** `gemini-2.5-flash` returns 404 for newly created Google keys; default checker/extract model pinned to `gemini-3.5-flash` (stable, free tier). Surfaced by Claude Code, approved by Aarvin. Wherever 01_spec §4 names 2.5-flash, read 3.5-flash.

**Refinement 1, database as cache/dedup layer:** materials are content-hashed and timestamped; ingestion checks freshness against a policy (per-property TTL) and fetches only missing or stale items. Never hit the internet for data we already hold fresh. Enables fast, cheap iteration.

**Refinement 2, our own MCP server:** v1 service layer is MCP-ready from day 1 (tool-shaped functions with Pydantic schemas: run_scan, get_report, list_flags, disposition_flag). Day 2, after the base condition is achieved, wrap them in a thin FastMCP server (~1h, pattern from the reference repo). Not a day-1 item; competes with correctness.

## 6h. Ground truth v1 assembled (2026-07-09, DRAFT pending Aarvin approval)

Approach pivot (Aarvin): establish ground truth BEFORE building; the approved dataset becomes the acceptance target for the FastAPI endpoint (wrapping LangGraph agents wrapping LLMs), scoped to the New check input + flags screens; evals in LangSmith.

Chain: 54-page TurboTax corpus captured by the (now frozen) snapshot-capture tool (crawl4ai, homogeneous, hash convention sha256-of-stripped-body) → Cowork compliance-analyst pass → `ground-truth/ground_truth.json` (460 records, reasoning embedded; 108 pass / 58 flag / 99 N-A / 195 needs_review; sources: 30 analyst, 220 footer-inherited, 193 screened-policy, 17 synthetic balanced 8 fail / 8 pass / 1 exemption) + `ground-truth/README.md` (metadata + approval line). Headline real findings: CKM FDIC formulation violation (P18), footer disclosure drift vs D-01 (44 pages), $0-price placement-violation candidates (P05/P07), Spanish-variant drift (P45), military free-offer unapproved class (P08/P10), strict-vs-practical R-01 policy question (GT-F05) deliberately left for the human gate. Corpus-in evaluation rule re-affirmed. Repo: github.com/AarvinGeorge/shiboleth-marketing-compliance-analyst (private). **APPROVED as-is by Aarvin 2026-07-09 → FROZEN.** MVP1 build set produced: `08_mvp1_build_brief` (4 UI surfaces incl. New check modal; seeded pre-decomposed scorecard, no Customize UI; corpus|live modes; acceptance thresholds §3; M0-M7 with M3 iterate-until-match loop; modality-ready schema) + `_HANDOFF_PROMPT_claude_code_mvp1` (points at design-files/ prototype as frontend layout source). Cowork QA-verifies each M-gate.

## 7. Open items

- Sample scorecard .xlsx file (Aarvin owes; rules above are the content).
- Needs-review score treatment (parked).
- Detailed eval metric scoping (parked; two-harness structure locked).
- Per-product scorecard overrides, email ingestion, multi-tenant (roadmap talking points for the interview, not build items).
