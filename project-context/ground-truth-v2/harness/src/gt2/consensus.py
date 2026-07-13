# ---------------------------------------------------------------------------
# consensus.py — turn 3 independent judgments into ground-truth records.
# Contract (locked with Aarvin 2026-07-13): findings from the three judges
#   are pooled per (page, rule) and grouped by evidence overlap
#   (token-Jaccard >= threshold; not_applicable findings group together).
#   Group supported by ALL THREE judges with the same verdict -> definitive
#   record (judgment_source judge_panel). Anything less -> the 4th-model
#   ARBITER sees the page and all opinions and makes the final call
#   (judgment_source judge_panel_arbiter); it may also reject a spurious
#   minority finding (no record). No human in the loop; legitimacy =
#   independence + full recorded provenance.
# Deps: llm, rules, capture, textnorm, models, config.
# ---------------------------------------------------------------------------
from __future__ import annotations

import json

from .config import ARBITER_MODEL, PAGE_TEXT_CAP, Paths
from .capture import load_snapshot_bodies
from .judge import _DEFINITIONS, _judge_system
from .llm import invoke_structured
from .models import ArbiterRuling
from .rules import load_rules
from .textnorm import quote_is_valid


def _group_findings(judges: list[dict]) -> list[list[dict]]:
    """Pool findings across judges; group by VERDICT CLASS (verdict_status,
    intersection_tag) — the v1 semantics: one candidate record per class per
    (page, rule). Judges quoting different spans of the same violation stay
    ONE finding (pilot lesson: overlap-grouping fragmented a unanimous flag
    into three arbiter calls). Distinct records only arise where judgments
    truly diverge (e.g. pass for one product mention, flag for another),
    and those splits go to the arbiter anyway. A judge contributing several
    findings to one class counts once toward support."""
    pool = []
    for j in judges:
        for f in j["findings"]:
            pool.append({**f, "model": j["model"]})
    classes: dict[tuple, list[dict]] = {}
    for f in pool:
        classes.setdefault(
            (f["verdict_status"], f["intersection_tag"]), []).append(f)
    return list(classes.values())


def _panel_provenance(group: list[dict], support: int,
                      arbiter: dict | None) -> dict:
    return {
        "judges": [{"model": f["model"], "verdict_status": f["verdict_status"],
                    "intersection_tag": f["intersection_tag"],
                    "confidence": f["confidence"]} for f in group],
        "support": support,
        "arbiter": arbiter,
    }


def _median_conf(group: list[dict]) -> float:
    vals = sorted(f["confidence"] for f in group)
    return vals[len(vals) // 2]


def consensus(paths: Paths, limit: int | None = None) -> None:
    rules = {r.id: r for r in load_rules(paths)}
    pages = load_snapshot_bodies(paths)
    docs = sorted(paths.judgments.glob("*_R-0*.json"))
    if limit:
        docs = docs[:limit]

    out_path = paths.data / "consensus.json"
    done: dict = json.loads(out_path.read_text()) if out_path.exists() else {}

    for doc_file in docs:
        key = doc_file.stem  # V01_R-01
        if key in done:
            continue
        doc = json.loads(doc_file.read_text())
        pid, rid = doc["page_id"], doc["rule_id"]
        rule = rules[rid]
        body = pages[pid]["body"][:PAGE_TEXT_CAP]
        results = []

        for group in _group_findings(doc["judges"]):
            judges_in = {f["model"] for f in group}
            verdicts = {f["verdict_status"] for f in group}
            if len(judges_in) == 3 and len(verdicts) == 1:
                best = max(group, key=lambda f: (f["evidence_valid"],
                                                 f["confidence"]))
                results.append({
                    "decision": "unanimous",
                    "record_fields": {k: best[k] for k in (
                        "trigger_met", "requirement_met", "axis_a_compliant",
                        "axis_b_matches_approval", "intersection_tag",
                        "evidence_quote", "location", "reasoning",
                        "verdict_status")},
                    "evidence_valid": best["evidence_valid"],
                    "confidence": _median_conf(group),
                    "panel": _panel_provenance(group, 3, None),
                })
                continue

            # non-unanimous -> arbiter
            opinions = json.dumps(
                [{k: f[k] for k in ("model", "verdict_status",
                                    "intersection_tag", "evidence_quote",
                                    "reasoning", "confidence")}
                 for f in group], indent=1)
            system = (_judge_system(rule)
                      + "\n\nYou are the ARBITER. Three independent judges "
                      "reviewed this page; on the finding below they did not "
                      "reach unanimity (or only a minority reported it). "
                      "Read the page yourself, weigh their reasoning, and "
                      "make the final call. Set accept=false ONLY if the "
                      "finding is spurious and should produce no ground-truth "
                      "record at all.")
            user = (f"Page {pid} ({doc['url']}) full text:\n\n{body}\n\n"
                    f"Disputed finding group (judge opinions):\n{opinions}")
            ruling = invoke_structured(paths.cache, ARBITER_MODEL,
                                       ArbiterRuling, system, user)
            r = ruling.model_dump()
            valid = (r["verdict_status"] == "not_applicable"
                     or quote_is_valid(r["evidence_quote"], body))
            if not valid:
                r["verdict_status"] = "needs_review"
            if not r.pop("accept"):
                results.append({"decision": "rejected",
                                "panel": _panel_provenance(
                                    group, len(judges_in),
                                    {"model": ARBITER_MODEL,
                                     "rationale": r["reasoning"]})})
                continue
            arb_conf = r.pop("confidence")
            rationale = r["reasoning"]
            results.append({
                "decision": "arbiter",
                "record_fields": r,
                "evidence_valid": valid,
                "confidence": arb_conf,
                "panel": _panel_provenance(group, len(judges_in),
                                           {"model": ARBITER_MODEL,
                                            "rationale": rationale}),
            })

        done[key] = {"page_id": pid, "rule_id": rid, "results": results}
        kinds = [r["decision"] for r in results]
        print(f"  {key}: {len(results)} group(s) -> {kinds}")
        out_path.write_text(json.dumps(done, indent=1))
    print(f"  consensus for {len(done)} pairs -> {out_path}")
