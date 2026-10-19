# 335. 6-밴드 전체 물리 반사도(BOA) 대기 보정 배치 감사 및 LCLUC 왜곡 방지 규격

상태: **VERIFIED_REAL** (1단계 적격 패치 1,407건 92,209,152화소 전수 실측 검증 완료, 10m 정밀도 100%, 무결성 변조 0건, 6-밴드 100% 준비 완료) / **TESTED_SYNTHETIC** (격리 작업공간 내 14개 단위 시험 전수 통과).

---

## 1. 개요 및 배경

Sentinel-2 Level-2A(L2A) 위성 데이터는 대기 하부 지표 반사도(BOA: Bottom-of-Atmosphere surface reflectance)를 제공하며, 인도네시아 6개 주(반텐, 서자바, 동자바, 남술라웨시, 동남술라웨시, 고론탈로) 대상의 토지 피복 분류(LCLUC)에 필수적인 6개 핵심 분광 밴드를 포함합니다:
- **B02** (Blue, 492.4 nm) — 10m 고유 해상도
- **B03** (Green, 559.8 nm) — 10m 고유 해상도
- **B04** (Red, 664.6 nm) — 10m 고유 해상도
- **B08** (NIR, 832.8 nm) — 10m 고유 해상도
- **B11** (SWIR-1, 1610.4 nm) — 20m 고유 해상도 (10m 쌍선형 리샘플링 정합)
- **B12** (SWIR-2, 2190.0 nm) — 20m 고유 해상도 (10m 쌍선형 리샘플링 정합)

기존 파이프라인의 리포트 상에는 다운로드 상태가 과거 명칭인 `'rgb_window_downloaded'`로 표기되어 있었고, 반사도 변환 여부 또한 `'reflectance_conversion_verified: False'`로 남아 있어 6-밴드 분광 가용성, 10m 정밀도, 수치 스케일링(0~10,000 DN vs 0.0~1.0 물리 반사도) 및 포화 화소에 의한 LCLUC 분류 왜곡 방지 계약의 수립이 시급했습니다.

본 작업에서는 격리 작업공간(`evidence/integration/spectral-pipeline-workspace-20261019`)에서 비파괴(Non-mutating) 전수 감사 도구와 단위 시험 14건을 구축하고, 실제 1,407건 패치(총 92,209,152 화소) 전수를 정밀 감사하여 분광 품질과 LCLUC 오염 방지 마스킹 계약을 확립했습니다.

---

## 2. 이론적 배경 및 왜곡 방지 원칙

### 2.1 ESA Sentinel-2 L2A 정밀 복사 보정 공식
Sentinel-2 L2A 제품의 표면 반사도($\rho_{BOA}$)는 16비트 정수형 Digital Number($DN$)로 양자화되어 배포됩니다:

$$\rho_{BOA} = \frac{DN + \text{BOA\_ADD\_OFFSET}}{\text{BOA\_QUANTIFICATION\_VALUE}} = DN \times \text{Scale} + \text{Offset}$$

- **양자화 스케일**: $\text{BOA\_QUANTIFICATION\_VALUE} = 10,000.0$ ($\text{Scale} = 0.0001$)
- **복사 오프셋 분기 (Processing Baseline 04.00, 2022.01.25 도입)**:
  - **PB < 04.00 (2020~2021년 수집 데이터, 519건)**:
    - $\text{BOA\_ADD\_OFFSET} = 0.0$
    - $\text{Offset} = 0.0$
    - $\rho_{BOA} = DN \times 0.0001$
  - **PB $\ge$ 04.00 (2022~2025년 수집 데이터, 888건)**:
    - 어두운 음영·수체의 정수 절삭(truncation)을 방지하기 위한 $-1,000 DN$ 복사 오프셋.
    - $\text{BOA\_ADD\_OFFSET} = -1000.0$
    - $\text{Offset} = -1000.0 / 10000.0 = -0.10$
    - $\rho_{BOA} = DN \times 0.0001 - 0.10$

> [!IMPORTANT]
> 2022년 이후 영상에 단순 $DN / 10000$을 적용할 경우, 반사도가 절대치 $+0.10$(+10% 반사도)만큼 계통 편향(systematic bias)을 일으켜 NDVI, EVI, NBR 등 다중 시계열 식생 지수와 모델 학습이 심각하게 왜곡됩니다. 씬별 오프셋($0.0$ vs $-0.10$) 분기가 반드시 엄격하게 적용되어야 합니다.

