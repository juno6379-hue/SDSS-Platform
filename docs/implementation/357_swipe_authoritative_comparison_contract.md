# Unit 357 — 권위 레이어 Registry와 Swipe 비교 계약

## 1. 결론과 상태

이 작업은 `landcover-series` 목록과 Swipe가 **아무 파일 두 개를 우연히 겹쳐 보이지 않도록** fail-closed 계약을 구현한 단위다.

- 코드/계약: `IMPLEMENTED_UNVERIFIED`
- 합성 fixture 집중시험: `TESTED_SYNTHETIC` — 12/12 PASS
- 운영 파일 읽기 감사: `VERIFIED_REAL` — 권위 원장 1,779행, 품질 적격 1,407행, 권위가 직접 참조한 source window 118개, 등록 시리즈 35개
- 실제 브라우저 적용: `VERIFIED_REAL` — 로컬 개발 서비스에서 API 계약 로드, 0/50/100 프리셋, 키보드 ArrowRight 이동을 실제 브라우저로 확인. 이는 화면 동작 검증이며 과학적 변화 검증은 아님
- 변화탐지/면적/전이행렬: `BLOCKED_NO_MODEL_PREDICTION` — 등록된 `model_prediction` 레이어 0개
- 픽셀 팝업: `BLOCKED_NO_PIXEL_QUERY_API`

따라서 현재 사용 가능한 범위는 **정합 검사를 통과한 연차 참조지도 source window의 시각적 Swipe/Animate**다. 이것을 주 전체 커버리지, 모델 추론, 변화 면적, 과학 정확도 또는 운영 배포로 해석하면 안 된다.

## 2. 발견한 기존 문제

기존 `backend/app/landcover_tiles.py`는 `first-group*/**/annual-window-report.json`을 수정시각 순으로 검색하고 최근 512개를 읽었다. 권위 원장 디렉터리에 `sources`가 있으면 오히려 건너뛰었으며, 동일 series/year가 나오면 `group['years'][year] = layer`로 경고 없이 뒤 파일이 앞 파일을 덮었다. `layer_id`도 파일 내용 SHA가 아니라 경로·크기·mtime 조합이었다.

기존 `TemporalCompare.tsx`는 서버의 비교 계약 없이 두 `layer_id`를 겹쳤다. 지도 위 divider는 `pointer-events:none`인 선이어서 직접 끌 수 없었고, 좌우 타일 오류를 한 문장으로 합쳤다. 같은 연도 선택, 격자 불일치, NoData/mask 차이, 모델 예측 부재가 Swipe나 통계 상태에 연결되지 않았다.

이 방식에서는 오래된 보고서나 새로 복사된 파일의 수정시각이 선택 결과를 바꿀 수 있고, 서로 다른 위치·크기·mask를 화면상 비슷하게 겹쳐 오판할 수 있다.

## 3. 구현한 권위 Registry

권위 파일은 `data/first-group-training-esri-v1/annual-window-report.json` 하나로 고정했다. 임의 glob 결과나 최신 mtime을 권위로 사용하지 않는다.

1. 권위 원장에서 `quality_status=quality_eligible`인 행만 읽는다.
2. 각 행의 `source_window.path`가 실제로 가리키는 디렉터리만 허용한다.
3. 그 디렉터리의 source report에서 `(year, province, label_source, source_group, taxonomy_signature)`가 권위 행과 정확히 같은 레이어만 등록한다.
4. label과 quality mask의 실제 SHA256을 계산해 `layer_id`와 응답에 넣는다. mask는 단일 band·동일 grid·0/1 값 도메인을 전수 검사한다.
5. 같은 논리 series/year가 두 번 발견되면 둘 다 제거하고 `DUPLICATE_GROUP_YEAR`로 registry를 `BLOCKED` 처리한다.
6. 실제 타일 요청 때 파일 size/mtime뿐 아니라 SHA256도 다시 확인한다. 같은 크기와 mtime으로 파일을 바꿔도 타일을 거부한다.
7. 권위 원장과 analyses 입력 stamp가 그대로면 메모리 registry를 재사용한다. 실제 측정은 cold 약 9.044초, 동일 입력 재조회 0.001초였다.

운영 파일 읽기 결과는 다음과 같다.

