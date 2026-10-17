# SDSS·GeoLLM·Agent Center UI 구현 근거

## G0: 원문·현행 구현 조사

기준은 `GreenBlue_CODEX_Master_Prompt_GMAIS_Integrated_Platform_v1.0.md` §9–10이다. 이 문서는 내부 개발 지시이며 TECH-4·승인 계약·컨소시엄 확정 규격과 동일하다고 주장하지 않는다. 조사 초기 저장소에서 GMAIS 패키지를 찾지 못해 SOURCE_MISSING으로 분류했으나, 통합 담당이 G:의 실제 패키지를 발견하고 원본을 `contracts/upstream/GMAIS-v0.2/`에 보존했다. **현재 상태는 SOURCE_FOUND**다. 초안의 미확보 UI 문구를 제거했다.

실제 읽은 원본: `api/openapi.yaml`, `schemas/agent-manifest.schema.json`, `job-request.schema.json`, `job-status.schema.json`, `result-manifest.schema.json`, `workflow-plan.schema.json`, `examples/workflow-example.json`. OpenAPI SHA256은 `8c9f21f89f34c325aa58153b031049c8e0e3c44eb1233ad9b3e003b539f92d44`, Result schema는 `351131b4d25d45b92ca3991125670829fb26a5c84844b10e7052b8c082504b0f`다. 표준은 내부 제안 v0.2.0이며 BIG 승인 규격이나 실제 모델 서비스가 아니라는 원문 설명을 유지한다.

기존 구현은 React/Vite/MapLibre와 `/api`의 실제 데이터·모델·작업·분석 기능이었다. `/api/query`는 승인된 정형 읽기 패턴이며 LLM·Policy RAG·자연어 임의 코드 실행 기능이 없었다. `/api/tools`는 LCLUC 구현과 외부 5개 interface-only를 반환했다. 기존 변화 GeoJSON·통계·보고서·Animate/Swipe·모델 승인 gate는 보존했다. Git 저장소가 없어 Git diff/commit 증거는 생성하지 않았다.

## G1: 파일 소유권·의존성

web_ui 소유 경로는 통합 담당에게 메시지로 전달하여 공통 `workstream_ownership.md`에 등록을 요청했다. 공통 소유권 파일은 통합 담당만 수정한다.

- `frontend/src/AgentCenter.tsx`, `GeoQuery.tsx`, `integrationAdapter.ts`, `integrationAdapter.test.mjs`
- `frontend/src/api.ts`, `App.tsx`, `AnalysisReview.tsx`, `style.css` 연결 변경
- 본 문서와 `docs/18_MLOps_SDSS_연계검증.md`의 후속 기록

표준 API·Registry·Job·Workflow·보안 구현은 통합 담당 소유다. UI는 해당 API 계약을 소비하며 백엔드 테이블·승인 gate·실제 수집 원장을 변경하지 않는다.

## G7/G8: 요구사항 대조와 구현

| requirement_id | source_section | source_type | subsystem / owner | 현재 구현·근거 | gap / 차단 |
|---|---|---|---|---|---|
| UI-09-01 | §9 조회 fallback | 내부 master + 기존 API | GeoQuery / web_ui | 유형별 실제 Dataset Catalog 읽기, 모델·분석 정형 근거 조회 | 범용 Intent/Spatial/Temporal parser 없음 |
| UI-09-02 | §9 계획·검증된 실행 | master + Workflow Plan schema | GeoQuery / web_ui, API / root | 실제 JSON 계획 입력·서버 응답·차단 근거 표시 | `/v1/workflows/plan`은 원본 OpenAPI에 없는 RFC 확장; 자동 Job 실행 미연결 |
| UI-09-03 | §9 근거·버전·불확실성 | master + Result schema | integrationAdapter / web_ui | 실제 ID·입력 참조·모델 참조·버전·SHA·validation·provenance·uncertainty 보존 | 서버 미제공 필드를 생성하지 않음; Policy RAG·RDTR·기관 ACL 미연결 |
| UI-10-01 | §10.2 Agent Center | GMAIS Agent schema | AgentCenter / web_ui | 실제 `/v1/agents`, 선택 readiness, 표준 Job ID 조회 | Agent readiness와 모델 승인 별도; 외부 모델은 연결대기/NOT_IMPLEMENTED |
| UI-10-02 | §10.1 Workflow 추적 | GMAIS Job schema | AgentCenter / web_ui | uppercase Job 상태·job_id·trace_id 실제 응답 | DAG 자동 실행·retry는 미연결; 비종료 Job 취소 요청 UI는 구현·실행 검증 대기 |
| UI-10-03 | §10.1 Map/Report | 기존 API + master | AnalysisReview / web_ui | 질의 Evidence의 실제 분석 ID를 동일 지도·보고서 선택에 전달 | 표준 Result 자산의 새 Layer/Report Adapter는 미연결 |
| UI-10-04 | §6.2·§9 MOCK_ONLY 금지 | master + Result schema | integrationAdapter / web_ui | Result `status:MOCK_ONLY` 및 호환 필드를 판정하여 지도·보고서 버튼과 핸들러 차단 | 기존 합성 fixture는 별도 시험용, 운영 과학 성과가 아님 |
| UI-10-05 | §10.2 Governance/O&M | master | 공통 통합 | 기존 토큰 기반 API 연결과 승인 gate 표시 보존 | 기관 로그인·역할 선택·이의제기·Feedback·롤백 운영 화면 미구현 |

