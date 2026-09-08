"""Satellite imagery processing package for marine oil spill detection.

This package provides tools for ingesting, preprocessing, and analyzing
Sentinel-1 SAR (Synthetic Aperture Radar) GRD imagery to detect and
characterize oil spills at sea.
"""

from .preprocessing import (
    SARIngestor,
    SpeckleFilter,
    IntensityToDecibel,
    AdaptiveSlickDetector,
    PreprocessingPipeline,
    FilterType,
    SARMetadata,
    SlickDetection,
    ProcessingResult,
    process_sar_scene,
)

__all__ = [
    "SARIngestor",
    "SpeckleFilter",
    "IntensityToDecibel",
    "AdaptiveSlickDetector",
    "PreprocessingPipeline",
    "FilterType",
    "SARMetadata",
    "SlickDetection",
    "ProcessingResult",
    "process_sar_scene",
]
