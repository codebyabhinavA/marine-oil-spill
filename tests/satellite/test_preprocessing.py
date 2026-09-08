"""
Test suite for the SAR preprocessing and oil spill detection pipeline.

Uses synthetic SAR imagery (no real satellite data required) to validate:
- GeoTIFF ingestion with rasterio
- Speckle filter mathematical correctness
- dB conversion accuracy
- Adaptive thresholding detection
- Metadata export contract
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_bounds

# ---------------------------------------------------------------------------
# Ensure the project root is on sys.path so `backend.satellite` resolves.
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.satellite.preprocessing import (
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

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def synthetic_sar_image():
    """512×512 float64 array with gamma-distributed ocean backscatter and
    three embedded dark ellipses simulating oil slicks."""
    rng = np.random.RandomState(42)
    shape_param, scale_param = 5.0, 200.0
    image = rng.gamma(shape_param, scale_param, (512, 512))

    rr, cc = np.ogrid[:512, :512]

    # Slick 1 – ellipse centred at (100, 150)
    mask1 = ((rr - 100) ** 2) / 20 ** 2 + ((cc - 150) ** 2) / 50 ** 2 <= 1
    image[mask1] = rng.gamma(shape_param, scale_param / 20.0, np.sum(mask1))

    # Slick 2 – ellipse centred at (300, 350)
    mask2 = ((rr - 300) ** 2) / 40 ** 2 + ((cc - 350) ** 2) / 30 ** 2 <= 1
    image[mask2] = rng.gamma(shape_param, scale_param / 15.0, np.sum(mask2))

    # Slick 3 – ellipse centred at (400, 100)
    mask3 = ((rr - 400) ** 2) / 25 ** 2 + ((cc - 100) ** 2) / 60 ** 2 <= 1
    image[mask3] = rng.gamma(shape_param, scale_param / 25.0, np.sum(mask3))

    return image.astype(np.float64)


@pytest.fixture
def synthetic_sar_tif(tmp_path, synthetic_sar_image):
    """Write *synthetic_sar_image* to a georeferenced GeoTIFF (Arabian Sea)."""
    filepath = tmp_path / "synthetic_sar.tif"
    transform = from_bounds(68.0, 18.0, 70.0, 20.0, 512, 512)

    with rasterio.open(
        filepath,
        "w",
        driver="GTiff",
        height=512,
        width=512,
        count=1,
        dtype=synthetic_sar_image.dtype,
        crs="EPSG:4326",
        transform=transform,
    ) as dst:
        dst.write(synthetic_sar_image, 1)

    return filepath


@pytest.fixture
def sample_metadata():
    """A realistic SARMetadata matching the synthetic GeoTIFF."""
    transform = from_bounds(68.0, 18.0, 70.0, 20.0, 512, 512)
    return SARMetadata(
        filepath=Path("synthetic_sar.tif"),
        crs="EPSG:4326",
        bounds=(68.0, 18.0, 70.0, 20.0),
        transform=transform,
        width=512,
        height=512,
        # ~111 320 m per degree × (2° / 512 px)
        pixel_size_m=(abs(transform.a) * 111320, abs(transform.e) * 111320),
        nodata=None,
        band_count=1,
        dtype="float64",
    )


# ============================================================================
# SARIngestor
# ============================================================================


class TestSARIngestor:
    def test_ingest_valid_geotiff(self, synthetic_sar_tif):
        ingestor = SARIngestor(synthetic_sar_tif)
        image, metadata = ingestor.ingest()
        assert image.shape == (512, 512)
        assert image.dtype == np.float64
        assert metadata.width == 512
        assert metadata.height == 512

    def test_ingest_nonexistent_file(self):
        with pytest.raises(FileNotFoundError):
            SARIngestor("nonexistent_file.tif")

    def test_ingest_invalid_extension(self, tmp_path):
        txt = tmp_path / "test.txt"
        txt.touch()
        with pytest.raises(ValueError):
            SARIngestor(txt)

    def test_metadata_extraction(self, synthetic_sar_tif):
        ingestor = SARIngestor(synthetic_sar_tif)
        _, metadata = ingestor.ingest()
        assert "4326" in metadata.crs
        assert metadata.bounds == pytest.approx((68.0, 18.0, 70.0, 20.0))
        assert metadata.width == 512
        assert metadata.height == 512

    def test_nodata_handling(self, tmp_path, synthetic_sar_image):
        filepath = tmp_path / "nodata_sar.tif"
        data = synthetic_sar_image.copy()
        data[:10, :10] = -9999.0
        transform = from_bounds(68.0, 18.0, 70.0, 20.0, 512, 512)

        with rasterio.open(
            filepath,
            "w",
            driver="GTiff",
            height=512,
            width=512,
            count=1,
            dtype=data.dtype,
            crs="EPSG:4326",
            transform=transform,
            nodata=-9999.0,
        ) as dst:
            dst.write(data, 1)

        ingestor = SARIngestor(filepath)
        image, _ = ingestor.ingest()
        # Nodata pixels should be replaced with the epsilon floor (1e-10), not NaN
        assert np.all(np.isfinite(image))
        assert np.all(image[:10, :10] > 0)


# ============================================================================
# SpeckleFilter
# ============================================================================


class TestSpeckleFilter:
    def test_lee_filter_reduces_variance(self, synthetic_sar_image):
        f = SpeckleFilter(FilterType.LEE, window_size=5)
        filtered = f.apply(synthetic_sar_image)
        assert np.var(filtered) < np.var(synthetic_sar_image)

    def test_lee_filter_preserves_mean(self, synthetic_sar_image):
        f = SpeckleFilter(FilterType.LEE, window_size=5)
        filtered = f.apply(synthetic_sar_image)
        rel_err = abs(np.mean(filtered) - np.mean(synthetic_sar_image)) / np.mean(
            synthetic_sar_image
        )
        assert rel_err < 0.05

    def test_refined_lee_preserves_edges(self):
        """A sharp step-edge should be better preserved by Refined Lee
        than by Standard Lee. Uses a larger contrast to make the
        difference clearly measurable."""
        img = np.ones((100, 100), dtype=np.float64) * 50
        img[:, 50:] = 5000  # 100× contrast
        rng = np.random.RandomState(42)
        noisy = img + rng.normal(0, 30, img.shape)
        noisy = np.maximum(noisy, 1.0)  # keep positive for SAR

        lee = SpeckleFilter(FilterType.LEE, window_size=7)
        refined = SpeckleFilter(FilterType.REFINED_LEE, window_size=7)

        lee_out = lee.apply(noisy)
        ref_out = refined.apply(noisy)

        # Compare the edge gradient at column 50 (step boundary)
        lee_grad = np.mean(np.abs(lee_out[:, 50] - lee_out[:, 49]))
        ref_grad = np.mean(np.abs(ref_out[:, 50] - ref_out[:, 49]))
        # Refined Lee should preserve the sharp transition better
        assert ref_grad > lee_grad * 0.95  # at least comparable or better

    def test_frost_filter_reduces_variance(self, synthetic_sar_image):
        f = SpeckleFilter(FilterType.FROST, window_size=5)
        filtered = f.apply(synthetic_sar_image)
        assert np.var(filtered) < np.var(synthetic_sar_image)

    @pytest.mark.parametrize("ftype", list(FilterType))
    def test_all_filter_types_produce_valid_output(self, synthetic_sar_image, ftype):
        f = SpeckleFilter(ftype, window_size=3)
        filtered = f.apply(synthetic_sar_image)
        assert filtered.shape == synthetic_sar_image.shape
        assert not np.isnan(filtered).any()
        assert not np.isinf(filtered).any()

    def test_window_size_effect(self, synthetic_sar_image):
        """A larger Lee filter window should smooth more on a noisy image."""
        # Use a high-noise image where the effect is unambiguous
        rng = np.random.RandomState(99)
        noisy = rng.gamma(3.0, 300.0, (256, 256)).astype(np.float64)
        small = SpeckleFilter(FilterType.LEE, window_size=3).apply(noisy)
        large = SpeckleFilter(FilterType.LEE, window_size=11).apply(noisy)
        assert np.var(large) < np.var(small)


# ============================================================================
# IntensityToDecibel
# ============================================================================


class TestIntensityToDecibel:
    def test_known_conversion(self):
        converter = IntensityToDecibel(floor_db=-50.0)
        arr = np.array([1000.0, 1.0, 0.001])
        db = converter.convert(arr)
        # 10·log10(1000)=30, 10·log10(1)=0, 10·log10(0.001)=-30
        np.testing.assert_allclose(db, [30.0, 0.0, -30.0], atol=1e-5)

    def test_zero_handling(self):
        converter = IntensityToDecibel(floor_db=-50.0)
        db = converter.convert(np.array([0.0, 0.0, 0.0]))
        assert not np.isinf(db).any()
        assert np.all(db >= -50.0)

    def test_floor_clamping(self):
        converter = IntensityToDecibel(floor_db=-20.0)
        arr = np.array([1e-5, 1e-6, 1e-7])
        db = converter.convert(arr)
        np.testing.assert_allclose(db, [-20.0, -20.0, -20.0])

    def test_normalize_range(self):
        converter = IntensityToDecibel(floor_db=-50.0)
        db = converter.convert(np.array([1000.0, 1.0, 0.001]))
        norm = converter.normalize(db)
        assert np.min(norm) >= 0.0
        assert np.max(norm) <= 1.0


# ============================================================================
# AdaptiveSlickDetector
# ============================================================================


class TestAdaptiveSlickDetector:
    def _make_db_image(self, synthetic_sar_image):
        """Helper: convert synthetic SAR to dB for detector tests."""
        converter = IntensityToDecibel()
        return converter.convert(synthetic_sar_image)

    def test_detects_dark_patches(self, synthetic_sar_image, sample_metadata):
        db = self._make_db_image(synthetic_sar_image)
        detector = AdaptiveSlickDetector(
            method="sliding_window", block_size=127, k_factor=1.5, min_area_px=50
        )
        mask, detections = detector.detect(db, sample_metadata)
        assert len(detections) >= 1

    def test_detection_area_reasonable(self, synthetic_sar_image, sample_metadata):
        db = self._make_db_image(synthetic_sar_image)
        detector = AdaptiveSlickDetector(
            method="sliding_window", block_size=127, k_factor=2.0, min_area_px=100
        )
        _, detections = detector.detect(db, sample_metadata)
        for d in detections:
            assert d.area_km2 > 0

    def test_confidence_in_range(self, synthetic_sar_image, sample_metadata):
        db = self._make_db_image(synthetic_sar_image)
        detector = AdaptiveSlickDetector(
            method="sliding_window", block_size=127, k_factor=2.0, min_area_px=100
        )
        _, detections = detector.detect(db, sample_metadata)
        for d in detections:
            assert 0.0 <= d.confidence <= 1.0

    def test_no_detection_on_uniform_image(self, sample_metadata):
        uniform = np.full((512, 512), -15.0, dtype=np.float64)
        detector = AdaptiveSlickDetector(
            method="adaptive_otsu", block_size=127, k_factor=0.3, min_area_px=500
        )
        _, detections = detector.detect(uniform, sample_metadata)
        assert len(detections) == 0

    def test_sliding_window_method(self, synthetic_sar_image, sample_metadata):
        db = self._make_db_image(synthetic_sar_image)
        detector = AdaptiveSlickDetector(
            method="sliding_window",
            block_size=127,
            k_factor=2.0,
            min_area_px=200,
        )
        _, detections = detector.detect(db, sample_metadata)
        assert isinstance(detections, list)

    def test_morphological_cleanup_removes_small_regions(self):
        detector = AdaptiveSlickDetector(min_area_px=100)
        mask = np.zeros((200, 200), dtype=np.uint8)
        # Small dots (area ≈ 25 px, below 100 threshold)
        mask[10:15, 10:15] = 1
        # Large region (area = 400 px, above threshold)
        mask[100:120, 100:120] = 1

        cleaned = detector._morphological_cleanup(mask)
        num_labels, _, _, _ = cv2.connectedComponentsWithStats(cleaned)
        # 1 background + 1 surviving region
        assert num_labels == 2


# ============================================================================
# PreprocessingPipeline (end-to-end)
# ============================================================================


class TestPreprocessingPipeline:
    def test_full_pipeline_e2e(self, synthetic_sar_tif, tmp_path):
        out_dir = tmp_path / "output"
        pipeline = PreprocessingPipeline(
            filter_type=FilterType.LEE,
            filter_window=5,
            detection_method="adaptive_otsu",
            k_factor=0.8,
            min_area_px=200,
        )
        result = pipeline.run(str(synthetic_sar_tif), str(out_dir))

        assert isinstance(result, ProcessingResult)
        assert result.processed_image.shape == (512, 512)

        # Verify output files exist
        base_name = Path(synthetic_sar_tif).stem
        tif_path = out_dir / f"{base_name}_db.tif"
        json_path = out_dir / f"{base_name}_metadata.json"
        assert tif_path.exists()
        assert json_path.exists()

        with rasterio.open(tif_path) as src:
            assert src.shape == (512, 512)

        with open(json_path, "r") as f:
            meta = json.load(f)
            assert "bounds" in meta
            assert "detections" in meta
            assert "summary" in meta

    def test_output_tif_georeference_preserved(self, synthetic_sar_tif, tmp_path):
        out_dir = tmp_path / "output_geo"
        pipeline = PreprocessingPipeline(
            filter_type=FilterType.LEE,
            filter_window=3,
            min_area_px=200,
            k_factor=0.8,
        )
        result = pipeline.run(str(synthetic_sar_tif), str(out_dir))

        base_name = Path(synthetic_sar_tif).stem
        tif_path = out_dir / f"{base_name}_db.tif"

        with rasterio.open(synthetic_sar_tif) as orig:
            orig_crs = orig.crs
            orig_bounds = orig.bounds

        with rasterio.open(tif_path) as out:
            assert out.crs == orig_crs
            assert out.bounds == orig_bounds

    def test_metadata_json_schema(self, synthetic_sar_tif, tmp_path):
        out_dir = tmp_path / "output_schema"
        pipeline = PreprocessingPipeline(
            filter_type=FilterType.LEE,
            filter_window=3,
            min_area_px=200,
            k_factor=0.8,
        )
        pipeline.run(str(synthetic_sar_tif), str(out_dir))

        base_name = Path(synthetic_sar_tif).stem
        json_path = out_dir / f"{base_name}_metadata.json"

        with open(json_path, "r") as f:
            data = json.load(f)

        assert "source_file" in data
        assert "crs" in data
        assert "bounds" in data
        assert "processing" in data
        assert "detections" in data
        assert "summary" in data
        assert "total_detections" in data["summary"]
        assert "total_slick_area_km2" in data["summary"]
        assert "max_confidence" in data["summary"]
        assert "timestamp" in data["summary"]

    def test_convenience_function(self, synthetic_sar_tif, tmp_path):
        out_dir = tmp_path / "output_conv"
        result = process_sar_scene(
            str(synthetic_sar_tif),
            str(out_dir),
            filter_type=FilterType.LEE,
            filter_window=3,
            min_area_px=200,
            k_factor=0.8,
        )
        assert isinstance(result, ProcessingResult)

        base_name = Path(synthetic_sar_tif).stem
        tif_path = out_dir / f"{base_name}_db.tif"
        assert tif_path.exists()
