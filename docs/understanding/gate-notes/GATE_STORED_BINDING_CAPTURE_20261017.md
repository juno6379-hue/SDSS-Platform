# Gate Stored Binding Capture 20261017 — 저장 제출 선언의 안전한 명시 조회

| 필드 | 값 |
|---|---|
| updated_at | 2026-10-17 23:36 KST — Git 상태 메타데이터 정정; 본문은 해당 Gate 기준 |
| source_commit | d474d5bce6c2a6c4bd8ba141c9256d15f6004631 (108까지 구현 검토 기준; 이 메타데이터 정리는 후속 문서 커밋) |
| evidence_paths | `backend/app/job_execution_binding_capture.py`; `backend/app/job_execution_binding_capture_api.py`; `tests/test_job_execution_binding_capture.py`; `docs/implementation/79_stored_binding_capture_api.md`; `evidence/integration/stored-binding-capture-related-20261017.log`; `evidence/integration/job-execution-binding-capture-independent-20261017.log`; `evidence/integration/stored-binding-capture-live-api-20261017.json`; `frontend/src/StoredExecutionBindingCapture.tsx`; `frontend/src/storedExecutionBindingCaptureAdapter.ts`; `frontend/src/storedExecutionBindingCaptureAdapter.test.mjs`; `frontend/src/stored-execution-binding-capture.css`; `frontend/src/AgentCenter.tsx`; `docs/implementation/80_stored_binding_capture_ui.md`; `evidence/integration/stored-binding-capture-live-ui-20261017.json`; `evidence/integration/stored-binding-capture-ui-adapter-20261017.log`; `evidence/integration/stored-binding-capture-ui-tests-20261017.log`; `evidence/integration/stored-binding-capture-ui-build-20261017.log`; `evidence/integration/stored-execution-binding-capture-ui-independent-20261017.log`; `backend/app/main.py`; `evidence/integration/stored-binding-capture-full-tests-20261017.log`; `evidence/integration/stored-binding-capture-live-integrity-20261017.json` |
| confidence | 코드·합성/독립·실제legacyGET; RECORDED실자료생성/실제executor 미확인 |
| status | TESTED_SYNTHETIC: API/UI/전체회귀; VERIFIED_REAL: 실제legacyGET·수동UI; 실행/현재파일인증false |

## 쉬운 설명

주문서의 내부 메모를 그대로 보여주는 대신, 기록이 있는지·유효한지·몇 개의 입력을 담았는지만 작은 조회창으로 읽는다. 메모가 없는 옛 주문은 ‘미기록’으로 두며0개라고 채우지 않는다. 메모의 내용과 지문이 서로 맞아도 현재 물품이나 실제 배달 목록까지 확인한 것은 아니다.

## 이론적 배경

78은새Job에만기대선언capture를저장했다.79는저장형식·Job/request연결·배열hash를대조해내부식별자/manifestpin/URI를노출하지않는최소projection을제공한다. 저장선언의내부일치와현재Registry/파일검증·실제executor전달일치는서로다르다. oldcapture부재·알려진미수집·손상·정상기록을구분하면없는자료를정상0으로바꾸지않고설명할수있다.

## 함수·검증 순서

순수 `project_job_execution_binding_capture(job, job_id)`는요청literal과Job id/job_id/status.job_id, Job/status/request agent, status/request trace가같은지먼저확인한다. 선택문자열은exactstr1..256·C0/C1/DEL/surrogate/공백only를제한한다. request refs1..64에서id/version/assetSHA/rolepresence·순서/index를77guard로검증한다. URI는문자열형식만확인하고복사·resolve·반환하지않는다. malformedJob은capture부재보다INVALID를우선한다.

capture는78exactschema/12false·additional_* exactint0·상태/시각·issue를검사한다. RECORDED의timezoneaware시각·빈issues·완전envelope selfcompareMATCH·canonicalbindingsSHA·Jobrequest선택선언linkage가맞아야한다. rehash로변조hash를숨겨도Job/Agent/Trace/id/version/assetSHA/role/순서가다르면INVALID다. UNAVAILABLE은시각Nonefallback을허용하되값이있으면aware여야하고envelope/hash모두null·안전issue1개만허용한다.

## 네 상태와null

| 상태 | 요청입력수 | capture/pin수·배열hash | 의미 |
|---|---|---|---|
| RECORDED |1..64 | 요청수와같은수·hash있음 | 저장선언내부일치 |
| UNAVAILABLE |1..64 |null | 알려진선택capture실패 |
| LEGACY |1..64 |null | capturekey미기록 |
| INVALID·Job손상 |null |null | 선택Job/request가무효 |
| INVALID·capture손상 |1..64 |null | 저장capture계약/연결이무효 |

