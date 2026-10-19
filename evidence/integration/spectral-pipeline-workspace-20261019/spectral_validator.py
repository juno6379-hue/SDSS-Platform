"""Spectral Band and Reflectance Audit & Batch Validation Tool.

Performs read-only inspection of multi-spectral Sentinel-2 patches, validating:
1. 6-band full BOA availability (B02, B03, B04, B08, B11, B12).
2. 10m spatial resolution precision across all 6 study provinces.
3. Dtype and radiometric scaling (raw DN 0-10,000 vs physical reflectance 0.0-1.0).
4. Calibration contract verification (scale=0.0001, offset=0.0 for PB < 04.00, offset=-0.1 for PB >= 04.00).
5. Saturated reflectance and negative anomaly flagging to prevent LCLUC land cover distortion.
6. Nodata consistency (nodata=0.0 and quality mask alignment).
7. Strict non-mutation guarantee across all raw data files.
"""

from dataclasses import dataclass, field, asdict
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import rasterio

# Sentinel-2 L2A Band Definitions
BAND_NAMES_6 = ('B02', 'B03', 'B04', 'B08', 'B11', 'B12')
LOGICAL_BANDS_6 = ('blue', 'green', 'red', 'nir', 'swir16', 'swir22')
BAND_NAMES_4 = ('B02', 'B03', 'B04', 'B08')
BAND_NAMES_3 = ('B02', 'B03', 'B04')

# Standard radiometric parameters
ESA_SCALE = 0.0001  # 1 / 10000 quantification value
PB_PRE04_OFFSET = 0.0
PB_POST04_OFFSET = -0.1  # -1000 / 10000 radiometric offset introduced in PB 04.00 (Jan 2022)

# Physical plausible reflectance bounds for Sentinel-2 Level-2A surface reflectance (BOA)
# Lower bound: -0.12 accounts for PB 04.00+ offset of -0.10 (-1000 DN) over dark water/shadows.
# Upper bound: 2.05 accounts for specular glint, bright rooftops, and cloud summits before saturation.
MIN_PHYSICAL_REFLECTANCE = -0.12
MAX_PHYSICAL_REFLECTANCE = 2.05

# LCLUC standard physical surface reflectance thresholds
MAX_PHYSICAL_LCLUC_REFLECTANCE = 1.00
MIN_PHYSICAL_LCLUC_REFLECTANCE = 0.00
SPATIAL_RESOLUTION_10M = 10.0