### 2.2 10m 공간 해상도 정밀도
- 모든 연구 패치는 $256 \times 256$ 화소, 픽셀 크기 $10.0\text{m} \times 10.0\text{m}$ ($2.56\text{km} \times 2.56\text{km}$ 범위)로 정규화되어 있으며 투영 좌표계(UTM)를 유지합니다.
- B11, B12(20m)는 10m 격자에 맞춰 기하 정합되어 있습니다.

### 2.3 포화(Saturation) 및 음수 이상치에 의한 LCLUC 오염 방지
- **포화 화소 ($\rho > 1.0$)**:
  - 구름 정상부, 강한 태양광 반사(수면 specular glint), 함석 지붕 등에서 발생하며, 미마스킹 시 나지나 도시 지역으로 오분류되는 심각한 왜곡을 초래합니다.
- **음수 이상치 ($\rho < 0.0$)**:
  - 짙은 산악 지형 그림자 등에서 PB 04.00 오프셋($-0.10$)이 적용되면서 발생하는 대기 과보정 화소입니다.
- **LCLUC 왜곡 방지 마스크**:
  - 유효 화소 중 $\rho \in [0.0, 1.0]$ 범위 내의 순수 물리 화소만을 `CLEAN_LCLUC_PIXEL`로 분류하고, 포화 및 이상 화소는 플래그 처리하여 AI 모델 학습 및 추론 시 오염을 방지합니다.

### 2.4 Nodata 보존 및 비파괴 원칙
- $DN = 0.0$ 화소는 센서 미관측/타일 경계이므로 오프셋 $-0.10$을 더해 $-0.10$으로 변환해서는 안 되며, $0.0$(Nodata)으로 엄격히 보존합니다.
- 원본 GeoTIFF는 0~10,000 DN 원본 상태 그대로 보존하며, 반사도 변환은 메모리 상에서 동적으로 적용합니다.

---

## 3. 코드 및 도구 구현

격리 작업공간 `evidence/integration/spectral-pipeline-workspace-20261019/` 내 모듈:

