# Marketing Compliance Checker — kickoff, scope, and handoff (2026-07-08)

> The complete origin snapshot for this project: the vision, the scoping answers, the locked scope, the honest-broker risk, the proposed MVP, the recommended stack, and the open questions for the next Cowork session. Read this plus `CLAUDE.md` plus `../_cowork_operating_manual.md` before doing anything. This is a hackathon build: one day, 12 to 16 hours, must be demoable and real.

## 1. What it is (the wedge)

A marketing compliance checker for the fintech-and-bank intersection. Banks are heavily regulated, so when a bank partners with a fintech it requires the fintech's marketing material to be compliant with banking marketing standards. This tool lets a fintech (or a bank's partnership team) check the fintech's public marketing and score it against a user-defined, product-specific compliance scorecard, flagging issues with cited evidence and an overall score. Single reviewer. Portfolio-grade demo, free-tier.

## 2. How it works (the vision, articulated)

- Input mediums: a website URL (the tool crawls the site and its linked pages to a customizable, capped depth), plus social media handles. Email is deferred to later.
- The crawled and scraped marketing content is scored against a user-defined scorecard: a set of compliance rules, specific to a product, functioning as a scorecard.
- Output: per-rule verdicts (pass / fail / needs-review) with a cited snippet and a reason, plus an overall compliance score.

## 3. Scoping-form answers (2026-07-08)

- Ruleset: a user-defined ruleset, described as "a scorecard of sorts with a set of rules, specific to a product."
- Content types: social posts, landing pages and web (websites). Website URLs and social handles are the input mediums; email later.
- Posture: portfolio-grade demo, real architecture.
- Users: a single reviewer.
- Interaction: both / not sure (resolved below to a single-screen instant checker for the one-day build).
- Vision (intent, in Aarvin's words): given a website link, crawl the site and its linked pages a customizable number of levels deep to scrape marketing content; also ingest social media handles; email later. Score the scraped content against a user-defined scorecard. A lean prototype, end-to-end deliverable.
- Timeline and context: one day, 12 to 16 hours, for a hackathon. Needs something demoable and real. The wedge is fintech-and-bank: for fintechs to be compliant with their banking partners' marketing standards.

## 4. Locked decisions (2026-07-08)

- 12h scope: **website AND real social** (Aarvin's choice; see the risk note in section 6). Email deferred.
- Scorecard: **seed an editable banking-marketing scorecard** (author a realistic starter set of rules, editable in the UI).
- Interaction shape: **single-screen instant checker** (given one day: no review workflow or queues, no auth, single user).
- Posture: portfolio-grade demo, real architecture, free-tier, cheap-model-first.
- Process: **compressed hackathon mode.** Do NOT run the full plan-then-build cycle (research, Figma, PRD, ADR, lock). Produce a one-page spec, lock the minimal scope, and hand to Claude Code with Superpowers to build immediately.

## 5. Proposed MVP (the one-day slice)

A single screen:
- Enter a website URL and social handles; see and edit the seeded scorecard.
- Crawl the website to a small, capped, adjustable depth; scrape the social handles.
- Extract the marketing text; for each scorecard rule, an LLM returns pass / fail / needs-review with a cited snippet and a one-line reason.
- Roll up into an overall compliance score; show a per-rule results panel with the evidence.

The real wow for the demo: it crawls and scores a genuine live website (and social) in front of the judges.

Recommended stack (finalize in the next session): Next.js + Tailwind + shadcn for the UI; a lightweight crawler (a simple fetch plus readability or cheerio, or a free crawl API such as Firecrawl's free tier for JavaScript-heavy pages); social scraping via whatever is fastest and least fragile per platform; one LLM scoring call behind a small provider-agnostic layer. No Google ADK or LangGraph: a crawl-then-score pipeline does not need a heavy agent framework in a day.

Deferred: email, multi-user and auth, a heavy agent framework, a full eval harness (a couple of test runs suffice), review workflow and queues.

## 6. Honest-broker risk (carry this forward)

Real social-media scraping is an authentication, anti-bot, and terms-of-service rabbit hole that can consume the whole 12 hours. I recommended website-only for the one-day build; Aarvin chose website plus real social, so the risk stands. The next session should: (a) build and stabilize the website path first so there is always a working demo; (b) time-box social hard with a fallback (mock or pasted social content scored through the same pipeline); and (c) re-confirm with Aarvin whether to drop live social if it threatens the deadline. Protect the deliverable.

## 7. Open questions for the next Cowork session

- The exact scorecard rules content (seed a starter set, refine with Aarvin). Candidate rules to propose: accurate deposit-insurance / FDIC disclosure; no misleading "bank" or "FDIC-insured" claims unless accurate and attributed to the partner bank; required APY / APR and fee disclosures; clear-and-conspicuous placement; no unsubstantiated or guaranteed-return claims; partner-bank attribution ("Banking services provided by ..."); UDAAP-style fair-and-not-misleading.
- Which social platforms (LinkedIn, X, Instagram, and so on) and the scraping approach plus fallback per platform.
- Crawl depth default and page cap.
- LLM provider and model (free-tier) and the provider-agnostic call shape.
- The scoring output schema (the rule-verdict enum, the evidence field, and the overall-score formula).
- Hosting and deploy for the demo (Vercel free tier).
- Repo setup: a `code/` repo with a gitignored `code/CLAUDE.md` carrying the build rules (per the operating manual).

## 8. Cross-project context (so this doc is self-contained)

This project lives under `tech-personal-projects/`, which has a shared operating manual (`../_cowork_operating_manual.md`) and a reusable Cowork skills plugin, `cowork-build-crew` (install it in the new Cowork; it loads role skills like spec-architect, solution-architect, compliance-domain-expert, design-partner, ai-engineer, and ai-agent-evaluations on demand). House rules that apply: no em-dashes in written artifacts; plan in Cowork and build in Claude Code with Superpowers (the `obra/Superpowers` plugin: TDD, git worktrees, code review); the preferred design stack is shadcn/ui + Tailwind (Material UI as an alternative), Emil Kowalski motion skills, and the impeccable taste gate; every code file carries a lean meta-snippet header; keep context docs lean and high-signal; confirm before any irreversible action (push, deploy). For a one-day hackathon, apply these lightly: the design stack and Superpowers help you go fast, but skip the heavy planning ceremony.

## 9. Immediate next step for the new session

Given the clock: confirm the seeded scorecard and the social approach with Aarvin, write the one-page spec, then produce the Claude Code build handoff (Superpowers-ready) so Aarvin can paste it and start building. The paste-ready orientation prompt for the new session is in `_HANDOFF_PROMPT_new_cowork_2026-07-08.md`.
