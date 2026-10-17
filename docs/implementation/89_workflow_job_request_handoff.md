# 89 — Workflow 선택 노드와 완성 Job 초안 전달 검사

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

상태: **TESTED_SYNTHETIC**. 공개 API·UI·실제 제출에 비연결인 내부 helper다. 운영 Workflow+Job 검증과 화면 연결은 **PLANNED**이며 원본·원장·모델·승인 변경이나 Job 생성/QA/학습 실행은 없다.

## 목적과 구현

사용자가 이미 작성한 완성 Job을 vendored 원schema로 확인하고, Agent/capability/trace/input_refs만 추출해 caller-pinned Workflow의 선택 노드와 86 comparator로 대조한다. AOI/output/purpose/environment/승인 값은 생성하거나 채우지 않는다. schema 적합성·선언 MATCH는 실제 Agent capability 지원·모델 준비·과학·기관 ACL·실행 승인이 아니다.

- 코드: `backend/app/workflow_job_request_handoff.py`, 함수 `compare_workflow_job_request_handoff(workflow_request, pinned_workflow_request_sha256, selected_node_id, full_job_request)`.
- 시험: `tests/test_workflow_job_request_handoff.py`.
- 재사용: `backend/app/gmais_api.py`의 `_job_request_validator()`, `backend/app/workflow_node_input_handoff.py`의 `compare_workflow_node_input_handoff()`.
- scope: `WORKFLOW_NODE_TO_FULL_JOB_DRAFT_HANDOFF_ONLY`; MATCH/BLOCKED. raw ID/URI/원문/예외 문자열 없이 고정 issue/hash/count와 안전한 86 comparison을 반환한다.

## hash 계약

Workflow pin은 caller가 가진 전체 Workflow canonical SHA와 비교한다. `full_job_request_sha256`은 이번 전체 초안의 **관측 hash**다. 네 인자에 full Job pin이 없으므로 caller가 이전 hash와 비교하고 실제 제출 직전 같은 초안인지 확인할 책임이 있다. `full_job_pin_verified=false`이며 출처 인증이 아니다.

`extracted_metadata_sha256`은 Agent/capability/{trace_id}/ordered input_refs만의 hash다. AOI/output/parameters/purpose가 달라지면 전체 초안 hash는 바뀌지만 metadata hash와 MATCH는 유지될 수 있다. 기대 AOI/output 동등성을 검사하지 않는다. Python `json.dumps(sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':'))` UTF8 SHA이므로 1.0/0.0·지수·Unicode 등 JS JSON.stringify 교차언어 동등성은 미검증이다. 배열 순서·URI/role의 존재와 빈 URI를 원형대로 보존한다.

## 순서·지원 범위

1. fullJob와 Workflow를 exact builtin JSON으로 선검사한다. dict/list/str/int/float/bool/null 외 객체·tuple/subclass, cycle, surrogate, 비문자 key를 거부한다. depth24, atom16384(key 포함), string4096 codepoint, key256, int 절댓값 2^53-1 이하, finite float, 각 canonical UTF8 512KiB를 지원한다. bit_length로 거대정수를 먼저 제한한다. string/key별 escape 포함 bytes·구분자를 누적해 전체 직렬화 전에 예산 차단한다. null/boolean은 누적5bytes로 보수적 계수하여 일부 경계 요청을 더 일찍 거부할 수 있다. API JSON parser가 아니므로 이미 dict로 잃은 중복 JSON key를 복원하지 않는다.
2. vendored 원schema factory를 재사용한다. `_validate_job()`·가짜 Idempotency-Key·path Agent 제출은 호출하지 않는다. required/unknown/context purpose/environment/ref SHA/CRS 등 원schema를 확인한다. schema가 허용한 parameters와 time_range 확장 속성은 유지한다.
3. 현재 `.runtime` FormatChecker에 선택 dependency 부재로 date-time checker가 없음을 첫 실패에서 발견했다. 89 전용 detached checker에 date-time을 등록하고 `validator.evolve(format_checker=...)`한다. cached validator/checker와 class 전역은 변경하지 않는다. timezone 필수, T/t·Z/z·소수초·달력·offset hour00..23/minute00..59를 확인하는 RFC3339 지원 subset이며 leap second는 거부한다. 기간 순서·과학 정책은 검사하지 않는다. 독립 검토에서 datetime.fromisoformat이 +00:60/+01:99 offset 분을 정규화하는 문제를 발견해 regex 범위와 회귀를 추가했다.
4. bbox는 exact int/float finite4개 및 west<east/south<north를 확인한다. bool은 숫자로 허용하지 않는다(일반 parameters JSON bool은 정상). 지리 경계·CRS 의미·투영·기대 AOI 일치 검사는 아니다.
5. optional model_ref id/version/role은 기존 `_text`의 비공백·256codepoint·제어문자 없음 지원범위로 확인하고 version latest/current는 거부한다. 모델 존재/Registry/원본 인증은 아니다. optional execution_context.workflow_run_id는 명시된 경우 Workflow 값과 같아야 하며 없으면 채우지 않는다.
6. metadata만 추출하여 86을 정확히1회 호출한다. 앞 단계 차단이면0회다. caller pin·선택 노드·ordered input identity/version/hash/role/URI 계약은86 그대로다.

