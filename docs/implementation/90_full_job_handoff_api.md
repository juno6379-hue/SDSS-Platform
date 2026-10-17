# 90 — 완성 Job 초안 입력 전달 검사 수동 API

## 2026-10-17 — model_ref 고정 문자 선언 검사 통일 (96)

`model_reference_contract.model_reference_issue()`를 GMAIS 제출 검사와 89 초안 검사에서 공유한다. id/version 및 제공한 role은 기존 89와 같은 1..256자 지원 범위로 확인하며, 공백만 있는 문자열·제어문자·단독 surrogate와 latest/current 버전 별칭을 거부한다. 정상 고정 문자열을 trim하거나 바꾸지는 않는다. 기존에 지원하던 패딩된 고정 v1과 256자 경계도 유지한다.

GMAIS는 기존 schema·SHA 검사를 먼저 하고, 새 문자 거부를 Store 접근 전 기존 `400 INVALID_REQUEST` 형식으로 반환한다. 이는 공통 제출 API의 허용 입력을 좁히는 변경이다. 89의 기존 모델 차단 코드와 순서, RFC1/RFC2 결과, 24개 false 플래그는 보존한다. 원 schema에서 SHA는 양쪽 모두 필수이며 helper가 SHA/URI/키 정책을 대신하거나 완화하지 않는다. model_ref 부재는 그대로이고 명시 null은 기존 schema 오류다.

이 검사는 문자 선언의 지원 범위만 확인한다. 실제 등록 모델·checkpoint·권위 있는 model version·기관 ACL·과학·실행 승인을 조회하지 않으며 `model_verified=false`를 유지한다. 기존 UI 오류 표시로 처리할 수 있어 직접 프론트 수정·build·브라우저 재시험은 없다. 지원 범위, 새 오류와 격리시험 근거는 [문서96](96_model_reference_contract.md)를 참조한다.

## 2026-10-17 — 선택형 완성 Job 로컬 등록관계 API·UI(94/95)

기존 수동 `/v1/workflows/full-job-input-handoff`에서 `contract_version`이 없는 정확4키 요청은 기존RFC1로유지한다. 사용자가기존details의기본off ‘로컬 등록관계도 확인 (RFC2)’를선택하고수동버튼을누를때만정확5키/정수2의RFC2를요청한다. RFC2는89의원결과를그대로보존하고innerMATCH때만Job제출과같은로컬staticmanifest firstmatch+93membership관계를관측한다. innerBLOCKED면등록관계는NOT_RUN이다.

등록됨도실제capability지원·모델/readiness·기관ACL·과학/실행승인이아니며inner24false/7IO0/schema읽기null과outer3false를유지한다. 생산·안전재검증의인메모리manifest관측2회와네트워크/Store0을구분하고관측변동·오염은503으로닫는다. UI는전체요청SHA와버전포함identity/편집·route/back세대폐기를적용하고outerBLOCKED와innermetadataMATCH를분리해표시한다.

실제8002진단HTTP15경우와5174브라우저합성초안으로정상·차단·오류·선택전환/뒤로가기를확인했고원Workflow초안을복원했다. 이는운영Job제출/Workflow실행승인이아니다. 요청/응답·지원범위·원문한도·시험/화면근거는 [API94](94_full_job_registration_api.md)·[UI95](95_full_job_registration_ui.md)를참조한다. 기존89/90/91 및93의정의는각단위이력으로보존한다.

## 2026-10-17 — 공통 날짜 형식 검사 환경 일관성 보완(92)

`schema_formats.create_format_checker()`를 공통 Job/Workflow cached validator 생성부와89의 `_draft_format_checker()` 호환 wrapper가 재사용한다. 선택 date-time dependency가 없는 현재환경에서도 새로 생성되는 공통Job검사기가 날짜·시각·시간대의 지원형식을 확인한다. 전역 FormatChecker registry와 이미 만들어진 checker 객체를 후행변조하지 않고 vendored 원schema를 보존한다. 89/90의 날짜오류200BLOCKED와 기존제출의 INVALID_REQUEST400 형태를 유지하며, 공통제출은 잘못된날짜를 Store 접근전에 거부한다.

지원범위는 기존89와 같은 T/t·Z/z·소수초·실제달력·offsetHH00..23/MM00..59인 zoned부분집합이다. leap second와연도0000은지원하지 않으며 기간순서·시간대변환·과학/기관ACL·실행승인 검사는추가하지 않는다. UI담당 읽기검토 결과 기존오류화면계약을유지해 직접프론트변경·build·브라우저재시험은없다. 자세한계약·시험근거·운영적용한계는 [문서92](92_common_datetime_validation.md)를참조한다. 이전절의 공통검사개선대기/미수정은 각단위시점의 이력이며 현재92의source 변경범위와구분한다. non-reload 기존API프로세스의 새코드적용은별도미검증이고, 격리시험을운영Job제출성공으로표현하지 않는다.

