# 348. LCLUC 공통 유효영역(Common Valid) 및 NoData 왜곡 원천 차단 전이행렬 엔진 구현 보고서

상태: **TESTED_SYNTHETIC_ANALYTICS** (격리 작업공간 검증 완료, 22건 단위시험 전수 합격, 회귀 15건 포함 총 37건 합격).
- **작업 공간**: `evidence/integration/lcluc-filter-workspace-20261019/`
- **구현 모듈**: `common_valid_transition.py`
- **단위 시험**: `test_common_valid_transition.py` (22건 전건 PASS, 1.25초)
- **회귀 시험**: `test_temporal_change_filter.py` (15건 전건 PASS, 1.75초)
- **종합 벤치마크**: `run_common_valid_verification.py` (5대 결측률 시나리오 및 연도 불일치 검증 완료)
- **산출물**:
  - `evidence/integration/lcluc-filter-workspace-20261019/artifacts/common_valid_verification_summary.json`
  - `evidence/integration/lcluc-filter-workspace-20261019/artifacts/scenario_verification_report.json`

---

## 1. 개요 및 구현 배경

토지피복 및 토지이용 변화 탐지(LCLUC Change Detection)에서 두 시점($T_1, T_2$) 간 전이행렬을 산출할 때 가장 심각한 데이터 왜곡 중 하나는 **구름, 그림자, 센서 결측치(NoData=255)가 토지피복 클래스(예: 산림 감소, 비인공 피복)나 '변화 없음'으로 둔갑하는 문제**입니다.

예를 들어:
- $T_1$에 산림(Forest, 1)이었던 화소가 $T_2$에 구름(NoData, 255)으로 가려진 경우, 이를 단순 마스킹하지 않고 집계하면 **실제로는 나무가 그대로 있는데도 '산림 감소(Deforestation)'로 오분류되어 정책적 통계가 심각하게 왜곡**됩니다.
- 반대로 $T_1$과 $T_2$ 모두 NoData인 영역을 '불변 화소(Persistence)'로 합산하면 전체 도메인 면적이 허위로 팽창합니다.
- 또한 결측 화소 비율이 비정상적으로 높은 영상(예: 우기 몬순 구름 15% 초과)이나, 요청 연도와 기본 래스터의 출처 연도가 불일치하는 경우(예: 요청 T2=2025 vs 실제 출처 2021 ESA WorldCover), 공식 인증 변경분석으로 유통되면 국가 기후·산림 통계의 신뢰도가 붕괴됩니다.

본 Unit 348은 `UI/GreenBlue_CODEX_LCLUC_Annual_Map_GeoServer_v1.0.md` 제3장 및 제6장의 원칙에 따라, **엄격한 공통 유효영역 필터링, 4방향 명시적 면적 분할, NoData 둔갑 원천 차단, 결측률 기반 잠정(Provisional/Uncertain) 플래그 및 인증 차단(Certification Gating), 연도 불일치 감지, 수학적 보존 불변식**을 보증하는 전이행렬 엔진 `common_valid_transition.py`를 완성하였습니다.

---

## 2. 핵심 아키텍처 및 수학적 정식화

### 2.1 공통 유효영역 (Common Valid Domain) 정의
두 시점의 변화 탐지는 오직 **두 시점 모두 유효하고 AOI 경계 내에 포함된 화소**만을 대상으로 수행됩니다:
$$\text{Valid}_{\text{common}} = \text{Valid}_{T1} \land \text{Valid}_{T2} \land \text{AOI}_{\text{mask}}$$

- $\text{Valid}_{T1} = (T_1 \ne 255) \land \text{isfinite}(T_1) \land (0 \le T_1 < K) \land \text{Quality}_{T1}$
- $\text{Valid}_{T2} = (T_2 \ne 255) \land \text{isfinite}(T_2) \land (0 \le T_2 < K) \land \text{Quality}_{T2}$

