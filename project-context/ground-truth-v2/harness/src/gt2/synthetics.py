# ---------------------------------------------------------------------------
# synthetics.py — 100 TurboTax-THEMED fixtures, generated then panel-validated.
# Contract (Aarvin 2026-07-13): TurboTax voice, not fictional brands. A
#   deterministic coverage matrix (rule x verdict x violation mode x surface x
#   phrasing style) drives a generator LLM; HALF the flag fixtures must phrase
#   the violation WITHOUT obvious trigger keywords (attacks the keyword blind
#   spot). Every fixture is then judged by the SAME 3-judge panel; majority
#   verdict must match the intent or the fixture is QUARANTINED for review,
#   never silently kept. Validated fixtures become records
#   (judgment_source synthetic_intended, synthetic true, page-level split).
# Deps: llm, judge, rules, textnorm, models, config.
# ---------------------------------------------------------------------------
from __future__ import annotations

import json
from collections import Counter

from .config import RANK_MODEL, SPLIT_SALT, TEST_FRACTION, Paths
from .judge import judge_pair
from .llm import invoke_structured
from .models import SyntheticSpec
from .rules import load_rules
from .textnorm import quote_is_valid, split_for

# verdict mix per rule (25 each, 100 total)
_MIX = [("flag", 11), ("pass", 8), ("not_applicable", 4), ("needs_review", 2)]

_MODES = {
    "R-01": {
        "flag": ["free claim with NO eligibility disclosure anywhere",
                 "disclosure present but far from the free claim (placement)",
                 "disclosure missing the schedule exceptions",
                 "wrong qualifying percentage stated",
                 "wording drifted from the approved D-01 text (content equivalent)",
                 "free claim in a comparison table, disclosure absent"],
        "pass": ["free claim with the approved disclosure right underneath",
                 "free claim with a compliant, complete disclosure variant"],
        "not_applicable": ["paid product page, free tier never mentioned",
                           "tax-tips article with no free-product claim"],
        "needs_review": ["free mention only in a legal footnote (strict-vs-practical placement call)",
                         "ambiguous 'file at no cost' phrasing with partial disclosure"],
    },
    "R-02": {
        "flag": ["interest rate stated as plain % without APR",
                 "monthly finance charge stated, APR never given",
                 "promotional 'X% interest' loan offer without APR",
                 "rate buried in fine print, not stated as APR",
                 "pay-later plan quoting a rate without APR",
                 "refund-advance loan describing cost as a rate, no APR"],
        "pass": ["loan offer stating the rate as APR",
                 "0% APR refund advance stated correctly"],
        "not_applicable": ["product page with no financing and no rates",
                           "loan mentioned with no rate or charge stated"],
        "needs_review": ["'no-cost loan' claim where whether a rate was 'stated' is debatable",
                         "fee stated in dollars only; whether it implies a finance-charge rate is a judgment call"],
    },
    "R-03": {
        "flag": ["deposit account with FDIC coverage overstated via a bank network (e.g. up to $5M)",
                 "deposit product advertised with no FDIC language",
                 "FDIC mentioned without the $250,000-through-[Bank] formulation",
                 "checking/savings feature with vague 'insured' claim",
                 "deposit product naming the wrong coverage amount",
                 "FDIC language attributed to the fintech instead of the partner bank"],
        "pass": ["deposit product with the exact required FDIC formulation",
                 "savings feature with correct $250,000 through partner Bank language"],
        "not_applicable": ["tax-filing page with no deposit product",
                           "credit product page (not a deposit product)"],
        "needs_review": ["whether the advertised feature is a 'deposit product' at all is debatable",
                         "FDIC language present but the through-Bank attribution is ambiguous"],
    },
    "R-04": {
        "flag": ["bonus offer missing the APY using that term",
                 "bonus with no time requirement disclosed",
                 "bonus with no minimum balance disclosed",
                 "bonus omitting when it will be provided",
                 "referral reward with account-opening minimum omitted",
                 "bonus disclosing some but not all applicable terms"],
        "pass": ["bonus offer disclosing APY, time, minimums, and payout timing",
                 "general 'get a bonus when you open an account' statement PLUS full terms nearby"],
        "not_applicable": ["page with no bonus or reward offer",
                           "general 'bonus checking' statement only (exemption: does not trigger)"],
        "needs_review": ["bonus terms split across a modal link (clear-and-conspicuous judgment call)",
                         "whether the promotion is a 'bonus' or a discount is debatable"],
    },
}
_SURFACES = ["product landing page", "pricing page section", "blog post",
             "comparison page", "promo banner + footer block"]


def _build_matrix(count: int) -> list[dict]:
    """Round-robin across rules so ANY prefix (count < 100) stays balanced
    per rule; sids are assigned after interleaving."""
    per_rule: dict[str, list[dict]] = {}
    for rule_id, modes in _MODES.items():
        specs = []
        for verdict, n in _MIX:
            pool = modes[verdict]
            for k in range(n):
                specs.append({
                    "rule_id": rule_id, "verdict": verdict,
                    "mode": pool[k % len(pool)],
                    # half the flags hide their trigger keywords on purpose
                    "stealth": verdict == "flag" and k % 2 == 1,
                })
        per_rule[rule_id] = specs
    interleaved: list[dict] = []
    depth = max(len(v) for v in per_rule.values())
    for k in range(depth):
        for rule_id in _MODES:
            if k < len(per_rule[rule_id]):
                interleaved.append(per_rule[rule_id][k])
    for i, spec in enumerate(interleaved, 1):
        spec["sid"] = f"S{i:03d}"
        spec["surface"] = _SURFACES[i % len(_SURFACES)]
    return interleaved[:count]