GMAIS의 Agent `readiness=BLOCKED|READY|NOT_IMPLEMENTED`, `model_approval_status`, Job `status=CREATED|VALIDATING|BLOCKED|QUEUED|RUNNING|SUCCEEDED|FAILED|CANCELLED`, Result `status=SCIENTIFIC_VALIDATED|DEVELOPMENT_ONLY|MOCK_ONLY`는 다른 의미다. Result 검증 수준 `CONTRACT_ONLY|PSEUDO_LABEL_AGREEMENT|INDEPENDENT_SCIENTIFIC`도 별도로 보존한다. 초기 제안의 scientific_status 필드를 표준 Result 필드로 주장하지 않는다. 호환 판정에서 기존 필드를 읽는 것과 표준 스키마를 확장하는 것은 구분한다.

## 실행 경로와 보호

`agentApi`는 기존 API_BASE의 **같은 origin**과 엄격한 `/v1/` 경로만 사용한다. `/api/v1`로 오접속하지 않는다. 표준 Job 요청에 필요한 Idempotency-Key를 지원하지만 현재 UI가 승인되지 않은 Job을 자동 제출하지 않는다. 사용자 JSON의 실제 ID·버전·SHA를 서버가 검증해야 하며 예시 값을 원본 데이터로 등록하지 않는다.

GeoQuery는 조회·실행계획·근거 설명을 나눈다. 계획 요청은 원본 Workflow Plan 스키마를 사용하며 `nodes`와 `input_bindings`를 실제 값으로 확인하도록 안내한다. 계획 응답에 없는 단계·완료 상태를 로컬에서 생성하지 않는다. 응답이404/422/409이면 그대로 오류로 표시한다. 표준 API가 실패해도 기존 Toolbox를 성공한 표준 Agent로 바꾸지 않는다.

## 검증 증거

`node --experimental-strip-types --test src/integrationAdapter.test.mjs`: **4시험 통과·0실패·360.1913ms**. 표준 MOCK_ONLY 게시 차단, 실행코드/데이터 적격이 독립 검증·배포 승인을 생성하지 않음, 외부 미구현 차단, Result/Job/Input/Model/validation/Trace ID 보존을 검증했다. 실제 합성 모델을 독립 검증 모델로 등록한 시험이 아니다.

첫 웹 빌드 `npm.cmd run build`: **TypeScript 통과·42모듈·20.43초·종료0**. CSS81.65kB(gzip13.16kB), JS1,354.15kB(gzip377.91kB), 지도 라이브러리 큰 청크 경고가 남았다. 후속 변경의 최종 빌드 결과는 아래에 추가한다.

실제 Chrome의 운영 localhost5173에서 GeoQuery 모델 근거 조회를 실행하여 `baseline2021_cpu_v1_model`, Dataset version `717e5e1cce1a6d56`, Draft, 독립 평가 false, checkpoint SHA `ad74f5cf5ab4bfd42bffd94b2fa399bf28f3527bc8e9f424d6a9d5339b12cd6c`를 확인했다. 응답 모드 predefined-pattern 및 Trace 미제공을 표시했다. 이를 GeoLLM/RAG 구현 완료나 독립 정확도 검증으로 주장하지 않는다.

표준 Agent·Workflow의 라이브 서버 검증과 고정 Job/Result/Trace 대조는 새 API 재기동 후 수행한다. 진행 중 상태를 성공으로 선기록하지 않는다.

후속 브라우저에서 실제 Catalog6건을 확인했다. RFC 계획 API와 표준 Agent Registry는 당시운영API에아직없어HTTP404를그대로표시했고,계획완료·Agent연결성공·Job실행으로바꾸지않았다. 표준미연결영역과기존Toolbox6개(LCLUC구현/외부5연결대기)를분리해표시함을확인했다. 새API재기동뒤의검증은별도후속기록으로남긴다.

표준 Job 취소는 CREATED/VALIDATING/QUEUED/RUNNING 상태에서만 요청할 수 있게 연결했다. Result 응답은 현재 조회 Job ID와 일치할 때만 표시하고 다른 Job으로 전환하면 이전 Result를 지운다. 이 기능의 실제 표준 API 검증은 재기동 후 수행하며 아직 성공으로 기록하지 않는다. 최종 adapter 시험 재실행도4개 통과(564.132ms)했다.

최종 웹 빌드: `npm.cmd run build`, TypeScript 통과·42모듈·11.88초·종료0. CSS81.65kB(gzip13.16kB), JS1,356.66kB(gzip378.54kB), 큰 지도 번들 경고만 남았다. 기존 과학모델·학습·수집 원장·표준 원본 패키지를 변경하지 않았다.

## 최종 라이브 표준 API·브라우저 검증

