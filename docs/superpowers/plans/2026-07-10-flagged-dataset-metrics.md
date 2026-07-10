# Flagged-Dataset Metrics + Placeholder Elimination Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Serve real flag-analytics (by rule, property, verdict tag, disposition) on GET /products/{id}, add GET /rules and GET /flags/{id} provenance, and remove every remaining placeholder display value in the web app.

**Architecture:** Server computes everything (route does SQL, pure function formats — the existing hero-KPI pattern); the frontend only renders. GET /rules becomes the single severity/rule-text source, deleting both hardcoded severity maps and fixtures.ts data. Flag provenance comes from persisted `events` rows, never synthesized.

**Tech Stack:** FastAPI + SQLAlchemy 2 (async) + pytest; Next.js 15 + TanStack Query + shadcn/ui; Playwright.

**Spec:** `docs/superpowers/specs/2026-07-10-flagged-dataset-metrics-design.md`

**Conventions (binding):**
- Work happens in `code/` (its own git repo). Never push without Aarvin's confirmation.
- Every code file carries a meta-snippet header; update it in the same commit as any change.
- Integration tests need `make db-up` first and skip when Postgres is down (existing pattern).
- Run pytest UNPIPED (piping through tail masks exit codes — M2 postmortem).
- Product copy: sentence case, no em-dashes.
- Rule ids derive from check ids via `check_id.rsplit("-", 1)[0]` ("R-01-REQ" -> "R-01"), the existing convention.

---

### Task 0: Commit the in-flight preview work separately

The working tree contains an uncommitted, complete flag-preview feature (own spec: `docs/superpowers/specs/2026-07-10-flag-preview-design.md`). It shares files with this plan (`api.ts`, `data.ts`, `fixtures.ts`, flag detail page, `products.py`, `main.py`). Commit it first so this plan's commits stay clean.

- [ ] **Step 1: Verify the preview work is green before committing it**

Run (from `code/`): `make db-up && cd apps/api && uv run pytest -q`
Expected: all tests pass (suite was 124+ at last delivery).
Run: `cd ../web && npm run build && npm run lint`
Expected: build + lint green.
If anything is red, STOP and surface to Aarvin — do not commit red work.

- [ ] **Step 2: Commit exactly the preview files**

```bash
cd code
git add docs/superpowers/specs/2026-07-10-flag-preview-design.md \
  apps/api/src/shiboleth/api/routes/preview.py \
  apps/api/src/shiboleth/services/preview.py \
  apps/api/src/shiboleth/api/static/ \
  apps/api/src/shiboleth/api/routes/products.py \
  apps/api/src/shiboleth/main.py \
  apps/api/tests/integration/test_api_disposition.py \
  "apps/web/src/app/products/[id]/flags/[flagId]/page.tsx" \
  apps/web/src/components/surfaces/evidence-panel.tsx \
  apps/web/src/lib/api.ts apps/web/src/lib/data.ts apps/web/src/lib/fixtures.ts
git commit -m "feat: flag source preview (in-flight work committed before analytics build)"
git status --short
```

Expected: `git status --short` prints nothing (clean tree).

---

### Task 1: `flag_analytics` pure function

**Files:**
- Create: `apps/api/src/shiboleth/services/scoring/analytics.py`
- Test: `apps/api/tests/unit/test_analytics.py`

- [ ] **Step 1: Write the failing tests**

Create `apps/api/tests/unit/test_analytics.py`:

```python
"""
meta:
  purpose: Unit tests (first) for the flag_analytics pure function behind the
           GET /products/{id} analytics block (spec 2026-07-10). Math only,
           no DB: honest zeros for seeded rules/properties, confirmed-family
           lifecycle states, fp_rate null until a disposition exists.
  contract: counts by rule/property/tag/disposition match the spec shapes and
            orderings exactly.
  deps: pytest.
"""

from shiboleth.services.scoring.analytics import flag_analytics

RULES = [
    {"id": "R-01", "severity": "High", "position": 1},
    {"id": "R-02", "severity": "High", "position": 2},
    {"id": "R-03", "severity": "Medium", "position": 3},
    {"id": "R-04", "severity": "Medium", "position": 4},
]
PROPERTIES = [
    {"id": "tt-website", "kind": "website"},
    {"id": "tt-instagram", "kind": "instagram"},
]


def _flag(check_id, state, tag, property_id="tt-website"):
    return {"check_id": check_id, "state": state,
            "intersection_tag": tag, "property_id": property_id}


def test_by_rule_counts_and_order():
    flags = [
        _flag("R-01-REQ", "open", "unapproved_violation"),
        _flag("R-01-REQ", "dismissed", "unapproved_violation"),
        _flag("R-01-REQ", "assigned", "unapproved_violation"),
        _flag("R-03-REQ", "open", "drifted_but_compliant"),
    ]
    a = flag_analytics(flags, RULES, PROPERTIES)
    assert [r["rule_id"] for r in a["by_rule"]] == ["R-01", "R-02", "R-03", "R-04"]
    r01 = a["by_rule"][0]
    # open = not dismissed/closed; assigned still open exposure
    assert r01 == {"rule_id": "R-01", "severity": "High",
                   "open": 2, "confirmed": 1, "dismissed": 1, "total": 3}
    r02 = a["by_rule"][1]  # honest zeros for a rule with no flags
    assert r02 == {"rule_id": "R-02", "severity": "High",
                   "open": 0, "confirmed": 0, "dismissed": 0, "total": 0}


def test_confirmed_family_includes_post_confirm_states():
    flags = [
        _flag("R-01-REQ", "confirmed", "unapproved_violation"),
        _flag("R-01-REQ", "assigned", "unapproved_violation"),
        _flag("R-01-REQ", "fix_pending_verification", "unapproved_violation"),
        _flag("R-01-REQ", "closed", "unapproved_violation"),
    ]
    a = flag_analytics(flags, RULES, PROPERTIES)
    assert a["by_rule"][0]["confirmed"] == 4
    # closed is resolved, not open exposure
    assert a["by_rule"][0]["open"] == 3


def test_by_property_counts_with_honest_zeros():
    flags = [
        _flag("R-01-REQ", "open", "unapproved_violation", "tt-website"),
        _flag("R-01-REQ", "dismissed", "unapproved_violation", "tt-website"),
    ]
    a = flag_analytics(flags, RULES, PROPERTIES)
    assert a["by_property"] == [
        {"property_id": "tt-website", "kind": "website", "open": 1, "total": 2},
        {"property_id": "tt-instagram", "kind": "instagram", "open": 0, "total": 0},
    ]


def test_by_tag_ordered_worst_first():
    flags = [
        _flag("R-01-REQ", "open", "drifted_but_compliant"),
        _flag("R-01-REQ", "open", "unapproved_violation"),
        _flag("R-02-REQ", "open", "unapproved_violation"),
    ]
    a = flag_analytics(flags, RULES, PROPERTIES)
    assert a["by_tag"] == [
        {"tag": "unapproved_violation", "count": 2},
        {"tag": "approved_but_non_compliant", "count": 0},
        {"tag": "drifted_but_compliant", "count": 1},
    ]


def test_disposition_fp_rate_and_null_until_dispositioned():
    none_yet = flag_analytics(
        [_flag("R-01-REQ", "open", "unapproved_violation")], RULES, PROPERTIES)
    assert none_yet["disposition"] == {
        "pending": 1, "confirmed": 0, "dismissed": 0, "fp_rate": None}

    some = flag_analytics([
        _flag("R-01-REQ", "open", "unapproved_violation"),
        _flag("R-01-REQ", "confirmed", "unapproved_violation"),
        _flag("R-01-REQ", "assigned", "unapproved_violation"),
        _flag("R-01-REQ", "dismissed", "unapproved_violation"),
    ], RULES, PROPERTIES)
    # fp_rate = dismissed / (dismissed + confirmed-family) = 1/3
    assert some["disposition"] == {
        "pending": 1, "confirmed": 2, "dismissed": 1, "fp_rate": 0.33}


def test_empty_flags_gives_all_zero_rows():
    a = flag_analytics([], RULES, PROPERTIES)
    assert len(a["by_rule"]) == 4
    assert all(r["total"] == 0 for r in a["by_rule"])
    assert a["disposition"]["fp_rate"] is None


def test_unknown_property_flag_still_counts_in_rule_and_tag():
    # a flag whose material/property was deleted must not crash or vanish
    flags = [_flag("R-01-REQ", "open", "unapproved_violation", None)]
    a = flag_analytics(flags, RULES, PROPERTIES)
    assert a["by_rule"][0]["total"] == 1
    assert sum(p["total"] for p in a["by_property"]) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd apps/api && uv run pytest tests/unit/test_analytics.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'shiboleth.services.scoring.analytics'`

