# 117 — LCLUC 고정 입력 실행과 조회 UI

상태: **TESTED_SYNTHETIC / 운영 실행 미수행**. 116의 로컬 Workflow API에 연결하는 명시 UI다. 기존 LCLUC Workspace에 기본 접힌 패널 하나를 추가하며 다른 5개 분야에는 표시하지 않는다. PNG 기반 카드·탭·SVG 체계와 기존 실행/비교/리포트 버튼을 바꾸지 않는다. 지도 변화쌍 투영은 후속이며 가짜 결과 지도를 만들지 않는다.

## 파일과 연결 범위

- `frontend/src/LclucWorkflowPanel.tsx`: 빈 요청/조회 입력, 수동 실행·조회·보고서·다운로드, 구조화 상태와 요약.
- `frontend/src/lclucWorkflowAdapter.ts`: 115 exact6 요청 및 116 상태/오류/보고서 연결 검사와 세대 방어.
- `frontend/src/lclucWorkflowClient.ts`: 기존 API_BASE의 동일 서버 origin, 기존 `geoai_token` 탭 세션 Bearer를 유지하는 전용 클라이언트.
- `frontend/src/lcluc-workflow.css`: 패널 내부에만 적용하는 간격·줄바꿈·표 스크롤 규칙.
- 기존 `ModelAnalysisWorkspace.tsx`는 import 한 곳과 `agentId==='lcluc'` sibling 슬롯 한 곳만 추가한다. main/api.ts/GeoQuery/기존 모델 레이아웃은 변경하지 않는다.

## 입력과 HTTP 계약

요청은 사용자가 직접 입력하는 exact6 `schema_version/capability/trace_id/idempotency_key/model_ref/images` JSON이다. 기본 값·실모델 ID·버전·SHA·예시 실제 참조를 자동 채우거나 위 지역 필터에서 추정하지 않는다. 모델/연차 ref exact3, SHA lowercase hex64, ASCII token, 이미지2..6개·1900..2200 정수 오름차순을 검사한다. 최대16KiB UTF-8이며 duplicate key·소수/지수·추가 키·경로를 거부한다. 기존 엄격 parser를 재사용하고 새 실행 계약의 범위를 추가 검사한다.

버튼 클릭만 POST `/v1/lcluc/workflows`를 호출한다. 최초 로드·패널 열기·이동·상태 확인에서 실행 요청을 만들지 않는다. 자동 polling·자동 제출·자동 retry/resume이 없다. 요청 전체 canonical SHA와 원문 실행 키의 전체 SHA를 계산해 응답 request_sha256/id와 연결하고, 저장 request_snapshot도 원래 요청에서 키만 제외한 값과 일치해야 한다. 키의 원문은 새 local/sessionStorage에 저장하지 않는다.

- POST200: RUNNING/FAILED/SUCCEEDED 또는 그 재생 receipt. POST409 BLOCKED: 실행 전 차단 receipt이며 claim 기록이 없다.
- GET `/{id}`: 수동 입력한64자리 ID의 기존 receipt. replayed=true가 필수이며 false인 오염 응답을 거부한다. 조회는 실행하지 않는다. BLOCKED가 저장된 실행처럼 보이지 않도록 미기록/404를 설명한다.
- GET `/{id}/report`: SUCCEEDED receipt의 report_path·checkpoint SHA·연도·변화쌍에 연결되는 raw timeseries JSON. 요약 표는 실제 valid_pixels/changed_area_m2만 표시한다.
- GET `/{id}/assets/{index}`: 검증된 receipt artifacts 배열의0..127 정수 index만 사용한다. 서버 URI·data URI·다른 다운로드 경로를 실행하지 않는다. 다운로드 파일명은 검증된 배열 path의 basename을 사용하고 인증 헤더를 유지한다. 화면에는 years/2020/classification.tif 등 namespace 아래의 원래 상대 경로를 표시해 연도별 동명 파일을 구분한다. 기존 `/v1/results` 전용 downloadAgentAsset을 변경하거나 우회하지 않는다. 공통 Icon은 바꾸지 않고 기존 AnalysisIcon의 결과 내보내기 SVG를 사용한다.

오류는 116 exact `{error:{code,message,retryable:false}}`와 HTTP 상태의 허용 조합을 검사하고 고정 한국어 안내만 표시한다. 기존401/403 인증 응답은 별도 안전 안내로 처리한다. 서버 message/native 예외·원문 경로를 오류 화면에 출력하지 않는다. 상태 receipt는 exact 키·고정 issue code·정확한 false 두 claim·요청 snapshot·상태별 timestamp/빈 artifact·성공 namespace/핀/중복 경로를 검사한다. GET 요청 ID는 응답 ID에 결합한다. 이 결합은 서버 신원/기관 권위를 추가 인증하는 것이 아니다.

115 Windows receipt/raw report의 역슬래시 경로를 지원한다. 검증 시 구분자만 slash로 정규화하고 원문을 보존한다. 다운로드 URL은 항상 ID와 index로 새로 구성하며 파일 경로를 URL로 직접 사용하지 않는다.

## 상태와 늦은 응답

BLOCKED는 claim 없음, RUNNING은 실행 중 또는 중단 후 미완료 기록, FAILED는 실패/부분 파일 보존·자동 retry 없음, SUCCEEDED는 로컬 실행 완료다. `replayed=true`는 과거 기록 읽기이며 현행 모델의 새 승인 재판정이나 새 실행이 아니다. UI는 항상 LOCAL_LCLUC_WORKFLOW_ONLY·scientific_accuracy_validated=false·standard_gmais_result=false의 의미를 설명한다.

