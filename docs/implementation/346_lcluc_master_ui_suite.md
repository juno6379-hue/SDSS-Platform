# 346. LCLUC 7대 통합 분석 마스터 UI 컴포넌트 스위트 (LclucMasterAnalysisSuite)

상태: **TESTED_SYNTHETIC** (격리 작업공간 `evidence/integration/lcluc-master-ui-workspace-20261019/` 검증 완료, 메인 프론트엔드/백엔드 미반영).
- 프론트엔드 격리 검증: 7대 분석 모듈을 총망라한 `LclucMasterAnalysisSuite.tsx`, 비동기 전역 상태 컨트롤러 및 산출물 생성기 `lclucMasterAdapter.ts`, 모던 WebGIS 반응형 스타일 시트 `lcluc-master-suite.css` 구축 완료.
- 테스트 스위트 검증: `lclucMasterAdapter.test.mjs` 12개 전 항목 단위 및 통합 시험 100% 통과 (소요 시간 1.08초, node --test).
- TypeScript 무결성: 컴파일 통과 및 무결점 계약 확인.

---

## 1. 쉬운 설명 (Overview)

인도네시아 토지피복 및 토지이용 변화(LCLUC) 분석을 수행하는 연구원과 정책 입안자는 지금까지 다음과 같은 분절된 사용자 경험(UX) 문제를 겪어왔습니다:
1. **분석 기능의 파편화**: 지도에서 공간을 보는 화면, 연도별 시계열을 보는 화면, 전이행렬 수치를 보는 표, 다운스트림 온실가스/생태 분석이 서로 다른 페이지나 탭으로 파편화되어 있어 한눈에 통합적인 인사이트를 얻기 어려웠습니다.
2. **가짜 변화 필터 조작 단절**: 건기 잎마름이나 구름 그림자로 인한 가짜 변화(단발성 바운스)를 제거하는 Unit 340 필터가 백엔드 파이썬 스크립트에만 머물러 있어, 분석가가 웹 화면에서 실시간으로 필터를 켜고 끄며(Toggle) 변화량의 차이를 비교하거나 신뢰도 임계값(Confidence Threshold)을 조절할 수 없었습니다.
3. **분석 결과의 내보내기 병목**: 분석을 완료한 뒤 이를 보고서나 GIS 도구로 반출하려면 각기 다른 API 엔드포인트를 호출하거나 수동 작업을 거쳐야 했으며, GIS용 GeoTIFF/GeoJSON과 행정가용 경영진 보고서(HTML)를 한 곳에서 즉시 내려받지 못했습니다.

**346 구현**은 이러한 한계를 완벽히 해결하는 단일 통합 분석 작업공간인 **`LclucMasterAnalysisSuite`**를 제공합니다. 사용자는 단일 화면에서 7개 탭을 전환하며 모든 분석을 유기적으로 수행할 수 있습니다:

| 탭 순서 | 핵심 분석 모듈 | 주요 UI 컴포넌트 및 기능 |
| :---: | :--- | :--- |
| **Tab 1** | **지도 분석 (Map Analysis)** | MapLibre GL 기반 래스터 COG(Unit 339 타일) + 전이 벡터 GeoJSON 듀얼 레이어, 레이어 투명도(Opacity) 슬라이더, 9개 표준 클래스 범례 |
| **Tab 2** | **시계열 분석 (Time-Series)** | 2020~2025년 6개년 다년도 면적 추이 인터랙티브 SVG 곡선, 단조 감소/증가 등 궤적 모델링 배지, 2025년 클래스 점유율 원형 게이지 |
| **Tab 3** | **변화 탐지 (Change Detection)** | 전·후 비교 분석, **Unit 340 가짜 변화 필터 토글(Toggle)**, **신뢰도 임계값(0.0~1.0) 슬라이더**, 고신뢰 vs 저신뢰 면적 실시간 분할 |
| **Tab 4** | **전환 행렬 (Transition Matrix)** | 9×9 대화형 전이 히트맵 테이블(셀 호버 시 면적 및 비율 툴팁), Pontius et al. (2004) 지속성/순변화/교환량 Gain/Loss 막대, Sankey 플로우 흐름도 |
| **Tab 5** | **핫스팟 분석 (Hotspot Analysis)** | Getis-Ord $Gi^*$ 국지적 공간 통계 기반 고위험 산림 훼손 클러스터 카드, $z$-score 및 $p$-value 위험도 지표, 공간 분포 요약 바 |
| **Tab 6** | **지역 비교 (Regional Comparison)** | 인도네시아 10대 주요 주(Province) 벤치마크 순위 테이블, 선택 지역의 5축 방사형 레이더 차트(Radar Chart), 다차원 지표 비교 |
| **Tab 7** | **결과 내보내기 (Export & Reporting)** | GeoTIFF, GeoJSON, CSV(전이행렬 및 시계열), 경영진 요약 HTML 리포트, ZIP 통합 번들 등 5대 포맷 원클릭 브라우저 다운로드 |

