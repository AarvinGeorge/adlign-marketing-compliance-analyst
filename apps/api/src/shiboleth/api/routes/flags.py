"""
meta:
  purpose: Disposition endpoint (S3 choreography, 07 §3): validate lifecycle
           transition, update flag, append eval_items (dismissed = FP label),
           recompute verified scores (pure SQL/Python, no LLM), return
           {flag, scores} so the UI updates without SSE.
  contract: POST /flags/{id}/disposition {action: confirm|dismiss, team?,
            note?}. confirm+team -> assigned (confirm then assign, one call —
            the U6/U7 Disposition panel's shape). Illegal transition -> 409.
  deps: db models, scoring metrics glue, formulas.validate_transition.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select

from shiboleth.db.models import EvalItem, Flag, Run
from shiboleth.domain.schemas import Disposition
from shiboleth.services.scoring.formulas import InvalidTransition, validate_transition
from shiboleth.services.scoring.metrics import outcomes_to_scores

router = APIRouter()

SEVERITY_BY_RULE = {"R-01": "High", "R-02": "High", "R-03": "Medium", "R-04": "Medium"}


def _severity(check_id: str) -> str:
    return SEVERITY_BY_RULE.get(check_id.rsplit("-", 1)[0], "Medium")


@router.post("/flags/{flag_id}/disposition")
async def disposition(flag_id: str, body: Disposition, request: Request) -> dict:
    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        flag = await session.get(Flag, flag_id)
        if flag is None:
            raise HTTPException(404, "flag not found")

        try:
            if body.action == "dismiss":
                validate_transition(flag.state, "dismissed")
                flag.state = "dismissed"
            else:  # confirm (+ optional team -> assigned in the same call)
                validate_transition(flag.state, "confirmed")
                flag.state = "confirmed"
                if body.team:
                    validate_transition(flag.state, "assigned")
                    flag.state = "assigned"
                    flag.assigned_team = body.team
        except InvalidTransition as exc:
            raise HTTPException(409, str(exc)) from exc

        flag.note = body.note
        flag.dispositioned_at = datetime.now(UTC)

        session.add(EvalItem(
            harness="checker", source="disposition",
            input={"flag_id": flag.id, "check_id": flag.check_id,
                   "evidence_quote": flag.evidence_quote},
            expected={"disposition": body.action, "note": body.note},
        ))

        # verified recompute: replay the SAME formula over the SAME outcome
        # rows the run persisted (corpus_run stores them in runs.scores)
        run = await session.get(Run, flag.run_id)
        flags = (await session.execute(
            select(Flag).where(Flag.run_id == run.id)
        )).scalars().all()
        dismissed = {f.id for f in flags if f.state == "dismissed"}
        outcome_rows = (run.scores or {}).get("outcome_rows", [])
        recomputed = outcomes_to_scores(outcome_rows, dismissed_ids=dismissed)
        run.scores = {**(run.scores or {}), "verified": recomputed["verified"],
                      "per_property": recomputed["per_property"]}
        await session.commit()

        return {
            "flag": {"id": flag.id, "state": flag.state,
                     "assigned_team": flag.assigned_team, "note": flag.note},
            "scores": {"draft": (run.scores or {}).get("draft"),
                       "verified": recomputed["verified"],
                       "per_property": recomputed["per_property"]},
        }
