# Marine Oil Spill Attribution — SIH26143

Detects oil spills at sea from satellite (SAR) imagery, estimates where
and roughly when the spill started by running an ocean-drift model
backward in time, then correlates that estimate against AIS vessel
traffic to shortlist and rank the vessel(s) most likely responsible.

**Problem statement:** SIH26143 — *Leveraging Satellite Imagery to
Determine Oil Spills at Sea Along with AIS Data Correlations to Identify
Vessel Responsible for the Spill* (NTRO, Disaster Management theme).

This repo runs entirely on **synthetic data** (a generated SAR scene +
a generated AIS fleet) so the whole pipeline works today, for a demo or
for development, with no external data-provider account needed. Swapping
in real Sentinel-1 imagery and a real AIS feed later is a matter of
replacing two generator modules — see [docs/API_CONTRACT.md](docs/API_CONTRACT.md).

## Pipeline

```
 M1 Satellite          M2 Detection         M3 Drift           M4 AIS              M5 Attribution
 ─────────────         ─────────────        ─────────────      ─────────────       ─────────────
 raw SAR scene    -->   spill blob(s)  -->   estimated    -->   vessels near  -->    ranked
 -> denoise/            + confidence         origin point       the drift          suspect list
    normalize            + polygon           + time window      path, at a          + scores
                                              (backward           matching
                                              Lagrangian          time
                                              drift model)
```

Every arrow is a JSON file on disk — see
[docs/API_CONTRACT.md](docs/API_CONTRACT.md) for the exact shape of each
one. `backend/pipeline.py` runs all five stages and writes one combined
`_final_report.json`; `backend/main.py` exposes that as an HTTP API for
the frontend.

## Repo layout

```
backend/
  satellite/     M1 — preprocessing.py, generate_test_scene.py, detection.py
  drift/         M3 — hindcasting.py, environment.py
  ais/           M4 — tracking.py, generate_test_ais.py
  attribution/   M5 — ranking.py
  common/        geo.py — shared lon/lat + distance/bearing math, used by every module
  pipeline.py    M6 — runs M1→M5 in order, writes the combined report
  main.py        M6 — FastAPI app (POST /api/analyze, serves frontend + data)
  requirements.txt
frontend/
  index.html     single-file dashboard (Leaflet map + intelligence panel)
docs/
  API_CONTRACT.md   the data contract — read this before writing any module code
data/runtime/    generated scenes + all pipeline output (gitignored, regenerable)
outputs/         a few sample outputs committed so teammates can look without running anything
```

## Quickstart

Requires Python 3.10+.

```bash
git clone <your-repo-url>
cd marine-oil-spill
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt
```

**Option A — run the whole pipeline from the command line**, no server:
```bash
python3 -m backend.pipeline demo_scene_01
```
This generates a synthetic scene, runs it through M1→M5, and prints a
summary. Full output lands in `data/runtime/demo_scene_01_final_report.json`.

**Option B — run the API + open the dashboard:**
```bash
uvicorn backend.main:app --reload --port 8000
```
Then open **http://localhost:8000** and click **Run analysis**. The
dashboard shows the SAR image before/after preprocessing, the detected
spill polygon on a map, the estimated origin + drift track, and the
ranked suspect vessel list with score breakdowns.

**Run any single module on its own** (useful while developing your
piece without the rest of the pipeline working yet):
```bash
python3 -m backend.satellite.generate_test_scene
python3 -m backend.satellite.preprocessing data/runtime demo_scene_01
python3 -m backend.satellite.detection data/runtime demo_scene_01
python3 -m backend.drift.hindcasting data/runtime demo_scene_01
python3 -m backend.ais.generate_test_ais data/runtime demo_scene_01
python3 -m backend.ais.tracking data/runtime demo_scene_01
python3 -m backend.attribution.ranking data/runtime demo_scene_01
```

## Team module ownership

| Stage | Folder | Owns |
|---|---|---|
| M1 — Satellite | `backend/satellite/` | SAR preprocessing, spill detection |
| M3 — Drift | `backend/drift/` | Backward drift model, current/wind lookup |
| M4 — AIS | `backend/ais/` | AIS ingestion, spatio-temporal correlation |
| M5 — Attribution | `backend/attribution/` | Suspect scoring + ranking |
| M6 — Integration | `backend/main.py`, `backend/pipeline.py`, `frontend/` | API, orchestration, dashboard |

Read [docs/API_CONTRACT.md](docs/API_CONTRACT.md) and
[CONTRIBUTING.md](CONTRIBUTING.md) before starting — the contract is
what lets everyone build in parallel without merge hell.

## Roadmap beyond the hackathon demo

- Swap `generate_test_scene.py` for a Copernicus Data Space / ASF Sentinel-1
  GRD loader (same `_raw.png` + `_meta.json` output contract).
- Swap `generate_test_ais.py` for a live AIS feed (Spire, MarineTraffic,
  or a national AIS receiver network).
- Swap the reverse-Lagrangian drift model in `hindcasting.py` for
  OpenDrift or a full hydrodynamic model, using real current/wind
  reanalysis instead of `environment.py`'s synthetic field.
- Replace the Otsu-threshold blob detector in `detection.py` with a
  trained segmentation model (e.g. a U-Net on labeled Sentinel-1 slick
  datasets) — same output contract, no downstream changes needed.