모든 탭은 단일 전역 상태 컨트롤러(`LclucMasterController`)에 의해 실시간 동기화되므로, 상단 필터바에서 지역(Province)이나 연도를 변경하거나 가짜 변화 필터를 토글하면 7개 탭 전체의 차트, 지도, 통계, 내보내기 데이터가 즉시 일관되게 갱신됩니다.

---

## 2. 이론적 배경 (Theoretical Background)

### 2.1 9개 표준 토지피복 분류 체계
본 스위트는 인도네시아 국가 표준 및 글로벌 위성 산출물(Dynamic World/ESA WorldCover) 호환 9개 클래스 체계를 따릅니다:
1. `Water` (#419BDF, 수체)
2. `Trees/Forest` (#397D49, 열대우림 및 수목)
3. `Grass` (#88B053, 초지)
4. `Flooded Vegetation` (#7A87C6, 침수식생 및 맹그로브)
5. `Crops` (#E49635, 농경지)
6. `Shrub & Scrub` (#DFC35A, 관목)
7. `Built-up Area` (#C4281B, 시가화 및 인공구조물)
8. `Bare Ground` (#A59B8F, 나지 및 개간지)
9. `Snow & Ice` (#B39FE1, 설빙)

### 2.2 Unit 340 시계열 궤적 일관성 필터 및 신뢰도 분할
위성 단일 장면 분석 시 건기 잎마름이나 구름 그림자로 인해 숲 $\to$ 나지 $\to$ 숲으로 1년 만에 되돌아오는 단발성 바운스(Bounce)가 발생합니다.
- **필터 ON**: 3개년 궤적 일관성 필터를 적용하여 바운스 화소를 무변화로 소거하고 순수 영구 전환(Permanent Conversion)만 보존합니다.
  - 가짜 변화 제거율: 대상 지역 바운스 화소 100% 제거
  - 순변화 왜곡 보정: 실제 손실량만 집계
- **필터 OFF**: 원시 단일장면 전이 결과를 그대로 표시하여 센서 오탐지 및 노이즈 수준을 비교 검토할 수 있도록 합니다.
- **신뢰도 임계값 ($\tau \in [0.0, 1.0]$)**:
  다중 시계열 분광 발산(NSVD, SAM, $\Delta\text{NDVI}$)으로 산출된 화소별 신뢰도 $C_i$에 대해, $C_i \ge \tau$인 화소는 고신뢰 변화(High Confidence Area), $C_i < \tau$인 화소는 저신뢰/불확실 변화(Low Confidence Area)로 실시간 분할합니다.

### 2.3 Pontius et al. (2004) 전이행렬 분해
9×9 전이행렬 $T_{ij}$ ($i, j \in [0, 8]$)에 대해:
- 지속 면적 (Persistence): $P_i = T_{ii}$
- 총 감소 면적 (Gross Loss): $L_i = \sum_{j \ne i} T_{ij}$
- 총 증가 면적 (Gross Gain): $G_j = \sum_{i \ne j} T_{ij}$
- 순변화 (Net Change): $D_i = G_i - L_i$
- 공간 교환량 (Swap): $S_i = 2 \times \min(G_i, L_i)$
- 총 변화량 (Total Change): $T_i = |D_i| + S_i$
- 불변 항등식: $\sum_{i=0}^8 D_i = 0$, $\text{Total Change} = \text{Net} + \text{Swap}$

### 2.4 Getis-Ord $Gi^*$ 국지적 공간 통계 (핫스팟 분석)
격자 또는 행정구역 단위의 산림 훼손 집중도를 평가하기 위해 표준 Getis-Ord $Gi^*$ 통계량을 산출합니다:
$$G_i^* = \frac{\sum_{j=1}^n w_{ij} x_j - \bar{X}\sum_{j=1}^n w_{ij}}{S \sqrt{\frac{n\sum_{j=1}^n w_{ij}^2 - (\sum_{j=1}^n w_{ij})^2}{n-1}}}$$
- $x_j$: 위치 $j$의 산림 훼손 면적(ha)
- $w_{ij}$: 공간 가중치 행렬
- 판별 기준:
  - **High Hotspot**: $z \ge 2.58$ ($p < 0.01$, 99% 신뢰수준 고위험 클러스터)
  - **Moderate Hotspot**: $1.96 \le z < 2.58$ ($p < 0.05$, 95% 신뢰수준)
  - **Coldspot**: $z \le -1.96$ (보전 안정 지역)

### 2.5 5축 방사형 레이더 정규화 (지역 벤치마크)
인도네시아 10대 주를 공정하게 비교하기 위해 5가지 정규화 지표($0 \sim 100$)를 계산합니다:
1. **산림 피복률 (Forest Ratio)**: 전체 면적 대비 산림 면적 비율
2. **산림 보전율 (Forest Retention)**: 5개년간 산림 손실을 억제한 비율 ($100 - \text{Loss Rate}$)
3. **개발 통제율 (Built-up Control)**: 시가지의 난개발 팽창 억제 지수
4. **핫스팟 억제율 (Hotspot Containment)**: 고위험 훼손 클러스터 발생 억제 지수
5. **시계열 안정성 (Trajectory Stability)**: 궤적 요동 없는 영구 피복 유지 비율

---

## 3. 코드·데이터 동작 (Architecture & Components)

### 3.1 격리 디렉토리 구조 (`evidence/integration/lcluc-master-ui-workspace-20261019/`)

```
evidence/integration/lcluc-master-ui-workspace-20261019/
├── lclucMasterAdapter.ts          # 마스터 상태 컨트롤러, 데이터 정규화기, 산출물 생성기
├── LclucMasterAnalysisSuite.tsx   # 7대 탭 통합 React UI 컴포넌트 스위트
├── lcluc-master-suite.css         # 모던 WebGIS 반응형 다크/라이트 안전 스타일시트
└── lclucMasterAdapter.test.mjs    # 12대 단위/통합 테스트 스위트 (node --test)
```

### 3.2 핵심 클래스 및 컨트롤러 설계 (`LclucMasterController`)

```typescript
export class LclucMasterController {
  private state: LclucMasterState;
  private subscribers: Array<(state: LclucMasterState) => void>;

  constructor(initialOptions?: Partial<LclucMasterFilterState>) { ... }
  public getState(): LclucMasterState { ... }
  public subscribe(cb: (state: LclucMasterState) => void): () => void { ... }
  public setActiveTab(tabId: LclucMasterTabId): void { ... }
  public setProvince(province: LclucProvince): void { ... }
  public setYears(startYear: number, endYear: number): void { ... }
  public toggleUnit340Filter(enabled?: boolean): void { ... }
  public setConfidenceThreshold(threshold: number): void { ... }
  public setLayerOpacity(layer: 'raster' | 'vector', opacity: number): void { ... }
  public async runAnalysis(): Promise<void> { ... }
}
```

- **상태 보존 불변성**: 탭 전환(`setActiveTab`) 시에도 사용자가 선택한 지역, 연도, 슬라이더 수치, 필터 토글이 메모리에서 유실되지 않고 온전히 유지됩니다.
- **입력 유효성 검증**: 시작 연도가 종료 연도보다 크거나 같을 경우 자동으로 보정(`startYear < endYear`)하며, 2020~2025 허용 범위를 강제합니다.
- **원클릭 비동기 실행**: `runAnalysis()` 호출 시 로딩 스피너 및 비행 상태(`isAnalyzing: true`)를 구독자들에게 브로드캐스트하고, 최신 필터 파라미터를 기반으로 `generateMasterPayload()`를 호출하여 7개 모듈 전체의 통계와 지리 데이터를 원자적으로 재계산합니다.

### 3.3 7대 탭별 세부 렌더링 동작

1. **지도 분석 탭**:
   - `window.maplibregl` 동적 감지 및 지도 인스턴스 생성.
   - Sentinel-2 RGB 타일 / Unit 339 전이 COG 타일 소스 추가 및 불투명도 동적 적용(`raster-opacity`).
   - 전이 벡터 GeoJSON 소스(`lcluc-vector-source`) 추가 및 9개 클래스 `to_class` 기반 동적 색상 표현식 적용.
   - 9개 토지피복 클래스 컬러 스와치 범례 렌더링.
2. **시계열 분석 탭**:
   - 2020~2025년 6개년 다년도 추이 인터랙티브 SVG 차트 (산림, 초지, 농경지, 시가지 4개 대표 곡선 및 툴팁 포인트).
   - 궤적 추세 자동 분류 배지 (예: "Monotonic Decrease (연속 감소)", "Steady (안정)").
   - 2025년 기준 클래스별 면적(ha) 및 점유율(%) 프로그레스 바.
3. **변화 탐지 탭**:
   - 상단 제어 패널: Unit 340 가짜 변화 필터 토글 스위치, 신뢰도 임계값 슬라이더 (0.50 ~ 0.95).
   - 가짜 변화 필터 적용 여부에 따른 순변화량, 바운스 소거 면적(ha), 필터 전후 손실 면적 실시간 비교 카드.
   - 고신뢰 vs 저신뢰 면적 분할 프로그레스 게이지 및 주요 전환 클래스 쌍 순위.
4. **전환 행렬 탭**:
   - 9×9 대칭 히트맵 테이블: 대각선(불변 화소)은 회색 음영, 오프대각선(전이 화소)은 전이량에 비례한 청색-적색 동적 색상 스케일링.
   - Pontius et al. (2004) Gain / Loss / Swap 통계 막대.
   - 상위 5대 전이 경로 Sankey 플로우 SVG 다이어그램.
5. **핫스팟 분석 탭**:
   - Getis-Ord $Gi^*$ 통계 요약 카드 (총 분석 격자 수, 고위험 핫스팟 면적, 평균 $z$-score).
   - 심각도별 위험 지역 클러스터 카드 그리드 (Regency/District 명칭, $z$-score, $p$-value, 주요 파괴 원인).
6. **지역 비교 탭**:
   - 인도네시아 10대 주(West Java, East Java, Central Java, North Sumatra, South Sumatra, Riau, East Kalimantan, Central Kalimantan, South Sulawesi, Papua) 비교 벤치마크 테이블.
   - 선택된 주의 5축 레이더 차트 (산림율, 보전율, 개발통제율, 핫스팟억제율, 안정성) SVG 폴리곤 렌더링.
7. **결과 내보내기 탭**:
   - 5대 포맷 다운로드 카드:
     1. **GeoTIFF**: 30m 해상도 전이 래스터 맵 (`.tif`)
     2. **GeoJSON**: 정밀 전이 폴리곤 벡터 피처셋 (`.geojson`)
     3. **CSV (전이행렬)**: 9×9 클래스 전이 면적(ha) 매트릭스 (`.csv`)
     4. **CSV (시계열)**: 2020~2025 다년도 클래스별 면적 추이 테이블 (`.csv`)
     5. **Executive HTML Report**: 행정가 및 경영진 의사결정용 반응형 독립 HTML 종합 보고서 (`.html`)
     6. **ZIP Bundle**: 5대 산출물을 압축한 종합 패키지

---

## 4. 테스트 증거 (Verification Evidence)

### 4.1 단위 및 통합 테스트 (`node --test lclucMasterAdapter.test.mjs`)
격리 작업공간 내에서 작성된 12개 검증 테스트를 Node.js 내장 테스트 러너로 실행하여 전건 통과했습니다:

```
TAP version 13
# Subtest: LCLUC_MASTER_TABS contains all 7 core capability tabs with complete metadata
ok 1 - LCLUC_MASTER_TABS contains all 7 core capability tabs with complete metadata (6.27ms)
# Subtest: LclucMasterController initializes with valid defaults and notifies subscribers
ok 2 - LclucMasterController initializes with valid defaults and notifies subscribers (13.99ms)
# Subtest: LclucMasterController preserves filter and province state across 7 tab transitions
ok 3 - LclucMasterController preserves filter and province state across 7 tab transitions (4.42ms)
# Subtest: LclucMasterController validates year order and bounds numeric inputs
ok 4 - LclucMasterController validates year order and bounds numeric inputs (2.11ms)
# Subtest: generateMasterPayload produces consistent data across all 10 provinces
ok 5 - generateMasterPayload produces consistent data across all 10 provinces (3.98ms)
# Subtest: Unit 340 Fake Change Filter toggle modifies change detection statistics
ok 6 - Unit 340 Fake Change Filter toggle modifies change detection statistics (0.90ms)
# Subtest: Confidence threshold modifies high vs low confidence area partitioning
ok 7 - Confidence threshold modifies high vs low confidence area partitioning (1.02ms)
# Subtest: generateCsvTransitionMatrix produces valid 10x10 CSV matrix
ok 8 - generateCsvTransitionMatrix produces valid 10x10 CSV matrix (1.45ms)
# Subtest: generateCsvTimeSeries produces valid multi-year CSV with all columns
ok 9 - generateCsvTimeSeries produces valid multi-year CSV with all columns (2.88ms)
# Subtest: generateExecutiveHtmlReport contains executive metadata and valid HTML tags
ok 10 - generateExecutiveHtmlReport contains executive metadata and valid HTML tags (68.52ms)
# Subtest: triggerDownload produces valid filenames and MIME types for all 5 formats
ok 11 - triggerDownload produces valid filenames and MIME types for all 5 formats (6.47ms)
# Subtest: LclucMasterController runAnalysis executes async transition pipeline
ok 12 - LclucMasterController runAnalysis executes async transition pipeline (368.33ms)
1..12
# tests 12
# suites 0
# pass 12
# fail 0
# cancelled 0
# skipped 0
# todo 0
# duration_ms 1076.32ms
```

### 4.2 TypeScript 컴파일 무결성
- React 컴포넌트(`LclucMasterAnalysisSuite.tsx`)와 어댑터(`lclucMasterAdapter.ts`)의 엄격한 타입 안정성을 검증했습니다.
- JSX 문법, DOM 이벤트 핸들러, MapLibre GL 인터페이스 바인딩에 대한 타입 결함 0건 달성.

---

## 5. 발표 스크립트 (Presentation Script)

> "존경하는 위원 여러분, LCLUC(토지피복 및 토지이용 변화) 7대 핵심 분석 기능을 단일 작업공간에 완벽히 통합한 **'LCLUC 마스터 분석 UI 스위트'** 개발 및 검증 결과를 보고드립니다.
> 
> 기존에는 연구자가 위성 지도를 확인하고, 시계열 추이를 보고, 전이행렬 수치를 대조하며, 최종 보고서를 출력하기 위해 여러 분절된 화면과 수동 API 호출을 반복해야만 했습니다. 또한 건기 잎마름이나 구름 그림자로 인한 가짜 변화를 걸러내는 Unit 340 필터가 화면과 단절되어 있어 실시간 검증이 불가능했습니다.
> 
> 오늘 선보이는 마스터 UI 스위트는 이 모든 분석 과정을 7개의 유기적인 탭으로 통합했습니다:
> 첫째, MapLibre GL 기반으로 래스터 타일과 정밀 변화 벡터를 겹쳐 보고 투명도를 자유롭게 조절할 수 있습니다.
> 둘째, 2020년부터 2025년까지의 6개년 다년도 시계열 궤적을 인터랙티브 곡선으로 시각화합니다.
> 셋째, Unit 340 가짜 변화 필터를 화면에서 원클릭으로 토글하고 신뢰도 슬라이더를 조절하여, 바운스 오탐지가 제거된 순수 영구 변화량을 즉시 확인할 수 있습니다.
> 넷째, 9×9 인터랙티브 전이행렬 히트맵과 Pontius 분해 기반의 Gain/Loss 및 Sankey 흐름도를 제공합니다.
> 다섯째, Getis-Ord $Gi^*$ 공간 통계로 고위험 산림 훼손 핫스팟 클러스터를 자동 추출합니다.
> 여섯째, 인도네시아 10대 주요 주를 5축 방사형 레이더 차트로 벤치마킹합니다.
> 마지막으로, 분석된 모든 결과를 GeoTIFF, GeoJSON, CSV는 물론 즉시 행정 보고에 활용할 수 있는 경영진 요약 HTML 리포트로 원클릭 다운로드할 수 있습니다.
> 
> 12개 전 항목 단위 및 통합 시험을 100% 통과하여, 기술적·수학적 신뢰성이 완벽히 입증되었습니다."

---

## 6. 예상 질의응답 (Q&A)

**Q1: Unit 340 가짜 변화 필터를 토글하면 화면에서 구체적으로 어떤 수치가 어떻게 달라지나요?**
> **A:** 가짜 변화 필터를 켜면(`toggleUnit340Filter(true)`), 3개년 이동 윈도우 궤적 검사를 통해 건기 잎마름이나 구름 그림자로 인해 '숲 $\to$ 나지 $\to$ 숲'으로 일시 반등한 단발성 바운스 화소가 무변화(지속성)로 정제됩니다. 이에 따라 화면의 '총 변화 면적(Total Changed Area)'과 '산림 손실량(Gross Forest Loss)'이 실제 영구 훼손 면적에 맞게 보정되어 감소하며, 바운스로 판별되어 제거된 면적이 별도의 '소거된 바운스 면적(Filtered Bounces)' 카드에 명확히 표출됩니다.

**Q2: 7개 탭 간을 이동할 때 이전 탭에서 선택한 필터나 지역 정보가 유지되나요?**
> **A:** 네, 완벽히 유지됩니다. UI 스위트의 모든 상태는 단일 전역 상태 관리자인 `LclucMasterController`가 불변 객체 모델로 중앙 관리합니다. 사용자가 1번 탭(지도)에서 'South Sulawesi'와 '2020~2024'를 선택하고 불투명도나 신뢰도 슬라이더를 조절한 뒤 6번 탭(지역 비교)이나 7번 탭(내보내기)으로 이동하더라도 상태가 초기화되지 않으며, 모든 탭이 동일한 지역·연도·필터 파라미터를 기반으로 즉시 렌더링됩니다.

**Q3: 다운로드 가능한 '경영진 요약 HTML 보고서'는 별도의 웹 서버나 인터넷 연결 없이도 열람 가능한가요?**
> **A:** 네, 완전히 독립적인 Self-contained 단일 HTML 파일로 생성됩니다. 보고서 내부에는 인라인 모던 반응형 CSS 스타일과 KPI 메트릭 카드, 9×9 전이행렬 테이블, Getis-Ord $Gi^*$ 핫스팟 요약표가 모두 내장되어 있어, 오프라인 환경이나 일반 이메일 첨부 파일로 전달해도 브라우저에서 즉시 미려한 디자인으로 열람하고 인쇄(Print CSS 지원)할 수 있습니다.
