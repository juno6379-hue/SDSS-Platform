"""FastAPI routes for bounded MLOps evidence and explicit execution requests.

The summary route is fail-closed: inventory facts may be shown, while coverage,
model metrics, promotion, and deployment stay blocked until their own evidence
contracts are satisfied.
"""

import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from fastapi import APIRouter, Body, HTTPException, Request
from pydantic import BaseModel, Field

from .ml.province_month_coverage_audit import build_province_month_audit
from .ml.recovery_rate_engine import compute_recovery_metrics
from .store import Store, now

SUMMARY_SCHEMA_VERSION = "2.1"
MODEL_EVIDENCE_RELATIVE_PATH = Path("docs/lcluc/v3/06_model_experiments_manifest.json")


class RetrainRequestPayload(BaseModel):
    model_id: str = Field(..., description="Target model identifier to retrain")
    target_version: Optional[str] = Field(default=None, description="Target model version")
    dataset_version: Optional[str] = Field(default="fg-annual-2020-2025-v2", description="Dataset registry version")
    epochs: Optional[int] = Field(default=50, description="Training epochs")
    holdout_split: Optional[str] = Field(default="test_west_java_val_banten", description="Geographic holdout split")
    priority: Optional[str] = Field(default="high", description="Job execution priority")


class ApprovalRequestPayload(BaseModel):
    model_id: str = Field(..., description="Target model ID")
    version: str = Field(..., description="Model version")
    target_env: str = Field(default="production", description="Target deployment environment")
    requested_by: str = Field(default="GeoAI MLOps Team", description="Name or role of applicant")
    rationale: str = Field(..., description="Scientific or operational justification")


def _load_model_evidence(data_root: Path) -> tuple[Dict[str, Any], Optional[str]]:
    """Read the bounded Unit352 manifest without promoting scenario metrics."""
    candidates = [
        data_root / MODEL_EVIDENCE_RELATIVE_PATH,
        data_root.parent / MODEL_EVIDENCE_RELATIVE_PATH,
    ]
    manifest_path = next((path for path in candidates if path.is_file()), None)
    if manifest_path is None:
        return {}, "MODEL_EVIDENCE_MISSING"
    try:
        payload = manifest_path.read_bytes()
        value = json.loads(payload.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}, "MODEL_EVIDENCE_INVALID"
    if not isinstance(value, dict):
        return {}, "MODEL_EVIDENCE_INVALID"
    if value.get("schema_version") != "3.1":
        return {}, "MODEL_EVIDENCE_SCHEMA_UNSUPPORTED"
    required_booleans = (
        "training_executed",
        "prediction_artifacts_verified",
        "scientific_accuracy_validated",
        "promotion_authorized",
    )
    if any(type(value.get(field)) is not bool for field in required_booleans):
        return {}, "MODEL_EVIDENCE_CONTRACT_INCOMPLETE"
    value["_source_sha256"] = hashlib.sha256(payload).hexdigest()
    return value, None


def _blocked_pipeline_steps() -> List[Dict[str, Any]]:
    names = (
        (1, "collection", "수집", "🛰️"),
        (2, "preprocessing", "전처리", "⚙️"),
        (3, "label_qa", "라벨QA", "🏷️"),
        (4, "model_training", "모델학습", "🧠"),
        (5, "validation", "성능검증", "📊"),
        (6, "approval", "승인", "🛡️"),
        (7, "deployment", "배포", "🚀"),
        (8, "monitoring", "모니터링", "📈"),
        (9, "retraining", "재학습", "🔄"),
    )
    return [
        {
            "step": step,
            "id": step_id,
            "name": name,
            "status": "blocked",
            "reason_code": "NO_VERIFIED_EXECUTION_EVIDENCE",
            "icon": icon,
        }
        for step, step_id, name, icon in names
    ]


