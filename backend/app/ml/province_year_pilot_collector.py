"""Bounded Sentinel-2 SCL pilot for the provisional BIG boundary workflow."""
from __future__ import annotations

from collections import deque
from contextlib import contextmanager, nullcontext
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import time
from typing import Any, Mapping

import numpy as np
import rasterio
from rasterio.transform import xy
from rasterio.warp import transform as warp_transform

from app.data import service
from app.data.budget import CollectionLedger
from app.ml.province_year_coverage import PinnedFile, sha256_file
from app.ml.province_year_evidence_builder import (
    build_local_scl_mosaics,
    validate_local_scl_mosaic_manifest,
)
from app.ml.province_year_gap_acquisition_planner import (
    build_gap_acquisition_plan,
    write_plan_json,
)


PILOT_SCHEMA_VERSION = "province-year-sentinel-scl-pilot/1.0"
PILOT_RESERVATION_BYTES = 32 * 1024 * 1024
PER_CANDIDATE_TRANSFER_BYTES = 8 * 1024 * 1024
PILOT_WINDOW_SIDE = 256
SCL_CLEAR = {4, 5, 6, 7, 11}
SCL_CLOUD = {8, 9, 10}
SCL_SHADOW = {2, 3}
SCL_NODATA = {0, 1}


class PilotCollectionError(RuntimeError):
    """Raised when the bounded pilot cannot safely proceed."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, value: Mapping[str, Any], *, exclusive: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "x" if exclusive else "w"
    with path.open(mode, encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")


def _inside(root: Path, path: Path, label: str) -> Path:
    root = root.resolve()
    candidate = path.resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise PilotCollectionError(f"{label}_OUTSIDE_WORKSPACE") from exc
    return candidate


def _existing_scene_ids(source_root: Path) -> set[str]:
    result: set[str] = set()
    for path in source_root.rglob("stac-item.json"):
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        scene_id = document.get("id")
        if isinstance(scene_id, str) and scene_id:
            result.add(scene_id)
    return result


def _distance_from_non_gap(mask: np.ndarray) -> np.ndarray:
    """Return deterministic Manhattan distance from non-target pixels without SciPy."""
    height, width = mask.shape
    distance = np.full((height, width), -1, dtype="int32")
    queue: deque[tuple[int, int]] = deque()
    for row, col in np.argwhere(~mask):
        distance[row, col] = 0
        queue.append((int(row), int(col)))
    if not queue:
        for col in range(width):
            distance[0, col] = 0
            distance[height - 1, col] = 0
            queue.append((0, col))
            queue.append((height - 1, col))
        for row in range(height):
            distance[row, 0] = 0
            distance[row, width - 1] = 0
            queue.append((row, 0))
            queue.append((row, width - 1))
    while queue:
        row, col = queue.popleft()
        next_distance = int(distance[row, col]) + 1
        for next_row, next_col in ((row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1)):
            if 0 <= next_row < height and 0 <= next_col < width and distance[next_row, next_col] < 0:
                distance[next_row, next_col] = next_distance
                queue.append((next_row, next_col))
    return distance


def select_pilot_target(
    mosaic_manifest: Path, *, exclude_cells: set[tuple[str, int]] | None = None,
) -> dict[str, Any]:
    document = json.loads(Path(mosaic_manifest).read_text(encoding="utf-8"))
    cells = document.get("cells")
    if not isinstance(cells, list) or len(cells) != 36:
        raise PilotCollectionError("MOSAIC_EXACT_36_CELLS_REQUIRED")
    ranked = sorted(
        cells,
        key=lambda row: (
            -int((row.get("cause_pixels") or {}).get("OUTSIDE_FOOTPRINT", 0)),
            str(row.get("province_id")),
            int(row.get("year")),
        ),
    )
    priorities = []
    for rank, row in enumerate(ranked, 1):
        total = int(row["boundary_pixels"])
        outside = int(row["cause_pixels"]["OUTSIDE_FOOTPRINT"])
        priorities.append({
            "rank": rank,
            "province_id": str(row["province_id"]),
            "year": int(row["year"]),
            "outside_footprint_pixels": outside,
            "outside_footprint_pct": round(outside * 100.0 / total, 6),
            "observed_pixels": int(row["observed_pixels"]),
            "boundary_pixels": total,
            "source_asset_count": int(row["source_asset_count"]),
        })
    excluded = exclude_cells or set()
    selected = next(
        (row for row in ranked if (str(row["province_id"]), int(row["year"])) not in excluded),
        None,
    )
    if selected is None:
        raise PilotCollectionError("NO_DISTINCT_PROVINCE_YEAR_TARGET_AVAILABLE")
    cause_path = (Path(mosaic_manifest).parent / str(selected["cause_path"])).resolve()
    with rasterio.open(cause_path) as dataset:
        cause = dataset.read(1)
        outside_mask = cause == 4
        if not np.any(outside_mask):
            raise PilotCollectionError("NO_OUTSIDE_FOOTPRINT_PIXEL_AVAILABLE")
        distance = _distance_from_non_gap(outside_mask)
        candidates = np.argwhere(outside_mask & (distance == int(distance[outside_mask].max())))
        row, col = (int(value) for value in candidates[0])
        x, y = xy(dataset.transform, row, col, offset="center")
        longitude, latitude = warp_transform(dataset.crs, "EPSG:4326", [x], [y])
    lon, lat = float(longitude[0]), float(latitude[0])
    half = 0.035
    return {
        "schema_version": "province-year-gap-priority/1.0",
        "generated_at": _utc_now(),
        "ranking_rule": "OUTSIDE_FOOTPRINT_PIXELS_DESC_THEN_PROVINCE_YEAR",
        "priorities": priorities,
        "selected": {
            "province_id": str(selected["province_id"]),
            "year": int(selected["year"]),
            "cause": "OUTSIDE_FOOTPRINT",
            "mosaic_row": row,
            "mosaic_col": col,
            "distance_from_existing_or_boundary_pixels_1km": int(distance[row, col]),
            "center_wgs84": [lon, lat],
            "search_bbox_wgs84": [lon - half, lat - half, lon + half, lat + half],
            "duplicate_spatial_check": "SELECTED_PIXEL_CAUSE_EQUALS_OUTSIDE_FOOTPRINT",
        },
    }


def inspect_preflight(
    *, workspace: Path, source_root: Path, ledger_path: Path, execution_lock: Path,
    priority: Mapping[str, Any], reservation_bytes: int = PILOT_RESERVATION_BYTES,
) -> dict[str, Any]:
    workspace = workspace.resolve()
    source_root = _inside(workspace, source_root, "SOURCE_ROOT")
    ledger_path = _inside(workspace, ledger_path, "LEDGER")
    historical = [
        workspace / "data/first-group-annual/run-result.json",
        workspace / "data/first-group-recovery32/run-result.json",
    ]
    ledger = CollectionLedger(ledger_path, historical, additional_budget=4 * 1024 ** 3)
    state = ledger.snapshot()
    remaining = int(state["additional_maximum_bytes"]) - int(state["new_charged_bytes"])
    disk = shutil.disk_usage(workspace)
    pending = sorted(
        key for key, value in state.get("batches", {}).items() if value.get("status") == "pending"
    )
    errors = []
    if state.get("rate_limit_active"):
        errors.append("GLOBAL_RATE_LIMIT_CIRCUIT_ACTIVE")
    if remaining < reservation_bytes:
        errors.append("GLOBAL_LEDGER_BUDGET_INSUFFICIENT")
    if disk.free < reservation_bytes * 4:
        errors.append("DISK_FREE_SPACE_INSUFFICIENT")
    if execution_lock.exists():
        errors.append("COLLECTOR_EXECUTION_LOCK_EXISTS")
    existing_ids = _existing_scene_ids(source_root)
    return {
        "schema_version": "province-year-pilot-preflight/1.0",
        "checked_at": _utc_now(),
        "status": "PASS" if not errors else "BLOCKED",
        "errors": errors,
        "selected_target": dict(priority["selected"]),
        "duplicate_check": {
            "existing_stac_item_count": len(existing_ids),
            "selected_pixel_outside_existing_footprint": True,
            "scene_id_rechecked_after_live_search": True,
        },
        "budget": {
            "ledger_path": str(ledger_path),
            "additional_maximum_bytes": int(state["additional_maximum_bytes"]),
            "new_charged_bytes_before": int(state["new_charged_bytes"]),
            "remaining_before": remaining,
            "pilot_reservation_bytes": reservation_bytes,
            "rate_limit_active": bool(state.get("rate_limit_active")),
            "preexisting_pending_batches": pending,
        },
        "storage": {
            "workspace_drive_total_bytes": int(disk.total),
            "workspace_drive_used_bytes": int(disk.used),
            "workspace_drive_free_bytes": int(disk.free),
            "minimum_required_free_bytes": reservation_bytes * 4,
        },
    }


@contextmanager
def _execution_lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        os.write(descriptor, str(os.getpid()).encode("ascii"))
        yield
    finally:
        os.close(descriptor)
        path.unlink(missing_ok=True)


def _redact_signed_urls(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _redact_signed_urls(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact_signed_urls(item) for item in value]
    if isinstance(value, str) and value.startswith("https://") and "?" in value:
        return value.split("?", 1)[0]
    return value


def _scl_quality(values: np.ndarray) -> dict[str, Any]:
    unique, counts = np.unique(values, return_counts=True)
    histogram = {str(int(key)): int(count) for key, count in zip(unique, counts)}
    if not set(int(key) for key in unique).issubset(set(range(12))):
        raise PilotCollectionError(f"SCL_VALUE_DOMAIN_INVALID:{sorted(histogram)}")
    total = int(values.size)
    count_for = lambda classes: int(np.count_nonzero(np.isin(values, tuple(classes))))
    clear = count_for(SCL_CLEAR)
    cloud = count_for(SCL_CLOUD)
    shadow = count_for(SCL_SHADOW)
    nodata = count_for(SCL_NODATA)
    return {
        "pixel_count": total,
        "histogram": histogram,
        "clear_pixels": clear,
        "clear_fraction": round(clear / total, 6),
        "cloud_pixels": cloud,
        "shadow_pixels": shadow,
        "nodata_pixels": nodata,
        "unclassified_pixels": total - clear - cloud - shadow - nodata,
        "quality_status": "OBSERVATION_ELIGIBLE" if clear / total >= 0.5 else "CAUSE_EVIDENCE_ONLY",
    }


def search_stac_with_retry(
    payload: Mapping[str, Any], *, max_attempts: int = 3, sleeper=time.sleep,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Retry transient STAC transport failures, but never retry HTTP 429."""
    if not 1 <= max_attempts <= 3:
        raise PilotCollectionError("STAC_RETRY_ATTEMPTS_INVALID")
    audit = []
    for attempt in range(1, max_attempts + 1):
        try:
            result = service.search_stac(dict(payload))
            audit.append({"attempt": attempt, "status": "SUCCESS"})
            return result, audit
        except Exception as exc:
            cause = exc
            http_status = None
            chain = []
            while cause is not None and len(chain) < 8:
                chain.append(type(cause).__name__)
                if getattr(cause, "code", None) is not None:
                    http_status = int(cause.code)
                cause = cause.__cause__
            audit.append({
                "attempt": attempt,
                "status": "FAILED",
                "error_type": type(exc).__name__,
                "cause_chain": chain,
                "http_status": http_status,
            })
            if http_status == 429 or attempt == max_attempts:
                setattr(exc, "search_attempts", audit)
                raise
            sleeper(float(attempt))
    raise PilotCollectionError("STAC_RETRY_UNREACHABLE")


