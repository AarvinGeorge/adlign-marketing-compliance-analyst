"""
meta:
  purpose: Independent verifier (trust Stage 2). Re-judges ONE flagged
           material+rule with a DIFFERENT model than the checker and reports
           agreement. `agrees` is COMPUTED by comparing axes, never
           self-reported (raw confidence is uncalibrated, 2026-07-14).
           Advisory only: never changes a verdict, score, or state.
  contract: run_verify(material_text, rule, checks, primary_trigger_met,
            primary_requirement_met, invoke) -> VerifierResult.
            production_verify_invoke(model_string) binds the schema to a model.
  deps: pydantic; langchain init_chat_model (production path only).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from pydantic import BaseModel, Field


class VerifierVerdict(BaseModel):
    trigger_met: bool = Field(
        description="Independently: does the material trigger this rule?"
    )
    requirement_met: bool | None = Field(
        default=None,
        description="If triggered: is the requirement satisfied? null when not triggered.",
    )
    reason: str = Field(description="1-2 sentences: why you agree or overturn.")


@dataclass(frozen=True)
class VerifierResult:
    agrees: bool
    trigger_met: bool
    requirement_met: bool | None
    reason: str


VERIFY_PROMPT = """You are a SECOND, independent marketing-compliance reviewer.
A first reviewer judged this material against the rule below and concluded:
  trigger_met = {primary_trigger}
  requirement_met = {primary_requirement}

Independently re-judge it. Try to OVERTURN the first reviewer if they are wrong.
Do not defer to them. Decide trigger_met and requirement_met yourself and quote
your reasoning.

RULE (verbatim): {rule_text}
TRIGGER: {trigger_text}  (criteria: {trigger_criteria})
REQUIREMENT: {requirement_text}  (criteria: {requirement_criteria})

MATERIAL:
{material_text}
"""


def build_verify_prompt(
    material_text: str,
    rule: dict,
    trigger: dict,
    requirement: dict,
    primary_trigger_met: bool,
    primary_requirement_met: bool | None,
) -> str:
    return VERIFY_PROMPT.format(
        primary_trigger=primary_trigger_met,
        primary_requirement=primary_requirement_met,
        rule_text=rule["verbatim_text"],
        trigger_text=trigger["text"],
        trigger_criteria=trigger["evidence_criteria"],
        requirement_text=requirement["text"],
        requirement_criteria=requirement["evidence_criteria"],
        material_text=material_text,
    )


def run_verify(
    material_text: str,
    rule: dict,
    checks: list[dict],
    primary_trigger_met: bool,
    primary_requirement_met: bool | None,
    invoke: Callable[[str], VerifierVerdict],
) -> VerifierResult:
    trigger = next(c for c in checks if c["kind"] == "trigger")
    requirement = next(c for c in checks if c["kind"] == "requirement")
    prompt = build_verify_prompt(
        material_text, rule, trigger, requirement,
        primary_trigger_met, primary_requirement_met,
    )
    v = invoke(prompt)
    agrees = (v.trigger_met == primary_trigger_met) and (
        v.requirement_met == primary_requirement_met
    )
    return VerifierResult(
        agrees=agrees,
        trigger_met=v.trigger_met,
        requirement_met=v.requirement_met,
        reason=v.reason,
    )


def production_verify_invoke(model_string: str) -> Callable[[str], VerifierVerdict]:
    """Bind the verifier schema to a chat model (init_chat_model string)."""
    from langchain.chat_models import init_chat_model

    model = init_chat_model(
        model_string, temperature=0, timeout=90, max_retries=2
    ).with_structured_output(VerifierVerdict)

    def invoke(prompt: str) -> VerifierVerdict:
        return model.invoke(prompt)

    return invoke
