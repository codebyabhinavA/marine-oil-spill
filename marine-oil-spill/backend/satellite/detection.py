"""
M2 — backend/satellite/detection.py

Consumes the processed scene from M1 (preprocessing.py) and finds
candidate oil-slick blobs: dark, coherent regions against the speckled
sea background.

Approach (deliberately simple + explainable for a hackathon demo/judges,
swap in a trained CNN/segmentation model later without touching the
contract):
  1. Otsu-style threshold on the normalized processed image to isolate
     "dark" pixels.
  2. Morphological opening (erode then dilate) to strip lone speckle
     pixels that survived preprocessing, without erasing the real slick.
  3. Connected-component labeling; keep components above a minimum pixel
     area (real slicks are big and coherent, noise is small and scattered).
  4. For each surviving component: pixel bbox -> lat/lon polygon (via
     common.geo), centroid, and a confidence score derived from size +
     contrast against the local background.

Run directly against a preprocessed demo scene:
    python3 -m backend.satellite.detection data/runtime demo_scene_01
"""
from __future__ import annotations
import json
import os
import sys
import numpy as np
from PIL import Image
from scipy import ndimage

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from backend.common.geo import pixel_to_lonlat  # noqa: E402

MIN_BLOB_AREA_PX = 60


def _otsu_threshold(img: np.ndarray) -> float:
    """Classic Otsu: pick the threshold that best separates the histogram
    into two classes by maximizing between-class variance."""
    hist, bin_edges = np.histogram(img.ravel(), bins=256, range=(0, 256))
    hist = hist.astype(np.float64)
    total = hist.sum()
    sum_all = np.dot(np.arange(256), hist)

    sum_bg, w_bg, best_thresh, best_var = 0.0, 0.0, 0, 0.0
    for t in range(256):
        w_bg += hist[t]
        if w_bg == 0:
            continue
        w_fg = total - w_bg
        if w_fg == 0:
            break
        sum_bg += t * hist[t]
        mean_bg = sum_bg / w_bg
        mean_fg = (sum_all - sum_bg) / w_fg
        between_var = w_bg * w_fg * (mean_bg - mean_fg) ** 2
        if between_var > best_var:
            best_var, best_thresh = between_var, t
    return float(best_thresh)


def detect_spills(scene_dir: str, scene_id: str) -> dict:
    meta_path = os.path.join(scene_dir, f"{scene_id}_meta.json")
    with open(meta_path) as f:
        meta = json.load(f)

    processed_path = os.path.join(scene_dir, meta["processed_image_path"])
    img = np.array(Image.open(processed_path).convert("L"))
    h, w = img.shape
    bounds = meta["bounds"]

    otsu_t = _otsu_threshold(img)
    # Slicks are DARKER than the sea, so we want pixels BELOW threshold.
    # Nudge slightly below Otsu's split so we favor precision over recall
    # for the demo (fewer, more confident blobs).
    thresh = max(otsu_t - 8, 0)
    dark_mask = img < thresh

    # Morphological opening: erode away thin/lone speckle, then dilate
    # back to restore the shape of anything that survived.
    structure = np.ones((3, 3), dtype=bool)
    opened = ndimage.binary_erosion(dark_mask, structure=structure, iterations=2)
    opened = ndimage.binary_dilation(opened, structure=structure, iterations=2)

    labeled, n_features = ndimage.label(opened)
    sea_mean = float(img[~opened].mean()) if (~opened).any() else float(img.mean())
    sea_std = float(img[~opened].std()) if (~opened).any() else float(img.std())

    detections = []
    for label_id in range(1, n_features + 1):
        ys, xs = np.where(labeled == label_id)
        area = len(ys)
        if area < MIN_BLOB_AREA_PX:
            continue

        blob_mean = float(img[ys, xs].mean())
        contrast = max(sea_mean - blob_mean, 0)
        # Confidence: combines how dark the blob is relative to sea
        # (in std-devs) with a size term, squashed into [0,1].
        contrast_score = min(contrast / (sea_std + 1e-6) / 4.0, 1.0)
        size_score = min(area / 4000.0, 1.0)
        confidence = round(0.7 * contrast_score + 0.3 * size_score, 3)

        min_row, max_row = int(ys.min()), int(ys.max())
        min_col, max_col = int(xs.min()), int(xs.max())
        corners_px = [
            (min_row, min_col),
            (min_row, max_col),
            (max_row, max_col),
            (max_row, min_col),
        ]
        polygon = [list(pixel_to_lonlat(r, c, h, w, bounds)) for r, c in corners_px]
        centroid_row, centroid_col = float(ys.mean()), float(xs.mean())
        centroid_lon, centroid_lat = pixel_to_lonlat(centroid_row, centroid_col, h, w, bounds)

        detections.append(
            {
                "blob_id": f"{scene_id}_blob_{label_id}",
                "area_px": int(area),
                "confidence": confidence,
                "centroid": {"lon": round(centroid_lon, 6), "lat": round(centroid_lat, 6)},
                "polygon": [[round(lo, 6), round(la, 6)] for lo, la in polygon],
            }
        )

    detections.sort(key=lambda d: d["confidence"], reverse=True)

    result = {
        "scene_id": scene_id,
        "detected_at": meta["acquired_at"],
        "threshold_used": round(thresh, 2),
        "sea_background": {"mean": round(sea_mean, 2), "std": round(sea_std, 2)},
        "spill_count": len(detections),
        "spills": detections,
    }

    out_path = os.path.join(scene_dir, f"{scene_id}_spill_detection.json")
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)

    return result


if __name__ == "__main__":
    scene_dir = sys.argv[1] if len(sys.argv) > 1 else "data/runtime"
    scene_id = sys.argv[2] if len(sys.argv) > 2 else "demo_scene_01"
    result = detect_spills(scene_dir, scene_id)
    print(json.dumps(result, indent=2))
