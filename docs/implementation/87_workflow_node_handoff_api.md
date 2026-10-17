# 87 — Workflow 선택 노드 → 제안 입력 전달 비교 API

상태: **TESTED_SYNTHETIC**. 신규 비실행 RFC route와 격리 HTTP 시험 완료. 실행 중 로컬 서버 배선·실제 HTTP·브라우저와 전체897건 회귀를 완료했고 Root의 최종 검증 절에 기록했다. 실제 HTTP도 합성 caller 선언을 사용했으며 운영 Workflow 전달 검증으로 확대하지 않는다. 실제 Job 생성·Workflow 실행 또는 운영 승인은 없다.

## 목적과 경계

신규 `backend/app/workflow_node_input_handoff_api.py`의 `create_workflow_node_input_handoff_router()`는 86의 순수 `compare_workflow_node_input_handoff`를 한 번 threadpool에서 호출한다. configured Store 인자를 받지 않고 DB·Registry·resolver·파일·executor를 호출하지 않는다. 기존 86 core와 upstream schema, 기존 API는 수정하지 않았다. `main.py` import/include는 Root 소유다. 인증은 기존 main의 공통 의존성을 승계하며 모든 자체 응답은 `Cache-Control: no-store`다.

`POST /v1/workflows/node-input-handoff`는 완성 Job을 제출하는 API가 아니다. caller가 가진 원 Workflow의 선택 노드와 제안 Job 입력 metadata의 동등성만 검사한다. AOI·output·purpose/environment·predecessor Result·모델·정책 기본값은 만들지 않는다. `MATCH`도 원본 인증·DAG/실행 준비·ACL·과학/학습/운영 승인과 다르다.

## 요청 계약

Content-Type은 `application/json`을 사용한다. UTF-8 원문 JSON envelope의 정확 네 키이며 모두 문자열이다.

```json
{
  "workflow_request_json": "{ ... 원 Workflow JSON 원문 ... }",
  "pinned_workflow_request_sha256": "소문자 16진수 64자리",
  "selected_node_id": "원문 node ID",
  "proposed_job_metadata_json": "{ ... 선택 metadata JSON 원문 ... }"
}
```

`workflow_request_json`과 `proposed_job_metadata_json`을 JSON 문자열로 보내는 이유는 서버가 duplicate key·원문 구조를 직접 검사하도록 하기 위해서다. 브라우저가 객체로 바꾼 뒤 다시 직렬화해 중복 키나 원문을 숨기는 방식으로 보내지 않는다. 두 원문은 공백/개행을 그대로 보존한다. selected_node_id는 trim/정규화하지 않는 1~256 code point 문자열이며 공백만·C0/C1·surrogate는 거부한다.

제안 metadata는 86의 정확 네 키 `agent_id`, `capability_id`, `execution_context:{trace_id}`, `input_refs`다. 완성 Job이나 추가 필드는 86의 유효 BLOCKED 진단으로 남는다. Workflow 전체 pin은 Python canonical UTF-8(sort_keys, ensure_ascii=False, allow_nan=False, compact separators)의 SHA-256이며 policy·dependencies·선택 외 node까지 포함한다.

## 파싱·예산·오류

본문은 `request.stream()`에서 실제 수신 byte를 누적하며 **1,048,576 byte** 초과 시 즉시 중단한다. 빈 chunk는 저장하지 않는다. outer JSON과 두 inner JSON에 모두 strict UTF-8, 중복 키 거부, NaN/Infinity 및 float/지수표현 거부를 적용한다. 정수는 변환 전에 부호 제외 10자리 한도를 적용하고 변환 후 signed int32(-2147483648~2147483647) 범위를 확인한다. bool은 JSON에서는 허용하지만 86 정수 필드에서는 bool로 거부된다.

