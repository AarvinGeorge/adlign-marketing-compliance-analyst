# ---------------------------------------------------------------------------
# models.py — pydantic schemas for structured LLM output + the v2 record.
# Contract: JudgeVerdict is what every judge must return per (page, rule);
#   1..N findings (multi-finding per page-rule fixes the v1 P02 gap).
#   Record mirrors the v1 ground-truth schema exactly, plus additive fields
#   (split, panel, evidence_valid, synthetic) so the product's data model
#   needs no change.
# Deps: pydantic v2.
# ---------------------------------------------------------------------------
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

VerdictStatus = Literal["pass", "flag", "not_applicable", "needs_review"]
IntersectionTag = Literal[
    "all_good", "drifted_but_compliant", "approved_but_non_compliant",
    "unapproved_violation", "na",
]
AxisB = Literal["true", "false", "na"]


class JudgeFinding(BaseModel):
    """One finding by one judge for one (page, rule)."""
    trigger_met: bool = Field(description="Does the rule's trigger condition apply to this page at all?")
    requirement_met: Optional[bool] = Field(description="If triggered: is the rule's requirement satisfied? null when trigger_met is false.")
    axis_a_compliant: bool = Field(description="Axis A: is the material compliant with the rule? Untriggered rules are compliant-by-inapplicability (true).")
    axis_b_matches_approval: AxisB = Field(description="Axis B: does the wording match the approved library entry? 'na' when no library entry governs this rule.")
    intersection_tag: IntersectionTag
    verdict_status: VerdictStatus = Field(description="pass | flag | not_applicable | needs_review. An untriggered rule is not_applicable, NEVER pass. Use needs_review for genuine judgment calls a human policy ruling should settle.")
    evidence_quote: str = Field(description="CONTIGUOUS verbatim quote from the page text proving the judgment. Copy exactly; never stitch sentences from different paragraphs; empty string only when verdict is not_applicable.")
    location: str = Field(description="Where on the page the evidence lives, e.g. 'hero headline', 'pricing card footnote', 'shared footer'.")
    reasoning: str = Field(description="Full reasoning: trigger analysis, requirement analysis, both axes, and the strongest counter-reading you considered.")
    confidence: float = Field(ge=0.0, le=1.0)


class JudgeVerdict(BaseModel):
    """Everything one judge concludes about one (page, rule)."""
    findings: list[JudgeFinding] = Field(min_length=1, description="One finding per distinct issue/aspect. A page can pass a rule for one product mention and fail it for another; report each separately. If the rule simply does not apply, return exactly one not_applicable finding.")


class ArbiterRuling(BaseModel):
    """The 4th model's final call on a non-unanimous finding group."""
    verdict_status: VerdictStatus
    trigger_met: bool
    requirement_met: Optional[bool]
    axis_a_compliant: bool
    axis_b_matches_approval: AxisB
    intersection_tag: IntersectionTag
    evidence_quote: str = Field(description="Contiguous verbatim quote from the page (pick or correct the best judge quote).")
    location: str
    reasoning: str = Field(description="Why this ruling; which judge(s) were right and why the others were not.")
    confidence: float = Field(ge=0.0, le=1.0)
    accept: bool = Field(description="false if the minority finding should produce NO record at all (spurious).")


class ScreenRuleResult(BaseModel):
    rule_id: Literal["R-01", "R-02", "R-03", "R-04"]
    relevant: bool = Field(description="Could this rule plausibly be triggered by anything on this page? Err toward true when in doubt.")
    signal: str = Field(description="Short quote or phrase that makes the rule relevant; empty if not relevant.")
    why: str


class ScreenVerdict(BaseModel):
    results: list[ScreenRuleResult] = Field(min_length=4, max_length=4)


class UrlScore(BaseModel):
    url: str
    r01: int = Field(ge=0, le=3, description="0-3 relevance to R-01 (free-product claims / eligibility disclosure)")
    r02: int = Field(ge=0, le=3, description="0-3 relevance to R-02 (rates / finance charges / APR)")
    r03: int = Field(ge=0, le=3, description="0-3 relevance to R-03 (deposit products / FDIC)")
    r04: int = Field(ge=0, le=3, description="0-3 relevance to R-04 (bonus / reward offers)")
    page_type: str = Field(description="e.g. product, pricing, offer, blog, support, comparison, guarantee")

    def relevance(self) -> dict[str, int]:
        return {"R-01": self.r01, "R-02": self.r02,
                "R-03": self.r03, "R-04": self.r04}


class UrlRanking(BaseModel):
    scores: list[UrlScore]


class SyntheticSpec(BaseModel):
    """Generator output: one authored TurboTax-themed fixture."""
    title: str
    body_markdown: str = Field(description="The full page-like marketing material, realistic TurboTax voice, 150-600 words, markdown.")
    intended_rule_id: Literal["R-01", "R-02", "R-03", "R-04"]
    intended_verdict: VerdictStatus
    intended_intersection_tag: IntersectionTag
    intended_evidence_quote: str = Field(description="The exact contiguous span in body_markdown that carries the violation/pass; must appear verbatim in body_markdown.")
    rationale: str