### 2.2 4방향 명시적 면적 및 화소 분할 (Area Partitioning)
1. **AOI 전체 도메인 면적 ($A_{\text{total}}$)**: $\sum \text{AOI}_{\text{mask}}$
2. **$T_1$ 유효 면적 ($A_{\text{valid}, T1}$)**: $\sum (\text{Valid}_{T1} \land \text{AOI}_{\text{mask}})$
3. **$T_2$ 유효 면적 ($A_{\text{valid}, T2}$)**: $\sum (\text{Valid}_{T2} \land \text{AOI}_{\text{mask}})$
4. **공통 유효 면적 ($A_{\text{common}}$)**: $\sum \text{Valid}_{\text{common}}$
5. **비교 불가 면적 ($A_{\text{incomparable}}$)**: $A_{\text{total}} - A_{\text{common}}$
   - $T_1$ 단독 결측 ($A_{T1\text{-only}}$): $\sum (\text{AOI}_{\text{mask}} \land \neg \text{Valid}_{T1} \land \text{Valid}_{T2})$
   - $T_2$ 단독 결측 ($A_{T2\text{-only}}$): $\sum (\text{AOI}_{\text{mask}} \land \text{Valid}_{T1} \land \neg \text{Valid}_{T2})$
   - 양 시점 동시 결측 ($A_{\text{both}}$): $\sum (\text{AOI}_{\text{mask}} \land \neg \text{Valid}_{T1} \land \neg \text{Valid}_{T2})$

$$\text{항등식 1: } A_{\text{incomparable}} = A_{T1\text{-only}} + A_{T2\text{-only}} + A_{\text{both}}$$
$$\text{항등식 2: } A_{\text{total}} = A_{\text{common}} + A_{\text{incomparable}}$$

### 2.3 NoData 둔갑 원천 차단 (NoData Masquerade Prevention)
- 전이행렬 $M[i, j]$ ($i, j \in \{0, \dots, K-1\}$, $K=9$)는 오직 $\text{Valid}_{\text{common}}$ 화소만으로 계산됩니다:
  $$M[i, j] = \sum_{p \in \text{Valid}_{\text{common}}} \mathbb{I}(T_1(p) = i \land T_2(p) = j)$$
- NoData(255) 화소는 행렬 인덱스(0..8)에 일절 포함되지 않습니다 (행렬 차원은 엄격히 $9 \times 9$).
- $T_1$ 산림(1) 화소가 $T_2$에 구름(255)인 경우, $M[1, j]$에 집계되지 않고 $A_{T2\text{-only}}$로 분리되어 산림 감소량이 0.00 ha로 정확히 보존됩니다.
- 2D 전이 래스터 지도에서 비교 불가 영역은 `TRANSITION_NODATA = 65535`로 격리 마스킹됩니다.

### 2.4 순변화 제로섬 항등식 (Zero-Sum Transition Identity)
전체 9개 토지피복 클래스에 대해:
1. **총 손실 합 == 총 이득 합**:
   $$\sum_{k=0}^{8} \text{gross\_loss}(k) = \sum_{k=0}^{8} \text{gross\_gain}(k)$$
2. **순변화 총합 제로섬 (Zero-Sum)**:
   $$\Delta \text{net}_{\text{total}} = \sum_{k=0}^{8} \text{gross\_gain}(k) - \sum_{k=0}^{8} \text{gross\_loss}(k) = \sum_{k=0}^{8} \text{net\_change}(k) \equiv 0$$
3. **각 클래스별 평형 항등식**:
   $$\forall k \in [0..8]: \quad \text{gross\_gain}(k) - \text{gross\_loss}(k) = \text{net\_change}(k)$$

### 2.5 공식 인증 거버넌스 및 차단 (Certification Gating)
- **결측률 기준**: $\text{Missing Ratio } = \frac{N_{\text{incomparable}}}{N_{\text{total}}}$
  - $\text{Missing Ratio} \le 0.15$ (15% 이하): `reliability_status = "CERTIFIED_RELIABLE"`, `certification_blocked = False`, `is_certified_usable = True`
  - $\text{Missing Ratio} > 0.15$ (15% 초과): `reliability_status = "PROVISIONAL_UNCERTAIN"`, `certification_blocked = True`, `is_certified_usable = False`
  - 차단 상태에서 `assert_certified_usable()` 호출 시 `CertificationBlockedError` 발생.
- **연도 불일치(Year Mismatch) 감지 및 차단**:
  - 요청 연도(예: T2=2025)와 기본 래스터의 메타데이터 출처 연도(예: 2021 ESA WorldCover)가 불일치할 경우 즉시 `year_mismatch_detected = True`로 기록하고 상태를 `PROVISIONAL_UNCERTAIN`으로 강등 및 공식 인증 차단.
  - `enforce_year_match=True` 옵션 지정 시 사전검사에서 `ValueError`를 발생시켜 분석 실행 자체를 거부.

---

## 3. 5대 결측률 시나리오 종합 검증 결과

`evidence/integration/lcluc-filter-workspace-20261019/run_common_valid_verification.py`를 통해 10,000 화소 (100.00 ha) 시뮬레이션 환경에서 5대 결측률 시나리오를 전수 검증하였습니다:

