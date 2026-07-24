"""
meta:
  purpose: Unit tests for the independent verifier (trust Stage 2). Agreement is
           COMPUTED from axes vs the primary verdict, never self-reported. Stub
           invoke, no LLM. Advisory only.
  deps: pytest; adlign.pipeline.nodes.verify.
"""

from adlign.pipeline.nodes.verify import VerifierVerdict, run_verify

RULE = {"verbatim_text": "rule text"}
CHECKS = [
    {"kind": "trigger", "text": "t", "evidence_criteria": "tc"},
    {"kind": "requirement", "text": "r", "evidence_criteria": "rc"},
]
MATERIAL = "we advertise free filing for everyone."


def _invoke(trigger, requirement):
    def invoke(_prompt: str) -> VerifierVerdict:
        return VerifierVerdict(trigger_met=trigger, requirement_met=requirement,
                               reason="stub")

    return invoke


def test_agrees_when_axes_match():
    res = run_verify(MATERIAL, RULE, CHECKS,
                     primary_trigger_met=True, primary_requirement_met=False,
                     invoke=_invoke(trigger=True, requirement=False))
    assert res.agrees is True


def test_disagrees_when_verifier_overturns_requirement():
    res = run_verify(MATERIAL, RULE, CHECKS,
                     primary_trigger_met=True, primary_requirement_met=False,
                     invoke=_invoke(trigger=True, requirement=True))
    assert res.agrees is False


def test_disagrees_when_verifier_says_not_triggered():
    res = run_verify(MATERIAL, RULE, CHECKS,
                     primary_trigger_met=True, primary_requirement_met=False,
                     invoke=_invoke(trigger=False, requirement=None))
    assert res.agrees is False


def test_result_carries_reason_and_axes():
    res = run_verify(MATERIAL, RULE, CHECKS, True, False, _invoke(True, False))
    assert res.reason == "stub"
    assert res.trigger_met is True and res.requirement_met is False
