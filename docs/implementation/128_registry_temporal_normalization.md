# 128 — 동일 Registry 관측에서 요청 UTC 연도와 영상 기간 결합

## 쉬운 설명과 범위

127은 year를 요청 라벨로만 처리했다. 신규 `backend/app/ml/registry_temporal_normalization.py`의 `inspect_registry_temporal_normalization(store, model_ref, training_report_sha256, requested_years)`는 **125가 실제로 읽는 영상 Registry record와 같은 관측**에서 temporal을 검산한다. 별도로 기간만 미리 조회한 뒤127이 다른 record를 다시 읽게 하지 않는다.

성공 시 새 `registry_temporal_year_verified:true`는 등록 문서의 기간 선언이 요청한 UTC 연도 안에 있다는 뜻이다. 실제 센서 취득 시점·기관 원문·raster header 연도 진위가 아니다. `physical_acquisition_year_verified:false`와 기관/과학/실행/Workflow false를 유지한다. 기존124~127·Store·Registry schema·API·UI·실행 gate를 수정하지 않았다. 실제 header/grid/AOI·mask는129 이후 별도다.

## 원 schema와 신규 내부 기간 소비 규칙

upstream Dataset Manifest temporal schema는 start/end의 date-time 형식과 nonempty calendar 문자열을 요구한다. calendar enum이나 요청 연도 전체 포함 규칙은 없다. 이 helper의 아래 정책은 **신규 내부 소비 규칙**이며 upstream 표준·기관 승인 조건으로 표현하지 않는다.

- calendar는 정확히 `gregorian`만 지원한다. `proleptic_gregorian`, `Gregorian` 등은 현재 범위 밖으로 차단한다.
- ASCII 숫자·uppercase T/Z 또는 명시 ±HH:MM의 알려진 offset만 받는 엄격한 RFC3339 **부분집합**이다. 날짜만·naive·공백 separator·lowercase t/z·Unicode 숫자를 거부한다. RFC3339 전체 문법 구현이 아니다.
- `-00:00`은 offset 미상이라는 의미이므로 UTC0으로 확정하지 않고 거부한다. Z/+00:00은 가능하다.
- 소수초는1~9자리까지 지원하고 UTC 정수 nanosecond로 비교한다. Python datetime의 microsecond 절삭으로 나노초 역전을 숨기지 않는다. 소수10자리 이상·leap second60·24시·잘못된 날짜/offset은 현재 미지원으로 거부한다.
- 요청 year는127의1900~2200 exactint다. 양 끝점 포함인 선언 기간에 `UTC Jan1(year) <= start <= end < UTC Jan1(year+1)`를 적용한다. start=end는 유효한 순간이고 end가 정확히 다음 Jan1이면 거부한다. 문자열의 local-year가 아니라 offset 적용 후 UTC를 비교한다.

기존 canonical_manifest는 datetime.fromisoformat과 Z 치환을 사용한다. 신규 parser와 원 schema/canonical validator의 교집합만 성공하며 원 validator를 느슨하게 바꾸지 않는다. 예를 들어 원 schema 자체는 허용할 수 있는 더 넓은 날짜 문법도 이 소비 부분집합에서 거부될 수 있다.

## 동일 get·동일 manifest snapshot과 failfast

먼저127의 `_request`로 **전체** model/ref/year rows를 검증·복사한다. invalid→valid로 caller가 동시에 값을 바꾸더라도 재검증으로 I/O가 생기지 않도록 invalid nested127은 고정 invalid sentinel `(None,None,None)`에서 생성한다. invalid 응답은127의 동일한 formal shape이고 Store/file 읽기0이다.

유효 요청은 get/root만 제공하는 readonly Store proxy를 통해 원127을 한 번 호출한다. 모델은124에서1회 읽고,125의 각 행3get 중 첫 번째 실제 image get의 record만 다음처럼 검사한다.

1. 실제 반환 record의 key/id와 bounded manifest의 dataset_id/version/artifact SHA·canonical JSON digest/저장 manifest_sha256을 확인한다.
2. 같은 bounded manifest의 기간을 위 UTC 규칙으로 검사한다. 기간 형식/역전 오류는 원 canonical의 일반 datetime 예외에 가려지지 않도록 고정 reason으로 분류한다.
3. 원 canonical_manifest/schema도 통과하고 digest가 같아야 한다. 그 canonical manifest의 deep snapshot을 넣은 record copy를 **그대로125에 반환**한다.125가 다른 image record를 새로 get하지 않는다.

