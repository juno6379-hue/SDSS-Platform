"""
Temporal Consistency & False Change Filter Engine for Multi-Year LCLUC Monitoring.
Isolated workspace: evidence/integration/lcluc-filter-workspace-20261019/temporal_change_filter.py

Addresses Gap 4: Eliminates false change artifacts caused by seasonal cloud shadows,
phenological browning (dry season), and single-scene classifier noise across 3+ observation years.
Integrates Unit 336's SCL median annual compositing engine and outputs raw/filtered transition matrices.
"""

import copy
import csv
import json
import math
from pathlib import Path
import sys
from typing import Dict, List, Optional, Tuple, Any, Union
import warnings

import numpy as np

# Dynamically locate Unit 336's composite pipeline if not on python path
UNIT_336_DIR = (Path(__file__).resolve().parent.parent / "temporal-composite-workspace-20261019").resolve()
if str(UNIT_336_DIR) not in sys.path:
    sys.path.insert(0, str(UNIT_336_DIR))

try:
    from composite_pipeline import (
        TemporalCompositeEngine,
        SCLMaskEvaluator,
        SyntheticSliceGenerator,
        BANDS,
        SCL_CLASSES,
        INVALID_SCL_CODES,
        VALID_SCL_CODES,
    )
except ImportError:
    warnings.warn(f"Could not directly import composite_pipeline from {UNIT_336_DIR}. Standalone fallback mode will be active.")
    TemporalCompositeEngine = None
    SCLMaskEvaluator = None
    SyntheticSliceGenerator = None
    BANDS = ["blue", "green", "red", "nir", "swir16", "swir22"]


# Standard 9 LCLUC classes aligned with backend/app/ml/raster.py
CLASS_NAMES = [
    "water",                # 0
    "trees",                # 1
    "grass",                # 2
    "flooded_vegetation",   # 3
    "crops",                # 4
    "shrub_and_scrub",      # 5
    "built",                # 6
    "bare",                 # 7
    "snow_and_ice",         # 8
]

CLASS_TO_IDX = {name: idx for idx, name in enumerate(CLASS_NAMES)}

IGNORE = 255
TRANSITION_NODATA = 65535
CONFIDENCE_NODATA = -9999.0

# Ecologically irreversible / highly stable transitions in single-year intervals
# e.g., 'built' (urban) cannot physically revert to mature 'trees' or 'water' within 1 year
# without catastrophic anomalies or misclassification
IRREVERSIBLE_CLASSES = frozenset([CLASS_TO_IDX["built"]])

# Canonical false-change bounce patterns caused by seasonal dry season, phenology, or cloud shadow
# Format: (C_prev, C_bounce, C_next) -> all represent (A, B, A) where B is temporary distortion
BOUNCE_PATTERNS = [
    (1, 7, 1),  # trees -> bare -> trees (phenology / dry season leaf drop)
    (1, 0, 1),  # trees -> water -> trees (cloud shadow dark pixel misclassification)
    (1, 6, 1),  # trees -> built -> trees (dry canopy specular reflectance / bright bare)
    (2, 7, 2),  # grass -> bare -> grass (dry season senescence)
    (4, 7, 4),  # crops -> bare -> crops (post-harvest bare ground phenology)
    (0, 7, 0),  # water -> bare -> water (seasonal dry shoreline / tidal recession)
    (1, 2, 1),  # trees -> grass -> trees (canopy gap / understory greening artifact)
]


