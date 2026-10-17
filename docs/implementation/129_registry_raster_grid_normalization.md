# 129 — 실제 GTiff header와 장면 간 엄격 grid 관측

## 쉬운 설명과 범위

신규 `backend/app/ml/registry_raster_grid_normalization.py`의 `inspect_registry_raster_grid_normalization(store, model_ref, training_report_sha256, requested_years)`는128의 같은 Registry get 경계에 header 읽기를 결합한다. 영상 고정 SHA와 맞는 bounded 복사 바이트를 Rasterio MemoryFile의 GTiff driver로 열어 metadata만 확인하고 요청 장면끼리 grid를 비교한다.

픽셀값·mask를 읽거나 모델을 실행하지 않는다. header/grid가 같다는 것은 실제 AOI·Registry bbox·독립 정답·보정·취득 진위·운영 승인을 뜻하지 않는다. Registry bbox/AOI 관계와 actual header geometry 대조는130 후속이다. 기존124~128·Store·Registry/API/UI·115 실행 gate는 수정하지 않았다.

## 신규 내부 header 소비 정책

이 정책은 기존 모든 래스터 처리의 보편 규칙이나 upstream 기관 표준이 아니라 **새 내부 reader의 엄격한 지원 범위**다.

- image manifest는 raster·PUBLIC 선언이어야 한다. header가125보다 먼저 읽히므로 파일 접근 전에 두 정책을 확인한다. 모든 quality_status는 진단 가능하지만 QA 본문·ACL 승인은 검사하지 않는다.
- image.source.band_names는 명시적으로 B02/B03/B04/B08/B11/B12 순서여야 하고, 실제 GTiff count6·각 band description도 정확히 같은 원문/순서여야 한다. 누락 이름을 모델·파일 순서에서 추정하지 않는다. source.scene_id는 기존125가 후속 검사한다.
- width/height는1~1024, CRS는 projected·metre 단위 factor1이어야 한다. geographic/feet/CRS 미확보는 이번 범위에서 차단한다. 실제 투영/좌표의 기관 정확성을 인증하지 않는다.
- affine6계수는 finite, a>0/e<0/b=d=0인 north-up이고 determinant가 유한·0이 아니어야 한다. 네 corner 계산도 finite, bounds 양의 폭/높이여야 한다. finite 계수라도 곱셈 overflow나 큰 origin의 수치 정밀도 소실로 bounds가 퇴화하면 거부한다.
- 첫 성공 장면의 **canonical WKT 문자열·width/height·6개 affine float값**과 이후 장면이 완전히 같아야 한다. 허용오차·reprojection을 적용하지 않는다. 같은 뜻의 CRS라도 WKT 문자열이 다르면 차단될 수 있어 semantic CRS equality보다 엄격하다. WKT32768자 초과는 조용히 자르지 않고 차단한다.

1픽셀 자료가 header 관측에 통과해도 기존115 실행기 min-size/patch 호환을 통과했다는 뜻이 아니다. 모델 state/추론 호환성 검사는 여전히 false다.

dtype/nodata/scale-offset metadata·픽셀 수치의 finite 여부·표준화된 물리값·valid-data coverage는 검사하지 않는다. 현재 dtype 제한은 없어 complex나 다른 dtype도 이 header 범위에서 통과할 수 있다. GTiff header true를 TinyUNet 실행 가능성으로 표현하지 않는다. metre 단위·같은 WKT/affine만으로 AOI 성립·동일 취득 품질을 증명하지도 않는다.

## 동일 Registry/파일 snapshot과 GDAL 읽기

127 요청 snapshot 선검사 후 get/root만 있는 header Store proxy를128에 전달한다. invalid는 고정 invalid sentinel로 원128 응답을 생성하므로 caller 변경으로 I/O가 생기지 않는다. 모델 실패·유효 global은 header/scene I/O0이며 모델 읽기는 기존대로1회다.

125의 row별3get 순서 중 실제 image get에서 bounded manifest/canonical digest·등록 id/version/요청 SHA를 확인하고 **raster/PUBLIC 선언과 명시 band names를 파일 전에** 검사한다.123의 동일 root/relative/nolink reader로 최대64MiB 복사하고 그 바이트 SHA를 image_ref와 비교한다. TIFF/BigTIFF magic이 아니면 GDAL에 전달하기 전에 거부한다. VRT/XML/임의 바이트의 외부 참조를 열지 않는다.

