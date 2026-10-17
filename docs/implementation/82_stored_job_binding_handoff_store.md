# 82. configured Store 단일조회 handoff adapter

## 2026-10-17 저장·현재 직접 입력의 비실행 preflight (83)

`inspect_stored_current_binding_preflight(store,requested_job_id)`는 저장된 제출 manifest pin과 같은 참조를 현재 resolver가 검증한 pin을 연결한다. 외부 expected/supplied/경로를 받지 않는다. 저장 capture가 RECORDED인 경우만 기존 resolver/capture의 단일 pass를 실행하고, 그 pass의 현재 envelope를81 비교 함수에 전달한다. 비교 때문에 추가 Registry 조회를 하지 않는다. legacy/unavailable은 resolver0·UNKNOWN으로 남겨 과거 pin을 소급 생성하지 않는다.

저장 근거·현재 integrity/quality/PUBLIC metadata 진단·pin 선언 일치의 세 축을 구분한다. 현재 metadata와 canonical digest가 함께 바뀌면 id/version/assetSHA가 같아도 저장 pin과 달라 차단된다. 품질·제한자료 차단은 pin 일치만으로 해제하지 않는다. 현재 resolver 응답의 크기·타입·enum·authorization_false를 snapshot projection보다 먼저 검사해 잘못된 권한 표시를 정상화하지 않는다.

이 단계는 실제 로컬 asset hash·Registry 읽기가 있을 수 있어 I/O0이 아니다. inner81의 DB0/current_files_revalidated=false는 순수 비교 범위다. top은 직접 입력 진단 관측과 전체 원본/전이 계보·기관 ACL·과학·학습·배포·executor·TOCTOU 승인을 구분한다. 새 top에 current_files_revalidated를 복사하지 않고 transitive_lineage_verified=false를 명시한다. 전체 body 파싱·파일 hash의 강제 메모리/개별 byte 상한을 제공하지 않는다.

관련12 PASS4.402초·독립12 PASS3.119초. 현재 pin 변조/품질·접근 차단의 양성·음성 검증은 격리 TempStore와 작은 로컬 시험 자산으로 수행했으며 운영 Registry를 변경한 것이 아니다. 실제 기존 legacy2는 UNKNOWN/current NOT_RUN, missing/invalid를 포함get3·resolver0/Registryget0·catalog14/Job 본문 불변이었다. 실제 current RECORDED/MATCH 또는 executor 전달 관측을 주장하지 않는다. 정확 계약·오류·시험은 [문서83](83_stored_current_binding_preflight.md), 실제 읽기 근거는 `evidence/integration/stored-current-binding-live-validation-20261017.json`을 따른다. 공개 API/UI/Workflow/executor에는 미연결이므로 기존79/80 화면·응답은 바꾸지 않는다.

상태: **TESTED_SYNTHETIC(합성 저장 capture) + VERIFIED_REAL(기존 Store.get을 사용한 실카탈로그 readonly legacy 조회) / 실제 executor 미연결**. `backend/app/stored_job_binding_handoff_store.py`의 `inspect_stored_job_binding_handoff(store,requested_job_id,supplied_envelope)`는 configured Store에서 Job을 한 번 읽어81 순수 대조를 호출한다. caller가 Job/expected를 직접 인자로 넣는 경로는 없다. Store 조회 관측과 stored binding 대조 결과를 서로 다른 필드에 기록한다.

## 입력·흐름

```python
result = inspect_stored_job_binding_handoff(store, requested_job_id, supplied_envelope)
```

요청 Job ID literal을77의 exact str1..256/비공백/control·surrogate 거부 계약으로 먼저 확인한다. 잘못된 literal이면 Store.get0이며 request hash=null이다. 유효 literal이면 supplied 형식이 틀려도 `store.get('gmais_jobs',requested_job_id)`를 정확히1회 시도한다. get 결과를 얻은 뒤81 `compare_stored_job_binding_handoff`를 재사용한다. 추가 list/put/Registry/resolver/원본 자산/학습 호출은 없다.

유효 get 반환이 malformed Job 또는 None/배열이어도 **Store 반환 관측은 성공**했으므로 OBSERVED/store_read_observed=true다. 내부 comparison은81에 의해 BLOCKED다. 조회 실패를 binding 불일치로 표현하거나, malformed Job을 미등록 Job으로 바꾸지 않는다. 공급된 Store 자체의 구현·정체·신뢰성을 이 adapter가 인증하지 않는다.

