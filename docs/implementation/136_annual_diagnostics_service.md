# 136 — 연차 입력 진단의 제한된 요청·안전 요약 서비스

상태: **TESTED_SYNTHETIC**. 신규 `read_annual_diagnostic_service(store, request_json: bytes)`는 명시한 고정 참조와 정책을 제한된 JSON bytes로 받아135를 한 번 호출하고 작은 안전 요약만 반환한다. 신규 source·시험·내부 request/response schema·본 문서만 소유한다. 기존123~135·Store·main·라우터·UI·실행 gate를 수정하지 않는다. 서비스 함수까지의 내부 연결이며 인증 HTTP endpoint·UI 연결은137 후속이다.

## exact6 요청과 strict transport 경계

요청은 정확히 schema_version:1, capability:`landcover.input_diagnostics`, model_ref, training_report_sha256, requested_years, policy의6개 키다. requested_years와 policy는134·135의 명시 계약을 따른다. 임의 경로·caller manifest·실행 명령·기본 정책을 받지 않는다. 모델/자료 고정 참조 원형을 정규화하거나 버전을 추정하지 않는다.

raw 입력은 정확한 bytes이며 최대16 KiB다. UTF-8 strict decode 후 문자열/escape를 구분하는 depth16 사전 스캔을 수행한다. JSON duplicate 키·NaN/Infinity·**모든 float 문법**(1.0/1e0 포함)을 거부한다. parse_int는 변환 전에 부호 제외 최대16자리로 제한하고 절댓값2^53−1을 넘으면 거부한다. parse 후 전체 node4096개·각 문자열512자와 lone surrogate 부재를 검사한다. depth/nodes/string/정수 제한은 이 서비스의 새 내부 소비 정책이며 기존 parser/제품 소스를 변경하지 않는다. 요청 자체가 정수만 사용하므로 소수 coercion은 없다.

exact6 검증 뒤135의 `_policy`와134의 `_snapshot_request`로 전체 요청을 I/O 전에 검증·복사한다. malformed JSON·초과 크기·invalid 참조/정책·extra 키는 모두 INVALID_REQUEST, request_sha256=null이며 Store/모델 접근0이다. 이 내부 함수는 HTTP status·auth·라우터를 추가하지 않는다.

유효한 사본을 `sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':')`로 canonical UTF-8 encode하고 SHA256을 계산한다. 공백·키 순서는 fingerprint에 영향이 없고 Unicode·패딩 문자열의 원형 값은 유지한다. raw bytes SHA가 아니라 **검증된 JSON 값의 canonical fingerprint**다. 서명·권한·멱등 실행 token이 아니다.

##135 한 번 호출과 출력 검산

서비스는135를 한 번 호출하며 추가 Store/model/file/pixel 읽기를 수행하지 않는다. actual135를 따를 때 정상2/6행의 get13/37·모델 load1회·mask read N회는 그대로다. nested135/Registry/파일 경로·checkpoint manifest·보고서 원문은 응답에 넣지 않는다.

projection 전에135 exact20·schema/scope·annual counter1의 exact int·검증된 policy 사본 일치·9개 false의 정확한 False·세 성공 flag의 exact bool을 확인한다. scope와 각 행 status도 정확한 builtin str·허용 enum이어야 하므로 subclass의 사용자 정의 동등 비교로 private 문자열을 요약에 섞지 못한다. 행 수·순서·exact int year·exact4 shape·typed counts·policy_met·상태를 검사하고 성공/미달 정책의 정수 교차곱을 **다시 계산**한다. 모든 parent status/flag/행/issue가 일관돼야 한다. 미달은 모든 연도 결과와 첫 미달 year를 확인한다. malformed/unsafe 부모나 예외는 raw 원문을 반환하지 않고 OUTPUT_INVALID 고정 결과로 바꾼다.

core에 전달하는 ref/rows/policy도 fingerprint·출력 검산 기준과 별도의 사본이다. 정상135는 이미 입력을 복사하지만,136 경계 시험의 오염 core가 인자를 바꾸더라도 fingerprint와 검산 기준이 함께 바뀌지 않도록 분리한다. 이는 기존135의 정상 동작 결함 수정이 아니라 새 서비스의 불신 출력 경계 보완이다.

source 차단은 ANNUAL 또는 COUNTS stage로만 구분한다. 원 issue의 code/field/path를 반사하지 않고 고정 SOURCE_BLOCKED와 요청에 속한 exact int year 또는 null만 반환한다. 원 issue year가 요청 밖이거나 bool이면 OUTPUT_INVALID다. source 차단 부모의 모든 정책 행은 NOT_CHECKED/counts=null/policy_met=null이어야 한다. 완전한 nested 진단은 이 서비스에 노출되지 않는다.

## exact19 응답

필드는 schema_version:1, scope:`LCLUC_ANNUAL_DIAGNOSTIC_SUMMARY_READ_ONLY`, status, request_sha256, blocking_stage, issue, per_year_observations, caller_policy_evaluated, caller_policy_met, artifact_bytes_verified와135의9개 false다.