`MemoryFile(raw).open(driver='GTiff')`로 강제하고 실제 driver도 GTiff인지 확인한다. PAM=NO, GDAL_DISABLE_READDIR_ON_OPEN=EMPTY_DIR, GDAL_GEOREF_SOURCES=INTERNAL 환경을 제한된 context에 적용한다. 원본 이미지 경로나 caller의 sibling/network URI를 GDAL에 전달하지 않고 복사 메모리 dataset만 사용한다. `.read`, `.read_masks`, sample/statistics/overview 계산을 호출하지 않는다. 이 설정이 GDAL의 모든 외부 I/O·네트워크·CPU/RSS를 OS 수준에서 격리하는 sandbox인 것은 아니다. source_url HTTP 조회·네트워크 라이브러리 호출을 추가하지 않는다.

같은 canonical manifest copy를128의 temporal proxy에 반환하고 이후125도 그 관측을 사용한다. Registry 추가 get0이며 정상1model+3N get·model load1회를 유지한다. **header 검사가128 temporal보다 먼저** 발생한다. 따라서 header/등록 경계 실패가 있으면 기간 검사를 수행하지 않을 수 있다. 이후125는 같은 image SHA를 다시 읽어 바이트를 재검산하지만 두 순차 snapshot이며 전역 원자성·모든 TOCTOU 제거를 보장하지 않는다.

GTiff/GDAL parser가 metadata를 해석하는 자체 CPU/RSS 비용은64MiB 파일 상한만으로 hardcap을 증명하지 못한다. 원래 Store.get의 DB 원문 predecode·Torch allowlist/자원·mapped drive 매체·다중파일 비원자성 한계도 그대로다. 신뢰할 수 있는 내부 작업 범위이며 공개/실행 권한 경계는 별도다.

## exact19 결과

필드는 schema_version:1, scope:`PINNED_YEARS_RASTER_GRID_READ_ONLY`, status, issue, temporal_batch_observation, header_observations, raster_header_verified, cross_scene_grid_verified, artifact_bytes_verified, registry_temporal_year_verified와 아래9개 false다.

- registry_aoi_verified / quality_report_verified / quality_mask_verified
- pixel_values_verified / state_dict_verified / source_authority_verified
- scientific_accuracy_validated / execution_authorized / workflow_supported

status는 INVALID_INPUT / MODEL_BLOCKED / OUT_OF_SCOPE / SCENE_BLOCKED / TEMPORAL_BLOCKED / RASTER_BLOCKED / RASTER_GRID_MATCHED_UNVERIFIED다. temporal_batch_observation은 원128 exact13을 보존하고 nested127의 temporal false·모든 미검증 flag도 수정하지 않는다. physical acquisition false도 nested128에서 유지된다. 상위 issue는 null 또는 고정 `{code,field,year}`다.

header_observations는 실제 image get의 검사 순서대로 `{year,status,header,issue}`다. status는 MATCHED_UNVERIFIED/BLOCKED, header는 null 또는 exact7 `{width,height,count,crs_wkt,transform,bounds,band_names}`다. transform6·bounds4는 새 detached 목록이며 raw path를 반환하지 않는다. grid 불일치 때 유효한 해당 header가 남을 수 있으나 전체 성공이 아니다. row issue는 null 또는 `{code,field}`다.

header 고정 code는 REGISTRY_RECORD_INVALID / REGISTRY_REFERENCE_CONFLICT / REGISTRY_TYPE_MISMATCH / ACCESS_DECLARATION_BLOCKED / RASTER_FORMAT_UNSUPPORTED / RASTER_HEADER_INVALID / RASTER_BAND_SIGNATURE_INVALID / RASTER_GRID_MISMATCH 및123 파일 오류다. RASTER_BLOCKED는 header 이전 등록/접근/파일 결합 실패도 포함한다. 원래125가 예외를 일반화해도 proxy가 기록한 고정 reason을 상위에 보존하고 caller path·예외 원문은 노출하지 않는다.

raster_header_verified와 cross_scene_grid_verified는 **모든 header와 원128 전체가 성공한 때만** true다. header2개가 먼저 통과해도 뒤의 temporal/metadata 파일 실패가 있으면 false다. 전체 artifact는 header/grid와 원128 artifact 모두 성공해야 true다. registry_temporal_year_verified는 원128의 해당 관측 범위를 그대로 따른다. 부분 header는 읽기 이력이며 QA·AOI·픽셀·과학·실행 승인으로 승격하지 않는다. 후속 행 NOT_CHECKED는 원127 rows에서 확인한다.

## 시험과 동결 인계

