"""
M1 — backend/satellite/preprocessing.py

Takes a raw SAR scene (PNG + meta.json sidecar, see generate_test_scene.py
for how the demo one is produced; a real Sentinel-1 GRD product would be
converted to this same PNG+meta shape by a small loader you'd swap in
later) and produces a denoised, normalized scene ready for detection (M2).

Steps, in order (standard SAR ocean preprocessing chain):
  1. Lee speckle filter  — SAR speckle is multiplicative noise; Lee
     filtering uses local mean/variance to smooth homogeneous regions
     while preserving edges (important: we don't want to blur away the
     slick boundary we're trying to detect).
  2. dB scale conversion — sigma-nought backscatter is usually worked
     with logarithmically (10*log10(x)); compresses dynamic range and is
     the conventional unit SAR analysts think in.
  3. Percentile-clip normalization — clips to the 2nd/98th percentile and
     stretches to 0-255 so a few bright outlier pixels (ships, etc.)
     don't wash out the contrast we need to see the slick.

Run directly against a generated demo scene:
    python3 -m backend.satellite.preprocessing data/runtime/demo_scene_01
"""
from __future__ import annotations
import json
import os
import sys
import numpy as np
from PIL import Image


def lee_filter(img: np.ndarray, window: int = 5) -> np.ndarray:
    """
    Simple Lee speckle filter.
    For each pixel: output = mean + k * (pixel - mean), where k is a
    weight derived from local vs. overall noise variance. In flat regions
    (low local variance) this collapses toward the local mean (denoise);
    near edges (high local variance) it preserves the original pixel.
    """
    img = img.astype(np.float64)
    from scipy.ndimage import uniform_filter

    mean = uniform_filter(img, size=window)
    sq_mean = uniform_filter(img * img, size=window)
    local_var = np.maximum(sq_mean - mean * mean, 0)

    overall_var = float(np.var(img))
    overall_var = max(overall_var, 1e-6)

    k = local_var / (local_var + overall_var)
    out = mean + k * (img - mean)
    return out


def to_db(img: np.ndarray, eps: float = 1.0) -> np.ndarray:
    """10*log10(x); eps avoids log(0) for any zero pixels."""
    return 10.0 * np.log10(np.clip(img, eps, None))


def percentile_normalize(img: np.ndarray, low: float = 2.0, high: float = 98.0) -> np.ndarray:
    lo, hi = np.percentile(img, [low, high])
    if hi <= lo:
        hi = lo + 1e-6
    out = (img - lo) / (hi - lo)
    out = np.clip(out, 0, 1) * 255.0
    return out.astype(np.uint8)


def preprocess_scene(scene_dir: str, scene_id: str, out_dir: str | None = None) -> dict:
    """
    Reads <scene_dir>/<scene_id>_raw.png + _meta.json, writes
    <out_dir>/<scene_id>_processed.png + an updated meta json (contract
    for M2, see docs/API_CONTRACT.md) and returns that metadata dict.
    """
    out_dir = out_dir or scene_dir
    os.makedirs(out_dir, exist_ok=True)

    meta_path = os.path.join(scene_dir, f"{scene_id}_meta.json")
    with open(meta_path) as f:
        meta = json.load(f)

    raw_path = os.path.join(scene_dir, meta["raw_image_path"])
    raw = np.array(Image.open(raw_path).convert("L"))

    filtered = lee_filter(raw, window=5)
    db = to_db(filtered)
    normalized = percentile_normalize(db, low=2.0, high=98.0)

    processed_path = os.path.join(out_dir, f"{scene_id}_processed.png")
    Image.fromarray(normalized, mode="L").save(processed_path)

    out_meta = dict(meta)
    out_meta.update(
        {
            "processed_image_path": os.path.basename(processed_path),
            "processing": {
                "speckle_filter": "lee",
                "lee_window": 5,
                "db_conversion": True,
                "normalization": "percentile_clip_2_98",
            },
        }
    )
    out_meta_path = os.path.join(out_dir, f"{scene_id}_meta.json")
    with open(out_meta_path, "w") as f:
        json.dump(out_meta, f, indent=2)

    return out_meta


if __name__ == "__main__":
    scene_dir = sys.argv[1] if len(sys.argv) > 1 else "data/runtime"
    scene_id = sys.argv[2] if len(sys.argv) > 2 else "demo_scene_01"
    result = preprocess_scene(scene_dir, scene_id)
    print(json.dumps(result, indent=2))
