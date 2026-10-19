# Codex 개발·감사·수정 명령서
## LCLUC 데이터 파이프라인 순서 재정렬 — GeoServer 1차 → AI 학습·검증 → 추론 → GeoServer 2차 → 변화탐지

- 버전: v1.1 / 작성: 2026-10-19
- 프로젝트: BIG Climate Action / GreenBlue SDSS-Platform / GeoAI Toolbox → LCLUC Workspace
- 문서 성격: 실행 가능한 **기존 저장소 점검·코드 수정·검증 명령서**. 별도의 화면 디자인 요청이나 신규 프로젝트 재구축 지시가 아니다.
- 선행 참조(저장소에 존재하면 확인): `GreenBlue_CODEX_LCLUC_Annual_Map_GeoServer_v1.0.md`, `GreenBlue_CODEX_Master_Prompt_GMAIS_Integrated_Platform_v1.0.md`, GMAIS v0.2 기계규격, TECH-4, 현재 Repository README·테스트·데이터 카탈로그
- 실제 계약/승인 규격 및 현행 코드와 충돌하면 충돌을 기록하고 근거 없는 호환성 파괴 변경을 하지 말 것.

---

## 0. 최우선 실행 명령

당신은 기존 SDSS-Platform의 데이터 엔지니어, GIS/GeoServer 엔지니어, ML 엔지니어, MLOps·Backend·Frontend 개발자, 통합 QA 책임자로 동작한다.

**사용자 보고에 따르면 GeoServer 레이어 통합과 변화탐지 분석 기능은 현재 구현돼 있지만, 변화탐지 화면에서 실제 픽셀 단위 토지피복 분류 지도가 보이지 않았다.** 이 진술을 현황 감사의 출발점으로 삼되, 원본 파일·현재 코드·API·실제 화면/네트워크 증거 없이 구현 완료로 확정하지 마라.

### 수행 목표

기존 기능과 데이터·실행기록을 최대한 보존하면서, 실데이터를 사용하는 LCLUC 파이프라인을 다음 단계로 재정렬하고, 코드·API·상태 관리·화면·자동시험까지 실제 수정한다.

```text
G0. 현재 구현·데이터·GeoServer 상태 감사
         ↓
G1. 데이터 수집·전처리 및 검증 (Raw → AI-ready)
         ↓
G2. GeoServer 1차 연계 (Pre-training GIS Validation)
    - 원본 영상/참조 토지피복도/품질마스크의 정확한 공간표시
    - CRS·Affine·Pixel Alignment·클래스·NoData 검증
         ↓
G3. AI 학습 준비성 → 학습 → 검증 (Model Training & Validation)
         ↓
G4. 연도별 AI 추론 (Inference)
    - 모델 예측 클래스 래스터 + 품질·출처·버전
         ↓
G5. GeoServer 2차 연계 (Post-inference Result Publishing)
    - 실제 모델 예측 토지피복도 게시 / 픽셀 질의 / 스타일 검증
         ↓
G6. T1/T2 픽셀 기반 변화탐지 (Change Detection)
    - 공통격자·공통유효영역·전이행렬·변화지도·면적통계
    - 변화 결과 래스터/벡터는 2차 지도 서비스 계층에 추가 게시
         ↓
G7. MapLibre SDSS Workspace (Swipe/Animate/Charts/Pixel Popup/Report)
         ↓
G8. 회귀시험·과학검증·운영승인 상태 분리 및 완료 보고
```

**실행 순서와 기능 완성도는 별개다.** 실제 학습데이터가 부족해 G3가 차단되더라도 G2의 실자료 지도 게시와 G3~G7의 단위·계약시험용 구현은 진행할 수 있다. 그러나 해당 단계의 **실자료 E2E 성공**은 `BLOCKED`로 기록한다. 합성 데이터·시각 효과·기존 Draft 모델을 실제 검증된 2020/2025 AI 결과로 표기하지 마라.

**GeoServer를 다시 처음부터 구축하지 마라.** 이미 통합한 서비스가 있으면 재사용하고, 부족한 연계·자료 게시·메타데이터·테스트만 보완한다.

---

## 1. 먼저 AS-IS를 코드로 증명하라 — 수정 이전에 수행

