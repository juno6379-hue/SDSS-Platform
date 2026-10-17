# 134 — 연차 공간·정규화와 명시 품질 마스크 진단의 결합

상태: **TESTED_SYNTHETIC**. 신규 `inspect_annual_quality_mask_diagnostics(store, model_ref, training_report_sha256, requested_years)`는 기존130의 전체 연차 관측 뒤 각 장면의133 이진 마스크 관측을 수행하고, 두 단계가 읽은 **영상 Registry manifest SHA**를 비교한다. 신규 source·시험·본 문서만 추가하며 기존123~133·실행 gate·API/UI를 수정하지 않는다. 실제 모델 실행이나 QA 승인을 허용하는 Workflow가 아니라 내부 읽기 전용 진단이다.

## 입력 선검사와 순서

requested_years는 정확한 list의2~6행이고 각 행은 정확한6개 키 `year,image_ref,evidence_ref,metadata_ref,quality_report_ref,mask_ref`를 가진다. 모든 참조를 exact id/version/SHA 계약으로 검사하고 복사한다. 앞의4개 키 projection을127 `_request`에 전달해 모델 참조·report SHA·1900~2200년 exact int(bool 제외)·엄격 오름차순·중복 image 금지·기존 normalization 역할별 구분을 재사용한다. 추가 두 ref도 모든 행에서 Store I/O 전에 검증하며 각 행의 image/quality_report/mask id/version 쌍은 서로 달라야 한다. 다섯 ref 전체를 무조건 서로 다르게 만드는 추가 규칙은 없다. 기존 유형/역할 검사에 따라 후행에서 차단될 수 있다.

잘못된 입력은 INVALID_INPUT이고 Store get·모델 관측·mask 호출이 모두0이다. 유효 요청은 exact4 projection으로130을 정확히 한 번 호출한다. 실제 모델 checkpoint/report는130 아래에서 한 번만 읽고 동일 actual manifest로 모든 정규화 장면을 진단한다.130이 REGISTRY_ENVELOPE_MATCHED_UNVERIFIED에 도달해야 mask 단계를 시작한다. global 모델 OUT_OF_SCOPE나 모델/장면/기간/header/공간 실패는 ANNUAL_SPATIAL_BLOCKED로 감싸고 원130의 상세 결과·issue를 보존한다.

130 전체 성공 뒤 요청 연도 순서대로133을 각 한 번 호출한다. 정상 get은 `1+6N`회, 모델 load는1회다. 추가 digest 조회나 Registry get을 하지 않는다. mask 첫 실패 또는 단계 간 manifest 불일치에서 멈추고 뒤 mask 행은 NOT_CHECKED로 남긴다.130이 먼저 모든 영상을 읽었으므로 여기서 **mask NOT_CHECKED가 영상 파일 미읽음을 뜻하지 않는다.** 실패 행도 mask_observation_calls와 checked_rows에 포함된다.

## 자산 SHA뿐 아니라 같은 영상 manifest의 결합

130의 `raster_batch_observation.temporal_batch_observation.temporal_observations`에서 실제 영상 get과 결합된 manifest_sha256을 얻는다. 각 성공133의 `grid_observation.quality_mask_observation.registry_bindings`에서 정확한 image 역할 하나의 manifest_sha256과 비교한다. 행의 연도 순서와 관측 수, 정확히 세 registry binding과 image 역할 하나를 요구한다. 두 digest 모두 정확한 문자열의 소문자 hex 64자리인지 먼저 확인하므로 양쪽 null/bool/잘못된 문자열이 같아도 통과하지 않는다. 추가/누락/중복 역할이나 digest 불일치는 차단한다.

영상 파일 id/version/SHA가 같아도 source·기간·bbox·품질 보고서 경로 등의 Registry manifest가 두 단계 사이 바뀌면 REGISTRY_IMAGE_MANIFEST_CHANGED/image_manifest로 차단한다. 비교를 위해 현재 Registry를 다시 조회하거나 digest를 추정하지 않는다. digest는 두 관측의 고정 선언 결합이지 기관 권위나 모든 시점의 불변성을 증명하지 않는다.

