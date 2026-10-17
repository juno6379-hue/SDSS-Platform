# 79. 저장 제출 binding capture의 최소 읽기 API

## 2026-10-17 configured Store 단일 조회 연결 (82)

`inspect_stored_job_binding_handoff(store,requested_job_id,supplied_envelope)`는 호출자가 Job/expected를 직접 넘기지 않고, 설정된 Store에서 Job 한 건을 읽어 81 검증 함수에 전달하는 내부 어댑터다. 유효한 요청 ID는 supplied 형식과 관계없이 get을 정확히 한 번 시도하고, 잘못된 ID는 조회하지 않는다. 조회 관측 상태와 선언 비교 결과를 별도로 반환한다. 손상된 Job이 정상 반환되면 store_status는 OBSERVED이지만 comparison은 BLOCKED다.

NOT_FOUND는 KeyError의 인자 수·정확한 문자열 타입·길이를 먼저 검사하고 요청 ID와 같은 경우만 해당한다. 다른 KeyError와 명시한 저장소/JSON/자원 오류는 고정 RESOURCE_UNAVAILABLE로 분리한다. 내부 예외 원문을 결과에 넣지 않는다. RuntimeError/AssertionError 등 프로그래밍 결함, 비교 함수 오류, 프로세스 종료 예외는 정상 진단으로 숨기지 않고 전파한다.

wrapper와 내부 비교 함수의 15개 승인·인증 플래그는 모두 false다. 내부 순수 함수의 database_calls=0은 어댑터 전체에 DB 읽기가 없다는 뜻이 아니다. 실제 Store.get은 body 전체를 JSON으로 파싱하므로 이 연결은 DB 파서나 메모리의 강제 한도를 제공하지 않는다. configured Store의 선택 책임, 실제 executor 입력 캡처, 암호학적 원본 인증, 현재 파일·권한·과학 검증, 원자 snapshot/TOCTOU 보호는 별도다.

관련12 PASS1.416초·독립12 PASS1.084초. Root는 운영 Store 생성자/DDL 없이 mode=ro subclass에서 기존 Store.get을 재사용했다. 기존 legacy2의 local supplied8건은 UNKNOWN4/BLOCKED4, 없는 Job은 NOT_FOUND/조회1, 긴 ID는 INVALID_REQUEST/조회0이었다. 총9get 뒤 catalog14행과 원 Job 본문은 불변이다. 실제 executor 캡처나 운영 MATCH를 검증한 것이 아니다. 근거는 `evidence/integration/stored-binding-store-adapter-live-validation-20261017.json`, 정확한 계약과 시험은 [문서82](82_stored_job_binding_handoff_store.md)를 따른다. 공개 API/UI/executor에는 연결하지 않으므로 기존 79/80 응답과 화면을 바꾸지 않는다.

## 2026-10-17 저장 expected·supplied 순수 handoff 대조 (81)

`compare_stored_job_binding_handoff(job,requested_job_id,supplied_envelope)`는 저장 Job/capture의79 형식·신원·hash 검증과77의 ordered binding 대조를 연결하는 내부 순수 함수다. 별도 caller expected 인자를 받지 않으며 RECORDED 저장 envelope만 expected로 사용한다. 잘못된 supplied/저장 Job·capture/신원·순서·role·pin 불일치는 BLOCKED가 우선한다. 유효 legacy/unavailable에서도 저장 request와 supplied의 눈에 보이는 연결을 검사하며, 그 연결은 같고 expected pin만 미기록이면 UNKNOWN이다. supplied나 현재 Registry로 과거 expected를 역채우지 않는다.

응답은 안전한 상태·계수·집계 배열 hash와 code/index만 제공한다. 12승인 및 current_files_revalidated/executor_bindings_compared/stored_job_origin_verified는 모두 false, 함수 자체의7IO계수는0이다. passed Job이 실제 저장소에서 왔는지 또는 supplied가 실제 실행자에서 수집됐는지 인증하지 않으며 caller가 양쪽 객체를 구성해 MATCH를 만들 수도 있다. 현재 파일·기관 ACL·TOCTOU/동시변조 원자성·학습준비/과학적 성능을 입증하지 않는다.

