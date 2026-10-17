# 137 — 인증된 연차 입력 진단 HTTP 연결

상태: **TESTED_SYNTHETIC**. API 담당은 신규 `annual_diagnostics_api.py`·시험·본 문서의 API 부분과 main의 router import/include 두 줄 및 승인된 단일 token 비교의 UTF-8 bytes 보강을 맡았다.136 서비스 및135 이하 진단·실행 gate·기존 main의 optional 인증/401 정책은 변경하지 않는다. UI 담당은 별도 frontend 영역을 맡고 Root가 최종 UI/브라우저·공통 인계를 통합한다.

## 수동 요청과 엄격한 별도 인증

`POST /v1/lcluc/input-diagnostics`는136의 exact6 요청을 application/json으로 받는다. Content-Type의 charset 같은 파라미터는 허용한다. 실제 진단은 명시 요청에만 수행하며 자동 실행·재시도·Job dispatch·승인 쓰기가 없다.

새 router 자체에서 `GEOAI_API_TOKEN`을 요구한다. 미설정·빈/공백 token이면503 AUTH_CONFIGURATION_REQUIRED, 정확한 `Bearer <token>`이 아니면401 AUTH_REQUIRED다. UTF-8 bytes의 constant-time compare_digest로 비교하고 token·원문 Authorization·예외를 로그나 응답에 출력하지 않는다. 기존 main의 optional auth는 그대로이며 이 router의 필수 guard가 추가된다.

실제 main에서는 token이 설정된 경우 기존 global authorized dependency가 router보다 먼저 인증한다. 이때 잘못된 Bearer는 기존 `{detail:...}` HTTP401 형태를 유지한다. router의 HTTP_ERROR 인증 envelope와 선행 global401 형태가 다르므로 UI는 두401을 안전한 인증 실패로 처리하고 원문 detail을 반사하지 않는다. 비ASCII Authorization에 기존 str compare_digest가 TypeError500을 내는 경계는 Root 승인으로 양항만 UTF-8 bytes 비교로 바꿨다. ASCII 비교 결과·선행401·미설정 시 optional 통과·health/ready 예외는 바꾸지 않았고 새 경로를 인증에서 제외하지 않는다.

인증·content-type·body 초과 실패는 Store factory와 서비스를 호출하지 않는다. Content-Length 초과를 사전 거부하고 request.stream의 실제 누적 바이트도16 KiB로 제한한다. chunked body도 같은 상한이다. request disconnect/transport 오류는 고정 RESOURCE_UNAVAILABLE다. 정상136의 INVALID_REQUEST는 worker에서 처리하되 Store.get은0이다.

## 응답 계약과 상태 코드

서비스 정상 요약은136 exact19를 그대로 안전 복사한다. CALLER_POLICY_MET_UNVERIFIED/CALLER_POLICY_NOT_MET/SOURCE_BLOCKED는200, INVALID_REQUEST는422, OUTPUT_INVALID는503이다. policy 충족·미달·source 차단의 의미는136과 같고 QA·기관·실행 flag는 false다.

HTTP 자체 오류는 정확히 다음 세 필드 envelope다.

```json
{"schema_version":1,"scope":"LCLUC_ANNUAL_DIAGNOSTIC_HTTP_ERROR","error":{"code":"AUTH_REQUIRED"}}
```

오류 code/status는 AUTH_CONFIGURATION_REQUIRED503, AUTH_REQUIRED401, REQUEST_TOO_LARGE413, UNSUPPORTED_MEDIA_TYPE415, DIAGNOSTIC_BUSY429, RESOURCE_UNAVAILABLE503이다. 모든 응답은 Cache-Control:no-store와 X-Content-Type-Options:nosniff를 사용한다. busy만 Retry-After:1을 추가한다. 원경로·source exception·token·nested Registry를 오류에 넣지 않는다.

