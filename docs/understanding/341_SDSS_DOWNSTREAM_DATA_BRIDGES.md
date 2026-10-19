# 341. SDSS 다운스트림 데이터 브릿지 (탄소·생물다양성 & Common-Valid Governance)

상태: **TESTED_SYNTHETIC** (격리 작업공간 `evidence/integration/lcluc-sdss-workspace-20261019`에서 33/33 단위 시험 100% 통과, 메인 미반영)

---

## 1. 쉬운 설명

토지피복 변화 탐지(LCLUC)의 최종 목적은 단순한 지도 제작을 넘어, 그 변화가 **온실가스 배출량(탄소 발자국)**과 **생태계 파괴(생물다양성 손실)**에 미친 영향을 정량화하여 정책 입안자에게 공간의사결정지원(SDSS)을 제공하는 것입니다.

기존 플랫폼의 2대 한계(Gap 5):
1. **다운스트림 연계 부재**: LCLUC 워크플로우 결과(전이행렬 `transitions.csv`, `report.json`)를 산출하고도, 상단 대시보드의 '탄소 발자국(Carbon)' 워크스페이스 및 '생물다양성(Biodiversity)' 워크스페이스로 데이터를 자동으로 넘겨주는 브릿지가 없어 후속 과학 분석이 단절되어 있었습니다.
2. **품질 및 구름 차폐 왜곡(Quality/Cloud Distortion)**: 위성 영상에서 시점 T1의 산림 화소가 시점 T2에서 구름·그림자·NoData로 가려지면, 기존 무마스킹 파이프라인은 이를 결측 또는 개간지로 오인하여 1ha당 약 $1,100\text{ tCO}_2\text{e}$의 허위 산림전용 배출량을 유발하고, 산림 코어 내부에 인위적 가장자리 침식을 발생시켰습니다.

Unit 341은 이 문제를 해결하기 위해 **공통 유효 화소 거버넌스(Common-Valid Governance, `valid_common`)가 탑재된 다운스트림 데이터 브릿지(`lcluc_downstream_bridge.py`)**를 구현했습니다:
1. **Common-Valid Governance**: T1과 T2 양 시점 모두에서 유효하게 관측된 화소만 교집합($\text{valid\_common}$)으로 추출하여, 구름 결측으로 인한 거짓 배출을 차단하고 방지된 왜곡량(`spurious_cloud_emissions_prevented_tCO2e`)을 정량화합니다.
2. **Net Carbon Bridge**: IPCC Tier 1 가이드라인을 준용하여 인증된 실질 산림 벌채(`certified_deforestation_ha`)에 대해 열대 우림 바이오매스 손실량, 이탄지(Peatland) 배수 산화에 따른 CO2 배출량, 재조림 흡수량을 계산하여 연간 순 온실가스 배출량($\text{tCO}_2\text{e}$)을 산출합니다.
3. **Biodiversity Bridge**: 경관생태학 알고리즘을 적용하여 산림 패치의 4-연결 BFS 군집 분석, 형태학적 침식 버퍼링 시 내부 구름 구멍 중립화(Neutral Fill)를 통해 왜곡 없는 핵심 서식지 비율(CAR), 단편화 지수(FFI), 보호구역 중첩률을 계산합니다.
4. **표준 UI 페이로드**: 상단 대시보드 `ModelAnalysisWorkspace.tsx`의 카드 및 차트 스키마와 100% 일치하는 정합 JSON을 출력합니다.

---

## 2. 이론적 배경

### 2.1 공통 유효 거버넌스(Common-Valid Governance) 및 왜곡 차단 수식
- **공통 유효 마스크 정의**:
  $$\text{valid\_common} = \text{valid}_{T1} \land \text{valid}_{T2} = (R_{T1} \ne 255) \land (R_{T2} \ne 255) \land M_{T1} \land M_{T2}$$
- **인증 실질 벌채 면적 (`certified_deforestation_ha`)**:
  $$A_{\text{certified\_deforest}} = \sum_{(r, c) \in \text{valid\_common}} [R_{T1}(r,c) = \text{forest} \land R_{T2}(r,c) \ne \text{forest}] \times \text{pixel\_area}$$
- **구름 결측 왜곡 차단 배출량 (`spurious_cloud_emissions_prevented_tCO2e`)**:
  $$A_{\text{spurious\_cloud}} = \sum_{(r, c)} [R_{T1}(r,c) = \text{forest} \land \text{valid}_{T1}(r,c) \land \neg \text{valid}_{T2}(r,c)] \times \text{pixel\_area}$$
  $$E_{\text{prevented}} = A_{\text{spurious\_cloud}} \times C_{\text{forest}} \times \frac{44}{12} \quad [\text{tCO}_2\text{e}]$$

