# 84. 명시적 현재 직접 입력 preflight API

상태: **TESTED_SYNTHETIC / 실행·학습 미승인**. 신규 `backend/app/stored_current_binding_preflight_api.py`는83의 결과를 엄격 검증하여 GET으로 제공한다. 200 응답은 **83 payload 그대로**이며 API extension wrapper를 추가하지 않는다. 기존79 저장 capture GET/payload는 변경하지 않는다. Root가 main.py import/include만 연결하고 UI85가 별도 수동 버튼을 구현한다.

## endpoint·export·HTTP

```text
create_stored_current_binding_preflight_router(get_store)
GET /v1/jobs/{job_id}/input-preflight
```

Job ID literal은 exact str1..256·비공백·C0/C1/DEL/surrogate 거부를 **worker/Store 조회 전** 검사한다. 잘못된 literal은400/get0이며 값은 trim/변환하지 않는다. URI·expected/supplied·manifest hash·path/time을 caller 입력으로 받지 않는다. 기존 main 인증 dependency를 계승한다. 지원 method는GET뿐이며 POST는405다. UI의 ASCII `[A-Za-z0-9_-]`1..200은 명시적인 좁은 제품 지원 범위다.

| HTTP | 조건 | code | message | retryable |
|---:|---|---|---|---|
|200 | 검증된83 MATCH/BLOCKED/UNKNOWN | 없음 |83 payload | 없음 |
|400 | Job literal 지원 밖 | INVALID_REQUEST | Invalid preflight request. |false |
|404 | Store NOT_FOUND | JOB_NOT_FOUND | Job was not found. |false |
|429 | 이 router의 worker 검사 중 | PREFLIGHT_BUSY | An input preflight is already running. |true |
|503 | Store/current resolver resource·worker Exception·반환 schema 모순 | RESOURCE_UNAVAILABLE | Input preflight is unavailable. |false |

오류 본문은 추가 키 없이 exact `{"error":{"code":...,"message":...,"retryable":...}}`다. 위 오류와200에는 `Cache-Control: no-store`를 붙이며429에는 `Retry-After: 1`도 붙인다. inherited 인증 오류는 기존 main 정책을 따른다. 원문 예외·Job ID·Registry/asset URI·절대 경로를 오류에 넣지 않는다. API는83에서 전파하는 RuntimeError/AssertionError 등 **Exception을 안전503으로 바꾸지만**, KeyboardInterrupt/SystemExit/다른 BaseException을 삼키지 않는다. 원래83 core의 예외 정책은 변경하지 않는다.

## 정확한 200 schema

API 모듈은 RESPONSE_SCHEMA,COMPARISON_SCHEMA,ERROR_SCHEMA를 OpenAPI에 제공한다. manual `validate_preflight_response`가 직렬화 **이전**에 exact key/type·bounded 배열·상태/계수 교차식을 추가 검증한다. OpenAPI의 구조 schema만으로 상태/계수 의미가 모두 검증된다고 주장하지 않는다. 원83/81 문서가 전체 field 목록이고 아래는 현재 HTTP 계약의 주요 조건이다.

- scope `STORED_TO_CURRENT_DIRECT_INPUT_PREFLIGHT_ONLY`, schema_version exact int1.
- 요청 literal UTF8 SHA와 request_job_sha256가 모든200 상태에서 정확히 일치한다.
- 200의 store_status는 OBSERVED/store_read_attempted=true/store_read_observed=true/store_get_calls exact int1이다.
- 전체 status는 MATCH/BLOCKED/UNKNOWN, stored_capture_status는 RECORDED/UNAVAILABLE/LEGACY/INVALID다.
- resolver_pass_calls exact int0/1. current_resolution_status는 NOT_RUN/INTEGRITY_VERIFIED/BLOCKED/RESOURCE_UNAVAILABLE/INVALID, current_capture_status는 NOT_RUN/RECORDED/UNAVAILABLE/INVALID다. RESOURCE_UNAVAILABLE은 반환 검증 뒤HTTP503으로 변환한다.
- current_input_count는 알려졌을 때1..64, integrity/quality observed는0..input_count, current_blocker_count는0..768이며 배열 길이와 같아야 한다. 미실행/형식·자원 실패이면 count/quality bool은null, blockers=[]다.
- binding_comparison은 검증된81 결과 또는null. top/inner 모두 raw Job·신원·URI·role·manifest pin·경로·capture 원문을 반환하지 않는다.

