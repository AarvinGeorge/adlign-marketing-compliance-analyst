"""
meta:
  purpose: Trust Stage 2 wiring. verify_run_flags() runs the independent
           verifier over every flag in a run and stores agreement on each flag.
           Resilient PER FLAG (a failed verification -> unverified, never
           raises) and advisory only (verdict/score/state untouched). Rule +
           checks come from load_rule_bundles (the DB scorecard), so it works
           for corpus and live flags alike.
  contract: verify_run_flags(session, run_id, verify_invoke, model_string) -> int
            (count of flags verified this pass).
  deps: db models, scorecard.load_rule_bundles, scoring.calibration.rule_id_of,
        nodes.verify.run_verify.
"""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from adlign.db.models import Flag, Material
from adlign.pipeline.nodes.verify import VerifierVerdict, run_verify
from adlign.services.scorecard import load_rule_bundles
from adlign.services.scoring.calibration import rule_id_of


async def verify_run_flags(
    session: AsyncSession,
    run_id: str,
    verify_invoke: Callable[[str], VerifierVerdict],
    model_string: str,
) -> int:
    bundles = {b["rule"]["id"]: b for b in await load_rule_bundles(session)}
    flags = (
        await session.execute(select(Flag).where(Flag.run_id == run_id))
    ).scalars().all()
    n = 0
    for f in flags:
        bundle = bundles.get(rule_id_of(f.check_id))
        if bundle is None or not f.material_id:
            continue
        material = await session.get(Material, f.material_id)
        if material is None:
            continue
        try:
            res = run_verify(
                material.extracted_text,
                bundle["rule"],
                bundle["checks"],
                primary_trigger_met=True,  # a flag is always triggered
                primary_requirement_met=f.axis_a,  # axis_a == requirement_met
                invoke=verify_invoke,
            )
            f.verifier_agrees = res.agrees
            f.verifier_model = model_string
            f.verifier_reason = res.reason
            n += 1
        except Exception:  # resilient: never let verification fail a run
            continue
    await session.commit()
    return n
