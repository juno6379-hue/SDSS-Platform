# 저장된 실행 입력 연결 기록 UI

## 2026-10-17 현재 직접 입력 수동 preflight API·UI companion (84/85)

`GET /v1/jobs/{job_id}/input-preflight`는83의 저장 근거·현재 직접 입력 integrity/quality/PUBLIC metadata·pin 대조 세 축을 수동 조회하는 내부 API다. 기존 `execution-input-binding` 저장 기록 조회와 Job Status/input-resolution 응답은 바꾸지 않는다. 83의 safe payload를 그대로 반환하고 개별 ID·URI·manifest pin·파일 경로·원문 예외를 노출하지 않는다.

worker 내부에서 단일 검사 semaphore를 획득하고 실제 작업 종료 시 해제한다. 요청 취소나 화면 표시 중단이 서버 파일 검사 취소를 뜻하지 않는다. 기존 인증을 상속하고 no-store를 적용한다. 잘못된 literal400, 없는 Job404, 중복 검사429(PREFLIGHT_BUSY/Retry-After1/retryable=true), 자원·잘못된 내부 응답503은 고정 안전 오류다. 동시 검사 수·refs/문자 상한은 전체 파일 byte/time/RAM 강제 상한과 다르다.

반환 계약은 타입·배열/코드 한도·Job literal SHA·15false·inner81·3축 상태를 교차검사한다. integrity 수는 실패 입력 index의 합집합, quality 관측 수는 metadata 미관측 실패 index의 합집합과 대조하며 quality passed는 관측 수·차단 코드와 양방향으로 일치해야 한다. 현재 capture가 RECORDED이면 모든 직접 입력의 integrity와 quality/access 관측이 존재해야 한다. 모순된 응답은 정상 판정으로 내보내지 않는다.

관련/독립 API13 PASS(3.779초/3.747초). 실제 API8002에서 legacy2 UNKNOWN/current NOT_RUN, missing404·긴/control literal400/no-store와 기존79/status/input-resolution6응답의 변경 전 동등성을 확인했다. 이번11GET과 이전 baseline6GET은 구별하며 catalog14행/Job 본문은 불변이다. MATCH·품질BLOCKED·취소중busy429/503은 합성 시험 범위이고 실제 executor·운영 Job POST·역채움·수집/QA학습은 없다. 근거: `evidence/integration/current-input-preflight-live-api-20261017.json`.

API 정확 계약·시험은 [문서84](84_current_input_preflight_api.md), 기존 카드에 독립 수동 버튼과 결과를 연결하는 UI의 최종 시험·실제 브라우저 근거는 [문서85](85_current_input_preflight_ui.md)를 따른다. 이번 조회의 MATCH는 입력 비교 관측일 뿐 실행·과학·기관 ACL·학습·배포/TOCTOU 승인이 아니다.

상태: VERIFIED_REAL(실행 중 API·브라우저의 기존 legacy 수동 조회와 안전한 복귀 범위). RECORDED/UNAVAILABLE/INVALID 응답 경계·경합 어댑터 검증은 TESTED_SYNTHETIC이며 해당 상태의 운영 생성·실제 모바일 검증은 하지 않았다. 신규 Job capture 생성의 합성 근거는 구현78, 저장 기록 projection/API 계약은 구현79와 구분한다.

## 연결 위치·명시 조회

Agent Center의 기존 표준 Job ID·Job 카드 영역에 독립 ‘저장된 실행 입력 연결 기록’ 카드를 추가했다. 기존 상태·Trace·입력 snapshot 조회에 합치지 않고 현재 계보 진단과도 별도로 둔다. 표준 Job ID 초기값은 기존처럼 빈 값이며 카드의 ‘저장된 입력 연결 기록 조회’ 버튼은 비활성이다. 유효한 ID를 사용자가 입력한 뒤 버튼을 누를 때만 `agentApi`의 `GET /v1/jobs/{job_id}/execution-input-binding`를 호출한다. 카드 마운트·선택·렌더·뒤로 이동·기존 Job 조회로 새 GET을 자동 호출하지 않는다. 표준 Job 상태를 먼저 조회해야만 이 카드를 사용할 수 있는 것은 아니다.

입력은 기존 `standardJobId` 원문을 사용한다. 이 UI가 지원하는 범위는 ASCII 영문·숫자·밑줄·하이픈 1..200자이며 공백 trim·대소문자 변환·추정·latest 선택은 하지 않는다. 지원 밖 입력은 버튼을 비활성화하고 지원 범위를 안내한다. 백엔드의 더 넓은1..256자 문자열 계약과 UI subset을 구별한다. 원문 UTF8 바이트의 SHA-256을 WebCrypto로 계산해 모든 상태의 `request_job_sha256`과 대조한다. UI subset에서는 응답의 null request hash도 표시 거부한다. URI 경로에는 encodeURIComponent를 사용하며 GET 본문·운영 POST를 보내지 않는다.

## 상태·계수·검사 범위