15 top flag는 모두 false다: execution_authorized,ready_for_execution,ready_for_training,scientific_approval,acl_verified,registry_verified,training_authorized,pixels_verified,toc_tou_protected,executor_connected,artifact_bytes_verified,manifest_bytes_verified,executor_bindings_compared,stored_job_origin_verified,transitive_lineage_verified. top current_files_revalidated는 없다. inner81의15false는12공통+current_files_revalidated/executor_bindings_compared/stored_job_origin_verified이고7개 IO counter는 exact int0이다. 이는 **순수 비교 scope**이며 전체 API가IO0이라는 뜻이 아니다.

bool을 int1/0으로 받아들이지 않는다. unknown top/inner/issue key, nested code/cycle·미허용 enum·과대 배열, hash retarget, false flag 변조, 상태/계수 모순은 원문 직렬화 없이503으로 닫는다. JSON schema의 일반 integer 허용과 별개로 runtime은 exact int를 검사한다.

## 세 축의 상태·계수 교차식

LEGACY/UNAVAILABLE은 UNKNOWN/resolver0/current statuses NOT_RUN·null counts·binding null이다. 저장 INVALID는 BLOCKED이며 현재 pass를 실행하지 않는다. 저장 RECORDED라도 URI가 지원 밖이면 resolver0/BLOCKED다. 그 외 RECORDED에서만 current pass1을 수행한다.

current resolution이 INTEGRITY_VERIFIED/BLOCKED일 때만 current 계수가 관측된다. quality observed는 실제 quality/access metadata를 받은 entry 수이며 기관 ACL 승인이 아니다. 다음을 runtime과 UI 계약에 동일하게 적용한다.

1. 각 `(input_index,code)` blocker는 중복 없이 input_index0..n-1·기존 code enum이며 blockers≤n×12다.
2. integrity_count = n − **quality 세 code를 제외한 blocker index들의 합집합 크기**. 여러 실패 code가 같은 ref를 가리키면 한 번만 센다.
3. quality_observed_count = n − **metadata 누락 code index들의 합집합 크기**. 누락 code는 DATASET_RECORD_CORRUPT,DATASET_REGISTRY_UNAVAILABLE,DATASET_VERSION_NOT_FOUND,INPUT_INTEGRITY_FAILED,INPUT_REFS_REQUIRED,INPUT_REF_NOT_PINNED,INPUT_REF_SCHEMA_MISMATCH다. URI/CONFLICT 실패는 metadata가 관측될 수 있다.
4. integrity_count≤quality_observed_count. quality_passed는 `(observed==n AND ACL/quality blocker 없음)`과 **양방향 동치**다.
5. quality code 세 개는 INPUT_ACL_NOT_IMPLEMENTED,INPUT_QUALITY_NOT_VALIDATED,INPUT_QUALITY_REJECTED다. quality_passed=true도 URI 등 integrity 실패를 없애지 않는다.
6. INTEGRITY_VERIFIED이면 integrity=observed=n/quality_passed=true/blockers0이다. BLOCKED이면 blocker가1개 이상이다.
7. current capture RECORDED는 같은 pass builder가 모든 integrity true를 요구하므로 integrity=observed=n이어야 한다. 품질/제한 ACL BLOCKED와의 공존은 가능하다.

current capture RECORDED에서만 inner81이 존재하고 stored/current input 계수와 inner3계수가 n으로 같고, 양쪽 digest는 유효하며 stored state도RECORDED다. inner status는 MATCH/BLOCKED이고 declarations_match는 MATCH에만 true, MATCH의 두 배열 digest도 같다. inner UNKNOWN·null hash/count·IO>0·승인true는 이 endpoint 문맥에서 허용하지 않는다.

**current BLOCKED + binding MATCH도 전체 BLOCKED**다. 전체 MATCH는 INTEGRITY_VERIFIED+current capture RECORDED+inner MATCH+top issues=[]인 경우뿐이다. 이 MATCH는 직접 입력의 제한된 현재 진단/저장 pin 일치이며 실제 executor·기관 ACL·과학/학습 승인과 다르다.

## 안전한 code·배열 한도