| 항목 | 실측 |
|---|---:|
| 권위 원장 행 | 1,779 |
| 품질 적격 행 | 1,407 |
| 품질 미달로 제외 | 372 |
| 권위 source window | 118 |
| 등록 시리즈 | 35 |
| 생성한 연도쌍 계약 | 210 |
| 시각 비교만 허용 | 183 |
| 격자/mask 불일치로 차단 | 27 |
| 모델 예측 레이어 | 0 |
| registry 오류 | 0 |

27개 차단 쌍은 `mask_grid` 불일치 27개이며, 그중 bounds/shape 불일치가 각각 8개 포함된다. 화면에서 재투영해 억지로 맞추지 않는다.

## 4. 비교 preflight와 API 계약

`GET /api/data/landcover-series`의 스키마 버전은 `2.0`, 비교 계약은 `landcover-comparison-contract-v1`이다. 기존 `series[].years[]`와 `tile_url`을 유지하면서 다음 증거를 추가했다.

레이어 필수 증거:

- `asset_sha256`, `asset_bytes`, `asset_verification`
- `aoi_id`
- `crs`, `affine`, `bounds`, `bbox`, `resolution`, `shape`, `dtype`, `nodata`
- `class_schema_id`, `class_schema_version`
- `mask_asset_sha256`, `mask_policy_version`, `mask_grid`
- `reference_kind`, `evidence_state`, `source.dataset_version`

두 시점 비교는 다음 필드를 exact 비교한다.

```text
aoi_id
crs
affine
bounds
resolution
shape
class_schema_id
class_schema_version
nodata
mask_policy_version
mask_grid
```

두 asset SHA가 없거나 동일 연도에 같은 SHA가 재사용돼도 차단한다. 통과한 쌍에는 입력 layer/SHA/schema/mask를 canonical JSON으로 해시한 안정적인 `comparison_id`를 부여한다.

비교 응답의 핵심 필드는 아래와 같다.

```json
{
  "comparison_id": "cmp-...",
  "preflight_status": "READY_VISUAL_REFERENCE_ONLY | READY | BLOCKED",
  "visual_comparison_allowed": true,
  "change_statistics_allowed": false,
  "change_statistics_status": "BLOCKED_REFERENCE_LAYERS_NOT_MODEL_PREDICTIONS",
  "pixel_query_status": "BLOCKED_NO_PIXEL_QUERY_API",
  "blockers": [],
  "matched_contract_fields": ["aoi_id", "crs", "affine"],
  "mismatched_contract_fields": []
}
```

`annual_reference` 두 장은 시각 확인만 허용한다. 두 장 모두 검증된 비합성 `model_prediction`이고 preflight를 통과해야만 통계 허용 후보가 된다. 현재 운영 목록에는 모델 예측이 0개라 전역 상태가 `BLOCKED_NO_MODEL_PREDICTION`이다.

## 5. UI 동작

`frontend/src/TemporalCompare.tsx`는 서버가 보낸 `tile_url`, `comparison_id`, preflight, SHA와 상태를 사용한다.

- divider를 지도 위에서 mouse/pointer/touch로 직접 끌 수 있다.
- 키보드 `Home`, `End`, `ArrowLeft`, `ArrowRight`를 지원한다. Shift+화살표는 10%씩 이동한다.
- `왼쪽 100%`, `50/50`, `오른쪽 100%` 프리셋을 제공한다.
- 어느 지도에서 조작해도 zoom/pan/bearing/pitch를 반대 지도에 동기화하며 재진입을 막는다. ResizeObserver에서는 두 지도를 함께 resize한다.
- 왼쪽/오른쪽 loading과 tile 오류를 별도로 표시한다.
- 같은 연도는 오른쪽 선택 목록에서 비활성화한다.
- 비교 계약이 없거나 grid/mask가 다르면 두 지도를 겹치지 않는다.
- asset SHA, AOI, CRS, 해상도, shape, NoData, schema와 통계 차단 사유를 화면에 표시한다.
- tile 렌더링은 quality mask가 1인 화소만 불투명하게 표시하며 mask가 0인 화소는 투명 처리한다.

서버 pixel-query가 없으므로 픽셀 팝업을 만든 척하지 않고 `BLOCKED_NO_PIXEL_QUERY_API`를 표시한다. 원본 class raster 기반 면적·전이행렬 API도 없으므로 UI에서 수치를 생성하지 않는다.

## 6. 시험 증거

명령:

```powershell
$env:PYTHONPATH='backend'
python -m pytest tests/test_landcover_tiles.py -q
```

결과: `12 passed` (약 5.35초). 다음을 검증했다.