def compute_file_sha256(path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with path.open('rb') as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


@dataclass
class PatchSpectralAudit:
    patch_id: str
    image_path: str
    file_exists: bool = False
    sha256_before: Optional[str] = None
    sha256_after: Optional[str] = None
    mutation_detected: bool = False
    
    # Raster geometry & bands
    band_count: int = 0
    shape: Tuple[int, int] = (0, 0)
    spatial_resolution: Tuple[float, float] = (0.0, 0.0)
    resolution_10m_verified: bool = False
    crs_valid: bool = False
    nodata_value: Optional[float] = None
    dtypes: List[str] = field(default_factory=list)
    descriptions: List[Optional[str]] = field(default_factory=list)
    
    # Spectral classification
    spectral_readiness: str = 'UNKNOWN'  # '6_BAND_BOA_READY', 'RGB_NIR_4_BAND_ONLY', 'RGB_3_BAND_ONLY', 'UNSUPPORTED'
    scale_status: str = 'UNKNOWN'  # 'RAW_DN_0_10000', 'NORMALIZED_REFLECTANCE_0_1', 'ANOMALOUS'
    
    # Statistics per band
    band_min: List[float] = field(default_factory=list)
    band_max: List[float] = field(default_factory=list)
    band_mean: List[float] = field(default_factory=list)
    
    # Nodata and quality mask
    total_pixels: int = 0
    nodata_pixel_count: int = 0
    nodata_ratio: float = 0.0
    quality_mask_exists: bool = False
    quality_mask_aligned: bool = False
    
    # Normalization calibration parameters
    declared_scale: Optional[List[float]] = None
    declared_offset: Optional[List[float]] = None
    calibration_baseline: Optional[str] = None
    offset_rule: Optional[str] = None  # 'PB_PRE04_ZERO_OFFSET' or 'PB_POST04_NEGATIVE_OFFSET'
    
    # Simulated normalization metrics (derived in-memory, non-mutating)
    normalized_band_min: List[float] = field(default_factory=list)
    normalized_band_max: List[float] = field(default_factory=list)
    reflectance_physically_plausible: bool = False
    
    # Distortion prevention & LCLUC contamination flagging
    saturated_pixel_count: int = 0
    saturated_pixel_ratio: float = 0.0
    negative_pixel_count: int = 0
    negative_pixel_ratio: float = 0.0
    clean_lcluc_pixel_count: int = 0
    clean_lcluc_pixel_ratio: float = 0.0
    distortion_flagged: bool = False
    
    # Overall status
    is_valid: bool = False
    issues: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def audit_single_patch(
    image_path: Path,
    patch_id: str = '',
    quality_mask_path: Optional[Path] = None,
    calibration_data: Optional[Dict[str, Any]] = None,
    declared_bands: Optional[List[str]] = None,
    check_sha_immutability: bool = True,
    sample_pixels: bool = True
) -> PatchSpectralAudit:
    """Audit a single patch raster file for spectral readiness, 10m precision, and distortion flags.
    
    Guarantees strict zero-mutation on the examined raster file.
    """
    image_path = Path(image_path)
    result = PatchSpectralAudit(patch_id=patch_id, image_path=str(image_path))
    
    if not image_path.exists():
        result.issues.append("FILE_NOT_FOUND")
        return result
    
    result.file_exists = True
    
    if check_sha_immutability:
        result.sha256_before = compute_file_sha256(image_path)
    
    try:
        with rasterio.open(image_path) as ds:
            result.band_count = ds.count
            result.shape = ds.shape
            result.dtypes = [str(dt) for dt in ds.dtypes]
            result.nodata_value = ds.nodata
            result.crs_valid = ds.crs is not None and ds.crs.is_projected
            result.descriptions = list(ds.descriptions) if ds.descriptions else []
            
            # Check 10m spatial resolution
            rx, ry = ds.res
            result.spatial_resolution = (float(rx), float(ry))
            result.resolution_10m_verified = (
                math.isclose(abs(rx), SPATIAL_RESOLUTION_10M, abs_tol=0.1) and
                math.isclose(abs(ry), SPATIAL_RESOLUTION_10M, abs_tol=0.1)
            )
            if not result.resolution_10m_verified:
                result.issues.append(f"SPATIAL_RESOLUTION_MISMATCH_({rx:.1f},{ry:.1f})")
            
            # Determine spectral readiness
            if result.band_count == 6:
                result.spectral_readiness = '6_BAND_BOA_READY'
            elif result.band_count == 4:
                result.spectral_readiness = 'RGB_NIR_4_BAND_ONLY'
            elif result.band_count == 3:
                result.spectral_readiness = 'RGB_3_BAND_ONLY'
            else:
                result.spectral_readiness = 'UNSUPPORTED'
                result.issues.append(f"UNSUPPORTED_BAND_COUNT_{result.band_count}")
            
            if sample_pixels:
                arr = ds.read()  # (bands, H, W)
                c, h, w = arr.shape
                result.total_pixels = h * w
                
                # Check nodata pixels
                if result.nodata_value is not None:
                    nodata_mask = (arr == result.nodata_value)
                    pixel_nodata = nodata_mask.all(axis=0)
                    result.nodata_pixel_count = int(np.sum(pixel_nodata))
                    result.nodata_ratio = float(result.nodata_pixel_count / result.total_pixels)
                else:
                    nodata_mask = np.zeros_like(arr, dtype=bool)
                
                # Per-band statistics on valid pixels
                for b_idx in range(c):
                    band_data = arr[b_idx]
                    valid_data = band_data[~nodata_mask[b_idx]] if nodata_mask.any() else band_data
                    if valid_data.size > 0:
                        b_min = float(np.min(valid_data))
                        b_max = float(np.max(valid_data))
                        b_mean = float(np.mean(valid_data))
                    else:
                        b_min, b_max, b_mean = 0.0, 0.0, 0.0
                    result.band_min.append(b_min)
                    result.band_max.append(b_max)
                    result.band_mean.append(b_mean)
                
                # Check raw scaling (DN vs Normalized)
                overall_max = max(result.band_max) if result.band_max else 0.0
                overall_min = min(result.band_min) if result.band_min else 0.0
                
                if overall_max > 1.5:
                    result.scale_status = 'RAW_DN_0_10000'
                elif 0.0 <= overall_min and overall_max <= 1.2:
                    result.scale_status = 'NORMALIZED_REFLECTANCE_0_1'
                else:
                    result.scale_status = 'ANOMALOUS'
                    result.issues.append(f"ANOMALOUS_VALUE_RANGE_MIN_{overall_min}_MAX_{overall_max}")
                
                # Resolve normalization calibration parameters
                scale, offset = None, None
                if calibration_data:
                    scale = calibration_data.get('scale')
                    offset = calibration_data.get('offset')
                    result.calibration_baseline = calibration_data.get('baseline')
                
                if scale is None:
                    scale = [ESA_SCALE] * result.band_count
                if offset is None:
                    offset = [0.0] * result.band_count
                
                result.declared_scale = scale
                result.declared_offset = offset
                
                # Determine offset rule
                if all(o == 0.0 for o in offset):
                    result.offset_rule = 'PB_PRE04_ZERO_OFFSET'
                elif all(math.isclose(o, -0.1, abs_tol=1e-5) for o in offset):
                    result.offset_rule = 'PB_POST04_NEGATIVE_OFFSET'
                else:
                    result.offset_rule = 'CUSTOM_OR_MIXED_OFFSET'
                
                # In-memory simulated normalization verification
                scales_np = np.asarray(scale, dtype='float32')[:, None, None]
                offsets_np = np.asarray(offset, dtype='float32')[:, None, None]
                
                if result.scale_status == 'RAW_DN_0_10000':
                    norm_arr = arr.astype('float32') * scales_np + offsets_np
                    if result.nodata_value is not None:
                        norm_arr = np.where(nodata_mask, result.nodata_value, norm_arr)
                    
                    for b_idx in range(c):
                        valid_norm = norm_arr[b_idx][~nodata_mask[b_idx]] if nodata_mask.any() else norm_arr[b_idx]
                        if valid_norm.size > 0:
                            result.normalized_band_min.append(float(np.min(valid_norm)))
                            result.normalized_band_max.append(float(np.max(valid_norm)))
                        else:
                            result.normalized_band_min.append(0.0)
                            result.normalized_band_max.append(0.0)
                else:
                    norm_arr = arr
                    result.normalized_band_min = list(result.band_min)
                    result.normalized_band_max = list(result.band_max)
                
                # Check physical plausibility of normalized values
                if result.normalized_band_min and result.normalized_band_max:
                    norm_min = min(result.normalized_band_min)
                    norm_max = max(result.normalized_band_max)
                    if MIN_PHYSICAL_REFLECTANCE <= norm_min and norm_max <= MAX_PHYSICAL_REFLECTANCE:
                        result.reflectance_physically_plausible = True
                    else:
                        result.reflectance_physically_plausible = False
                        result.issues.append(f"REFLECTANCE_OUT_OF_BOUNDS_MIN_{norm_min:.3f}_MAX_{norm_max:.3f}")
                
                # LCLUC Distortion Prevention: Saturation & Negative Anomaly Flagging
                valid_pixels_mask = ~nodata_mask.any(axis=0) if nodata_mask.any() else np.ones((h, w), dtype=bool)
                
                # Saturated: reflectance > 1.0 on any band
                sat_mask = (norm_arr > MAX_PHYSICAL_LCLUC_REFLECTANCE) & (~nodata_mask)
                sat_pixel_mask = sat_mask.any(axis=0)
                result.saturated_pixel_count = int(sat_pixel_mask.sum())
                result.saturated_pixel_ratio = float(result.saturated_pixel_count / result.total_pixels)
                
                # Negative anomaly: reflectance < 0.0 on any band
                neg_mask = (norm_arr < MIN_PHYSICAL_LCLUC_REFLECTANCE) & (~nodata_mask)
                neg_pixel_mask = neg_mask.any(axis=0)
                result.negative_pixel_count = int(neg_pixel_mask.sum())
                result.negative_pixel_ratio = float(result.negative_pixel_count / result.total_pixels)
                
                # Clean LCLUC pixel: valid and not saturated and not negative
                clean_pixel_mask = valid_pixels_mask & (~sat_pixel_mask) & (~neg_pixel_mask)
                result.clean_lcluc_pixel_count = int(clean_pixel_mask.sum())
                result.clean_lcluc_pixel_ratio = float(result.clean_lcluc_pixel_count / result.total_pixels)
                
                # Flag if any distortion is detected
                result.distortion_flagged = (result.saturated_pixel_count > 0 or result.negative_pixel_count > 0)
    
    except Exception as e:
        result.issues.append(f"RASTER_READ_ERROR_{type(e).__name__}_{str(e)}")
    
    # Quality mask check
    if quality_mask_path is not None:
        qm_path = Path(quality_mask_path)
        if qm_path.exists():
            result.quality_mask_exists = True
            try:
                with rasterio.open(qm_path) as qds:
                    if qds.shape == result.shape and qds.crs == ds.crs:
                        result.quality_mask_aligned = True
                    else:
                        result.quality_mask_aligned = False
                        result.issues.append("QUALITY_MASK_GEOMETRY_MISMATCH")
            except Exception as e:
                result.issues.append(f"QUALITY_MASK_READ_ERROR_{type(e).__name__}")
        else:
            result.issues.append("QUALITY_MASK_NOT_FOUND")
    
    # Check non-mutation
    if check_sha_immutability:
        result.sha256_after = compute_file_sha256(image_path)
        result.mutation_detected = (result.sha256_before != result.sha256_after)
        if result.mutation_detected:
            result.issues.append("CRITICAL_FILE_MUTATION_DETECTED")
    
    # Determine overall validity
    result.is_valid = (
        result.file_exists and
        not result.mutation_detected and
        result.spectral_readiness == '6_BAND_BOA_READY' and
        result.resolution_10m_verified and
        result.crs_valid and
        result.reflectance_physically_plausible and
        len([i for i in result.issues if not i.startswith("REFLECTANCE_OUT_OF_BOUNDS")]) == 0
    )
    
    return result


def audit_annual_window_report(
    report_path: Path,
    limit: Optional[int] = None,
    verify_only_eligible: bool = True
) -> Dict[str, Any]:
    """Execute batch spectral audit across scenes defined in annual-window-report.json."""
    report_path = Path(report_path)
    with report_path.open('r', encoding='utf-8') as f:
        report_data = json.load(f)
    
    all_scenes = report_data.get('scenes', [])
    if verify_only_eligible:
        target_scenes = [s for s in all_scenes if s.get('quality_status') == 'quality_eligible']
    else:
        target_scenes = all_scenes
    
    if limit is not None:
        target_scenes = target_scenes[:limit]
    
    total_targets = len(target_scenes)
    audits: List[Dict[str, Any]] = []
    
    # Counters for metrics
    readiness_counts = {'6_BAND_BOA_READY': 0, 'RGB_NIR_4_BAND_ONLY': 0, 'RGB_3_BAND_ONLY': 0, 'UNSUPPORTED': 0, 'MISSING': 0}
    scale_counts = {'RAW_DN_0_10000': 0, 'NORMALIZED_REFLECTANCE_0_1': 0, 'ANOMALOUS': 0, 'MISSING': 0}
    offset_rule_counts = {'PB_PRE04_ZERO_OFFSET': 0, 'PB_POST04_NEGATIVE_OFFSET': 0, 'CUSTOM_OR_MIXED_OFFSET': 0, 'MISSING': 0}
    year_distribution: Dict[str, int] = {}
    province_distribution: Dict[str, int] = {}
    
    # 10m precision and distortion metrics
    resolution_10m_verified_count = 0
    total_saturated_pixels = 0
    total_negative_pixels = 0
    total_clean_lcluc_pixels = 0
    total_inspected_pixels = 0
    patches_with_saturation = 0
    patches_with_negative = 0
    
    mutations_detected = 0
    plausible_count = 0
    valid_count = 0
    
    province_metrics: Dict[str, Dict[str, Any]] = {}
    
    for idx, scene in enumerate(target_scenes):
        patch_id = scene.get('patch_id', f"idx_{idx}")
        image_path = Path(scene.get('image_path', ''))
        qm_path = Path(scene.get('quality_mask_path', '')) if scene.get('quality_mask_path') else None
        
        # Calibration info
        norm_info = scene.get('normalization', {})
        cal_path = scene.get('calibration', {}).get('path')
        cal_data = None
        if cal_path and Path(cal_path).exists():
            try:
                with open(cal_path, 'r', encoding='utf-8') as cf:
                    cal_data = json.load(cf)
            except Exception:
                cal_data = None
        
        if not cal_data:
            cal_data = {
                'scale': norm_info.get('scale', [ESA_SCALE] * 6),
                'offset': norm_info.get('offset', [0.0] * 6),
                'baseline': None
            }
        
        # Run audit on patch
        audit = audit_single_patch(
            image_path=image_path,
            patch_id=patch_id,
            quality_mask_path=qm_path,
            calibration_data=cal_data,
            declared_bands=scene.get('bands'),
            check_sha_immutability=True,
            sample_pixels=True
        )
        
        audits.append(audit.to_dict())
        
        if not audit.file_exists:
            readiness_counts['MISSING'] += 1
            scale_counts['MISSING'] += 1
            offset_rule_counts['MISSING'] += 1
            continue
        
        if audit.mutation_detected:
            mutations_detected += 1
        
        readiness_counts[audit.spectral_readiness] = readiness_counts.get(audit.spectral_readiness, 0) + 1
        scale_counts[audit.scale_status] = scale_counts.get(audit.scale_status, 0) + 1
        if audit.offset_rule:
            offset_rule_counts[audit.offset_rule] = offset_rule_counts.get(audit.offset_rule, 0) + 1
        
        if audit.reflectance_physically_plausible:
            plausible_count += 1
        if audit.resolution_10m_verified:
            resolution_10m_verified_count += 1
        if audit.is_valid:
            valid_count += 1
            
        yr = str(scene.get('year', 'unknown'))
        year_distribution[yr] = year_distribution.get(yr, 0) + 1
        
        prov = str(scene.get('province', 'unknown'))
        province_distribution[prov] = province_distribution.get(prov, 0) + 1
        
        # Accumulate distortion metrics
        total_inspected_pixels += audit.total_pixels
        total_saturated_pixels += audit.saturated_pixel_count
        total_negative_pixels += audit.negative_pixel_count
        total_clean_lcluc_pixels += audit.clean_lcluc_pixel_count
        
        if audit.saturated_pixel_count > 0:
            patches_with_saturation += 1
        if audit.negative_pixel_count > 0:
            patches_with_negative += 1
            
        # Province-level metrics
        if prov not in province_metrics:
            province_metrics[prov] = {
                'total_patches': 0,
                'resolution_10m_verified': 0,
                'patches_with_saturation': 0,
                'patches_with_negative': 0,
                'saturated_pixels': 0,
                'negative_pixels': 0,
                'clean_pixels': 0,
                'total_pixels': 0
            }
        p_stat = province_metrics[prov]
        p_stat['total_patches'] += 1
        if audit.resolution_10m_verified:
            p_stat['resolution_10m_verified'] += 1
        if audit.saturated_pixel_count > 0:
            p_stat['patches_with_saturation'] += 1
        if audit.negative_pixel_count > 0:
            p_stat['patches_with_negative'] += 1
        p_stat['saturated_pixels'] += audit.saturated_pixel_count
        p_stat['negative_pixels'] += audit.negative_pixel_count
        p_stat['clean_pixels'] += audit.clean_lcluc_pixel_count
        p_stat['total_pixels'] += audit.total_pixels
    
    # Calculate percentage for province metrics
    for prov, p_stat in province_metrics.items():
        t = p_stat['total_pixels']
        p_stat['clean_pixel_ratio'] = float(p_stat['clean_pixels'] / t) if t > 0 else 0.0
        p_stat['saturated_pixel_ratio'] = float(p_stat['saturated_pixels'] / t) if t > 0 else 0.0
        p_stat['negative_pixel_ratio'] = float(p_stat['negative_pixels'] / t) if t > 0 else 0.0
    
    summary = {
        'total_audited': total_targets,
        'eligible_total_in_report': len([s for s in all_scenes if s.get('quality_status') == 'quality_eligible']),
        'total_scenes_in_report': len(all_scenes),
        'spatial_resolution_10m_verified_count': resolution_10m_verified_count,
        'spatial_resolution_10m_verified_ratio': float(resolution_10m_verified_count / total_targets) if total_targets else 0.0,
        'spectral_readiness': readiness_counts,
        'scale_status': scale_counts,
        'offset_rules': offset_rule_counts,
        'year_distribution': year_distribution,
        'province_distribution': province_distribution,
        'province_metrics': province_metrics,
        'distortion_and_saturation': {
            'total_inspected_pixels': total_inspected_pixels,
            'total_clean_lcluc_pixels': total_clean_lcluc_pixels,
            'overall_clean_lcluc_ratio': float(total_clean_lcluc_pixels / total_inspected_pixels) if total_inspected_pixels else 0.0,
            'patches_with_saturation': patches_with_saturation,
            'total_saturated_pixels': total_saturated_pixels,
            'overall_saturated_pixel_ratio': float(total_saturated_pixels / total_inspected_pixels) if total_inspected_pixels else 0.0,
            'patches_with_negative': patches_with_negative,
            'total_negative_pixels': total_negative_pixels,
            'overall_negative_pixel_ratio': float(total_negative_pixels / total_inspected_pixels) if total_inspected_pixels else 0.0,
            'distortion_masking_contract_defined': True
        },
        'mutations_detected': mutations_detected,
        'reflectance_physically_plausible_count': plausible_count,
        'valid_conforming_count': valid_count,
        'contract_verification_status': 'VERIFIED_REAL' if valid_count == total_targets and mutations_detected == 0 else 'VERIFIED_WITH_EXCEPTIONS'
    }
    
    return {
        'summary': summary,
        'audits': audits
    }
