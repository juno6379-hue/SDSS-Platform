# Gate Current Input Preflight UI 20261017 — 저장 조회와 현재 재검증의 구분

| 필드 | 값 |
|---|---|
| updated_at | 2026-10-17 23:36 KST — Git 상태 메타데이터 정정; 본문은 해당 Gate 기준 |
| source_commit | d474d5bce6c2a6c4bd8ba141c9256d15f6004631 (108까지 구현 검토 기준; 이 메타데이터 정리는 후속 문서 커밋) |
| evidence_paths | `backend/app/stored_current_binding_preflight_api.py`; `tests/test_stored_current_binding_preflight_api.py`; `docs/implementation/84_current_input_preflight_api.md`; `evidence/integration/current-input-preflight-api-related-20261017.log`; `evidence/integration/stored-current-binding-api-independent-20261017.log`; `evidence/integration/current-input-preflight-live-api-20261017.json`; `docs/implementation/85_current_input_preflight_ui.md`; `frontend/src/CurrentInputPreflight.tsx`; `frontend/src/currentInputPreflightAdapter.ts`; `frontend/src/currentInputPreflightAdapter.test.mjs`; `frontend/src/current-input-preflight.css`; `frontend/src/StoredExecutionBindingCapture.tsx`; `evidence/integration/current-input-preflight-live-ui-20261017.json`; `evidence/integration/current-input-preflight-ui-desktop-20261017.jpg`; `evidence/integration/current-input-preflight-ui-adapter-20261017.log`; `evidence/integration/current-input-preflight-ui-tests-20261017.log`; `evidence/integration/current-input-preflight-ui-independent-20261017.log`; `evidence/integration/current-input-preflight-ui-build-20261017.log`; `evidence/integration/current-input-preflight-full-tests-20261017.log`; `evidence/integration/current-input-preflight-live-integrity-20261017.json` |
| confidence | API 소스·합성시험·실제 legacy HTTP; 현재 positive와 busy/cancel은 합성 범위 |
| status | VERIFIED_REAL: API·UI legacy 조회 범위; TESTED_SYNTHETIC: current positive/busy/cancel; 학습·실행 BLOCKED |

## 쉬운 설명

예전 주문 메모를 보는 것과 지금 창고의 재료를 다시 검사하는 것은 다르다. 새 API는 현재 검사를 명시적으로 요청하는 통로다. 저장된 메모, 현재 재료의 지문과 품질 표시, 두 목록의 일치를 따로 보여준다. 옛 메모가 없으면 현재 값을 과거 기록으로 채우지 않는다. 검사를 시작한 뒤 화면을 떠나도 창고의 실제 검사가 바로 멈추는 것은 아니다.

## 이론적 배경

저장 조회 GET은 제출 때 남긴 metadata를 검증한다. `GET /v1/jobs/{job_id}/input-preflight`는 83의 비실행 검사를 호출할 수 있다. RECORDED 경로는 Registry와 현재 자산 hash를 실제로 읽으므로 저장 조회와 비용이 다르다. 과거 기록이 없으면 UNKNOWN/current NOT_RUN이며 개수는 null이다. null을 정상 0개로 표시하지 않는다.

세 축은 저장 기준의 유효성, 현재 integrity·quality/PUBLIC 진단, 저장 대비 현재 선언이다. 품질 차단과 pin MATCH가 동시에 가능하며 전체는 BLOCKED다. MATCH도 기관 ACL·모델 준비도·과학·학습·실행 승인과 다르다.

## 코드와 HTTP 계약

`create_stored_current_binding_preflight_router(get_store)`가 route를 만들고 main의 기존 인증을 계승한다. 외부 expected/supplied/경로 입력 없이 Job literal만 받는다. 200은 83 payload 그대로다. `validate_preflight_response`가 직렬화 전에 exact 키·타입·hash·배열 한도와 상태/계수 교차식을 검증한다. raw 추가 키·원문 경로·불일치 metadata는 안전 503으로 닫는다.