상태: **TESTED_SYNTHETIC**. 구현·합성 HTTP 계약 시험이며 운영 Workflow+Job의 실제 실행·기관 승인 근거가 아니다. 기존89 core와86~88·원schema·기존 제출 API는 수정하지 않는다.

## 목적과 파일

89 내부 helper를 별도 수동 진단 POST에 연결한다. 완성 Job을 만들거나 저장/제출하지 않고 caller가 보낸 원Workflow와 원Job JSON을 해석해 schema 지원 검사와 선택노드 metadata 일치를 확인한다. MATCH는 실행 준비/ACL/과학/모델·Agent capability/Workflow 출처 인증이 아니다.

- 구현: `backend/app/workflow_job_request_handoff_api.py`.
- 시험: `tests/test_workflow_job_request_handoff_api.py`.
- router factory: `create_workflow_job_request_handoff_router()`; main import/include는 Root 소유.
- 기존 내부 계약: `docs/implementation/89_workflow_job_request_handoff.md` 및 `docs/implementation/86_workflow_node_input_handoff.md`.

## 요청

`POST /v1/workflows/full-job-input-handoff`, 정확한 네 키 객체:

```json
{
  "workflow_request_json": "<원Workflow JSON 문자열>",
  "pinned_workflow_request_sha256": "<64자리 lowercase SHA256>",
  "selected_node_id": "<명시 선택 node ID>",
  "full_job_request_json": "<사용자 작성 완성Job JSON 문자열>"
}
```

원문 문자열 두 개를 재구성/정규화/자동채움하지 않는다. Workflow pin은87과 동일한 Python-compatible integer-only Workflow canonical 계약이다. fullJob의 AOI/output/purpose/environment/approval_ref를 추정하지 않는다. 문자열 숫자를 숫자로 바꾸지 않고 bool을 numeric bbox 값으로 취급하지 않는다.

## transport 한도와 decimal 지원

- 실제 stream 누적 수신 body 최대1MiB, 원문별 UTF8 최대512KiB. Content-Length를 신뢰해 생략하지 않는다. outer depth8, 중복 key/잘못된 UTF8/surrogate/NaN/Infinity를 거부한다.
- Workflow는87 `_strict_json(inner=True)`를 재사용한다. depth12·string256·int32 및 float 거부를 유지한다. 기존87 source 변경0.
- fullJob는 별도 parser로 depth24·atom16384(key 포함)·string4096codepoint·key256·정수 ±(2^53-1)·finite 소수/지수 표기를 허용한다. 숫자 lexeme128 문자 선한도 및 정수 digits/bit_length를 변환 전에 적용한다. -0 정수는 JSON 숫자로0, -0.0은 float 부호를 보존하고1.0/1e0도 float로 해석한다.
- float overflow와 **비영 coefficient의 underflow-to-zero**를 거부한다. 0e-999와 같은 진짜0은 허용하고 유한 subnormal 5e-324는 허용한다. lexeme128 이하라도 Decimal의 지원 범위를 넘는 거대 exponent는 DecimalException을 ValueError로 바꾸어400으로 닫는다. 0e거대지수/1e거대음수지수 회귀를 포함한다.
- parser의 JSON nesting depth24는89의 root-depth0보다 일부 경계에서 엄격할 수 있다. 문자열·key/atom/numeric lexeme·depth/bytes 예산초과는413이다. syntax·dupe·UTF8·finite/int범위·underflow/지원불가exponent는400이다. parser가 통과해도89의 canonical 누적bytes 등 지원한도에서 BLOCKED일 수 있다.

## 응답과 실패

200 wrapper는 정확히 다음 다섯 키다. result는89 원payload이며 필드를 추가/삭제하지 않는다.

```json
{
  "extension": "greenblue.workflow-full-job-input-handoff.rfc1",
  "approval_status": "INTERNAL_REVIEW",
  "present_in_upstream_openapi": false,
  "request_sha256": "<전체 수신 raw UTF8 body SHA256>",
  "result": "<89 payload 객체>"
}
```

