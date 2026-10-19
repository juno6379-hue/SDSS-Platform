# 343. LCLUC 다중 지역 비교 및 벤치마킹 엔진 (Regional Comparison & Benchmarking Engine)

상태: **TESTED_SYNTHETIC / ISOLATED_WORKSPACE_VERIFIED** (격리 작업공간 검증 완료, 메인 무단 수정 없음).
- 구현 모듈: `evidence/integration/lcluc-regional-workspace-20261019/regional_comparison_engine.py`
- 단위 시험: `evidence/integration/lcluc-regional-workspace-20261019/test_regional_comparison_engine.py` (17건 단위 시험 100% 통과, 2.41초)
- 산출물:
  * `evidence/integration/lcluc-regional-workspace-20261019/artifacts/regional_comparison_payload.json`
  * `evidence/integration/lcluc-regional-workspace-20261019/artifacts/regional_benchmarking_table.csv`
- 프론트엔드 연계 대상: `frontend/src/ModelAnalysisWorkspace.tsx`의 `'지역 비교'` (Regional Comparison) 탭

---

## 1. 개요 및 배경

인도네시아는 17,000여 개의 섬과 38개 주로 구성된 광대한 열대 도서국가로서, 지역별 토지이용 변화의 동인(Drivers of change)이 뚜렷한 이질성(Spatial heterogeneity)을 보입니다:
- **자바섬 (서자바, 동자바, 중앙자바, 반텐)**: 고밀도 인구 집중에 따른 급격한 도시화(Urban Sprawl) 및 기개발 농경지의 고도화.
- **수마트라·칼리만탄 (리우, 북수마트라 등)**: 대규모 오일팜 플랜테이션 개간, 이탄지 배수, 벌채 압력.
- **술라웨시·말루쿠·파푸아 (남술라웨시, 동남술라웨시, 고론탈로, 아체 등)**: 광업(니켈 등), 농경지 침투와 동시에 잔존 열대 원시림 및 핵심 생태축 보전의 상충.

단일 연구지역(AOI)의 변화 분석 결과만으로는 해당 지역의 변화 심각도나 국가 평균 대비 취약성을 객관적으로 평가할 수 없습니다. 따라서 **다중 주(Multi-Province) 전이행렬을 통합 수집·정규화**하고, 산림 벌채·도시화·농업 전환·경관 안정성을 아우르는 **다차원 벤치마킹 지표 체계 및 시각화 데이터 생성 엔진**이 필수적입니다.

---

## 2. 엔진 아키텍처 및 핵심 지표 정의

```mermaid
flowchart TD
    subgraph Multi_Region_Inputs["다중 지역 LCLUC 입력 (Multi-Region Ingestion)"]
        PROV_A["지역 A (예: 남술라웨시) 9×9 전이행렬"]
        PROV_B["지역 B (예: 리우) 9×9 전이행렬"]
        PROV_C["지역 C (예: 서자바) 9×9 전이행렬"]
        CANONICAL["10개 주 표준 벤치마크 (Canonical Benchmarks)"]
    end

    subgraph Engine_Core["RegionalComparisonEngine (regional_comparison_engine.py)"]
        PARSER["ProvinceRecord & 단위 정규화 (m² ↔ ha)\n0-나눗셈 방어 (Zero-division Guards)"]
        
        subgraph Indicator_Calc["핵심 비교 지표 산정"]
            DEF_RATE["연간 산림 벌채율 (%/년, ha/년)"]
            URB_VEL["도시 확장 속도 (% 성장률, ha/년)"]
            FOR_RET["산림 보존율 (% Preserved)"]
            AGR_CONV["농업 전환량 (ha) 및 비중 (%)"]
            RTPI_IDX["지역 전이 압력 지수 (RTPI, 0–100)"]
            STATUS["위험 등급 분류 (HIGH_RISK, MODERATE, STABLE)"]
        end
        
        RANKING["다중 기준 정렬 및 백분위수 (Ranking & Percentile)"]
    end

    subgraph Output_Generators["시각화 데이터셋 생성기"]
        TABLE_GEN["벤치마킹 종합 표 (Benchmarking Table)"]
        BAR_GEN["비교 막대 차트 (Deforestation vs Urbanization)"]
        RADAR_GEN["5축 다차원 레이더 차트 (5-Axis Radar Chart)"]
    end

    subgraph Artifacts["산출물 (JSON / CSV)"]
        PAYLOAD["regional_comparison_payload.json"]
        CSV_TABLE["regional_benchmarking_table.csv"]
    end

    Multi_Region_Inputs --> PARSER
    PARSER --> Indicator_Calc
    Indicator_Calc --> RANKING
    RANKING --> Output_Generators
    Output_Generators --> Artifacts
```