1. [spectral_validator.py](file:///e:/GeoAI%E2%80%93MLOps%E2%80%93SDSS/evidence/integration/spectral-pipeline-workspace-20261019/spectral_validator.py)
   - `audit_single_patch`: 10m 해상도 검증, 6-밴드 분광 가용성, SHA-256 무변조 가드, 포화 화소 및 음수 이상치 집계.
   - `audit_annual_window_report`: 전체 컬렉션 1,407건 배치 전수 감사 및 주별·연도별 지표 산출.
2. [spectral_batch_contract.py](file:///e:/GeoAI%E2%80%93MLOps%E2%80%93SDSS/evidence/integration/spectral-pipeline-workspace-20261019/spectral_batch_contract.py)
   - `SpectralBatchContract`:
     - `get_calibration_parameters`: 연도 및 베이스라인 기반 오프셋 도출.
     - `apply_physical_reflectance`: 순수 Nodata 보존 물리 반사도 변환.
     - `generate_spectral_quality_mask`: LCLUC 분류 오염 방지 비트 마스크 생성 (포화, 음수이상치, Nodata, Clean 구분).
     - `apply_physical_reflectance_for_lcluc`: 포화 화소를 마스킹한 LCLUC 전용 텐서 및 이진 마스크 반환.
     - `validate_spectral_contract`: 10m 해상도 및 6-밴드 정합성 검증.
3. [test_spectral_validator.py](file:///e:/GeoAI%E2%80%93MLOps%E2%80%93SDSS/evidence/integration/spectral-pipeline-workspace-20261019/test_spectral_validator.py)
   - 14개 단위 시험 (10m 해상도 검증, 6/4/3 밴드 탐지, PB 04.00 수치 검증, 포화/음수 플래깅, LCLUC 마스킹, 무변조 보장).
4. [run_batch_audit.py](file:///e:/GeoAI%E2%80%93MLOps%E2%80%93SDSS/evidence/integration/spectral-pipeline-workspace-20261019/run_batch_audit.py)
   - 1,407건 일괄 자동 실행기 및 상세 결과 JSON 저장기.

---

## 4. 실측 전수 감사 결과 (1,407건 적격 패치 / 92,209,152 화소)

`data/first-group-training-esri-v1/annual-window-report.json`의 1,407건 적격 패치 전수를 감사 완료했습니다.

### 4.1 핵심 요약 지표

| 검사항목 | 결과 수치 | 비율 | 비고 |
|---|---|---|---|
| **총 감사 적격 패치** | **1,407건** | 100.0% | 디스크 상 파일 전수 실재 확인 |
| **10m 공간 해상도 검증 (`10m_verified`)** | **1,407건** | **100.0%** | $10.0\text{m} \times 10.0\text{m}$ 정밀도 전수 일치 |
| **6-밴드 BOA 준비 완료 (`6_BAND_BOA_READY`)** | **1,407건** | **100.0%** | B02, B03, B04, B08, B11, B12 보유 |
| 4-밴드 RGB-NIR 전용 (`RGB_NIR_4_BAND_ONLY`) | 0건 | 0.0% | 4-밴드 누락 패치 없음 |
| 3-밴드 RGB 전용 (`RGB_3_BAND_ONLY`) | 0건 | 0.0% | 3-밴드 누락 패치 없음 |
| 원시 스케일 상태 (`RAW_DN_0_10000`) | 1,407건 | 100.0% | 현재 원시 DN으로 보존 중 |
| PB < 04.00 규칙 (오프셋 0.0) | 519건 | 36.89% | 2020년(284건), 2021년(235건) |
| PB $\ge$ 04.00 규칙 (오프셋 -0.10) | 888건 | 63.11% | 2022~2025년 (254, 191, 220, 223건) |
| **디스크 원본 바이트 변조 (`mutations_detected`)** | **0건** | **0.0%** | 전후 SHA-256 100% 일치 |
| **총 검사 화소 수** | **92,209,152 px** | 100.0% | $1,407 \times 256 \times 256$ |
| **LCLUC 정상 유효 화소 (`Clean LCLUC`)** | **92,108,855 px** | **99.891%** | 오염 없는 순수 표면 반사도 화소 |
| **포화 화소 ($\rho > 1.0$)** | **19,406 px** | **0.0210%** | 290개 패치에 걸쳐 존재 (플래그 격리 완료) |
| **음수 이상치 화소 ($\rho < 0.0$)** | **73,691 px** | **0.0799%** | 140개 패치에 걸쳐 존재 (음영 대기과보정) |
| **물리적 반사도 타당성 합치** | **1,407건** | **100.0%** | S2 L2A 범위 $[-0.12, 2.05]$ 전건 합치 |
| **최종 계약 검증 상태** | **VERIFIED_REAL** | - | 배치 계약 체결 완료 |

### 4.2 주(Province)별 10m 정밀도 및 LCLUC 품질 분포

| 주 (Province) | 패치 수 | 10m 검증 | Clean 화소율 | 포화 화소 수 | 주요 특이사항 |
|---|---|---|---|---|---|
| **고론탈로 (Gorontalo)** | 212건 | 212 (100%) | 99.98% | 2,003 px | 높은 맑음 화소율 |
| **동남술라웨시 (SE Sulawesi)** | 217건 | 217 (100%) | 99.94% | 8,538 px | 해안 수면 반사광 포화 포함 |
| **동자바 (East Java)** | 209건 | 209 (100%) | 99.93% | 2,459 px | 농경지 및 도시 혼재 |
| **반텐 (Banten)** | 292건 | 292 (100%) | 99.97% | 4,219 px | 산림 및 농경지 |
| **서자바 (West Java)** | 250건 | 250 (100%) | 99.99% | 1,881 px | 매우 안정적인 물리 반사도 |
| **남술라웨시 (South Sulawesi)** | 227건 | 227 (100%) | 99.52% | 306 px | 산악 지형 깊은 음영(음수 이상치 69k) 포함 |
| **합계** | **1,407건** | **1,407 (100%)** | **99.891%** | **19,406 px** | **전 주 10m 일관성 확보** |

---

## 5. 테스트 증거

### 5.1 격리 단위 시험 (14/14 PASS, 0.474s)
```
Ran 14 tests in 0.474s
OK

- test_6band_raw_dn_patch_audit: 통과 (6-밴드 DN 정상 식별)
- test_10m_spatial_resolution_verification: 통과 (10m 정합성 및 20m 불일치 감지)
- test_4band_rgb_nir_detection: 통과 (4-밴드 패치 식별 및 미달 격리)
- test_3band_rgb_detection: 통과 (3-밴드 패치 식별 및 미달 격리)
- test_already_normalized_reflectance_patch: 통과 (기 정규화 패치 감지)
- test_pb_post04_negative_offset_calibration: 통과 (DN 5000 -> 0.40 검증)
- test_strict_zero_mutation_guarantee: 통과 (감사 전후 SHA 불변)
- test_saturation_and_distortion_flagging: 통과 (포화 및 음수 화소 분리 집계)
- test_quality_mask_alignment_and_mismatch: 통과 (품질 마스크 정합성 확인)
- test_apply_physical_reflectance_preserves_nodata: 통과 (Nodata 보존 확인)
- test_spectral_quality_mask_and_distortion_prevention: 통과 (비트마스크 정상 생성)
- test_apply_physical_reflectance_for_lcluc_masks_distortion: 통과 (LCLUC 마스킹 텐서 생성)
- test_calibration_parameter_resolution: 통과 (연도/베이스라인별 오프셋 매핑)
- test_spectral_contract_validation_including_10m_resolution: 통과 (계약 종합 검증)
```

### 5.2 전수 감사 실행기 증거
- 실행 명령: `python evidence/integration/spectral-pipeline-workspace-20261019/run_batch_audit.py`
- 소요 시간: 112.72초 (1,407개 GeoTIFF 92,209,152개 화소 전수 검사)
- 산출물 경로: [spectral_audit_results_1407.json](file:///e:/GeoAI%E2%80%93MLOps%E2%80%93SDSS/evidence/integration/spectral-pipeline-workspace-20261019/spectral_audit_results_1407.json)

---

## 6. LCLUC 분류 왜곡 방지 배치 적용 계약

토지 피복 AI 모델의 학습 DataLoader 및 추론 파이프라인은 아래 규격을 준수합니다:

1. **입력 검증**:
   - 6개 채널 (B02, B03, B04, B08, B11, B12), 10m 해상도 일치.
2. **복사 보정 및 Nodata 보존**:
   $$\text{Reflectance} = \begin{cases} 0.0 & \text{if } DN = 0.0 \text{ (Nodata)} \\ DN \times 0.0001 + \text{offset} & \text{if } DN > 0.0 \end{cases}$$
   - $year < 2022$: $\text{offset} = 0.0$
   - $year \ge 2022$: $\text{offset} = -0.10$
3. **LCLUC 왜곡 방지 마스킹**:
   - $\rho > 1.0$ (포화 화소, 전체의 0.0210%) 및 $\rho < 0.0$ (음수 이상치, 전체의 0.0799%)는 `clean_mask = False`로 플래그 처리.
   - 손실 함수 계산(Loss computation) 시 `clean_mask == True` 화소만을 역전파 대상으로 하여 이상치에 의한 모델 왜곡을 원천 차단.

---

## 7. 발표 스크립트

> "토지 피복 분류 AI 모델의 신뢰성을 확보하기 위해서는 10m 정밀도에서의 6-밴드 표면 반사도(BOA) 보정과 함께, 포화 화소에 의한 분류 오염을 방지하는 것이 결정적입니다.
> 
> 이번 전수 감사 결과, 대상 6개 주 1,407건 적격 패치는 전건 $10\text{m} \times 10\text{m}$ 정밀 해상도와 6개 분광 밴드를 100% 갖추고 있음을 실측 확인했습니다.
> 
> 나아가 9천 2백만 개 전체 화소를 분석하여 0.021%의 포화 화소(태양광 반사, 구름 정상 등)와 0.080%의 깊은 음영 대기과보정 화소를 정밀 탐지하는 왜곡 방지 마스킹 계약을 수립했습니다. 이로써 모델 학습 시 99.891%의 깨끗한 물리적 화소만을 정밀 선별하여 학습에 반영할 수 있는 과학적 기틀이 완성되었습니다."