- [ ] **Step 3: Write the implementation**

Create `apps/api/src/shiboleth/services/scoring/analytics.py`:

```python
"""
meta:
  purpose: Pure flag-analytics math behind the GET /products/{id} analytics
           block (spec 2026-07-10-flagged-dataset-metrics-design). Breakdowns
           of one run's flags by rule, property, verdict tag, and disposition
           outcome. Honest zeros for seeded rules / tracked properties;
           fp_rate null until at least one disposition exists.
  contract: flag_analytics(flag_rows, rules, properties) -> dict. flag_rows:
            {check_id, state, intersection_tag, property_id|None}. rules:
            {id, severity, position} (any order). properties: {id, kind}.
            No DB, no I/O — the route does the SQL and calls this.
  deps: stdlib only.
"""

from __future__ import annotations

# Lifecycle families (formulas.ALLOWED_TRANSITIONS is the transition source;
# these are the reporting buckets over those states).
RESOLVED_STATES = frozenset({"dismissed", "closed"})
CONFIRMED_FAMILY = frozenset(
    {"confirmed", "assigned", "fix_pending_verification", "closed"}
)

# Worst-first display order (mirrors the web TAG_RANK).
TAG_ORDER = (
    "unapproved_violation",
    "approved_but_non_compliant",
    "drifted_but_compliant",
)


def _rule_id(check_id: str) -> str:
    return check_id.rsplit("-", 1)[0]


def flag_analytics(
    flag_rows: list[dict], rules: list[dict], properties: list[dict]
) -> dict:
    by_rule = []
    for rule in sorted(rules, key=lambda r: r["position"]):
        mine = [f for f in flag_rows if _rule_id(f["check_id"]) == rule["id"]]
        by_rule.append({
            "rule_id": rule["id"],
            "severity": rule["severity"],
            "open": sum(1 for f in mine if f["state"] not in RESOLVED_STATES),
            "confirmed": sum(1 for f in mine if f["state"] in CONFIRMED_FAMILY),
            "dismissed": sum(1 for f in mine if f["state"] == "dismissed"),
            "total": len(mine),
        })

    by_property = []
    for prop in sorted(properties, key=lambda p: p["id"]):
        mine = [f for f in flag_rows if f.get("property_id") == prop["id"]]
        by_property.append({
            "property_id": prop["id"],
            "kind": prop["kind"],
            "open": sum(1 for f in mine if f["state"] not in RESOLVED_STATES),
            "total": len(mine),
        })

    by_tag = [
        {"tag": tag,
         "count": sum(1 for f in flag_rows if f["intersection_tag"] == tag)}
        for tag in TAG_ORDER
    ]

    confirmed = sum(1 for f in flag_rows if f["state"] in CONFIRMED_FAMILY)
    dismissed = sum(1 for f in flag_rows if f["state"] == "dismissed")
    pending = sum(1 for f in flag_rows if f["state"] == "open")
    dispositioned = confirmed + dismissed
    fp_rate = round(dismissed / dispositioned, 2) if dispositioned else None

    return {
        "by_rule": by_rule,
        "by_property": by_property,
        "by_tag": by_tag,
        "disposition": {"pending": pending, "confirmed": confirmed,
                        "dismissed": dismissed, "fp_rate": fp_rate},
    }
```

Note `test_by_property_counts_with_honest_zeros` expects property order `tt-website` before `tt-instagram`: sorted by id gives `tt-instagram` first, which FAILS the test as written. This is intentional TDD friction — fix the ordering to match the spec ("by_property by property id"): update the TEST to expect id order (`tt-instagram` first). The spec's ordering wins over the sample's readability. Adjust the test in the same commit and note it.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd apps/api && uv run pytest tests/unit/test_analytics.py -v`
Expected: all PASS (after aligning the ordering expectation to id order).

- [ ] **Step 5: Lint and commit**

```bash
cd apps/api && uv run ruff check src tests
cd ../.. && git add apps/api/src/shiboleth/services/scoring/analytics.py \
  apps/api/tests/unit/test_analytics.py
git commit -m "feat: flag_analytics pure function (by rule/property/tag/disposition)"
```

---

### Task 2: GET /rules endpoint

**Files:**
- Create: `apps/api/src/shiboleth/api/routes/rules.py`
- Modify: `apps/api/src/shiboleth/main.py` (mount router, lines 70-80)
- Test: `apps/api/tests/integration/test_api_rules.py`

- [ ] **Step 1: Write the failing test**

Create `apps/api/tests/integration/test_api_rules.py`:

```python
"""
meta:
  purpose: GET /rules serves the seeded scorecard rules byte-for-byte from
           Postgres (single severity + rule-text source for web and API).
           Verbatim check reuses the doc 05 §1 pin the seed tests establish
           (R-03 double-space canary).
  contract: needs docker Postgres; ordered by position; exact field set.
  deps: pytest, httpx, seeded_session fixture from test_seed_db.
"""

