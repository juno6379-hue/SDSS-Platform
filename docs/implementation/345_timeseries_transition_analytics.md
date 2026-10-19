# 345. LCLUC 시계열 궤적 및 고급 전이행렬 분석 엔진 구현 보고서

상태: **TESTED_SYNTHETIC_ANALYTICS** (격리 작업공간 검증 완료, 메인 미반영).
- **작업 공간**: `evidence/integration/lcluc-analytics-workspace-20261019/`
- **단위 시험**: 14건 전건 통과 (`test_timeseries_transition_engine.py`, 3.30s).
- **6개 주 6개년 (2020-2025) 벤치마크**: Pontius (2004) 보존 항등식 100% 충족, Markov 행 확률 합 1.0(행 확률성) 100% 검증, Sankey 플로우 무결성 100% 확인 (`run_analytics_benchmark.py`, 0.58s).

---

## 1. 개요 및 목적

토지피복 및 토지이용 변화 탐지(LCLUC Change Detection)에서 두 시점 사이의 전이행렬(Transition Matrix)과 다년도(2020~2025) 면적 시계열은 의사결정자 및 분석가에게 핵심적인 정량적 지표를 제공합니다.

기존 파이프라인(`backend/app/ml/service.py:analyze_change`)은 인접 또는 기준 연도 간 전이 화소 수와 면적 행렬을 단순 계산하는 데 그쳐 다음과 같은 분석적 공백이 존재했습니다:
1. **변화 유형의 미분리**: 순변화(Net Change, 실제 총량적 증감)와 공간 교환(Swap, 상호 치환/순환 변화)이 분리되지 않아, 토지 변화의 지배적 메커니즘을 파악하기 어려움.
2. **시계열 궤적 추세 분류 부재**: 6개년 시계열 추세(단조 증가/감소, 정상 상태, 급변, 계절적 변동) 및 연평균 복합 성장률(CAGR) 산출 부재.
3. **확률 모델 및 시각화 데이터 부재**: 마르코프 연쇄(Markov Chain) 전이 확률 행렬과 Sankey 플로우 다이어그램 데이터가 제공되지 않아 미래 예측 및 UI 시각화에 제약.

본 345 구현은 Pontius et al. (2004) 및 Aldwaik & Pontius (2012)의 행렬 분해 이론과 Puyravaud (2003) 연속 성장률 공식을 적용한 고급 분석 엔진 `timeseries_transition_engine.py`를 완성하고 격리 검증을 완료하였습니다.

---

## 2. 수학적 정의 및 행렬 보존 항등식 (Mathematical Formulations)

### 2.1 다년도 궤적 지표 및 추세 분류

임의의 토지피복 클래스 $k$에 대한 $T$개년 면적 시계열 $A_k = [a_1, a_2, \dots, a_T]$ (기간: $y_1 \sim y_T$)에 대해:

1. **연평균 순변화율 (Annual Net Rate of Change)**:
   $$R_{\text{net}, k} = \frac{a_T - a_1}{y_T - y_1} \quad (\text{ha/year})$$
2. **복합 연간 성장률 (Compound Annual Growth Rate, CAGR)**:
   $$\text{CAGR}_k = \left(\frac{a_T}{a_1}\right)^{\frac{1}{y_T - y_1}} - 1.0$$
3. **Puyravaud (2003) 연속 지수 변화율**:
   $$r_k = \frac{1}{y_T - y_1} \ln\left(\frac{a_T}{a_1}\right) \times 100\% \quad (\%/\text{year})$$
4. **추세 유형 분류 (Trend Classification)**:
   - **`STEADY` (안정 추세)**: 상대 변동폭 $\frac{\max(A_k) - \min(A_k)}{\text{mean}(A_k)} \le 0.04$ (변동률 4% 이하 유지).
   - **`MONOTONIC_INCREASE` (단조 증가)**: 모든 연차 차분 $\Delta_t = a_{t+1} - a_t \ge 0$ 이며 $\max(A_k) > \min(A_k)$.
   - **`MONOTONIC_DECREASE` (단조 감소)**: 모든 연차 차분 $\Delta_t \le 0$ 이며 $\max(A_k) > \min(A_k)$.
   - **`SUDDEN_TRANSITION` (급격한 전이)**: 단일 연도 변화량이 전체 변동폭의 60% 이상을 차지하며 계단형 상태 유지.
   - **`FLUCTUATING_SEASONAL` (변동/계절 추세)**: 차분의 부호 반전이 다수 발생하며 일정 범위 내 진동.

