# 131 — 등록 품질 보고서와 명시 마스크의 고정 참조 읽기

상태: **TESTED_SYNTHETIC**. `read_registered_quality_mask_files(store, image_ref, quality_report_ref, mask_ref)`는 한 장면의 등록 영상·품질 보고서·명시 마스크 참조와 실제 파일 바이트를 읽기 전용으로 결합한다. 신규 파일은 `backend/app/ml/registered_quality_mask_files.py`, 집중 시험과 본 문서뿐이다. 기존 Registry·GMAIS schema·115 실행 gate·124~130·API/UI를 수정하지 않았다. 130 배치의 자동 연결은 후속으로 분리한다.

## 필요한 새 내부 보고서 계약

기존 `dataset_registry.verify_artifact`는 VALIDATED 자료의 `quality_report_ref` 존재와 로컬 경로만 확인한다. 115 실행 gate는 요청에 고정한 품질 보고서 SHA와 파일을 비교한다. 기존 소스·scripts·tests를 검색한 결과 이번 envelope를 생성하는 producer는 확인되지 않았다. 따라서 아래 형식은 **새 내부 소비 계약**이며 GMAIS 공식 품질 표준·기관 정책·기존 producer 출력으로 표현하지 않는다.

보고서 JSON은 정확히 **5개 키**를 요구한다.

```json
{
  "schema_version": 1,
  "scope": "LCLUC_QUALITY_MASK_EVIDENCE",
  "image_ref": {"id": "fixed-image", "version": "v1", "sha256": "64 lowercase hex"},
  "mask_ref": {"id": "fixed-mask", "version": "v1", "sha256": "64 lowercase hex"},
  "quality_status": "RAW"
}
```

SHA 예시 문자열은 설명용이며 실제 유효 입력이 아니다. schema_version은 bool을 제외한 정확한 int 1이다. image_ref와 mask_ref는 각 요청 참조와 원형 그대로 같아야 한다. quality_status는 영상 manifest의 선언과 같아야 한다. RAW/STAGED/STANDARDIZED/VALIDATED/REJECTED 모두 진단할 수 있지만 품질 승인으로 승격하지 않는다. legacy `{}`·`pass:[]`·추가 명령 키·누락값을 추정하거나 보완하지 않는다.

## 선검사와 파일 관측 순서

세 참조는 정확한 `{id,version,sha256}`이며 96번 계약의 문자열 검사와 고정 버전·소문자 hex SHA 검사를 사용한다. 세 id/version 쌍은 서로 달라야 한다. 모든 입력 참조를 먼저 검증·복사한 뒤 Store에 접근한다. 잘못된 입력은 Store I/O 없이 BLOCKED다.

Store.get을 영상·보고서·마스크 순서로 각각 한 번 호출한다. 반환 record의 id, bounded canonical manifest, manifest SHA, 고정 id/version/artifact SHA를 검산한다. 자료 유형은 각각 raster/document/raster여야 하고, **세 record 모두 PUBLIC 선언을 확인한 뒤** 파일을 읽는다. PUBLIC은 새 reader의 선언 소비 제한이지 실제 ACL 검사나 접근 승인 증명이 아니다. resolve_version·verify_artifact·재귀 lineage 조회·등록·Store.put은 호출하지 않는다.

보고서 manifest의 직접 lineage에는 `quality_input_image`와 `quality_input_mask`가 각각 정확히 하나 있어야 하며 해당 id/version/SHA가 요청과 같아야 한다. 다른 직접 부모 선언은 허용하지만 그 자산이나 전체 DAG는 조회하지 않는다. 영상의 `quality_report_ref`와 보고서의 `artifact_uri`는 같은 root 아래 정규화된 경로로 같아야 한다. RAW 영상도 명시 참조가 없으면 차단하며 파일명으로 추측하지 않는다.

123의 root·상대 경로·링크/junction·일반 파일·전후 식별자 및 성장 제한을 적용한다. 영상 64 MiB, 보고서 2 MiB, 마스크 16 MiB 상한이다. 보고서의 bounded 복사 바이트와 SHA를 먼저 확인하고 strict UTF-8 JSON으로 duplicate/NaN/Infinity/overflow/surrogate·과도한 깊이/노드를 거부한다. 124의 bounded JSON tree 검사 후 exact envelope를 검산한다. 그 다음 영상 SHA, 마지막으로 마스크 SHA를 확인한다. 보고서 바이트가 맞아도 envelope가 잘못되면 영상·마스크를 읽지 않는다.

