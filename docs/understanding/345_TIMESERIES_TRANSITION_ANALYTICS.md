# 345. LCLUC 시계열 궤적 및 고급 전이행렬 분석 엔진

상태: **TESTED_SYNTHETIC_ANALYTICS** (격리 작업공간 검증 완료, 메인 미반영).
- 실물 기록 감사(`VERIFIED_REAL`): 기존 `service.py:analyze_change`는 단순 전이 픽셀/면적 행렬만 산출하여 순변화와 교환량의 구분이 불가능했고, 다년도 시계열 추세 및 마르코프 전이 확률 모델이 부재했음.
- 격리 검증(`TESTED_SYNTHETIC`): 격리 작업공간(`evidence/integration/lcluc-analytics-workspace-20261019/`) 내에서 Pontius et al. (2004) 전이행렬 분해, 5가지 시계열 추세 분류, CAGR/Puyravaud 성장률, 행 확률성 Markov 전이 확률 모델, Sankey 플로우 생성 엔진 개발. 14건 단위시험 전건 통과, 6개 주 6개년(2020~2025) 벤치마크 보존 법칙 100% 검증(0.58s).

---

## 1. 쉬운 설명

토지피복 변화를 분석할 때 단순히 "숲이 1,000 ha 줄었다"고만 알면 불충분합니다.
1. 줄어든 1,000 ha가 어디로 갔는가? (도시로 갔는가, 농경지로 갔는가?)
2. 다른 곳에서 숲이 새로 자라난 곳은 없는가? (공간적으로 위치만 맞바뀐 '교환'은 얼마인가?)
3. 지난 6년간(2020~2025) 매년 꾸준히 줄어든 것인가, 아니면 특정 연도에 갑자기 파괴된 것인가?

본 345 분석 엔진은 이러한 질문에 완벽히 답할 수 있는 고급 통계 분석 기능을 제공합니다:
- **순변화(Net Change)와 교환량(Swap) 분리**: 총 변화량을 '실제로 사라진 순수 손실'과 '위치만 서로 맞바뀐 공간적 교환'으로 깔끔하게 쪼개어 분석합니다.
- **시계열 추세 자동 분류**: 6개년 면적 데이터를 보고 이 토지가 '꾸준히 증가'하는지, '꾸준히 감소'하는지, '안정 상태'인지, '단 1년 만에 급변'했는지, 아니면 '계절적 요동'인지를 자동으로 판별합니다.
- **미래 예측 마르코프 확률 행렬**: 현재의 변화 속도가 지속될 경우 5년 뒤, 10년 뒤 토지가 어떻게 변할지 확률적으로 시뮬레이션할 수 있는 행렬을 계산합니다.
- **Sankey 플로우 다이어그램 데이터**: 2020년의 숲, 농경지, 도시가 2025년에 어디로 흘러들어갔는지를 직관적인 흐름 선(Sankey)으로 그릴 수 있는 데이터를 자동 생성합니다.

---

## 2. 이론적 배경

- **Pontius et al. (2004) 행렬 분해 이론**:
  전이행렬 $\mathbf{N}$을 대각 성분인 지속성(Persistence), 총 증가(Gain), 총 감소(Loss)로 분해한 뒤, 순변화(Net Change = Gain - Loss)와 공간 교환량(Swap = $2 \times \min(\text{Gain}, \text{Loss})$)을 도출합니다.
  - 클래스 보존 법칙: $\text{Total Change} = |\text{Net Change}| + \text{Swap}$
  - 경관 전체 보존 법칙: $\text{Landscape Total Change} = \text{Landscape Net Change} + \text{Landscape Swap}$
- **취약성 및 지속성 지수 (Vulnerability & Persistence Ranking)**:
  - 지속 비율($P_{\text{persist}} = N_{ii} / R_i$): 원래 면적 대비 보존된 비율 (1.0이면 완벽한 불변).
  - 손실 취약도($V_{\text{loss}} = 1 - P_{\text{persist}}$): 원래 면적 대비 다른 용도로 전환된 비율.
- **Puyravaud (2003) & CAGR 산출**:
  연평균 복합 성장률(CAGR) 및 FAO 산림 변화율 표준인 연속 지수 성장률 $r = \frac{1}{t_2 - t_1} \ln(A_2 / A_1) \times 100\%$ 산출.
- **마르코프 연쇄 (Markov Chain) 전이 확률**:
  $P_{ij} = N_{ij} / R_i$로 정규화하여 모든 행의 합이 정확히 1.0이 되는 행 확률성(Row Stochasticity)을 충족하는 전이 확률 모델 구축.

---

## 3. 코드/데이터 동작

- 작업공간: `evidence/integration/lcluc-analytics-workspace-20261019/`
- 핵심 구현 모듈:
  - `timeseries_transition_engine.py`:
    - `TimeSeriesTrajectoryAnalyzer`: 6개년 시계열 궤적 추세 분류, CAGR/Puyravaud 성장률 산출.
    - `AdvancedTransitionMatrixAnalytics`: Pontius 행렬 분해, 보존 항등식 검증, 지속성/취약성 랭킹, Markov 확률 행렬, Sankey 플로우 생성.
    - `TimeSeriesTransitionAnalyticsEngine`: 전체 파이프라인 통합 및 JSON 산출물 내보내기.
  - `test_timeseries_transition_engine.py`: 14건 단위 테스트 스위트.
  - `run_analytics_benchmark.py`: 인도네시아 6개 주 6개년(2020~2025) 벤치마크 러너.
