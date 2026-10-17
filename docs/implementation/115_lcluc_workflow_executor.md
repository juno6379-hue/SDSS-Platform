# 115 — 고정 Registry 입력을 실제 LCLUC 시계열 추론에 연결

## 118 후속 — 같은 실행의 선택 변화쌍 지도 연결

[118 구현·검증](118_lcluc_workflow_change_map.md)에서 수동 pair 선택→고정 index GET→browser SHA·WGS84 도형 검사→중립 지도 미리보기를 연결했다. 기존115의 nonempty tuple/JSON list 보고서 비교 결함도 canonical JSON 동치로 최소 수정하고 회귀2건을 추가했다. 아래 지도 연결 미완료 표현은 당시 이력이며 최신 상태는118과 인계서를 따른다. 기존 상단 지도/KPI·운영 Draft/승인·원본은 보존했고 운영 실행은0이다. 6밴드 per_scene·실제 독립 검증·운영 GeoLLM/RAG·staging/UAT 완료를 뜻하지 않는다.

## 116·117 후속 상태 — 명시 실행 API·화면 연결 완료

[116 API](116_lcluc_workflow_api.md)와 [117 UI](117_lcluc_workflow_ui.md)에서 115 코어를 수동 제출·상태/보고서 조회·검증 산출물 다운로드에 연결했다. 임시 합성 자료의 실제 CPU 실행과 기존5174/8002 반영은 검증됐으며 운영 실행은0이다. 아래 API/UI 미연결·미착수 표현은 당시 이력이다. 현재도 독립 정확도·공식 GMAIS Result·운영 배포 인수·6밴드 per_scene·선택 변화쌍 지도 연결은 미완료이며, GeoLLM 서비스의 기존 NO-LLM fallback은 그대로다. 최신 시험·보존·후속은 인계서와116·117을 따른다.

상태: **TESTED_SYNTHETIC / 운영 실행 미수행**. `backend/app/lcluc_workflow.py`와 명시 CLI `scripts/run_lcluc_workflow.py`는 로컬 DatasetVersion·모델 admission을 검사하고 기존 `ml.service.analyze_timeseries`를 실제 호출한다. 별도 진단만 추가한 기능이 아니다. 격리 TempStore에서 작은 실제 GeoTIFF·TinyUNet CPU 추론·변화/전환 행렬·report와 SHA 연결을 시험했다. 승인 metadata는 시험이 만든 **명시 mock 경계**이며 독립 과학 평가·실제 모델 승인 증거가 아니다.

## 구현 범위

[113 수락안](113_lcluc_integration_acceptance.md)의 단일 로컬 LCLUC 경로다. 기존 Agent capability `landcover.change_detection`을 사용하며 처리기는 로컬 시계열 runner다. 새로운 표준 capability·GMAIS Job/Result·generic DAG executor·외부5개 모델 지원으로 확대하지 않는다. 기존 main/gmais/ML service/Store/data 모듈과 운영 원본·원장·lock·예약·분할·모델을 수정하지 않는다.

기존 시계열 함수의 연차별 classification, 실제 관측연도 인접/기준연도 change, GeoTIFF·GeoJSON·CSV·timeseries.json을 재사용한다. 모델 학습·새 QA·수집·다운로드·자동 배포는 하지 않는다. 현재 원본 Draft 모델·후보4차단을 성공으로 우회하지 않는다.

## 입력 exact6

```json
{
  "schema_version": 1,
  "capability": "landcover.change_detection",
  "trace_id": "operator-trace-001",
  "idempotency_key": "operator-operation-001",
  "model_ref": {"id": "explicit-model", "version": "v1", "sha256": "<lowercase-hex64>"},
  "images": [
    {"year": 2020, "input_ref": {"id": "input-2020", "version": "v1", "sha256": "<hex64>"}, "quality_report_sha256": "<hex64>"},
    {"year": 2021, "input_ref": {"id": "input-2021", "version": "v1", "sha256": "<hex64>"}, "quality_report_sha256": "<hex64>"}
  ]
}
```

예시의 `<...>`는 실제 hash가 아니므로 실행 입력으로 쓸 수 없다. schema_version은 정확한 int1(bool 거부), capability는 위 고정 문자열이다. trace/key는 `[A-Za-z0-9_-]` 1..128자다. model_ref/input_ref는 정확한 id/version/sha256 세 키이며 96의 빈/alias/control/surrogate 검증과 SHA lowercase hex64를 적용한다. 추가로 이 새 실행 계약의 id/version은 `[A-Za-z0-9_.-]` 1..128자의 opaque token만 허용한다. URL/서명 query/경로를 receipt에 복사하는 통로가 되지 않으며 Unicode·패딩 버전까지 받던 다른 metadata helper의 허용 범위를 바꾸지 않는다.