1. Repository의 브랜치·commit SHA·`git status`, 실행·테스트 가능한 환경, Docker/Compose/K8s 구성과 설치 GeoServer 버전을 기록한다.
2. 데이터 수집/STAC, Raw Store, 전처리, QC, Dataset Registry, 학습 Ready Gate, Train/Evaluate, Inference, Change Detection, Result Registry, GeoServer Publish, MapLibre UI의 **실제 진입점·함수·잡·API**를 추적한다.
3. GeoServer의 존재만 확인하지 말고 실제 `Workspace → DataStore/CoverageStore → Layer → Style → WMS GetCapabilities → GetMap` 경로를 확인한다. 자격증명은 문서나 로그에 노출하지 않는다.
4. 기존 T1/T2의 래스터 소스 URL과 응답이 **실제 GeoTIFF/COG 기반 서비스 타일인지**, 큰 사각 격자·Canvas/WebGL 절차적 생성·정적 PNG·Mock Tile인지 구분한다. MapLibre `raster` 타입은 실자료 사용의 증거가 아니다.
5. '9개 클래스' 범례와 실제 데이터의 클래스 ID 정의, GeoServer SLD/스타일, 팝업 픽셀값, 면적·전이행렬 출처를 각각 추적한다.
6. 기존 Change Detection 코드의 입력이 ① 실제 연도별 정수 분류 래스터 ② 외부 참조분류도 ③ 브라우저 RGB/시각적 이미지 ④ 임의 합성 값 중 무엇인지 확인한다.
7. 기존 결과와 시험을 파괴하거나 조용히 변경하지 말고, 오류 재현용 스크린샷·네트워크 요청/응답·관련 파일 경로·실행 명령을 보관한다.
8. 과거 2026-10-16 보고에는 Banten/West Java의 6밴드+WorldCover 소규모 패치 2쌍, 학습 Train=0·Validation=1·Test=1, `ready_for_training=false`가 기록돼 있다. 이를 **과거 보고 스냅샷**으로만 취급하고 최신 실제 원장과 비교한다. 단일 장소·시점만 확보한 경우 두 시점 변화를 검증했다고 하지 마라.

**최소 AS-IS→TO-BE 테이블**

| 단계 | 현재 파일/함수·API | 실제 데이터 연결 | 지금의 문제 | 수정 항목 | 검사 방법 | 판정 |
|---|---|---|---|---|---|---|
| 수집 | ... | ... | ... | ... | ... | PASS/FAIL/BLOCKED |
| 전처리 | ... | ... | ... | ... | ... | ... |
| GeoServer 1차 | ... | ... | ... | ... | ... | ... |
| 학습·검증 | ... | ... | ... | ... | ... | ... |
| 추론 | ... | ... | ... | ... | ... | ... |
| GeoServer 2차 | ... | ... | ... | ... | ... | ... |
| 변화탐지 | ... | ... | ... | ... | ... | ... |
| SDSS | ... | ... | ... | ... | ... | ... |

**필수 작성:** `docs/lcluc/pipeline_audit_as_is_to_be.md`, `docs/lcluc/layer_registry_audit.md`, `docs/lcluc/data_provenance_inventory.md`.

---

## 2. G1 — 데이터 수집·전처리의 산출물과 품질 Gate를 명확히 하라

실제 Sentinel-2 B02/B03/B04/B08/B11/B12 + SCL(Level-2A) + WorldCover 참조라벨 또는 합법적으로 확보한 공식 자료를 데이터셋 출처별로 관리하라.

**검증 항목**
- 원본 URL/데이터 자산 ID/라이선스/관측일·기간/센서·처리레벨/해시/원본 보관 위치.
- 이미지 밴드 순서와 수, 손상/누락/NoData, 반사도 변환 계수 및 적용 여부(원본 DN과 실제 반사도 구분).
- CRS, width/height, bounds, pixel size, affine transform, pixel alignment, 유효 footprint.
- B11/B12와 10m 밴드 등 서로 다른 원해상도에 대한 명시적인 재표본화 정책. 연속 영상은 검토된 bilinear 등, **SCL/WorldCover 범주형 자료는 nearest neighbor** 사용. 20m → 10m는 신규 관측정보 생성이 아님.
- 구름·구름 그림자·결함 등 SCL 상태에 따른 `valid_mask`/`quality_mask` 생성, 마스크 정책·버전·적용시점 명시.
- WorldCover 등 참조 분류 자료의 실제 연도와 Sentinel-2 관측시점 차이 및 라벨 불확실성 기록.
- 원본 클래스 수와 프로젝트 목표 9개 클래스 간 mapping 버전. 9개로 변환이 정당화되지 않으면 자동 변환·누락·가짜 클래스를 만들지 말 것.
- AOI가 실제 데이터 범위를 초과할 경우 `valid_footprint`만 게시하고 나머지는 NoData 처리.

