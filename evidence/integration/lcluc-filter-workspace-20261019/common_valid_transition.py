"""Common Valid Area & Strict NoData Exclusion Transition Matrix Engine.

Implements Sections 3, 6, 8, and 13 of UI/GreenBlue_CODEX_LCLUC_Annual_Map_GeoServer_v1.0.md:
1. Spatial Grid & Preflight Alignment:
   Strict verification of CRS, affine transform, dimensions, and taxonomy between T1 and T2.
   Rejects sub-pixel offsets and CRS mismatches immediately before any matrix calculation.
2. Strict Common Valid Domain Definition:
   valid_common = valid_T1 & valid_T2 & aoi_mask.
   Only pixels valid in BOTH observation years and within the AOI mask participate in change detection.
3. Explicit 4-Way Area & Pixel Partitioning:
   - Total AOI Area (Domain)
   - T1 Valid Area
   - T2 Valid Area
   - Common Valid Area (Basis of Transition Matrix)
   - Incomparable Area (Missing/Cloud/Shadow in T1, T2, or both)
4. Absolute NoData Leak Prevention:
   NoData (255 / clouds / shadows / borders) is strictly prevented from masquerading as:
   - "Unchanged" / persistence (diagonal)
   - "Forest loss" / deforestation (falsely inflated by clouds in T2)
   - Any of the 9 valid land cover classes (0..8)
5. Missing Ratio & Provisional Reliability Flag:
   If missing ratio (incomparable_pixels / total_aoi_pixels) > 15% (configurable),
   the transition analysis is flagged as 'PROVISIONAL_UNCERTAIN' to prevent policy misinterpretation.
6. Mathematical Conservation Invariants:
   - Total matrix sum == common_valid_pixels == common_valid_area / pixel_area
   - Row sums == T1 common valid class counts
   - Column sums == T2 common valid class counts
   - Sum of net changes across all classes == 0 (zero-sum conservation)
   - common_valid_pixels + incomparable_pixels == total_aoi_pixels
"""

from __future__ import annotations

import copy
import json
import math
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np

# Standard 9-Class Taxonomy (matches CODEX and backend/app/ml/raster.py)
DEFAULT_CLASS_NAMES: Tuple[str, ...] = (
    "water",               # 0
    "trees",               # 1
    "grass",               # 2
    "flooded_vegetation",  # 3
    "crops",               # 4
    "shrub_and_scrub",     # 5
    "built",               # 6
    "bare",                # 7
    "snow_and_ice",        # 8
)

DEFAULT_CLASS_COLORS: Tuple[str, ...] = (
    "#2563eb",  # 0: water
    "#15803d",  # 1: trees / forest
    "#84cc16",  # 2: grass
    "#14b8a6",  # 3: flooded_vegetation
    "#eab308",  # 4: crops
    "#a16207",  # 5: shrub_and_scrub
    "#dc2626",  # 6: built
    "#a8a29e",  # 7: bare
    "#a5d8f3",  # 8: snow_and_ice
)

DEFAULT_NODATA: int = 255
TRANSITION_NODATA: int = 65535
M2_PER_HA: float = 10000.0
PROVISIONAL_MISSING_RATIO_THRESHOLD: float = 0.15  # 15% missing data threshold


class ReliabilityStatus(str, Enum):
    CERTIFIED_RELIABLE = "CERTIFIED_RELIABLE"
    PROVISIONAL_UNCERTAIN = "PROVISIONAL_UNCERTAIN"


class CertificationBlockedError(RuntimeError):
    """Raised when an official certified change analysis is attempted on an uncertified or provisional transition result."""
    pass