def collect_one_scl_pilot(
    *, workspace: Path, source_root: Path, evidence_dir: Path, priority: Mapping[str, Any],
    ledger_path: Path, execution_lock: Path, batch_key_override: str | None = None,
    report_name: str = "pilot-acquisition-report.json",
    window_side: int = PILOT_WINDOW_SIDE,
    reservation_bytes: int = PILOT_RESERVATION_BYTES,
    metadata_budget_bytes: int = 4 * 1024 * 1024,
    lock_already_held: bool = False,
) -> dict[str, Any]:
    workspace = workspace.resolve()
    source_root = _inside(workspace, source_root, "SOURCE_ROOT")
    evidence_dir = _inside(workspace, evidence_dir, "EVIDENCE_DIR")
    selected = priority["selected"]
    province_id = str(selected["province_id"])
    year = int(selected["year"])
    batch_key = batch_key_override or f"unit363-pilot-{province_id}-{year}-p00"
    if not batch_key or any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for character in batch_key):
        raise PilotCollectionError("PILOT_BATCH_KEY_INVALID")
    if not 1 <= int(window_side) <= 2048:
        raise PilotCollectionError("PILOT_WINDOW_SIDE_INVALID")
    if not 1 <= int(metadata_budget_bytes) <= 8 * 1024 * 1024:
        raise PilotCollectionError("PILOT_METADATA_BUDGET_INVALID")
    if not metadata_budget_bytes < reservation_bytes <= 2 * 1024 * 1024 * 1024:
        raise PilotCollectionError("PILOT_RESERVATION_INVALID")
    batch_root = source_root / batch_key
    cell_root = batch_root / f"{province_id}-pilot-00-{year}"
    if batch_root.exists():
        raise PilotCollectionError("PILOT_OUTPUT_ALREADY_EXISTS")
    config = {
        "schema_version": PILOT_SCHEMA_VERSION,
        "batch_key": batch_key,
        "province_id": province_id,
        "year": year,
        "bbox": list(selected["search_bbox_wgs84"]),
        "collection": "sentinel-2-l2a",
        "endpoint": "planetary-computer",
        "season": [f"{year}-06-01", f"{year}-09-30"],
        "cloud_cover_max": 20,
        "window_side": int(window_side),
        "reservation_bytes": int(reservation_bytes),
        "metadata_budget_bytes": int(metadata_budget_bytes),
        "boundary_sha256": priority["boundary_sha256"],
        "cross_check_decision_sha256": priority["cross_check_decision_sha256"],
    }
    config_sha = hashlib.sha256(
        json.dumps(config, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    historical = [
        workspace / "data/first-group-annual/run-result.json",
        workspace / "data/first-group-recovery32/run-result.json",
    ]
    ledger = CollectionLedger(ledger_path, historical, additional_budget=4 * 1024 ** 3)
    report: dict[str, Any] = {
        "schema_version": PILOT_SCHEMA_VERSION,
        "started_at": _utc_now(),
        "status": "EXECUTING",
        "config": config,
        "config_sha256": config_sha,
        "execution": {
            "collector_invoked": True,
            "execution_lock_acquired": False,
            "ledger_reserved": False,
            "ledger_settled": False,
            "remote_sentinel_downloads": 0,
        },
        "candidate_audit": [],
    }
    evidence_dir.mkdir(parents=True, exist_ok=True)
    report_path = evidence_dir / report_name
    if report_path.exists():
        raise PilotCollectionError("PILOT_REPORT_ALREADY_EXISTS")
    reserved = False
    settled = False
    try:
        lock_context = nullcontext() if lock_already_held else _execution_lock(execution_lock)
        with lock_context:
            report["execution"]["execution_lock_acquired"] = True
            reserved = ledger.reserve(batch_key, reservation_bytes, config_sha)
            if not reserved:
                raise PilotCollectionError("PILOT_BATCH_ALREADY_SETTLED")
            report["execution"]["ledger_reserved"] = True
            existing_ids = _existing_scene_ids(source_root)
            service.configure_metadata_budget(metadata_budget_bytes)
            search_payload = {
                "bbox": config["bbox"],
                "start_date": config["season"][0],
                "end_date": config["season"][1],
                "collection": config["collection"],
                "endpoint": config["endpoint"],
                "cloud_cover": config["cloud_cover_max"],
                "limit": 20,
                "sort_by_cloud": True,
                "include_raw": True,
            }
            try:
                search, search_attempts = search_stac_with_retry(search_payload)
            except Exception as exc:
                report["search_attempts"] = getattr(exc, "search_attempts", None)
                raise
            report["search_attempts"] = search_attempts
            report["search"] = {
                "endpoint": search["source"],
                "query": search["query"],
                "item_count": search["count"],
                "cloud_cover_response_verified": search["cloud_cover_response_verified"],
                "metadata_body_bytes": None,
                "metadata_budget_treatment": "UNMEASURED_CHARGE_FULL_RESERVATION",
            }
            accepted = None
            for item in search["items"]:
                audit = {
                    "scene_id": item.get("id"),
                    "cloud_cover": item.get("cloud_cover"),
                    "duplicate_scene_id": item.get("id") in existing_ids,
                }
                report["candidate_audit"].append(audit)
                if audit["duplicate_scene_id"]:
                    audit["status"] = "REJECTED_DUPLICATE_SCENE_ID"
                    continue
                asset = item.get("assets", {}).get("SCL")
                if not isinstance(asset, dict):
                    audit["status"] = "REJECTED_SCL_ASSET_MISSING"
                    continue
                try:
                    pixels, profile, transfer = service.read_cog_window(
                        asset["href"], config["bbox"], side=window_side,
                        max_transfer_bytes=min(PER_CANDIDATE_TRANSFER_BYTES * 4, reservation_bytes - metadata_budget_bytes),
                    )
                except Exception as exc:
                    audit.update(status="REJECTED_SCL_READ_FAILED", error_type=type(exc).__name__)
                    continue
                if pixels.shape[0] != 1 or profile.get("crs") is None:
                    audit["status"] = "REJECTED_SCL_GRID_INVALID"
                    continue
                resolution = [abs(float(profile["transform"].a)), abs(float(profile["transform"].e))]
                if max(abs(value - 20.0) for value in resolution) > 0.001:
                    audit.update(status="REJECTED_SCL_RESOLUTION_INVALID", resolution=resolution)
                    continue
                quality = _scl_quality(pixels[0])
                audit.update(status="ACCEPTED", resolution=resolution, transfer=transfer, quality=quality)
                accepted = (item, asset, pixels, profile, transfer, quality)
                break
            if accepted is None:
                raise PilotCollectionError("NO_NON_DUPLICATE_READABLE_SCL_CANDIDATE")
            item, asset, pixels, profile, transfer, quality = accepted
            cell_root.mkdir(parents=True, exist_ok=False)
            raw_scl = cell_root / "raw-SCL.tif"
            profile = {**profile, "driver": "GTiff", "count": 1, "dtype": "uint8"}
            for field in ("blockxsize", "blockysize", "tiled"):
                profile.pop(field, None)
            with rasterio.open(raw_scl, "w", **profile) as dataset:
                dataset.write(pixels.astype("uint8"))
            public_item = _redact_signed_urls(item.get("stac_feature", item))
            _write_json(cell_root / "stac-item.json", public_item)
            asset_record = {
                "path": str(raw_scl),
                "sha256": sha256_file(raw_scl),
                "bytes": raw_scl.stat().st_size,
                "scene_id": item["id"],
                "collection": item["collection"],
                "datetime": item.get("datetime"),
                "cloud_cover": item.get("cloud_cover"),
                "source_url": str(asset["href"]).split("?", 1)[0],
                "source_role": "SENTINEL_2_L2A_SCL_CAUSE_AND_OBSERVATION_EVIDENCE",
                "transfer": transfer,
                "quality": quality,
            }
            _write_json(cell_root / "pilot-asset.json", asset_record)
            report.update(
                status="COLLECTED_AND_SCL_QA_COMPLETED",
                completed_at=_utc_now(),
                accepted_asset=asset_record,
            )
            report["execution"]["remote_sentinel_downloads"] = 1
            metadata_budget = service.metadata_budget_status()
            charged_bytes = int(transfer["http_body_bytes"]) + int(metadata_budget["charged_bytes"])
            if charged_bytes > reservation_bytes:
                raise PilotCollectionError("PILOT_MEASURED_CHARGE_EXCEEDS_RESERVATION")
            report["budget"] = {
                "reservation_bytes": reservation_bytes,
                "measured_scl_range_body_bytes": int(transfer["http_body_bytes"]),
                "local_scl_file_bytes": int(raw_scl.stat().st_size),
                "metadata": metadata_budget,
                "ledger_charge_bytes": charged_bytes,
                "ledger_charge_reason": "Measured COG Range plus bounded metadata response bodies",
            }
            _write_json(report_path, report)
            ledger.settle(batch_key, charged_bytes, str(report_path))
            settled = True
            report["execution"]["ledger_settled"] = True
            _write_json(report_path, report)
    except Exception as exc:
        report.update(status="FAILED", completed_at=_utc_now(), error_type=type(exc).__name__, error=str(exc))
        if reserved and not settled:
            try:
                ledger.settle(batch_key, reservation_bytes, str(report_path))
                settled = True
                report["execution"]["ledger_settled"] = True
                report["budget_failure_policy"] = "FULL_RESERVATION_CHARGED_NO_AUTOMATIC_REFUND"
            except Exception as settle_exc:
                report["ledger_settle_error"] = f"{type(settle_exc).__name__}:{settle_exc}"
        _write_json(report_path, report)
        raise
    return report


def run_provisional_pilot(
    *, workspace: Path, boundary: PinnedFile, mosaic_manifest: PinnedFile,
    cross_check_decision: PinnedFile, source_root: Path, evidence_dir: Path,
    ledger_path: Path, execution_lock: Path,
) -> dict[str, Any]:
    workspace = workspace.resolve()
    evidence_dir = _inside(workspace, evidence_dir, "EVIDENCE_DIR")
    evidence_dir.mkdir(parents=True, exist_ok=True)
    priority = select_pilot_target(Path(mosaic_manifest.path))
    priority.update(
        boundary_sha256=boundary.sha256,
        cross_check_decision_sha256=cross_check_decision.sha256,
        source_mosaic_sha256=mosaic_manifest.sha256,
    )
    priority_path = evidence_dir / "36-cell-gap-priority.json"
    _write_json(priority_path, priority, exclusive=True)
    plan = build_gap_acquisition_plan(
        root=workspace,
        source=mosaic_manifest,
        boundaries=boundary,
        cross_check_decision=cross_check_decision,
        evidence_status="PROVISIONAL_REAL",
    )
    plan_path = evidence_dir / "provisional-gap-acquisition-plan.json"
    write_plan_json(plan, plan_path)
    preflight = inspect_preflight(
        workspace=workspace, source_root=source_root, ledger_path=ledger_path,
        execution_lock=execution_lock, priority=priority,
    )
    preflight_path = evidence_dir / "pilot-preflight.json"
    _write_json(preflight_path, preflight, exclusive=True)
    if preflight["status"] != "PASS":
        raise PilotCollectionError("PILOT_PREFLIGHT_BLOCKED:" + ",".join(preflight["errors"]))
    before = json.loads(Path(mosaic_manifest.path).read_text(encoding="utf-8"))
    report = collect_one_scl_pilot(
        workspace=workspace, source_root=source_root, evidence_dir=evidence_dir,
        priority=priority, ledger_path=ledger_path, execution_lock=execution_lock,
    )
    updated_manifest = build_local_scl_mosaics(
        Path(boundary.path), source_root, evidence_dir / "updated-mosaics", resolution_m=1000.0,
        execution_metadata={
            "collector_invoked": True,
            "remote_sentinel_downloads": 1,
            "ledger_written": True,
            "execution_lock_acquired": True,
        },
    )
    validation_path = evidence_dir / "updated-mosaic-validation.json"
    validation = validate_local_scl_mosaic_manifest(
        updated_manifest, output_path=validation_path, allow_execution=True,
    )
    after = json.loads(updated_manifest.read_text(encoding="utf-8"))
    selected_key = (priority["selected"]["province_id"], int(priority["selected"]["year"]))
    before_cell = next(row for row in before["cells"] if (row["province_id"], int(row["year"])) == selected_key)
    after_cell = next(row for row in after["cells"] if (row["province_id"], int(row["year"])) == selected_key)
    comparison = {
        "province_id": selected_key[0],
        "year": selected_key[1],
        "before": {
            "source_asset_count": before_cell["source_asset_count"],
            "observed_pixels": before_cell["observed_pixels"],
            "cause_pixels": before_cell["cause_pixels"],
        },
        "after": {
            "source_asset_count": after_cell["source_asset_count"],
            "observed_pixels": after_cell["observed_pixels"],
            "cause_pixels": after_cell["cause_pixels"],
        },
        "observed_pixel_delta": int(after_cell["observed_pixels"]) - int(before_cell["observed_pixels"]),
        "outside_footprint_pixel_delta": int(after_cell["cause_pixels"]["OUTSIDE_FOOTPRINT"]) - int(before_cell["cause_pixels"]["OUTSIDE_FOOTPRINT"]),
    }
    _write_json(evidence_dir / "before-after.json", comparison, exclusive=True)
    completion = {
        "schema_version": "province-year-provisional-pilot-completion/1.0",
        "status": "PILOT_COLLECTED_QA_AND_MOSAIC_UPDATED_BOUNDARY_APPROVAL_PENDING",
        "completed_at": _utc_now(),
        "gistaru": "SKIPPED_BY_USER_DECISION",
        "boundary": {"path": str(boundary.path), "sha256": boundary.sha256, "status": "PROVISIONAL_BIG_BASELINE"},
        "decision": {"path": str(cross_check_decision.path), "sha256": cross_check_decision.sha256},
        "priority": {"path": str(priority_path), "sha256": sha256_file(priority_path)},
        "plan": {"path": str(plan_path), "sha256": sha256_file(plan_path), "target_count": plan.target_count},
        "preflight": {"path": str(preflight_path), "sha256": sha256_file(preflight_path)},
        "pilot_report": {"path": str(evidence_dir / "pilot-acquisition-report.json"), "sha256": sha256_file(evidence_dir / "pilot-acquisition-report.json")},
        "updated_mosaic": {"path": str(updated_manifest), "sha256": sha256_file(updated_manifest), "validation": validation},
        "comparison": comparison,
        "execution": {"new_sentinel_downloads": 1, "collector_invoked": True, "ledger_written": True, "execution_lock_acquired": True, "training_runs": 0},
        "remaining_blockers": ["BOUNDARY_APPROVAL_PENDING", "NOT_AUTHORIZED_FOR_TRAINING_OR_DEPLOYMENT"],
    }
    _write_json(evidence_dir / "completion.json", completion, exclusive=True)
    return completion