images는2..6개, 각 행 exact3 `year/input_ref/quality_report_sha256`이다. year는 정확한 int1900..2200, 중복 없는 오름차순이어야 한다. caller checkpoint/image/quality/output 경로·URI·scale/offset·source_scene·임의 실행 옵션은 받지 않는다. JSON CLI 입력은 최대16KiB이며 duplicate key·float·비유한 수를 거부한다. 정상 입력은 원형을 보존한 canonical snapshot/SHA로 묶는다.

## 실행 전 admission

1. 모델은 요청 ID와 본문 ID가 같아야 한다. status=Deployed, independent_evaluation은 정확한 true, evaluation.reference_kind=expert_independent와 evaluation.checkpoint_sha256가 요청/등록 checkpoint SHA와 같아야 한다. 이 local metadata는 기관 인증이 아니며 독립성 자체를 자동 공인하지 않는다.
2. 100의 버전 선언 관측이 CONSISTENT_UNVERIFIED여야 한다. exact5 명시 선언의 version/checkpoint/training-report SHA가 모델 부모 필드와 요청에 일치해야 한다. 선언 source 문자열을 등록 권위나 immutable 모델 resolver 증명으로 승격하지 않는다. dataset_version을 모델 버전으로 대체/역채움하지 않는다.
3. data root 안의 checkpoint 실제 SHA와 기존 등록 규약 `checkpoint.parent/report.json` 실제 SHA를 검사한다. 임의 training-report caller 경로를 추가하지 않는다. checkpoint는 CPU `weights_only=True`로 읽고 architecture=tiny_unet 및 실제 TinyUNet state shape를 확인한다. model과 checkpoint manifest의 synthetic은 **정확한 False 명시가 필수**다. 누락·null·true·1을 거부하며 reference_kind가 strip/lower 후 synthetic으로 시작해도 거부한다.
4. v1은 checkpoint의 **global normalization만** 지원한다. 고정 manifest의 scale/offset을 유한 값·채널 길이·양수 scale 조건으로 확인한다. per_scene_product_metadata는 NORMALIZATION_MODE_UNSUPPORTED로 차단한다. 공식 제품 metadata 보정·source_scene·quality mask 연결이 구현된 6밴드 정식 연계가 아니다. 이를 임의 normalization으로 대체하거나 기존 검증을 생략하지 않는다.
5. bands는 정확한 정수·중복 없는1..16, band_names는 같은 길이의 명시 이름이어야 한다. 실제 raster의 선택 밴드 descriptions와 정확히 같아야 한다. 9개 class_names와4..256 patch_size를 확인한다. 밴드 순서나 분류체계를 추정하지 않는다.
6. 각 DatasetVersion은 기존 resolve_version으로 요청 id/version/asset SHA·저장 manifest SHA·현재 자산을 재검증한다. quality_status=VALIDATED, access_class=PUBLIC, data_type=raster를 요구한다. manifest 시작/종료 연도가 모두 행의 year와 같아야 한다. asset 경로는 Registry의 검증된 manifest에서만 선택한다.
7. 기존 Registry가 보장하는 VALIDATED 보고서 참조 존재에 더해, quality_report_ref 실제 파일 SHA를 각 요청의 quality_report_sha256와 비교한다. **보고서 내용의 QA 통과·독립성·과학 정확도를 새로 검증하는 것은 아니다.** 기관/product/license/공간/시간은 고정 Registry 선언이며 기관 원출처 authenticity도 인증하지 않는다.
8. admission은 claim 전과 runner 직전 두 번 수행한다. 모델 본문 metadata SHA와 각 DatasetVersion manifest SHA가 두 검사 사이 변하면 실행하지 않는다. quality/checkpoint/input SHA는 재검사한다. 첫 검사 후 동시 dispatcher가 claim/output을 만들었으면 그 기존 상태를 다시 읽어 재생하므로 잘못된 새 BLOCKED 상태를 만들지 않는다.

## 자원·경로 상한

| 대상 | v1 상한/검사 |
| --- | --- |
| 요청 JSON | 16KiB |
| checkpoint | 8MiB·CPU weights_only·TinyUNet shape |
| training/quality report | 각각2MiB |
| 각 입력 artifact | 64MiB·header1024×1024 이하·16밴드 이하·CRS 필요 |
| 합산 입력 읽기 추정 |128MiB: 모든 밴드 원dtype bytes + 선택밴드 float32 + mask2B/pixel |
| 기록하는 출력 |128개 파일 이하·합256MiB 이하, 각 파일 hash |

