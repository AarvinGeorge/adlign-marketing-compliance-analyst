# Ground truth v2 — review digest for Aarvin (2026-07-13)

The dataset is DRAFT until you approve. This digest is what you need to make
that call without reading 367 records. Full records:
`data/ground_truth_v2.json` (each carries evidence, reasoning, and complete
panel provenance).

## What the run produced

| | |
|---|---|
| Pages | 78 real TurboTax pages (76 new via semantic discovery + 2 pilot), hash-frozen in `data/snapshots/` |
| Records | 367 total: 340 real-page + 27 synthetic-fixture records |
| Verdicts | 80 flag · 15 pass · 272 not_applicable · 0 needs_review (2 ruled strict by Aarvin 2026-07-13) |
| Split | 249 train / 118 test (page-level, deterministic; test quarantined) |
| Sources | 47 judge_panel (3/3 unanimous) · 52 judge_panel_arbiter · 241 semantic_screen · 27 synthetic_intended |
| Quarantined | 2 fixtures (panel disagreed with generator intent; never silently kept) |
| Judge roster | claude-sonnet-5, gpt-5.1, gpt-5; arbiter claude-opus-4-8 |

## Headline real-page findings (51 flags)

- **R-01 dominates (39 flags):** the free-claim disclosure problem is
  widespread beyond the v1 corpus — blog posts and announcement pages
  mention TurboTax free offers with missing, partial, or drifted
  eligibility disclosures. Includes Spanish-language pages (GT2-V02:
  Absolute Zero announcement, unanimous unapproved_violation — same class
  as v1's GT-P45 finding).
- **R-03 is newly productive (10 flags):** semantic discovery surfaced
  Credit Karma Money / Credit Builder banking content the v1 corpus barely
  covered, incl. "MVB Bank, Member FDIC. Maximum balance and transfer
  limits apply" formulations that do not match the required
  $250,000-through-[Bank] wording (GT2-V03 unapproved_violation).
- **Tag split: 28 unapproved_violation vs 23 drifted_but_compliant** — both
  reconciliation classes are now well represented (v1: 11 vs 47).

## What to eyeball before approving (15 min, not 367 records)

1. ~~The 2 needs_review records~~ **RULED 2026-07-13 (Aarvin, strict):**
   GT2-V44-R-03-2 and GT2-V66-R-03-2 are now `flag` — any page promoting
   the CKM account triggers R-03, and "Member FDIC" without the
   $250,000-through-[Bank] formulation fails it. Ruling recorded in each
   record's reasoning and arbiter provenance.
2. ~~GT2-V51-R-02~~ **RULED 2026-07-13 (compliance-officer call, delegated
   by Aarvin): FLAG KEPT.** R-02 has no editorial carve-out (contrast
   R-04's explicit exemption); a partner-promotion page quoting loan rates
   beside a refinance pitch is comparative rate advertising. Counter-reading
   documented in the record; confidence 0.68 marks it the dataset's softest
   record.
3. ~~The 2 quarantined fixtures~~ **REJECTIONS CONFIRMED 2026-07-13**
   (S020: generator tripped R-04's conditional requirement 4; S026: R-02
   trigger left debatable). Recorded in `quarantine.json`.

## Known limitations (recorded, not hidden)

- The 241 semantic_screen not_applicable records are one-model (Haiku)
  screening judgments, not panel-judged (cost control; same honesty-label
  pattern as v1's screened_policy class).
- Panel disagreement was high: 52 of 99 panel-judged records needed the
  arbiter. Compliance judgment is genuinely ambiguous; the provenance
  makes every arbiter call auditable.
- 27/50 synthetics done (OpenAI quota stop, Aarvin capped at 27); the
  remaining 23 can be generated later with `gt2 synthetics --count 50`.
- Stealth synthetics (violations phrased without trigger keywords): 14 of
  27, of which 9 got unanimous panel support — these are the fixtures that
  will stress the checker's keyword-bound retrieval.

## Approval

- [ ] Approved by Aarvin George on ____ → set `_meta.status` to FROZEN;
      after that, system improvement iterates on train ONLY, test is the
      held-out measurement set.
