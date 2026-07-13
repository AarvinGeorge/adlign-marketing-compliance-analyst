# 09 — MVP1 knowledge base (2026-07-10)

> The complete, QA-verified picture of the Shiboleth MVP1 build, written for two uses: Aarvin's own understanding, and answering stakeholder questions at the demo. Every claim below is tagged: **[disk]** = Cowork verified directly in the repository; **[commit]** = verified in commit history / code/CLAUDE.md gate evidence; **[reported]** = Claude Code's account, plausible and consistent, not independently re-run (e.g. LangSmith dashboards, spend, live DB rows on Aarvin's machine).

## 1. The product in one sentence

An analyst enters a product's marketing properties; the system checks every material against the customer-defined scorecard; and the flags on screen **provably** match an expert answer key, down to a highlighted verbatim quote. "Provably" is the differentiator: the entire build exists to make AI compliance flags *verifiably correct*, not plausible-looking.

## 2. Where the build stands (gates)

| Gate | Status | Receipts |
|---|---|---|
| M0 skeleton (FastAPI + Next.js/shadcn + Postgres + traced LLM smoke) | DONE, approved | commits `baac46a`,`09053f3` [disk] |
| M1 domain + seeds (13 tables, scoring math, byte-for-byte scorecard, hash-verified corpus loader) | DONE, approved | `6d6a62a`; verbatim canary test [disk] |
| M2 checker beats 17/17 synthetics incl. S17 exemption; evidence 100% valid; deterministic cassette CI | DONE, approved | `f6c029b`; S17 test asserts vs frozen GT [disk] |
| M3 certification vs ground truth: **96.23% strict (n=199, bar 90), footer class 100%, synthetics 17/17, evidence validity 100%** | DONE, pending Aarvin's formal approval | `f0b63bf`; phase table + decision log [disk]; LangSmith experiments [reported] |
| M4 API (disposition + lifecycle + recompute, product payloads, SSE replay) | Built + tested, gate not yet declared (correct discipline) | routes on disk [disk]; `f51ade6`,`bbc20ae` |
| M5 four screens (Lane B worktree, integrator-reviewed) | Built on fixtures, gate deferred to integration | branch `lane-b/m5-frontend`, incl. the caught-and-fixed verbatim violation `e8f5b6b` [disk] |
| M6 live mode, M7 audit + `mvp1-base-condition` tag | Remaining | |

## 3. The methodology (the story that sells)

1. **The answer key preceded the product.** 54 real TurboTax pages captured and content-hash-frozen; 460 expert judgments (verdict + evidence + reasoning) approved and frozen BEFORE the first feature was built. The exam existed before the student. [disk]
2. **Correctness earned inward-out through gates.** Synthetics before real pages; stored corpus before live crawling; no gate advances on red tests; every gate's evidence recorded and QA-verified by a second agent (Cowork) against the repo before Aarvin approves. [disk]
3. **Tests before code; claims never trusted.** TDD caught real bugs pre-ship: a startup log about to print the DB password, API keys loaded but never propagated to the LLM library, a fixture-mangling test helper. [commit]

## 4. The M3 certification story (the demo's technical heart)

The iterate-until-match loop, every iteration a named LangSmith experiment:

- **Iter-6, 73.1%.** One root cause amplified 44×: token-saving excerpt windows truncated the shared footer before its drifted disclosure, so the checker failed on text it never received. Fix: retrieval anchors derived from the approved library wording (distinctive tokens like "1040", "1-A") guaranteeing disclosure passages survive the cut. Plus evidence-aware matching for pages carrying two judgments on one rule (P18: fail and pass on the same page). [commit]
- **Iter-7/8, 84.9%.** The checker judged the drift correctly but "quoted" it by stitching sentences from two paragraphs; the programmatic validator refused the stitched quote. The validator was NOT loosened; the checker's quoting discipline was tightened. The standard never bent. [commit]
- **Iter-9, 96.23%. Passed.** Footer class 100%, synthetics 17/17, every quote genuine. [disk: gate commit + phase table]

**Key insight for stakeholders:** across all iterations, the model's *judgment* was rarely wrong; the *scaffolding* (what text it sees, how quotes are validated and matched) was. That's why evals matter more than model choice.

**The 8 residual disagreements (3.77%)** are documented, not tuned away: five are the strict-vs-practical R-01 placement question the ground truth itself deliberately marked as a human policy call (GT-F05 class). They await Aarvin's ruling. Reporting disagreement honestly instead of grinding it to zero is a feature of the method. [disk: decision log]

**Certified run persisted:** 138 per-page flags (the 44-page footer drift materialized per page then clustered into ONE reviewable group: the product's signature batch-triage move), 9 clusters, 197 audit events. [commit; DB rows [reported]]

## 5. Engineering decisions and infrastructure truths

- **Model journey (all committed, all reversible via env):** spec's gemini-2.5-flash → dead for new keys (404) → gemini-3.5-flash pinned → Groq llama-3.3-70b primary for speed/quota (Aarvin) → check stage on **anthropic:claude-haiku-4-5, PAID, Aarvin-approved** after Groq's hidden 100k tokens/day cap surfaced *in the LangSmith traces* (Aarvin spotted it there himself). Extract/report stages remain on free tiers. Total certification spend ≈ $3. [disk: config comments; spend [reported]]
- **Telemetry first, theories second** is now written into the code (retries log loudly, never sleep silently) after quota exhaustion masqueraded as a hang. [commit]
- **Retrieval windowing is production code** (`services/ingestion/windows.py`), used identically in corpus and live modes per Aarvin's binding condition, header-documented. Keyword-recall limitation logged; pgvector semantic retrieval is the day-2 upgrade. [disk]
- **Product-agnosticism is a tested property, not a claim:** grep-verifiable zero TurboTax logic in code (TurboTax exists only as seed rows); synthetics deliberately use fictional brands (TaxCo, NeoBank), and M2 initially failed 15/17 precisely because a TurboTax assumption had leaked into the R-01 trigger decomposition; fixing it made the checker brand-agnostic, proven 17/17 in CI ever since. [disk]
- **One logged mid-M3 seed change:** R-02's trigger decomposition was broadened to match ground truth (`289931d`); decomposition is runtime data, the change is committed and visible. [disk]
- **Orchestration reality (say it accurately):** the pipeline is plain async Python with DB-as-checkpoint, exactly per the pinned 07 §2 decision; there is ONE LLM agent (the checker: LangChain `init_chat_model` + structured output, caged by a programmatic evidence validator and code-owned reconciliation), plus an LLM cluster-labeler. LangGraph is installed but unused: its state machinery was redundant for a linear checkpointed pipeline and returns with the interactive Customize-studio flows. Demo phrasing: "a LangChain structured-output agent harness inside graph-style deterministic orchestration with database checkpointing." Do NOT claim "built on LangGraph." [disk: zero langgraph imports in src] Clustering v1 is normalized-identical wording with an LLM labeler; pgvector similarity is the day-2 upgrade (embedding free tiers were unavailable at $0). [disk]

## 6. Stakeholder Q&A (anticipated, with answers)

**"Is this a TurboTax product?"** No. TurboTax is three seed rows (one product, three properties) plus a scorecard that is runtime data. Point it at another fintech: new rows, new scorecard, zero code changes. CI proves the checker on fictional brands daily.

**"Why TurboTax first, then?"** (1) It's the case you specified, tied to the real FTC "~37% qualify" story. (2) Correctness can only be *proven* against a specific answer key, and one deep case beats five shallow ones; generality is guaranteed by architecture, correctness proven on the measurable case. (3) It's genuinely hard: free-claims, APR language, FDIC via Credit Karma, bonuses, a 44-page shared footer, Spanish variants, which stress-tested every general mechanism. (4) It becomes the permanent regression baseline (`mvp1-base-condition`).

**"How do you know the flags are right?"** Frozen expert answer key (460 records) created before the build; the system currently agrees 96.23% strictly, with 100% evidence validity (every quote programmatically verified to exist in the material); improvement arc receipted in LangSmith (73→85→96); residual disagreements reported to the human, never tuned away silently.

**"What happens when the AI is wrong?"** That's designed in: every flag carries a Confirm/Dismiss disposition; a dismissal with note is a labeled false positive that feeds the eval set automatically; the verified score recomputes; the draft score and verified score are shown separately, because only the human-verified number is defensible.

**"What if I add our Instagram/Facebook handles today?"** The system already expects them: seeded as properties, chips render in the modal, the checker is channel-indifferent by design (it judges stored text), cross-channel clustering is native. The honest gap: live fetching is M6, Meta blocks scrapers as the normal case, so the designed path is a hard time-boxed attempt, then an awaiting_input state with per-property Paste/Skip that survives restarts. Caveat owed: the answer key contains zero real captions, so social verdicts are certified-on-web-copy until dispositions accumulate; hashtag-dense captions are a different text distribution: decent but unproven accuracy expected initially.

**"What did this cost to certify?"** About $3 of paid LLM calls (check stage on Haiku); everything else free-tier. A full certification run is ~233 checker calls kept cheap by rule-relevant retrieval (~10× token cut) and judge-once footer inheritance.

**"Why LangSmith?"** Three earned reasons: debugging on facts (the Groq daily-cap truth sat in the traces while theories chased ghosts); iterations as named comparable experiments (the 73→96 arc has receipts, per-record); and per-flag lineage to the exact model call, which for a compliance audience is itself a product feature.

**"What's left?"** M4/M5 gate declarations (built, integrating), M6 live crawl with the paste fallback, M7 UI audit + full acceptance + freeze as `mvp1-base-condition`. Day-2 backlog (untouched, fenced): screenshots with region highlights, Customize studio + E2 evals, Missing-flag UI, insights, daily cron, auto-verify closure, MCP server, semantic retrieval, multimodal.

## 7. Honest limitations (say them before they're asked)

Social/caption accuracy unproven until real dispositions accumulate; the 195 screened-policy ground-truth records are honesty-labeled needs_review (excluded from strict scoring), upgraded over time by dispositions; keyword-anchored retrieval can miss violations phrased without trigger terms (parity with how ground truth was screened; pgvector is the upgrade); P03's hero was client-gated at capture (recorded in its ground-truth record); the demo's persisted-run numbers (138/9/197) are commit-evidenced, live DB rows sit on the demo machine.

## 8. Glossary (for quick answers)

**Ground truth / answer key**: the frozen 460-record expert dataset. **Corpus mode vs live mode**: run on stored hash-verified snapshots (provable) vs real crawling (demo). **E1/E2/E3**: retrieval / decomposition / checker eval harnesses; E3 is the acceptance instrument; E2 returns with the Customize studio. **Trigger/requirement**: each rule decomposed into "does this rule apply?" then "is the requirement satisfied?"; untriggered = N/A, never pass. **Three-tag verdict**: compliant? × matches-approval? × the named intersection (all good / drifted but compliant / approved but non-compliant / unapproved violation). **Disposition**: the human confirm/dismiss(+assign) that converts draft score to verified score and feeds evals. **Base condition**: the frozen first-certified run every future change is measured against.