새 `_file` streaming 검사는 성장 파일도 최대 bound+1 바이트에서 거부한다. 기존 resolve_version 내부의 파일 해시는 초기 크기 검사를 선행하지만 기존 구현 자체의 성장 파일 총 I/O를 새로 제한하지 않았다. 동시 파일 변경·TOCTOU에 대한 완전한 atomic snapshot 보장이 아니다. 128MiB는 입력 배열 읽기의 보수적 추정이며 Torch/GDAL/활성화·GeoJSON 등 전체 프로세스 RSS 보장이 아니다. 기존 runner의 연산시간 timeout/cancel은 추가하지 않았다. 출력 상한은 생성 후 검증이며 초과·실패 파일을 삭제하지 않는다. 원자 파일 quota/샌드박스가 아니다.

출력은 caller가 정하지 않고 `results/lcluc-workflows/<idempotency-key-full-SHA256>`로 고정한다. 이 lexical 경로와 resolve 결과가 같아야 하므로 parent symlink/junction이 다른 DATA 내부를 가리키는 경우도 거부한다. admission·runner 직전·직후에 확인하고 출력 파일 내 symlink/탈출도 거부한다. 입력은 기존 Registry/local_asset의 DATA 내부 resolved 경로 정책을 사용한다. 출력은 별도 고유 namespace 정책이 더 엄격하다. 모든 경로 검사 직후 발생할 수 있는 외부 동시 교체까지 없애는 원자 lock은 없다.

## claim·상태·Trace·재생

ROOT DB의 새 `lcluc_workflows` namespace와 key 전체 SHA를 사용한다. 같은 key의 동시 호출은 `BEGIN IMMEDIATE`에서 단일 INSERT claim을 확보한다. 기존 Store.put의 INSERT OR REPLACE를 사용하지 않는다. 요청 SHA가 다르면 IDEMPOTENCY_CONFLICT이며 두 번째 runner는 실행하지 않는다. claim transaction이 이미 있는 기록을 발견한 경우 트랜잭션을 해제한 뒤 artifact hash 재생 검사를 하여 DB write lock 중 장시간 읽기를 피한다.

- strict 요청 오류: 고정 WorkflowError INVALID_REQUEST. claim/출력 없음.
- 최초 admission 실패: BLOCKED 반환, workflow claim/분석 출력 없음. CLI가 앞서 Store를 열면서 수행할 수 있는 DB/테이블 초기화와는 별개다. 이 미claim 상태는 영속 멱등 등록이 아니며 나중의 별도 명시 호출에서 admission을 다시 검사할 수 있다.
- claim 직후 RUNNING을 영속 저장한다. 같은 payload의 중복은 기존 상태만 읽는다.
- claim 후 admission 변화/runner/출력 검증 실패는 FAILED로 기록한다. 부분 파일은 보존한다.
- 실제 runner report·산출물 검증을 마치면 SUCCEEDED다. finite JSON, 기대 report 경로/checkpoint SHA·실제 timeseries.json 내용, 출력 파일 hash를 확인한다.
- RUNNING/FAILED는 자동 재실행·재시작 복구·파일 삭제를 하지 않는다. 다른 key의 수동 재요청에도 현재 admission·namespace 조건을 적용한다.
- SUCCEEDED 재생 시 모든 기록 artifact SHA를 다시 확인한다. 변경됐으면 STORED_OUTPUT_CHANGED로 거부하고 재실행하지 않는다. **replayed=true는 과거 실행 상태 읽기이지 현재 모델의 새 실행 승인 재확인이 아니다.**

claim에는 원문 key를 제외한 request_snapshot(schema/capability/trace/model_ref/images/quality SHA)을 저장하므로 입력 lineage를 나중에 재현할 수 있다. request_sha256는 key를 포함한 고정 요청 전체에 결합된다. 같은 snapshot은 최종 claim-body CAS update에도 묶여 외부 상태 변경을 조용히 덮지 않는다. receipt의 scope는 LOCAL_LCLUC_WORKFLOW_ONLY이며 Trace·고정 ref·admission pins·report 경로·artifact SHA를 연결한다. scientific_accuracy_validated/standard_gmais_result는 항상 false다.

원자성은 SQLite claim 한 건에 한정된다. runner 파일 생성과 최종 DB 상태는 하나의 transaction이 아니다. crash 시 RUNNING과 부분/완성 파일이 남을 수 있고 이를 SUCCEEDED로 추정하지 않는다. 최종 상태 update가 실패해도 자동 runner 재실행은 없다. 분산 exactly-once·복구 coordinator·취소·재시도 scheduler를 구현한 것이 아니다. native 예외는 LOCAL_WORKFLOW_UNAVAILABLE/LOCAL_EXECUTION_FAILED/ADMISSION_GATE_BLOCKED 같은 고정 코드로 처리하며 native 경로·비밀·예외 원문을 출력하지 않는다.

