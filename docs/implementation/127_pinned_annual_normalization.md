# 127 — 실제 고정 모델을 한 번 읽는 요청 연도2~6개 정규화 관측

## 쉬운 설명과 범위

신규 `backend/app/ml/pinned_annual_normalization.py`의 `inspect_pinned_annual_normalization(store, model_ref, training_report_sha256, requested_years)`는124로 실제 모델 checkpoint/report를 **한 번** 읽고, 그 동일 manifest 객체를125의 장면 읽기에 순서대로 전달한다.126을 연도 수만큼 호출하여 모델을 반복 load하지 않는다. caller checkpoint_manifest·파일 경로·source_scene·normalization 입력은 없다.

이는 내부 읽기 전용 **요청 연도 라벨 묶음**이다. 실제 자료의 temporal/header/acquisition 연도 일치나6개 주×2020~2025 확보 완료를 뜻하지 않는다. `temporal_year_verified:false`를 항상 유지한다. 실제 Registry temporal과 요청 연도 대조는128 후속이며 기관 취득 시점의 진위·grid/mask·과학 승인·실행은 그와도 별도다. 기존124/125/126·Store·API·UI·global-only 실행 gate는 수정하지 않는다.

## 전체 입력 선검사와 snapshot

requested_years는 정확한 builtin list2~6개다. 각 row는 exact `{year,image_ref,evidence_ref,metadata_ref}`이며 year는1900~2200의 정확 int다. bool/float/string은 거부하고 엄격 오름차순·중복 없음을 요구한다. 각 ref는125의 exact3·96번 계약의 id/version 문자열 검사(1..256자)·lowercase hex64를 따른다. 각 row의 세 id/version key는 서로 달라야 하고 연도 간 image id/version도 중복될 수 없다. 모델 ID는124와 같은 ASCII1..100이며 version/자료ID는96번 계약의 원형 문자 범위다.

모델 ref·report SHA와 **모든 row**를 먼저 검사하고 model_ref 및 각 ref의 작은 원형 snapshot을 복사한다. 마지막 row가 잘못돼도 Store/file 읽기0의 INVALID_INPUT이다. invalid 출력의 rows는 빈 목록이며 issue의 year는 null로, 잘못된 caller 값을 그대로 출력하지 않는다. version을 trim/추정/보정하지 않는다.

서로 다른 image id/version도 같은 SHA·artifact URI·원본 scene을 가리킬 수 있다. 이 유일성 규칙은 실제 독립 장면·연차 독립성·정보 누출 방지·서로 다른 취득일 보장이 아니다. evidence/metadata refs는 여러 row에서 재사용할 수 있으며 각 row의 기존125 관계/바이트 검증을 다시 수행한다.

## 호출 순서·failfast·부분 관측

1. 유효한 요청 snapshot을 만든 뒤124를 정확1회 호출한다. 모델 실패는 scene125 호출0·모든 row NOT_CHECKED다.
2. 실제 manifest의 mode가 global/미기재/지원외인122 OUT_OF_SCOPE 경계면 모델 읽기 후 OUT_OF_SCOPE로 반환한다.125 호출·scene Registry 조회0이며 row는 모두 NOT_CHECKED다. **유효 global 요청은 모델 I/O가 있고, 잘못된 global batch는 전체 입력 선검사로 I/O0**인 차이를 구분한다.
3. 지원 범위면 동일 실제 manifest 객체와 각 고정 세 ref를125에 행 순서로 전달한다. 첫 실패/예외에서 failfast하며 뒤의 행은 조회하지 않는다. 앞서 성공한 row와 실패한 row의 nested 관측을 보존하고 나머지 row는 NOT_CHECKED/null이다.
4. 모든 행과 모델 관측이 성공해야 전체 PINNED_YEARS_MATCHED_UNVERIFIED와 aggregate artifact true다. 정상 Store.get은 model1+dataset3×N회이며 checkpoint load는1회다. 등록·쓰기·retry·실행 payload·자동 복구는 없다.