current_blockers는12개 기존 enum만 허용한다: DATASET_RECORD_CORRUPT,DATASET_REGISTRY_UNAVAILABLE,DATASET_VERSION_NOT_FOUND,INPUT_ACL_NOT_IMPLEMENTED,INPUT_INTEGRITY_FAILED,INPUT_QUALITY_NOT_VALIDATED,INPUT_QUALITY_REJECTED,INPUT_REFS_REQUIRED,INPUT_REF_CONFLICT,INPUT_REF_NOT_PINNED,INPUT_REF_SCHEMA_MISMATCH,INPUT_URI_MISMATCH. 최대64×12=768이다.

top issues는83의14개 안전 code 중 최대1개 exact `{code}`다. inner issues는81의24개 안전 code 집합·side enum·exact index/null·최대512개이며 추가 raw 필드를 허용하지 않는다. 실제 목록은 API의 TOP_CODES/INNER_CODES와 문서81/83에 기록한다. MATCH의 inner issues는[]이고 BLOCKED는1개 이상이어야 한다.

## worker lock·취소 수명·비용

worker 내부에서 BoundedSemaphore(1)를 nonblocking 획득한다. 바쁜 경우 core/Store를 호출하지 않고429를 반환한다. acquired worker는83 검사와 응답 검증이 끝난 뒤 finally에서 해제한다. lock은 **요청 coroutine이 아니라 실제 hash worker가 소유**하므로 화면 이동/Abort/요청 task 취소 뒤에도 실제 검사 종료 전까지 busy가 유지된다. lock 해제 후 다음 요청을 받을 수 있다.

이 제한은 해당 프로세스/router instance의 동시 검사1개다. 다른 API 프로세스/직접83 호출의 작업을 전역 잠금하거나 작업을 강제 취소하지 않는다. UI의 '표시 중단'은 서버 파일 검사의 취소가 아니다. 전체 요청 timeout/개별 file byte cap/누적 IO·CPU·RAM 강제 한도를 추가하지 않는다.

RECORDED 현재 검사는 기존 resolver의 Registry/로컬 artifact SHA/URI I/O를 실제 실행한다. 전체 source/전이 lineage·과학 정답·나지 부족·모델/배포 gate를 검사하는 기능은 아니다. 현재 pin은 관측 시점 한정이며 실행 전 TOCTOU나 다중 파일 원자 snapshot을 보장하지 않는다. legacy는 resolver0/역채움0이고 운영 Job/Registry·원장/lock·분할·모델을 쓰지 않는다.

## 합성 시험·통합 인계

```powershell
$env:PYTHONPATH="$PWD\.runtime;$PWD\backend;$PWD\tests"
python -m unittest test_stored_current_binding_preflight_api -v
```

관련 **13 PASS /3.779초 /종료0**, `evidence/integration/current-input-preflight-api-related-20261017.log`. TempStore positiveMATCH·현재I/O 호출수, qualityBLOCKED+pinMATCH의200차단, legacyUNKNOWN·기존79 GETpayload동등, invalidliteral400/get0·인증계승, safe404503/no-store·error release, currentresource503, unknownrawextra·형식/승인/hash·innerIO/issue한도·모순503, quality/integrity/관측계수의합집합 교차식·capture같은pass계수, workerthread/429·RetryAfter, async요청취소뒤 실제worker종료전busy/해제후재사용, BaseException전파, OpenAPI/GETonly를 확인했다. 초기12개는 계수교차 회귀를 추가하기 전 이력이며 최종13개에 합산하지 않는다.

독립 검토에서 지적한 quality_passed의 일방향 검사와 Root의 current capture RECORDED 계수 모순을 양방향/합집합 식으로 보완했다. 해당 metadata 변조회귀와 positive URI-failure 계수 사례를 모두 통과했다. 원83/81/82/79 helpers는 수정하지 않았다. 기존 TestClient httpx deprecation 경고는 추가 설치/의존성 변경 없이 유지한다.

Root는 main.py 연결·실제HTTP/기존79 동등·전체회귀·보존·브라우저를 담당하고, UI85에는 exact83/inner81/enum·safeerror·비용/취소 의미를 직접 공유했다. 실제 운영 RECORDED/MATCH나 품질BLOCKED·cancelbusy를 합성 근거와 혼동하지 않는다. 새 API의 구현 완료를 모델 readiness·학습 승인 또는 전체 프로젝트 완료로 표현하지 않는다.

독립 최종 시험도 **13 PASS /3.747초 /종료0**, `evidence/integration/stored-current-binding-api-independent-20261017.log`다. 同一13개 재실행은 전체 회귀 건수에 중복 합산하지 않는다. 추가 결함은 발견하지 않았다.

## Root 실제 HTTP 관측