def _build_retraining_readiness(
    *,
    coverage_status: str,
    training_executed: bool,
    predictions_verified: bool,
    scientific_accuracy_validated: bool,
    promotion_authorized: bool,
    deployment_executed: bool,
) -> Dict[str, Any]:
    """Describe the evidence chain required before retraining or promotion.

    Confidence is a model-output property and must be calibrated on a pinned
    calibration set. Accuracy/F1/mIoU require predictions compared with an
    independent labelled holdout. Neither an Esri weak label nor a reference
    map can satisfy the independent-ground-truth gate.
    """
    collection_ready = coverage_status == "VERIFIED_REAL"
    stages = [
        {
            "id": "gap_measurement",
            "name": "주 전체 누락 측정",
            "status": "ready" if collection_ready else "blocked",
            "reason_code": None
            if collection_ready
            else "BLOCKED_MISSING_AUTHORITATIVE_BOUNDARY_AND_CAUSE_MOSAICS",
            "required_evidence": [
                "authoritative_boundary_sha256",
                "same_grid_observed_mask_sha256",
                "same_grid_cause_mask_sha256",
            ],
        },
        {
            "id": "collection_execution",
            "name": "Sentinel-2 누락 관측 수집",
            "status": "blocked",
            "reason_code": "NO_EXECUTED_PROVINCE_GAP_COLLECTION",
            "required_evidence": [
                "collection_plan_sha256",
                "sentinel2_asset_sha256",
                "scl_asset_sha256",
                "collection_receipt_sha256",
            ],
        },
        {
            "id": "dataset_freeze",
            "name": "품질검사와 학습 데이터 동결",
            "status": "blocked",
            "reason_code": "NO_IMMUTABLE_RETRAINING_DATASET_PIN",
            "required_evidence": [
                "quality_gate_report_sha256",
                "dataset_manifest_sha256",
                "split_manifest_sha256",
                "scene_leakage_zero",
            ],
        },
        {
            "id": "training",
            "name": "재학습",
            "status": "complete" if training_executed else "blocked",
            "reason_code": None if training_executed else "NO_EXECUTED_TRAINING_RUN",
            "required_evidence": ["training_run_id", "checkpoint_sha256", "training_log_sha256"],
        },
        {
            "id": "prediction",
            "name": "고정 holdout 예측",
            "status": "complete" if predictions_verified else "blocked",
            "reason_code": None
            if predictions_verified
            else "NO_MEASURED_PREDICTION_ARTIFACTS",
            "required_evidence": ["prediction_manifest_sha256", "holdout_manifest_sha256"],
        },
        {
            "id": "confidence_calibration",
            "name": "신뢰도 보정",
            "status": "blocked",
            "reason_code": "NO_VERIFIED_CONFIDENCE_CALIBRATION",
            "required_evidence": [
                "calibration_set_sha256",
                "reliability_bins",
                "expected_calibration_error",
                "brier_score",
            ],
        },
        {
            "id": "independent_accuracy",
            "name": "독립 정확도 평가",
            "status": "complete" if scientific_accuracy_validated else "blocked",
            "reason_code": None
            if scientific_accuracy_validated
            else "NO_INDEPENDENT_GROUND_TRUTH_EVALUATION",
            "required_evidence": [
                "independent_label_manifest_sha256",
                "overall_accuracy",
                "macro_f1",
                "miou",
                "per_class_metrics",
            ],
        },
        {
            "id": "human_approval",
            "name": "사람 승인",
            "status": "complete" if promotion_authorized else "blocked",
            "reason_code": None if promotion_authorized else "PROMOTION_NOT_AUTHORIZED",
            "required_evidence": ["approval_record_sha256", "approver", "approved_at"],
        },
        {
            "id": "promotion_and_deployment",
            "name": "승격·배포·롤백 준비",
            "status": "complete" if deployment_executed else "blocked",
            "reason_code": None if deployment_executed else "DEPLOYMENT_NOT_EXECUTED",
            "required_evidence": [
                "promotion_receipt_sha256",
                "deployment_receipt_sha256",
                "rollback_target_sha256",
            ],
        },
    ]
    pipeline_complete = collection_ready and all(
        stage["status"] == "complete" for stage in stages[1:]
    )
    return {
        "schema_version": "retraining-readiness/1.0",
        "status": "ready" if pipeline_complete else "blocked",
        "pipeline_complete": pipeline_complete,
        "retrain_allowed": False,
        "automatic_gate_bypass_allowed": False,
        "weak_labels_can_measure_accuracy": False,
        "reference_landcover_can_replace_observations": False,
        "stages": stages,
        "confidence": {
            "value": None,
            "status": "blocked",
            "reason_code": "NO_VERIFIED_CONFIDENCE_CALIBRATION",
            "meaning": "MODEL_PROBABILITY_CALIBRATION_NOT_CORRECTNESS",
        },
        "accuracy": {
            "overall_accuracy": None,
            "macro_f1": None,
            "miou": None,
            "status": "blocked" if not scientific_accuracy_validated else "verified",
            "reason_code": None
            if scientific_accuracy_validated
            else "NO_INDEPENDENT_GROUND_TRUTH_EVALUATION",
            "independent_ground_truth_required": True,
        },
    }


