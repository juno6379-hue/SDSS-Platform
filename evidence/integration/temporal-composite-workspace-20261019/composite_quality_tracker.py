"""
Annual Composite Quality Tracker & Observation Count Pipeline (Section 2).
Workspace: evidence/integration/temporal-composite-workspace-20261019/composite_quality_tracker.py

Features:
1. Multi-temporal Sentinel-2 filtering based on SCL and spectral data validity.
2. Quality-based compositing within designated temporal/seasonal observation windows:
   - Pixel-wise median of valid observations
   - Priority selection (cleanest / highest NDVI valid pixel)
3. Exhaustive per-pixel metadata tracking:
   - Valid observation count (N_valid per pixel)
   - Temporal observation dates (first valid DOY, last valid DOY, selected observation DOY)
   - Categorized missingness reason mask (Cloud, Shadow, Cirrus, Defective, Sensor NoData)
4. Strict NoData preservation: Pixels with 0 valid observations are explicitly kept as NoData
   (no procedural gap-filling or artificial interpolation).
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import IntEnum
import math
from typing import Dict, List, Optional, Tuple, Any
import numpy as np

# Sentinel-2 SCL Classes
SCL_CLASSES = {
    0: "NO_DATA",
    1: "SATURATED_OR_DEFECTIVE",
    2: "DARK_AREA_PIXELS",
    3: "CLOUD_SHADOWS",
    4: "VEGETATION",
    5: "NOT_VEGETATED",
    6: "WATER",
    7: "UNCLASSIFIED",
    8: "CLOUD_MEDIUM_PROBABILITY",
    9: "CLOUD_HIGH_PROBABILITY",
    10: "THIN_CIRRUS",
    11: "SNOW",
}

INVALID_SCL_CODES = frozenset([0, 1, 3, 8, 9, 10, 11])
VALID_SCL_CODES = frozenset([2, 4, 5, 6, 7])


class MissingReason(IntEnum):
    """Enumeration of pixel status and primary missingness reasons."""
    NOT_MISSING = 0            # Has at least one valid observation
    CLOUD = 1                  # SCL 8 (medium prob) or 9 (high prob)
    CLOUD_SHADOW = 2           # SCL 3 (cloud shadow)
    THIN_CIRRUS = 3            # SCL 10 (thin cirrus)
    DEFECTIVE_OR_SNOW = 4      # SCL 1 (saturated/defective) or 11 (snow)
    SENSOR_NODATA = 5          # SCL 0 (nodata) or spectral NaN/zero out-of-swath


def _to_utc_dt(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@dataclass
class TemporalWindow:
    """Designates a temporal/seasonal filtering window."""
    name: str = "annual"
    start_date: Optional[str] = None  # ISO-8601 date 'YYYY-MM-DD'
    end_date: Optional[str] = None    # ISO-8601 date 'YYYY-MM-DD'
    min_doy: Optional[int] = None     # Day of year 1..366
    max_doy: Optional[int] = None     # Day of year 1..366

    def contains(self, dt: datetime) -> bool:
        norm_dt = _to_utc_dt(dt)
        if self.start_date:
            s_dt = _to_utc_dt(datetime.fromisoformat(self.start_date.replace("Z", "+00:00")))
            if norm_dt < s_dt:
                return False
        if self.end_date:
            # If end_date is date-only (length 10), extend to end of day
            end_str = self.end_date
            if len(end_str) == 10:
                end_str = f"{end_str}T23:59:59"
            e_dt = _to_utc_dt(datetime.fromisoformat(end_str.replace("Z", "+00:00")))
            if norm_dt > e_dt:
                return False
        doy = norm_dt.timetuple().tm_yday
        if self.min_doy is not None and doy < self.min_doy:
            return False
        if self.max_doy is not None and doy > self.max_doy:
            return False
        return True


class CompositeQualityTracker:
    """
    Tracks per-pixel observation quality, computes composite bands,
    observation counts, and pixel-level missingness diagnostics.
    """

    def __init__(self, nodata_value: float = 0.0):
        self.nodata_value = nodata_value

    @staticmethod
    def _parse_datetime(dt_str: str) -> datetime:
        """Parse ISO-8601 string to UTC datetime."""
        clean = dt_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean)
        return _to_utc_dt(dt)

    @staticmethod
    def _calculate_ndvi(nir: np.ndarray, red: np.ndarray) -> np.ndarray:
        """Normalized Difference Vegetation Index."""
        denom = nir.astype(np.float32) + red.astype(np.float32)
        numer = nir.astype(np.float32) - red.astype(np.float32)
        ndvi = np.zeros_like(denom)
        valid = denom > 1e-6
        ndvi[valid] = numer[valid] / denom[valid]
        return np.clip(ndvi, -1.0, 1.0)

    @staticmethod
    def classify_scl_missing_reason(scl_val: int) -> int:
        """Map SCL invalid code to MissingReason enum code."""
        if scl_val in (8, 9):
            return int(MissingReason.CLOUD)
        elif scl_val == 3:
            return int(MissingReason.CLOUD_SHADOW)
        elif scl_val == 10:
            return int(MissingReason.THIN_CIRRUS)
        elif scl_val in (1, 11):
            return int(MissingReason.DEFECTIVE_OR_SNOW)
        elif scl_val == 0:
            return int(MissingReason.SENSOR_NODATA)
        return int(MissingReason.SENSOR_NODATA)

    def process_annual_observations(
        self,
        slices: List[Dict[str, Any]],
        window: Optional[TemporalWindow] = None,
        method: str = "median",
        target_bands: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Process a stack of temporal Sentinel-2 slices and produce a quality-tracked composite.

        Args:
            slices: List of dicts, each with:
                - 'scene_id': str
                - 'datetime': str (ISO-8601)
                - 'bands': Dict[str, np.ndarray (H, W)]
                - 'scl': np.ndarray (H, W) uint8
            window: Optional TemporalWindow filter
            method: 'median' or 'priority' (highest valid NDVI)
            target_bands: Optional list of bands to composite

        Returns:
            Dict containing:
                - 'composite_bands': Dict[str, np.ndarray (H, W)] (Strict NoData preserved)
                - 'quality_mask': np.ndarray (H, W) uint8 (1 = valid observation, 0 = NoData)
                - 'valid_count_mask': np.ndarray (H, W) uint16 (N_valid per pixel)
                - 'missing_reason_mask': np.ndarray (H, W) uint8 (MissingReason code)
                - 'first_valid_doy': np.ndarray (H, W) int16 (-1 if no valid observation)
                - 'last_valid_doy': np.ndarray (H, W) int16 (-1 if no valid observation)
                - 'selected_observation_doy': np.ndarray (H, W) int16 (-1 if none selected)
                - 'metadata': Dict with exhaustive summary statistics
        """
        if not slices:
            raise ValueError("At least one observation slice is required.")

        # Step 1: Temporal Window Filtering
        filtered_slices = []
        for s in slices:
            dt = self._parse_datetime(s["datetime"])
            if window is None or window.contains(dt):
                filtered_slices.append((dt, s))

        if not filtered_slices:
            raise ValueError("No slices matched the specified temporal window.")

        # Extract raster geometry
        first_slice = filtered_slices[0][1]
        available_bands = list(first_slice["bands"].keys())
        band_names = target_bands or available_bands
        height, width = first_slice["scl"].shape

        T = len(filtered_slices)
        scl_stack = np.zeros((T, height, width), dtype=np.uint8)
        spectral_valid_stack = np.ones((T, height, width), dtype=bool)
        doy_list = []

        for t, (dt, s) in enumerate(filtered_slices):
            doy = dt.timetuple().tm_yday
            doy_list.append(doy)
            scl_stack[t] = s["scl"]
            # Check spectral bounds and NaN
            for bname in band_names:
                arr = s["bands"][bname]
                spectral_valid_stack[t] &= (arr != self.nodata_value) & (~np.isnan(arr)) & (~np.isinf(arr))

        # Step 2: Compute per-slice valid mask
        # Valid = (SCL in VALID_SCL_CODES) & spectral_valid
        is_scl_valid = np.isin(scl_stack, list(VALID_SCL_CODES))
        valid_stack = is_scl_valid & spectral_valid_stack  # Shape: (T, H, W)

        # Step 3: Compute Valid Observation Counts per pixel
        valid_count_mask = np.sum(valid_stack, axis=0).astype(np.uint16)  # Shape: (H, W)
        has_valid = valid_count_mask > 0

        # Step 4: Track Observation Dates (First, Last, and Selected DOY)
        first_valid_doy = np.full((height, width), -1, dtype=np.int16)
        last_valid_doy = np.full((height, width), -1, dtype=np.int16)
        selected_doy = np.full((height, width), -1, dtype=np.int16)

        for t in range(T):
            v_t = valid_stack[t]
            cur_doy = doy_list[t]
            # Update first valid doy where not set yet
            update_first = v_t & (first_valid_doy == -1)
            first_valid_doy[update_first] = cur_doy
            # Update last valid doy
            last_valid_doy[v_t] = cur_doy

        # Step 5: Perform Quality-based Compositing
        composite_bands = {
            bname: np.full((height, width), self.nodata_value, dtype=np.float32)
            for bname in band_names
        }

        if method == "median":
            # Pixel-wise median across valid slices
            for bname in band_names:
                b_stack = np.stack([s["bands"][bname].astype(np.float32) for _, s in filtered_slices], axis=0)
                b_stack[~valid_stack] = np.nan
                import warnings
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", category=RuntimeWarning)
                    med_vals = np.nanmedian(b_stack, axis=0)
                # Assign ONLY to pixels with valid observations
                composite_bands[bname][has_valid] = med_vals[has_valid]

            # For selected_doy under median: pick observation closest to median date or median value
            selected_doy[has_valid] = ((first_valid_doy[has_valid].astype(np.int32) + 
                                        last_valid_doy[has_valid].astype(np.int32)) // 2).astype(np.int16)

        elif method == "priority":
            # Priority: observation with highest valid NDVI (or first valid if NDVI not available)
            if "nir" in band_names and "red" in band_names:
                ndvi_stack = np.full((T, height, width), -999.0, dtype=np.float32)
                for t, (_, s) in enumerate(filtered_slices):
                    ndvi_t = self._calculate_ndvi(s["bands"]["nir"], s["bands"]["red"])
                    ndvi_t[~valid_stack[t]] = -999.0
                    ndvi_stack[t] = ndvi_t
                best_t = np.argmax(ndvi_stack, axis=0)  # Shape (H, W)
            else:
                # Fallback priority: first valid observation index
                best_t = np.argmax(valid_stack, axis=0)

            for bname in band_names:
                b_stack = np.stack([s["bands"][bname].astype(np.float32) for _, s in filtered_slices], axis=0)
                selected_vals = np.take_along_axis(b_stack, best_t[np.newaxis, :, :], axis=0).squeeze(axis=0)
                composite_bands[bname][has_valid] = selected_vals[has_valid]

            # Record selected DOY
            doy_arr = np.array(doy_list, dtype=np.int16)
            selected_doy[has_valid] = doy_arr[best_t[has_valid]]
        else:
            raise ValueError(f"Unsupported compositing method: {method}")

        # Step 6: Strict NoData Preservation & Missing Reason Diagnostics
        # Pixels with valid_count_mask == 0 remain strictly nodata_value (No interpolation!)
        quality_mask = has_valid.astype(np.uint8)  # 1 = valid, 0 = NoData

        missing_reason_mask = np.zeros((height, width), dtype=np.uint8)
        missing_pixels_mask = ~has_valid

        # For unobserved pixels, determine primary/majority cause across the invalid observations
        if np.any(missing_pixels_mask):
            # Count causes across time for each missing pixel
            cause_counts = {
                MissingReason.CLOUD: np.zeros((height, width), dtype=np.uint16),
                MissingReason.CLOUD_SHADOW: np.zeros((height, width), dtype=np.uint16),
                MissingReason.THIN_CIRRUS: np.zeros((height, width), dtype=np.uint16),
                MissingReason.DEFECTIVE_OR_SNOW: np.zeros((height, width), dtype=np.uint16),
                MissingReason.SENSOR_NODATA: np.zeros((height, width), dtype=np.uint16),
            }

            for t in range(T):
                scl_t = scl_stack[t]
                spec_v_t = spectral_valid_stack[t]
                
                cause_counts[MissingReason.CLOUD] += np.isin(scl_t, [8, 9]).astype(np.uint16)
                cause_counts[MissingReason.CLOUD_SHADOW] += (scl_t == 3).astype(np.uint16)
                cause_counts[MissingReason.THIN_CIRRUS] += (scl_t == 10).astype(np.uint16)
                cause_counts[MissingReason.DEFECTIVE_OR_SNOW] += np.isin(scl_t, [1, 11]).astype(np.uint16)
                cause_counts[MissingReason.SENSOR_NODATA] += ((scl_t == 0) | (~spec_v_t)).astype(np.uint16)

            # Determine dominant cause per missing pixel
            dominant_cause = np.full((height, width), int(MissingReason.SENSOR_NODATA), dtype=np.uint8)
            max_c = np.zeros((height, width), dtype=np.uint16)
            for reason in [
                MissingReason.CLOUD,
                MissingReason.CLOUD_SHADOW,
                MissingReason.THIN_CIRRUS,
                MissingReason.DEFECTIVE_OR_SNOW,
                MissingReason.SENSOR_NODATA,
            ]:
                better = cause_counts[reason] > max_c
                dominant_cause[better] = int(reason)
                max_c[better] = cause_counts[reason][better]

            missing_reason_mask[missing_pixels_mask] = dominant_cause[missing_pixels_mask]

        # Step 7: Summary Metadata Computation
        total_pixels = height * width
        valid_pixels = int(np.count_nonzero(quality_mask == 1))
        missing_pixels = total_pixels - valid_pixels

        # Missing reason breakdown
        missing_breakdown = {}
        for r in MissingReason:
            if r == MissingReason.NOT_MISSING:
                continue
            cnt = int(np.count_nonzero(missing_reason_mask == int(r)))
            pct = round(cnt / total_pixels * 100.0, 4) if total_pixels > 0 else 0.0
            missing_breakdown[r.name] = {"code": int(r), "count": cnt, "percentage": pct}

        # Observation frequency histogram (0, 1, 2, ..., T)
        obs_hist = {}
        for c in range(T + 1):
            c_cnt = int(np.count_nonzero(valid_count_mask == c))
            if c_cnt > 0 or c <= 3:
                obs_hist[str(c)] = c_cnt

        metadata = {
            "schema_version": 1,
            "scope": "ANNUAL_COMPOSITE_QUALITY_TRACKER",
            "blending_method": method,
            "temporal_window": {
                "name": window.name if window else "annual",
                "start_date": window.start_date if window else None,
                "end_date": window.end_date if window else None,
                "total_slices_available": len(slices),
                "total_slices_evaluated": T,
                "doy_span": [int(min(doy_list)), int(max(doy_list))],
            },
            "pixel_counts": {
                "total_pixels": total_pixels,
                "valid_composite_pixels": valid_pixels,
                "missing_nodata_pixels": missing_pixels,
                "valid_coverage_ratio": round(valid_pixels / total_pixels, 6) if total_pixels > 0 else 0.0,
            },
            "observation_count_distribution": {
                "min_valid_observations": int(np.min(valid_count_mask)),
                "max_valid_observations": int(np.max(valid_count_mask)),
                "mean_valid_observations": round(float(np.mean(valid_count_mask)), 3),
                "histogram": obs_hist,
            },
            "missingness_diagnostics": {
                "procedural_interpolation_applied": False,
                "nodata_strictly_preserved": True,
                "missing_reasons_breakdown": missing_breakdown,
            },
        }

        return {
            "composite_bands": composite_bands,
            "quality_mask": quality_mask,
            "valid_count_mask": valid_count_mask,
            "missing_reason_mask": missing_reason_mask,
            "first_valid_doy": first_valid_doy,
            "last_valid_doy": last_valid_doy,
            "selected_observation_doy": selected_doy,
            "metadata": metadata,
        }
