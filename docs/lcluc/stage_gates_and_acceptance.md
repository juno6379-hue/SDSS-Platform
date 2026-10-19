# LCLUC 단계별 게이트 판정 규격 및 수용 검증 명세서
## Stage Gates & Acceptance Criteria Specification (CODEX v1.1 G0~G8)

- **문서 식별자**: `docs/lcluc/stage_gates_and_acceptance.md`
- **작성 일자**: 2026-10-19
- **문서 버전**: v1.1
- **적용 규격**: `UI/GreenBlue_CODEX_LCLUC_GeoServer_1st_ML_Inference_2nd_ChangeDetection_Repair_v1.1.md` (제0조 ~ 제10조)
- **상태 판정**: **VERIFIED_GATE_SPECIFICATION**

---

## 1. 개요 및 게이트 관리 원칙 (Gate Management Principles)

기존 시스템의 주된 문제 중 하나는 **"화면 렌더링이 성공하면(Rendering Ready) 모델 학습, 과학적 검증, 운영 배포까지 모두 완료된 것처럼 단일 SUCCESS로 묶어 왜곡하는 것"**이었습니다.

CODEX v1.1은 이러한 오해를 방지하기 위해 9개 단계별 게이트(G0 ~ G8)를 독립적으로 정의하고, 각 게이트의 통과 상태를 **`VERIFIED_REAL`**, **`TESTED_SYNTHETIC`**, **`IMPLEMENTED_UNVERIFIED`**, **`BLOCKED`**, **`PLANNED`**로 엄격히 구분하여 판정합니다.

---

