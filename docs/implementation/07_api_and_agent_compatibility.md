# GMAIS v0.2 API·Agent 호환성 구현 기록

## 2026-10-17 — 기존 Draft 등록 API·화면의 선택적 버전 전달 (98/99)

기존 `POST /api/models/register-experiment`는 요청에 `model_version` 키가 있을 때만 원문 값을 keyword 인자로 전달한다. 키가 없으면 기존 `register_experiment(store, report_path)` 두 인자 호출을 유지한다. 명시 null은 생략으로 바꾸지 않으며 97의 기존 검사 순서에 따라 거부된다. 기존 인증·등록 lock·성공 201·오류 422·알려지지 않은 추가 필드를 무시하는 정책을 보존한다. 원 schema, 훈련 producer, 모델 승인·배포 정책은 변경하지 않았다.

ModelReview의 기존 등록 details 안에 기본 off 선택란과 빈 모델 버전 입력을 추가했다. 선택하지 않으면 기존 `{report_path}` 본문 그대로이며, 선택하면 입력 원문을 추가한다. 자동 POST·trim·dataset_version 대체·레거시 역채움은 없다. 등록 중 입력과 모델 선택을 비활성화하고 이동·unmount 후 늦은 선택/오류 표시를 폐기한다. 서버 성공 뒤 목록 refresh는 수행하므로 화면 폐기를 서버 등록 취소로 해석하지 않는다. 201 뒤 refresh 실패는 등록 실패와 구별하고 목록 확인을 안내한다.

API 관련 48 PASS·독립 11 PASS, UI 관련 16 PASS·독립 16 PASS·전체 153 PASS·89 modules production build를 확인했다. API 독립 시험은 원 main의 인증/app/등록 route AST를 격리 앱과 TempStore에서 실행했으며 운영 main 초기화·운영 성공 등록의 증거가 아니다. 실제 API는 없는 report 경로 4회가 422였고 catalog 14행이 같았다. [실제 API 근거](../../evidence/integration/model-version-api-live-api-20261017.json)를 따른다. 브라우저의 오류 입력·뒤로가기와 layout 보완은 Root의 최종 근거를 기다리며 이 기록으로 화면 검증 완료를 주장하지 않는다.

명시 선언은 caller metadata이며 기관 권위·원본 인증·과학/실행 승인이 아니다. 생략 raw 필드의 같은 모양만으로 명시 등록의 진정성을 판정하지 않는다. [API 계약98](98_model_version_registration_api.md), [UI 계약99](99_model_version_registration_ui.md), [내부 선언97](97_model_version_declaration.md)을 함께 참조한다. 아래 97의 API/UI 미연결 설명은 당시 내부 단위의 범위다.

## 2026-10-17 — 향후 내부 등록의 명시 모델 버전 선언 (97)

`register_experiment(store, report_path, *, model_version=...)`에서 호출자가 명시한 미래 버전을 선택적으로 보존한다. 옵션 생략은 기존 응답·레코드 바이트와 raw training의 임의 필드 복사를 그대로 유지한다. 명시할 때만 96 문자 검증과 보고서 필드 충돌 검사를 거쳐 모델 레코드의 exact5 `model_version_declaration`에 버전 원문·기존 checkpoint SHA·훈련 report SHA를 연결한다. 잘못된 명시 값은 기존 검사가 끝난 뒤 첫 Store.put 전에 거부한다.

기존 main/API·훈련 producer·UI는 이 옵션을 전달하지 않는다. 따라서 현재 공개 요청·화면의 동작은 그대로다. 명시 선언은 caller metadata이며 기관 권위·원본 인증·과학/모델/실행 승인이 아니다. 같은 모양의 raw 필드도 생략 경로에서 복사될 수 있으므로 키/source만으로 명시 호출이 생성했다고 인증하지 않는다. 기존 model_id 또는 dataset_id 중복 거부·Draft·독립평가 false·쓰기 순서를 유지한다.

기존 기록의 dataset_version을 모델 버전으로 대체하거나 역채움하지 않는다. 두 번 쓰기의 비트랜잭션·동시경쟁/전역 immutable 한계도 해결했다고 표현하지 않는다. 사용법·충돌 규칙·합성 임시 Store 시험·한계는 [문서97](97_model_version_declaration.md)를 따른다.

## 2026-10-17 — model_ref 고정 문자 선언 검사 통일 (96)

`model_reference_contract.model_reference_issue()`를 GMAIS 제출 검사와 89 초안 검사에서 공유한다. id/version 및 제공한 role은 기존 89와 같은 1..256자 지원 범위로 확인하며, 공백만 있는 문자열·제어문자·단독 surrogate와 latest/current 버전 별칭을 거부한다. 정상 고정 문자열을 trim하거나 바꾸지는 않는다. 기존에 지원하던 패딩된 고정 v1과 256자 경계도 유지한다.

GMAIS는 기존 schema·SHA 검사를 먼저 하고, 새 문자 거부를 Store 접근 전 기존 `400 INVALID_REQUEST` 형식으로 반환한다. 이는 공통 제출 API의 허용 입력을 좁히는 변경이다. 89의 기존 모델 차단 코드와 순서, RFC1/RFC2 결과, 24개 false 플래그는 보존한다. 원 schema에서 SHA는 양쪽 모두 필수이며 helper가 SHA/URI/키 정책을 대신하거나 완화하지 않는다. model_ref 부재는 그대로이고 명시 null은 기존 schema 오류다.

