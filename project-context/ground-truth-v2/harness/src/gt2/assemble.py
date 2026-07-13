# ---------------------------------------------------------------------------
# assemble.py — build data/ground_truth_v2.json (v1-compatible + additive).
# Contract: records come from three sources: consensus results (panel /
#   arbiter), screen-negative pairs (honest not_applicable,
#   judgment_source semantic_screen), and validated synthetics. Split is
#   deterministic per PAGE (sha256, 70/30) so no page straddles train/test.
#   The frozen v1 dataset is untouched and not merged.
# Deps: rules, capture, textnorm, config.
# ---------------------------------------------------------------------------
from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime

from .config import JUDGE_MODELS, ARBITER_MODEL, SPLIT_SALT, TEST_FRACTION, Paths
from .capture import load_snapshot_bodies
from .rules import load_rules
from .textnorm import split_for


def assemble(paths: Paths) -> None:
    rules = {r.id: r for r in load_rules(paths)}
    pages = load_snapshot_bodies(paths)
    consensus_path = paths.data / "consensus.json"
    consensus = (json.loads(consensus_path.read_text())
                 if consensus_path.exists() else {})
    screens = (json.loads(paths.screen.read_text())
               if paths.screen.exists() else {})

    records: list[dict] = []

    # 1) panel/arbiter records
    for key, doc in sorted(consensus.items()):
        pid, rid = doc["page_id"], doc["rule_id"]
        n = 0
        for res in doc["results"]:
            if res["decision"] == "rejected":
                continue
            n += 1
            f = res["record_fields"]
            records.append({
                "id": f"GT2-{pid}-{rid}" + (f"-{n}" if n > 1 else ""),
                "page_id": pid, "rule_id": rid,
                **{k: f[k] for k in (
                    "trigger_met", "requirement_met", "axis_a_compliant",
                    "axis_b_matches_approval", "intersection_tag",
                    "evidence_quote", "location", "reasoning",
                    "verdict_status")},
                "severity": rules[rid].severity,
                "judgment_source": ("judge_panel"
                                    if res["decision"] == "unanimous"
                                    else "judge_panel_arbiter"),
                "confidence": res["confidence"],
                "evidence_valid": res["evidence_valid"],
                "panel": res["panel"],
                "synthetic": False,
                "split": split_for(pid, SPLIT_SALT, TEST_FRACTION),
            })

    # 2) screen-negative not_applicable records (honest labels)
    judged_pairs = {(d["page_id"], d["rule_id"]) for d in consensus.values()}
    for pid, results in sorted(screens.items()):
        if pid not in pages:
            continue
        for res in results:
            rid = res["rule_id"]
            if res["relevant"] or (pid, rid) in judged_pairs:
                continue
            records.append({
                "id": f"GT2-{pid}-{rid}", "page_id": pid, "rule_id": rid,
                "trigger_met": False, "requirement_met": None,
                "axis_a_compliant": True, "axis_b_matches_approval": "na",
                "intersection_tag": "na", "severity": rules[rid].severity,
                "evidence_quote": "", "location": "",
                "reasoning": f"Semantic screen: {res['why']}",
                "verdict_status": "not_applicable",
                "judgment_source": "semantic_screen",
                "confidence": 0.8, "evidence_valid": True,
                "panel": None, "synthetic": False,
                "split": split_for(pid, SPLIT_SALT, TEST_FRACTION),
            })

    # 3) validated synthetics
    syn_path = paths.synthetics_dir / "synthetics_validated.json"
    if syn_path.exists():
        records.extend(json.loads(syn_path.read_text())["records"])

    by_verdict = Counter(r["verdict_status"] for r in records)
    by_split = Counter(r["split"] for r in records)
    by_source = Counter(r["judgment_source"] for r in records)
    meta = {
        "name": "Shiboleth ground truth v2 (TurboTax, semantic discovery + 3-LLM judge panel)",
        "assembled_at": datetime.now(UTC).isoformat(),
        "status": "DRAFT until Aarvin approves; then this dataset DEFINES the product's direction (2026-07-13). v1 remains frozen as the historical baseline.",
        "judges": JUDGE_MODELS, "arbiter": ARBITER_MODEL,
        "split": {"method": f"sha256(page_id) page-level, salt {SPLIT_SALT}",
                  "test_fraction": TEST_FRACTION,
                  "discipline": "system improvement may iterate on train ONLY; test is quarantined for held-out measurement"},
        "counts": {"records": len(records), "by_verdict": dict(by_verdict),
                   "by_split": dict(by_split), "by_source": dict(by_source)},
    }
    paths.records.write_text(json.dumps(
        {"_meta": meta, "records": records}, indent=1))
    print(f"  {len(records)} records -> {paths.records}")
    print(f"  verdicts: {dict(by_verdict)}")
    print(f"  split:    {dict(by_split)}")
    print(f"  sources:  {dict(by_source)}")
