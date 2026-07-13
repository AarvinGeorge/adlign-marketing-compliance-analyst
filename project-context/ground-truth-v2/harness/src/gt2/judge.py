# ---------------------------------------------------------------------------
# judge.py — the 3-LLM judge panel. One verdict per judge per (page, rule).
# Contract: each judge independently sees the FULL page text (cap only guards
#   degenerate pages — the v1 iter-6 truncation lesson), the verbatim rule,
#   the D-01 approved wording, the axis/verdict definitions, and two worked
#   v1 examples. Evidence quotes are programmatically validated (contiguous
#   substring after normalization); one retry with explicit feedback; still
#   invalid -> the finding is forced to needs_review with evidence_valid
#   false. Judges never see each other's output. Results:
#   data/judgments/<page>_<rule>.json with all three verdicts.
# Deps: llm, rules, capture, textnorm, models, config.
# ---------------------------------------------------------------------------
from __future__ import annotations

import json

from .config import JUDGE_MODELS, PAGE_TEXT_CAP, Paths
from .capture import load_snapshot_bodies
from .llm import invoke_structured
from .models import JudgeVerdict
from .rules import LIBRARY, Rule, load_rules
from .textnorm import quote_is_valid

_DEFINITIONS = """
Definitions (binding):
- trigger_met: does the rule's IF-condition apply to anything on this page?
- An untriggered rule is verdict not_applicable, NEVER pass.
- Axis A (compliant): does the material satisfy the rule's requirement?
- Axis B (matches approval): does the wording match the approved library
  entry verbatim-or-equivalent? Only rules governed by a library entry have
  an axis B; otherwise 'na'.
- intersection_tag: all_good (A yes, B yes/na) | drifted_but_compliant
  (A yes, B no) | approved_but_non_compliant (A no, B yes) |
  unapproved_violation (A no, B no/na) | na (untriggered).
- verdict_status: pass (triggered, requirement met, no drift) | flag
  (triggered and non-compliant OR drifted) | not_applicable (untriggered) |
  needs_review (a genuine judgment call a human policy ruling should settle
  — e.g. strict-vs-practical placement readings; use it honestly, not as an
  escape hatch).
- evidence_quote: a CONTIGUOUS verbatim span copied from the page text.
  Never stitch sentences from different places. Never paraphrase.
- Report MULTIPLE findings when a page genuinely carries distinct judgments
  for this rule (e.g. one product mention passes, another fails).
- In reasoning, state the strongest counter-reading and why you rejected it.
""".strip()

# Two worked v1 examples (frozen ground truth): one drift flag, one pass.
_EXAMPLES = """
Worked example 1 (flag, drifted_but_compliant): the shared footer's Free
Edition footnote read "TurboTax Free Edition ($0 Federal + $0 State + $0 To
File) is available for those filing simple Form 1040 returns only (no forms
or schedules except as needed to claim the Earned Income Tax Credit, Child
Tax Credit, student loan interest, and Schedule 1-A). More details are
available here. Roughly 37% of taxpayers qualify." Ruling: R-01 trigger met
(free product mentioned), requirement substantively met (eligibility % +
simple-1040 limitation both present) so axis A compliant, BUT the wording
drifts from the approved D-01 text ("Roughly 37% of taxpayers qualify" vs
approved "~37% of filers qualify") so axis B false -> drifted_but_compliant,
verdict flag.

Worked example 2 (pass): footer text "TurboTax Refund Advance is a loan based
upon your anticipated refund and is not the refund itself. 0% APR and $0 loan
fees." Ruling: R-02 trigger met (a rate of finance charge is stated),
requirement met (stated as APR, literally "0% APR"), axis A compliant, no
library entry governs APR language so axis B na -> all_good, verdict pass.
""".strip()


