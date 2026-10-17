# 78. 제출 시 고정 입력 binding의 선택 캡처

## 2026-10-17 저장·현재 직접 입력의 비실행 preflight (83)

`inspect_stored_current_binding_preflight(store,requested_job_id)`는 저장된 제출 manifest pin과 같은 참조를 현재 resolver가 검증한 pin을 연결한다. 외부 expected/supplied/경로를 받지 않는다. 저장 capture가 RECORDED인 경우만 기존 resolver/capture의 단일 pass를 실행하고, 그 pass의 현재 envelope를81 비교 함수에 전달한다. 비교 때문에 추가 Registry 조회를 하지 않는다. legacy/unavailable은 resolver0·UNKNOWN으로 남겨 과거 pin을 소급 생성하지 않는다.

저장 근거·현재 integrity/quality/PUBLIC metadata 진단·pin 선언 일치의 세 축을 구분한다. 현재 metadata와 canonical digest가 함께 바뀌면 id/version/assetSHA가 같아도 저장 pin과 달라 차단된다. 품질·제한자료 차단은 pin 일치만으로 해제하지 않는다. 현재 resolver 응답의 크기·타입·enum·authorization_false를 snapshot projection보다 먼저 검사해 잘못된 권한 표시를 정상화하지 않는다.

이 단계는 실제 로컬 asset hash·Registry 읽기가 있을 수 있어 I/O0이 아니다. inner81의 DB0/current_files_revalidated=false는 순수 비교 범위다. top은 직접 입력 진단 관측과 전체 원본/전이 계보·기관 ACL·과학·학습·배포·executor·TOCTOU 승인을 구분한다. 새 top에 current_files_revalidated를 복사하지 않고 transitive_lineage_verified=false를 명시한다. 전체 body 파싱·파일 hash의 강제 메모리/개별 byte 상한을 제공하지 않는다.

관련12 PASS4.402초·독립12 PASS3.119초. 현재 pin 변조/품질·접근 차단의 양성·음성 검증은 격리 TempStore와 작은 로컬 시험 자산으로 수행했으며 운영 Registry를 변경한 것이 아니다. 실제 기존 legacy2는 UNKNOWN/current NOT_RUN, missing/invalid를 포함get3·resolver0/Registryget0·catalog14/Job 본문 불변이었다. 실제 current RECORDED/MATCH 또는 executor 전달 관측을 주장하지 않는다. 정확 계약·오류·시험은 [문서83](83_stored_current_binding_preflight.md), 실제 읽기 근거는 `evidence/integration/stored-current-binding-live-validation-20261017.json`을 따른다. 공개 API/UI/Workflow/executor에는 미연결이므로 기존79/80 화면·응답은 바꾸지 않는다.

## 2026-10-17 저장 expected·supplied 순수 handoff 대조 (81)

`compare_stored_job_binding_handoff(job,requested_job_id,supplied_envelope)`는 저장 Job/capture의79 형식·신원·hash 검증과77의 ordered binding 대조를 연결하는 내부 순수 함수다. 별도 caller expected 인자를 받지 않으며 RECORDED 저장 envelope만 expected로 사용한다. 잘못된 supplied/저장 Job·capture/신원·순서·role·pin 불일치는 BLOCKED가 우선한다. 유효 legacy/unavailable에서도 저장 request와 supplied의 눈에 보이는 연결을 검사하며, 그 연결은 같고 expected pin만 미기록이면 UNKNOWN이다. supplied나 현재 Registry로 과거 expected를 역채우지 않는다.

응답은 안전한 상태·계수·집계 배열 hash와 code/index만 제공한다. 12승인 및 current_files_revalidated/executor_bindings_compared/stored_job_origin_verified는 모두 false, 함수 자체의7IO계수는0이다. passed Job이 실제 저장소에서 왔는지 또는 supplied가 실제 실행자에서 수집됐는지 인증하지 않으며 caller가 양쪽 객체를 구성해 MATCH를 만들 수도 있다. 현재 파일·기관 ACL·TOCTOU/동시변조 원자성·학습준비/과학적 성능을 입증하지 않는다.

관련/독립 신규13 PASS(0.057초/0.056초), 실제 기존 legacy2의 선택 저장 선언을 로컬 supplied로 복사한8경우 UNKNOWN4/BLOCKED4·catalog14/Jobbody불변을 확인했다. 실제 executor 관측/생성된 production MATCH는 아니다. `evidence/integration/stored-binding-handoff-live-validation-20261017.json` 참조. 정확 결과 계약·safe enum·한계·시험은 [문서81](81_stored_job_binding_handoff.md)을 따른다. API/UI/executor/DB에는 미연결인 내부 단위이므로 기존79/80 공개 응답·카드·승인 gate는 그대로이며 직접 프론트/브라우저 재시험은 하지 않는다.

