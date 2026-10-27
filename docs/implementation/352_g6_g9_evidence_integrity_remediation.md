# Unit 352 — G6~G9 증거 무결성 교정

## 목적

2026-10-20 07:59에 기록된 G6/G7 완결과 기존 G8/G9 모델 승격 주장을 코드, 운영 원본, 실서비스 응답과 다시 대조했다. 파일 존재, 합성 시험, 실제 관측, 운영 승인을 구분하고 근거가 없는 성공 상태를 실패 시 닫히도록 교정한다.

## 발견한 차단 결함

### G6

- 로컬 primary TIFF 54개는 실제 존재한다.
- `coverage_comparison`은 입력 래스터를 비교하지 않고 고정 배열을 만든다. `newly_recovered`와 `still_missing`은 이 합성 배열에서 파생된다.
- manager는 게시 API나 GetCapabilities를 확인하지 않고 `PUBLISHED_ONLINE`을 기록한다.
- `08_geoserver_1st_2nd_layer_registry.csv`는 primary 54행으로 덮여 부모 판본의 secondary 18행이 사라졌다.
- 현재 8088은 GetCapabilities HTTP 200과 표본 named GetMap PNG 200을 반환하지만, GetCapabilities XML에 실제 named layers를 열거하지 않는다.

따라서 로컬 파일 존재는 `VERIFIED_REAL`, 생성/라우터 시험은 `TESTED_SYNTHETIC`, 54/72 전수 게시와 과학적 복구 의미는 `BLOCKED`다.

### G7

- 기존 manager는 이미지·라벨·quality 파일명 존재만으로 적격을 정하고 실제 TIFF band 수를 읽지 않은 채 6으로 기록했다.
- 공간 누출은 상수 false였고 readiness는 단순 개수 하한만 사용했다.
- 권위 원본 보고서는 1,779행, 품질 적격 1,407행(865/292/250), 원본 scene split conflict 1건, 클래스 기여 부족, `learning_ready=false`다.

따라서 1,780은 파일명 세 종류가 있는 폴더 인벤토리 범위만 인정한다. 품질 적격, 누출 0, 학습 준비 완료는 `BLOCKED`다.

### G8/G9

- 기존 evaluator는 학습을 실행하거나 체크포인트, 독립 라벨, 예측 파일을 읽지 않는다.
- 264개, OA/F1/mIoU, 클래스별 F1, 혼동행렬은 코드에 고정하거나 난수 seed로 합성했다.
- 그럼에도 `PRODUCTION_CANDIDATE_APPROVED`, `PROMOTED_TO_PRODUCTION`, KLHK 승인자, 무중단 롤백 성공을 출력했다.

## 완료한 G8/G9 교정

`backend/app/ml/model_benchmark_evaluator.py` 스키마를 3.1로 올리고 다음을 명시했다.

- `evidence_status=TESTED_SYNTHETIC`
- `metrics_origin=DETERMINISTIC_SCENARIO_FIXTURE`
- 검증된 test patch/pixel은 0, 과거 264개는 별도 scenario 수량
- `training_executed=false`
- `prediction_artifacts_verified=false`
- `holdout_independence_verified=false`
- `scientific_accuracy_validated=false`
- `promotion_authorized=false`
- `best_experiment_id=null`, promotion/rollback target null
- 결정 `BLOCKED_NO_EXECUTED_TRAINING_OR_MEASURED_PREDICTIONS`
- 실행 학습, checkpoint SHA, 측정 예측, 독립 라벨, scene conflict 해소, learning-ready, 사람 승인 부재를 각각 차단 사유로 기록

CSV의 지표 열은 `scenario_*`로 바꾸고 5개 산출물 전체에서 운영 승인, 실측 성능, 승인자 표현을 제거했다. 숫자는 UI·문서 흐름용 결정적 시나리오로만 남긴다.

## 시험

- `python -m pytest tests/test_model_benchmark_evaluator.py -q`
- 결과: 4 PASS, 3.08초
- `python -m py_compile backend/app/ml/model_benchmark_evaluator.py`: exit 0
- 최초 CLI 실행은 Windows CP949가 작업공간 경로의 en dash를 출력하지 못해 export 전에 종료했다. `PYTHONIOENCODING=utf-8`로 동일 CLI를 다시 실행해 5개 산출물을 정상 재발행했다. 제품 로직 실패나 부분 산출물 적용으로 계산하지 않는다.

시험은 합성 시나리오가 운영 승격으로 바뀌지 않는 계약을 검증한다. 실제 모델 품질을 검증하지 않는다.

## 서비스 복구와 한계

collector·QA 0, execution lock 부재를 확인한 뒤 API 8002, UI 5174, GeoServer 호환 8088을 복구했다. 세 서비스 HTTP 200과 표본 GetMap PNG를 확인했다. GetCapabilities named-layer 목록 공백과 registry 손실은 별도 차단 결함으로 남는다.

## 운영 보존

운영 source와 ledger 지문은 각각 `0c149628...4658`, `d5ee31ff...1c91`로 유지했다. collector 실행, 원장 쓰기, 원격 수집, 실제 학습, 모델 승격, 운영 배포는 수행하지 않았다.

## 남은 작업

1. G7 manager가 권위 원본 보고서와 동일한 적격 수·split·scene 충돌·learning-ready 상태로 fail-closed하는지 검토한다.
2. G6 합성 마스크를 실제 G5 lineage가 확인된 입력 없이는 게시 불가로 바꾸고 registry를 primary/secondary 보존 방식으로 수리한다.
3. GetCapabilities가 실제 named layers를 열거하도록 계약을 구현하고 전수 외부 HTTP 증거를 남긴다.
4. 실제 학습 로그, checkpoint SHA, 독립 라벨, 예측 산출물, 재계산 가능한 지표, 사람 승인이 마련되기 전에는 G8/G9 승격을 해제하지 않는다.