| API 상태 | 제품 표시 | 의미 |
|---|---|---|
| RECORDED | 기록 있음 · 저장 연결 구조 일치 | 저장된 Job 요청과 capture의 연결 구조 일치가 보고됨. 현재 파일·권한·학습·실행 승인 아님 |
| UNAVAILABLE | 제출 시 기록 생성 불가 | 제출 시 기록을 만들지 못함. 원인 코드와 일부 입력의 순서만 제한적으로 표시 |
| LEGACY | 이전 Job의 미기록 | 이전 Job에 별도 capture가 저장되지 않음. 소급 기록을 만들지 않으며 null을0으로 바꾸지 않음 |
| INVALID | 저장 기록 확인 불가 | 저장된 Job 요청 또는 capture의 형식·일관성 확인 불가. 정상 기록이나 현재 검증으로 대체하지 않음 |

세 카운터는 저장 요청의 입력 수, 기록된 입력 연결 수, 입력별 manifest 기준 수다. 마지막 값은 입력별 pin 기록 수이며 중복 제거한 고유 manifest 파일 수와 다르다. RECORDED일 때1..64의 동일한3계수·집계 SHA-256·저장 연결 일치 true·빈 issue 목록을 요구한다. 나머지 상태의 capture/pin/집계hash는 모두 null, 저장 연결 일치는 false다. 정상 저장 요청을 가진 LEGACY/UNAVAILABLE/INVALID(STORED_CAPTURE_INVALID)는 request count1..64이며, INVALID(STORED_JOB_INVALID)만 request count=null이다.

응답의 원문 Job/Agent/Trace/Dataset ID·역할·개별 manifest SHA·URI·경로·시각·거대 JSON을 표시하거나 내려받지 않는다. 카드에 입력 ID를 다시 출력하지 않고, 결과는 계수·집계 해시·검사 범위·허용된 원인 코드/입력 순서의 작은 allowlist만 보관한다. 기존 표준 Job ID 입력 필드는 사용자가 명시한 값을 계속 보인다. 집계 해시는 저장 연결 목록의 식별값이며 개별 manifest pin이나 현재 원본 파일 hash 인증이 아니다.

## 엄격한 어댑터 계약

정확한26개 top key, schema_version1, extension `greenblue.stored-execution-input-binding.rfc1`, approval_status INTERNAL_REVIEW, scope STORED_SUBMISSION_BINDING_ONLY와 정확한4상태를 검사한다. bool·문자열을 계수로 허용하지 않으며 unknown key/state/scope·허위 승인·다른 Job 응답은 failclosed로 표시하지 않는다.

다음12필드는 정확히 false다: execution_authorized, ready_for_execution, ready_for_training, scientific_approval, acl_verified, registry_verified, training_authorized, pixels_verified, toc_tou_protected, executor_connected, artifact_bytes_verified, manifest_bytes_verified. 여기에 current_files_revalidated와 executor_bindings_compared도 false를 요구한다. 저장 구조 일치와 현재 Registry/바이트/픽셀·실제 실행자 입력 대조·학습/과학/ACL/실행 승인을 구분한다. 시점 보호·원본 인증·실행자 연결도 보장하지 않는다.

issues는 최대1개 exact `{code,input_index}`다. RECORDED는0개, LEGACY는 LEGACY_CAPTURE_NOT_RECORDED/null, INVALID는 STORED_JOB_INVALID 또는 STORED_CAPTURE_INVALID/null을 검사한다. UNAVAILABLE 허용 코드는 CAPTURE_UNAVAILABLE/TIME_INVALID/ROWS_UNAVAILABLE/ROW_UNAVAILABLE/BINDING_INVALID/BOUNDARY_FAILURE(각 CAPTURE_ 접두)이며 CAPTURE_ROW_UNAVAILABLE만 request count 범위의 정수0기반 index를 허용한다. 나머지 index는 null이다. 제품에는 쉬운 한국어와 필요한 코드·1기반 순서만 보여주며 원본 입력 식별자를 추정하지 않는다.

HTTP404·503·401·403·연결 실패를 안전한 한국어로 구별한다. 서버 error.message의 원문·JSON·경로를 화면에 넘기지 않는다. 조회 실패를 LEGACY/null이나 기록 존재·학습 준비 완료로 대체하지 않는다.

## 이동·재조회·스타일

입력 변경·기존 Job 재조회·Agent/호환 모델 선택·Registry refresh는 `stored-execution-binding:` namespace의 component key에 해당 context와 jobRequestGeneration을 포함해 이전 진단을 폐기한다. 기존 출처 카드·후보 카드와 key가 충돌하지 않는다. popstate/hashchange·unmount도 세대를 무효화한다. 수동 재조회는 기존 결과/오류를 지우고, 세대·원문 Job ID·현재 hash가 모두 같을 때만 응답을 표시한다. SHA 계산 중 입력이 바뀌면 GET을 보내지 않으며 이미 전송한 응답도 뒤늦게 표시하지 않는다.

