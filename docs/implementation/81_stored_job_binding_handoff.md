# 81. 저장 expected와 전달 supplied binding의 순수 handoff 대조

## 2026-10-17 저장·현재 직접 입력의 비실행 preflight (83)

`inspect_stored_current_binding_preflight(store,requested_job_id)`는 저장된 제출 manifest pin과 같은 참조를 현재 resolver가 검증한 pin을 연결한다. 외부 expected/supplied/경로를 받지 않는다. 저장 capture가 RECORDED인 경우만 기존 resolver/capture의 단일 pass를 실행하고, 그 pass의 현재 envelope를81 비교 함수에 전달한다. 비교 때문에 추가 Registry 조회를 하지 않는다. legacy/unavailable은 resolver0·UNKNOWN으로 남겨 과거 pin을 소급 생성하지 않는다.

저장 근거·현재 integrity/quality/PUBLIC metadata 진단·pin 선언 일치의 세 축을 구분한다. 현재 metadata와 canonical digest가 함께 바뀌면 id/version/assetSHA가 같아도 저장 pin과 달라 차단된다. 품질·제한자료 차단은 pin 일치만으로 해제하지 않는다. 현재 resolver 응답의 크기·타입·enum·authorization_false를 snapshot projection보다 먼저 검사해 잘못된 권한 표시를 정상화하지 않는다.

이 단계는 실제 로컬 asset hash·Registry 읽기가 있을 수 있어 I/O0이 아니다. inner81의 DB0/current_files_revalidated=false는 순수 비교 범위다. top은 직접 입력 진단 관측과 전체 원본/전이 계보·기관 ACL·과학·학습·배포·executor·TOCTOU 승인을 구분한다. 새 top에 current_files_revalidated를 복사하지 않고 transitive_lineage_verified=false를 명시한다. 전체 body 파싱·파일 hash의 강제 메모리/개별 byte 상한을 제공하지 않는다.

관련12 PASS4.402초·독립12 PASS3.119초. 현재 pin 변조/품질·접근 차단의 양성·음성 검증은 격리 TempStore와 작은 로컬 시험 자산으로 수행했으며 운영 Registry를 변경한 것이 아니다. 실제 기존 legacy2는 UNKNOWN/current NOT_RUN, missing/invalid를 포함get3·resolver0/Registryget0·catalog14/Job 본문 불변이었다. 실제 current RECORDED/MATCH 또는 executor 전달 관측을 주장하지 않는다. 정확 계약·오류·시험은 [문서83](83_stored_current_binding_preflight.md), 실제 읽기 근거는 `evidence/integration/stored-current-binding-live-validation-20261017.json`을 따른다. 공개 API/UI/Workflow/executor에는 미연결이므로 기존79/80 화면·응답은 바꾸지 않는다.

## 2026-10-17 configured Store 단일 조회 연결 (82)

`inspect_stored_job_binding_handoff(store,requested_job_id,supplied_envelope)`는 호출자가 Job/expected를 직접 넘기지 않고, 설정된 Store에서 Job 한 건을 읽어 81 검증 함수에 전달하는 내부 어댑터다. 유효한 요청 ID는 supplied 형식과 관계없이 get을 정확히 한 번 시도하고, 잘못된 ID는 조회하지 않는다. 조회 관측 상태와 선언 비교 결과를 별도로 반환한다. 손상된 Job이 정상 반환되면 store_status는 OBSERVED이지만 comparison은 BLOCKED다.

NOT_FOUND는 KeyError의 인자 수·정확한 문자열 타입·길이를 먼저 검사하고 요청 ID와 같은 경우만 해당한다. 다른 KeyError와 명시한 저장소/JSON/자원 오류는 고정 RESOURCE_UNAVAILABLE로 분리한다. 내부 예외 원문을 결과에 넣지 않는다. RuntimeError/AssertionError 등 프로그래밍 결함, 비교 함수 오류, 프로세스 종료 예외는 정상 진단으로 숨기지 않고 전파한다.