@dataclass(frozen=True)
class IncomparableBreakdown:
    """Detailed breakdown of pixels that cannot be compared across T1 and T2."""
    t1_only_missing_pixels: int
    t2_only_missing_pixels: int
    both_missing_pixels: int
    total_incomparable_pixels: int
    t1_only_missing_ha: float
    t2_only_missing_ha: float
    both_missing_ha: float
    total_incomparable_ha: float
    missing_ratio_pct: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AreaPartitionSummary:
    """Explicit 4-way area and pixel partitioning across AOI, T1, T2, and Common."""
    total_aoi_pixels: int
    total_aoi_area_ha: float
    t1_valid_pixels: int
    t1_valid_area_ha: float
    t2_valid_pixels: int
    t2_valid_area_ha: float
    common_valid_pixels: int
    common_valid_area_ha: float
    incomparable_pixels: int
    incomparable_area_ha: float
    coverage_ratio_pct: float  # common_valid / total_aoi
    incomparable: IncomparableBreakdown

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ClassTransitionSummary:
    """Net and gross transition statistics for a specific land cover class."""
    class_id: int
    name: str
    color: str
    t1_pixels: int
    t2_pixels: int
    t1_area_ha: float
    t2_area_ha: float
    unchanged_pixels: int
    unchanged_ha: float
    gross_loss_pixels: int
    gross_loss_ha: float
    gross_gain_pixels: int
    gross_gain_ha: float
    net_change_pixels: int
    net_change_ha: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CommonValidTransitionResult:
    """Complete analytical results of the common valid transition matrix."""
    aoi_id: str
    from_year: int
    to_year: int
    resolution_m: float
    pixel_area_m2: float
    num_classes: int
    class_names: List[str]
    # Partitioning & Domain
    partition: AreaPartitionSummary
    # Reliability & Quality Governance
    reliability_status: str
    is_provisional: bool
    missing_ratio_pct: float
    provisional_threshold_pct: float
    provisional_warning: Optional[str]
    certification_blocked: bool = False
    # Year Provenance Audit & Mismatch Tracking
    year_mismatch_detected: bool = False
    year_mismatch_details: Optional[Dict[str, Any]] = None
    # Change Dynamics
    changed_pixels: int = 0
    changed_area_ha: float = 0.0
    unchanged_pixels: int = 0
    unchanged_area_ha: float = 0.0
    change_rate_pct: float = 0.0
    # 2D Matrices (K x K)
    transition_pixels: List[List[int]] = field(default_factory=list)
    transition_area_ha: List[List[float]] = field(default_factory=list)
    # Per-Class Summaries
    classes: List[ClassTransitionSummary] = field(default_factory=list)
    # Mathematical Conservation Check Badge
    conservation_check_passed: bool = True
    conservation_identity: Dict[str, Any] = field(default_factory=dict)
    # 2D Map (uint16 array: valid codes 0..K^2-1, non-common pixels = 65535)
    transition_raster: Optional[np.ndarray] = field(default=None, repr=False)

    @property
    def is_certified_usable(self) -> bool:
        """Determines whether this analysis meets the strict requirements for official certification."""
        return (
            (not self.certification_blocked)
            and (not self.is_provisional)
            and (not self.year_mismatch_detected)
            and self.conservation_check_passed
        )

    def assert_certified_usable(self) -> None:
        """Enforces certification gating. Raises CertificationBlockedError if analysis is uncertified."""
        if not self.is_certified_usable:
            reasons = []
            if self.missing_ratio_pct > self.provisional_threshold_pct:
                reasons.append(
                    f"결측률 초과(missing_ratio={self.missing_ratio_pct:.2f}% > 허용기준 {self.provisional_threshold_pct:.1f}%)"
                )
            if self.year_mismatch_detected:
                reasons.append(
                    f"연도 불일치(요청 연도 vs 래스터 출처 연도: {self.year_mismatch_details})"
                )
            if not self.conservation_check_passed:
                reasons.append("수학적 보존 항등식 검증 실패")
            if self.certification_blocked and not reasons:
                reasons.append("공식 인증 거버넌스 정책에 의해 수동 차단됨")
            msg = f"공식 변경분석 인증 차단(Certification Blocked): {'; '.join(reasons)}."
            if self.provisional_warning:
                msg += f" [경고: {self.provisional_warning}]"
            raise CertificationBlockedError(msg)

    def to_dict(self, include_raster: bool = False) -> Dict[str, Any]:
        data = {
            "aoi_id": self.aoi_id,
            "from_year": self.from_year,
            "to_year": self.to_year,
            "resolution_m": self.resolution_m,
            "pixel_area_m2": self.pixel_area_m2,
            "num_classes": self.num_classes,
            "class_names": self.class_names,
            "partition": self.partition.to_dict(),
            "reliability_status": self.reliability_status,
            "is_provisional": self.is_provisional,
            "certification_blocked": self.certification_blocked,
            "is_certified_usable": self.is_certified_usable,
            "year_mismatch_detected": self.year_mismatch_detected,
            "year_mismatch_details": self.year_mismatch_details,
            "missing_ratio_pct": round(self.missing_ratio_pct, 4),
            "provisional_threshold_pct": round(self.provisional_threshold_pct, 2),
            "provisional_warning": self.provisional_warning,
            "changed_pixels": self.changed_pixels,
            "changed_area_ha": round(self.changed_area_ha, 4),
            "unchanged_pixels": self.unchanged_pixels,
            "unchanged_area_ha": round(self.unchanged_area_ha, 4),
            "change_rate_pct": round(self.change_rate_pct, 4),
            "transition_pixels": self.transition_pixels,
            "transition_area_ha": [[round(v, 4) for v in row] for row in self.transition_area_ha],
            "classes": [c.to_dict() for c in self.classes],
            "conservation_check_passed": self.conservation_check_passed,
            "conservation_identity": self.conservation_identity,
        }
        if include_raster and self.transition_raster is not None:
            data["transition_raster_shape"] = list(self.transition_raster.shape)
        return data

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(include_raster=False), ensure_ascii=False, indent=indent)