worker 안에서 응답을 검산한다. serialize 전에 exact builtin tree만 수용하고 depth8·node512·dict32키·list6개·문자열/키256자·surrogate 부재·53bit 정수·float/custom type 부재를 요구한다. 로컬 response schema와 status/flag/행/counts/issue 조합도 검사한다. SOURCE_BLOCKED의 issue year는 null 또는 응답 행에 속한 exact int여야 한다. strict 유한 JSON bytes가16 KiB를 넘거나 출력이 잘못되면 fixed RESOURCE_UNAVAILABLE503으로 바꾸고 부모 원문을 노출하지 않는다. schema 구조 통과만으로 정책 산술·과학적 정합을 주장하지 않는다. 정책 정수 재산출은136의 책임이고 route는 요약의 안전한 구조·조합을 추가 확인한다.

## 동시성·취소·worker 경계

프로세스 로컬 BoundedSemaphore(1)를 nonblocking으로 획득한다. 점유 중이면 queue를 만들지 않고429를 반환한다. multi-process/다른 서버 전체의 전역 lock·예약·Job 스케줄러는 아니다.136 서비스와 Store factory 및 출력 schema/JSON 검사는 threadpool에서 실행해 async event loop의 CPU 작업을 피한다.

실제 worker의 finally가 slot을 해제한다. HTTP task는 shield된 worker task를 기다리며, client 표시 취소/연결 중단이 이미 실행 중인 파일 진단의 즉시 중단이나 rollback을 보장하지 않는다. 취소만으로 slot을 풀어 다른 CPU 진단이 겹치지 않도록 한다. background task 예외는 callback으로 소비하며 secret을 기록하지 않는다. queue/cancellation latency·CPU/RSS/시간 SLA나 모든 자원 격리를 주장하지 않는다. 원136/135의 Store predecode·GDAL/Torch·비원자성 한계는 그대로다.

## main 배선과 검증 범위

기존 main에는 `create_annual_diagnostics_router` import와 `app.include_router(create_annual_diagnostics_router(lambda: store))`를 추가하고, authorized의 단일 compare_digest 양항만 UTF-8 bytes로 보강했다. 기존 route·schema·ML writer/실행기와 인증 허용 정책은 변경하지 않았다. 시험은 운영 main을 import하지 않는 isolated FastAPI router를 사용한다. AST 보존 시험은 고정 Git baseline `bec226ec460ca2497e092e34c21c64bd9ab0da99`의 main에 대해 정확한 두 배선 노드 및 지정한 비교 호출 한 곳만 바뀌었는지 확인한다. 함수 전체를 무조건 무시하지 않고 기대한 단일 호출 변경의 AST도 검산한다. 움직이는 HEAD를 baseline으로 사용하지 않는다.

API 시험은 필수 token/잘못된 Bearer·비ASCII 입력·media/stream/Content-Length·초과·disconnect·invalid422/Store.get0·malformed response503·schema·busy nonblocking/RetryAfter·worker exception release·HTTP 취소 후 실행 slot 유지·실제 Temp2년의13get 및 무쓰기를 검증한다. 실제 main의 authorized 함수만 AST로 추출한 별도 앱에서 ASCII/비ASCII401·정상422·미설정 시 router503도 확인한다. mainAST의 baseline 고정과 response key·source year 경계는 새137의 검토 보완이며 기존136 이하 제품 결함 수정이 아니다. 최종 수치·동결 SHA와 Root 관련/전체/브라우저 근거는 완료 후 아래에 반영한다.

API 담당은 frontend를 편집하지 않았다. UI는 요청·정책 수동 입력과 Bearer·응답 검산·취소 표시를 연결하며 Root가 실제 서버 적용과 브라우저 검증을 구분해 최종 인계한다. 운영 모델·원본 자료·원장·예약·분할·Registry를 보존하고 수집·훈련·추론·배포·Job·승인 쓰기는 수행하지 않는다. 이해 담당은 완료된 API/UI 코드·시험·한계를 해설/발표/FAQ/INDEX/변경 이력에 반영한다.

## API 담당 집중 결과와 동결 인계

