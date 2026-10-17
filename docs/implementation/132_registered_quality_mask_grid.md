# 132 — 고정 품질 참조의 실제 영상·마스크 헤더와 격자 대조

상태: **TESTED_SYNTHETIC**. 신규 `inspect_registered_quality_mask_grid(store, image_ref, quality_report_ref, mask_ref)`는 131의 고정 등록 참조·품질 선언·파일 SHA 관측 뒤 실제 영상과 마스크의 GTiff 헤더를 비교한다. 신규 `backend/app/ml/registered_quality_mask_grid.py`, 집중 시험, 본 문서만 추가한다. 기존 123~131·Registry schema·실행 gate·API/UI는 변경하지 않는다. 한 장면 내부 reader이며 130 연차 배치 자동 연결이나 실제 QA/마스크 값 검증은 수행하지 않는다.

## 같은 등록 관측과 의도적인 재읽기

세 exact 참조와 서로 다른 id/version을 먼저 검증·복사한다. invalid는 고정 invalid sentinel로 원131 결과를 생성해 Store I/O를 하지 않는다. get/root 전용 proxy가 131의 실제 영상·마스크 get에서 반환된 record의 bounded canonical manifest, id/version/SHA, raster 유형과 PUBLIC 선언을 검사하고 같은 canonical copy를 131에 돌려준다. 다른 시점의 별도 get으로 경로를 얻지 않는다. 품질 보고서는 원131이 검산한다.

원131을 정확히 한 번 호출하며 원형 결과를 중첩 보존한다. 131 실패 시 영상·마스크 헤더 검사는 시작하지 않는다. 성공 후 캡처한 영상 manifest의 명시 `source.band_names`가 B02/B03/B04/B08/B11/B12 순서의 정확한 여섯 문자열인지 검사한다. 모델 밴드나 파일명으로 누락된 선언을 만들지 않는다.

123의 링크/junction·상대 경로·파일 식별자·성장 제한 reader로 영상 최대 64 MiB와 마스크 최대 16 MiB를 복사하고 같은 고정 참조 SHA를 다시 확인한다. 각 복사 바이트에서 헤더를 읽는다. 추가 Store.get은 없고 정상 총 3회다. 파일은 의도적으로 두 번 읽는다. 첫 번째는 131의 SHA 관측이고 두 번째는 이 단위의 헤더 snapshot이다. 같은 SHA 재검산은 다중 파일의 원자 snapshot이나 모든 TOCTOU 제거를 보장하지 않는다. 131 이후 바이트가 바뀌면 상위에서 차단하지만 중첩131의 이전 성공 이력은 그대로 남는다.

## 실제 헤더의 새 내부 소비 정책

영상은 129의 `_header(raw, source.band_names)`를 재사용한다. TIFF/BigTIFF magic, 강제 GTiff driver, 실제 여섯 band description, projected metre CRS, width/height 1~1024, 유한 north-up affine와 determinant·네 모서리·양의 extent를 요구한다. 기존 image 헤더 정책을 변경하지 않는다.

마스크는 TIFF/BigTIFF magic을 먼저 확인한 뒤 `MemoryFile(raw).open(driver='GTiff')`로 열고 실제 GTiff driver인지 확인한다. **한 밴드·uint8**, width/height 1~1024, projected metre CRS, 유한 north-up affine·determinant·네 모서리·양의 extent를 요구한다. source manifest의 raster 선언만으로 헤더 성공을 추정하지 않는다. VRT/XML/opaque 바이트는 GDAL에 전달하기 전에 거부한다.

두 헤더의 WKT 문자열·width/height·affine 6개·bounds 4개가 정확히 같아야 한다. 수치 오차를 허용하거나 재투영·resample하지 않는다. 의미상 같은 CRS도 WKT 표현이 다르면 차단될 수 있는 엄격한 내부 소비 정책이다. 별도 등록 참조라도 같은 실제 파일을 가리킬 수 있지만 동일 파일이 영상의 6밴드와 마스크의 1밴드 요구를 동시에 만족할 수 없어 이 진단에서는 차단된다. 이것만으로 독립 취득·마스크 정답성까지 확인한 것은 아니다.

