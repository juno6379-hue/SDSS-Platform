# 130 — Registry bbox와 실제 래스터 경계 표본의 읽기 전용 대조

> 후속131: 품질 보고서·명시적 마스크의3개 고정 Registry 참조와 바이트를 연결하는 독립 reader를 `131_registered_quality_mask_files.md`에서 구현·검증했다.130 batch 자동 연결이나 실제 마스크·품질 승인은 아니며132 이후 별도 진단이 필요하다.

상태: **TESTED_SYNTHETIC**. 새 `backend/app/ml/registry_spatial_normalization.py`는 고정 모델·장면 참조의 기존129 읽기 결과에 Registry 공간 선언 대조를 추가한다. 운영 실행·API·UI에는 연결하지 않았다. 기존124~129 및 실행 gate를 수정하지 않는다. Registry bbox가 실제 헤더에서 변환한 경계 표본의 근사 envelope를 포함하는지만 관측하며, 실제 AOI·취득 지역·주 전체 자료 확보를 인증하지 않는다.

## 입력과 같은 관측의 결합

`inspect_registry_spatial_normalization(store, model_ref, training_report_sha256, requested_years)`의 입력은127과 같다. 2~6행,1900~2200년의 정확한 정수·엄격 오름차순·고정3참조 및 중복 규칙을 원127 `_request`로 먼저 검사하고 detached snapshot을 사용한다. 잘못된 입력은 고정 invalid sentinel로 하위129 결과를 생성하며 Store I/O0이다. 유효 global 모델은 기존대로 모델 관측만 수행하고 장면은 읽지 않는다.

get/root 전용 proxy가 실제 image get에서 반환된 record의 bounded manifest·canonical SHA·id/version·요청 artifact SHA를 확인한다. 그 canonical copy의 spatial을 캡처하고 **같은 copy**를129에 반환한다. 공간 선언만 별도로 먼저 조회한 뒤 바뀐 manifest를129에서 다시 허용하는 구조가 아니다. 125의 행별 image/evidence/metadata3get 순서 중 실제 image 위치만 캡처하므로 다른 role이 미래 image 키와 같아도 공간 관측을 잘못 생성하지 않는다.

추가 Store get·이미지 snapshot·header open0이며 정상 모델 load1회와1+3N get을 유지한다. 원129 전체 관측을 그대로 결과에 보존한다. bounded tree 검사는 Store.get가 DB body를 decode한 **이후**이며 DB 원문 decode/RSS hardcap을 보장하지 않는다.

## 새 내부 공간 소비 정책

Registry `spatial.crs`는 정확한 `EPSG:4326` 또는 `OGC:CRS84`만 수용하고 둘 다 bbox를 `[west,south,east,north]`, 즉 경도·위도로 해석한다. upstream 보편 표준을 변경한 것이 아니라 이 내부 reader의 명시적 제한이다. 다른 CRS를 자동 추정·수정하지 않는다.

원129의 실제 projected metre CRS WKT와 실제 header bounds를 `transform_bounds(..., 'OGC:CRS84', densify_pts=21)`로 변환한다. 21개 densification을 사용하는 **경계 표본에서 계산한 근사 envelope**이며, 미표본 극값을 놓치지 않는 보수적 상한·정확한 footprint·완전한 포함 증명은 아니다. 좌표별 포함 비교 허용오차는 고정 `1e-7`도다. 면적·픽셀·통계에는 이 오차를 사용하지 않는다.

Registry bbox와 변환 envelope 모두 유한 좌표·양의 너비/높이·경도[-180,180]·위도[-90,90]를 요구한다. 날짜변경선 ±180도 접촉/교차, 경도 폭180도 초과, 위도 절댓값85도 이상은 보수적 내부 정책으로 거부한다. 따라서 전세계 bbox도 차단된다. 허용 범위 안에서 실제 envelope보다 큰 bbox는 통과할 수 있으나 province 전체 coverage나 선언 진실성을 의미하지 않는다.

