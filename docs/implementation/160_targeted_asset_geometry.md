# 160 — 고정 로컬 영상·동년 참조라벨 전체 영역 검사

상태: `TESTED_SYNTHETIC`. `inspect_targeted_asset_geometry(project_root, request)`는 명시적으로 고정된 영상과 참조라벨 두 파일의 실제 GTiff 헤더를 읽어 요청 WGS84 사각형의 전체 영역이 각각의 래스터 범위 안에 있는지 관측한다. collector·157·원장·API/UI를 연결하거나 변경하지 않는다. 실제 원격 자산 수신·학습·Registry 쓰기는 0이다.

## 목적과 계약

동자바2025 일반 수집 2차의 SCL 후보 검사는 통과했지만 이후 COG 읽기가 `AOI 중심점이 COG 범위 밖입니다`로 종료됐다. 코드 순서와 보존 자료는 B02 이전의 Esri 예비 라벨 읽기를 가리키지만, 실패한 실제 원격 헤더는 보존되지 않아 이를 확정적인 B02 오류나 Esri 경계 원인으로 표현하지 않는다. 160은 이 사건의 원격 재실행이나 원인 확정 도구가 아니다. SCL·카탈로그 경계만으로 다른 영상·참조 파일의 범위를 추정하지 않도록 만드는 로컬 검사 단위다.

입력은 정확히 다음 8개 키다. JSON 문자열 파서가 아니라 Python dict 진입점이다.

```json
{
  "schema_version": 1,
  "kind": "TARGETED_ASSET_GEOMETRY_REQUEST",
  "target_year": 2025,
  "image_year": 2025,
  "label_year": 2025,
  "target_bbox_wgs84": [105.01, -6.34, 105.02, -6.33],
  "image_ref": {"path": "data/local-image.tif", "sha256": "고정 lowercase64 SHA"},
  "label_ref": {"path": "data/local-label.tif", "sha256": "고정 lowercase64 SHA"}
}
```

위 경로와 SHA는 예시이며 실행 가능한 실제 자료 선언이 아니다. 연도는 bool이 아닌 2020~2025 정수이고 세 선언이 같아야 한다. 이는 caller 선언의 일치만 검사하며 영상 촬영연도·동년 라벨 출처 진실은 검증하지 않는다. 역할 두 개는 키로 고정된다. 파일의 실제 밴드 의미·라벨 taxonomy·서로 다른 실물 여부를 추정하지 않는다.

138 `_copy_json`의 strict builtin 사본을 재사용한다. cycle·surrogate·NaN/Inf·53bit 밖 정수·깊이16·8192노드·256KiB 초과와 여분 키를 차단한다. bbox는 유한 숫자 4개이고 bool·0면적·뒤집힘·날짜변경선 통과·극점 접촉을 거부한다. 경도는 -180~180, 위도는 -90과90의 사이여야 한다. 극점/날짜변경선 전용 처리는 이 단위가 지원하지 않는다.

## 실제 바이트와 기하 검사

157 `_pinned`와 123 read-only 파일 경계 검사를 재사용한다. 각 ref는 정확히 path/sha256, 프로젝트 `data` 아래 상대경로와 lowercase SHA를 요구한다. 파일당64MiB 상한과 경로/링크/파일변경 검사를 적용하고 바이트를 메모리에 고정한다. 이 상한은 native GDAL 전체 CPU/RSS sandbox가 아니다.

TIFF/BigTIFF magic을 먼저 검사하고 MemoryFile을 GTiff driver로 연다. PAM·디렉터리 탐색·외부 지리참조를 비활성화하고 PROJ network를 OFF로 설정한다. VRT·opaque bytes·subdataset·GCP/RPC 지리참조를 허용하지 않는다. 내부 CRS는 EPSG로 식별되는 projected 또는 geographic CRS여야 한다. width/height1~65536·band1~64, 유한 north-up affine, 회전0·양수 x해상도·음수 y해상도를 요구한다.

실제 affine와 shape의 **픽셀 바깥 경계**가 검사 기준이다. 카탈로그 bbox 입력 자체가 없으므로 caller의 카탈로그 경계로 실제 범위를 대체할 수 없다. EPSG4326은 bbox를 직접 비교해 정확한 경계 접촉을 허용한다. 다른 CRS에서는 GDAL `transform_bounds`로 각 edge를1024개 추가점으로 조밀화하고 네 bound를 각각16ULP씩 바깥으로 확장한 envelope를 실제 래스터 범위에 대조한다. 비유한/뒤집힌 변환을 거부한다.

**변환은 유한 표본의 수치 관측이다.** 임의 비선형 투영의 모든 연속점에 대한 수학적 포함 증명은 아니다. 16ULP 확장은 부동소수점 반올림 여유이며 모든 곡률 오차를 제한한다는 보장은 아니다. 좁은 경계 사례는 보수적으로 차단될 수 있다. 이 한계를 운영 실행 안전성 보증으로 확대하지 않는다. 검사 단위는 caller가 요청한 WGS84 사각형 전체이며 157의 회전된 native256 polygon과 동일하지 않을 수 있다.

영상과 라벨은 서로 다른 CRS·해상도를 가질 수 있으며 각자 독립적으로 검사한다. 성공이 같은 grid·256픽셀 창 정렬·정확히10m·resampling 불필요를 뜻하지 않는다. SCL·SWIR·기타 보조 자산도 검사하지 않는다. 두 파일을 모두 관측한 뒤 원본 ref를 다시 읽어 SHA를 확인한다. 이 전후 검사는 atomic snapshot이나 그 사이 변경 후 복구까지 검출하는 OS 잠금이 아니다.

## 출력과 차단

