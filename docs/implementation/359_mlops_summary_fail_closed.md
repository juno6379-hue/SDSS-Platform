# Unit 359 — MLOps summary fail-closed 교정

## 결과

`GET /v1/mlops/summary`는 더 이상 가상 모델 6개, 학습 대기열, 배포 횟수, F1/mIoU, 주별 95~98% coverage, healthy 배포를 사실처럼 반환하지 않는다. 실제 인벤토리와 Unit352/353 증거를 읽고, 측정 증거가 없는 필드는 `null` 또는 실행 없음을 의미하는 `0`과 명시적 차단 코드로 반환한다.

현재 상태는 `BLOCKED`이다. 이는 API 오류가 아니라 실제 주 경계×footprint×quality mask union, 실학습, 실 예측, 독립 라벨, 승인, 배포 증거가 없다는 상태이다.

## 사용한 증거

- Unit353 운영 source: `annual-window-report.json`
  - SHA-256: `0c149628ccfa916ee976e561c5da05f9ccc810cbeab7d233a05b9bc7eff54658`
  - 1,779 patch rows, 107 unique scenes, 1,407 eligible, 372 insufficient
  - 432 province-month cells의 주 전체 coverage는 `BLOCKED_NOT_MEASURED`
- Unit353 recovery:
  - explicit pinned before/after coverage report가 없어 `MISSING_EXPLICIT_PINNED_BEFORE_AND_AFTER_COVERAGE_REPORTS`
  - before/after/recovery 비율은 모두 `null`
- Unit352 model manifest schema `3.1`
  - 검증 시점 SHA-256: `99be93e5eb9528521ddf6fdd3f0b7107e6080b8027ab5fc84a2df1df98ff3511`
  - `TESTED_SYNTHETIC`, `DETERMINISTIC_SCENARIO_FIXTURE`
  - `training_executed=false`, `prediction_artifacts_verified=false`
  - `scientific_accuracy_validated=false`, `promotion_authorized=false`

## API 계약

Top-level에 `schema_version=2.0`, `status`, `reason_codes`, `timestamp`를 반환한다. 현재 `status=blocked`이며 대표 reason code는 다음과 같다.

- `BLOCKED_NOT_MEASURED`
- `MISSING_EXPLICIT_PINNED_BEFORE_AND_AFTER_COVERAGE_REPORTS`
- `NO_EXECUTED_TRAINING_RUN`
- `NO_MEASURED_PREDICTION_ARTIFACTS`
- `NO_VERIFIED_MODEL_METRICS`
- `PROMOTION_NOT_AUTHORIZED`
- `DEPLOYMENT_NOT_EXECUTED`

UI 호환 필드는 유지하되 의미를 안전하게 바꾸었다.

- `kpis.models_in_production.value=0`
- `kpis.training_in_queue.value=0`
- `kpis.deployments_30d.value=0`
- `kpis.mean_f1_score.value=null`
- `kpis.mean_miou.value=null`
- `coverage_audit.provinces[*].valid_coverage_pct/cloud_pct/missing_pct=null`
- `model_evidence.training_executed=false`
- `model_evidence.predictions_verified=false`
- `model_evidence.metrics_verified=false`
- `model_evidence.model_prediction_layers=0`
- `model_evidence.promotion_authorized=false`
- `model_evidence.deployment_executed=false`
- `models=[]`, `experiments=[]`
- 모든 pipeline step과 deployment environment는 `status=blocked`
- `actions.retrain_allowed=false`, `actions.approval_allowed=false`

`approvals`는 기본 예시를 합치지 않고 현재 Store의 `mlops_approvals` 레코드만 반환한다. 기존 레코드는 `미검증 기록`, `IMPLEMENTED_UNVERIFIED`로 표시하고 `verified_approval_count=0`으로 집계한다. 승인 레코드 존재 자체는 모델 승격이나 배포 증거로 사용되지 않는다.

coverage reader가 실패해도 endpoint는 예관 가능한 200 JSON 계약을 유지하며 `COVERAGE_AUDIT_UNAVAILABLE`, `coverage_audit.status=BLOCKED_AUDIT_UNAVAILABLE`를 반환한다. 근거 없는 기본 성공값은 사용하지 않는다.

직접 호출 우회도 막았다. `GET /v1/mlops/experiments`는 실행된 실험이 없으므로 `runs=[]`, `best_run=null`, `metrics=null`인 blocked envelope를 반환한다. `POST /v1/mlops/retrain`과 `POST /v1/mlops/approval`은 각각 근거 코드와 HTTP 409를 반환하며 Store에 아무 레코드도 쓰지 않는다.

## 검증

`python -m pytest tests/test_mlops_router.py -q`

- `8 passed`, `1 warning`, `14.33s`
- `TemporaryDirectory`에 운영 source와 Unit352 manifest를 복사하고 임시 SQLite Store만 사용했다.
- 실패 fixture로 coverage reader를 차단해도 안전한 schema/status/reason code가 유지되는지 확인했다.
- 별도 실험 조회, 재학습, 승인 endpoint가 합성 지표나 성공 응답을 만들지 않고 write-free로 차단되는지 확인했다.
- 작업 전·후 `data/catalog.sqlite3` SHA-256은 `d08418826b858deccad972d5326cfaa2122f56aa13faef0fc1e3628650fdfc45`로 동일했다.
- `python -m compileall -q backend/app/mlops_router.py` 통과.
- `git diff --check -- backend/app/mlops_router.py tests/test_mlops_router.py` 통과.

## 제한과 다음 Gate

이 변경은 주 전체 coverage를 새로 측정하지 않았고, 학습·예측·승격·배포를 실행하지 않았다. coverage 숫자를 제공하려면 경계/source/asset SHA가 고정된 EPSG:6933 동일 grid mask union 36개(6주×6년)가 필요하다. F1/mIoU 및 기존 작은 패치 대비 향상률을 제공하려면 실학습 checkpoint SHA, 실 예측 산출물, 독립 정답 라벨, 공정한 동일 holdout 평가가 먼저 필요하다.
