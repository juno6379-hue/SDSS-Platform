# LCLUC 데이터 파이프라인 현황 감사 및 AS-IS → TO-BE 전환 보고서
## Pipeline Audit: Current State vs Target Architecture (CODEX v1.1 G0~G8)

- **문서 식별자**: `docs/lcluc/pipeline_audit_as_is_to_be.md`
- **작성 일자**: 2026-10-19
- **문서 버전**: v1.1
- **적용 규격**: `UI/GreenBlue_CODEX_LCLUC_GeoServer_1st_ML_Inference_2nd_ChangeDetection_Repair_v1.1.md` (제0조 ~ 제1조)
- **감사 대상 환경**:
  - Python: 3.11.9, OS: Windows 10 (10.0.26200), GDAL/rasterio: 1.4.4, numpy: 2.4.6, pytest: 9.1.1
  - Git Commit: 관측 HEAD `36d433b3d65cddc1166750f3fa98f9f7c0a38298` + Units 332~347 구현
  - GeoServer 연계 버전: 2.24+ / 내장 고성능 WMS 1.3.0 VRT 타일 엔진

---

## 1. 개요 및 감사 배경 (Executive Context)

### 1.1 사용자 문제 제기 및 감사의 출발점
사용자 보고에 따르면, **"GeoServer 레이어 통합과 변화탐지 분석 기능은 현재 구현돼 있지만, 변화탐지 화면에서 실제 픽셀 단위 토지피복 분류 지도가 보이지 않고 큰 사각 격자나 절차적 패턴만 나타난다"**는 중대한 결함이 지적되었습니다.

본 감사는 이 진술을 검증 출발점으로 삼아, 코드베이스 전체의 파일·함수·API·데이터 원장을 실측 감사하고, 파이프라인의 각 단계(G0 ~ G8)가 **실자료 GeoTIFF**를 사용하는지, 아니면 **임의 격자/Canvas 절차적 생성/가짜 노이즈**에 의존하고 있는지를 과학적으로 규명했습니다.

### 1.2 왜 기존 화면에서 격자/절차적 패턴이 나타났는가? (근본 원인 규명)
실측 소스 코드 감사 결과, 기존 시스템에서 실제 픽셀 분류 지도가 보이지 않았던 정확한 원인은 다음과 같습니다:
1. **프론트엔드 절차적 캔버스 대체 (`frontend/src/lclucLandcoverRaster.ts`)**:
   - 프론트엔드 연구 지도에서 실제 GeoServer WMS 래스터 타일을 호출하지 않고, 클라이언트 단에서 `generateLandcoverCanvasDataUrl` 함수를 통해 fBm(다중 옥타브 프랙털 노이즈)과 수학적 사행천/호수 함수로 512×512 HTML5 Canvas 상에 가상의 지형을 절차적으로 합성하여 `type: 'image'` 레이어로 띄우고 있었습니다.
   - 이는 외형상 유기적인 지형처럼 보이지만, **디스크의 실제 위성 관측 래스터와는 0% 일치하는 가짜 시각화**였습니다.
2. **시계열 다중 연도 실자료 파이프라인의 연결 단절**:
   - `data/first-group-2021/`에는 2021년 단일 시점 WorldCover 참조도만 존재하고, 2020년 또는 2025년 단일 장면 단위의 전역 분류도가 준비되지 않았습니다.
   - 2개 시점의 실자료가 확보되지 않은 상태에서 UI 변화탐지를 렌더링하려다 보니, T1(2020)과 T2(2025)에 임의의 산림 감소/시가지 확장 시뮬레이션 데이터를 주입하는 임시 코드가 작동했습니다.
3. **GeoServer 1차(참조자료)와 2차(모델추론)의 게시 분리 부재**:
   - 학습 전 검증을 위한 외부 참조자료(`reference_landcover`)와 AI 모델이 추론한 결과(`model_prediction`)가 단일한 네임스페이스와 상태 구분 없이 뒤섞여 있었습니다.

---

## 2. CODEX v1.1 9대 단계별 재정렬 (G0 ~ G8 Target Architecture)

CODEX v1.1 명령에 따라 전체 파이프라인을 9개 정규 게이트로 재정렬합니다:

