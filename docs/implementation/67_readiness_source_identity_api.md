# 67. 저장된 출처 대조 진단 최소 읽기 API

상태: **VERIFIED_REAL(고정 저장 보고서의 실제 API·수동 UI 조회)**. 요청·투영·동시성 합성 시험은 TESTED_SYNTHETIC이며 생산 배선·실제 HTTP·브라우저 근거를 아래와 문서68에 구분한다. 이 API는 저장된 JSON의 선언 단서를 보여주며 현재 원본 영상 인증, 적격성 재판정, 학습 승인 또는 차단 해제를 수행하지 않는다.

## 구현과 입력

`backend/app/readiness_source_identity_api.py`의 `create_readiness_source_identity_router(get_store)`를 Root가 FastAPI에 연결한다. Store에서는 `root`만 읽는다. 저장/복구/Job/원장 작업을 호출하지 않는다.

`POST /v1/diagnostics/readiness-source-identity`의 JSON 키는 정확히 `report_sha256`, `manifest_sha256`, `token`이다. SHA는 소문자 64자리 hex, 토큰은 원문 문자열 최대 4,096자다. 토큰을 trim하거나 추정하지 않는다. 스트림을 읽으며 8,192바이트를 넘으면 413으로 중단한다. 파싱 전 깊이 8을 제한하고 엄격한 UTF-8, 중복 키, 비유한 수, 추가 키, 잘못된 타입을 거부한다. UI의 ASCII 1~256자 제품 토큰 입력은 API보다 좁은 지원 범위다.

클라이언트는 파일 경로를 지정할 수 없다. DATA root 안의 다음 두 JSON만 사용한다.

- `first-group/readiness-source-identity-20261017.json`
- `first-group-training-esri-v1/annual-window-report.json`

기존 lineage 코어를 `max_members=2000`, `max_candidates=1000`, 명시적인 새 보고서 경로로 호출한다. 초기 구현에서 경로를 생략하면 코어 기본값인 이전 보고서를 읽어 새 SHA와 충돌하는 409가 발생했다. 새 경로를 명시하고 서로 다른 이전/새 보고서 바이트를 가진 합성 회귀로 보완했다. 이전 보고서와 실제 입력은 수정하지 않는다.

## 정확한 응답 계약

최상위 키는 다음과 같다. 코드의 `REQUEST_SCHEMA`, `RESPONSE_SCHEMA`, `ERROR_SCHEMA`가 OpenAPI에 연결되어 있다. 응답 투영은 정해진 키만 생성하며 원문 토큰·파일 경로·장면 배열·거대한 JSON을 반환하지 않는다.

```json
{
  "schema_version": 1,
  "status": "BLOCKED",
  "diagnostic_status": "OBSERVED_DECLARATIONS",
  "scope": "PINNED_STORED_REPORT_DECLARATIONS_ONLY",
  "report_sha256": "소문자64hex",
  "manifest_sha256": "소문자64hex",
  "query_token_sha256": "원문토큰 UTF8 SHA256",
  "counts": {},
  "output_truncated": false,
  "ready_for_training": false,
  "scientific_accuracy_validated": false,
  "source_authenticity_verified": false,
  "exact_row_binding_verified": false,
  "execution_authorized": false,
  "settlement_authorized": false,
  "automatic_resume_allowed": false,
  "training_split_leakage_resolved": false
}
```

`counts`의 정확한 12개 키와 상한:

| 키 | 상한/의미 |
|---|---|
| scene_count | 2,000; 적격 패치 합계와 다름 |
| complete_identity_scene_count | 2,000; 완전한 선언 path/hash 쌍이 있는 장면 수 |
| saved_blocker_count | 10,000; 저장 보고서 blocker 배열 길이 |
| query_member_count | scene_count 이하; 원문 토큰 일치 회원 |
| query_active_token_member_count | query_member_count 이하; falsy group 스킵 반영 |
| query_zero_patch_scene_count | query_member_count 이하; 0패치 회원 |
| query_eligible_patch_count | 9,007,199,254,740,991; 회원의 패치 합계 |
| broad_candidate_link_count | 200,000,000; 기존 province/group/id 후보 연결 수 |
| broad_unique_raw_row_count | 100,000; 기존 고유 원본 후보 행 수 |
| refined_candidate_link_count | 200,000,000; 선언 path/hash로 좁힌 연결 수 |
| refined_unique_raw_row_count | 100,000; 좁힌 고유 원본 후보 행 수 |
| refined_unique_member_count | 2,000; 선언 메타데이터 단일 후보 회원 수 |

`OBSERVED_DECLARATIONS`에서는 모든 계수가 정수다. `SOURCE_IDENTITY_NOT_PROVIDED`와 `SOURCE_IDENTITY_NOT_CAPTURED`에서는 complete 계수와 refined 3계수가 정확히 null이며, 존재하지 않는 진단을 0이나 성공으로 만들지 않는다. 일부 선언이 부족해도 나머지 선언은 관측할 수 있다. 단일 후보는 파일 인증·정확한 원본 행 결합을 뜻하지 않는다.

projection은 exact bool/int, scene/member 유일 index와 순서, 회원 수/활성/0패치/패치 합계, broad/refined 합계 및 교차상한을 검증한다. refinement v1, lexical protocol, refinement reason과 match status의 일관성, unknown일 때 원후보 보존, 모든 false/0 비실행 주장을 검증한다. 잘림은 `output_truncated`로 보존한다. 원문 코어의 전체 이벤트 재연산이나 GEOS/영상 검사는 하지 않는다.

## 오류·동시 실행·읽기 예산

