# 88 — Workflow 선택 노드 입력 전달 선언의 독립 수동 UI

## 2026-10-17 — 완성 Job 초안 수동 API·UI 연결(90/91)

89 내부검사를 독립 RFC `POST /v1/workflows/full-job-input-handoff`와 GeoQuery의 접이식 ‘완성 Job 초안 검토’ 패널에 연결했다. 원 Workflow JSON·callerpin·명시node·사용자fullJob JSON의 정확4키를 보존한다. Workflow는87정수규약, fullJob은별도strict decimal/지수·int53/finite·비영underflow0/overflow·숫자lexeme/UTF8/중복키/byte/깊이한도를 적용한다. 정상schema/metadata불일치200BLOCKED, 잘못된JSON400/예산413/schema자원실패·예상밖오염503을 구분하고 기존인증/no-store를 유지한다.

전체 RAWbody SHA로 응답을 연결하고 fullJob Pythoncanonical SHA는 서버의 초안관측값으로 표시한다. JS fullJob숫자 직렬화 hash와 대조하지 않는다. schema/날짜형식·bbox숫자순서·metadata대조를 분리하며24개승인false·7개자산/DB등I/O0·schema파일읽기미계측null을 확인한다. 기존plan/lineage/88과독립state/명시수동POST/편집·선택·route/back/세대무효화를 적용했다. 기존metadata입력과정수전용계약을fullJob입력으로바꾸지 않았다.

실제 로컬HTTP/브라우저에서 합성초안의정상·차단을확인했다. 이는운영Workflow의Job제출/실행이나과학/기관ACL/모델승인 검증이아니다. 기존입력초안은시연뒤복원했고운영Job생성·학습은없다. 원schema cold읽기와자산읽기0을구분하고기존공통date-time검사개선은별도대기다. 사용법·API/오류·UI검증·한계는 [API90](90_full_job_handoff_api.md)·[UI91](91_full_job_handoff_ui.md)를따른다.

## 2026-10-17 — 완성 Job 초안 schema·metadata 내부 연결(89)

신규 `workflow_job_request_handoff.compare_workflow_job_request_handoff`는 사용자 완성 Job 초안의 bounded JSON/finite·원schema·날짜형식·bbox 숫자/순서를 확인하고, agent/capability/{trace}/ordered input_refs만 추출하여86에1회 대조한다. optional workflow_run_id가 있으면 caller Workflow와 같아야 하며 필드를 생성하거나 채우지 않는다. sourceasset/DB/Registry/실제Job/executor를 호출하지 않는다. 다만 원schema cold load는 local schema 읽기가 있어 단위전체 I/O0로 표현하지 않고 schema_files_read는 미계측 null이다.

fullJob 전체 canonical SHA는 이번 caller 초안의 관측값이며 별도 fullJobpin 인자가 없어 출처/과거초안 일치를 인증하지 않는다. metadata SHA는 부분범위로 AOI/output/purpose 변경 시 metadata MATCH와 전체초안 SHA가 다를 수 있다. AOI 소수좌표를 허용하고87/88 integer-only parser/canonical은 재사용하지 않는다. 기존환경의 date-time checker 미등록 공백은89 전용 detached checker/evolve로 보완했으며 기존 cachedvalidator/class·원schema/API는 변경하지 않았다. 원schema 및 지원검사 통과도 실제 Agent/model/과학적 AOI/output·ACL·DAG·학습/실행 승인이 아니다.

이번89는 공개API/UI 비연결의 내부 기능이다. 기존87/88 응답과 화면은 fullJob 검증을 제공한다고 표시하지 않고 그대로 유지한다. 사용법·새지원subset·오류/자원경계·합성시험·다음화면연결한계는 [문서89](89_workflow_job_request_handoff.md)를 참조한다.