마스크는 **불투명 바이트의 SHA만** 검사한다. raster 유형 선언은 실제 TIFF/header·CRS·격자·band·nodata·mask pixel 의미를 확인한 것이 아니다. 별도 등록 id/version이라도 영상과 마스크의 URI/SHA가 같을 수 있고 이를 추가로 금지하지 않는다. 이때도 역할 선언 일치만 관측하며 물리적으로 구별되는 마스크나 유효 픽셀 증거로 해석하지 않는다. 후속 header/grid/mask 의미 검사는 별도 단위다.

## exact18 결과와 부분 성공의 뜻

반환은 `schema_version:1`, `scope:'REGISTERED_QUALITY_MASK_FILES_READ_ONLY'`, status, issue, registry_bindings, file_bindings, registry_references_verified, report_bindings_verified, artifact_bytes_verified와 아래 9개 false로 구성된다.

- quality_report_verified / quality_mask_verified / raster_header_verified
- state_dict_verified / source_authority_verified / access_authorization_verified
- scientific_accuracy_validated / execution_authorized / workflow_supported

status는 BLOCKED 또는 REGISTERED_QUALITY_MASK_MATCHED_UNVERIFIED다. issue는 null 또는 고정 `{code,field}`다. raw 경로·보고서 원문·예외 메시지는 반환하지 않는다. registry_bindings는 완료한 등록 관측 순서대로 `{role,ref,manifest_sha256,quality_status,access_class}`다. file_bindings는 영상/보고서/마스크 순서의 `{role,status}`이며 상태는 NOT_CHECKED 또는 MATCH다. 실제 읽기는 보고서부터이므로 목록 순서와 읽기 순서를 혼동하지 않는다. NOT_CHECKED는 SHA 성공 MATCH를 아직 확보하지 못했다는 뜻이며, 읽기 시도 자체가 없었다는 뜻은 아니다. SHA 불일치로 이미 읽은 파일도 NOT_CHECKED일 수 있으므로 issue와 함께 해석한다.

registry_references_verified는 세 등록 record의 identity/canonical/type/PUBLIC 결합이 완료되면 true가 되어 후행 lineage·경로·파일 실패에도 남는다. report_bindings_verified는 고정 보고서 바이트의 envelope와 요청·영상 선언 결합 후 true가 되어 후행 영상/마스크 실패에도 남는다. file MATCH는 해당 역할 SHA 관측 이력이며 JSON 의미나 전체 성공이 아니다. **artifact_bytes_verified만 세 역할의 모든 결합·바이트 확인 완료 때 true**다. 모든 품질/권위/실행 관련 false는 그대로 유지한다.

고정 오류에는 INVALID_INPUT, REGISTRY_RECORD_UNAVAILABLE, REGISTRY_RECORD_INVALID, REGISTRY_REFERENCE_CONFLICT, REGISTRY_TYPE_MISMATCH, ACCESS_DECLARATION_BLOCKED, LINEAGE_BINDING_INVALID, QUALITY_REPORT_PATH_MISMATCH, SHA256_MISMATCH, QUALITY_REPORT_INVALID, QUALITY_REPORT_BINDING_MISMATCH 및 재사용한 bounded reader/tree 오류가 있다. 앞선 실패가 뒤의 검사를 막는다.

## 한계와 검증 범위

보고서 envelope는 고정 역할·품질 상태의 **선언 일치**일 뿐 점수·임계값·QA 정책의 타당성·기관 승인·과학적 품질을 검증하지 않는다. 파일 자체의 SHA 일치는 보고서 주장이나 mask 의미를 참으로 만들지 않는다. 모델 checkpoint·state·추론·훈련·실행에 자동 전달하지 않는다.

기존 Store.get는 DB body를 무상한 decode한 뒤 반환하므로 bounded tree는 그 이후 범위다. DB 원문 decode·전체 RSS/시간 hardcap이나 불신 원격 서비스 경계를 보장하지 않는다. 세 record와 세 파일은 순차 관측이며 단일 원자 snapshot이 아니다. 기존 링크/식별자 검사도 모든 TOCTOU·FIFO 경주를 완전히 제거하지 않는다. mapped drive의 실제 저장 매체를 증명하지 않고 HTTP/source URL 조회나 네트워크 라이브러리 호출을 추가하지 않는다.

담당 최종 집중 **10 PASS / 5.212초 / exit 0**는 `evidence/integration/quality-mask-agent-20261018-focused-final.log`다. 최초 10 PASS / 4.242초 로그 `quality-mask-agent-20261018-focused.log`는 보완 전 근거로 보존했다. 독립 읽기 검토에서 재사용 parser/tree 오류의 field가 normalization_evidence/checkpoint_manifest로 남는 점을 확인해 신규 helper에서 code를 유지하고 field만 quality_report로 매핑했다. malformed JSON과 깊이 18의 bounded tree 회귀를 추가했으며 기존123/124는 수정하지 않았다. 실제 TempStore·임시 opaque 파일로 exact18/9false, get 3회·무쓰기·resolver 금지, 전 품질 상태, 선검사 I/O0·caller 참조 snapshot, 전 역할 type/PUBLIC/pin 선검사, lineage 누락/중복/SHA·추가 부모 미조회, 명시 경로, legacy/추가 키/strict JSON, 각 파일 변조·부분 flag, 상한·부재·비정규 파일·안전 오류를 확인했다. 불투명 mask의 성공은 mask 유효성 검증이 아니다.