join은133 전체 뒤에 수행하므로, join에 실패해도 해당 nested133에는 이미 읽은 mask counts와 값 성공이 남을 수 있다. 이것은 부분 관측 이력이며 전체 성공이 아니다.130과 여러133은 순차 실행이며 DB/모델/모든 파일의 원자 snapshot·트랜잭션을 만들지 않는다.

## exact22 결과

필드는 schema_version:1, scope:`ANNUAL_REGISTERED_QUALITY_MASK_READ_ONLY`, status, issue, annual_spatial_observation, mask_observations, spatial_observation_calls, mask_observation_calls, checked_rows, artifact_bytes_verified, mask_values_verified, registry_manifest_join_verified와 다음10개 false다.

- quality_report_verified / quality_mask_verified / mask_semantics_verified
- minimum_validity_policy_verified / registry_aoi_verified / source_authority_verified
- scientific_accuracy_validated / execution_authorized / state_dict_verified / workflow_supported

status는 INVALID_INPUT / ANNUAL_SPATIAL_BLOCKED / MASK_BLOCKED / ANNUAL_QUALITY_MASK_MATCHED_UNVERIFIED다. issue는 null 또는 고정 `{code,field,year}`다. 단계 예외는 고정 ANNUAL_SPATIAL_BLOCKED 또는 MASK_OBSERVATION_BLOCKED로 변환하고 raw 경로·예외 문자열을 반환하지 않는다. 원 하위 진단이 제공한 안전 issue는 연도와 함께 유지한다.

annual_spatial_observation은 원130 결과를 그대로 보존한다. mask_observations는 요청 순서의 exact5 `{year,status,mask_observation,registry_manifest_join_verified,issue}`이며 status는 NOT_CHECKED/MATCHED_UNVERIFIED/BLOCKED다. mask_observation은 null 또는 원133 결과다. 행 issue는 null 또는 고정 `{code,field}`다. 성공한 앞 행과 실패한 행의 부분 결과를 보존하며 상위 세 verified flag는 **130과 모든133 및 모든 manifest join이 성공한 때만** true다.

실제 AOI/취득 권위·mask 의미의 정답성·구름/품질 정책·최소 유효 비율·모델 state 호환·과학 정확도·기관/운영 실행 승인은 검사하지 않는다. all0 mask도133의 값 진단은 통과할 수 있다. bounds는130의 유한 표본 근사이며 footprint 보수 상한이 아니다. 기존 Store 원문 predecode, Torch ambient allowlist, GDAL/native parser CPU/RSS/시간, mapped drive 매체, 링크/TOCTOU 및 다중 파일 비원자성 한계를 상속한다. 운영 자료 쓰기·수집·훈련·추론·배포를 수행하지 않는다.

## 검증과 인계

최종 집중 **9 PASS / 33.800초 / exit 0**는 `evidence/integration/annual-mask-agent-20261018-focused-final.log`다. 실제 Temp GeoTIFF·정규화 문서·품질 보고서·명시 binary mask·Registry·미훈련 CPU checkpoint로2/6행,1+6N get, 모델 한 번, 전체 선검사 I/O0,130 실패의 mask0, 중간 mask 실패의 부분 관측, 같은 파일 pin을 유지한 Registry metadata 변경 차단, image binding 누락/중복, caller snapshot·무쓰기·global/예외 범위를 검증했다. Root 초안 검토의 양쪽 null digest 동등 가능성에 따라 SHA 형식과 bounded selector 경계를 강화하고 malformed digest·temporal year 회귀를 추가했다. 보완 전 8 PASS / 28.923초 원로그 `annual-mask-agent-20261018-focused.log`는 보존하며 최종 결과와 합산하지 않는다. Affine 라이브러리의 PendingDeprecationWarning은 로그에 남겼다.