| HTTP | 의미 | 다음 행동 |
|---:|---|---|
| 200 | MATCH/BLOCKED/UNKNOWN 진단 | 실행 승인이 아닌 상태를 읽는다 |
| 400 | 지원 밖 Job literal | 입력을 수정한다 |
| 404 | Job 없음 | 식별자를 확인한다 |
| 429 | PREFLIGHT_BUSY, retryable true | 실제 작업 종료 뒤 명시적으로 다시 조회한다 |
| 503 | 자원·응답 형식 검증 실패 | 원문 오류 없이 안전 안내를 읽는다 |

200과 안전 오류에는 no-store를 붙이고 429에는 Retry-After: 1을 붙인다. 인증 오류는 기존 정책을 따른다. POST는 지원하지 않는다. 현재 input은 최대 64개, current blocker는 최대 768개, inner issue는 최대 512개지만 전체 자산 바이트나 메모리 상한이 아니다.

integrity 실패는 blocker의 입력 index 합집합으로 센다. 같은 입력의 여러 실패를 여러 입력처럼 세지 않는다. quality 관측도 metadata 누락 index를 제외해 계산한다. quality 진단 true는 전체 metadata 관측과 관련 차단 부재의 양방향 조건이다. current capture RECORDED는 같은 pass의 전 입력 integrity 확인과 일치해야 한다. nested 81 guard의 IO 0은 순수 대조 범위다.

## 단일 검사와 표시 중단

worker 안에서 process/router instance별 semaphore 1개를 획득한다. 검사와 응답 검증이 실제로 끝난 뒤 finally에서 해제한다. 요청 coroutine이 취소돼도 worker가 끝나기 전에는 다른 검사가 429를 받는다. 다른 프로세스를 전역 잠그거나 실행 중인 파일 읽기를 강제 취소하는 장치는 아니다.

화면의 표시 중단이나 이동은 서버 취소를 뜻하지 않는다. 전체 파일 byte·누적 IO·CPU·시간·RAM hard cap이나 TOCTOU·원자적 snapshot을 보장하지 않는다. 직접 입력만 대상이며 전이 계보·기관·과학·학습·실행 승인은 모두 별도다.

## 검증 증거와 UI 진행 상태

관련 API 13 PASS/3.779초·독립 13 PASS/3.747초다. 합성 환경에서 MATCH, 품질 차단+pin MATCH, 정확한 schema/계수, 인증·오류·privacy, busy/취소 뒤 lock 유지와 해제 후 재사용을 확인했다. 실제 운영 current MATCH·품질 BLOCKED·busy/cancel 성공으로 확대하지 않는다.

실제 API8002에서는 legacy 두 건이 200 UNKNOWN/current NOT_RUN이었다. 새 조회와 기존 응답 대조·오류를 포함한 11 GET과 변경 전 baseline 6 GET은 별도다. 기존 저장 조회·status·input-resolution 6응답은 baseline과 같았다. missing 404·과대/control 400·no-store를 확인했고 카탈로그 14기록과 기존 Job 본문도 같았다. legacy resolver 0·운영 POST/역채움 0이다.

UI85는 완료 코드·시험·build·실제 데스크톱 legacy 조회로 확인했다. 현재 positive/busy/cancel은 합성 범위이며 모바일은 이번에 실행하지 않았다. 기존 준비성 원본 5차단·후보 4차단은 유지한다.

## 1분 발표

“저장 메모 조회와 현재 입력 재검증을 나누었습니다. 새 통로는 현재 파일의 지문과 품질 표시를 다시 확인하고 저장된 선언과 비교합니다. 옛 기록이 없으면 현재 값을 역채우지 않고 모름으로 표시합니다. 목록이 같아도 품질이 부족하면 차단하고 일치해도 실행 승인은 아닙니다. 실제 기존 두 Job은 미기록이라 현재 검사를 하지 않았습니다. 검사 중 화면을 떠나는 것은 표시 중단이며 실제 서버 작업의 즉시 취소는 아닙니다.”

## 5분 발표 순서

1. **0~1분:** 주문 메모 조회와 현재 창고 검사의 차이를 설명한다.
2. **1~2분:** 저장·현재 진단·선언 일치의 세 축과 null을 설명한다.
3. **2~3분:** 명시 요청과 HTTP 상태·단일 worker·표시 중단의 의미를 설명한다.
4. **3~4분:** 합성 positive/busy와 실제 legacy 조회·UI 근거를 나눈다.
5. **4~5분:** 실제 IO 비용·상한의 한계와 실행·과학·기관 승인의 경계를 말한다.

