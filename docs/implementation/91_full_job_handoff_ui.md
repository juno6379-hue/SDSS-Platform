# 91 — 완성 Job 초안의 독립 수동 검토 UI

## 2026-10-17 — 선택형 완성 Job 로컬 등록관계 API·UI(94/95)

기존 수동 `/v1/workflows/full-job-input-handoff`에서 `contract_version`이 없는 정확4키 요청은 기존RFC1로유지한다. 사용자가기존details의기본off ‘로컬 등록관계도 확인 (RFC2)’를선택하고수동버튼을누를때만정확5키/정수2의RFC2를요청한다. RFC2는89의원결과를그대로보존하고innerMATCH때만Job제출과같은로컬staticmanifest firstmatch+93membership관계를관측한다. innerBLOCKED면등록관계는NOT_RUN이다.

등록됨도실제capability지원·모델/readiness·기관ACL·과학/실행승인이아니며inner24false/7IO0/schema읽기null과outer3false를유지한다. 생산·안전재검증의인메모리manifest관측2회와네트워크/Store0을구분하고관측변동·오염은503으로닫는다. UI는전체요청SHA와버전포함identity/편집·route/back세대폐기를적용하고outerBLOCKED와innermetadataMATCH를분리해표시한다.

실제8002진단HTTP15경우와5174브라우저합성초안으로정상·차단·오류·선택전환/뒤로가기를확인했고원Workflow초안을복원했다. 이는운영Job제출/Workflow실행승인이아니다. 요청/응답·지원범위·원문한도·시험/화면근거는 [API94](94_full_job_registration_api.md)·[UI95](95_full_job_registration_ui.md)를참조한다. 기존89/90/91 및93의정의는각단위이력으로보존한다.

상태: **TESTED_SYNTHETIC** — 신규 adapter·컴포넌트·부모 mount의 프론트 시험 및 Python89 교차 검산 완료. 실행 중 서버 적용·실제5174 브라우저의 합성초안 관측을 완료했고 Root의 검증 절에 기록했다. 운영 Workflow/Job 검증·제출·실행은 아니다.

## 화면과 사용자 동작

GeoQuery의 실행 요청 종류에서 기존 Workflow 노드 metadata 검사 아래 `완성 Job 초안 검토`를 연다. 사용자가 선택 node_id와 완성 Job JSON 원문을 직접 입력하고 `완성 Job 초안 입력 전달 검사`를 클릭한다. 두 입력은 빈 상태로 시작하며 AOI·출력·model·context·metadata를 자동 생성/복사하지 않는다. 펼치기·렌더·편집·기존 계획/계보/metadata 조회로 자동 요청하지 않는다.

`FullJobHandoff.tsx`는 독립 busy/result/error/request/generation을 갖는다. planJson/node/fullJob/executionRevision 변경, hashchange/popstate, 응답 표시 중단과 unmount는 기존 응답 표시를 무효화한다. 서버 처리 취소를 주장하지 않는다. 기존88 컴포넌트/adapter/CSS 변경은 없으며 GeoQuery import와 실행 종류 안의 독립 child mount만 추가했다.

## API·숫자·응답 결합 계약

POST `/v1/workflows/full-job-input-handoff`에 정확한 네 키 `workflow_request_json`, `pinned_workflow_request_sha256`, `selected_node_id`, `full_job_request_json`을 보낸다. Workflow는 기존87 parser/canonical/SHA protocol을 재사용한다. fullJob은 입력 원문을 그대로 보존한다. 클라이언트의 JSON.parse는 metadata 추출 프리뷰만 수행하며 중복 키·소수/지수·finite/overflow/underflow·숫자 lexeme·atom/depth·문자 한도의 최종 판정은90 서버 strict parser가 담당한다. 새 fullJob parser를 구현하거나87 정수전용 parser를 fullJob에 적용하지 않는다.

실제 agentApi의 JSON.stringify 요청 전체 UTF8 SHA와 응답 request_sha256를 대조한다. exact wrapper extension은 `greenblue.workflow-full-job-input-handoff.rfc1`, approval_status INTERNAL_REVIEW, upstream false다. fullJob Python canonical SHA는 형식검사 후 관측값으로 표시하며 JS JSON.stringify fullJob hash와 대조하지 않는다(1.0·지수·음수0 차이). 추출 metadata만 별도 canonical hash로 대조한다. schema가 허용하지만86이 차단하는 257..4096자 metadata도 안전한 BLOCKED를 표시하도록 metadata-only canonical은256문자 상한을 강요하지 않는다.

## 상태·안전한 표시

원 schema/날짜 형식, bbox 숫자·순서, metadata 비교를 별도 단계로 표시한다. 89 exact result·24 false flags·7개 typed numeric0·schema_files_read null·comparator_calls0/1·상태/이슈/단계 연계와86 내부 안전한 코드·hash·실제 입력 위치/count를 확인한다. 미계측 null을0으로 바꾸지 않는다. schema cold local 읽기가 있으므로 전체 I/O0으로 표현하지 않는다.

형식/bbox/model/workflow-ID/metadata 차단은 정상200 BLOCKED다.90의 schema 자원 실패는 고정503이며200 resource payload는 거부한다.400/413/503/401/403은 고정된 짧은 UI 설명을 제공하고 서버 원문 오류/URI/예외를 출력하지 않는다. MATCH는 caller metadata 선언 일치다. 과학적 AOI/output·기간순서·Agent capability/model·DAG·기관 ACL·원본 인증·완성Job pin·실행/학습 승인은 확인하지 않는다.

SVG는 기존 Icon 스타일을 쓰며 scoped CSS에서 header flex-start·본문 flex1/min-width0, hash 줄바꿈과 panel overflow를 처리한다. 모바일 CSS는 구현 상태이며 실제 모바일 확인을 뜻하지 않는다.

## 시험 근거

- 신규 `frontend/src/fullJobHandoffAdapter.test.mjs`: **14 PASS**, 3122.0076ms. raw decimal/exponent/negative0 원문·전체요청SHA·server관측hash·정확wrapper·24false/7typed0/null·phase·inner86·오류·stale·AST상 수동POST/독립details mount를 검사했다.
- 마지막 신규 시험은 실제 Python89 helper를 격리 subprocess로 호출해 match/id257/role257/refs65/없는node/schema/bbox/trace **8경우**를 JS view와 교차검산한다. 이8경우를 별도 신규시험 수에 더하지 않는다. 임시 합성 선언이며 운영 Job 생성/수집/학습을 하지 않는다.
- 전체 프론트 **127 PASS**, 5013.0695ms. 기존113개를 보존했다.
- 로그: `evidence/integration/full-job-handoff-ui-adapter-20261017.log`, `evidence/integration/full-job-handoff-ui-tests-20261017.log`, `evidence/integration/full-job-handoff-ui-build-20261017.log`.
- production build **PASS**, 87 modules,16.14초. 기존500kB chunk 경고가 남아 있다. 독립 **14 PASS**,4369.1739ms/exit0, 추가결함0. 로그는 `evidence/integration/full-job-handoff-ui-independent-20261017.log`다. 실제 브라우저·API/전체 backend·보존 증거는 Root가 같은 단위에 연결한다.

## 관련 자료

- [89 내부 helper](89_workflow_job_request_handoff.md)
- [인계서](00_next_session_handoff.md)
- [이해자료](../understanding/INDEX.md)

실제 JobPOST/Workflow 실행·QA/학습·수집/배포0이다. 이 UI 완료를 전체 프로젝트 완료로 보지 않는다.


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