상태: **TESTED_SYNTHETIC**. 신규 화면 코드·adapter 시험 및 전체 frontend 회귀 완료. 실제5174 브라우저·로컬 HTTP로 합성 선언의 수동 MATCH/BLOCKED와 독립 상태/이동을 확인했고 마지막 검증 절에 기록했다. 실제 화면 적용 확인과 운영 Workflow 전달 검증은 별개다. 운영 Workflow/Job 생성·실행·학습 또는 전체 프로젝트 완료가 아니다.

## 문제와 화면 구성

기존 GeoQuery의 실행계획 검토 화면은 Workflow JSON 원문을 편집하고 계획·현재 계보를 읽는다. 이제 `frontend/src/WorkflowNodeHandoff.tsx`를 `GeoQuery.tsx`의 `kind === execution` 조건 안에 독립 child로 항상 mount한다. 부모 변경은 import와 이 mount뿐이다. 기존 계획·계보 결과나 요청 성공 여부에 따라 child를 생성하지 않는다.

새 카드의 이름은 **Workflow 노드 입력 전달 선언 검사**다. 사용자에게 다음 두 입력을 직접 받는다.

- **전달 검사 선택 노드 ID**: 위 Workflow 원문에 있는 node_id를 원문 그대로 입력한다. 자동 선택·trim·정규화하지 않는다.
- **제안 Job 입력 metadata JSON**: 사용자가 `agent_id`, `capability_id`, `execution_context:{trace_id}`, `input_refs`의 정확 네 키를 작성한다. 초기 값은 빈 문자열이다. Workflow를 읽어 제안을 자동 채우거나 성공 예제를 기본 승인 상태로 표시하지 않는다.

**선택 노드 입력 전달 선언 검사** 버튼의 명시 클릭만 신규 POST를 보낸다. 입력 편집·mount·계획 조회·계보 조회·뒤로 이동으로 자동 요청하지 않는다. 완성 Job·AOI·출력·선행 Result를 생성하는 기능이 아니다. 서버 HTTP200의 `MATCH`와 `BLOCKED`는 서로 다른 문구로 표시하고 null 계수를 0개 통과로 바꾸지 않는다. 안전한 원인 코드/대상/위치를 표시하며 raw ID·URI를 오류 응답으로 되돌려 보충하지 않는다.

## 요청 원문과 교차 언어 SHA 계약

[87 API 계약](87_workflow_node_handoff_api.md)의 정확 네 키 wrapper를 `agentApi`에 전달한다. `workflow_request_json`은 위 편집기의 `planJson` 원문, `proposed_job_metadata_json`은 새 textarea 원문이다. 공백·개행·JSON escape를 포함해 문자열을 보존한다. 반환 요약인 `plan.nodes`에서 Workflow를 재구성하지 않는다.

`workflowNodeHandoffAdapter.ts`의 strict parser는 중복 키(escape로 같은 키를 쓴 경우 포함), 소수·지수·NaN·Infinity, int32 범위 초과, 단독 surrogate·C0/C1 문자, 문자열 256 code point 초과·각 원문 UTF-8 512KiB·깊이 12 초과를 로컬 오류로 거부한다. 로컬에서 거부된 요청은 POST하지 않는다. 서버도 원문을 다시 strict 검사하므로 클라이언트 parser를 신뢰 경계로 삼지 않는다. 서버의 추가 object-key/atom 예산은 87을 따르며 HTTP413으로 표시한다. 숫자를 먼저 JSON.parse해서 1.0과 1을 같게 만드는 방식을 사용하지 않는다.

전체 Workflow pin은 Python86의 `json.dumps(sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':'))` UTF-8 SHA에 맞춘다. JavaScript 기본 UTF-16 key 정렬 대신 Unicode code point 정렬을 사용한다. 정렬된 JS 객체를 다시 stringify하면 숫자 모양 키가 재배열되므로 canonical 문자열을 직접 조립한다. 배열 순서는 보존한다. 공유 golden은 `evidence/integration/workflow-node-handoff-canonical-fixture-20261017.json`이며 한글·é·emoji·비BMP·U+2028를 포함한다. 별도 시험은 숫자 모양 키와 BMP/비BMP key 정렬도 검증한다.