# ============================================================================
# Preflight Spatial Grid & Transform Alignment
# ============================================================================

def assert_raster_alignment(
    first_profile: Dict[str, Any],
    second_profile: Dict[str, Any],
    tolerance: float = 1e-6,
) -> None:
    """Preflight check: verifies spatial alignment between T1 and T2 profiles.

    Enforces:
    - Identical Coordinate Reference System (CRS)
    - Identical pixel dimensions (width, height)
    - Identical affine transform (dx, dy, x_origin, y_origin).
      Explicitly catches half-pixel or intentional grid offsets.
    """
    # 1. CRS Check
    crs1 = str(first_profile.get("crs", "")).strip().upper()
    crs2 = str(second_profile.get("crs", "")).strip().upper()
    if crs1 != crs2:
        raise ValueError(
            f"래스터 공간 정합 불일치: crs; T1 CRS '{crs1}' != T2 CRS '{crs2}'. "
            "먼저 reproject_to_reference를 실행하세요."
        )

    # 2. Dimensions Check
    w1, h1 = first_profile.get("width"), first_profile.get("height")
    w2, h2 = second_profile.get("width"), second_profile.get("height")
    if (w1, h1) != (w2, h2):
        raise ValueError(
            f"래스터 공간 정합 불일치: dimensions; T1 ({w1}x{h1}) != T2 ({w2}x{h2})."
        )

    # 3. Affine Transform Check (including half-pixel shifts)
    t1 = first_profile.get("transform")
    t2 = second_profile.get("transform")
    if t1 is not None and t2 is not None:
        t1_elements = tuple(t1)[:6] if hasattr(t1, "__iter__") else ()
        t2_elements = tuple(t2)[:6] if hasattr(t2, "__iter__") else ()
        if len(t1_elements) == 6 and len(t2_elements) == 6:
            diffs = [abs(a - b) for a, b in zip(t1_elements, t2_elements)]
            max_diff = max(diffs)
            if max_diff > tolerance:
                raise ValueError(
                    f"래스터 공간 정합 불일치: transform; Affine transform mismatch (max diff={max_diff:.8f}). "
                    f"T1={t1_elements}, T2={t2_elements}. 고의 반픽셀 또는 격자 오프셋이 감지되었습니다."
                )
        elif t1 != t2:
            raise ValueError(f"래스터 공간 정합 불일치: transform; {t1} != {t2}")


# ============================================================================
# Core Common Valid Transition Engine
# ============================================================================

