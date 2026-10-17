# Gate Source Identity API·UI 20261017 — 저장 진단의 명시 읽기 조회

| 필드 | 값 |
|---|---|
| updated_at | 2026-10-17 23:36 KST — Git 상태 메타데이터 정정; 본문은 해당 Gate 기준 |
| source_commit | Git 연결됨; 문서 작성 시 변경분 미커밋, evidence snapshot SHA로 추적 (원격 기준 d483d25) |
| evidence_paths | `backend/app/readiness_source_identity_api.py`; `frontend/src/ReadinessSourceIdentityDiagnostics.tsx`; `docs/implementation/68_readiness_source_identity_ui.md`; `backend/app/main.py`; `tests/test_readiness_source_identity_api.py`; `frontend/src/AgentCenter.tsx`; `frontend/src/readinessSourceIdentityAdapter.ts`; `frontend/src/readinessSourceIdentityAdapter.test.mjs`; `frontend/src/readiness-source-identity.css`; `docs/implementation/67_readiness_source_identity_api.md`; `evidence/integration/readiness-source-identity-api-related-20261017.log`; `evidence/integration/readiness-source-identity-api-independent-20261017.log`; `evidence/integration/readiness-source-identity-api-live-20261017.json`; `evidence/integration/readiness-source-identity-api-ui-full-tests-20261017.log`; `evidence/integration/readiness-source-identity-ui-adapter-20261017.log`; `evidence/integration/readiness-source-identity-ui-tests-20261017.log`; `evidence/integration/readiness-source-identity-ui-build-20261017.log`; `evidence/integration/readiness-source-identity-ui-independent-20261017.log`; `evidence/integration/readiness-source-identity-ui-live-20261017.json`; `evidence/integration/readiness-source-identity-ui-console-20261017.json`; `evidence/integration/readiness-source-identity-api-ui-live-integrity-20261017.json` |
| confidence | 코드·전체/독립로그·실제 API/브라우저 근거; 과학·운영 승인 아님 |
| status | TESTED_SYNTHETIC: API/UI·회귀; VERIFIED_REAL: 5174/8002 명시 저장조회; 학습 BLOCKED |

## 쉬운 설명

두꺼운 검사 원장을 그대로 내려받는 대신, 사용자가 검사표 지문과 제품표식을 명시해 요청하면 필요한 숫자만 작은 창으로 읽는다. 읽기 조회는 새 검사를 시작하거나 학습을 승인하지 않는다. 화면을 열었다고 자동 조회하지 않고 버튼을 누를 때만 저장된 진단을 읽는다.

## 이론적 배경

66의 실자료 진단 파일은 경로·행·토큰 등 많은 내부 정보를 담는다. 조회 API는 기존 읽기 코어 결과를 고정 allowlist로 투영해 내부 경로·원본행·원문 JSON을 노출하지 않는다. 입력 핀을 명시하면 다른 보고서로 조용히 바뀌는 일을 피하고, 상태/계수/false flags를 프론트에서도 다시 검사하면 잘못된 응답을 성공으로 표시하지 않는다. 저장된 관측의 조회와 현재 원본 파일 재검증은 구분한다.

## 코드·API 사용 계약

`POST /v1/diagnostics/readiness-source-identity`의 본문은 정확히 report_sha256·manifest_sha256·token 세 키다. report는66의 고정 파일, manifest는 기존 고정 aggregate를 사용한다. 호출자가 임의 경로나 latest 탐색을 지정할 수 없다. 두 SHA는 소문자64hex이고 token은 API에서 최대4096문자, 본문은8KiB·JSON깊이8로 제한한다. API worker는 threadpool에서 실행하며 process-local semaphore1로 동시에 하나만 읽고 초과 요청은429로 알린다. 여러 프로세스 전체의 전역 동시성 제한은 아니다.

`project_readiness_source_identity`는 기존 코어의 상태·참조핀·회원/후보 계수·미실행 flags를 재대조해12개 계수, 보고서/manifest SHA, token UTF8 SHA, 진단 상태와8개 비승인 false flags만 반환한다. raw token·이미지 경로·원본행 index·원본 JSON은 반환하지 않는다. HTTP200도 status BLOCKED이며 저장된 선언 관측만을 뜻한다.

| 상태/오류 | 의미 |
|---|---|
| OBSERVED_DECLARATIONS | 선언 객체가 있는 저장 관측 |
| SOURCE_IDENTITY_NOT_PROVIDED | 저장 보고서에 선택적 객체 없음; 관련4계수null |
| SOURCE_IDENTITY_NOT_CAPTURED | 알려진 단서 생성 실패; 관련4계수null |
|400 INVALID_REQUEST | 요청 형식 오류 |
|409 PINNED_INPUT_CONFLICT | 고정 입력 충돌/변경 |
|413 REQUEST_TOO_LARGE |8KiB 초과 |
|429 DIAGNOSTIC_BUSY | 진단 읽기 사용 중; Retry-After1 |
|503 RESOURCE_UNAVAILABLE | 자료/진단 사용 불가 |

