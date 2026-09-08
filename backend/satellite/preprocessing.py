"""SAR Preprocessing and Oil Spill Detection Engine.

This module implements a complete satellite data ingestion and processing
pipeline for detecting marine oil spills from Sentinel-1 SAR GRD imagery.

Pipeline stages:
    1. Ingest Sentinel-1 GRD GeoTIFF → extract intensity + geospatial metadata
    2. Speckle filtering (Lee / Refined Lee / Frost)
    3. Intensity → decibel (dB) conversion with contrast stretching
    4. Adaptive dark-spot segmentation (Adaptive Otsu / Sliding Window)
    5. Connected-component labelling, confidence scoring, and export

Designed for SIH 2026 problem SIH26143 (NTRO):
"Leveraging Satellite Imagery to Determine Oil Spills at Sea".
"""

import argparse
import dataclasses
import datetime
import json
import logging
import math
import time
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import cv2
import numpy as np
import rasterio
import scipy.ndimage as ndimage
import scipy.signal as signal

# ============================================================================
# 1. Imports & Constants
# ============================================================================

# Physical constants
SPEED_OF_LIGHT = 299792458.0  # m/s

# Configure module-level logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


# ============================================================================
# 2. Data Models (dataclasses)
# ============================================================================

@dataclasses.dataclass
class SARMetadata:
    """Geospatial metadata extracted from a Sentinel-1 GRD GeoTIFF."""
    filepath: Path
    crs: str
    bounds: tuple
    transform: rasterio.Affine
    width: int
    height: int
    pixel_size_m: Tuple[float, float]
    nodata: Optional[float]
    band_count: int
    dtype: str


@dataclasses.dataclass
class SlickDetection:
    """A single detected oil slick region."""
    slick_id: int
    area_km2: float
    center_lat: float
    center_lon: float
    bbox: Tuple[float, float, float, float]
    pixel_count: int
    mean_db: float
    contrast_ratio: float
    confidence: float


@dataclasses.dataclass
class ProcessingResult:
    """Complete output contract of the preprocessing pipeline."""
    metadata: SARMetadata
    detections: List[SlickDetection]
    processed_image: np.ndarray
    binary_mask: np.ndarray
    processing_time_s: float


# ============================================================================
# 3. Enum: FilterType
# ============================================================================

class FilterType(Enum):
    LEE = "lee"
    REFINED_LEE = "refined_lee"
    FROST = "frost"


# ============================================================================
# 4. Class: SARIngestor
# ============================================================================

class SARIngestor:
    """Responsible for reading Sentinel-1 GRD GeoTIFF files."""

    def __init__(self, filepath: Union[str, Path]):
        self.filepath = Path(filepath)
        if not self.filepath.exists():
            raise FileNotFoundError(f"File not found: {self.filepath}")
        if self.filepath.suffix.lower() not in ('.tif', '.tiff'):
            raise ValueError(
                f"Invalid file extension '{self.filepath.suffix}'. "
                f"Expected a GeoTIFF file (.tif or .tiff)."
            )

    def ingest(self) -> Tuple[np.ndarray, SARMetadata]:
        """
        Open with rasterio, read band 1 as float64 array, extract full metadata.
        """
        logger.info(f"Ingesting SAR imagery from {self.filepath}")
        with rasterio.open(self.filepath) as src:
            image = src.read(1).astype(np.float64)
            transform = src.transform
            
            # pixel_size_m (x_res, y_res)
            # transform.a is pixel width, transform.e is pixel height (usually negative)
            # This is an approximation for lat/lon, but exact for projected CRS.
            # Assuming the inputs are usually in a projected CRS for accurate sizing, or degree conversion needed.
            # We'll use the absolute values of the transform parameters as requested.
            pixel_size_m = (abs(transform.a), abs(transform.e))
            
            # If the CRS is geographic (degrees), this approximation is flawed for real meters, 
            # but we adhere to the basic definition provided. A robust implementation would use pyproj.
            if src.crs and src.crs.is_geographic:
                # roughly degrees to meters at equator
                pixel_size_m = (abs(transform.a) * 111320, abs(transform.e) * 111320)
                
            crs_str = src.crs.to_string() if src.crs else "EPSG:4326"

            metadata = SARMetadata(
                filepath=self.filepath,
                crs=crs_str,
                bounds=(src.bounds.left, src.bounds.bottom, src.bounds.right, src.bounds.top),
                transform=transform,
                width=src.width,
                height=src.height,
                pixel_size_m=pixel_size_m,
                nodata=src.nodata,
                band_count=src.count,
                dtype=str(src.meta['dtype'])
            )

            # Handle edge cases: nodata masking, zero-value pixels
            if metadata.nodata is not None:
                image[image == metadata.nodata] = 1e-10
            image[image <= 0] = 1e-10

            return image, metadata