| 시나리오 | 결측률 (%) | 전체 AOI (px) | 공통 유효 (px) | 비교 불가 (px) | T1 단독 / T2 단독 / 동시 | 신뢰도 상태 | 공식인증 차단 여부 | Gross Loss == Gain (px) | Net Sum (px) |
|---|---|---|---|---|---|---|---|---|---|
| **A (Clear Sky)** | **0.00%** | 10,000 | 10,000 (100.0%) | 0 (0.0%) | 0 / 0 / 0 | `CERTIFIED_RELIABLE` | 허용 (`is_usable=True`) | 1,500 == 1,500 | 0 |
| **B (Light Cloud)** | **5.00%** | 10,000 | 9,500 (95.0%) | 500 (5.0%) | 200 / 200 / 100 | `CERTIFIED_RELIABLE` | 허용 (`is_usable=True`) | 1,425 == 1,425 | 0 |
| **C (Exact Boundary)** | **15.00%** | 10,000 | 8,500 (85.0%) | 1,500 (15.0%) | 600 / 600 / 300 | `CERTIFIED_RELIABLE` | 허용 (`is_usable=True`) | 1,254 == 1,254 | 0 |
| **D (Monsoon Cloud)** | **35.00%** | 10,000 | 6,500 (65.0%) | 3,500 (35.0%) | 1,400 / 1,400 / 700 | `PROVISIONAL_UNCERTAIN` | **차단 (`Blocked`)** | 969 == 969 | 0 |
| **E (Severe Cloud)** | **60.00%** | 10,000 | 4,000 (40.0%) | 6,000 (60.0%) | 2,400 / 2,400 / 1,200 | `PROVISIONAL_UNCERTAIN` | **차단 (`Blocked`)** | 590 == 590 | 0 |

---

## 4. 연도 불일치 (Year Mismatch) 및 사전검사 거부 검증

1. **연도 불일치 자동 감지 및 인증 차단**:
   - 요청 연도: $T_1 = 2020$, $T_2 = 2025$
   - 래스터 출처: $T_1 = 2020$, $T_2 = 2021$ (ESA WorldCover)
   - 결과:
     - `year_mismatch_detected`: `True`
     - `reliability_status`: `PROVISIONAL_UNCERTAIN`
     - `certification_blocked`: `True`
     - `assert_certified_usable()` 호출 시: `CertificationBlockedError: 공식 변경분석 인증 차단(Certification Blocked): 연도 불일치...` 정상 발생.
2. **사전검사 강제 모드 (`enforce_year_match=True`)**:
   - `ValueError: 요청 연도와 래스터 출처 연도 불일치(Year Mismatch)로 인해 분석이 거부되었습니다: T2 요청 연도(2025) != 래스터 출처 연도(2021, 소스: reference_landcover)` 정상 예외 발생 및 분석 사전 차단.

---

## 5. 단위 시험 및 회귀 시험 전수 합격 증거

```powershell
$env:PYTHONPATH="evidence/integration/lcluc-filter-workspace-20261019;backend;."
pytest evidence/integration/lcluc-filter-workspace-20261019/test_common_valid_transition.py -v
```