이 검사는 문자 선언의 지원 범위만 확인한다. 실제 등록 모델·checkpoint·권위 있는 model version·기관 ACL·과학·실행 승인을 조회하지 않으며 `model_verified=false`를 유지한다. 기존 UI 오류 표시로 처리할 수 있어 직접 프론트 수정·build·브라우저 재시험은 없다. 지원 범위, 새 오류와 격리시험 근거는 [문서96](96_model_reference_contract.md)를 참조한다.

## 2026-10-17 — 선택형 완성 Job 로컬 등록관계 API·UI(94/95)

기존 수동 `/v1/workflows/full-job-input-handoff`에서 `contract_version`이 없는 정확4키 요청은 기존RFC1로유지한다. 사용자가기존details의기본off ‘로컬 등록관계도 확인 (RFC2)’를선택하고수동버튼을누를때만정확5키/정수2의RFC2를요청한다. RFC2는89의원결과를그대로보존하고innerMATCH때만Job제출과같은로컬staticmanifest firstmatch+93membership관계를관측한다. innerBLOCKED면등록관계는NOT_RUN이다.

등록됨도실제capability지원·모델/readiness·기관ACL·과학/실행승인이아니며inner24false/7IO0/schema읽기null과outer3false를유지한다. 생산·안전재검증의인메모리manifest관측2회와네트워크/Store0을구분하고관측변동·오염은503으로닫는다. UI는전체요청SHA와버전포함identity/편집·route/back세대폐기를적용하고outerBLOCKED와innermetadataMATCH를분리해표시한다.

실제8002진단HTTP15경우와5174브라우저합성초안으로정상·차단·오류·선택전환/뒤로가기를확인했고원Workflow초안을복원했다. 이는운영Job제출/Workflow실행승인이아니다. 요청/응답·지원범위·원문한도·시험/화면근거는 [API94](94_full_job_registration_api.md)·[UI95](95_full_job_registration_ui.md)를참조한다. 기존89/90/91 및93의정의는각단위이력으로보존한다.

## 2026-10-17 — Agent·capability 등록관계 공통 검사(93)

`agent_capability_contract.agent_capability_issue(agent, capability_id)`는 이미 선택된 내부 manifest의 부재/등록capability membership만 검사한다. Job 제출과 Workflow 계획의 중복검사를재사용하되 Job의firstmatch·Workflow의lastduplicate 선택·HTTP코드/문구·readiness·Store접근순서·멱등동작을그대로둔다. 원문모듈 SHA핀과격리임시Store를사용해 기존전체응답/헤더·레코드·접근순서동등성을검증한다.

이함수는Registry를읽거나 모델/기관ACL/과학·실행을승인하지않는다. trusted내부manifest 전제가있으며새validation/normalization정책을추가하지않아잘못된manifest의기존예외도보존한다. 기존89/90/91 fullJob검토에는연결하지않고24false·agent_capability_verified=false·날짜검사92를보존한다. 공개API/화면계약변경이없어직접frontend/build/브라우저재시험은없으며운영JobPOST는하지않았다. 계약·시험·한계는 [문서93](93_agent_capability_contract.md)를참조한다.

## 2026-10-17 — 공통 날짜 형식 검사 환경 일관성 보완(92)

`schema_formats.create_format_checker()`를 공통 Job/Workflow cached validator 생성부와89의 `_draft_format_checker()` 호환 wrapper가 재사용한다. 선택 date-time dependency가 없는 현재환경에서도 새로 생성되는 공통Job검사기가 날짜·시각·시간대의 지원형식을 확인한다. 전역 FormatChecker registry와 이미 만들어진 checker 객체를 후행변조하지 않고 vendored 원schema를 보존한다. 89/90의 날짜오류200BLOCKED와 기존제출의 INVALID_REQUEST400 형태를 유지하며, 공통제출은 잘못된날짜를 Store 접근전에 거부한다.

지원범위는 기존89와 같은 T/t·Z/z·소수초·실제달력·offsetHH00..23/MM00..59인 zoned부분집합이다. leap second와연도0000은지원하지 않으며 기간순서·시간대변환·과학/기관ACL·실행승인 검사는추가하지 않는다. UI담당 읽기검토 결과 기존오류화면계약을유지해 직접프론트변경·build·브라우저재시험은없다. 자세한계약·시험근거·운영적용한계는 [문서92](92_common_datetime_validation.md)를참조한다. 이전절의 공통검사개선대기/미수정은 각단위시점의 이력이며 현재92의source 변경범위와구분한다. non-reload 기존API프로세스의 새코드적용은별도미검증이고, 격리시험을운영Job제출성공으로표현하지 않는다.

## 2026-10-17 — 완성 Job 초안 수동 API·UI 연결(90/91)

89 내부검사를 독립 RFC `POST /v1/workflows/full-job-input-handoff`와 GeoQuery의 접이식 ‘완성 Job 초안 검토’ 패널에 연결했다. 원 Workflow JSON·callerpin·명시node·사용자fullJob JSON의 정확4키를 보존한다. Workflow는87정수규약, fullJob은별도strict decimal/지수·int53/finite·비영underflow0/overflow·숫자lexeme/UTF8/중복키/byte/깊이한도를 적용한다. 정상schema/metadata불일치200BLOCKED, 잘못된JSON400/예산413/schema자원실패·예상밖오염503을 구분하고 기존인증/no-store를 유지한다.