산출물은 `RawAssets`, `AIReadyDataset`, `ReferenceLandcover`, `QualityMask`, `DatasetManifest`로 분리하라. **AI-ready와 '학습 가능한 충분한 데이터'는 별개 상태**다.

학습 준비성은 기존의 실제 문턱값 및 검증 규칙을 유지하되, 부족한 데이터는 부족하다고 판정한다. 기술 검토 없이 준비성 flag나 최소 패치 수를 완화하지 마라.

---

## 3. G2 — GeoServer 1차 연계 (AI 학습 이전)

이 단계는 **학습 전 데이터 검증용 GIS 서비스**다. 모델의 실제 예측결과가 없어도 구현할 수 있어야 한다.

### 게시할 실제 레이어
1. `reference_landcover`: WorldCover 등 외부 참조 **클래스 정수 래스터** (실제 있는 연도·위치만).
2. `quality_mask` 또는 `scl`: SCL 상태·분석 가능한 픽셀 영역.
3. `imagery_preview`: 실제 Sentinel-2 영상의 올바른 RGB/false-color 시각화. **분류도와 혼동하지 않게 다른 데이터 유형**으로 표기.
4. 선택적으로 `study_area`/`valid_footprint`: 분석경계·실제 자료 유효범위.

### 반드시 구현·검증할 사항
- 파일을 GeoServer CoverageStore/레이어에 등록하고, GetCapabilities/GetMap/픽셀 조회 등 실제 응답을 확인한다. 기존 REST 및 WMS 설정 재사용.
- 단일밴드 정수 클래스 값 `class_id` → SLD `RasterSymbolizer`의 이산 `ColorMap` → UI 공통 범례의 ID·명칭·색상을 연결한다.
- 토지피복 범주형 지도의 원본 재표본화 및 WMS 렌더링에서 **nearest neighbor**를 적용한다. 세밀한 산림 경계가 큰 관리용 격자만으로 대체되지 않아야 한다.
- NoData 및 마스크 제외 영역을 지도에서 명확히 처리한다. 마스크 표시/해제 토글을 제공한다.
- 원본 참조자료와 영상 사이의 CRS·Affine·Grid·범위·픽셀 샘플이 실제로 정합되었는지 수치·지도 양측에서 확인한다. GeoServer 표시만으로 수치 정합 PASS 처리하지 않는다.
- 화면 표기: `분류 종류: 외부 참조`, `참조 연도`, `관측기간`, `자료 유효범위`, `원본 출처`.
- 실제 레이어가 없는 연도는 WMS 이미지를 복제하거나 가장 가까운 연도로 자동 대체하지 않는다.

**1차 Gate 합격**: (a) 실제 참조 래스터 파일과 checksum 확인 (b) 동일 AOI WMS 지도 응답 (c) 표본 픽셀의 원본 class_id와 레이어 조회 일치 (d) 클래스 범례·NoData·품질마스크 정합 (e) E2E 화면에서 실제 지표 분포 확인. 단, 이 통과를 모델 학습·검증 완료라고 하지 마라.

---

## 4. G3 — AI 학습 준비성 → 학습 → 검증

**GeoServer 1차 통과 후 실제 학습 Ready Gate를 검사하되, 지도 게시 성공이 학습 가능 상태를 자동으로 만들지 않도록 하라.**

### 입력 및 실행
- `AIReadyDataset + ReferenceLandcover + ValidMask + ClassMapping`의 immutable 버전을 학습작업에 전달.
- 학습/검증/시험의 지역·시점 누출을 점검하고, train/val/test 샘플 수와 클래스별 면적/분포·부족 클래스를 보고.
- 현행 모델 구조·checkpoint·실험 설정을 임의 리셋하지 않는다. 구현/테스트 목적의 합성 fixture는 별도 namespace.
- 승인된 준비 기준을 충족하지 못하면 `train_job=BLOCKED_DATA_INSUFFICIENT`로 유지한다. Draft 추론 테스트가 가능하더라도 과학적 성능을 확보한 것으로 표기하지 않는다.
- 충족 시 재현 가능한 학습(데이터/모델/코드/seed/하이퍼파라미터 버전)과 `ModelRegistry`/실험 로그 연결.
- 검증은 OA, 클래스별 Precision/Recall/F1/IoU, mIoU, confusion matrix, 누락 클래스, 공간·시간 일반화, 독립 검증, 모델카드·한계를 포함한다.
- 실제 미검증 또는 불충분한 모델은 `Draft/Unvalidated` 유지. 과학검증, 지도 렌더링, 통합계약시험, 운영승인을 단일 `SUCCESS`로 합치지 말 것.