‘응답 표시 중단’은 UI 반영을 무효화하며 이미 전송된 서버 요청이나 작업을 취소했다고 주장하지 않는다. `api.ts`에 AbortSignal·운영 동작을 추가하지 않았다. 기존 SVG Icon과 전용 scoped CSS를 사용한다. 카드 header는 flex-start와 자식 min-width:0/flex:1을 명시했고 모바일에서는 카운터를1열로 바꾸고 집계 해시를 줄바꿈한다. 반응형 CSS 구현과 실제 모바일 브라우저 검증은 구분한다.

## 검증·인계

신규 어댑터14시험은 Job literal 지원 범위·독립 UTF8 hash 대조, RECORDED·LEGACY·UNAVAILABLE·INVALID의 count/null/issue 매핑, 다른 Job hash,14false, typed count/cap·집계 hash·무결성 일관성, unknown/raw정보 거부, 늦은 성공/오류·입력/메뉴/중단, 실제 React 형제3개 key 구분·선택 변경 remount, 오류 분리를 검증한다. 운영 Job·Registry·DB에 합성 fixture를 생성하지 않는다.

로그: `evidence/integration/stored-binding-capture-ui-adapter-20261017.log`, `evidence/integration/stored-binding-capture-ui-tests-20261017.log`, `evidence/integration/stored-binding-capture-ui-build-20261017.log`. 최종 시험·build와 root 실제 브라우저 수치는 후속 절에 기록한다.

소유 범위는 신규 StoredExecutionBindingCapture.tsx, storedExecutionBindingCaptureAdapter.ts, 관련 .test.mjs, stored-execution-binding-capture.css 및 AgentCenter import/render 최소 삽입이다. API 공통 helper·공용 CSS·backend·원본·운영 문서·understanding 자료는 UI 담당이 수정하지 않는다. Root가 main 연결·실제 기존 Job2개 GET·오류·브라우저·전체 회귀·보존과 이해자료·인계·snapshot을 같은 작업 단위로 통합한다. 학습·QA·운영 POST·Registry 등록은 수행하지 않는다.


## 최종 프론트 검증

신규 adapter14/14 PASS /544.6393ms, 전체 UI86/86 PASS /0 FAIL /0 SKIP /1546.3622ms. TypeScript + Vite production build PASS /78 modules /19.77s. JS1,554.86kB(gzip438.28kB), CSS175.66kB(gzip32.13kB)이며 기존500kB chunk 경고만 있다. 독립 신규14/14 PASS /960.7704ms는 `evidence/integration/stored-execution-binding-capture-ui-independent-20261017.log`에 기록됐고 소스 읽기 추가결함0이다. 같은 시험의 반복 실행을 신규 시험 수로 합산하지 않는다.

카드의 구현·합성 경계 시험·build는 완료하고 소스를 동결했다. 실행 중 API에 대한 실제 legacy GET·404·브라우저 수동 조회·뒤로가기·화면/콘솔·보존은 root의 별도 검증 결과를 받은 뒤 이 문서에 적용 절만 추가한다. 이것은 아직 RECORDED 실자료 생성·현재 파일 검사·실제 executor 연결·학습 승인을 주장하는 근거가 아니다.


## Root 실제 서버·브라우저 적용 확인

실행 중 Vite5174와 API8002에서 기존 legacy Job을 명시 버튼으로 조회해 LEGACY·요청입력1·capture/manifest 기준수 미기록·미확인(null)을 확인했다. 입력만으로 결과를 생성하지 않으며 입력변경은 이전 표시를 지웠다. 없는Job404의 안전 메시지·선행공백ID 버튼비활성/자동trim없음·모델허브 뒤로/앞으로 복귀 시 Job입력과 결과초기화·Agent선택변경 결과제거·복귀후재조회 성공을 확인했다. 기본1449×1087 화면에서 문서/카드 가로넘침0, 관측콘솔error목록[]이다. 실제모바일/지연네트워크경합을 강제로 재현하지 않았으며 late응답·나머지3상태는합성시험범위다. 실제RECORDED 생성·현재파일검사·executor연결·학습승인은검증하지않았다.

근거: `evidence/integration/stored-binding-capture-live-ui-20261017.json`, `evidence/integration/stored-binding-capture-ui-desktop-20261017.jpg`. 실제API의기존2Job/원상태·input-resolution·없는404/긴literalINVALID8GET과catalog14전후불변은 `evidence/integration/stored-binding-capture-live-api-20261017.json`에 기록했다. 실제새JobPOST/역채움/QA·학습0이다.


최종 Root 전체 backend 회귀:819개/818 PASS/기존Windows symlink1 SKIP/394.315초/exit0. `evidence/integration/stored-binding-capture-full-tests-20261017.log`. 종료후보호141/불변코어39/catalog14SHA동일·기존허용main/AgentCenter만변경은 `evidence/integration/stored-binding-capture-live-integrity-20261017.json`에기록했다.