pyproj 네트워크 설정은 읽기만 하고 활성화 상태면 차단한다. Rasterio context는 `PROJ_NETWORK='OFF'`를 사용한다. helper가 패키지를 설치하거나 pyproj 네트워크 설정을 변경하지 않는다. 라이브러리 부재·변환 오류는 고정 오류로 차단한다. 이 설정은 OS/native 전체 네트워크·CPU/RSS 격리 증명이 아니다. PROJ 변환/라이브러리 리소스와 기존 GDAL/Torch allowlist·다중파일 비원자성·mapped drive 매체 한계가 남는다.

## 순서·부분 관측과 exact17 출력

129 전체가 성공한 뒤에만 공간 수학 대조를 시작한다. 따라서 **후행 공간 대조 실패** 뒤 행의 NOT_CHECKED는 공간 검사 미수행일 뿐이며129의 모든 파일/헤더 관측은 이미 완료됐다. 반면 proxy의 등록 캡처 실패는129 도중 조기 차단될 수 있고, 원129 자체 실패도 파일 미읽기 행을 남길 수 있다. SPATIAL_BLOCKED 전체가 모든 I/O 완료라는 뜻은 아니다. 파일 읽기 이력은 항상 nested129를 함께 확인한다.

반환 exact17 필드는 다음과 같다.

- `schema_version:1`, `scope:'PINNED_YEARS_REGISTRY_ENVELOPE_READ_ONLY'`, `status`, `issue`
- `raster_batch_observation`: 원129 exact19 결과
- `spatial_observations`: 요청 행 순서의 `{year,status,registry_bbox,raster_wgs84_envelope,issue}`
- `registry_bbox_contains_raster_envelope_verified`, `artifact_bytes_verified`: 전체 공간 대조와 원129가 모두 성공할 때만 true
- 항상 false: `registry_aoi_verified`, `physical_coverage_verified`, `quality_report_verified`, `quality_mask_verified`, `pixel_values_verified`, `source_authority_verified`, `scientific_accuracy_validated`, `execution_authorized`, `workflow_supported`

최종 성공 status는 `REGISTRY_ENVELOPE_MATCHED_UNVERIFIED`, 새 실패는 `SPATIAL_BLOCKED`다. 이외 INVALID_INPUT/MODEL_BLOCKED/OUT_OF_SCOPE/SCENE_BLOCKED/TEMPORAL_BLOCKED/RASTER_BLOCKED는 원129 결과를 보존한다. 행 status는 NOT_CHECKED/MATCHED_UNVERIFIED/BLOCKED이며 부분 bbox/envelope는 진단 이력이다. 최상위 issue는 null 또는 고정 `{code,field,year}`, 행 issue는 null 또는 `{code,field}`다. raw path·예외 원문은 반환하지 않는다.

새 code는 REGISTRY_CAPTURE_INVALID, REGISTRY_REFERENCE_CONFLICT, REGISTRY_SPATIAL_CRS_UNSUPPORTED, SPATIAL_BOUNDS_INVALID, SPATIAL_DATELINE_UNSUPPORTED, SPATIAL_POLAR_UNSUPPORTED, SPATIAL_TRANSFORM_UNAVAILABLE, REGISTRY_BBOX_DOES_NOT_CONTAIN_ENVELOPE다. 첫 실패 뒤 공간 행은 NOT_CHECKED로 남긴다. nested129 및 그 이하의 기존 false flag를 true로 바꾸지 않는다.

dtype/nodata/scale-offset·픽셀 유한성·실제 valid coverage·mask·QA 본문·물리 보정·기관 권위·state_dict 호환·과학 정확도·실행 승인은 검사하지 않는다. bbox를 고치거나 픽셀을 재투영하지 않는다. 실제 AOI polygon 및 품질/mask 고정 참조 연결은 별도 후속이다.

## 집중 시험과 동결

담당 집중 **10 PASS / 17.669초 / exit0**: `evidence/integration/registry-spatial-agent-20261018-focused.log`. 실제 Temp GeoTIFF2/6장면·등록 참조·미훈련 CPU checkpoint를 사용했다. 정상1+3N get/추가 header open0, 정확 bbox·큰 허용 bbox·CRS84, 허용오차 안/밖, 중간 failfast, 날짜변경선·극지·CRS·비유한/퇴화 변환, 설정 읽기만·변환 고정 오류, 하위129 실패 우선순서, 같은 canonical copy와 원 record 변경 방어, DB/입력 불변·쓰기 금지·9false를 검증했다. Affine 라이브러리의 PendingDeprecationWarning은 로그에 보존했다.