**중요:** G3가 BLOCKED이면 무리해서 학습을 실행하거나 합성 패치를 실제 학습 데이터로 승격하지 않는다. 코드·상태/API·계약시험을 계속 구축하고 G4~G7의 **실과학 데이터 E2E**는 별도 차단 처리하라.

---

## 5. G4 — 연도별 실제 AI 추론

모델 실행이 허용된 상태에서만 승인된 입력 범위에 추론 작업을 실행한다. 모델이 Draft인 경우 정책상 허용되는 개발/Staging 범위에서만 `Draft prediction`으로 표시할 수 있으며 검증·승인된 예측 결과와 구분한다.

- 해당 연도의 실제 입력 영상과 모델·클래스·전처리 버전을 고정한다.
- patch prediction → 동일 격자 mosaic → 경계/중복 처리 → `class_id` 정수형 래스터 생성.
- 결과 파일: 예 `prediction_class.tif` (GeoTIFF/COG), `prediction_valid_mask.tif`, 필요 시 `class_probability.tif`, `manifest.json`, `quality_report.json`.
- `source_kind=model_prediction`, 실제 관측기간, `model_id/version`, `dataset_id/version`, `class_schema_id/version`, CRS/affine/resolution/extent, NoData, checksum, `scientific_validation_state`, `approval_state` 포함.
- 2020년/2025년 모델 입력 또는 유효한 실제 출력이 없으면 해당 연도 예측 결과를 새로 만들지 않는다. 다른 연도의 WorldCover를 '2025 AI 추론'으로 이름만 바꾸지 않는다.
- 새 데이터를 덮어쓰지 않고 버전별 불변 자산으로 관리한다.

**G4 합격**: 실제 허용된 모델과 자료의 추론 실행기록·분류 래스터·메타데이터·검사 로그. 데이터가 없으면 코드의 synthetic fixture 테스트와 실제 G4 합격을 구별한다.

---

## 6. G5 — GeoServer 2차 연계 (AI 추론 이후)

**G2와 별도의 GeoServer 서버를 만들 필요는 없다. 같은 GIS 서비스의 '두 번째 게시 단계'를 뜻한다.**

1. G4의 검증 가능한 `model_prediction` 정수형 raster를 **새로운 Result/Layer 버전**으로 게시한다.
2. `reference_landcover` 레이어와 혼동되지 않게 source_kind별 layer namespace·스타일·팝업 설명·레지스트리를 구분한다.
3. 동일 9개 class schema/version에 대해서는 연도별 공통 SLD 색상·명칭 유지. 해석이 다른 원천 클래스의 색상을 억지로 맞춰 비교하지 않는다.
4. 초기에는 실제 개별 연도별 레이어를 이용한다. 연도·타일량이 증가한 뒤 ImageMosaic + `TIME`를 도입해도 된다. `TIME` 미지정/없는 연도를 최신 연도로 자동 대체하지 않는다.
5. Backend `LayerRegistry`가 `result_id → layer_id → coverage_store/style/time/source/version/valid_footprint`를 추적한다.
6. T1/T2 MapLibre Layer는 실제 GeoServer WMS/WMTS를 참조하고, Zoom/Pan/Swipe 시 같은 지리 위치를 표시한다. 큰 격자·절차적 산림 모양·붉은 전선 패턴으로 실제 분류를 대체하지 않는다.
7. Pixel popup은 화면 RGB 역추정이 아닌 서버/원본 클래스 조회 결과 사용. 고도는 별도 DEM이 있을 때만 표시한다.
8. 통계·분류 데이터의 계산용 값은 GeoServer에서 반환한 색상 PNG가 아니라 **분류 원본 class_id 래스터**를 사용한다.
9. 게시 전후 허가·권한 및 운영승인 상태를 검사한다. Draft는 허용된 테스트 화면에서만 노출하며 운영 게시로 자동 승격하지 않는다.

