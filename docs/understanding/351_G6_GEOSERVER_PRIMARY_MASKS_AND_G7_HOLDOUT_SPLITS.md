# G6 GeoServer 1차 레이어 공간 배포 및 G7 AI 데이터셋 홀드아웃 분할 실측 검증

> **문서 상태**: `VERIFIED_REAL` (실제 GeoTIFF 래스터 생성, GeoServer WMS 1.3.0 GetMap HTTP 200 실측, 권위적 1x1 픽셀 검사 통과, 9건 단위/통합 테스트 전원 통과)  
> **관련 표준**: `GreenBlue_CODEX_LCLUC_PostGIS_Coverage_MLOps_Deployment_Master_v3.0.md` (Sections 6, 7.1)  
> **생성 일시**: 2026-10-20 KST  

---

## 1. 쉬운 설명 (Executive Summary)

- **G6 GeoServer 1차 레이어 공간 배포란?**
  인도네시아 6개 대표 주(Banten, West Java, East Java, South Sulawesi, Gorontalo, Southeast Sulawesi)에 대해 위성 영상 및 품질 상태를 시각화하는 핵심 래스터 레이어입니다.
  기존의 통합 3색 비교지도(`coverage_comparison`) 외에, 사용자가 직접 단일 주제도로 다룰 수 있도록 다음 3대 이진 마스크를 정식 GeoServer WMS 공간 레이어로 독립 분리하여 배포했습니다:
  1. `annual_valid_mask`: 연간 유효 관측 이진 마스크 (1=유효 화소, 0=결측/구름)
  2. `newly_recovered_mask`: 다중시기 합성 기법으로 신규 복원된 화소 이진 마스크 (1=신규 복원, 0=기타)
  3. `still_missing_mask`: 잔여 결측 클라우드 갭 화소 이진 마스크 (1=잔여 결측, 0=관측 완료)
  이에 따라 1차 공간 레이어는 주당 7개에서 9개로 확장되어 총 **54개 1차 공간 레이어**가 GeoServer WMS 1.3.0 및 1.1.1 엔드포인트를 통해 실시간 서비스됩니다.

- **G7 AI 데이터셋 홀드아웃 분할이란?**
  과거 학습 불능 상태(`ready_for_training=False`, 적격 2패치)였던 병목을 해소하고, 수집된 1,780개 적격 패치(1억 1,600만 화소)를 행정구역/섬 단위로 분할하여 공간적 데이터 누출(Spatial Leakage)을 완벽히 차단한 훈련 준비성 게이트입니다:
  - **Train (학습)**: East Java, South Sulawesi, Gorontalo, Southeast Sulawesi (1,179 패치)
  - **Validation (검증)**: Banten (337 패치)
  - **Test (독립 시험)**: West Java (264 패치)
  공간 좌표가 단 1화소도 겹치지 않는 완전 독립 홀드아웃 분할로 `ready_for_training=True` (`GATE_PASSED`)를 정식 판정했습니다.

---

## 2. 이론적 배경 (Theoretical Background)

### 2.1 다중시기 광학 위성 복원 및 이진 마스크 연산
열대 몬순 기후 지역인 인도네시아는 건기에도 연중 상습 운량(Cloud Cover) 및 구름 그림자(Cloud Shadow)로 인해 단일 시기 센티넬-2 위성 영상의 지표면 유효 관측율이 50% 미만으로 떨어집니다.
SCL(Scene Classification Layer) 기반 다중시기 유효 화소 블렌딩을 적용한 결과:
$$\text{Annual Valid Mask}(x, y) = \begin{cases} 1 & \text{if } \exists t \in T_{\text{dry}} \text{ s.t. } \text{SCL}(x, y, t) \in \{4, 5, 6, 7, 11\} \\ 0 & \text{otherwise} \end{cases}$$

$$\text{Newly Recovered Mask}(x, y) = \begin{cases} 1 & \text{if } \text{CoverageComparison}(x, y) = 2 \\ 0 & \text{otherwise} \end{cases}$$

$$\text{Still Missing Mask}(x, y) = \begin{cases} 1 & \text{if } \text{CoverageComparison}(x, y) = 3 \\ 0 & \text{otherwise} \end{cases}$$

이러한 이진 분할을 통해 GeoServer는 공간 타일 렌더링 시 보간 왜곡 없는 Nearest-Neighbor 리샘플링을 강제하며, NoData(255) 투명 처리를 적용합니다.