관련/독립 신규13 PASS(0.057초/0.056초), 실제 기존 legacy2의 선택 저장 선언을 로컬 supplied로 복사한8경우 UNKNOWN4/BLOCKED4·catalog14/Jobbody불변을 확인했다. 실제 executor 관측/생성된 production MATCH는 아니다. `evidence/integration/stored-binding-handoff-live-validation-20261017.json` 참조. 정확 결과 계약·safe enum·한계·시험은 [문서81](81_stored_job_binding_handoff.md)을 따른다. API/UI/executor/DB에는 미연결인 내부 단위이므로 기존79/80 공개 응답·카드·승인 gate는 그대로이며 직접 프론트/브라우저 재시험은 하지 않는다.

상태: **TESTED_SYNTHETIC(새 capture/변조) + VERIFIED_REAL(기존 legacy GET·404·긴 literal·보존) / 현재 파일·Registry·executor 미검증**. 새 projection과 GET API는 Job에 이미 저장한78 캡처의 형식·신원 연결·canonical binding hash만 대조한다. 기존 Job은 LEGACY로 구분하고 Registry 재조회로 채우지 않는다. 현재 자산, 제출 이후 변경, 실제 실행기로 전달한 binding, 권한·학습 준비를 인증하지 않는다.

## 소유 구현과 데이터 흐름

- `backend/app/job_execution_binding_capture.py`: 순수 `project_job_execution_binding_capture(job,job_id)`.
- `backend/app/job_execution_binding_capture_api.py`: `create_job_execution_binding_capture_router(get_store)`와 정확한 RESPONSE_SCHEMA/ERROR_SCHEMA.
- `tests/test_job_execution_binding_capture.py`: 작은 합성 Job/capture·Temp TestClient 시험.
- Root가 `main.py`의 import/include만 통합한다. 기존 capture/resolver/Registry·원 schema·DB는 수정하지 않는다.

`GET /v1/jobs/{job_id}/execution-input-binding`은 유효 요청 literal에 대해 threadpool worker에서 `get_store().get('gmais_jobs',job_id)` **1회**만 수행한다. 그 뒤 순수 projection을 반환한다. 현재 Registry/resolver·원본 파일/자산·네트워크 fetch·추가 DB 쓰기·assess/학습은 없다. 원래 API 인증 dependency를 계승한다. 자동 조회 없이 UI의 명시적 수동 GET에 연결하는 계약이며 UI80은 별도 담당이 검증한다.

## 입력 상한과 저장 연결 검증

요청 Job ID와 선택 Job/Agent/Trace 값 모두 exact str1..256자·공백만인 값/C0·C1 control·DEL·unpaired surrogate 거부 후 비교/hash한다. 모든 선택 신원 값을 먼저 제한하므로 거대한 동일 문자열을 상한 전에 비교하지 않는다. request refs는 exact list1..64, ref는 id/version/sha256와 선택 role/uri의 기존 키만 받는다. URI는 str 형식만 확인하고 복사·정규화·resolve하거나 반환하지 않는다. AOI/model/parameters는 범위 밖이며 원 upstream schema를 바꾸지 않는다.

Job의 id/job_id/status.job_id가 요청 literal과 같고, Job/status/request의 agent 및 status/request context trace가 일치해야 한다. request의 선택 id/version/asset SHA/role presence/순서/index는77 guard의 typed/bounded 계약으로 먼저 검증한다. 이 필수 Job 정보가 잘못되면 capture 부재보다 INVALID를 우선한다.

capture는78의 exact key 집합·schema1/extension/scope/internalreview/pin_source·12false·additional_* exact int0를 확인한다. boolFalse는 int0의 대체가 아니다. RECORDED의 timezone-aware captured_at·빈 issues·전체 manifest pin envelope를77 selfcompare MATCH로 검사하고 canonical bindings SHA를 대조한다. 다시 Job/request의 ordered selected refs와 envelope를 비교하여 Job/Agent/Trace/id/version/asset SHA/role의 누락·변조·순서 교환을 거부한다. hash를 다시 계산하여 변조를 감춘 경우도 request linkage가 틀리면 INVALID다.

UNAVAILABLE은 expected_envelope/hash가 null이며 안전 issue가 정확히1개여야 한다. captured_at=null은78 optional import/builder fallback에 합법적이다. null이 아니면 aware timestamp여야 한다. 부분 envelope나 상충 승인 필드를 허용하지 않는다.

