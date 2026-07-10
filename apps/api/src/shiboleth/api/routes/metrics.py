"""
meta:
  purpose: GET /metrics — the five hero KPIs (01_spec §10) computed from the
           REAL database (no fixtures). Also POST /products (create product +
           properties from New-check chips) and the product-level metric
           mirror used by GET /products/{id}. Every number traces to a SQL
           aggregate over current DB state (KPI traceability, E3).
  contract: GET /metrics -> {portfolio_score, open_violations, triage,
            coverage, caught} each {value, sublabel, intent, trend?}.
            POST /products {name, properties:[{kind,url_or_handle,config?}]}
            -> {id}. compute_product_metric_row for U6.
  deps: db models, scoring.kpis (pure), scoring.formulas (severity).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import desc, select

from shiboleth.db.models import Flag, Material, Product, Property, Run, RunInventory, new_id
from shiboleth.services.scoring.kpis import (
    caught_metric,
    coverage_metric,
    open_violations_metric,
    portfolio_score_metric,
    triage_metric,
)

router = APIRouter()

SEVERITY_BY_RULE = {"R-01": "High", "R-02": "High", "R-03": "Medium", "R-04": "Medium"}


def _severity(check_id: str) -> str:
    return SEVERITY_BY_RULE.get(check_id.rsplit("-", 1)[0], "Medium")


async def _latest_runs(session) -> list[Run]:
    """The latest run per product (any status). Metric surfaces read from the
    product's most recent run, matching what the dashboard card shows."""
    products = (await session.execute(select(Product))).scalars().all()
    runs = []
    for p in products:
        r = (await session.execute(
            select(Run).where(Run.product_id == p.id)
            .order_by(desc(Run.started_at)).limit(1)
        )).scalar_one_or_none()
        if r is not None:
            runs.append(r)
    return runs


async def compute_portfolio_metrics(session) -> dict:
    now = datetime.now(UTC)
    latest = await _latest_runs(session)
    completed = [r for r in latest if r.status == "completed"]

    # 1. verified portfolio score + real per-run trend
    per_product = []
    for r in completed:
        v = (r.scores or {}).get("verified")
        if v is None:
            continue
        rows = (r.scores or {}).get("outcome_rows", [])
        weight = sum(1 for row in rows if row["verdict_status"] in ("pass", "flag"))
        per_product.append((v, weight or 1))
    trend_runs = (await session.execute(
        select(Run).where(Run.status == "completed").order_by(Run.started_at)
    )).scalars().all()
    trend = [(r.scores or {}).get("verified") for r in trend_runs]
    trend = [t for t in trend if t is not None]

    # flags across the latest run of each product
    flag_rows: list[dict] = []
    ttds: list[timedelta] = []
    undispositioned = 0
    unapproved = drift = 0
    for r in latest:
        opened = r.started_at or now
        flags = (await session.execute(select(Flag).where(Flag.run_id == r.id))).scalars().all()
        for f in flags:
            flag_rows.append({"severity": _severity(f.check_id),
                              "opened_at": opened, "state": f.state})
            if f.dispositioned_at is None and f.state == "open":
                undispositioned += 1
            if f.dispositioned_at is not None:
                ttds.append(f.dispositioned_at - opened)
            if f.intersection_tag == "unapproved_violation":
                unapproved += 1
            elif f.intersection_tag == "drifted_but_compliant":
                drift += 1

    # coverage: distinct materials tracked vs fetched <=24h
    total_assets = 0
    checked_recent = 0
    for r in latest:
        inv = (await session.execute(
            select(RunInventory).where(RunInventory.run_id == r.id)
        )).scalars().all()
        hashes = {row.content_hash for row in inv}
        if not hashes:
            # corpus runs store materials directly, not always in inventory
            mats = (await session.execute(
                select(Material.content_hash, Material.fetched_at)
                .join(Property, Material.property_id == Property.id)
                .where(Property.product_id == r.product_id)
            )).all()
            for _h, fetched in mats:
                total_assets += 1
                if fetched and (now - fetched) <= timedelta(hours=24):
                    checked_recent += 1
        else:
            mats = (await session.execute(
                select(Material.content_hash, Material.fetched_at)
                .where(Material.content_hash.in_(hashes))
            )).all()
            for _h, fetched in mats:
                total_assets += 1
                if fetched and (now - fetched) <= timedelta(hours=24):
                    checked_recent += 1

    return {
        "portfolio_score": portfolio_score_metric(per_product, trend),
        "open_violations": open_violations_metric(flag_rows, now=now),
        "triage": triage_metric(undispositioned, ttds),
        "coverage": coverage_metric(checked_recent, total_assets),
        "caught": caught_metric(unapproved, drift),
    }


@router.get("/metrics")
async def get_metrics(request: Request) -> dict:
    async with request.app.state.session_factory() as session:
        return await compute_portfolio_metrics(session)


class NewProperty(BaseModel):
    kind: str
    url_or_handle: str
    config: dict = {}


class NewProduct(BaseModel):
    name: str
    properties: list[NewProperty] = []


@router.post("/products", status_code=201)
async def create_product(body: NewProduct, request: Request) -> dict:
    async with request.app.state.session_factory() as session:
        existing = (await session.execute(
            select(Product).where(Product.name == body.name)
        )).scalar_one_or_none()
        if existing is not None:
            raise HTTPException(409, f"product '{body.name}' already exists")
        product = Product(id=new_id(), name=body.name, status="active")
        session.add(product)
        await session.flush()
        for prop in body.properties:
            session.add(Property(id=new_id(), product_id=product.id, kind=prop.kind,
                                 url_or_handle=prop.url_or_handle, config=prop.config))
        await session.commit()
        return {"id": product.id, "name": product.name}
