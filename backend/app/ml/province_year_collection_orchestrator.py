"""Guarded three-window Sentinel-2 SCL collection batch orchestration."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import threading
from typing import Any, Mapping

from app.data import service
from app.ml.province_year_coverage import PinnedFile, sha256_file
from app.ml.province_year_evidence_builder import (
    build_local_scl_mosaics,
    validate_local_scl_mosaic_manifest,
)
from app.ml.province_year_pilot_collector import (
    _execution_lock,
    _write_json,
    collect_one_scl_pilot,
    inspect_preflight,
    select_pilot_target,
)


ORCHESTRATION_DECISION_SCHEMA = "province-year-collection-orchestration-decision/1.0"
AUTOMATED_BATCH_SIZE = 3
AUTOMATED_WINDOW_SIDE = 2048
AUTOMATED_RESERVATION_BYTES = 48 * 1024 * 1024
AUTOMATED_METADATA_BUDGET_BYTES = 4 * 1024 * 1024


class CollectionOrchestrationError(RuntimeError):
    """Raised when the automated collection policy cannot safely continue."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_pinned_json(ref: PinnedFile, label: str) -> dict[str, Any]:
    path = Path(ref.path).resolve()
    if not path.is_file() or sha256_file(path) != ref.sha256:
        raise CollectionOrchestrationError(f"{label}_PIN_MISMATCH")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CollectionOrchestrationError(f"{label}_JSON_INVALID") from exc
    if not isinstance(value, dict):
        raise CollectionOrchestrationError(f"{label}_OBJECT_REQUIRED")
    return value


def validate_orchestration_decision(
    decision: PinnedFile, *, boundary_sha256: str, starting_mosaic_sha256: str,
) -> dict[str, Any]:
    document = _load_pinned_json(decision, "ORCHESTRATION_DECISION")
    if document.get("schema_version") != ORCHESTRATION_DECISION_SCHEMA:
        raise CollectionOrchestrationError("ORCHESTRATION_DECISION_SCHEMA_MISMATCH")
    if document.get("authorized_by") != "USER_EXPLICIT_INSTRUCTION":
        raise CollectionOrchestrationError("ORCHESTRATION_USER_AUTHORIZATION_REQUIRED")
    if document.get("decision") != "AUTOMATE_GAP_COLLECTION_WITH_APPROVAL_GATED_TRAINING_DEPLOYMENT":
        raise CollectionOrchestrationError("ORCHESTRATION_DECISION_MISMATCH")
    if not isinstance(document.get("batch_run_id"), str) or not re.fullmatch(
        r"unit\d{3}-auto(?:-retry\d+)?", document["batch_run_id"]
    ):
        raise CollectionOrchestrationError("ORCHESTRATION_BATCH_RUN_ID_INVALID")
    if document.get("boundary_sha256") != boundary_sha256:
        raise CollectionOrchestrationError("ORCHESTRATION_BOUNDARY_SHA_MISMATCH")
    if document.get("starting_mosaic_sha256") != starting_mosaic_sha256:
        raise CollectionOrchestrationError("ORCHESTRATION_MOSAIC_SHA_MISMATCH")
    policy = document.get("policy")
    if not isinstance(policy, dict) or (
        policy.get("max_windows_per_batch") != AUTOMATED_BATCH_SIZE
        or policy.get("window_side_scl20m") != AUTOMATED_WINDOW_SIDE
        or policy.get("reservation_bytes_per_window") != AUTOMATED_RESERVATION_BYTES
        or policy.get("stop_on_first_failure") is not True
        or policy.get("stop_on_http_429") is not True
        or policy.get("distinct_province_year_per_batch") is not True
    ):
        raise CollectionOrchestrationError("ORCHESTRATION_POLICY_MISMATCH")
    approvals = document.get("approvals")
    if not isinstance(approvals, dict) or (
        approvals.get("collection_batch") is not True
        or approvals.get("automatic_training") is not False
        or approvals.get("automatic_deployment") is not False
    ):
        raise CollectionOrchestrationError("ORCHESTRATION_APPROVAL_BOUNDARY_MISMATCH")
    return document