원문 formatting까지 포함한 전체 body SHA는 요청/응답 결합용이다. fullJob schema INVALID·bbox/model/workflow ID·metadata 불일치 같은 정상 진단은200 BLOCKED다. core89 validator_status RESOURCE_UNAVAILABLE는 **고정 HTTP503**으로 매핑하여 원문 result를 내보내지 않는다. 모든 정상/오류 응답은 Cache-Control:no-store이며 인증은 main의 기존 router/middleware 설정을 상속한다.

고정 오류 형식은 `{"error":{"code":"...","message":"...","retryable":false}}`다.

| HTTP | code | message |
| --- | --- | --- |
| 400 | INVALID_REQUEST | Invalid full Job handoff request. |
| 413 | REQUEST_TOO_LARGE | Full Job handoff request exceeds limits. |
| 503 | RESOURCE_UNAVAILABLE | Full Job handoff comparison is unavailable. |

에러 원문/원ID/URI/trace·body는 반환하지 않는다. 예상 밖 parser/core/response 오염의 Exception은503이다. BaseException은 잡아 정상 결과로 숨기지 않는다.

## 응답 안전 검사와 I/O 범위

89 helper는 threadpool에서 정확히1회 호출한다. 그 반환을 exact key/typed schemaVersion/status/단계 bool/24false/7 typed I/O0/schema_files_read=null/comparator0or1/nullable SHA/issue code로 확인한다. 실제 bounded 입력에서 가능한 validator attempted·NOT_RUN/INVALID/VALID/RESOURCE_UNAVAILABLE 상태와 bbox/model/workflow ID 조기차단을 대조한다. 전체 Job 관측 canonical SHA, 추출 metadata SHA, inner86의 pin/선택노드/index·입력 count/hash·issue실제배열경계·false flag를 재검증한다. 오염·retarget·불가능 단계는safe503이다.

fullJob hash는 **server Python canonical 관측값**이다. client의 JSON.stringify fullJob hash와 비교하지 않는다. Workflow caller pin 또는 fullJob 출처 인증/초안 pin과 혼동하면 안 된다. 같은 metadata라도 AOI/output/parameters가 달라지면 전체 관측 hash가 달라질 수 있으며 기대 AOI를 검증한 것은 아니다.

schema cold load의 local schema 읽기는 미계측null을 보존한다. 전체 I/O0로 주장하지 않는다. 원본 source asset 읽기·쓰기/DB/Registry/resolver/executor/network 호출0, 실제 Job 생성·제출·역채움·QA/학습/수집/배포0이다. main auth 및 schema read는 source asset 접근·운영 승인과 구분한다.

## 시험과 인계

`evidence/integration/full-job-handoff-api-related-20261017.log`: **15 PASS/1.275초**. threadpool1회·원문불변·rawbodySHA·privacy/Store0·소수/1.0/지수/-0/subnormal/zero·under/overflow·거대exponent·중복/UTF8/surrogate·size/depth/key/atom·quotednumeric/bool·schema 정상BLOCKED·resource503·typed/hash/index/phase오염·인증상속·stream한도·기존87 router응답불변을 합성 HTTP 시험했다. 독립/전체/실제서버 결과는 Root 인계서에 별도 기록한다.

UI91 담당에게 exact envelope/wrapper·고정오류·200 BLOCKED와503 resource·fullJob관측hash/Pythondecimal 차이·수동요청만 허용 계약을 전달했다. UI 연결·프론트 시험·실제브라우저 확인은91 및 Root의 별도 근거다. 본 문서의 TestClient 성공을 실행 중 서버 적용이나 UI 완료로 간주하지 않는다.


## Root 실제 HTTP·브라우저 확인

`evidence/integration/full-job-handoff-api-live-api-20261017.json`은 최종새endpoint19POST와 기존plan/lineage/88세진단POST를 시작기준선3POST와 대조했다. 소수·지수·음의0의MATCH, AOI만변경시관측fullJobSHA변경/metadataSHA동일, schema/날짜·role·pin·선택차단, outer/inner중복·UTF8·overflow/비영underflow/거대exponent400, 숫자lexeme/원문/깊이/body413이통과했다. 기존세진단응답은volatile시각외동일하며catalog14/Job본문동일·JobPOST0이다. 자원503·인증·응답오염은격리시험근거다.

`evidence/integration/full-job-handoff-api-live-ui-20261017.json` 및 `full-job-handoff-ui-desktop-20261017.jpg`: 실제5174/#/view/15에서합성초안8POST(중복JSON400포함)/기존3진단으로MATCH·날짜형식차단·role메타차단·없는node/null·schema읽기미계측표시를확인했다. 기존세조회와독립/역방향88결과유지, 접기/펼치기상태유지, fullJob/node/Workflow편집clear·뒤로/앞으로이동후빈기본disabled를확인했다.1449×1087 문서/패널overflow0·console[]·SVG헤더정렬확인. 시험후원Workflow원문복원/합성node/fullJob/결과제거. JPG는복원전합성시연이다.