source SHA `d20caf38bb67db6374864546e541bd9d2893d1e549c85f4e98c7ddb68145047b`, test SHA `6a10deb09606af535512bd61aa5806f0cc3421fbd0b8a577342cc4877cd80b49`로 Root/독립 담당에게 동결 인계했다. Root는 관련 회귀·실파일 대조·보존·공통 문서/인계/Git을, 독립 담당은 별도 fixture 경계를 검증한다. 이해 담당은 완료 구현·근거·한계를 해설/발표/FAQ/INDEX/변경 이력에 반영한다. 내부 미연결 reader이므로 UI/API/frontend/build/browser 재실행은 필요하지 않다. 운영 자료·등록·모델 load·수집·훈련·추론·배포는 수행하지 않았다.

## 독립 최종 근거

독립 **8 PASS / 0 SKIP / 3.722738초 / exit 0**는 `evidence/integration/quality-mask-independent-20261018.py`와 같은 stem `.json`·`.log`에 동결했다. 실제 TempStore의 세 등록 참조와 세 get, DB/전체 파일 불변을 확인했다. put/register/resolve/verify 호출과 Torch import는 없었다. ref 선검사, 두 lineage 역할, 정규화된 경로, 유형/PUBLIC의 파일 전 차단, exact envelope와 legacy/명령 추가 키/schema bool/핀·품질 충돌을 검증했다. 모든 품질 상태, 세 파일 변조와 역할별 상한, 부분 flag·요청 참조 복사, 같은 파일을 가리키는 opaque image/mask가 mask 의미 검증으로 승격되지 않음도 확인했다.

malformed JSON과 깊이 18 오류의 field가 quality_report로 매핑됨을 재검증해 읽기 검토 지적을 종결했다. 최종 source SHA와 Git e4ed887의 기존 핵심 8개 source SHA·tracked source 불변이며 추가 제품 지적은 없다. NOT_CHECKED는 성공 MATCH 미확보이지 I/O0이 아니라는 범위를 유지한다. 운영·훈련·추론·header·픽셀 읽기 및 API/UI/frontend/build/browser 변경·재실행은 없었다.

## Root 관련 시험·실파일 대조·보존 마감

Root 관련 **48 PASS / 11.419초 / exit 0**는 `evidence/integration/quality-mask-root-related-20261018.log`다. 신규 10개, DatasetRegistry 11개,125의 13개,123의 14개를 포함하며 집중·독립과 중복 합산하지 않는다.

`evidence/integration/quality-mask-runtime-20261018.py`와 같은 stem `.json`·`.log`는 실제 Temp 영상/마스크 GeoTIFF 및 세 등록 버전의 **7개 시나리오 통과**를 기록한다. 정상 결합, opaque mask의 SHA 성공과 QA false, 보고서/영상/마스크 바이트 변조, legacy envelope, 명시 보고서 경로 부재를 확인했다. reader는 get 3회만 사용하고 쓰기·모델 접근·Torch/Rasterio import 시도 없이 동작했으며 전체 Temp 파일과 DB를 보존했다. 실제 GeoTIFF fixture를 사용했더라도 이 reader 자체가 헤더나 픽셀을 검사한 것은 아니다.

`evidence/integration/quality-mask-live-integrity-20261018.json`은 보호 141개·기존 source 295개·이전 증거 1138개·catalog 14행 SHA와 예약 136314880바이트 불변을 기록한다. source/tests 최종 동결 SHA를 유지했고 기존 제품 소스는 수정하지 않았다. 내부 미연결 reader의 집중·관련·독립·실파일 대조 범위로 마감하며 이전 전체 backend/frontend 결과를 이번 재실행으로 표현하지 않는다. 130 배치 연결과 실제 mask header/grid/값·QA 정책·기관·과학·실행 승인은 별도 후속이다. 최종 근거를 반영한 뒤 문서를 동결했다.

## 후속132

실제 영상·마스크 헤더와 격자 정합 진단은 `132_registered_quality_mask_grid.md` 및 신규 `registered_quality_mask_grid.py`에서 수행한다. 131의 바이트 관측을 변경하지 않고 성공 후 재고정 SHA와 헤더를 검사한다. 마스크 픽셀값·의미·QA 승인은 여전히 미검증이다.