# ============================================================================
# 5. Class: SpeckleFilter
# ============================================================================

class SpeckleFilter:
    """Implements three real speckle filter algorithms."""

    def __init__(self, filter_type: FilterType = FilterType.REFINED_LEE, window_size: int = 7):
        self.filter_type = filter_type
        self.window_size = window_size
        self.damping_factor = 2.0

    def apply(self, image: np.ndarray) -> np.ndarray:
        """Dispatcher to the selected filter."""
        logger.info(f"Applying speckle filter: {self.filter_type.value} with window size {self.window_size}")
        if self.filter_type == FilterType.LEE:
            return self._lee_filter(image)
        elif self.filter_type == FilterType.REFINED_LEE:
            return self._refined_lee_filter(image)
        elif self.filter_type == FilterType.FROST:
            return self._frost_filter(image)
        else:
            raise ValueError(f"Unknown filter type: {self.filter_type}")

    def _lee_filter(self, image: np.ndarray) -> np.ndarray:
        """Standard Lee Filter."""
        image_mean = ndimage.uniform_filter(image, size=self.window_size)
        image_sqr_mean = ndimage.uniform_filter(image**2, size=self.window_size)
        image_var = image_sqr_mean - image_mean**2

        # Estimate global noise variance from the image
        # Standard Lee assumes noise variance can be approximated by variance in homogeneous areas.
        # We'll use a global estimation for simplicity: global coefficient of variation squared
        global_mean = np.mean(image)
        global_var = np.var(image)
        noise_var = global_var / (global_mean**2 + 1e-8) if global_mean > 0 else 1.0

        # Lee formula: output = mean + k * (pixel - mean)
        # where k = variance / (variance + noise_variance * mean^2) for multiplicative noise
        # Using the formulation requested: k = variance / (variance + noise_variance)
        k = image_var / (image_var + noise_var + 1e-8)
        output = image_mean + k * (image - image_mean)
        return output

    def _refined_lee_filter(self, image: np.ndarray) -> np.ndarray:
        """Refined Lee Filter (edge-aligned)."""
        # Create 8 directional kernels
        k_size = self.window_size
        kernels = []
        
        # We define simple directional line masks
        for i in range(8):
            k = np.zeros((k_size, k_size))
            if i == 0: k[k_size//2, :] = 1 # Horizontal
            elif i == 1: k[:, k_size//2] = 1 # Vertical
            elif i == 2: np.fill_diagonal(k, 1) # Diagonal 1
            elif i == 3: np.fill_diagonal(np.fliplr(k), 1) # Diagonal 2
            elif i == 4: k[:k_size//2, :] = 1 # Top half
            elif i == 5: k[k_size//2+1:, :] = 1 # Bottom half
            elif i == 6: k[:, :k_size//2] = 1 # Left half
            elif i == 7: k[:, k_size//2+1:] = 1 # Right half
            k /= np.sum(k)
            kernels.append(k)
            
        means = np.zeros((8, *image.shape))
        vars = np.zeros((8, *image.shape))
        
        for i, kernel in enumerate(kernels):
            means[i] = ndimage.convolve(image, kernel, mode='reflect')
            sqr_means = ndimage.convolve(image**2, kernel, mode='reflect')
            vars[i] = np.maximum(sqr_means - means[i]**2, 0)
            
        # Select the direction with minimum variance
        min_var_idx = np.argmin(vars, axis=0)
        
        # Gather chosen mean and var
        chosen_mean = np.take_along_axis(means, np.expand_dims(min_var_idx, axis=0), axis=0)[0]
        chosen_var = np.take_along_axis(vars, np.expand_dims(min_var_idx, axis=0), axis=0)[0]
        
        global_var = np.var(image)
        noise_var = global_var / (np.mean(image)**2 + 1e-8)
        
        k = chosen_var / (chosen_var + noise_var + 1e-8)
        output = chosen_mean + k * (image - chosen_mean)
        return output

    def _frost_filter(self, image: np.ndarray) -> np.ndarray:
        """Frost Filter (Exponentially weighted adaptive filter)."""
        local_mean = ndimage.uniform_filter(image, size=self.window_size)
        local_sqr_mean = ndimage.uniform_filter(image**2, size=self.window_size)
        local_var = np.maximum(local_sqr_mean - local_mean**2, 0)
        
        # Coefficient of variation squared
        ci2 = local_var / (local_mean**2 + 1e-8)
        
        half_win = self.window_size // 2
        result = np.zeros_like(image)
        weight_sum = np.zeros_like(image)
        
        # Shift-based convolution for spatially variant kernel
        for y in range(-half_win, half_win + 1):
            for x in range(-half_win, half_win + 1):
                dist = np.sqrt(x**2 + y**2)
                
                shifted_image = np.roll(image, shift=(y, x), axis=(0, 1))
                # Frost weighting uses the center pixel's Ci² — the kernel
                # adapts to local heterogeneity at the pixel being filtered.
                weight = np.exp(-self.damping_factor * ci2 * dist)
                result += shifted_image * weight
                weight_sum += weight
                
        # Fix boundaries due to roll
        result = result / (weight_sum + 1e-8)
        return result


# ============================================================================
# 6. Class: IntensityToDecibel
# ============================================================================

class IntensityToDecibel:
    """Converts SAR intensity to decibel scale and normalizes it."""

    def __init__(self, floor_db: float = -30.0):
        self.floor_db = floor_db

    def convert(self, intensity: np.ndarray) -> np.ndarray:
        """Convert SAR intensity to decibel scale: dB = 10 * log10(intensity).

        For uncalibrated Sentinel-1 GRD data, intensity values are typically
        raw digital numbers (DN²) in the hundreds-to-thousands range, yielding
        positive dB values.  Only the lower tail is clamped at ``floor_db`` to
        suppress extreme noise spikes.
        """
        logger.info("Converting intensity to decibel (dB) scale.")
        with np.errstate(divide='ignore', invalid='ignore'):
            # Clamp zeros and negatives to a small epsilon before log
            clamped = np.maximum(intensity, 1e-10)
            db_image = 10.0 * np.log10(clamped)

        # Only apply a floor clamp — do NOT cap positive dB values, as raw
        # SAR DN intensities routinely exceed 10 * log10(1) = 0 dB.
        db_image = np.maximum(db_image, self.floor_db)
        return db_image

    def normalize(self, db_image: np.ndarray) -> np.ndarray:
        """Min-max normalize the dB image to [0, 1] range."""
        min_val = np.min(db_image)
        max_val = np.max(db_image)
        if max_val > min_val:
            return (db_image - min_val) / (max_val - min_val)
        return np.zeros_like(db_image)


# ============================================================================
# 7. Class: AdaptiveSlickDetector
# ============================================================================

class AdaptiveSlickDetector:
    """The core oil spill detection engine using adaptive thresholding."""

    def __init__(self, method: str = 'adaptive_otsu', block_size: int = 127, 
                 k_factor: float = 0.3, min_area_px: int = 500, morphology_kernel_size: int = 5):
        self.method = method
        self.block_size = block_size
        self.k_factor = k_factor
        self.min_area_px = min_area_px
        self.morphology_kernel_size = morphology_kernel_size

    def detect(self, db_image: np.ndarray, metadata: SARMetadata) -> Tuple[np.ndarray, List[SlickDetection]]:
        """Full detection pipeline."""
        logger.info(f"Running detection using {self.method}")
        
        # 1. Thresholding
        if self.method == 'adaptive_otsu':
            threshold_surface = self._adaptive_otsu(db_image)
            # For dB images (negative values), a pixel is "dark" if it falls
            # below the local Otsu threshold by k_factor times the image range.
            global_range = np.ptp(db_image)  # peak-to-peak dynamic range
            if global_range < 1e-6:
                # Perfectly uniform image — no anomalies possible
                logger.info("Image is uniform; skipping detection.")
                binary_mask = np.zeros(db_image.shape, dtype=np.uint8)
            else:
                binary_mask = (db_image < (threshold_surface - self.k_factor * global_range)).astype(np.uint8)
        elif self.method == 'sliding_window':
            binary_mask = self._sliding_window_dark_spot(db_image)
        else:
            raise ValueError(f"Unknown detection method: {self.method}")
            
        binary_mask = binary_mask.astype(np.uint8)
            
        # 2. Morphological cleanup
        clean_mask = self._morphological_cleanup(binary_mask)
        
        # 3. Component labeling & slick extraction
        detections = self._extract_slick_regions(clean_mask, db_image, metadata)
        
        return clean_mask, detections

    def _adaptive_otsu(self, image: np.ndarray) -> np.ndarray:
        """Localized Adaptive Otsu."""
        h, w = image.shape
        # Ensure block size is reasonable
        bs = min(self.block_size, h, w)
        
        tiles_y = int(np.ceil(h / bs))
        tiles_x = int(np.ceil(w / bs))
        
        thresh_surf = np.zeros((tiles_y, tiles_x))
        
        for i in range(tiles_y):
            for j in range(tiles_x):
                tile = image[i*bs:(i+1)*bs, j*bs:(j+1)*bs]
                t_min, t_max = np.min(tile), np.max(tile)
                
                if t_max > t_min:
                    # scale to 0-255 for cv2 Otsu
                    tile_u8 = ((tile - t_min) / (t_max - t_min) * 255).astype(np.uint8)
                    t_val, _ = cv2.threshold(tile_u8, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                    t_real = (t_val / 255.0) * (t_max - t_min) + t_min
                    thresh_surf[i, j] = t_real
                else:
                    thresh_surf[i, j] = np.mean(tile)
                    
        # Bilinear interpolation back to full size
        threshold_surface = cv2.resize(thresh_surf, (w, h), interpolation=cv2.INTER_LINEAR)
        return threshold_surface

    def _sliding_window_dark_spot(self, image: np.ndarray) -> np.ndarray:
        """Sliding Window Anomaly Detector."""
        local_mean = ndimage.uniform_filter(image, size=self.block_size)
        local_sqr_mean = ndimage.uniform_filter(image**2, size=self.block_size)
        local_var = np.maximum(local_sqr_mean - local_mean**2, 0)
        local_std = np.sqrt(local_var)
        
        # Anomalous if pixel < local_mean - k_factor * local_std
        mask = image < (local_mean - self.k_factor * local_std)
        return mask

    def _morphological_cleanup(self, mask: np.ndarray) -> np.ndarray:
        """Apply morphological opening and closing, then remove small components."""
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, 
                                           (self.morphology_kernel_size, self.morphology_kernel_size))
        
        # Opening (remove small noise)
        opened = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        # Closing (fill small gaps)
        closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel)
        
        # Remove components smaller than min_area_px
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(closed, connectivity=8)
        clean_mask = np.zeros_like(closed)
        
        for i in range(1, num_labels):
            if stats[i, cv2.CC_STAT_AREA] >= self.min_area_px:
                clean_mask[labels == i] = 1
                
        return clean_mask

    def _extract_slick_regions(self, mask: np.ndarray, db_image: np.ndarray, metadata: SARMetadata) -> List[SlickDetection]:
        """Use cv2.connectedComponentsWithStats to extract and score slick regions."""
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)
        detections = []
        
        global_mean = np.mean(db_image)
        
        for i in range(1, num_labels):
            pixel_count = stats[i, cv2.CC_STAT_AREA]
            if pixel_count < self.min_area_px:
                continue
                
            # Geometry
            x, y, w, h = stats[i, cv2.CC_STAT_LEFT], stats[i, cv2.CC_STAT_TOP], stats[i, cv2.CC_STAT_WIDTH], stats[i, cv2.CC_STAT_HEIGHT]
            cx, cy = centroids[i]
            
            # Area in km2
            area_km2 = pixel_count * metadata.pixel_size_m[0] * metadata.pixel_size_m[1] / 1e6
            
            # Transform pixel to geo coordinates
            center_lon, center_lat = metadata.transform @ (cx, cy)
            
            # Calculate bbox in geo coordinates
            west, north = metadata.transform @ (x, y)
            east, south = metadata.transform @ (x + w, y + h)
            bbox = (min(west, east), min(south, north), max(west, east), max(south, north))
            
            # Mask for current slick
            slick_mask = (labels == i)
            
            # Annular surround for contrast ratio
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
            dilated = cv2.dilate(slick_mask.astype(np.uint8), kernel)
            surround_mask = (dilated > 0) & (~slick_mask)
            
            slick_mean = float(np.mean(db_image[slick_mask]))
            
            if np.sum(surround_mask) > 0:
                surround_mean = float(np.mean(db_image[surround_mask]))
            else:
                surround_mean = global_mean
                
            # Contrast ratio (in dB, a difference is a ratio of intensities)
            # Since we are already in dB, we can use the difference or raw ratio.
            # Usually contrast is surround - slick (in dB). Let's use slick_mean / surround_mean if negative, 
            # but dB is negative. 
            contrast_ratio = abs(slick_mean / (surround_mean + 1e-8))
            
            # Confidence score calculation
            # 1. Area significance (saturates around 5 km2)
            score_area = min(area_km2 / 5.0, 1.0)
            
            # 2. Contrast (high contrast is good)
            contrast_diff = surround_mean - slick_mean # positive if slick is darker
            score_contrast = min(max(contrast_diff / 10.0, 0.0), 1.0) 
            
            # 3. Compactness = 4 * pi * area / perimeter^2
            # For shapes, a true oil slick is often elongated, so compactness is variable, but extremely complex shapes might be noise.
            # Using a simplified compactness based on bounding box
            perimeter_est = 2 * (w + h)
            compactness = (4 * np.pi * pixel_count) / (perimeter_est**2 + 1e-8)
            score_shape = min(max(compactness, 0.0), 1.0)
            
            confidence = 0.5 * score_contrast + 0.3 * score_area + 0.2 * score_shape
            
            detection = SlickDetection(
                slick_id=i,
                area_km2=area_km2,
                center_lat=center_lat,
                center_lon=center_lon,
                bbox=bbox,
                pixel_count=pixel_count,
                mean_db=slick_mean,
                contrast_ratio=contrast_ratio,
                confidence=min(max(confidence, 0.0), 1.0)
            )
            detections.append(detection)
            
        logger.info(f"Extracted {len(detections)} slicks.")
        return detections


# ============================================================================
# 8. Class: PreprocessingPipeline (Orchestrator)
# ============================================================================

class PreprocessingPipeline:
    """Orchestrates the full SAR preprocessing and detection pipeline."""

    def __init__(self, filter_type: FilterType = FilterType.REFINED_LEE, filter_window: int = 7, 
                 detection_method: str = 'adaptive_otsu', block_size: int = 127, 
                 k_factor: float = 0.3, min_area_px: int = 500, floor_db: float = -30.0):
        self.filter_type = filter_type
        self.filter_window = filter_window
        self.detection_method = detection_method
        self.block_size = block_size
        self.k_factor = k_factor
        self.min_area_px = min_area_px
        self.floor_db = floor_db

    def run(self, input_path: Union[str, Path], output_dir: Optional[Union[str, Path]] = None) -> ProcessingResult:
        """Full pipeline orchestration."""
        start_time = datetime.datetime.now()
        input_path = Path(input_path)
        logger.info(f"Starting pipeline for {input_path}")
        
        # 1. Ingest
        ingestor = SARIngestor(input_path)
        image, metadata = ingestor.ingest()
        
        # 2. Speckle Filter
        speckle_filter = SpeckleFilter(filter_type=self.filter_type, window_size=self.filter_window)
        filtered_image = speckle_filter.apply(image)
        
        # 3. Convert to dB
        converter = IntensityToDecibel(floor_db=self.floor_db)
        db_image = converter.convert(filtered_image)
        
        # 4. Run adaptive detection
        detector = AdaptiveSlickDetector(
            method=self.detection_method, 
            block_size=self.block_size, 
            k_factor=self.k_factor, 
            min_area_px=self.min_area_px
        )
        binary_mask, detections = detector.detect(db_image, metadata)
        
        end_time = datetime.datetime.now()
        processing_time_s = (end_time - start_time).total_seconds()
        logger.info(f"Pipeline completed in {processing_time_s:.2f} seconds.")
        
        result = ProcessingResult(
            metadata=metadata,
            detections=detections,
            processed_image=db_image,
            binary_mask=binary_mask,
            processing_time_s=processing_time_s
        )
        
        # 5. Export outputs
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            base_name = input_path.stem
            
            tif_out = output_dir / f"{base_name}_db.tif"
            self._export_processed_tif(db_image, metadata, tif_out)
            
            mask_out = output_dir / f"{base_name}_mask.tif"
            self._export_processed_tif(binary_mask, metadata, mask_out)
            
            json_out = output_dir / f"{base_name}_metadata.json"
            self._export_metadata_json(result, json_out)
            
        return result

    def _export_processed_tif(self, image: np.ndarray, metadata: SARMetadata, output_path: Path):
        """Write processed image as GeoTIFF preserving CRS and transform."""
        logger.info(f"Exporting GeoTIFF to {output_path}")
        with rasterio.open(
            output_path,
            'w',
            driver='GTiff',
            height=image.shape[0],
            width=image.shape[1],
            count=1,
            dtype=image.dtype,
            crs=metadata.crs,
            transform=metadata.transform,
        ) as dst:
            dst.write(image, 1)

    def _export_metadata_json(self, result: ProcessingResult, output_path: Path):
        """Write standardized metadata.json."""
        logger.info(f"Exporting metadata to {output_path}")
        
        total_area = sum(d.area_km2 for d in result.detections)
        max_conf = max((d.confidence for d in result.detections), default=0.0)
        
        data = {
            "source_file": str(result.metadata.filepath.name),
            "crs": result.metadata.crs,
            "bounds": {
                "west": result.metadata.bounds[0],
                "south": result.metadata.bounds[1],
                "east": result.metadata.bounds[2],
                "north": result.metadata.bounds[3]
            },
            "processing": {
                "filter_type": self.filter_type.value,
                "filter_window": self.filter_window,
                "detection_method": self.detection_method,
                "processing_time_s": result.processing_time_s
            },
            "detections": [
                {
                    "slick_id": d.slick_id,
                    "area_km2": d.area_km2,
                    "center": {"lat": d.center_lat, "lon": d.center_lon},
                    "bbox": {
                        "west": d.bbox[0],
                        "south": d.bbox[1],
                        "east": d.bbox[2],
                        "north": d.bbox[3]
                    },
                    "confidence": d.confidence,
                    "mean_backscatter_db": d.mean_db,
                    "contrast_ratio": d.contrast_ratio
                }
                for d in result.detections
            ],
            "summary": {
                "total_detections": len(result.detections),
                "total_slick_area_km2": total_area,
                "max_confidence": max_conf,
                "timestamp": datetime.datetime.now().isoformat()
            }
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)


# ============================================================================
# 9. Module-level convenience function
# ============================================================================

def process_sar_scene(input_path: Union[str, Path], output_dir: Optional[Union[str, Path]] = None, **kwargs) -> ProcessingResult:
    """One-liner convenience function to process a SAR scene."""
    
    # Extract enum if passed as string
    if 'filter_type' in kwargs and isinstance(kwargs['filter_type'], str):
        kwargs['filter_type'] = FilterType(kwargs['filter_type'])
        
    pipeline = PreprocessingPipeline(**kwargs)
    return pipeline.run(input_path, output_dir)


# ============================================================================
# 10. CLI Block
# ============================================================================

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="SAR Preprocessing and Oil Spill Detection")
    parser.add_argument("input_file", help="Path to input Sentinel-1 GRD GeoTIFF")
    parser.add_argument("--output_dir", "-o", help="Directory to save output files")
    parser.add_argument("--filter", type=str, choices=["lee", "refined_lee", "frost"], default="refined_lee", help="Speckle filter type")
    parser.add_argument("--window_size", type=int, default=7, help="Filter window size")
    parser.add_argument("--method", type=str, choices=["adaptive_otsu", "sliding_window"], default="adaptive_otsu", help="Detection method")
    parser.add_argument("--block_size", type=int, default=127, help="Block size for adaptive thresholding")
    parser.add_argument("--k_factor", type=float, default=0.3, help="K factor for thresholding")
    
    args = parser.parse_args()
    
    print(f"Processing: {args.input_file}")
    result = process_sar_scene(
        input_path=args.input_file,
        output_dir=args.output_dir,
        filter_type=FilterType(args.filter),
        filter_window=args.window_size,
        detection_method=args.method,
        block_size=args.block_size,
        k_factor=args.k_factor
    )
    
    print("-" * 50)
    print(f"Detection Summary:")
    print(f"Total Detections: {len(result.detections)}")
    total_area = sum(d.area_km2 for d in result.detections)
    print(f"Total Area: {total_area:.2f} km^2")
    if result.detections:
        highest_conf = max(result.detections, key=lambda d: d.confidence)
        print(f"Highest Confidence Slick: ID {highest_conf.slick_id} ({highest_conf.confidence:.2f}) at Lat/Lon: {highest_conf.center_lat:.4f}, {highest_conf.center_lon:.4f}")
    print(f"Processing Time: {result.processing_time_s:.2f} s")
    print("-" * 50)
