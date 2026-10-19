"""Formal Contract and Specification for 6-Band Full Physical BOA Reflectance Application.

Defines the mathematical, architectural, and operational rules governing:
1. Exact radiometric scaling for B02, B03, B04, B08, B11, B12.
2. 10m spatial resolution precision across all study provinces.
3. Saturated reflectance and missing band flagging to prevent LCLUC classification distortion.
4. Nodata preservation and non-mutating transformation.
"""

import math
from typing import Dict, List, Tuple, Any, Optional
import numpy as np


# Immutable Band Definitions
S2_6BANDS = ('B02', 'B03', 'B04', 'B08', 'B11', 'B12')
S2_LOGICAL_BANDS = ('blue', 'green', 'red', 'nir', 'swir16', 'swir22')
S2_BAND_CENTRAL_WAVELENGTH_NM = {
    'B02': 492.4,   # Blue (10m native)
    'B03': 559.8,   # Green (10m native)
    'B04': 664.6,   # Red (10m native)
    'B08': 832.8,   # NIR (10m native)
    'B11': 1610.4,  # SWIR-1 (20m native -> resampled to 10m)
    'B12': 2190.0   # SWIR-2 (20m native -> resampled to 10m)
}

# 10m Precision Requirement
SPATIAL_RESOLUTION_METERS = 10.0

# Radiometric Constants
ESA_QUANTIFICATION_VALUE = 10000.0
ESA_SCALE_FACTOR = 0.0001  # 1.0 / ESA_QUANTIFICATION_VALUE

# Baseline Radiometric Offsets
PB_PRE04_BOA_ADD_OFFSET = 0.0
PB_PRE04_REFLECTANCE_OFFSET = 0.0

PB_POST04_BOA_ADD_OFFSET = -1000.0
PB_POST04_REFLECTANCE_OFFSET = -0.1  # -1000.0 / 10000.0

# LCLUC Distortion Prevention Thresholds
MAX_PHYSICAL_LCLUC_REFLECTANCE = 1.00  # 100% surface reflectance upper bound for standard land covers
MIN_PHYSICAL_LCLUC_REFLECTANCE = 0.00  # 0% surface reflectance lower bound
EXTREME_CORRUPT_REFLECTANCE = 2.05    # Extreme unphysical sensor anomaly