## 정확한 wrapper 응답

```text
schema_version: 1
scope: CONFIGURED_STORE_BINDING_HANDOFF_ONLY
store_status: INVALID_REQUEST | OBSERVED | NOT_FOUND | RESOURCE_UNAVAILABLE
request_job_sha256: lower64hex | null
store_read_attempted: bool
store_read_observed: bool
store_get_calls: exact int 0 | 1
comparison: exact81 result | null
issues: list[0..1] of exact {code}
```

여기에81과 같은15개 false flag만 추가된다: execution_authorized, ready_for_execution, ready_for_training, scientific_approval, acl_verified, registry_verified, training_authorized, pixels_verified, toc_tou_protected, executor_connected, artifact_bytes_verified, manifest_bytes_verified, current_files_revalidated, executor_bindings_compared, stored_job_origin_verified.

| store_status | attempted | observed | calls | comparison | issue |
|---|---|---|---:|---|---|
| INVALID_REQUEST | false | false |0 | null | INVALID_JOB_ID |
| OBSERVED | true | true |1 |81 MATCH/BLOCKED/UNKNOWN | [] |
| NOT_FOUND | true | false |1 | null | JOB_NOT_FOUND |
| RESOURCE_UNAVAILABLE | true | false |1 | null | RESOURCE_UNAVAILABLE |

request_job_sha256는 유효 literal의 UTF8 SHA다. 조회 실패에도 유효 요청 hash를 유지한다. raw Job/Agent/Trace/Dataset ID·role·manifest pin·URI/경로/예외는 wrapper나 내부 비교에 노출하지 않는다. wrapper issues는 index/원문 예외 없이 위 세 code만 사용한다. comparison 내부 safe code/index·hash/count는81 계약을 그대로 따른다.

`store_get_calls=1`은 adapter가 구성 Store의 get을 한 번 호출 시도했다는 의미다. Store 내부 SQL 실행 횟수·파일 read 횟수와 같다고 주장하지 않는다. **wrapper Store 조회1과 내부 순수 comparison.database_calls=0은 서로 다른 scope**다. 후자의0을 전체 adapter IO0이라고 표현하면 안 된다. observed=true도 stored_job_origin_verified를 true로 바꾸지 않는다.

## 누락·자원 오류·전파 경계

현재 기존 Store.get은 누락 시 `KeyError(identifier)`를 내므로 args가 정확히1개이고 exact str·길이가 validated 요청 literal과 같고 값까지 같을 때만 NOT_FOUND다. args 개수/타입/길이를 값 비교보다 먼저 확인하여 nested/custom equality·거대 문자열을 안전하게 분류한다. 다른 내부 KeyError는 RESOURCE_UNAVAILABLE로 반환한다. 오류 메시지 문자열을 해석하지 않는다.

get 경계의 sqlite3.Error, UnicodeError, OSError, TypeError, ValueError(JSONDecodeError 포함), OverflowError, RecursionError, MemoryError만 고정 RESOURCE_UNAVAILABLE로 변환한다. 오류 원문/traceback을 결과에 넣지 않는다. 이는 예상 자원/파싱 오류를 안전하게 분리하는 계약이며 메모리 부족에서 무조건 응답할 수 있다는 OS/RAM 보장은 아니다.

RuntimeError·AssertionError 같은 예상 밖 프로그래밍 오류와 KeyboardInterrupt/SystemExit/다른 BaseException은 그대로 전파한다. catch는 **get 호출만** 감싸며81 comparison이 발생시키는 오류를 저장소 오류로 덮지 않는다. 비교 자체의 ValueError를 주입하면 wrapper가 RESOURCE_UNAVAILABLE을 반환하지 않고 전파하는 시험을 포함한다.

## 읽기·출처·동시성 한계

기존 Store.get은 SQLite body 전체를 가져와 json.loads한다. 이 단위는 Store/parser를 수정하지 않으며 DB body 크기/깊이의 사전 bounded parsing·전체 IO/RAM/CPU hard cap을 제공하지 않는다. 77/79/81의 선택 메타데이터 상한은 JSON body가 이미 읽힌 뒤의 비교 범위다. root 구성·저장소 연결의 신뢰성·원자 다중파일 snapshot·실행 전 TOCTOU·현재 원본 바이트/manifest 진실성·기관 ACL·과학/학습 승인은 검증하지 않는다.

