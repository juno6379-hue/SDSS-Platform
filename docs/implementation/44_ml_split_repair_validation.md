# 저장 ML 분할 복구 계획 읽기 검증 — 2026-10-17

## 상태와 목적

**TESTED_SYNTHETIC:** 격리한 임시 JSON으로 17개 시험을 통과했다. 실제 기존 계획의 재검증 결과는 root 통합 근거에서 별도로 기록한다. **PLANNED:** 실제 후보 발행과 raster readiness 재검사. **BLOCKED:** bare 대표성, 공간 누출 재검사, 독립 라벨·전문가 승인과 정식 학습.

저장된 계획 JSON을 그대로 믿지 않고, 호출자가 별도로 고정한 원본 SHA·readiness SHA·province split을 이용하여 기존 planner를 다시 실행한 결과와 전체 문서를 대조한다. 검증기는 계획이나 후보를 생성하지 않으며 원본 분할·raster·원장·lock·모델을 수정하지 않는다. 메타데이터 무결성 성공은 학습 준비성이나 과학적 성능 승인이 아니다.

## 구현 및 신뢰 경계

- [split_validation.py](../../backend/app/ml/split_validation.py)의 `validate_split_repair_plan`은 원본 manifest 경로·명시적 SHA와 독립 `province_splits`를 필수 입력으로 받는다. 저장 계획의 경로·정책·SHA를 신뢰 입력으로 재사용하지 않는다. readiness 경로/SHA는 함께 지정하며 기존 planner가 원본 참조·적격 split 계수·정책 일치를 재검사한다.
- 저장 계획의 모든 JSON 필드를 재계산 결과와 비교한다. 키 순서는 무관하지만 배열 순서·원소·키 집합·타입은 정확히 같아야 한다. `true`와 `1`, `1.0`과 `1`은 다르다. 알 수 없는 추가 필드나 실행 플래그 조작도 불일치다.
- 모든 JSON 입력에서 중복 키, NaN/Infinity와 `1e999`의 비유한 숫자를 거부한다. 원본 연도는 정수 또는 ASCII 4자리 연도 문자열(기존 실자료 계약), synthetic은 있을 때 boolean이어야 한다.
- plan/source/readiness/candidate 경로는 서로 달라야 한다. 모든 입력을 읽기 전후 SHA로 비교하고 planner 재계산 중 변경도 거부한다. 이는 순차 파일 관측의 안정성 검사이며 운영체제 lock 또는 여러 파일의 원자적 snapshot을 제공하지 않는다. 검증 후 다른 프로세스의 변경까지 방지하는 보증은 아니다.
- 선택 `candidate_path`/`candidate_sha256`를 함께 제공하면 실제 후보 SHA와 예상 문서 전체를 대조한다. source row indexes, 보존 행 순서·내용, 원본 SHA·선택 정책 lineage, 후보 버전, status, `executed=false`, `learning_ready=false`까지 포함한다. 적격 여부만 보고 원본 행을 재작성하거나 split을 다시 배정하지 않는다.
- 후보 입력이 없으면 `candidate_validation.status=NOT_REQUESTED`, `candidate_integrity_valid=null`, `reference=null`이다. 후보가 존재하거나 발행되었다고 추정하지 않으며 후보 검증 완료로 표시하지 않는다. 경로를 명시했는데 파일이 없으면 실패한다.

## CLI 계약과 사용법

### 선택적 bounded 내부 호출

후속 구현 70에서 `validate_split_repair_plan(..., io_policy=...)`와 `load_json_document(..., io_policy=..., role=...)`를 추가했다. 모든 초기 읽기·planner 재개방·종료 SHA/상태 확인에 동일한 operation context를 전달한다. 정책 생략 시 기존 동작을 유지하며 기존 CLI가 자동으로 이 제한 모드로 바뀌지는 않는다. 역할별 제한과 strict UTF-8/중복 키/비유한 숫자/깊이 거부, 필수 source/readiness SHA 검사는 [70 입출력 계약](70_split_bounded_io.md)에 설명한다. 제한 모드에서도 후보 미지정은 `NOT_REQUESTED/null`이고 raster·기하·정확 클래스·실행·승인 검증은 하지 않는다.