```text
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0
rootdir: E:\GeoAI–MLOps–SDSS
plugins: anyio-4.15.1
collected 22 items

evidence/integration/lcluc-filter-workspace-20261019/test_common_valid_transition.py::TestPreflightSpatialAlignment::test_identical_profiles_pass PASSED [  4%]
evidence/integration/lcluc-filter-workspace-20261019/test_common_valid_transition.py::TestPreflightSpatialAlignment::test_crs_mismatch_raises_value_error PASSED [  9%]
evidence/integration/lcluc-filter-workspace-20261019/test_common_valid_transition.py::TestPreflightSpatialAlignment::test_dimensions_mismatch_raises_value_error PASSED [ 13%]
evidence/integration/lcluc-filter-workspace-20261019/test_common_valid_transition.py::TestPreflightSpatialAlignment::test_half_pixel_offset_raises_value_error PASSED [ 18%]
evidence/integration/lcluc-filter-workspace-20261019/test_common_valid_transition.py::TestStrictNoDataExclusionAndMasqueradePrevention::test_nodata_in_t1_or_t2_strictly_excluded_from_matrix PASSED [ 22%]
evidence/integration/lcluc-filter-workspace-20261019/test_common_valid_transition.py::TestStrictNoDataExclusionAndMasqueradePrevention::test_t2_cloud_over_forest_is_not_falsely_counted_as_forest_loss PASSED [ 27%]
evidence/integration/lcluc-filter-workspace-20261019/test_common_valid_transition.py::TestStrictNoDataExclusionAndMasqueradePrevention::test_nodata_in_both_years_is_not_counted_as_unchanged_persistence PASSED [ 31%]
evidence/integration/lcluc-filter-workspace-20261019/test_common_valid_transition.py::TestStrictNoDataExclusionAndMasqueradePrevention::test_quality_mask_excludes_cloud_and_shadow_pixels PASSED [ 36%]
evidence/integration/lcluc-filter-workspace-20261019/test_common_valid_transition.py::TestMathematicalConservationInvariants::test_mathematical_conservation_laws PASSED [ 40%]
evidence/integration/lcluc-filter-workspace-20261019/test_common_valid_transition.py::TestMissingRatioAndProvisionalFlag::test_low_missing_ratio_is_certified_reliable PASSED [ 45%]
evidence/integration/lcluc-filter-workspace-20261019/test_common_valid_transition.py::TestMissingRatioAndProvisionalFlag::test_high_missing_ratio_triggers_provisional_uncertain_flag PASSED [ 50%]
evidence/integration/lcluc-filter-workspace-20261019/test_common_valid_transition.py::TestMissingRatioAndProvisionalFlag::test_zero_aoi_pixels_handled_gracefully PASSED [ 54%]
evidence/integration/lcluc-filter-workspace-20261019/test_common_valid_transition.py::TestSerializationAndExport::test_to_dict_and_to_json PASSED [ 59%]
evidence/integration/lcluc-filter-workspace-20261019/test_common_valid_transition.py::TestMissingRateScenarios::test_missing_rate_scenarios_governance_and_partition[0.0-CERTIFIED_RELIABLE-False] PASSED [ 63%]
evidence/integration/lcluc-filter-workspace-20261019/test_common_valid_transition.py::TestMissingRateScenarios::test_missing_rate_scenarios_governance_and_partition[5.0-CERTIFIED_RELIABLE-False] PASSED [ 68%]
evidence/integration/lcluc-filter-workspace-20261019/test_common_valid_transition.py::TestMissingRateScenarios::test_missing_rate_scenarios_governance_and_partition[15.0-CERTIFIED_RELIABLE-False] PASSED [ 72%]
evidence/integration/lcluc-filter-workspace-20261019/test_common_valid_transition.py::TestMissingRateScenarios::test_missing_rate_scenarios_governance_and_partition[35.0-PROVISIONAL_UNCERTAIN-True] PASSED [ 77%]
evidence/integration/lcluc-filter-workspace-20261019/test_common_valid_transition.py::TestMissingRateScenarios::test_missing_rate_scenarios_governance_and_partition[60.0-PROVISIONAL_UNCERTAIN-True] PASSED [ 81%]
evidence/integration/lcluc-filter-workspace-20261019/test_common_valid_transition.py::TestYearMismatchDetectionAndCertificationGating::test_matching_provenance_years_passes_certification PASSED [ 86%]
evidence/integration/lcluc-filter-workspace-20261019/test_common_valid_transition.py::TestYearMismatchDetectionAndCertificationGating::test_mismatched_t2_provenance_year_degrades_and_blocks_certification PASSED [ 90%]
evidence/integration/lcluc-filter-workspace-20261019/test_common_valid_transition.py::TestYearMismatchDetectionAndCertificationGating::test_enforce_year_match_raises_value_error PASSED [ 95%]
evidence/integration/lcluc-filter-workspace-20261019/test_common_valid_transition.py::TestYearMismatchDetectionAndCertificationGating::test_combined_high_missing_and_year_mismatch PASSED [100%]

============================= 22 passed in 1.25s ==============================
```

---

## 6. 결론 및 향후 연계

본 Unit 348은 `UI/GreenBlue_CODEX_LCLUC_Annual_Map_GeoServer_v1.0.md`의 Section 3 및 6에 명시된 엄격한 과학적 품질 거버넌스 및 NoData 위장 차단 요건을 100% 충족하였습니다:
1. **5대 결측률 시나리오(0%, 5%, 15%, 35%, 60%) 완벽 지원 및 4방향 면적 분할 불변식 보증**.
2. **NoData(255)의 전이행렬 침투 원천 차단 및 순변화 제로섬($\sum \text{Net} = 0$) 불변식 보증**.
3. **결측률 15% 초과 및 연도 불일치 시 공식 인증 차단(`CertificationBlockedError`) 거버넌스 완성**.
4. 향후 통합 파이프라인에서 상위 서비스(WMS 타일 서비스, GeoServer ImageMosaic, GeoAI 통계 API)가 본 엔진을 직접 호출하도록 표준 인터페이스로 제공됩니다.