동기 pending guard로 중복 클릭을 막는다. 요청 JSON/조회 ID 편집, popstate/hashchange, unmount, 명시 표시 중단에서 세대를 무효화하며 결과·오류·busy의 늦은 갱신을 폐기한다. 준비 SHA 계산 뒤에도 유효 세대를 확인한 후 POST한다. 다운로드는 응답 후 유효 세대에서만 anchor를 클릭한다. **표시 폐기는 서버 처리 취소·파일 삭제·DB rollback이 아니다.** 같은 키 수동 재요청의 재생은 서버115의 단일 claim 정책을 따른다.

## 과학·제품 경계

현재 실모델 Draft·독립 라벨 미확보·QA 차단을 그대로 안내한다. 실행 승인은 서버가 확인하며 UI 입력만으로 승인하지 않는다. 115는 global normalization만 지원하고 per_scene 공식 제품 정규화/6밴드 제품·구름 mask 연결은 후속이다. caller 버전 선언·VALIDATED/PUBLIC·로컬 독립평가 metadata를 기관 인증이나 실제 과학 정확도 검증으로 승격하지 않는다.

보고서 요약은 시점·센서·계절·구름·모델 오류를 포함할 수 있다. 이 패널은 기존 지도의 bbox/미연결 레이어를 실제 결과처럼 바꾸지 않으며 지도 pair 선택·GeoJSON 투영·표준 GMAIS Result 발행은 구현하지 않는다. 전체 프로젝트 완료나 실제 운영 실행 인수를 뜻하지 않는다.

## 검증 근거

신규 adapter/client15 PASS/12.831초: exact 요청·잘못된 입력/HTTP·receipt 상태/핀/경로·request SHA/snapshot·보고서 연결, 동기 중복 및 늦은 결과/오류 폐기, mock fetch의 기존 세션 Bearer·허용 endpoint·stale download 클릭 방지, GET replayed 필수·전용 SVG/연도 경로 표시를 검사했다. 실제 Python115 TempStore가 생성한 Windows 경로의16×16 두 연도 TinyUNet CPU receipt/raw report·7개 산출물이 UI parser를 통과했다. 생성 영상과 fabricated 승인 metadata의 명시 fixture이며 **학습·실제 전문가 평가·운영 실행은 수행하지 않았다.** 로그: `evidence/integration/lcluc-workflow-ui-related-final3-20261018.log`.

최종 전체 frontend **206 PASS/24.216초**, 최종 production build **100 modules/13.01초/exit0**다. 기존 큰 bundle 경고는 남으며 빌드 오류가 아니다. 로그는 `evidence/integration/lcluc-workflow-ui-tests-final2-20261018.log`와 `evidence/integration/lcluc-workflow-ui-build-final3-20261018.log`다. 최초 실제 브라우저에서 다운로드의 미지원 Icon 이름을 발견하여 공통 파일 변경 없이 기존 결과 내보내기 SVG로 교체했고 GET replayed 검사와 연도별 경로를 보강한 뒤 위 최종 동작시험을 다시 실행했다. 이후 Root PNG 시각검토에서 전역 hover 배경과 파란 글자의 대비가 낮음을 발견하여 scoped hover 배경/글자와 focus-visible outline만 보완하고 build만 다시 검증했다. TS/동작 변경이 없어 전체 동작시험을 반복하지 않았다. CSS append 명령 한 번은 중복 cwd 경로로 파일을 찾지 못했으며 기존 파일 변경 없이 올바른 scoped 경로로 정정했다. 중간 로그는 보존하고 최종 근거와 합산하지 않는다.

Root는 별도 fixture UI5175/API8003에서 수동 POST 성공·7개 산출물, 최종 HMR 뒤 reload 후 저장 ID 조회의 replayed=true, 보고서2020/2021·유효256픽셀·변화0m²를 실제 브라우저로 확인했다. transitions.csv 다운로드는936B·SHA `bb8f6a00c74cc8fce6cab598e8500d7c35d9ae57739bb2c4f8ae429877651ad2`로 receipt와 일치했다. 뒤로 가기 후 LCLUC에 복귀할 때 과거 receipt가 다시 표시되지 않았고 다른5개 모델에는 패널이 없었다. 기존 UI5174/API8002는 별도 시험 탭에서 신규 패널의 실제 반영·`{}` 입력의 실행 disabled만 확인했으며 사용자 원래 탭은 바꾸지 않았다. 운영 dispatch0을 유지했다.

근거는 `evidence/integration/lcluc-workflow-ui-browser-20261018.json`, `lcluc-workflow-ui-synthetic-report-dom-20261018.txt`, `lcluc-workflow-ui-live-invalid-dom-20261018.txt`, 최종 대비 보완 화면 `lcluc-workflow-ui-synthetic-desktop-final2-20261018.png`, `lcluc-workflow-ui-live-invalid-20261018.png`다. 최종 CSS의 실제 hover computed 배경은 rgb(223,238,255), 글자는 rgb(7,90,200)로 확인했다. **모바일 viewport는 시험하지 않았다.** 실제 브라우저에서는 지연 응답을 주입하지 않았으며 늦은 응답 폐기는 위 adapter 시험의 근거다. fixture 브라우저 token은 비어 있어 Bearer 인증 성공을 브라우저 다운로드로 입증하지 않는다. 인증은 별도 API TestClient와 mock scoped-client 시험으로 구분한다. 실제 서버 연결·브라우저 관측과 Node mock/fixture 통과를 합산하지 않는다. UI 담당은 운영 Store/API 실행·등록·다운로드·학습·모델 변경을 수행하지 않았다.