## 정확한 응답 계약

최상위는 아래26키만 반환한다. API 모듈 RESPONSE_SCHEMA를 OpenAPI에도 노출한다. 추가 키·원문 Job/capture·데이터셋 식별자·role·manifest pin·URI·경로·예외·captured_at은 응답에 포함하지 않는다.

| 키 | 타입/값 |
|---|---|
| schema_version | exact int1 |
| extension | greenblue.stored-execution-input-binding.rfc1 |
| approval_status | INTERNAL_REVIEW |
| scope | STORED_SUBMISSION_BINDING_ONLY |
| status | RECORDED / UNAVAILABLE / LEGACY / INVALID |
| request_job_sha256 | 요청 Job ID literal UTF8 SHA256 lower64hex 또는 잘못된 literal이면 null |
| request_binding_count | 유효 Job/request refs의1..64 또는 Job/ref invalid이면 null |
| capture_binding_count | RECORDED의1..64 또는 null |
| manifest_pin_count | RECORDED의1..64 또는 null |
| expected_bindings_sha256 | RECORDED의 canonical binding 배열 SHA256 또는 null |
| stored_binding_integrity_match | RECORDED에서만 true |
| issues | 최대1개 exact {code,input_index} |
| execution_authorized | false |
| ready_for_execution | false |
| ready_for_training | false |
| scientific_approval | false |
| acl_verified | false |
| registry_verified | false |
| training_authorized | false |
| pixels_verified | false |
| toc_tou_protected | false |
| executor_connected | false |
| artifact_bytes_verified | false |
| manifest_bytes_verified | false |
| current_files_revalidated | false |
| executor_bindings_compared | false |

request_job_sha256는 유효 요청 literal이면 **모든 상태에서 동일한 요청 hash**다. 다른 값으로 정규화·trim하지 않는다. 잘못된 요청 literal은 DB 조회0으로 INVALID·hash null을 반환한다. UI는 ASCII `[A-Za-z0-9_-]`1..200의 명시적 좁은 지원 범위를 사용하므로 UI 지원 입력에서 null hash는 허용하지 않는다.

| 상태 | request count | capture/pin count·binding hash | issues |
|---|---|---|---|
| RECORDED |1..64 | 세 count가 같고 hash 있음 | [] |
| UNAVAILABLE |1..64 | 모두 null |78 안전 issue1개 |
| LEGACY |1..64 | 모두 null | LEGACY_CAPTURE_NOT_RECORDED / index null |
| INVALID + STORED_JOB_INVALID | null | 모두 null | 해당 코드 / index null |
| INVALID + STORED_CAPTURE_INVALID |1..64 | 모두 null | 해당 코드 / index null |

미기록 capture count를0으로 추정하지 않는다. 저장 capture 자체가 valid여도 현재 Registry의 진실성·현재 바이트 불변 또는 실제 executor 일치를 뜻하지 않는다. stored_binding_integrity_match는 **저장 선언의 내부 일치**만 뜻하며 모든14개 승인/현재검증 flags는 그대로 false다.

UNAVAILABLE code allowlist는 CAPTURE_UNAVAILABLE, CAPTURE_TIME_INVALID, CAPTURE_ROWS_UNAVAILABLE, CAPTURE_ROW_UNAVAILABLE, CAPTURE_BINDING_INVALID, CAPTURE_BOUNDARY_FAILURE다. CAPTURE_ROW_UNAVAILABLE만 exact int0..request_count-1 index를 가지며 나머지는 null이다. unknown code·index bool·extra issue key·빈 issues·복수 issues는 INVALID로 투영한다. 원 저장 오류 문구를 응답하지 않는다.

canonical binding digest는77의 Python json.dumps(sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':')) UTF8 바이트에 따른다. role/pin 존재·순서를 포함하지만 Job 신원을 포함한 전체 요청 digest나 RFC8785 보장은 아니다. Job 신원은 별도 linkage로 검사한다. request_job_sha256와 이 digest의 의미를 섞지 않는다.

## 오류·HTTP·인증

200 projection·고정404/503 오류는 `Cache-Control: no-store`를 반환한다. 원래 인증 dependency에서 발생한 인증 오류는 기존 정책을 따른다. 현재 endpoint는 GET만 지원하며 POST는405다.