import pytest

from shiboleth.db.seed_rules import RULES
from tests.integration.test_api_metrics import make_client
from tests.integration.test_seed_db import _postgres_available, seeded_session  # noqa: F401

pytestmark = pytest.mark.skipif(
    not _postgres_available(), reason="docker Postgres not running (make db-up)"
)


async def test_rules_served_verbatim_in_position_order(seeded_session):  # noqa: F811
    app, client, engine = await make_client(seeded_session)
    async with client:
        rows = (await client.get("/rules")).json()
    await engine.dispose()

    assert [r["id"] for r in rows] == [rid for rid, _t, _s, _p in RULES]
    for row, (rule_id, verbatim_text, severity, position) in zip(rows, RULES):
        assert row == {"id": rule_id, "verbatim_text": verbatim_text,
                       "severity": severity, "position": position}
    # canary: R-03's double space survived the trip
    r03 = next(r for r in rows if r["id"] == "R-03")
    assert "through  Bank" in r03["verbatim_text"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/api && uv run pytest tests/integration/test_api_rules.py -v`
Expected: FAIL with 404 (route not mounted).

- [ ] **Step 3: Write the route and mount it**

Create `apps/api/src/shiboleth/api/routes/rules.py`:

```python
"""
meta:
  purpose: GET /rules — the seeded scorecard rules from Postgres, ordered by
           position. The SINGLE source of rule text + severity for the web
           app and any API-side severity lookups (spec 2026-07-10; replaces
           the hardcoded SEVERITY_BY_RULE maps and the fixtures.ts rule text).
  contract: GET /rules -> [{id, verbatim_text, severity, position}].
  deps: db models only.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from sqlalchemy import select

from shiboleth.db.models import Rule

router = APIRouter()


@router.get("/rules")
async def list_rules(request: Request) -> list[dict]:
    async with request.app.state.session_factory() as session:
        rows = (await session.execute(
            select(Rule).order_by(Rule.position)
        )).scalars().all()
        return [{"id": r.id, "verbatim_text": r.verbatim_text,
                 "severity": r.severity, "position": r.position} for r in rows]
```

In `apps/api/src/shiboleth/main.py`, extend the router block (currently lines 70-80):

```python
    from shiboleth.api.routes.rules import router as rules_router
```

and after the existing `include_router` calls:

```python
    app.include_router(rules_router)
```

Also add `rules` to the meta header's route list in main.py in the same commit.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/api && uv run pytest tests/integration/test_api_rules.py -v`
Expected: PASS.

- [ ] **Step 5: Lint and commit**

```bash
cd apps/api && uv run ruff check src tests
cd ../.. && git add apps/api/src/shiboleth/api/routes/rules.py \
  apps/api/src/shiboleth/main.py apps/api/tests/integration/test_api_rules.py
git commit -m "feat: GET /rules — single rule-text + severity source"
```

---

### Task 3: analytics block + found_at on GET /products/{id}

**Files:**
- Modify: `apps/api/src/shiboleth/api/routes/products.py` (the `product_detail` route)
- Test: `apps/api/tests/integration/test_api_analytics.py`

- [ ] **Step 1: Write the failing tests**

Create `apps/api/tests/integration/test_api_analytics.py`:

```python
"""
meta:
  purpose: KPI traceability for the product analytics block (spec 2026-07-10):
           every number in GET /products/{id} analytics equals an INDEPENDENT
           SQL aggregate over the same DB state. found_at = the run's
           started_at. Empty states honest (fp_rate null, zero rows present).
  contract: needs docker Postgres; builds a known-state test DB.
  deps: pytest, httpx, seeded_session fixture from test_seed_db.
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select

from shiboleth.db.models import Flag, Material, Property, Run
from tests.integration.test_api_metrics import make_client
from tests.integration.test_seed_db import _postgres_available, seeded_session  # noqa: F401

pytestmark = pytest.mark.skipif(
    not _postgres_available(), reason="docker Postgres not running (make db-up)"
)


@pytest.fixture
async def analytics_state(seeded_session):  # noqa: F811
    """One completed run, two properties, four flags in known states."""
    now = datetime.now(UTC)
    seeded_session.add(Property(id="tt-instagram", product_id="turbotax-free",
                                kind="instagram", url_or_handle="@turbotax",
                                config={}))
    run = Run(product_id="turbotax-free", mode="corpus", status="completed",
              started_at=now - timedelta(hours=2), finished_at=now,
              scores={"draft": 50.0, "verified": 50.0, "per_property": {}})
    seeded_session.add(run)
    await seeded_session.flush()
    web_mat = Material(property_id="tt-website", ref="https://x/a", kind="page",
                       content_hash="h-a", extracted_text="a", fetched_at=now)
    ig_mat = Material(property_id="tt-instagram", ref="https://ig/p1", kind="post",
                      content_hash="h-b", extracted_text="b", fetched_at=now)
    seeded_session.add_all([web_mat, ig_mat])
    await seeded_session.flush()

    def flag(mat, check_id, state, tag, **kw):
        return Flag(run_id=run.id, material_id=mat.id, check_id=check_id,
                    axis_a=False, axis_b=False, intersection_tag=tag,
                    evidence_quote="q", reason="r", confidence=0.9,
                    state=state, location="loc", **kw)

    seeded_session.add_all([
        flag(web_mat, "R-01-REQ", "open", "unapproved_violation"),
        flag(web_mat, "R-01-REQ", "dismissed", "unapproved_violation",
             dispositioned_at=now),
        flag(web_mat, "R-03-REQ", "assigned", "drifted_but_compliant",
             dispositioned_at=now, assigned_team="web"),
        flag(ig_mat, "R-02-REQ", "open", "unapproved_violation"),
    ])
    await seeded_session.commit()
    app, client, engine = await make_client(seeded_session)
    async with client:
        yield client, seeded_session, run
    await engine.dispose()


async def test_by_rule_matches_independent_sql(analytics_state):
    client, session, run = analytics_state
    detail = (await client.get("/products/turbotax-free")).json()
    by_rule = {r["rule_id"]: r for r in detail["analytics"]["by_rule"]}

    for rule_id in ("R-01", "R-02", "R-03", "R-04"):
        sql_total = (await session.execute(
            select(func.count(Flag.id)).where(
                Flag.run_id == run.id, Flag.check_id.like(f"{rule_id}-%"))
        )).scalar()
        assert by_rule[rule_id]["total"] == sql_total
    assert by_rule["R-01"] == {"rule_id": "R-01", "severity": "High",
                               "open": 1, "confirmed": 0, "dismissed": 1,
                               "total": 2}
    assert by_rule["R-03"]["confirmed"] == 1  # assigned is confirmed-family
    assert by_rule["R-04"]["total"] == 0      # honest zero row present


async def test_by_property_and_tag_match_independent_sql(analytics_state):
    client, session, run = analytics_state
    detail = (await client.get("/products/turbotax-free")).json()
    by_prop = {p["property_id"]: p for p in detail["analytics"]["by_property"]}

    ig_total = (await session.execute(
        select(func.count(Flag.id)).join(Material, Flag.material_id == Material.id)
        .where(Flag.run_id == run.id, Material.property_id == "tt-instagram")
    )).scalar()
    assert by_prop["tt-instagram"]["total"] == ig_total == 1
    assert by_prop["tt-website"] == {"property_id": "tt-website",
                                     "kind": "website", "open": 2, "total": 3}

    tags = {t["tag"]: t["count"] for t in detail["analytics"]["by_tag"]}
    sql_unapproved = (await session.execute(
        select(func.count(Flag.id)).where(
            Flag.run_id == run.id,
            Flag.intersection_tag == "unapproved_violation")
    )).scalar()
    assert tags["unapproved_violation"] == sql_unapproved == 3


async def test_disposition_block_and_found_at(analytics_state):
    client, session, run = analytics_state
    detail = (await client.get("/products/turbotax-free")).json()

    assert detail["analytics"]["disposition"] == {
        "pending": 2, "confirmed": 1, "dismissed": 1, "fp_rate": 0.5}
    for f in detail["flags"]:
        assert f["found_at"] == run.started_at.isoformat()


async def test_analytics_empty_state_no_runs(seeded_session):  # noqa: F811
    app, client, engine = await make_client(seeded_session)
    async with client:
        detail = (await client.get("/products/turbotax-free")).json()
    await engine.dispose()
    a = detail["analytics"]
    assert len(a["by_rule"]) == 4 and all(r["total"] == 0 for r in a["by_rule"])
    assert a["disposition"]["fp_rate"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd apps/api && uv run pytest tests/integration/test_api_analytics.py -v`
Expected: FAIL with `KeyError: 'analytics'`.

- [ ] **Step 3: Extend the product_detail route**

In `apps/api/src/shiboleth/api/routes/products.py`:

Add imports:

```python
from shiboleth.db.models import Cluster, Flag, Material, Product, Property, Run, Rule
from shiboleth.services.scoring.analytics import flag_analytics
```

Inside `product_detail`, the existing material query only selects `id, ref`; extend it to carry `property_id`, and build the analytics inputs. Replace the `source_urls` block with:

```python
            material_ids = {f.material_id for f in rows if f.material_id}
            source_urls: dict[str, str] = {}
            prop_of_material: dict[str, str] = {}
            if material_ids:
                mat_rows = (await session.execute(
                    select(Material.id, Material.ref, Material.property_id)
                    .where(Material.id.in_(material_ids))
                )).all()
                source_urls = {mid: ref for mid, ref, _pid in mat_rows}
                prop_of_material = {mid: pid for mid, _ref, pid in mat_rows}
```

Add `found_at` to each flag dict (inside the existing loop over `rows`):

```python
                    "found_at": latest.started_at.isoformat()
                    if latest.started_at else None,
```

After the flags loop (still inside `if latest:` — but analytics must ALSO exist when there is no run), compute the block. Place this right before the `return`:

```python
        rule_rows = (await session.execute(
            select(Rule).order_by(Rule.position)
        )).scalars().all()
        analytics = flag_analytics(
            [{"check_id": f.check_id, "state": f.state,
              "intersection_tag": f.intersection_tag,
              "property_id": prop_of_material.get(f.material_id)}
             for f in rows] if latest else [],
            [{"id": r.id, "severity": r.severity, "position": r.position}
             for r in rule_rows],
            [{"id": p.id, "kind": p.kind} for p in properties],
        )
```

`rows` and `prop_of_material` must be initialized before the `if latest:` block (`rows: list[Flag] = []`, `prop_of_material = {}`) so the no-run path works. Add `"analytics": analytics,` to the returned dict, and update the file's meta header (analytics + found_at now part of the contract).

- [ ] **Step 4: Run the new tests, then the full suite**

Run: `cd apps/api && uv run pytest tests/integration/test_api_analytics.py -v`
Expected: PASS.
Run: `uv run pytest -q`
Expected: full suite green (product payload additions are additive; existing tests unaffected).

- [ ] **Step 5: Lint and commit**

```bash
cd apps/api && uv run ruff check src tests
cd ../.. && git add apps/api/src/shiboleth/api/routes/products.py \
  apps/api/tests/integration/test_api_analytics.py
git commit -m "feat: analytics block + found_at on GET /products/{id}"
```

---

### Task 4: GET /flags/{flag_id} with real provenance trace

**Files:**
- Modify: `apps/api/src/shiboleth/api/routes/flags.py` (add the GET route)
- Test: `apps/api/tests/integration/test_api_flag_detail.py`

- [ ] **Step 1: Write the failing tests**

Create `apps/api/tests/integration/test_api_flag_detail.py`:

```python
"""
meta:
  purpose: GET /flags/{id} provenance (spec 2026-07-10): the trace is
           assembled from PERSISTED rows only — material_fetched event
           (matched by run + payload ref), check_result event (matched by
           flag_id), verdict fields from the flag, model from the run's
           model_config. Absent event rows -> null step, never synthesized.
  contract: needs docker Postgres.
  deps: pytest, httpx, seeded_session fixture from test_seed_db.
"""

from datetime import UTC, datetime, timedelta

import pytest

from shiboleth.db.models import Event, Flag, Material, Run
from tests.integration.test_api_metrics import make_client
from tests.integration.test_seed_db import _postgres_available, seeded_session  # noqa: F811,F401

pytestmark = pytest.mark.skipif(
    not _postgres_available(), reason="docker Postgres not running (make db-up)"
)


@pytest.fixture
async def flag_with_events(seeded_session):  # noqa: F811
    now = datetime.now(UTC)
    run = Run(product_id="turbotax-free", mode="corpus", status="completed",
              started_at=now - timedelta(hours=1), finished_at=now,
              model_config_json={"check": "groq:llama-3.3-70b-versatile"},
              scores={})
    seeded_session.add(run)
    await seeded_session.flush()
    mat = Material(property_id="tt-website", ref="https://x/page", kind="page",
                   content_hash="h1", extracted_text="body", fetched_at=now)
    seeded_session.add(mat)
    await seeded_session.flush()
    flag = Flag(run_id=run.id, material_id=mat.id, check_id="R-01-REQ",
                axis_a=False, axis_b=False,
                intersection_tag="unapproved_violation",
                evidence_quote="q", reason="the reason", confidence=0.87,
                state="open", location="page (page)")
    seeded_session.add(flag)
    await seeded_session.flush()
    seeded_session.add(Event(run_id=run.id, node="ingest",
                             event_type="material_fetched",
                             payload={"ref": "https://x/page",
                                      "cache_hit": True, "corpus": True},
                             ts=now - timedelta(minutes=50)))
    seeded_session.add(Event(run_id=run.id, flag_id=flag.id, node="check",
                             event_type="check_result",
                             payload={"verdict": "flag",
                                      "tag": "unapproved_violation"},
                             ts=now - timedelta(minutes=10)))
    await seeded_session.commit()
    app, client, engine = await make_client(seeded_session)
    async with client:
        yield client, run, mat, flag
    await engine.dispose()


async def test_trace_is_assembled_from_persisted_rows(flag_with_events):
    client, run, mat, flag = flag_with_events
    body = (await client.get(f"/flags/{flag.id}")).json()

    assert body["flag"]["id"] == flag.id
    assert body["flag"]["found_at"] == run.started_at.isoformat()
    ingested = body["trace"]["ingested"]
    assert ingested["ref"] == "https://x/page"
    assert ingested["cache_hit"] is True
    assert ingested["ts"]  # real event timestamp, ISO string
    assert body["trace"]["checked"]["ts"]
    verdict = body["trace"]["verdict"]
    assert verdict["check_id"] == "R-01-REQ"
    assert verdict["confidence"] == 0.87
    assert verdict["reason"] == "the reason"
    assert verdict["model"] == "groq:llama-3.3-70b-versatile"


async def test_missing_events_are_null_not_synthesized(seeded_session):  # noqa: F811
    now = datetime.now(UTC)
    run = Run(product_id="turbotax-free", mode="corpus", status="completed",
              started_at=now, finished_at=now, scores={})
    seeded_session.add(run)
    await seeded_session.flush()
    flag = Flag(run_id=run.id, material_id=None, check_id="R-01-REQ",
                axis_a=False, axis_b=False,
                intersection_tag="unapproved_violation",
                evidence_quote="q", reason="r", confidence=0.5,
                state="open", location="x")
    seeded_session.add(flag)
    await seeded_session.commit()
    app, client, engine = await make_client(seeded_session)
    async with client:
        body = (await client.get(f"/flags/{flag.id}")).json()
        missing = await client.get("/flags/nope")
    await engine.dispose()
    assert body["trace"]["ingested"] is None
    assert body["trace"]["checked"] is None
    assert body["trace"]["verdict"]["model"] is None
    assert missing.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd apps/api && uv run pytest tests/integration/test_api_flag_detail.py -v`
Expected: FAIL — GET /flags/{id} returns 405 or 404 (only POST disposition exists).

- [ ] **Step 3: Add the GET route**

In `apps/api/src/shiboleth/api/routes/flags.py`, add imports (`Event`, `Material` to the models import) and the route:

```python
@router.get("/flags/{flag_id}")
async def flag_detail(flag_id: str, request: Request) -> dict:
    """Provenance trace assembled from persisted rows only (spec 2026-07-10).
    Steps with no event row are null — the UI drops them, never invents."""
    async with request.app.state.session_factory() as session:
        flag = await session.get(Flag, flag_id)
        if flag is None:
            raise HTTPException(404, "flag not found")
        run = await session.get(Run, flag.run_id)
        material = (await session.get(Material, flag.material_id)
                    if flag.material_id else None)

        ingested = None
        if material is not None:
            ev = (await session.execute(
                select(Event).where(
                    Event.run_id == run.id,
                    Event.event_type == "material_fetched",
                    Event.payload["ref"].astext == material.ref,
                ).order_by(Event.ts).limit(1)
            )).scalar_one_or_none()
            if ev is not None:
                ingested = {"ts": ev.ts.isoformat(), "ref": material.ref,
                            "cache_hit": bool(ev.payload.get("cache_hit"))}

        check_ev = (await session.execute(
            select(Event).where(
                Event.flag_id == flag.id,
                Event.event_type == "check_result",
            ).order_by(Event.ts).limit(1)
        )).scalar_one_or_none()
        checked = {"ts": check_ev.ts.isoformat()} if check_ev else None

        model = (run.model_config_json or {}).get("check") if run else None
        return {
            "flag": {"id": flag.id, "state": flag.state,
                     "check_id": flag.check_id,
                     "found_at": run.started_at.isoformat()
                     if run and run.started_at else None},
            "trace": {
                "ingested": ingested,
                "checked": checked,
                "verdict": {"check_id": flag.check_id, "axis_a": flag.axis_a,
                            "axis_b": flag.axis_b,
                            "intersection_tag": flag.intersection_tag,
                            "confidence": flag.confidence,
                            "reason": flag.reason, "model": model},
            },
        }
```

Update the file's meta header (now also GET /flags/{id}). Note: `run.model_config_json` is the attribute name the products route already uses.

- [ ] **Step 4: Run the tests, then the full suite**

Run: `cd apps/api && uv run pytest tests/integration/test_api_flag_detail.py -v`
Expected: PASS.
Run: `uv run pytest -q`
Expected: green.

- [ ] **Step 5: Lint and commit**

```bash
cd apps/api && uv run ruff check src tests
cd ../.. && git add apps/api/src/shiboleth/api/routes/flags.py \
  apps/api/tests/integration/test_api_flag_detail.py
git commit -m "feat: GET /flags/{id} — provenance trace from persisted events"
```

---

### Task 5: severity single-source refactor (API side)

**Files:**
- Modify: `apps/api/src/shiboleth/api/routes/metrics.py` (delete `SEVERITY_BY_RULE` + `_severity`, lines 35-38)
- Modify: `apps/api/src/shiboleth/api/routes/flags.py` (delete its duplicate map, lines 28-32)

- [ ] **Step 1: Check current usage**

`metrics.py` uses `_severity(f.check_id)` when building `flag_rows` for `open_violations_metric`. `flags.py` defines the map but — verify with `grep -n "_severity" apps/api/src/shiboleth/api/routes/flags.py` — the disposition route never calls it (scores recompute from persisted outcome_rows, which already carry severity). If unused there, delete it outright.

- [ ] **Step 2: Replace the hardcoded map in metrics.py with a rules-table read**

In `compute_portfolio_metrics`, after `latest = await _latest_runs(session)`, add:

```python
    rule_rows = (await session.execute(select(Rule))).scalars().all()
    severity_by_rule = {r.id: r.severity for r in rule_rows}

    def _severity(check_id: str) -> str:
        return severity_by_rule.get(check_id.rsplit("-", 1)[0], "Medium")
```

Delete the module-level `SEVERITY_BY_RULE` and `_severity`. Add `Rule` to the models import. Delete `SEVERITY_BY_RULE`/`_severity` from flags.py (if Step 1 confirmed unused). Update both meta headers.

- [ ] **Step 3: Run the full suite**

Run: `cd apps/api && uv run pytest -q`
Expected: green — behavior identical because the seeded rules table contains exactly the same severities (pinned by the verbatim seed test).

- [ ] **Step 4: Lint and commit**

```bash
cd apps/api && uv run ruff check src tests
cd ../.. && git add apps/api/src/shiboleth/api/routes/metrics.py \
  apps/api/src/shiboleth/api/routes/flags.py
git commit -m "refactor: severity from the rules table, not hardcoded maps"
```

---

### Task 6: web — rules from the API, fixtures.ts to types-only

**Files:**
- Modify: `apps/web/src/lib/api.ts` (add `ApiRule`, `getRulesApi`, `analytics` + `found_at` types)
- Modify: `apps/web/src/lib/data.ts` (add `useRules`, thread rules into `buildProductView`/`toFlagView`/`severityOf`, delete the web `SEVERITY_BY_RULE`)
- Modify: `apps/web/src/lib/fixtures.ts` (delete the `rules` array)

- [ ] **Step 1: Add API types + fetcher in `lib/api.ts`**

Add after the existing `ApiFlag` interface (and add `found_at` to `ApiFlag` itself):

```ts
export interface ApiRule {
  id: string;
  verbatim_text: string;
  severity: "High" | "Medium" | "Low";
  position: number;
}

export interface ApiAnalyticsRuleRow {
  rule_id: string;
  severity: "High" | "Medium" | "Low";
  open: number;
  confirmed: number;
  dismissed: number;
  total: number;
}
export interface ApiAnalyticsPropertyRow {
  property_id: string;
  kind: PropertyKind;
  open: number;
  total: number;
}
export interface ApiAnalytics {
  by_rule: ApiAnalyticsRuleRow[];
  by_property: ApiAnalyticsPropertyRow[];
  by_tag: { tag: IntersectionTag; count: number }[];
  disposition: {
    pending: number;
    confirmed: number;
    dismissed: number;
    fp_rate: number | null;
  };
}

export function getRulesApi(): Promise<ApiRule[]> {
  return fetchJson("/rules");
}
```

In `ApiFlag` add `found_at: string | null;`. In `ApiProductDetail` add `analytics: ApiAnalytics;`. Update the meta header (mirrors rules.py now too).

- [ ] **Step 2: Add `useRules` and thread rules through `data.ts`**

Add near the hero-metrics section:

```ts
// Rules are static seed data: fetch once, never refetch.
export function useRules(): { rules: ApiRule[]; isLoading: boolean } {
  const q = useQuery({
    queryKey: ["rules"],
    queryFn: getRulesApi,
    staleTime: Infinity,
  });
  return { rules: q.data ?? [], isLoading: q.isLoading };
}
```

Delete the `SEVERITY_BY_RULE` constant. Change `severityOf` to take the fetched rules:

```ts
function severityOf(checkId: string, rulesById: Map<string, ApiRule>): Severity {
  return rulesById.get(ruleIdOf(checkId))?.severity ?? "Medium";
}
```

Thread a `rulesById: Map<string, ApiRule>` parameter through `buildProductView`, `toFlagView`, and `buildMetrics` (each currently calls `severityOf`). In `toFlagView`, replace the fixtures lookup at line ~476:

```ts
  const apiRule = rulesById.get(ruleId);
  const rule: Rule = apiRule ?? {
    id: ruleId,
    verbatim_text: "",
    severity: "Medium",
    position: 0,
  };
```

In `useProductView`, call `useRules()` alongside the product query, build the map with `useMemo`, pass it down, and include rules loading in `isLoading`:

```ts
  const { rules, isLoading: rulesLoading } = useRules();
  const rulesById = useMemo(
    () => new Map(rules.map((r) => [r.id, r])),
    [rules]
  );
  // ... isLoading: q.isLoading || rulesLoading
```

Remove `rules` from the fixtures import (keep the type imports). Update both meta headers (data.ts no longer imports any fixture data; fixtures.ts is types-only).

- [ ] **Step 3: Delete the rules array from `fixtures.ts`**

Delete the `export const rules: Rule[] = [...]` block and the now-unused `Rule`/`Severity`/`PropertyKind` type imports it needed (keep whichever the remaining interfaces still use). Update the meta header: file is view-model types ONLY; rule text now comes from GET /rules.

- [ ] **Step 4: Build, lint, grep-verify**

```bash
cd apps/web && npm run build && npm run lint
grep -rn "from \"@/lib/fixtures\"" src | grep -v "import type"
```

Expected: build + lint green; the grep prints NOTHING (only type imports remain).

- [ ] **Step 5: Commit**

```bash
cd .. && git add apps/web/src/lib/api.ts apps/web/src/lib/data.ts \
  apps/web/src/lib/fixtures.ts
git commit -m "feat: web rules from GET /rules; fixtures.ts becomes types-only"
```

---

### Task 7: web — "Flagged dataset" section on the product page

**Files:**
- Create: `apps/web/src/components/surfaces/flagged-dataset.tsx`
- Modify: `apps/web/src/lib/data.ts` (expose `analytics` on `ProductView`)
- Modify: `apps/web/src/app/products/[id]/page.tsx` (render the section under the metric row, after line ~109)

- [ ] **Step 1: Expose analytics on the view model**

In `data.ts`: add `analytics: ApiAnalytics | null;` to `ProductView`, return `detail.analytics` from `buildProductView` (and `null` in the loading/error branch of `useProductView`).

- [ ] **Step 2: Create the section component**

Create `apps/web/src/components/surfaces/flagged-dataset.tsx`:

```tsx
// meta: U6 "Flagged dataset" section (spec 2026-07-10). Four panels rendered
// verbatim from the API analytics block (by rule, by property, by verdict
// tag, disposition outcomes + FP rate). Zero client math beyond bar widths;
// existing primitives + DESIGN.md tokens only. Honest empty state when the
// run has no flags.

import { SeverityBadge } from "@/components/primitives/severity-badge";
import { IntersectionPill } from "@/components/primitives/verdict-tags";
import { PropertyIcon } from "@/components/primitives/property-chip";
import type { ApiAnalytics } from "@/lib/api";

function CountBar({ value, max }: { value: number; max: number }) {
  const pct = max > 0 ? Math.round((100 * value) / max) : 0;
  return (
    <div className="h-1.5 w-full rounded-full bg-surface">
      <div
        className="h-1.5 rounded-full bg-foreground/60"
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-2 rounded-md border border-border bg-surface px-3.5 py-3">
      <span className="text-xs font-medium text-muted-foreground">{title}</span>
      {children}
    </div>
  );
}

export function FlaggedDataset({ analytics }: { analytics: ApiAnalytics }) {
  const total = analytics.by_rule.reduce((n, r) => n + r.total, 0);
  if (total === 0) {
    return (
      <div className="mb-6 rounded-md border border-border bg-surface px-3.5 py-3 text-xs text-muted-foreground">
        No flags in this run.
      </div>
    );
  }
  const ruleMax = Math.max(...analytics.by_rule.map((r) => r.total));
  const propMax = Math.max(...analytics.by_property.map((p) => p.total));
  const d = analytics.disposition;
  return (
    <section aria-label="Flagged dataset" className="mb-6 grid grid-cols-4 gap-3">
      <Panel title="By rule">
        {analytics.by_rule.map((r) => (
          <div key={r.rule_id} className="flex flex-col gap-1">
            <div className="flex items-center justify-between text-xs">
              <span className="flex items-center gap-1.5">
                <span className="font-mono">{r.rule_id}</span>
                <SeverityBadge severity={r.severity} />
              </span>
              <span className="text-muted-foreground">
                {r.open} open · {r.total} total
              </span>
            </div>
            <CountBar value={r.total} max={ruleMax} />
          </div>
        ))}
      </Panel>
      <Panel title="By property">
        {analytics.by_property.map((p) => (
          <div key={p.property_id} className="flex flex-col gap-1">
            <div className="flex items-center justify-between text-xs">
              <span className="flex items-center gap-1.5">
                <PropertyIcon kind={p.kind} />
                <span>{p.property_id}</span>
              </span>
              <span className="text-muted-foreground">
                {p.open} open · {p.total} total
              </span>
            </div>
            <CountBar value={p.total} max={propMax} />
          </div>
        ))}
      </Panel>
      <Panel title="By verdict tag">
        {analytics.by_tag.map((t) => (
          <div
            key={t.tag}
            className="flex items-center justify-between text-xs"
          >
            <IntersectionPill tag={t.tag} />
            <span className="text-muted-foreground">{t.count}</span>
          </div>
        ))}
      </Panel>
      <Panel title="Disposition">
        <div className="flex flex-col gap-1.5 text-xs">
          <div className="flex justify-between">
            <span>Pending</span>
            <span className="text-muted-foreground">{d.pending}</span>
          </div>
          <div className="flex justify-between">
            <span>Confirmed</span>
            <span className="text-muted-foreground">{d.confirmed}</span>
          </div>
          <div className="flex justify-between">
            <span>Dismissed</span>
            <span className="text-muted-foreground">{d.dismissed}</span>
          </div>
          <div className="flex justify-between border-t border-border pt-1.5">
            <span>Observed FP rate</span>
            <span className="font-medium">
              {d.fp_rate === null ? "no dispositions yet" : `${Math.round(d.fp_rate * 100)}%`}
            </span>
          </div>
        </div>
      </Panel>
    </section>
  );
}
```

Before using `SeverityBadge`, `IntersectionPill`, `PropertyIcon`, check their actual prop names in `apps/web/src/components/primitives/` (severity-badge.tsx, verdict-tags.tsx, property-chip.tsx) and adjust — the component must compile against the real primitives, not assumed ones.

- [ ] **Step 3: Render it on the product page**

In `apps/web/src/app/products/[id]/page.tsx`: import `FlaggedDataset`, destructure `analytics` from `useProductView(id)`, and render directly after the metric-row `</div>` (after line ~109):

```tsx
      {analytics ? <FlaggedDataset analytics={analytics} /> : null}
```

- [ ] **Step 4: Build, lint, verify against the live API**

```bash
cd apps/web && npm run build && npm run lint
```

Expected: green. Then with `make db-up`, `make dev-api`, `make dev-web` running, load `http://localhost:3000/products/turbotax-free` and confirm the four panels show the certified corpus run's real counts (137 flags total across rules; zero console errors).

- [ ] **Step 5: Commit**

```bash
cd .. && git add apps/web/src/components/surfaces/flagged-dataset.tsx \
  apps/web/src/lib/data.ts "apps/web/src/app/products/[id]/page.tsx"
git commit -m "feat: flagged dataset section on the product page"
```

---

### Task 8: web — real provenance on the flag detail page

**Files:**
- Modify: `apps/web/src/lib/api.ts` (flag detail fetcher)
- Modify: `apps/web/src/lib/data.ts` (`useFlagTrace` hook; real `foundAt`; remove `postDate`/`missingRequirement`; chain from trace)
- Modify: `apps/web/src/lib/fixtures.ts` (drop the two dead props from `FlagMeta`)
- Modify: `apps/web/src/app/products/[id]/flags/[flagId]/page.tsx` (render real chain + foundAt; drop dead-prop render paths)

- [ ] **Step 1: Add the fetcher in `api.ts`**

```ts
export interface ApiTrace {
  ingested: { ts: string; ref: string; cache_hit: boolean } | null;
  checked: { ts: string } | null;
  verdict: {
    check_id: string;
    axis_a: boolean;
    axis_b: boolean | null;
    intersection_tag: IntersectionTag | "na";
    confidence: number;
    reason: string;
    model: string | null;
  };
}
export interface ApiFlagDetail {
  flag: { id: string; state: string; check_id: string; found_at: string | null };
  trace: ApiTrace;
}
export function getFlagDetailApi(flagId: string): Promise<ApiFlagDetail> {
  return fetchJson(`/flags/${flagId}`);
}
```

- [ ] **Step 2: Build the chain from the trace in `data.ts`**

Add a hook + a pure builder:

```ts
export function useFlagTrace(flagId: string | null): {
  trace: ApiFlagDetail | null;
} {
  const q = useQuery({
    queryKey: ["flag-trace", flagId],
    queryFn: () => getFlagDetailApi(flagId!),
    enabled: flagId !== null,
  });
  return { trace: q.data ?? null };
}

function fmtTs(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

// Chain steps come ONLY from persisted trace rows; absent rows drop out.
export function traceToChain(detail: ApiFlagDetail, model: string): WhyStep[] {
  const t = detail.trace;
  const tag = coerceTag(t.verdict.intersection_tag);
  const steps: (WhyStep | null)[] = [
    t.ingested
      ? {
          title: `Ingested · ${t.ingested.ref}`,
          detail: `fetched ${fmtTs(t.ingested.ts)}${t.ingested.cache_hit ? " (cache)" : ""}`,
        }
      : null,
    t.checked
      ? { title: `Checked · ${t.verdict.check_id} · ${fmtTs(t.checked.ts)}` }
      : null,
    {
      title: `Verdict · ${TAG_LABEL[tag]} at ${t.verdict.confidence.toFixed(2)} confidence · ${t.verdict.model ?? model}`,
      detail: t.verdict.reason,
    },
  ];
  return steps.filter((s): s is WhyStep => s !== null);
}
```

In `toFlagView`: set `foundAt` from the flag's `found_at` (`f.found_at ? fmtTs(f.found_at) : "latest run"` — the string fallback only for pre-`found_at` payloads), delete the `missingRequirement` and `postDate` fields, and leave the existing `chain` as the fallback used only until the trace query resolves.

In `fixtures.ts` `FlagMeta`: delete `missingRequirement` and `postDate` (keep `sourceUrl`, which the preview feature added). Update meta headers.

- [ ] **Step 3: Wire the flag detail page**

In `apps/web/src/app/products/[id]/flags/[flagId]/page.tsx`:
- Call `useFlagTrace(flagId)` next to the existing data hook.
- Where `<WhyFlagged steps={meta.chain} />` renders (line ~171), prefer the trace: `steps={trace ? traceToChain(trace, meta.model) : meta.chain}`.
- Where `meta.foundAt` renders (line ~87), it now shows the real timestamp automatically.
- Delete any render path referencing `meta.postDate` or `meta.missingRequirement` (grep the file first: `grep -n "postDate\|missingRequirement" <file>`).

- [ ] **Step 4: Build, lint, verify live**

```bash
cd apps/web && npm run build && npm run lint
```

Expected: green. Live check: open any flag detail page; the chain shows real timestamps from the run's events (corpus run 559e0b15 has material_fetched + check_result rows), foundAt shows a real date, no "Extracted · marketing copy" synthetic line remains.

- [ ] **Step 5: Commit**

```bash
cd .. && git add apps/web/src/lib/api.ts apps/web/src/lib/data.ts \
  apps/web/src/lib/fixtures.ts \
  "apps/web/src/app/products/[id]/flags/[flagId]/page.tsx"
git commit -m "feat: flag detail provenance from persisted events; dead props removed"
```

---

### Task 9: web — "Caught" label + final sweep

**Files:**
- Modify: `apps/web/src/lib/data.ts` (HERO_ORDER label, line ~147)

- [ ] **Step 1: Rename the card**

In `HERO_ORDER`: `{ key: "caught", label: "Caught" }` (was "Caught this week"). Approved deviation from spec §10.5's name — the API sublabel already carries the honest window ("this run").

- [ ] **Step 2: Placeholder sweep**

```bash
cd apps/web && grep -rn "latest run\"\|this week\|postDate\|missingRequirement" src
```

Expected: the only hit is the `foundAt` fallback string for pre-`found_at` payloads (data.ts). Anything else found: fix it now.

- [ ] **Step 3: Build, lint, commit**

```bash
npm run build && npm run lint
cd .. && git add apps/web/src/lib/data.ts
git commit -m "fix: Caught card label matches its honest per-run window"
```

---

### Task 10: end-to-end + regression gate

**Files:**
- Modify: `apps/web/e2e/journey.spec.ts` (add analytics + provenance assertions)

- [ ] **Step 1: Extend the journey spec**

Read `apps/web/e2e/journey.spec.ts` first to match its structure and selectors. After the existing "both flag groupings" step (product page, flags present), add:

```ts
    // Flagged dataset section renders real API analytics
    const dataset = page.locator('section[aria-label="Flagged dataset"]');
    await expect(dataset).toBeVisible();
    await expect(dataset.getByText("By rule")).toBeVisible();
    await expect(dataset.getByText("Observed FP rate")).toBeVisible();
```

And in the flag-detail step (after the evidence assertion), assert the chain is event-backed:

```ts
    // why-flagged chain shows a real ingest timestamp, not synthetic copy
    await expect(page.getByText(/Ingested · /)).toBeVisible();
    await expect(page.getByText("Extracted · marketing copy")).toHaveCount(0);
```

- [ ] **Step 2: Run the full gate**

With `make db-up` and the API + web dev servers running:

```bash
cd apps/api && uv run pytest -q          # full suite, unpiped
cd ../web && npm run build && npm run lint && npm run e2e
```

Expected: pytest green (all existing + ~15 new tests), build + lint green, Playwright journey green including the new assertions.

- [ ] **Step 3: Regression — certification replay untouched**

```bash
cd ../api && CASSETTE_MODE=replay uv run python -m shiboleth.evals.harnesses.e3 --name post-analytics-regression
```

Expected: strict accuracy 97.99%, synthetics 17/17, evidence validity 1.0, 0 live calls — identical to e3-iter-11 (no checker-path code was touched).

- [ ] **Step 4: Commit + update code/CLAUDE.md decision log**

Append to the build-level decision log in `code/CLAUDE.md`: one entry dated 2026-07-10 noting the analytics block, GET /rules as the severity single source, event-backed provenance, the "Caught" rename (approved §10.5 deviation), and dead props removed.

```bash
git add apps/web/e2e/journey.spec.ts CLAUDE.md
git commit -m "test: e2e analytics + provenance assertions; decision log entry"
```

Do NOT push — Aarvin confirms pushes explicitly.

---

## Self-review notes

- Spec coverage: analytics block (Tasks 1, 3), GET /rules + severity single source (Tasks 2, 5, 6), found_at + trace (Tasks 3, 4, 8), fixtures types-only (Task 6), U6 section (Task 7), Caught rename + dead props (Tasks 8, 9), tests-first throughout, e2e + certification regression (Task 10).
- Known judgment calls an executor must respect: primitive prop names in Task 7 Step 2 must be verified against the real components before compiling; Task 1's by_property ordering test must be aligned to id order per spec; Task 5 Step 1 verifies flags.py's severity map is truly unused before deleting.
- The disposition endpoint response is unchanged — the UI's existing invalidation of the product query refetches the analytics block after any disposition, so the panels stay live with no extra wiring.