`request_sha256`는 `agentApi`가 실제 보내는 `JSON.stringify(wrapper)` UTF-8 byte의 SHA와 일치해야 한다. 이는 Workflow canonical pin과 별개다. 선택 node ID의 canonical JSON SHA, 계산 가능한 선택 metadata SHA와 사용자 제안 SHA도 응답과 대조한다. 이들은 caller 선언의 동일성이며 신뢰 원본 인증·전자서명·운영 승인을 뜻하지 않는다.

## 응답과 오류 처리

adapter는 exact wrapper 다섯 키와 RFC extension/INTERNAL_REVIEW/upstream false/실제 요청 SHA를 검사한다. result의 exact 키·typed MATCH/BLOCKED·declarations_match 동치·20개 false·7개 정수 I/O0·nullable SHA/count/index의 단계별 일관성을 확인한다. wrapper/result의 추가 키, array를 status 문자열처럼 취급하는 강제 변환, 다른 요청·다른 node·다른 metadata digest를 거부한다.

허용 safe issue code/side 및 exact 네 키, 실제 node/input 범위, comparison 입력의 양쪽 최소 범위, 중복 issue와 최대 324건을 확인한다. Workflow 구조 오류의 HTTP200 BLOCKED와 null, node 미발견·선택 입력 없음·제안 metadata 오류의 단계별 null은 정상적으로 표시한다. 86 전체 의미 validator를 UI에 중복 구현하지 않는다. 서버의 순수 비교 결과를 요청과 엄격히 결합하는 표시 검증이다.

HTTP400/413/503과 공통 인증401/403은 고정된 한국어 메시지로 표시한다. API 원문 예외·응답 body를 오류 UI에 그대로 출력하지 않는다. 성공처럼 보이는 응답의 계약 검증이 실패하면 별도 오류로 닫으며 이전 성공을 재사용하지 않는다.

## 독립 상태와 stale 응답 방지

child는 busy/result/error/generation을 따로 가진다. 부모의 계획 조회 generation·계획 성공/실패·계보 상태와 연결하지 않는다. `planJson`, 명시 node ID, 제안 원문, 부모 `executionRevision`을 요청 identity에 포함한다. 편집·질의 유형 변경·실행 revision 변화·hashchange/popstate·unmount가 결과와 이전 요청 세대를 무효화한다. 비동기 SHA 계산 전후와 응답·오류·finally에서 generation/identity/route를 다시 확인한다. route가 바뀌었다 돌아오는 동안 결과가 잘못 남지 않도록 이벤트도 세대를 올린다.

**전달 검사 응답 표시 중단**은 화면의 응답 수신 표시만 폐기한다. 서버 threadpool 비교를 취소했다고 표시하지 않는다. 기존 계획/계보 버튼을 누른 성공·실패만으로 이 child의 결과를 초기화하지 않는다. 선택 node/proposal 입력은 사용자가 작성한 초안이며 실제 Job의 저장·생성 근거가 아니다.

## 범위·스타일

공통 SVG `Icon`의 network/compare를 사용하고 `workflow-node-handoff.css`는 `.workflow-handoff-card` 안에만 적용한다. header는 위쪽 정렬, 입력/집계 SHA는 줄바꿈, 넓은 원인 표는 카드 안 스크롤로 처리한다. 작은 화면의 2열 집계·버튼 배치는 CSS 구현 상태이며 실제 모바일 검증은 Root가 별도 수행하지 않은 이상 주장하지 않는다.

MATCH도 완성 Job·AOI·requested outputs·선행 Result·전체 DAG·현재 Registry/파일 무결성·전이 계보·executor binding·TOCTOU·출처 인증·기관 ACL·과학·학습·실행 승인을 뜻하지 않는다. 순수 비교의 I/O0는 신규 route 범위이며 기존 계획/계보 진단이 I/O0라는 뜻이 아니다. RFC 내부 검토가 upstream OpenAPI에 승인된 기능을 의미하지 않는다.