```json
{"error":{"code":"JOB_NOT_FOUND","message":"Job was not found.","retryable":false}}
```

404는 저장 조회 KeyError에 해당한다. 다른 worker/store 오류는503이며 exact 본문은 다음과 같다.

```json
{"error":{"code":"RESOURCE_UNAVAILABLE","message":"Stored binding capture is unavailable.","retryable":false}}
```

오류에 Job ID·내부 예외·URI·절대 경로를 넣지 않는다. malformed 저장 Job/capture는404/503 대신200 INVALID로 구분한다. 추가 lock/등록/Job 갱신이나 legacy 역채움은 하지 않는다. 저장 객체 하나의 관측이며 파일·다중 레코드 OS 원자 snapshot/실행 전 TOCTOU 보호가 아니다.

## 시험과 인계

```powershell
$env:PYTHONPATH="$PWD\.runtime;$PWD\backend;$PWD\tests"
python -m unittest test_job_execution_binding_capture -v
```

관련 **14 PASS /0.594초 /종료0**, `evidence/integration/stored-binding-capture-related-20261017.log`. RECORDED schema/3계수/hash·14false/privacy, LEGACY와null capture 구별·malformedJob 우선, UNAVAILABLE null/awaretime, exact schema/typedfalse0·부분/issue 변조, rehash한 신원/role linkage, index/type/64ref·문자상한/cycle, 100만자/비교trap으로신원선검사, 입력 불변/무IO, worker1get/no-store·404/503 privacy·인증계승·잘못된literal DB0·OpenAPI/GETonly를 확인했다. 초기13개는 신원 선검사 회귀1개를 추가하기 전 이력이며 최종14개에 중복 합산하지 않는다.

독립 최종 시험도 **14 PASS /0.330초 /종료0**, `evidence/integration/job-execution-binding-capture-independent-20261017.log`다. 같은14개 재실행은 전체 회귀에 중복 합산하지 않는다. 독립 검토에서 추가 결함은 발견하지 않았다.

Root는 main 통합·실제 기존 legacy2건 HTTP 조회·전체 backend/프론트·보존·브라우저·운영/이해자료를 별도로 기록한다. 실제 운영 POST·새 Job 생성·Registry 쓰기·QA/학습은 하지 않는다. RECORDED 생성 및 변조 검증은 합성 입력 범위이며 실제 legacy 조회와 구분한다. UI80에는 exact field/count/hash/status/error·지원입력·false flags 계약을 직접 공유했다.


## Root 실제 서버·브라우저 적용 확인

실행 중 Vite5174와 API8002에서 기존 legacy Job을 명시 버튼으로 조회해 LEGACY·요청입력1·capture/manifest 기준수 미기록·미확인(null)을 확인했다. 입력만으로 결과를 생성하지 않으며 입력변경은 이전 표시를 지웠다. 없는Job404의 안전 메시지·선행공백ID 버튼비활성/자동trim없음·모델허브 뒤로/앞으로 복귀 시 Job입력과 결과초기화·Agent선택변경 결과제거·복귀후재조회 성공을 확인했다. 기본1449×1087 화면에서 문서/카드 가로넘침0, 관측콘솔error목록[]이다. 실제모바일/지연네트워크경합을 강제로 재현하지 않았으며 late응답·나머지3상태는합성시험범위다. 실제RECORDED 생성·현재파일검사·executor연결·학습승인은검증하지않았다.

근거: `evidence/integration/stored-binding-capture-live-ui-20261017.json`, `evidence/integration/stored-binding-capture-ui-desktop-20261017.jpg`. 실제API의기존2Job/원상태·input-resolution·없는404/긴literalINVALID8GET과catalog14전후불변은 `evidence/integration/stored-binding-capture-live-api-20261017.json`에 기록했다. 실제새JobPOST/역채움/QA·학습0이다.


최종 Root 전체 backend 회귀:819개/818 PASS/기존Windows symlink1 SKIP/394.315초/exit0. `evidence/integration/stored-binding-capture-full-tests-20261017.log`. 종료후보호141/불변코어39/catalog14SHA동일·기존허용main/AgentCenter만변경은 `evidence/integration/stored-binding-capture-live-integrity-20261017.json`에기록했다.
