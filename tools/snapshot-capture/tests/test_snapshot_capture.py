# ---------------------------------------------------------------------------
# test_snapshot_capture.py — fast, offline unit tests (no network/browser).
# Guards the determinism guarantee and the pure helpers.
# ---------------------------------------------------------------------------
from __future__ import annotations

from snapshot_capture.manifest import build_manifest, write_manifest
from snapshot_capture.quality import classify
from snapshot_capture.snapshot_io import (
    body_sha256,
    normalize_body,
    parse_front_matter,
    slug,
    write_snapshot,
)
from snapshot_capture.triggers import compute_triggers


def test_hash_stable_under_trailing_whitespace():
    a = "Refund Advance has 0% APR.\n\n"
    b = "Refund Advance has 0% APR."
    assert body_sha256(a) == body_sha256(b)


def test_front_matter_roundtrip(tmp_path):
    body = "Free* to file.\n\n*~37% of filers qualify.\n"
    fields = {
        "id": "P99", "url": "https://x.test/", "discovery": "free",
        "fetched_at": "2026-07-09T00:00:00Z", "fetcher": "crawl4ai",
        "content_sha256": body_sha256(body), "quality": "good", "notes": "n",
    }
    path = tmp_path / "P99_x.md"
    write_snapshot(path, fields, body)
    fm, parsed_body = parse_front_matter(path.read_text())
    assert fm["id"] == "P99"
    assert fm["fetcher"] == "crawl4ai"
    # Body preserved verbatim (the fine print survives).
    assert "~37% of filers qualify" in parsed_body
    assert body_sha256(parsed_body) == fields["content_sha256"]


def test_triggers_word_boundary():
    t = compute_triggers("This is FREE. FDIC-insured deposit. 0% APR bonus.")
    assert t == {"free": True, "apr_finance": True,
                 "fdic_deposit": True, "bonus_reward": True}
    # "freedom" must not trip the free trigger.
    assert compute_triggers("freedom of choice")["free"] is False


def test_quality_thresholds():
    assert classify("", False)[0] == "failed"
    assert classify("word " * 10, True)[0] == "thin"
    assert classify("word " * 200, True)[0] == "good"


def test_slug():
    assert slug("https://turbotax.intuit.com/personal-taxes/online/free-edition.jsp") == "free-edition"
    assert slug("https://turbotax.intuit.com/") == "turbotax-intuit-com"


def test_normalize_body_idempotent():
    once = normalize_body("  hi \n\n\n")
    twice = normalize_body(once)
    assert once == twice


def test_manifest_deterministic(tmp_path):
    snaps = tmp_path / "snapshots"
    snaps.mkdir()
    for pid, body in [("P02", "free " * 200), ("P01", "APR " * 200)]:
        fields = {
            "id": pid, "url": f"https://x.test/{pid}", "discovery": "free",
            "fetched_at": "2026-07-09T00:00:00Z", "fetcher": "crawl4ai",
            "content_sha256": body_sha256(body), "quality": "good", "notes": "n",
        }
        write_snapshot(snaps / f"{pid}_x.md", fields, body)

    m1 = build_manifest(snaps)
    write_manifest(tmp_path / "m1.json", m1)
    m2 = build_manifest(snaps)
    write_manifest(tmp_path / "m2.json", m2)

    # Byte-identical across rebuilds, and sorted by id (P01 before P02).
    assert (tmp_path / "m1.json").read_bytes() == (tmp_path / "m2.json").read_bytes()
    assert [p["id"] for p in m1["pages"]] == ["P01", "P02"]
    assert m1["pages"][0]["triggers"]["apr_finance"] is True
