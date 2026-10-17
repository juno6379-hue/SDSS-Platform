# 133 — 명시된 이진 유효성 마스크의 제한된 값 계수

상태: **TESTED_SYNTHETIC**. 신규 `inspect_registered_binary_mask_values(store, image_ref, quality_report_ref, mask_ref)`는 132의 등록 품질 참조·실파일 SHA·영상/마스크 헤더·격자 진단 뒤, 명시된 이진 마스크의 0과 1을 센다. 추가 파일은 `backend/app/ml/registered_binary_mask_values.py`, 집중 시험, 본 문서뿐이다. 기존 123~132·실행 gate·GMAIS schema·API/UI는 변경하지 않는다. 130 배치 연결이나 모델 실행에 자동 전달하지 않는다.

## 명시 선언과 같은 등록 관측

입력은 기존 exact 참조 세 개다. 모두 검증·복사하고 서로 다른 id/version임을 확인한 뒤 Store에 접근한다. 잘못된 입력은 고정 invalid sentinel로 원132 결과를 생성하며 Store I/O0이다. get/root 전용 proxy는 **실제 mask get에서** 반환된 bounded canonical manifest·record id·manifest SHA·고정 id/version/artifact SHA·raster/PUBLIC을 확인한다. 그 detached copy를 그대로132에 반환하고 이후 선언과 경로도 같은 copy에서 얻는다. 추가 Store.get은 없으며 정상 총 3회다.

132 전체가 성공한 다음에만 mask manifest의 `source.mask_semantics`를 확인한다. 이는 source 확장 키를 소비하는 새 내부 계약이며 기관의 공식 마스크 표준이 아니다. 정확히 다음 4개 키만 수용한다.

```json
{"schema_version":1,"kind":"binary_validity","valid_value":1,"invalid_value":0}
```

세 숫자는 bool을 제외한 정확한 int여야 한다. 누락·null·추가 키·다른 kind·뒤바뀐 0/1·bool을 거부한다. 파일 값이나 모델/파일명에서 의미를 추측하거나 legacy 선언을 역채우지 않는다. 선언이 일치해도 그 값이 실제 구름·유효 영역의 정답인지 인증하지 않는다.

## 동일 바이트의 헤더와 한 번의 mask read

선언 검사 후 123의 경로·링크/junction·일반 파일·성장·전후 식별자 정책으로 마스크를 최대 16 MiB 복사하고 고정 참조 SHA를 다시 확인한다. 정상 파일 관측은 영상 두 번, 마스크 세 번이다. 131의 SHA,132의 헤더 snapshot,133의 값 snapshot은 의도적인 순차 관측이며 전역 원자 snapshot이 아니다. 132 뒤 변경은 세 번째 마스크 SHA에서 차단하지만 nested132의 이전 성공 이력은 남는다.

복사된 동일 바이트의 TIFF/BigTIFF magic을 확인하고 **단일** `MemoryFile(raw).open(driver='GTiff')` context에서 헤더와 값을 확인한다. 132의 헤더 helper를 다시 열어 이중 파싱하지 않는다. PAM=NO, EMPTY_DIR, INTERNAL georef 환경을 적용한다. 실제 GTiff·한 밴드 uint8·width/height 1~1024를 확인하고 WKT/shape/affine/bounds를 포함한 헤더가132의 mask_header와 정확히 같아야 한다.

픽셀 읽기 전에 nodata가 None이고 유일한 밴드의 mask flags가 정확히 all_valid인지 검사한다. 내장 nodata·내장 per_dataset mask 등 추가 유효성 해석을 거부한다. 그 뒤 `read(1, masked=False)`를 정확히 한 번 호출한다. 영상 픽셀과 `.read_masks`는 읽지 않는다. 반환 array가 uint8·헤더 shape인지 확인하고 모든 값이0 또는1이어야 한다. 255·SCL 코드·다른 숫자를 유효/무효로 임의 해석하지 않는다.

