# 02_handoff_to_claude_code_v1 (2026-07-09)

> The build handoff for Shiboleth MVP v1. Read with: `06_prd_shiboleth_v1` (requirements + acceptance), `01_spec_v1` (technical spec), `07_architecture_v1` (runtime choreography, pause/resume, frontend architecture, scaffold, contracts, autonomy dial), `DESIGN.md` (UI contract), `04_trial_context` §6b-§6g (locked decisions), `05_shibboleth_problem_context` (VERBATIM scorecard). The paste-ready prompt is `_HANDOFF_PROMPT_claude_code_2026-07-09.md`.

## 1. Intent (verbatim, binding)

Shiboleth is a marketing-compliance monitoring product for compliance analysts. MVP v1 succeeds when ONE scan of Intuit TurboTax Free runs end to end, correctly, producing the report, per-property analysis, two-axis three-tag scoring, and the defined metrics, and that run freezes as the **base condition** (LangSmith experiment `base-condition-v1`) for all future data-driven enhancement. This is a real product: **nothing hardcoded to TurboTax**; product, properties, scorecard, and library are runtime data in a fixed, opinionated architecture (product-agnostic, scorecard-agnostic).

Doctrine, in force for every task: intent-driven, spec-driven, **test-driven (tests before implementation)**; reusability and appropriate abstraction; graph-orchestrated sub-agents; minimum cost (free tiers, cheap models first); completeness and correctness as the end goal; **every code file opens with a meta-snippet header** (purpose, contract, key dependencies) **updated in the same commit as any change to the file**; three eval harnesses (retrieval, decomposition, checker) wired in LangSmith from day one; dispositions feed the golden set.

## 2. Repo layout and environment (locked)