최종 집중 **11 PASS / 6.292초 / exit 0**는 `evidence/integration/diagnostic-api-agent-20261018-focused-final3.log`다. schema/실제 Temp2년·필수 인증·비ASCII·bounded stream·busy/release·취소·private output·main AST 보존을 확인했다. 운영 main 자체를 import한 검증은 아니며 실제 main의 authorized 함수만 추출한 isolated dependency 검증과 구분한다. 실제 서버/브라우저·기존 route·전체 backend 검증은 Root가 별도로 수행한다.

보완 전 `diagnostic-api-agent-20261018-focused.log`, `-focused-final.log`, `-focused-final2.log`를 보존했다. 이는 단계별 AST baseline 고정·response key/year 경계·main auth bytes 보강 전 근거이며 최종 결과와 합산하지 않는다. framework의 StarletteDeprecationWarning과 Affine PendingDeprecationWarning도 로그에 남겼고 이를 오류나 새 dependency 설치로 처리하지 않았다.

API source SHA `c110dd9c70bfafcb2a7dfdf2ee0f1c0f3b1f30e1b2f7f0c4651eb300cda6dfd8`, main SHA `d5efc3acb269ab1397ff0e32b829f7ce8820799bcb16ed3e64d59121ccc27467`, test SHA `25204c7c4db8357e2653979f828e3754fbc5f53e00788de5dc2ac95c28ba5eae`로 최종 동결했다. 기존136 및135 이하 source/schema는 변경하지 않았다. 이 시점에 API 담당의 본 문서 쓰기를 동결하고 UI/Root의 최종 frontend·브라우저·전체 시험·보존·이해자료 결과 통합으로 인계한다.

## UI 위치와 실제 입력 방법

UI 구현 상태는 **TESTED_SYNTHETIC**이다. 모델 검토 화면의 `등록 모델` 선택 바로 아래에 기본 접힌 **연차 입력 진단** 패널을 추가했다. 모델을 선택하지 않아도 필요한 고정 참조 안내를 표시한다. 기존 `ModelReview.tsx`에는 import 한 곳과 namespaced key를 쓰는 sibling 한 곳만 추가했으며, 등록·readiness·평가·승인·전이·배포 동작과 다른 모델 화면의 상단 카드·레이아웃은 바꾸지 않았다.

1. 등록 모델을 선택한다. 기존 `modelErrorPins`를 재사용해 저장 metadata의 명시 버전 선언과 부모 checkpoint/training-report SHA가 일치하는지 확인한다. 선언이 없거나 잘못되면 **고정 참조 미확보**를 표시하고 조회를 막는다. metadata가 있어도 실제 파일의 존재·바이트 SHA를 이미 확인했다는 뜻은 아니다. latest·데이터 버전·파일 경로로 모델 버전을 추정하거나 backfill하지 않는다.
2. 최소 유효율의 분자와 분모를 직접 입력한다. 두 입력은 처음에 비어 있고 승인 기준 기본값이 없다. 분모는1~1,000,000의 정수, 분자는0~분모의 정수여야 한다. 분자0이면 유효 픽셀이0인 자료도 충족할 수 있으므로 기준의 적정성을 승인하지 않는다고 설명한다.
3. 접힌 **고정 참조 입력**을 열고 실제 등록 자료의 연차 배열을 입력한다. 편집 대상은 전체 요청 중 `requested_years` 배열이며, 각 행은 정확히 `year`, `image_ref`, `evidence_ref`, `metadata_ref`, `quality_report_ref`, `mask_ref`다. 각 참조는 정확히 `id`, `version`, `sha256`이며 연도 오름차순2~6행을 요구한다. 모델 참조와 정책은 위 입력에서 별도로 결합해 exact6 요청을 만든다. 가짜 ID/SHA 예시나 자동 채움 값은 제공하지 않는다.
4. **고정 참조로 입력 진단 읽기**를 직접 누른다. 잘못되거나 비어 있는 입력은 로컬 안내와 disabled 버튼으로 막는다. 결과는 요청 SHA·단계·연도별 유효/무효/전체 픽셀·충족/미달/대기를 표시한다. 대기·미관측은0 측정으로 표현하지 않는다. 별도 Workflow 실행·학습·승인 버튼은 없다.

