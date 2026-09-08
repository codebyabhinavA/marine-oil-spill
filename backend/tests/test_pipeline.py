"""
End-to-end smoke test: runs the full M1->M5 pipeline against a throwaway
scene and checks the contract shapes + basic sanity, not exact values (the
synthetic generators are randomized unless seeded). Good first check to
run after changing any module — if this fails, something broke the
contract in docs/API_CONTRACT.md.

Run: pytest backend/tests/test_pipeline.py -v
"""
import os
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from backend.pipeline import run_full_pipeline  # noqa: E402

TEST_SCENE_DIR = "data/runtime/_pytest"
TEST_SCENE_ID = "pytest_scene"


def setup_module():
    os.makedirs(TEST_SCENE_DIR, exist_ok=True)


def teardown_module():
    shutil.rmtree(TEST_SCENE_DIR, ignore_errors=True)


def test_full_pipeline_runs_and_matches_contract():
    report = run_full_pipeline(
        scene_dir=TEST_SCENE_DIR,
        scene_id=TEST_SCENE_ID,
        seed=123,
        ais_seed=456,
        num_vessels=8,
    )

    # M1 — scene
    assert report["scene"]["scene_id"] == TEST_SCENE_ID
    assert "bounds" in report["scene"]

    # M2 — detection
    det = report["detection"]
    assert det["spill_count"] == len(det["spills"])
    assert det["spill_count"] > 0, "synthetic scene should always yield at least one candidate blob"
    confidences = [s["confidence"] for s in det["spills"]]
    assert confidences == sorted(confidences, reverse=True), "spills must be sorted by confidence desc"

    # M3 — hindcast
    hind = report["hindcast"]
    assert hind["track"][0]["hours_before_detection"] == 0.0
    assert hind["track"][-1]["hours_before_detection"] == hind["hindcast_hours"]

    # M4 — AIS
    ais = report["ais_tracking"]
    assert ais["vessels_checked"] == 8
    assert 0 <= ais["candidate_count"] <= ais["vessels_checked"]

    # M5 — attribution
    attr = report["attribution"]
    assert attr["suspect_count"] == ais["candidate_count"]
    scores = [s["final_score"] for s in attr["suspects"]]
    assert scores == sorted(scores, reverse=True), "suspects must be ranked by final_score desc"
    ranks = [s["rank"] for s in attr["suspects"]]
    assert ranks == list(range(1, len(ranks) + 1)), "ranks must be contiguous starting at 1"
    for s in attr["suspects"]:
        assert 0.0 <= s["final_score"] <= 1.0


def test_final_report_written_to_disk():
    path = os.path.join(TEST_SCENE_DIR, f"{TEST_SCENE_ID}_final_report.json")
    assert os.path.exists(path)