**2차 Gate 합격**: 원본 추론 래스터 ↔ GeoServer GetMap/픽셀 조회 ↔ MapLibre 표시가 같은 지리범위·클래스·결과 버전에 연결된 것이 증명돼야 한다.

---

## 7. G6 — 기존 변화탐지 코드를 보존하면서 '진짜 T1/T2 픽셀 비교'로 수정

**변화탐지 알고리즘을 처음부터 다시 만들지 말고, 기존 Change Detection 기능의 입력·검사·산출물·표시를 감사한 후 최소 변경으로 수정하라.**

### 필수 Preflight (분석 전 자동 차단)
- T1/T2에 실제 존재하는 시점별 분류자료가 각각 등록되어 있는가?
- 사용자가 선택한 AOI/연도가 두 레이어의 실제 footprint에 포함되는가? 유효 중첩영역이 충분한가?
- 비교 목적에 적합한 동일/호환 class schema 및 정당한 source-kind/제품/모델 차이 처리 정책인가?
- CRS, affine, pixel grid, 해상도, NoData, quality mask, 클래스 대응을 검증했는가? 필요한 경우 명시적으로 하나의 **analysis grid**로 정합했는가?
- 참조지도↔참조지도 변화인지, 모델예측↔모델예측 변화인지, 서로 다른 원천을 비교한 실험인지 표시했는가?
- 자료가 없으면 `INSUFFICIENT_TEMPORAL_DATA`, 미정합이면 `GRID_MISALIGNMENT`, 분류체계 불일치는 `CLASS_SCHEMA_MISMATCH`, 중첩 없음은 `NO_COMMON_VALID_FOOTPRINT` 등 코드로 중단하라.

### 분석 규칙
- 같은 유효 픽셀 `(r,c)`에서 `from_class=T1[r,c]`, `to_class=T2[r,c]` 비교.
- `valid_common = valid_T1 & valid_T2 & AOI_mask`를 적용. 구름·NoData·결측은 **변화 없음**으로 세지 않는다.
- 전이행렬 행=T1, 열=T2. 변화픽셀 수, 클래스별 총감소·총증가·순변화·전이면적·공통유효면적 산출.
- 면적은 면적 측정에 맞는 CRS/측지 방법·AOI 경계 픽셀 정책을 사용. EPSG:3857 픽셀 면적을 그대로 정책 면적이라고 하지 않는다.
- `change_class.tif`, `change_pair.tif` 또는 검증된 전이 식별값 래스터, `change_valid_mask.tif`, `transition_matrix.json`, `area_statistics.json`, `comparison_manifest.json` 등을 기존 schema와 조화시켜 생성.
- 변화 마스크/핫스팟은 원본 비교에 따라 생성해 GeoServer의 **2차 결과 서비스 계층**에 추가 게시한다. T2 시가지 전체를 산림→시가지 변화지도라고 표기하지 않는다.
- 원인 단정(예: 산림 감소=벌채)은 별도 증거가 없으면 하지 않는다.
- 기존 분석 로직에 이미 올바른 부분이 있으면 보존하고 그 코드에 회귀시험을 추가한다.

**한 시점의 참조 라벨만 존재하면:** 진짜 두 시점 변화분석의 실제 완료는 BLOCKED. UI상 기존 변경분석 컴포넌트를 렌더링할 수 있어도 분석 성공 배지·면적·변화행렬 실측값을 표시하면 안 된다.

---

## 8. G7 — 기존 GeoAI Toolbox / LCLUC UI 연결 방식 수정

기존 7개 상위 메뉴 및 `GeoAI Toolbox → LCLUC Workspace` 구조를 유지하고, 단계별 화면과 연차 비교 화면을 일관되게 연결한다.

### 권장 내부 탭 구조(기존 메뉴명을 우선 재사용)
1. `데이터 수집`: 원본·출처·관측시기·AOI·다운로드/QC 상태.
2. `전처리·품질`: CRS/Affine/해상도/정합 PASS·FAIL, SCL 마스크, 원본 vs 정합 영상.
3. `GeoServer 1차: 참조지도`: 실제 WorldCover 등 출처명·년도·범례·픽셀 조회.
4. `AI 학습·검증`: Dataset Readiness, train/val/test, 학습·지표·Model Card·차단 원인.
5. `추론·분류결과`: 연도별 실제 모델 예측 자산, 스테이징 상태·품질.
6. `GeoServer 2차: 예측지도`: 예측 결과 래스터와 Layer Registry, 픽셀 클래스·스타일 검증.
7. `변화탐지·지도분석`: T1/T2 선택, Swipe, Animate, 변화만 보기, 팝업, 통계·전이행렬.