출력은 `{valid_pixels,invalid_pixels,total_pixels}`의 정수 계수만이며 array나 원본 바이트를 반환하지 않는다. valid+invalid=total이고1을 valid,0을 invalid로 센다. **전부0과 전부1도 허용한다.** 최소 유효 비율·구름 비율·coverage·QA 정책을 추가하지 않는다. 모든 검사 완료 전에 실패하면 counts는 null이며 부분 계수를 성공처럼 반환하지 않는다.

## exact19 결과와 범위

반환 필드는 schema_version:1, scope:`REGISTERED_BINARY_MASK_VALUES_READ_ONLY`, status, issue, grid_observation, counts, mask_declaration_verified, mask_values_verified, artifact_bytes_verified와 아래10개 false다.

- quality_report_verified / quality_mask_verified / mask_semantics_verified
- registry_aoi_verified / source_authority_verified / minimum_validity_policy_verified
- scientific_accuracy_validated / execution_authorized / state_dict_verified / workflow_supported

status는 BLOCKED 또는 REGISTERED_BINARY_MASK_VALUES_MATCHED_UNVERIFIED다. grid_observation은 원132 exact20 결과를 그대로 보존한다. issue는 null 또는 고정 `{code,field}`다. 새 오류는 MASK_DECLARATION_INVALID, MASK_HEADER_CHANGED, MASK_INTRINSIC_VALIDITY_UNSUPPORTED, MASK_VALUES_INVALID, MASK_VALUES_NOT_BINARY, MASK_VALUES_UNAVAILABLE이며 기존 참조·파일·형식·헤더 오류도 유지한다. raw 경로·예외 원문은 반환하지 않는다.

mask_declaration_verified는 명시된 네 필드의 형식·값 일치 이후 true가 되어 후행 바이트/값 실패에도 남을 수 있다. 실제 의미의 진실성은 mask_semantics_verified=false로 분리한다. mask_values_verified와 artifact_bytes_verified는132 전체·선언·추가 SHA·재헤더·nodata/flags·값 검사를 모두 통과해야 true다. 부분 선언이나 nested132 성공은 전체 성공·QA·실행 승인으로 승격하지 않는다.

## 한계와 집중 근거

유효 계수는 caller가 고정한 선언 아래의 실제 바이트 값을 센 관측이다. mask가 영상과 정답으로 대응하는지, 구름/결측/센서 QA가 맞는지, 훈련/추론용 표본에 충분한지는 검사하지 않는다. state_dict·물리 보정·AOI·기관 권위·과학 정확도·최소 coverage·배포를 검증하지 않는다. mask를 수정하거나 수집·훈련·모델 load·추론을 수행하지 않는다.

압축 TIFF 해석과 array 계산의 CPU/RSS/시간을 OS 수준으로 제한하는 sandbox는 아니다. 파일 크기 16 MiB 및 최대1024² uint8 출력 범위는 GDAL/native parser 전체 자원 hardcap을 증명하지 못한다. PAM/sidecar 설정도 완전한 외부 I/O 격리 증명이 아니다. 기존 Store DB predecode, mapped drive 매체, 순차 파일·record 비원자성과 TOCTOU 한계를 상속한다. 네트워크 조회·Torch/model import/load·패키지 설치·운영 쓰기는 추가하지 않는다.

담당 집중 **9 PASS / 7.291초 / exit 0**는 `evidence/integration/binary-mask-agent-20261018-focused.log`다. 실제 Temp 영상과 마스크·세 Registry 참조로 혼합80/176/256계수, all0/all1,255/SCL/기타 값, 누락·추가·bool·뒤바뀐 선언, nodata와 내장 mask의 read 전 거부,132 실패의 pixel0,132 후 변조의 세 번째 SHA 차단, 같은 get copy·DB/전체 파일 불변·invalid I/O0·재헤더 변조 거부를 확인했다. DatasetReader.read 호출은 mask band1/ masked=False 한 번이고 image pixel/read_masks0이다. MemoryFile은132의 두 헤더와133의 단일 값 context만 연다. Affine PendingDeprecationWarning은 로그에 보존했다.