검증 기록 UTC: 2026-10-16T07:07:32.994030+00:00. 서버는 통합 담당이 실제 vendored schema 검증과 RFC plan 경로를 포함해 재기동했다. 운영 과학 자료 대신 `contract-fixture-web-ui-not-operational`, URI `urn:contract-fixture:web-ui:not-operational`, 0으로 명시된 시험 SHA를 가진 계약 fixture 요청만 제출했다. 이 값은 실제 자료 해시가 아니며 입력을 실제 데이터로 등록하지 않았다.

| 경로/행동 | 실제 결과 | 증거 |
|---|---|---|
| GET /v1/agents | HTTP200, items6개, LCLUC BLOCKED/DRAFT, 외부5 NOT_IMPLEMENTED | agents.json·브라우저 선택 목록 |
| GET /v1/agents/lcluc-agent | HTTP200 실제 Manifest | agent.json 및 headers |
| capabilities/readiness | HTTP200, landcover.change_detection; runtime READY, dataset/science/deployment BLOCKED, contract PROPOSED | capabilities/readiness JSON·headers·브라우저 펼침 |
| POST agents/lcluc-agent/jobs | HTTP409 MODEL_NOT_READY, BLOCKED Job 기록 | blocked-request/blocked-submit JSON·headers·Idempotency-Key |
| GET 동일 Job | HTTP200, 같은 Job ID·Trace·BLOCKED | job.json·headers·브라우저 표시 |
| GET 동일 Job/results | HTTP409, Result 미생성 | job-results.json·headers |
| RFC plan UI 요청 | PLAN_ONLY, BLOCKED, can_execute=false, execution_started=false | browser-plan-request/response.json, 실제 DOM·스크린샷 확인 |

고정 Job ID: `job-4c21cb611db54fffb798879453d2ffc6`. Trace: `ui-contract-5d69cd44a4c14e26aa1a699df2372487`. 브라우저 Agent Center가 동일 ID/Trace를 표시하고 Result·취소 버튼을 비활성화함을 확인했다. Result 객체나 mock 지도·보고서를 생성하지 않았다.

계획 ID는 `ui-8fe6b57c-aac9-4d54-a00a-6ed9c66ae16c`, Trace는 `trace-3f84737a-85b9-404d-b14b-a9d5b764f8d4`다. 계획의 빈 input_bindings는 의도적으로 고정 입력 근거가 없는 상태이며 DATA_MISSING/MODEL_NOT_READY가 실제 반환되었다. 실제 브라우저에서 JSON과 RFC/기관미승인 표시를 확인했다. 저장 JSON은 DOM pre.json에서 읽은 실제 응답을 복사해 JSON 들여쓰기만 정리한 것이며, UI 응답 HTTP 원시 헤더는 별도 저장하지 않았다. 스크린샷은 도구에서 확인했고 PNG 파일은 보존하지 않았다.

한계: raw results URL의 별도 Chrome 탭 탐색은 Browser Use가 `net::ERR_BLOCKED_BY_CLIENT`로 거절했다. 우회하지 않았으므로 **직접 브라우저409 페이지는 미검증**이다. Result HTTP409는 실제 curl 응답 헤더이고, 브라우저에서는 Result 버튼 차단과 동일 Job 조회를 검증했다. 첫 로컬 curl은 샌드박스 연결에 실패해 정상 승인 경로로 재실행했다. POST 승인 대기 중 도구가 장시간 대기했으나 승인 완료 후 실제409와 Job을 확인했다. 서브 Python의 jsonschema 모듈은 없어 로컬 스키마 검증 성공을 주장하지 않는다. 서버가 원본 스키마로 검증한 요청이며 실제 HTTP 결과만 기록했다.

재현 파일은 `frontend/evidence/gmais-live/reproduce.ps1`이다. 같은 Idempotency-Key와 원래 fixture body를 재사용하므로 동일 서버 기록에서 중복 Job 생성을 방지한다. 재현 스크립트 자체를 이번 검증에서 추가 실행하지 않았으며, 사용자가 재현할 때 공유 서버의 인증 설정이 있으면 기존 토큰 정책을 적용해야 한다. `verification-summary.json`에 ID 대조·시각·파일 SHA와 한계를 기록했다.

최종 브라우저 후 빌드 시도는 TypeScript 단계 후 Vite가 main.tsx realpath에서 EPERM 환경 제한으로 실패했다. 이전 성공한42모듈 빌드 근거와 구분한다. 정상 권한 재시도는 통합 담당의 추가 재시도 중지 메시지 전에 이미 시작했으며, 권한·보안 우회는 하지 않았다.

이미 시작된 정상 승인 빌드 재시도는 종료0으로 완료되었다. TypeScript 통과·42모듈·32.65초, CSS81.65kB(gzip13.16kB), JS1,356.73kB(gzip378.56kB)이며 큰 청크 경고만 남았다. frontend/evidence/gmais-live/build.log는 앞선 EPERM 실패 로그이고 build-success.json은 후속 실제 성공 출력의 구조화 기록이다. 두 결과를 구분해 보존했다.