- quality_report_verified / quality_mask_verified / mask_semantics_verified
- registry_aoi_verified / source_authority_verified / scientific_accuracy_validated
- execution_authorized / state_dict_verified / workflow_supported

status는 INVALID_REQUEST / OUTPUT_INVALID / SOURCE_BLOCKED / CALLER_POLICY_MET_UNVERIFIED / CALLER_POLICY_NOT_MET다. blocking_stage는 REQUEST/OUTPUT/ANNUAL/COUNTS/POLICY 또는 성공 시 null이다. issue는 null 또는 exact2 `{code,year}`이고 code는 INVALID_REQUEST/OUTPUT_INVALID/SOURCE_BLOCKED/CALLER_POLICY_NOT_MET 중 하나다. per_year_observations는 detached exact4 `{year,status,counts,policy_met}`이며 원135의 작은 값만 수용한다. counts는 exact3 정수 계수이고 배열/픽셀은 없다.

정책 전체 충족만 caller_policy_met와 artifact_bytes_verified가 true다. 미달은 evaluated=true, met/artifact=false이고 전행 결과를 반환한다. source/output 오류는 세 flag false다. OUTPUT_INVALID는 request fingerprint를 유지하지만 행을 비우고 고정 issue만 반환한다. 오류 처리에서 이미 일부 projection한 내용을 반환하지 않는다. NOT_CHECKED는 정책 계산 미수행이며 하위134의 파일 I/O0을 의미하지 않는다.

## 내부 JSON Schema와 runtime의 차이

`contracts/internal/lcluc-annual-diagnostics-request.schema.json`과 `lcluc-annual-diagnostics-response.schema.json`은 JSON Schema Draft2020-12의 내부 문서화·구조 검산 계약이다. GMAIS 공식 schema나 기관 승인 기준이 아니다. schema 자체를 Draft202012Validator로 검사하고 실제2/6행 응답도 검증한다.

JSON Schema의 integer는 수학적으로 정수인1.0을 수용할 수 있지만 runtime은 float 문법 자체를 거부한다. 두 schema는 shape/enum/bounds 중심이며 schema만으로 오름차순/역할 중복·alias·숫자 교차 상한·counts 합·정책 교차곱·status/flag/행 사이의 일관성·canonical fingerprint를 보장하지 않는다. 따라서 schema 통과와 runtime 전체 수용의 동등성을 주장하지 않는다. 크기/depth/node/bigint/duplicate 및 private-output 경계도 runtime 책임이다. 실제 라우터의 schema·서비스 적용은137 후속이다.

## 한계와 검증 인계

안전 요약은 caller 정책의 수학적 충족이지 실제 QA·기관 기준 채택·mask 정답성·과학 정확도·AOI coverage·모델 승인·실행 허용이 아니다. 기존135 아래의 Store DB predecode·Torch allowlist·GDAL CPU/RSS/시간·다중 snapshot 비원자성/TOCTOU 한계를 유지한다. 유효 요청은 실제 읽기 비용을 유발하므로 이 서비스 자체가 공개 HTTP 인증/동시성/작업 스케줄 경계를 만든다고 표현하지 않는다. 그 연결은137 후속 설계다.

담당 최종 집중 **11 PASS / 64.474초 / exit 0**는 `evidence/integration/diagnostic-service-agent-20261018-focused-final2.log`다. actual Temp 모델·Registry·GeoTIFF2/6행과 별도의 mock135 오염을 구분했다. transport 한도·duplicate/float/nonfinite/depth/nodes/string/surrogate/bigint·alias·bool·전체 요청 사전검사, canonical fingerprint, source private issue 비노출, 부모 type/flag/year/counts/status/policy 모순의 OUTPUT_INVALID, 정책 전행 검산과 schema 차이를 확인했다. core 인자 변조에도 fingerprint/검산 사본이 유지되고, status str subclass의 동등 비교 callback을 호출하지 않고 거부하며, escaped quote/backslash/괄호 문자열의 depth 처리를 검증했다.

초기 PowerShell 실행은 source 경계 보완 전 첫 출력이 없는 상태에서 Ctrl+C로 종료했다. 해당 `diagnostic-service-agent-20261018-focused.log` 파일은 생성되지 않았고 완료 시험 결과도 없으므로 원로그 보존이나 시험 실행 수치를 주장하지 않는다. 첫 cmd 시도의 PYTHONPATH 인용 처리 때문에 모듈 import error가 발생한 **실제 존재 로그** `diagnostic-service-agent-20261018-focused-final.log`는 보존했다. 환경 명령만 수정한 final2에서 통과했으며 기존 제품 소스 결함은 아니다. 최종 실행의 모델 import 전 시작 지연은 unittest의 Ran64.474초와 별도다. 실제 CPU 진행과 부모 process·중복/orphan 부재를 Root가 확인했고 훈련 실행으로 표현하지 않는다. Affine PendingDeprecationWarning은 로그에 남겼다.

