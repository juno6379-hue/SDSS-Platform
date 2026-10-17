# 105. Workflow·완성 Job·제공 모델 레코드의 별도 관측 API

상태: **TESTED_SYNTHETIC**. 별도 진단 endpoint·격리 API 시험을 추가했다. 운영 모델 등록·Job 제출·Workflow 실행·역채움·학습·배포는 없다. 실제 서버 GET/POST·UI 연결은 Root와 UI 담당의 별도 근거로 구분한다.

## endpoint와 기존 계약 보존

```http
POST /v1/workflows/full-job-model-record-handoff
```

[새 router](../../backend/app/workflow_job_model_record_handoff_api.py)를 기존 main의 import/include_router 두 줄로 연결한다. 기존 `/v1/workflows/full-job-input-handoff`의 RFC1/RFC2 parser·route·결과는 변경하지 않는다. 89/94/100/103/104 core와 원 GMAIS schema도 그대로다. main의 기존 전역 인증 dependency를 상속한다.

새 경로는 [104 내부 wrapper](104_workflow_job_model_record_handoff.md)의 별도 수동 관측이다. 모델을 Registry/Store에서 찾는 endpoint가 아니며 caller가 제공한 레코드를 비교한다. 원 model_ref에서 exact3 identity를 추출하는 것은 89 MATCH 뒤 104에서만 수행한다.

## 요청과 strict 원문 계약

필수 exact4 키와 선택적 `model_record_json` 하나만 허용한다. `contract_version`을 포함한 다른 키는 400이다.

```json
{
  "workflow_request_json": "<Workflow JSON 원문>",
  "pinned_workflow_request_sha256": "<Workflow canonical SHA-256>",
  "selected_node_id": "<선택 노드 원문 ID>",
  "full_job_request_json": "<완성 Job JSON 원문>",
  "model_record_json": "<caller가 제공한 모델 레코드 JSON 원문>"
}
```

선택 키를 생략하면 candidate는 None이다. 선택 키의 값은 반드시 문자열이며 transport null/bool/object·빈 값·공백 JSON은 400이다. 문자열 `"null"`은 정상 JSON으로 파싱돼 candidate None을 뜻한다. 이것은 DB를 조회했으나 레코드가 없다는 증거가 아니다. 문자열 `"true"`, `"[]"`처럼 문법상 정상인 JSON은 core에 전달돼 레코드 타입 관측으로 구분한다.

원문 세 개 각각 UTF-8 **512KiB**, 전체 요청은 streaming **1MiB** 한도다. 세 원문이 각각 한도 이내여도 전체 body 한도가 우선할 수 있다. pin은 소문자 hex64, selected node는 기존 96 계열 문자 한도를 사용한다. 원문을 trim·정규화·자동 보정하지 않는다.

| 원문 | 재사용 parser·주요 한도 |
|---|---|
| Workflow | 기존 `_strict_json(inner=True)`: 깊이12·int32·문자256·객체128키·정수 전용·제어문자 제외 |
| 완성 Job | 기존 `_strict_full_job`: 깊이24·atom16384·키256·문자4096·정수 ±(2^53−1)·유한 decimal/exponent |
| 제공 레코드 | Job과 동일 `_strict_full_job`; unknown 필드도 transport 예산 안에서 파싱 |

UTF-8 오류·중복 JSON 키·NaN/Infinity·surrogate·부정확한 숫자 범위/비영 underflow는 400이며 byte/깊이/atom/문자/numeric token 예산 초과는 413이다. source parsing은 core 실행 전에 이루어진다. 따라서 **89가 차단될 입력이어도 제공 레코드 원문을 strict 파싱한다**. 104의 ‘89 차단 뒤 추가 candidate 접근0’과 transport parsing을 혼동하지 않는다.

## 생산과 독립 응답 검증

104 생산과 전체 응답 검증을 같은 threadpool 작업에서 실행한다.

1. 104를 정확히 1회 호출한다. 이 안에서 89 원 comparator도 정확히 1회 호출한다.
2. 원 89의 기존 `validate_full_job_handoff_response()`로 embedded 결과를 확인한다. 검증을 위해 89를 다시 실행하지 않는다.
3. outer exact12·schema/scope·항상 false인 다섯 flag·세 상태·projection bool·호출 카운터의 조합을 검사한다. 차단/참조부재면 nested 비교는 null이어야 한다.
4. OBSERVED일 때만 같은 exact3 projection과 parsed candidate로 **103을 독립적으로 한 번 재산출**한다. 실제 반환 nested 결과와 예상 결과를 dict/list/scalar의 정확한 타입까지 재귀 대조한다. 단순 `dict ==`로 비교하지 않으므로 `False`→`0`, `True`→`1`, schema int→bool 같은 오염을 중첩100까지 거부한다.