## 시험과 재현

```powershell
cd frontend
node --experimental-strip-types --test src/workflowNodeHandoffAdapter.test.mjs
node --experimental-strip-types --test src/*.test.mjs
npm run build
```

신규 **13 PASS / 1.400초**, 전체 frontend **113 PASS / 2.260초**. 로그는 `evidence/integration/workflow-node-handoff-ui-adapter-20261017.log`와 `workflow-node-handoff-ui-tests-20261017.log`다. production build 결과는 `workflow-node-handoff-ui-build-20261017.log`에 기록한다. 원문/wholebodySHA·공유 Python golden·정렬·duplicate/숫자/Unicode/byte/depth·typed status·20false/7typed0·digest/count/indices 변조·각 정상 BLOCKED 단계·stale guard·manual POST의 AST 소유 함수·부모 독립 mount를 검증했다.

이는 합성 선언과 코드/adapter 시험이다. 실제 브라우저 성공/차단·기존 계획/계보 독립·편집/뒤로 이동·console/overflow·스크린샷은 Root가 완료 코드와 실행 서버를 대상으로 확인한 후 증거 파일을 추가한다. UI 담당은 API/오류/상태/fixture/시험을 Root와 독립 reviewer에게 인계하고, 이해 에이전트가 검증된 코드·로그·실제/합성 구분과 한계로 쉬운 설명·발표 대본·FAQ·INDEX·변경 이력을 함께 갱신한다.


## Root 실제 API·브라우저 검증 근거

`evidence/integration/workflow-node-handoff-api-live-api-20261017.json`: 최종 새endpoint11POST(Unicode합성MATCH·role부재드리프트BLOCKED·잘못된callerpinBLOCKED·빈선택BLOCKED·outer/inner중복/UTF8/nonfinite400·depth/body413), 기존plan/lineage2POST는 시작기준선2POST와 응답동일. 최초checker의본문공백/compact차이로derived requestSHA가달랐던 시도는별도initial-attempt JSON에보존했고 원baseline직렬화로수정후PASS했다. application변경은없으며 반복검증을새시험건수로합산하지않는다. catalog14행/기존Job본문동일·JobPOST0이다.

`evidence/integration/workflow-node-handoff-api-live-ui-20261017.json` 및 `workflow-node-handoff-ui-desktop-20261017.jpg`: 실제5174/#/view/15에서 합성선언수동MATCH·role변조BLOCKED·없는node/null·중복JSON로컬거부, 기존계획/계보완료후결과유지, node/proposal/원Workflow편집clear·뒤로/앞으로이동폐기를확인했다. 1449×1087 문서/패널가로넘침0·console오류[]·SVG/제목간격보완반영. 테스트후기존Workflow초안을원문그대로복원하고합성node/proposal/결과는지웠다. 스크린샷은복원전합성시연이다.

실제UI모바일·강제지연/취소경합·HTTP503/인증오류·5173적용은미검증이다. 운영Workflow/Job생성·실행·새QA/학습은0. 새비교의I/O0와기존plan/lineage의Registry읽기를혼동하지않는다. 최종전체회귀/보존/문서감사는Root완료절을따른다.


## 최종 CSS 보완·독립 검증

실제 화면에서 SVG와 제목의 과도한 간격을 확인해 신규 scoped header에 justify-content:flex-start, header>div flex:1/min-width:0만 보완했다. 기능·공용CSS 변경은 없다. 최종 신규13 PASS/1400.1225ms·전체113 PASS/2260.0008ms·production build19.17초 PASS. 기존500kB chunk 경고만 있다. 독립13 PASS/2073.8207ms와 별도 실제86core→JSview 합성14경우 교차검산0실패는 independent 로그를 따른다. 교차검산/반복 실행을 신규 시험 건수에 합산하지 않는다. Root의 최종 screenshot은 CSS 보완 후이며 정렬/overflow도 재확인했다.