`AnnualInputDiagnostics.tsx`와 `annual-input-diagnostics.css`는 기존 SVG Icon의 clipboard/search/close 스타일을 사용하고, scoped summary 간격·표 caption/열 머리글·가로 스크롤·focus-visible·hover 대비를 적용한다. 전체 요청을 임의로 편집하는 모델 JSON 대신 모델 pin·명시 정책·연차 참조 입력의 역할을 구분한다. 실제 브라우저의 간격·overflow·포커스 확인 결과는 Root의 후속 근거이며 이 단락만으로 통과했다고 주장하지 않는다.

## UI client와 응답 검산

`annualInputDiagnosticsAdapter.ts`는16KiB 이내 UTF-8 입력을 재귀 parser로 읽고 중복 키·float 지수/소수 표기·nonfinite·unsafe integer·긴 문자열·surrogate·과도한 깊이/노드를 거부한다. 참조 exact shape/SHA, 명시 버전, 정렬 연도, 행 내부의 image/evidence/metadata 및 image/quality-report/mask 구분, 연차 간 image ID/version 중복을 검사한다. Unicode와 유효한 버전 padding 원형은 전송에 유지한다. `refText`의 JS trim은 FEFF만 있는 ID 같은 극단값을 Python보다 엄격하게 로컬 거부할 수 있다. 이는 서버 허용을 넓히는 동작이 아니며 Unicode 정규화나 실제 자료 의미 인증도 아니다.

canonical 요청은 고정 ASCII 키를 정렬하고 원 Unicode 문자열·정수 값으로 직렬화해 SHA256을 계산한다. 응답 exact19와 요청 SHA, 요청 연도 순서·개수, status/HTTP status/blocking_stage/issue 조합, 계수 exact3·합계·상한을 확인한다. 각 연도의 `valid_pixels × denominator >= total_pixels × numerator`를 정수로 재산출해 행 판정과 전체 충족·첫 미달 연도를 대조한다.9개 권한·품질 관련 flag는 모두 정확한 false인지 검산한다. 화면은 이9개 필드명을 개별 나열하기보다 품질 보고서·품질 마스크·과학 정확도·실행·Workflow false와 기관·모델 미승인 설명으로 그룹 안내한다. 원 Registry·원경로·임의 오류 원문을 결과에 노출하지 않는다.

`annualInputDiagnosticsClient.ts`는 기존 API_BASE와 같은 origin의 새 endpoint만 호출하며 sessionStorage의 `geoai_token`을 Bearer로 전달한다. 응답은 최대16KiB의 bounded stream 복사와 strict UTF-8/JSON 검사를 거친다. Content-Length 또는 실제 누적 초과 시 reader를 취소한다. HTTP401은 기존 main의 `{detail:...}`와 새 router envelope 모두 원문을 버리고 고정 인증 안내로 처리한다. 다른 transport 오류는 고정 code/status 조합만 허용한다.429를 포함한 자동 재시도는 없다.

동기 pending lock으로 같은 입력의 연속 클릭을 한 요청으로 제한한다. 입력 수정은 현재 transport를 AbortController로 중단하고 결과·오류·generation을 초기화한다. 모델 pin 변경은 결과 identity도 즉시 대조해 이전 결과를 숨긴다. hashchange·popstate·unmount와 표시 중단도 늦은 응답 표시를 폐기한다. 이 UI 방어는 서버 진단의 취소·rollback이나 원자 snapshot을 증명하지 않는다. 이미 시작한 worker는 서버 slot을 계속 점유할 수 있으며 다른 진단 요청은429가 될 수 있다.

## UI 시험·교차 검토와 동결

