# 94 — 완성 Job 초안의 로컬 등록관계 관측 RFC2

## 2026-10-17 — model_ref 고정 문자 선언 검사 통일 (96)

`model_reference_contract.model_reference_issue()`를 GMAIS 제출 검사와 89 초안 검사에서 공유한다. id/version 및 제공한 role은 기존 89와 같은 1..256자 지원 범위로 확인하며, 공백만 있는 문자열·제어문자·단독 surrogate와 latest/current 버전 별칭을 거부한다. 정상 고정 문자열을 trim하거나 바꾸지는 않는다. 기존에 지원하던 패딩된 고정 v1과 256자 경계도 유지한다.

GMAIS는 기존 schema·SHA 검사를 먼저 하고, 새 문자 거부를 Store 접근 전 기존 `400 INVALID_REQUEST` 형식으로 반환한다. 이는 공통 제출 API의 허용 입력을 좁히는 변경이다. 89의 기존 모델 차단 코드와 순서, RFC1/RFC2 결과, 24개 false 플래그는 보존한다. 원 schema에서 SHA는 양쪽 모두 필수이며 helper가 SHA/URI/키 정책을 대신하거나 완화하지 않는다. model_ref 부재는 그대로이고 명시 null은 기존 schema 오류다.

이 검사는 문자 선언의 지원 범위만 확인한다. 실제 등록 모델·checkpoint·권위 있는 model version·기관 ACL·과학·실행 승인을 조회하지 않으며 `model_verified=false`를 유지한다. 기존 UI 오류 표시로 처리할 수 있어 직접 프론트 수정·build·브라우저 재시험은 없다. 지원 범위, 새 오류와 격리시험 근거는 [문서96](96_model_reference_contract.md)를 참조한다.

상태: **TESTED_SYNTHETIC**. 합성 초안과 실제 로컬 static manifest 함수로 API 계약을 검증했다. 등록관계는 실제 Agent capability 지원·기관 ACL·과학적 적합성·실행 승인이 아니다.

## 목적과 호환성

기존 `POST /v1/workflows/full-job-input-handoff`에 명시적인 opt-in RFC2를 추가한다. 원 89의 schema/bbox/선택노드 metadata 비교 결과를 그대로 안에 보존하고, 그 결과가 MATCH일 때만 로컬 static manifest에 Agent/capability 등록관계가 있는지 별도로 관측한다.

`contract_version` 키가 없는 기존 정확4키 요청은 RFC1이다. 기존5키 wrapper의 extension·89 결과·오류 계약을 유지한다. 원89/core·vendored schema·93의 등록관계 helper·기존 Job/Workflow 제출 정책은 수정하지 않는다.

## 요청

RFC2는 기존 정확4키에 `contract_version`만 추가한 정확5키 객체다. version은 JSON **정수 2**만 허용한다. bool, 1, 3, 2.0, 문자열 "2", null, 추가/누락 키는 기존 `400 INVALID_REQUEST`다. absent version과 명시적인 version1을 같은 요청으로 취급하지 않는다.

```json
{
  "contract_version": 2,
  "workflow_request_json": "{사용자가 작성한 원 Workflow JSON}",
  "pinned_workflow_request_sha256": "caller가 보유한 Workflow canonical SHA256",
  "selected_node_id": "명시적으로 선택한 node",
  "full_job_request_json": "{사용자가 작성한 완성 Job 초안 JSON}"
}
```

기존90의 바깥 body1MiB/원문별512KiB·Workflow 정수 parser·fullJob 별도 decimal/지수·finite/int53·비영 underflow0/overflow·숫자 lexeme/UTF8/중복 key/깊이/atom 한도를 그대로 적용한다. FullJob은 관측 Python canonical hash이며 caller pin/출처 인증이 아니다.

## 응답

바깥 wrapper는 기존 정확5키다. extension만 `greenblue.workflow-full-job-input-handoff.rfc2`이고 `approval_status=INTERNAL_REVIEW`, `present_in_upstream_openapi=false`, 전체 수신 RAW body의 `request_sha256`, `result`를 반환한다.

RFC2 result는 다음 정확8키다.