추가 Store.get은0이며 정상1model+3N dataset get과 model load1회를 유지한다. proxy는 보호된125의3get 순서(image/evidence/metadata)를 사용한다. 단순 key 목록만 보고 temporal을 검사하지 않아, 이전 행의 metadata key가 미래 image key와 겹치는 경우에 미래 row 관측을 잘못 생성하지 않는다.125 호출 순서가 바뀌는 후속 변경에는 이 계약도 함께 검토해야 한다.

proxy는 precise 고정 temporal reason을 기록하고 예외를 발생시킨다.125가 이를 generic 고정 오류로 바꿔도128의 독립 관측에 정확한 reason이 남는다.127은 기존대로 첫 실패에서 멈추고 뒤의 row를 NOT_CHECKED로 보존한다. 모델 실패·유효 global은 image get0이며, global도 모델 파일 읽기는 이미 수행했다.127 nested 반환은 수정하지 않고 temporal_year_verified=false도 그대로 둔다.

## exact13 출력

필드는 schema_version:1, scope:`PINNED_YEARS_REGISTRY_TEMPORAL_READ_ONLY`, status, issue, batch_observation, temporal_observations, registry_temporal_year_verified, physical_acquisition_year_verified, artifact_bytes_verified, source_authority_verified, scientific_accuracy_validated, execution_authorized, workflow_supported다.

status는 INVALID_INPUT / MODEL_BLOCKED / OUT_OF_SCOPE / SCENE_BLOCKED / TEMPORAL_BLOCKED / REGISTRY_YEARS_MATCHED_UNVERIFIED다. batch_observation은 원127 exact24이며 수정하지 않는다. issue는 null 또는 exact `{code,field,year}`다. invalid/model/일반 scene 오류는 원127의 고정 stage reason을 유지한다.

temporal_observations는 실제 image get이 반환되어 검사한 순서의 exact `{year,status,manifest_sha256,issue}` 목록이다. status는 MATCHED_UNVERIFIED 또는 BLOCKED, issue는 null 또는 `{code,field}`다. **BLOCKED의 manifest_sha256은 계산한 후보 digest일 수 있다.** 값이 있다는 이유로 저장 pin/원 schema/기간과 일치했다고 단정하지 않는다. record를 해석하지 못하면 null일 수 있다. 뒤의 NOT_CHECKED 행은127 rows에서 확인한다.

proxy reason code는 REGISTRY_RECORD_INVALID / REGISTRY_REFERENCE_CONFLICT / TEMPORAL_FIELD_INVALID / TEMPORAL_CALENDAR_UNSUPPORTED / TEMPORAL_OFFSET_UNKNOWN / TEMPORAL_WINDOW_REVERSED / TEMPORAL_YEAR_MISMATCH다. field는 image/temporal/calendar/start/end/window의 고정 이름이다. raw path·caller 날짜 문자열·예외 원문을 오류에 넣지 않는다. TEMPORAL_BLOCKED는 이 image-record↔year 결합 경계의 차단으로 record pin/schema 오류도 포함할 수 있다.

registry_temporal_year_verified는 **모든 image 기간 관측과127 batch 전체가 성공한 경우만** true다. 기간이 먼저 맞았어도 후속 파일 변조가 있으면 SCENE_BLOCKED이고 전체 temporal flag도 false다. artifact_bytes_verified도 이 전체 성공과 원127 artifact true일 때만 true다. 실제 취득 연도·기관 권위·과학 정확도·실행/Workflow 다섯 false는 항상 유지한다. nested127의 기존 승인/temporal false를 승격하거나 수정하지 않는다.

## 한계와 시험

같은 get으로 temporal과125가 보는 manifest를 결합하지만 전체 DB/다중파일을 같은 시점에 잠그는 원자 snapshot은 아니다. 기록을 읽고 난 뒤 변경하는 모든 경쟁을 제거하거나 모델/파일을 마지막에 재load하지 않는다. 다른 image ID가 같은 path/SHA를 가진 경우 실제 독립 장면/연차 독립성을 보장하지 않는다. 기간 선언이 맞아도 실제 acquisition·원 기관 증명·header/grid/AOI/CRS·mask·QA·ACL·물리 보정·state_dict는 미검증이다. inherited Store.get 원문 predecode/RSS·Torch ambient allowlist/CPU시간·mapped drive/TOCTOU 한계를 그대로 따른다.