- 권위 원장만 사용하고 더 최신인 decoy report를 무시
- 누락 연도 보존
- 참조지도 Swipe 허용과 변화통계 차단 분리
- 동일 group/year 두 자산 동시 제거와 registry 차단
- affine/bounds가 다른 두 레이어의 Swipe 차단
- size/mtime을 보존한 SHA 변조의 타일 거부
- Esri Cloud/NoData 및 quality mask 0 투명 처리와 water 색상
- 잘못된 mask 값·label/mask grid 불일치·mask SHA 변조 차단
- 외부 경로 거부와 잘못된 XYZ/layer 거부

프런트 명령:

```powershell
cd frontend
npm run build
```

결과: TypeScript와 Vite production build PASS(131 modules, 20.08초). 기존 번들 크기 경고(약 1.89 MB JS)는 남아 있으나 이 작업의 실패는 아니다.

실제 파일 smoke에서 첫 등록 레이어의 XYZ z0 타일은 334 bytes PNG로 생성됐고 SHA256은 `3c6c50f94ab35e9f96c772731fe6b7950048179bc81b8ab0396cc1edbde89163`이었다.

## 7. 실행 서비스와 GeoServer 확인 범위

2026-10-21 read-only 확인:

- API 8002 `/healthz`: HTTP 200, 48 bytes
- UI 5174 `/`: HTTP 200, UI proxy `/healthz`: HTTP 200
- GeoServer 호환 8088 GetCapabilities: HTTP 200, 1,626 bytes
- Capabilities의 `<Name>`은 `WMS`, `lcluc_discrete_9classes`만 열거됨

실제 브라우저 `#/view/8`에서 registry `REGISTERED`, contract `landcover-comparison-contract-v1`, 등록 레이어 118개, 모델 예측 0개를 확인했다. 2020/2021 참조 레이어 쌍은 `READY_VISUAL_REFERENCE_ONLY`로 표시됐고 변화 통계와 pixel query는 차단됐다. 프리셋은 왼쪽 100%=split 100, 오른쪽 100%=0, 50/50=50으로 동작했고 키보드 ArrowRight는 51로 이동했다.

따라서 GeoServer HTTP 응답을 54/72개 named layer 게시 증거로 확대하지 않는다. 이 Unit은 로컬 원본 래스터 타일 계약을 교정했으며 실제 GeoServer 게시, 서비스 재시작, 운영 registry 쓰기를 수행하지 않았다.

## 8. 남은 P0/P1

### P0

1. 실제 연도별 `model_prediction` COG와 valid/quality mask를 같은 AOI/grid/schema 계약으로 생성하고 ResultRegistry/LayerRegistry에 등록한다.
2. 서버 원본 raster 기반 `/pixel-query`, common-valid 변화, 면적, 전이행렬 API를 `comparison_id`에 묶는다.
3. 실제 독립 holdout과 사람 승인으로 baseline/challenger OA·Precision·Recall·F1·IoU를 재측정한다. 현재는 작은 패치 대비 향상 수치를 계산할 실제 예측/독립 정답이 없다.
4. 6개 주 경계 전체를 대상으로 valid coverage와 remaining gap을 측정한다. 현재 118 source window/patch 표시는 주 전체 커버리지가 아니다.

### P1

1. 실제 브라우저에서 확인한 프리셋·키보드에 더해 drag/touch, zoom/pan/resize, 좌우 tile 오류를 자동 E2E로 고정한다.
2. pixel-query가 구현되면 NoData, mask 제외, T1/T2 한쪽 누락을 `비교 불가` 팝업으로 구분한다.
3. GeoServer가 실제 immutable layer version과 named layer 목록을 제공하면 로컬 XYZ 대신 검증된 WMS/WMTS URL을 같은 `comparison_id`에 연결한다.

## 9. 사용법

1. `/api/data/landcover-series`를 조회한다.
2. `registry_status=REGISTERED`인지 확인한다.
3. 시리즈와 서로 다른 두 연도를 선택한다.
4. 해당 layer id 쌍의 `comparisons[]`를 찾는다.
5. `visual_comparison_allowed=true`일 때만 Swipe를 표시한다.
6. `change_statistics_allowed=false`이면 화면 비교만 수행하고 변화량을 계산하거나 보고하지 않는다.
7. `blockers`가 있으면 레이어를 재투영하거나 누락값으로 채우지 말고 원본 registry/grid/mask를 교정한다.
