# 83. 저장 binding pin과 현재 직접 입력의 비실행 preflight

## 2026-10-17 현재 직접 입력 수동 preflight API·UI companion (84/85)

`GET /v1/jobs/{job_id}/input-preflight`는83의 저장 근거·현재 직접 입력 integrity/quality/PUBLIC metadata·pin 대조 세 축을 수동 조회하는 내부 API다. 기존 `execution-input-binding` 저장 기록 조회와 Job Status/input-resolution 응답은 바꾸지 않는다. 83의 safe payload를 그대로 반환하고 개별 ID·URI·manifest pin·파일 경로·원문 예외를 노출하지 않는다.

worker 내부에서 단일 검사 semaphore를 획득하고 실제 작업 종료 시 해제한다. 요청 취소나 화면 표시 중단이 서버 파일 검사 취소를 뜻하지 않는다. 기존 인증을 상속하고 no-store를 적용한다. 잘못된 literal400, 없는 Job404, 중복 검사429(PREFLIGHT_BUSY/Retry-After1/retryable=true), 자원·잘못된 내부 응답503은 고정 안전 오류다. 동시 검사 수·refs/문자 상한은 전체 파일 byte/time/RAM 강제 상한과 다르다.

반환 계약은 타입·배열/코드 한도·Job literal SHA·15false·inner81·3축 상태를 교차검사한다. integrity 수는 실패 입력 index의 합집합, quality 관측 수는 metadata 미관측 실패 index의 합집합과 대조하며 quality passed는 관측 수·차단 코드와 양방향으로 일치해야 한다. 현재 capture가 RECORDED이면 모든 직접 입력의 integrity와 quality/access 관측이 존재해야 한다. 모순된 응답은 정상 판정으로 내보내지 않는다.

관련/독립 API13 PASS(3.779초/3.747초). 실제 API8002에서 legacy2 UNKNOWN/current NOT_RUN, missing404·긴/control literal400/no-store와 기존79/status/input-resolution6응답의 변경 전 동등성을 확인했다. 이번11GET과 이전 baseline6GET은 구별하며 catalog14행/Job 본문은 불변이다. MATCH·품질BLOCKED·취소중busy429/503은 합성 시험 범위이고 실제 executor·운영 Job POST·역채움·수집/QA학습은 없다. 근거: `evidence/integration/current-input-preflight-live-api-20261017.json`.

API 정확 계약·시험은 [문서84](84_current_input_preflight_api.md), 기존 카드에 독립 수동 버튼과 결과를 연결하는 UI의 최종 시험·실제 브라우저 근거는 [문서85](85_current_input_preflight_ui.md)를 따른다. 이번 조회의 MATCH는 입력 비교 관측일 뿐 실행·과학·기관 ACL·학습·배포/TOCTOU 승인이 아니다.

상태: **TESTED_SYNTHETIC / 실행·과학·학습 미승인**. `backend/app/stored_current_binding_preflight.py`의 `inspect_stored_current_binding_preflight(store,requested_job_id)`는 configured Store의 Job1조회 후 **저장 expected pin / 현재 직접 입력 진단 / binding 일치**를 분리한다. 외부 Job·expected·supplied·경로·time 인자는 없다. 기존 resolver/capture/guard/Store/API/UI는 수정하지 않는다.

## 흐름과 failclosed 조건

1.77 `_text`로 요청 literal을 선검사한다. invalid면 get0·BLOCKED다. 유효하면82와 같은 `store.get('gmais_jobs',id)`1회/안전 오류 분류를 수행한다.
2.79 projection으로 Job/Agent/Trace/request linkage와 저장 capture exact형식/hash를 검증한다. INVALID는 BLOCKED다. LEGACY 또는UNAVAILABLE은 UNKNOWN이며 **현재 resolver0**이다. 현재 Registry의 pin으로 과거 미기록을 채우지 않는다.
3.RECORDED만79 `_selected_request`의 bounded refs를 사용한다. optional URI도 exact str1..256/공백전용·control·surrogate 거부를 모든 ref에 먼저 적용한다. 한 ref라도 지원 밖이면 전체 current pass0이다. 원 저장 URI를 새 caller 경로로 대체하지 않는다.
4.검증한 bounded ref만 복사하고 내부 UTC timestamp를 생성하여 기존 `resolve_job_inputs_with_capture`를 **단일 pass** 호출한다. 같은 resolver 반환 record에서 current manifest pin을 캡처하며 비교 때문에 Registry를 추가 조회하지 않는다.
5.current resolution을 bounded typed 선검사한 뒤 기존 `job_snapshot._project_snapshot`으로 순수 재대조한다. current capture는79 `_capture`로 exact schema·Job/request linkage·canonical hash를 먼저 검증한다.
6.current RECORDED envelope만81의 supplied로 넣는다. 저장 expected는81이 검증한 Job 내부에서만 선택한다. current resolution이 BLOCKED이면 binding MATCH여도 전체 BLOCKED다. current resolution INTEGRITY_VERIFIED + current capture RECORDED + binding MATCH일 때만 전체 MATCH다.