담당 집중 최종 **11 PASS / 19.150초 / exit0**: `evidence/integration/raster-grid-agent-20261018-focused-final.log`. 최초10건 중 fixture 복구 ERROR1은 `raster-grid-agent-20261018-focused.log`에 보존했다. 제품이 정상 거부한 malformed VRT를 시험 writer가 덮어쓰면서 GDAL이 기존 VRT를 해석해 실패한 것이며, 임시 fixture 파일만 먼저 unlink하고 다시 작성하도록 시험을 고쳤다. 제품 VRT 경계는 MemoryFile 호출 전에 정상 차단했고 기존 제품 소스 수정은0이다.

실제 Temp GeoTIFF2/6장면·CPU checkpoint/등록 참조로1+3N get·동일 header·메모리 driver 강제/PAM 제한·DatasetReader read/read_masks 금지·PUBLIC/type 조기 검사·밴드 누락/순서/count·geographic/feet CRS·north-up/shape·shift grid·실수 overflow/퇴화 bounds·VRT/opaque·파일 hash 변조·후속 기간/metadata 실패·무쓰기/원본 불변/false flags를 시험했다. fixture의 Registry bbox와 실제 UTM grid/AOI 관계는 검사하지 않아 registry_aoi_verified=false다. 훈련·forward·추론·load_state_dict0이다.

source SHA `17371e6a2a49a9845bf2a5d6b2cb0a777808400ac814b2d14e6347d7eb992501`, test SHA `ec89b2e7fefd750dbd24562d213fef698d035e0149bab2c19a67bbe17594635f`로 Root/독립 담당에게 동결 인계했다. Root는 실제 GeoTIFF 대조·관련 회귀·보존·공통 문서/Git을, 독립 담당은 별도 실제2/6장면·driver/경쟁/링크/상태 경계를 검증한다. 이해 담당은 완료 코드·시험·한계를 읽고 설명·이론·발표·FAQ·INDEX·변경 이력을 갱신한다.

미연결 내부 reader이므로 UI/API/frontend/build/browser를 수정·재실행하지 않고 기존115 실행 gate를 유지한다. 이전120 backend1184/front261은 이번 결과가 아니다. 운영 모델 load·자료/Registry 쓰기·등록·수집·훈련·추론·배포0이며 실제 AOI/header 진위·운영 준비 완료는 별도 후속이다.

## 최종 관련·실파일 대비·보존 근거

Root 관련 **44 PASS / 40.033초 / exit0**는 `evidence/integration/raster-grid-root-related-20261018.log`다. 신규11·128의11·127의9·125의13을 포함하며 집중·독립과 중복 합산하지 않는다.

Root의 `evidence/integration/raster-grid-runtime-20261018.py`와 같은 stem `.json`·`.log`는 시나리오마다 새로 만든 Temp fixture7개에서 실제 GeoTIFF3개·등록9참조·CPU checkpoint를 사용한 **7시나리오 통과/exit0** 근거다. 정상은 torch.load1회/get10회로 통과하고 shift·band description 누락/순서·geographic CRS·크기 초과·비래스터 바이트를 거부했다. 임시 생성 자료의 metadata 관측이며 훈련/추론·운영 등록·자료 변경은 아니다.

`evidence/integration/raster-grid-live-integrity-20261018.json`은 보호141개·기존source291개·이전증거1109개·catalog14행 SHA와 예약136314880바이트 불변을 기록한다. source/test 동결 SHA를 유지했고 dtype/픽셀/QA/mask/실AOI·취득 품질·실행 권한을 확인한 것으로 확대하지 않는다.

독립 최종 **9 PASS / 0 SKIP / 17.265843초 / exit0**는 `evidence/integration/raster-grid-independent-20261018.py`와 같은 stem `.json`·`.log`에 동결했다. 별도 fresh Temp6 GeoTIFF·18 Registry·CPU checkpoint로2/6행의7/19 get·DB/파일 불변을 확인했다. DatasetReader.read/read_masks 금지 patch 및 AST의 pixel method0, CRS/shift/shape failfast·누락/반대 description·geographic/feet/회전/width 초과·opaque/VRT의 MemoryFile 호출0·명시 names 미확보/RESTRICTED의 image snapshot0을 검증했다. header 관측 뒤 파일 변경은125 SHA 재검사로 차단했고 실제 Windows junction을 거부한 뒤 링크만 제거하고 target을 보존했다. invalid/global/model 실패의 header0·exact19/9false와 nested 범위도 유지했다. 동결 SHA 및 Git97e712d의 기존 핵심8 source SHA·tracked source 불변이며 제품 지적0이다. 운영·훈련·추론·픽셀 읽기0, API/UI/frontend/build/browser 변경·재실행0이며 엄격 grid/미검증 AOI/자원·비원자성 한계를 유지한다. 최종 독립 근거 반영 후 문서를 동결했다.