- 집중 최종 **10 PASS / 193.219ms / exit0**: `evidence/integration/annual-input-diagnostics-ui-focused-final-20261018.log`. 명시 pin/빈 정책, strict JSON·16KiB,2~6행/참조, canonical SHA, 계수·정수 정책, exact19 오염/9false, HTTP 상태·고정 오류, 중복/늦은 응답 폐기, client Bearer/Abort/stream 초과/401 원문 무시, 수동 접힘 UI 연결을 확인했다. client와 응답은 명시 mock이며 실제 운영 API·자료 검증이 아니다.
- 전체 프런트 **271 PASS / 25.6785829초 / exit0**: `evidence/integration/annual-input-diagnostics-ui-front-20261018.log`. 집중10개도 이 묶음에 포함되므로 통과 수를 합산하지 않는다.
- 최종 build **112 modules / 13.48초 / exit0**: `evidence/integration/annual-input-diagnostics-ui-build-final2-20261018.log`. 기존 큰 bundle 경고는 남아 있으며 실패로 취급하거나 성능 SLA 통과로 표현하지 않는다.

초기 build의 TypeScript narrowing 오류2건은 수정하고 `annual-input-diagnostics-ui-build-initial-20261018.log`를 보존했다. 초기 집중9/10은 strict parser의 null-prototype 사본과 일반 JSON 객체를 시험에서 deepStrictEqual로 비교한 차이였다. 전송 JSON의 정확한 문자열 비교로 시험을 보완했고 제품의 JSON 계약 오류로 분류하지 않는다. 초기 로그와 중간 build 로그도 덮지 않았다.

API 담당의 UI 읽기 교차 검토에서 차단 지적은 없었다. UI 담당도 최종 API/main/tests를 읽어 인증·bounded 출력·HTTP 상태·worker 취소·false 승인 표현을 대조했다. 공백만 있는 token은 router 자체에서 미설정503이지만, 실제 main의 기존 truthy-token 인증이 먼저401을 낼 수 있다는 차이를 확인했다. Root는 다른 endpoint의 기존 인증 정책을 보존하기 위해 공백 token을 global 미설정으로 바꾸지 않기로 결정했다. 따라서 **실제 main의 공백 token은 선행401일 수 있으며 router 단독503 계약과 다르다**. UI는 이를 안전한 인증 실패로 안내한다. 해당 차이를 제거하려고 전역 인증을 우회하거나 약화하지 않았다.

UI 소스 동결 SHA256:

| 파일 | SHA256 |
|---|---|
| `AnnualInputDiagnostics.tsx` | `0746f331ebbb08ef9a010a21000bf1eb6c0ee2466aa325f417c9d72e79d46779` |
| `annualInputDiagnosticsAdapter.ts` | `292de1baed285f0a8a2ebd300735457edafe3b427b6c0b7fc0102e815a74c86b` |
| `annualInputDiagnosticsClient.ts` | `bb0c3d3aa37b3411250f15017ec56a5e3d0877dc9700bc0fc69228f07fe6c2f8` |
| `annual-input-diagnostics.css` | `58b3b4ac0e75ca20c52d45c112dd21bf36c4b98ffb8f259f4be51178aab5afa9` |
| `annualInputDiagnosticsAdapter.test.mjs` | `b6674d5c465b394ff99d5aa0b62c14ebef76124c6798f53c5c1db3c800a92634` |
| `ModelReview.tsx` | `c845118bed7dc06b5f84fedc8960c18d16015677bfeb968f88c304decc0e94fd` |

이 UI 인계 시점에 Root의 실제 HTTP·브라우저·전체 backend·보존 감사는 진행 중이다. 위 node/build 결과를 실행 중 서버 적용 또는 실제 브라우저 통과로 대체하지 않는다. Root가 완료 근거와 공통 인계·이해자료 갱신을 후속 추가한다. 운영 원본·Registry·모델·분할·원장·예약에 대한 UI 담당의 변경·수집·등록·훈련·추론·배포·Workflow dispatch는0이다.

## Root 실제 연결·전체 회귀·보존 검증

