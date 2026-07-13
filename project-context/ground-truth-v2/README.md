# Ground truth v2 — semantic discovery + 3-LLM judge panel (TurboTax)

Standalone harness, outside the product (like `../trace-analysis/`). Nothing in
`code/apps/` is imported or modified. Ground truth v1 (`../ground-truth/`,
FROZEN, 460 records) is never touched; v2 is additive and, once approved,
**defines the product's direction** (Aarvin, 2026-07-13). v1 remains the
historical baseline.

## Why v2 exists

The v1 certification (97.99%) proved the system replicates the expert on the
54-page corpus it iterated on. What it could not prove: performance on data
the system never practiced on. v2 fixes that by (a) discovering MORE TurboTax
pages semantically (driven by rule meaning, not keywords), (b) judging them
with a panel of independent LLMs instead of a single analyst pass, and
(c) enforcing a train/test split from day one so future system improvements
are measured on records they never iterated against.

Client context: the product is for Intuit; analysts will check any Intuit
product. TurboTax is the ground-truth anchor because the 4-rule scorecard is
TurboTax's. The harness itself is product-agnostic: every TurboTax-specific
input (domains, sitemaps, scorecard path) is config, not code.

## Pipeline (each stage a CLI subcommand, each resumable, all LLM calls cached)

```
discover  sitemap harvest (turbotax.intuit.com + blog) → LLM ranks every URL
          against the MEANING of the 4 rules → data/candidates.json
          (v1's 54 URLs excluded; per-rule quotas guarantee variety)
capture   crawl4ai with the proven v1 config (domcontentloaded + settle,
          raw_markdown) → data/snapshots/V##_*.md + data/manifest.json
          (same front matter + sha256-of-stripped-body convention as v1)
screen    cheap LLM (Haiku) reads each page × 4 rules → relevant / not.
          Not relevant → not_applicable record (judgment_source
          "semantic_screen", honest label). Relevant → judged by the panel.
judge     THREE independent judges per (page, rule):
            A anthropic:claude-sonnet-5   B openai:gpt-5.1   C openai:gpt-5
          Each returns 1..N findings (multi-finding fixes the v1 P02 gap):
          trigger/requirement, two axes, intersection tag, contiguous
          verbatim evidence quote (programmatically validated; one retry;
          still invalid → forced needs_review, never invented), reasoning,
          confidence. Judges see the FULL page text, the verbatim rule, the
          D-01 approved wording, and two worked v1 examples.
consensus findings pooled and grouped by evidence overlap:
            3/3 same verdict → definitive record (judgment_source
                "judge_panel")
            2/3 or 1/3      → ARBITER anthropic:claude-opus-4-8 (4th model,
                strongest tier) sees the page + all judge opinions and makes
                the final call (judgment_source "judge_panel_arbiter";
                rationale recorded). No human in the loop by design;
                legitimacy comes from independence + the recorded provenance.
assemble  data/ground_truth_v2.json — v1-compatible record schema plus
          additive fields: split, panel provenance, evidence_valid.
          Split: sha256(page_id) → 70% train / 30% test, at PAGE level so no
          page straddles the sets. TEST records are the quarantine: system
          improvement work may only iterate on train.
synthetics 100 TurboTax-THEMED fixtures (not fictional brands): a coverage
          matrix of violation modes per rule × pass/fail/na/edge; a generator
          LLM authors each page-like fixture with an INTENDED verdict; the
          same 3-judge panel then validates each one; fixtures where the
          panel disagrees with the intent are quarantined for review, never
          silently kept. Split 70/30 like real pages.
```

## Model roster (env-overridable, see harness/src/gt2/config.py)

| Role | Model | Why |
|---|---|---|
| Judge A | anthropic:claude-sonnet-5 | strong Anthropic tier |
| Judge B | openai:gpt-5.1 | strong OpenAI tier, different provider |
| Judge C | openai:gpt-5 | third independent opinion |
| Arbiter | anthropic:claude-opus-4-8 | strongest tier for final calls only |
| Screen | anthropic:claude-haiku-4-5 | cheap, high-volume relevance pass |

Gemini and Groq deliberately excluded (Aarvin, 2026-07-13). The product's
checker model (Haiku) never issues verdicts here — it only screens relevance —
so the ground truth stays independent of the model it will later grade.

## Record schema

v1 fields unchanged: `id, page_id, rule_id, trigger_met, requirement_met,
axis_a_compliant, axis_b_matches_approval, intersection_tag, severity,
evidence_quote, location, reasoning, verdict_status, judgment_source,
confidence`. New (additive, so the product's data model needs no change):
`split` (train|test), `evidence_valid` (bool), `synthetic` (bool),
`panel` ({judges: [{model, verdict_status, intersection_tag, confidence}],
support, arbiter: {model, rationale} | null}).

Judgment sources: `judge_panel` (3/3), `judge_panel_arbiter` (2/3 or 1/3,
arbiter decided), `semantic_screen` (screened not-relevant → not_applicable),
`synthetic_intended` (fixture, panel-validated).

Page ids are `V01…` (v2 namespace; v1 uses `P01…`). Record ids are
`GT2-<page>-<rule>[-n]`.

## Run

```bash
cd ground-truth-v2/harness
uv sync
uv run gt2 discover            # free (sitemaps) + ~1 ranking call
uv run gt2 capture             # free, local browser, polite crawl
uv run gt2 screen              # ~4 Haiku calls per page
uv run gt2 judge               # 3 calls per relevant (page,rule)
uv run gt2 consensus           # arbiter calls for non-unanimous groups only
uv run gt2 assemble
uv run gt2 synthetics          # generate + panel-validate 100 fixtures
uv run gt2 status              # where things stand
# every stage takes --limit N for pilots
```

Keys are read from `../../code/.env` (ANTHROPIC_API_KEY, OPENAI_API_KEY;
read-only). LangSmith tracing goes to project `shiboleth-gt2` when
LANGSMITH_TRACING is set. Estimated full-run spend: roughly $10–20 paid API
across ~80 new pages + 100 synthetics (judges see full page text; that is the
deliberate cost of judging on complete evidence after v1's iter-6 truncation
lesson).

## Social media (planned, not built)

The record schema already fits: a post becomes a page-like material
(`page_id` = post ref). Capture will differ (Meta blocks scrapers; paste
fallback per the product's M6 pattern); the judging pipeline is reused as-is.

## Status

- [x] Pilot run verified end to end (2026-07-13)
- [x] Full run: 78 pages, 71 panel pairs, 367 records (2026-07-13; two
      mid-run stops: Anthropic monthly cap, then OpenAI quota — resumed
      from cache both times)
- [x] Synthetics: 27 validated, 2 quarantined (Aarvin capped at 27, down
      from 100 → 50 → 27, cost call; remainder can be generated later)
- [ ] Aarvin reviews `REVIEW.md` and approves → v2 becomes the acceptance
      target; test split quarantined for all future system iteration