이 라우터가 처리한 성공/오류는 Cache-Control no-store이고 오류는 안전한 코드·고정 문구·retryable만 반환한다. POST 외 기본405처럼 프레임워크가 처리하는 응답은 이 계약과 별도다. 경로가 포함된 예외 원문을 응답하지 않는다. 이 API는 현재 원본 영상/라벨 재hash·assess·Job 생성·학습·수집·재개·정산을 하지 않는다. 두JSON은 전후 검사와 저장계수 확인을 위해 여러 번 읽으며 상한 예산은 manifest64MiB×2+report16MiB×3=176MiB다. 이는 두 파일을 한 번만 읽거나 다중 파일 원자적 snapshot을 보장하는 계약이 아니다.

## UI 동작

Agent Center의 ‘저장된 출처 대조 진단’ 카드에서 핀/제품 token을 명시하고 조회 버튼을 누른다. UI token 범위는 ASCII 영문·숫자·밑줄·하이픈1..256자로 API보다 좁다. token 공백을 조용히 제거하지 않는다. 화면 진입·선택·렌더·이동으로 자동 호출하지 않는다.

어댑터는 정확한 응답 키/상태·schema·핀·token SHA·12개 계수·8개 false flags와 계수 간 모순을 검사한다. 조회회원·넓은후보연결·선언유일회원·0patch장면·패치수와 기존 저장 차단5를 구분한다. 기대값28/400/28/3/25를 성공으로 하드코딩하지 않고 검증된 응답만 표시한다. BLOCKED와 선언 유일성≠원본 인증 문구를 함께 보여준다.

입력·수동 재조회·선택 Agent/모델/Job·Registry 재조회·메뉴/브라우저 이동 때 이전 결과를 지우고 세대/입력key/hash가 같은 응답만 표시한다. 오래된 성공·실패 응답이 새 입력 결과를 덮지 않게 한다. 오류 원문이나 경로를 표시하지 않고 자동 핀 대체/재시도를 하지 않는다. 기존 SVG 스타일·공통 화면 구조를 사용한다.

## 시험 증거

완료 인계 기준 API14 PASS/6.055초, 신규 UI10 PASS/302.8698ms·전체 UI59 PASS/1317.2334ms·build72modules/16.95초다. 이는 합성 경계와 빌드 근거이며 실행 중 서버 적용·실제 브라우저 확인과 구분한다. Root가 실제 첫 요청에서 보고서 경로 전달 누락으로409를 발견해 수정/회귀검사를 수행했으므로 최종 근거는 후속 실제 재조회 결과를 사용한다. API 독립14 PASS/4.934초와 신규 UI 독립10 PASS/447.0061ms도 읽었다. 최종 전체 scripts/test.ps1은652건 중651 PASS·1 SKIP/258.461초/종료0이다. SKIP은 기존 Windows symlink 생성권한이며 deterministic 경계 시험은 통과했다. 관련/독립/프론트 시험 반복을 전체652에 중복 합산하지 않는다. 이해 에이전트는 API/브라우저를 조작하거나 시험을 실행하지 않는다.

## 한계·보존

선언 유일후보는 정확 원본행·파일/제품 진실·누출 해결·과학성능·학습 승인 인증이 아니다. 새 API가 현재 원본을 다시 검사하거나 이전 과거 원인을 복원하지 않는다. 실제66의 영상/라벨 읽기와 이번 저장JSON 조회를 구분한다. 기존5차단·패치628/233/250·terminal2missing·예약136,314,880B·환불0·모델/분할·과학/실행/정산 승인false를 유지한다.

이번은 UI 영향 기능이므로 web_ui 화면 연결·프론트 검증·실제 브라우저·실행서버 적용의 근거를 각각 확인한 뒤 완료 상태를 확정한다. 전체 개발과10분 보고는 지속한다.

## 발표 1분

“저장된 출처 대조 진단을 Agent Center에서 직접 조회하도록 읽기 API와 카드를 연결했습니다. 사용자가 고정 보고서 지문과 제품표식을 명시해 버튼을 눌러야 조회하며, 큰 원문이나 이미지 경로 대신 필요한 숫자만 전달합니다. 넓은 후보와 별도 선언 유일후보,0패치와 패치 수·기존 학습 차단을 구분해 보여줍니다. 입력이나 선택이 바뀌면 이전 응답을 지워 다른 조건의 결과가 남지 않게 했습니다. 저장된 관측을 읽는 기능이며 현재 원본 재검사나 학습 승인은 아닙니다.”