- 두 inner JSON 원문은 각각 **524,288 UTF-8 byte** 이하다. char 길이도 같은 상한을 먼저 검사한다.
- 문자열·escape를 구분하는 선행 scan으로 outer 구조 깊이 최대 8, inner 최대 12를 확인한 후 `json.loads`를 실행한다. 문자열 안 괄호는 깊이로 세지 않는다.
- JSON object 키 수 최대 128, 각 파싱 트리 key/value/container/scalar 합계 32,768 atom 이하다. 이는 HTTP 입력 파싱 예산이고 executor 자원 한도 또는 hard RAM/time 한도가 아니다.
- inner의 모든 문자열과 키는 256 code point 이내·C0/C1 및 surrogate 없음이어야 한다. 문자열의 빈 값은 transport에서 보존하고 의미는 86이 판정한다. outer의 두 원문 문자열은 pretty JSON의 개행을 포함할 수 있으므로 inner scalar 규칙을 그대로 적용하지 않는다. outer에서도 unpaired surrogate는 거부한다.
- JSON 구문/키 중복/UTF-8/타입/비유한·float·int32 초과/문자 규칙 오류는 **400**, byte/depth/object-key/atom/정수 자리수 예산 초과는 **413**이다. transport를 통과한 86의 schema/pin/입력 차이는 **HTTP 200, result.status=BLOCKED**다. 예기치 않은 내부 오류 및 안전 응답 검증 실패는 **503**으로 닫는다.

오류 응답의 정확 모양은 `{error:{code,message,retryable:false}}`다. 원문 ID·URI·본문·예외/stack은 포함하지 않는다.

| HTTP | code | 고정 message |
| --- | --- | --- |
| 400 | INVALID_REQUEST | Invalid handoff request. |
| 413 | REQUEST_TOO_LARGE | Handoff request exceeds limits. |
| 503 | RESOURCE_UNAVAILABLE | Handoff comparison is unavailable. |

기존 공통 인증의 401은 main의 계약이며 위 자체 오류와 별개다. 현재 API는 동시 요청 worker semaphore나 서버 검사 취소를 제공하지 않는다. 클라이언트의 표시 중단은 서버 threadpool 비교의 완료와 다르다.

## 성공 wrapper와 응답 검증

정확 다섯 키다.

```json
{
  "extension": "greenblue.workflow-node-input-handoff.rfc1",
  "approval_status": "INTERNAL_REVIEW",
  "present_in_upstream_openapi": false,
  "request_sha256": "전체 실제 수신 outer UTF-8 byte의 SHA-256",
  "result": {"schema_version":1,"...":"86 safe payload"}
}
```

`request_sha256`는 실제 전송 outer 원문의 SHA이고 86 `workflow_request_sha256`는 canonical 전체 Workflow SHA다. 공백만 바꿔도 전자는 달라질 수 있고 후자는 같을 수 있다. 결과의 selected_node_sha256는 node ID 문자열의 JSON canonical SHA다. 이들 digest는 호출자 선언의 동일성을 묶으며 원본 인증이나 암호학적 운영 승인을 뜻하지 않는다.

`validate_handoff_response`는 exact result 키·정확한 타입·scope·상태와 declarations_match의 동치, 모든 20 false 및 7개 정수 I/O0를 확인한 후 직렬화한다. unknown raw 값·추가 키·재귀 출력·알 수 없는 issue code를 거부한다. 입력 pin/선택 ID/전체 요청 및 expected/proposed metadata hash가 현재 요청과 연결되는지, count/null/hash 관계·MATCH의 hash/count 일치·issues 부재를 확인한다. 검증된 MATCH는 86의 순수 `_workflow_error` shape 선검사를 방어적으로 재사용하며 전체 compare는 한 번뿐이다.

safe issue는 code/side/node_index/input_index의 정확 네 키이고 최대 324개다. 중복 issue를 거부한다. index는 0..127/0..63뿐 아니라 실제 Workflow nodes, 해당 input_bindings, 제안 input_refs 및 comparison의 양쪽 count 범위와 연결해 검사한다. 실행 준비·DAG·AOI/output·선행 Result 검증 false는 응답에서도 바뀌지 않는다. 86의 선택 외 빈 node·순환 DAG의 전달 선언 MATCH도 그대로 HTTP 200이지만 `dag_validated=false`다. 지원 외 policy 확장은 86의 BLOCKED 200이다.

## 합성 시험·공유 fixture

```powershell
$env:PYTHONPATH="$PWD\.runtime;$PWD\backend;$PWD\tests"
python -m unittest test_workflow_node_input_handoff_api -v
```