- **All code lives in `code/` inside this project directory.** Nothing outside it.
- **`code/` is its own git repository with its own dedicated GitHub remote** (project norm: each project gets its own repo, separate and non-conflicting from any parent directory's remote; never nest-commit into a parent repo). `.gitignore` covers `.env`, `CLAUDE.md`, dependency and browser caches. Creating the remote and any push require Aarvin's confirmation first.
- `code/apps/web` Next.js + shadcn/ui (+ shadcn Charts). `code/apps/api` Python 3.12 + FastAPI + LangGraph/LangChain 1.x + SQLAlchemy 2 + Alembic. `code/docker-compose.yml` Postgres 16 + pgvector. `code/` uses `uv` for Python, pnpm or npm for web.
- **Secrets and config only in `code/.env`** (gitignored), with a committed `code/.env.example` carrying placeholder values, following the reference conventions (placeholders like 'your_..._key_here'; verify-at-startup with masked `*_API_KEY` echo): `DATABASE_URL`, `GOOGLE_API_KEY`, `GROQ_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `TAVILY_API_KEY` (present, UNUSED in v1), `LANGSMITH_TRACING=true`, `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT=shiboleth-marketing-compliance-analyst-project`, `DEFAULT_MODEL_*` per stage. Load via python-dotenv; never read keys anywhere else; never commit `.env`.
- Create **`code/CLAUDE.md` (gitignored)** at scaffold time containing: the §1 intent verbatim, the doctrine, the phase plan and current phase status (update as phases complete), the meta-snippet convention, the guardrails (§5), and pointers to the five planning docs by relative path (`../06_prd...`, `../01_spec...`, `../DESIGN.md`, `../04...`, `../05...`).

## 3. Build phases (from 01_spec §9; each phase gates on its tests passing)

- **P0 scaffold:** repo layout, docker-compose Postgres+pgvector up, `.env.example`, env verification, LangSmith tracing smoke test, CI (pytest + web build), meta-snippet convention documented in `code/CLAUDE.md`. Gate: hello-world trace visible in LangSmith; CI green.
- **P1 domain core:** migrations for the full data model (01_spec §5, including runs.scores, run_inventory, events, lifecycle enum, eval_items); scoring module (pure functions) with unit tests first (severity weights, N/A exclusion, draft vs verified recompute, intersection-tag derivation, lifecycle transition validation, content-hash dedup, freshness policy). Gate: all unit tests green.
- **P2 scorecard service + studio (U4):** xlsx parse (verbatim preservation test), decomposition sub-agent (Pydantic response_format), library synthesis + auto-linking, re-decompose-on-edit; U4 per DESIGN.md. Gate: the 4-rule scorecard uploads, decomposes, is editable; recorded-LLM (cassette) tests green.
- **P3 ingestion:** crawl4ai crawler (BFS depth 2 cap 20, domain-scoped), cache/dedup + freshness, run inventory, social fetch attempt inside a 10-minute hard time-box, paste-content intake; integration tests against a local fixture site. Gate: fixture crawl deterministic; cache hit on second run proven by test.
- **P4 pipeline + run view (U5):** LangGraph StateGraph N1-N7 (01_spec §4), SSE events, evidence substring validator, needs-input state; U3 modal + U5 lanes. Gate: fixture E2E scan completes; events ordered; run watchable.
- **P5 flags + disposition (U6, U7):** three-tag verdicts everywhere, cluster grouping, disposition endpoint (dismiss/confirm+assign+note), verified-score recompute, report block. Gate: E2E fixture scan → flag → disposition → score change, all asserted in tests.
- **P6 dashboard (U2) + metrics:** hero strip + product cards per 01_spec §10 and DESIGN.md, shadcn Charts sparklines, metrics SQL aggregates with unit tests. Gate: metrics match hand-computed fixtures.
- **P7 evals:** three harnesses (01_spec §7), golden-set seeding flows (E2 reference decompositions and E3 labeled triples drafted for Aarvin's approval), disposition-to-golden-set append. Gate: all three harnesses run against the fixture scan.
- **P8 the base condition:** run the real TurboTax scan (paste social content when Meta blocks), review outputs with Aarvin (decomposition approval, flag verification, disposition pass), fix, re-run, then freeze `base-condition-v1` in LangSmith and tag the git commit `base-condition-v1`. Gate: PRD §8 acceptance checklist fully satisfied.
- **UI audit gate (before calling v1 done):** run the impeccable taste-gate audit over U2-U7 against DESIGN.md; fix violations that are cheap; log the rest as day-2 items.

## 4. Dev tooling

Use these MCP servers/tools during the build where available: **Context7** (library docs: LangGraph 1.x, LangChain 1.x, crawl4ai, shadcn), **Postgres MCP** (inspect schema/data), **Playwright MCP** (verify web UI states), **shadcn MCP** (component reference). Superpowers discipline: TDD, git worktrees per phase if useful, code review before merging each phase. Reference project for LangChain/LangGraph patterns (learning only, never import code): `~/Documents/Climb/Profile_Builder/Self-Learning/LangSmith/lca-lc-foundations` (typed AgentState subclasses, Command state updates, Pydantic response_format, InMemorySaver + thread-per-run, MCP server example).

## 5. Guardrails (hard)

1. No TurboTax-specific logic anywhere in code; seed data lives in fixtures/seeds only. Grep-verifiable.
2. The scorecard rule text from doc 05 §1 is VERBATIM data; never paraphrase it in seeds, fixtures, or prompts.
3. No scope beyond PRD §4 / spec §9; anything tempting goes to the day-2 backlog note in `code/CLAUDE.md`.
4. Untriggered rules are N/A, never pass. Evidence quotes must substring-match stored material or the flag becomes needs-review. Draft never shown at portfolio level.
5. Frontend uses only shadcn/ui + shadcn Charts; only lucide icons; DESIGN.md precedence order is binding. DESIGN.md follows the Google Labs design.md spec: its YAML front matter is the normative token source (exportable via `npx -p @google/design.md designmd export --format css-tailwind ../DESIGN.md`); keep it linting clean (`designmd lint`) if you touch it.
6. Tests before implementation for every module with logic; recorded LLM cassettes for deterministic CI; no phase advances with red tests.
7. Confirm with Aarvin before anything irreversible (git push to a remote, deploys, destructive migrations on non-empty data).
8. Keep costs at $0: free-tier models by default; document any paid call before making it routine.
9. Sentence case, no em-dashes in all product copy.
10. **Autonomy dial (07_architecture §7):** decide implementation detail freely and log notable choices in `code/CLAUDE.md`; but surface to Aarvin, with options and a recommendation, before changing any cross-cutting contract (07 §6), the pause/resume mechanic (07 §2), the data model, scoring formulas, phase order, or any guardrail.

## 6. Definition of done

PRD §8 checklist, all nine items, plus: `base-condition-v1` frozen in LangSmith and tagged in git; `code/CLAUDE.md` current; the three eval harness scores recorded in `04_trial_context` (Cowork will log them).
