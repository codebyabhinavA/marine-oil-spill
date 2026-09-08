"""
M5 — backend/attribution/ranking.py

Consumes M4's candidate list (vessels that passed near the estimated spill
origin at a matching time) and turns "who was nearby" into a ranked,
scored suspect list — the actual deliverable NTRO's problem statement asks
for: not just detection, but attribution.

Score is a weighted blend of four signals, each explainable to a judge
(swap any of these for a trained model later without touching the output
contract):

  1. proximity   (50%) — closer closest-approach distance is stronger
                          evidence. Linear falloff to 0 at the candidate
                          radius.
  2. vessel_type (25%) — tankers/bulk carriers/cargo ships realistically
                          carry the bunker fuel or cargo oil volumes that
                          produce a slick this size; fishing/passenger
                          vessels essentially don't.
  3. speed_anomaly (15%) — a vessel slowing sharply right at the moment of
                          closest approach is consistent with a discharge,
                          transfer, or mechanical stop; cruising at normal
                          transit speed is not.
  4. track_consistency (10%) — a vessel that stayed broadly near the whole
                          drift path (not just one lucky instant) is more
                          convincing than one with a single close ping.

Run directly against a demo candidate set:
    python3 -m backend.attribution.ranking data/runtime demo_scene_01
"""
from __future__ import annotations
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from backend.common.geo import haversine_km  # noqa: E402
from backend.ais.tracking import _interpolate_position  # noqa: E402

# Higher = more plausible as the source of a bulk-liquid spill.
VESSEL_TYPE_RISK = {
    "Tanker": 1.00,
    "Bulk Carrier": 0.70,
    "Cargo": 0.60,
    "Container": 0.45,
    "Fishing": 0.15,
    "Passenger": 0.10,
}
DEFAULT_TYPE_RISK = 0.30

# A drop of at least this many knots right at closest approach reads as
# a meaningful slow-down/stop rather than normal speed variation.
SPEED_ANOMALY_KNOTS = 4.0

WEIGHTS = {"proximity": 0.50, "vessel_type": 0.25, "speed_anomaly": 0.15, "track_consistency": 0.10}


def _proximity_score(closest_km: float, radius_km: float) -> float:
    return max(0.0, 1.0 - closest_km / radius_km)


def _vessel_type_score(vessel_type: str) -> float:
    return VESSEL_TYPE_RISK.get(vessel_type, DEFAULT_TYPE_RISK)


def _speed_anomaly_score(vessel_track: list[dict], closest_time_iso: str) -> float:
    """
    Compares the vessel's speed AT closest approach against its own
    average cruising speed elsewhere in the track. A big relative drop
    scores high; steady speed scores 0.
    """
    if not vessel_track:
        return 0.0
    speeds = [p["speed_knots"] for p in vessel_track if "speed_knots" in p]
    if not speeds:
        return 0.0
    avg_speed = sum(speeds) / len(speeds)

    from backend.ais.tracking import _speed_near  # local import, avoids cycle at module load

    at_match = _speed_near(vessel_track, closest_time_iso)
    if at_match is None or avg_speed <= 0:
        return 0.0
    drop = max(0.0, avg_speed - at_match)
    return min(drop / max(SPEED_ANOMALY_KNOTS, 1e-6), 1.0)


def _track_consistency_score(vessel_track: list[dict], hindcast_track: list[dict], radius_km: float) -> float:
    """
    Fraction of hindcast track points where this vessel had ANY AIS
    coverage within radius_km — rewards vessels that shadowed the drift
    path broadly, not just a single close ping.
    """
    if not hindcast_track:
        return 0.0
    within = 0
    covered = 0
    for hpoint in hindcast_track:
        pos = _interpolate_position(vessel_track, hpoint["timestamp"])
        if pos is None:
            continue
        covered += 1
        dist = haversine_km(hpoint["lon"], hpoint["lat"], pos[0], pos[1])
        if dist <= radius_km:
            within += 1
    if covered == 0:
        return 0.0
    return within / covered


def rank_candidates(scene_dir: str, scene_id: str) -> dict:
    hindcast_path = os.path.join(scene_dir, f"{scene_id}_hindcast.json")
    candidates_path = os.path.join(scene_dir, f"{scene_id}_ais_candidates.json")
    ais_path = os.path.join(scene_dir, f"{scene_id}_ais_data.json")

    with open(hindcast_path) as f:
        hindcast = json.load(f)
    with open(candidates_path) as f:
        tracking = json.load(f)
    with open(ais_path) as f:
        ais = json.load(f)

    vessel_by_mmsi = {v["mmsi"]: v for v in ais["vessels"]}
    radius_km = tracking["radius_km"]

    ranked = []
    for cand in tracking["candidates"]:
        vessel = vessel_by_mmsi[cand["mmsi"]]
        prox = _proximity_score(cand["closest_approach_km"], radius_km)
        vtype = _vessel_type_score(cand["vessel_type"])
        speed = _speed_anomaly_score(vessel["track"], cand["closest_approach_time"])
        consistency = _track_consistency_score(vessel["track"], hindcast["track"], radius_km)

        final_score = (
            WEIGHTS["proximity"] * prox
            + WEIGHTS["vessel_type"] * vtype
            + WEIGHTS["speed_anomaly"] * speed
            + WEIGHTS["track_consistency"] * consistency
        )

        ranked.append(
            {
                "mmsi": cand["mmsi"],
                "name": cand["name"],
                "vessel_type": cand["vessel_type"],
                "flag": cand["flag"],
                "closest_approach_km": cand["closest_approach_km"],
                "closest_approach_time": cand["closest_approach_time"],
                "vessel_position_at_match": cand["vessel_position_at_match"],
                "scores": {
                    "proximity": round(prox, 3),
                    "vessel_type": round(vtype, 3),
                    "speed_anomaly": round(speed, 3),
                    "track_consistency": round(consistency, 3),
                },
                "final_score": round(final_score, 4),
            }
        )

    ranked.sort(key=lambda r: r["final_score"], reverse=True)
    for i, r in enumerate(ranked, start=1):
        r["rank"] = i

    result = {
        "scene_id": scene_id,
        "weights": WEIGHTS,
        "radius_km": radius_km,
        "suspect_count": len(ranked),
        "suspects": ranked,
    }

    out_path = os.path.join(scene_dir, f"{scene_id}_attribution.json")
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)

    return result


if __name__ == "__main__":
    scene_dir = sys.argv[1] if len(sys.argv) > 1 else "data/runtime"
    scene_id = sys.argv[2] if len(sys.argv) > 2 else "demo_scene_01"
    result = rank_candidates(scene_dir, scene_id)
    print(json.dumps(result, indent=2))
