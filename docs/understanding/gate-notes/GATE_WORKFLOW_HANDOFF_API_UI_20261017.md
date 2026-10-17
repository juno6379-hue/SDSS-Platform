# Gate Workflow Handoff API UI 20261017 — 원문 기반 수동 선언 비교

| 필드 | 값 |
|---|---|
| updated_at | 2026-10-17 23:36 KST — Git 상태 메타데이터 정정; 본문은 해당 Gate 기준 |
| source_commit | d474d5bce6c2a6c4bd8ba141c9256d15f6004631 (108까지 구현 검토 기준; 이 메타데이터 정리는 후속 문서 커밋) |
| evidence_paths | `backend/app/workflow_node_input_handoff_api.py`; `tests/test_workflow_node_input_handoff_api.py`; `docs/implementation/87_workflow_node_handoff_api.md`; `evidence/integration/workflow-node-handoff-api-related-20261017.log`; `evidence/integration/workflow-node-handoff-api-independent-20261017.log`; `evidence/integration/workflow-node-handoff-api-live-api-20261017.json`; `evidence/integration/workflow-node-handoff-canonical-fixture-20261017.json`; `docs/implementation/88_workflow_node_handoff_ui.md`; `frontend/src/WorkflowNodeHandoff.tsx`; `frontend/src/workflowNodeHandoffAdapter.ts`; `frontend/src/workflowNodeHandoffAdapter.test.mjs`; `frontend/src/workflow-node-handoff.css`; `frontend/src/GeoQuery.tsx`; `evidence/integration/workflow-node-handoff-api-live-ui-20261017.json`; `evidence/integration/workflow-node-handoff-api-full-tests-20261017.log`; `evidence/integration/workflow-node-handoff-api-live-integrity-20261017.json`; `evidence/integration/workflow-node-handoff-ui-adapter-20261017.log`; `evidence/integration/workflow-node-handoff-ui-tests-20261017.log`; `evidence/integration/workflow-node-handoff-ui-independent-20261017.log`; `evidence/integration/workflow-node-handoff-ui-build-20261017.log`; `evidence/integration/workflow-node-handoff-ui-desktop-20261017.jpg` |
| confidence | API 코드·격리 시험·로컬 HTTP 합성 선언; 운영 Workflow 전달·실행 미검증 |
| status | TESTED_SYNTHETIC: caller 선언; 실제 API·UI 전송/표시 검증 완료; 운영 전달·실행 미검증 |

## 쉬운 설명

전체 작업 지시서 원문과 전달 초안을 비교 창구에 보낸다. 지시서 일부 요약으로 원문을 다시 만들지 않는다. 같은 글의 공백 배치와 글의 구조를 각각 구분할 지문도 붙인다. 비교가 맞아도 그 지시서가 공식 원본인지, 작업을 실행해도 되는지는 별도 질문이다.

## 이론적 배경

86의 순수 선언 대조를 수동 API로 연결했다. caller는 전체 Workflow 원문, 그 canonical pin, 선택 node, 독립 제안 metadata 원문을 제공한다. 원문을 문자열로 보내 서버가 중복 JSON 키와 부정확한 문자를 직접 검사한다. 먼저 객체로 바꾸고 원문을 버리면 중복 키가 숨겨질 수 있기 때문이다.

두 지문을 구분한다. 전체 outer 요청 raw UTF8 bytes의 request_sha256는 실제 보낸 봉투의 지문이다. result.workflow_request_sha256는 전체 Workflow 구조를 canonical 직렬화한 지문이다. 공백만 바뀌면 전자는 달라도 후자는 같을 수 있다. 어느 것도 caller 선언을 공식 원본으로 인증하거나 실행을 승인하지 않는다.

## 코드와 데이터 동작

`POST /v1/workflows/node-input-handoff`는 outer 네 키 workflow_request_json/pinned_workflow_request_sha256/selected_node_id/proposed_job_metadata_json을 받는다. `parse_handoff_request`가 strict UTF8로 outer와 두 inner 원문을 파싱하고 기존86 함수를 threadpool에서 한 번 호출한다. configured Store를 받거나 DB·Registry·resolver·자산 파일·Job 생성·executor를 호출하지 않는다. 네트워크0 등 core의7IO0은 선언 대조 범위이며 HTTP 통신 자체가 없다는 뜻은 아니다.

