# 현재 직접 입력 다시 검증 UI

상태: VERIFIED_REAL(기존 legacy의 실제 API·데스크톱 수동 UNKNOWN/null 조회). RECORDED의 현재 MATCH/BLOCKED·응답 경계·경합·결합 구조는 TESTED_SYNTHETIC이며 실제 resolver 관측 근거83 및 API84와 구분한다. 이번 실제 legacy 조회는 현재 파일 검사를 수행하지 않았다.

## 연결과 명시 조회

기존 ‘저장된 실행 입력 연결 기록’ 카드 하단에 독립 `CurrentInputPreflight` child를 추가했다. 기존 저장 GET·4상태·버튼·어댑터·공통 API·공용 CSS·AgentCenter는 변경하지 않는다. 기존 parent TSX에는 import와 조건 밖 child mount만 최소 삽입했다. 따라서 저장 기록 조회의 성공·실패·로컬 busy/result/error 변화로 현재 검증을 자동 시작하거나 현재 결과를 대체하지 않는다. 현재 검증도 기존 저장 결과를 덮어쓰지 않는다.

사용자는 기존 표준 Job ID를 명시한 뒤 **‘현재 직접 입력 다시 검증’** 버튼을 눌러 `GET /v1/jobs/{job_id}/input-preflight`를1회 보낸다. 저장 GET을 먼저 누를 필요가 없고 새 버튼을 누르기 전에는 마운트·렌더·선택·뒤로 이동·재조회로 preflight를 호출하지 않는다. 빈 값은 비활성이며 기존과 동일한 ASCII 영문·숫자·밑줄·하이픈1..200자 subset만 지원한다. trim·대소문자 정규화·자동 ID 대체는 없다. API의1..256자 더 넓은 literal 지원 범위와 구별한다. 원문 UTF8 SHA-256을 WebCrypto로 계산해 응답 `request_job_sha256`과 대조한다.

이 조회는 조건을 충족한 RECORDED에서 실제 기존 resolver의 Registry·직접 로컬 asset 읽기/해시를 수행할 수 있다. 따라서 저장 GET과 비용·검사 범위가 다르다. UI는 파일 읽기·시간 비용을 명시한다. legacy/unavailable은 resolver0·UNKNOWN으로 남기고 현재 Registry로 과거 제출 pin을 채우지 않는다. 새 QA·학습·Job·Registry 등록·운영 POST·실행을 시작하지 않는다.

## 세 축과 실행 차단

1. **저장된 제출 근거:** RECORDED/LEGACY/UNAVAILABLE/INVALID를 한국어로 구별한다. 저장소 조회 관측이 원본 출처 인증이라는 뜻은 아니다.
2. **현재 직접 입력 진단:** 현재 실행 여부·무결성 일치 관측·품질/접근 메타데이터 관측·품질/PUBLIC 진단·차단 빈도를 별도로 표시한다. 품질/접근 기록 수는 VALIDATED/PUBLIC 수 자체가 아니며 미승인·비공개 metadata가 존재한 경우도 기록 관측에 포함된다. 진단 통과 bool은 전체 기록과 품질/접근 차단을 교차 검사한다. 현재 PUBLIC 진단은 기관 ACL 승인·외부 과학 정답 인증이 아니다.
3. **저장·현재 선언 대조:** 현재 capture 상태와 inner81의 선언 MATCH/BLOCKED·집계 hash·입력 수·원인 요약을 표시한다. pin 선언이 일치해도 현재 품질·접근 진단이 BLOCKED면 전체는 BLOCKED다. 전체 MATCH도 제한된 직접 입력·선언 일치 관측이며 실행 허가가 아니다.

현재 검사가 미실행이거나 진단을 확인하지 못했으면 count/quality bool을 null로 보존해 ‘미실행·미확인’으로 표시한다. 0건 통과로 치환하지 않는다. 유효 current 진단 뒤 capture가 실패하면 이미 관측한 계수·차단은 남기고 선언 대조는 미실행으로 구별한다.

차단은 허용된 코드와 빈도로만 묶어 표시하고 전체 차단 수를 유지한다. inner 원인의 반복도 코드별 요약과 전체 건수를 구분한다. 원 Job/Agent/Trace/Dataset ID·role·개별 manifest pin·URI·경로·원문 exception·큰 JSON을 표시하지 않는다. 저장/현재 binding 집계 hash만 별도 접기에서 표시하며 각각 ordered binding 배열의 집계 식별값이라는 범위를 유지한다.

## 엄격한 응답·계수 계약

200 응답은83 payload 그대로이며 새 wrapper를 만들지 않는다. 정확35개 top key와 schema1/scope STORED_TO_CURRENT_DIRECT_INPUT_PREFLIGHT_ONLY를 검사한다. 이 API의200에서는 OBSERVED/get1/읽기 관측 true와 유효 Job literal hash가 일치해야 한다. NOT_FOUND/자원 실패/invalid literal은 HTTP 오류와 구별한다. top 상태 MATCH/BLOCKED/UNKNOWN, 저장/current/capture enum과 각 원인·resolver0/1을 교차 검사한다.