## CLI와 시험

```powershell
$env:PYTHONPATH = '.runtime;backend;tests;.'
python scripts/run_lcluc_workflow.py --execute --data-root <명시한_별도_루트> --request <고정요청.json>
python -m unittest test_lcluc_workflow -v
```

--data-root와--request는 필수이고--execute 없이는 Store를 열기 전에 거부한다. default 운영 DATA 경로가 없다. CLI는 JSON 상태를 출력하고 성공0/차단·거부·실패2로 종료한다. Store 생성은 명시 실행의 일부라 DB/테이블 초기화가 가능하다. `_runner` injection은 Python 격리 시험용 seam이며 CLI 옵션이나 승인을 우회하는 공개 route가 아니다. 기본 runner는 기존 analyze_timeseries를 직접 호출한다.

합성 fixture의 영상은 실제16×16 GeoTIFF 두 연도이며 실제 TinyUNet CPU inference·classification2개·change GeoTIFF/GeoJSON/CSV/report·timeseries의7개 파일을 확인했다. 학습은 수행하지 않았다. checkpoint에는 fixture_only 표시가 있고 TempStore의 Deployed/독립평가 metadata는 시험이 만든 mock admission boundary다. 실제 전문가 라벨/평가를 수행하거나 synthetic 데이터를 운영 승인했다는 증거가 아니다. synthetic flag/kind 차단은 별도 음성 시험으로 유지한다.

최초 focused11건에서 실제 artifact 계약7개를8개 이상으로 잘못 기대한 시험1건이 실패했다. 기대를 실제 runner 계약에 맞추었으며 최초 로그를 보존했다. stream/output/finite/race/snapshot 보강 후 최종 focused는 **17 PASS/4.203초/exit0**, `evidence/integration/lcluc-workflow-focused-final4-20261018.log`다. 실제 CPU E2E·동시 claim1·running/failed no retry·race 상태 재조회·DB lock 밖 replay·다른payload 충돌·report변조·admission 변화·partial 보존·상한/출력경로·정규화/품질/연차/합성 gate·고정 오류·명시 CLI 차단을 검사했다. 중간 로그는 최종 근거와 합산하지 않는다.

독립 검토는 **24 PASS/12.821초/exit0**(신규17+별도7), `evidence/integration/lcluc-workflow-independent-final2-20261018.log`다. 독립 관련은 **26 PASS/21.460초/exit0**, `evidence/integration/lcluc-workflow-independent-related-20261018.log`다. 세부 판정과 이전 실행 시작 오류의 보존은 `evidence/integration/lcluc-workflow-independent-review-20261018.json`을 따른다. 구현 담당 시험과 중복된17건 및 관련 묶음을 전체 건수에 다시 합산하지 않는다. 기존 소스는 바꾸지 않고 최종 source/test freeze 이후의 독립 격리 근거다.

## 인계와 미완료

Root 전체 backend는 **1153건/1152 PASS/기존 Windows 1 SKIP/331.642초/exit0**이며 `evidence/integration/lcluc-workflow-full-tests-20261018.log`에 보존했다. 신규·관련·독립 묶음과 중복 합산하지 않는다. Root의 `evidence/integration/lcluc-workflow-live-integrity-20261018.json`은 보호141·기존 소스252·이전 증거866·catalog14 불변, source/test/CLI 동결 SHA 일치와 pending2/예약136,314,880B 유지를 확인했다.

기존 source/API/UI는 바꾸지 않았고 운영 Store/Job/Registry 등록·새 QA·수집·다운로드·정식 학습·배포·실제 운영 CLI 호출0이다. 이번 front/build/browser는 재실행하지 않았다. 향후116 UI/API의 상태 조회·선택 change pair·같은 Trace 탐색은 별도 연결이며 지금 화면에 반영됐다고 표시하지 않는다. Root와 이해 에이전트에 완료 소스·합성 시험·v1 한계를 전달해 관련 인계/설명/대본/FAQ/INDEX/변경 이력을 갱신한다.

남은 범위는 per_scene 공식 제품 정규화/6밴드·구름 mask 계약, 실제 승인/자료 권한, generic DAG/취소/재시작 정책, 표준 GMAIS Result 어댑터·기관 과학/UAT·운영 권한이다. 현재 Draft 모델·독립 라벨 미확보·후보 Gate 차단을 바꾸지 않으며 전체 프로젝트 완료로 간주하지 않는다.