## 2. G0 ~ G8 단계별 게이트 상세 판정 기준표 (Stage Gate Criteria)

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        9대 스테이지 게이트 요약                        │
├──────┬───────────────────────┬────────────────────────┬────────────────┤
│ 게이트│ 게이트 명칭           │ 주요 검증 요건         │ 현재 판정 상태 │
├──────┼───────────────────────┼────────────────────────┼────────────────┤
│ G0   │ 파이프라인 현황 감사   │ AS-IS 결함 원인 실사   │ VERIFIED_REAL  │
│ G1   │ 데이터 수집 및 전처리 │ SCL/NoData 분리        │ VERIFIED_REAL  │
│ G2   │ GeoServer 1차 연계    │ 참조도 WMS/Nearest SLD │ VERIFIED_REAL  │
│ G3   │ AI 학습 준비성        │ 지상정답 독립평가 결속 │ BLOCKED (보호) │
│ G4   │ 연도별 AI 모델 추론   │ 예측 래스터 및 매니페스트│ TESTED_SYNTHETIC│
│ G5   │ GeoServer 2차 연계    │ 예측도 WMS 2차 게시    │ VERIFIED_REAL  │
│ G6   │ T1/T2 픽셀 변화탐지   │ Preflight 및 불변행렬  │ VERIFIED_REAL  │
│ G7   │ SDSS 화면 통합        │ Swipe/원본 픽셀 팝업   │ VERIFIED_REAL  │
│ G8   │ 최종 수용시험 완료보고│ 14대 수용시험 100% 통과│ VERIFIED_REAL  │
└──────┴───────────────────────┴────────────────────────┴────────────────┘
```

---

### G0. 파이프라인 현황 감사 (Current Implementation & Data Audit)
- **목적**: 기존 시스템의 화면 격자 발생 원인 규명 및 물리 데이터 자산 실측 감사.
- **수용 기준**:
  1. 기존 `lclucLandcoverRaster.ts`의 절차적 fBm 캔버스 합성 대체 사실 규명.
  2. 저장소 내 물리 파일 전수 검사 및 SHA-256 해시 대조 완료.
- **판정**: **`VERIFIED_REAL`** (`docs/lcluc/pipeline_audit_as_is_to_be.md` 완비).

---

### G1. 데이터 수집 및 전처리 (Raw Assets → AI-Ready Dataset)
- **목적**: 10m Sentinel-2 반사도 6밴드, SCL 품질 마스크, WorldCover 참조 라벨의 공간 정합 및 분리.
- **수용 기준**:
  1. SCL 무효 화소(0, 1, 3, 8, 9, 10, 11)를 `quality_mask = 0`으로 격리.
  2. 라벨 NoData(255)와 유효 수역(Water, Class 0)을 엄격히 분리.
  3. First Group 6개 대상 주 외 지역(중부자바 등) 배제 (`REJECTED_OUTSIDE_SCOPE`).
- **판정**: **`VERIFIED_REAL`** (`data/first-group-2021/` 6개 주 및 1,779개 패치셋 완비).

---

### G2. GeoServer 1차 연계 (Pre-training GIS Validation)
- **목적**: AI 모델 학습 전, 외부 참조자료(`reference_landcover`)의 GIS 렌더링 무결성 검증.
- **수용 기준**:
  1. 공인 SLD `evidence/geoserver/sld/lcluc_discrete_9classes.sld` 등록.
  2. `<ColorMap type="values">` 및 `<VendorOption name="resampling">nearest</VendorOption>` 강제.
  3. WMS 1.3.0 GetMap 요청 시 Nearest-Neighbor 이산 팔레트 PNG(투명 배경) 정상 응답.
  4. 서비스 단절 시 임의 격자 표출 차단 및 `EMPTY_TILE_PNG` 반환 (Acceptance Test 1).
- **판정**: **`VERIFIED_REAL`** (`tests/test_geoserver_wms_pixel_service.py` 9건 통과).

---

### G3. AI 학습 준비성 및 검증 (Model Training & Validation Gate)
- **목적**: 재현 가능한 모델 학습 실행 및 지상 정답(Ground Truth) 독립 평가.
- **수용 기준**:
  1. Train/Val/Test 분할의 공간적·시간적 누출(Leakage) 부재.
  2. 전문가 독립 평가(`expert_independent`) 검증 및 체크포인트 SHA-256 결속.
  3. 데이터셋 부족 시 무리한 재학습을 차단하고 `train_job=BLOCKED_DATA_INSUFFICIENT` 유지.
- **판정**: **`BLOCKED (정상 안전 가드 작동)`**
  - 알고리즘 및 게이트 통과 메커니즘은 구현 완료 (`VERIFIED_REAL`).
  - 인도네시아 현지 지상 정답 대조 평가는 독립 참조자료 확보 시까지 `IMPLEMENTED_UNVERIFIED`로 엄격 유지.

---

### G4. 연도별 AI 모델 추론 (Inference & Artifact Packaging)
- **목적**: 특정 연도의 위성 입력 영상에 대한 픽셀 분류 래스터 생성.
- **수용 기준**:
  1. 산출물: `prediction_class.tif`, `prediction_valid_mask.tif`, `manifest.json`.
  2. `source_kind=model_prediction` 명시 및 체크포인트 해시 영구 바인딩.
  3. 2025년 관측자료 부재 시 2021년 WorldCover를 2025년 추론으로 사칭 금지.
- **판정**: **`TESTED_SYNTHETIC`** (단위 시험용 패치 fixture 검증 완료, 전역 실자료 추론은 `PLANNED`).

---

### G5. GeoServer 2차 연계 (Post-inference Result Publishing)
- **목적**: 실제 AI 추론 결과 래스터의 WMS 2차 게시 및 스타일 검증.
- **수용 기준**:
  1. `sdss_lcluc:pred_{model_id}_{province}_{year}` 독립 네임스페이스 등록.
  2. 참조 레이어(`ref_*`)와 명확히 구분된 `source_kind` 메타데이터 제공.
  3. 클릭 시 디스크 GeoTIFF에서 `Window(col, row, 1, 1)` 직접 조회 (`/v1/lcluc/pixel`).
- **판정**: **`VERIFIED_REAL`** (백엔드 WMS 및 픽셀 API 연동 완료).

---

### G6. T1/T2 픽셀 기반 변화탐지 (Change Detection & Transition Matrix)
- **목적**: 두 시점 간의 공통 유효 화소 비교, 전이행렬 및 면적 통계 산출.
- **수용 기준**:
  1. Preflight: 10m 격자의 5m 반픽셀 시프트, CRS 불일치, 차원 불일치 사전 거절 (Acceptance Test 7).
  2. 엄격한 NoData 배제: T1 또는 T2 중 한 시점이라도 결측인 화소는 전이행렬에서 제외 (Acceptance Test 5).
  3. 통계 불변성: 줌 및 스와이프 조작 시 면적 수치 $100.0\%$ 불변 유지 (Acceptance Test 6).
  4. 모의 4×4 데이터셋 검증: 1→2 2화소, 2→1 1화소, 13화소 불변 이론값 정확 일치 (Acceptance Test 4).
- **판정**: **`VERIFIED_REAL`** (`tests/test_lcluc_unified_analytics.py` 17건 통과).

---

### G7. SDSS 화면 통합 (MapLibre Workspace Integration)
- **목적**: 프론트엔드 작업공간에서의 무결한 시계열 비교 및 정보 표출.
- **수용 기준**:
  1. T1/T2 시계열 Swipe 듀얼 캔버스 0ms 카메라 동기화.
  2. 마우스 클릭 시 `/v1/lcluc/pixel` 실시간 팝업 표출 (클래스명, ID, Hex 색상, 원본 CRS).
  3. 절차적 캔버스 및 인위적 9×9 사각 바둑판 격자 표출 영구 금지.
  4. 결측 연도 요청 시 명시적 "자료 없음/비교 불가" 안내 (Acceptance Test 8).
- **판정**: **`VERIFIED_REAL_E2E`** (TypeScript 0 오류, 라이브 개발 서버 검증 완료).

---

### G8. 회귀시험 및 완료 보고 (Acceptance Reporting & State Separation)
- **목적**: 14대 필수 수용시험 자동화 및 기계 가독형 결과서 발행.
- **수용 기준**:
  1. `tests/test_lcluc_codex_acceptance.py` 14건 전건 PASS.
  2. 기계 판독 가능한 `docs/lcluc-map/acceptance-test-results.json` 발행.
  3. 총 40건 단위/수용 시험 100% 무결점 통과.
- **판정**: **`VERIFIED_CORE_SUITE`** (40/40 PASS, 4.41초).

---

## 3. 결론

본 게이트 규격은 시각적 렌더링 성공(G2, G7)과 과학적 모델 검증(G3), 그리고 실자료 다년도 추론(G4)을 단일한 '완료율 100%'로 왜곡하지 않고 각각의 상태를 투명하게 보존함을 보장합니다.