class SpectralBatchContract:
    """Formal contract for Sentinel-2 Level-2A BOA reflectance transformation and LCLUC distortion prevention."""

    @staticmethod
    def get_calibration_parameters(
        year: int,
        baseline: Optional[str] = None,
        override_offset: Optional[float] = None
    ) -> Tuple[List[float], List[float]]:
        """Derive authoritative scale and offset based on ESA processing baseline.
        
        Rules:
        - Sentinel-2 PB 04.00 was deployed on 25 January 2022.
        - Scenes from 2020 and 2021 use PB < 04.00 (offset = 0.0).
        - Scenes from 2022 to 2025 use PB >= 04.00 (offset = -0.1).
        """
        scale = [ESA_SCALE_FACTOR] * 6
        
        if override_offset is not None:
            offset = [override_offset] * 6
        elif baseline is not None:
            try:
                major_version = int(baseline.split('.')[0])
                offset = [PB_POST04_REFLECTANCE_OFFSET if major_version >= 4 else PB_PRE04_REFLECTANCE_OFFSET] * 6
            except Exception:
                offset = [PB_POST04_REFLECTANCE_OFFSET if year >= 2022 else PB_PRE04_REFLECTANCE_OFFSET] * 6
        else:
            offset = [PB_POST04_REFLECTANCE_OFFSET if year >= 2022 else PB_PRE04_REFLECTANCE_OFFSET] * 6
            
        return scale, offset

    @staticmethod
    def apply_physical_reflectance(
        raw_dn_array: np.ndarray,
        scale: List[float],
        offset: List[float],
        nodata_val: float = 0.0,
        clip_negative: bool = False
    ) -> np.ndarray:
        """Apply full physical BOA reflectance transformation without side-effects."""
        if raw_dn_array.ndim != 3:
            raise ValueError(f"Input array must have 3 dimensions (channels, height, width), got shape {raw_dn_array.shape}")
        
        channels = raw_dn_array.shape[0]
        if channels != 6:
            raise ValueError(f"Expected 6 channels for Sentinel-2 full BOA spectrum, got {channels}")
        
        scales = np.asarray(scale, dtype='float32')[:, None, None]
        offsets = np.asarray(offset, dtype='float32')[:, None, None]
        
        # Identify nodata mask
        nodata_mask = (raw_dn_array == nodata_val)
        
        # Apply radiometric transformation: Reflectance = DN * scale + offset
        reflectance = raw_dn_array.astype('float32') * scales + offsets
        
        # Preserve nodata
        reflectance = np.where(nodata_mask, nodata_val, reflectance)
        
        if clip_negative:
            valid_mask = ~nodata_mask
            reflectance = np.where(valid_mask & (reflectance < 0.0), 0.0, reflectance)
            
        return reflectance

    @staticmethod
    def generate_spectral_quality_mask(
        raw_dn_array: np.ndarray,
        scale: List[float],
        offset: List[float],
        nodata_val: float = 0.0
    ) -> Dict[str, Any]:
        """Generate pixel-level distortion prevention mask for LCLUC land cover classification.
        
        Flags:
        - NODATA: DN == nodata_val across all bands or in any band.
        - SATURATED: BOA reflectance > 1.0 (cloud summits, bright tin roofs, specular sun glint).
        - NEGATIVE_ANOMALY: BOA reflectance < 0.0 (over-corrected shadow/water under PB 04.00 offset).
        - CORRUPT_ANOMALY: NaN, Inf, or values > 2.05.
        - CLEAN_LCLUC_PIXEL: Physically clean pixel valid for Land Cover classification.
        """
        if raw_dn_array.ndim != 3 or raw_dn_array.shape[0] != 6:
            raise ValueError(f"Expected 6-band array, got {raw_dn_array.shape}")
            
        c, h, w = raw_dn_array.shape
        total_pixels = h * w
        
        scales = np.asarray(scale, dtype='float32')[:, None, None]
        offsets = np.asarray(offset, dtype='float32')[:, None, None]
        
        nodata_per_band = (raw_dn_array == nodata_val)
        nodata_pixel_mask = nodata_per_band.any(axis=0)  # Pixel invalid if any band is nodata
        
        refl = raw_dn_array.astype('float32') * scales + offsets
        refl = np.where(nodata_per_band, nodata_val, refl)
        
        valid_pixel_mask = ~nodata_pixel_mask
        
        # Saturated: reflectance > 1.0 on any band
        saturated_per_band = (refl > MAX_PHYSICAL_LCLUC_REFLECTANCE) & (~nodata_per_band)
        saturated_pixel_mask = saturated_per_band.any(axis=0)
        
        # Negative anomaly: reflectance < 0.0 on any band
        negative_per_band = (refl < MIN_PHYSICAL_LCLUC_REFLECTANCE) & (~nodata_per_band)
        negative_pixel_mask = negative_per_band.any(axis=0)
        
        # Corrupted / Extreme unphysical
        corrupt_per_band = (~np.isfinite(refl)) | ((refl > EXTREME_CORRUPT_REFLECTANCE) & (~nodata_per_band))
        corrupt_pixel_mask = corrupt_per_band.any(axis=0)
        
        # Clean LCLUC pixel: valid, not saturated, not negative anomaly, not corrupt
        clean_pixel_mask = valid_pixel_mask & (~saturated_pixel_mask) & (~negative_pixel_mask) & (~corrupt_pixel_mask)
        
        clean_count = int(clean_pixel_mask.sum())
        sat_count = int(saturated_pixel_mask.sum())
        neg_count = int(negative_pixel_mask.sum())
        corrupt_count = int(corrupt_pixel_mask.sum())
        nodata_count = int(nodata_pixel_mask.sum())
        
        return {
            'clean_pixel_mask': clean_pixel_mask,
            'saturated_pixel_mask': saturated_pixel_mask,
            'negative_pixel_mask': negative_pixel_mask,
            'corrupt_pixel_mask': corrupt_pixel_mask,
            'nodata_pixel_mask': nodata_pixel_mask,
            'total_pixels': total_pixels,
            'clean_pixel_count': clean_count,
            'clean_pixel_ratio': float(clean_count / total_pixels),
            'saturated_pixel_count': sat_count,
            'saturated_pixel_ratio': float(sat_count / total_pixels),
            'negative_pixel_count': neg_count,
            'negative_pixel_ratio': float(neg_count / total_pixels),
            'corrupt_pixel_count': corrupt_count,
            'nodata_pixel_count': nodata_count,
            'is_contamination_free': (sat_count == 0 and corrupt_count == 0)
        }

    @staticmethod
    def apply_physical_reflectance_for_lcluc(
        raw_dn_array: np.ndarray,
        scale: List[float],
        offset: List[float],
        nodata_val: float = 0.0,
        mask_saturated: bool = True,
        clip_negative: bool = True
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Produce LCLUC-ready reflectance array and associated clean binary mask."""
        q_mask = SpectralBatchContract.generate_spectral_quality_mask(
            raw_dn_array, scale, offset, nodata_val
        )
        
        # Basic reflectance
        refl = SpectralBatchContract.apply_physical_reflectance(
            raw_dn_array, scale, offset, nodata_val, clip_negative=clip_negative
        )
        
        if mask_saturated:
            # Mask out saturated pixels with nodata to prevent LCLUC model distortion
            sat_mask = q_mask['saturated_pixel_mask']
            refl = np.where(sat_mask[None, :, :], nodata_val, refl)
            
        clean_mask = q_mask['clean_pixel_mask']
        return refl, clean_mask

    @staticmethod
    def validate_spectral_contract(
        band_count: int,
        band_names: List[str],
        dtypes: List[str],
        scale: List[float],
        offset: List[float],
        spatial_resolution: Optional[Tuple[float, float]] = None
    ) -> Tuple[bool, List[str]]:
        """Validate whether a patch satisfies the 6-band full BOA spectral contract at 10m resolution."""
        issues = []
        if band_count != 6:
            issues.append(f"INCOMPLETE_SPECTRUM: expected 6 bands, found {band_count}")
        
        if list(band_names) != list(S2_6BANDS):
            issues.append(f"BAND_ALIGNMENT_MISMATCH: expected {S2_6BANDS}, found {band_names}")
            
        if not all(dt in ('float32', 'float64', 'uint16') for dt in dtypes):
            issues.append(f"UNSUPPORTED_DTYPE: {dtypes}")
            
        if len(scale) != 6 or not all(s > 0 for s in scale):
            issues.append("INVALID_SCALE_PARAMETERS")
            
        if len(offset) != 6:
            issues.append("INVALID_OFFSET_PARAMETERS")
            
        if spatial_resolution is not None:
            rx, ry = spatial_resolution
            if not (math.isclose(abs(rx), SPATIAL_RESOLUTION_METERS, abs_tol=0.1) and
                    math.isclose(abs(ry), SPATIAL_RESOLUTION_METERS, abs_tol=0.1)):
                issues.append(f"SPATIAL_RESOLUTION_MISMATCH: expected 10m, found ({rx}, {ry})")
            
        return (len(issues) == 0), issues