current capture UNAVAILABLE/INVALID나 current resolution의 resource/형식 실패는 BLOCKED다. 현재 진단을 실행하지 않았거나 partial 실패한 것을 MATCH로 표시하지 않는다. quality/PUBLIC 진단과 과학/기관 ACL 승인은 별개다.

## current resolution 선검사

기존 resolver의 정확한 기본 키10개만 지원한다: schema_version,scope,status,input_integrity_verified,resolved,blockers,ready_for_execution,scientific_approval,network_requests,source_files_written. fixed schema1/scope INPUT_INTEGRITY_ONLY, ready/science isFalse, network/writes exact int0를 확인한다. boolFalse를0으로 받아들이지 않는다. scope/status는 exactstr/길이 선검사 뒤 enum 비교한다.

resolved는 exact list이며 bounded refs와 같은 길이1..64다. 각 entry의 필수 키는 input_index,integrity_verified,authorization_verified,status,blocker_codes,id,version,sha256이며 선택 quality_status/access_class만 허용한다. unknown/nested extra key를 제거하여 정상으로 바꾸지 않고 거부한다. raw authorization_verified는 **isFalse**여야 한다. 기존 snapshot projector가 boolTrue도 false로 재투영하므로 이 선검사가 허위 승인을 정상화하는 것을 막는다.

각 blocker_codes 배열은 기존 `_CODES` 개수 이하, 전체 blockers는64×코드개수 이하다. 모든 code는 exactstr/1..64자/기존 enum이며 index는 exactint/현재 refs 범위다. 각 entry 식별자/상태/quality/access 문자도 상한을 먼저 확인한다. 그 뒤에만 `_project_snapshot`을 호출한다. raw resolution을 복사한 다음 고정 extension/internalreview/evaluation_scope/time 필드를 덮어써 wrapper fixed 필드가 raw metadata에 의해 대체되지 않게 한다. 최종 projector가 원래 코드 순서/quality/PUBLIC 차단·integrity·status 정합을 확인한다.

## 정확한 safe 응답

```text
schema_version: 1
scope: STORED_TO_CURRENT_DIRECT_INPUT_PREFLIGHT_ONLY
status: MATCH | BLOCKED | UNKNOWN
store_status: INVALID_REQUEST | OBSERVED | NOT_FOUND | RESOURCE_UNAVAILABLE
store_read_attempted: bool
store_read_observed: bool
store_get_calls: exact int 0 | 1
request_job_sha256: lower64hex | null
stored_capture_status: RECORDED | UNAVAILABLE | LEGACY | INVALID | null
resolver_pass_calls: exact int 0 | 1
current_resolution_status: NOT_RUN | INTEGRITY_VERIFIED | BLOCKED | RESOURCE_UNAVAILABLE | INVALID
current_capture_status: NOT_RUN | RECORDED | UNAVAILABLE | INVALID
current_input_count: exact int 1..64 | null
current_integrity_verified_count: exact int 0..current_input_count | null
current_quality_public_observed_count: exact int 0..current_input_count | null
current_quality_public_diagnostics_passed: bool | null
current_blocker_count: exact int 0..64*len(_CODES) | null
current_blockers: bounded list[{code,input_index}]
binding_comparison: exact81 result | null
issues: list[0..1] of exact {code}
```

추가15개 flag는 모두 false다: execution_authorized,ready_for_execution,ready_for_training,scientific_approval,acl_verified,registry_verified,training_authorized,pixels_verified,toc_tou_protected,executor_connected,artifact_bytes_verified,manifest_bytes_verified,executor_bindings_compared,stored_job_origin_verified,transitive_lineage_verified.

