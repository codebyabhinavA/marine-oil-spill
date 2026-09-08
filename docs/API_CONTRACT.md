# API / Data Contract

This is the one document everyone on the team should agree on before
touching code. Every stage reads a JSON shape written by the stage before
it and writes a JSON shape for the stage after it. As long as you don't
change these shapes, you can rewrite the *internals* of your module
however you want (swap the synthetic generator for real Sentinel-1, swap
the reverse-drift model for OpenDrift, swap the scoring weights) without
breaking anyone else's code.

All files for a given `scene_id` live together in one directory
(`data/runtime/` locally). Every filename is `<scene_dir>/<scene_id>_<thing>`.

```
scene_id_raw.png                raw SAR scene              (M1 generates/loads)
scene_id_meta.json              scene metadata              (M1 writes, everyone reads bounds/timing from it)
scene_id_processed.png          denoised/normalized scene   (M1 writes)
scene_id_spill_detection.json   detected slick polygon(s)   (M2 writes)
scene_id_hindcast.json          estimated origin + track    (M3 writes)
scene_id_ais_data.json          synthetic AIS fleet         (M4 helper writes, for demo only)
scene_id_ais_candidates.json    vessels near the drift path (M4 writes)
scene_id_attribution.json       final ranked suspect list   (M5 writes)
scene_id_final_report.json      everything above, combined  (backend/pipeline.py writes)
```

Every module also has a `__main__` block so you can run and test it in
isolation from the command line — you don't need the rest of the team's
code working to develop and demo your own piece.

---

## M1 — Satellite preprocessing (`backend/satellite/`)

**Owns:** `preprocessing.py`, `generate_test_scene.py`

**Writes `<scene_id>_meta.json`:**
```json
{
  "scene_id": "demo_scene_01",
  "source": "SYNTHETIC",
  "width": 512,
  "height": 512,
  "bounds": {"min_lon": 72.15, "max_lon": 73.05, "min_lat": 18.45, "max_lat": 19.35},
  "acquired_at": "2026-09-07T14:15:17Z",
  "raw_image_path": "demo_scene_01_raw.png",
  "processed_image_path": "demo_scene_01_processed.png",
  "processing": {"speckle_filter": "lee", "lee_window": 5, "db_conversion": true, "normalization": "percentile_clip_2_98"}
}
```
`bounds` uses row 0 = north (top of the image), consistent with
`backend/common/geo.py:pixel_to_lonlat` — every module that converts
pixel coordinates to lon/lat must use that function so everyone agrees on
the same mapping.

A real Sentinel-1 loader replaces `generate_test_scene.py` but must
produce this same `_raw.png` + `_meta.json` pair — nothing downstream
changes.

## M2 — Spill detection (`backend/satellite/detection.py`)

**Reads:** `_meta.json` + `_processed.png`
**Writes `<scene_id>_spill_detection.json`:**
```json
{
  "scene_id": "demo_scene_01",
  "detected_at": "2026-09-07T14:15:17Z",
  "spill_count": 1,
  "spills": [
    {
      "blob_id": "demo_scene_01_blob_3",
      "area_px": 7790,
      "confidence": 0.73,
      "centroid": {"lon": 72.7084, "lat": 18.9436},
      "polygon": [[lon,lat], [lon,lat], [lon,lat], [lon,lat]]
    }
  ]
}
```
Spills are sorted by `confidence` descending. Downstream stages use
`spills[0]` (highest confidence) unless a human operator picks a
different blob.

## M3 — Drift hindcasting (`backend/drift/`)

**Owns:** `hindcasting.py`, `environment.py` (current/wind lookup — swap
for a real metocean API without changing the contract)

**Reads:** `_spill_detection.json`
**Writes `<scene_id>_hindcast.json`:**
```json
{
  "estimated_origin": {"lon": 72.8955, "lat": 19.1604},
  "estimated_origin_time_window": {"start": "...Z", "end": "...Z"},
  "hindcast_hours": 18.0,
  "track": [
    {"timestamp": "...Z", "lon": ..., "lat": ..., "hours_before_detection": 0.0},
    ...
    {"timestamp": "...Z", "lon": ..., "lat": ..., "hours_before_detection": 18.0}
  ]
}
```
`track[0]` is the detected spill position (now); `track[-1]` is the
estimated origin (furthest back). M4 correlates AIS against every point
in `track`, not just the endpoints.

## M4 — AIS correlation (`backend/ais/`)

**Owns:** `tracking.py`, `generate_test_ais.py` (synthetic fleet — demo
only; swap for a real AIS feed without changing the contract)

**Reads:** `_hindcast.json` + `_ais_data.json`
**Writes `<scene_id>_ais_candidates.json`:**
```json
{
  "radius_km": 40.0,
  "candidate_count": 2,
  "candidates": [
    {
      "mmsi": "410006335",
      "name": "MV SUSPECT-02",
      "vessel_type": "Tanker",
      "closest_approach_km": 15.89,
      "closest_approach_time": "...Z",
      "vessel_position_at_match": {"lon": ..., "lat": ...},
      "vessel_speed_knots_at_match": 14.7,
      "is_candidate": true
    }
  ]
}
```
A vessel is a candidate if its closest approach to the drift track, **at
a matching timestamp**, is within `radius_km`. See the long comment at
the top of `tracking.py` for why the radius is calibrated wide (40km) —
short version: an 18-hour hindcast window and a vessel's own course
changes both add real uncertainty, so this stage is deliberately a
shortlist, not a verdict.

## M5 — Attribution / ranking (`backend/attribution/ranking.py`)

**Reads:** `_ais_candidates.json` + `_ais_data.json` + `_hindcast.json`
**Writes `<scene_id>_attribution.json`:**
```json
{
  "weights": {"proximity": 0.5, "vessel_type": 0.25, "speed_anomaly": 0.15, "track_consistency": 0.1},
  "suspects": [
    {
      "rank": 1,
      "mmsi": "410006335",
      "name": "MV SUSPECT-02",
      "final_score": 0.5596,
      "scores": {"proximity": 0.603, "vessel_type": 1.0, "speed_anomaly": 0.001, "track_consistency": 0.081}
    }
  ]
}
```
Scoring logic is intentionally simple + explainable (see the module
docstring). Swap any individual score function for a trained model later
without changing this shape.

## M6 — Integration (`backend/main.py`, `backend/pipeline.py`, `frontend/`)

`backend/pipeline.py::run_full_pipeline()` calls M1→M5 in order and writes
`<scene_id>_final_report.json`, combining every stage's output into one
object (see the file for the exact shape — it's just scene + detection +
hindcast + ais_tracking summary + attribution, nested).

`backend/main.py` exposes that as `POST /api/analyze`. The frontend calls
this one endpoint and renders the whole report — it does not need to know
about the intermediate per-stage files at all.