## 발표 5분·10분

1. **0~1분:** 두꺼운 원장과 작은 명시 조회창 비유를 설명한다.
2. **1~2분:** 고정 핀·token과12계수/8false 투영·원본경로 비노출을 설명한다.
3. **2~3분:** Agent Center 수동 조회·입력/선택 변경과 오래된 응답 차단을 보여준다.
4. **3~4분:** 합성시험/빌드와 실제 API/브라우저·전체/보존 근거를 구분한다.
5. **4~5분:** 저장 관측·singleton 미인증·5차단 유지·운영/과학 승인 한계를 말한다.

10분 확장에서는 null 상태와0 차이·8KiB/단일worker/429·no-store·UI/API token범위 차이·초기409 수정/회귀·실행서버 포트를 설명한다.

## Q&A

**조회하면 새 assess나 학습이 시작되나?** 저장된 두JSON 읽기만 수행하며 새 assess/Job/학습을 시작하지 않는다.

**원본 경로도 볼 수 있나?** 응답과 화면은 고정 allowlist 계수/해시만 사용하며 원본경로·행index·큰JSON을 반환하지 않는다.

**화면을 열면 자동으로 읽나?** 명시 버튼만 호출하며 이동·선택·입력변경 때 이전 결과를 무효화한다.

**28유일후보면 학습 가능한가?** 선언 일치이며 인증false·기존5차단 BLOCKED를 함께 표시한다.

**200이면 모두 정상인가?** 조회 성공이며 status는BLOCKED다. 저장된 관측이 현재 파일·과학/운영 승인으로 승격되지 않는다.

## 이후 갱신

실제 API/브라우저·전체/보존 최종근거를 읽고 INDEX·변경 이력·구조/계약/GeoLLM·대본/FAQ/시연을 함께 갱신했다. 기존 서버 적용과 빌드 성공을 구분한다.

## 실제 API·실행서버·브라우저 관측

실제 API8002의 POST는200·1,065bytes/18.797초였고12계수/8false/no-store를 반환했다. bool핀400·틀린핀409·초과본문413은 안전한 오류/no-store였고 GET405는 프레임워크 기본 응답으로 별도다. 초기409 원인은 새 report_path 누락이었고 수정·회귀 이후 이 최종 관측이 성공했다. 처음 실패 기록을 성공 근거로 사용하지 않는다.

Root 실제 화면 주소는 `http://127.0.0.1:5174/#/view/24?model=lcluc&tab=evidence`이며 동일출처 개발 proxy로 API8002에 연결한다. 기존5173/8000/8001에 새 기능이 적용됐다고 주장하지 않는다. Root가 최초 결과 없음→명시조회→28회원/400넓은연결/28유일선언회원/0patch3/patch25·장면/완전선언1384·저장차단5 표시를 확인했다. 입력 변경 결과 제거·틀린핀409 안전안내·허브 back 후 forward에서 이전 결과 폐기도 확인했다. 이 브라우저 관측은 전체 네트워크 요청 전수 목록의 증명은 아니다.

모바일 요청390×844에서 document client/scroll 폭375/375·카드 약315.57로 수평넘침이 없었다. viewport를 복원하고 성공 결과가 있는 탭을 유지했으며 console error0이다. 실제 스크린샷·DOM·콘솔 기록을 근거로 읽었고 이해 에이전트가 브라우저를 조작하지 않았다. 새 source assess·Job·학습·다운로드는 시작하지 않았다.

### 67/68 최종 보존·다음 계획

최종 보존은134참조·25기존 계약SHA와 카탈로그14기록(기존 gmais_jobs2개 포함)의 canonical records SHA불변을 확인했다. 이전에 추적한 코드/데이터/프론트 중 바뀐 것은 의도한 main 배선과 AgentCenter 두 파일이며 신규 파일을 포함한 전체 workspace 변경이2개뿐이라는 뜻은 아니다. main은 두 배선 줄을 제외하면 raw baseline과 같았다. 새 source assess·Job·학습·수집/다운로드를 실행하지 않았고 저장5차단·패치628/233/250·원본 분할·모델·예약136,314,880B·환불0을 유지했다. 보존 검사는 원자적 snapshot이나 전체workspace inventory 보장이 아니다.

다음 PLANNED 단위는 원본을 보존하는 신규 Dataset 버전 후보 계획에 기존 split repair plan과 최신 진단 핀을 연결하고 클래스 부족을 명시하는 내부 작업이다. 후보계획일 뿐 발행·원본삭제·분할/gate변경·다운로드·훈련·자료준비완료가 아니다. 이번 저장조회 UI 완성과 전체 ML/프로젝트 완료를 구분한다.