PAM=NO, GDAL_DISABLE_READDIR_ON_OPEN=EMPTY_DIR, GDAL_GEOREF_SOURCES=INTERNAL을 제한된 context에 적용한다. 원본 경로나 caller 원격 URI 대신 복사 메모리 바이트만 GDAL에 전달한다. `.read`·`.read_masks`·sample·통계·overview 계산은 호출하지 않는다. 마스크 description/nodata도 값 의미를 증명하지 않으며 0/1·SCL·구름·유효 영역 코드를 해석하지 않는다. 영상 dtype/nodata/scale-offset·픽셀 유한성·물리 보정·실 AOI·과학 정확도·QA 정책·기관 승인·모델 state 호환은 검사하지 않는다.

## exact20 결과와 실패 이력

반환 필드는 schema_version:1, scope:`REGISTERED_QUALITY_MASK_GRID_READ_ONLY`, status, issue, quality_mask_observation, image_header, mask_header, image_mask_headers_verified, image_mask_grid_verified, artifact_bytes_verified와 아래 10개 false다.

- quality_report_verified / quality_mask_verified / pixel_values_verified / mask_semantics_verified
- registry_aoi_verified / source_authority_verified / scientific_accuracy_validated
- execution_authorized / state_dict_verified / workflow_supported

status는 BLOCKED 또는 REGISTERED_QUALITY_MASK_GRID_MATCHED_UNVERIFIED다. quality_mask_observation은 원131 exact18 결과다. image_header는 원129 exact7 `{width,height,count,crs_wkt,transform,bounds,band_names}`, mask_header는 exact7 `{width,height,count,dtype,crs_wkt,transform,bounds}`이며 미확보 시 null이다. 새 detached JSON 값만 반환하고 raw 경로·바이트·예외 원문은 노출하지 않는다.

image_mask_headers_verified·image_mask_grid_verified·artifact_bytes_verified는 **131 전체 성공과 두 헤더·격자 대조가 모두 성공한 때만** true다. image 헤더가 파싱돼 결과에 남아도 mask 실패나 grid 불일치가 있으면 상위 세 flag는 false다. header 실패 시 nested131은 이미 파일을 읽고 성공했을 수 있다. 부분 헤더·중첩 바이트 성공은 읽기 이력이며 QA나 실행 승인이 아니다.

issue는 null 또는 고정 `{code,field}`다. 새 mask 오류는 MASK_FORMAT_UNSUPPORTED, MASK_HEADER_INVALID, IMAGE_MASK_GRID_MISMATCH, MASK_GRID_UNAVAILABLE다. 기존 등록·입력·파일·영상 오류 code를 유지하며 후행 129/123 reader의 오류 field는 실제 image/mask 역할로 매핑한다. 누락된 band 선언은 RASTER_BAND_SIGNATURE_INVALID/band_names다. 131의 기존 품질 보고서 오류 field도 그대로 유지한다.

## 보안·자원·검증 한계

최대 파일 크기는 GDAL TIFF parser의 CPU/RSS/시간 hardcap 증명이 아니다. PAM/sidecar 설정도 GDAL 모든 외부 I/O의 OS sandbox가 아니다. Store.get의 DB 원문 무상한 predecode 후 bounded tree 검사, mapped drive 매체, 다중 record/file 비원자성과 TOCTOU 한계가 남는다. 모델/Torch load·네트워크 조회·환경 패키지 설치·자료 수정·등록을 하지 않는다. PUBLIC은 선언 소비 조건이지 ACL 인증이 아니다.

담당 집중 **10 PASS / 6.446초 / exit 0**는 `evidence/integration/mask-grid-agent-20261018-focused.log`다. 실제 Temp GeoTIFF 6밴드 영상·1밴드 uint8 mask와 세 Registry 참조를 사용했다. get 3회·put 금지·DatasetReader.read/read_masks 금지·exact20/10false, 131 실패의 헤더0, mask shift/shape/CRS·count/dtype/geographic/회전/width 초과, VRT/opaque의 mask MemoryFile0, source band 누락/순서·실 description 누락, 재사용 오류 역할, 131 이후 영상/마스크 변조, 동일 물리 파일 alias 차단, 같은 canonical copy와 invalid I/O0을 확인했다. Affine 라이브러리의 PendingDeprecationWarning은 로그에 보존했다. 시험 fixture 작성의 픽셀 쓰기는 Temp 파일 생성에만 해당하며 reader는 픽셀을 읽지 않았다.