## 2026-10-17 저장 제출 binding 조회 companion (79/80)

`GET /v1/jobs/{job_id}/execution-input-binding`은 저장 Job 1건에서 제출 당시 별도 capture를 안전하게 투영하는 내부 RFC다. 기존 Job Status·input-resolution·현재 계보 API와 구별한다. 현재 Registry·파일·실행자의 입력을 재검사하거나 과거 Job에 capture를 역채우지 않는다. 응답은 RECORDED/UNAVAILABLE/LEGACY/INVALID와 request_job_sha256·안전한 입력/핀 계수·전체 binding 집계 SHA만 제공하고 개별 ID·역할·manifest pin·URI/경로·원문/예외를 반환하지 않는다. 12개 승인 및 현재파일 재검증/실행자 대조는 모두 false다.

한도·타입·Job/Agent/Trace 및 요청 참조 순서/역할 presence·canonical digest를 대조한다. 손상된 Job은 capture 부재보다 우선 INVALID이며, 미기록 null을 0개로 바꾸지 않는다. 단일 store.get을 threadpool에서 수행하고 no-store·기존 인증을 상속한다. 고정 404 JOB_NOT_FOUND / 503 RESOURCE_UNAVAILABLE 오류는 비재시도 선언이며 내부 예외를 노출하지 않는다.

실제 API8002의 기존 legacy Job2건은 LEGACY, 원상태 응답과 동일하고 catalog14행 전후 SHA 불변이다. 추가 없는 Job404 및 257자 요청 INVALID를 포함8GET만 수행했으며 실제 새 Job POST/소급 capture/실행0이다. 근거: `evidence/integration/stored-binding-capture-live-api-20261017.json`. RECORDED 생성은 합성시험 범위이고 운영 환경 관측으로 표현하지 않는다. 수동 UI·실제 브라우저/최종 회귀 검증 결과는 [문서79](79_stored_binding_capture_api.md)·[문서80](80_stored_binding_capture_ui.md)에 기록한다. upstream 확정 표준/학습 준비/과학·기관 권한 승인이 아니다.

상태: **TESTED_SYNTHETIC / 내부 RFC / 실제 executor 미연결**. 새 Job을 제출할 때 기존 입력 점검과 같은 pass에서 얻은 고정 manifest pin을 별도 메타데이터 extension으로 저장한다. 이전 Job이나 멱등 재요청에는 역채우지 않는다. 기존 HTTP 오류·Job Status·input_resolution·upstream schema·모델 gate는 유지한다.

## 구현과 호출

`backend/app/job_inputs.py`는 기존 루프를 `_resolve_job_inputs(store,input_refs,capture_rows=None)`로 분리했다. 기존 `resolve_job_inputs(store,input_refs)`는 capture 없이 동일 결과를 반환한다. 추가 호출은 다음과 같다.

```python
resolution, capture = resolve_job_inputs_with_capture(
    store, refs, job_id=job_id, agent_id=agent_id,
    trace_id=trace_id, captured_at=stamp,
)
```

새 pair는 기존 resolve pass를 **한 번만** 실행한다. `resolve_version`이 검증하여 반환한 동일 record의 `manifest_sha256`와 동일 local ref snapshot의 id/version/asset SHA/optional role/index만 수집한다. 현재 Registry를 추가 조회하거나 자산을 다시 hash하지 않는다. `backend/app/execution_binding_capture.py`의 `build_submission_binding_capture`는 선택 메타데이터를 받는 순수 builder다.

Root가 소유한 `gmais_api.py` 통합은 새 Job 제출 분기에서 pair를 호출하고 기존 resolution을 그대로 input_resolution에 포함한다. 별도 `execution_input_binding_capture`만 동일 Job 레코드의 같은 `store.put`에 추가한다. 기존 멱등 분기는 이 호출보다 먼저 반환하므로 재조회/추가 검증/역채움이 없다. workflow validation이나 다른 기존 resolver 호출은 capture를 요청하지 않는다.

## 메타데이터 캡처 가능 조건

capture만 exact list1..64를 지원하며 문자열·고정 version·64lowerhex SHA·순서/index·동일 identity 충돌 검증은 77의 순수 `compare_execution_input_bindings(envelope,envelope)`를 재사용한다. 모든 manifest pin이 명시되어 selfcompare MATCH인 경우만 RECORDED다. role 부재는 부재 그대로 유지한다.

기존 resolution entry의 integrity_verified가 true면 quality RAW/REJECTED 또는 제한 ACL 때문에 resolution이 BLOCKED여도 선언 pin을 캡처할 수 있다. 이는 **quality/ACL/실행 승인과 다른 메타데이터 기록**이다. URI 불일치, 같은 identity의 상충 자산 SHA, resolve 실패, 일부 row 누락·잘못된 pin/index/상한이면 전체 UNAVAILABLE이며 부분 expected_envelope/hash를 제공하지 않는다. 다른 성공 row의 pin을 실패/미기록 row로 전파하지 않는다.