wrapper와 내부 비교 함수의 15개 승인·인증 플래그는 모두 false다. 내부 순수 함수의 database_calls=0은 어댑터 전체에 DB 읽기가 없다는 뜻이 아니다. 실제 Store.get은 body 전체를 JSON으로 파싱하므로 이 연결은 DB 파서나 메모리의 강제 한도를 제공하지 않는다. configured Store의 선택 책임, 실제 executor 입력 캡처, 암호학적 원본 인증, 현재 파일·권한·과학 검증, 원자 snapshot/TOCTOU 보호는 별도다.

관련12 PASS1.416초·독립12 PASS1.084초. Root는 운영 Store 생성자/DDL 없이 mode=ro subclass에서 기존 Store.get을 재사용했다. 기존 legacy2의 local supplied8건은 UNKNOWN4/BLOCKED4, 없는 Job은 NOT_FOUND/조회1, 긴 ID는 INVALID_REQUEST/조회0이었다. 총9get 뒤 catalog14행과 원 Job 본문은 불변이다. 실제 executor 캡처나 운영 MATCH를 검증한 것이 아니다. 근거는 `evidence/integration/stored-binding-store-adapter-live-validation-20261017.json`, 정확한 계약과 시험은 [문서82](82_stored_job_binding_handoff_store.md)를 따른다. 공개 API/UI/executor에는 연결하지 않으므로 기존 79/80 응답과 화면을 바꾸지 않는다.

상태: **TESTED_SYNTHETIC / 실제 executor 미연결**. `backend/app/stored_job_binding_handoff.py`의 `compare_stored_job_binding_handoff(job,requested_job_id,supplied_envelope)`는 검증한 저장 Job/capture 안의 expected만77 비교기로 연결한다. caller가 별도의 expected를 주입하는 인자는 없다. 현재 Registry로 과거 pin을 채우거나 원본 파일을 확인하지 않는다.

## 흐름과 상태 우선순위

1.79 public `project_job_execution_binding_capture`로 Job/Agent/Trace/request 순서/id/version/asset SHA/role presence·78 exact capture/12false/additional0·awaretime·canonical hash를 검증한다. 기존79 코드는 수정하지 않는다.
2.77 selfcompare로 supplied envelope의 exact schema·64개/256자·typed index/고정version/SHA·같은 identity 상충을 검증한다. MATCH뿐 아니라 선택 manifest pin이 없는 UNKNOWN도 **형식상 유효**한 supplied다. malformed supplied는 legacy/unavailable이라도 BLOCKED다.
3.저장 상태 INVALID는 BLOCKED다. supplied와 stored가 둘 다 invalid이면 안전한 두 쪽 reason을 함께 담을 수 있다.
4.RECORDED에서만 검증한 `job.execution_input_binding_capture.expected_envelope`를 expected로77에 전달한다. supplied의 pin 누락/변조·Job/Agent/Trace·순서/개수/id/version/asset SHA/role presence 차이는 BLOCKED다. 모두 일치하면 MATCH다.
5.LEGACY/UNAVAILABLE도79 `_selected_request`의 bounded 선택 메타데이터를 supplied와 비교한다. 눈에 보이는 신원·ref 차이는 BLOCKED다. 이 부분이 같고 저장 expected/manifest pin이 없다는 이유만 남으면 UNKNOWN이다. supplied의 새 pin으로 저장 expected를 만들지 않는다.

우선순위는 **BLOCKED > UNKNOWN > MATCH**다. LEGACY나UNAVAILABLE라는 이유로 잘못된 supplied를 UNKNOWN으로 덮지 않는다. UNKNOWN을 현재 Registry 조회/다른 row의 pin/외부 expected로 해소하지 않는다. role 미기록을 null/default로 채우지 않으며 같은 id의 다른 고정 version은 정상 복수 입력이다.

## 입력과 bounded 동작

세 인자는 메모리 객체다. Job 원문 전체를 deepcopy/serialize하지 않고79에서 검증한 선택 scalar만 다룬다. request refs 및 supplied bindings는1..64, 식별자/role은 exact str1..256·공백전용/control/surrogate 거부, SHA는 lower64hex, index는 exact int이며 배열 position과 같아야 한다. version latest/current는 거부한다. unknown key·nested/cycle·bool/int 혼동·거대 수/문자열은 기존77/79의 선검사로 차단한다.