[validate_training_split_repair.py](../../scripts/validate_training_split_repair.py)는 기본 stdout만 사용한다. stdout JSON과 stderr 오류는 ASCII escape로 출력하여 Windows CP949에서도 경로의 en dash 등으로 인한 인코딩 실패를 방지한다. evidence 파일은 UTF-8로 유지한다. `--plan`은 실험 정책 파일이며 `--saved-plan`인 저장 복구 보고서와 구별한다. 정책 파일도 strict JSON과 전후 SHA를 검사하고 결과에 경로/SHA를 기록한다. `--output`은 프로젝트 `evidence/` 아래의 새 경로만 허용한다. 원본·정책·계획·readiness·후보·기존 파일 덮어쓰기와 evidence 밖 출력을 거부한다. exclusive create로 최종 파일 생성 경쟁도 방어한다. 새 evidence의 부모 디렉터리 생성 이외 수집·학습 작업은 없다.

```powershell
python scripts/validate_training_split_repair.py `
  --saved-plan evidence/integration/ml-split-repair-plan-20261017.json `
  --manifest data/first-group-training-esri-v1/annual-window-report.json `
  --expected-sha256 cdc374b2779dee749b57689fd90ef27e3525a48e59062343537327d0f4859a8f `
  --plan data/first-group/experiment-esri-v003-2020-2025.json `
  --readiness data/first-group/readiness-resume-20261017.json `
  --readiness-sha256 6e59c3aee00f53609237b889bfc304a811d298b464b6d6ae2c8e563cc29a34db
```

기존 계획이 그대로 일치하면 exit 0, `METADATA_INTEGRITY_VERIFIED`와 `plan_integrity_valid=true`를 반환한다. 읽기 오류·stale SHA·조작·잘못된 JSON·출력 경로 충돌 등은 exit 1, stderr 오류 메시지이며 성공 evidence를 생성하지 않는다. 후보를 확인하려면 `--candidate <기존 후보 경로> --candidate-sha256 <별도 고정 SHA>`를 추가한다. 이 옵션도 후보를 발행하지 않는다.

결과는 `projected_after`, 제외 행 수, source identity 계획 재계산 여부를 보여주되 다음을 항상 유지한다: `raster_files_rehashed=false`, `spatial_overlap_rechecked=false`, `exact_class_counts_recomputed=false`, `ready_for_training=false`, `training_executed=false`, `scientific_accuracy_validated=false`, `source_files_written=0`. 후보 메타데이터가 일치해도 원래 raster 파일을 재해시했다는 뜻이 아니다.

## 시험 근거

```powershell
$env:PYTHONPATH="$PWD\.runtime;$PWD\backend"
python -m unittest discover -s tests -p test_ml_split_validation.py -v
```

[시험 파일](../../tests/test_ml_split_validation.py), [최종 로그](../../evidence/integration/ml-split-validation-tests-20261017.log): **17 PASS (최종 실행 시간은 아래 시험 로그 기준)**. 임시 합성 원본과 후보만 사용했다. 계획 재계산/후보 미요청 구분, 정확 후보/원본 보존, row·정책·승인 플래그 조작, boolean/int/float 혼동, 중복 키·비유한 숫자, stale 원본/readiness와 독립 caller split, 후보 행·lineage·실행 상태·SHA 조작, 미존재 후보·짝 없는 옵션, 재계산 중 입력 변경, stdout·새 evidence 생성, 기존/입력 덮어쓰기와 evidence 밖 출력 거부, 실패 시 evidence 미생성을 검사했다.

17개는 신규 기능 단위시험 수이며 기존 backend 전체 회귀 결과에 중복 합산하지 않는다. 합성 시험은 실제 후보나 실제 과학적 누출 해소의 증거가 아니다. 독립 검토의 14개 시험과 추가 적대 fixture는 별도 확인이며 전체 회귀에 중복 합산하지 않는다. 실제 원본의 문자열 연도를 그대로 보존하고 boolean/float/공백/잘못된 문자열은 거부하는 두 시험과 Windows CP949 stdout·stderr 회귀시험을 후속 추가했다.

## 실제 실행 보완 이력