응답과 처리한 오류에는 `Cache-Control: no-store`를 붙인다. GET 경로는 제공하지 않는다(프레임워크 기본 405 응답은 별도). 오류 JSON은 정확히 `{"error":{"code":"...","message":"고정 안전 안내","retryable":false}}` 형식이다. 예외 문자열과 절대 경로는 노출하지 않는다.

| HTTP | code | retryable |
|---|---|---|
| 400 | INVALID_REQUEST | false |
| 413 | REQUEST_TOO_LARGE | false |
| 409 | PINNED_INPUT_CONFLICT | false |
| 503 | RESOURCE_UNAVAILABLE | false |
| 429 | DIAGNOSTIC_BUSY | true (`Retry-After: 1`) |

검사는 threadpool에서 수행하며 라우터 인스턴스당 무거운 작업 1개만 허용한다. 세마포어는 실제 worker 내부에서 획득/해제하므로 HTTP coroutine이 취소되어도 읽기가 끝나기 전에 잠금이 풀리지 않는다. 이는 단일 프로세스/라우터의 제한이며 여러 서버 프로세스 전체를 조율하는 분산 잠금이 아니다.

lineage 코어는 두 JSON의 SHA·크기·논리 경로/해석 대상·전후 파일 상태를 확인한다. complete identity 수와 blocker 수를 위해 보고서를 추가로 16MiB 한도 내 읽고 같은 SHA와 경로/상태를 재검사한다. 최대 읽기 예산은 manifest 64MiB×2 + report 16MiB×3 = 176MiB다. 두 파일을 한 번만 읽는 구현이 아니며, 이 검사는 다중 파일의 원자적 snapshot 보증이 아니다. 이미지/헤더/픽셀/출처 파일 SHA·기존 113개 source manifest는 읽지 않는다. 추가 assess, helper 재실행, 다운로드, 학습, 네트워크, 원본/DB/원장/lock 쓰기가 없다.

## 검증과 연결

합성 관련 시험: **14 PASS / 6.055초 / 종료 0**. 명령:

```powershell
$env:PYTHONPATH="$PWD\.runtime;$PWD\backend;$PWD\tests"
python -m unittest test_readiness_source_identity_api -v
```

로그: `evidence/integration/readiness-source-identity-api-related-20261017.log`. 작은 임시 JSON만 사용했다. 테스트는 새 고정 보고서/이전 기본 경로 차이, exact OpenAPI 계약, legacy/미수집 null, 스트림 제한·엄격 JSON, false/typed 계수·refinement 모순, SHA/retarget, 경로 비노출 오류, worker busy·취소 후 해제, 무추가 source IO·입력 바이트 보존, ASCII summary를 확인한다. `httpx`와 Starlette의 기존 의존성 deprecation 경고가 있으나 시험은 통과했다.

UI 담당에게 같은 요청·응답·상한·오류 계약을 인계했다. 화면은 사용자 명시 조회만 제공하며 자동 assess나 자동 조회를 하지 않는다. 기존 gate의 5개 차단, 예약, 분할과 학습 승인은 이 조회로 바뀌지 않는다. 실제 HTTP/실행 서버 적용·브라우저 검증·전체 회귀와 이해자료 갱신은 Root의 종결 증거에 연결한다.


## Root 통합·실제 적용·보존

main.py의 import/include 두 줄만 추가해 API8002 reload에 연결했다. 두 줄을 제거한 원문 bytes SHA가 사전 main 기준과 같음을 확인했다. 기존 API8000/8001 및 UI5173/5174 서버를 중지하지 않았다. UI5174 동일출처 `/v1` proxy→API8002에서 실제 수동조회 결과를 관측했다.

실제HTTP evidence `readiness-source-identity-api-live-20261017.json`: 명시고정 report200/1065B/18.797초, badbool400, wrongpin409/9.625초, 본문8193B는413, GET405. POST응답200/400/409/413 no-store이며 framework GET405는Cache-Control이없다. 예외 원문/원본경로/raw토큰 노출없음, 12계수 및8승인false 확인. worker상한은process별이며여러서버전체공유quota가아니다. 응답시간은이환경관측이며일반성능보장이아니다.

브라우저 evidence `readiness-source-identity-ui-live-20261017.json`/desktop·mobile JPG: LCLUC Workspace 검증·근거 탭에서28회원/400넓은후보/28선언유일/0patch3/patch25/1384장면·완전선언/기존5차단 표시. 입력변경즉시 결과삭제, HTTP409안내, back허브→forwardevidence복귀시이전진단삭제, 모바일390x844 요청(client375/scroll375) 가로넘침0·viewport복원·consoleerror0을확인했다. 성공결과를사용자탭에남겼다. UI가표시한저장진단은현재영상재검증·원본인증·과학/학습승인과다르다.

전체 scripts/test.ps1 **652건/651PASS/1SKIP/258.461초/종료0**. 기존OSsymlink권한 SKIP/deterministic경계 PASS. 관련API14/6.055초·독립14/4.934초, 신규UI10·전체UI59/1317.2334ms·독립신규10/447.0061ms·빌드72모듈/16.95초 통과. 반복/관련시험을전체652에중복합산하지않는다. 기존chunk분할경고는빌드성공과구분한다.

`readiness-source-identity-api-ui-live-integrity-20261017.json`:134보호참조/25기존코어계약SHA·카탈로그14기록(2gmaisJobs)canonicalSHA·고정report/manifest·원본/원장/lock/예약136314880B/분할/모델 그대로. 기존추적code/data/frontend 변경은 main배선과AgentCenter카드삽입 두파일뿐, 나머지는 신규 API/UI·시험파일이다. 이조회에서새assess/수집/학습/다운로드/Job/배포를실행하지않았다. 원자OSsnapshot이나운영ACL확정을뜻하지않는다.