---

### 2.2 Pontius et al. (2004) 전이행렬 분해

$K \times K$ 전이행렬 $\mathbf{N} = [N_{ij}]$ ($N_{ij}$는 $t_1$ 시점 클래스 $i$에서 $t_2$ 시점 클래스 $j$로 전이된 면적, ha):

- 초기 면적 (행 합): $R_i = \sum_{j=1}^K N_{ij}$
- 최종 면적 (열 합): $C_j = \sum_{i=1}^K N_{ij}$
- **지속성 (Persistence)**: $P_k = N_{kk}$ (대각 성분)
- **총 증가 (Gross Gain)**: $G_k = C_k - N_{kk} = \sum_{i \ne k} N_{ik}$
- **총 감소 (Gross Loss)**: $L_k = R_k - N_{kk} = \sum_{j \ne k} N_{kj}$
- **순변화 (Net Change)**: $D_{\text{net}, k} = G_k - L_k = C_k - R_k$
- **교환량 (Total Swap)**: $S_k = 2 \times \min(G_k, L_k)$
- **총 변화량 (Total Change)**: $T_k = G_k + L_k$

#### 보존 항등식 (Conservation Identities):
1. **클래스별 전이 항등식**:
   $$T_k = |D_{\text{net}, k}| + S_k \quad (\forall k \in \{1, \dots, K\})$$
   (각 클래스의 총 변화량은 순변화의 절댓값과 공간 교환량의 합과 정확히 일치함)
2. **순변화 제로합 법칙**:
   $$\sum_{k=1}^K D_{\text{net}, k} = 0$$
3. **전체 경관 변화 항등식**:
   $$\text{Total Landscape Change} = \text{Total Area} - \sum_{k=1}^K P_k = \frac{1}{2} \sum_{k=1}^K T_k$$
   $$\text{Total Landscape Net Change} = \frac{1}{2} \sum_{k=1}^K |D_{\text{net}, k}|$$
   $$\text{Total Landscape Swap} = \frac{1}{2} \sum_{k=1}^K S_k$$
   $$\mathbf{\text{Total Landscape Change} = \text{Total Landscape Net} + \text{Total Landscape Swap}}$$

---

### 2.3 취약성 및 지속성 지수 (Vulnerability & Persistence Ranking)

- **지속 비율 (Persistence Ratio)**: $p_i = \frac{N_{ii}}{R_i} \in [0.0, 1.0]$
- **손실 취약도 (Vulnerability to Loss)**: $v_i = \frac{L_i}{R_i} = 1 - p_i \in [0.0, 1.0]$
- **확장 강도 (Expansion Ratio)**: $e_j = \frac{G_j}{R_j}$
- 순위 산정: 지속 비율이 높고 면적이 큰 순으로 `most_persistent`, 손실 취약도가 높고 손실 면적이 큰 순으로 `most_vulnerable_to_loss` 산정.

---

### 2.4 마르코프 연쇄 전이 확률 행렬 (Markov Transition Probability Matrix)

전이 확률 행렬 $\mathbf{P} = [P_{ij}] \in \mathbb{R}^{K \times K}$:
$$P_{ij} = \begin{cases} \frac{N_{ij}}{R_i}, & \text{if } R_i > 0 \\ 1.0, & \text{if } R_i = 0 \land i = j \\ 0.0, & \text{if } R_i = 0 \land i \ne j \end{cases}$$

#### 행 확률성 조건 (Row Stochasticity):
$$\sum_{j=1}^K P_{ij} = 1.0 \quad (\forall i \in \{1, \dots, K\})$$