79 public projection은 safe 상태/계수/hash를 만들고, legacy 비교에는 private `_selected_request`를 재사용한다. 이는 같은 bounded 메타데이터의 순수 재대조이며 DB/파일 재읽기가 아니다. URI/AOI/model/parameters는 범위 밖이다. supplied는 호출자 선언이며 **실제 executor에서 캡처한 값이라는 인증이 없다**.

## 정확한 결과 계약

```text
schema_version: 1
scope: STORED_EXPECTED_TO_SUPPLIED_DECLARATIONS_ONLY
status: MATCH | BLOCKED | UNKNOWN
stored_capture_status: RECORDED | UNAVAILABLE | LEGACY | INVALID
request_job_sha256: lower64hex | null
expected_bindings_sha256: lower64hex | null
supplied_bindings_sha256: lower64hex | null
request_binding_count: 1..64 | null
stored_expected_binding_count: 1..64 | null
supplied_binding_count: 1..64 | null
declarations_match: bool
issues: list[{side,input_index,code}]
```

request_job_sha256는 유효 요청 Job ID literal의 UTF8 SHA다. literal 자체가 잘못됐을 때만 null이며 stored Job/capture가 invalid여도 유효 요청의 hash는 유지한다. request_binding_count는79에서 유효한 Job/request refs이면 유지하고 아니면 null이다. expected_bindings_sha256/stored_expected_binding_count는 저장 RECORDED만 값이 있으며 supplied가 invalid여도 검증된 저장 근거를 유지할 수 있다. supplied의 hash/count는 supplied 형식이 유효한 경우만 반환하며 invalid이면 null이다.

두 bindings digest는 각각 **ordered binding 배열만**의 canonical SHA256다. Python json.dumps(sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':')) UTF8 규약이며 RFC8785 또는 Job/Agent/Trace 전체 요청 hash가 아니다. 신원은 따로 비교한다. supplied의 Job ID만 바꾸면 배열 digest는 같을 수 있지만 결과는 BLOCKED다. 선언이 일치했다는 declarations_match는 MATCH에서만 true다.

issues는 raw id/version/SHA/role/URI/manifest·경로·원문 예외 없이 safe code/index만 반환한다. side는 stored/supplied/comparison이며77의 저장 expected 검증 관련 reason을 그대로 분류할 수 있는 expected도 허용한다. index는 null 또는 exact int0..63이다. 반복검증의 중복 supplied 오류는 selfcompare의 expected-side 한 집합만 골라 supplied-side로 표시한다. 입력64개와 고정 검증 필드 수로 issue는512개 이하이며 저장을 자르거나 오류를 생략해 MATCH로 만들지 않는다.

safe code 집합은 다음과 같다.

```text
ENVELOPE_SCHEMA_INVALID, IDENTITY_SCHEMA_INVALID, BINDING_COUNT_INVALID,
BINDING_SCHEMA_INVALID, BINDING_INDEX_INVALID, BINDING_IDENTITY_INVALID,
BINDING_VERSION_NOT_PINNED, BINDING_SHA_INVALID, BINDING_ROLE_INVALID,
BINDING_MANIFEST_SHA_INVALID, BINDING_IDENTITY_CONFLICT,
JOB_ID_MISMATCH, AGENT_ID_MISMATCH, TRACE_ID_MISMATCH,
BINDING_COUNT_MISMATCH, BINDING_ID_MISMATCH, BINDING_VERSION_MISMATCH,
BINDING_SHA_MISMATCH, BINDING_ROLE_MISMATCH, BINDING_MANIFEST_PIN_MISMATCH,
STORED_JOB_INVALID, STORED_CAPTURE_INVALID,
LEGACY_EXPECTED_BINDING_NOT_RECORDED, EXPECTED_BINDING_CAPTURE_UNAVAILABLE
```

유효 legacy/unavailable의 UNKNOWN은 마지막 두 code 중 정확히 하나와 side stored/index null을 반환한다. RECORDED MATCH는 issues=[]다. supplied 또는 저장 invalid에 이유가 있으면 BLOCKED를 유지한다.

다음15개 flag는 모두 false다: execution_authorized, ready_for_execution, ready_for_training, scientific_approval, acl_verified, registry_verified, training_authorized, pixels_verified, toc_tou_protected, executor_connected, artifact_bytes_verified, manifest_bytes_verified, current_files_revalidated, executor_bindings_compared, stored_job_origin_verified. network_requests/source_files_read/source_files_written/database_calls/registry_calls/resolver_calls/executor_calls는 각각0이다.