프로젝트 기존 메뉴/탭과 충돌하면 새 메뉴를 중복 생성하지 말고 **동일한 7개 논리 단계를 기존 탭/서브패널에 매핑**하라.

### UI 수용조건
- 선택 시점의 라벨/지도타일/범례/그래프/팝업 모두 `comparison_id`와 `result_id/version`으로 정합.
- 비교 기본모드: `T1 분류도 ↔ T2 분류도`; 보조: `원영상 ↔ 해당 시점 참조/예측도`; 선택: `변화만 보기`.
- Swipe가 이동해도 데이터 자체가 바뀌는 것이 아니라 **같은 좌표에서 어느 시점 레이어를 보여줄지만 바뀜**.
- 사용가능 연도 목록은 Registry에서 조회하고 없는 연도는 `미확보/미생성`으로 명확히 안내.
- 9클래스 개별 체크·색상·투명도는 원본 class_id에 연결. GeoServer SLD나 타일 스타일의 클래스를 임의 RGB 픽셀 조작으로 흉내 내지 않는다.
- 모든 시험용 합성지도에는 눈에 띄는 `TEST DATA` 표시. '본 지역 2020→2025 실제 변화'로 오인되지 않도록 할 것.
- 큰 사각형 패치/타일 격자는 일반 사용자 화면에서 기본 숨김; 개발자 디버그 토글로만 표시.
- 마스크된 픽셀 또는 T1/T2 한쪽 데이터가 없을 때는 팝업에서 `비교 불가`, 면적통계 제외 사유 표시.
- First Group 6개 주(South Sulawesi, Gorontalo, Southeast Sulawesi, Banten, West Java, East Java)로 초기 실증지역 한정. 실제 256×256 패치를 주 전체의 완료 자료로 표시하지 않음.

---

## 9. 서비스·Job 오케스트레이션 및 게시 상태 관리

기존 GMAIS의 Agent/Job/Result API 계약을 조사하고 **가능한 한 기존 경로와 schema를 유지**한다. 필요 시 새 API는 기존 버전과 호환되도록 추가한다.

### 권장 상태 흐름 (설계 의도)
```text
DATA:        raw_registered → preprocessed → qc_passed → ai_ready
GIS_1:       reference_layer_registered → reference_layer_verified
ML:          readiness_checked → training → validated_or_draft
INFERENCE:   inference_succeeded → prediction_artifact_validated
GIS_2:       prediction_layer_registered → prediction_layer_verified
CHANGE:      preflight_passed → comparison_succeeded → change_layer_verified
UI:          results_synchronized → map_and_statistics_verified
```

이 상태는 **서로 다른 축으로 관리**한다. `dataset_ready`, `map_render_ready`, `model_scientifically_validated`, `prediction_available`, `change_analysis_available`, `published_to_production`을 하나의 '완료율 100%'로 합치지 말 것.

- 참조지도 열람은 학습 차단 여부와 독립적으로 허용될 수 있다.
- 실제 예측지도 2차 게시에는 적어도 원본 추론 아티팩트·메타데이터·접근권한·환경별 게시정책이 필요하다.
- 실제 두 시점 변화분석 완료에는 유효한 서로 다른 T1/T2 자료와 Preflight 통과가 필요하다.
- 작업이 실패했는데 GeoServer에 이전 결과가 남아 있을 경우 최신 성공 버전으로 자동 갈아치우지 않고 상태·버전을 표시한다.
- 비동기 작업 중 중복 요청·Retry·권한·캐시·반쯤 게시된 레이어 노출을 차단하고 등록 스크립트를 idempotent하게 한다.

---

## 10. 자동시험 및 사람이 보는 수용시험 (반드시 실행)