10분 설명에서는 exact 응답 검증, index 합집합 계수, 같은 pass capture 정합과 프로세스별 semaphore 범위를 추가한다.

## Q&A

**새 조회는 저장 기록 보기와 같은가?** 다르다. 유효한 저장 기록이 있을 때 현재 Registry와 자산을 다시 검사할 수 있다.

**UNKNOWN이면 입력이 0개인가?** 아니다. 과거 근거가 없어 현재 검사를 하지 않은 경우이며 계수도 미확인이다.

**화면을 떠나면 작업이 멈추나?** 표시를 중단한다. 실제 worker가 끝날 때까지 단일 검사 lock은 유지된다.

**MATCH면 학습해도 되나?** 아니다. 직접 입력의 제한된 진단이며 과학·기관·모델 준비도 승인은 별도다.

**실제 정상 자산과 busy를 관측했나?** 해당 성공과 경합은 합성 검증이다. 실제 기존 두 Job은 legacy였다.

## 이후 갱신

UI85·전체 회귀·보존 근거를 읽고 INDEX·변경 이력·계약·구조·06·발표·FAQ와 함께 갱신했다. 다음 기능은 별도 인계 전 PLANNED로만 표시한다. 전체 개발과 10분 보고는 계속된다.


## UI 연결과 실제 적용

기존 저장 capture 카드 아래 `CurrentInputPreflight` child를 독립 연결했다. 같은 표준 Job ID를 쓰되 저장 조회를 먼저 누를 필요가 없다. 입력만으로 조회하지 않고 “현재 직접 입력 다시 검증” 버튼으로 GET 한 번을 보낸다. 저장 조회의 성공·실패·busy 상태가 현재 결과를 대신하거나 자동 검사를 시작하지 않는다.

UI는 기존 SVG와 scoped CSS를 쓴다. WebCrypto로 Job literal 지문을 비교하고 exact 응답·false flags·계수와 상태를 검증한다. 입력·Agent·Registry·메뉴/뒤로 이동·hash·요청 세대가 바뀌면 결과를 폐기한다. 늦은 응답을 표시하지 않는 것은 서버 취소가 아니다. API보다 좁은 ASCII 영문·숫자·밑줄·하이픈 1..200자만 지원하고 공백을 자동 제거하지 않는다.

실제 UI5174/API8002의 1449×1087 데스크톱에서 legacy UNKNOWN과 세 축·null의 미확인 표시, 저장 GET과 결과 독립, 입력·Agent·Registry 변경 및 뒤로/앞으로 이동 시 결과 제거, 빈 값·공백 차단, 없는 Job 404를 확인했다. 문서와 패널 가로 넘침은 0, 콘솔 오류는 없었다. 실제 current MATCH/BLOCKED·busy/cancel·강제 지연 경합·모바일은 이번 브라우저 확인 범위가 아니다. 원래 UI5173의 새 API 적용을 검증한 것도 아니다.

## 최종 시험과 보존

최종 backend 전체 869건 중 868 PASS·기존 Windows symlink 권한 제약 1 SKIP, 389.808초·종료 0이다. deterministic 경계시험은 통과했다. 관련 API 13개·독립 13개는 반복 검증으로 합산하지 않는다.

신규 UI 14 PASS/1802.7215ms, 전체 UI 100 PASS/2384.4127ms, 독립 신규 14 PASS/1609.1864ms다. production build는 81 modules/18.96초 PASS이며 기존 chunk 크기 경고가 있다. 코드·시험·build와 실제 개발 서버/브라우저의 적용 근거는 구분한다.

시험 종료 후 보호 참조 141개·기존 코어 45개·카탈로그 14기록과 기존 Job 본문이 같았다. 기존 추적 코드 변경은 허용한 main.py 배선과 StoredExecutionBindingCapture.tsx child 연결 두 파일뿐이다. 전체 워크스페이스 불변이나 원자 snapshot 보장은 아니다. 운영 POST·역채움·새 QA·학습·실행기 연결은 없다.
