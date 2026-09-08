"""
M3 — backend/drift/hindcasting.py

Takes M2's spill detection (centroid + detection timestamp) and works
BACKWARD in time to estimate where and roughly when the spill started.

Model (simple Lagrangian particle backtracking — standard first-pass
approach before anyone reaches for a full OpenDrift/hydrodynamic sim):
  - Oil at sea moves at approximately: 100% of current velocity +
    ~3% of wind velocity (the "3% rule" is a widely used rule-of-thumb
    for wind's direct drag contribution to surface slick drift).
  - We step backward in fixed increments (default: 30 min steps, up to
    HINDCAST_HOURS back), at each step looking up the local
    current/wind (environment.py) and moving the point OPPOSITE that
    combined drift vector.
  - The resulting track's start point is the estimated spill ORIGIN;
    each step's timestamp gives a rough origin TIME WINDOW.

This deliberately stays a straight-line-per-step reverse advection model
— good enough to shortlist an origin area + time window for M4/M5 to work
with. A real system would swap this for OpenDrift or similar without
changing the output contract.

Run directly against a demo spill detection:
    python3 -m backend.drift.hindcasting data/runtime demo_scene_01
"""
from __future__ import annotations
import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from backend.common.geo import destination_point  # noqa: E402
from backend.drift.environment import get_environment_at  # noqa: E402

WIND_DRIFT_FACTOR = 0.03  # "3% rule"
HINDCAST_HOURS = 18.0
STEP_HOURS = 0.5


def _reverse_bearing(bearing: float) -> float:
    return (bearing + 180) % 360


def hindcast_origin(
    centroid_lon: float,
    centroid_lat: float,
    detected_at_iso: str,
    hours_back: float = HINDCAST_HOURS,
    step_hours: float = STEP_HOURS,
) -> dict:
    detected_at = datetime.strptime(detected_at_iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)

    lon, lat = centroid_lon, centroid_lat
    track = [
        {
            "timestamp": detected_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "lon": round(lon, 6),
            "lat": round(lat, 6),
            "hours_before_detection": 0.0,
        }
    ]

    steps = int(hours_back / step_hours)
    for i in range(1, steps + 1):
        hours_before = i * step_hours
        env = get_environment_at(lon, lat, hours_before)

        # Combined drift velocity the slick was riding AT this moment
        # (current fully + a fraction of wind). We reverse it to step
        # the point backward to where it must have been `step_hours`
        # earlier.
        cur_speed = env["current_speed_kmh"]
        cur_bear = env["current_bearing_deg"]
        wind_speed = env["wind_speed_kmh"] * WIND_DRIFT_FACTOR
        wind_bear = env["wind_bearing_deg"]

        # Vector-sum current + wind-drag by moving along each bearing in
        # turn over the step distance (small-step approximation of true
        # vector addition — accurate enough at 30 min resolution).
        dist_current = cur_speed * step_hours
        dist_wind = wind_speed * step_hours

        lon, lat = destination_point(lon, lat, _reverse_bearing(cur_bear), dist_current)
        lon, lat = destination_point(lon, lat, _reverse_bearing(wind_bear), dist_wind)

        ts = detected_at - timedelta(hours=hours_before)
        track.append(
            {
                "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "lon": round(lon, 6),
                "lat": round(lat, 6),
                "hours_before_detection": round(hours_before, 2),
            }
        )

    origin = track[-1]
    # Origin time window: give a +/- 2hr band around the furthest-back
    # estimate to account for model uncertainty, rather than pretending
    # false precision on a single instant.
    origin_ts = datetime.strptime(origin["timestamp"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    window_start = origin_ts - timedelta(hours=2)
    window_end = origin_ts + timedelta(hours=2)

    return {
        "estimated_origin": {"lon": origin["lon"], "lat": origin["lat"]},
        "estimated_origin_time_window": {
            "start": window_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "end": window_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        "hindcast_hours": hours_back,
        "step_hours": step_hours,
        "model": "reverse_lagrangian_current_plus_3pct_wind",
        "track": track,
    }


def hindcast_from_detection_file(scene_dir: str, scene_id: str) -> dict:
    det_path = os.path.join(scene_dir, f"{scene_id}_spill_detection.json")
    with open(det_path) as f:
        detection = json.load(f)

    if not detection["spills"]:
        raise ValueError("No spills in detection result to hindcast from.")

    top_spill = detection["spills"][0]  # highest-confidence blob
    result = hindcast_origin(
        top_spill["centroid"]["lon"],
        top_spill["centroid"]["lat"],
        detection["detected_at"],
    )
    result["scene_id"] = scene_id
    result["source_blob_id"] = top_spill["blob_id"]

    out_path = os.path.join(scene_dir, f"{scene_id}_hindcast.json")
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)

    return result


if __name__ == "__main__":
    scene_dir = sys.argv[1] if len(sys.argv) > 1 else "data/runtime"
    scene_id = sys.argv[2] if len(sys.argv) > 2 else "demo_scene_01"
    result = hindcast_from_detection_file(scene_dir, scene_id)
    print(json.dumps(result, indent=2))