실제 executor supplied capture와 실행 체인/API/UI에는 아직 연결하지 않았다. supplied는 caller 선언이며 일치 MATCH도 실제 executor 대조가 아니다. 이전 Job의 누락 pin을 현재 Registry로 채우거나 Job을 갱신하지 않는다. 원본·원장/lock·예약·분할·모델·Registry 쓰기는 없다.

## 합성 시험과 인계

```powershell
$env:PYTHONPATH="$PWD\.runtime;$PWD\backend;$PWD\tests"
python -m unittest test_stored_job_binding_handoff_store -v
```

관련 **12 PASS /1.416초 /종료0**, `evidence/integration/stored-binding-store-adapter-related-20261017.log`. TempStore에 실제 fixture를 put한 뒤 get1/inner MATCH·wrapper/inner15false·scope/IO계수분리, fake Store 관측≠출처 인증, invalidliteral get0, 잘못된 supplied도get1/81BLOCKED, malformed 반환 OBSERVED, 실제 missing·KeyError arity/type/거대값/custom-equality, 예상 자원/JSON 오류 safe결과, 프로그래밍/process예외 전파, comparison오류분리, legacy/unavailable UNKNOWN과Trace변조BLOCKED, put/list/Registry/resolver/학습/원본파일 trap·원 body불변·caller 입력 불변/privacy/Job·expected 주입거부를 확인했다.

fixture setup의 TempStore 생성/put은 합성 준비 작업이고 adapter의 쓰기가 아니다. 기존 TestClient fixture import에서 나타나는 httpx deprecation 경고는 의존성 변경 없이 유지한다. 초기 반복12개는 최종12개에 중복 합산하지 않는다. Root가 실제 저장소의 읽기전용 연결 subclass(기존 Store.get 재사용·Store 생성자DDL 없이), 전체 회귀·보존·운영/이해자료를 별도로 검증한다. 이 단위는 새 API/UI/CLI 없는 내부 adapter이므로 직접 화면 변경·프론트/브라우저 시험은 없다. 기존44 코어는 변경하지 않는다.

독립 최종 시험도 **12 PASS /1.084초 /종료0**, `evidence/integration/stored-binding-store-adapter-independent-20261017.log`다. 같은12개 재실행은 전체 회귀에 중복 합산하지 않는다. 독립 검토에서 추가 결함은 발견하지 않았다.

## Root 실제 저장 읽기 관측

Root는 Store 생성자/DDL 없이 read-only SQLite connection subclass에서 기존 Store.get을 재사용했다. `evidence/integration/stored-binding-store-adapter-live-validation-20261017.json`과 `evidence/integration/stored-binding-store-adapter-live-check-20261017.py`에 기존 legacy2개의 로컬 선언 replay8건 UNKNOWN4/BLOCKED4, missing NOT_FOUND/get1, invalid literal/get0를 기록했다. adapter get은 총9회이며 catalog14행과 원 Job body는 전후 불변이다. supplied는 실제 executor capture가 아니고 운영 MATCH는 관측하지 않았다. API/운영 POST·QA/학습은0이다. 전체 backend 회귀는 Root가 별도 실행하며 이 문서에 미완료 결과를 선기입하지 않는다.


## Root 최종 통합 검증과 후속

전체 backend 회귀는844개/843 PASS/기존 Windows symlink1 SKIP/342.991초/exit0이다. `evidence/integration/stored-binding-store-adapter-full-tests-20261017.log` 참조. 시험 후 보호141·기존 코어44·catalog14/원 Job 본문 SHA 동일과 기존 추적 code/data/tests/frontend 변경0은 `evidence/integration/stored-binding-store-adapter-live-integrity-20261017.json`에 기록했다. 실제 executor·운영 Job POST·역채움·QA/학습은 없고, 직접 API/UI 변경도 없다.

다음은 저장 제출 manifest pin과 현재 resolver 검증 pin을 연결하는 내부 비실행 preflight로 PLANNED다. 저장 근거·현재 integrity/quality/PUBLIC 진단·선언 일치를 분리하고, 현재 입력 차단은 pin 일치만으로 해제하지 않는다. legacy의 과거 pin은 소급 생성하지 않는다. 기존 resolver가 수행하는 Registry/파일 읽기를 IO0 또는 hardRAM/per-file cap으로 표현하지 않는다. 현재 후속 구현과 API/UI/Workflow/executor 연결은0이다.