전체 RAWbody SHA로 응답을 연결하고 fullJob Pythoncanonical SHA는 서버의 초안관측값으로 표시한다. JS fullJob숫자 직렬화 hash와 대조하지 않는다. schema/날짜형식·bbox숫자순서·metadata대조를 분리하며24개승인false·7개자산/DB등I/O0·schema파일읽기미계측null을 확인한다. 기존plan/lineage/88과독립state/명시수동POST/편집·선택·route/back/세대무효화를 적용했다. 기존metadata입력과정수전용계약을fullJob입력으로바꾸지 않았다.

실제 로컬HTTP/브라우저에서 합성초안의정상·차단을확인했다. 이는운영Workflow의Job제출/실행이나과학/기관ACL/모델승인 검증이아니다. 기존입력초안은시연뒤복원했고운영Job생성·학습은없다. 원schema cold읽기와자산읽기0을구분하고기존공통date-time검사개선은별도대기다. 사용법·API/오류·UI검증·한계는 [API90](90_full_job_handoff_api.md)·[UI91](91_full_job_handoff_ui.md)를따른다.

## 2026-10-17 — 완성 Job 초안 schema·metadata 내부 연결(89)

신규 `workflow_job_request_handoff.compare_workflow_job_request_handoff`는 사용자 완성 Job 초안의 bounded JSON/finite·원schema·날짜형식·bbox 숫자/순서를 확인하고, agent/capability/{trace}/ordered input_refs만 추출하여86에1회 대조한다. optional workflow_run_id가 있으면 caller Workflow와 같아야 하며 필드를 생성하거나 채우지 않는다. sourceasset/DB/Registry/실제Job/executor를 호출하지 않는다. 다만 원schema cold load는 local schema 읽기가 있어 단위전체 I/O0로 표현하지 않고 schema_files_read는 미계측 null이다.

fullJob 전체 canonical SHA는 이번 caller 초안의 관측값이며 별도 fullJobpin 인자가 없어 출처/과거초안 일치를 인증하지 않는다. metadata SHA는 부분범위로 AOI/output/purpose 변경 시 metadata MATCH와 전체초안 SHA가 다를 수 있다. AOI 소수좌표를 허용하고87/88 integer-only parser/canonical은 재사용하지 않는다. 기존환경의 date-time checker 미등록 공백은89 전용 detached checker/evolve로 보완했으며 기존 cachedvalidator/class·원schema/API는 변경하지 않았다. 원schema 및 지원검사 통과도 실제 Agent/model/과학적 AOI/output·ACL·DAG·학습/실행 승인이 아니다.

이번89는 공개API/UI 비연결의 내부 기능이다. 기존87/88 응답과 화면은 fullJob 검증을 제공한다고 표시하지 않고 그대로 유지한다. 사용법·새지원subset·오류/자원경계·합성시험·다음화면연결한계는 [문서89](89_workflow_job_request_handoff.md)를 참조한다.

## 2026-10-17 — Workflow 입력 전달 수동 API·UI 연결 (87/88)

순수86을 독립 내부 RFC `POST /v1/workflows/node-input-handoff`와 GeoQuery 실행계획 검토의 ‘Workflow 노드 입력 전달 선언 검사’에 연결했다. API는 원 Workflow/제안metadata JSON 문자열2개·caller canonical pin·명시 node_id의 정확4키를 받는다. 엄격UTF8·중복키/nonfinite/float·int32·원문별512KiB/전체1MiB·깊이/atom 한도 검사 후86을1회 호출한다. wrapper 전체 수신 rawbody SHA와 내부 canonical pin은 범위가 다르다. 고정400/413/503·no-store/기존인증을 유지하고 raw본문/URI/ID/예외를 응답하지 않는다.

UI는 원 planJson을 보존하며 node/제안metadata를 직접 입력하고 버튼을 눌러야만 검사한다. 기존 계획·현재 계보와 별도 상태이며 편집/node/proposal/revision/route/back/unmount가 이전 응답을 폐기한다. 전체요청 SHA·canonical pin·안전형식/indices/count/20false7IO0를 검증하고, Python/JS Unicode canonical fixture로 프로토콜을 대조했다. 기존 반환 plan.nodes 요약에서 원문을 재구성하지 않는다.

실제 로컬 HTTP와 브라우저에서 합성 caller선언의 MATCH/변조BLOCKED·미확인계수·원문검사·기존조회독립/뒤로가기를 확인했다. 이는 운영 Workflow/Job 전달의 검증이 아니다. MATCH는 완성Job/AOI/output/선행Result/DAG/원본인증/기관ACL/과학/학습/실제executor 승인을 부여하지 않는다. 신규 비교의 I/O0와 기존 plan/lineage의 Registry진단은 별도 범위다. 사용법·계약·시험/한계는 [API87](87_workflow_node_handoff_api.md)·[UI88](88_workflow_node_handoff_ui.md)를 따른다. 실제 Job 생성·실행·capture역채움은 없다.

## 2026-10-17 — 선택 노드와 제안 Job의 입력 전달 계약(86)

신규 `backend/app/workflow_node_input_handoff.py:compare_workflow_node_input_handoff`는 caller-pinned 전체 Workflow request와 선택 node_id를 제안 Job의 제한된 metadata와 순수 대조한다. agent_id·capability_id·execution_context.trace_id 및 ordered input_refs의 id/version/sha256·role/URI의 부재와 값을 비교한다. pin에는 선택외 node·policy·dependency도 포함되지만 SHA 일치는 신뢰한 원본 인증이 아니다.

