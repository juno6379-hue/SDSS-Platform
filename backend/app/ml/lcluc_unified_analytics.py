"""LCLUC Unified Analytics and Invariant Statistics Engine.

Implements Sections 3, 8, and 9 of UI/GreenBlue_CODEX_LCLUC_Annual_Map_GeoServer_v1.0.md:
1. Invariant Statistics Guarantee:
   Statistics are computed strictly from the source classification raster (and quality masks),
   NOT from UI zoom level, viewport size, or swipe slider position.
2. Authentic Area Calculations:
   Pixel counts × spatial resolution (e.g. 10m × 10m = 100 m² = 0.01 ha) or ellipsoidal geodesic area.
   Never uses EPSG:3857 distorted areas for policy statistics.
3. Transition Matrix Calculation:
   Rows = T1, Columns = T2, Diagonal = unchanged, Off-diagonal = transition.
   Total matrix sum strictly equals the common valid area.
   NoData pixels in T1 or T2 are strictly excluded from the transition matrix.
4. Unified Provenance & Identity:
   Map, Legend, Annual Area, and Transition Matrix all reference the exact same
   dataset_id, version, aoi_id, and observation_period.
5. Frame Manifest Schema:
   Full dataclass and schema generator matching Section 9 mandatory fields.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np

# Standard 9-Class Taxonomy (matches backend/app/ml/raster.py CLASS_NAMES)
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

# Standard Color Palette for UI and SLD styling
DEFAULT_CLASS_COLORS: Tuple[str, ...] = (
    "#2563eb",  # 0: water (blue)
    "#15803d",  # 1: trees (dark green)
    "#84cc16",  # 2: grass (lime)
    "#14b8a6",  # 3: flooded_vegetation (teal)
    "#eab308",  # 4: crops (yellow)
    "#a16207",  # 5: shrub_and_scrub (amber)
    "#dc2626",  # 6: built (red)
    "#a8a29e",  # 7: bare (stone grey)
    "#a5d8f3",  # 8: snow_and_ice (light cyan)
)

DEFAULT_NODATA: int = 255
M2_PER_HA: float = 10000.0


class SourceKind(str, Enum):
    REFERENCE_LANDCOVER = "reference_landcover"
    MODEL_PREDICTION = "model_prediction"
    SYNTHETIC_FIXTURE = "synthetic_fixture"


class PublicationState(str, Enum):
    REGISTERED = "registered"
    VALIDATED_FOR_RENDERING = "validated_for_rendering"
    PUBLISHED_TO_STAGING = "published_to_staging"
    TILE_VERIFIED = "tile_verified"


class ValidationState(str, Enum):
    DRAFT = "Draft"
    VALIDATED = "Validated"
    APPROVED = "Approved"


class ApprovalState(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class DatasetIdentity:
    """Unified provenance and identity binding.

    Ensures Map, Legend, Annual Area, and Transition Matrix all reference
    the exact same dataset_id, version, aoi_id, and observation_period.
    """
    dataset_id: str
    version: str
    aoi_id: str
    observation_period: str
    source_kind: SourceKind = SourceKind.MODEL_PREDICTION
    checksum: Optional[str] = None

    def assert_matches(self, other: DatasetIdentity) -> None:
        """Raises ValueError if any core identity field mismatches."""
        if self.dataset_id != other.dataset_id:
            raise ValueError(f"dataset_id mismatch: '{self.dataset_id}' != '{other.dataset_id}'")
        if self.version != other.version:
            raise ValueError(f"version mismatch: '{self.version}' != '{other.version}'")
        if self.aoi_id != other.aoi_id:
            raise ValueError(f"aoi_id mismatch: '{self.aoi_id}' != '{other.aoi_id}'")
        if self.observation_period != other.observation_period:
            raise ValueError(
                f"observation_period mismatch: '{self.observation_period}' != '{other.observation_period}'"
            )


@dataclass
class FrameManifest:
    """Frame Manifest implementing Section 9 mandatory fields."""
    series_id: str
    frame_id: str
    result_id: str  # or dataset_id
    version: str
    year: int
    time_parameter: str
    observation_start: str
    observation_end: str
    composite_method: str
    source_kind: str  # reference_landcover, model_prediction, synthetic_fixture
    source_refs: List[str]
    model_id: Optional[str] = None
    model_version: Optional[str] = None
    class_schema_id: str = "indonesia_lcluc_9class"
    class_schema_version: str = "1.0"
    quality_mask_ref: Optional[str] = None
    analysis_grid_ref: Optional[str] = None
    footprint: Dict[str, Any] = field(default_factory=dict)
    bbox_crs84: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0, 0.0])
    native_crs: str = "EPSG:4326"
    resolution: float = 10.0
    nodata: int = DEFAULT_NODATA
    storage_ref: str = ""
    checksum: str = ""
    geoserver_layer: Optional[str] = None
    style_version: str = "v1.0"
    publication_state: str = PublicationState.REGISTERED.value
    scientific_validation_state: str = ValidationState.DRAFT.value
    approval_state: str = ApprovalState.PENDING.value

    def validate(self) -> None:
        """Validates all mandatory Section 9 requirements."""
        if not self.series_id:
            raise ValueError("series_id is required")
        if not self.frame_id:
            raise ValueError("frame_id is required")
        if not self.result_id:
            raise ValueError("result_id is required")
        if not self.version:
            raise ValueError("version is required")
        if not (1900 <= self.year <= 2100):
            raise ValueError(f"year must be between 1900 and 2100, got {self.year}")
        if self.source_kind not in [s.value for s in SourceKind]:
            raise ValueError(f"source_kind must be one of {[s.value for s in SourceKind]}, got {self.source_kind}")
        if self.resolution <= 0:
            raise ValueError(f"resolution must be positive, got {self.resolution}")
        if len(self.bbox_crs84) != 4:
            raise ValueError("bbox_crs84 must be [minx, miny, maxx, maxy]")
        if self.bbox_crs84[0] > self.bbox_crs84[2] or self.bbox_crs84[1] > self.bbox_crs84[3]:
            raise ValueError("Invalid bbox_crs84 order: min coordinates must not exceed max coordinates")

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


@dataclass
class AnnualClassStat:
    """Class area and proportion for a single timepoint."""
    class_id: int
    name: str
    color: str
    pixels: int
    area_m2: float
    area_ha: float
    ratio_pct: float


@dataclass
class AnnualStatistics:
    """Annual land cover statistics for a single timepoint and AOI."""
    identity: DatasetIdentity
    year: int
    total_pixels: int
    valid_pixels: int
    nodata_pixels: int
    valid_area_m2: float
    valid_area_ha: float
    resolution_m: float
    area_method: str
    classes: List[AnnualClassStat]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "identity": asdict(self.identity),
            "year": self.year,
            "total_pixels": self.total_pixels,
            "valid_pixels": self.valid_pixels,
            "nodata_pixels": self.nodata_pixels,
            "valid_area_m2": round(self.valid_area_m2, 2),
            "valid_area_ha": round(self.valid_area_ha, 4),
            "resolution_m": self.resolution_m,
            "area_method": self.area_method,
            "classes": [asdict(c) for c in self.classes],
        }


@dataclass
class TransitionClassChange:
    """Net and gross transition statistics for a specific class."""
    class_id: int
    name: str
    color: str
    before_pixels: int
    after_pixels: int
    before_area_ha: float
    after_area_ha: float
    net_area_ha: float
    gross_loss_ha: float
    gross_gain_ha: float
    unchanged_ha: float


@dataclass
class TransitionAnalytics:
    """Comprehensive change statistics and transition matrix across T1 and T2."""
    t1_identity: DatasetIdentity
    t2_identity: DatasetIdentity
    from_year: int
    to_year: int
    elapsed_years: float
    resolution_m: float
    area_method: str
    # Pixel & Area sums
    total_domain_pixels: int
    common_valid_pixels: int
    excluded_nodata_pixels: int
    common_valid_area_m2: float
    common_valid_area_ha: float
    changed_pixels: int
    changed_area_m2: float
    changed_area_ha: float
    change_rate_pct: float
    # Matrices (shape K x K)
    class_names: List[str]
    transition_pixels: List[List[int]]
    transition_area_m2: List[List[float]]
    transition_area_ha: List[List[float]]
    # Per-class summary
    classes: List[TransitionClassChange]
    # Invariant guarantee badge
    statistics_basis: str = "full_valid_source_raster_invariant"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "t1_identity": asdict(self.t1_identity),
            "t2_identity": asdict(self.t2_identity),
            "from_year": self.from_year,
            "to_year": self.to_year,
            "elapsed_years": self.elapsed_years,
            "resolution_m": self.resolution_m,
            "area_method": self.area_method,
            "total_domain_pixels": self.total_domain_pixels,
            "common_valid_pixels": self.common_valid_pixels,
            "excluded_nodata_pixels": self.excluded_nodata_pixels,
            "common_valid_area_m2": round(self.common_valid_area_m2, 2),
            "common_valid_area_ha": round(self.common_valid_area_ha, 4),
            "changed_pixels": self.changed_pixels,
            "changed_area_m2": round(self.changed_area_m2, 2),
            "changed_area_ha": round(self.changed_area_ha, 4),
            "change_rate_pct": round(self.change_rate_pct, 4),
            "class_names": self.class_names,
            "transition_pixels": self.transition_pixels,
            "transition_area_m2": [[round(v, 2) for v in row] for row in self.transition_area_m2],
            "transition_area_ha": [[round(v, 4) for v in row] for row in self.transition_area_ha],
            "classes": [asdict(c) for c in self.classes],
            "statistics_basis": self.statistics_basis,
        }


@dataclass
class PixelInspection:
    """Inspection result for a single geographic coordinate / pixel."""
    row: int
    col: int
    t1_class_id: Optional[int]
    t1_class_name: Optional[str]
    t2_class_id: Optional[int]
    t2_class_name: Optional[str]
    is_changed: bool
    is_nodata: bool
    t1_identity: DatasetIdentity
    t2_identity: DatasetIdentity
    pixel_area_m2: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "row": self.row,
            "col": self.col,
            "t1_class_id": self.t1_class_id,
            "t1_class_name": self.t1_class_name,
            "t2_class_id": self.t2_class_id,
            "t2_class_name": self.t2_class_name,
            "is_changed": self.is_changed,
            "is_nodata": self.is_nodata,
            "pixel_area_m2": self.pixel_area_m2,
            "t1_identity": asdict(self.t1_identity),
            "t2_identity": asdict(self.t2_identity),
        }


# ============================================================================
# Core Analytic Calculation Engines (Invariant to UI Viewport/Zoom/Swipe)
# ============================================================================

def compute_annual_statistics(
    raster: np.ndarray,
    quality_mask: Optional[np.ndarray] = None,
    nodata: int = DEFAULT_NODATA,
    resolution_m: float = 10.0,
    class_names: Sequence[str] = DEFAULT_CLASS_NAMES,
    class_colors: Sequence[str] = DEFAULT_CLASS_COLORS,
    identity: Optional[DatasetIdentity] = None,
    year: int = 2020,
    area_method: str = "projected_grid_area_m2",
) -> AnnualStatistics:
    """Computes single-year land cover distribution strictly from the source raster.

    Guarantees:
    - Never influenced by UI zoom level, viewport size, or swipe position.
    - Pixel count × (resolution × resolution) gives authentic ground area in m².
    - Area sum strictly equals valid_pixels × pixel_area.
    - Zero valid pixels handled gracefully without ZeroDivisionError.
    """
    arr = np.asarray(raster)
    if arr.ndim != 2:
        raise ValueError(f"raster must be 2D array, got shape {arr.shape}")

    total_pixels = int(arr.size)
    valid = (arr != nodata) & np.isfinite(arr) & (arr >= 0) & (arr < len(class_names))
    if quality_mask is not None:
        valid &= np.asarray(quality_mask, dtype=bool)

    valid_pixels = int(valid.sum())
    nodata_pixels = total_pixels - valid_pixels

    px_area_m2 = resolution_m * resolution_m
    valid_area_m2 = valid_pixels * px_area_m2
    valid_area_ha = valid_area_m2 / M2_PER_HA

    classes: List[AnnualClassStat] = []
    if valid_pixels > 0:
        counts = np.bincount(arr[valid].astype(np.int64), minlength=len(class_names))
    else:
        counts = np.zeros(len(class_names), dtype=np.int64)

    for cid, name in enumerate(class_names):
        c_pixels = int(counts[cid])
        c_area_m2 = c_pixels * px_area_m2
        c_area_ha = c_area_m2 / M2_PER_HA
        c_ratio = (c_pixels / valid_pixels * 100.0) if valid_pixels > 0 else 0.0
        color = class_colors[cid % len(class_colors)]

        classes.append(AnnualClassStat(
            class_id=cid,
            name=str(name),
            color=color,
            pixels=c_pixels,
            area_m2=c_area_m2,
            area_ha=c_area_ha,
            ratio_pct=round(c_ratio, 2),
        ))

    ident = identity or DatasetIdentity(
        dataset_id="default_dataset",
        version="v1",
        aoi_id="default_aoi",
        observation_period=str(year),
    )

    return AnnualStatistics(
        identity=ident,
        year=year,
        total_pixels=total_pixels,
        valid_pixels=valid_pixels,
        nodata_pixels=nodata_pixels,
        valid_area_m2=valid_area_m2,
        valid_area_ha=valid_area_ha,
        resolution_m=resolution_m,
        area_method=area_method,
        classes=classes,
    )


def compute_transition_analytics(
    t1_raster: np.ndarray,
    t2_raster: np.ndarray,
    t1_mask: Optional[np.ndarray] = None,
    t2_mask: Optional[np.ndarray] = None,
    nodata: int = DEFAULT_NODATA,
    resolution_m: float = 10.0,
    class_names: Sequence[str] = DEFAULT_CLASS_NAMES,
    class_colors: Sequence[str] = DEFAULT_CLASS_COLORS,
    t1_identity: Optional[DatasetIdentity] = None,
    t2_identity: Optional[DatasetIdentity] = None,
    from_year: int = 2020,
    to_year: int = 2025,
    area_method: str = "projected_grid_area_m2",
) -> TransitionAnalytics:
    """Computes full-raster change statistics and transition matrix between T1 and T2.

    Guarantees:
    - Rows = T1, Columns = T2.
    - Diagonal = unchanged, Off-diagonal = transition.
    - Total matrix sum strictly equals common valid area.
    - Strict NoData exclusion: if either T1 or T2 is NoData, the pixel is excluded from transition matrix.
    - Invariant to UI viewport/zoom/swipe position.
    """
    a = np.asarray(t1_raster)
    b = np.asarray(t2_raster)
    if a.shape != b.shape or a.ndim != 2:
        raise ValueError(f"t1 and t2 rasters must have identical 2D shape, got {a.shape} vs {b.shape}")

    k = len(class_names)
    total_domain_pixels = int(a.size)

    # Common valid mask: both must be non-nodata and within valid class bounds
    common_valid = (
        (a != nodata) & (b != nodata)
        & np.isfinite(a) & np.isfinite(b)
        & (a >= 0) & (a < k)
        & (b >= 0) & (b < k)
    )
    if t1_mask is not None:
        common_valid &= np.asarray(t1_mask, dtype=bool)
    if t2_mask is not None:
        common_valid &= np.asarray(t2_mask, dtype=bool)

    common_valid_pixels = int(common_valid.sum())
    excluded_nodata_pixels = total_domain_pixels - common_valid_pixels

    px_area_m2 = resolution_m * resolution_m
    common_valid_area_m2 = common_valid_pixels * px_area_m2
    common_valid_area_ha = common_valid_area_m2 / M2_PER_HA

    if common_valid_pixels > 0:
        a_valid = a[common_valid].astype(np.int64)
        b_valid = b[common_valid].astype(np.int64)
        # 1D codes: code = a * K + b
        code = a_valid * k + b_valid
        pixels_matrix = np.bincount(code, minlength=k * k).reshape(k, k)
    else:
        pixels_matrix = np.zeros((k, k), dtype=np.int64)

    area_m2_matrix = pixels_matrix.astype(np.float64) * px_area_m2
    area_ha_matrix = area_m2_matrix / M2_PER_HA

    # Change calculations
    unchanged_pixels = int(np.trace(pixels_matrix))
    changed_pixels = common_valid_pixels - unchanged_pixels
    changed_area_m2 = changed_pixels * px_area_m2
    changed_area_ha = changed_area_m2 / M2_PER_HA
    change_rate_pct = (changed_pixels / common_valid_pixels * 100.0) if common_valid_pixels > 0 else 0.0

    # Per-class transitions
    # Row sum = before (T1)
    before_px = pixels_matrix.sum(axis=1)
    # Column sum = after (T2)
    after_px = pixels_matrix.sum(axis=0)

    classes_summary: List[TransitionClassChange] = []
    for cid, name in enumerate(class_names):
        b_px = int(before_px[cid])
        a_px = int(after_px[cid])
        b_ha = (b_px * px_area_m2) / M2_PER_HA
        a_ha = (a_px * px_area_m2) / M2_PER_HA
        net_ha = a_ha - b_ha

        diag_px = int(pixels_matrix[cid, cid])
        unchanged_ha = (diag_px * px_area_m2) / M2_PER_HA
        gross_loss_ha = b_ha - unchanged_ha
        gross_gain_ha = a_ha - unchanged_ha
        color = class_colors[cid % len(class_colors)]

        classes_summary.append(TransitionClassChange(
            class_id=cid,
            name=str(name),
            color=color,
            before_pixels=b_px,
            after_pixels=a_px,
            before_area_ha=round(b_ha, 4),
            after_area_ha=round(a_ha, 4),
            net_area_ha=round(net_ha, 4),
            gross_loss_ha=round(gross_loss_ha, 4),
            gross_gain_ha=round(gross_gain_ha, 4),
            unchanged_ha=round(unchanged_ha, 4),
        ))

    ident1 = t1_identity or DatasetIdentity("t1", "v1", "aoi", str(from_year))
    ident2 = t2_identity or DatasetIdentity("t2", "v1", "aoi", str(to_year))

    return TransitionAnalytics(
        t1_identity=ident1,
        t2_identity=ident2,
        from_year=from_year,
        to_year=to_year,
        elapsed_years=float(to_year - from_year),
        resolution_m=resolution_m,
        area_method=area_method,
        total_domain_pixels=total_domain_pixels,
        common_valid_pixels=common_valid_pixels,
        excluded_nodata_pixels=excluded_nodata_pixels,
        common_valid_area_m2=common_valid_area_m2,
        common_valid_area_ha=common_valid_area_ha,
        changed_pixels=changed_pixels,
        changed_area_m2=changed_area_m2,
        changed_area_ha=changed_area_ha,
        change_rate_pct=change_rate_pct,
        class_names=list(class_names),
        transition_pixels=pixels_matrix.tolist(),
        transition_area_m2=area_m2_matrix.tolist(),
        transition_area_ha=area_ha_matrix.tolist(),
        classes=classes_summary,
    )


def inspect_pixel_at(
    t1_raster: np.ndarray,
    t2_raster: np.ndarray,
    row: int,
    col: int,
    nodata: int = DEFAULT_NODATA,
    resolution_m: float = 10.0,
    class_names: Sequence[str] = DEFAULT_CLASS_NAMES,
    t1_identity: Optional[DatasetIdentity] = None,
    t2_identity: Optional[DatasetIdentity] = None,
) -> PixelInspection:
    """Inspects authentic integer classes at a specific pixel coordinate.

    Never reverse-engineers class IDs from display RGB colors.
    """
    h, w = t1_raster.shape
    if not (0 <= row < h and 0 <= col < w):
        raise IndexError(f"Pixel coordinates (row={row}, col={col}) out of bounds for raster ({h}x{w})")

    val1 = int(t1_raster[row, col])
    val2 = int(t2_raster[row, col])

    is_t1_nodata = (val1 == nodata) or (val1 < 0) or (val1 >= len(class_names))
    is_t2_nodata = (val2 == nodata) or (val2 < 0) or (val2 >= len(class_names))
    is_nodata = is_t1_nodata or is_t2_nodata

    t1_class_id = None if is_t1_nodata else val1
    t1_class_name = None if is_t1_nodata else class_names[val1]
    t2_class_id = None if is_t2_nodata else val2
    t2_class_name = None if is_t2_nodata else class_names[val2]

    is_changed = False if is_nodata else (val1 != val2)

    return PixelInspection(
        row=row,
        col=col,
        t1_class_id=t1_class_id,
        t1_class_name=t1_class_name,
        t2_class_id=t2_class_id,
        t2_class_name=t2_class_name,
        is_changed=is_changed,
        is_nodata=is_nodata,
        t1_identity=t1_identity or DatasetIdentity("t1", "v1", "aoi", "2020"),
        t2_identity=t2_identity or DatasetIdentity("t2", "v1", "aoi", "2025"),
        pixel_area_m2=resolution_m * resolution_m,
    )


def build_4x4_acceptance_fixture() -> Tuple[np.ndarray, np.ndarray]:
    """Builds the mandatory Section 13 Test #4 acceptance fixture.

    Setup (4x4 mock raster):
    - 1 -> 2: two pixels (row 0 col 0, row 0 col 1)
    - 2 -> 1: one pixel (row 1 col 0)
    - All other pixels unchanged (fill class 0, 1, 2, 4)
    """
    t1 = np.array([
        [1, 1, 0, 4],
        [2, 1, 1, 4],
        [0, 0, 2, 2],
        [4, 4, 1, 1],
    ], dtype=np.uint8)

    t2 = np.array([
        [2, 2, 0, 4],  # 1->2 (2 pixels)
        [1, 1, 1, 4],  # 2->1 (1 pixel)
        [0, 0, 2, 2],  # unchanged
        [4, 4, 1, 1],  # unchanged
    ], dtype=np.uint8)

    return t1, t2