```text
G0. 현재 구현·데이터·GeoServer 상태 감사 (본 문서)
     ↓
G1. 데이터 수집·전처리 및 검증 (Raw Sentinel-2 + SCL + WorldCover → AI-ready 패치)
     ↓
G2. GeoServer 1차 연계 (Pre-training GIS Validation: 참조도, 품질마스크, 원영상 WMS 게시)
     ↓
G3. AI 학습 준비성 → 학습 → 검증 (Model Training & Validation Gate)
     ↓
G4. 연도별 AI 추론 (Inference: 모델 예측 정수 래스터 + 매니페스트 발행)
     ↓
G5. GeoServer 2차 연계 (Post-inference Result Publishing: AI 예측도 WMS 게시 및 스타일 검증)
     ↓
G6. T1/T2 픽셀 기반 변화탐지 (Change Detection: 공통유효영역, 전이행렬, 변화지도)
     ↓
G7. MapLibre SDSS Workspace (Swipe, Animate, Authoritative Pixel Popup, KPI 동기화)
     ↓
G8. 회귀시험·과학검증·운영승인 상태 분리 및 완료 보고
```

---

## 3. AS-IS vs TO-BE 상세 비교표 (Minimum AS-IS → TO-BE Table)

| 단계 | 현재 파일/함수·API (AS-IS) | 실제 데이터 연결 | 지금의 문제 (Current Gaps) | 수정 항목 (TO-BE Implementation) | 검사 방법 (Verification) | 판정 (Status) |
|---|---|---|---|---|---|:---:|
| **G0. 현황 감사** | `docs/lcluc-map/current-state-audit.md` | 저장소 내 물리 파일 전수 감사 | 화면의 격자/절차적 노이즈 표시 원인 미문서화 | CODEX v1.1 기준 8종 감사 보고서 체계 구축 | 파일 경로·SHA-256·로그 실사 | **PASS** |
| **G1. 수집·전처리** | `data/first-group-2021/`, `data/first-group-training-esri-v1/`, `scripts/collect_targeted_bare.py` | 2021 참조 6장면, 2020~2025 1,779개 패치셋 | SCL 구름 결측과 라벨 NoData 혼동 가능성, 2021 WorldCover를 2025 관측으로 오용 위험 | SCL 마스크(0,1,3,8,9,10,11 결측) 분리 및 NoData(255) vs 수역(0) 분리 확립 | `tests/test_lcluc_inventory_codex.py` | **VERIFIED_REAL** |
| **G2. GeoServer 1차** | `evidence/geoserver/sld/lcluc_discrete_9classes.sld`, `backend/app/ml/raster_tile_engine.py` | `data/first-group-2021/*/label-worldcover.tif` | 연속형 Bilinear 보간 적용 시 클래스 경계에 가짜 클래스 생성 위험 | 공인 SLD `<ColorMap type="values">` 및 Nearest-Neighbor 강제, WMS 1.3.0 엔드포인트 연동 | `tests/test_geoserver_wms_pixel_service.py` (9건 PASS) | **VERIFIED_REAL** |
| **G3. AI 학습·검증** | `backend/app/lcluc_workflow.py:_gate`, `backend/app/ml/model_deployment_promotion.py` | TinyUNet 체크포인트 `baseline2021_cpu_v1_model` | 현지 지상 정답(Ground Truth) 부재, 학습 데이터 부족으로 전역 학습 차단 | `train_job=BLOCKED_DATA_INSUFFICIENT` 명시, 지상정답 독립평가 시까지 Draft 유지 | `tests/test_lcluc_codex_acceptance.py` Test 12 | **BLOCKED (정상 가드)** |
| **G4. AI 추론** | `backend/app/ml/timeseries_transition_engine.py` | 패치 단위 합성 예측 fixture | 2025년 관측자료 부재 상태에서 허위 2025 예측 래스터 생성 위험 | 2025 실영상 및 모델 없는 경우 예측 생성 차단, 합성 fixture는 `TEST DATA` 네임스페이스 격리 | `tests/test_lcluc_codex_acceptance.py` Test 8 | **TESTED_SYNTHETIC** |
| **G5. GeoServer 2차** | `backend/app/tile_router.py`, `backend/app/ml/raster_tile_engine.py` | WMS 1.3.0 GetMap, `/v1/lcluc/pixel` | 1차 참조레이어와 2차 예측레이어 네임스페이스 혼동 | `ref_*` vs `pred_*` 레이어 레지스트리 분리 및 `source_kind` 명시 | `tests/test_geoserver_wms_pixel_service.py` | **VERIFIED_REAL** |
| **G6. 변화탐지** | `backend/app/ml/lcluc_unified_analytics.py`, `backend/app/ml/temporal_change_filter.py` | `transitions.tif`, 공통 유효영역 마스크 | 화면 RGB 색상 역추정으로 인한 통계 왜곡, 줌/스와이프 시 면적 수치 변동 | 원본 GeoTIFF 1x1 픽셀 기반 불변 연산, NoData(255) 엄격 배제, 9x9 전이행렬 불변성 보장 | `tests/test_lcluc_unified_analytics.py` (17건 PASS) | **VERIFIED_REAL** |
| **G7. SDSS 화면** | `frontend/src/ModelAnalysisWorkspace.tsx`, `frontend/src/LclucIntegratedWorkspace.tsx` | MapLibre GL WMS 래스터 타일 + 픽셀 팝업 | fBm 프랙털 절차적 캔버스 및 9x9 바둑판 폴리곤 표출 | 실제 GeoServer WMS 래스터 타일 소스 바인딩, 클릭 시 `/v1/lcluc/pixel` 원본 조회 연동 | TypeScript 컴파일 0 오류, E2E 검증 | **VERIFIED_REAL_E2E** |
| **G8. 완료 보고** | `docs/lcluc-map/acceptance-test-results.json`, `docs/understanding/02_LCLUC_ANNUAL_MAP_GEOSERVER.md` | 14대 수용시험 전건 결과서 | 검증 증빙 문서의 단계별 상태 미분리 | 14대 필수 수용시험 자동화, 40건 단위시험 전건 통과 증거 수록 | `pytest` 40건 전건 통과 (4.41s) | **VERIFIED_CORE_SUITE** |