`tests/test_workflow_node_input_handoff_api.py`: **15 PASS / 0.842초**. 로그: `evidence/integration/workflow-node-handoff-api-related-20261017.log`. 독립 검토도 **15 PASS / 1.250초 / exit0**, 추가 결함 0이며 `evidence/integration/workflow-node-handoff-api-independent-20261017.log`에 기록했다. code/tests 및 이 구현 문서는 이 상태로 동결해 Root의 서버·전체 검증으로 인계했다.

증거는 TestClient/격리 FastAPI와 합성 caller 입력이다. 정확 wrapper/raw SHA·core1회/worker·Store.get 금지·원문 불변·BLOCKED200·중복 outer/양쪽 inner·UTF-8/BOM·오류 envelope·nonfinite/float/거대 정수·제어문자/surrogate·byte/depth/atom 예산·한글 byte 상한·문자열 내 괄호·공백에 따른 outer SHA 변화·Unicode canonical fixture·예외 safe503·output raw/타입/hash/count/false/순환/issue index 변조 차단·인증 승계·86 지원 subset/미검사 DAG 범위를 확인했다. 실제 운영 자료·Job 생성·학습은 하지 않았다.

공유 golden fixture는 `evidence/integration/workflow-node-handoff-canonical-fixture-20261017.json`이다. 키는 workflow_request/canonical_json/sha256/selected_node_id/proposed_job_metadata이며 한글·é·emoji·비BMP·U+2028를 포함한다. frontend는 Python과 동일한 code point 기반 key 정렬·정수/UTF-8 직렬화를 검증하고 두 원문을 보존해야 한다. 이미 JSON.parse 후 원문을 버리는 입력은 서버 strict parse의 근거가 될 수 없다.

## UI·이해자료·인계

web_ui의 별도 88 단위는 기존 Workflow 원문 + caller pin/선택 node + 독립 proposal 원문을 명시적 비교 버튼에 연결한다. source/selection/route 세대 변화 및 뒤로 이동 시 stale 응답을 버리고, 실제 보낸 outer SHA와 응답 wrapper를 검증해야 한다. 이 문서와 코드·fixture·시험 로그를 UI 담당 및 독립 reviewer에게 전달했다. 실제 서버 반영·프론트 시험/빌드·브라우저 확인은 Root와 UI의 최종 증거로 구분해 보고한다.

Root는 main 배선·실제 HTTP/브라우저·전체 회귀·보호 자료 불변·관련 문서·인계서를 담당한다. understanding_agent는 검증된 코드/로그와 한계로 쉬운 설명·이론·코드/데이터·발표 대본·FAQ·INDEX·변경 이력을 갱신한다. 내부 RFC 완료는 전체 Workflow/executor·DAG/Result/RAG 또는 프로젝트 전체 완료가 아니다.


## Root 실제 API·브라우저 검증 근거

`evidence/integration/workflow-node-handoff-api-live-api-20261017.json`: 최종 새endpoint11POST(Unicode합성MATCH·role부재드리프트BLOCKED·잘못된callerpinBLOCKED·빈선택BLOCKED·outer/inner중복/UTF8/nonfinite400·depth/body413), 기존plan/lineage2POST는 시작기준선2POST와 응답동일. 최초checker의본문공백/compact차이로derived requestSHA가달랐던 시도는별도initial-attempt JSON에보존했고 원baseline직렬화로수정후PASS했다. application변경은없으며 반복검증을새시험건수로합산하지않는다. catalog14행/기존Job본문동일·JobPOST0이다.

`evidence/integration/workflow-node-handoff-api-live-ui-20261017.json` 및 `workflow-node-handoff-ui-desktop-20261017.jpg`: 실제5174/#/view/15에서 합성선언수동MATCH·role변조BLOCKED·없는node/null·중복JSON로컬거부, 기존계획/계보완료후결과유지, node/proposal/원Workflow편집clear·뒤로/앞으로이동폐기를확인했다. 1449×1087 문서/패널가로넘침0·console오류[]·SVG/제목간격보완반영. 테스트후기존Workflow초안을원문그대로복원하고합성node/proposal/결과는지웠다. 스크린샷은복원전합성시연이다.