모바일·강제지연/취소경합·브라우저503/인증·5173적용은미검증이다. 실제운영Workflow/Job제출·실행·수집/QA/학습없음. 비교의자산/DB/Registry0과기존진단읽기/원schema파일미계측을구분한다. 전체회귀·최종보존·문서감사는Root완료절을따른다.


## 20:24 KST — 완성 Job 초안의 수동 API·UI 연결 검증 완료 (90/91)

- **full_job_handoff / API:** POST /v1/workflows/full-job-input-handoff와 main배선 완료. 관련15 PASS/1.275초·독립15 PASS/1.075초. 원문4키·Workflow정수/fullJob별도decimal규약·finite/int53·비영underflow0/overflow/Decimal예외·byte/depth/atom/lexeme·중복UTF8를 검증했다. schemaINVALID200BLOCKED/transport400/예산413/스키마자원·오염503 구분과 인증/no-store·exact89phase/24false7IO0/schema읽기null/inner86방어를 유지한다.
- **full_job_handoff_ui / 화면:** 기존88 아래 독립접이식 FullJobHandoff를 적용했다. 신규14 PASS/3122.0076ms·전체127 PASS/5013.0695ms·독립14 PASS/4369.1739ms·production87modules/build16.14초 PASS(기존chunk경고).14시험에 Python89→JS8경우 교차검산(257문자id/role·65refs정당BLOCKED포함)이 포함되며 별도합산하지 않는다. fullJob원문서버strict위임·metadata-only확장canonical·fullJobPython관측hash표시만/JSfloathash불대조를 검증했다.
- **Root 실제HTTP/UI:** 새19POST+기존plan/lineage/88세진단은 기준선3POST와동일응답(volatile시각제외)이었다. AOI만변경시관측fullJobSHA변경/metadataSHA동일도확인했다. 실제5174/#/view/15 합성초안8POST(중복400포함)로 소수/지수/음0 MATCH·날짜schema차단·role메타차단·없는node/null·미계측schema읽기를 확인했다. 기존세조회/역방향88결과독립·접기펼치기보존·편집(node/fullJob/Workflow)clear·뒤로앞으로이동후빈기본disabled·1449×1087 overflow0/console[]·SVG헤더정렬을 확인하고JPG를저장했다. 원래Workflow초안은원문복원/합성필드·결과제거했다. 모바일·강제지연/취소·브라우저503/인증·5173적용은미검증이다.
- **전체·보존:** backend927개/926 PASS/기존Windows symlink1 SKIP/370.179초/exit0. 보호141·불변core+schema56 변경0·catalog14/기존Job본문동일. 기존tracked code변경은허용main.py+GeoQuery.tsx뿐이고89/86~88/원schema/기존공통validator는그대로다. 원본·원장/lock·예약136314880B·분할·모델·후보1095/차단4·학습BLOCKED보존. 실제JobPOST/역채움/Workflow실행·새QA/학습·수집/배포0. Vite2/API3유지·관측한Python/node수집학습후보[]이며geoai-2 ACTIVE10분은예약설정이다.
- **문서·이해자료:** 신규90/91·관련07/89/88·운영원장/소유권/인계서를 갱신했다. understanding_agent에 완료코드/시험·실제HTTPUI·보존을 전달해 쉬운설명·이론·코드데이터·시험·대본/FAQ·INDEX/변경이력을 같은단위로 갱신한다. 최종문서감사/rawSHA snapshot은 `evidence/integration/full-job-handoff-api-closeout-20261017.json`에기록한다.
- **범위·다음:** 실제API/UI에합성초안을사용한 TESTED_SYNTHETIC이며운영Job제출/Workflow실행검증이아니다. schema/bbox숫자순서/metadata일치도과학적AOI/output·모델/Agentcapability·기관ACL/원본인증/실행승인이아니다. fullJobSHA는Python관측값·schema파일읽기는미계측null로범위를구분한다. 다음은알려진공통date-time선택dependency공백을공통detached FormatChecker factory추출로개선하는작은단위(PLANNED/미착수)다. 전체개발은미완료이며대기열과10분보고를유지한다.

근거: `evidence/integration/full-job-handoff-api-live-integrity-20261017.json`, `evidence/integration/full-job-handoff-api-live-api-20261017.json`, `evidence/integration/full-job-handoff-api-live-ui-20261017.json`.
