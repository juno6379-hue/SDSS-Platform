# 126 — 실제 고정 모델 manifest와 한 장면 Registry 정규화의 자동 읽기 결합

> 후속127: 본 단일 장면 계약 다음으로 실제 모델을 한 번 읽는2~6개 요청 연도 묶음 관측을 `127_pinned_annual_normalization.md`에서 구현·검증했다. 요청 연도와 실제 temporal 대조·실행 승인은128 이후 미완료다.

## 쉬운 설명과 구현 범위

124는 실제 checkpoint 바이트에서 모델 manifest를 읽고125는 caller manifest와 세 Registry 참조를 결합했다. 신규 `backend/app/ml/pinned_scene_normalization.py`의 `inspect_pinned_scene_normalization(store, model_ref, training_report_sha256, image_ref, evidence_ref, metadata_ref)`는124가 실제로 읽은 manifest만125에 전달한다. caller checkpoint_manifest 인수를 제거했으며 보고서의 input_signature/copied manifest로 대체하지 않는다.

한 장면의 **내부 읽기 합성**이다. 기존124/125/Store/API/UI/실행 gate를 바꾸지 않고 Workflow·추론·훈련·등록·쓰기·자동 재시도를 수행하지 않는다.124의 checkpoint CPU weights_only 로드는 수행하지만 load_state_dict/forward/모델 실행은 하지 않는다. 연차 batch·전연차 수집/확보·mask/품질/운영 승인은127 이후 별도 후속이다. 이번 연결로115 global-only 실행 제한이 바뀌지 않는다.

## 호출 순서와 단계 계약

1.124 `read_pinned_model_checkpoint_manifest`를 정확히 한 번 호출해 고정 모델 ID/version/checkpoint SHA·학습 보고서 SHA·실제 checkpoint manifest를 읽는다. 이 단계 실패 또는 예외이면125 호출/scene Registry 조회0이다.
2.124 성공이면 그 반환 객체 안의 실제 detached manifest를125에 그대로 전달한다. image/evidence/metadata refs도 기존125의 고정 참조 계약을 유지한다. 모델의 실제 mode가 global/지원외이면125의 OUT_OF_SCOPE를 재사용하며 scene ref를 읽거나 Dataset Registry를 조회하지 않는다. 정상 global도 모델 record·checkpoint/report 읽기는 이미 수행했다.
3.125가 세 record·명시 scene/bands·직접 lineage·PUBLIC 선언·파일 SHA/정규화 관측까지 성공해야 전체 `PINNED_SCENE_MATCHED_UNVERIFIED`다. 새로운 보정값·출처·상태를 추정/역채우거나 실행 payload를 만들지 않는다.

전체 성공은 정상 경로 Store.get models1회 + dataset_versions3회다.124/125의 원래 반환 객체를 nested 결과로 보존한다. 예외 원문·path·비밀을 출력하지 않고 stage별 고정 오류만 반환한다. 별도 retry/rollback/write/lock/claim을 추가하지 않는다.

## exact20 반환

| 필드 | 값/의미 |
|---|---|
| schema_version | 1 |
| scope | PINNED_MODEL_REGISTERED_SCENE_READ_ONLY |
| status | MODEL_BLOCKED / OUT_OF_SCOPE / SCENE_BLOCKED / PINNED_SCENE_MATCHED_UNVERIFIED |
| issue | null 또는 exact {code,field} |
| model_observation | 124 원 반환 객체 또는 null |
| scene_observation | 125 원 반환 객체 또는 null |
| checkpoint_artifact_verified | 124의 해당 바이트 확인 이력 |
| training_report_artifact_verified | 124의 해당 바이트 확인 이력 |
| registry_references_verified | 125의3개 metadata/ref 확인 이력 |
| artifact_bytes_verified | checkpoint/report와 scene 파일 전체 관측 성공 시만 true |