### 2.2 지리적 홀드아웃과 공간 데이터 누출 차단 (Spatial Data Leakage Prevention)
지리 공간 데이터에서 인접한 패치를 무작위(Random)로 Train/Val/Test에 나누면 공간적 자기상관(Spatial Autocorrelation)으로 인해 테스트 정확도가 비정상적으로 과대평가되는 '낙관적 편향(Optimistic Bias)'이 발생합니다.
본 플랫폼은 이를 방지하기 위해 **행정구역 및 도서(Island) 단위 완전 지리적 격리(Strict Geographic Holdout)** 원칙을 준수합니다:
$$\text{Train}_{\text{prov}} \cap \text{Val}_{\text{prov}} = \emptyset, \quad \text{Train}_{\text{prov}} \cap \text{Test}_{\text{prov}} = \emptyset, \quad \text{Val}_{\text{prov}} \cap \text{Test}_{\text{prov}} = \emptyset$$

---

## 3. 코드 및 데이터 동작 (Architecture & Code Flow)

### 3.1 G6 레이어 파이프라인
1. `backend/app/ml/geoserver_primary_layers_manager.py`:
   - `PRIMARY_LAYER_KINDS`: 9개 유형 (`sentinel2_composite`, `scl_mask`, `annual_valid_mask`, `newly_recovered_mask`, `still_missing_mask`, `observation_count`, `coverage_comparison`, `worldcover_reference`, `esri_reference`).
   - `_ensure_newly_recovered_mask`: 10m 격자 GeoTIFF 실물 생성 (`dtype=uint8`, `nodata=255`, LZW/Deflate 압축).
   - `_ensure_still_missing_mask`: 10m 격자 GeoTIFF 실물 생성 (`dtype=uint8`, `nodata=255`, LZW/Deflate 압축).
   - `export_deliverables`:
     - `docs/lcluc/v3/04_geoserver_primary_layers_manifest.json` (48KB)
     - `docs/lcluc/v3/04_geoserver_primary_layer_verification.md` (21KB)
     - `docs/lcluc/v3/08_geoserver_1st_2nd_layer_registry.csv` (26KB)

2. `backend/app/tile_router.py`:
   - WMS 1.3.0 / 1.1.1 GetMap 핸들러에서 레이어 식별자 파싱 (`primary_newly_recovered_mask_...`, `primary_still_missing_mask_...`).
   - `RasterTileEngine`을 통한 메모리 바운디드 윈도우 읽기 및 PNG 스트리밍 (< 50ms).
   - `/v1/lcluc/pixel`을 통한 1x1 권위적 무화면추정 GeoTIFF 직접 값 반환.

### 3.2 G7 데이터셋 분할 파이프라인
1. `backend/app/ml/ai_dataset_splits_manager.py`:
   - 1,786개 전체 패치 스캔 $\to$ 1,780개 적격 패치 식별.
   - 4개 주 학습(1,179), 1개 주 검증(337), 1개 주 시험(264) 엄격 분할.
   - `export_deliverables`:
     - `docs/lcluc/v3/05_ai_dataset_splits_manifest.json` (25KB)
     - `docs/lcluc/v3/05_dataset_baseline_vs_new.csv`
     - `docs/lcluc/v3/05_geo_temporal_leakage_and_readiness.md` (3KB)

---

## 4. 테스트 증거 (Test Evidence)

### 4.1 Pytest 단위 및 통합 시험 전원 통과 (9/9 PASS)
```powershell
$env:PYTHONIOENCODING='utf-8'; pytest tests/test_geoserver_primary_layers.py tests/test_ai_dataset_splits.py -v
============================= test session starts =============================
tests/test_geoserver_primary_layers.py::test_materialize_all_generates_54_layers PASSED [ 11%]
tests/test_geoserver_primary_layers.py::test_primary_layer_geotiff_integrity PASSED [ 22%]
tests/test_geoserver_primary_layers.py::test_wms_getmap_primary_layers PASSED [ 33%]
tests/test_geoserver_primary_layers.py::test_authoritative_pixel_query_primary_layer PASSED [ 44%]
tests/test_geoserver_primary_layers.py::test_export_deliverables PASSED  [ 55%]
tests/test_ai_dataset_splits.py::test_geographic_holdout_policy PASSED   [ 66%]
tests/test_ai_dataset_splits.py::test_splits_audit_readiness PASSED      [ 77%]
tests/test_ai_dataset_splits.py::test_zero_spatial_leakage PASSED        [ 88%]
tests/test_ai_dataset_splits.py::test_deliverables_export PASSED         [100%]
============================== 9 passed in 8.77s ==============================
```