## exact24 출력

필드13개는 schema_version:1, scope:`PINNED_MODEL_REQUESTED_YEARS_READ_ONLY`, status, issue, model_observation, rows, model_observation_calls, scene_observation_calls, checked_rows, checkpoint_artifact_verified, training_report_artifact_verified, registry_references_verified, artifact_bytes_verified다.

추가11개는 항상 false다: state_dict_verified, raster_header_verified, quality_report_verified, quality_mask_verified, source_authority_verified, access_authorization_verified, other_lineage_parents_verified, scientific_accuracy_validated, execution_authorized, workflow_supported, temporal_year_verified.

status는 INVALID_INPUT / MODEL_BLOCKED / OUT_OF_SCOPE / SCENE_BLOCKED / PINNED_YEARS_MATCHED_UNVERIFIED다. issue는 null 또는 exact `{code,field,year}`다. 고정 조합은 INVALID_INPUT/request/null, MODEL_OBSERVATION_BLOCKED/model/null, SCENE_OBSERVATION_BLOCKED/scene/검증된요청연도다. 정상·OUT_OF_SCOPE는 issue null이다. 예외 원문·비밀·경로는 반환하지 않는다.

rows의 각 항목은 exact `{year,status,scene_observation,issue}`이고 status는 NOT_CHECKED / MATCHED_UNVERIFIED / BLOCKED다. scene_observation은125 원 반환 객체 또는 null이며 row issue는 null 또는 `{code:'SCENE_OBSERVATION_BLOCKED',field:'scene'}`다. model_observation은124 원 반환 객체 또는 null이다. 기존 helper의 상세 고정 오류는 이 nested 결과에서 확인한다.

model_observation_calls는 시도한124 호출 수0/1, scene_observation_calls는 시도한125 호출 수0~6이다. checked_rows도 **실패/예외 행을 포함한 시도 수**이며 성공 수가 아니다. 모델의 두 artifact flag는 이전 단계 바이트 확인 이력으로 실패에도 true가 남을 수 있다. 반면 바깥 registry_references_verified·artifact_bytes_verified는 전체 row를 모두 통과한 경우에만 집계한다. 중간 실패 때 앞 row의 nested true가 있어도 전체 집계는 false다.

## 상속한 한계

124의 실제8MiB checkpoint/2MiB report·동일 BytesIO·ZIP/CPU weights_only·manifest bounded JSON 및125/123의 Registry·직접 lineage·명시 source scene/bands·PUBLIC 선언·image64MiB/evidence2MiB/원metadata2MiB 한도를 재사용한다. 품질 모든 상태 관측은 실행/QA 승인이나 ACL 검증이 아니다. evidence 계수 자기 선언은 독립 물리 보정 검증이 아니다. source_url HTTP 접속·네트워크 라이브러리 호출을 추가하지 않는다.

모델과 여러 Registry/file 관측은 순차 snapshot이며 전역 원자성·동시 현재 상태·모든 TOCTOU 제거를 보장하지 않는다. 모델은 한 번 읽고 전체 batch 뒤 재load/재확인하지 않는다. 다른 thread/프로세스가 중간에 모델 파일을 바꾸는 모든 경쟁을 차단하는 실행 gate가 아니다. 기존 Store.get의 DB 원문 JSON decode가 먼저이므로 후행 metadata tree 한도를 DB decode/RSS 전체 hardcap으로 해석하지 않는다. Torch의 ambient allowlist·CPU/RSS/시간 격리 한계도124 그대로다. 무쓰기 trusted-local 내부 함수이며 공개 API/권한/실행에는 별도 설계가 필요하다.

## 시험·동결 인계

담당 집중 **9 PASS / 8.756초 / exit0**: `evidence/integration/annual-normalization-agent-20261018-focused.log`. 실제 임시 TinyUNet CPU checkpoint와2/6개 장면 Registry 묶음으로 모델1회·같은 manifest identity·1+3N get·무쓰기/원본 불변을 확인했다. checkpoint 저장/weights_only 읽기만 했으며 학습·forward·추론·load_state_dict0이다.