이 함수는 전체 Job 생성기/검증기가 아니다. 기존 Workflow 계획·DAG 검사·현재 Registry/파일 진단·79~85의 기존 Job 검증을 호출하거나 대신하지 않는다. 선택외 빈입력은 보존하고 선택node 빈입력만 차단한다. 전체 DAG cycle을 검사하지 않아 선언이 같으면 cycle 포함 요청도 MATCH일 수 있으며 dag_validated=false다. AOI·requested_outputs·선행 Result를 추정하지 않고 Job/Result·실제 executor/학습을 시작하지 않는다. 공개 API/UI 연결은 없고 기존 응답/화면을 유지한다. 세부 지원subset·한도·순수함수 사용법·시험/한계는 [문서86](86_workflow_node_input_handoff.md)에 기록한다.

## 2026-10-17 현재 직접 입력 수동 preflight API·UI companion (84/85)

`GET /v1/jobs/{job_id}/input-preflight`는83의 저장 근거·현재 직접 입력 integrity/quality/PUBLIC metadata·pin 대조 세 축을 수동 조회하는 내부 API다. 기존 `execution-input-binding` 저장 기록 조회와 Job Status/input-resolution 응답은 바꾸지 않는다. 83의 safe payload를 그대로 반환하고 개별 ID·URI·manifest pin·파일 경로·원문 예외를 노출하지 않는다.

worker 내부에서 단일 검사 semaphore를 획득하고 실제 작업 종료 시 해제한다. 요청 취소나 화면 표시 중단이 서버 파일 검사 취소를 뜻하지 않는다. 기존 인증을 상속하고 no-store를 적용한다. 잘못된 literal400, 없는 Job404, 중복 검사429(PREFLIGHT_BUSY/Retry-After1/retryable=true), 자원·잘못된 내부 응답503은 고정 안전 오류다. 동시 검사 수·refs/문자 상한은 전체 파일 byte/time/RAM 강제 상한과 다르다.

반환 계약은 타입·배열/코드 한도·Job literal SHA·15false·inner81·3축 상태를 교차검사한다. integrity 수는 실패 입력 index의 합집합, quality 관측 수는 metadata 미관측 실패 index의 합집합과 대조하며 quality passed는 관측 수·차단 코드와 양방향으로 일치해야 한다. 현재 capture가 RECORDED이면 모든 직접 입력의 integrity와 quality/access 관측이 존재해야 한다. 모순된 응답은 정상 판정으로 내보내지 않는다.

관련/독립 API13 PASS(3.779초/3.747초). 실제 API8002에서 legacy2 UNKNOWN/current NOT_RUN, missing404·긴/control literal400/no-store와 기존79/status/input-resolution6응답의 변경 전 동등성을 확인했다. 이번11GET과 이전 baseline6GET은 구별하며 catalog14행/Job 본문은 불변이다. MATCH·품질BLOCKED·취소중busy429/503은 합성 시험 범위이고 실제 executor·운영 Job POST·역채움·수집/QA학습은 없다. 근거: `evidence/integration/current-input-preflight-live-api-20261017.json`.

API 정확 계약·시험은 [문서84](84_current_input_preflight_api.md), 기존 카드에 독립 수동 버튼과 결과를 연결하는 UI의 최종 시험·실제 브라우저 근거는 [문서85](85_current_input_preflight_ui.md)를 따른다. 이번 조회의 MATCH는 입력 비교 관측일 뿐 실행·과학·기관 ACL·학습·배포/TOCTOU 승인이 아니다.

## 2026-10-17 저장 제출 binding 조회 companion (79/80)

`GET /v1/jobs/{job_id}/execution-input-binding`은 저장 Job 1건에서 제출 당시 별도 capture를 안전하게 투영하는 내부 RFC다. 기존 Job Status·input-resolution·현재 계보 API와 구별한다. 현재 Registry·파일·실행자의 입력을 재검사하거나 과거 Job에 capture를 역채우지 않는다. 응답은 RECORDED/UNAVAILABLE/LEGACY/INVALID와 request_job_sha256·안전한 입력/핀 계수·전체 binding 집계 SHA만 제공하고 개별 ID·역할·manifest pin·URI/경로·원문/예외를 반환하지 않는다. 12개 승인 및 현재파일 재검증/실행자 대조는 모두 false다.

한도·타입·Job/Agent/Trace 및 요청 참조 순서/역할 presence·canonical digest를 대조한다. 손상된 Job은 capture 부재보다 우선 INVALID이며, 미기록 null을 0개로 바꾸지 않는다. 단일 store.get을 threadpool에서 수행하고 no-store·기존 인증을 상속한다. 고정 404 JOB_NOT_FOUND / 503 RESOURCE_UNAVAILABLE 오류는 비재시도 선언이며 내부 예외를 노출하지 않는다.

실제 API8002의 기존 legacy Job2건은 LEGACY, 원상태 응답과 동일하고 catalog14행 전후 SHA 불변이다. 추가 없는 Job404 및 257자 요청 INVALID를 포함8GET만 수행했으며 실제 새 Job POST/소급 capture/실행0이다. 근거: `evidence/integration/stored-binding-capture-live-api-20261017.json`. RECORDED 생성은 합성시험 범위이고 운영 환경 관측으로 표현하지 않는다. 수동 UI·실제 브라우저/최종 회귀 검증 결과는 [문서79](79_stored_binding_capture_api.md)·[문서80](80_stored_binding_capture_ui.md)에 기록한다. upstream 확정 표준/학습 준비/과학·기관 권한 승인이 아니다.

## 2026-10-17 제출 binding capture의 내부 저장