- 산출물:
  - `analytics_report.json`: 궤적, 분해, 랭킹 종합 JSON.
  - `sankey_data.json`: 웹 UI 시각화용 Sankey 노드/링크 JSON.
  - `markov_probabilities.json`: $P_{ij}$ 전이 확률 행렬 및 행 확률성 검증 JSON.
  - `analytics_summary.json`: 6개 주 벤치마크 총괄 리포트.

---

## 4. 테스트 증거

1. **단위 테스트 (`pytest test_timeseries_transition_engine.py`)**:
   - **14 / 14 PASS** (소요 시간 3.30초, exit code 0)
   - 주요 통과 항목:
     - 5대 추세 유형(STEADY, MONOTONIC_INCREASE, MONOTONIC_DECREASE, SUDDEN_TRANSITION, FLUCTUATING_SEASONAL) 분류 정확도: PASS
     - CAGR 및 Puyravaud 지수 변화율 수식 검증: PASS
     - Grass 클래스 Swap(80ha) + Net(-40ha) = Total(120ha) 일치: PASS
     - Pontius 3대 보존 항등식(클래스별, 순변화 합=0, 경관 전체): PASS
     - Markov 행 확률성($\sum_j P_{ij} = 1.0$) 및 1단계 투영 보존: PASS
     - Sankey 노드 18개 및 플로우 총량 일치: PASS
     - 통합 엔진 실행 및 3대 JSON 산출물 내보내기: PASS

2. **6개 주 6개년 (2020-2025) 벤치마크 (`run_analytics_benchmark.py`)**:
   - 대상: 반텐, 서자바, 동자바, 남술라웨시, 동남술라웨시, 고론탈로 (각 100,000 ha)
   - **Pontius 보존 법칙 통과율**: **6개 주 전건 100% 통과 (1.0)**
   - **Markov 행 확률성 통과율**: **6개 주 전건 100% 통과 (1.0)**
   - **총 실행 시간**: **0.58초**

---

## 5. 발표 스크립트

> "안녕하십니까, '시계열 궤적 및 고급 전이행렬 분석 엔진' 검증 결과를 보고드립니다.
> 
> 기존에는 두 연도 간 변화를 분석할 때 단순히 전이 면적의 합계만 계산할 수 있어, 실제 순수하게 감소한 면적(Net Change)과 공간적으로 위치만 맞바뀐 교환량(Swap)을 구분할 수 없었습니다.
> 
> 이에 따라 Pontius et al. (2004) 행렬 분해 이론을 적용하여, 모든 클래스와 전체 경관에 대해 '총 변화량 = |순변화량| + 교환량'이 수학적으로 정확히 성립함을 입증하는 고급 분석 엔진을 구현하였습니다.
> 
> 또한 2020년부터 2025년까지의 6개년 시계열 궤적에 대해 연평균 복합 성장률(CAGR)을 산출하고, 추세를 단조 증가, 단조 감소, 안정, 급격한 전이, 계절적 변동으로 자동 분류합니다. 나아가 모든 행의 확률 합이 1.0인 마르코프 전이 확률 행렬과 웹 UI 시각화를 위한 Sankey 플로우 데이터를 자동으로 생성합니다.
> 
> 인도네시아 6개 대상 주에 대한 6개년 벤치마크 결과, 6개 주 전건에서 보존 법칙과 마르코프 행 확률성이 100% 완벽히 입증되었습니다."

---

## 6. 예상 질의응답 (Q&A)

**Q1: 순변화(Net Change)와 교환량(Swap)을 구분하는 것이 왜 실무적으로 중요한가요?**
> A: 예를 들어 어느 지역의 농경지가 1,000 ha 증가하고 다른 지역에서 1,000 ha 감소했다면, 순변화는 0 ha이지만 실제로는 2,000 ha의 토지가 교환(Swap)된 것입니다. 이를 구분하지 못하면 환경 파괴나 농지 이동이 활발하게 일어났음에도 불구하고 "토지 변화가 전혀 없다"고 왜곡 판단하게 됩니다. 본 엔진은 이 둘을 정밀하게 분리하여 정책 입안자가 실제 경관 변화의 역학을 올바르게 파악할 수 있도록 돕습니다.

**Q2: 마르코프 전이 확률 행렬은 미래 예측에 어떻게 활용되나요?**
> A: 2020년에서 2025년 사이의 전이 확률 행렬 $P$를 구하면, 현재의 개발 및 보전 추세가 유지된다는 가정 하에 5년 뒤(2030년)의 토지피복 분포를 $v(2030) = v(2025) \times P$로 간편하게 예측할 수 있습니다. 이는 산림 전용 방지 정책이나 도시계획 시나리오 평가에 매우 유용합니다.

**Q3: 웹 대시보드에는 어떻게 연계됩니까?**
> A: 엔진이 자동 생성하는 `sankey_data.json`은 출발 연도와 도착 연도의 18개 노드와 클래스 간 플로우(ha, %) 링크를 표준 규격으로 포함하고 있어, 프론트엔드의 Recharts/Plotly Sankey 뷰어에 그대로 전달되어 1클릭으로 대화형 전환 흐름 차트를 렌더링할 수 있습니다.