top15개 false는12개 기존 비승인 필드와 executor_bindings_compared/stored_job_origin_verified/transitive_lineage_verified다. top에는 current_files_revalidated를 추가·정규화하지 않는다. 반면 inner81은12개 비승인+current_files_revalidated/executor_bindings_compared/stored_job_origin_verified false 및7개 정확 int0 IO 카운터를 검사한다. inner의 DB/파일 호출0은 순수 비교 범위이며 이번 전체 GET의 실제 파일 I/O0이 아니다. boolFalse를 int0으로 받아들이지 않는다.

current input1..64, integrity/quality 관측0..n, 차단≤n×12/최대768과 배열 합계·정확 코드/index를 검사한다. 같은(code,index) 중복은 거부한다. 무결성 관측은 품질/ACL3코드를 제외한 차단 index 집합으로 재산출하고, metadata 관측은 등록 손상/미발견/무결성 실패/형식 문제 등7코드의 index 집합으로 재산출한다. integrity≤qualityObserved와 qualityPassed == (qualityObserved==n && 품질/ACL 차단 없음)을 양방향 검사한다. INTEGRITY_VERIFIED는 모든 관측n/quality true/차단0만 허용한다. 현재 capture RECORDED도 integrity/qualityObserved=n을 요구한다.

inner81은 정확34개 key·scope·request literal SHA·stored RECORDED·현재 입력 수와 동일한3계수·집계 SHA·15false·7IO0을 대조한다. MATCH는 declarations_match true/빈 issues/두 집계 hash 동일, BLOCKED는 false/하나 이상 원인만 허용한다. inner issue는≤512·허용 code/side·null 또는 해당 input 범위 index만 허용한다. unknown key/state/type·거짓 승인·모순 count·다른 Job 응답은 failclosed로 표시하지 않는다. 원문을 제거해 정상으로 재해석하지 않는다.

## 독립 상태·이동·오류·스타일

현재 child만의 busy/result/error·세대를 사용한다. child key는 `current-input-preflight:` namespace와 Job ID에만 연결되어 parent 저장 조회의 로컬 inspect 세대·성공·실패로 remount되지 않는다. Agent/model/Job/기존 공통 Job 조회 세대/Registry refresh의 기존 parent key가 바뀌면 두 영역 모두 폐기된다. 입력·재조회·표시 중단·popstate/hashchange·unmount는 늦은 성공/오류를 무효화한다. 요청 세대·Job ID 원문·현재 route hash가 모두 같을 때만 반영한다. hash 계산 도중 입력이 바뀌면 GET 자체를 보내지 않는다.

‘현재 검증 응답 표시 중단’은 UI 반영만 멈추며 이미 수행 중인 서버 파일 검사의 취소·lock 해제를 뜻하지 않는다. API는 worker 종료까지 동시1개 보호를 유지한다. 자동 재시도·polling을 하지 않는다. HTTP400 입력·404 부재·429 진행 중·503 자원 실패 및401/403·연결 실패를 안전한 한국어로 구별한다. 429는 서버 검사 종료 후 명시 재조회해야 함을 안내한다. 서버 error.message 원문을 렌더하지 않는다.

독립 scoped CSS와 기존 SVG를 사용하고 header flex-start/자식 min-width:0/flex:1, 긴 hash 줄바꿈, 좁은 폭의3축1열을 구현했다. 반응형 CSS 구현과 실제 모바일 브라우저 확인은 구분한다. 개별 파일 byte·총 CPU/시간/RAM 강제 상한·전체 전이 계보 검증·원자 snapshot/TOCTOU·실제 executor 연결·학습/과학/기관 권한은 보장하지 않는다.

## 시험·인계

신규14시험은 legacy null/UNKNOWN, 저장 상태별 미실행, 제한된 MATCH, quality/ACL BLOCKED+innerMATCH, pin 불일치, exact/hash/typed scope·count, top/inner15false와IO범위, 차단별 계수 정확식·품질 bool, 코드/index/cap·중복, current 진단·capture 실패의 관측 보존, inner hash/count/issue, 늦은 성공·실패, 안전 오류, 저장/현재 영역 독립 구조를 검증한다. 마지막 시험은 TypeScript AST로 child의 조건 밖 mount·Job ID 전용 key·별도 inspect 내 GET1arg 호출을 확인하고 React 형제 key를 대조한다. 이는 source/guard 경계의 합성 검증이며 실제 저장 성공/실패·현재 결과 독립 동작의 브라우저 근거와 구분한다.