로컬 성공은 `LOCAL_COVERAGE_OBSERVED_EXECUTION_BLOCKED` / `EXECUTION_GUARDS_NOT_CONNECTED`다. role·SHA·실제 CRS/affine/shape/band 수·실제 bounds·native 요청 envelope·수치 여유를 `assets`에 반환한다. 자산 관측은 `sampled_native_envelope_contained=true`이며 `coverage_method`는 `EPSG4326_EXACT` 또는 `DENSIFIED_ENVELOPE_NUMERICAL_OBSERVATION`이다. `complete_projection_coverage_proven`은 항상 false다. 입력 상대/절대 경로와 원격 URL·예외 원문은 반환하지 않는다. request canonical SHA와 `local_bytes_verified`, `declared_years_match`를 제공한다.

실패는 `BLOCKED`와 고정 issue, 빈 assets·null request SHA·false 관측으로 닫힌다. 대표 issue는 `REQUEST_INVALID`, `YEAR_DECLARATION_MISMATCH`, `BBOX_INVALID`, `FILE_PIN_MISMATCH`, `RASTER_INVALID`, `RASTER_GRID_INVALID`, `TRANSFORM_INVALID`, 역할별 `IMAGE_COVERAGE_SHORTFALL`/`LABEL_COVERAGE_SHORTFALL`, 안전 reader 실패의 `LOCAL_INPUT_UNAVAILABLE`이다. 부분 통과 자산을 성공으로 반환하지 않는다.

`same_grid_asserted`, `execution_supported`, `pending_footprints_verified`, `support_assets_verified`, `source_scene_split_verified`, `quality_verified`, `temporal_truth_verified`, `training_ready`는 항상 false다. job·claim·예약·다운로드·terminal/finalize·정산 결과를 생성하지 않는다. 후속 collector 연결에는 최신 원장과 pending/support footprint, scene 분할, 명시 claim, native crop 정렬, 최종 품질·나지 기준 검증이 별도로 필요하다.

## 시험 근거와 UI 영향

```powershell
$env:PYTHONPATH='.runtime;.;backend;tests'
python -m unittest test_targeted_asset_geometry -v
```

`evidence/integration/targeted-asset-geometry-agent-20261018.log`: 최종 **10 PASS / 1.613초**. Temp 실제 projected GTiff256~512와 다른20m/10m 해상도, 별도 geographic CRS, 중심은 안이나 전체 bbox는 밖, 영상은 안이나 라벨은 밖, 정확한 geographic 경계 접촉, 실제 헤더 범위 불일치, SHA 사전 변조/관측 후 변조, bool/NaN/cycle/여분 키/연도 불일치, VRT·회전·경로 탈출 차단과 입력·파일 불변을 검증했다. 추가 시험은 malformed TIFF의 반환 경로/원문 비누출과 변환 envelope가 projected 경계에 정확히 맞는 fault injection에서 outward padding으로 보수 차단되는 동작이다. 초기9 PASS/3.090초와 최종10 PASS는 중복이므로 합산하지 않는다. rasterio affine 연산의 PendingDeprecationWarning은 실패가 아니다.

위 시험은 모두 Temp 합성 자료다. Root 후속에서 실제 고정 영상과 정합 라벨 한 쌍의 작은 interior bbox를 읽어 관측할 수 있지만, 이를 실제256 crop 정렬·나지성과·과학 정확도 검증으로 확대하지 않는다. 그 관측은 별도 증거와 함께 기록해야 한다. 내부 read-only helper이며 HTTP·상태·오류 API와 기존 Workspace를 바꾸지 않아 UI 연결이나 브라우저 검증은 이 단위에 필요하지 않다. Root의 독립 검토·이해자료·공통 인계 갱신은 별도 최종 마감 항목이다.

## Root 통합 수락 — 2026-10-18 10:50 KST

독립 검토는 최종10 PASS/1.656초이고, Root는 신규10개와 기존157의8개를 함께 실행해 **18 PASS/5.324초/exit0**을 확인했다. 범위·이름·수치 변환 한계에 대한 리뷰를 반영한 최종 코드 기준이다. 시험 집합은 겹치므로10+10+18을 합산하지 않는다. 근거는 `targeted-asset-geometry-independent-20261018.json` 및 `targeted-asset-geometry-root-related-20261018.log`다.

Root는 실제 저장된 품질 적격 기록의 영상·정합 라벨 한 쌍에서 영상 내부 절반 영역의 WGS84 bbox를 만들고 두 원본을 SHA로 고정해 함수를 실행했다. `LOCAL_COVERAGE_OBSERVED_EXECUTION_BLOCKED`, 두 원본 SHA 불변, 보호한 기존157/collector/API/App/Toolbox 소스6개 SHA 불변을 확인했다. 이 관측은 로컬 헤더와 고정 바이트에 한정한다. 실제256 crop·원격 COG·나지 픽셀·새 품질 검사는0이다. 결과는 `targeted-asset-geometry-real-20261018.py/json`에 있다.

첫 실제 관측 caller가 기존 manifest의 문자열 연도를 그대로 전달해 REQUEST_INVALID로 정상 차단됐다. Caller가2020~2025 십진 문자열임을 확인한 뒤 명시 정수 선언으로 수정했으며 제품 함수·기존 원본·연도는 변경하지 않았다. 실패 원인을 새 제품 결함이나 실물 관측 성공으로 섞지 않는다.

설명·발표 대본·FAQ는 `docs/understanding/160_TARGETED_ASSET_GEOMETRY.md`에 별도 이해 담당이 작성한다.160 전체 집행가드 중 이 로컬 검사만 완료됐으며, 기존 collector 연결과 나머지 실행조건은 계속 PLANNED/BLOCKED다.