실행 중인5174 Vite 화면의 `#/view/17` 승인·배포에서 운영 baseline Draft 모델을 선택해 새 진단 패널을 확인했다. 모델의 필수 고정 참조 미확보로 조회가 disabled이며 분자/분모는 빈 값이다. 기존 승인·배포 차단을 우회하지 않았다. 운영8002의 OpenAPI에 새 POST가 있고 token 미설정의 빈 요청은503 AUTH_CONFIGURATION_REQUIRED/no-store였다.8000/8001의 별도 기존 프로세스까지 새 route 적용을 검증한 것은 아니다. 운영 인증을 새로 설정하거나 실제 모델·Registry를 수정하지 않았다.

실제 main 전체를 import하는 별도 no-reload API18037과 Vite15137을 임시 SQLite·6년 GTiff·CPU 랜덤 미훈련 TinyUNet fixture에 연결했다. 운영 data root를 쓰지 않고 import 전에 임시 root와 명시적인 시험용 인증 값을 설정했다. 첫2년의128 valid/128 invalid/256 total mask와 품질 JSON/Registry의 고정 SHA·lineage를 함께 재결합했다. 이는 실제 파일을 읽는 TESTED_SYNTHETIC 시험이며 독립 검증·학습 완료·기관 권위·품질 승인이 아니다.

실HTTP는 인증 누락/오류401,1/2 정책의 충족200,500001/1000000 정책의 미달200,잘못된 요청422,16KiB 초과413을 확인했다. 기존 global401은 detail envelope이며 Cache-Control이 없고, 새 router 직접 응답의 no-store/nosniff와 구분한다. 앞의 ‘모든 응답’은 router가 직접 만드는 응답 범위다. 원문 detail은 UI에서 반사하지 않는다.

실브라우저6 checks는 모두 통과했다. 빈 policy/refs 비활성화, 실제1/2 충족 계수·요청SHA,입력 변경 시 이전 결과 폐기,실제 미달 전행 계수·요청SHA,메뉴 이동/뒤로 가기 무오류·결과 폐기,운영 필수핀 미확보 차단이다. console/uncaught JavaScript 오류0,운영 쓰기0이고 사용자의 원래 탭은 그대로 두었다.3개 PNG와 MET/NOTMET/운영/back DOM 원문을 저장했다. 모바일·강제 지연 주입 E2E·모든 운영 서버의 인증 성공을 시험했다고 주장하지 않는다. 늦은 응답/중복 flight는 별도 adapter/API 시험 근거와 구분한다.

최초 전체 백엔드는1358 run/1354 PASS/3 FAIL/1 SKIP/490.787초였다. 과거 provenance·model version·Workflow model handoff AST 보존 guard3건이 이번 정확한 라우터2배선/단일 UTF8 비교 보강을 허용하지 않아 실패했다. 제품 코드는 추가 변경하지 않고 그3시험만 엄격히 갱신했다. 정확한 compare 호출을 검증한 후 비교용 AST에서만 정규화하고 나머지 함수·모듈 AST는 계속 비교한다. 실제 현재 auth를 실행하는 isolated 앱은 정규화 사본이 아닌 원래 UTF8 AST로 compile한다. 예상 밖 인자·중복 호출 거부 회귀도 추가했다. 원본3시험 바이트/SHA/LF 형식을 별도 증거에 보존했고 비교 함수 전체를 제외하거나 baseline을 HEAD로 옮기지 않았다.

최종 관련 compat36 PASS/6.983초 및 전체 백엔드 **1359 run/1358 PASS/1 SKIP/484.770초**다. SKIP은 기존 Windows symlink 생성 권한 제한이다. API 집중11·compat36·frontend집중10은 각각 전체 묶음에 포함되므로 합산하지 않는다. frontend271 PASS/25.6785829초·build112modules/13.48초는 제품 소스 동결 후 결과다. 전체 재시험 사이에는 기존 AST시험3개만 바뀌었고 API/UI 제품은 그대로다. 최초 전체 실패·compat 변경 전 실패·초기 frontend 오류 로그와 최종 통과 로그를 별도 보존했다.