def _build_fail_closed_summary(store: Store) -> Dict[str, Any]:
    reason_codes: List[str] = []
    audit = None
    try:
        audit = build_province_month_audit(store.root)
    except Exception:
        reason_codes.append("COVERAGE_AUDIT_UNAVAILABLE")

    try:
        recovery = compute_recovery_metrics(store.root.parent)
        if recovery.evidence_status == "BLOCKED" and recovery.blocking_reason:
            reason_codes.append(recovery.blocking_reason)
    except Exception:
        recovery = None
        reason_codes.append("RECOVERY_EVIDENCE_UNAVAILABLE")

    manifest, manifest_error = _load_model_evidence(store.root)
    if manifest_error:
        reason_codes.append(manifest_error)

    training_executed = manifest.get("training_executed") is True
    predictions_verified = manifest.get("prediction_artifacts_verified") is True
    scientific_accuracy_validated = manifest.get("scientific_accuracy_validated") is True
    promotion_authorized = manifest.get("promotion_authorized") is True
    metrics_verified = training_executed and predictions_verified and scientific_accuracy_validated
    deployment_executed = manifest.get("deployment_executed") is True
    if not training_executed:
        reason_codes.append("NO_EXECUTED_TRAINING_RUN")
    if not predictions_verified:
        reason_codes.append("NO_MEASURED_PREDICTION_ARTIFACTS")
    if not metrics_verified:
        reason_codes.append("NO_VERIFIED_MODEL_METRICS")
    if not promotion_authorized:
        reason_codes.append("PROMOTION_NOT_AUTHORIZED")
    if not deployment_executed:
        reason_codes.append("DEPLOYMENT_NOT_EXECUTED")

    try:
        approvals = []
        for item in store.list("mlops_approvals"):
            approvals.append(
                {
                    **item,
                    "original_status": item.get("status"),
                    "status": "미검증 기록",
                    "status_code": "unverified",
                    "evidence_status": "IMPLEMENTED_UNVERIFIED",
                    "human_approval_verified": False,
                }
            )
    except Exception:
        approvals = []
        reason_codes.append("APPROVAL_STORE_UNAVAILABLE")

    if audit is None:
        provinces = []
        coverage_status = "BLOCKED_AUDIT_UNAVAILABLE"
        coverage_audit: Dict[str, Any] = {
            "status": coverage_status,
            "evidence_status": "BLOCKED",
            "source_sha256": None,
            "total_cells": 432,
            "total_unique_scenes": None,
            "total_patches_inventory": None,
            "total_eligible_patches": None,
            "total_insufficient_patches": None,
            "provinces": provinces,
        }
    else:
        coverage_status = audit.coverage_measurement_status
        provinces = [
            {
                "province": item.province_name,
                "province_id": item.province_id,
                "id": item.province_id,
                "name": item.province_name,
                "valid_coverage_pct": None,
                "coverage_pct": None,
                "cloud_pct": None,
                "missing_pct": None,
                "status": coverage_status,
                "reason_code": "ACTUAL_PINNED_PROVINCE_MASK_UNION_REQUIRED",
            }
            for item in audit.province_rollups
        ]
        coverage_audit = {
            "status": coverage_status,
            "evidence_status": audit.evidence_status,
            "source_sha256": audit.source_sha256,
            "total_cells": audit.total_cells,
            "total_unique_scenes": audit.total_unique_scenes,
            "total_patches_inventory": audit.total_patches_inventory,
            "total_eligible_patches": audit.total_eligible_patches,
            "total_insufficient_patches": audit.total_insufficient_patches,
            "provinces": provinces,
        }
        if coverage_status != "VERIFIED_REAL":
            reason_codes.append(coverage_status)

    model_evidence = {
        "schema_version": manifest.get("schema_version"),
        "source_sha256": manifest.get("_source_sha256"),
        "evidence_status": manifest.get("evidence_status", "BLOCKED"),
        "metrics_origin": manifest.get("metrics_origin"),
        "training_executed": training_executed,
        "predictions_verified": predictions_verified,
        "metrics_verified": metrics_verified,
        "promotion_authorized": promotion_authorized,
        "deployment_executed": deployment_executed,
        "model_prediction_layers": 0 if not predictions_verified else None,
        "best_experiment_id": manifest.get("best_experiment_id") if metrics_verified else None,
        "promotion_target": manifest.get("promotion_target") if promotion_authorized else None,
        "gate_promotion_decision": manifest.get(
            "gate_promotion_decision", "BLOCKED_MODEL_EVIDENCE_UNAVAILABLE"
        ),
    }
    recovery_summary = {
        "schema_version": recovery.schema_version if recovery else None,
        "status": recovery.evidence_status if recovery else "BLOCKED",
        "reason_code": recovery.blocking_reason if recovery else "RECOVERY_EVIDENCE_UNAVAILABLE",
        "mean_before_valid_pct": recovery.mean_before_valid_pct if recovery else None,
        "mean_after_valid_pct": recovery.mean_after_valid_pct if recovery else None,
        "mean_recovery_rate_pct": recovery.mean_recovery_rate_pct if recovery else None,
    }
    retraining_readiness = _build_retraining_readiness(
        coverage_status=coverage_status,
        training_executed=training_executed,
        predictions_verified=predictions_verified,
        scientific_accuracy_validated=scientific_accuracy_validated,
        promotion_authorized=promotion_authorized,
        deployment_executed=deployment_executed,
    )
    deduplicated_reasons = list(dict.fromkeys(reason_codes))
    unavailable_metric = {"value": None, "label": "미측정", "status": "blocked"}
    return {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "status": "blocked" if deduplicated_reasons else "success",
        "reason_codes": deduplicated_reasons,
        "timestamp": now(),
        "kpis": {
            "models_in_production": {"value": 0, "active_production": 0, "total": None, "label": "0개", "status": "blocked"},
            "training_in_queue": {"value": 0, "label": "0개", "status": "blocked"},
            "deployments_30d": {"value": 0, "label": "0회", "status": "blocked"},
            "retraining_needed": dict(unavailable_metric),
            "mean_f1_score": {**unavailable_metric, "change": None, "trend": None},
            "mean_miou": {**unavailable_metric, "change": None, "trend": None},
        },
        "models": [],
        "pipeline_steps": _blocked_pipeline_steps(),
        "experiments": [],
        "coverage_audit": coverage_audit,
        "coverage_provinces": provinces,
        "recovery_summary": recovery_summary,
        "retraining_readiness": retraining_readiness,
        "model_evidence": model_evidence,
        "actions": {
            "retrain_allowed": False,
            "approval_allowed": False,
            "reason_code": "BLOCKED_NO_EXECUTED_TRAINING_OR_MEASURED_PREDICTIONS",
        },
        "approval_evidence": {
            "human_approval_verified": False,
            "verified_approval_count": 0,
            "stored_record_count": len(approvals),
            "status": "BLOCKED_NO_VERIFIED_HUMAN_APPROVAL",
        },
        "monitoring": {
            "status": "blocked",
            "reason_code": "NO_VERIFIED_RUNTIME_MONITORING_EVIDENCE",
            "inference_requests_24h": None,
            "avg_latency_ms": None,
            "error_count_24h": None,
            "feature_drift_score": None,
            "class_imbalance_ratio": None,
            "drift_trend": None,
            "active_alert": None,
        },
        "deployments": {
            environment: {
                "status": "blocked",
                "reason_code": "NO_VERIFIED_DEPLOYMENT_EVIDENCE",
                "pods": None,
                "url": None,
                "version": None,
            }
            for environment in ("dev", "staging", "production", "geoserver")
        },
        "approvals": approvals,
    }