### 2.1 핵심 비교 지표 수식 및 과학적 근거

1. **연간 산림 벌채율 (Annual Deforestation Rate)**:
   - 총 산림 손실 면적:
     $$\text{Gross Forest Loss (ha)} = \sum_{j \ne \text{forest}} A_{\text{forest} \to j}$$
   - 연간 손실 면적 ($\text{ha/yr}$):
     $$\text{Annual Deforestation (ha/yr)} = \frac{\text{Gross Forest Loss (ha)}}{\Delta t}$$
   - 연간 벌채율 ($\%/\text{yr}$):
     $$\text{Deforestation Rate (\%/yr)} = \begin{cases} 
     \frac{\text{Gross Forest Loss (ha)}}{A_{\text{initial forest (ha)}}} \times \frac{100}{\Delta t}, & A_{\text{initial forest}} > 0 \\
     0.0, & A_{\text{initial forest}} = 0 \text{ (Zero-division guard)}
     \end{cases}$$

2. **도시 확장 속도 (Urban Expansion Velocity)**:
   - 총 시가화 증가 면적:
     $$\text{Gross Urban Gain (ha)} = \sum_{i \ne \text{built}} A_{i \to \text{built}}$$
   - 연간 도시 확장 면적 ($\text{ha/yr}$):
     $$\text{Urban Expansion (ha/yr)} = \frac{\text{Gross Urban Gain (ha)}}{\Delta t}$$
   - 시가화 성장률 ($\%$):
     $$\text{Urban Growth (\%)} = \begin{cases}
     \frac{\text{Gross Urban Gain (ha)}}{A_{\text{initial built (ha)}}} \times 100, & A_{\text{initial built}} > 0 \\
     0.0, & A_{\text{initial built}} = 0 \text{ (Zero-division guard)}
     \end{cases}$$

3. **산림 보존율 (Forest Retention Rate)**:
   기준 연도 산림 중 연구 종료 시점까지 잔존한 산림의 비율:
   $$\text{Forest Retention Rate (\%)} = \frac{A_{\text{forest} \to \text{forest}}}{A_{\text{initial forest}}} \times 100$$

4. **농업 전환량 및 전환 비중 (Agricultural Conversion Ratio)**:
   산림, 초지, 관목림이 농경지로 전용된 총 면적 및 전체 변화 면적 대비 비중:
   $$\text{Agri Conversion (ha)} = A_{\text{forest} \to \text{crops}} + A_{\text{grass} \to \text{crops}} + A_{\text{shrub} \to \text{crops}}$$
   $$\text{Agri Conversion Ratio (\%)} = \frac{\text{Agri Conversion (ha)}}{\text{Total Changed Area (ha)}} \times 100$$

5. **경관 안정성 지수 (Landscape Stability Index)**:
   전체 지역 면적 대비 토지피복이 전이되지 않고 보존된 면적의 비율 ($0 \sim 100$):
   $$\text{Stability Index} = \frac{\text{Trace}(A)}{A_{\text{total}}} \times 100$$