def estimate_remaining_scale(mosaic_manifest: Path) -> dict[str, Any]:
    document = json.loads(Path(mosaic_manifest).read_text(encoding="utf-8"))
    outside = sum(int(row["cause_pixels"]["OUTSIDE_FOOTPRINT"]) for row in document["cells"])
    pilot_gain = 25
    area_scale = (AUTOMATED_WINDOW_SIDE // 256) ** 2
    expected_gain = pilot_gain * area_scale
    estimated_windows = math.ceil(outside / expected_gain) if expected_gain else None
    return {
        "outside_footprint_pixels_before": outside,
        "pilot_256_observed_gain_pixels": pilot_gain,
        "window_area_scale_vs_pilot": area_scale,
        "planning_gain_pixels_per_2048_window": expected_gain,
        "rough_windows_to_full_inventory_coverage": estimated_windows,
        "estimate_limitations": [
            "Area scaling ignores coastlines, scene edges, repeat overlap, clouds, and MGRS tile boundaries.",
            "This estimate is for the 1 km inventory, not final native-resolution scientific completeness.",
        ],
    }


def run_automated_collection_batch(
    *, workspace: Path, boundary: PinnedFile, starting_mosaic: PinnedFile,
    cross_check_decision: PinnedFile, orchestration_decision: PinnedFile,
    source_root: Path, evidence_dir: Path, ledger_path: Path, execution_lock: Path,
) -> dict[str, Any]:
    workspace = workspace.resolve()
    evidence_dir = evidence_dir.resolve()
    evidence_dir.relative_to(workspace)
    boundary_path = Path(boundary.path).resolve()
    mosaic_path = Path(starting_mosaic.path).resolve()
    if sha256_file(boundary_path) != boundary.sha256:
        raise CollectionOrchestrationError("BOUNDARY_PIN_MISMATCH")
    if sha256_file(mosaic_path) != starting_mosaic.sha256:
        raise CollectionOrchestrationError("STARTING_MOSAIC_PIN_MISMATCH")
    cross_check = _load_pinned_json(cross_check_decision, "CROSS_CHECK_DECISION")
    if (
        cross_check.get("decision") != "SKIP_GISTARU_BY_USER_DECISION"
        or cross_check.get("boundary_sha256") != boundary.sha256
    ):
        raise CollectionOrchestrationError("CROSS_CHECK_DECISION_MISMATCH")
    decision = validate_orchestration_decision(
        orchestration_decision,
        boundary_sha256=boundary.sha256,
        starting_mosaic_sha256=starting_mosaic.sha256,
    )
    evidence_dir.mkdir(parents=True, exist_ok=True)
    if any(evidence_dir.iterdir()):
        raise CollectionOrchestrationError("ORCHESTRATION_EVIDENCE_DIR_NOT_EMPTY")

    targets = []
    excluded: set[tuple[str, int]] = set()
    for index in range(AUTOMATED_BATCH_SIZE):
        priority = select_pilot_target(mosaic_path, exclude_cells=excluded)
        selected = priority["selected"]
        cell = (str(selected["province_id"]), int(selected["year"]))
        excluded.add(cell)
        priority.update(
            batch_index=index + 1,
            boundary_sha256=boundary.sha256,
            cross_check_decision_sha256=cross_check_decision.sha256,
            source_mosaic_sha256=starting_mosaic.sha256,
        )
        targets.append(priority)
    scale = estimate_remaining_scale(mosaic_path)
    plan = {
        "schema_version": "province-year-automated-collection-batch-plan/1.0",
        "created_at": _utc_now(),
        "status": "PLANNED_GUARDED_EXECUTION",
        "policy": decision["policy"],
        "scale_estimate": scale,
        "targets": [target["selected"] for target in targets],
        "training_authorized": False,
        "deployment_authorized": False,
    }
    plan_path = evidence_dir / "batch-plan.json"
    _write_json(plan_path, plan, exclusive=True)
    preflight = inspect_preflight(
        workspace=workspace,
        source_root=source_root,
        ledger_path=ledger_path,
        execution_lock=execution_lock,
        priority=targets[0],
        reservation_bytes=AUTOMATED_BATCH_SIZE * AUTOMATED_RESERVATION_BYTES,
    )
    preflight["batch_size"] = AUTOMATED_BATCH_SIZE
    preflight["per_window_reservation_bytes"] = AUTOMATED_RESERVATION_BYTES
    preflight_path = evidence_dir / "batch-preflight.json"
    _write_json(preflight_path, preflight, exclusive=True)
    if preflight["status"] != "PASS":
        raise CollectionOrchestrationError("AUTOMATED_BATCH_PREFLIGHT_BLOCKED:" + ",".join(preflight["errors"]))

    reports = []
    errors = []
    circuit = threading.Event()
    service.configure_request_circuit(circuit)
    service.configure_request_spacing(1)
    try:
        with _execution_lock(execution_lock):
            for index, priority in enumerate(targets, 1):
                selected = priority["selected"]
                batch_key = (
                    f"{decision['batch_run_id']}-{index:02d}-{selected['province_id']}-{int(selected['year'])}"
                )
                try:
                    report = collect_one_scl_pilot(
                        workspace=workspace,
                        source_root=source_root,
                        evidence_dir=evidence_dir,
                        priority=priority,
                        ledger_path=ledger_path,
                        execution_lock=execution_lock,
                        batch_key_override=batch_key,
                        report_name=f"batch-item-{index:02d}-report.json",
                        window_side=AUTOMATED_WINDOW_SIDE,
                        reservation_bytes=AUTOMATED_RESERVATION_BYTES,
                        metadata_budget_bytes=AUTOMATED_METADATA_BUDGET_BYTES,
                        lock_already_held=True,
                    )
                    reports.append(report)
                except Exception as exc:
                    errors.append({"index": index, "error_type": type(exc).__name__, "error": str(exc)})
                    break
                if circuit.is_set():
                    errors.append({"index": index, "error_type": "HTTP_429_CIRCUIT", "error": "shared circuit opened"})
                    break
    finally:
        service.configure_request_circuit(None)
        service.configure_request_spacing(0)
    if not reports:
        _write_json(evidence_dir / "failure-completion.json", {
            "schema_version": "province-year-automated-collection-batch-failure/1.0",
            "status": "AUTOMATED_BATCH_STOPPED_WITHOUT_NEW_ASSET",
            "completed_at": _utc_now(),
            "errors": errors,
            "execution": {
                "remote_sentinel_downloads": 0,
                "training_runs": 0,
                "deployment_runs": 0,
                "execution_lock_released": not execution_lock.exists(),
            },
            "next_action": "RETRY_TRANSIENT_STAC_FAILURE_WITH_NEW_BATCH_KEY_AND_BOUNDED_ATTEMPTS",
        }, exclusive=True)
        raise CollectionOrchestrationError("AUTOMATED_BATCH_NO_SUCCESSFUL_COLLECTION")

    updated_manifest = build_local_scl_mosaics(
        boundary_path,
        source_root,
        evidence_dir / "updated-mosaics",
        resolution_m=1000.0,
        execution_metadata={
            "collector_invoked": True,
            "remote_sentinel_downloads": len(reports),
            "ledger_written": True,
            "execution_lock_acquired": True,
        },
    )
    validation_path = evidence_dir / "updated-mosaic-validation.json"
    validation = validate_local_scl_mosaic_manifest(
        updated_manifest, output_path=validation_path, allow_execution=True,
    )
    before_doc = json.loads(mosaic_path.read_text(encoding="utf-8"))
    after_doc = json.loads(updated_manifest.read_text(encoding="utf-8"))
    before_observed = sum(int(row["observed_pixels"]) for row in before_doc["cells"])
    after_observed = sum(int(row["observed_pixels"]) for row in after_doc["cells"])
    before_outside = sum(int(row["cause_pixels"]["OUTSIDE_FOOTPRINT"]) for row in before_doc["cells"])
    after_outside = sum(int(row["cause_pixels"]["OUTSIDE_FOOTPRINT"]) for row in after_doc["cells"])
    comparisons = []
    for priority in targets[:len(reports)]:
        selected = priority["selected"]
        key = (str(selected["province_id"]), int(selected["year"]))
        before = next(row for row in before_doc["cells"] if (row["province_id"], int(row["year"])) == key)
        after = next(row for row in after_doc["cells"] if (row["province_id"], int(row["year"])) == key)
        comparisons.append({
            "province_id": key[0], "year": key[1],
            "observed_before": int(before["observed_pixels"]),
            "observed_after": int(after["observed_pixels"]),
            "observed_delta": int(after["observed_pixels"]) - int(before["observed_pixels"]),
            "outside_before": int(before["cause_pixels"]["OUTSIDE_FOOTPRINT"]),
            "outside_after": int(after["cause_pixels"]["OUTSIDE_FOOTPRINT"]),
            "outside_delta": int(after["cause_pixels"]["OUTSIDE_FOOTPRINT"]) - int(before["cause_pixels"]["OUTSIDE_FOOTPRINT"]),
        })
    total_charge = sum(int(report["budget"]["ledger_charge_bytes"]) for report in reports)
    completion = {
        "schema_version": "province-year-automated-collection-batch-completion/1.0",
        "status": (
            "AUTOMATED_BATCH_COMPLETED_MORE_GAPS_REMAIN"
            if len(reports) == AUTOMATED_BATCH_SIZE and not errors
            else "AUTOMATED_BATCH_PARTIAL_STOPPED"
        ),
        "completed_at": _utc_now(),
        "batch_size_planned": AUTOMATED_BATCH_SIZE,
        "batch_size_completed": len(reports),
        "errors": errors,
        "gates": {
            "gistaru": "SKIPPED_BY_USER_DECISION",
            "boundary": "PROVISIONAL_BIG_BASELINE_BOUNDARY_APPROVAL_PENDING",
            "automatic_training": "BLOCKED_REQUIRES_HUMAN_APPROVAL",
            "automatic_deployment": "BLOCKED_REQUIRES_HUMAN_APPROVAL",
        },
        "scale_estimate": scale,
        "reports": [{
            "scene_id": report["accepted_asset"]["scene_id"],
            "province_id": report["config"]["province_id"],
            "year": report["config"]["year"],
            "quality": report["accepted_asset"]["quality"],
            "range_body_bytes": report["accepted_asset"]["transfer"]["http_body_bytes"],
            "local_scl_bytes": report["accepted_asset"]["bytes"],
            "ledger_charge_bytes": report["budget"]["ledger_charge_bytes"],
        } for report in reports],
        "budget": {
            "total_reservation_upper_bound_bytes": AUTOMATED_BATCH_SIZE * AUTOMATED_RESERVATION_BYTES,
            "total_ledger_charge_bytes": total_charge,
        },
        "comparison": {
            "observed_before": before_observed,
            "observed_after": after_observed,
            "observed_delta": after_observed - before_observed,
            "outside_before": before_outside,
            "outside_after": after_outside,
            "outside_delta": after_outside - before_outside,
            "cells": comparisons,
        },
        "updated_mosaic": {
            "path": str(updated_manifest),
            "sha256": sha256_file(updated_manifest),
            "validation": validation,
        },
        "execution": {
            "collector_invoked": True,
            "remote_sentinel_downloads": len(reports),
            "ledger_written": True,
            "execution_lock_released": not execution_lock.exists(),
            "training_runs": 0,
            "deployment_runs": 0,
        },
    }
    completion_path = evidence_dir / "completion.json"
    _write_json(completion_path, completion, exclusive=True)
    return completion