나머지10개 필드는 항상 false다: state_dict_verified, raster_header_verified, quality_report_verified, quality_mask_verified, source_authority_verified, access_authorization_verified, other_lineage_parents_verified, scientific_accuracy_validated, execution_authorized, workflow_supported.

MODEL_BLOCKED의 issue는 `{code:'MODEL_OBSERVATION_BLOCKED',field:'model'}`, SCENE_BLOCKED는 `{code:'SCENE_OBSERVATION_BLOCKED',field:'scene'}`다. 세부 이유는 보존한 nested124/125의 고정 코드로 확인한다. 예외로 nested 결과를 얻지 못한 경우 해당 관측은 null이다. OUT_OF_SCOPE와 전체 성공의 issue는 null이다.

부분 true는 단계 이력이다. 예를 들어 checkpoint SHA 성공 후 report 변조는 MODEL_BLOCKED이면서 checkpoint_artifact_verified만 true일 수 있다. 모델 성공 후 scene 선언 누락은 SCENE_BLOCKED이면서 모델의 두 artifact와 registry_references_verified가 true일 수 있다. 어느 경우도 전체 artifact·실행·과학 승인으로 확대하지 않는다.125 내부 checkpoint_artifact_verified=false는125 자체가 caller manifest만 처리했다는 원래 범위로 그대로 보존되며,126의 실제124 관측 flag와 모순이 아니다.

## 상속하는 한도와 한계

124의 checkpoint8MiB/report2MiB·동일 BytesIO SHA/ZIP_STORED·CPU weights_only·manifest bounded JSON 검증,125의 Registry metadata/ref·명시 scene_id/band_names·lineage 두 역할·PUBLIC 소비 경계·123의 image64MiB/evidence2MiB/원metadata2MiB·path/link/변경 검사 한도를 그대로 따른다. 원 schema/기존 gate를 수정하지 않는다.

checkpoint architecture/manifest를 읽는 것은 weights/state shape·추론 호환성을 검사한 것이 아니다. 실제 checkpoint의 manifest에 caller가 쓴 승인 필드가 있어도 wrapper의10개 false가 바뀌지 않는다. evidence 계수는 같은 pin 문서의 선언이지 물리적인 제품 보정값의 독립 검증이 아니다. 품질 상태 전부 관측 가능/PUBLIC 선언만 소비하는125 정책은 QA 본문·기관 권위·실제 ACL·모델 승인·mask/CRS/정렬/header 확인이 아니다.

모델 관측과 세 scene Registry/file 관측은 순차적이다. 같은 시점에 묶은 전역 원자 snapshot/잠금이 아니며 모델을 읽은 뒤 checkpoint/report가 바뀌는 모든 경쟁을 제거하거나 최종 재확인하지 않는다. 현재 반환된 관측과 읽은 바이트의 범위로 해석한다. evidence는125와123에서 같은 SHA로 두 번 읽는다. Store.get의 DB 원문 무상한 JSON decode는 후행 metadata tree 한도 이전에 발생하므로 전체 RSS hardcap이 아니다. weights_only/ZIP 한도도 CPU/RSS/시간 sandbox·ambient allowlist 격리를 보장하지 않는다. 설치 Torch/호출 환경 allowlist를 상속하고 add/clear/replace나 False fallback을 하지 않는다.

신뢰할 수 있는 내부 로컬 작업 범위이며 source_url HTTP fetch·네트워크 라이브러리 호출은 없다. mapped drive의 실제 매체나 기관 원출처는 증명하지 않는다.127 연차 wrapper 및 향후 실행/공개 API에는 별도 snapshot·권한·자원/실행 설계가 필요하다.

## 시험과 인계

담당 집중 **10 PASS / 3.261초 / exit0**: `evidence/integration/pinned-scene-agent-20261018-focused.log`. TempStore의3개 Registry record와 임시6밴드 TinyUNet 초기화 checkpoint를 사용했다. 실제 저장/CPU weights_only 읽기는 했지만 훈련·forward·추론·load_state_dict는0이다.