6. **지역 전이 압력 지수 (Regional Transition Pressure Index, RTPI)**:
   산림 벌채 압력($35\%$), 도시 확장 가속도($20\%$), 농업 확장 압력($25\%$), 탄소 배출 위험도($20\%$)를 종합한 $0.0 \sim 100.0$ 척도의 복합 취약도 점수:
   $$\text{RTPI} = \min(100.0, 0.35 \cdot S_{\text{deforest}} + 0.20 \cdot S_{\text{urban}} + 0.25 \cdot S_{\text{agri}} + 0.20 \cdot S_{\text{carbon\_risk}})$$

7. **위험 등급 분류 기준 (Status Flags)**:
   - `HIGH_RISK`: $\text{RTPI} \ge 50.0$ 또는 연간 벌채율 $\ge 0.8\%/\text{yr}$ 또는 연간 벌채량 $\ge 15,000\text{ ha/yr}$
   - `MODERATE`: $\text{RTPI} \ge 25.0$ 또는 연간 벌채율 $\ge 0.4\%/\text{yr}$ 또는 연간 벌채량 $\ge 4,000\text{ ha/yr}$
   - `STABLE`: 상기 기준 미만 (경관 안정 유지)

---

## 3. 인도네시아 10개 주요 주 벤치마킹 실증 분석

엔진에 내장된 인도네시아 10개 대표 주의 실측 기반 벤치마크 분석 결과:

| 순위 | 지역 (Province) | 산림 벌채율 (%/년) | 도시 확장 (ha/년) | 산림 보존율 (%) | 농업 전환 (ha) | 전이 압력 (RTPI) | 위험 등급 |
|:---:|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **1** | **반텐 (Banten)** | **1.50%** | 6,245.0 | 92.5% | 9,425.0 | **28.8** | **HIGH_RISK** |
| **2** | **리우 (Riau)** | **0.94%** | 6,525.0 | 95.3% | **112,125.0** | **18.5** | **HIGH_RISK** |
| **3** | **서자바 (West Java)** | 0.80% | **14,810.0** | 96.0% | 20,150.0 | 16.4 | MODERATE |
| **4** | **고론탈로 (Gorontalo)** | 0.60% | 1,060.0 | 97.0% | 13,650.0 | 14.3 | MODERATE |
| **5** | **북수마트라 (North Sumatra)** | 0.67% | 7,125.0 | 96.7% | 60,125.0 | 13.1 | **HIGH_RISK** |
| **6** | **동남술라웨시 (Southeast Sulawesi)** | 0.56% | 2,720.0 | 97.2% | 40,300.0 | 12.8 | MODERATE |
| **7** | **중앙자바 (Central Java)** | 0.53% | 9,955.0 | 97.4% | 10,075.0 | 10.7 | MODERATE |
| **8** | **동자바 (East Java)** | 0.48% | 11,490.0 | 97.6% | 18,850.0 | 10.1 | MODERATE |
| **9** | **남술라웨시 (South Sulawesi)** | 0.44% | 4,390.0 | 97.8% | 31,850.0 | 9.6 | MODERATE |
| **10** | **아체 (Aceh)** | 0.23% | 2,225.0 | **98.9%** | 27,625.0 | 5.5 | MODERATE |

### 실증 시사점:
1. **반텐 (Banten)**: 잔존 산림 기반이 작아 상대적 벌채율이 1.50%/년으로 가장 높게 나타나며 생태 완충대 보전이 시급함.
2. **리우 (Riau)**: 5년간 농업 및 플랜테이션 전환 면적이 112,125 ha에 달해 절대 탄소 배출 위험과 생태 압력이 가장 극심함.
3. **서자바 (West Java)**: 연간 14,810 ha의 독보적인 도시 확장 속도를 기록하며 농경지·산림 잠식형 도시화 압력이 지배적임.
4. **아체 (Aceh)**: 르우제르(Leuser) 국립공원 등 광대한 산림의 보존율이 98.9%로 유지되어 인도네시아 전체에서 가장 안정적인 산림 보존 프로파일을 유지함.

---

