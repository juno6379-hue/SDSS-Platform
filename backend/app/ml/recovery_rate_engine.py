"""Recovery metrics from pinned same-grid observed-mask transitions only."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import rasterio

from .province_year_coverage import (
    COVERAGE_REPORT_SCHEMA_VERSION, EQUAL_AREA_CRS, CoverageEvidenceError,
    PinnedFile, ProvinceCoverageReport, ProvinceYearCoverage, sha256_file,
)

RECOVERY_SCHEMA_VERSION = "4.1"
TRANSITION_SCHEMA_VERSION = "observed-transition/1.0"
TRANSITION_MASK_SEMANTICS = "BINARY_INSIDE_BOUNDARY_OBSERVED_0_1"
PROVINCE_METADATA = {
    "banten":{"name":"Banten","island":"Java","split":"val"},
    "west_java":{"name":"West Java","island":"Java","split":"test"},
    "east_java":{"name":"East Java","island":"Java","split":"train"},
    "south_sulawesi":{"name":"South Sulawesi","island":"Sulawesi","split":"train"},
    "gorontalo":{"name":"Gorontalo","island":"Sulawesi","split":"train"},
    "southeast_sulawesi":{"name":"Southeast Sulawesi","island":"Sulawesi","split":"train"},
}
YEARS = list(range(2020, 2026))
PROVINCE_LAND_AREAS_HA = {key: 0.0 for key in PROVINCE_METADATA}


@dataclass(frozen=True)
class ObservedMaskTransition:
    province_id: str
    year: int
    before_observed: PinnedFile
    after_observed: PinnedFile
    boundary_mask: PinnedFile
    schema_version: str = TRANSITION_SCHEMA_VERSION
    mask_semantics: str = TRANSITION_MASK_SEMANTICS
    nodata: None = None


@dataclass
class CellRecoveryMetric:
    cell_id: str; province_id: str; province_name: str; island: str; split: str; year: int; epoch: str
    total_land_area_ha: Optional[float]; before_valid_coverage_pct: Optional[float]; after_valid_coverage_pct: Optional[float]
    coverage_increase_pct_point: Optional[float]; before_valid_area_ha: Optional[float]; after_valid_area_ha: Optional[float]
    aggregate_net_observed_area_change_ha: Optional[float]; aggregate_net_coverage_change_pct_point: Optional[float]
    newly_recovered_area_ha: Optional[float]; still_missing_area_ha: Optional[float]; recovery_rate_pct: Optional[float]
    aggregate_change_status: str; gap_reason_resolved: str; status: str


@dataclass
class ProvinceRecoveryRollup:
    province_id: str; province_name: str; island: str; split: str; total_land_area_ha: Optional[float]
    avg_before_coverage_pct: Optional[float]; avg_after_coverage_pct: Optional[float]
    avg_aggregate_net_coverage_change_pct_point: Optional[float]
    total_newly_recovered_ha: Optional[float]; avg_recovery_rate_pct: Optional[float]; status: str


@dataclass
class RecoverySummary:
    schema_version: str; generated_at: str; evidence_status: str; blocking_reason: Optional[str]; total_cells: int
    before_source_sha256: Optional[str]; after_source_sha256: Optional[str]; boundary_sha256: Optional[str]
    mean_before_valid_pct: Optional[float]; mean_after_valid_pct: Optional[float]; mean_increase_pct_point: Optional[float]
    mean_aggregate_net_coverage_change_pct_point: Optional[float]; total_aggregate_net_observed_area_change_ha: Optional[float]
    total_newly_recovered_ha: Optional[float]; mean_recovery_rate_pct: Optional[float]
    aggregate_change_status: str; cells: List[CellRecoveryMetric]; province_rollups: List[ProvinceRecoveryRollup]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _blank_cell(pid: str, year: int) -> CellRecoveryMetric:
    meta = PROVINCE_METADATA[pid]
    return CellRecoveryMetric(
        f"{pid}_{year}", pid, meta["name"], meta["island"], meta["split"], year,
        "T1_BASELINE" if year < 2022 else "T2_MONITORING",
        None, None, None, None, None, None, None, None, None, None, None,
        "BLOCKED_NO_COMPARABLE_REPORTS", "NO", "BLOCKED",
    )


def _blank_summary(reason: str) -> RecoverySummary:
    cells = [_blank_cell(pid, year) for pid in PROVINCE_METADATA for year in YEARS]
    rollups = [ProvinceRecoveryRollup(pid, m["name"], m["island"], m["split"], None, None, None, None, None, None, "BLOCKED")
               for pid, m in PROVINCE_METADATA.items()]
    return RecoverySummary(
        RECOVERY_SCHEMA_VERSION, datetime.now(timezone.utc).isoformat(), "BLOCKED", reason, 36,
        None, None, None, None, None, None, None, None, None, None,
        "BLOCKED_NO_COMPARABLE_REPORTS", cells, rollups,
    )


def _validate_cell(cell: ProvinceYearCoverage, report_status: str, key: Tuple[str, int]) -> None:
    if cell.measurement_status != report_status:
        raise CoverageEvidenceError(f"CELL_MEASUREMENT_STATUS_MISMATCH:{key[0]}:{key[1]}")
    if not (cell.readiness_status == "COVERAGE_COMPLETE" or cell.readiness_status.startswith("BLOCKED_")):
        raise CoverageEvidenceError(f"CELL_READINESS_STATUS_UNKNOWN:{key[0]}:{key[1]}")
    values = [cell.boundary_area_ha, cell.footprint_area_ha, cell.observed_area_ha, cell.missing_area_ha,
              cell.cloud_area_ha, cell.shadow_area_ha, cell.nodata_area_ha,
              cell.outside_footprint_area_ha, cell.not_measured_area_ha]
    if any(not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0 for v in values):
        raise CoverageEvidenceError(f"CELL_AREA_INVALID:{key[0]}:{key[1]}")
    tolerance = max(0.02, 0.001 * cell.boundary_area_ha)
    if cell.boundary_area_ha <= 0 or abs(cell.observed_area_ha + cell.missing_area_ha - cell.boundary_area_ha) > tolerance:
        raise CoverageEvidenceError(f"CELL_OBSERVED_MISSING_INVARIANT:{key[0]}:{key[1]}")
    causes = cell.cloud_area_ha + cell.shadow_area_ha + cell.nodata_area_ha + cell.outside_footprint_area_ha + cell.not_measured_area_ha
    if abs(causes - cell.missing_area_ha) > tolerance:
        raise CoverageEvidenceError(f"CELL_MISSING_CAUSE_INVARIANT:{key[0]}:{key[1]}")
    if abs(cell.observed_coverage_pct - 100 * cell.observed_area_ha / cell.boundary_area_ha) > 0.02:
        raise CoverageEvidenceError(f"CELL_OBSERVED_PERCENT_INVARIANT:{key[0]}:{key[1]}")
    if abs(cell.missing_coverage_pct - 100 * cell.missing_area_ha / cell.boundary_area_ha) > 0.02:
        raise CoverageEvidenceError(f"CELL_MISSING_PERCENT_INVARIANT:{key[0]}:{key[1]}")


def _index_report(report: ProvinceCoverageReport, label: str) -> Dict[Tuple[str, int], ProvinceYearCoverage]:
    if report.schema_version != COVERAGE_REPORT_SCHEMA_VERSION:
        raise CoverageEvidenceError(f"{label}_REPORT_SCHEMA_VERSION_MISMATCH")
    if report.evidence_status not in {"VERIFIED_REAL", "TESTED_SYNTHETIC"}:
        raise CoverageEvidenceError(f"{label}_REPORT_EVIDENCE_STATUS_INVALID")
    if report.equal_area_crs != EQUAL_AREA_CRS:
        raise CoverageEvidenceError(f"{label}_REPORT_EQUAL_AREA_CRS_MISMATCH")
    expected = {(p, y) for p in PROVINCE_METADATA for y in YEARS}
    result: Dict[Tuple[str, int], ProvinceYearCoverage] = {}
    for cell in report.cells:
        key = (cell.province_id, cell.year)
        if key in result:
            raise CoverageEvidenceError(f"{label}_DUPLICATE_CELL:{key[0]}:{key[1]}")
        if key not in expected:
            raise CoverageEvidenceError(f"{label}_CELL_OUTSIDE_SCOPE:{key[0]}:{key[1]}")
        _validate_cell(cell, report.evidence_status, key)
        result[key] = cell
    if set(result) != expected:
        raise CoverageEvidenceError(f"{label}_RECOVERY_SCOPE_MUST_BE_6_PROVINCES_X_6_YEARS")
    return result


def _read_transition_mask(ref: PinnedFile, label: str):
    path = Path(ref.path).resolve()
    if not path.is_file() or sha256_file(path) != ref.sha256.lower():
        raise CoverageEvidenceError(f"{label}_PIN_MISMATCH:{path}")
    with rasterio.open(path) as ds:
        if ds.count != 1 or ds.crs is None or ds.crs.to_epsg() != 6933 or ds.nodata is not None:
            raise CoverageEvidenceError(f"{label}_EPSG6933_BINARY_NO_NODATA_REQUIRED:{path}")
        if ds.transform.b != 0 or ds.transform.d != 0 or ds.transform.a <= 0 or ds.transform.e >= 0:
            raise CoverageEvidenceError(f"{label}_GRID_INVALID:{path}")
        arr = ds.read(1)
        if not {int(v) for v in np.unique(arr)}.issubset({0, 1}):
            raise CoverageEvidenceError(f"{label}_BINARY_VALUES_REQUIRED:{path}")
        return arr.astype(bool), ds.crs, ds.transform, ds.shape


def _transition_index(transitions: Sequence[ObservedMaskTransition]) -> Dict[Tuple[str, int], ObservedMaskTransition]:
    expected = {(p, y) for p in PROVINCE_METADATA for y in YEARS}
    result: Dict[Tuple[str, int], ObservedMaskTransition] = {}
    for item in transitions:
        key = (item.province_id, item.year)
        if key in result:
            raise CoverageEvidenceError(f"DUPLICATE_TRANSITION:{key[0]}:{key[1]}")
        if key not in expected:
            raise CoverageEvidenceError(f"TRANSITION_OUTSIDE_SCOPE:{key[0]}:{key[1]}")
        if item.schema_version != TRANSITION_SCHEMA_VERSION or item.mask_semantics != TRANSITION_MASK_SEMANTICS or item.nodata is not None:
            raise CoverageEvidenceError(f"TRANSITION_CONTRACT_MISMATCH:{key[0]}:{key[1]}")
        result[key] = item
    if set(result) != expected:
        raise CoverageEvidenceError("TRANSITION_SCOPE_MUST_BE_6_PROVINCES_X_6_YEARS")
    return result


def compute_recovery_metrics(
    data_root: Optional[Path] = None, *, before_report: Optional[ProvinceCoverageReport] = None,
    after_report: Optional[ProvinceCoverageReport] = None,
    observed_mask_transitions: Optional[Sequence[ObservedMaskTransition]] = None,
) -> RecoverySummary:
    """Return recovery only when complete pinned same-grid transition masks exist."""
    del data_root
    if before_report is None or after_report is None:
        return _blank_summary("MISSING_EXPLICIT_PINNED_BEFORE_AND_AFTER_COVERAGE_REPORTS")
    before, after = _index_report(before_report, "BEFORE"), _index_report(after_report, "AFTER")
    if before_report.boundary_sha256 != after_report.boundary_sha256:
        raise CoverageEvidenceError("BOUNDARY_SHA256_MISMATCH")
    report_status = "VERIFIED_REAL" if before_report.evidence_status == after_report.evidence_status == "VERIFIED_REAL" else "TESTED_SYNTHETIC"
    expected = sorted(before)
    aggregate_cells: List[CellRecoveryMetric] = []
    for pid, year in expected:
        old, new = before[(pid, year)], after[(pid, year)]
        if abs(old.boundary_area_ha - new.boundary_area_ha) > max(0.02, old.boundary_area_ha * 0.001):
            raise CoverageEvidenceError(f"BOUNDARY_AREA_MISMATCH:{pid}:{year}")
        meta = PROVINCE_METADATA[pid]
        aggregate_cells.append(CellRecoveryMetric(
            f"{pid}_{year}", pid, meta["name"], meta["island"], meta["split"], year,
            "T1_BASELINE" if year < 2022 else "T2_MONITORING", new.boundary_area_ha,
            old.observed_coverage_pct, new.observed_coverage_pct, None, old.observed_area_ha, new.observed_area_ha,
            round(new.observed_area_ha - old.observed_area_ha, 4),
            round(new.observed_coverage_pct - old.observed_coverage_pct, 4), None, new.missing_area_ha, None,
            report_status, "NO_SAME_GRID_MASK_DIFFERENCE", "BLOCKED_MISSING_SAME_GRID_OBSERVED_MASK_TRANSITION",
        ))
    if observed_mask_transitions is None:
        rollups = _rollups(aggregate_cells, recovery_available=False)
        return _summary(before_report, after_report, aggregate_cells, rollups, "BLOCKED",
                        "MISSING_SAME_GRID_OBSERVED_MASK_TRANSITIONS", report_status)

    transition_by_key = _transition_index(observed_mask_transitions)
    measured_cells: List[CellRecoveryMetric] = []
    for cell in aggregate_cells:
        key = (cell.province_id, cell.year)
        item = transition_by_key[key]
        before_mask, before_crs, before_transform, before_shape = _read_transition_mask(item.before_observed, "BEFORE_OBSERVED")
        after_mask, after_crs, after_transform, after_shape = _read_transition_mask(item.after_observed, "AFTER_OBSERVED")
        boundary_mask, boundary_crs, boundary_transform, boundary_shape = _read_transition_mask(item.boundary_mask, "BOUNDARY")
        if not (before_crs == after_crs == boundary_crs and before_transform == after_transform == boundary_transform and
                before_shape == after_shape == boundary_shape):
            raise CoverageEvidenceError(f"TRANSITION_GRID_MISMATCH:{key[0]}:{key[1]}")
        if np.any(before_mask & ~boundary_mask) or np.any(after_mask & ~boundary_mask):
            raise CoverageEvidenceError(f"OBSERVED_OUTSIDE_BOUNDARY_MASK:{key[0]}:{key[1]}")
        pixel_area_ha = abs(before_transform.a * before_transform.e) / 10000.0
        boundary_area = float(np.count_nonzero(boundary_mask)) * pixel_area_ha
        before_area = float(np.count_nonzero(before_mask & boundary_mask)) * pixel_area_ha
        after_area = float(np.count_nonzero(after_mask & boundary_mask)) * pixel_area_ha
        tolerance = max(0.02, cell.total_land_area_ha * 0.001)
        if abs(boundary_area - cell.total_land_area_ha) > tolerance or abs(before_area - cell.before_valid_area_ha) > tolerance or abs(after_area - cell.after_valid_area_ha) > tolerance:
            raise CoverageEvidenceError(f"TRANSITION_REPORT_AREA_MISMATCH:{key[0]}:{key[1]}")
        newly = float(np.count_nonzero((~before_mask) & after_mask & boundary_mask)) * pixel_area_ha
        before_missing = float(np.count_nonzero((~before_mask) & boundary_mask)) * pixel_area_ha
        still_missing = float(np.count_nonzero((~after_mask) & boundary_mask)) * pixel_area_ha
        rate = 100.0 * newly / before_missing if before_missing else 0.0
        cell.newly_recovered_area_ha = round(newly, 4)
        cell.still_missing_area_ha = round(still_missing, 4)
        cell.recovery_rate_pct = round(rate, 4)
        cell.gap_reason_resolved = "PINNED_SAME_GRID_OBSERVED_MASK_DIFFERENCE"
        cell.status = report_status
        measured_cells.append(cell)
    return _summary(before_report, after_report, measured_cells, _rollups(measured_cells, recovery_available=True),
                    report_status, None, report_status)


def _avg(values: Sequence[float]) -> float:
    return round(sum(values) / len(values), 4)


def _rollups(cells: List[CellRecoveryMetric], *, recovery_available: bool) -> List[ProvinceRecoveryRollup]:
    result = []
    for pid, meta in PROVINCE_METADATA.items():
        selected = [c for c in cells if c.province_id == pid]
        result.append(ProvinceRecoveryRollup(
            pid, meta["name"], meta["island"], meta["split"], selected[0].total_land_area_ha,
            _avg([c.before_valid_coverage_pct for c in selected]), _avg([c.after_valid_coverage_pct for c in selected]),
            _avg([c.aggregate_net_coverage_change_pct_point for c in selected]),
            round(sum(c.newly_recovered_area_ha for c in selected), 4) if recovery_available else None,
            _avg([c.recovery_rate_pct for c in selected]) if recovery_available else None,
            selected[0].status if recovery_available else "BLOCKED_MISSING_SAME_GRID_OBSERVED_MASK_TRANSITION",
        ))
    return result


def _summary(before_report, after_report, cells, rollups, status, reason, aggregate_status) -> RecoverySummary:
    available = status != "BLOCKED"
    return RecoverySummary(
        RECOVERY_SCHEMA_VERSION, datetime.now(timezone.utc).isoformat(), status, reason, 36,
        before_report.source_sha256, after_report.source_sha256, before_report.boundary_sha256,
        _avg([c.before_valid_coverage_pct for c in cells]), _avg([c.after_valid_coverage_pct for c in cells]), None,
        _avg([c.aggregate_net_coverage_change_pct_point for c in cells]),
        round(sum(c.aggregate_net_observed_area_change_ha for c in cells), 4),
        round(sum(c.newly_recovered_area_ha for c in cells), 4) if available else None,
        _avg([c.recovery_rate_pct for c in cells]) if available else None,
        aggregate_status, cells, rollups,
    )


def export_recovery_report(summary: RecoverySummary, target_file: Path) -> None:
    target_file.parent.mkdir(parents=True, exist_ok=True)
    target_file.write_text(
        "# Recovery measurement\n\n"
        f"- Status: `{summary.evidence_status}`\n"
        f"- Schema: `{summary.schema_version}`\n"
        f"- Blocking reason: `{summary.blocking_reason}`\n"
        f"- Aggregate net-change status: `{summary.aggregate_change_status}`\n"
        "- `newly_recovered_area_ha` and `recovery_rate_pct` require pinned before/after/boundary masks on one EPSG:6933 grid.\n",
        encoding="utf-8",
    )