```json
{
  "schema_version": 2,
  "scope": "WORKFLOW_FULL_JOB_LOCAL_REGISTRATION_OBSERVATION_ONLY",
  "status": "MATCH",
  "full_job_comparison": {"기존89결과": "전체를 변경 없이 보존"},
  "local_manifest_registration": {
    "source": "LOCAL_STATIC_AGENT_MANIFESTS",
    "status": "REGISTERED",
    "checked": true
  },
  "actual_capability_supported": false,
  "institution_acl_verified": false,
  "execution_authorized": false
}
```

예시의 inner 객체 표기는 자리 표시자이며 실제 응답은 기존89의 완전한 safe 결과다. 원래24개 false와 `agent_capability_verified=false`도 유지한다. 새 등록관계 관측을 해당 기존 미검증 값을 true로 바꾸는 근거로 사용하지 않는다.

| Inner89 결과 | 등록관계 상태 | checked | RFC2 바깥 상태 |
|---|---|---|---|
| BLOCKED | NOT_RUN | false | BLOCKED |
| MATCH | REGISTERED | true | MATCH |
| MATCH | AGENT_UNKNOWN | true | BLOCKED |
| MATCH | CAPABILITY_UNREGISTERED | true | BLOCKED |

`checked=true`는 로컬 등록관계 조회를 마쳤다는 뜻이다. Agent가 없거나 capability가 없어도 true이며, 실행 가능한 실제 기능 지원을 뜻하지 않는다. 원89의 schema/date/bbox/metadata 차단과 새 관측 축을 구별한다.

## 구현과 안전 검증

- `backend/app/workflow_job_registration_handoff.py`: `compare_workflow_job_registration_handoff(workflow_request, pinned_workflow_request_sha256, selected_node_id, full_job_request)`가89를 정확1회 호출한다. inner MATCH 이후에만 `gmais_api._agent_manifests()`와93 `agent_capability_issue()`를 사용한다.
- Job 제출과 같은 첫 manifest 일치를 선택한다. 중복 Agent ID 거부·정규화·readiness 판단은 추가하지 않는다. 내부 manifest의 목록/객체·id/capability 문자열 형태가 깨졌거나 함수가 예외를 내면 HTTP 경계에서 safe503으로 닫는다. raw manifest/ID/URI/예외 원문을 응답에 추가하지 않는다.
- `validate_registration_handoff_response()`는 기존89 safe validator를 callable로 재사용해 inner hash/단계/index/false/I/O 상태를 검증한다. 새 result/axis의 정확 key·정수/boolean·phase·세 false·outer 상태를 검증한다.
- forged REGISTERED와 outer MATCH가 서로 일관되어도 요청 Job과 로컬 관측을 다시 대조해 차단한다. 따라서 inner MATCH 경로는 생산/독립 안전검증에서 **인메모리 static manifest 조회 총2회**, inner BLOCKED 경로는0회다. 89/86 comparator를 재실행하지 않는다.
- Store/DB·원격 Registry·네트워크·원본 asset·resolver/executor 접근/Job 저장·Workflow 실행을 추가하지 않는다. inner의 기존7 I/O0와 schema cold read 미계측 `null`을 유지하며, 단위 전체 schema 파일 읽기를0으로 표시하지 않는다.

## 오류·인증·UI 인계

잘못된 transport/JSON/version은 기존400, byte/depth 등 예산 초과는413, schema 자원 실패·예상 밖 예외·manifest 실패·오염 응답은503이다. 오류는90과 같은 고정 code/message/retryable 객체와 `Cache-Control: no-store`다. 정상 JSON의 inner 차단이나 미등록 관측은200 BLOCKED다. 기존 main 인증을 승계한다.

UI 담당은 기존 수동 패널에서 RFC2를 명시 요청하고 inner89의 schema/metadata 결과와 로컬 관측 축을 구분해 표시한다. RAW body SHA로 결합하고 outer/inner·checked·false 상태를 안전 검증한다. 요청 자체가 version을 생략하면 RFC1 호환을 유지하지만, RFC2 요청에 돌아온 RFC1을 RFC2 완료로 표시하지 않는다. 편집/route/back/revision 무효화와 기존 결과 독립성은 UI95 검증 범위다.

## 시험 근거

신규 core8/API10, 합계 **18 PASS / 2.887초**: `full-job-registration-api-development-20261017.log`. 상태4가지·inner 불변·첫 manifest 선택·readiness 무관·인메모리2조회/89 1회·inner BLOCKED0조회·manifest 오류·관측 위조/phase/typed false 오염·privacy·인증/no-store·strict/한도/decimal을 검증했다.