#### 다단계 미래 상태 예측:
초기 면적 분포 벡터 $\mathbf{v}(t_0) \in \mathbb{R}^K$에 대해 $m$ 스텝 후의 분포:
$$\mathbf{v}(t_0 + m \Delta t) = \mathbf{v}(t_0) \mathbf{P}^m$$

---

### 2.5 Sankey 플로우 다이어그램 생성

D3, Recharts, Plotly 등 웹 UI 시각화를 위한 정규 노드/링크 스키마 생성:
- 노드 집합: $2K$개 (출발 연도 $K$개 소스 노드 + 도착 연도 $K$개 타깃 노드)
- 링크 집합: $N_{ij} \ge \text{threshold}$ 인 유효 전이 플로우
- 링크 필드: `source`, `target`, `from_class`, `to_class`, `value_ha`, `percentage_of_total`, `is_persistence`
- 보존 조건: 모든 링크의 `value_ha` 합 = 전체 경관 면적 (Persistence 포함 시).

---

## 3. 소프트웨어 모듈 구조

`evidence/integration/lcluc-analytics-workspace-20261019/` 하위에 구현된 모듈:

```
evidence/integration/lcluc-analytics-workspace-20261019/
├── timeseries_transition_engine.py  # 핵심 분석 엔진 (궤적, 행렬분해, 마르코프, Sankey)
├── test_timeseries_transition_engine.py  # 14건 단위 테스트 스위트
├── run_analytics_benchmark.py       # 6개 주 6개년 (2020-2025) 벤치마크 러너
├── analytics_summary.json           # 6개 주 벤치마크 총괄 리포트
├── analytics_verification.log       # 실행 로그
└── artifacts/                       # 주별 산출물 디렉터리
    ├── banten/
    │   ├── analytics_report.json    # 궤적, 분해, 랭킹 종합 JSON
    │   ├── markov_probabilities.json # P_ij 행렬 및 행 확률성 검증 JSON
    │   └── sankey_data.json         # Sankey 노드/링크 플로우 JSON
    ├── east_java/
    ├── gorontalo/
    ├── south_sulawesi/
    ├── southeast_sulawesi/
    └── west_java/
```

---

## 4. 검증 결과 및 시험 증거 (Validation Results)

### 4.1 단위 시험 결과 (`pytest test_timeseries_transition_engine.py`)
- **결과**: **14 / 14 PASS** (소요 시간 3.30초, exit code 0)
- **주요 검증 내역**:
  1. `test_trend_classification_steady`: 4% 이내 변동 시 STEADY 판정 검증.
  2. `test_trend_classification_monotonic_increase`: 단조 증가 시 MONOTONIC_INCREASE 검증.
  3. `test_trend_classification_monotonic_decrease`: 단조 감소 시 MONOTONIC_DECREASE 검증.
  4. `test_trend_classification_sudden_transition`: 단일 연도 급변 시 SUDDEN_TRANSITION 검증.
  5. `test_trend_classification_fluctuating_seasonal`: 다회 부호 반전 시 FLUCTUATING_SEASONAL 검증.
  6. `test_cagr_and_puyravaud_rate_calculations`: CAGR 및 Puyravaud 지수 변화율 수식 검증.
  7. `test_analyze_trajectory_series_structure`: 6개년 시계열 분석 데이터 스키마 검증.
  8. `test_class_level_swap_and_net_decomposition`: Grass 클래스의 Net(-40ha) + Swap(80ha) = Total(120ha) 일치 검증.
  9. `test_pontius_decomposition_identities`: 클래스별 $T_k = |Net_k| + Swap_k$, 순변화 합 0, 경관 $Total = Net + Swap$ 보존 검증.
  10. `test_rankings_persistence_and_vulnerability`: 지속성 및 손실 취약도 순위 정렬 검증.
  11. `test_markov_transition_probability_matrix`: 행 확률성($\sum_j P_{ij} = 1.0$) 및 1단계 투영 보존 검증.
  12. `test_sankey_flow_generation_integrity`: Sankey 노드 18개, 플로우 합 = 전체 면적 일치 검증.
  13. `test_sankey_flow_excluding_persistence`: 대각 지속성 제외 옵션 검증.
  14. `test_full_analytics_run_and_artifact_export`: 통합 엔진 실행 및 3개 JSON 파일 출력 검증.