재동결 source SHA `709e011bc7abbd050b316e8ac5586a2f9421ed2019a7ca66f31e9090db65f98e`, test SHA `40776b85f4c8562312d1df06b22531389ec75845e59342b24ea2cf066b752558`다. request schema SHA는 `c1e90cc402f08a5d08d19ca76832d54727b756a6048b0a03b973d790f66a8f94`, response schema SHA는 `56d5a0110de527f68d326f6af90f33fc2289f209d7ada002f5f860061544b8c6`다. 기존135 이하 소스는 변경하지 않았다.

Root는 관련 회귀·실제 Temp 대비·보존·공통 인계/Git을, 독립 담당은 별도 fixture 경계를 검증한다. 이해 담당은 완료 코드·증거·한계를 해설/발표/FAQ/INDEX/변경 이력에 반영한다. 라우터/main/UI 변경이 없으므로 frontend/build/browser 재실행은 필요하지 않다. 운영 모델·자료·원장·분할·예약을 보존하고 운영 등록·수집·훈련·추론·배포는 수행하지 않는다.

## Root 실제 파일 대조와 보존

Root 최종 관련 **28 PASS / 119.021초 / exit 0**는 `evidence/integration/diagnostic-service-root-related-final-20261018.log`다. 신규136의11개,135의8개,134의9개를 포함하며 집중·독립과 중복 합산하지 않는다. Root의 초기 중단 `diagnostic-service-root-related-20261018.log`·`diagnostic-service-runtime-20261018.log`는0바이트로 남았고 완료 결과가 없다. 이 기록을 최종 통과 로그와 구분한다.

`evidence/integration/diagnostic-service-runtime-20261018.py`·`diagnostic-service-runtime-20261018.json` 및 **최종** `diagnostic-service-runtime-final-20261018.log`는 실제 Temp fixture의 **7개 시나리오 통과/exit0** 근거다. 정확한1/2 경계, 두 번째 행 미달 뒤에도 전행 평가, all0 기준0/양수, bool 정책의 INVALID_REQUEST/I/O0, 부모255·Registry manifest 변경의 SOURCE_BLOCKED를 확인했다. 정상 get19회·모델 load1회·mask read3회, source 차단 get16회, invalid0이며 서비스가 추가 I/O를 만들지 않는다. canonical fingerprint 일치·경로 비노출·DB/전체 파일 불변도 확인했다. 단순 schema 통과와 runtime 전체 정합을 구분했다.

`evidence/integration/diagnostic-service-live-integrity-20261018.json`은 보호141개·기존 source305개·이전 증거1215개·catalog14행과 SHA·예약136314880바이트 불변을 기록한다. 별도 상태 문서16/20의 시각·정체 기간 변경은 `diagnostic-service-separate-status-docs-20261018.json`로 검산했고 이번 구현팀의 기능 변경이나 실제 수집 재개로 표현하지 않는다. 운영 dataset_versions0과 예약/실제 학습 프로세스 구분을 유지한다.

## 독립 최종 근거와 문서 동결

독립 **7 PASS / 0 SKIP / 88.681709초 / exit 0**는 `evidence/integration/diagnostic-service-independent-20261018.py`와 같은 stem `.json`·`.log`에 동결했다. 실제2/6행에서 get13/37회·모델 load1회·mask read N회·영상 픽셀0·DB/전체 파일 불변과 두 schema 검증을 확인했다.16 KiB 정확 경계·strict JSON·invalid I/O0·canonical fingerprint의 순서/공백/quote/괄호 안정성, 실제 policy/model 차단 요약을 확인했다.

별도 명시 mock에서는 private nested·issue·예외·status/counts/flags를 노출하지 않음, str subclass callback0, core policy/year 변조가 fingerprint/검산 기준을 바꾸지 못하고 불일치 시 OUTPUT_INVALID가 됨을 검증했다. 이는 실제135 정상 입력 수정이 아니라136의 불신 출력 경계 시험이다. 재동결 source/test/schema 두 개 SHA가 모두 일치하고 Git4c14031의 기존 핵심8개 SHA·tracked source는 불변이다. 검토 보완 두 건은 종결했고 추가 제품 지적은 없다.

모델 import 전 시작 지연과 unittest 본문 시간은 별개이며 위 시간은 서비스 latency SLA·운영 응답 보장이 아니다. 장시간 진행 중 실제 CPU 사용과 부모 프로세스 존재·중복/orphan0을 확인했고 단일 세션 완료 후 추가 시험을 중복 실행하지 않았다. 운영·훈련·추론·API/UI/frontend/build/browser 재실행 없이 내부 서비스·schema·제한된 Temp/오염 시험 범위로 마감한다. 최종 증거를 반영한 뒤 본 문서를 동결했다.

## 후속137 연결

137에서 인증 필수 진단 POST와 ModelReview의 수동 연차 입력 진단 패널을 연결했다.136 서비스/Schema와135 이하 진단·실행기는 그대로다. 설계·사용법·실HTTP/브라우저·전체 회귀·제한은 [137 연결 문서](137_annual_diagnostics_api_ui.md)를 참조한다. 정책 충족은 품질·모델·실행 승인이 아니며 기존 운영 Draft 모델은 핀 미확보로 조회가 차단된다.