source SHA `5b19a4590b2a395c63d25c6a3e0aadbe36e54c0521b7c551396ea0083dec80d2`, test SHA `f254d55a16fdc593c123decc6251e38b73644cedf3ee529bf0ccdd5041e941ac`로 Root/독립 담당에게 동결했다. Root는 관련 회귀·실파일 대비·보존·공통 인계/Git을, 독립 담당은 별도 fixture 경계를 검증한다. 이해 담당은 완료 코드·검증·한계를 해설/발표/FAQ/INDEX/변경 이력에 반영한다. 내부 미연결 reader이므로 API/UI/frontend/build/browser 수정·재실행은 필요하지 않다. 운영 자료·원장·예약·분할·모델은 보존한다.

## Root 관련·실파일 대비·보존 근거

Root 관련 **40 PASS / 16.334초 / exit 0**는 `evidence/integration/binary-mask-root-related-20261018.log`다. 신규9개,132의10개,131의10개, DatasetRegistry11개를 포함하며 집중·독립과 중복 합산하지 않는다.

`evidence/integration/binary-mask-runtime-20261018.py`와 같은 stem `.json`·`.log`는 실제 Temp 영상·마스크·등록 참조의 **7개 시나리오 통과**를 기록한다. 혼합 마스크는 valid/invalid 각각32768개, all0은0/65536개, all1은65536/0개로 관측했다. 255·선언 누락·nodata·격자 shift는 차단했다. get3회, mask read1회 또는 선행 차단 시0회, image 픽셀0과 DB/전체 파일 불변을 확인했다. 계수가 맞아도 최소 coverage·QA·실제 마스크 정답성을 승인하지 않는다.

`evidence/integration/binary-mask-live-integrity-20261018.json`은 보호141개·기존 source299개·이전 증거1169개·catalog14행과 SHA·예약136314880바이트 불변을 기록한다. 운영 inventory의 dataset_versions는0이며 운영 자료 쓰기·수집·훈련·추론·모델 load는 수행하지 않았다. 기존 제품 파일과 source/tests 동결 SHA를 유지했다. 새 내부 reader의 제한된 시험 범위이며 이번 전체 backend/frontend/build/browser 재실행으로 표현하지 않는다.

## 독립 최종 근거와 문서 동결

독립 **8 PASS / 0 SKIP / 6.724950초 / exit 0**는 `evidence/integration/binary-mask-independent-20261018.py`와 같은 stem `.json`·`.log`에 동결했다. 별도 실제 checkerboard의128/128 계수, all0/all1과 최소 비율 정책 부재,255 실패 시 counts 미출력, missing/SCL/bool/추가 키 선언과 nodata·실제 내장 mask 거부를 검증했다. 정상 get3회·영상 두 번/마스크 세 번 파일 관측·mask `read(1, masked=False)` 한 번, image 픽셀/read_masks0과 DB/전체 파일 불변을 확인했다.

132 실패·131 quality_report 오류 field 보존·invalid Store I/O0,132 이후 변경의 세 번째 SHA 차단·동일 get copy·dtype/shape guard·exact19/10false와 nested 관측 범위도 확인했다. 최종 source와 test SHA가 일치하며 Git45d4000의 기존 핵심8개 SHA·tracked source는 불변이다. 독립 로그 끝의 test SHA 추가는 metadata 확인 기록이며 재시험이나 제품 변경이 아니다. 추가 제품 지적은 없다. 운영 모델 load·훈련·추론·API/UI/frontend/build/browser 실행 없이 의미의 진실성·QA·최소 정책·비원자성 한계를 유지한다. 최종 근거 반영 후 본 문서를 동결했다.