## 19:55 KST — Workflow 입력 전달의 수동 API·UI 연결 검증 완료 (87/88)

- **workflow_handoff / API:** 새 POST /v1/workflows/node-input-handoff와 main배선 완료. 관련15 PASS/0.842초·독립15 PASS/1.250초. 원JSON문자열2개/정확4키·strictUTF8/중복/nonfinite/float/int32·body1MiB/원문별512KiB·깊이/atom 한도·400/413/503 고정오류·no-store/기존인증·86 comparator1회를 검증했다. safe wrapper wholebodySHA·실제list index/20false7IO0·core86불변을 유지했다.
- **workflow_handoff_ui / 화면:** GeoQuery 실행계획 검토에 독립 수동 child를 적용했다. 신규13 PASS/1400.1225ms·전체113 PASS/2260.0008ms·독립13 PASS/2073.8207ms·production84modules/build19.17초 PASS(기존chunk경고). Python86→JS14합성경우 교차검산0실패이며 신규시험 수에 합산하지 않는다. status array 정규화·실제입력index 경계를 보완했고 실제 화면의 SVG/제목 간격을 scopedCSS로 수정·재검증했다.
- **Root 실제API/UI:** 최종HTTP 새11POST+기존진단2POST(기준선2별도) 통과. 최초증거checker의본문직렬화차이로derivedhash가 달랐던 시도는 별도기록 후 exactbaseline본문으로 수정해 PASS했다(application변경X). 실제5174/#/view/15 합성선언의 수동MATCH·role드리프트BLOCKED·없는node/null·중복JSONlocal거부·기존plan/완료lineage와결과독립·편집/뒤로/앞으로이동clear를 확인했다. 1449×1087 문서/패널overflow0·console[]·최종JPG저장. 시험뒤기존Workflow초안은원문복원하고합성node/proposal/결과를지웠다. 모바일/강제취소지연경합/HTTP503·인증의실브라우저/5173적용은미검증이다.
- **전체·보존:** backend897개/896 PASS/기존Windows symlink1 SKIP/382.270초/exit0. 보호141·불변core51 변경0·catalog14/기존Job본문같음. 기존tracked code변경은허용main.py+GeoQuery.tsx뿐, core86/기존Workflow/계보/84~85응답보존. 원본·원장/lock·예약136314880B·분할·모델·후보1095/차단4·학습BLOCKED 유지. 실제JobPOST/역채움/Workflow실행·새QA/학습·수집/배포0.
- **문서·이해자료:** 신규87/88·관련07/41/86·운영원장/소유권/인계서 수정. understanding_agent에완료코드/관련·독립·전체/실제HTTPUI·보존근거를전달하여쉬운설명·이론·코드데이터·발표대본·FAQ·INDEX/변경이력갱신을같은단위로진행한다. 최종문서감사/rawSHA snapshot은 `evidence/integration/workflow-node-handoff-api-closeout-20261017.json`에기록한다.
- **범위·다음:** 실제HTTP/UI이지만새기능의선언은합성(TESTED_SYNTHETIC)이며운영Workflow→Job전달검증이아니다. callerpin은신뢰원본인증이아니고MATCH는완성Job/AOI/output/선행Result/DAG/기관ACL/과학/실행승인이아니다. 신규비교I/O0와기존plan/lineage Registry읽기를구분한다. 다음은사용자완성Job초안원schema검증→metadata추출→86대조의내부작업(PLANNED/미착수)이다. 전체프로젝트미완료·지속개발대기열을유지하며 geoai-2 ACTIVE10분예약과실제worker실행을구분한다.

근거: `evidence/integration/workflow-node-handoff-api-live-integrity-20261017.json`, `evidence/integration/workflow-node-handoff-api-live-ui-20261017.json`, `evidence/integration/workflow-node-handoff-api-live-api-20261017.json`.