로그는 `evidence/integration/current-input-preflight-ui-adapter-20261017.log`, `evidence/integration/current-input-preflight-ui-tests-20261017.log`, `evidence/integration/current-input-preflight-ui-build-20261017.log`다. 최종 전체 UI/build·독립 검토·실제 브라우저 수치는 후속 절에 기록한다.

UI 담당 변경은 신규 CurrentInputPreflight.tsx/currentInputPreflightAdapter.ts/.test.mjs/current-input-preflight.css와 parent StoredExecutionBindingCapture.tsx의 import/child mount뿐이다. 기존 stored adapter/API/CSS·AgentCenter·공용 helper·backend·원본·운영/이해자료는 변경하지 않는다. Root가84 main 연결·실제 legacy GET/브라우저·전체/보존·이해자료·인계·snapshot을 통합한다. 실제 데이터에 합성 RECORDED/MATCH fixture를 만들지 않는다.


## 최종 프론트 검증

신규 어댑터14/14 PASS /1802.7215ms, 전체 UI100/100 PASS /0 FAIL /0 SKIP /2384.4127ms. 최종 TypeScript + Vite production build PASS /81 modules /18.96s. JS1,577.00kB(gzip443.15kB), CSS178.69kB(gzip32.56kB)이며 기존500kB chunk 경고만 있다. 독립 신규14/14 PASS /1609.1864ms와 소스 읽기 추가결함0은 `evidence/integration/current-input-preflight-ui-independent-20261017.log`에 기록됐다. 같은 시험의 반복 실행은 신규 시험 건수로 합산하지 않는다.

코드·시험·build·관련 문서를 완료하고 source를 동결했다. 실제 API8002 배선·기존 legacy의 UNKNOWN/null 관측·브라우저 버튼/이동/독립 결과·콘솔·데스크톱/모바일·보존은 root의 별도 근거 수신 뒤 이 문서에 추가한다. 현재 실자료 RECORDED/MATCH나 강제 late race·429/503가 실제 브라우저에서 입증됐다고 주장하지 않는다.


## 실제 적용·브라우저·보존 검증

Root 근거 `evidence/integration/current-input-preflight-live-ui-20261017.json`을 읽고 `current-input-preflight-ui-desktop-20261017.jpg`를 직접 열어 확인했다. 실제 UI5174의 `#/view/24?model=lcluc&tab=evidence`에서 기존 legacy Job의 수동 GET은 UNKNOWN이며 저장 근거/현재 직접 입력 진단/저장·현재 선언 대조의3축을 보여준다. 현재 resolver pass는0, 계수와 품질 bool은 null의 ‘미실행·미확인’으로 표시했고0건 통과나 현재 파일 검사 완료로 바꾸지 않았다.

빈 ID의 비활성, ID 입력만으로 자동 조회하지 않음, 명시 조회와 기존 저장 GET의 독립성(저장 GET 뒤에도 현재 결과 유지), Job 변경 시 이전 결과 제거를 확인했다. 없는 Job의 안전한 HTTP404, 앞 공백 입력의 trim 없는 비활성, Agent 변경·Registry refresh의 결과 초기화, 허브/Workspace의 뒤로·앞으로·뒤로 복귀에서 이전 결과를 표시하지 않음도 확인했다. 실제 저장 GET 성공과 현재 결과 독립성을 관측한 것이며 강제 저장 GET 실패에 대한 동적 상태 독립성은 source/guard 시험과 구분한다.

데스크톱1449×1087에서 문서·panel 가로 넘침은 각각0px, 관측된 콘솔 오류 목록은[]였다. 스크린샷은 `evidence/integration/current-input-preflight-ui-desktop-20261017.jpg`다. 이번에는 모바일 viewport, 실자료 RECORDED의 current MATCH/BLOCKED, HTTP429/503, 강제 취소·지연 응답 경합을 실제 브라우저에서 검증하지 않았다. 해당 상태·범위의 합성/API 시험을 운영 브라우저 근거로 확대하지 않는다. 표시 중단은 서버 작업 취소가 아니라는 제한도 유지한다.

`evidence/integration/current-input-preflight-live-integrity-20261017.json`은 Root의 전체 backend869건/868PASS/기존Windows symlink1SKIP/389.808초/exit0과 후속 보호141참조·기존45코어·catalog14행/기존Job본문 불변을 기록한다. 기존 추적 코드의 변경은 허용한 backend/main배선과 parent StoredExecutionBindingCapture.tsx 연결뿐이며 신규파일은 별도다. 이 보호 범위를 전체 workspace 원자 snapshot 인증으로 표현하지 않는다. frontend100시험과 backend869건을 같은 실행이나 신규 시험 수로 합산하지 않는다.

새 운영 Job POST·capture 역채움·새 QA·학습·실제 executor 연결은0이다. 이 실제 적용 절 작성 후 소스·시험·build 변경 없이 문서 쓰기를 동결한다. API84·공통 운영 문서·이해자료·인계·snapshot의 최종 통합은 Root가 맡는다.