기존Job제출분기의입력점검과같은pass에서얻은선택manifestpin을새Job의별도versioned execution_input_binding_capture에저장한다. HTTP오류/JobStatus/input_resolution/upstream schema는그대로이고공개응답에새필드를추가하지않는다. 과거Job/동일멱등replay는재조회·capture소급보강하지않는다. 변경전후3TempStore사례의전체응답/원저장Job(capture제외)동등·resolve각1/put2를확인했다. 운영POST는하지않고실제기존2legacyJob/status·input-resolution조회4건호환·catalog14불변만확인했다. 새capture생성은합성시험범위다.

기록은실행·과학·기관ACL승인이아니며실제executor전달/TOCTOU보호도제공하지않는다. 기존Registry/asset검사는수행되며additional_*0은capture추가작업만뜻한다. 정확계약/한계/시험은 [문서78](78_submission_binding_capture.md),후속전달선언대조는 [문서77](77_execution_input_binding.md)를따른다. 조회API/UI companion 구현과 검증 근거는 상단 79/80 절을 따른다.


## 2026-10-17 원본·후보 저장 QA 비교 진단 (74/75)

`POST /v1/diagnostics/candidate-readiness-comparison`은 원본 보고서, 후보 QA 보고서, QA 완료확인서, 복사확인서의 SHA-256 네 개만 받는 내부 읽기 진단이다. 경로나 최신 자료 자동 선택을 받지 않는다. 2048바이트 요청, 보고서 각16MiB/확인서 각64KiB·깊이32, 전후 고정 핀 대조를 적용한다. 원본·후보 manifest 및 래스터를 열거나 QA/Registry/학습을 실행하지 않는다. 기존 main 인증을 상속하고 동시 작업1개와 no-store를 적용한다.

응답은 `BLOCKED` / `PINNED_REPORT_COMPARISON_ONLY`다. 분할별 적격 패치·차단 코드 빈도·나지 클래스7 근거를 비교하고 모든 실행·과학·등록·재개·정산 승인 플래그를 false로 유지한다. 원본 물리 장면 수는 미저장 null이며, 복사확인서 행 수 선언과 후보 보고서의 QA 캡처 장면 수를 별도 범위로 반환한다. 출처 공유 차단 항목의 부재로 완전한 누출 해소나 독립성을 승인하지 않는다.

오류는 400 INVALID_REQUEST / 409 PINNED_INPUT_CONFLICT / 413 REQUEST_TOO_LARGE / 429 DIAGNOSTIC_BUSY / 503 RESOURCE_UNAVAILABLE이며 내부 경로·보고서 원문을 노출하지 않는다. 구현·시험은 [문서74](74_candidate_qa_comparison_api.md), LCLUC 근거 탭의 명시 버튼 UI·입력 및 이동 시 결과 무효화는 [문서75](75_candidate_qa_comparison_ui.md)를 따른다. upstream 컨소시엄 확정 규격으로 표현하지 않는다. 실제 HTTP200/409/400/413 및 브라우저 수동 조회·안전 복귀를 확인했으며 근거와 한계는 문서74/75에 기록했다.


## 2026-10-17 Workflow 현재 전이 계보 companion RFC

`POST /v1/workflows/lineage-validation`는 원문 Workflow Plan schema·DAG를 먼저 확인한 뒤 현재 고정 입력 계보를 검사하는 별도 내부 확장이다. `greenblue.workflow-lineage-validation.rfc1`/INTERNAL_REVIEW, `CURRENT_WORKFLOW_TRANSITIVE_LINEAGE_PLAN_ONLY` 범위를 명시하며 기존 `/v1/workflows/plan` 응답과 정책 진단을 대체하지 않는다. 계보가 모두 일치해도 modePLAN_ONLY/statusBLOCKED/execution_startedfalse/can_executefalse이며 실행·기관 권한·과학 승인은 부여하지 않는다.

기본노드128·전체refs64/uniqueroot32·depth32/root64/총nodechecks256 한도를 둔다. 동일고정참조의진단을노드간공유하고,같은ID/version의상충SHA는워크플로전체에서검사전차단한다. 다른root의같은조상을다시검사하면전체비용에재차감한다. 빈입력·미검사binding·한도부분검사를통과로보지않는다. request_sha256는canonicalJSON이아닌 **실제수신HTTP본문bytes의SHA256** 이며 원문본문·URI/role/params를반환하지않는다. UI가실제전송할JSON.stringify본문과대조하고세대검사로늦은응답을제외한다.

형식·DAG·NaN/Infinity 등비표준JSON은고정400 INVALID_REQUEST,예상밖자원오류는503 RESOURCE_UNAVAILABLE이다. 유효진단/검사한도보고는200이며no-store/threadpool/기존main인증경계를유지한다. Job/Result/Trace/Workflow실행기록을만들지않으며 Job계보공통검사helper추출의기존응답회귀도검증한다. 사용법·한계·시험은 [문서40](40_workflow_lineage_validation.md), 명시UI와기존계획응답경합보완은 [문서41](41_workflow_lineage_ui.md)를따른다. upstream원문OpenAPI/Schema는변경하지않았다.

## 2026-10-17 Job 현재 전이 계보 companion RFC

`GET /v1/jobs/{job_id}/lineage-validation`는 저장 Job/request/Agent/Trace 신원을 대조하고 요청 당시의 고정 입력 참조로 **지금의 로컬 전이 계보**를 읽기 검사한다. `greenblue.job-lineage-validation.rfc1`/INTERNAL_REVIEW, `CURRENT_TRANSITIVE_LINEAGE_NOT_SUBMISSION_SNAPSHOT` 범위이며 원문 Job Status와 제출 snapshot 응답은 바꾸지 않는다. 저장 snapshot이 없는 legacy라도 request가 온전하면 현재검사는 가능하며, 과거 제출 검증을 복원했다고 표현하지 않는다.