## 상태·I/O·오류

`full_job_schema_validated`는 원schema와 date-time 지원검사, `bbox_numeric_order_validated`는 bbox 지원검사만 나타낸다. schema VALID 후 model/bbox/metadata에서 BLOCKED일 수 있다. `complete_job_validated`, aoi/output verified, execution/training/science/ACL/Registry/bytes/TOCTOU/executor/DAG/선행Result/모델/capability/원본 인증 flag는 false다.

`validator_attempted`, `validator_status` NOT_RUN/INVALID/VALID/RESOURCE_UNAVAILABLE, `comparator_calls`0/1을 반환한다. loader OSError·Unicode/JSON/SchemaError·MemoryError 및 기존 factory의 **정확한 schema 미발견 메시지** RuntimeError만 safe RESOURCE_UNAVAILABLE로 반환한다. 다른 RuntimeError/AssertionError와 BaseException은 전파한다. schema 순회 OSError/MemoryError는 safe resource 차단이다. 예외 원문은 반환하지 않는다.

schema factory cold path는 local schema 확인/읽기가 가능해 전체 I/O0로 주장하지 않는다. `schema_files_read=null`은 실행별 실제 파일 계수를 계측하지 않았다는 뜻이다. network/source asset 읽기·쓰기/DB/Registry/resolver/executor는0이다. module import/schema load를 원본 asset 검사와 구분한다. 실제 Job POST/저장/역채움/수집/QA/학습/배포0.

## 시험 근거와 한계

`evidence/integration/full-job-handoff-related-20261017.log`: **15 PASS/0.172초**. 필수/format/unknown/context, decimal bbox/bool/finite/order, size/depth/atom/cycle/bigint/임의타입, metadata 변조·URI/role 부재·모델 pin·workflow ID, 전체hash 변경·순서·privacy/원문불변, comparator1회·가짜제출0·schema cold read1개·cached checker불변·실제 factory missing-schema safe차단과 복귀를 합성 시험했다. 독립·전체·보존 증거는 Root 인계서에 기록한다.

`evidence/integration/full-job-handoff-initial-format-gap-20261017.log`는 최초 date-time 기대 실패의 **재현 로그**다. 최초 원로그는 이미 덮어써졌으므로 최초 원본 로그라고 주장하지 않는다. 개발 중 신규문서 쓰기 인코딩 실수를 복원했고 오류문자열은 ASCII Unicode escapes로 정확히 기록했으며 실제 factory missing 회귀로 검증했다. 기존 schema/API/86~88 수정0.

## UI 인계

공개 API/UI에 비연결인 내부 core이므로 이번 직접 화면 변경·프론트 빌드·브라우저 재시험은 불필요하다. 현재87/88 metadata 화면을 full Job 검증 완료로 표시하면 안 된다. web_ui는 다음 연결 시 full draft 별도 입력, finite decimal strict parser, Pythoncanonical·전체초안 관측hash와 callerWorkflowpin 구분, typed 상태/안전 오류, 수동 요청·stale guard·실제 브라우저 시험을 설계한다. 실제 Job/Workflow 실행·기관 승인은 별도다.


## 20:10 KST — 완성 Job 초안과 Workflow 노드 내부 연결 검증 완료 (89)