모델 참조가 있고 candidate ID가 같아 intrinsic 관측을 하는 정상 경우, 생산 103/100 각1회와 검증 추가 103/100 각1회로 합계 각각2회다. candidate 미제공·다른 ID 등 103이 100을 호출하지 않는 가지에서는 100 합계0이다. 차단/참조부재면 103 생산·검증 모두0이다.

반환된 104의 `model_comparison_calls=1`과 103의 `inspection_calls=1`은 **생산 단계 범위**이며 validator의 추가 호출을 누락된 실행으로 해석하지 않는다. 두 관측이 달라지면 503으로 닫지만 이것이 원자적 snapshot·등록 권위·레코드 신원 인증을 보장하지 않는다. validator도 Store·파일·resolver를 호출하지 않는다.

## 응답과 오류

성공은 HTTP200·exact5 wrapper다. result는 104 exact12를 그대로 담는다.

```json
{
  "extension": "greenblue.workflow-full-job-model-record-handoff.rfc1",
  "approval_status": "INTERNAL_REVIEW",
  "present_in_upstream_openapi": false,
  "request_sha256": "<전체 요청 raw UTF-8 body SHA-256>",
  "result": "<104 exact12 객체>"
}
```

위 result 문자열은 문서 자리표시자이며 실제 응답은 객체다. raw body SHA는 공백·숫자 원문·candidate 원문까지 묶는 요청 관측값이지 원본 인증·model pin의 권위가 아니다. 원 89의 full Job hash 관측 및 기존 24 false도 그대로다.

outer `HANDOFF_BLOCKED`, `MODEL_REFERENCE_ABSENT`, `MODEL_REFERENCE_OBSERVED`는 정상 진단 결과이므로 200이다. OBSERVED는 실행한 관측이며 nested conflict/invalid/not-comparable를 승인으로 바꾸지 않는다. 89의 `RESOURCE_UNAVAILABLE`은 안전 503으로 변환한다. 결과 원문 ID·버전·SHA·URI·경로·candidate를 echo하지 않는다.

모든 이 router의 성공·실패 응답은 `Cache-Control: no-store`다. 오류는 exact `{error:{code,message,retryable:false}}`다. 기존 main 인증 거부는 기존 인증 정책을 따르며 이 router 오류 envelope를 새로 씌우지 않는다.

| HTTP / code | 고정 message |
|---|---|
| 400 `INVALID_REQUEST` | `Invalid Workflow model-record handoff request.` |
| 413 `REQUEST_TOO_LARGE` | `Workflow model-record handoff request exceeds limits.` |
| 503 `RESOURCE_UNAVAILABLE` | `Workflow model-record observation is unavailable.` |

예상하지 못한 parser/core/validator 예외·오염 응답·중간 관측 불일치도 동일503이다. 원 예외 메시지나 로컬 경로를 반환하지 않는다. 모델 관련 권위·artifact 바이트·실행·과학·model_verified는 모두 false다. 이것은 관측의 미검증 범위이며 기존 모델 승인 필드를 변경한 것이 아니다.

## I/O·schema·미구현 한계

API 자체의 Store factory/get/list/put·등록·Job 제출·resolver·artifact/network I/O는 0이다. caller가 제공한 JSON을 비교할 뿐 Registry에서 적합 모델을 찾지 않는다. URI는 원 89의 문자열/full JSON 한도 검사만 거치며 정체·로컬/원격 정책·실재 자원 해결을 검사하지 않는다. dataset_version 추정이나 역채움은 없다.

원 89의 cached schema factory cold path는 vendored Job schema를 읽을 수 있다. 시험에서 cold 1회/warm 추가0을 계측했고 이후 warm의 artifact open/outbound connection 차단도 통과했다. 원 `schema_files_read=null`은 그대로다. 전체 호출 chain을 항상 파일 읽기0으로 표현하지 않는다. model_record decimal 필드는 파싱 가능하나 모델 비교가 수치 과학 의미를 검증하는 것은 아니다.

## 시험과 근거