전체4get·Store.put0·원본 DB/파일 불변, 모델 실패 시 scene 함수 호출/조회0, 실제 global 모델은 모델1get만, actual manifest identity 전달/보고서 decoy 무시/caller manifest 인수 부재, checkpoint/report/scene3파일 변조·고정 ref·lineage·단계 사이 변경·부분 true·nested 결과 보존·고정 예외/no retry·입력 불변을 확인했다. 이는 운영 자료가 아닌 TESTED_SYNTHETIC의 내부 합성 검증이다.

source SHA `b4553a8c3163f8f7213e745b8f8b4ccb989300fd48e49286e0eecadbb900b9e1`, test SHA `08435da8362f375b0f4afc97d2b54044a4562a15d57aacc31557aea644a26ab4`로 Root/독립 담당에게 동결 인계했다. Root는 관련/runtime/보존·공통 문서·Git을, 독립 담당은 별도 actual checkpoint/등록/단계 fixture 검증을 맡는다. 이해 담당에는 완료 코드·시험·한계를 전달해 쉬운 설명·발표·FAQ·INDEX·변경이력을 갱신한다.

미연결 내부 함수이므로 UI/API/frontend/build/browser를 수정하거나 재실행하지 않는다. 이전120 backend1184/front261은 과거 근거이며 이번 집중과 합산하지 않는다. 운영 모델 load·Store 쓰기·수집·등록·훈련·추론·배포0이다. single-scene 연결126과 all-year batch127은 별개이며 전체 프로젝트 완료로 표시하지 않는다.

## 최종 관련·실파일 대비·보존 근거

Root 관련 **37 PASS / 12.616초 / exit0**는 `evidence/integration/pinned-scene-root-related-20261018.log`다. 신규10·124의14·125의13을 포함하며 집중/독립과 중복 합산하지 않는다.

Root의 `evidence/integration/pinned-scene-runtime-20261018.py`와 같은 stem `.json`·`.log`는 실제 임시6밴드 GeoTIFF·학습하지 않은 CPU checkpoint·등록3참조의 **6시나리오 통과/exit0** 근거다. 보고서 decoyglobal과 actual per_scene 구분, legacy 선언 미확보 차단과 세 scene 역할 바이트 변조 차단을 확인했다. 최초 runtime import 실패는 Root 실행의 PYTHONPATH .runtime 누락이었으며 소스 변경 없이 환경 정정 후 통과했다. 원로그 `pinned-scene-runtime-initial-20261018.log`를 보존하고 제품 결함으로 표시하지 않는다. 임시 생성 자료의 실제 manifest/바이트 연결이며 훈련·추론·운영 등록이 아니다.

`evidence/integration/pinned-scene-live-integrity-20261018.json`은 보호141개·기존source285개·이전증거1065개·catalog14행 SHA와 예약136314880바이트 불변을 확인했다. 운영 자료에는 실행하지 않았고 source/test 동결 SHA를 유지했다.

독립 최종 **8 PASS / 0 SKIP / 2.807693초 / exit0**는 `evidence/integration/pinned-scene-independent-20261018.py`와 같은 stem `.json`·`.log`에 동결했다. 별도 TempStore의 실제3등록과 TinyUNet6 CPU checkpoint 저장/읽기로 보고서 decoy 무시·실제 manifest 객체의125 전달1회·성공1model+3dataset get·global의 scene 조회0·모델 실패 시125 호출0·파일/참조/명시 확장 누락 차단·부분 flags·stage 예외/경로 비노출·exact20/10false를 확인했다. DB 바이트 불변/no put/forward/load_state_dict와 caller manifest/path 인수 부재도 검증했다. source 동결 SHA 및 Git2a980f9의 기존 핵심8 source SHA·tracked source 불변, 제품 지적0이다. inherited allowlist/자원·Store predecode·비원자 snapshot 한계를 유지하고 API/UI/frontend/build/browser를 수정·재실행하지 않았다. 최종 독립 근거 반영 후 문서를 동결했다.