`evidence/integration/current-input-preflight-live-api-20261017.json`과 `evidence/integration/current-input-preflight-live-check-20261017.py`는 신규 route의 기존 legacy2 UNKNOWN/current NOT_RUN, missing404·257자/control400·no-store를 기록한다. 기존79/status/input-resolution6응답은 변경 전 baseline과 deep-equal이며 이번11GET과 별도 baseline6GET을 구분한다. catalog14행과 원 Job body는 불변이고 운영 POST·pin 역채움은0이다. 실제 운영 RECORDED/MATCH·품질BLOCKED·cancelbusy·인증경합은 이번 실제관측으로 주장하지 않으며 해당 합성 시험과 구분한다. 전체 backend 회귀와 UI85 브라우저·보존/이해자료는 Root가 별도로 마감한다.


## 19:28 KST — 현재 입력 수동 preflight API·UI 연결 검증 완료 (84/85)

- **백엔드 / ml_plan_validation:** `GET /v1/jobs/{job_id}/input-preflight`와 main router 연결 완료. 관련13 PASS/3.779초·독립13 PASS/3.747초. worker 내부 semaphore1은 호출자 취소 뒤에도 검사 종료까지 유지한다. 상태·계수·품질 bool 동치·중복 blocker·15false/inner81을 엄격히 검증하며 고정400/404/429/503 오류로 닫는다. 기존83/81/82/79 helper와 기존 GET 본문은 유지했다.
- **UI / web_ui:** 독립 수동 ‘현재 직접 입력 다시 검증’과 저장 근거·현재 진단·선언 대조 3축 표시 완료. 신규14·전체100·독립14 시험 PASS, production build18.96초 PASS(기존 chunk 크기 경고). 자동 조회 없이 기존 저장 GET과 상태를 분리한다. 표시 중단은 서버 검사 취소가 아니다.
- **Root 실제 검증:** API11 GET(이전 기준선6 GET 별도)에서 legacy2 UNKNOWN/current NOT_RUN·고정 오류·기존3종 GET 총6 응답 동등 확인. 실제 브라우저에서 legacy 수동 조회·null≠0·저장GET 독립·404·공백ID 거부·Agent/Registry 변경 및 뒤로/앞으로 이동의 이전 결과 제거를 확인했다. 1449×1087에서 문서/패널 가로 넘침0·콘솔 오류0. 실제 current MATCH/BLOCKED·busy/취소/지연 race·모바일은 운영 브라우저로 검증하지 않았으며 해당 분기는 합성 시험 근거다.
- **전체 시험·보존:** backend869개/868 PASS/기존 Windows symlink1 SKIP/389.808초/exit0. 보호141·불변 코어45 변경0·catalog14행/기존 Job본문 동일. 기존 추적 코드의 변경은 허용된 main.py와 StoredExecutionBindingCapture.tsx 두 곳뿐이다. 운영 Job POST·역채움·새 QA·학습·executor 연결0. 원본·원장·lock·예약136314880B·분할·모델·후보1095/차단4·학습BLOCKED 보존.
- **문서·이해자료:** 신규84/85와 관련07/80/83·운영원장/소유권/인계 갱신. understanding_agent에 완료 코드·시험·실제 API/UI/보존 근거를 전달해 쉬운 설명·이론·코드/데이터·발표 대본·FAQ·INDEX·변경 이력을 함께 갱신한다. 최종 문서 감사·raw SHA snapshot 대조는 `evidence/integration/current-input-preflight-closeout-20261017.json`, 실제 UI는 `current-input-preflight-live-ui-20261017.json`과 desktop JPG를 참조한다.
- **전체 범위와 다음 작업:** 단일 API/UI 단위 완료이며 전체 프로젝트는 미완료다. 다음은 실제 Workflow/executor 전달 직전 입력 계약의 남은 경계를 읽기 검토해 작은 내부 단위로 선정한다(PLANNED, 실제 실행 연결 승인 아님). 외부 terminal 자료·나지 부족/과학 승인·DAG/Result/RAG/운영 범위가 남는다. geoai-2 ACTIVE10분은 예약 설정이며 실행 중인 수집·학습 worker와 구분한다.

근거: `evidence/integration/current-input-preflight-live-api-20261017.json`, `evidence/integration/current-input-preflight-live-ui-20261017.json`, `evidence/integration/current-input-preflight-live-integrity-20261017.json`, `evidence/integration/current-input-preflight-full-tests-20261017.log`.