### A. 작은 결정적 fixture 기반 회귀시험 — 실제 분석 증거와 구분
1. 알려진 4×4 또는 16×16 정수 클래스 지도 T1/T2를 만들고 `1→2` 전이 2픽셀, `2→1` 전이 1픽셀 등 기대값 검증.
2. NoData/클라우드 마스크 픽셀을 변화 면적에서 제외하는지 검증.
3. T1/T2 affine에 반픽셀 오차를 주면 정합 검사 실패·명시적 재정합/차단을 검증.
4. 분류 래스터 nearest 사용 시 존재하지 않는 새 class_id가 나오지 않는지 검증.
5. SLD class_id-범례 색상 일치, 클래스 필터·NoData·투명도 검증.
6. GeoServer 레이어 등록 성공만이 아니라 WMS GetMap·실제 픽셀 조회·MapLibre 화면까지 확인.
7. 사용가능 연도가 2021 하나뿐일 때 2020/2025를 선택하면 `미확보` 표시하고 실제 변화분석을 실행하지 않는지 검증.
8. GeoServer를 중단하거나 레이어를 삭제했을 때 UI가 임의 형태학적 패턴/격자/과거 타일로 성공처럼 표시하지 않는지 검증.
9. 지도 확대/Swipe 위치 변경만으로 동일 비교조건의 통계가 바뀌지 않는지 검증.
10. model readiness가 false일 때 정식 학습을 차단하되 참조지도 미리보기는 허용하는지 검증.
11. GeoServer 2차 결과는 **실제 추론 아티팩트 참조가 없으면 게시 성공 불가**인지 검증.
12. 변경된 클래스 체계·모델 버전·AOI·시간·유효마스크에서 잘못된 캐시 결과가 재사용되지 않는지 검증.
13. Stage/Draft 결과가 Production 승인으로 승격되지 않고, 합성자료가 실제 성능지표에 편입되지 않는지 검증.
14. 원본 T1/T2 픽셀값과 팝업의 두 클래스, 전이행렬의 관련 카운트가 일치하는지 검증.

### B. 실제 확보자료 기반 검사 — 실행 가능 범위만
- 최소 한 개의 실제 Banten 또는 West Java 원본+WorldCover+SCL 패치로 **G2 실자료 GeoServer 지도 게시**를 재현해라.
- 같은 지점 표본 좌표에서 원본 클래스값 ↔ GeoServer/백엔드 픽셀 질의 ↔ 지도 범례 일치를 근거자료로 제시하라.
- 실제 모델 체크포인트·가용연도·두 시점 영상·충분한 검증자료가 없으면 G3~G7 해당 실데이터 시험은 `NOT_RUN/BLOCKED`로 기록하라.
- 실자료 두 연도와 검증된 예측이 존재하면 별도의 한 AOI에서 GeoServer 2차 → 변화분석 → UI 전체 E2E를 수행하라.
- 기존 107 tests 통과 등 과거 로그 숫자를 최신 테스트 결과로 복사하지 말 것.

### C. 브라우저/시각 수용시험
- 전처리 화면에서 SCL(구름·그림자), 참조 토지피복도, 위성영상의 위치 일치.
- 정상 실제 분류 데이터의 산림/농경지/시가지/수역 경계가 픽셀 분포로 표시되고 **큰 사각 격자만 존재하지 않음**.
- T1 및 T2 동일 중심/확대/회전/뷰포트 유지, Swipe 0/50/100% 및 Resize에서 위치 일치.
- 서로 다른 연도 두 데이터가 실제로 없으면 비교할 수 없다는 메시지.
- 픽셀 팝업은 반환 데이터 종류·시점·좌표·class ID·품질·출처 표시.
- 면적·전이행렬·그래프는 동일 비교 ID에 연결; 연도 전환 시 이전 값이 남지 않음.

---

## 11. 권장 구현/문서 산출물

기존 Repository 경로·코딩규약을 우선하고 아래 파일명은 권장 예시다.

```text
docs/lcluc/
  pipeline_audit_as_is_to_be.md
  data_provenance_inventory.md
  layer_registry_audit.md
  pipeline_dependency_graph.md
  stage_gates_and_acceptance.md
  geoserver_first_second_publish_guide.md
  lcluc_pixel_map_change_e2e_test_report.md
  open_issues_and_blockers.md

src/.../ (현재 구조에 맞게 수정)
  preprocessing / qc / class_mapping / dataset_manifest
  gis/reference_layer_publisher / prediction_layer_publisher
  gis/layer_registry / geoserver_client / style_definition
  ml/train_readiness / training / validation / inference
  change/preflight / pixel_change / statistics
  api/lcluc_results / pixel_query / comparison
  ui/lcluc_workspace / swipe / class_legend / status

tests/ (기존 규칙에 맞게 추가)
  test_preprocess_geospatial_alignment
  test_geoserver_reference_publish
  test_training_readiness_gate
  test_inference_prediction_manifest
  test_geoserver_prediction_publish
  test_change_detection_common_valid_mask
  test_t1_t2_pixel_provenance
  test_lcluc_swipe_real_layers
```

