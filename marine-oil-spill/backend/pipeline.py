"""
backend/pipeline.py

Wires M1 -> M2 -> M3 -> M4 -> M5 together into one call. This is what
main.py's API calls, and what run_demo.py (repo root) calls for a
no-server, just-run-it-in-a-terminal demo. Each stage is still fully
independent and runnable on its own (see the __main__ block in every
module) — this file just saves everyone from typing five commands.

Output: <scene_dir>/<scene_id>_final_report.json — one JSON a frontend
(or a judge) can read to get the whole story: the scene, the detected
spill(s), the estimated origin + drift track, and the ranked suspect
vessel list.
"""
from __future__ import annotations
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__) + "/..")
from backend.satellite.generate_test_scene import generate_scene  # noqa: E402
from backend.satellite.preprocessing import preprocess_scene  # noqa: E402
from backend.satellite.detection import detect_spills  # noqa: E402
from backend.drift.hindcasting import hindcast_from_detection_file  # noqa: E402
from backend.ais.generate_test_ais import generate_fleet  # noqa: E402
from backend.ais.tracking import track_vessels  # noqa: E402
from backend.attribution.ranking import rank_candidates  # noqa: E402


def run_full_pipeline(
    scene_dir: str = "data/runtime",
    scene_id: str = "demo_scene_01",
    seed: int | None = 42,
    ais_seed: int | None = 7,
    num_vessels: int = 10,
    regenerate_scene: bool = True,
) -> dict:
    os.makedirs(scene_dir, exist_ok=True)

    # M1 — get a scene (synthetic for the demo) and preprocess it.
    meta_path = os.path.join(scene_dir, f"{scene_id}_meta.json")
    if regenerate_scene or not os.path.exists(meta_path):
        generate_scene(out_dir=scene_dir, scene_id=scene_id, seed=seed)
    preprocess_scene(scene_dir, scene_id)

    # M2 — detect candidate spill blobs.
    detection = detect_spills(scene_dir, scene_id)
    if not detection["spills"]:
        raise ValueError(f"No spill detected in {scene_id}; nothing to hindcast/attribute.")

    # M3 — backtrack the highest-confidence blob to an estimated origin.
    hindcast = hindcast_from_detection_file(scene_dir, scene_id)

    # M4 — correlate AIS traffic against the drift path.
    generate_fleet(
        out_dir=scene_dir,
        scene_id=scene_id,
        suspect_lon=hindcast["estimated_origin"]["lon"],
        suspect_lat=hindcast["estimated_origin"]["lat"],
        suspect_time_iso=hindcast["track"][-1]["timestamp"],
        detection_time_iso=hindcast["track"][0]["timestamp"],
        num_vessels=num_vessels,
        seed=ais_seed,
    )
    tracking = track_vessels(scene_dir, scene_id)

    # M5 — score and rank the shortlisted vessels.
    attribution = rank_candidates(scene_dir, scene_id)

    with open(meta_path) as f:
        meta = json.load(f)

    report = {
        "scene_id": scene_id,
        "scene": meta,
        "detection": detection,
        "hindcast": hindcast,
        "ais_tracking": {
            "vessels_checked": tracking["vessels_checked"],
            "radius_km": tracking["radius_km"],
            "candidate_count": tracking["candidate_count"],
        },
        "attribution": attribution,
    }

    out_path = os.path.join(scene_dir, f"{scene_id}_final_report.json")
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)

    return report


if __name__ == "__main__":
    scene_id = sys.argv[1] if len(sys.argv) > 1 else "demo_scene_01"
    report = run_full_pipeline(scene_id=scene_id)
    top = report["attribution"]["suspects"]
    print(f"\n=== {scene_id}: pipeline complete ===")
    print(f"Spills detected: {report['detection']['spill_count']}")
    print(f"Estimated origin: {report['hindcast']['estimated_origin']}")
    print(f"AIS candidates shortlisted: {report['ais_tracking']['candidate_count']}")
    if top:
        print(f"Top suspect: {top[0]['name']} ({top[0]['vessel_type']}) — score {top[0]['final_score']}")
    print(f"Full report: data/runtime/{scene_id}_final_report.json\n")
