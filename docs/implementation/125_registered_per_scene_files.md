# 125 — 세 Dataset Registry 고정 참조와 한 장면의 정규화 파일 결합

> 후속126: 실제 모델 checkpoint manifest와 본 장면 reader의 자동 연결을 `126_pinned_scene_normalization.md`에서 구현·검증했다. caller manifest 없는 단일 장면 내부 읽기이며 연차 일괄 사전검증·실행 gate는127 이후 미완료다.

## 쉬운 설명과 이번 범위

123은 caller가 지정한 경로·SHA를 읽었다. 신규 `backend/app/ml/registered_per_scene_files.py`의 `read_registered_per_scene_files(store, checkpoint_manifest, image_ref, evidence_ref, metadata_ref)`는 영상·보정 evidence·원 metadata의 세 **등록 ID/version/SHA**를 받아 Registry record와 canonical manifest를 검산하고 실제 파일 관측123에 연결한다. caller가 source_scene·normalization·원문 경로를 별도로 제출하지 않는다.

한 장면의 내부 읽기 helper이며 실행/API/UI에 연결하지 않는다. checkpoint_manifest는 여전히 caller 입력이다.124의 실제 model_ref/checkpoint manifest 읽기와 자동 결합하지 않고, 연차 묶음·품질 mask·기존115 실행은126 이후 후속으로 남긴다. 기존 Registry schema·Store·등록·실행 코드를 수정하지 않는다. 운영 등록·수집·훈련·추론·모델/파일 쓰기0이다.

## 세 고정 참조와 신규 내부 소비 계약

각 ref는 exact `{id,version,sha256}`다.96의 원형 ID/version 문자열 검사와 고정 version alias 거부·lowercase hex64를 사용하며 서로 다른 세 id/version key를 요구한다. 같은 ID라도 다른 version은 다른 key다. version을 trim/보정하거나 latest/current를 해석하지 않는다.

Store.get('dataset_versions', version_key(id,version))을 역할별 한 번, 정상 경로 총3회 호출한다. 저장 key/본문id·manifest dataset_id/version·requested artifact SHA·canonical manifest SHA가 일치해야 한다. 반환 manifest tree를124의 bounded builtin JSON 복사로 먼저 제한하고 `canonical_manifest`만 호출한다. 원자 등록/이력 인증을 새로 증명하는 것이 아니라 현재 저장된 선언의 정합 관측이다. `resolve_version`, `verify_artifact`, `register_version`를 호출하지 않아 상한 검사 전에 기존 무한 asset hash나 quality 파일 부수 조회를 하지 않는다.

역할 타입은 raster / document / document다. 세 역할 모두 PUBLIC 선언이어야 한다. 이는 **새 reader만의 소비 경계**이며 실제 ACL·caller 인증·기관 허가를 검사한 것이 아니다. RAW/STAGED/STANDARDIZED/VALIDATED/REJECTED 모든 quality 상태는 진단 대상이다. quality_status는 그대로 반환하고 QA 본문·품질 승인·학습 가능성을 추정하지 않는다. REJECTED 자료의 바이트 조회가 성공해도 실행/QA 승인이 아니다.

원 GMAIS source schema는 additionalProperties:false가 없어 아래 명시 확장 필드를 수용한다. 이번 reader는 image manifest.source의 `scene_id`와 `band_names`를 필수로 요구한다. 이는 **신규 내부 소비 계약**이며 upstream 기관의 공식 필드/정책으로 주장하지 않는다. source.scene_id는 원형128자 이하 제어문자 없는 문자열, source.band_names는 원형64자 이하 문자열6개다. source.product는 제품군일 수 있으므로 장면 ID로 추정/동등 강제하지 않는다. checkpoint.band_names를 source 선언으로 복사해 발명하지 않는다. 필드 없는 legacy record는 BLOCKED이며 기존 record를 역채우거나 수정하지 않는다.

evidence manifest.lineage에는 아래 직접 부모 두 역할을 각각 정확1개 요구하고 id/version/SHA가 요청 ref와 같아야 한다.

| 내부 role | 참조 |
|---|---|
| normalization_input_image | image_ref |
| normalization_source_metadata | metadata_ref |

두 role 역시 내부 계약이며 공식 upstream 표준 role을 추가한 것이 아니다. 중복 role·반대 role·다른 pin을 거부한다. 다른 직접 부모는 허용하고 전체 manifest canonical/schema 형식은 검사하지만 그 부모의 record/asset·전체 DAG·시간/기관 의미는 재귀 조회하지 않는다.

## 파일 경로·SHA·보정 선언 결합

