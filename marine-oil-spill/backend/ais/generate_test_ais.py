"""
M4 helper — backend/ais/generate_test_ais.py

Synthesizes a fleet of vessels with AIS-style position tracks (MMSI,
type, hourly pings) around the demo scene, INCLUDING 1-2 vessels that
plausibly pass near the M3-estimated spill origin at roughly the right
time — plus several "innocent" vessels elsewhere — so tracking.py and
ranking.py have a real (if synthetic) detective problem to solve rather
than an empty list.

Run directly (needs a hindcast result already produced by M3):
    python3 -m backend.ais.generate_test_ais data/runtime demo_scene_01
"""
from __future__ import annotations
import json
import math
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from backend.common.geo import destination_point  # noqa: E402

VESSEL_TYPES = ["Tanker", "Cargo", "Container", "Bulk Carrier", "Fishing", "Passenger"]
PING_INTERVAL_MIN = 20
TRACK_HOURS_BEFORE = 26
TRACK_HOURS_AFTER = 2


def _mmsi(seed_val: int) -> str:
    return f"4{100000000 + (seed_val * 7919) % 800000000}"[:9]


def _build_track(
    start_lon: float,
    start_lat: float,
    start_time: datetime,
    bearing: float,
    speed_knots: float,
    heading_jitter: float,
    rng,
) -> list[dict]:
    n_pings = int((TRACK_HOURS_BEFORE + TRACK_HOURS_AFTER) * 60 / PING_INTERVAL_MIN)
    speed_kmh = speed_knots * 1.852
    lon, lat = start_lon, start_lat
    cur_bearing = bearing
    track = []
    for i in range(n_pings):
        ts = start_time + timedelta(minutes=i * PING_INTERVAL_MIN)
        track.append(
            {
                "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "lon": round(lon, 6),
                "lat": round(lat, 6),
                "heading_deg": round(cur_bearing % 360, 1),
                "speed_knots": round(speed_knots + rng.uniform(-0.5, 0.5), 1),
            }
        )
        cur_bearing += rng.uniform(-heading_jitter, heading_jitter)
        dist_step = speed_kmh * (PING_INTERVAL_MIN / 60.0)
        lon, lat = destination_point(lon, lat, cur_bearing, dist_step)
    return track


def generate_fleet(
    out_dir: str,
    scene_id: str,
    suspect_lon: float,
    suspect_lat: float,
    suspect_time_iso: str,
    detection_time_iso: str,
    num_vessels: int = 10,
    num_suspects: int = 2,
    seed: int | None = None,
) -> dict:
    import random

    rng = random.Random(seed)
    suspect_time = datetime.strptime(suspect_time_iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    detection_time = datetime.strptime(detection_time_iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    track_start = detection_time - timedelta(hours=TRACK_HOURS_BEFORE)

    vessels = []
    for i in range(num_vessels):
        is_suspect = i < num_suspects
        vtype = "Tanker" if is_suspect else rng.choice(VESSEL_TYPES)
        speed = rng.uniform(9, 16)

        if is_suspect:
            # Work out where this vessel must START so that, sailing at
            # `speed`, it passes through (suspect_lon, suspect_lat) at
            # suspect_time (± a little jitter so it's not a bullseye).
            hrs_from_track_start_to_suspect = (suspect_time - track_start).total_seconds() / 3600.0
            approach_bearing = rng.uniform(0, 360)
            dist_back_km = speed * 1.852 * hrs_from_track_start_to_suspect
            # walk backward from the suspect point along the reverse
            # bearing to find a plausible start point
            start_lon, start_lat = destination_point(
                suspect_lon, suspect_lat, (approach_bearing + 180) % 360, dist_back_km
            )
            jitter_km = rng.uniform(0.5, 4.0)  # closest approach, not a perfect hit
            start_lon, start_lat = destination_point(start_lon, start_lat, rng.uniform(0, 360), jitter_km)
            bearing = approach_bearing
        else:
            # Innocent vessel: random start further out, random heading,
            # generally not near the suspect point/time.
            far_km = rng.uniform(15, 70)
            far_bearing = rng.uniform(0, 360)
            start_lon, start_lat = destination_point(suspect_lon, suspect_lat, far_bearing, far_km)
            bearing = rng.uniform(0, 360)

        track = _build_track(
            start_lon, start_lat, track_start, bearing, speed, heading_jitter=6.0, rng=rng
        )
        vessels.append(
            {
                "mmsi": _mmsi(i + (seed or 0)),
                "name": f"MV {'SUSPECT' if is_suspect else 'VESSEL'}-{i+1:02d}",
                "vessel_type": vtype,
                "flag": rng.choice(["IN", "PA", "LR", "MH", "SG"]),
                "track": track,
            }
        )
    rng.shuffle(vessels)

    result = {"scene_id": scene_id, "vessel_count": len(vessels), "vessels": vessels}
    out_path = os.path.join(out_dir, f"{scene_id}_ais_data.json")
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
    return result


if __name__ == "__main__":
    scene_dir = sys.argv[1] if len(sys.argv) > 1 else "data/runtime"
    scene_id = sys.argv[2] if len(sys.argv) > 2 else "demo_scene_01"

    with open(os.path.join(scene_dir, f"{scene_id}_hindcast.json")) as f:
        hindcast = json.load(f)

    result = generate_fleet(
        out_dir=scene_dir,
        scene_id=scene_id,
        suspect_lon=hindcast["estimated_origin"]["lon"],
        suspect_lat=hindcast["estimated_origin"]["lat"],
        suspect_time_iso=hindcast["track"][-1]["timestamp"],
        detection_time_iso=hindcast["track"][0]["timestamp"],
        seed=7,
    )
    print(json.dumps({"vessel_count": result["vessel_count"], "sample": result["vessels"][0]["mmsi"]}, indent=2))