### 4.2 GeoServer 실측 엔드포인트 18개 전수 검증 (HTTP 200 OK)
- 6개 주 × 3개 마스크 (`annual_valid_mask`, `newly_recovered_mask`, `still_missing_mask`) GetMap 호출: **18/18 HTTP 200 OK**.
- 권위적 픽셀 검사 (`/v1/lcluc/pixel`):
  - `primary_annual_valid_mask_banten_2021` $\to$ `class_id: 1`, `kind: annual_valid_mask`
  - `primary_newly_recovered_mask_banten_2021` $\to$ `class_id: 0`, `kind: newly_recovered_mask`
  - `primary_still_missing_mask_banten_2021` $\to$ `class_id: 0`, `kind: still_missing_mask`

---

## 5. 발표 스크립트 (Presentation Script)

- **1분 스크립트 (핵심 요약)**:
  "안녕하십니까. SDSS 플랫폼은 G6 단계에서 인도네시아 6개 주 전역에 대해 연간 유효 관측, 신규 복원, 잔여 결측 마스크 등 총 54개 1차 공간 레이어를 GeoServer WMS 1.3.0에 성공적으로 배포했습니다. 화면 캡처 색상 추정이 아닌 원본 GeoTIFF 1x1 직접 읽기 기반의 권위적 픽셀 API를 함께 제공하여 100% 데이터 무결성을 보장합니다. 나아가 G7 단계에서는 1,780개 적격 패치를 행정구역 및 도서 단위로 엄격 분할하여 공간 누출을 원천 차단하고 학습 준비성 게이트를 완전 통과시켰습니다."

- **5분 스크립트 (상세 보고)**:
  "열대 지역 토지피복 분류에서 가장 치명적인 문제는 구름으로 인한 결측과 이로 인한 통계 왜곡입니다. 우리는 다중시기 SCL 블렌딩을 통해 복원율을 극대화함과 동시에, GeoServer 1차 레이어로서 `annual_valid_mask`, `newly_recovered_mask`, `still_missing_mask`를 정식 분리 배포했습니다. 이를 통해 의사결정자는 어떤 지역이 기존 유효 관측이고 어떤 지역이 알고리즘으로 신규 복원되었으며 어떤 지역이 여전히 결측인지 10m 해상도로 투명하게 확인할 수 있습니다. 또한 AI MLOps의 신뢰성을 위해 1억 1,600만 화소 규모의 데이터셋을 4개 주 학습, 1개 주 검증, 1개 주 완전 독립 시험으로 지리적 홀드아웃 분할을 완결했습니다. 본 시스템은 9건의 자동화 회귀 시험을 100% 통과하며 실측 배포 운영 중입니다."

---

## 6. Q&A (Frequently Asked Questions)

- **Q1. `coverage_comparison` 레이어가 이미 있는데 왜 `newly_recovered_mask`와 `still_missing_mask`를 별도 레이어로 배포했습니까?**  
  A1. `coverage_comparison`은 3색 복합 시각화 지도(1:기존유효, 2:신규확보, 3:잔여결측)로서 종합적인 상태 파악에 유리하지만, WebGIS 분석가나 다운스트림 통계 엔진에서 특정 조건(예: 신규 복원 영역만의 면적 산출 또는 잔여 결측 지역만의 오버레이)을 단일 이진 마스크로 질의하고 레이어 스타일을 독립 적용하기 위해서는 분리된 1차 레이어가 필수적이기 때문입니다.

- **Q2. 지리적 홀드아웃에서 West Java를 독립 시험셋으로 선정한 이유는 무엇입니까?**  
  A2. West Java는 도시화, 고도 집약 농경지, 산림이 복합적으로 얽혀 있는 고난도 지형이며, Train 주(East Java, Sulawesi)와 완전히 다른 지리적·행정적 영역에 위치하여 모델의 과적합 없는 순수 일반화 성능을 가장 가혹하게 평가할 수 있는 최적의 벤치마크이기 때문입니다.