명시 store.root와 각 manifest.artifact_uri는123의 상대 경로·루트/ancestor symlink/junction·UNC/탈출 거부 경계로 검사한다. evidence를 최대2MiB 복사해 evidence_ref SHA와 비교하고 strict JSON으로 파싱한다. evidence.source_metadata_path는 metadata Registry artifact_uri와 안전 정규화 후 같은 경로여야 하고 evidence.source_metadata_sha256은 metadata_ref SHA와 같아야 한다.

source_scene은 image manifest의 명시 scene_id/band_names와 image_ref SHA에서 구성한다. normalization은 읽은 evidence의 scale/offset, evidence Registry 경로·SHA에서 구성한다.123이 같은 evidence pin을 다시 읽고122로 product_id·밴드·보정 선언을 검산한 뒤 영상64MiB·원 metadata2MiB의 실제 SHA를 확인한다. image/source의 scene_id·밴드 원문을 유지하며 evidence에서 source.scene_id를 역추정하지 않는다.

scale/offset은 동일하게 pin된 evidence JSON에서 추출한 값이다.123에서 같은 pin을 재검산한다고 물리적인 제품 보정값을 독립 검증하는 것은 아니다. source_url도 HTTP로 접속하거나 기관 권위로 인증하지 않는다. evidence는 초기 추출과123에서 두 번 읽으므로 두 순차 snapshot이다. 같은 SHA 재검사로 중간 변경을 거부하지만 세 Registry record·세 파일을 같은 시점에 묶은 원자 snapshot이 아니다.

`canonical_manifest`의 vendored schema validator가 cold 상태면 기존 schema 파일을 읽는다. source asset을 무상한 읽는 것은 아니지만 파일 I/O0인 순수 함수로 표현하지 않는다. 재사용 metadata tree의2MiB byte budget·깊이16·node65536 등은 반환된 JSON tree의 범위다. 기존 Store.get는 DB body를 상한 없는 json.loads로 반환하므로 신규 bounded tree 검사는 **반환된 dict 이후**에 일어난다. DB 원문 decode부터 RSS 전체 hardcap을 보장하지 않는다.124 등 기존 Store 호출에도 상속되는 trusted-local 경계이며 외부 공개/SQL 원문 경계 제한은 후속이다. 기존 Store를 수정하거나 대체하지 않았다.

## exact19 결과와 오류

필드8개는 schema_version:1, scope:`REGISTERED_PER_SCENE_FILES_READ_ONLY`, status, issue, registry_bindings, file_observation, registry_references_verified, artifact_bytes_verified다. 추가11개는 항상 false다.

- checkpoint_artifact_verified / raster_header_verified
- quality_report_verified / quality_mask_verified
- source_authority_verified / access_authorization_verified
- other_lineage_parents_verified / state_dict_verified
- scientific_accuracy_validated / execution_authorized / workflow_supported

status는 OUT_OF_SCOPE / BLOCKED / REGISTERED_FILES_MATCHED_UNVERIFIED다. global/mode 누락/지원외 정상 mode는122 경계대로 OUT_OF_SCOPE이며 Store/file I/O0이다. issue는 null 또는 exact `{code,field}`이고 caller 경로·예외 내용은 반환하지 않는다. file_observation은123의 exact12 또는 null이다. registry_bindings는 완료한 record 관측 순서의 `{role,ref,manifest_sha256,quality_status,access_class}` 목록이다. ref는 원형 exact3 복사다.

registry_references_verified=true는 세 record의 key/identity/canonical SHA/type/PUBLIC **선언 관측**을 마쳤다는 뜻이다. 후속 scene/lineage/file에서 BLOCKED여도 남으며 전체 성공이 아니다. 바깥 artifact_bytes_verified는123의 FILES_MATCHED_UNVERIFIED까지 도달한 경우만 true다. 안쪽123의 부분 MATCH는 해당 역할 읽기 이력으로만 해석한다. checkpoint/실물 header·CRS/정렬/mask·물리 source/calibration·float32·기관 권위·ACL·다른 부모·state/실행/과학 검증은 하지 않는다.

새 고정 code는 INVALID_INPUT / REGISTRY_RECORD_UNAVAILABLE / REGISTRY_RECORD_INVALID / REGISTRY_REFERENCE_CONFLICT / REGISTRY_TYPE_MISMATCH / ACCESS_DECLARATION_BLOCKED / SCENE_DECLARATION_MISSING / SCENE_DECLARATION_INVALID / LINEAGE_BINDING_INVALID / EVIDENCE_BINDING_INVALID / DECLARATION_NOT_CONSISTENT다.123의 ROOT_UNAVAILABLE / PATH_INVALID / FILE_UNAVAILABLE / FILE_LIMIT / FILE_CHANGED / SHA256_MISMATCH / EVIDENCE_JSON_INVALID 등도 유지한다. 이는 내부 반환 코드이며 새 HTTP endpoint/상태를 만들지 않는다.