실제UI모바일·강제지연/취소경합·HTTP503/인증오류·5173적용은미검증이다. 운영Workflow/Job생성·실행·새QA/학습은0. 새비교의I/O0와기존plan/lineage의Registry읽기를혼동하지않는다. 최종전체회귀/보존/문서감사는Root완료절을따른다.


## 19:55 KST — Workflow 입력 전달의 수동 API·UI 연결 검증 완료 (87/88)

- **workflow_handoff / API:** 새 POST /v1/workflows/node-input-handoff와 main배선 완료. 관련15 PASS/0.842초·독립15 PASS/1.250초. 원JSON문자열2개/정확4키·strictUTF8/중복/nonfinite/float/int32·body1MiB/원문별512KiB·깊이/atom 한도·400/413/503 고정오류·no-store/기존인증·86 comparator1회를 검증했다. safe wrapper wholebodySHA·실제list index/20false7IO0·core86불변을 유지했다.
- **workflow_handoff_ui / 화면:** GeoQuery 실행계획 검토에 독립 수동 child를 적용했다. 신규13 PASS/1400.1225ms·전체113 PASS/2260.0008ms·독립13 PASS/2073.8207ms·production84modules/build19.17초 PASS(기존chunk경고). Python86→JS14합성경우 교차검산0실패이며 신규시험 수에 합산하지 않는다. status array 정규화·실제입력index 경계를 보완했고 실제 화면의 SVG/제목 간격을 scopedCSS로 수정·재검증했다.
- **Root 실제API/UI:** 최종HTTP 새11POST+기존진단2POST(기준선2별도) 통과. 최초증거checker의본문직렬화차이로derivedhash가 달랐던 시도는 별도기록 후 exactbaseline본문으로 수정해 PASS했다(application변경X). 실제5174/#/view/15 합성선언의 수동MATCH·role드리프트BLOCKED·없는node/null·중복JSONlocal거부·기존plan/완료lineage와결과독립·편집/뒤로/앞으로이동clear를 확인했다. 1449×1087 문서/패널overflow0·console[]·최종JPG저장. 시험뒤기존Workflow초안은원문복원하고합성node/proposal/결과를지웠다. 모바일/강제취소지연경합/HTTP503·인증의실브라우저/5173적용은미검증이다.
- **전체·보존:** backend897개/896 PASS/기존Windows symlink1 SKIP/382.270초/exit0. 보호141·불변core51 변경0·catalog14/기존Job본문같음. 기존tracked code변경은허용main.py+GeoQuery.tsx뿐, core86/기존Workflow/계보/84~85응답보존. 원본·원장/lock·예약136314880B·분할·모델·후보1095/차단4·학습BLOCKED 유지. 실제JobPOST/역채움/Workflow실행·새QA/학습·수집/배포0.
- **문서·이해자료:** 신규87/88·관련07/41/86·운영원장/소유권/인계서 수정. understanding_agent에완료코드/관련·독립·전체/실제HTTPUI·보존근거를전달하여쉬운설명·이론·코드데이터·발표대본·FAQ·INDEX/변경이력갱신을같은단위로진행한다. 최종문서감사/rawSHA snapshot은 `evidence/integration/workflow-node-handoff-api-closeout-20261017.json`에기록한다.
- **범위·다음:** 실제HTTP/UI이지만새기능의선언은합성(TESTED_SYNTHETIC)이며운영Workflow→Job전달검증이아니다. callerpin은신뢰원본인증이아니고MATCH는완성Job/AOI/output/선행Result/DAG/기관ACL/과학/실행승인이아니다. 신규비교I/O0와기존plan/lineage Registry읽기를구분한다. 다음은사용자완성Job초안원schema검증→metadata추출→86대조의내부작업(PLANNED/미착수)이다. 전체프로젝트미완료·지속개발대기열을유지하며 geoai-2 ACTIVE10분예약과실제worker실행을구분한다.

근거: `evidence/integration/workflow-node-handoff-api-live-integrity-20261017.json`, `evidence/integration/workflow-node-handoff-api-live-ui-20261017.json`, `evidence/integration/workflow-node-handoff-api-live-api-20261017.json`.
