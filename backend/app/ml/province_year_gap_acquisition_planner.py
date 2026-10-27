"""Fail-closed province-year gap acquisition planning.

This module only produces a deterministic, non-executing plan.  It never calls
collectors, remote services, ledgers, or execution locks.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple
from urllib.parse import urlparse

import numpy as np
import rasterio
from rasterio.features import geometry_mask, shapes
from rasterio.warp import transform_geom
from shapely.geometry import mapping, shape

from .province_year_coverage import PinnedFile, sha256_file


PLAN_SCHEMA_VERSION = "province-year-gap-acquisition-plan/1.2"
SOURCE_SCHEMA_VERSION = "province-year-gap-acquisition-source/1.0"
BOUNDARY_SCHEMA_VERSION = "province-boundaries/1.0"
BOUNDARY_CANDIDATE_SCHEMA_VERSION = "province-boundary-candidate/1.0"
GISTARU_REFERENCE_SCHEMA_VERSION = "gistaru-boundary-reference/1.0"
CROSS_CHECK_DECISION_SCHEMA_VERSION = "spatial-plan-cross-check-decision/1.0"
MOSAIC_MANIFEST_SCHEMA_VERSION = "province-year-scl-mosaic-manifest/1.0"
SENTINEL_PROVENANCE_SCHEMA_VERSION = "sentinel-2-observation-provenance/1.0"
ESRI_PROVENANCE_SCHEMA_VERSION = "esri-weak-label-provenance/1.0"
OBSERVED_MASK_SEMANTICS = "BINARY_OBSERVED_0_1"
OBSERVED_MASK_POLICY_VERSION = "quality-mask/1.0"
CAUSE_MASK_SEMANTICS = "0_NONE_1_CLOUD_2_SHADOW_3_NODATA_4_OUTSIDE_FOOTPRINT"
CAUSE_MASK_POLICY_VERSION = "acquisition-gap-cause-mask/1.0"
EQUAL_AREA_CRS = "EPSG:6933"
PROVINCES = (
    "banten", "west_java", "east_java", "south_sulawesi", "gorontalo",
    "southeast_sulawesi",
)
YEARS = tuple(range(2020, 2026))
ROLE_CONTRACT = {
    "authoritative_boundary": "STATISTICAL_AOI_ONLY",
    "gistaru": "BOUNDARY_CROSS_CHECK_ONLY",
    "esri": "WEAK_LABEL_ONLY",
    "sentinel2": "OBSERVATION_AND_CAUSE_MASK_SOURCE",
}
CAUSE_NAMES = {1: "CLOUD", 2: "SHADOW", 3: "NODATA", 4: "OUTSIDE_FOOTPRINT"}
CAUSE_PRIORITY = {4: 1, 3: 2, 1: 3, 2: 4}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class GapPlanningEvidenceError(ValueError):
    """Raised when evidence is insufficient to create any acquisition target."""


@dataclass(frozen=True)
class GapTarget:
    target_id: str
    province_id: str
    year: int
    gap_cause: str
    priority: int
    area_ha: float
    pixel_count: int
    geometry_wgs84: Dict[str, Any]
    bbox_wgs84: List[float]
    acquisition_source: str = "SENTINEL_2_L2A"
    action: str = "PLAN_CANDIDATE_ONLY"
    remote_request_created: bool = False


@dataclass(frozen=True)
class GapCellSummary:
    province_id: str
    year: int
    total_boundary_pixels: int
    observed_pixels: int
    gap_pixels: int
    observed_pct: float
    gap_pct: float
    cause_pixels: Dict[str, int]
    target_count: int


@dataclass(frozen=True)
class MLOpsGate:
    gate_id: str
    status: str
    evidence_status: str
    required_input: str
    blocker: Optional[str]


@dataclass(frozen=True)
class MLOpsHandoff:
    status: str
    retraining_ready: bool
    immutable_dataset_pin: Optional[Dict[str, str]]
    required_gates: List[MLOpsGate]
    blockers: List[str]


@dataclass(frozen=True)
class GapAcquisitionPlan:
    schema_version: str
    generated_at: str
    evidence_status: str
    planning_status: str
    execution_authorized: bool
    collector_invoked: bool
    ledger_written: bool
    execution_lock_acquired: bool
    remote_downloads_performed: bool
    boundary_sha256: str
    gistaru_reference_sha256: Optional[str]
    cross_check_decision_sha256: Optional[str]
    cross_check_status: str
    source_sha256: str
    roles: Dict[str, str]
    target_count: int
    cells: List[GapCellSummary]
    targets: List[GapTarget]
    mlops_handoff: MLOpsHandoff

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _validate_sha(value: Any, label: str) -> str:
    normalized = str(value).lower()
    if not _SHA256.fullmatch(normalized):
        raise GapPlanningEvidenceError(f"{label}_SHA256_INVALID")
    return normalized


def _inside_root(root: Path, path: Path, label: str) -> Path:
    root = root.resolve()
    raw_candidate = path if path.is_absolute() else root / path
    if raw_candidate.is_symlink():
        raise GapPlanningEvidenceError(f"{label}_REGULAR_FILE_REQUIRED")
    try:
        candidate = raw_candidate.resolve(strict=True)
    except OSError as exc:
        raise GapPlanningEvidenceError(f"{label}_FILE_MISSING") from exc
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise GapPlanningEvidenceError(f"{label}_OUTSIDE_ROOT") from exc
    if not candidate.is_file():
        raise GapPlanningEvidenceError(f"{label}_REGULAR_FILE_REQUIRED")
    return candidate


def _load_pinned_json(root: Path, ref: PinnedFile, label: str) -> Tuple[Path, Dict[str, Any], str]:
    path = _inside_root(root, Path(ref.path), label)
    expected = _validate_sha(ref.sha256, label)
    actual = sha256_file(path)
    if actual != expected:
        raise GapPlanningEvidenceError(f"{label}_SHA256_MISMATCH:{actual}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GapPlanningEvidenceError(f"{label}_JSON_INVALID") from exc
    if not isinstance(value, dict):
        raise GapPlanningEvidenceError(f"{label}_OBJECT_REQUIRED")
    return path, value, actual


def _require_https(url: Any, label: str, *, host: Optional[str] = None) -> str:
    parsed = urlparse(str(url))
    if parsed.scheme != "https" or not parsed.netloc:
        raise GapPlanningEvidenceError(f"{label}_HTTPS_URL_REQUIRED")
    if host is not None and parsed.hostname != host:
        raise GapPlanningEvidenceError(f"{label}_HOST_MISMATCH")
    return str(url)


def _require_iso_date(value: Any, label: str) -> str:
    text = str(value)
    try:
        datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise GapPlanningEvidenceError(f"{label}_ISO8601_REQUIRED") from exc
    return text


def _validate_boundaries(doc: Mapping[str, Any], expected_provinces: Sequence[str],
                         evidence_status: str) -> Dict[str, Mapping[str, Any]]:
    if doc.get("schema_version") != BOUNDARY_SCHEMA_VERSION:
        raise GapPlanningEvidenceError("BOUNDARY_SCHEMA_VERSION_MISMATCH")
    crs_name = (((doc.get("crs") or {}).get("properties") or {}).get("name"))
    if crs_name != "EPSG:4326":
        raise GapPlanningEvidenceError("BOUNDARY_CRS_4326_REQUIRED")
    if doc.get("evidence_status") != evidence_status:
        raise GapPlanningEvidenceError("BOUNDARY_EVIDENCE_STATUS_MISMATCH")
    authority = doc.get("authority")
    if not isinstance(authority, dict):
        raise GapPlanningEvidenceError("BOUNDARY_AUTHORITY_REQUIRED")
    if authority.get("legal_status") != "AUTHORITATIVE_ADMINISTRATIVE_BOUNDARY":
        raise GapPlanningEvidenceError("BOUNDARY_NOT_AUTHORITATIVE")
    if authority.get("approved_for_statistics") is not True:
        raise GapPlanningEvidenceError("BOUNDARY_NOT_APPROVED_FOR_STATISTICS")
    for key in ("organization", "publication_id"):
        if not isinstance(authority.get(key), str) or not authority[key].strip():
            raise GapPlanningEvidenceError(f"BOUNDARY_AUTHORITY_{key.upper()}_REQUIRED")
    _require_iso_date(authority.get("effective_date"), "BOUNDARY_EFFECTIVE_DATE")
    _require_https(authority.get("source_url"), "BOUNDARY_SOURCE")

    features = doc.get("features")
    if not isinstance(features, list):
        raise GapPlanningEvidenceError("BOUNDARY_FEATURES_REQUIRED")
    result: Dict[str, Mapping[str, Any]] = {}
    for feature in features:
        if not isinstance(feature, dict):
            raise GapPlanningEvidenceError("BOUNDARY_FEATURE_OBJECT_REQUIRED")
        province_id = (feature.get("properties") or {}).get("province_id")
        if province_id in result:
            raise GapPlanningEvidenceError(f"BOUNDARY_DUPLICATE_PROVINCE:{province_id}")
        if province_id not in expected_provinces:
            raise GapPlanningEvidenceError(f"BOUNDARY_PROVINCE_OUTSIDE_SCOPE:{province_id}")
        try:
            geom = shape(feature.get("geometry"))
        except Exception as exc:
            raise GapPlanningEvidenceError(f"BOUNDARY_GEOMETRY_INVALID:{province_id}") from exc
        if geom.is_empty or not geom.is_valid or geom.geom_type not in {"Polygon", "MultiPolygon"}:
            raise GapPlanningEvidenceError(f"BOUNDARY_GEOMETRY_INVALID:{province_id}")
        result[str(province_id)] = feature
    if set(result) != set(expected_provinces):
        raise GapPlanningEvidenceError("BOUNDARY_EXACT_PROVINCE_SCOPE_REQUIRED")
    return result


def _validate_provisional_boundaries(
    doc: Mapping[str, Any], expected_provinces: Sequence[str]
) -> Dict[str, Mapping[str, Any]]:
    """Accept the pinned BIG public candidate only for an explicitly limited pilot."""
    if doc.get("schema_version") != BOUNDARY_CANDIDATE_SCHEMA_VERSION:
        raise GapPlanningEvidenceError("PROVISIONAL_BOUNDARY_SCHEMA_VERSION_MISMATCH")
    if doc.get("evidence_status") != "IMPLEMENTED_UNVERIFIED":
        raise GapPlanningEvidenceError("PROVISIONAL_BOUNDARY_EVIDENCE_STATUS_MISMATCH")
    if doc.get("status") != "CANDIDATE_PENDING_COMPETENT_AUTHORITY_AND_STATISTICAL_APPROVAL":
        raise GapPlanningEvidenceError("PROVISIONAL_BOUNDARY_STATUS_MISMATCH")
    crs_name = (((doc.get("crs") or {}).get("properties") or {}).get("name"))
    if crs_name != "EPSG:4326":
        raise GapPlanningEvidenceError("PROVISIONAL_BOUNDARY_CRS_4326_REQUIRED")
    authority = doc.get("authority")
    if not isinstance(authority, dict):
        raise GapPlanningEvidenceError("PROVISIONAL_BOUNDARY_AUTHORITY_REQUIRED")
    if (
        authority.get("organization") != "Badan Informasi Geospasial (BIG)"
        or authority.get("official_public_service") is not True
        or authority.get("layer_id") != 12
        or authority.get("approved_for_project_statistics") is not False
    ):
        raise GapPlanningEvidenceError("PROVISIONAL_BOUNDARY_BIG_LAYER12_CONTRACT_MISMATCH")
    _require_https(authority.get("source_url"), "PROVISIONAL_BOUNDARY_SOURCE", host="geoservices.big.go.id")
    features = doc.get("features")
    if not isinstance(features, list):
        raise GapPlanningEvidenceError("PROVISIONAL_BOUNDARY_FEATURES_REQUIRED")
    result: Dict[str, Mapping[str, Any]] = {}
    for feature in features:
        if not isinstance(feature, dict):
            raise GapPlanningEvidenceError("PROVISIONAL_BOUNDARY_FEATURE_OBJECT_REQUIRED")
        province_id = (feature.get("properties") or {}).get("province_id")
        if province_id in result:
            raise GapPlanningEvidenceError(f"PROVISIONAL_BOUNDARY_DUPLICATE_PROVINCE:{province_id}")
        if province_id not in expected_provinces:
            raise GapPlanningEvidenceError(f"PROVISIONAL_BOUNDARY_PROVINCE_OUTSIDE_SCOPE:{province_id}")
        try:
            geom = shape(feature.get("geometry"))
        except Exception as exc:
            raise GapPlanningEvidenceError(f"PROVISIONAL_BOUNDARY_GEOMETRY_INVALID:{province_id}") from exc
        if geom.is_empty or not geom.is_valid or geom.geom_type not in {"Polygon", "MultiPolygon"}:
            raise GapPlanningEvidenceError(f"PROVISIONAL_BOUNDARY_GEOMETRY_INVALID:{province_id}")
        result[str(province_id)] = feature
    if set(result) != set(expected_provinces):
        raise GapPlanningEvidenceError("PROVISIONAL_BOUNDARY_EXACT_PROVINCE_SCOPE_REQUIRED")
    return result


def _validate_cross_check_decision(doc: Mapping[str, Any], boundary_sha: str) -> None:
    if doc.get("schema_version") != CROSS_CHECK_DECISION_SCHEMA_VERSION:
        raise GapPlanningEvidenceError("CROSS_CHECK_DECISION_SCHEMA_VERSION_MISMATCH")
    if doc.get("decision") != "SKIP_GISTARU_BY_USER_DECISION":
        raise GapPlanningEvidenceError("CROSS_CHECK_DECISION_NOT_EXPLICIT")
    if doc.get("scope") != "PROVISIONAL_SENTINEL_PILOT_ONLY":
        raise GapPlanningEvidenceError("CROSS_CHECK_DECISION_SCOPE_MISMATCH")
    if doc.get("authorized_by") != "USER_EXPLICIT_INSTRUCTION":
        raise GapPlanningEvidenceError("CROSS_CHECK_DECISION_AUTHORITY_MISMATCH")
    if doc.get("risk_acknowledged") is not True:
        raise GapPlanningEvidenceError("CROSS_CHECK_DECISION_RISK_ACKNOWLEDGEMENT_REQUIRED")
    _require_iso_date(doc.get("recorded_at"), "CROSS_CHECK_DECISION_RECORDED_AT")
    if _validate_sha(doc.get("boundary_sha256"), "CROSS_CHECK_BOUNDARY") != boundary_sha:
        raise GapPlanningEvidenceError("CROSS_CHECK_DECISION_BOUNDARY_SHA256_MISMATCH")
    blockers = doc.get("remaining_blockers")
    required = {"BOUNDARY_APPROVAL_PENDING", "NOT_AUTHORIZED_FOR_TRAINING_OR_DEPLOYMENT"}
    if not isinstance(blockers, list) or not required.issubset(set(blockers)):
        raise GapPlanningEvidenceError("CROSS_CHECK_DECISION_REMAINING_BLOCKERS_REQUIRED")


def _provisional_source_rows(
    root: Path, source_path: Path, doc: Mapping[str, Any], boundary_sha: str
) -> List[Mapping[str, Any]]:
    if doc.get("schema_version") != MOSAIC_MANIFEST_SCHEMA_VERSION:
        raise GapPlanningEvidenceError("PROVISIONAL_SOURCE_MOSAIC_SCHEMA_MISMATCH")
    if doc.get("evidence_status") != "IMPLEMENTED_UNVERIFIED":
        raise GapPlanningEvidenceError("PROVISIONAL_SOURCE_EVIDENCE_STATUS_MISMATCH")
    boundary = doc.get("boundary")
    if not isinstance(boundary, dict) or _validate_sha(
        boundary.get("sha256"), "PROVISIONAL_SOURCE_BOUNDARY"
    ) != boundary_sha:
        raise GapPlanningEvidenceError("PROVISIONAL_SOURCE_BOUNDARY_SHA256_MISMATCH")
    assets = doc.get("source_assets")
    if not isinstance(assets, list) or not assets:
        raise GapPlanningEvidenceError("PROVISIONAL_SOURCE_ASSETS_REQUIRED")
    seen_assets = set()
    for asset in assets:
        if not isinstance(asset, dict):
            raise GapPlanningEvidenceError("PROVISIONAL_SOURCE_ASSET_OBJECT_REQUIRED")
        path = _inside_root(root, Path(str(asset.get("path", ""))), "PROVISIONAL_SOURCE_ASSET")
        if path in seen_assets:
            raise GapPlanningEvidenceError("PROVISIONAL_SOURCE_ASSET_DUPLICATE")
        seen_assets.add(path)
        if sha256_file(path) != _validate_sha(asset.get("sha256"), "PROVISIONAL_SOURCE_ASSET"):
            raise GapPlanningEvidenceError("PROVISIONAL_SOURCE_ASSET_SHA256_MISMATCH")
    rows = doc.get("cells")
    if not isinstance(rows, list):
        raise GapPlanningEvidenceError("PROVISIONAL_SOURCE_CELLS_LIST_REQUIRED")
    normalized: List[Mapping[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            raise GapPlanningEvidenceError("PROVISIONAL_SOURCE_CELL_OBJECT_REQUIRED")
        observed_path = (source_path.parent / str(row.get("observed_path", ""))).resolve()
        cause_path = (source_path.parent / str(row.get("cause_path", ""))).resolve()
        normalized.append({
            "province_id": row.get("province_id"),
            "year": row.get("year"),
            "observed_mosaic": {"path": str(observed_path), "sha256": row.get("observed_sha256")},
            "observed_contract": {
                "semantics": OBSERVED_MASK_SEMANTICS, "version": OBSERVED_MASK_POLICY_VERSION, "nodata": None,
            },
            "cause_mosaic": {"path": str(cause_path), "sha256": row.get("cause_sha256")},
            "cause_contract": {
                "semantics": CAUSE_MASK_SEMANTICS, "version": CAUSE_MASK_POLICY_VERSION, "nodata": None,
            },
        })
    return normalized


def _validate_gistaru(root: Path, doc: Mapping[str, Any], boundary_sha: str,
                      evidence_status: str) -> None:
    if doc.get("schema_version") != GISTARU_REFERENCE_SCHEMA_VERSION:
        raise GapPlanningEvidenceError("GISTARU_REFERENCE_SCHEMA_VERSION_MISMATCH")
    if doc.get("role") != ROLE_CONTRACT["gistaru"]:
        raise GapPlanningEvidenceError("GISTARU_ROLE_MISMATCH")
    if doc.get("evidence_status") != evidence_status:
        raise GapPlanningEvidenceError("GISTARU_EVIDENCE_STATUS_MISMATCH")
    _require_https(doc.get("portal_url"), "GISTARU_PORTAL", host="gistaru.atrbpn.go.id")
    _require_iso_date(doc.get("checked_at"), "GISTARU_CHECKED_AT")
    service_url = _require_https(
        doc.get("service_url"), "GISTARU_SERVICE", host="gistaru.atrbpn.go.id"
    )
    if "/arcgis/rest/services/" not in service_url or not service_url.rstrip("/").endswith("MapServer"):
        raise GapPlanningEvidenceError("GISTARU_MAPSERVER_URL_REQUIRED")
    layer_id = doc.get("layer_id")
    if type(layer_id) is not int or layer_id < 0:
        raise GapPlanningEvidenceError("GISTARU_LAYER_ID_REQUIRED")
    if not isinstance(doc.get("layer_name"), str) or not doc["layer_name"].strip():
        raise GapPlanningEvidenceError("GISTARU_LAYER_NAME_REQUIRED")
    if not isinstance(doc.get("query_where"), str) or not doc["query_where"].strip():
        raise GapPlanningEvidenceError("GISTARU_QUERY_WHERE_REQUIRED")
    if doc.get("out_sr") != 4326:
        raise GapPlanningEvidenceError("GISTARU_OUT_SR_4326_REQUIRED")
    _require_iso_date(doc.get("retrieved_at"), "GISTARU_RETRIEVED_AT")
    if _validate_sha(doc.get("boundary_sha256"), "GISTARU_BOUNDARY") != boundary_sha:
        raise GapPlanningEvidenceError("GISTARU_BOUNDARY_SHA256_MISMATCH")
    if doc.get("comparison_status") not in {"VERIFIED_MATCH", "DISCREPANCY_ADJUDICATED"}:
        raise GapPlanningEvidenceError("GISTARU_COMPARISON_NOT_VERIFIED")
    for field, label in (
        ("service_metadata_evidence", "GISTARU_SERVICE_METADATA_EVIDENCE"),
        ("comparison_evidence", "GISTARU_COMPARISON_EVIDENCE"),
    ):
        evidence = doc.get(field)
        if not isinstance(evidence, dict):
            raise GapPlanningEvidenceError(f"{label}_REQUIRED")
        path = _inside_root(root, Path(str(evidence.get("path", ""))), label)
        if sha256_file(path) != _validate_sha(evidence.get("sha256"), label):
            raise GapPlanningEvidenceError(f"{label}_SHA256_MISMATCH")


def _validate_roles(doc: Mapping[str, Any]) -> None:
    roles = doc.get("roles")
    if roles != ROLE_CONTRACT:
        raise GapPlanningEvidenceError("EVIDENCE_ROLE_CONTRACT_MISMATCH")
    if doc.get("esri_used_for_gap_detection") is not False:
        raise GapPlanningEvidenceError("ESRI_WEAK_LABEL_CANNOT_DEFINE_GAPS")
    if doc.get("esri_used_for_boundary") is not False:
        raise GapPlanningEvidenceError("ESRI_WEAK_LABEL_CANNOT_DEFINE_BOUNDARY")
    if doc.get("sentinel2_used_for_gap_detection") is not True:
        raise GapPlanningEvidenceError("SENTINEL2_GAP_EVIDENCE_REQUIRED")


def _validate_support_manifest(root: Path, value: Any, label: str, expected_role: str,
                               expected_schema: str, evidence_status: str) -> None:
    if not isinstance(value, dict):
        raise GapPlanningEvidenceError(f"{label}_REFERENCE_REQUIRED")
    path = _inside_root(root, Path(str(value.get("path", ""))), label)
    if sha256_file(path) != _validate_sha(value.get("sha256"), label):
        raise GapPlanningEvidenceError(f"{label}_SHA256_MISMATCH")
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GapPlanningEvidenceError(f"{label}_JSON_INVALID") from exc
    if not isinstance(doc, dict) or doc.get("role") != expected_role:
        raise GapPlanningEvidenceError(f"{label}_ROLE_MISMATCH")
    if doc.get("schema_version") != expected_schema:
        raise GapPlanningEvidenceError(f"{label}_SCHEMA_VERSION_MISMATCH")
    if doc.get("evidence_status") != evidence_status:
        raise GapPlanningEvidenceError(f"{label}_EVIDENCE_STATUS_MISMATCH")
    if expected_role == ROLE_CONTRACT["sentinel2"]:
        if doc.get("collection") != "sentinel-2-l2a" or doc.get("scl_used_for_cause") is not True:
            raise GapPlanningEvidenceError("SENTINEL2_SOURCE_CONTRACT_MISMATCH")
        if evidence_status == "VERIFIED_REAL" and doc.get("observations_verified") is not True:
            raise GapPlanningEvidenceError("SENTINEL2_OBSERVATIONS_NOT_VERIFIED")
        if evidence_status == "TESTED_SYNTHETIC" and doc.get("fixture_only") is not True:
            raise GapPlanningEvidenceError("SENTINEL2_SYNTHETIC_FIXTURE_MARKER_REQUIRED")
    elif expected_role == ROLE_CONTRACT["esri"]:
        if doc.get("used_for_gap_detection") is not False or doc.get("used_as_independent_ground_truth") is not False:
            raise GapPlanningEvidenceError("ESRI_WEAK_LABEL_ROLE_VIOLATION")


def _mask_ref(root: Path, row: Mapping[str, Any], field: str, contract_field: str,
              semantics: str, version: str) -> Tuple[Path, str]:
    value = row.get(field)
    contract = row.get(contract_field)
    if not isinstance(value, dict):
        raise GapPlanningEvidenceError(f"{field.upper()}_REFERENCE_REQUIRED")
    if not isinstance(contract, dict):
        raise GapPlanningEvidenceError(f"{contract_field.upper()}_REQUIRED")
    if contract != {"semantics": semantics, "version": version, "nodata": None}:
        raise GapPlanningEvidenceError(f"{contract_field.upper()}_MISMATCH")
    path = _inside_root(root, Path(str(value.get("path", ""))), field.upper())
    expected = _validate_sha(value.get("sha256"), field.upper())
    if sha256_file(path) != expected:
        raise GapPlanningEvidenceError(f"{field.upper()}_SHA256_MISMATCH")
    return path, expected


def _read_mask(path: Path, allowed: Iterable[int], label: str):
    with rasterio.open(path) as ds:
        if ds.count != 1 or ds.crs is None or ds.crs.to_string() != EQUAL_AREA_CRS:
            raise GapPlanningEvidenceError(f"{label}_SINGLE_BAND_EPSG6933_REQUIRED")
        if ds.nodata is not None:
            raise GapPlanningEvidenceError(f"{label}_NODATA_MUST_BE_UNSET")
        if ds.transform.b != 0 or ds.transform.d != 0 or ds.transform.a <= 0 or ds.transform.e >= 0:
            raise GapPlanningEvidenceError(f"{label}_AXIS_ALIGNED_GRID_REQUIRED")
        array = ds.read(1)
        values = set(int(v) for v in np.unique(array))
        if not values.issubset(set(allowed)):
            raise GapPlanningEvidenceError(f"{label}_VALUE_DOMAIN_INVALID:{sorted(values)}")
        return array, ds.crs, ds.transform, (ds.height, ds.width)


def _target_id(province_id: str, year: int, cause: str, geometry: Mapping[str, Any]) -> str:
    canonical = json.dumps(geometry, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(f"{province_id}|{year}|{cause}|{canonical}".encode("utf-8")).hexdigest()[:20]
    return f"{province_id}-{year}-{cause.lower()}-{digest}"


def _targets_for_cell(province_id: str, year: int, cause: np.ndarray, gap: np.ndarray,
                      transform: Any, pixel_area_m2: float) -> List[GapTarget]:
    targets: List[GapTarget] = []
    for geometry, raw_value in shapes(cause.astype("uint8"), mask=gap, transform=transform, connectivity=8):
        cause_value = int(raw_value)
        cause_name = CAUSE_NAMES[cause_value]
        component = geometry_mask([geometry], out_shape=cause.shape, transform=transform, invert=True)
        pixel_count = int(np.count_nonzero(component & gap & (cause == cause_value)))
        geometry_wgs84 = transform_geom(EQUAL_AREA_CRS, "EPSG:4326", geometry, precision=9)
        bounds = shape(geometry_wgs84).bounds
        targets.append(GapTarget(
            _target_id(province_id, year, cause_name, geometry_wgs84), province_id, year,
            cause_name, CAUSE_PRIORITY[cause_value], round(pixel_count * pixel_area_m2 / 10000.0, 6),
            pixel_count, geometry_wgs84, [round(float(v), 9) for v in bounds],
        ))
    return sorted(targets, key=lambda t: (t.priority, t.target_id))


def _mlops_handoff(evidence_status: str) -> MLOpsHandoff:
    evidence_gate_status = "PASSED" if evidence_status == "VERIFIED_REAL" else "TESTED_SYNTHETIC"
    blockers = [
        "ACQUISITION_NOT_EXECUTED",
        "ACQUISITION_QUALITY_QA_NOT_COMPLETED",
        "IMMUTABLE_DATASET_NOT_PINNED",
        "RETRAINING_NOT_READY",
    ]
    if evidence_status == "PROVISIONAL_REAL":
        blockers.insert(0, "BOUNDARY_APPROVAL_PENDING")
    elif evidence_status != "VERIFIED_REAL":
        blockers.insert(0, "SYNTHETIC_INPUT_NOT_OPERATIONAL_EVIDENCE")
    gates = [
        MLOpsGate(
            "coverage_boundary_cause_evidence", evidence_gate_status, evidence_status,
            "authoritative boundary plus pinned same-grid observed/cause mosaics",
            None if evidence_status == "VERIFIED_REAL" else (
                "BOUNDARY_APPROVAL_PENDING" if evidence_status == "PROVISIONAL_REAL"
                else "SYNTHETIC_INPUT_NOT_OPERATIONAL_EVIDENCE"
            ),
        ),
        MLOpsGate(
            "acquisition_execution", "BLOCKED", "NOT_EXECUTED",
            "approved collector execution manifest with downloaded asset hashes",
            "ACQUISITION_NOT_EXECUTED",
        ),
        MLOpsGate(
            "acquisition_quality_qa", "BLOCKED", "NOT_MEASURED",
            "independent coverage, SCL, grid, nodata, and source-lineage QA",
            "ACQUISITION_QUALITY_QA_NOT_COMPLETED",
        ),
        MLOpsGate(
            "immutable_dataset_pin", "BLOCKED", "NOT_AVAILABLE",
            "immutable dataset manifest pinning every accepted asset and split",
            "IMMUTABLE_DATASET_NOT_PINNED",
        ),
        MLOpsGate(
            "retraining_readiness", "BLOCKED", "NOT_READY",
            "all predecessor gates passed plus explicit training authorization",
            "RETRAINING_NOT_READY",
        ),
    ]
    return MLOpsHandoff("BLOCKED_PENDING_ACQUISITION_AND_DATASET_PIN", False, None, gates, blockers)


def build_gap_acquisition_plan(
    *,
    root: Path,
    source: PinnedFile,
    boundaries: PinnedFile,
    gistaru_reference: Optional[PinnedFile] = None,
    cross_check_decision: Optional[PinnedFile] = None,
    expected_provinces: Sequence[str] = PROVINCES,
    expected_years: Sequence[int] = YEARS,
    evidence_status: str = "VERIFIED_REAL",
) -> GapAcquisitionPlan:
    """Validate all evidence before returning any non-executing acquisition targets."""
    root = Path(root).resolve()
    if evidence_status not in {"VERIFIED_REAL", "TESTED_SYNTHETIC", "PROVISIONAL_REAL"}:
        raise GapPlanningEvidenceError("EVIDENCE_STATUS_INVALID")
    if tuple(expected_provinces) != PROVINCES or tuple(expected_years) != YEARS:
        raise GapPlanningEvidenceError("EXACT_SIX_PROVINCE_SIX_YEAR_SCOPE_REQUIRED")

    _, boundary_doc, boundary_sha = _load_pinned_json(root, boundaries, "BOUNDARY")
    gistaru_sha: Optional[str] = None
    decision_sha: Optional[str] = None
    if evidence_status == "PROVISIONAL_REAL":
        boundary_index = _validate_provisional_boundaries(boundary_doc, expected_provinces)
        if gistaru_reference is not None or cross_check_decision is None:
            raise GapPlanningEvidenceError("PROVISIONAL_CROSS_CHECK_DECISION_REQUIRED")
        _, decision_doc, decision_sha = _load_pinned_json(
            root, cross_check_decision, "CROSS_CHECK_DECISION"
        )
        _validate_cross_check_decision(decision_doc, boundary_sha)
        source_path, source_doc, source_sha = _load_pinned_json(root, source, "SOURCE")
        rows = _provisional_source_rows(root, source_path, source_doc, boundary_sha)
        roles = dict(ROLE_CONTRACT)
        roles["gistaru"] = "SKIPPED_BY_USER_DECISION_FOR_PROVISIONAL_PILOT"
        cross_check_status = "SKIPPED_BY_USER_DECISION"
    else:
        boundary_index = _validate_boundaries(boundary_doc, expected_provinces, evidence_status)
        if gistaru_reference is None or cross_check_decision is not None:
            raise GapPlanningEvidenceError("GISTARU_REFERENCE_REQUIRED")
        _, gistaru_doc, gistaru_sha = _load_pinned_json(root, gistaru_reference, "GISTARU_REFERENCE")
        _validate_gistaru(root, gistaru_doc, boundary_sha, evidence_status)
        _, source_doc, source_sha = _load_pinned_json(root, source, "SOURCE")
        if source_doc.get("schema_version") != SOURCE_SCHEMA_VERSION:
            raise GapPlanningEvidenceError("SOURCE_SCHEMA_VERSION_MISMATCH")
        if source_doc.get("evidence_status") != evidence_status:
            raise GapPlanningEvidenceError("SOURCE_EVIDENCE_STATUS_MISMATCH")
        if _validate_sha(source_doc.get("boundary_sha256"), "SOURCE_BOUNDARY") != boundary_sha:
            raise GapPlanningEvidenceError("SOURCE_BOUNDARY_SHA256_MISMATCH")
        if _validate_sha(source_doc.get("gistaru_reference_sha256"), "SOURCE_GISTARU") != gistaru_sha:
            raise GapPlanningEvidenceError("SOURCE_GISTARU_SHA256_MISMATCH")
        _validate_roles(source_doc)
        _validate_support_manifest(root, source_doc.get("sentinel2_source_manifest"),
                                   "SENTINEL2_SOURCE_MANIFEST", ROLE_CONTRACT["sentinel2"],
                                   SENTINEL_PROVENANCE_SCHEMA_VERSION, evidence_status)
        _validate_support_manifest(root, source_doc.get("esri_weak_label_manifest"),
                                   "ESRI_WEAK_LABEL_MANIFEST", ROLE_CONTRACT["esri"],
                                   ESRI_PROVENANCE_SCHEMA_VERSION, evidence_status)
        rows = source_doc.get("cells")
        roles = dict(ROLE_CONTRACT)
        cross_check_status = "VERIFIED_GISTARU"
    if not isinstance(rows, list):
        raise GapPlanningEvidenceError("SOURCE_CELLS_LIST_REQUIRED")
    by_cell: Dict[Tuple[str, int], Mapping[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise GapPlanningEvidenceError("SOURCE_CELL_OBJECT_REQUIRED")
        try:
            key = (str(row["province_id"]), int(row["year"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise GapPlanningEvidenceError("SOURCE_CELL_ID_INVALID") from exc
        if key in by_cell:
            raise GapPlanningEvidenceError(f"SOURCE_CELL_DUPLICATE:{key[0]}:{key[1]}")
        by_cell[key] = row
    expected = {(p, int(y)) for p in expected_provinces for y in expected_years}
    if set(by_cell) != expected:
        raise GapPlanningEvidenceError("SOURCE_EXACT_36_CELL_SCOPE_REQUIRED")

    # Validate every file and grid first.  No target exists until this pass completes.
    validated = []
    for key in sorted(expected):
        row = by_cell[key]
        observed_path, _ = _mask_ref(root, row, "observed_mosaic", "observed_contract",
                                     OBSERVED_MASK_SEMANTICS, OBSERVED_MASK_POLICY_VERSION)
        cause_path, _ = _mask_ref(root, row, "cause_mosaic", "cause_contract",
                                  CAUSE_MASK_SEMANTICS, CAUSE_MASK_POLICY_VERSION)
        observed, crs, transform, dimensions = _read_mask(observed_path, {0, 1}, "OBSERVED_MOSAIC")
        cause, cause_crs, cause_transform, cause_dimensions = _read_mask(cause_path, set(range(5)), "CAUSE_MOSAIC")
        if cause_crs != crs or cause_transform != transform or cause_dimensions != dimensions:
            raise GapPlanningEvidenceError(f"SAME_GRID_MOSAICS_REQUIRED:{key[0]}:{key[1]}")
        boundary_wgs84 = boundary_index[key[0]]["geometry"]
        boundary_equal_shape = shape(
            transform_geom("EPSG:4326", EQUAL_AREA_CRS, boundary_wgs84, precision=9)
        )
        if not boundary_equal_shape.is_valid:
            original_area = float(boundary_equal_shape.area)
            repaired = boundary_equal_shape.buffer(0)
            relative_change = (
                abs(float(repaired.area) - original_area) / original_area if original_area else 1.0
            )
            if repaired.is_empty or not repaired.is_valid or relative_change > 0.0001:
                raise GapPlanningEvidenceError(
                    f"BOUNDARY_EQUAL_AREA_TOPOLOGY_REPAIR_FAILED:{key[0]}:{relative_change:.12f}"
                )
            boundary_equal_shape = repaired
        inside = geometry_mask([mapping(boundary_equal_shape)], out_shape=dimensions, transform=transform,
                               invert=True, all_touched=False)
        if not np.any(inside):
            raise GapPlanningEvidenceError(f"BOUNDARY_HAS_NO_GRID_PIXELS:{key[0]}:{key[1]}")
        if np.any(observed[~inside] != 0) or np.any(cause[~inside] != 0):
            raise GapPlanningEvidenceError(f"NONZERO_PIXEL_OUTSIDE_BOUNDARY:{key[0]}:{key[1]}")
        if np.any(inside & (observed == 1) & (cause != 0)):
            raise GapPlanningEvidenceError(f"CAUSE_ON_OBSERVED_PIXEL:{key[0]}:{key[1]}")
        gap = inside & (observed == 0)
        if np.any(gap & (cause == 0)):
            raise GapPlanningEvidenceError(f"UNCLASSIFIED_GAP_PIXEL:{key[0]}:{key[1]}")
        validated.append((key, observed, cause, inside, gap, transform))

    targets: List[GapTarget] = []
    cells: List[GapCellSummary] = []
    for (province_id, year), observed, cause, inside, gap, transform in validated:
        pixel_area_m2 = abs(float(transform.a * transform.e))
        cell_targets = _targets_for_cell(province_id, year, cause, gap, transform, pixel_area_m2)
        targets.extend(cell_targets)
        total = int(np.count_nonzero(inside))
        observed_count = int(np.count_nonzero(inside & (observed == 1)))
        gap_count = int(np.count_nonzero(gap))
        cause_counts = {name: int(np.count_nonzero(gap & (cause == value)))
                        for value, name in CAUSE_NAMES.items()}
        cells.append(GapCellSummary(
            province_id, year, total, observed_count, gap_count,
            round(observed_count * 100.0 / total, 6), round(gap_count * 100.0 / total, 6),
            cause_counts, len(cell_targets),
        ))

    targets.sort(key=lambda t: (t.priority, t.province_id, t.year, t.target_id))
    return GapAcquisitionPlan(
        PLAN_SCHEMA_VERSION, datetime.now(timezone.utc).isoformat(), evidence_status,
        "PLANNED_NO_EXECUTION" if evidence_status == "VERIFIED_REAL" else (
            "PROVISIONAL_PILOT_PLANNED_NO_EXECUTION" if evidence_status == "PROVISIONAL_REAL"
            else "TESTED_SYNTHETIC_NO_EXECUTION"
        ),
        False, False, False, False, False, boundary_sha, gistaru_sha, decision_sha,
        cross_check_status, source_sha, roles, len(targets), cells, targets,
        _mlops_handoff(evidence_status),
    )


def write_plan_json(plan: GapAcquisitionPlan, target_file: Path) -> None:
    """Write a new plan file exclusively; existing evidence is never overwritten."""
    target = Path(target_file)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(plan.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    try:
        with target.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
    except FileExistsError as exc:
        raise GapPlanningEvidenceError("OUTPUT_ALREADY_EXISTS") from exc