새 파일을 무조건 여러 개 만들지 말고 **기존 모듈이 이미 수행하는 기능은 최소 변경으로 재사용**하라. GeoServer REST admin credential은 프런트에 노출하거나 Git에 커밋하지 않는다.

---

## 12. 최종 보고 양식과 중단 규칙

개발 보고를 다음 구조로 제출하라.

### 12.1 전체 단계별 완료표

| 단계 | 코드 구현 | 계약/fixture 시험 | 실제 입력 데이터 | 실자료 검증 | 장애·차단 사유 | 근거 경로 |
|---|---|---|---|---|---|---|
| 수집·전처리 | | | | | | |
| GeoServer 1차 | | | | | | |
| AI 학습·검증 | | | | | | |
| AI 추론 | | | | | | |
| GeoServer 2차 | | | | | | |
| 변화탐지 분석 | | | | | | |
| SDSS Swipe/Animate | | | | | | |

### 12.2 구체적 증거
1. 변경된 파일/함수/API/GeoServer Layer와 역할, Git diff 요약.
2. 수정 전 T1/T2가 격자로 나타났던 **정확한 원인** (확인하지 못하면 추정과 사실 구분).
3. GeoServer 1차의 실제 입력 파일·원본 해시, WMS 요청, 지도 스크린샷, 클래스 픽셀 대응표.
4. 학습 준비성 데이터 수와 판정, 실제 실행한 학습·검증 또는 정식 차단 원인.
5. GeoServer 2차의 실제 `prediction.tif` 추론 실행ID 및 결과ID (미존재면 `미완료`).
6. 변화분석의 실제 두 입력 버전·공통유효영역·전이행렬 근거 또는 `BLOCKED` 이유.
7. 프런트의 실제 Network 요청과 같은 `layer/result/comparison_id` 연결.
8. 변경 후 통과·실패 테스트 수, 실행 명령, 성능·보안 이슈, 미검증 사항.
9. 다음 단계 실행에 필요한 **실제 데이터·사람의 승인·인프라 의존성**.

### 12.3 하지 말아야 할 일
- 결과가 없어도 지도에 붉은 산림손실 경계·임의 패턴을 생성하여 실측 변화처럼 표시하지 않는다.
- 첫 단계 참조지도 게시를 `AI 학습 성공`, `AI 추론 완료` 또는 `변화탐지 검증 완료`로 보고하지 않는다.
- 고품질 화면·자동시험만으로 과학적 정확도 또는 운영 승인 완료라고 선언하지 않는다.
- 과거 Draft 예측(단일 클래스 붕괴 등)을 검증된 실측 자료로 승격하지 않는다.
- 실제 주 전체 분석이 아닌 소규모 패치를 6개 주 전체 결과처럼 표시하지 않는다.
- 사용자 확인 없이 데이터 원장·학습 체크포인트·모델 Registry·기존 DB 스키마를 파괴적으로 초기화하지 않는다.
- 사용 승인 없는 대규모 원격 다운로드·유료 인프라 생성·운영환경 변경을 하지 않는다.

---

## 13. 즉시 실행 지시

1. **G0 감사를 시작하고**, 현재 구현의 실제 Stage와 데이터 출처를 근거와 함께 문서화하라.
2. 이미 통합된 GeoServer 자원을 재사용해 **G1 → G2(학습 전 참조자료 지도)**의 최소 실제 데이터 경로부터 검증하라.
3. 기존 ML 학습·검증·추론 코드를 점검하여 **G2 → G3 → G4 → G5(추론 후 예측지도)** 의존성과 상태 Gate를 수정하라.
4. 기존 변화탐지 기능을 실제 T1/T2 원본 분류 픽셀과 연결하도록 **G5 → G6 → G7**을 수정하고 회귀시험하라.
5. 실제 데이터가 없는 단계는 BLOCKED로 표시하되 fixture/계약시험 구현과 실제 데이터 E2E 완료를 구분해 보고하라.
6. 코드·테스트·근거 보고서까지 작성하라. **문서만 작성하고 종료하지 마라.**

**최종 성공 판단:** '실제 한 시점 참조 분류도'의 GeoServer 1차 검증 성공과 '실제 AI 추론 두 시점'의 GeoServer 2차·변화탐지 성공은 전혀 다른 게이트다. 각 게이트의 근거를 보여주어야 한다.