def create_mlops_router(store_getter: Callable[[], Store]) -> APIRouter:
    router = APIRouter(prefix="/v1/mlops", tags=["Model & MLOps"])

    @router.get("/summary")
    def get_mlops_summary():
        """Return a bounded, evidence-backed dashboard summary."""
        return _build_fail_closed_summary(store_getter())

    @router.get("/coverage/audit")
    def get_coverage_audit():
        """Retrieve authoritative G2 432-cell province-month availability audit."""
        store = store_getter()
        audit_result = build_province_month_audit(store.root)
        return {
            "status": "success",
            "audit": audit_result.to_dict(),
        }

    @router.get("/recovery-rate")
    def get_recovery_rate():
        """Retrieve authoritative G5 cloud and missing pixel recovery rate calculations."""
        store = store_getter()
        summary = compute_recovery_metrics(store.root.parent)
        return {
            "schema_version": summary.schema_version,
            "status": "blocked" if summary.evidence_status == "BLOCKED" else "success",
            "reason_code": summary.blocking_reason,
            "recovery_summary": summary.to_dict(),
        }

    @router.get("/experiments")
    def get_experiments():
        """Expose the absence of executed experiments without scenario scores."""
        return {
            "schema_version": SUMMARY_SCHEMA_VERSION,
            "status": "blocked",
            "reason_code": "BLOCKED_NO_EXECUTED_TRAINING_OR_MEASURED_PREDICTIONS",
            "runs": [],
            "best_run": None,
            "metrics": None,
        }

    @router.post("/retrain")
    def trigger_retraining(payload: RetrainRequestPayload = Body(...)):
        """Reject retraining until executed-training and prediction evidence exists."""
        raise HTTPException(
            status_code=409,
            detail={
                "status": "blocked",
                "reason_code": "BLOCKED_NO_EXECUTED_TRAINING_OR_MEASURED_PREDICTIONS",
                "model_id": payload.model_id,
            },
        )

    @router.post("/approval")
    def submit_approval_request(payload: ApprovalRequestPayload = Body(...)):
        """Reject approval until measured metrics and an approvable candidate exist."""
        raise HTTPException(
            status_code=409,
            detail={
                "status": "blocked",
                "reason_code": "BLOCKED_NO_VERIFIED_CANDIDATE_OR_HUMAN_APPROVAL_BASIS",
                "model_id": payload.model_id,
                "version": payload.version,
            },
        )

    return router
