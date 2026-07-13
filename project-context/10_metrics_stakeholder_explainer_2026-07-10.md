# 10 — Metrics stakeholder explainer (2026-07-10)

> Demo crib sheet: every UI metric with its formula, the formula's parts, and plain-language talking points. Formulas match `01_spec_v1` §5/§10 and the implemented, unit-tested scoring functions. Product-level cards use identical formulas scoped to one product.

## 1. Verified portfolio score

**Formula:** `score = 100 × weighted_passes ÷ (weighted_passes + weighted_fails)`; portfolio = weighted average over products with runs.
**Parts:** weight = rule severity (High 3, Medium 2, Low 1) · passes = checks judged compliant · fails = standing violations · excluded = N/A (rule never applied) and needs-review (unresolved) · draft = before human rulings, verified = after.

- One risk-weighted number: "how safe is our marketing right now?"
- Serious rules count triple, so the score moves the way regulatory concern moves, not like a flat percentage.
- Only definitive results count: no free credit for rules that never applied, no guessing on unclear cases.
- Draft vs verified split is accountability: only the human-verified number is defensible to a bank partner, and only dismissals (human: "false alarm") can raise it.
- Trend = one dot per real scan (`runs.scores`); nothing interpolated or fabricated.

## 2. Open violations

**Formula:** `count(violation flags in states open/confirmed/assigned/fix-pending)`, severity split, `oldest age = now − found_at`.
**Parts:** open = any state before verified closure · severity split = how many High · aging clock starts at detection, stops at verified closure only.

- "What's exposed right now, and for how long?"
- A to-do list, not a grade: each unit is one real problem currently live.
- The age is the accountability clock: High open 6 days vs 2 hours are different conversations.
- Drops only on actual verified fixes, never on promises.

## 3. Awaiting triage

**Formula:** `count(flags with no human ruling)` + `median time-to-disposition = median(ruling_time − detection_time)`.
**Parts:** awaiting = AI has spoken, human hasn't · median (not mean) resists outliers.

- "Is the review queue under control, or is the analyst drowning?"
- Measures the human half of the loop; value exists only after a person rules.
- Rising median = early warning: understaffed team or too-noisy scorecard, both fixable.
- The #1 validated analyst pain (volume/overwhelm) made visible and manageable.

## 4. Coverage (24h)

**Formula:** `100 × materials_checked_last_24h ÷ total_tracked_materials`, plus the true asset count.
**Parts:** material = one page or post · checked = ran through the checker · tracked = full inventory (crawled + pasted).

- The audit question: "can we attest to what's live right now?"
- In monitoring the population is discovered, not given; coverage = how much of the known world was recently examined.
- 100% coverage with violations beats 60% coverage with none: you can't fix what you haven't seen.
- "Falling through the cracks" quantified: the crack is 100 minus this number.

## 5. Caught: unapproved + drift

**Formula:** `count(tag = unapproved_violation) + count(tag = drifted_but_compliant)` within the stated real window.
**Parts:** drift = published text differs from approved library wording (deterministic string comparison, no AI opinion) · unapproved = claim with no approved counterpart · window labeled honestly ("this run" until a week of history exists).

- The process-integrity alarm: "is anything shipping around our approval process?"
- Drift catches quiet edits after sign-off; even when still compliant, the process broke.
- Unapproved catches bypass: claims that never saw approval at all.
- These two are exactly how content escapes governance, and the reconciliation story this product category is sold on.

## One-line answers for hard follow-ups

- "Why not a simple percentage?" — Because ten trivial passes shouldn't hide one serious FDIC failure; severity weighting matches how risk actually works.
- "Why are some checks excluded?" — N/A would be free credit for compliance never demonstrated; needs-review would be guessing. Both dishonest.
- "Can the AI improve its own score?" — No. Only a human dismissal raises the verified score. The system cannot grade itself up.
- "Where do these numbers come from?" — Every one traces to a database query you could run yourself; happy to show any of them.