본문은 실제 stream 누적1MiB, 두 inner는 각각512KiB로 제한한다. outer 깊이8·inner12, object키128·트리 atoms32768을 제한한다. 중복 키·NaN/Infinity·float/지수 표현·잘못된UTF8·surrogate를 거부한다. 정수는 자리수 선검사와 signed int32 범위를 적용한다. inner 문자열은256자·제어문자 제한이다. 이 입력 예산은 전체 프로세스 RAM·시간 hard cap이 아니다.

JSON 구문·중복·문자·타입 오류는400, byte/depth/atom 등 예산 초과는413, 안전 응답 검증 실패는503이다. transport를 통과한86 의미 차이·wrong pin·선택 빈 입력은200 result BLOCKED다. 자체 응답은 no-store이며 인증은 기존 main을 계승한다. 신규 RFC extension은 INTERNAL_REVIEW/present_in_upstream_openapi=false다.

응답 wrapper는 extension/approval_status/present_in_upstream_openapi/request_sha256/result의 정확5키다. `validate_handoff_response`가20false·7정수IO0·현재 요청의pin/hash/count/index·MATCH의동등성·안전issue최대324와중복부재를검사한다. 원문ID/URI/예외·큰JSON은반환하지않는다. DAG·AOI/output·predecessor·원본인증·실행승인은false를유지한다.

## 시험 증거와 실제 범위

관련 API15 PASS/0.842초·독립15 PASS/1.250초다. strict 파싱·예산·인증·안전오류·output변조·Unicode canonical golden·전체 raw요청sha를검증했다. 같은시험 반복은전체에더하지않는다.

실제 로컬 HTTP의 새POST11회는 caller가 만든 합성 선언이다. Unicode MATCH, role부재차이·wrongpin·선택빈입력 BLOCKED, outer/inner중복·UTF8·비유한400, 깊이/본문413을확인했다. 기존plan/lineage2POST응답은시각제외baseline과같았고기준선2POST는별도다. 카탈로그14기록은같고JobPOST·역채움·실행·새QA·학습은없다. 초기checker의raw요청공백차이는checker직렬화를일치시켜수정했으며application변경이아니다.

UI88의 완료 코드·시험·실제 합성 선언 시연을 확인했다. 최종 전체 회귀는897건 중896 PASS·기존 Windows symlink권한1 SKIP/382.270초·종료0이다. 현재 API가 실제로 응답했다는 사실을 운영 Workflow 전달이나 모델 결과 검증으로 확대하지 않는다.

## 한계

호출자가 원문과 pin을 함께 제공한다. 동일성 대조는 출처 인증이 아니다. MATCH에도 DAG·전체 Job·현재 파일·권한·모델 readiness·과학·실행 승인은 없다. 표시 중단은 서버 비교의 취소가 아니다. 이 API는 현재 preflight의 worker semaphore를 공유하지 않으며 자체 동시검사 semaphore도 제공하지 않는다.

기존 Workflow PLAN_ONLY/BLOCKED와 원본5차단·후보4차단, 예약136314880B·환불0을유지한다. 완료 UI의 실제 브라우저 근거는 코드·시험·build와 구분해 아래 기록했다.

## 1분 발표

“Workflow 원문과 제안 입력을 직접 비교하는 창구를 만들었습니다. 요약된 노드로 원문을 다시 만들지 않고 두 JSON 원문을 그대로 보냅니다. 실제 요청 봉투의 지문과 전체 지시서 구조의 지문을 나누어 잘못된 요청의 결과가 섞이지 않게 합니다. 실제 HTTP에서는 합성 선언의 일치와 차단을 확인했습니다. 이것은 목록 비교이며 공식 원본 인증이나 작업 실행이 아닙니다. Job을 만들거나 파일을 읽어 학습시키지 않으며 MATCH도 실행 승인은 아닙니다.”

## 5분 발표 순서

1. **0~1분:** 원 작업 지시서와 전달 초안의 비교 창구를 설명한다.
2. **1~2분:** raw 요청 지문과 canonical Workflow pin의 차이를 설명한다.
3. **2~3분:** 원문 strict JSON·예산·200 BLOCKED와400/413/503을 나눈다.
4. **3~4분:** 합성시험·실제HTTP·UI·전체회귀의 범위를 구분한다.
5. **4~5분:** 원본 인증·DAG·파일·Job 생성·실행 미검증을 말한다.

10분 설명에서는 Unicode golden, 응답의 전체 요청 결속, issue 실제 index 검증과 편집/선택/route 세대 폐기를 추가한다.

## Q&A

**POST면 Job을 제출하나?** 아니다. 선언 비교 요청이며 Job 생성 API가 아니다.

**공백만 바꾸면 pin이 달라지나?** raw outer 요청 지문은 달라질 수 있다. 같은 Workflow 구조의 canonical pin은 같을 수 있다.