source SHA `c7dcf589ead5abd94365cf816314f5a2936e029ce9c23bdac12dd2d63afe6abe`, test SHA `0bba28e14244f6dc2d753bab6bc14ee3b1e7e0f6639016b40f1ef71ac5d11f38`로 Root/독립 담당에게 동결했다. 기존 소스는 수정하지 않았다.

Root는 관련 회귀·실제 Temp 대비·보존·공통 인계/Git을, 독립 담당은 별도 fixture 경계를 검증한다. 이해 담당은 완료 코드·시험·한계를 해설/발표/FAQ/INDEX/변경 이력에 반영한다. 이번 단위로130과133 사이의 내부 자동 연결은 완료했다.115 실행기 및 API/UI에는 연결하지 않았으므로 frontend/build/browser 변경·재실행은 필요하지 않다. 기존 전체 backend/frontend 시험은 이전 이력이며 이번 제한된 검증과 합산하지 않는다.

## Root 실파일 대비와 보존

Root 관련 최종 **28 PASS / 69.773초 / exit 0**는 `evidence/integration/annual-mask-root-related-20261018.log`다. 신규134의9개,130의10개,133의9개를 포함하며 집중·독립과 중복 합산하지 않는다.

`evidence/integration/annual-mask-runtime-20261018.py`와 같은 stem `.json`·`.log`는 실제 Temp fixture의 **7개 시나리오 통과**를 기록한다.3개 연도의 정상/all0은 모델 load1회·get19회·mask read3회다. 두 번째 행의255·선언 누락·grid shift는 get16회·checked2에서 멈추고 세 번째 mask 행은 NOT_CHECKED다. 공간 범위 불일치는 get10회 뒤 mask0으로 차단했다. 두 단계 사이 image institution만 변경하고 파일 SHA를 유지한 사례는2022행의 REGISTRY_IMAGE_MANIFEST_CHANGED로 차단했으며 nested counts는 부분 관측으로 남았다. 그 단계 간 변경은 mock 관측으로 주입해 DB와 전체 파일은 보존했다. 영상 픽셀·훈련·추론은 수행하지 않았다.

`evidence/integration/annual-mask-live-integrity-20261018.json`은 보호141개·기존 source301개·이전 증거1184개·catalog14행과 SHA·예약136314880바이트 불변을 기록한다. 기존 제품 코드·운영 자료·원장·모델·분할·예약을 변경하지 않았다. 이전 전체 backend1184와 여기의 이전 증거1184개는 서로 다른 집계이며 이번 전체 회귀 실행을 뜻하지 않는다.

## 독립 최종 근거와 동결

독립 **7 PASS / 0 SKIP / 24.295825초 / exit 0**는 `evidence/integration/annual-mask-independent-20261018.py`와 같은 stem `.json`·`.log`에 동결했다. 별도 Temp6개 영상 GeoTIFF·30 Registry·미훈련 CPU checkpoint로2/6행의 get13/37회·모델 load1회·mask read N회·영상 픽셀0과 DB/전체 파일 불변을 확인했다. 여섯 번째 행의 입력 불량은 Store I/O0이며 중간255 실패는130 전체 성공 뒤 get25회·mask read2회에서 failfast했다.

동일한 영상 파일 SHA를 유지한 채 두 번째 Registry 관측의 institution과 canonical digest를 바꿨을 때 join이 차단됐다. 이때 nested133 counts의 이전 성공을 남기고 상위 flags는 false로 유지했다. 실제 normalization evidence의 scale을 numeric string으로 오염한 경우130에서 차단되고 mask 호출0이었다. pin·모델 변조·all0·caller snapshot도 확인했다. exact22/10false와 최종 source/test SHA가 일치하며 Git c8ce70a의 기존 핵심8개 source SHA·tracked source는 불변이다. 추가 제품 지적은 없다. 운영·훈련·추론 없이 부분 관측·비원자성·QA/최소 정책·실행 미승인의 범위를 유지한다. 최종 증거 반영 후 본 문서를 동결했다.