유효 요청 literal이면 request_job_sha256는 조회 실패에도 유지한다. get 미수행/실패 때 stored_capture_status는null이다. get 성공 뒤 malformed Job도 OBSERVED지만 저장 상태 INVALID/전체BLOCKED다. current pass 미실행이면 current 계수/quality bool은null이며0으로 추정하지 않는다. current resolution이 유효해진 뒤 current capture가 실패해도 이미 관측한 current 계수/차단은 유지한다.

quality_public_observed_count는 **실제로 quality/access metadata가 존재한 entry만** 센다. diagnostics_passed는 전체 entry에 metadata가 있고 모두 VALIDATED/PUBLIC일 때만 true다. missing entry를 품질 양호로 추정하지 않는다. 이것은 Registry 진단의 관측이지 기관 ACL 승인·외부 과학 정답 인증이 아니다. current blockers는 기존 `_CODES`/index의 safe 사본이고 원 URI·asset 경로·manifest 본문·원문 예외는 반환하지 않는다.

current capture가 유효하면 binding_comparison에81의 배열 hash/안전 계수·safe code/index가 담긴다. current quality/ACL BLOCKED + binding MATCH도 전체BLOCKED다. 입력 id/version/asset SHA가 같더라도 current canonical manifest metadata와 digest가 바뀌면 저장 manifest pin과 달라 binding BLOCKED다. 이를 단순 자산 SHA 일치로 덮지 않는다.

전체 issues code는 INVALID_JOB_ID,JOB_NOT_FOUND,RESOURCE_UNAVAILABLE,STORED_JOB_INVALID,STORED_CAPTURE_INVALID,LEGACY_EXPECTED_BINDING_NOT_RECORDED,EXPECTED_BINDING_CAPTURE_UNAVAILABLE,STORED_URI_UNSUPPORTED,CURRENT_RESOLVER_RESOURCE_UNAVAILABLE,CURRENT_RESOLUTION_INVALID,CURRENT_CAPTURE_INVALID,CURRENT_CAPTURE_UNAVAILABLE,CURRENT_INPUT_DIAGNOSTICS_BLOCKED,CURRENT_BINDINGS_MISMATCH만 사용한다. 정상MATCH는 issues=[]다. inner81의 오류 code/index는 별도81 계약을 따른다.

## IO·예외·승인 한계

이 단위는 **IO0이 아니다**. configured Store Job get1과 기존 current resolver의 각 ref Registry/자산 hash·URI 검사가 실행된다. resolver_pass_calls=1은 registry get1이 아니라 기존 resolver 전체 pass1이라는 뜻이다. 비교/현재 pin 수집 때문에 추가 Registry 조회는 없다. 반면 inner81 comparison.database_calls=0/current_files_revalidated=false는 그 순수 비교 범위만 뜻한다.

top에 current_files_revalidated=false를 복사하지 않는다. 실제 direct resolver hash 관측과 '전 파일을 확인하지 않았다'는 flag의 혼동을 피하기 위해 top은 transitive_lineage_verified=false를 명시한다. top의12 공통 승인false도 직접 입력의 제한된 현재 integrity 관측을 부정하는 것이 아니라 전체 원본·현재/미래 바이트·권한·실행 인증을 부여하지 않는다는 의미다.

Store.get의 전체 JSON body 파싱과 기존 resolver artifact hash는 기존 동작 그대로다. 이 wrapper는 전체 body bounded parser/hard RAM·CPU·누적 IO·개별 파일 byte cap을 제공하지 않는다. 직접 request refs만 검사하며 manifest lineage의 전이 연결이나 전체 계보·소스 독립성·나지 class 조건·모델 readiness·배포/과학 gate를 검증하지 않는다. passed configured Store의 진실성·원자 snapshot/TOCTOU·실제 executor 전달 상태도 인증하지 않는다.

get/resolve 호출 경계에서만 sqlite3.Error/UnicodeError/OSError/TypeError/ValueError(JSON 파싱 포함)/OverflowError/RecursionError/MemoryError를 고정 안전 결과로 바꾼다. get KeyError는82와 같은 arity/exactstr/길이/값 선검사로 missing과 내부 resource를 구별한다. RuntimeError/AssertionError 같은 프로그래밍 오류와 KeyboardInterrupt/SystemExit 등 BaseException은 삼키지 않는다. current metadata의 알려진 형식 실패는 별도 INVALID로 표시하며 resolver resource와 섞지 않는다.

