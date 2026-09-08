# Sample outputs

A committed, already-run example so teammates can see real results
without setting anything up first:

- `demo_scene_01_final_report.json` — full pipeline output (detection +
  hindcast + AIS attribution combined)
- `demo_scene_01_raw.png` / `demo_scene_01_processed.png` — the synthetic
  SAR scene before/after M1's speckle filtering + normalization

Regenerate these anytime with `python3 -m backend.pipeline demo_scene_01`.