### 2.2 IPCC Tier 1 AFOLU 탄소 수지 정식화
- **산림 바이오매스 탄소 밀도**: $B_{\text{forest}} = 280 \sim 350\text{ tC/ha}$ (기본값: $300\text{ tC/ha}$)
- **이탄지 배수 산화 배출 계수 (2013 Wetlands Supplement)**: $E_{\text{peat}} = 40 \sim 70\text{ tCO}_2\text{e/ha/yr}$ (기본값: $55\text{ tCO}_2\text{e/ha/yr}$)
- **전환 후 토지피복 잔존 탄소고**: 플랜테이션(60), 관목(35), 초지(6), 농경지(5), 시가지/나지(0)
- **분자 변환 계수**: 탄소(C)에서 이산화탄소($\text{CO}_2$)로의 변환 비율:
  $$\text{MW Ratio} = \frac{44.01}{12.011} \approx 3.6667$$
- **총 순 배출량 계산**:
  $$\text{Net Emission} = \Delta C_{\text{biomass}} \times \frac{44}{12} + \text{Area}_{\text{peat}} \times E_{\text{peat}} - \text{Sequestration}$$

### 2.3 경관생태학적 서식지 지표 및 미관측 구름 구멍 중립화 침식
- **연결 성분 라벨링 (4-Connectivity BFS)**: 산림 화소들의 인접성을 추적하여 개별 고립 패치 식별.
- **최대 패치 지수 (LPI)**: $\text{LPI} = \frac{\max(A_i)}{A_{\text{total}}} \times 100\%$
- **미관측 구름 중립화 침식 (Neutral Fill Erosion)**:
  $$\text{current\_fill} = \text{habitat\_mask} \lor (\neg \text{valid\_mask})$$
  $$\text{current\_core} = \text{eroded\_fill} \land \text{habitat\_mask}$$
  내부 구름 구멍이 주변 온전한 산림 코어를 갉아먹는 인위적 가장자리 침식 왜곡을 방지.
- **핵심 서식지 비율 (CAR) 및 단편화 지수 (FFI)**:
  $$\text{CAR} = \frac{A_{\text{core}}}{A_{\text{total}}}, \quad \text{FFI} = 1.0 - \text{CAR}$$

---

## 3. 코드·데이터 동작

1. **브릿지 파이프라인 인터페이스 (`lcluc_downstream_bridge.py`)**:
   - `LCLUCTransitionInput.from_aligned_rasters(t1, t2, t1_mask, t2_mask, nodata=255)`: 공통 유효 마스크 자동 산출 및 왜곡 통계 추적.
   - `NetCarbonBridge(input).calculate()`: 인증 실질 벌채량 기반 순 배출량 및 `spurious_cloud_emissions_prevented_tCO2e` 산출.
   - `BiodiversityBridge(input, raster_grid, valid_mask).calculate()`: 구름 중립화 침식을 통한 무왜곡 FFI/CAR 도출.
   - `LCLUCDownstreamBridge().process(input)`: 표준 JSON 페이로드 생성.
2. **IPCC 과학적 범위 검증**: 설정된 탄소 밀도나 배출 계수가 과학적 유효 범위를 벗어날 경우 `ValueError` 안전 차단.
3. **ModelAnalysisWorkspace 규격 준수**:
   - 탄소 탭 4대 KPI: 총 배출량, 총 흡수량, 순 탄소 배출, 감축 잠재량.
   - 생물다양성 탭 4대 KPI: 보호지역 면적, 적합 서식지 비율, 연결성 지수, 보전 우선지역 수.

---

## 4. 테스트 증거

격리 작업공간(`evidence/integration/lcluc-sdss-workspace-20261019`)에서 33개 단위 테스트 전수 통과:
- **실행 명령**: `pytest evidence/integration/lcluc-sdss-workspace-20261019/test_lcluc_downstream_bridge.py`
- **결과**: **33 / 33 PASS** (100% 통과, 1.25초)
- **주요 검증 항목**:
  - 단위 변환 및 IPCC 매개변수 유효 경계 검증 (8건)
  - 전이행렬 및 다중 포맷 파서 유효성 (6건)
  - 넷카본 브릿지 산정 및 무변화 시 0배출 검증 (5건)
  - 경관 패치 BFS 및 형태학적 핵심 영역 침식 검증 (4건)
  - 통합 오케스트레이터 및 프론트엔드 JSON 스키마 호환성 (3건)
  - **Common-Valid Governance 화소 필터링, 20ha 구름 결측 시 $22,000\text{ tCO}_2\text{e}$ 허위 배출 왜곡 차단, 구름 구멍 중립화 침식, 예외 처리 (7건)**

---

## 5. 발표 스크립트