def synthetics(paths: Paths, count: int = 100, limit: int | None = None) -> None:
    rules = {r.id: r for r in load_rules(paths)}
    out_path = paths.synthetics_dir / "synthetics_validated.json"
    quarantine_path = paths.synthetics_dir / "quarantine.json"
    state = {"records": [], "quarantine": []}
    if out_path.exists():
        state["records"] = json.loads(out_path.read_text())["records"]
    if quarantine_path.exists():
        state["quarantine"] = json.loads(quarantine_path.read_text())
    done_ids = ({r["page_id"] for r in state["records"]}
                | {q["sid"] for q in state["quarantine"]})

    todo = [s for s in _build_matrix(count) if s["sid"] not in done_ids]
    if limit:
        todo = todo[:limit]
    print(f"  fixtures to build: {len(todo)} (done: {len(done_ids)})")

    for spec in todo:
        rule = rules[spec["rule_id"]]
        stealth = ("\nIMPORTANT: phrase the problematic content WITHOUT the "
                   "obvious trigger keywords — a compliance system relying on "
                   "keyword matching should struggle, but a careful analyst "
                   "reading meaning should still catch it."
                   if spec["stealth"] else "")
        system = (
            "You author realistic TurboTax marketing fixtures for a "
            "compliance ground-truth dataset. Write in authentic Intuit "
            "TurboTax voice (products: TurboTax Free Edition, Refund "
            "Advance, Credit Karma Money, referral program). The fixture "
            "must be self-contained page-like markdown, 150-600 words, "
            "realistic enough to pass as a real page."
        )
        user = (
            f"Rule (verbatim): {rule.verbatim_text}\n\n"
            f"Author one fixture: surface = {spec['surface']}; intended "
            f"verdict for this rule = {spec['verdict']}; scenario = "
            f"{spec['mode']}.{stealth}\n"
            "intended_evidence_quote must appear verbatim and contiguous in "
            "body_markdown (empty string only for not_applicable)."
        )
        fx = invoke_structured(paths.cache, RANK_MODEL, SyntheticSpec,
                               system, user)
        body = fx.body_markdown
        if (spec["verdict"] != "not_applicable"
                and not quote_is_valid(fx.intended_evidence_quote, body)):
            state["quarantine"].append(
                {**spec, "why": "generator evidence span not found in body"})
            _save(out_path, quarantine_path, state)
            print(f"  {spec['sid']} QUARANTINED (bad generator span)")
            continue

        # validate with the SAME 3-judge panel used for real pages
        doc = judge_pair(paths, rule, spec["sid"],
                         f"synthetic:{spec['sid']}", body)
        primaries = []
        for j in doc["judges"]:
            flags = [f for f in j["findings"]
                     if f["verdict_status"] != "not_applicable"]
            primaries.append(flags[0] if flags else j["findings"][0])
        votes = Counter(p["verdict_status"] for p in primaries)
        top, n_top = votes.most_common(1)[0]

        if top != spec["verdict"] or n_top < 2:
            state["quarantine"].append(
                {**spec, "why": f"panel voted {dict(votes)}, intended "
                                f"{spec['verdict']}", "title": fx.title})
            print(f"  {spec['sid']} QUARANTINED (panel {dict(votes)} vs "
                  f"intent {spec['verdict']})")
        else:
            fname = f"{spec['sid']}_{spec['rule_id']}.md"
            (paths.synthetics_dir / fname).write_text(
                f"---\nid: {spec['sid']}\nrule: {spec['rule_id']}\n"
                f"intended: {spec['verdict']}\nsynthetic: true\n---\n\n{body}")
            match = next((p for p in primaries
                          if p["verdict_status"] == top), primaries[0])
            state["records"].append({
                "id": f"GT2-{spec['sid']}-{spec['rule_id']}",
                "page_id": spec["sid"], "rule_id": spec["rule_id"],
                **{k: match[k] for k in (
                    "trigger_met", "requirement_met", "axis_a_compliant",
                    "axis_b_matches_approval", "intersection_tag",
                    "location", "reasoning")},
                "evidence_quote": (fx.intended_evidence_quote
                                   if spec["verdict"] != "not_applicable"
                                   else ""),
                "verdict_status": spec["verdict"],
                "severity": rule.severity,
                "judgment_source": "synthetic_intended",
                "confidence": 1.0, "evidence_valid": True,
                "panel": {"judges": [
                    {"model": j["model"],
                     "verdict_status": p["verdict_status"],
                     "intersection_tag": p["intersection_tag"],
                     "confidence": p["confidence"]}
                    for j, p in zip(doc["judges"], primaries)],
                    "support": n_top, "arbiter": None},
                "synthetic": True, "stealth": spec["stealth"],
                "split": split_for(spec["sid"], SPLIT_SALT, TEST_FRACTION),
            })
            print(f"  {spec['sid']} OK ({spec['verdict']}, "
                  f"support {n_top}/3, stealth={spec['stealth']})")
        _save(out_path, quarantine_path, state)

    print(f"  validated: {len(state['records'])}, "
          f"quarantined: {len(state['quarantine'])}")


def _save(out_path, quarantine_path, state) -> None:
    out_path.write_text(json.dumps({"records": state["records"]}, indent=1))
    quarantine_path.write_text(json.dumps(state["quarantine"], indent=1))
