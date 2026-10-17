# 저장된 출처 대조 진단 UI

상태: VERIFIED_REAL(고정 저장 보고서의 실제 API·수동 UI 조회). 응답 경계·경합 어댑터 시험은 TESTED_SYNTHETIC이며 원본 파일 재검증·학습 승인을 뜻하지 않는다. 실자료 보고서 생성 근거는 문서66과 구분한다.

## 화면·계약

Agent Center의 기존 LCLUC 호환 정보 뒤에 ‘저장된 출처 대조 진단’ 카드를 추가했다. 기존 모델·데이터·실행 gate와 6모델/참조 PNG 레이아웃은 변경하지 않는다. 화면 진입·마운트·선택·렌더·뒤로 이동으로 진단을 호출하지 않는다. 사용자가 ‘저장된 출처 대조 조회’를 명시적으로 누를 때만 `agentApi`로 `POST /v1/diagnostics/readiness-source-identity`를 호출한다.

요청 본문은 정확히 `{report_sha256, manifest_sha256, token}` 3개다. 고정 예시는 보고서 `6bc86c9883716565946cff1700780db98aea005bca2e8da2c225520501dda642`, manifest `cdc374b2779dee749b57689fd90ef27e3525a48e59062343537327d0f4859a8f`, 토큰 `S2A_MSIL2A_20210812T025551_R032_T48MXT_20210812T132431`이다. latest 탐색·자동 대체는 하지 않는다. SHA는 소문자 64자리(입력 여백 정리)를 요구한다. 이 UI의 토큰 지원 범위는 ASCII 영문·숫자·밑줄·하이픈 1..256자이며 토큰 원문의 공백을 조용히 제거하지 않고 잘못된 입력으로 안내한다. API 자체의 토큰 지원 범위와 UI의 좁은 입력 범위를 구별한다.

응답은 schema_version 1, status BLOCKED, scope PINNED_STORED_REPORT_DECLARATIONS_ONLY와 3종 diagnostic_status를 정확히 검사한다. 보고서·manifest 핀과 토큰 UTF8 SHA-256(WebCrypto)을 요청과 대조한다. 정해진 응답·counts 키 외 필드, 알 수 없는 상태/형식, bool을 가장한 계수, true/0/문자열/누락된 비승인 flag는 결과를 폐기한다. 선택4계수는 OBSERVED_DECLARATIONS일 때 정수, 미제공/미수집 두 상태에서는 null만 허용한다. scene·완전선언·회원·연결참여·0패치·선언유일회원≤2000, 저장차단≤10000, 고유원본후보≤100000, 후보연결≤200000000, 패치수≤Number.MAX_SAFE_INTEGER를 검사한다. 회원≤전체장면, 유일선언회원≤완전선언·조회회원·선언연결 등 교차 모순도 검사한다.

카운터 12개 중 조회 회원·넓은 후보 연결·선언 유일대조 회원·0패치 장면·적격 패치를 각각 표시한다. 전체 장면·완전 선언, 문자열 일치 회원·연결 참여 회원, 넓은 후보·선언 후보의 고유 원본 후보는 별도 표로 보여준다. 기존 차단 건수는 `saved_blocker_count`로 표시하고 학습 BLOCKED를 별도 유지한다. 현재 실자료의 기대치 28/400/28/3/25/차단5는 코드에 성공값으로 고정하지 않고 검증된 응답을 통해서만 표시한다.

원본 경로·원본 행 index·원문 JSON 다운로드/렌더·거대 report를 노출하지 않는다. 응답 전체를 state나 원본 JSON 접기에 저장하지 않고 작은 allowlist 투영만 표시한다. 핀은 결과에 12자리 접두로 보여주며 원문 토큰을 결과에 되돌려 표시하지 않는다. 입력 폼은 사용자가 명시한 고정 식별자이다.

## 승인·현재성·오류

유일한 선언 일치는 원본 진실성 인증·정확한 원본 행 확정·누수 해소·과학적 정확도 검증이 아니다. `ready_for_training`, `scientific_accuracy_validated`, `source_authenticity_verified`, `exact_row_binding_verified`, `execution_authorized`, `settlement_authorized`, `automatic_resume_allowed`, `training_split_leakage_resolved`는 모두 정확히 false여야 한다. 저장 보고서 기준이며 현재 원본 파일 재검증을 요청하지 않는다. 학습·수집·다운로드·작업 제출·자동 재개·정산 API를 호출하지 않는다.

HTTP400 입력형식, 409 고정핀 충돌, 413 본문크기, 429 진단 진행/한도, 503 리소스 미사용, 401/403 인증, 404 API/자료 부재를 구별한 안전한 한국어 문구를 사용한다. 서버 오류의 원문 message나 경로를 표시하지 않는다. 오류가 나도 핀을 자동 변경하거나 재시도하지 않는다.