**pin이 맞으면 공식 원본인가?** caller가 선언한 내용이 같다는 뜻이다. 원본 인증은 별도다.

**왜 JSON 원문을 보내나?** 서버가 중복 키와 문자·구조를 직접 검사하고 원문 변형을 숨기지 않기 위해서다.

**실제 Workflow 실행을 확인했나?** 로컬 HTTP의 합성 선언 비교만 확인했다. 실행기·Job POST·학습은 없다.

## 이후 갱신

UI88·전체 회귀·보존 근거를 읽고 INDEX·계약·구조·06·용어·발표·FAQ·변경 이력을 함께 갱신했다. 다음은 PLANNED다. 사용자가 작성한 full Job request를 원 schema로 검증한 뒤 선택 metadata를 추출해86과 대조할 계획이다. AOI/output/model/context를 채우거나 Job을 만들지 않는다. schema cold read가 있어 전체 IO0으로 부르지 않으며 AOI 소수를 허용해야 하므로87의 int-only parser를 그대로 재사용하지 않는다. 아직 이 후속 구현과 실제 검증은 없다. 전체 개발과10분 보고는 계속된다.


## UI88 연결과 실제 시연 범위

GeoQuery 실행계획 화면에 `WorkflowNodeHandoff`를 독립 child로 연결했다. 원문 planJson과 executionRevision을 받고 선택 node와 제안 metadata는 빈 수동 입력으로 시작한다. 기존 plan/lineage 응답의 요약 nodes로 원요청을 다시 만들거나 제안을 자동 채우지 않는다. 명시 버튼만 새 POST를 보낸다.

adapter는 원문 strict parse와 Unicode code point 정렬을 사용해 Python canonical golden과 대조한다. JavaScript 객체의 숫자 모양 key 재열거를 피하려고 canonical 문자열을 직접 구성한다. 실제 전송한 outer JSON.stringify bytes SHA와 응답 wrapper를 묶고 선택 node·제안 metadata의 지문도 확인한다. 편집·선택·execution revision·route·back/forward·표시 중단이 이전 세대를 폐기한다. 기존 계획/계보 조회 완료만으로 새 결과를 지우지 않는다.

최종 신규13 PASS/1400.1225ms·전체113 PASS/2260.0008ms·독립13 PASS/2073.8207ms다. build19.17초 PASS이며 기존 chunk 크기 경고가 있다. 별도 core→UI 합성14경우 교차검산은 시험 합계에 더하지 않는다. SVG와 제목 간격은 신규 scoped CSS에서 보완했다.

실제 UI5174/#/view/15의1449×1087에서 합성 선언으로 수동 MATCH·role drift BLOCKED·없는 node/null·중복JSON 로컬 거부를 확인했다. 비교POST6회와 기존 진단POST2회는 별도다. 기존 plan/완료 lineage 결과와 독립, node/proposal/Workflow 편집 clear와 back/forward 폐기를 확인했다. 문서·패널 가로 넘침0/콘솔 오류0이었다. 시연 후 원래 Workflow 초안을 원문 그대로 복원하고 합성 node/proposal/result는 지웠다. 스크린샷은 복원 전 합성 시연이다.

모바일·강제 지연/취소·브라우저503/인증 실패·원래5173 적용은 확인하지 않았다. 실제 UI/API를 사용한 합성 선언 검증이지 운영 Workflow 실행·원본 인증·실제 Job 전달은 아니다. 기존 plan/lineage 진단은 Registry를 읽을 수 있으므로 새 비교의7IO0을 그 경로에 확대하지 않는다.


## 최종 전체와 보존

최종 backend 전체897건 중896 PASS·기존 Windows symlink 권한 제약1 SKIP,382.270초·종료0이다. 기존 deterministic 경계시험은 통과했다. API 관련/독립 각15개와 UI 신규/독립 각13개, 별도 교차검산·HTTP/UI 요청을 이 수에 더하지 않는다. production build는84 modules/19.17초 PASS다.

시험 후 보호141참조·기존51코어·catalog14·기존Job2 본문이 같았다. 기존 추적 코드 변경은 허용한 main.py 배선과 GeoQuery.tsx child mount 두 파일뿐이다. 이는 지정한 보호 범위이며 전체 워크스페이스나 원자 snapshot 보장이 아니다. JobPOST·역채움·executor·새QA·학습은0이다. 실제 전송과 표시가 검증됐어도 내용은 합성caller선언이며 원본·자료·모델·실행 인증은 아니다.