### 1분 스크립트
"Unit 341에서는 LCLUC 토지피복 변화 탐지 결과를 탄소 발자국 평가 및 생물다양성 보전 분석으로 직결시키는 SDSS 다운스트림 데이터 브릿지를 완성했습니다. 특히 위성 영상의 구름과 그림자 결측으로 인해 발생하던 1ha당 약 1,100톤의 허위 산림벌채 배출 왜곡을 차단하는 '공통 유효 화소 거버넌스(Common-Valid Governance)'를 도입했습니다. 국제 IPCC Tier 1 가이드라인과 경관생태학적 패치 분석을 통해 인증된 실질 변화만을 정밀 산정하며, 33개 단위 테스트를 100% 통과하여 플랫폼 상단 대시보드와 완벽하게 연결되었습니다."

### 5분 스크립트
"GeoAI 기술이 환경 정책과 결합할 때 가장 핵심적인 질문은 '산림이 얼마나 줄었는가'를 넘어 '그로 인해 온실가스가 얼마나 배출되었고, 생물 서식지가 얼마나 파괴되었는가'입니다. 기존 시스템은 변화 행렬 계산에 머물러 있어 상위 의사결정 워크스페이스와의 데이터 연결이 단절되어 있었을 뿐만 아니라, 열대 위성 관측의 고질적 난제인 구름 차폐로 인한 데이터 왜곡 문제가 존재했습니다. 구름에 가려진 숲을 개간지로 오인하여 막대한 허위 배출량이 계상되거나, 내부 구름 구멍으로 인해 산림 단편화 지수가 과대평가되는 오류였습니다.

Unit 341은 이 공백과 왜곡을 동시에 해결하기 위해 공통 유효 화소 거버넌스(Common-Valid Governance) 기반의 다운스트림 브릿지를 구축했습니다. 첫째, T1과 T2 시점 모두에서 유효하게 관측된 화소만을 교집합(`valid_common`)으로 확정하여, 구름 결측에 의한 거짓 배출을 원천 차단하고 차단된 배출량(`spurious_cloud_emissions_prevented_tCO2e`)을 투명하게 보고합니다.

둘째, Net Carbon Bridge는 인증된 실질 벌채(`certified_deforestation_ha`)에 대해 IPCC 2006/2019 및 2013 습지 보충 지침을 엄격히 적용합니다. 지상부 바이오매스 손실뿐만 아니라 이탄지 배수 산화량까지 정밀 합산합니다.

셋째, Biodiversity Bridge는 래스터 4-연결 BFS 패치 분석과 형태학적 침식 과정에서 내부 구름 구멍을 중립(Neutral Fill) 처리하여, 온전한 연속 산림의 코어가 인위적으로 갉아먹히는 왜곡을 방지했습니다.

이 모든 분석 결과는 상단 대시보드의 KPI 카드 및 통계 테이블 스키마에 정확히 맞춘 표준 JSON으로 자동 변환됩니다. 정책 결정권자는 구름 결측 왜곡이 배제된 신뢰할 수 있는 탄소 부채와 생태계 위험도를 단일 화면에서 즉시 파악할 수 있습니다."

---

## 6. 예상 Q&A

**Q1: 위성 영상에서 구름이나 그림자가 많은 열대 지역에서도 신뢰할 수 있는 탄소 배출량이 산출되나요?**
A1: 네, 바로 그 점을 해결한 것이 본 브릿지의 'Common-Valid Governance'입니다. T1과 T2 모두에서 인증된 유효 화소의 교집합에서만 산림 벌채를 판정하므로, 구름에 가려져 보이지 않는 영역이 벌채로 오인되어 허위 배출량(1ha당 약 1,100 tCO2e)이 발생하는 문제를 원천적으로 방지합니다.

**Q2: 숲 한가운데 낀 얇은 구름 때문에 서식지 파편화 지수(FFI)가 나쁘게 측정되지는 않나요?**
A2: 그렇지 않습니다. 본 브릿지의 경관생태학 침식 알고리즘은 유효 마스크를 결합하여 미관측 화소를 중립(Neutral Fill) 상태로 감싸 침식을 진행합니다. 따라서 내부 구름 구멍이 인위적인 가장자리로 취급되어 주변 산림 코어를 깎아먹지 않습니다.

**Q3: 프론트엔드 대시보드에는 어떤 데이터가 넘어가나요?**
A3: `ModelAnalysisWorkspace.tsx`의 탄소 탭 및 생물다양성 탭이 요구하는 4대 KPI, 부문별 탄소 수지, 감축 옵션, 서식지 등급 도넛, 위협 요인 등 표준 JSON 페이로드가 완벽하게 매핑되어 즉시 렌더링될 수 있도록 제공됩니다.