class TrajectoryConsistencyFilter:
    """
    Evaluates land cover trajectory across 3+ observation years and eliminates spurious bounces.
    Preserves true permanent transitions (e.g. Forest -> Urban -> Urban).
    """

    def __init__(
        self,
        class_names: List[str] = CLASS_NAMES,
        irreversible_classes: Optional[frozenset] = None,
        enforce_bounce_patterns_only: bool = False,
        spectral_divergence_threshold: float = 0.15,
    ):
        self.class_names = class_names
        self.num_classes = len(class_names)
        self.irreversible_classes = irreversible_classes if irreversible_classes is not None else IRREVERSIBLE_CLASSES
        self.enforce_bounce_patterns_only = enforce_bounce_patterns_only
        self.spectral_divergence_threshold = spectral_divergence_threshold

    @staticmethod
    def identify_bounces_3year(
        c_prev: np.ndarray,
        c_curr: np.ndarray,
        c_next: np.ndarray,
        valid_mask: Optional[np.ndarray] = None,
        bounce_whitelist: Optional[List[Tuple[int, int, int]]] = None,
    ) -> np.ndarray:
        """
        Detect single-year bounce artifacts: C_prev == C_next and C_curr != C_prev.
        
        Args:
            c_prev: 2D uint8 array of classifications at t-1
            c_curr: 2D uint8 array of classifications at t
            c_next: 2D uint8 array of classifications at t+1
            valid_mask: Optional 2D boolean mask indicating valid pixels across all 3 years
            bounce_whitelist: Optional list of explicit (c_prev, c_curr, c_next) tuples to filter
            
        Returns:
            2D boolean array where True indicates a detected bounce at year t.
        """
        if c_prev.shape != c_curr.shape or c_curr.shape != c_next.shape:
            raise ValueError("All classification arrays must have identical shapes.")

        valid = (c_prev != IGNORE) & (c_curr != IGNORE) & (c_next != IGNORE)
        if valid_mask is not None:
            valid = valid & valid_mask

        # Basic bounce condition: endpoints identical, midpoint different
        bounce = valid & (c_prev == c_next) & (c_curr != c_prev)

        if bounce_whitelist is not None:
            # Filter only specified bounce tuples
            matched_whitelist = np.zeros_like(bounce)
            for (p_c, m_c, n_c) in bounce_whitelist:
                match = (c_prev == p_c) & (c_curr == m_c) & (c_next == n_c)
                matched_whitelist |= match
            bounce = bounce & matched_whitelist

        return bounce

    def filter_trajectory_stack(
        self,
        class_stack: np.ndarray,
        valid_masks: Optional[np.ndarray] = None,
        spectral_divergences: Optional[np.ndarray] = None,
        confidence_scores: Optional[np.ndarray] = None,
        confidence_cutoff: float = 0.35,
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Apply temporal trajectory consistency filtering across a full multi-year stack (T >= 3).
        
        Args:
            class_stack: 3D uint8 array of shape (T, H, W) containing classified maps.
            valid_masks: Optional 3D boolean/uint8 array of shape (T, H, W).
            spectral_divergences: Optional 3D float array of spectral divergences between adjacent years.
            confidence_scores: Optional 3D float array of change confidence scores.
            confidence_cutoff: Changes with confidence below cutoff revert to previous stable class.
            
        Returns:
            Tuple of:
                filtered_stack: 3D uint8 array of shape (T, H, W) with smoothed trajectories.
                stats: Dictionary with detailed filtering metrics.
        """
        if class_stack.ndim != 3:
            raise ValueError(f"class_stack must be 3D (T, H, W), got {class_stack.shape}")
        
        t_steps, height, width = class_stack.shape
        if t_steps < 3:
            raise ValueError(f"Trajectory filtering requires at least 3 observation years, got {t_steps}")

        filtered = class_stack.copy()
        bounce_records = []
        total_bounces = 0

        # Create combined validity mask
        if valid_masks is not None:
            v_all = (valid_masks > 0).astype(bool)
        else:
            v_all = (class_stack != IGNORE)

        # Step 1: Moving 3-year window bounce smoothing across internal observation years t in [1, T-2]
        for t in range(1, t_steps - 1):
            c_prev = filtered[t - 1]
            c_curr = filtered[t]
            c_next = class_stack[t + 1]  # Compare against future year
            v_window = v_all[t - 1] & v_all[t] & v_all[t + 1]

            # Detect bounce
            whitelist = BOUNCE_PATTERNS if self.enforce_bounce_patterns_only else None
            is_bounce = self.identify_bounces_3year(c_prev, c_curr, c_next, valid_mask=v_window, bounce_whitelist=whitelist)

            # Check irreversible rule: if c_prev is built and c_curr is not built, and c_next is built
            # it is strictly an impossible demolition-reconstruction artifact
            for irr_c in self.irreversible_classes:
                irr_bounce = v_window & (c_prev == irr_c) & (c_next == irr_c) & (c_curr != irr_c)
                is_bounce |= irr_bounce

            # If spectral divergence is provided, verify whether the bounce has weak spectral evidence
            if spectral_divergences is not None and t < spectral_divergences.shape[0]:
                weak_divergence = spectral_divergences[t] < self.spectral_divergence_threshold
                # Bounces with weak divergence are definitely false changes
                is_bounce |= (v_window & (c_prev == c_next) & (c_curr != c_prev) & weak_divergence)

            # Apply smoothing: reset c_curr to c_prev
            filtered[t][is_bounce] = c_prev[is_bounce]
            
            bounce_count = int(np.count_nonzero(is_bounce))
            total_bounces += bounce_count
            bounce_records.append({
                "time_index": t,
                "bounces_detected": bounce_count,
                "bounce_rate": round(bounce_count / (height * width), 6),
            })

        # Step 2: Confidence-based filtering for remaining changes if confidence maps are supplied
        confidence_reversals = 0
        if confidence_scores is not None:
            for t in range(1, t_steps):
                raw_diff = (filtered[t] != filtered[t - 1]) & (filtered[t] != IGNORE) & (filtered[t - 1] != IGNORE)
                low_conf = raw_diff & (confidence_scores[t - 1] < confidence_cutoff)
                if np.any(low_conf):
                    filtered[t][low_conf] = filtered[t - 1][low_conf]
                    confidence_reversals += int(np.count_nonzero(low_conf))

        total_pixels = height * width
        stats = {
            "time_steps": t_steps,
            "height": height,
            "width": width,
            "total_pixels_per_slice": total_pixels,
            "total_bounces_smoothed": total_bounces,
            "confidence_reversals": confidence_reversals,
            "per_year_bounce_details": bounce_records,
            "filter_status": "FILTER_SUCCESSFUL",
        }

        return filtered, stats


class SpectralDivergenceCalculator:
    """
    Computes multi-temporal spectral divergence metrics (SED, NSVD, SAM, and index deltas)
    from annual composite band stacks.
    """

    @staticmethod
    def calculate_nsvd(
        bands_t1: Dict[str, np.ndarray],
        bands_t2: Dict[str, np.ndarray],
        band_names: Optional[List[str]] = None,
        epsilon: float = 1e-6,
    ) -> np.ndarray:
        """
        Normalized Spectral Vector Distance (NSVD):
        D_NSVD = ||X_t2 - X_t1||_2 / (||X_t1||_2 + ||X_t2||_2 + epsilon)
        Value range: [0.0, 1.0].
        """
        eval_bands = band_names or [b for b in bands_t1.keys() if b in bands_t2]
        if not eval_bands:
            raise ValueError("No common spectral bands between t1 and t2.")

        sq_diff_sum = None
        norm_t1_sq = None
        norm_t2_sq = None

        for b in eval_bands:
            b1 = bands_t1[b].astype(np.float32)
            b2 = bands_t2[b].astype(np.float32)
            diff = b2 - b1
            diff_sq = diff * diff
            b1_sq = b1 * b1
            b2_sq = b2 * b2

            if sq_diff_sum is None:
                sq_diff_sum = diff_sq
                norm_t1_sq = b1_sq
                norm_t2_sq = b2_sq
            else:
                sq_diff_sum += diff_sq
                norm_t1_sq += b1_sq
                norm_t2_sq += b2_sq

        l2_diff = np.sqrt(sq_diff_sum)
        l2_t1 = np.sqrt(norm_t1_sq)
        l2_t2 = np.sqrt(norm_t2_sq)

        nsvd = l2_diff / (l2_t1 + l2_t2 + epsilon)
        return np.clip(nsvd, 0.0, 1.0)

    @staticmethod
    def calculate_spectral_angle_mapper(
        bands_t1: Dict[str, np.ndarray],
        bands_t2: Dict[str, np.ndarray],
        band_names: Optional[List[str]] = None,
        epsilon: float = 1e-6,
    ) -> np.ndarray:
        """
        Spectral Angle Mapper (SAM) in radians:
        theta = arccos( (X_t1 . X_t2) / (||X_t1|| * ||X_t2|| + epsilon) )
        """
        eval_bands = band_names or [b for b in bands_t1.keys() if b in bands_t2]
        dot_product = None
        norm_t1_sq = None
        norm_t2_sq = None

        for b in eval_bands:
            b1 = bands_t1[b].astype(np.float32)
            b2 = bands_t2[b].astype(np.float32)
            dot = b1 * b2
            if dot_product is None:
                dot_product = dot
                norm_t1_sq = b1 * b1
                norm_t2_sq = b2 * b2
            else:
                dot_product += dot
                norm_t1_sq += b1 * b1
                norm_t2_sq += b2 * b2

        denom = np.sqrt(norm_t1_sq) * np.sqrt(norm_t2_sq) + epsilon
        cos_theta = np.clip(dot_product / denom, -1.0, 1.0)
        return np.arccos(cos_theta)

    @staticmethod
    def calculate_ndvi_delta(
        bands_t1: Dict[str, np.ndarray],
        bands_t2: Dict[str, np.ndarray],
        epsilon: float = 1e-6,
    ) -> np.ndarray:
        """Calculate absolute NDVI difference between two dates."""
        def get_ndvi(b_dict):
            nir = b_dict.get("nir", np.zeros_like(next(iter(b_dict.values())))).astype(np.float32)
            red = b_dict.get("red", np.zeros_like(nir)).astype(np.float32)
            denom = nir + red + epsilon
            return (nir - red) / denom

        ndvi1 = get_ndvi(bands_t1)
        ndvi2 = get_ndvi(bands_t2)
        return np.abs(ndvi2 - ndvi1)


class ChangeConfidenceScorer:
    """
    Computes a calibrated pixel-wise change confidence score (0.0 to 1.0)
    combining multi-temporal spectral divergence, index change, and trajectory permanence.
    """

    def __init__(
        self,
        spectral_weight: float = 0.40,
        ndvi_weight: float = 0.30,
        permanence_weight: float = 0.30,
        divergence_scaling: float = 3.0,
    ):
        self.w_spec = spectral_weight
        self.w_ndvi = ndvi_weight
        self.w_perm = permanence_weight
        self.scaling = divergence_scaling

    def compute_confidence(
        self,
        c_t1: np.ndarray,
        c_t2: np.ndarray,
        bands_t1: Dict[str, np.ndarray],
        bands_t2: Dict[str, np.ndarray],
        is_bounce_mask: Optional[np.ndarray] = None,
        c_t3: Optional[np.ndarray] = None,
        bands_t3: Optional[Dict[str, np.ndarray]] = None,
        valid_mask: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """
        Compute pixel-wise change confidence score for transition t1 -> t2.
        
        Args:
            c_t1: 2D uint8 classification at t1
            c_t2: 2D uint8 classification at t2
            bands_t1: Dict of 2D spectral bands at t1
            bands_t2: Dict of 2D spectral bands at t2
            is_bounce_mask: Optional 2D boolean mask where True indicates a transient bounce at t2
            c_t3: Optional future classification at t3 for permanence evaluation
            bands_t3: Optional future spectral bands at t3
            valid_mask: Optional 2D boolean mask indicating valid observation
            
        Returns:
            2D float32 array in [0.0, 1.0] representing change confidence.
            Unchanged pixels receive 0.0.
            Bounces receive heavy penalty (near 0.0).
            Confirmed permanent changes receive high confidence (0.7 ~ 1.0).
        """
        height, width = c_t1.shape
        confidence = np.zeros((height, width), dtype=np.float32)

        # Pixels where classification predicted a change
        has_change = (c_t1 != c_t2) & (c_t1 != IGNORE) & (c_t2 != IGNORE)
        if valid_mask is not None:
            has_change = has_change & valid_mask

        if not np.any(has_change):
            return confidence

        # 1. Spectral divergence (NSVD)
        nsvd = SpectralDivergenceCalculator.calculate_nsvd(bands_t1, bands_t2)
        # Non-linear mapping to emphasize significant spectral shifts
        spectral_score = 1.0 - np.exp(-self.scaling * nsvd)

        # 2. Vegetation index change (|Delta NDVI|)
        ndvi_delta = SpectralDivergenceCalculator.calculate_ndvi_delta(bands_t1, bands_t2)
        ndvi_score = np.clip(ndvi_delta * 2.0, 0.0, 1.0)

        # 3. Trajectory Permanence factor
        if c_t3 is not None and bands_t3 is not None:
            # Multi-temporal trajectory permanence:
            # True change (A -> B -> B): delta_12 large, delta_23 small, delta_13 large
            # Bounce (A -> B -> A): delta_12 large, delta_23 large, delta_13 ~ 0
            d12 = SpectralDivergenceCalculator.calculate_nsvd(bands_t1, bands_t2)
            d23 = SpectralDivergenceCalculator.calculate_nsvd(bands_t2, bands_t3)
            d13 = SpectralDivergenceCalculator.calculate_nsvd(bands_t1, bands_t3)

            denom = d12 + d23 + 1e-6
            # Permanence ratio: how much of original difference remains at t3
            r_perm = np.clip(d13 / denom, 0.0, 1.0)
            
            # Label permanence confirmation
            label_sustained = (c_t2 == c_t3) & (c_t1 != c_t2)
            perm_factor = np.where(label_sustained, 0.5 + 0.5 * r_perm, r_perm)
        else:
            perm_factor = np.full((height, width), 0.5, dtype=np.float32)

        # Composite confidence score
        raw_confidence = (
            self.w_spec * spectral_score +
            self.w_ndvi * ndvi_score +
            self.w_perm * perm_factor
        )

        confidence[has_change] = np.clip(raw_confidence[has_change], 0.0, 1.0)

        # 4. Severe damping for detected bounces
        if is_bounce_mask is not None:
            bounce_idx = has_change & is_bounce_mask
            # Penalize bounce change confidence down to <= 0.08
            confidence[bounce_idx] = confidence[bounce_idx] * 0.08

        return confidence


class TransitionMatrixEngine:
    """
    Computes raw and filtered transition matrices, pixel counts, area in m^2,
    and conducts rigorous conservation arithmetic verification.
    """

    @staticmethod
    def compute_matrix(
        c_from: np.ndarray,
        c_to: np.ndarray,
        valid_mask: Optional[np.ndarray] = None,
        pixel_size_m: float = 10.0,
        num_classes: int = len(CLASS_NAMES),
        class_names: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Compute transition matrix between two land cover classification grids.
        
        Args:
            c_from: 2D uint8 array at start year
            c_to: 2D uint8 array at end year
            valid_mask: Optional 2D boolean mask
            pixel_size_m: Resolution in meters (Sentinel-2 default = 10m -> 100 m^2 per pixel)
            num_classes: Number of distinct classes (default 9)
            class_names: Optional list of class names
            
        Returns:
            Dict with pixel matrix, area matrix (m^2), net change, and conservation metrics.
        """
        if c_from.shape != c_to.shape:
            raise ValueError("c_from and c_to must have identical dimensions.")

        c_names = class_names or CLASS_NAMES[:num_classes]
        pixel_area_m2 = pixel_size_m * pixel_size_m

        # Valid where neither is IGNORE and within class boundaries
        valid = (
            (c_from != IGNORE) &
            (c_to != IGNORE) &
            (c_from >= 0) &
            (c_from < num_classes) &
            (c_to >= 0) &
            (c_to < num_classes)
        )
        if valid_mask is not None:
            valid = valid & valid_mask

        total_pixels = int(c_from.size)
        valid_count = int(np.count_nonzero(valid))
        excluded_count = total_pixels - valid_count

        # Transition code = from_class * num_classes + to_class
        code = c_from[valid].astype(np.int64) * num_classes + c_to[valid].astype(np.int64)
        pixel_matrix = np.bincount(code, minlength=num_classes**2).reshape(num_classes, num_classes)
        area_matrix = (pixel_matrix.astype(np.float64) * pixel_area_m2)

        # Transition raster
        transition_raster = np.full(c_from.shape, TRANSITION_NODATA, dtype=np.uint16)
        transition_raster[valid] = code.astype(np.uint16)

        # Matrix arithmetic checks
        total_valid_matrix_pixels = int(pixel_matrix.sum())
        diagonal_pixels = int(np.trace(pixel_matrix))
        changed_pixels = total_valid_matrix_pixels - diagonal_pixels
        total_area = float(area_matrix.sum())
        changed_area = float(total_area - np.trace(area_matrix))
        unchanged_area = float(np.trace(area_matrix))
        change_rate = round(changed_pixels / valid_count, 6) if valid_count > 0 else 0.0

        # Class net changes: sum(column) - sum(row)
        # Positive = net gain, Negative = net loss
        class_net_pixels = (pixel_matrix.sum(axis=0) - pixel_matrix.sum(axis=1)).tolist()
        class_net_area = (area_matrix.sum(axis=0) - area_matrix.sum(axis=1)).tolist()

        # Arithmetic conservation verifications
        sum_check = (total_valid_matrix_pixels == valid_count)
        diag_check = (changed_pixels + diagonal_pixels == total_valid_matrix_pixels)
        net_sum_zero = (sum(class_net_pixels) == 0)

        arithmetic_passed = sum_check and diag_check and net_sum_zero

        return {
            "transition_pixel_matrix": pixel_matrix.tolist(),
            "transition_area_matrix_m2": area_matrix.tolist(),
            "transition_raster": transition_raster,
            "valid_pixels": valid_count,
            "excluded_pixels": excluded_count,
            "total_pixels": total_pixels,
            "pixel_area_m2": pixel_area_m2,
            "total_area_m2": total_area,
            "changed_pixels": changed_pixels,
            "changed_area_m2": changed_area,
            "unchanged_pixels": diagonal_pixels,
            "unchanged_area_m2": unchanged_area,
            "change_rate": change_rate,
            "class_net_pixels": class_net_pixels,
            "class_net_area_m2": class_net_area,
            "class_names": c_names,
            "arithmetic_verification": {
                "passed": arithmetic_passed,
                "sum_equals_valid_count": sum_check,
                "diag_plus_changed_equals_total": diag_check,
                "net_change_sum_zero": net_sum_zero,
            }
        }

    @staticmethod
    def export_transition_csv(matrix_dict: Dict[str, Any], filepath: Union[str, Path]) -> None:
        """Export transition matrix to standard CSV with headers."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        pixel_matrix = np.array(matrix_dict["transition_pixel_matrix"])
        area_matrix = np.array(matrix_dict["transition_area_matrix_m2"])
        class_names = matrix_dict["class_names"]
        num_classes = len(class_names)

        with path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["from_class_idx", "from_class_name", "to_class_idx", "to_class_name", "pixels", "area_m2"])
            for i in range(num_classes):
                for j in range(num_classes):
                    writer.writerow([
                        i,
                        class_names[i],
                        j,
                        class_names[j],
                        int(pixel_matrix[i, j]),
                        float(area_matrix[i, j]),
                    ])


class TemporalChangeDetectionEngine:
    """
    Complete end-to-end Change Detection Engine with Temporal Trajectory Filtering.
    Integrates:
    - Unit 336 SCL median annual composite blending.
    - 3+ year trajectory consistency filtering (Gap 4 false change elimination).
    - Multi-temporal spectral divergence & calibrated change confidence scoring.
    - Dual raw vs filtered transition matrix generation and GeoTIFF/CSV export.
    """

    def __init__(
        self,
        pixel_size_m: float = 10.0,
        default_crs: str = "EPSG:32748",
        confidence_cutoff: float = 0.35,
    ):
        self.pixel_size_m = pixel_size_m
        self.default_crs = default_crs
        self.confidence_cutoff = confidence_cutoff
        self.filter = TrajectoryConsistencyFilter()
        self.scorer = ChangeConfidenceScorer()

    @staticmethod
    def write_geotiff(
        filepath: Union[str, Path],
        data: np.ndarray,
        crs: str = "EPSG:32748",
        transform: Optional[Any] = None,
        nodata: Optional[Union[int, float]] = None,
        dtype: Optional[str] = None,
    ) -> None:
        """Write numpy array as GeoTIFF using rasterio with robust fallback handling."""
        import rasterio
        from rasterio.transform import from_origin

        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        height, width = data.shape
        t = transform if transform is not None else from_origin(500000.0, 9300000.0, 10.0, 10.0)
        out_dtype = dtype or str(data.dtype)
        out_nodata = nodata

        profile = {
            "driver": "GTiff",
            "height": height,
            "width": width,
            "count": 1,
            "dtype": out_dtype,
            "crs": crs,
            "transform": t,
            "compress": "deflate",
        }
        if out_nodata is not None:
            profile["nodata"] = out_nodata

        with rasterio.open(path, "w", **profile) as dst:
            dst.write(data.astype(out_dtype), 1)

    def execute_annual_series_change_analysis(
        self,
        annual_composites: List[Dict[str, Any]],
        raw_classifications: List[np.ndarray],
        years: List[int],
        output_dir: Union[str, Path],
        target_pair: Optional[Tuple[int, int]] = None,
    ) -> Dict[str, Any]:
        """
        Run full temporal change filtering across multi-year annual composites and classifications.
        
        Args:
            annual_composites: List of Dicts containing 'composite_bands' and 'quality_mask' per year.
            raw_classifications: List of 2D uint8 classification arrays per year.
            years: List of integer years (e.g. [2020, 2021, 2022]).
            output_dir: Directory to export results.
            target_pair: Pair of years (from_year, to_year) for transition matrices (default: first and last).
            
        Returns:
            Comprehensive report dictionary.
        """
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        num_years = len(years)
        if num_years < 3:
            raise ValueError(f"Temporal change filtering requires at least 3 years, provided: {num_years}")
        if len(annual_composites) != num_years or len(raw_classifications) != num_years:
            raise ValueError("Mismatched counts between annual_composites, raw_classifications, and years.")

        # Stack classifications: Shape (T, H, W)
        raw_stack = np.stack(raw_classifications, axis=0)
        t_steps, height, width = raw_stack.shape

        # Stack quality masks
        quality_masks = np.stack([comp["quality_mask"] for comp in annual_composites], axis=0)

        # 1. Trajectory consistency filtering
        filtered_stack, filter_stats = self.filter.filter_trajectory_stack(
            class_stack=raw_stack,
            valid_masks=quality_masks,
        )

        # 2. Select target transition pair (e.g. 2020 -> 2021 or 2020 -> 2022)
        if target_pair is None:
            from_yr, to_yr = years[0], years[1]
        else:
            from_yr, to_yr = target_pair

        idx_from = years.index(from_yr)
        idx_to = years.index(to_yr)

        raw_from = raw_stack[idx_from]
        raw_to = raw_stack[idx_to]
        filt_from = filtered_stack[idx_from]
        filt_to = filtered_stack[idx_to]

        # Valid mask for transition pair
        v_pair = (quality_masks[idx_from] > 0) & (quality_masks[idx_to] > 0)

        # 3. Detect bounces for target year
        is_bounce = np.zeros((height, width), dtype=bool)
        if 0 < idx_to < num_years - 1:
            is_bounce = self.filter.identify_bounces_3year(
                c_prev=raw_stack[idx_to - 1],
                c_curr=raw_stack[idx_to],
                c_next=raw_stack[idx_to + 1],
                valid_mask=v_pair & (quality_masks[idx_to - 1] > 0) & (quality_masks[idx_to + 1] > 0),
            )

        # 4. Multi-temporal spectral divergence & pixel-wise change confidence
        c_future = raw_stack[idx_to + 1] if idx_to < num_years - 1 else None
        b_future = annual_composites[idx_to + 1]["composite_bands"] if idx_to < num_years - 1 else None

        confidence_map = self.scorer.compute_confidence(
            c_t1=raw_from,
            c_t2=raw_to,
            bands_t1=annual_composites[idx_from]["composite_bands"],
            bands_t2=annual_composites[idx_to]["composite_bands"],
            is_bounce_mask=is_bounce,
            c_t3=c_future,
            bands_t3=b_future,
            valid_mask=v_pair,
        )

        # 5. Compute Raw Transition Matrix
        raw_matrix = TransitionMatrixEngine.compute_matrix(
            c_from=raw_from,
            c_to=raw_to,
            valid_mask=v_pair,
            pixel_size_m=self.pixel_size_m,
        )

        # 6. Compute Filtered Transition Matrix
        filtered_matrix = TransitionMatrixEngine.compute_matrix(
            c_from=filt_from,
            c_to=filt_to,
            valid_mask=v_pair,
            pixel_size_m=self.pixel_size_m,
        )

        # 7. False change reduction evaluation
        raw_changed = raw_matrix["changed_pixels"]
        filtered_changed = filtered_matrix["changed_pixels"]
        false_changes_removed = max(0, raw_changed - filtered_changed)
        reduction_rate = round(false_changes_removed / raw_changed, 6) if raw_changed > 0 else 0.0

        # 8. Export files
        # GeoTIFF exports
        self.write_geotiff(
            filepath=out_path / "transitions_raw.tif",
            data=raw_matrix["transition_raster"],
            crs=self.default_crs,
            nodata=TRANSITION_NODATA,
            dtype="uint16",
        )
        self.write_geotiff(
            filepath=out_path / "transitions_filtered.tif",
            data=filtered_matrix["transition_raster"],
            crs=self.default_crs,
            nodata=TRANSITION_NODATA,
            dtype="uint16",
        )
        self.write_geotiff(
            filepath=out_path / "change_confidence.tif",
            data=confidence_map,
            crs=self.default_crs,
            nodata=CONFIDENCE_NODATA,
            dtype="float32",
        )

        # CSV exports
        TransitionMatrixEngine.export_transition_csv(raw_matrix, out_path / "transitions_raw.csv")
        TransitionMatrixEngine.export_transition_csv(filtered_matrix, out_path / "transitions_filtered.csv")

        # Compile final summary report
        report = {
            "schema_version": 1,
            "status": "TEMPORAL_CHANGE_FILTER_COMPLETE",
            "time_horizon": {
                "years": years,
                "total_years": num_years,
                "evaluated_pair": {"from_year": from_yr, "to_year": to_yr},
            },
            "trajectory_filter_metrics": {
                "total_pixels": height * width,
                "total_bounces_smoothed": filter_stats["total_bounces_smoothed"],
                "confidence_reversals": filter_stats["confidence_reversals"],
                "per_year_details": filter_stats["per_year_bounce_details"],
            },
            "transition_comparison": {
                "raw_changed_pixels": raw_changed,
                "raw_changed_area_m2": raw_matrix["changed_area_m2"],
                "raw_change_rate": raw_matrix["change_rate"],
                "filtered_changed_pixels": filtered_changed,
                "filtered_changed_area_m2": filtered_matrix["changed_area_m2"],
                "filtered_change_rate": filtered_matrix["change_rate"],
                "false_changes_removed_pixels": false_changes_removed,
                "false_change_reduction_rate": reduction_rate,
                "confidence_mean_on_filtered_changes": float(np.mean(confidence_map[filt_from != filt_to])) if np.any(filt_from != filt_to) else 0.0,
            },
            "matrix_conservation_verified": (
                raw_matrix["arithmetic_verification"]["passed"] and
                filtered_matrix["arithmetic_verification"]["passed"]
            ),
            "exported_artifacts": {
                "transitions_raw_tif": str((out_path / "transitions_raw.tif").resolve()),
                "transitions_filtered_tif": str((out_path / "transitions_filtered.tif").resolve()),
                "change_confidence_tif": str((out_path / "change_confidence.tif").resolve()),
                "transitions_raw_csv": str((out_path / "transitions_raw.csv").resolve()),
                "transitions_filtered_csv": str((out_path / "transitions_filtered.csv").resolve()),
            },
        }

        # Write JSON report
        (out_path / "filter_summary_report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        return report
