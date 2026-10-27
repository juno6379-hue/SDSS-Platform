"""Fail-closed 6 province x 6 year x 12 month inventory audit."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import csv
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from .province_year_coverage import CoverageEvidenceError, sha256_file

AUDIT_SCHEMA_VERSION = "4.1"
SOURCE_POLICY_VERSION = "guarded-deficit-1024"
SOURCE_STATUS = "deficit_guarded_bounded_stage"
ALLOWED_QUALITY_STATUSES = {"quality_eligible", "quality_insufficient"}
FIRST_GROUP_6_PROVINCES: List[Dict[str, str]] = [
    {"id":"banten","name":"Banten","local_name":"Banten","island":"Java","split":"val"},
    {"id":"west_java","name":"West Java","local_name":"Jawa Barat","island":"Java","split":"test"},
    {"id":"east_java","name":"East Java","local_name":"Jawa Timur","island":"Java","split":"train"},
    {"id":"south_sulawesi","name":"South Sulawesi","local_name":"Sulawesi Selatan","island":"Sulawesi","split":"train"},
    {"id":"gorontalo","name":"Gorontalo","local_name":"Gorontalo","island":"Sulawesi","split":"train"},
    {"id":"southeast_sulawesi","name":"Southeast Sulawesi","local_name":"Sulawesi Tenggara","island":"Sulawesi","split":"train"},
]
FIRST_GROUP_IDS: Set[str] = {p["id"] for p in FIRST_GROUP_6_PROVINCES}
EXPECTED_SPLITS = {p["id"]: p["split"] for p in FIRST_GROUP_6_PROVINCES}
YEARS = list(range(2020, 2026))
MONTHS = list(range(1, 13))
DRY_SEASON_MONTHS = {6, 7, 8, 9}
MONTH_NAMES = {m: datetime(2000, m, 1).strftime("%b") for m in MONTHS}
OPERATING_SOURCE_SHA256 = "0c149628ccfa916ee976e561c5da05f9ccc810cbeab7d233a05b9bc7eff54658"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


@dataclass
class ProvinceMonthCell:
    cell_id: str; province_id: str; province_name: str; island: str; split: str; year: int; month: int; month_name: str
    season_policy: str; target_grid: str; mask_policy_version: str; discovered_scenes_count: int; verified_download_scenes_count: int
    patch_rows_count: int; eligible_6band_patches: int; insufficient_patches: int; avg_scene_cloud_pct: Optional[float]
    aoi_cloud_shadow_pct: Optional[float]; valid_coverage_pct: Optional[float]; outside_footprint_pct: Optional[float]
    inventory_status: str; baseline_before_status: str; measurement_status: str; gap_reason: str


@dataclass
class ProvinceRollup:
    province_id: str; province_name: str; island: str; split: str; total_cells: int; active_cells: int; unique_scenes: int
    total_patches: int; eligible_patches: int; insufficient_patches: int; eligible_rate: float
    avg_cloud_cover_pct: Optional[float]; avg_valid_coverage_pct: Optional[float]
    nominal_cell_count: int; degraded_cell_count: int; unclassified_cell_count: int


@dataclass
class YearRollup:
    year: int; epoch: str; total_cells: int; active_cells: int; unique_scenes: int; total_patches: int; eligible_patches: int
    insufficient_patches: int; eligible_rate: float; avg_cloud_cover_pct: Optional[float]
    avg_valid_coverage_pct: Optional[float]; nominal_cell_count: int; degraded_cell_count: int; unclassified_cell_count: int


@dataclass
class ProvinceMonthAuditResult:
    schema_version: str; generated_at: str; evidence_status: str; coverage_measurement_status: str; source_sha256: str
    source_policy_version: str; total_cells: int; dry_season_cells: int; wet_season_cells: int; active_observation_cells: int
    total_unique_scenes: int; total_patches_inventory: int; total_eligible_patches: int; total_insufficient_patches: int
    overall_eligible_rate: float; nominal_cells_count: int; degraded_cells_count: int; unclassified_cells_count: int
    cells: List[ProvinceMonthCell]; province_rollups: List[ProvinceRollup]; year_rollups: List[YearRollup]

    def to_dict(self) -> Dict[str, Any]:
        value = asdict(self)
        value["overall_eligible_rate"] = round(self.overall_eligible_rate, 4)
        return value


def _locate_data_root(value: Optional[Path]) -> Path:
    if value is None:
        return Path(__file__).resolve().parents[3] / "data"
    candidate = Path(value).resolve()
    return candidate / "data" if (candidate / "data/first-group-training-esri-v1").is_dir() else candidate


def _validate_source_document(doc: Any) -> List[Dict[str, Any]]:
    if not isinstance(doc, dict):
        raise CoverageEvidenceError("SOURCE_DOCUMENT_OBJECT_REQUIRED")
    if doc.get("policy_version") != SOURCE_POLICY_VERSION:
        raise CoverageEvidenceError("SOURCE_POLICY_VERSION_MISMATCH")
    if doc.get("status") != SOURCE_STATUS or doc.get("executed") is not True:
        raise CoverageEvidenceError("SOURCE_EXECUTION_STATUS_MISMATCH")
    rows = doc.get("scenes")
    if not isinstance(rows, list):
        raise CoverageEvidenceError("SOURCE_SCENES_LIST_REQUIRED")
    return rows


def build_province_month_audit(data_root: Optional[Path] = None, *, expected_source_sha256: Optional[str] = None) -> ProvinceMonthAuditResult:
    root = _locate_data_root(data_root)
    report_path = root / "first-group-training-esri-v1/annual-window-report.json"
    if not report_path.is_file():
        raise CoverageEvidenceError(f"SOURCE_REPORT_MISSING:{report_path}")
    expected = (expected_source_sha256 or OPERATING_SOURCE_SHA256).lower()
    if not _SHA256.fullmatch(expected):
        raise CoverageEvidenceError("EXPECTED_SOURCE_SHA256_INVALID")
    actual_sha = sha256_file(report_path)
    if actual_sha != expected:
        raise CoverageEvidenceError(f"SOURCE_SHA256_MISMATCH:{actual_sha}")
    try:
        doc = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CoverageEvidenceError("SOURCE_JSON_INVALID") from exc
    rows = _validate_source_document(doc)

    by_cell: Dict[Tuple[str, int, int], List[Dict[str, Any]]] = {}
    all_scene_ids: set[str] = set()
    patch_ids: set[str] = set()
    total_eligible = total_insufficient = 0
    for row in rows:
        if not isinstance(row, dict):
            raise CoverageEvidenceError("SOURCE_ROW_OBJECT_REQUIRED")
        province = row.get("province")
        if province not in FIRST_GROUP_IDS or row.get("aoi") != province:
            raise CoverageEvidenceError(f"SOURCE_PROVINCE_OUTSIDE_SCOPE:{province}")
        try:
            year = int(row["year"])
            timestamp = str(row["datetime"])
            datetime_year, month = int(timestamp[0:4]), int(timestamp[5:7])
        except (KeyError, TypeError, ValueError) as exc:
            raise CoverageEvidenceError("SOURCE_ROW_TIME_INVALID") from exc
        if year != datetime_year:
            raise CoverageEvidenceError("SOURCE_YEAR_TIMESTAMP_MISMATCH")
        if year not in YEARS or month not in MONTHS:
            raise CoverageEvidenceError(f"SOURCE_TIME_OUTSIDE_SCOPE:{year}:{month}")
        scene_id, patch_id = row.get("scene_id"), row.get("patch_id")
        if not isinstance(scene_id, str) or not scene_id:
            raise CoverageEvidenceError("SCENE_ID_REQUIRED")
        if not isinstance(patch_id, str) or not patch_id:
            raise CoverageEvidenceError("PATCH_ID_REQUIRED")
        if patch_id in patch_ids:
            raise CoverageEvidenceError(f"DUPLICATE_PATCH_ID:{patch_id}")
        patch_ids.add(patch_id)
        if row.get("split") != EXPECTED_SPLITS[province]:
            raise CoverageEvidenceError(f"SOURCE_SPLIT_MISMATCH:{patch_id}")
        quality_status = row.get("quality_status")
        if quality_status not in ALLOWED_QUALITY_STATUSES:
            raise CoverageEvidenceError(f"QUALITY_STATUS_UNKNOWN:{quality_status}")
        quality_sha = (row.get("patch_sha256") or {}).get("quality")
        if not isinstance(quality_sha, str) or not _SHA256.fullmatch(quality_sha.lower()):
            raise CoverageEvidenceError(f"QUALITY_SHA256_INVALID:{patch_id}")
        if not isinstance(row.get("quality_mask_path"), str) or not row["quality_mask_path"]:
            raise CoverageEvidenceError(f"QUALITY_MASK_PATH_REQUIRED:{patch_id}")
        all_scene_ids.add(scene_id)
        by_cell.setdefault((province, year, month), []).append(row)
        total_eligible += int(quality_status == "quality_eligible")
        total_insufficient += int(quality_status == "quality_insufficient")
    if total_eligible + total_insufficient != len(rows):
        raise CoverageEvidenceError("QUALITY_STATUS_ACCOUNTING_MISMATCH")

    cells: List[ProvinceMonthCell] = []
    active = 0
    for province in FIRST_GROUP_6_PROVINCES:
        for year in YEARS:
            for month in MONTHS:
                selected = by_cell.get((province["id"], year, month), [])
                scene_ids = {r["scene_id"] for r in selected}
                active += int(bool(selected))
                clouds = [float(r["cloud_cover"]) for r in selected if r.get("cloud_cover") is not None]
                shadows = [float((r.get("source_properties") or {})["s2:cloud_shadow_percentage"]) for r in selected
                           if (r.get("source_properties") or {}).get("s2:cloud_shadow_percentage") is not None]
                eligible = sum(r["quality_status"] == "quality_eligible" for r in selected)
                cells.append(ProvinceMonthCell(
                    f"{province['id']}_{year}_{month:02d}", province["id"], province["name"], province["island"], province["split"],
                    year, month, MONTH_NAMES[month], "DRY_SEASON_WINDOW" if month in DRY_SEASON_MONTHS else "WET_SEASON_MONSOON",
                    "UNMEASURED_PROVINCE_GRID", "SOURCE_DECLARATION_ONLY", len(scene_ids), 0, len(selected), eligible,
                    len(selected) - eligible, round(sum(clouds) / len(clouds), 2) if clouds else None,
                    round(sum(shadows) / len(shadows), 2) if shadows else None, None, None, "VERIFIED_REAL_INVENTORY_ONLY",
                    "INVENTORY_ONLY", "BLOCKED_NOT_MEASURED",
                    "ACTUAL_PINNED_PROVINCE_MASK_UNION_REQUIRED" if selected else "NO_SCENE",
                ))

    def common(selected: List[ProvinceMonthCell], *, province_id: Optional[str] = None, selected_year: Optional[int] = None) -> Dict[str, Any]:
        patch = sum(c.patch_rows_count for c in selected)
        eligible = sum(c.eligible_6band_patches for c in selected)
        unique = len({r["scene_id"] for (p, y, _), rs in by_cell.items() for r in rs
                      if (province_id is None or p == province_id) and (selected_year is None or y == selected_year)})
        return dict(total_cells=len(selected), active_cells=sum(c.patch_rows_count > 0 for c in selected), unique_scenes=unique,
                    total_patches=patch, eligible_patches=eligible, insufficient_patches=patch - eligible,
                    eligible_rate=round(eligible / patch, 4) if patch else 0.0, avg_cloud_cover_pct=None,
                    avg_valid_coverage_pct=None, nominal_cell_count=0, degraded_cell_count=0,
                    unclassified_cell_count=len(selected))

    province_rollups = [ProvinceRollup(province_id=p["id"], province_name=p["name"], island=p["island"], split=p["split"],
                                         **common([c for c in cells if c.province_id == p["id"]], province_id=p["id"]))
                        for p in FIRST_GROUP_6_PROVINCES]
    year_rollups = [YearRollup(year=y, epoch="T1_BASELINE" if y < 2022 else "T2_MONITORING",
                               **common([c for c in cells if c.year == y], selected_year=y)) for y in YEARS]
    return ProvinceMonthAuditResult(
        AUDIT_SCHEMA_VERSION, datetime.now(timezone.utc).isoformat(), "VERIFIED_REAL", "BLOCKED_NOT_MEASURED",
        actual_sha, SOURCE_POLICY_VERSION, len(cells), 144, 288, active, len(all_scene_ids), len(rows), total_eligible,
        total_insufficient, total_eligible / len(rows) if rows else 0.0, 0, 0, len(cells), cells,
        province_rollups, year_rollups,
    )


def export_audit_csv(result: ProvinceMonthAuditResult, target_file: Path) -> None:
    target_file.parent.mkdir(parents=True, exist_ok=True)
    rows = [asdict(cell) for cell in result.cells]
    with target_file.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)


def export_audit_markdown(result: ProvinceMonthAuditResult, target_file: Path) -> None:
    target_file.parent.mkdir(parents=True, exist_ok=True)
    target_file.write_text(
        "# Province-month inventory audit\n\n"
        f"- Inventory: `{result.evidence_status}` ({result.total_patches_inventory} patch rows / {result.total_unique_scenes} unique scenes)\n"
        f"- Province coverage: `{result.coverage_measurement_status}`\n"
        f"- Classification: nominal={result.nominal_cells_count}, degraded={result.degraded_cells_count}, unclassified={result.unclassified_cells_count}\n"
        "- Patch-local ratios are not province coverage. Pinned EPSG:6933 binary mask unions are required.\n",
        encoding="utf-8",
    )