---

### 4.2 6개 주 6개년 (2020-2025) 벤치마크 결과 (`run_analytics_benchmark.py`)

인도네시아 First Group 6개 주(반텐, 서자바, 동자바, 남술라웨시, 동남술라웨시, 고론탈로) 대상 각 100,000 ha 경관 시뮬레이션:

| 대상 주 (Province) | 산림(Trees) 추세 | 도시(Built) 추세 | 산림 CAGR | 도시 CAGR | 경관 순변화량 (Net) | 경관 교환량 (Swap) | Pontius 보존 항등식 | Markov 행 확률성 | Sankey 플로우 수 |
|---|---|---|---|---|---|---|---|---|---|
| **반텐 (`banten`)** | MONOTONIC_DECREASE | MONOTONIC_INCREASE | -1.04%/yr | +3.34%/yr | 2,297.77 ha | 1,100.00 ha | **100% VERIFIED** | **100% VERIFIED** | 14 flows |
| **동자바 (`east_java`)** | MONOTONIC_DECREASE | MONOTONIC_INCREASE | -1.09%/yr | +3.42%/yr | 2,405.96 ha | 1,100.00 ha | **100% VERIFIED** | **100% VERIFIED** | 14 flows |
| **고론탈로 (`gorontalo`)** | MONOTONIC_DECREASE | MONOTONIC_INCREASE | -1.12%/yr | +3.46%/yr | 2,455.36 ha | 1,100.00 ha | **100% VERIFIED** | **100% VERIFIED** | 14 flows |
| **남술라웨시 (`south_sulawesi`)** | MONOTONIC_DECREASE | MONOTONIC_INCREASE | -1.20%/yr | +3.59%/yr | 2,627.48 ha | 1,100.00 ha | **100% VERIFIED** | **100% VERIFIED** | 14 flows |
| **동남술라웨시 (`southeast_sulawesi`)** | MONOTONIC_DECREASE | MONOTONIC_INCREASE | -1.14%/yr | +3.49%/yr | 2,503.30 ha | 1,100.00 ha | **100% VERIFIED** | **100% VERIFIED** | 14 flows |
| **서자바 (`west_java`)** | MONOTONIC_DECREASE | MONOTONIC_INCREASE | -1.13%/yr | +3.48%/yr | 2,487.72 ha | 1,100.00 ha | **100% VERIFIED** | **100% VERIFIED** | 14 flows |

- **Pontius 보존 법칙 통과율**: **6개 주 전건 100% 통과 (Pass Rate: 1.0)**
- **Markov 행 확률성 통과율**: **6개 주 전건 100% 통과 (Pass Rate: 1.0)**
- **벤치마크 총 소요 시간**: **0.58초**

---

## 5. 결론 및 다운스트림 인계 계획

본 엔진은 격리 작업공간 내에서 완전한 단위 시험과 대규모 벤치마크를 마쳤으며, 향후 다음과 같이 메인 시스템에 통합될 수 있습니다:

1. **`backend/app/ml/service.py:analyze_timeseries` 연계**:
   - 다년도 추론 결과에 대해 본 분석 엔진을 호출하여 연차별 추세 분류 및 Pontius 행렬 분해 결과를 `timeseries.json` 리포트에 포함.
2. **SDSS 의사결정 지원 및 정책 대시보드 (`web_ui`) 연계**:
   - `sankey_data.json`을 프론트엔드 Sankey 차트 컴포넌트에 공급하여 직관적인 토지피복 전환 흐름 시각화.
   - `markov_probabilities.json`을 정책 시뮬레이터에 연결하여 향후 5년/10년 후 산림 감소 및 도시 확장 예측치 제공.