root의 최초 실제 실행에서 원본 1,384행의 연도가 문자열인 기존 계약과 새 검증기의 정수 전용 조건이 충돌했다. 원본을 수정하지 않고 정수/ASCII 4자리 문자열을 허용하도록 보완했으며 행 원형 보존 및 잘못된 연도 타입 거부 시험을 추가했다. 다음 실행에서는 메타데이터 대조·UTF-8 evidence 생성까지 성공했으나 Windows CP949 stdout이 경로의 en dash를 인코딩하지 못해 exit 1이었다. stdout/stderr를 ASCII escape로 보완하고 명시 CP949 회귀시험을 추가했다.

중간 산출물 `ml-split-repair-validation-live-20261017.json`은 메타데이터 대조 후 콘솔 출력에 실패한 실행의 기록으로 보존한다. 최종 재검증은 별도의 [최종 실제 검증 근거](../../evidence/integration/ml-split-repair-validation-live-final-20261017.json)를 사용한다. 최종 실행 성공 여부·보호 SHA·전체 회귀는 root가 실제 로그와 함께 확정한다. 과거 실패 산출물과 최종 성공 근거를 혼동하지 않는다.

## UI 영향 및 다음 작업

이 단위는 내부 읽기 CLI이고 공개 API·응답·UI 상태 계약을 변경하지 않는다. 따라서 실행 중 UI 서버에 화면 변경을 적용하거나 브라우저 검증을 추가할 필요가 없다. 향후 UI에 검증 결과를 노출할 때는 web_ui에 실제 API·상태·오류 계약과 근거를 전달하고 화면 검증까지 별도 완료해야 한다.

기존 [계획 문서25](25_ml_split_repair_plan.md)의 한계가 그대로 남는다. source identity 계획의 일관성만 검증하며 실제 기하 중첩, raster SHA, 정확한 클래스 통계, 라이선스·기관 권한, 독립 검증·승인·학습은 수행하지 않는다. root가 실제 기존 계획의 읽기 결과·보호 SHA·전체 회귀와 인계를 기록하고 이해 에이전트가 완료 코드·근거를 바탕으로 해설/발표/FAQ/INDEX/변경 이력을 함께 갱신한다.

## Root 최종 실제 통합 확인

**VERIFIED_REAL(메타데이터만):** CP949 stdout 환경에서 최종 CLI가 exit 0으로 완료됐다. [최종 JSON](../../evidence/integration/ml-split-repair-validation-live-final-20261017.json)은 `METADATA_INTEGRITY_VERIFIED`, `plan_integrity_valid=true`다. 원본 적격1111/계획상 제외16/예상1095(train628·val217·test250)가 보존 계획과 일치한다. 실제 후보를 지정하거나 발행하지 않았으므로 후보 상태는 `NOT_REQUESTED/null`이다. 원본 raster 및 기하/클래스 준비성 검증으로 확대 해석하지 않는다.

[보호 대조](../../evidence/integration/ml-split-validation-live-integrity-20261017.json)는 Catalog DB·원장·원본 manifest·기존 readiness·upstream 계약·저장 계획의 6개 SHA 불변을 확인한다. 최종 관련17 PASS/7.544초, 독립17 PASS/8.900초이며 [전체 회귀](../../evidence/integration/ml-split-validation-full-tests-20261017.log)는 **338건 중337 PASS·1 SKIP·113.601초·종료0**이다. 독립 실행을 전체338건에 중복 합산하지 않는다. SKIP은 기존 Windows symlink 생성 권한 제한이고 deterministic 경로 이탈 시험은 PASS다. 프론트 변경이 없어 UI49건/build를 반복하지 않았다.

## 후속 실제 후보 패키지 — 구현 71

[71 후보 생성·재검증](71_candidate_materialization.md)에서 기존 bounded writer/validator를 연결하여 새 evidence 후보1368행과 마지막 완료receipt를 실제 생성·대조했다. 원본1384행은 보존하며 후보계획 적격1095는 실제 raster 준비성 결과가 아니다. 후보는 PLANNED_DERIVED_CANDIDATE/learning_ready=false/executed=false, 미등록·readiness NOT_ASSESSED다. 이 문서의 이전 미생성/PLANNED 기록은 해당 단위의 역사이며, 최신 생성 상태는71의 고정 SHA/근거를 참조한다.
