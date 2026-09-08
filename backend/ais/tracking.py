"""
M4 — backend/ais/tracking.py

Consumes M3's hindcast track (the estimated backward drift path of the
spill, one point every 30 min) and the AIS fleet data (generate_test_ais.py
for the demo; a real system would swap this loader for a live AIS feed /
MarineTraffic-style API without touching the contract below).

For every vessel, we ask: at each timestamp along the hindcast track, how
far was this vessel from where the drift model says the oil was at that
same moment? We take the MINIMUM of that distance across the whole track
(a vessel only needs to have been close at ONE matching instant to be a
suspect — that's the moment it plausibly discharged). Vessels whose best
match is still far away are dropped; everyone else becomes a candidate for
M5 to score and rank.

This is deliberately a straightforward spatio-temporal correlation (not
just "closest vessel to the origin POINT") because it's the time alignment
that actually makes this a correlation instead of a coincidence — a vessel
could be geographically close to the origin at the WRONG time and it means
nothing.

Run directly against a demo hindcast + AIS set:
    python3 -m backend.ais.tracking data/runtime demo_scene_01
"""
from __future__ import annotations
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from backend.common.geo import haversine_km  # noqa: E402

# How close a vessel must have come to the estimated drift path, at a
# matching timestamp, to be considered a candidate at all. Generous on
# purpose for a demo: real AIS courses meander (heading changes, weather
# routing) and the drift model is a simplification, so over an 18-hour
# hindcast window a genuinely-involved vessel can still be tens of km off
# a straight-line estimate. We'd rather over-shortlist here and let M5's
# scoring (plus a human analyst) do the fine discrimination than silently
# drop the real suspect. Calibrated against the synthetic generator: true
# "innocent" vessels land 100km+ away, true suspects land within ~35km —
# there's a wide natural gap between the two groups.
CANDIDATE_RADIUS_KM = 40.0

# A vessel ping outside this window either side of the hindcast track's
# time span is not interpolated against (avoids extrapolating a straight
# line miles past a vessel's actual recorded track).
_ISO = "%Y-%m-%dT%H:%M:%SZ"


def _parse(ts: str) -> datetime:
    return datetime.strptime(ts, _ISO).replace(tzinfo=timezone.utc)


def _interpolate_position(track: list[dict], query_iso: str) -> tuple[float, float] | None:
    """
    Linear interpolation of a vessel's lon/lat at `query_iso`, using its two
    surrounding AIS pings. Returns None if the query time falls outside the
    vessel's recorded track (no extrapolation).
    """
    query_t = _parse(query_iso)
    if not track:
        return None
    times = [_parse(p["timestamp"]) for p in track]
    if query_t < times[0] or query_t > times[-1]:
        return None

    # Find the bracketing pair (track is chronological).
    for i in range(len(track) - 1):
        t0, t1 = times[i], times[i + 1]
        if t0 <= query_t <= t1:
            span = (t1 - t0).total_seconds()
            frac = 0.0 if span == 0 else (query_t - t0).total_seconds() / span
            p0, p1 = track[i], track[i + 1]
            lon = p0["lon"] + frac * (p1["lon"] - p0["lon"])
            lat = p0["lat"] + frac * (p1["lat"] - p0["lat"])
            return lon, lat
    return None


def _speed_near(track: list[dict], query_iso: str) -> float | None:
    """Reported AIS speed (knots) from the ping nearest to query_iso."""
    query_t = _parse(query_iso)
    if not track:
        return None
    best = min(track, key=lambda p: abs((_parse(p["timestamp"]) - query_t).total_seconds()))
    return best.get("speed_knots")


def correlate_vessel(vessel: dict, hindcast_track: list[dict]) -> dict:
    """
    Walks the whole hindcast track and finds this vessel's closest approach
    (in km) to the drift-estimated slick position at a MATCHING timestamp.
    """
    best = None  # (distance_km, hindcast_point, vessel_lon, vessel_lat)
    for hpoint in hindcast_track:
        pos = _interpolate_position(vessel["track"], hpoint["timestamp"])
        if pos is None:
            continue
        vlon, vlat = pos
        dist = haversine_km(hpoint["lon"], hpoint["lat"], vlon, vlat)
        if best is None or dist < best[0]:
            best = (dist, hpoint, vlon, vlat)

    if best is None:
        return {
            "mmsi": vessel["mmsi"],
            "name": vessel["name"],
            "vessel_type": vessel["vessel_type"],
            "flag": vessel["flag"],
            "matched": False,
            "reason": "no AIS coverage overlapping the hindcast window",
        }

    dist_km, hpoint, vlon, vlat = best
    speed_at_closest = _speed_near(vessel["track"], hpoint["timestamp"])

    return {
        "mmsi": vessel["mmsi"],
        "name": vessel["name"],
        "vessel_type": vessel["vessel_type"],
        "flag": vessel["flag"],
        "matched": True,
        "closest_approach_km": round(dist_km, 3),
        "closest_approach_time": hpoint["timestamp"],
        "hours_before_detection": hpoint["hours_before_detection"],
        "vessel_position_at_match": {"lon": round(vlon, 6), "lat": round(vlat, 6)},
        "drift_position_at_match": {"lon": hpoint["lon"], "lat": hpoint["lat"]},
        "vessel_speed_knots_at_match": speed_at_closest,
        "is_candidate": dist_km <= CANDIDATE_RADIUS_KM,
    }


def track_vessels(scene_dir: str, scene_id: str, radius_km: float = CANDIDATE_RADIUS_KM) -> dict:
    hindcast_path = os.path.join(scene_dir, f"{scene_id}_hindcast.json")
    ais_path = os.path.join(scene_dir, f"{scene_id}_ais_data.json")
    with open(hindcast_path) as f:
        hindcast = json.load(f)
    with open(ais_path) as f:
        ais = json.load(f)

    all_results = [correlate_vessel(v, hindcast["track"]) for v in ais["vessels"]]
    candidates = [r for r in all_results if r.get("is_candidate")]
    candidates.sort(key=lambda r: r["closest_approach_km"])

    result = {
        "scene_id": scene_id,
        "radius_km": radius_km,
        "vessels_checked": len(all_results),
        "candidate_count": len(candidates),
        "candidates": candidates,
        "all_vessels": sorted(
            [r for r in all_results if r.get("matched")],
            key=lambda r: r["closest_approach_km"],
        ),
    }

    out_path = os.path.join(scene_dir, f"{scene_id}_ais_candidates.json")
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)

    return result


if __name__ == "__main__":
    scene_dir = sys.argv[1] if len(sys.argv) > 1 else "data/runtime"
    scene_id = sys.argv[2] if len(sys.argv) > 2 else "demo_scene_01"
    result = track_vessels(scene_dir, scene_id)
    print(json.dumps({k: v for k, v in result.items() if k != "all_vessels"}, indent=2))