refs64/고유root32 preflight 상한, 기본깊이32·root당64nodes·총256node 검사비용 한도를 사용한다. 다른root에서 공유부모를 다시검사하면 재차감하며 같은 고정root의호출내cache는 재차감하지 않는다. 미검사binding은checkedfalse/diagnostic_index:null로 남고 일부검사만으로 전체성공을 표시하지 않는다. URI/role/manifest/snapshot원문·내부예외는 반환하지 않는다. 현재진단도 실행·기관권한·과학승인false다. 유효진단200 BLOCKED/INTEGRITY_VERIFIED, 누락Job404 JOB_NOT_FOUND, 예상밖자원오류503 RESOURCE_UNAVAILABLE, no-store/threadpool/기존main인증상속을 따른다.

API·한계·시험은 [문서38](38_job_lineage_validation.md), 명시클릭 UI·요청경합·저장진단과의 구분은 [문서39](39_job_lineage_ui.md)를 따른다. 이경로를upstream v0.2 OpenAPI경로로표현하거나실제Executor/기관ACL/원자적파일snapshot완료로확대하지 않는다.

## 2026-10-17 Dataset 계보 진단 내부 RFC

`POST /v1/datasets/lineage/verify`는 불변 Dataset 고정 참조의 현재 로컬 자산과 전이적 부모를 읽기 검사하는 별도 내부 확장이다. 원문 v0.2 OpenAPI에 Dataset HTTP 경로가 있는 것으로 표현하지 않는다. 기존 `/api/datasets`는 legacy 목록이며 불변 `dataset_versions`와 다르다. JSON 요청은 `root_ref{id,version,sha256}`와 깊이/노드 한도만 받으며 미확인 legacy 버전·SHA를 추정하지 않는다.

`greenblue.dataset-lineage-verification.rfc1`/INTERNAL_REVIEW wrapper 안의 `diagnostic`에 현재 무결성·차단·시도 여부와 검사 시작/종료 시각을 분리한다. 유효 진단은 BLOCKED도200, 잘못된형식400 INVALID_REQUEST, 예상밖 실행환경 오류503 RESOURCE_UNAVAILABLE이다. 요청 오류·내부 예외에 파일경로/원문요청을 반사하지 않고 no-store를 사용한다. 기존 main token 인증 의존성을 상속한다. 제한·기밀 조상은 더 위로 확장하지 않으며 실행·기관권한·과학 승인false, 신규Job/Result/Trace나 원본/카탈로그 쓰기없음. current_assets_revalidated=true는 한 번 이상 resolve 시도이며 전체성공 표시가 아니다. 순차적 현시점 검사이며 불변 파일 snapshot/기관RBAC/운영성능 승인으로 보지 않는다. 구현·시험·한계는 [문서36](36_dataset_lineage_api_plan.md), 카탈로그 상세 연결은 [문서37](37_dataset_lineage_ui.md)를 따른다. 최종시험과 실제브라우저 검증 수치는 각 문서/인계의 최신 기록을 확인한다.

## 2026-10-17 Job 제출 입력 snapshot companion

별도 `GET /v1/jobs/{job_id}/input-resolution` 내부 RFC로 제출 시점 진단을 조회한다. 기존 GET Job Status schema와 제출 멱등 응답은 보존한다. Legacy 기록 부재와 손상, 현재 파일 재검증을 구분하며 실행 승인을 부여하지 않는다. [문서31](31_job_input_snapshot_read.md)·[UI 기록32](32_job_snapshot_ui.md)의 최종 검증을 따른다.

## 2026-10-17 계획 단계 차단 정책 진단과 UI 인계

Workflow의 `policy_resolution`과 노드별 `dependency_resolution`에 local·선행 경로·FAIL_ALL 전역 정책 원인을 구분했다. 기존 node.blockers·응답 순서·PLAN_ONLY·BLOCKED·비실행은 보존한다. [문서29](29_workflow_blocking_policy.md)와 [UI 인계 기록](30_workflow_diagnostics_ui.md)을 따른다. 실제 상태 전이/스케줄링·작업 취소 정책을 실행한 것은 아니다. UI 영향 기능은 web_ui 인계·표시 연결·브라우저 검증까지 확인하는 AGENTS 완료 조건을 추가했다.

## 2026-10-17 Workflow 노드 입력 진단 연결

`POST /v1/workflows/plan`은 DAG 검증 후 각 노드 input_bindings를 Dataset 진단 코어에 연결한다. 정상 입력의 무조건 DATA_MISSING은 제거하고 실제 누락·무결성·품질·접근 차단 원인을 반환한다. node.input_resolution은 매 요청 snapshot이며 Job의 저장 진단 재생과 다르다. PLAN_ONLY·BLOCKED·비실행은 유지한다. [사용법·검증·후속 범위](28_workflow_input_resolution.md). 아래 Registry adapter 미연결 표기는 이번 노드 진단 연결 이전의 이력이며 실제 executor·동적 출력 바인딩은 여전히 미구현이다.

## 2026-10-17 Job 고정 입력 진단 RFC

기존 Job 제출의 409/BLOCKED·표준 Job Status·멱등성 응답을 유지하면서 `error.details.input_resolution`에 제출 시점 Dataset 대조 근거를 추가한다. 원문 status schema나 vendored 계약은 수정하지 않는다. 같은 키의 재생은 저장한 최초 진단을 돌려주며 실제 실행 시점의 재검증을 대체하지 않는다. 내부 확장 `greenblue.job-input-resolution.rfc1`과 아직 남은 ACL/과학·모델·배포 gate는 [구현·검증 기록](27_job_input_resolution.md)을 따른다. 아래 과거 시험 수치는 해당 시점의 이력이다.

