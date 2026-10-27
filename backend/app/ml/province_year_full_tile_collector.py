"""Guarded expansion of one pinned Sentinel-2 SCL window to its full MGRS tile."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping

import rasterio

from app.data import service
from app.data.budget import CollectionLedger
from app.ml.province_year_coverage import PinnedFile, sha256_file
from app.ml.province_year_evidence_builder import (
    build_local_scl_mosaics,
    validate_local_scl_mosaic_manifest,
)
from app.ml.province_year_pilot_collector import (
    _execution_lock,
    _inside,
    _scl_quality,
    _write_json,
    inspect_preflight,
)


FULL_TILE_DECISION_SCHEMA = "province-year-scl-full-tile-pilot-decision/1.0"
FULL_TILE_REPORT_SCHEMA = "province-year-scl-full-tile-pilot/1.0"
FULL_TILE_RESERVATION_BYTES = 64 * 1024 * 1024
FULL_TILE_METADATA_BUDGET_BYTES = 4 * 1024 * 1024
FULL_TILE_MAX_RANGE_BYTES = FULL_TILE_RESERVATION_BYTES - FULL_TILE_METADATA_BUDGET_BYTES
FULL_TILE_MAX_SIDE = 8192


class FullTileCollectionError(RuntimeError):
    """Raised when a pinned full-tile strategy pilot cannot safely continue."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_pinned_json(ref: PinnedFile, label: str) -> dict[str, Any]:
    path = Path(ref.path).resolve()
    if not path.is_file() or sha256_file(path) != ref.sha256:
        raise FullTileCollectionError(f"{label}_PIN_MISMATCH")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FullTileCollectionError(f"{label}_JSON_INVALID") from exc
    if not isinstance(value, dict):
        raise FullTileCollectionError(f"{label}_OBJECT_REQUIRED")
    return value


def validate_full_tile_decision(
    decision: PinnedFile,
    *,
    boundary_sha256: str,
    starting_mosaic_sha256: str,
    source_report_sha256: str,
) -> dict[str, Any]:
    document = _load_pinned_json(decision, "FULL_TILE_DECISION")
    if document.get("schema_version") != FULL_TILE_DECISION_SCHEMA:
        raise FullTileCollectionError("FULL_TILE_DECISION_SCHEMA_MISMATCH")
    if document.get("authorized_by") != "USER_EXPLICIT_INSTRUCTION":
        raise FullTileCollectionError("FULL_TILE_USER_AUTHORIZATION_REQUIRED")
    if document.get("decision") != "RUN_ONE_FULL_TILE_STRATEGY_PILOT":
        raise FullTileCollectionError("FULL_TILE_DECISION_MISMATCH")
    if document.get("boundary_sha256") != boundary_sha256:
        raise FullTileCollectionError("FULL_TILE_BOUNDARY_SHA_MISMATCH")
    if document.get("starting_mosaic_sha256") != starting_mosaic_sha256:
        raise FullTileCollectionError("FULL_TILE_MOSAIC_SHA_MISMATCH")
    if document.get("source_report_sha256") != source_report_sha256:
        raise FullTileCollectionError("FULL_TILE_SOURCE_REPORT_SHA_MISMATCH")
    policy = document.get("policy")
    if not isinstance(policy, dict) or (
        policy.get("max_full_tiles") != 1
        or policy.get("reservation_bytes") != FULL_TILE_RESERVATION_BYTES
        or policy.get("max_side") != FULL_TILE_MAX_SIDE
        or policy.get("stop_on_failure") is not True
    ):
        raise FullTileCollectionError("FULL_TILE_POLICY_MISMATCH")
    approvals = document.get("approvals")
    if not isinstance(approvals, dict) or (
        approvals.get("collection_pilot") is not True
        or approvals.get("automatic_training") is not False
        or approvals.get("automatic_deployment") is not False
    ):
        raise FullTileCollectionError("FULL_TILE_APPROVAL_BOUNDARY_MISMATCH")
    batch_key = document.get("batch_key")
    if not isinstance(batch_key, str) or not re.fullmatch(
        r"unit\d{3}-fulltile-[a-z0-9_]+-20\d{2}-\d{2}", batch_key
    ):
        raise FullTileCollectionError("FULL_TILE_BATCH_KEY_INVALID")
    source_window_gain = document.get("source_window_observed_gain_pixels")
    if source_window_gain is not None and (
        not isinstance(source_window_gain, int) or isinstance(source_window_gain, bool)
        or not 1 <= source_window_gain <= 100_000
    ):
        raise FullTileCollectionError("FULL_TILE_SOURCE_WINDOW_GAIN_INVALID")
    return document