전체 shape 선검사 I/O0·bool/연도 범위·오름차순/중복·refs·global valid/invalid 차이·모델 실패·중간/첫 행 예외 failfast·NOT_CHECKED·부분/aggregate flags·고정 오류/privacy·입력 snapshot을 시험했다. Registry temporal은2020인데 요청 라벨1900/2200도 이 범위에서 성공하고 temporal_year_verified=false임을 확인해 **실제연도 미검증 한계**를 직접 보여준다. 이것은 연도 gate를 우회한 성공이 아니라 아직 그 검사가 없는 관측 범위다.

source SHA `4589a70425dcdfc1e6f7b9a065929f74860f572284cf9fd8c021a8fb5fc81953`, test SHA `319a390b4ad3bf3e2c8c2859c66c07dc1107370b78b34f0038ecf80ca93d27c5`로 Root/독립 담당에게 동결 인계했다. Root는 실제 GeoTIFF 묶음·관련 회귀·보존·공통 문서/Git을, 독립 담당은 별도 실제2/6장면/경계 검증을 맡는다. 이해 담당은 완료 소스·시험·한계를 읽고 설명·이론·발표·FAQ·INDEX·변경이력을 갱신한다.

미연결 내부 함수이므로 UI/API/frontend/build/browser를 수정/재실행하지 않는다. 이전120 backend1184/front261은 이번 결과가 아니다. 운영 Registry/모델/파일 쓰기·수집·등록·훈련·추론·배포0이며 연차 실행/전체 개발 완료로 표현하지 않는다.

## 최종 관련·실파일 대비·보존 근거

Root 관련 **46 PASS / 19.993초 / exit0**는 `evidence/integration/annual-normalization-root-related-20261018.log`다. 신규9·126의10·124의14·125의13을 포함하며 집중/독립과 중복 합산하지 않는다.

Root의 `evidence/integration/annual-normalization-runtime-20261018.py`와 같은 stem `.json`·`.log`는 실제 임시6밴드 GeoTIFF3개·실제 Registry9버전·학습하지 않은 CPU checkpoint의 **6시나리오 통과/exit0** 근거다. torch.load1회·Store.get10회·보고서 decoy 무시를 확인했다. 모든 manifest temporal은2021인데 요청2021/2022/2023이 이 범위에서 통과하고 temporal_year_verified=false임을 명시했다. bool year는 I/O0 거부하고, 마지막 실패에는 이전2행 관측을 보존하며 첫 실패에는 뒤2행 NOT_CHECKED임을 확인했다. 기존 DB/파일 무쓰기·훈련/추론0이다.

`evidence/integration/annual-normalization-live-integrity-20261018.json`은 보호141개·기존source287개·이전증거1080개·catalog14행과 예약136314880바이트 불변을 기록한다. source/test 동결 SHA를 유지했다. 이 근거를 temporal 검증·독립 연차 자료 확보·실행 승인으로 확대하지 않는다.

독립 최종 **7 PASS / 0 SKIP / 7.603356초 / exit0**는 `evidence/integration/annual-normalization-independent-20261018.py`와 같은 stem `.json`·`.log`에 동결했다. 별도 TempStore의 실제18버전과 TinyUNet checkpoint로2/6row·모델1회/1+3N get·같은 manifest identity N회·DB 불변/no writes를 검증했다. 전체 입력 오류의 I/O0·global1get·모델 hash 실패·중간/마지막 failfast·입력 snapshot 방어도 확인했다. manifest temporal2024와 요청2020~2025의 불일치가 이번 범위에서는 성공하되 temporal_year_verified=false이며, 다른 image ID가 같은 path/bytes를 참조해도 성공할 수 있다는 한계를 직접 증명했다. 제품 지적0이며 운영 접촉·훈련·추론·API/UI 변경은0이다. 최종 독립 근거를 반영하고 문서를 동결했다.