수정 전 API 바이트는 `evidence/integration/full-job-registration-api-original-20261017.py`, SHA256 `48dcd410e6e259d1c0d3537cb4cb9585c2f0c8c836ee35a8a9f388197656a98d`에 고정했다. 이 원 모듈 router를 격리 앱에서 실행해 기존 RFC1 정상/차단/오류8경우의 status·전체 header·응답 byte를 정확 대조했다. 원90 시험은 수정하지 않는다. 경계 반복과 전후 대조를 신규 시험 수에 중복 합산하지 않는다.

관련 회귀 `evidence/integration/full-job-registration-api-related-20261017.log`: **69 PASS / 8.515초**(신규18+기존89/90·93·92). 독립·전체·실제 HTTP/UI·보존·이해자료 갱신은 Root closeout/인계서를 따른다. 운영 Job POST·수집/QA/학습/배포는 없다. 실행 중 non-reload 서버의 소스 적용은 별도 확인 없이 주장하지 않는다.

## 관련 문서

- [89 내부 초안 검사](89_workflow_job_request_handoff.md)
- [90 RFC1 API](90_full_job_handoff_api.md)
- [93 등록관계 공통 계약](93_agent_capability_contract.md)

## Root 최종 통합 확인

전체backend966개/965 PASS/기존1 SKIP/350.995초/exit0. 보호141·불변core+schema62·catalog14/기존Job본문·이전증거576파일을보존했다. 관련API69/독립18·프론트137/build88modules19.48초는각시험종류별근거이며반복사례를신규시험수에더하지않는다.

`full-job-registration-api-live-api-20261017.json`은8002합성진단HTTP15경우, `full-job-registration-api-live-ui-20261017.json`은5174실제브라우저13check를기록한다. RFC1보존·로컬등록/차단/NOT_RUN·중복400·버전전환/old88독립·접기펼치기/편집clear·뒤로가기초기화와원Workflow정확복원을확인했다. 9회fullJob수동클릭+1회old88클릭은네트워크계측치가아니다.1449×1087 overflow0/console[]·SVG정렬과정상/차단PNG를확인했다. 모바일·강제지연/취소·브라우저503/auth·5173·이번forward는미검증이다.

8002진단/5174화면의합성초안확인과운영Job제출/Workflow실행·기관ACL/과학/승인은구분한다. nonreload8000/8001적용미검증·운영Job생성/수집/정식학습/배포0. 관련문서·인계서와이해자료/대본/FAQ·INDEX/변경이력을같은단위로갱신하며최종감사는 `evidence/integration/full-job-registration-api-closeout-20261017.json`을따른다.

## 104 별도 내부 Workflow 모델 대조 연결

[연결함수104](104_workflow_job_model_record_handoff.md)는원89결과를그대로유지하며정상MATCH뒤에모델참조가있을때만exact3 identity를추출해103과호출자제공레코드를대조한다. 89차단후wrapper추가접근/1030,참조부재1030,참조존재1031회다. outerOBSERVED는대조수행관측일뿐일치·승인이아니고nested103과5false로한계를구분한다. 기존89/94/RFC1/2·103/API/UI출력은변경하지않았다. URI해결·Registry/resolver·바이트검증·기관/실행승인0이다. 원89coldschema읽기와wrapper추가IO0은구분한다. [관련·독립시험/보존](../../evidence/integration/workflow-model-record-live-integrity-20261017.json)은합성근거이며운영Workflow참조시험이아니다. 이번전체/frontend/build/browser재시험없음도이전전체근거와구분한다.

### 105/106 후속 연결 및 검증

별도 비변경 진단 API와 수동 UI를 연결했다. 기존 RFC1/RFC2 결과·승인 경계를 유지한다. 새 계약·원문/한도·생산과 검증 호출 수·실제/합성 시험 및 한계는 [API105](105_workflow_job_model_record_handoff_api.md), [UI106](106_workflow_model_record_handoff_ui.md)를 따른다. 최종 전체 회귀·브라우저·보존 근거는 `evidence/integration/workflow-model-record-api-live-integrity-20261017.json`과 `evidence/integration/workflow-model-record-api-live-ui-20261017.json`이다. 이해자료·인계서도 같은 단위로 갱신했다. metadata 일치는 실바이트·권위·과학/실행 승인이 아니며 운영 Job 생성/등록은 없다.
