# Ground truth: Shiboleth v1 (TurboTax corpus)

Dataset metadata only; the single source of truth is `ground_truth.json` (every record carries its own reasoning).

## What this is

The expert-labeled answer key for the Shiboleth compliance-check endpoint. Corpus: `snapshots/` (54 live TurboTax pages, captured 2026-07-09 via crawl4ai, homogeneous extractor) plus `snapshots-synthetic/` (17 authored fixtures). Every record judges one rule against one page/fixture under the VERBATIM 4-rule scorecard (doc 05 §1) and library entry D-01.

## Binding rules

- Ground truth binds to snapshots by content hash. Hash convention: **sha256 of the whitespace-stripped body** (text after the front matter, `.strip()` applied).
- The endpoint is evaluated **corpus-in** (stored snapshots as input), making checker evaluation extractor-independent. Live-fetch parity is a separate concern (E1 retrieval harness, `01_spec_v1` §7).
- Scoring convention: `needs_review` records are excluded from strict accuracy scoring (per the product's own scoring rule: needs-review is excluded from the denominator); they ARE valid targets for "did the endpoint recognize ambiguity" evaluation.

## Record schema

`id, page_id, rule_id, trigger_met, requirement_met, axis_a_compliant, axis_b_matches_approval (true|false|na), intersection_tag (all_good | drifted_but_compliant | approved_but_non_compliant | unapproved_violation | na), severity, evidence_quote, location, reasoning, verdict_status (pass | flag | not_applicable | needs_review), judgment_source, confidence`

## Judgment sources (honesty labels)

- `analyst` (30): individually judged in the compliance-analyst pass, full reasoning embedded.
- `footer_inherited` (220): the shared footer block (identical fine-print footnotes on 44 of 54 pages) judged once, inherited per page. Includes the footer drift flag (GT-F03) and the two APR passes.
- `screened_policy` (193): deterministic keyword screening only; labeled `not_applicable` (no trigger signal) or `needs_review` (signal present, not individually eyeballed). **Never an invented verdict.** These upgrade to analyst labels over time via dispositions.
- `synthetic_author` (17): authored fixtures, balanced 8 fail / 8 pass / 1 exemption-N/A, covering every rule's violation modes (marked `synthetic: true`).

## Headline real-world findings (see records for reasoning)

1. GT-P18-01: CKM page advertises deposit accounts with "FDIC insurance up to $5M through a network of participating banks" instead of the required $250,000-through-[Bank] formulation (violation candidate); same page passes for Credit Builder (GT-P18-02).
2. GT-F03 (×44 pages): footer eligibility disclosure drifted from D-01 ("Roughly 37% of taxpayers qualify" vs "~37% of filers qualify").
3. GT-P05-01 / GT-P07-01: $0 price-range cards without adjacent eligibility disclosure (placement-violation candidates, confidence 0.7, counter-reading documented).
4. GT-P45-01: Spanish-language disclosure variant with no approved Spanish library entry (drift, language-variant subclass).
5. GT-P08-01 / GT-P10-01: military free-filing offer with no approved library counterpart (unapproved-claim class).
6. GT-F05 / GT-P22-01: the strict-vs-practical reading of R-01 on legal-footnote mentions, deliberately left needs_review for the human policy call.

## Distribution

460 records: 108 pass · 58 flag (47 drifted_but_compliant, 11 unapproved_violation) · 99 not_applicable · 195 needs_review.

## Limitations

- Fetcher renders JS via crawl4ai, but some page content may still be client-gated (P03's hero, noted in its record).
- The analyst is an LLM operating under the compliance-domain-expert role; **this dataset is DRAFT until Aarvin reviews and approves**, at which point it freezes and becomes the acceptance target for the FastAPI endpoint build.
- `_analysis/` is the analyst's working directory (windows, triage, draft) kept for auditability; not part of the dataset contract.

## Approval

- [x] Reviewed and approved by Aarvin George on 2026-07-09 (approved as-is in the Cowork session; no corrections). Status in ground_truth.json: FROZEN. Seeds the E3 checker golden set in LangSmith.