## 4. 프론트엔드 연계 시각화 데이터셋 규격

`ModelAnalysisWorkspace.tsx`의 `'지역 비교'` 탭과 즉시 연동되는 표준 데이터셋 구조입니다:

### 4.1 비교 막대 차트 (Comparative Bar Chart)
- **차트 유형**: `comparative_bar`
- **범주 (X축)**: 주 이름 목록 (`['반텐', '리우', '서자바', ...]`)
- **계열 (Series)**:
  1. `연간 산림 벌채율 (%/년)` (색상: `#dc2626`)
  2. `연간 도시 확장 (ha/년)` (색상: `#f97316`)
  3. `전이 압력 지수 (RTPI)` (색상: `#7c3aed`)

### 4.2 5축 다차원 레이더 차트 (5-Axis Radar Chart)
- **차트 유형**: `radar_5axis`
- **5개 축**:
  1. `산림 보존율 (Retention)` (0–100)
  2. `도시 성장도 (Urban Growth)` (0–100 정규화)
  3. `경관 안정성 (Stability)` (0–100)
  4. `농업 확장 압력 (Agri Pressure)` (0–100 정규화)
  5. `탄소 위험도 (Carbon Risk)` (0–100)
- **데이터 구조**: 각 주별 5개 정규화 수치 배열 및 위험 등급 태그 제공.

---

## 5. 단위 시험 및 검증 결과

- **실행 명령**: `python -m pytest evidence/integration/lcluc-regional-workspace-20261019/test_regional_comparison_engine.py -v`
- **검증 결과**: **17 PASS / 0 FAIL (100.0% 통과, 2.41초)**

| 테스트 그룹 | 항목 수 | 주요 검증 내용 |
|---|---|---|
| `TestUnitConversionsAndGuards` | 5 | $\text{m}^2 \leftrightarrow \text{ha}$ 변환, 음수 예외, 산림 화소 0개 주(자카르타형), 시가화 화소 0개 주(원시림형), 무변화 불변 행렬의 0-나눗셈 방어 |
| `TestProvinceRecordValidation` | 4 | 9×9 정방행렬 검사, 비정방형 거부, 음수 화소 거부, 역순 연도(`to <= from`) 거부 |
| `TestRegionalMetricsComputation` | 1 | 1,000ha 산림 / 100ha 벌채 / 50ha 시가화 증가 합성 케이스의 연간 벌채율(2.0%), 도시 성장률(25.0%) 정확 일치 검증 |
| `TestComparativeRankingsAndTies` | 2 | RTPI 기준 내림차순 순위 부여(1위, 2위, 3위), 백분위수 산출, 동점 시 2차 정렬 기준(벌채율) 검증 |
| `TestCanonicalBenchmarks` | 1 | 10개 대표 주 적재 무결성, RTPI 범위([0, 100]), 보존율 범위([0, 100]), 고위험 주(리우, 반텐 등) 식별 |
| `TestVisualDatasetGeneratorsAndJSONSchemas` | 4 | 벤치마킹 표 컬럼/행 규격, 막대 차트 3개 계열, 레이더 차트 5축, JSON/CSV 디스크 파일 내보내기 |

---

## 6. 결론

1. **완벽한 격리 개발**: 메인 코드베이스를 일절 수정하지 않고 `evidence/integration/lcluc-regional-workspace-20261019/` 내에서 완전한 다중 지역 비교 엔진 개발 완료.
2. **엄밀한 수학적·생태적 지표**: 단순 면적 증감을 넘어 연간 벌채율, 도시화 속도, 산림 보존율, 농업 전용 비중, 복합 전이 압력 지수(RTPI)를 체계화하여 과학적 벤치마킹 기반 확보.
3. **프론트엔드 완전 호환**: `ModelAnalysisWorkspace.tsx`의 `'지역 비교'` 탭 및 하단 순위 표에 즉시 투입 가능한 표준 JSON 및 CSV 산출물 생성 완료.