담당 집중 최종 **11 PASS / 13.072초 / exit0**: `evidence/integration/temporal-normalization-agent-20261018-focused-final.log`. 최초10 PASS/12.528초는 `temporal-normalization-agent-20261018-focused.log`에 보존했다. freeze 전 review의 invalid mutable 재검증 경쟁을 고정 sentinel 및 시험으로 보완했고 ASCII regex도 명시했다. 기존 소스는 수정하지 않았다.

실제 TempStore2/6장면·CPU checkpoint 읽기로1+3N get/추가 get0·같은 반환 manifest snapshot·UTC offset/local-year 차이·Jan1 경계·나노초 역전·start=end·형식/Unicode/nullable/calendar/-00·failfast/부분 관측·예외 숨김 뒤 precise reason·metadata/pin 변조·파일 후속 실패·invalid/global/model0image·DB/파일/입력 무쓰기·invalid→valid 경쟁 I/O0을 확인했다. 훈련·forward·추론·state 적용은0이다.

source SHA `6cc04dcfb2e71745a09ed7a62b17ccc94637e5c9ad12730fe7ac3d8e20b98f15`, test SHA `d6c51b9a6075b381c2840ea8b8bcd059025253ccf92866cf6e391613e4693619`로 Root/독립 담당에게 동결 인계했다. Root는 실제 GeoTIFF/등록 묶음·관련 시험·보존·공통 문서/Git을, 독립 담당은 별도 UTC/같은get/경계 fixture를 검증한다. 이해 담당은 완료 소스·시험·한계를 읽고 설명·발표·FAQ·INDEX·변경 이력을 갱신한다.

미연결 내부 reader이므로 UI/API/frontend/build/browser를 수정·재실행하지 않고 기존115 실행 gate를 유지한다. 이전120 backend1184/front261은 과거 근거다. 운영 모델 load·데이터/Registry 쓰기·등록·수집·훈련·추론·배포0이다.129의 actual raster header/grid/AOI 진단과 전체 운영 실행·완료는 별개다.

## 최종 독립·관련·실파일 대비·보존 근거

독립 최종 **7 PASS / 0 SKIP / 9.008356초 / exit0**는 `evidence/integration/temporal-normalization-independent-20261018.py`와 같은 stem `.json`·`.log`에 동결했다. 별도 Temp18 Registry records·실제 CPU checkpoint로2/6행의7/19 get·각 key1회·DB 불변과 top registry true/physical false/nested127 temporal false를 확인했다. UTC offset으로 local2019/2021이 UTC2020이 되는 경우, 마지막9자리 소수초·1ns 역전·다음 Jan1·start=end·nullable/naive/-00/leap second/lowercase/Unicode/소수10자리/calendar를 검증했다. 실제 같은 get의 coherent metadata 변경은 차단하고, 미래 image key가 현재 다른 role에 쓰이는 경우도 잘못된 미래 temporal 관측을 만들지 않음을 확인했다. Git0ff7126의 기존 핵심8 source SHA·tracked source 불변과 동결 source SHA 일치, 제품 지적0이다.

Root 관련 **47 PASS / 27.445초 / exit0**는 `evidence/integration/temporal-normalization-root-related-20261018.log`다. 신규11·127의9·124의14·125의13을 포함하며 집중·독립과 중복 합산하지 않는다.

Root의 `evidence/integration/temporal-normalization-runtime-20261018.py`와 같은 stem `.json`·`.log`는 실제 임시 GeoTIFF3개·등록9역할·CPU checkpoint의 **7시나리오 통과/exit0**다. 실제 top/nested 범위·torch.load1회/get10회·bool 요청 I/O0·요청2024와기록2023 불일치·local2021-12-31T23:30-01:00의 UTC2022 일치·다음 Jan1 첫 행 차단/뒤2행 NOT_CHECKED·-00 중간 차단을 확인했다. 변경 metadata는 mock 반환 record의 canonical SHA를 갱신해 같은 get 경계를 검증했으며 DB 쓰기나 운영 자료 수정이 아니다.

`evidence/integration/temporal-normalization-live-integrity-20261018.json`은 보호141개·기존source289개·이전증거1094개·catalog14행 SHA와 예약136314880바이트 불변을 기록한다. source/test 동결 SHA를 유지했다. 최종 근거에도 후보 digest·엄격 소비 부분집합·실제 취득 권위/자원 격리/비원자성 한계를 유지하고 API/UI/front/build/browser를 바꾸거나 재실행하지 않았다. 문서 최종 근거를 반영하고 동결했다.