source SHA `d4827f901496607e9bd33e9d4bb9446f19de176592b3a903405fe243e4ee6ec3`, test SHA `3f8031206d0e24a26f5d4408bfe0a0c299ed8ed697ce65750957d53cb0d43641`로 Root와 독립 담당에게 동결 인계했다. Root는 관련 회귀·실파일 대조·보존·공통 문서/인계/Git을, 독립 담당은 별도 fixture 경계를 검증한다. 이해 담당은 완료 코드·시험·한계를 해설/발표/FAQ/INDEX/변경 이력에 반영한다. 내부 미연결 reader이므로 API/UI/frontend/build/browser를 수정하거나 재실행하지 않는다. 운영 모델·자료·Registry·원장·예약·분할은 보존하며 수집·훈련·추론·배포는 실행하지 않았다.

## 독립 최종 근거

독립 **8 PASS / 0 SKIP / 3.574802초 / exit 0**는 `evidence/integration/mask-grid-independent-20261018.py`와 같은 stem `.json`·`.log`에 동결했다. 별도 실제 6밴드 영상·1밴드 uint8 마스크와 세 등록 참조로 get 3회, 영상/마스크 각 두 번 읽기, DB와 전체 파일 불변, read/read_masks 금지를 확인했다. offset/CRS/shape/count/dtype/회전/크기 초과와 opaque/VRT를 차단했다. 명시 band 누락은 131 바이트 성공 뒤 헤더0이며 추정하지 않았고, 품질 보고서 JSON 오류는 원131의 quality_report field와 헤더0을 유지했다.

131 직후 각 자산의 바이트 변경을 두 번째 SHA 관측에서 거부하고 같은 get의 canonical copy·invalid Store I/O0·exact20/10false·nested 관측 범위를 확인했다. 마스크 값 255를 의미 해석하지 않고 헤더만 관측하는 한계도 고정했다. 최종 source SHA와 Git e994e83의 기존 핵심 8개 source SHA(131·129 포함)·tracked source 불변이며 제품 지적은 없다. 운영·훈련·추론·픽셀 읽기 및 API/UI/frontend/build/browser 변경·재실행은 없었다.

## Root 최종 관련·실파일 대조·보존

Root 최종 관련 **42 PASS / 29.023초 / exit 0**는 `evidence/integration/mask-grid-root-related-final-20261018.log`다. 신규 10개,131의 10개,129의 11개, DatasetRegistryVersions 11개를 포함한다. 최초 실행은 잘못 지정한 `test_dataset_registry` 모듈 이름 때문에 실제 31 PASS와 import error 1개로 끝났다. 그 32건 실행/26.398초의 원로그 `mask-grid-root-related-20261018.log`를 보존하고 정확한 `test_dataset_registry_versions`로 수정해 최종 통과했다. 이는 Root 시험 명령 오류이며 제품 소스 수정은 없었다. 최종 묶음과 집중·독립을 중복 합산하지 않는다.

`evidence/integration/mask-grid-runtime-20261018.py`와 같은 stem `.json`·`.log`는 실제 Temp 영상·마스크 GeoTIFF와 세 등록 참조의 **7개 시나리오 통과**를 기록한다. 정상은 get 3회와 두 헤더·격자가 일치하고, mask shift/다른 CRS/width, 두 밴드·uint16·opaque mask는 차단했다. 후행 header/grid 실패에도 원131 파일 관측은 성공한 이력으로 남는다. 실제 Temp fixture를 사용한 metadata 대조이며 운영 자료·픽셀 의미·모델 실행 또는 QA 검증은 아니다.

`evidence/integration/mask-grid-live-integrity-20261018.json`은 보호 141개·기존 source 297개·이전 증거 1153개·catalog 14행과 canonical SHA·예약 136314880바이트 불변을 기록한다. 운영 dataset_versions는 0이며 원본·원장·모델·예약·분할을 보존했다. source/tests 최종 동결 SHA를 유지했고 기존 제품 파일은 수정하지 않았다. 새 내부 reader의 집중·관련·독립·실파일 대조 범위로 마감하며 전체 backend/frontend/build/browser를 이번에 재실행한 것으로 표현하지 않는다. 최종 근거를 반영한 뒤 문서를 동결했다.