def compute_common_valid_transition(
    t1_raster: np.ndarray,
    t2_raster: np.ndarray,
    aoi_mask: Optional[np.ndarray] = None,
    quality_mask_t1: Optional[np.ndarray] = None,
    quality_mask_t2: Optional[np.ndarray] = None,
    nodata: int = DEFAULT_NODATA,
    resolution_m: float = 10.0,
    class_names: Sequence[str] = DEFAULT_CLASS_NAMES,
    class_colors: Sequence[str] = DEFAULT_CLASS_COLORS,
    aoi_id: str = "custom_aoi",
    from_year: int = 2020,
    to_year: int = 2025,
    t1_metadata: Optional[Dict[str, Any]] = None,
    t2_metadata: Optional[Dict[str, Any]] = None,
    t1_provenance_year: Optional[int] = None,
    t2_provenance_year: Optional[int] = None,
    enforce_year_match: bool = False,
    provisional_threshold: float = PROVISIONAL_MISSING_RATIO_THRESHOLD,
    return_raster: bool = True,
) -> CommonValidTransitionResult:
    """Computes transition matrix strictly on the common valid domain (valid_common).

    Guarantees:
    1. Preflight provenance verification: detects and flags year mismatches
       (e.g., requested T2=2025 vs underlying raster provenance 2021 ESA WorldCover).
    2. valid_common = valid_T1 & valid_T2 & aoi_mask.
    3. NoData (255) in T1 or T2 is NEVER counted as unchanged or as a transition.
    4. Missing ratio > provisional_threshold or year mismatch triggers PROVISIONAL_UNCERTAIN
       status and blocks official certification (certification_blocked=True).
    5. Row sums, col sums, gross loss/gain balances, and zero-sum net changes strictly
       satisfy mathematical conservation identities.
    """
    a = np.asarray(t1_raster)
    b = np.asarray(t2_raster)

    if a.shape != b.shape:
        raise ValueError(f"T1 and T2 raster shapes must be identical, got {a.shape} vs {b.shape}")
    if a.ndim != 2:
        raise ValueError(f"Rasters must be 2D arrays, got dimension {a.ndim}")

    num_classes = len(class_names)
    pixel_area_m2 = resolution_m * resolution_m
    px_to_ha = pixel_area_m2 / M2_PER_HA

    # 0. Provenance Year Mismatch Verification
    def _resolve_year(meta: Optional[Dict[str, Any]], override_year: Optional[int]) -> Optional[int]:
        if override_year is not None:
            return int(override_year)
        if not meta:
            return None
        for key in ("provenance_year", "observation_year", "data_year", "year", "dataset_year"):
            val = meta.get(key)
            if val is not None:
                try:
                    return int(val)
                except (ValueError, TypeError):
                    pass
        return None

    prov_t1 = _resolve_year(t1_metadata, t1_provenance_year)
    prov_t2 = _resolve_year(t2_metadata, t2_provenance_year)

    year_mismatch_detected = False
    mismatch_reasons: List[str] = []

    if prov_t1 is not None and prov_t1 != from_year:
        year_mismatch_detected = True
        mismatch_reasons.append(
            f"T1 요청 연도({from_year}) != 래스터 출처 연도({prov_t1}, 소스: {(t1_metadata or {}).get('source_kind', 'unknown')})"
        )
    if prov_t2 is not None and prov_t2 != to_year:
        year_mismatch_detected = True
        mismatch_reasons.append(
            f"T2 요청 연도({to_year}) != 래스터 출처 연도({prov_t2}, 소스: {(t2_metadata or {}).get('source_kind', 'unknown')})"
        )

    year_mismatch_details = None
    if year_mismatch_detected:
        year_mismatch_details = {
            "t1_requested_year": from_year,
            "t1_provenance_year": prov_t1,
            "t2_requested_year": to_year,
            "t2_provenance_year": prov_t2,
            "t1_source": (t1_metadata or {}).get("source_kind", "unknown"),
            "t2_source": (t2_metadata or {}).get("source_kind", "unknown"),
            "mismatch_reasons": mismatch_reasons,
        }
        if enforce_year_match:
            raise ValueError(
                f"요청 연도와 래스터 출처 연도 불일치(Year Mismatch)로 인해 분석이 거부되었습니다: {'; '.join(mismatch_reasons)}"
            )

    # 1. Base AOI Mask (defaults to entire raster domain if None)
    if aoi_mask is not None:
        mask_aoi = np.asarray(aoi_mask, dtype=bool)
        if mask_aoi.shape != a.shape:
            raise ValueError(f"aoi_mask shape {mask_aoi.shape} != raster shape {a.shape}")
    else:
        mask_aoi = np.ones(a.shape, dtype=bool)

    total_aoi_pixels = int(mask_aoi.sum())
    total_aoi_area_ha = total_aoi_pixels * px_to_ha

    # 2. Individual Validity Masks
    valid_t1_raw = (a != nodata) & np.isfinite(a) & (a >= 0) & (a < num_classes) & (a == np.floor(a))
    if quality_mask_t1 is not None:
        q1 = np.asarray(quality_mask_t1)
        if q1.shape != a.shape:
            raise ValueError(f"quality_mask_t1 shape {q1.shape} != raster shape {a.shape}")
        valid_t1_raw &= (q1 > 0)

    valid_t2_raw = (b != nodata) & np.isfinite(b) & (b >= 0) & (b < num_classes) & (b == np.floor(b))
    if quality_mask_t2 is not None:
        q2 = np.asarray(quality_mask_t2)
        if q2.shape != b.shape:
            raise ValueError(f"quality_mask_t2 shape {q2.shape} != raster shape {b.shape}")
        valid_t2_raw &= (q2 > 0)

    # Scoped to AOI
    valid_t1 = valid_t1_raw & mask_aoi
    valid_t2 = valid_t2_raw & mask_aoi

    t1_valid_pixels = int(valid_t1.sum())
    t1_valid_area_ha = t1_valid_pixels * px_to_ha

    t2_valid_pixels = int(valid_t2.sum())
    t2_valid_area_ha = t2_valid_pixels * px_to_ha

    # 3. Common Valid Domain: valid_common = valid_T1 & valid_T2 & aoi_mask
    valid_common = valid_t1 & valid_t2
    common_valid_pixels = int(valid_common.sum())
    common_valid_area_ha = common_valid_pixels * px_to_ha

    # 4. Incomparable Pixels Partitioning
    incomparable_pixels = total_aoi_pixels - common_valid_pixels
    incomparable_area_ha = incomparable_pixels * px_to_ha

    t1_only_missing = int((mask_aoi & ~valid_t1 & valid_t2).sum())
    t2_only_missing = int((mask_aoi & valid_t1 & ~valid_t2).sum())
    both_missing = int((mask_aoi & ~valid_t1 & ~valid_t2).sum())

    # Mathematical identity verification for incomparable partitioning
    assert incomparable_pixels == (t1_only_missing + t2_only_missing + both_missing), (
        f"Incomparable partition mismatch: {incomparable_pixels} != {t1_only_missing} + {t2_only_missing} + {both_missing}"
    )

    incomparable_breakdown = IncomparableBreakdown(
        t1_only_missing_pixels=t1_only_missing,
        t2_only_missing_pixels=t2_only_missing,
        both_missing_pixels=both_missing,
        total_incomparable_pixels=incomparable_pixels,
        t1_only_missing_ha=round(t1_only_missing * px_to_ha, 4),
        t2_only_missing_ha=round(t2_only_missing * px_to_ha, 4),
        both_missing_ha=round(both_missing * px_to_ha, 4),
        total_incomparable_ha=round(incomparable_area_ha, 4),
        missing_ratio_pct=round((incomparable_pixels / total_aoi_pixels * 100.0) if total_aoi_pixels > 0 else 0.0, 4),
    )

    coverage_ratio_pct = (common_valid_pixels / total_aoi_pixels * 100.0) if total_aoi_pixels > 0 else 0.0

    partition = AreaPartitionSummary(
        total_aoi_pixels=total_aoi_pixels,
        total_aoi_area_ha=round(total_aoi_area_ha, 4),
        t1_valid_pixels=t1_valid_pixels,
        t1_valid_area_ha=round(t1_valid_area_ha, 4),
        t2_valid_pixels=t2_valid_pixels,
        t2_valid_area_ha=round(t2_valid_area_ha, 4),
        common_valid_pixels=common_valid_pixels,
        common_valid_area_ha=round(common_valid_area_ha, 4),
        incomparable_pixels=incomparable_pixels,
        incomparable_area_ha=round(incomparable_area_ha, 4),
        coverage_ratio_pct=round(coverage_ratio_pct, 4),
        incomparable=incomparable_breakdown,
    )

    # 5. Missing Ratio & Provisional Flag / Certification Gating
    missing_ratio = (incomparable_pixels / total_aoi_pixels) if total_aoi_pixels > 0 else 0.0
    missing_ratio_exceeded = missing_ratio > provisional_threshold
    is_provisional = missing_ratio_exceeded or year_mismatch_detected
    certification_blocked = is_provisional

    if is_provisional:
        reliability_status = ReliabilityStatus.PROVISIONAL_UNCERTAIN.value
        warning_parts = []
        if missing_ratio_exceeded:
            warning_parts.append(
                f"AOI 결측률({missing_ratio * 100.0:.2f}%)이 허용 기준({provisional_threshold * 100.0:.1f}%)을 초과하여 "
                "변화 통계가 '미확정(Provisional/Uncertain)' 상태로 플래그되었으며 공식 변경분석 인증이 차단(Blocked)되었습니다."
            )
        if year_mismatch_detected:
            warning_parts.append(
                f"요청 연도와 기본 래스터 출처 연도 불일치(Year Mismatch)가 감지되었습니다 ({'; '.join(mismatch_reasons)}). "
                "공식 변경분석 인증이 차단(Blocked)되었습니다."
            )
        provisional_warning = " ".join(warning_parts)
    else:
        reliability_status = ReliabilityStatus.CERTIFIED_RELIABLE.value
        provisional_warning = None

    # 6. 2D Transition Matrix (K x K) strictly on common_valid
    if common_valid_pixels > 0:
        a_valid = a[valid_common].astype(np.int64)
        b_valid = b[valid_common].astype(np.int64)
        codes = a_valid * num_classes + b_valid
        matrix = np.bincount(codes, minlength=num_classes * num_classes).reshape(num_classes, num_classes)
    else:
        matrix = np.zeros((num_classes, num_classes), dtype=np.int64)
        codes = np.array([], dtype=np.int64)

    area_ha_matrix = (matrix.astype(np.float64) * px_to_ha).tolist()
    pixel_matrix = matrix.tolist()

    # 7. Overall Dynamics
    unchanged_pixels = int(np.trace(matrix))
    changed_pixels = common_valid_pixels - unchanged_pixels
    unchanged_area_ha = unchanged_pixels * px_to_ha
    changed_area_ha = changed_pixels * px_to_ha
    change_rate_pct = (changed_pixels / common_valid_pixels * 100.0) if common_valid_pixels > 0 else 0.0

    # 8. Per-Class Summaries and Net Change Identities
    row_sums = matrix.sum(axis=1)  # T1 class counts in common valid
    col_sums = matrix.sum(axis=0)  # T2 class counts in common valid

    classes_summary: List[ClassTransitionSummary] = []
    for cid in range(num_classes):
        c_name = class_names[cid]
        c_color = class_colors[cid % len(class_colors)]

        t1_px = int(row_sums[cid])
        t2_px = int(col_sums[cid])
        diag_px = int(matrix[cid, cid])

        gross_loss_px = t1_px - diag_px
        gross_gain_px = t2_px - diag_px
        net_px = t2_px - t1_px  # gross_gain - gross_loss

        classes_summary.append(ClassTransitionSummary(
            class_id=cid,
            name=c_name,
            color=c_color,
            t1_pixels=t1_px,
            t2_pixels=t2_px,
            t1_area_ha=round(t1_px * px_to_ha, 4),
            t2_area_ha=round(t2_px * px_to_ha, 4),
            unchanged_pixels=diag_px,
            unchanged_ha=round(diag_px * px_to_ha, 4),
            gross_loss_pixels=gross_loss_px,
            gross_loss_ha=round(gross_loss_px * px_to_ha, 4),
            gross_gain_pixels=gross_gain_px,
            gross_gain_ha=round(gross_gain_px * px_to_ha, 4),
            net_change_pixels=net_px,
            net_change_ha=round(net_px * px_to_ha, 4),
        ))

    # 9. Mathematical Conservation Invariants Verification
    sum_matrix_pixels = int(matrix.sum())
    sum_row_pixels = int(row_sums.sum())
    sum_col_pixels = int(col_sums.sum())
    sum_gross_loss = sum(c.gross_loss_pixels for c in classes_summary)
    sum_gross_gain = sum(c.gross_gain_pixels for c in classes_summary)
    sum_net_changes = sum(c.net_change_pixels for c in classes_summary)

    # Invariants verification:
    all_classes_balanced = all(
        (c.gross_gain_pixels - c.gross_loss_pixels == c.net_change_pixels) for c in classes_summary
    )
    gross_loss_gain_balanced = (sum_gross_loss == sum_gross_gain)
    net_changes_zero_sum = (sum_net_changes == 0)

    conservation_identity = {
        "matrix_sum_equals_common_valid": (sum_matrix_pixels == common_valid_pixels),
        "row_sum_equals_common_valid": (sum_row_pixels == common_valid_pixels),
        "col_sum_equals_common_valid": (sum_col_pixels == common_valid_pixels),
        "net_changes_zero_sum": net_changes_zero_sum,
        "gross_loss_gain_balance": gross_loss_gain_balanced,
        "all_classes_balanced": all_classes_balanced,
        "zero_sum_identity_verified": (gross_loss_gain_balanced and net_changes_zero_sum and all_classes_balanced),
        "domain_partition_conserved": (common_valid_pixels + incomparable_pixels == total_aoi_pixels),
        "nodata_strictly_excluded_from_matrix": True,
        "matrix_shape": list(matrix.shape),
        "matrix_sum": sum_matrix_pixels,
        "gross_loss_total_pixels": sum_gross_loss,
        "gross_gain_total_pixels": sum_gross_gain,
        "net_change_sum": sum_net_changes,
        "common_valid_pixels": common_valid_pixels,
        "total_aoi_pixels": total_aoi_pixels,
        "incomparable_pixels": incomparable_pixels,
    }
    conservation_check_passed = all([
        conservation_identity["matrix_sum_equals_common_valid"],
        conservation_identity["row_sum_equals_common_valid"],
        conservation_identity["col_sum_equals_common_valid"],
        conservation_identity["net_changes_zero_sum"],
        conservation_identity["gross_loss_gain_balance"],
        conservation_identity["all_classes_balanced"],
        conservation_identity["domain_partition_conserved"],
    ])

    if not conservation_check_passed:
        certification_blocked = True
        reliability_status = ReliabilityStatus.PROVISIONAL_UNCERTAIN.value
        is_provisional = True

    # 10. Optional 2D Transitions Map
    transition_raster = None
    if return_raster:
        transition_raster = np.full(a.shape, TRANSITION_NODATA, dtype=np.uint16)
        if common_valid_pixels > 0:
            transition_raster[valid_common] = codes.astype(np.uint16)

    return CommonValidTransitionResult(
        aoi_id=aoi_id,
        from_year=from_year,
        to_year=to_year,
        resolution_m=resolution_m,
        pixel_area_m2=pixel_area_m2,
        num_classes=num_classes,
        class_names=list(class_names),
        partition=partition,
        reliability_status=reliability_status,
        is_provisional=is_provisional,
        certification_blocked=certification_blocked,
        year_mismatch_detected=year_mismatch_detected,
        year_mismatch_details=year_mismatch_details,
        missing_ratio_pct=missing_ratio * 100.0,
        provisional_threshold_pct=provisional_threshold * 100.0,
        provisional_warning=provisional_warning,
        changed_pixels=changed_pixels,
        changed_area_ha=changed_area_ha,
        unchanged_pixels=unchanged_pixels,
        unchanged_area_ha=unchanged_area_ha,
        change_rate_pct=change_rate_pct,
        transition_pixels=pixel_matrix,
        transition_area_ha=area_ha_matrix,
        classes=classes_summary,
        conservation_check_passed=conservation_check_passed,
        conservation_identity=conservation_identity,
        transition_raster=transition_raster,
    )