## 시험·동결·후속

담당 집중 **13 PASS / 4.377초 / exit0**: `evidence/integration/registry-normalization-agent-focused-20261018.log`. TempStore의 canonical Registry3개와 임의 영상 역할 바이트·evidence JSON·원 XML을 사용했다. 실제 영상 header 검증으로 표현하지 않는다.3get/no resolver/무한 verifier 미호출·명시 source2필드·제품군≠scene·모든 quality/PUBLIC 정책·직접 lineage 두 역할/추가 부모 미조회·metadata 경로/SHA·canonical metadata tamper·evidence 두 번째 읽기의 변경·파일별 변조/상한·Windows 경로·원본/Store.put 불변을 확인했다. 운영 등록/Store 접촉은0이다.

source SHA `8c36bf4f5715784db59c46f378878675702804878ba132d272657e5c86ff2866`, test SHA `04f209ee6fb60b21ad5ab4410329d0277a9b7d5d34620a8cb4da919b31086379`로 Root/독립 담당에게 동결 인계했다. Root는 실제 임시 register_version/GeoTIFF 대비·관련 시험·보존, 독립 담당은 별도3ref/상태/경계 검토를 맡는다. 관련/runtime 로그는 Root가 별도 suffix로 관리하며 중복 실행·덮어쓰기를 피한다.

미연결 내부 reader이므로 UI/API/global-only 실행 Gate를 바꾸지 않고 frontend/build/browser를 재실행하지 않는다. 이전120 backend1184/front261은 이번 검증 결과가 아니다. 다음126에서124의 실제 고정 모델 manifest와 이 한 장면 reader의 명시 조합, 이후 연차·품질/mask·실행 계약을 별도 검토한다. Root가 완료 코드·검증 근거·한계를 이해 담당에게 전달해 쉬운 설명·이론·발표·FAQ·INDEX·변경이력을 갱신한다.

## 최종 독립·관련·실파일 대비·보존 근거

독립 **9 PASS / 0 SKIP / 2.9209618초 / exit0**는 `evidence/integration/registry-normalization-independent-20261018.py`와 같은 stem `.json`·`.log`에 동결했다. 추가 race 시험 전의8 PASS/2.097초는 별도 initial JSON·로그에 보존했고 제품 결함0이다. 실제 TempStore에 등록한3개 version fixture로 reader의3get만 허용하고 put/resolve/verify/register 호출 금지·Torch import0·DB 원문 바이트 불변을 확인했다. 전 quality 관측·PUBLIC 선언 경계·명시 source 두 필드와 제품군 분리·refs/canonical/types·직접 lineage 역할·metadata 경로/SHA·실제 image 변조와 Registry 결합 뒤123 호출 직전 image 변경 주입 거부를 검증했다. Git4824b45의 기존 핵심8 source SHA·tracked source 불변이다.

Root 관련 **38 PASS / 6.463초 / exit0**는 `evidence/integration/registry-normalization-root-related-20261018.log`다. 신규13·기존 DatasetVersion11·123 reader14를 포함하며 집중·독립과 중복 합산하지 않는다.

Root의 `evidence/integration/registry-normalization-runtime-20261018.py`와 같은 stem `.json`·`.log`는 **6 PASS**다. 실제 임시6밴드 GeoTIFF·보정 JSON·원 metadata 세 registered refs를 결합하고 명시 scene와 generic product를 구분했다. legacy scene 선언 부재와 세 파일의 바이트 변조는 차단했다. 임시 등록 자료의 바이트 연결을 확인한 것이며 실제 기관 출처·독립 물리 보정값·품질/ACL 승인·운영 모델 실행의 증거가 아니다.

`evidence/integration/registry-normalization-live-integrity-20261018.json`에서 보호141개·기존source283개·이전증거1049개·catalog14행 SHA와 예약136314880바이트 불변을 확인했다. source/test 동결 SHA를 유지했고 문서에 최종 근거를 반영해 동결했다. evidence의 계수 자기 선언과 독립 물리 검증, Store.get의 DB 원문 predecode/RSS 한계, caller checkpoint와 실제124 자동 결합126 후속을 구분하며 기존 API/UI/front/build/browser를 바꾸거나 재실행하지 않았다.