null은알수없거나미기록이며0개라는뜻이아니다. capturekey가있는null도LEGACY로보지않고INVALID다. 안전issue는code/index만있으며rawid/version/role/manifestpin/URI/경로/예외/captured_at은출력하지않는다. request_job_sha256는요청Jobliteral의UTF8hash, expected_bindings_sha256는expected배열만의hash라Jobidentity전체digest가아니다.

## API 사용·권한 범위

`GET /v1/jobs/{job_id}/execution-input-binding`은유효literal에대해threadpool에서Job get1회만한다. 기존인증dependency를계승한다. 잘못된literal은DB조회없이200INVALID/hashnull,없는Job은404JOB_NOT_FOUND·기타store오류는503RESOURCE_UNAVAILABLE로안전문구만반환한다. 처리한200/404/503은no-store이고POST405같은프레임워크응답/기존인증오류는별도다.

최상위26키·4status·요청/배열hash·nullablecounts·stored_binding_integrity_match·safeissue·12+2false만반환한다. stored_binding_integrity_matchtrue는RECORDED내부일치이며 current_files_revalidated/executor_bindings_compared와12승인flags는계속false다. 현재Registry/자산/manifestbytes/TOCTOU·실제executor/assess/훈련·DB쓰기/legacy역채움은없다. 기존원본5/후보4차단·나지부족을해제하지않는다.

## 시험·실제 API 관측

관련14 PASS/0.594초·독립14 PASS/0.330초를읽었다. RECORDED/UNAVAILABLE/LEGACY/INVALID·hash/Joblinkage변조·시각/정확타입/issue·신원선상한·무IO/입력불변·안전필드·workerget1/invalidDB0·인증/no-store/404/503·OpenAPI를합성검증했다. RECORDED생성은이합성범위이며실제신규운영capture생성이아니다.

Root API8002의실제legacy2조회와기존status/inputresolution·없는Job404/257자INVALID 총8GET을검증했다. legacycapturecount/pincount/hash는null·requestcount1·저장원본body/카탈로그14SHA동일·POST0/역채움0이다. 실제LEGACY관측과합성RECORDED를섞지않는다. 실제실행기연결·현재자산검증·새QA/학습없음이다. 최종backend전체는 **819건 중818 PASS·1 SKIP/394.315초/종료0**다. 기존Windows symlink생성권한 제약1개를 건너뛰었고 deterministic경계시험은통과했다. backend관련14 PASS/0.594초·독립14 PASS/0.330초와신규UI14 PASS/544.6393ms·독립UI14 PASS/960.7704ms·전체UI86 PASS/1546.3622ms·build78modules/19.77초는범위를분리해backend819에합산하지않는다. 시험후보호141참조·39기존코어SHA와카탈로그14기록canonicalSHA/기존Job body불변을재확인했다. 이전추적code/data/tests/frontend중의도한main.py/AgentCenter.tsx두파일만변경됐고신규파일도있으므로전체workspace변경2개/원자snapshot보장은아니다.

## 80 UI 명시 조회와 실제 적용

완료카드는Agent Center 표준Job ID영역에별도로연결하며현재상태/입력snapshot/현재lineage와합치지않는다. 빈ID는버튼비활성이고ASCII영문·숫자·밑줄·하이픈1..200자literal만지원한다. API1..256보다좁은UI범위이며trim/대소문자변환/추정은없다. 유효ID입력만으로결과를만들지않고명시버튼GET만호출한다. 기존Job상태조회를먼저실행할필요도없다.

WebCrypto의원문Jobhash를응답requesthash와대조하고exact26키/4상태·nullablecount/issue·집계hash/저장일치·14false를검사한다. 입력별manifest기준수는중복제거한고유파일수가아니다. 계수·집계hash·안전코드/1기반입력순서만보이고원문식별자/manifestpin/URI/경로/시각·거대JSON을노출하지않는다.

입력·기존Job재조회·Agent/모델/Registry·메뉴/뒤앞이동은namespacedkey/세대/원문JobID/hash로이전응답을무효화한다. SHA계산중입력이바뀌면GET을보내지않고이미전송한late응답도반영하지않는다. 응답표시중단은서버작업취소가아니다. 기존SVG/전용CSS와형제keynamespace를사용한다.

최종신규UI14 PASS/544.6393ms·전체UI86 PASS/1546.3622ms·build78modules/19.77초·독립UI14 PASS/960.7704ms다. API관련14 PASS/0.594초·독립14 PASS/0.330초와별도범위로기록하며전체backend에합산하지않는다.