입력 변경·수동 재조회는 세대를 증가시키고 이전 결과/오류를 즉시 지운다. 요청 세대·입력 key·현재 hash가 모두 같을 때만 응답을 표시한다. popstate/hashchange와 unmount는 이전 응답을 무효화한다. AgentCenter 선택 Agent·호환 모델·Job ID·Registry 재조회 변경도 keyed remount로 상태를 지운다. 기존 저장 보고서·원본·Job·승인 상태는 변경하지 않는다.

## 검증·인계

신규 adapter 시험은 명시3핀, 잘못된 핀·토큰 SHA, 8개 false flag의 변조, unknown/schema/scope/추가필드, bool/음수/분수/비유한 계수, null 상태 계약, 계수 교차 모순, 입력/세대/메뉴 경합, 오류 분리와 토큰 원문 hash를 검증한다. 전체 UI 시험과 production build의 최종 수치는 후속 절에 기록한다.

로그: `evidence/integration/readiness-source-identity-ui-adapter-20261017.log`, `evidence/integration/readiness-source-identity-ui-tests-20261017.log`, `evidence/integration/readiness-source-identity-ui-build-20261017.log`.

소스: `frontend/src/ReadinessSourceIdentityDiagnostics.tsx`, `readinessSourceIdentityAdapter.ts`, `readinessSourceIdentityAdapter.test.mjs`, `readiness-source-identity.css`, AgentCenter의 import/render 최소 연결. `api.ts`·backend·원본 데이터는 UI 담당이 수정하지 않는다. API 실제 실행 서버 적용과 브라우저 확인은 root가 수행하며, 이해자료·운영 원장·인계는 root가 별도 담당과 통합한다.


## 최종 프론트 검증

신규 어댑터 10/10 PASS, 전체 UI 59/59 PASS / 0 FAIL / 0 SKIP, 1317.2334ms. 전체 UI에는 이전 경로·storage·Job/Workflow/계보 진단 검증도 포함한다. 이 수치는 합성 경계 시험이며 실제 저장보고서 28/400/28 관측·현재 파일 검증으로 합산하지 않는다. TypeScript + Vite production build PASS / 72 modules / 16.95s. JS 1,527.31kB(gzip 431.29kB), CSS 169.84kB(gzip 31.18kB)이며 기존 500kB chunk 경고만 있다. 이 build는 코드 검증이며 실행 중 API의 route 적용이나 실제 브라우저 수동조회 성공을 뜻하지 않는다. root가 서버 배선·실제 브라우저 결과를 별도 확인한다.


## 실제 서버 적용·브라우저 검증

Root가 API 8002에 배선한 뒤 UI 5174의 `#/view/24?model=lcluc&tab=evidence`에서 실제 수동 조회를 확인했다. 근거는 `evidence/integration/readiness-source-identity-ui-live-20261017.json`이다. 카드 최초 표시에는 결과가 없었으며 명시 조회의 실제 HTTP200 응답에서 조회 회원28 / 넓은 후보 연결400 / 선언 유일대조 회원28 / 0패치 장면3 / 적격 패치25 / 전체·완전선언 장면1384 / 저장 차단5를 관측했다. 이는 저장된 선언 대조의 관측이며 현재 원본 재검증·원본 인증·정확한 원본 행 연결·학습 승인과 다르다.

입력 핀을 변경하면 결과가 즉시 제거되고, 잘못된 보고서 핀은 HTTP409의 안전한 한국어 안내를 표시했다. 최신 보고서로 자동 교체하지 않았다. 브라우저 뒤로는 모델 허브에 오류 없이 도착했고, 앞으로로 evidence 화면에 돌아왔을 때 이전 진단은 폐기되고 명시 고정 핀 예시가 복원됐다. 실제 브라우저의 명시 진단 POST는 3회로 기록했으며, 이 브라우저 상태 관측을 전체 네트워크 요청 재고의 증명으로 확대하지 않는다.

모바일 요청 viewport 390×844에서 수동 성공 결과를 확인했다. 문서 client/scroll 폭은 모두375px, 카드 폭은 약315.57px로 문서 가로 넘침이 없었다. 임시 viewport는 기본값으로 복원했고 성공 결과를 표시한 탭을 유지했다. 콘솔 오류0건을 확인했다.

실제 근거 파일은 `readiness-source-identity-ui-desktop-20261017.jpg`, `readiness-source-identity-ui-mobile-20261017.jpg`, `readiness-source-identity-ui-success-dom-20261017.txt`, `readiness-source-identity-ui-error-dom-20261017.txt`, `readiness-source-identity-ui-console-20261017.json`이며 모두 `evidence/integration/`에 있다. 독립 UI 어댑터10 PASS /447.0061ms는 `readiness-source-identity-ui-independent-20261017.log`에 기록됐다. Root의 전체 backend 회귀652건/651PASS/1SKIP/258.461초는 별도 근거이며 UI59시험과 합산하지 않는다.

이번 화면 조회는 새 assess·원본 검사·Job·학습·수집·다운로드를 시작하지 않았다. 원본 진실성 인증이나 정확한 원본 행 연결을 주장하지 않았다. 이 실제 적용 절 반영 후 UI 소스 수정·재빌드는 없으며 관련 이해자료·운영 원장·인계의 최종 통합은 root 담당이다.