## 입증하지 않는 범위

passed Job이 실제 DB에서 읽혔는지·신뢰하는 제출 snapshot인지 이 함수는 인증하지 않는다. caller가 Job과 supplied를 함께 구성하여 MATCH를 만들 수 있으므로 이것을 원본 출처 인증으로 해석하면 안 된다. 실제 저장소의 신뢰 경계와 executor supplied 캡처 adapter가 후속으로 필요하다. 현재 함수는 그 adapter/API/UI/DB/executor에 연결되어 있지 않다.

순수 메타데이터 대조는 입력 객체를 변경하지 않지만 caller의 동시 변경에 대한 OS 원자 snapshot/TOCTOU 보호는 제공하지 않는다. 원본 자산·manifest 바이트·기관 ACL·모델 readiness·분할/독립성·과학/학습 승인을 확인하거나 gate를 해제하지 않는다. 원장/lock/예약·기존 Job·분할·모델·Registry를 쓰지 않는다.

## 합성 시험과 인계

```powershell
$env:PYTHONPATH="$PWD\.runtime;$PWD\backend;$PWD\tests"
python -m unittest test_stored_job_binding_handoff -v
```

관련 **13 PASS /0.057초 /종료0**, `evidence/integration/stored-job-binding-handoff-related-20261017.log`. RECORDED MATCH/15false, caller expected 인자 거부, legacy/unavailable supplied pin 역채움 금지, invalidsupplied 우선, visible Job/Agent/Trace/id/version/asset/role 차이, manifest pin 누락/변조, malformed 저장 Job/capture, 공동 invalid 안전 reason·요청hash, ordered 교환/개수/index·다른 버전, 타입/한도/cycle/상충, issue상한/privacy, 배열 digest와신원범위분리, IO0/입력 불변을 확인했다. 합성 fixture import 과정에서 기존 TestClient httpx deprecation 경고가 나타나지만 추가 설치/의존성 변경은 하지 않았다.

독립 최종 시험도 **13 PASS /0.056초 /종료0**, `evidence/integration/stored-binding-handoff-independent-20261017.log`다. 같은13개 재실행은 Root 전체 회귀 건수에 중복 합산하지 않는다. 독립 source 검토에서 추가 결함은 발견하지 않았다.

Root 실제 읽기 검증은 기존 legacy Job2개의 선택 선언을 로컬 replay한8건으로 UNKNOWN4/BLOCKED4를 확인했다. `evidence/integration/stored-binding-handoff-live-validation-20261017.json`과 `evidence/integration/stored-binding-handoff-live-replay-20261017.py`가 근거이며 catalog14행과 원 Job body는 불변이다. Root가 전체 회귀·보존·운영/이해자료를 별도로 연결한다. 로컬 replay는 실제 executor capture가 아니다. 이번에는 공개 API/UI/CLI를 추가하지 않는 순수 내부 비교 계약이므로 직접 화면 변경·프론트/브라우저 검증은 없다. 기존79/80 화면과 기존42 코어는 변경하지 않는다.


## Root 최종 통합 검증

전체backend회귀832개/831 PASS/기존Windows symlink1 SKIP/344.500초/exit0. `evidence/integration/stored-binding-handoff-full-tests-20261017.log` 참조. 종료후 보호141/불변코어42/catalog14/원JobbodySHA동일·기존추적code/data/test/frontend변경0은 `evidence/integration/stored-binding-handoff-live-integrity-20261017.json`에기록했다. 실제수집/QA/학습/executor/새JobPOST/역채움없음·직접API/UI변경없음.

후속은configured Store의Job1회조회→이guard를호출하는내부readonlyadapter로PLANNED다. callerJob/expected주입을호출경계에서줄이되저장소암호학적출처인증/실제executor관측/TOCTOU보호가아니다. Store.get의전체JSON읽기를boundedDBparser/hardRAM보장으로표현하지않는다. 아직후속코드구현/실행0이며기존Job·Workflowgate는BLOCKED/PLAN_ONLY를유지한다.