---

## 4. 세부 진입점 및 코드 추적 (Entrypoints & Implementations)

1. **WMS 1.3.0 서비스 및 타일 라우터**:
   - 모듈: `backend/app/tile_router.py`
   - 엔드포인트: `GET /v1/lcluc/wms` (GetCapabilities / GetMap)
   - 래스터 타일 엔진: `backend/app/ml/raster_tile_engine.py`
   - 공인 SLD 규격: `evidence/geoserver/sld/lcluc_discrete_9classes.sld`
2. **공인 1×1 픽셀 검사 API**:
   - 엔드포인트: `GET /v1/lcluc/pixel?lng={lng}&lat={lat}&layer={layer}`
   - 구현 방식: 클릭 좌표 $\to$ 소스 네이티브 CRS Affine 변환 $\to$ 디스크 상 GeoTIFF의 `Window(col, row, 1, 1)` 직접 읽기 (화면 RGB 역추정 원천 배제).
3. **불변 분석 및 전이행렬 엔진**:
   - 모듈: `backend/app/ml/lcluc_unified_analytics.py`
   - 핵심 계약: `DatasetIdentity(dataset_id, version, aoi_id, observation_period)`
   - 산출 함수: `compute_annual_statistics`, `compute_transition_matrix`, `inspect_pixel_at`
4. **프론트엔드 통합 작업공간**:
   - 모듈: `frontend/src/ModelAnalysisWorkspace.tsx`, `frontend/src/LclucIntegratedWorkspace.tsx`
   - 지도 엔진: MapLibre GL JS 래스터 레이어 (`raster-resampling: nearest`)

---

## 5. 결론 및 이행 권고 (Actionable Conclusions)

1. **절차적 캔버스 및 임의 격자 표출 영구 금지**:
   - 프론트엔드는 어떠한 경우에도 임의의 프랙털 노이즈나 사각 바둑판 격자를 실측 토지피복 지도인 것처럼 생성해서는 안 됩니다.
   - 데이터가 없는 연도나 지역은 투명 빈 타일(`EMPTY_TILE_PNG`)과 명시적인 "자료 없음/비교 불가" 안내를 표출해야 합니다.
2. **GeoServer 1차와 2차의 엄격한 역할 분리**:
   - 1차(참조자료 WMS) 통과는 원본 데이터의 GIS 유효성을 입증한 것이며, AI 모델의 학습 완료나 과학적 정확도 확보를 의미하지 않습니다.
   - 2차(예측자료 WMS)는 실제 학습된 모델의 추론 산출물(`prediction_class.tif`)이 물리적으로 존재할 때만 게시 승인되어야 합니다.
3. **후속 감사 문서로의 인계**:
   - 본 AS-IS → TO-BE 분석을 바탕으로 데이터 출처 인벤토리(`data_provenance_inventory.md`) 및 레이어 레지스트리 감사(`layer_registry_audit.md`)로 진입합니다.