## 2026-10-17 Result→SDSS RFC 추가

- `GET /v1/results/{result_id}/sdss`: 원문 Result schema, Job SUCCEEDED, Result/Job/Agent/Trace, 고정 input/model 참조, 독립 과학검증 분류와 로컬 자산 SHA를 확인한다. 차단 시 layers/reports/assets를 비워 게시하지 않는다.
- `GET /v1/results/{result_id}/assets/{index}`: 동일 manifest snapshot에서 선택한 자산을 spool 복사하고 SHA를 검증한 복사본만 전송한다. 검증 후 manifest 재조회나 원본 변경으로 다른 바이트가 전달되지 않게 했다. data root 상대경로만 지원하며 원격 URL·UNC·절대경로·경로탈출을 차단한다. 기존 API 인증을 상속한다.
- 원문 OpenAPI에 없는 `greenblue.sdss-result.rfc1` 내부 확장이다. vendored 계약은 수정하지 않았다. 외부 자산 fetch, COG tile 렌더링, 기관 승인·운영 인수를 구현한 것은 아니다.
- `tests/test_sdss_results.py` 10 PASS. 성공 경로는 명시적 임시 계약 fixture만 사용했으며 운영 Registry에 성공 Result를 추가하지 않았다. UI는 승인 Result가 있을 때 GeoJSON 지도와 검증 자산 다운로드를 연결한다.

작성: 2026-10-16. 기준 문서는 워크스페이스의 `GreenBlue_GMAIS_v0.2/GreenBlue_GMAIS_v0.2_실행형_표준패키지/`이다. **내부 검토용 제안본**이며 컨소시엄/BIG의 승인 계약이나 운영 승인으로 간주하지 않는다. 계약 기준 파일은 수정하지 않고 `contracts/upstream/GMAIS-v0.2/`에 복사해 사용한다.

## 구현된 로컬 vertical slice

`backend/app/gmais_api.py`가 제안 `/v1` 경로를 제공하고 `backend/app/main.py`가 기존 `/api`와 별도로 router를 연결한다. 현재 여섯 모델 슬롯을 Agent manifest로 노출한다. 실제 구현 상태는 LCLUC만 `BLOCKED`; 다른 다섯 개는 `NOT_IMPLEMENTED`이다. 상위 manifest는 원문 schema의 필드만 사용하고 runtime·dataset·science·deployment·contract 세부축은 별도 `/readiness` companion 응답으로 둔다.

Job 요청은 vendored `job-request.schema.json` Draft 2020-12 validator로 검사하고 `Idempotency-Key`로 중복 제출을 통제한다. 현재 학습자료 준비도, 독립 과학평가, 승인·배포 모델 gate를 통과하지 못하므로 Job은 저장된 `BLOCKED` 상태로 응답한다. 표준 `job_id`·`trace_id`를 조회할 수 있지만 이 상태에서 `Result`·지도·보고서를 만들지 않는다. 같은 키/같은 본문은 동일 Job을 가리키고, 같은 키/다른 본문은 `SCHEMA_MISMATCH`로 거절한다. `/healthz`·`/readyz`는 인증 없이 런타임 상태만 제공하며 과학 준비도를 암시하지 않는다. 브라우저 CORS 요청은 `Idempotency-Key`를 허용한다.

## 경로별 상태

| 경로 | 로컬 상태 | 참고 |
|---|---|---|
| `GET /healthz`, `GET /readyz` | 구현 | 런타임 liveness/readiness만 확인 |
| `GET /v1/agents` 및 `/{agent_id}` | 구현 | 6개 manifest, 원문 Agent schema와 계약 시험 |
| `GET /v1/agents/{agent_id}/capabilities` | 구현 | Agent별 등록 capability |
| `GET /v1/agents/{agent_id}/readiness` | 구현 | proposal companion; 다섯 readiness 축을 manifest 확장 속성으로 위장하지 않음 |
| `POST /v1/agents/{agent_id}/jobs` | 부분 구현 | Idempotency·원문 요청 schema 검사·audit 가능한 BLOCKED Job. 실행 가능한 scientific executor가 없음 |
| `GET /v1/jobs/{job_id}` | 구현 | 표준 status/trace 조회 |
| `GET /v1/jobs/{job_id}/results`·`GET /v1/results/{result_id}` | 차단/조회 | 결과가 없으면 409, 임의 result를 만들지 않음 |
| `POST /v1/jobs/{job_id}/cancel` | 제한 | BLOCKED 상태는 종결 상태로 취소 거부 |
| `POST /v1/workflows/plan` | 로컬 RFC 확장·계획 전용 | upstream workflow schema·DAG를 검사하지만 upstream v0.2 OpenAPI path가 아니다. 노드 고정 입력 Registry 진단 연결, Agent 실행 미연결로 항상 BLOCKED·Job/Result 생성 없음 |
| `POST /v1/models/{model_id}/update-tickets` | 미구현 | schema/OpenAPI만 확인; 실제 approval·ticket store·운영 책임 미확정 |

## 남은 호환·거버넌스 gap

