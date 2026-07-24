"""
meta:
  purpose: Stage 2b wiring: verify_run_flags runs the verifier over a run's
           flags and stores agreement, resilient per flag (a failing verifier
           leaves the flag unverified and never raises). Stub invoke, no LLM.
           Advisory only.
  deps: docker Postgres (skipped when down); seeded test DB fixture.
"""

import pytest

from adlign.db.models import Flag, Material, Run
from adlign.pipeline.nodes.verify import VerifierVerdict
from adlign.services.verification import verify_run_flags
from tests.integration.test_seed_db import TEST_URL, _postgres_available, seeded_session  # noqa: F401

pytestmark = pytest.mark.skipif(
    not _postgres_available(), reason="docker Postgres not running (make db-up)"
)


@pytest.fixture
async def run_with_flag(seeded_session):  # noqa: F811
    run = Run(product_id="turbotax-free", mode="corpus", status="completed",
              scores={"draft": 50.0, "verified": 50.0})
    seeded_session.add(run)
    await seeded_session.flush()
    material = Material(property_id="tt-website", ref="https://x/", kind="page",
                        content_hash="h-verify", extracted_text="File free for all.")
    seeded_session.add(material)
    await seeded_session.flush()
    flag = Flag(run_id=run.id, material_id=material.id, check_id="R-01-REQ",
                axis_a=False, axis_b=False, intersection_tag="unapproved_violation",
                evidence_quote="File free.", location="hero", reason="r",
                confidence=0.9, state="open", evidence_valid=True, ambiguous=False)
    seeded_session.add(flag)
    await seeded_session.commit()
    return run, flag


def _agree_invoke(_prompt):
    # verifier agrees with the primary (triggered, requirement not met)
    return VerifierVerdict(trigger_met=True, requirement_met=False, reason="agree")


def _raise_invoke(_prompt):
    raise RuntimeError("verifier provider down")


async def test_verify_run_flags_stores_agreement(seeded_session, run_with_flag):  # noqa: F811
    run, flag = run_with_flag
    n = await verify_run_flags(seeded_session, run.id, _agree_invoke, "openai:test")
    assert n == 1
    refreshed = await seeded_session.get(Flag, flag.id)
    assert refreshed.verifier_agrees is True
    assert refreshed.verifier_model == "openai:test"
    assert refreshed.verifier_reason == "agree"


async def test_verify_run_flags_resilient_on_failure(seeded_session, run_with_flag):  # noqa: F811
    run, flag = run_with_flag
    # must not raise; flag stays unverified
    n = await verify_run_flags(seeded_session, run.id, _raise_invoke, "openai:test")
    assert n == 0
    refreshed = await seeded_session.get(Flag, flag.id)
    assert refreshed.verifier_agrees is None


async def test_verify_run_flags_skips_already_verified(seeded_session, run_with_flag):  # noqa: F811
    run, flag = run_with_flag
    # first pass verifies the flag
    assert await verify_run_flags(seeded_session, run.id, _agree_invoke, "openai:test") == 1
    # second pass is idempotent: the already-verified flag is skipped (0 re-verified)
    called = {"n": 0}

    def _counting_invoke(prompt):
        called["n"] += 1
        return _agree_invoke(prompt)

    assert await verify_run_flags(seeded_session, run.id, _counting_invoke, "openai:test") == 0
    assert called["n"] == 0  # no re-calls -> no wasted OpenAI spend
