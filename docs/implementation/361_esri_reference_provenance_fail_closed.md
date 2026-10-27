# Unit 361 — Esri 참조 계보 fail-closed 교정

## 1. 쉽게 설명

기존 `esri_reference.tif`는 Esri에서 받은 자료가 아니라 ESA WorldCover 클래스 번호를 다른 번호로 바꾼 파일이었다. 이를 Esri 레이어로 보여주면 원천이 다른 두 지도를 교차 검증한 것처럼 오해할 수 있다. 생성 코드를 폐기하고, 기존 파일은 감사용으로 남겨 두되 파일 경로·WMS·픽셀 API에서 제공하지 않도록 차단했다.

## 2. 역할 분리

| 자료 | 역할 | 현재 상태 |
|---|---|---|
| ESA WorldCover | 독립 제품의 참조 래스터 후보 | `IMPLEMENTED_UNVERIFIED`; 외부 게시는 미검증 |
| Esri 10m Annual Land Cover | 권위 원장 행이 직접 가리키는 연차 weak training label | `IMPLEMENTED_UNVERIFIED`; 모델 예측·독립 지상정답으로 사용 금지 |
| legacy `esri_reference.tif` | WorldCover LUT 파생물 | `BLOCKED_LEGACY_WORLDCOVER_CROSSWALK_QUARANTINED` |

실제 Esri weak label의 권위 경로는 `data/first-group-training-esri-v1/annual-window-report.json`이다. `landcover_tiles.py`는 `quality_eligible` 행이 직접 참조한 `label_path`, `quality_mask_path`, dataset version, source URL, 실제 SHA를 검사한다. 임의 파일 검색으로 누락 연도를 만들지 않는다.

## 3. 코드·API 동작

- `GeoServerPrimaryLayersManager.materialize_all()`은 WorldCover 입력이 있어도 `esri_reference.tif`를 생성하지 않는다.
- 호환용 `esri_reference` 행은 계속 반환하지만 `file_rel_path`, 크기, nodata, WMS URL을 null로 두고 `BLOCKED`로 표시한다. `independent_ground_truth=false`, `model_prediction=false`를 명시해 학습/평가 근거로 오인하지 않게 한다.
- 기존 파일이 보이면 `legacy_artifact_quarantined=true`로 기록하고 인정 자산수에 포함하지 않는다.
- 폐기된 private 생성기를 직접 호출해도 `LEGACY_WORLDCOVER_CROSSWALK_MUST_NOT_BE_PUBLISHED_AS_ESRI`로 중단한다.
- `/geoserver/wms` GetMap과 `/v1/lcluc/pixel`은 레이어 이름과 direct path 모두에서 `esri_reference`를 탐지해 HTTP 409, `UNVERIFIED_REFERENCE_PROVENANCE`을 반환한다.
- Swipe의 연차 Esri 자료 경로는 `landcover_tiles.py`의 `weak_label_agreement`로 계속 분리되며, 각 series/layer에 `independent_ground_truth=false`, `model_prediction=false`를 내려 모델 평가·변화통계 입력 오염을 차단한다.

## 4. 시험 근거

`2026-10-21` 집중 회귀:

```text
python -m pytest -q \
  tests/test_geoserver_esri_reference_fail_closed.py \
  tests/test_geoserver_primary_layers.py \
  tests/test_landcover_tiles.py \
  tests/test_geoserver_wms_pixel_service.py \
  tests/test_mlops_router.py \
  tests/test_model_benchmark_evaluator.py

53 passed, 147 warnings in 39.01s
```

시험은 다음을 고정한다.

1. WorldCover 소스가 있어도 Esri 파일을 새로 쓰지 않음
2. 기존 legacy 파일이 있어도 registry 경로/WMS URL이 null이고 차단됨
3. WMS 레이어 명, pixel 레이어 명, direct path 모두 HTTP 409
4. 권위 report 기반 실제 Esri weak-label 타일 렌더링 기존 시험은 계속 통과

운영 data, 수집 원장, GeoServer 게시, 실행 서비스는 쓰거나 재시작하지 않았다.

## 5. 실파일 읽기 감사

6개 주의 기존 `worldcover_reference.tif` 픽셀에 종전 구현과 같은 256-entry uint8 LUT(기본 0, 10→1, 20→5, 30→2, 40→4, 50→6, 60→7, 80→0, 90→3)를 적용한 결과와 `esri_reference.tif`를 독립 비교했다. 6/6이 shape과 픽셀 전체에서 일치했다. 이는 기존 파일이 Esri 원천의 독립 증거가 아니라 WorldCover 파생물이라는 차단 근거다. Root 재검산 결과는 `evidence/integration/unit361-root-integration-20261021/legacy-esri-lut-audit.json`에 보존했다.

## 6. 현재 판정

- 코드 및 임시 픽스처 시험: `TESTED_SYNTHETIC`
- 기존 6개 파일의 WorldCover LUT 일치: `VERIFIED_REAL_LOCAL_BYTES`
- Esri 연차 weak label의 독립 지상정답 자격: `BLOCKED`
- Esri primary GeoServer named-layer 게시: `BLOCKED`
- 실학습·실예측·정확도 향상 증거: `BLOCKED`
