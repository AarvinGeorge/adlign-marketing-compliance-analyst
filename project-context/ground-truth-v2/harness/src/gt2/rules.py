# ---------------------------------------------------------------------------
# rules.py — the VERBATIM scorecard, the D-01 library entry, per-rule severity.
# Contract: rule text is EXTRACTED AT RUNTIME from doc 05 §1 (canonical,
#   never paraphrased, never retyped — same doctrine as the product's seed).
#   Severity is the per-rule mode from frozen ground truth v1. D-01 text is
#   pinned here byte-for-byte (verified against the product DB 2026-07-13).
# Deps: stdlib + config.
# ---------------------------------------------------------------------------
from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache

from .config import Paths

# The approved disclosure library (v1 has exactly one entry).
LIBRARY = {
    "D-01": {
        "kind": "disclosure",
        "title": "TurboTax Free eligibility disclosure",
        "approved_text": (
            "~37% of filers qualify. Simple Form 1040 returns only "
            "(no schedules, except for EITC, CTC, student loan interest, "
            "and Schedule 1-A)."
        ),
        "governs_rule": "R-01",
    }
}

RULE_IDS = ("R-01", "R-02", "R-03", "R-04")


@dataclass(frozen=True)
class Rule:
    id: str
    verbatim_text: str
    severity: str
    library_entry_id: str | None


def _extract_scorecard_lines(doc_text: str) -> dict[str, str]:
    """Pull the four numbered scorecard lines from doc 05 §1, verbatim."""
    section = doc_text.split("## 1. The scorecard", 1)[1].split("## 2.", 1)[0]
    out: dict[str, str] = {}
    for m in re.finditer(r"^(\d)\.\s(.+)$", section, flags=re.M):
        out[f"R-0{m.group(1)}"] = m.group(2).rstrip()
    if set(out) != set(RULE_IDS):
        raise RuntimeError(f"scorecard extraction failed: got {sorted(out)}")
    return out


def _severity_modes(v1_path) -> dict[str, str]:
    records = json.loads(v1_path.read_text())["records"]
    by_rule: dict[str, Counter] = {r: Counter() for r in RULE_IDS}
    for rec in records:
        if rec.get("severity"):
            by_rule[rec["rule_id"]][rec["severity"]] += 1
    return {r: (c.most_common(1)[0][0] if c else "High") for r, c in by_rule.items()}


@lru_cache(maxsize=1)
def load_rules_cached(scorecard_doc: str, v1_gt: str) -> tuple[Rule, ...]:
    from pathlib import Path
    texts = _extract_scorecard_lines(Path(scorecard_doc).read_text())
    severities = _severity_modes(Path(v1_gt))
    governed = {v["governs_rule"]: k for k, v in LIBRARY.items()}
    return tuple(
        Rule(id=r, verbatim_text=texts[r], severity=severities[r],
             library_entry_id=governed.get(r))
        for r in RULE_IDS
    )


def load_rules(paths: Paths) -> tuple[Rule, ...]:
    return load_rules_cached(str(paths.scorecard_doc), str(paths.v1_ground_truth))