Root실제5174→8002 LCLUC evidence에서기존legacy를명시GET해requestcount1/capture·manifestcountnull의‘미기록·미확인’을관측했다. 빈IDdisabled·입력만결과없음·입력변경clear·없는404안전·선행공백disabled/trim없음·허브back/forward/back Job입력/결과clear·Agent변경clear·복귀재조회성공을확인했다. desktop1449×1087문서/카드넘침0·관측consoleerror목록[]다. 기존5173적용검증으로확대하지않는다.

실제RECORDED/UNAVAILABLE/INVALID렌더·강제late네트워크경합·모바일실환경은검사하지않았다. 네상태/late/key검증의나머지범위는합성시험으로구분한다. 운영POST/역채움/새QA학습0이며UI완료는실행/파일인증완료가아니다. 최종backend전체는 **819건 중818 PASS·1 SKIP/394.315초/종료0**다. 기존Windows symlink생성권한 제약1개를 건너뛰었고 deterministic경계시험은통과했다. backend관련14 PASS/0.594초·독립14 PASS/0.330초와신규UI14 PASS/544.6393ms·독립UI14 PASS/960.7704ms·전체UI86 PASS/1546.3622ms·build78modules/19.77초는범위를분리해backend819에합산하지않는다. 시험후보호141참조·39기존코어SHA와카탈로그14기록canonicalSHA/기존Job body불변을재확인했다. 이전추적code/data/tests/frontend중의도한main.py/AgentCenter.tsx두파일만변경됐고신규파일도있으므로전체workspace변경2개/원자snapshot보장은아니다. 이해에이전트는API/브라우저/시험을실행하지않는다.

## 발표1분

“새 조회 API는 Job에 저장된 제출 입력 메모의 형식과 연결 지문을 확인해, 기록됨·미수집·미기록·무효를 구분합니다. 내부 식별자나 파일 경로 대신 입력 개수와 집계 지문·안전 코드만 보여줍니다. 옛 Job의 미기록 개수는0이 아니라 알 수 없음으로 남깁니다. 실제 기존 Job 두 건은 미기록 상태를 유지했고 새 정상기록 검증은 합성시험 범위입니다. 저장 메모가 맞아도 현재 파일이나 실행기에 전달된 목록을 확인한 것은 아니며 실행 승인은 모두 false입니다.”

## 발표5분·10분

1. **0~1분:** 내부메모를작은안전조회창으로읽는비유를말한다.
2. **1~2분:** Job/request/capturelinkage·hash·시각검증을설명한다.
3. **2~3분:** 네상태/null≠0·최소26키·14false를보여준다.
4. **3~4분:** 합성RECORDED/실제legacyGET·UI/전체/보존근거를구분한다.
5. **4~5분:** 현재files/executor미검증·승인false·UI실제적용범위를말한다.

10분확장에서는malformedJob우선·capturekeynull과legacy차이·awaretimefallback·requesthash/배열hash차이·유효get1/invalidDB0·공개민감필드비노출을설명한다.

## Q&A

**RECORDED면현재파일도맞나?** 저장선언내부일치만이며current_files_revalidatedfalse다.

**LEGACY의null은입력0개인가?** requestcount는있어도미기록capture/pin수는모르므로null이다.

**실제정상capture도조회했나?** 실제기존2Job은LEGACY이고RECORDED생성/변조검증은합성범위다.

**실행기에전달된목록인가?** 저장제출expected의안전요약이며executor_bindings_comparedfalse다.

**화면도완료됐나?**80코드/프론트/실제legacy수동조회를확인했다. 나머지3상태/강제late/mobile은이번실환경검증아니다.

## 이후갱신

80UI·전체/실제브라우저·보존최종근거를읽고INDEX·변경이력·계약/Orchestrator/구조/용어·대본/FAQ/시연을함께갱신했다. 공개안전조회는실행/학습/과학승인이아니다.

## 다음 저장expected 기반 handoff guard — PLANNED

후속설계는 compare_stored_job_binding_handoff(job, requested_job_id, supplied_envelope)라는순수경계를검토한다.79저장검증을통과한RECORDED의expected만꺼내77과비교하고caller가expected를임의로주입하거나Registry로역채우지않는방향이다. 유효legacy/unavailable은UNKNOWN, malformedJob/capture/supplied는BLOCKED, 일치해도승인false/실제executor미연결을유지한다. 현재새guard/API/UI는미구현이며기존코드/원본을바꾸거나실행을시작한것은아니다.
