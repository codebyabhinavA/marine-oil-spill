"""
M1 helper — generate_test_scene.py

Synthesizes a fake SAR (Synthetic Aperture Radar) backscatter scene so the
whole pipeline (M1 -> M2 -> M3 -> M4 -> M5) can be built and demoed before
anyone has a real Copernicus/ASF account approved.

Physical intuition baked into the fake data (so it "looks" like a real
scene to anyone reviewing it):
  - Open ocean = mid-brightness backscatter with speckle noise (SAR's
    signature grainy noise from coherent radar interference).
  - Oil slicks dampen capillary waves -> much LOWER backscatter -> they
    show up as a dark, roughly-elliptical smudge on an otherwise speckled
    grey sea.

Run directly to produce a sample scene:
    python3 -m backend.satellite.generate_test_scene
"""
from __future__ import annotations
import json
import os
import time
import numpy as np
from PIL import Image

DEFAULT_SIZE = 512


def generate_scene(
    out_dir: str,
    scene_id: str,
    size: int = DEFAULT_SIZE,
    seed: int | None = None,
    center_lon: float = 72.60,
    center_lat: float = 18.90,
    extent_deg: float = 0.9,
    slick_center_frac: tuple[float, float] = (0.62, 0.45),
    slick_axes_frac: tuple[float, float] = (0.16, 0.07),
    slick_angle_deg: float = 35.0,
) -> dict:
    """
    Creates <out_dir>/<scene_id>_raw.png and <out_dir>/<scene_id>_meta.json.

    center_lon/lat + extent_deg define a bounding box roughly off the west
    coast of India (Arabian Sea, a real shipping corridor) purely as a
    plausible default for the demo scenario.
    """
    rng = np.random.default_rng(seed)
    os.makedirs(out_dir, exist_ok=True)

    # Base sea backscatter: mid-grey with multiplicative speckle noise,
    # which is how real SAR speckle behaves (Gamma-distributed).
    base_level = 130.0
    speckle = rng.gamma(shape=4.0, scale=1.0 / 4.0, size=(size, size))  # mean ~1
    scene = base_level * speckle

    # A few low-amplitude sinusoidal "wave streaks" so the sea isn't uniform.
    yy, xx = np.mgrid[0:size, 0:size]
    scene += 6 * np.sin(xx / 14.0) * np.cos(yy / 23.0)

    # Carve the oil slick: an elliptical region with much lower backscatter,
    # feathered at the edges (slicks don't have hard boundaries).
    cy, cx = slick_center_frac[1] * size, slick_center_frac[0] * size
    ay, ax = slick_axes_frac[1] * size, slick_axes_frac[0] * size
    theta = np.radians(slick_angle_deg)
    yr = (yy - cy) * np.cos(theta) + (xx - cx) * np.sin(theta)
    xr = -(yy - cy) * np.sin(theta) + (xx - cx) * np.cos(theta)
    ellipse = (xr / ax) ** 2 + (yr / ay) ** 2
    slick_mask = np.clip(1.2 - ellipse, 0, 1)  # 1 in the core, feathering to 0 at edge
    scene = scene * (1 - 0.75 * slick_mask)  # slick suppresses backscatter ~75% at core

    # A couple of small "false alarm" dark patches (calm-water look-alikes)
    # so detection has to do a little real work, not just threshold-and-win.
    for fx, fy, fr in [(0.20, 0.75, 0.03), (0.85, 0.20, 0.025)]:
        fyy = (yy - fy * size) ** 2
        fxx = (xx - fx * size) ** 2
        patch = np.clip(1.0 - (fxx + fyy) / (fr * size) ** 2, 0, 1)
        scene = scene * (1 - 0.35 * patch)

    scene = np.clip(scene, 0, 255).astype(np.uint8)

    raw_path = os.path.join(out_dir, f"{scene_id}_raw.png")
    Image.fromarray(scene, mode="L").save(raw_path)

    bounds = {
        "min_lon": round(center_lon - extent_deg / 2, 6),
        "max_lon": round(center_lon + extent_deg / 2, 6),
        "min_lat": round(center_lat - extent_deg / 2, 6),
        "max_lat": round(center_lat + extent_deg / 2, 6),
    }
    acquired_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    meta = {
        "scene_id": scene_id,
        "source": "SYNTHETIC",  # would be "SENTINEL-1" for a real scene
        "width": size,
        "height": size,
        "bounds": bounds,
        "acquired_at": acquired_at,
        "raw_image_path": os.path.basename(raw_path),
        "notes": "Synthetic SAR scene generated for demo/testing (backend.satellite.generate_test_scene).",
    }
    meta_path = os.path.join(out_dir, f"{scene_id}_meta.json")
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)

    return meta


if __name__ == "__main__":
    m = generate_scene(out_dir="data/runtime", scene_id="demo_scene_01", seed=42)
    print(json.dumps(m, indent=2))