원 Job/Registry·asset/품질 파일·원장/lock·예약·정책/분할·모델은 변경하지 않는다. 등록/학습/수집/정산/재개·API/UI/executor 체인에 연결하지 않는다. 내부 preflight이므로 이번 직접 UI 변경·프론트/브라우저 검증은 없다.

## 합성 검증

```powershell
$env:PYTHONPATH="$PWD\.runtime;$PWD\backend;$PWD\tests"
python -m unittest test_stored_current_binding_preflight -v
```

관련 **12 PASS /4.402초 /종료0**, `evidence/integration/stored-current-binding-preflight-related-20261017.log`. TempStore의 pinMATCH/getJob1+각refresolve1·추가조회0, current canonical manifest metadata 재해시만 변한 경우 stored pin mismatch, 품질/제한 ACL 차단+bindingMATCH, asset bytes/저장URI 변조, partial missing, legacy/unavailable resolver0·invalid우선, URI 전체 선검사, get/resource/programmer/process 예외, exact raw10키/배열코드상한·authTrue·unknownnested·거대scope/status를 projector 이전거부, currentcapture invalid/unavailable, put/list/학습 trap·Job/Registry/asset 원문 불변/privacy/외부supplied인자 거부를 확인했다.

metadata 재해시 시험의 Registry 변경은 **격리 TempStore fixture에서의 synthetic current-record 변조 시뮬레이션**이다. 운영 불변 Registry의 버전을 수정하거나 허용한 것이 아니다. Root는 실제 기존 Job의 read-only metadata 관측·전체 회귀·보존·관련 문서/인계·이해자료를 별도로 연결하며 실자료 current RECORDED 또는 운영 MATCH를 임의 추정하지 않는다. 초기 반복12개는 최종12개나 전체 회귀에 중복 합산하지 않는다.

독립 최종 시험도 **12 PASS /3.119초 /종료0**, `evidence/integration/stored-current-binding-independent-20261017.log`다. authTrue/unknown entry/거대scope 선검사 보완 뒤의 최종 소스를 확인했으며 추가 결함은 발견하지 않았다. 같은12개 재실행은 전체 회귀 수에 중복 합산하지 않는다.

## Root 실제 legacy 관측

`evidence/integration/stored-current-binding-live-validation-20261017.json`과 `evidence/integration/stored-current-binding-live-check-20261017.py`는 read-only Store에서 기존 legacy2개가 UNKNOWN/current NOT_RUN이고, missing/invalid literal을 포함하여 get 총3회·resolver0/Registry get0임을 기록한다. 과거 pin 역채움0이며 catalog14행과 원 Job body는 불변이다. 실제 RECORDED의 current asset hash/MATCH는 이번 운영 관측이 아니며 합성 시험과 구분한다. API/운영 POST·수집/QA/학습은0이고 전체 backend 회귀는 Root가 별도로 실행 중이다.


## Root 최종 통합 검증과 인계

전체 backend 회귀는856개/855 PASS/기존 Windows symlink1 SKIP/343.921초/exit0이다. `evidence/integration/stored-current-binding-full-tests-20261017.log` 참조. 시험 후 보호141·기존 코어45·catalog14/원 Job 본문 SHA 동일과 기존 추적 code/data/tests/frontend 변경0은 `evidence/integration/stored-current-binding-live-integrity-20261017.json`에 기록했다. 실제 수집·QA/학습·executor·운영 Job POST·역채움은0이며 직접 API/UI 변경은 없다.

후속은 내부 GET input-preflight와 기존 카드의 독립 수동 현재 검증 버튼/3축 결과를 같은 단위로 연결하는 계획이다. 기존 stored 조회 계약을 바꾸지 않고 동시 worker1·인증/no-store·안전 오류·literal 요청 SHA·늦은 응답/뒤로가기 무효화를 검증할 예정이다. 파일 검사 비용과 한도를 명시하며 MATCH를 실행 승인으로 표시하지 않는다. 현재 후속 코드와 실제 Workflow/executor 연결은0이다.