def _judge_system(rule: Rule) -> str:
    lib = ""
    if rule.library_entry_id:
        entry = LIBRARY[rule.library_entry_id]
        lib = (f"\n\nApproved library entry {rule.library_entry_id} "
               f"({entry['title']}) — axis B compares against this text:\n"
               f"\"{entry['approved_text']}\"")
    return (
        "You are a senior marketing-compliance analyst for fintech/bank "
        "partnership marketing, judging Intuit TurboTax web pages. You are "
        "establishing GROUND TRUTH: your judgment will grade an automated "
        "compliance system, so be rigorous, evidence-bound, and honest about "
        "ambiguity. Judge this ONE rule against the page provided.\n\n"
        f"Rule {rule.id} (verbatim, canonical — never paraphrase it):\n"
        f"{rule.verbatim_text}{lib}\n\n{_DEFINITIONS}\n\n{_EXAMPLES}"
    )


def judge_pair(paths: Paths, rule: Rule, page_id: str, url: str,
               body: str) -> dict:
    """Run all three judges on one (page, rule). Returns the judgment doc."""
    text = body[:PAGE_TEXT_CAP]
    system = _judge_system(rule)
    user = f"Page {page_id} ({url}) full text:\n\n{text}"

    def _one_judge(model: str) -> dict:
        v = invoke_structured(paths.cache, model, JudgeVerdict, system, user)
        findings = [f.model_dump() for f in v.findings]
        # evidence validation + one retry with explicit feedback
        bad = [f for f in findings
               if f["verdict_status"] != "not_applicable"
               and not quote_is_valid(f["evidence_quote"], text)]
        if bad:
            feedback = (
                user + "\n\nYour previous answer contained evidence quotes "
                "that are NOT contiguous verbatim spans of the page text: "
                + json.dumps([f["evidence_quote"] for f in bad])
                + "\nRe-judge. Copy each evidence quote EXACTLY as one "
                "contiguous span from the page text above."
            )
            v = invoke_structured(paths.cache, model, JudgeVerdict, system,
                                  feedback)
            findings = [f.model_dump() for f in v.findings]
        for f in findings:
            valid = (f["verdict_status"] == "not_applicable"
                     or quote_is_valid(f["evidence_quote"], text))
            f["evidence_valid"] = valid
            if not valid:
                f["verdict_status"] = "needs_review"  # never invented evidence
        return {"model": model, "findings": findings}

    # the three judges are independent by design -> run them concurrently
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=len(JUDGE_MODELS)) as ex:
        verdicts = list(ex.map(_one_judge, JUDGE_MODELS))
    return {"page_id": page_id, "rule_id": rule.id, "url": url,
            "judges": verdicts}


def judge(paths: Paths, limit: int | None = None) -> None:
    rules = {r.id: r for r in load_rules(paths)}
    pages = load_snapshot_bodies(paths)
    screens = json.loads(paths.screen.read_text())

    pairs = [(pid, res["rule_id"]) for pid, results in screens.items()
             for res in results if res["relevant"] and pid in pages]
    todo = [(p, r) for p, r in sorted(pairs)
            if not (paths.judgments / f"{p}_{r}.json").exists()]
    if limit:
        todo = todo[:limit]
    print(f"  panel pairs: {len(pairs)} relevant, {len(todo)} to judge")

    from concurrent.futures import ThreadPoolExecutor, as_completed

    def _run(pid: str, rid: str) -> tuple[str, str, dict]:
        doc = judge_pair(paths, rules[rid], pid, pages[pid]["url"],
                         pages[pid]["body"])
        (paths.judgments / f"{pid}_{rid}.json").write_text(
            json.dumps(doc, indent=1))
        return pid, rid, doc

    with ThreadPoolExecutor(max_workers=3) as ex:  # 3 pairs x 3 judges = 9
        futures = [ex.submit(_run, pid, rid) for pid, rid in todo]
        for i, fut in enumerate(as_completed(futures), 1):
            pid, rid, doc = fut.result()
            summary = ["/".join(sorted({f["verdict_status"]
                                        for f in j["findings"]}))
                       for j in doc["judges"]]
            print(f"  [{i}/{len(todo)}] {pid} {rid}: {summary}")