[신규 시험](../../tests/test_workflow_job_model_record_handoff_api.py)은 운영 main을 import하지 않는다. 원 [main 사본](../../evidence/integration/workflow-model-record-api-original-main-20261017.py)의 SHA `9e68da6ce85c43cb804999962fb7d894f17f3047a45870f95f3e2e853aca4f28`를 확인하고 import/include 두 AST 추가만 제외하면 기존 main 전체가 같음을 검사한다. 실제 authorized/app 선언 AST만 격리 실행해 새 router의 상속401도 확인한다.

```powershell
# 프로젝트 루트, PYTHONPATH=.runtime;backend;tests
python -m unittest test_workflow_job_model_record_handoff_api -v
python -m unittest test_workflow_job_model_record_handoff_api test_workflow_job_model_record_handoff test_workflow_job_request_handoff_api test_workflow_job_registration_handoff_api test_workflow_job_request_handoff test_workflow_job_registration_handoff test_model_reference_record_comparison test_model_registration_provenance -v
```

- 집중 신규 **15 PASS / 1.736초**: [집중 로그](../../evidence/integration/workflow-model-record-api-focused-20261017.log).
- 관련 **101 PASS / 6.697초**: [관련 로그](../../evidence/integration/workflow-model-record-api-related-20261017.log). 신규15개는 관련 묶음에 포함된다. 전체 회귀·독립 검토·실제 서버/브라우저·보존은 Root 근거로 구분한다.
- exact wrapper/raw SHA/privacy·세 outer 흐름·candidate 미제공/JSON null/문법오류·intrinsic 상태·decimal/exponent·depth/size/UTF-8/duplicate·gate 전 record 파싱을 검증했다.
- 1041/89생산1/생산1031/검증1031/same-ID100총2와 같은 worker thread, nested 100까지 exact type 오염 거부·예외/자원실패503/no-store·Store0·schema cold/warm을 확인했다.
- 기존 RFC1/RFC2의 body/headers·parser 분리를 비교했다. 다른 endpoint·전체 main 초기화/CORS/운영 서버 교체를 이 격리 시험만으로 검증했다고 표현하지 않는다.

## 전체 회귀에서 확인한 이전 AST 보호 시험의 호환 수정

Root의 [최초 전체 로그](../../evidence/integration/workflow-model-record-api-full-tests-20261017.log)는 **1060건/409.580초·실패1/기존 skip1**이다. 실패는 `test_model_registration_provenance_api.py`의 101 당시 전체 main AST 보호 시험 한 건이었다. 이 시험은 원 101 route 추가만 제외하고 모든 노드를 비교하므로, 이번에 명시 승인된 105 router import/include 두 문장까지 변경으로 감지했다. API 동작 실패나 기존 route 변경을 발견한 것이 아니다.

사용자가 위임한 Root의 명시 수정 범위에 따라 해당 기존 시험만 호환 수정했다. 편집 전에 [원 시험 사본](../../evidence/integration/workflow-model-record-api-test-compat-original-20261017.py) 10349바이트/SHA `e4380845692e87a3a4e0847d6339646457706527704ec8a4100e50909fc2eb81`와 [새 사전 기준선](../../evidence/integration/workflow-model-record-api-test-compat-baseline-20261017.json)을 보존했다. 기존 preflight나 최초 실패 로그를 덮어쓰지 않았다.

수정은 **정확한 105 import AST 한 개와 정확한 include_router AST 한 개**만 허용 목록에 추가한다. 각 문장이 정확히 한 번 있어야 하며, 그 외 모든 기존 main 노드와 순서는 여전히 전체 AST 동등으로 보호한다. import나 함수 호출을 포괄적으로 무시하지 않는다. 제품 소스와 시험 메서드 수는 바꾸지 않았다.

원101+새105의 집중 재시험은 **24 PASS / 4.702초**이며 [호환 집중 로그](../../evidence/integration/workflow-model-record-api-test-compat-focused-20261017.log)를 따른다. [수정 결과 근거](../../evidence/integration/workflow-model-record-api-test-compat-result-20261017.json)는 수정 후 시험 SHA와 최초 full 로그의 크기/SHA 불변을 확인한다. 전체 재실행 결과는 Root의 별도 새 로그와 최종 인계서를 따르며, 이 24개 통과로 최초 전체 실행을 성공으로 바꾸지 않는다.

## UI 인계