source SHA `3044f176093c462eb2a407cc4a3b7310ae115b8700c0f71735f05c245ac5c108`, test SHA `9e2b162a6a1e7ec2b9ca08deb1949b5b495cd1f750bf25f5fb4172d95e9cdeb7`로 Root/독립 담당에게 동결했다. Root는 관련 회귀·실제 Temp GeoTIFF 대비·보존·공통 문서/인계/Git을, 독립 담당은 별도 fixture 경계를 검증한다. 이해 담당은 검증된 구현·한계를 해설/발표/FAQ/INDEX/변경 이력에 반영한다.

미연결 내부 reader이므로 API/UI/frontend/build/browser 수정·재실행은 필요하지 않다. 이전 전체 backend1184/frontend261은 이번 결과가 아니며 집중·관련·독립 수치를 중복 합산하지 않는다. 운영 checkpoint load·자료/Registry 쓰기·등록·수집·훈련·추론·배포0이다.

## 독립 최종 근거

독립 **8 PASS / 0 SKIP / 19.816819초 / exit0**는 `evidence/integration/registry-spatial-independent-20261018.py`와 같은 stem `.json`·`.log`에 동결했다. 별도 실제 Temp GeoTIFF·18 Registry·CPU checkpoint로2/6행의7/19 get·기존2N image open인4/12회·header2/6회·DB와 전체 파일 불변·픽셀 읽기0을 검증했다. 두 Registry CRS의 lon/lat 해석, 실제105E/−9도 부근 좌표와 별도101개 edge 표본 변환의1e-9도 이내 일치, 정확1e-7도 허용/2e-7도 거부를 확인했다. 별도 표본과의 일치는 해당 fixture 근거이며 모든 변환의 수학적 상한 보장은 아니다.

후행 공간 실패에도 nested129 성공·모든 파일 읽기 완료와 잔여 spatial NOT_CHECKED를 확인했다. 동일 get copy 캡처·재조회0, header 실패 시 공간 수학0, CRS/날짜변경선/극지/NaN/wrap/network 활성화 차단·환경 불변, 넓은 bbox가 coverage 승인으로 바뀌지 않음, invalid/global/model 실패의 image0도 검증했다. frozen source SHA 및 Git759eac0의 기존 핵심8 source SHA·tracked source 불변이며 제품 지적0이다. UI/API 미연결·표본 근사/권위·자원·비원자성 한계를 유지한다.

## Root 관련·실파일 대비·보존 마감

Root 관련 **41 PASS / 61.722초 / exit0**는 `evidence/integration/registry-spatial-root-related-20261018.log`다. 신규10·129의11·128의11·127의9를 포함하며 다른 집중/독립 결과와 중복 합산하지 않는다.

`evidence/integration/registry-spatial-runtime-20261018.py`와 같은 stem `.json`·`.log`는 **7개 fresh Temp fixture 시나리오 통과/exit0**를 기록한다. 실제 GeoTIFF3장면·Registry 참조·미훈련 CPU checkpoint에서 허용된 넓은 bbox·변환과 정확히 같은 bbox·CRS84는 통과하고, 범위 밖/좁은 bbox·미지원 CRS·world bbox는 차단했다. 각 사례는 원129 전체 성공의 모델 load1/get10/header3회를 유지한 뒤 공간 대조했다. 실패 이후 spatial NOT_CHECKED가 파일 미읽기를 의미하지 않는 경계를 확인했다. 훈련·추론·운영 등록은 수행하지 않았다.

`evidence/integration/registry-spatial-live-integrity-20261018.json`은 보호141개·기존 source293개·이전 증거1124개·catalog14행 SHA와 예약136314880바이트 불변을 기록한다. source/tests 동결 SHA를 유지했고 기존 제품 파일은 수정하지 않았다. 집중·관련·독립 및 실제 Temp 대비 범위로 검증했으며 전체 backend/frontend/build/browser를 이번 단위에서 재실행한 것으로 표현하지 않는다. 다음 QA report·명시 mask 고정 참조 계약과 실제 AOI/취득·과학·실행 승인 과제는 별도다. 최종 근거 반영 후 본 문서를 동결했다.
