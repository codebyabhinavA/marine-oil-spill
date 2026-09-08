"""
backend/main.py — M6, API/integration layer

Thin FastAPI wrapper around backend/pipeline.py. Serves:
  - POST /api/analyze         run the full M1-M5 pipeline, return the report
  - GET  /api/report/{id}     re-fetch a previously-run report
  - GET  /api/scenes          list scenes that have been run
  - /data/*                   the raw/processed images + all JSON artifacts
                               (so the frontend can show the actual SAR image)
  - /                         the frontend (frontend/index.html)

Run it:
    uvicorn backend.main:app --reload --port 8000
then open http://localhost:8000
"""
from __future__ import annotations
import glob
import json
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.pipeline import run_full_pipeline

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO_ROOT, "data", "runtime")
FRONTEND_DIR = os.path.join(REPO_ROOT, "frontend")
os.makedirs(DATA_DIR, exist_ok=True)

app = FastAPI(title="Marine Oil Spill Attribution API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # demo-only; scope this down for a real deployment
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    scene_id: str = "demo_scene_01"
    seed: int | None = 42
    ais_seed: int | None = 7
    num_vessels: int = 10
    regenerate_scene: bool = True


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/analyze")
def analyze(req: AnalyzeRequest):
    """
    Runs the full pipeline (M1-M5). For the hackathon demo this always
    works against the synthetic scene/AIS generators, so it's a genuine
    one-click, no-external-account-needed demo. Swap `regenerate_scene`
    logic for a real Sentinel-1 loader when that's ready — nothing else
    in this endpoint needs to change.
    """
    try:
        report = run_full_pipeline(
            scene_dir=DATA_DIR,
            scene_id=req.scene_id,
            seed=req.seed,
            ais_seed=req.ais_seed,
            num_vessels=req.num_vessels,
            regenerate_scene=req.regenerate_scene,
        )
    except Exception as e:  # noqa: BLE001 — surface pipeline errors to the caller for a demo
        raise HTTPException(status_code=500, detail=str(e)) from e
    return report


@app.get("/api/report/{scene_id}")
def get_report(scene_id: str):
    path = os.path.join(DATA_DIR, f"{scene_id}_final_report.json")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"No report for '{scene_id}' yet — POST /api/analyze first.")
    with open(path) as f:
        return json.load(f)


@app.get("/api/scenes")
def list_scenes():
    paths = glob.glob(os.path.join(DATA_DIR, "*_final_report.json"))
    return {"scenes": sorted(os.path.basename(p).replace("_final_report.json", "") for p in paths)}


# Raw/processed images + every intermediate JSON, for the frontend to load directly.
app.mount("/data", StaticFiles(directory=DATA_DIR), name="data")


@app.get("/")
def index():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    raise HTTPException(status_code=404, detail="frontend/index.html not found")


# Any other static frontend asset (kept last so it doesn't shadow /api or /data).
if os.path.isdir(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="frontend")