64개/256자 상한은 optional capture만의 지원 범위다. 기존 resolver는 이전과 같은 schema/반복·IO·예외 계약을 유지하며 이 변경이 전체 resolver의 IO/RAM/CPU hard cap을 제공하지 않는다. capture가 지원 범위 밖이어도 기존 resolver의 장문/다수 ref 진단을 생략하지 않는다.

## 저장 extension 계약

```text
schema_version: 1
extension: greenblue.execution-input-binding-capture.rfc1
approval_status: INTERNAL_REVIEW
scope: SUBMISSION_EXPECTED_BINDING_METADATA
captured_at: bounded timezone ISO datetime string | null
status: RECORDED | UNAVAILABLE
expected_envelope: {job_id,agent_id,trace_id,bindings} | null
expected_bindings_sha256: lowercase64hex | null
issues: list[{code,input_index}]
pin_source: SAME_RESOLVE_VERSION_RETURN
additional_registry_queries: 0
additional_artifact_reads: 0
additional_database_writes: 0
```

RECORDED의 expected_envelope는77 계약과 동일하다. binding은 input_index/id/version/sha256/manifest_sha256 및 선택 role만 포함한다. expected_bindings_sha256는 canonical **bindings 배열만**의 digest이며 Job/Agent/Trace 전체 요청 hash가 아니다. pin 자체는 같은 resolver pass가 반환한 record의 메타데이터 snapshot이다. 현재/미래 파일·권한 또는 executor 전달 상태를 인증하지 않는다.

UNAVAILABLE이면 expected_envelope/hash는 둘 다 null이고 안전한 code/index만 남는다. 잘못된 captured_at 또는 optional import/builder 경계 실패에는 시간도 null일 수 있다. 원문 예외/URI·자산 경로·manifest 본문·품질 보고서 경로를 저장하지 않는다. expected envelope에는 내부 신원과 고정 pin을 의도적으로 저장하지만 공개 HTTP 응답이나 Job Status에 추가하지 않는다.

12개 필드는 모두 false다: execution_authorized, ready_for_execution, ready_for_training, scientific_approval, acl_verified, registry_verified, training_authorized, pixels_verified, toc_tou_protected, executor_connected, artifact_bytes_verified, manifest_bytes_verified. 이는 캡처가 해당 승인을 부여하지 않는다는 뜻이며 원래 resolver의 자산 SHA 점검이 실행되지 않았다는 뜻은 아니다.

`additional_* = 0`은 **capture 때문에 추가된 IO**만 뜻한다. pair가 수행하는 원래 resolver pass는 기존 Registry/자산/URI 검사를 수행한다. builder 자체는 순수하지만 전체 pair를 IO0이라고 표현하지 않는다. Job 저장 쓰기2회(Job+멱등 레코드)는 기존과 같으며 capture 전용 DB 쓰기는 없다.

## 오류 격리와 불변성

optional sink에서 선택 메타데이터를 복사하는 실패와 optional module import/builder 실패만 Exception 경계로 격리한다. 실패해도 기존 resolution/HTTP/Job Status/차단 순서를 바꾸지 않고 UNAVAILABLE을 저장한다. 기존 resolve pass는 이 경계 밖에 있으므로 기존에 전파되던 RuntimeError 등 예외를 새로 삼키지 않는다. KeyboardInterrupt/SystemExit도 삼키지 않는다.

입력 ref는 기존 resolver가 사용하는 deep copy snapshot에서 선택하며 원래 caller 객체를 변경하지 않는다. 반환 capture의 scalar binding과 기존 resolution/Registry 객체는 분리된다. 선택 builder가 rows를 변경한 뒤 예외를 내도 기존 resolution을 변경하지 않는다. 전체 데이터셋 원본·원장·lock·분할·모델은 수정하지 않는다.

## 시험 근거

```powershell
$env:PYTHONPATH="$PWD\.runtime;$PWD\backend;$PWD\tests"
python -m unittest test_execution_binding_capture test_job_inputs test_job_input_snapshot test_gmais_api -v
```

관련 **50 PASS /15.440초 /종료0**: 신규16개와 기존34개다. 로그는 `evidence/integration/submission-binding-capture-related-20261017.log`다. 새16개는 samepass resolve 호출 수·canonical manifest pin/asset SHA 구분, old wrapper 호환, 제한 ACL/quality BLOCKED 캡처와 승인false, partial/URI/상충/실패 wholeUNAVAILABLE, capture만 상한, 순서/role absent/다른 버전, caller/record/결과 분리, mutate-then-raise와 import 실패 격리, process exit/원래 예외 전파, 잘못된 pin/신원/time/타입, pure 무IO, 원본 bytes/no-write/no-path-leak, TempStore API 같은 Job 저장·HTTP/Status 동일·멱등/legacy 재캡처0을 검사한다.