- API route의 contract response와 에러 status/body를 원문 OpenAPI 모든 사례로 확대 검증한다.
- workflow plan은 GMAIS v0.2의 존재하는 schema를 쓰되 `/v1/workflows/plan` 별도 extension으로 버전·소유·승인 상태를 명시한다.
- Update Ticket, Model Registry, artifact/result publication, 권한별 RBAC, 감사 주체 및 기관별 external API/OCI adapter는 미구현이다.
- 현재 `/api` 모델 lifecycle과 표준 Agent approval enum은 서로 다른 저장 계약이다. 기존 기록을 임의 변환하지 않고, 버전·체크포인트 SHA·데이터 lineage를 대조하는 명시적 projection이 필요하다.
- 현재 계약 응답은 내부 검토본의 호환 구현이며 BIG/컨소시엄 승인, 독립 정확도, 실제 여섯 모델 실행, 운영 보안/배포 검증이 아니다.

## 계약 검증

`tests/test_gmais_api.py`는 upstream JSON Schema로 여섯 manifest와 Job/error/status 응답을 검사하고, BLOCKED Job의 trace/멱등성/결과 부재/외부 Agent 차단을 확인한다. `tests/test_gmais_workflow_extension.py`는 plan-only RFC, schema·DAG·차단·비실행을 검사한다. 두 파일은 각각 **8개와 7개 PASS**였고 2026-10-16 전체 회귀시험 **175개 PASS**다. 실제 로컬 HTTP smoke는 [증거](../../evidence/integration/gmais-live-http-contract-only-20261016.json)에 기록했다. 이는 계약·차단 통합시험이며 위성자료의 과학적 정확도 증거가 아니다.


## 저장 보고서 출처 대조 진단 읽기 API (67/68)

`POST /v1/diagnostics/readiness-source-identity`는 고정DATA 보고서/manifest의 명시SHA와토큰만 받아 기존읽기진단을 최소요약으로 투영한다. body exact3필드·8KiB·strictUTF8/중복/unknown/typedpin 검사, client경로입력금지, process별heavyworker1개/busy429, threadpool·no-store를 적용한다. 원본영상/assess/Job/Store 쓰기는 수행하지 않는다. HTTP200도status BLOCKED이며8승인flags false, 12계수와고정핀/토큰SHA만 반환하고 원본경로·raw토큰·member목록은 제외한다.

내부67 구현의 초기default보고서선택 오류는명시새report_path 및old/newSHA가다른합성회귀로 수정했다. Root실제HTTP는200(요약1065B)·badbool400·wrongpin409·bodylimit413·GET405를 확인했다. POST의200/400/409/413 응답no-store확인, framework GET405는별도캐시헤더없음으로기록한다. 저장보고서선언대조와현재원본파일재검증·과학/학습/실행승인은구별한다.

AgentCenter LCLUC/Workspace 검증·근거 탭에서 입력핀3개와수동조회카드를제공한다. 화면진입/뒤로가기/선택변경에자동POST하지않고입력·세대·현재route·선택key가다르면응답을폐기한다. nullable단서부재/unknown·bool/허위승인/계수모순응답은결과로표시하지않는다. 관련구현/시험은 [67 API](67_readiness_source_identity_api.md), [68 UI](68_readiness_source_identity_ui.md)를참조한다. 실제브라우저검증은67/68종결근거에기록한다.

## 98/99 최종 통합 검증 보충

최종 전체 회귀는 [corrected 로그](../../evidence/integration/model-version-api-full-tests-corrected-20261017.log)의998건/997 PASS/기존Windows1 SKIP/366.134초다. 최초 PYTHONPATH누락648건/import31오류 로그는 보존하며 통과 근거와 구분한다. [실제 화면](../../evidence/integration/model-version-api-live-ui-20261017.json)8체크·음성등록1회422·뒤로가기복귀·겹침/넘침0을 확인하고 최종layout build90 modules/27.52초를 실제로그로 정정했다(초기89와 구분). [보존 근거](../../evidence/integration/model-version-api-live-integrity-20261017.json)의 보호141·core70·이전증거631·catalog14 변경0이다. 성공등록은 격리시험만이며 운영성공등록0, caller선언≠승인을 유지한다.

## 101/102 읽기 전용 API·화면 후속

[API101](101_model_registration_provenance_api.md)과 [UI102](102_model_registration_provenance_ui.md)는100pure관측을기존선택모델에서수동조회하게연결한다. 5상태200·기존auth/404·고정503,응답상태/binding/issue·4false정합과세대방어를적용했다. 실제API/브라우저는기존모델ABSENT와없는모델404를읽기확인했고등록/실행/승인0이다. 타상태와오염·지연응답은합성시험만이다. [통합시험·보존](../../evidence/integration/model-provenance-api-live-integrity-20261017.json)과 [실제화면](../../evidence/integration/model-provenance-api-live-ui-20261017.json)을따른다. 관측4false는기존모델필드변경이아니며세대방어는응답모델신원인증이아니다. 기존선택시readiness의실파일검증과새metadataendpoint의artifact읽기0은구분한다.

### 105/106 후속 연결 및 검증

별도 비변경 진단 API와 수동 UI를 연결했다. 기존 RFC1/RFC2 결과·승인 경계를 유지한다. 새 계약·원문/한도·생산과 검증 호출 수·실제/합성 시험 및 한계는 [API105](105_workflow_job_model_record_handoff_api.md), [UI106](106_workflow_model_record_handoff_ui.md)를 따른다. 최종 전체 회귀·브라우저·보존 근거는 `evidence/integration/workflow-model-record-api-live-integrity-20261017.json`과 `evidence/integration/workflow-model-record-api-live-ui-20261017.json`이다. 이해자료·인계서도 같은 단위로 갱신했다. metadata 일치는 실바이트·권위·과학/실행 승인이 아니며 운영 Job 생성/등록은 없다.
