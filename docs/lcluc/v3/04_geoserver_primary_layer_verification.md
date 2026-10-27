# G6 1차 GeoServer 레이어 증거 교정

> 상태: `BLOCKED`
> 교정 단위: Unit358 + Unit361
> 실제 확인 범위: 로컬 primary GeoTIFF 54개 파일 존재·SHA-256, 그중 `esri_reference` 6개의 WorldCover LUT 변환 일치

## 확인된 사실

- 6개 주 × 9종 기존 경로에 로컬 GeoTIFF 54개가 물리적으로 존재한다.
- 그중 6개 `esri_reference.tif`는 각 주의 `worldcover_reference.tif`에 기존 LUT를 적용한 결과와 픽셀 단위로 전부 일치했다. Esri 원천 증거가 아니다.
- [04_geoserver_primary_layers_manifest.json](04_geoserver_primary_layers_manifest.json)은 이 6개를 `BLOCKED_LEGACY_WORLDCOVER_CROSSWALK_QUARANTINED`로 표시하고, 제공 경로·WMS URL·인정 SHA를 `null`로 차단한다. 물리 파일은 감사 증거로 보존하며 삭제하지 않았다.
- GeoServer 호환 서비스의 GetCapabilities HTTP 200과 일부 표본 GetMap PNG 200 이력은 있다.

이 사실은 나머지 후보 48개가 GetCapabilities에 전부 열거되었다는 증거가 아니다. `esri_reference` 6개는 코드·manifest·registry·WMS/pixel 경로에서 일괄 차단한다. 나머지 레이어도 capabilities 원문과 SHA가 확보되기 전에는 `PUBLISHED_ONLINE`로 표시하지 않는다.

## Esri weak label의 올바른 역할

실제 Esri 10m Annual Land Cover 파일은 `data/first-group-training-esri-v1/annual-window-report.json`이 직접 참조한 `quality_eligible` 행의 `label_path`, `label_source_url`, `label_dataset_version`, 파일 SHA, quality mask로만 등록한다. UI Swipe에서도 이 경로는 `weak_label_agreement`, `independent_ground_truth=false`, `model_prediction=false`인 참조 자료이며 변화통계·정확도·승격 입력이 아니다. 고정 2021 `primary_esri_reference_*`를 만들거나 제공하는 경로와 분리한다.

## 합성 fixture와 원천 계보

다음 3종 × 6개 주, 총 18개는 결정적 합성 패턴에서 생성된 fixture로 확인되어 `TESTED_SYNTHETIC`으로 표시한다.

- `coverage_comparison`
- `newly_recovered_mask`
- `still_missing_mask`

나머지 18개 source-backed 후보도 이번 단위에서는 파일 존재와 SHA만 확인했다. Sentinel-2/WorldCover 원천의 실제 다운로드 provenance, 원천 asset SHA, 처리 graph가 독립적으로 검증되지 않았으므로 `LOCAL_FILE_SHA_VERIFIED_PROVENANCE_UNVERIFIED`다. 별도 18개는 합성 fixture, 6개는 legacy WorldCover 교차표 차단 대상이다.

## 현재 수용 기준

레이어별 `VERIFIED_REAL` 또는 게시 완료 판정에는 다음 자료가 모두 필요하다.

1. 불변 원천 asset URI와 SHA-256
2. 생성 코드/설정/입력 SHA를 잇는 lineage
3. 출력 GeoTIFF SHA, CRS, affine, bounds, resolution, shape, nodata/mask
4. GetCapabilities 원문과 SHA 및 기대 named-layer 전수 열거
5. 해당 named layer의 GetMap과 원본 픽셀 대조 증거

현재는 4와 5가 전수 기준으로 없고, 합성 18개는 1~3의 실제 관측 계보가 없다. 그래서 전수 게시, 구름 복구 면적, 과학 통계 근거로 사용할 수 없다.