UI 담당에게 별도 경로·old4+선택 raw 레코드·transport null/JSON null 구별·512KiB/1MiB·고정 오류·exact5/104·103/100·생산 카운터와 재검증 추가 호출을 인계한다. client는 raw 요청 SHA 및 편집/이동 세대와 연결해 오래된 표시를 폐기하고, caller 레코드를 실제 조회된 등록 모델로 표시하지 않아야 한다.

화면 연결·프론트 검증·실제 브라우저 확인은 UI 담당/Root의 별도 작업이다. API 합성 검증을 운영 성공 등록·실모델 resolver·실행 승인으로 표시하지 않는다.

## Workflow 모델 레코드 대조 API·UI 검증 완료 (105/106)

별도 수동 진단 POST와 실행계획 검토 화면의 ‘모델 레코드 초안 대조’를 연결했다. API 담당은 strict parsing·크기 한도·원문 SHA·nested exact typed 재검증을, UI 담당은 공통 SVG·명시 클릭·오래된 응답 폐기·안전 오류를 구현했다. 기존 RFC1/RFC2 결과와 승인 gate를 보존한다. producer의 103 호출 1회와 독립 validator의 추가 1회를 구분하며, record 원문 파싱은 89 gate보다 먼저다.

관련 API 101 PASS·독립 15 PASS, 프론트 관련/독립 각19 PASS·전체191 PASS, 빌드96 modules/28.34초다. Root 최종 전체 backend는 1060건/1059 PASS/기존 Windows symlink 1 SKIP/364.175초/exit0다. 첫 전체 실행은 기존101 AST 보존 시험의 새 router 허용목록 부재로 실패1건이었다. 정확한 두 연결만 허용하는 시험 호환 수정 후 전체를 재실행했고, 최초 실패 로그도 보존했다. 제품 동작 오류와 시험 호환 수정은 구분한다.

Root는 합성 원문으로 실제 HTTP 10건(200×6/400×3/413×1)과 브라우저 11개 확인·수동 진단 POST4회를 수행했다. 미제공·일치 미검증·공백400·null 미제공, 입력/Workflow 편집의 결과 폐기와 화면 이동/뒤로가기를 확인했다. 원래 Workflow 원문은 정확히 복원하고 새 node/job/record 필드는 비웠다. desktop 제목 겹침·가로넘침0/제목·버튼 SVG 정상, 시험 이후 수집된 최근20 warn/error 중 새 항목0이다. 지연·동시성 방어는 격리 시험 근거이며 실제 back 확인은 완료 응답 이후다. 표시 중단은 서버 취소가 아니다.

보호141·이전 증거736·catalog14·기존 Job 본문을 보존했다. 계약기준73개 중72개는 byte 불변이며 나머지 GeoQuery1개는 허용된 import/sibling 두 조각만 제거하면 원문 byte와 정확히 같다. 기존제품의 허용 변경은 main router import/include와 GeoQuery sibling 배치이며 추가 기존 시험1개 호환 수정은 별도 사전 byte 근거를 남겼다. 운영 등록/Job 생성·Workflow 제출·수집/새 운영 QA/정식 학습/배포0, 원본/원장/lock/예약136314880B/분할/모델 보존·QA차단4/학습BLOCKED 유지다. 이 진단은 metadata 관계만 관측하며 기관 권위·실바이트·과학 정확도·실행 승인·모델 인증을 입증하지 않는다. 성공 화면 PNG도 합성 입력 진단 예시다.

완료 코드·시험·실제 화면 근거를 이해 에이전트에 전달해 쉬운 설명·발표 대본·FAQ·INDEX·변경 이력을 함께 갱신했다. 다음은 Workflow 입력 연결 대기열 검토(PLANNED)이며 전체 개발은 미완료다. geoai-2 예약 ACTIVE와 실제 worker 실행은 다르다. 최종 로컬 프로세스 관측의 수집/학습 후보는0이며 원격/숨은 worker까지 보장하지 않는다. 8002는 실제 진단 요청으로 새 경로를 확인했고8000/8001은 유지·새 코드 로딩 미확인이다. 지속 개발과10분 담당별 보고를 유지한다.

근거: `evidence/integration/workflow-model-record-api-live-integrity-20261017.json`, `evidence/integration/workflow-model-record-api-live-api-20261017.json`, `evidence/integration/workflow-model-record-api-live-ui-20261017.json`, `evidence/integration/workflow-model-record-api-runtime-final-20261017.json`. 최종 문서 감사와 rawSHA snapshot은 `evidence/integration/workflow-model-record-api-closeout-20261017.json`을 따른다.

