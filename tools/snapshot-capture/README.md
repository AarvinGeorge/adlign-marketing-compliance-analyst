# snapshot-capture

One-shot capture of ground-truth page text for the Shiboleth corpus. Reads the
curated TurboTax page list, fetches each fully rendered page, and writes one
Markdown snapshot per page plus a deterministic manifest.

This is an **isolated data-capture tool**. Its crawl4ai core is the seed of the
product's ingestion service, so extraction parity matters: it uses crawl4ai's
default LLM-ready markdown (`raw_markdown`, **not** `fit_markdown`, which would
prune the disclosures we need).

## Why these snapshots are canonical

These snapshots are the **canonical corpus**. Ground truth (the E2/E3 golden
sets) binds to them **by content hash** (`content_sha256`). The compliance
checker must therefore support **corpus-in (fixture) mode**: it takes stored
snapshots as input so checker evaluation is **extractor-independent**. Live-fetch
parity — whether the production crawler reproduces these bodies from the live
URLs — is a *separate* concern, evaluated by the **E1 retrieval harness**
(`../../../01_spec_v1_2026-07-09.md` §7). Keep the two apart: a checker
regression and a crawler regression are different failures.

## The fine print is the payload

Content is captured **verbatim**. Asterisked disclosures, footnotes,
"% of filers qualify" phrasing, APR figures, FDIC language, and bonus/offer
terms must survive extraction exactly. No summarization, no cleanup beyond the
boilerplate stripping the fetcher does natively.

## Fetcher policy

1. **crawl4ai** — primary. Local Playwright render, $0, the locked production
   crawler. Emits `raw_markdown`.
2. **Hyperbrowser** — fallback #1. Cloud render, only when crawl4ai returns
   thin/blocked/failed content.
3. **Apify Website Content Crawler** — fallback #2, same trigger.

One retry per fetcher; the chain advances only when a result is thin/failed.
Fallback keys come from **this tool's `.env` only** (`HYPERBROWSER_API_KEY`,
`APIFY_TOKEN`) — never the app-level `code/.env`, never hardcoded, never logged.

## Snapshot format

```
---
id: P01
url: https://turbotax.intuit.com/
discovery: free
fetched_at: 2026-07-09T18:00:00Z
fetcher: crawl4ai | hyperbrowser | apify | webfetch
content_sha256: <sha256 of the body text>
quality: good | thin | failed
notes: <one line>
---

<full visible page text, verbatim>
```

`fetcher: webfetch` is a **legacy-only** value: the 14 pre-existing snapshots
were captured with a WebFetch-style tool before this script existed. The
production ingestion service never emits it. It survives only when a legacy
page's crawl4ai refetch **degrades** (comes back thin/failed) — we keep the
verified old body rather than discard it.

> **Final corpus note (2026-07-09):** the corpus is frozen at 54 pages, all
> captured by crawl4ai (`content_sha256` = sha256 of the whitespace-stripped
> body). `fetcher: webfetch` never occurs in the final corpus; it survives in
> this doc only as the historical legacy value. This tool is COMPLETE and
> FROZEN: bugfix-only on explicit request.

### Hash rule (determinism)

`content_sha256` = `sha256(body.strip())` over the body **after** the closing
`---`, UTF-8. New files are written already normalized, so recomputing the hash
from any snapshot on disk is byte-identical. The manifest is rebuilt **from the
files** every run and carries no timestamp, so regeneration is deterministic.

## Quality

- `good` — substantive marketing content.
- `thin` — usable text but < ~150 words, or navigation-only.
- `failed` — every fetcher failed (after one retry each).

Never fabricated. `failed`/`thin` bodies hold whatever text was actually seen.

## Idempotency modes

- **default** (no flag): refetch **all** curated pages with crawl4ai to
  homogenize the corpus on one extractor. If a page that was already `good`
  comes back degraded, the prior body is **kept** (legacy bodies stay
  `webfetch`).
- `--skip-good`: classic idempotent fill — skip existing `good`, (re)fetch
  `thin`/`failed`/missing only.
- `--refetch-all`: force overwrite every page, even when the refetch degrades.
- `--discover`: harvest up to 10 new marketing URLs from the TurboTax search
  results for a fixed term set, append them as `P55+` in `curated_pages.json`,
  then snapshot them too. Best-effort (the search page is JS-heavy).
- `--limit N`: process only the first N pages (debugging).

## Outputs

- `../../../ground-truth/snapshots/<ID>_<slug>.md` — one per page.
- `../../../ground-truth/snapshot_manifest.json` — per page:
  `{id, url, fetcher, quality, word_count, content_sha256,
  triggers:{free, apr_finance, fdic_deposit, bonus_reward}}`.
  Triggers are case-insensitive, word-boundary keyword hits:
  `free` | `APR`/`finance charge` | `FDIC`/`deposit`/`checking`/`savings` |
  `bonus`/`reward`/`referral`.

## Run

```bash
cd code/tools/snapshot-capture
uv sync
uv run crawl4ai-setup          # one-time: installs the Playwright browser
cp .env.example .env           # optional: fill in fallback keys
uv run snapshot-capture        # default homogenize run
```

Politeness: max 2 concurrent fetches, ≥2.5s between request starts, honest
user agent naming the tool and a contact.

## Tests

`uv run python -m pytest` — covers hash/format round-trip, trigger detection,
quality classification, and manifest determinism (the manifest guarantee).