보호141개·기존 소스307개 중 main/ModelReview/기존AST시험3개만 변경,나머지302개·이전 증거1235개·catalog14행 canonicalSHA·dataset_versions0·예약136314880바이트 불변을 확인했다. 초기 조회 스크립트의136 증거 경로 재사용은137 관측 보존+published136 원바이트 복원 후 이전 snapshot1788 SHA를 검산했다. 이 교정 경위는preflight에 남겼다. 최종 무결성 근거는 `diagnostic-api-live-integrity-final-20261018.json`이며 앞05:28의 `...live-integrity...json`은 기존 시험 보완 전 중간 관측이다.

시험 탭과 임시 Vite/API는 종료했다. API CtrlC는exit1이고 finally의 cleanup 완료 표시는 없었으므로 정상 graceful shutdown으로 과장하지 않는다. 재귀 Temp 정리는 자동 승인에서 거부됐고 상세 이유는 없었다. 중지 지시 수신 전 담당이 검증한 정확한 root의 일반파일36개·빈폴더11개를 비재귀 방식으로 정리해exit0/root없음을 확인했다. 최초 거부·후속 정리·추가 삭제0을 cleanup JSON에 기록했다. 운영 서버 종료/자료 삭제는0이다. 예약 ACTIVE/10분과 실제 수집/학습0을 구분한다.

설계·HTTP/JSON 계약·사용법·시험 근거·인계서와 이해자료14개를 같은 단위로 갱신했다. 전체 개발은 계속되며 원자료/독립 라벨·품질/모델 승인·다른5개 실행기·운영 GeoLLM/RAG/PostGIS·Kubernetes staging/RBAC/기관 UAT는 미완료다. 다음138은 현재 입력 생산자의 마스크 의미·nodata·band descriptions·고정 참조 계약 차이를 먼저 확인한다. 기존 자료나 label-support mask를 새 품질 의미로 소급 선언하지 않는다.

138의 사전 읽기 검토에서 제품의 LCLUC_QUALITY_MASK_EVIDENCE/source.mask_semantics 생성부는 없고131/133 reader와 fixture만 확인했다. `scripts/collect_samples.py:478` 이후는 SCL/nodata 유효성에 nodata0 mask를 쓰며 `scripts/collect_training_grid.py:215` 이후는 AOI·label!=0 조건까지 결합한 patch mask를 nodata0으로 쓴다.133은 nodataNone/all_valid·명시 binary semantics를 요구하므로 직접 호환된다고 볼 수 없다. 영상 write 구간에 descriptions 설정도 없어129의6band descriptions 검사를 충족하는지 별도 확인이 필요하다. 실제 운영 header는 열지 않았다. 다음 최소 후보는 caller가 이미 고정한 새 manifest에서 exact5 보고서 bytes/SHA·미등록 refs/manifest 초안을 순수 함수로 준비하고 RAW/STAGED를 유지하는 것이다. 이는 PLANNED이며 파일 쓰기·Registry 등록·QA 승인을 구현한 성과가 아니다. 별도 derived raster 작업은 source quality와 label-support mask 의미를 먼저 구분해야 한다.

검증 파일은 모두 `evidence/integration/` 아래다: `diagnostic-api-live-http-20261018.json`, `diagnostic-api-browser-20261018.json`, `diagnostic-api-browser-met-20261018.png`, `diagnostic-api-browser-not-met-20261018.png`, `diagnostic-api-operating-ui-20261018.png`, `diagnostic-api-root-full-backend-20261018.log`(최초), `diagnostic-api-root-full-backend-final2-20261018.log`(최종), `diagnostic-api-compat-test-update-20261018.json`, `diagnostic-api-compat-tests-final2-20261018.log`, `diagnostic-api-cross-review-20261018.json`, `diagnostic-api-live-integrity-final-20261018.json`, `diagnostic-api-final-processes-20261018.json`, `diagnostic-api-live-cleanup-20261018.json`과 최종 `diagnostic-api-closeout-20261018.json`이다.
