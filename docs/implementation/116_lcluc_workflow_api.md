# 116 — LCLUC Workflow 명시 제출·상태·검증 산출물 API

## 118 후속 — 같은 실행의 선택 변화쌍 지도 연결

[118 구현·검증](118_lcluc_workflow_change_map.md)에서 수동 pair 선택→고정 index GET→browser SHA·WGS84 도형 검사→중립 지도 미리보기를 연결했다. 기존115의 nonempty tuple/JSON list 보고서 비교 결함도 canonical JSON 동치로 최소 수정하고 회귀2건을 추가했다. 아래 지도 연결 미완료 표현은 당시 이력이며 최신 상태는118과 인계서를 따른다. 기존 상단 지도/KPI·운영 Draft/승인·원본은 보존했고 운영 실행은0이다. 6밴드 per_scene·실제 독립 검증·운영 GeoLLM/RAG·staging/UAT 완료를 뜻하지 않는다.

상태: **TESTED_SYNTHETIC / 운영 성공 실행 미수행**. 신규 `backend/app/lcluc_workflow_api.py`는 115의 고정 Registry→admission→실제 시계열 runner를 HTTP에 연결한다. core115·모델/자료 Gate·멱등/실패 정책은 변경하지 않았다. main의 router import/include 두 줄은 Root가 별도 배선한다. 기존 앱을 import해 운영 Store를 초기화하는 새 모듈이 아니며 `create_lcluc_workflow_router(get_store)`가 caller의 기존 Store를 사용한다.

## HTTP 계약

| 경로 | 동작·응답 |
| --- | --- |
| POST `/v1/lcluc/workflows` | 115 exact6 JSON을 명시 제출. claimed SUCCEEDED/FAILED 또는 기존 RUNNING/replay는200 receipt |
| GET `/v1/lcluc/workflows/{id}` | 영속 기록과 산출물 무결성 읽기.200 receipt+replayed:true, 실행 함수 호출0 |
| GET `/v1/lcluc/workflows/{id}/report` | 같은 SUCCEEDED record에 결합된 timeseries.json의 **검증 복사 원문 JSON**. 별도 wrapper 없음 |
| GET `/v1/lcluc/workflows/{id}/assets/{index}` | 같은 record.artifacts 배열의0-based index 파일을 검증 복사하여 attachment로 제공 |

id는 idempotency_key의 전체 lowercase SHA256이다. URL에 caller 경로/URI를 받지 않는다. artifact index는 정규10진수0..배열끝이며 음수·선행0·잘못된 형식·범위 밖은404다. 기록 id가 잘못된 SHA 형식이면400, 없는 기록은404다. 일반 목록/임의 파일 탐색·표준 GMAIS Result·선택 change pair 지도 투영은 추가하지 않았다. 117의 실행/보고서 UI와 pair 지도 구현은 별개이며 선택 지도 투영은 후속이다.

POST body는 115와 같은 exact6 `schema_version/capability/trace_id/idempotency_key/model_ref/images`다. raw request stream 누적16KiB에서 중단하며 strict duplicate/비유한/float/shape 검증을 Store getter 호출 전에 수행한다. 임의 caller 이미지·checkpoint·quality·출력 경로나 retry 옵션은 받지 않는다. 디코드·작은 요청 검증 후 Store getter·core 실행·응답 검사는 같은 threadpool worker에서 수행한다. async event loop에서 CPU 추론이나 파일 해시를 실행하지 않는다. POST는 완료까지 기다리는 동기 결과이며 새 background Job/queue/자동 취소를 만들지 않았다. HTTP 중단·UI 중단은 이미 진행 중인 runner의 취소가 아니다.

새 claim 성공 여부만으로 HTTP를201/202로 나누지 않는다.200 안의 status·replayed를 해석해야 한다. FAILED200도 실패 기록이며 실행 성공이 아니다. preclaim admission의 BLOCKED는 **409 receipt**이고 기록/분석 출력이 없으므로 GET404다. 이 경우 receipt에는115의 최소키만 있고 request_snapshot/request_sha256/artifacts가 없다. 같은 key 다른 payload는409 **error envelope**다. 두409 응답은 status 또는 error로 구분한다.

## receipt와 historical read

claimed receipt는 115의 필드 그대로에 replayed만 붙인다. schema_version/scope/id/trace/request_sha256/request_snapshot/status/created_at/issue/artifacts/scientific_accuracy_validated/standard_gmais_result를 확인한다. FAILED에는finished_at, SUCCEEDED에는finished_at/report_path/admission_pins가 추가된다. status별 exact key·정확한 타입·ISO timestamp·고정 issue code·두 false flag·artifact SHA·snapshot 형식을 검사한다. POST 응답은 요청 SHA/id/snapshot에도 결합한다.

GET는 `store.get('lcluc_workflows', id)`만 사용하며 Store 생성·put/connect transaction·core execute·admission 재실행이 없다. SUCCEEDED 상태 읽기에서는 기록 artifact 전부의 현재 SHA를 확인한다. report/다운로드는 선택한 artifact의 복사 바이트를 해당 record snapshot의 SHA와 확인한다. 현재 모델이 Draft/Retired로 바뀌어도 과거 성공 상태를 읽는 것은 새 실행 승인이나 배포 승인이 아니다. RUNNING/FAILED 자동 재실행·재시작·partial 삭제는 없다.