- **full_job_handoff:** 신규 workflow_job_request_handoff.py·합성시험·문서89 완료/동결. 관련15 PASS/0.172초. bounded builtin JSON/finite·원schema·날짜형식·소수bbox 숫자/순서·model 고정버전 지원검사를 거쳐 exact4 metadata를 추출해86에1회 대조한다. optional workflow ID 부재는 채우지 않으며 AOI/output/model/context 기본값·가짜제출/Job 생성은 없다.
- **독립 검토:** 최종15 PASS/0.220초, 보완 후 추가결함0. date-time 선택 dependency가 없는 기존 환경에서 잘못된 날짜가 통과하는 현상을 재현했고89 전용 detached checker/evolve로 보완했다. timezone분 정규화(+00:60/+01:99)·모델공백·missing-schema와 programmerRuntimeError의 구분을 보완했다. 실제factory missing-schema 회귀까지 확인했다. 기존cachedchecker/원schema/API는 변경하지 않아 기존공통날짜검사개선은 별도 대기다.
- **증거 구분:** 최초날짜기대실패 raw로그는 이미 덮어써져 남아있지 않으며 initial-format-gap 로그는 현상재현 근거다. 독립14개 중간이력은 history로그에 보존하고 대표로그는 최종15개만 기록했다. 반복/별도경계시험을 신규시험 수에 합산하지 않는다. source와 신규문서의 인코딩 실수는 복원하고 실제factory예외 회귀로 검증했다. 원본/기존소스 변경은 없다.
- **Root 전체·보존:** backend912개/911 PASS/기존Windows symlink1 SKIP/359.738초/exit0. 보호141·기존core+원schema57 변경0·기존tracked code/data/tests/frontend변경[]·catalog14/기존Job본문동일. 원본·원장/lock·예약136314880B·분할·모델·후보1095/차단4·학습BLOCKED 보존. mode=ro 실제catalog에 저장Workflow0/Job2이며 새helper의 성공/차단은 TESTED_SYNTHETIC, 운영Workflow 전달 검증이 아니다.
- **UI·실행 상태:** UI담당읽기검토 결과 이번내부helper는 공개API/UI에 비연결이므로 직접UI/프론트빌드/브라우저재시험은 불필요했다. 기존86~88 코드/응답/화면 보존. 실제JobPOST·역채움·새QA/학습·수집/배포·Workflow/executor연결0. Vite2/API3 유지, 실제worker관측과 geoai-2 ACTIVE10분 예약설정을 구분한다.
- **문서·이해자료:** 신규89·관련07/86/88·운영원장/소유권/인계서를 갱신했다. understanding_agent에 완료코드/관련·독립·전체/실제catalog·보존을 전달해 쉬운설명·이론·코드데이터·시험·대본/FAQ·INDEX/변경이력을 같은단위로 갱신한다. 최종감사와 rawSHA snapshot은 `evidence/integration/full-job-handoff-closeout-20261017.json`에기록한다.
- **범위·다음:** schema 적합성·bbox숫자순서·metadata MATCH도 완성Job/과학적AOI/output·Agentcapability/model·DAG·기관ACL/학습/실행 승인이 아니다. schema coldlocal읽기는 미계측null이며 자산/DB/Registry I/O0와구분한다. fullJob SHA는 Pythoncanonical 관측값일뿐 fullJobpin이나출처인증이아니다. 다음은 별도수동 fullJob API/독립child 연결(PLANNED/미착수): 전체RAWbodySHA로응답결합·decimalparser·server관측hash표시를사용하고 기존87/88정수전용입력계약은유지한다. 전체프로젝트는 미완료이며 지속개발 대기열을 유지한다.

근거: `evidence/integration/full-job-handoff-live-integrity-20261017.json`, `evidence/integration/full-job-handoff-full-tests-20261017.log`, `evidence/integration/full-job-handoff-catalog-observation-20261017.json`.

## 103 별도 내부 identity 비교 후속

[명시 identity 대조](103_model_reference_record_comparison.md)는전체GMAIS model_ref가아닌명시추출exact3 id/version/sha256와호출자가제공한레코드만비교한다. 역할/URI·전체Job검증이나record선택/Registry조회는수행하지않는다. 같은id의100관측이일치미검증인때만버전/SHA를비교하고최고상태도MATCH_UNVERIFIED·권위/실바이트/과학/실행/model_verifiedfalse다. None은RECORD_NOT_PROVIDED이며실DBNotFound조회와다르다. 기존Workflow89·94/등록/관측API/UI호출은미연결·기존출력/falseflags불변이다. [합성시험·보존근거](../../evidence/integration/model-reference-record-live-integrity-20261017.json)를따르며이번전체/frontend/build/browser재시험은없다.

## 104 별도 내부 Workflow 모델 대조 연결

[연결함수104](104_workflow_job_model_record_handoff.md)는원89결과를그대로유지하며정상MATCH뒤에모델참조가있을때만exact3 identity를추출해103과호출자제공레코드를대조한다. 89차단후wrapper추가접근/1030,참조부재1030,참조존재1031회다. outerOBSERVED는대조수행관측일뿐일치·승인이아니고nested103과5false로한계를구분한다. 기존89/94/RFC1/2·103/API/UI출력은변경하지않았다. URI해결·Registry/resolver·바이트검증·기관/실행승인0이다. 원89coldschema읽기와wrapper추가IO0은구분한다. [관련·독립시험/보존](../../evidence/integration/workflow-model-record-live-integrity-20261017.json)은합성근거이며운영Workflow참조시험이아니다. 이번전체/frontend/build/browser재시험없음도이전전체근거와구분한다.

### 105/106 후속 연결 및 검증

별도 비변경 진단 API와 수동 UI를 연결했다. 기존 RFC1/RFC2 결과·승인 경계를 유지한다. 새 계약·원문/한도·생산과 검증 호출 수·실제/합성 시험 및 한계는 [API105](105_workflow_job_model_record_handoff_api.md), [UI106](106_workflow_model_record_handoff_ui.md)를 따른다. 최종 전체 회귀·브라우저·보존 근거는 `evidence/integration/workflow-model-record-api-live-integrity-20261017.json`과 `evidence/integration/workflow-model-record-api-live-ui-20261017.json`이다. 이해자료·인계서도 같은 단위로 갱신했다. metadata 일치는 실바이트·권위·과학/실행 승인이 아니며 운영 Job 생성/등록은 없다.
