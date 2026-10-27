"""Fail-closed province coverage measurement from pinned equal-area masks."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.features import geometry_mask
from rasterio.warp import transform_geom
from shapely.geometry import shape
from shapely.ops import transform as shapely_transform, unary_union


COVERAGE_REPORT_SCHEMA_VERSION = "1.1"
SOURCE_SCHEMA_VERSION = "province-coverage-source/1.0"
BOUNDARY_SCHEMA_VERSION = "province-boundaries/1.0"
QUALITY_MASK_SEMANTICS = "BINARY_OBSERVED_0_1"
QUALITY_MASK_POLICY_VERSION = "quality-mask/1.0"
CAUSE_MASK_SEMANTICS = "0_NONE_1_CLOUD_2_SHADOW_3_NODATA"
CAUSE_MASK_POLICY_VERSION = "coverage-cause-mask/1.0"
EQUAL_AREA_CRS = "EPSG:6933"
ALLOWED_QUALITY_STATUSES = {"quality_eligible", "quality_insufficient"}
COVERAGE_STATES = (
    "OBSERVED", "MISSING", "CLOUD", "SHADOW", "NODATA",
    "OUTSIDE_FOOTPRINT", "NOT_MEASURED",
)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class CoverageEvidenceError(ValueError):
    """Raised when evidence cannot support the requested measurement."""


@dataclass(frozen=True)
class PinnedFile:
    path: Path
    sha256: str


@dataclass
class ProvinceYearCoverage:
    province_id: str
    year: int
    boundary_area_ha: float
    patch_rows_count: int
    unique_scene_count: int
    footprint_area_ha: float
    observed_area_ha: float
    missing_area_ha: float
    cloud_area_ha: float
    shadow_area_ha: float
    nodata_area_ha: float
    outside_footprint_area_ha: float
    not_measured_area_ha: float
    observed_coverage_pct: float
    missing_coverage_pct: float
    measurement_status: str
    readiness_status: str
    reason: str


@dataclass
class ProvinceCoverageReport:
    schema_version: str
    generated_at: str
    evidence_status: str
    source_sha256: str
    boundary_sha256: str
    cause_semantics: str
    cells: List[ProvinceYearCoverage]
    source_schema_version: str = SOURCE_SCHEMA_VERSION
    boundary_schema_version: str = BOUNDARY_SCHEMA_VERSION
    quality_mask_semantics: str = QUALITY_MASK_SEMANTICS
    quality_mask_policy_version: str = QUALITY_MASK_POLICY_VERSION
    equal_area_crs: str = EQUAL_AREA_CRS

    def to_dict(self) -> Dict[str, Any]:
        value = asdict(self)
        value["coverage_states"] = list(COVERAGE_STATES)
        return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _validate_sha(value: str, label: str) -> str:
    normalized = str(value).lower()
    if not _SHA256.fullmatch(normalized):
        raise CoverageEvidenceError(f"{label}_SHA256_INVALID")
    return normalized


def _read_pinned_json(ref: PinnedFile) -> Mapping[str, Any]:
    path = Path(ref.path).resolve()
    expected = _validate_sha(ref.sha256, "PINNED_FILE")
    if not path.is_file():
        raise CoverageEvidenceError(f"PINNED_FILE_MISSING:{path}")
    actual = sha256_file(path)
    if actual != expected:
        raise CoverageEvidenceError(f"SHA256_MISMATCH:{path}:{actual}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CoverageEvidenceError(f"INVALID_JSON:{path}") from exc
    if not isinstance(value, dict):
        raise CoverageEvidenceError(f"JSON_OBJECT_REQUIRED:{path}")
    return value


def _safe_asset(root: Path, raw_path: str) -> Path:
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = root / candidate
    candidate = candidate.resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise CoverageEvidenceError(f"ASSET_OUTSIDE_ROOT:{candidate}") from exc
    if not candidate.is_file():
        raise CoverageEvidenceError(f"ASSET_MISSING:{candidate}")
    return candidate


def _boundary_index(boundary_doc: Mapping[str, Any]) -> Dict[str, Mapping[str, Any]]:
    if boundary_doc.get("type") != "FeatureCollection":
        raise CoverageEvidenceError("BOUNDARY_FEATURE_COLLECTION_REQUIRED")
    if boundary_doc.get("schema_version") != BOUNDARY_SCHEMA_VERSION:
        raise CoverageEvidenceError("BOUNDARY_SCHEMA_VERSION_MISMATCH")
    crs = boundary_doc.get("crs")
    crs_name = ((crs or {}).get("properties") or {}).get("name") if isinstance(crs, dict) else None
    if crs_name not in {"EPSG:4326", "urn:ogc:def:crs:OGC:1.3:CRS84"}:
        raise CoverageEvidenceError("BOUNDARY_CRS_4326_REQUIRED")
    features = boundary_doc.get("features")
    if not isinstance(features, list):
        raise CoverageEvidenceError("BOUNDARY_FEATURES_LIST_REQUIRED")
    result: Dict[str, Mapping[str, Any]] = {}
    for feature in features:
        if not isinstance(feature, dict) or feature.get("type") != "Feature":
            raise CoverageEvidenceError("BOUNDARY_FEATURE_INVALID")
        props, geom = feature.get("properties"), feature.get("geometry")
        pid = props.get("province_id") if isinstance(props, dict) else None
        if not isinstance(pid, str) or not pid or not isinstance(geom, dict):
            raise CoverageEvidenceError("BOUNDARY_ID_AND_GEOMETRY_REQUIRED")
        if pid in result:
            raise CoverageEvidenceError(f"DUPLICATE_BOUNDARY:{pid}")
        parsed = shape(geom)
        if parsed.is_empty or not parsed.is_valid or parsed.geom_type not in {"Polygon", "MultiPolygon"}:
            raise CoverageEvidenceError(f"BOUNDARY_GEOMETRY_INVALID:{pid}")
        result[pid] = geom
    return result


def _equal_area_geometry(geom: Mapping[str, Any]):
    transformer = Transformer.from_crs("EPSG:4326", EQUAL_AREA_CRS, always_xy=True)
    return shapely_transform(transformer.transform, shape(geom))


def _round_ha(square_metres: float) -> float:
    return round(max(0.0, square_metres) / 10000.0, 4)


def _pct(area_ha: float, total_ha: float) -> float:
    return round(100.0 * area_ha / total_ha, 4) if total_ha > 0 else 0.0


def _require_contract(row: Mapping[str, Any], field: str, *, semantics: str, version: str) -> None:
    contract = row.get(field)
    if not isinstance(contract, dict):
        raise CoverageEvidenceError(f"{field.upper()}_REQUIRED")
    if contract.get("semantics") != semantics:
        raise CoverageEvidenceError(f"{field.upper()}_SEMANTICS_MISMATCH")
    if contract.get("version") != version:
        raise CoverageEvidenceError(f"{field.upper()}_VERSION_MISMATCH")
    if "nodata" not in contract or contract["nodata"] is not None:
        raise CoverageEvidenceError(f"{field.upper()}_NODATA_MISMATCH")


def _read_mask(path: Path, *, allowed_values: set[int], label: str):
    with rasterio.open(path) as dataset:
        if dataset.count != 1 or dataset.crs is None or dataset.crs.to_epsg() != 6933:
            raise CoverageEvidenceError(f"{label}_EQUAL_AREA_EPSG6933_REQUIRED:{path}")
        if dataset.transform.b != 0 or dataset.transform.d != 0 or dataset.transform.a <= 0 or dataset.transform.e >= 0:
            raise CoverageEvidenceError(f"{label}_GRID_INVALID:{path}")
        if dataset.nodata is not None:
            raise CoverageEvidenceError(f"{label}_NODATA_MUST_BE_UNSET:{path}")
        values = dataset.read(1)
        actual_values = {int(v) for v in np.unique(values)}
        if not actual_values.issubset(allowed_values):
            raise CoverageEvidenceError(f"{label}_VALUE_DOMAIN_INVALID:{path}:{sorted(actual_values)}")
        return values, dataset.crs, dataset.transform, dataset.bounds, dataset.shape


def measure_province_year_coverage(
    *, root: Path, source: PinnedFile, boundaries: PinnedFile,
    expected_provinces: Sequence[str], expected_years: Sequence[int],
    evidence_status: str = "VERIFIED_REAL",
) -> ProvinceCoverageReport:
    """Measure coverage only from pinned binary masks on EPSG:6933 grids."""
    if evidence_status not in {"VERIFIED_REAL", "TESTED_SYNTHETIC"}:
        raise CoverageEvidenceError("EVIDENCE_STATUS_INVALID")
    if len(set(expected_provinces)) != len(expected_provinces) or len(set(expected_years)) != len(expected_years):
        raise CoverageEvidenceError("EXPECTED_SCOPE_CONTAINS_DUPLICATES")
    root = Path(root).resolve()
    source_doc, boundary_doc = _read_pinned_json(source), _read_pinned_json(boundaries)
    if source_doc.get("schema_version") != SOURCE_SCHEMA_VERSION:
        raise CoverageEvidenceError("SOURCE_SCHEMA_VERSION_MISMATCH")
    boundary_by_id = _boundary_index(boundary_doc)
    expected_keys = {(p, int(y)) for p in expected_provinces for y in expected_years}
    if set(expected_provinces) != set(boundary_by_id):
        raise CoverageEvidenceError("BOUNDARY_SCOPE_MISMATCH")
    rows = source_doc.get("scenes")
    if not isinstance(rows, list):
        raise CoverageEvidenceError("SOURCE_SCENES_LIST_REQUIRED")
    grouped: Dict[Tuple[str, int], List[Mapping[str, Any]]] = {key: [] for key in expected_keys}
    patch_ids: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise CoverageEvidenceError("SOURCE_ROW_OBJECT_REQUIRED")
        try:
            key = (row["province"], int(row["year"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise CoverageEvidenceError("SOURCE_ROW_SCOPE_INVALID") from exc
        if not isinstance(key[0], str) or key not in grouped:
            raise CoverageEvidenceError(f"SOURCE_ROW_OUTSIDE_SCOPE:{key[0]}:{key[1]}")
        patch_id = row.get("patch_id")
        if not isinstance(patch_id, str) or not patch_id:
            raise CoverageEvidenceError("PATCH_ID_REQUIRED")
        if patch_id in patch_ids:
            raise CoverageEvidenceError(f"DUPLICATE_PATCH_ID:{patch_id}")
        patch_ids.add(patch_id)
        if row.get("quality_status") not in ALLOWED_QUALITY_STATUSES:
            raise CoverageEvidenceError(f"QUALITY_STATUS_UNKNOWN:{row.get('quality_status')}")
        grouped[key].append(row)

    cells: List[ProvinceYearCoverage] = []
    any_cause = False
    for province_id in expected_provinces:
        boundary_wgs84 = boundary_by_id[province_id]
        boundary_equal = _equal_area_geometry(boundary_wgs84)
        boundary_area_m2 = float(boundary_equal.area)
        if boundary_area_m2 <= 0:
            raise CoverageEvidenceError(f"EMPTY_BOUNDARY:{province_id}")
        for year in expected_years:
            cell_rows = grouped[(province_id, int(year))]
            footprint_parts = []
            observed_m2 = cloud_m2 = shadow_m2 = nodata_m2 = not_measured_m2 = 0.0
            scene_ids: set[str] = set()
            for row in cell_rows:
                scene_id = row.get("scene_id")
                if not isinstance(scene_id, str) or not scene_id:
                    raise CoverageEvidenceError("SCENE_ID_REQUIRED")
                scene_ids.add(scene_id)
                _require_contract(row, "quality_mask_contract", semantics=QUALITY_MASK_SEMANTICS,
                                  version=QUALITY_MASK_POLICY_VERSION)
                mask_path = _safe_asset(root, str(row.get("quality_mask_path", "")))
                declared = (row.get("patch_sha256") or {}).get("quality")
                if not isinstance(declared, str) or sha256_file(mask_path) != _validate_sha(declared, "QUALITY"):
                    raise CoverageEvidenceError(f"QUALITY_SHA256_MISMATCH:{mask_path}")
                quality, crs, transform, bounds, mask_shape = _read_mask(
                    mask_path, allowed_values={0, 1}, label="QUALITY_RASTER"
                )
                geom_in_crs = transform_geom("EPSG:4326", crs, boundary_wgs84)
                inside = geometry_mask([geom_in_crs], transform=transform, out_shape=mask_shape,
                                       invert=True, all_touched=False)
                pixel_area = abs(transform.a * transform.e)
                observed, invalid = inside & (quality == 1), inside & (quality == 0)
                observed_m2 += float(np.count_nonzero(observed)) * pixel_area
                cause_ref = row.get("coverage_cause_mask")
                if cause_ref is None:
                    not_measured_m2 += float(np.count_nonzero(invalid)) * pixel_area
                else:
                    if not isinstance(cause_ref, dict) or not isinstance(cause_ref.get("sha256"), str):
                        raise CoverageEvidenceError("CAUSE_MASK_PIN_REQUIRED")
                    _require_contract(row, "coverage_cause_contract", semantics=CAUSE_MASK_SEMANTICS,
                                      version=CAUSE_MASK_POLICY_VERSION)
                    cause_path = _safe_asset(root, str(cause_ref.get("path", "")))
                    if sha256_file(cause_path) != _validate_sha(cause_ref["sha256"], "CAUSE"):
                        raise CoverageEvidenceError(f"CAUSE_SHA256_MISMATCH:{cause_path}")
                    cause, cause_crs, cause_transform, _, cause_shape = _read_mask(
                        cause_path, allowed_values={0, 1, 2, 3}, label="CAUSE_RASTER"
                    )
                    if cause_crs != crs or cause_transform != transform or cause_shape != mask_shape:
                        raise CoverageEvidenceError(f"CAUSE_GRID_MISMATCH:{cause_path}")
                    if np.any((~invalid) & (cause != 0)):
                        raise CoverageEvidenceError(f"CAUSE_ASSIGNED_OUTSIDE_INVALID_PIXELS:{cause_path}")
                    cloud_m2 += float(np.count_nonzero(invalid & (cause == 1))) * pixel_area
                    shadow_m2 += float(np.count_nonzero(invalid & (cause == 2))) * pixel_area
                    nodata_m2 += float(np.count_nonzero(invalid & (cause == 3))) * pixel_area
                    not_measured_m2 += float(np.count_nonzero(invalid & (cause == 0))) * pixel_area
                    any_cause = True
                footprint_parts.append(shape({"type": "Polygon", "coordinates": [[
                    [bounds.left, bounds.bottom], [bounds.right, bounds.bottom],
                    [bounds.right, bounds.top], [bounds.left, bounds.top], [bounds.left, bounds.bottom],
                ]]}).intersection(boundary_equal))

            boundary_area_ha = _round_ha(boundary_area_m2)
            if not footprint_parts:
                footprint_area_m2 = observed_m2 = cloud_m2 = shadow_m2 = nodata_m2 = not_measured_m2 = 0.0
                outside_m2 = missing_m2 = boundary_area_m2
                measurement_status, readiness, reason = "NOT_MEASURED", "BLOCKED_NO_VERIFIED_ASSETS", "NO_SCENE"
            else:
                footprint_area_m2 = float(unary_union(footprint_parts).area)
                accounted_inside_m2 = observed_m2 + cloud_m2 + shadow_m2 + nodata_m2 + not_measured_m2
                tolerance = max(1.0, 0.001 * boundary_area_m2)
                if accounted_inside_m2 - footprint_area_m2 > tolerance:
                    raise CoverageEvidenceError(f"OVERLAPPING_FOOTPRINTS_REQUIRE_MOSAIC:{province_id}:{year}")
                outside_m2, missing_m2 = max(0.0, boundary_area_m2 - footprint_area_m2), max(0.0, boundary_area_m2 - observed_m2)
                residual = missing_m2 - outside_m2 - cloud_m2 - shadow_m2 - nodata_m2 - not_measured_m2
                if residual < -tolerance:
                    raise CoverageEvidenceError(f"COVERAGE_ACCOUNTING_OVERFLOW:{province_id}:{year}")
                not_measured_m2 += max(0.0, residual)
                measurement_status = evidence_status
                blockers = []
                if outside_m2 > tolerance: blockers.append("OUTSIDE_FOOTPRINT")
                if cloud_m2 > tolerance: blockers.append("CLOUD")
                if shadow_m2 > tolerance: blockers.append("SHADOW")
                if nodata_m2 > tolerance: blockers.append("NODATA")
                if not_measured_m2 > tolerance: blockers.append("NOT_MEASURED")
                if blockers:
                    readiness, reason = "BLOCKED_" + "_AND_".join(blockers), "INCOMPLETE_OR_INVALID_AREA_REMAINS"
                elif abs(observed_m2 - boundary_area_m2) > tolerance:
                    readiness, reason = "BLOCKED_BOUNDARY_NOT_FULLY_OBSERVED", "OBSERVED_MASK_DOES_NOT_COVER_BOUNDARY"
                else:
                    readiness, reason = "COVERAGE_COMPLETE", "BOUNDARY_FULLY_OBSERVED_WITH_ZERO_INVALID_AND_OUTSIDE_AREA"

            observed_ha, missing_ha = _round_ha(observed_m2), _round_ha(missing_m2)
            cells.append(ProvinceYearCoverage(
                province_id, int(year), boundary_area_ha, len(cell_rows), len(scene_ids),
                _round_ha(footprint_area_m2), observed_ha, missing_ha,
                _round_ha(cloud_m2), _round_ha(shadow_m2), _round_ha(nodata_m2),
                _round_ha(outside_m2), _round_ha(not_measured_m2),
                _pct(observed_ha, boundary_area_ha), _pct(missing_ha, boundary_area_ha),
                measurement_status, readiness, reason,
            ))

    return ProvinceCoverageReport(
        COVERAGE_REPORT_SCHEMA_VERSION, datetime.now(timezone.utc).isoformat(), evidence_status,
        source.sha256.lower(), boundaries.sha256.lower(),
        CAUSE_MASK_SEMANTICS if any_cause else "QUALITY_MASK_ONLY_INVALID_CAUSE_IS_NOT_MEASURED",
        cells,
    )