request_snapshot에는 원문 idempotency_key가 없으므로 GET만으로 request_sha256 전체를 재계산하지 않는다. GET id와 저장 snapshot 형식을 검증하는 historical read다. DB 자체의 기관 서명·작성자 권위를 인증하지 않으며 historical receipt의 두 과학/표준 Result flag는 항상 false다.

Windows의115 receipt/report는 `str(relative_path)` 때문에 backslash를 포함할 수 있다. API는 **원문 표기를 유지**하고 내부 경로 검사에만 `\\`→`/`를 정규화한다. UI도 두 표기를 읽되 다운로드는 raw path를 URL에 붙이지 않고 배열 index endpoint를 생성한다.

## 파일 경계와 복사 바이트

허용 namespace는 `results/lcluc-workflows/{동일64hex-id}/...` 하나다. relative 구성요소는 bounded ASCII token이며 빈 요소·dot/dotdot·원격 URL·drive/UNC·다른 namespace를 거부한다. 출력 namespace의 lexical 경로와 resolve 결과가 같아야 하고 파일도 그 아래의 같은 lexical 경로여야 한다. symlink/junction으로 DATA의 다른 내부 폴더를 가리키는 경우까지 거부한다.

복사 전에 file/size/namespace를 확인하고 streaming SHA를 계산하며 제한+1 byte에서 성장 파일을 거부한다. 복사 뒤 stat/namespace/path·SHA를 다시 확인한다. **FileResponse로 나중에 원본을 다시 여는 대신 이미 검증한 bytes를 응답**하므로 복사 완료 후 원본이 바뀌어도 전송 바이트가 바뀌지 않는다. 다음 요청은 변경을 거부한다. 파일과 DB의 원자 snapshot·호스트의 모든 동시 경로 교체를 차단하는 kernel sandbox는 아니다.

- 한 다운로드/상태 해시 대상 파일64MiB 이하, 상태 조회의 합산256MiB 이하.
- report JSON8MiB 이하. duplicate key·NaN/Infinity/overflow float를 거부하고 years는 정확한 int 목록으로 snapshot과 같아야 한다. checkpoint SHA·report 경로도 같은 기록에 결합한다.
- 허용 확장자/MIME: json=`application/json`, geojson=`application/geo+json`, csv=`text/csv`, tif=`image/tiff`.
- 다운로드 filename은 검증된 경로 basename이며 attachment다. ASCII 구성요소만 허용하므로 header 개행/quote 주입이 없다.
- 모든 새 route 응답에 `Cache-Control:no-store`, `X-Content-Type-Options:nosniff`를 적용한다.

64MiB는 HTTP 읽기의 추가 상한이다. core115가 허용한 합계256MiB 안이라도 단일 파일이 이 상한을 넘으면 읽기를503으로 거부하며 자동 삭제·재실행하지 않는다. 상태/다운로드 조회는 한 record snapshot에서 수행하지만 동시 여러 HTTP 요청 전체의 RAM/RSS quota·rate limit을 구현한 것은 아니다. 과학/기관 승인·자료 ACL 전체 구현과 구분한다.

## 인증과 고정 오류

router는 기존 FastAPI 전역 `authorized` dependency를 상속한다. GEOAI_API_TOKEN을 설정하면 기존 Bearer401이 모든 새 경로의 Store 접근보다 먼저 적용된다. 토큰 미설정 시 기존 앱의 로컬 선택적 인증 정책도 그대로이며 새 기관 RBAC/ACL을 추가하거나 인증을 강화했다고 주장하지 않는다. auth401의 기존 FastAPI `{detail:...}` 형식은 아래 router error envelope와 별개다.

새 route 오류는 exact `{error:{code,message,retryable:false}}`이고 message는 고정 한국어다. native 예외·입력 원문·파일 경로·토큰을 오류로 되돌리지 않는다.

| code | HTTP |
| --- | ---: |
| INVALID_REQUEST |400|
| REQUEST_TOO_LARGE |413|
| NOT_FOUND |404|
| IDEMPOTENCY_CONFLICT |409|
| WORKFLOW_NOT_SUCCEEDED |409|
| STORED_OUTPUT_CHANGED |503|
| RESOURCE_UNAVAILABLE |503|

RUNNING/FAILED report·download는 WORKFLOW_NOT_SUCCEEDED409다. malformed record/producer 응답은 RESOURCE_UNAVAILABLE503, 읽기 중 변경/해시/파일 검증 실패는 STORED_OUTPUT_CHANGED503으로 처리한다. 복구 가능한 의미의 자동 retry 승인은 없으며 retryable은 모두 false다. 115의 preclaim BLOCKED/FAILED issue도 서버의 고정 allowlist로만 노출한다.

## 시험·증거

