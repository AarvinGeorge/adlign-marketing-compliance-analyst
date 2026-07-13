# Shibboleth problem context and scorecard (received from Aarvin, 2026-07-09)

> Source material from the trial company, plus Aarvin's framing. The scorecard and its four rules are VERBATIM and must not be paraphrased when seeded into the product. The analysis sections are synthesized. Referenced from `CLAUDE.md`; read alongside `04_trial_context_shiboleth_2026-07-08.md`.

## 1. The scorecard (VERBATIM, seed for Customize)

ScoreCard

1. If Turbotax free is mentioned, the following must be disclosed right underneath ~37% of filers qualify. [Simple Form 1040 returns only](https://turbotax.intuit.com/personal-taxes/online/free-edition.jsp#modals/simple-tax-returns-en) (no schedules, except for EITC, CTC, student loan interest, and Schedule 1-A).
2. If a rate of finance charge was stated, was the finance charge stated as an APR?
3. If the product being advertised is a deposit product, does the FDIC insurance language state Deposit product is FDIC-insured up to $250,000 through  Bank
4. If an institution states a bonus in an advertisement, does the advertisement state clearly and conspicuously the following information, if applicable to the advertised product: (1) "Annual percentage yield," using that term; (2) Time requirement to obtain the bonus; (3) Minimum balance required to obtain the bonus; (4) Minimum balance required to open the account, if it is greater than the minimum balance necessary to obtain the bonus; and (5) Time when the bonus will be provided? In addition, general statements such as "bonus checking" or "get a bonus when you open a checking account" do not trigger the bonus disclosures.

## 2. The demo use case (near-verbatim)

Focus: TurboTax Free. Caveat from the source: even if no true positive appears, insights into how results would be shown is helpful.

What to look for: mention of TurboTax Free with the disclosure "~37% of filers qualify. Simple Form 1040 returns only (no schedules, except for EITC, CTC, student loan interest, and Schedule 1-A)."

Scope:
- Website: https://turbotax.intuit.com/ (capability to search all links attached to this domain)
- Email: 2 samples as .eml files — **DECISION 2026-07-09: email is completely OUT of scope for now (Aarvin), despite appearing in the company demo narrative. No .eml handling in any version until Aarvin reopens it.**
- Social: Facebook facebook.com/turbotax, Instagram instagram.com/turbotax; posts any timeframe, most relevant around February to March

Demo narrative from the source: crawl website + Facebook/Instagram (+ email) to pull all marketing material; walk through the disclosure and substantiation library (the ~37% language, substantiated claims); every material reviewed against the rules AND the library; two highlighted capabilities: findings clustered by similar wording (batch review incl. false positives) and reconciliation of pre-approved material vs what's published (unapproved or drifted).

## 3. The monitoring problem statement (synthesized from the source)

**Root cause:** in pre-approval testing the population is GIVEN (run rules on 30 items, get 30 results). In monitoring the population is DISCOVERED: you don't know what exists until you crawl, and the count changes between runs. Everything else follows.

**Four consequences, mapped to Shiboleth:**

| # | Consequence | What it means | Where it lives in Shiboleth | Status |
|---|---|---|---|---|
| 1 | Coverage becomes a finding | "Did we see everything?" is itself a compliance question. Some findings have NO material to attach (e.g., a disclosure page that disappeared between runs) | Coverage hero metric exists. NEW: a "Missing/Gone" finding type + run-over-run population diff | LOCKED 2026-07-09: model day 1, UI day 2 (04 §6e) |
| 2 | The unit of review inverts | 60 pages failing from one template edit is ONE decision. Cluster = the issue; materials = line items; bulk disposition with individual exclusions = the core interaction | Clusters + bulk actions + per-item dismiss already core. Confirmed as THE core interaction | Covered |
| 3 | The verdict splits in two | "Is it compliant" and "is it what we approved" are independent axes. Off-diagonals are the interesting cells: compliant-but-drifted (process failure) and matches-approval-but-non-compliant (the approval process itself was wrong; monitoring audits pre-approval) | We have both axes (Fail vs Drift/Unapproved) but not as an explicit 2x2 per material; matches-approval-but-non-compliant implies checking rules against library entries themselves | LOCKED 2026-07-09: two-axis model day 1 with named intersection, three tags per material; library audit day 2 if time (04 §6e) |
| 4 | Lifecycle is remediation, not adjudication | A failing page is still live. Incident loop: detect → confirm → fix → verify → close, not approve/reject | Our lifecycle: open → confirmed → assigned → resolved. Missing: verify-the-fix (re-check) before close | LOCKED 2026-07-09: states day 1 (… → fix pending verification → closed), auto-verify day 2 (04 §6e) |

**What stays the same (transfers untouched, on clusters instead of accounts):** the human judgment layer — agree/disagree with AI (disposition), FP/FN tracking (dismissals = FP labels; FN needs the eval golden set), audit trail, entity-vs-rule pivot. Same review engine, different population engine.

**Other named hard problems:** one campaign appears in many places (dedup before clustering); did content change wording only, or layout/disclosures/offer terms (change classification); disclosures can be hard to map to the content they qualify (the attribution problem — R-01's "right underneath" is an attribution rule; evidence criteria must carry positional semantics).

## 4. How this helps us (analysis)

- It confirms the two differentiators (clustering, reconciliation) are what the company itself sells, and elevates bulk-disposition-with-exclusions to the single most important interaction in the product.
- It gives us the demo's intellectual spine: "same review engine, different population engine" is the sentence that frames the whole day-3 narrative.
- It hands us a scoring/verdict model refinement (the 2x2) and two lifecycle refinements (coverage findings, verify-before-close) that we can adopt cheaply at the data-model level even if their full UI is day 2+.
- It re-opens one scoping conflict to resolve explicitly: the company's demo flow includes email; Aarvin deferred email.