API failure 비교 fixture의 첫 실행에서는 Store.created_at 시각 차이로 동등 assertion이 실패하여 uuid/API stamp와 함께 store.now도 고정했다. 이는 생산 응답 변경이나 capture 결함 재현이 아니다. 기존 FastAPI TestClient의 httpx deprecation 경고는 남으며 의존성 설치/변경은 하지 않았다. 반복 실행/기존34개는 Root 전체 회귀 수에 중복 합산하지 않는다.

독립 신규 시험도 **16 PASS /6.243초 /종료0**이며 `evidence/integration/submission-binding-capture-independent-20261017.log`에 기록했다. 같은16개 재실행이므로 관련50개에 합산하지 않는다. 독립 검토에서 추가 결함은 발견하지 않았다.

Root의 독립 before/after 호환 근거는 PUBLIC/RESTRICTED 등록 및 미등록 세 TempStore 사례의 전체 응답·기존 resolver·새 extension 제외 Job·멱등 replay·resolve1/put2를 대조한다. 실제 운영 API 제출은 수행하지 않았다. 기존 실제 legacy Job은 읽기 검증만 하며 새 extension을 역채우지 않는다. 운영 원본 보존·전체 회귀·이해자료·인계는 Root가 별도 연결한다.

## 다음 경계

제출 시 expected snapshot 기록은 구현했지만 실제 executor에 전달된 supplied capture와 실행 전77 대조 연결은 아직 없다. 같은 source pin 기록이 모델 readiness·과학 독립성·기관 ACL·파일 TOCTOU·실행/학습 gate를 해제하지 않는다. 공개 API/UI 응답에 새 필드가 없고 내부 Job 저장만 확장하므로 이번 직접 UI 변경·브라우저 시험은 없다. 후속 조회/노출에는 별도 안전 projection 계약이 필요하다.


## Root 호환 및 실제 legacy 조회

`submission-binding-capture-compat-before-20261017.json`과 `-compat-after-20261017.json` 및 `-compat-runner-20261017.py`는 고정uuid/API stamp/store.now의TempStore3경우(PUBLIC/RESTRICTED등록·미등록)를대조했다. 기존resolver·전체HTTP·새capture만제외한storedJob·resolve각1/put2·멱등재조회/쓰기0이동일했다. 이합성대조는관련50건/독립16건/전체회귀와중복합산하지않는다.

실제API8002의기존legacyJob2건에GET상태/입력snapshot각1회(총4GET)만수행했다. status원문BLOCKED동일·LEGACY_SNAPSHOT_NOT_RECORDED availablefalse·capture미기록유지·catalog14행과Jobbody전후동일이다. `evidence/integration/submission-binding-capture-live-legacy-20261017.json`이근거다. 운영POST/새운영capture생성/실제executor/학습0이며새RECORDED/UNAVAILABLE생성은TempStore검증범위다. 최종전체backend회귀는805개중804 PASS·기존Windows symlink제약1 SKIP /327.813초/exit0이다. submission-binding-capture-full-tests-20261017.log가근거이며관련50/독립16/TempStore3대조·실제GET4는전체건수에중복합산하지않는다.


## 최종 보존·문서와 다음 경계

전체시험종료후보호141참조/기존불변코어36 SHA·catalog14행 canonical SHA/기존Jobbody불변을다시확인했다. 직전추적backend/scripts/tests/data/frontend중변경은승인한job_inputs.py/gmais_api.py2개뿐이다. 새구현/증거·문서를추가했으므로전체workspace/OS원자snapshot불변보장은아니다. `submission-binding-capture-live-integrity-20261017.json`과 `-runtime-20261017.json`을따른다. 원본·분할·모델·원장/lock·예약및후보차단4건은유지된다. 이해에이전트가완료코드·최종시험·합성생성과실제legacy조회범위로설명/발표대본·FAQ·INDEX·변경이력을갱신했다. 최종문서감사·snapshot rawSHA/크기대조는 `submission-binding-capture-closeout-20261017.json`에기록한다.

다음79는저장capture의exact형식·hash·Job/request연결만확인하는safeprojection/API와같은단위의수동UI연결을PLANNED로검토했다. raw식별자/manifestpin/URI/경로를노출하지않고RECORDED/UNAVAILABLE/LEGACY/INVALID를구분한다. RECORDED시간은aware ISO이고합법UNAVAILABLE fallback은null일수있다. 현재Registry/byte인증·실제executor대조·실행승인은범위밖이며현재79코드는없다.