운영 main import 없이 FastAPI+TempStore를 구성하고 main의 **authorized 함수 AST만 격리 실행**하여 동일 인증을 검사했다. 이것은 전체 main/CORS/운영 서버 적용 증거와 구분한다. fixture의 Deployed/독립평가/VALIDATED는 명시 mock admission metadata이며 실제 독립 승인/정확도 근거가 아니다.

실제16×16 두 연도 TinyUNet CPU POST→상태 GET→raw report→7개 산출물 attachment/SHA→같은 key replay를 Windows 표기로 검증했다. GET의 execute 호출0·auth401 beforeStore·400/413 beforeStore·preclaim409/GET404·FAILED200/no retry·동시1dispatch/RUNNING replay·payload 충돌·malformed record/다른 namespace·보고서 typed year/strict JSON·reader 크기/성장·변조·복사 후 원본 변경·고정 오류를 검사했다.

최초12 PASS/10.331초 로그를 보존한다. 중간15건에서 시험 io import 누락1건과 monkeypatch 상한이 Python default argument에 반영되지 않은 시험/호출 경계1건을 확인했다. io import를 추가하고 다운로드 호출에 고정MAX_ASSET을 명시했으며 최초/중간 로그를 보존했다. 최종 신규는 **15 PASS/18.676초/exit0**, `evidence/integration/lcluc-workflow-api-focused-final2-20261018.log`다. 중간 근거를 최종 시험과 합산하지 않는다.

Root 독립은 **23 PASS/20.003초/exit0**(기존 core17+별도6), `evidence/integration/lcluc-workflow-api-independent-tests-20261018.log`다. 실제 Windows report/download·GET 실행 금지·현재 Draft 변경 후 historical success·변조 거부와 main exact2 AST 배선을 확인했다. 기존 core17과 중복 합산하지 않는다. 관련/전체·최종 보존/실제 서버/UI 적용 근거는 완료 시 별도 기록한다.

구현 담당 관련은 **59 PASS/29.615초/exit0**, `evidence/integration/lcluc-workflow-api-related-20261018.log`다. 새API15+기존core17+기존GMAIS/RFC API를 격리/TempStore로 실행했다. 기존 API 시험의 main import도 자체 임시 DATA bootstrap을 사용하며 운영 main/운영 DB를 초기화하지 않았다. 새·관련·독립 중복 묶음은 합산하지 않는다.

Root 전체 backend는 **1168건/1167 PASS/기존 Windows 1 SKIP/406.540초/exit0**, `evidence/integration/lcluc-workflow-api-full-tests-20261018.log`다. 기존 route 보존은 **24 PASS/2.756초/exit0**, `evidence/integration/lcluc-workflow-api-route-preservation-tests-20261018.log`다. Root의 기존 main 두 router 연결과 두 기존 AST 허용목록 보정은 지정된 신규 router node만 허용하며 기존 route를 폭넓게 검사 제외하지 않는다.

`evidence/integration/lcluc-workflow-api-live-route-20261018.json`에서 기존8002의 missing GET404/POST 빈객체400을 실제 확인했다. catalog14가 그대로이며 운영 dispatch0다. `evidence/integration/lcluc-workflow-api-live-integrity-20261018.json`은 보호141·기존 증거889와 기존 소스258개 중 허용4개(main 배선/Workspace 배치/AST guard2개) 이외 불변을 확인했다. core115·원본/원장/lock/예약·분할·모델을 보존했다.

`evidence/integration/lcluc-workflow-ui-browser-20261018.json`은 **별도 임시5175 UI→8003 합성 서버**의 실제 CPU receipt/report·7개 파일과 CSV936B 다운로드 SHA 일치를 확인했다. 기존5174 화면에서는 invalid 입력 실행 버튼 disabled를 확인했다. 임시 합성 성공을 운영8002의 승인 모델 실행이나 기관 인증으로 확대하지 않는다. Bearer 권한 경계는 별도의 TestClient auth 시험 근거이며 이 브라우저 성공으로 인증 운영 인수를 주장하지 않는다. UI의 최종 시험/빌드/이동·stale 방어 근거는117 문서를 따른다.

## 인계·남은 범위

UI 담당에게 200 receipt/409 두 형태·401 별도·고정 오류·raw report·Windows path 유지·index attachment·Bearer 상속·historical read/no retry·cancel≠runner 취소 계약을 전달했다. UI/API 실제 화면 적용과 코드/격리 시험을 위 근거로 구분한다. Root는 main 두 줄/기존 AST 허용목록·전체 회귀·문서/원장/인계와 이해 에이전트의 설명·대본·FAQ·INDEX·변경 이력을 통합한다.

운영 등록/수집/다운로드/학습/배포와 승인 성공 POST는 수행하지 않았다. 원본·원장·예약·lock·분할·모델과 기존115를 보존한다. 현재 Draft·후보4차단·독립 라벨 미확보 및 global-only/6밴드 per_scene 미지원 한계를 유지한다. 이번 local API를 표준 GMAIS Result·기관 승인·full DAG·과학/UAT 완료로 표현하지 않는다.