def run_full_tile_strategy_pilot(
    *,
    workspace: Path,
    boundary: PinnedFile,
    starting_mosaic: PinnedFile,
    cross_check_decision: PinnedFile,
    source_report: PinnedFile,
    decision: PinnedFile,
    source_root: Path,
    evidence_dir: Path,
    ledger_path: Path,
    execution_lock: Path,
) -> dict[str, Any]:
    workspace = workspace.resolve()
    source_root = _inside(workspace, source_root, "SOURCE_ROOT")
    evidence_dir = _inside(workspace, evidence_dir, "EVIDENCE_DIR")
    ledger_path = _inside(workspace, ledger_path, "LEDGER")
    boundary_path = Path(boundary.path).resolve()
    mosaic_path = Path(starting_mosaic.path).resolve()
    if sha256_file(boundary_path) != boundary.sha256:
        raise FullTileCollectionError("BOUNDARY_PIN_MISMATCH")
    if sha256_file(mosaic_path) != starting_mosaic.sha256:
        raise FullTileCollectionError("STARTING_MOSAIC_PIN_MISMATCH")
    cross_check = _load_pinned_json(cross_check_decision, "CROSS_CHECK_DECISION")
    if (
        cross_check.get("decision") != "SKIP_GISTARU_BY_USER_DECISION"
        or cross_check.get("boundary_sha256") != boundary.sha256
    ):
        raise FullTileCollectionError("CROSS_CHECK_DECISION_MISMATCH")
    source = _load_pinned_json(source_report, "SOURCE_REPORT")
    accepted = source.get("accepted_asset")
    config = source.get("config")
    if not isinstance(accepted, dict) or not isinstance(config, dict):
        raise FullTileCollectionError("SOURCE_REPORT_CONTENT_INVALID")
    province_id = str(config.get("province_id"))
    year = int(config.get("year"))
    source_asset_path = _inside(workspace, Path(str(accepted.get("path"))), "SOURCE_ASSET")
    if not source_asset_path.is_file() or sha256_file(source_asset_path) != accepted.get("sha256"):
        raise FullTileCollectionError("SOURCE_ASSET_PIN_MISMATCH")
    stac_path = source_asset_path.with_name("stac-item.json")
    if not stac_path.is_file():
        raise FullTileCollectionError("SOURCE_STAC_ITEM_MISSING")
    stac_item = json.loads(stac_path.read_text(encoding="utf-8"))
    if stac_item.get("id") != accepted.get("scene_id"):
        raise FullTileCollectionError("SOURCE_STAC_SCENE_MISMATCH")
    scl_asset = (stac_item.get("assets") or {}).get("SCL")
    if not isinstance(scl_asset, dict) or not isinstance(scl_asset.get("href"), str):
        raise FullTileCollectionError("SOURCE_STAC_SCL_MISSING")
    full_tile_decision = validate_full_tile_decision(
        decision,
        boundary_sha256=boundary.sha256,
        starting_mosaic_sha256=starting_mosaic.sha256,
        source_report_sha256=source_report.sha256,
    )
    if full_tile_decision.get("scene_id") != accepted.get("scene_id"):
        raise FullTileCollectionError("FULL_TILE_SCENE_MISMATCH")
    if [full_tile_decision.get("province_id"), int(full_tile_decision.get("year"))] != [province_id, year]:
        raise FullTileCollectionError("FULL_TILE_CELL_MISMATCH")

    evidence_dir.mkdir(parents=True, exist_ok=True)
    if any(evidence_dir.iterdir()):
        raise FullTileCollectionError("FULL_TILE_EVIDENCE_DIR_NOT_EMPTY")
    priority = {
        "selected": {
            "province_id": province_id,
            "year": year,
            "cause": "OUTSIDE_FOOTPRINT",
            "strategy": "EXPAND_PINNED_SCENE_TO_FULL_MGRS_TILE",
        }
    }
    preflight = inspect_preflight(
        workspace=workspace,
        source_root=source_root,
        ledger_path=ledger_path,
        execution_lock=execution_lock,
        priority=priority,
        reservation_bytes=FULL_TILE_RESERVATION_BYTES,
    )
    preflight["source_report_sha256"] = source_report.sha256
    preflight["source_scene_id"] = accepted["scene_id"]
    _write_json(evidence_dir / "preflight.json", preflight, exclusive=True)
    if preflight["status"] != "PASS":
        raise FullTileCollectionError("FULL_TILE_PREFLIGHT_BLOCKED:" + ",".join(preflight["errors"]))

    batch_key = full_tile_decision["batch_key"]
    run_config = {
        "schema_version": FULL_TILE_REPORT_SCHEMA,
        "batch_key": batch_key,
        "province_id": province_id,
        "year": year,
        "scene_id": accepted["scene_id"],
        "source_report_sha256": source_report.sha256,
        "starting_mosaic_sha256": starting_mosaic.sha256,
        "boundary_sha256": boundary.sha256,
        "reservation_bytes": FULL_TILE_RESERVATION_BYTES,
        "metadata_budget_bytes": FULL_TILE_METADATA_BUDGET_BYTES,
        "max_range_bytes": FULL_TILE_MAX_RANGE_BYTES,
        "max_side": FULL_TILE_MAX_SIDE,
    }
    config_sha = hashlib.sha256(
        json.dumps(run_config, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    report: dict[str, Any] = {
        "schema_version": FULL_TILE_REPORT_SCHEMA,
        "status": "EXECUTING",
        "started_at": _utc_now(),
        "config": run_config,
        "config_sha256": config_sha,
        "execution": {
            "collector_invoked": True,
            "remote_sentinel_downloads": 0,
            "ledger_reserved": False,
            "ledger_settled": False,
            "training_runs": 0,
            "deployment_runs": 0,
        },
    }
    report_path = evidence_dir / "full-tile-acquisition-report.json"
    historical = [
        workspace / "data/first-group-annual/run-result.json",
        workspace / "data/first-group-recovery32/run-result.json",
    ]
    ledger = CollectionLedger(ledger_path, historical, additional_budget=4 * 1024 ** 3)
    reserved = False
    settled = False
    metadata_budget: Mapping[str, Any] | None = None
    try:
        with _execution_lock(execution_lock):
            report["execution"]["execution_lock_acquired"] = True
            reserved = ledger.reserve(batch_key, FULL_TILE_RESERVATION_BYTES, config_sha)
            if not reserved:
                raise FullTileCollectionError("FULL_TILE_BATCH_ALREADY_SETTLED")
            report["execution"]["ledger_reserved"] = True
            service.configure_metadata_budget(FULL_TILE_METADATA_BUDGET_BYTES)
            pixels, profile, transfer = service.read_cog_full_tile(
                scl_asset["href"],
                max_transfer_bytes=FULL_TILE_MAX_RANGE_BYTES,
                max_side=FULL_TILE_MAX_SIDE,
            )
            quality = _scl_quality(pixels[0])
            resolution = [abs(float(profile["transform"].a)), abs(float(profile["transform"].e))]
            if max(abs(value - 20.0) for value in resolution) > 0.001:
                raise FullTileCollectionError("FULL_TILE_SCL_RESOLUTION_INVALID")
            expected_shape = scl_asset.get("proj:shape")
            actual_shape = [int(pixels.shape[1]), int(pixels.shape[2])]
            if isinstance(expected_shape, list) and [int(value) for value in expected_shape] != actual_shape:
                raise FullTileCollectionError("FULL_TILE_STAC_SHAPE_MISMATCH")
            batch_root = source_root / batch_key
            cell_root = batch_root / f"{province_id}-fulltile-00-{year}"
            cell_root.mkdir(parents=True, exist_ok=False)
            raw_scl = cell_root / "raw-SCL.tif"
            output_profile = {**profile, "driver": "GTiff", "count": 1, "dtype": "uint8", "compress": "deflate"}
            for field in ("blockxsize", "blockysize", "tiled"):
                output_profile.pop(field, None)
            with rasterio.open(raw_scl, "w", **output_profile) as dataset:
                dataset.write(pixels.astype("uint8"))
            _write_json(cell_root / "stac-item.json", stac_item)
            asset_record = {
                "path": str(raw_scl),
                "sha256": sha256_file(raw_scl),
                "bytes": raw_scl.stat().st_size,
                "scene_id": accepted["scene_id"],
                "expands_source_asset_sha256": accepted["sha256"],
                "collection": accepted.get("collection"),
                "datetime": accepted.get("datetime"),
                "cloud_cover": accepted.get("cloud_cover"),
                "source_url": str(scl_asset["href"]).split("?", 1)[0],
                "source_role": "SENTINEL_2_L2A_SCL_FULL_TILE_STRATEGY_EVIDENCE",
                "shape": actual_shape,
                "resolution": resolution,
                "quality": quality,
                "transfer": transfer,
            }
            _write_json(cell_root / "full-tile-asset.json", asset_record)
            metadata_budget = service.metadata_budget_status()
            charge = int(transfer["http_body_bytes"]) + int(metadata_budget["charged_bytes"])
            if charge > FULL_TILE_RESERVATION_BYTES:
                raise FullTileCollectionError("FULL_TILE_MEASURED_CHARGE_EXCEEDS_RESERVATION")
            report.update(
                status="COLLECTED_AND_SCL_QA_COMPLETED",
                completed_at=_utc_now(),
                accepted_asset=asset_record,
                budget={
                    "reservation_bytes": FULL_TILE_RESERVATION_BYTES,
                    "measured_scl_range_body_bytes": int(transfer["http_body_bytes"]),
                    "source_content_length_bytes": int(transfer["source_content_length_bytes"]),
                    "local_scl_file_bytes": int(raw_scl.stat().st_size),
                    "metadata": metadata_budget,
                    "ledger_charge_bytes": charge,
                },
            )
            report["execution"]["remote_sentinel_downloads"] = 1
            _write_json(report_path, report)
            ledger.settle(batch_key, charge, str(report_path))
            settled = True
            report["execution"]["ledger_settled"] = True
            _write_json(report_path, report)
    except Exception as exc:
        report.update(status="FAILED", completed_at=_utc_now(), error_type=type(exc).__name__, error=str(exc))
        if reserved and not settled:
            try:
                ledger.settle(batch_key, FULL_TILE_RESERVATION_BYTES, str(report_path))
                settled = True
                report["execution"]["ledger_settled"] = True
                report["budget_failure_policy"] = "FULL_RESERVATION_CHARGED_NO_AUTOMATIC_REFUND"
            except Exception as settle_exc:
                report["ledger_settle_error"] = f"{type(settle_exc).__name__}:{settle_exc}"
        _write_json(report_path, report)
        raise
    finally:
        service.configure_metadata_budget(None)

    updated_manifest = build_local_scl_mosaics(
        boundary_path,
        source_root,
        evidence_dir / "updated-mosaics",
        resolution_m=1000.0,
        execution_metadata={
            "collector_invoked": True,
            "remote_sentinel_downloads": 1,
            "ledger_written": True,
            "execution_lock_acquired": True,
        },
    )
    validation = validate_local_scl_mosaic_manifest(
        updated_manifest,
        output_path=evidence_dir / "updated-mosaic-validation.json",
        allow_execution=True,
    )
    before = json.loads(mosaic_path.read_text(encoding="utf-8"))
    after = json.loads(updated_manifest.read_text(encoding="utf-8"))
    before_cell = next(row for row in before["cells"] if row["province_id"] == province_id and int(row["year"]) == year)
    after_cell = next(row for row in after["cells"] if row["province_id"] == province_id and int(row["year"]) == year)
    before_observed = sum(int(row["observed_pixels"]) for row in before["cells"])
    after_observed = sum(int(row["observed_pixels"]) for row in after["cells"])
    completion = {
        "schema_version": "province-year-scl-full-tile-pilot-completion/1.0",
        "status": "FULL_TILE_PILOT_COMPLETED_MORE_GAPS_REMAIN",
        "completed_at": _utc_now(),
        "strategy_comparison": {
            "window_side": int(source["config"]["window_side"]),
            "window_range_body_bytes": int(accepted["transfer"]["http_body_bytes"]),
            "window_observed_gain_pixels": int(
                full_tile_decision.get("source_window_observed_gain_pixels", 1606)
            ),
            "full_tile_shape": report["accepted_asset"]["shape"],
            "full_tile_range_body_bytes": int(report["budget"]["measured_scl_range_body_bytes"]),
            "full_tile_content_length_bytes": int(report["budget"]["source_content_length_bytes"]),
            "cell_observed_before": int(before_cell["observed_pixels"]),
            "cell_observed_after": int(after_cell["observed_pixels"]),
            "cell_observed_gain_pixels": int(after_cell["observed_pixels"]) - int(before_cell["observed_pixels"]),
            "total_observed_before": before_observed,
            "total_observed_after": after_observed,
            "total_observed_gain_pixels": after_observed - before_observed,
        },
        "updated_mosaic": {
            "path": str(updated_manifest),
            "sha256": sha256_file(updated_manifest),
            "validation": validation,
        },
        "execution": {
            "remote_sentinel_downloads": 1,
            "execution_lock_released": not execution_lock.exists(),
            "training_runs": 0,
            "deployment_runs": 0,
        },
    }
    _write_json(evidence_dir / "completion.json", completion, exclusive=True)
    return completion
