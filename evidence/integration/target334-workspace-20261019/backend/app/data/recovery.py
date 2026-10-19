"""중단된 수집의 복구 근거를 원본 변경 없이 검사한다."""
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit


def _confined(root, path):
    # 외부 절대 경로와 UNC는 파일시스템 해석 전에 배제한다.
    if path.anchor.startswith("\\\\") or urlsplit(str(path)).netloc:
        raise ValueError("원격 경로는 복구 근거로 읽지 않습니다")
    path.absolute().relative_to(root)
    resolved = path.resolve()
    resolved.relative_to(root)
    return resolved


def _reference(path):
    """한 파일의 읽는 도중 변경을 감지하고 원본 바이트의 해시를 남긴다."""
    if not path.exists():
        return None, {"path": str(path), "exists": False}
    if not path.is_file():
        raise ValueError("복구 근거가 일반 파일이 아닙니다")
    before = path.stat()
    raw = path.read_bytes()
    after = path.stat()
    if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
        raise ValueError("복구 근거를 읽는 도중 파일이 변경되었습니다")
    return raw, {"path": str(path), "exists": True,
                 "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def _read(path):
    raw, reference = _reference(path)
    if raw is None:
        return None, reference
    try:
        return json.loads(raw.decode("utf-8")), reference
    except (ValueError, UnicodeError):
        reference["invalid_json"] = True
        return None, reference


def inspect_recovery(data_root):
    """예약을 환불하거나 완료 판정하지 않고 불일치와 로컬 근거만 반환한다."""
    requested_root = Path(data_root)
    if requested_root.anchor.startswith("\\\\") or urlsplit(str(requested_root)).netloc:
        raise ValueError("데이터 루트는 로컬 경로여야 합니다")
    root = requested_root.resolve()
    ledger_path = _confined(root, root / "first-group-training-budget/global-ledger.json")
    ledger, ledger_ref = _read(ledger_path)
    if not isinstance(ledger, dict):
        raise ValueError("기존 전역 원장을 읽을 수 없습니다")
    output = _confined(root, root / "first-group-training-esri-v1")
    run, run_ref = _read(_confined(root, output / "run-result.json"))
    run = run if isinstance(run, dict) else {}
    manifest, manifest_ref = _read(_confined(root, output / "annual-window-report.json"))
    _, execution_lock_ref = _reference(_confined(root, ledger_path.with_suffix(".execution.lock")))
    _, ledger_lock_ref = _reference(_confined(root, ledger_path.with_suffix(".lock")))
    historical = []
    for entry in ledger.get("historical_ledgers", []):
        candidate = Path(entry["path"])
        path = _confined(root, candidate if candidate.is_absolute() else root / candidate)
        _, reference = _reference(path)
        historical.append(dict(reference, expected_sha256=entry["sha256"],
            matches_ledger=reference.get("sha256") == entry["sha256"]))
    pending = []
    for key, batch in sorted(ledger.get("batches", {}).items()):
        if batch.get("status") != "pending":
            continue
        # UNC/절대 경로와 다른 경로 문법은 resolve 이전에 거부한다.
        if not isinstance(key, str) or not key or key in (".", "..") or any(char in key for char in ("/", "\\", ":")) or urlsplit(key).scheme:
            raise ValueError("복구 batch 키는 단일 로컬 이름이어야 합니다")
        directory = _confined(root, output / "sources" / key)
        # 원장의 키도 신뢰하지 않고 데이터 루트 밖의 파일을 읽지 않는다.
        directory.relative_to((output / "sources").resolve())
        values, references = {}, {}
        for name in ("config.json", "window-state.json", "worker-result.json", "annual-window-report.json"):
            values[name], references[name] = _read(_confined(root, directory / name))
        config = values["config.json"]
        config_hash = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest() if isinstance(config, dict) else None
        state = values["window-state.json"]
        state = state if isinstance(state, dict) else {}
        partials = []
        for path in sorted(directory.rglob("*.part")):
            _, reference = _reference(_confined(root, path))
            partials.append(reference)
        pending.append({"key": key, "reserved_bytes": batch["reserved_bytes"],
            "charged_bytes_preserved": batch["charged_bytes"], "artifacts": references,
            "config_matches_ledger": config_hash is not None and config_hash == batch.get("config_sha256"),
            "window_state_http_body_bytes": state.get("http_body_bytes"),
            "window_state_measured_body_bytes": state.get("http_body_bytes_measured"),
            "partial_files": partials,
            "worker_terminal_evidence_present": isinstance(values["worker-result.json"], dict),
            "source_terminal_report_present": isinstance(values["annual-window-report.json"], dict),
            "settlement_authorized": False,
            "action": "PRESERVE_RESERVATION_RECONCILE_MANUALLY"})
    charged = ledger["new_charged_bytes"]
    run_charged = run.get("new_charged_upper_bound_bytes")
    return {"ledger": ledger_ref, "run_result": run_ref, "manifest": manifest_ref,
        "manifest_object_valid": isinstance(manifest, dict),
        "execution_lock": execution_lock_ref, "ledger_lock": ledger_lock_ref,
        "historical_ledgers": historical,
        "execution_lock_present": execution_lock_ref["exists"],
        "process_health_verified": False, "pending_batches": pending,
        "pending_reserved_bytes": sum(b["reserved_bytes"] for b in pending),
        "ledger_new_charged_bytes": charged,
        "remaining_budget_bytes": ledger["additional_maximum_bytes"] - charged,
        "ledger_internal_sum_matches": charged == ledger.get("external_research_metadata_body_bytes", 0)
            + sum(b["charged_bytes"] for b in ledger.get("batches", {}).values()),
        "run_result_new_charged_bytes": run_charged,
        "run_result_ledger_delta_bytes": charged - run_charged if isinstance(run_charged, int) else None,
        "rate_limit_active": ledger.get("rate_limit_active"),
        "automatic_resume_allowed": False, "network_requests": 0,
        "source_files_written": 0,
        "note": "로컬 파일 크기와 window-state는 완전한 네트워크 계측이나 완료 증거가 아니다. lock 존재만으로 프로세스 상태를 판정하지 않는다."}


PROHIBITED_RECOVERY_ACTIONS = [
    "RELEASE_OR_REFUND_RESERVATIONS", "DELETE_LOCKS", "NETWORK_REQUESTS",
    "RESTART_COLLECTION", "MODIFY_SOURCE_FILES", "REWRITE_AGGREGATE_MANIFEST",
]


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
        separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def build_recovery_plan(data_root):
    """같은 불변 snapshot에는 같은 계획 ID를 부여하며 실행 권한을 부여하지 않는다."""
    snapshot = inspect_recovery(data_root)
    # 서로 다른 파일을 읽는 사이의 갱신도 검출한다. 원장 잠금을 획득하지 않는다.
    if snapshot != inspect_recovery(data_root):
        raise ValueError("복구 조사 중 snapshot이 변경되어 계획을 생성하지 않습니다")
    blockers = [{"code": "PROCESS_HEALTH_UNVERIFIED", "scope": "global"},
                {"code": "COORDINATOR_APPLY_NOT_IMPLEMENTED", "scope": "global"}]
    if not snapshot["manifest_object_valid"]:
        blockers.append({"code": "MANIFEST_MISSING_OR_INVALID", "scope": "global"})
    if not snapshot["ledger_internal_sum_matches"] or snapshot["remaining_budget_bytes"] < 0:
        blockers.append({"code": "LEDGER_INCONSISTENT", "scope": "global"})
    if snapshot["rate_limit_active"]:
        blockers.append({"code": "RATE_LIMIT_ACTIVE", "scope": "global"})
    if snapshot["execution_lock_present"] or snapshot["ledger_lock"]["exists"]:
        blockers.append({"code": "LOCK_REQUIRES_OWNER_REVIEW", "scope": "global"})
    if any(not entry["matches_ledger"] for entry in snapshot["historical_ledgers"]):
        blockers.append({"code": "HISTORICAL_LEDGER_CHANGED", "scope": "global"})
    batches = []
    for batch in snapshot["pending_batches"]:
        missing = []
        for field, code in (("config_matches_ledger", "CONFIG_MISSING_OR_MISMATCH"),
                ("worker_terminal_evidence_present", "WORKER_TERMINAL_MISSING"),
                ("source_terminal_report_present", "SOURCE_REPORT_MISSING")):
            if not batch[field]:
                missing.append(code)
                blockers.append({"code": code, "scope": batch["key"]})
        if batch["charged_bytes_preserved"] != batch["reserved_bytes"]:
            missing.append("PENDING_RESERVATION_INCONSISTENT")
            blockers.append({"code": "PENDING_RESERVATION_INCONSISTENT", "scope": batch["key"]})
        batches.append({"batch_id": batch["key"], "disposition": "HOLD_FULL_RESERVATION",
            "reserved_bytes": batch["reserved_bytes"],
            "proposed_refund_bytes": 0, "terminal_or_config_gaps": missing,
            "review_steps": ["VERIFY_PROCESS_EXIT_AND_LOCK_OWNER", "VERIFY_CONFIG_AND_WINDOW_STATE_LINEAGE",
                "RECOVER_TERMINAL_AND_COMPLETE_TRANSFER_ACCOUNTING", "VERIFY_AGGREGATE_APPLIED_EXACTLY_ONCE"],
            "settlement_authorized": False})
    body = {"schema_version": 1, "kind": "COLLECTION_RECOVERY_PLAN",
        "mode": "DRY_RUN_READ_ONLY", "snapshot_sha256": _digest(snapshot), "snapshot": snapshot,
        "process_evidence": {"state": "NOT_VERIFIED", "verified": False,
            "note": "파일 lock과 보고서로 OS 프로세스 종료를 추정하지 않는다."},
        "status": "BLOCKED", "execution_authorized": False,
        "prohibited_actions": PROHIBITED_RECOVERY_ACTIONS.copy(),
        "required_approval_conditions": [
            "현재 snapshot 재검증 및 원장 내부합계·과거 원장 SHA 일치",
            "OS 프로세스 종료와 lock 소유권을 확인하는 별도 시각 포함 근거",
            "batch 설정·정규화된 window-state lineage·terminal 결과의 연결 확인",
            "COG와 메타데이터 전체 전송 근거 및 미계측 예약의 보수적 보존",
            "동일 batch의 원장 정산과 aggregate 반영을 중복하지 않는 coordinator 구현·검증",
            "복구 적용 범위와 책임자 검토 기록; 이 계획 검증 성공만으로 실행하지 않음",
        ], "batches": batches, "blockers": blockers,
        "network_requests": 0, "source_files_written": 0}
    return dict(body, plan_id="collection-recovery-" + _digest(body))


def validate_recovery_plan(data_root, plan):
    """계획 변조·현재 자료 변경을 거부한다. 성공은 검토용 계획의 일치만 뜻한다."""
    errors = []
    if not isinstance(plan, dict):
        return {"valid_for_review": False, "execution_authorized": False,
            "status": "REJECTED", "errors": ["INVALID_PLAN_OBJECT"]}
    try:
        body = {key: value for key, value in plan.items() if key != "plan_id"}
        if plan.get("plan_id") != "collection-recovery-" + _digest(body):
            errors.append("PLAN_ID_MISMATCH")
        current = build_recovery_plan(data_root)
        if plan.get("snapshot_sha256") != current["snapshot_sha256"]:
            errors.append("SNAPSHOT_STALE")
        if plan != current:
            errors.append("PLAN_CONTENT_MISMATCH")
    except (OSError, ValueError, KeyError, TypeError):
        errors.append("SNAPSHOT_UNREADABLE_OR_CHANGED")
    return {"plan_id": plan.get("plan_id"), "valid_for_review": not errors,
        "execution_authorized": False, "status": "VALID_BLOCKED" if not errors else "REJECTED",
        "errors": errors, "network_requests": 0, "source_files_written": 0}
