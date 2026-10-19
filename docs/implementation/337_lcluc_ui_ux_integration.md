# 337. LCLUC UI/UX 통합 — ModelAnalysisWorkspace와 LclucWorkflowPanel 연계 상태 어댑터

상태: **TESTED_SYNTHETIC**. 격리 작업공간(`evidence/integration/lcluc-ui-workspace-20261019/`)에서 `lclucIntegratedWorkspaceAdapter.ts` 구현, `LclucIntegratedWorkspace.tsx` UI 컴포넌트 개발 및 18개 전 항목 단위·통합 시험을 100% 통과했습니다. 기존 메인 브랜치 코드(`frontend/src/`)를 훼손하지 않고 격리 설계·검증되었습니다.

---

## 1. 쉬운 설명 (Overview)

인도네시아 토지피복 및 토지이용 변화 분석(LCLUC)을 사용하는 분석가는 화면 최상단의 웹 대시보드(`ModelAnalysisWorkspace.tsx`)에서 **지역(Province)**과 **시작 연도(Start Year)**, **종료 연도(End Year)**를 선택한 후 상단의 **"분석 실행"** 버튼을 누릅니다.

그러나 기존 구현에서는 심각한 UX 단절(**Gap 1**)이 존재했습니다:
1. **요청 자동 생성 부재**: 상단에서 "South Sulawesi", "2020", "2021"을 선택해도, 하단의 워크플로 엔진(`LclucWorkflowPanel.tsx`)은 사용자가 텍스트 영역에 모델 ID, 버전, SHA-256 체크포인트, 연차별 입력 식별자 및 품질보고서 해시가 포함된 복잡한 `exact6` JSON 규격을 직접 수동 입력해야만 실행되었습니다.
2. **상단 실행 버튼 단절**: 상단 "분석 실행" 버튼은 단지 증거(Evidence) 탭으로 이동하고 안내 문구만 띄울 뿐 실제 워크플로 실행을 트리거하지 못했습니다.
3. **산출물 및 시각화 고립**: 하단 패널에서 워크플로가 성공하더라도, 생성된 변화 폴리곤 GeoJSON과 전이 통계는 하단의 별도 독립 미리보기 창(`LclucWorkflowChangeMap.tsx`)에만 갇혀 있었고, 상단의 메인 위성 지도(`ResearchMap`)와 주요 지표 카드(KPI Cards)에는 "과학모델 레이어 미연결", "검증 결과 미연결" 상태로 방치되었습니다.

**337 구현**은 이 UX 단절을 완전히 해소하는 **통합 워크플로 상태 어댑터(`lclucIntegratedWorkspaceAdapter.ts`)**를 제공합니다:
- 사용자가 상단 드롭다운을 조작하면 **유효한 exact6 워크플로 요청을 자동 합성·검증**합니다.
- 상단 **"분석 실행" 버튼이 원클릭으로 백엔드 로컬 워크플로 실행을 트리거**합니다.
- 실행이 완료되면 변화 GeoJSON과 9×9 전이행렬 통계를 상위 지도(`ResearchMap`)와 KPI 카드로 자동 스트리밍하여:
  - **지도(MapLibre GL)**: 9개 토지피복 클래스 전이 색상(`WORKFLOW_CLASS_COLORS`)이 적용된 변화 폴리곤이 즉시 오버레이되고 분석 범위로 카메라가 자동 이동(`fitBounds`)합니다.
  - **핵심 지표(KPI Cards)**: 산림 감소량(**Forest Loss**), 시가지 증가량(**Built-up Increase**), 순 전이 면적(**Net Transition Area**) 및 총 유효 면적이 즉시 실시간 갱신됩니다.

```
[사용자 UI 드롭다운: 지역·시작·종료 연도]
                 │
                 ▼
[constructLclucWorkflowRequest: exact6 JSON 자동 검증·합성]
                 │
                 ▼ (상단 "분석 실행" 원클릭)
[executeIntegratedLclucWorkflow / LclucIntegratedWorkspaceManager]
                 │
  ┌──────────────┴──────────────┐
  ▼                             ▼
[MapLibre GL ResearchMap]      [Top KPI Cards]
• 9개 클래스 전이 색상 오버레이  • Forest Loss (산림 감소 ha)
• 자동 영역 맞춤 (fitBounds)    • Built-up Increase (시가지 증가 ha)
• 실시간 변화 레이어 활성화      • Net Transition Area (전이 면적 ha)
```

---

## 2. 이론적 배경 (Theoretical Background)

### 2.1 exact6 불변 계약과 자동 합성 무결성
LCLUC 로컬 워크플로는 위성 센서 및 딥러닝 모델의 신뢰성을 위해 엄격한 불변 계약(`exact6`)을 요구합니다:
- `schema_version`: 정수 `1`
- `capability`: `'landcover.change_detection'`
- `trace_id` / `idempotency_key`: 1~128자 영숫자 토큰
- `model_ref`: 배포 검증된 모델 식별자, 고정 버전, 64자리 SHA-256 체크포인트 해시
- `images`: 최소 2개~최대 6개의 엄격 오름차순 연도 객체 (`year`, `input_ref`, `quality_report_sha256`)

`lclucIntegratedWorkspaceAdapter.ts`는 사용자가 선택한 UI 값(예: `region="South Sulawesi"`, `startYear=2020`, `endYear=2021`)을 받아, 인도네시아 10대 주요 주(Province)에 대해 사전 정의되거나 카탈로그에서 조회된 검증 핀(`PinnedImageSpec`)과 모델 핀(`DEFAULT_LCLUC_MODEL_REF`)을 매핑하여 수학적·형식적으로 완벽한 exact6 JSON을 비동기 생성합니다.

### 2.2 전이행렬 산술 일관성과 KPI 유도 공식
전이행렬 $T_{i, j}$는 시점 $t_1$의 토지피복 클래스 $i$가 시점 $t_2$의 클래스 $j$로 전이된 면적($\text{m}^2$)을 나타냅니다 ($0 \le i, j \le 8$, 9개 클래스):
- **클래스 정의**:
  - $0$: 수체 (water)
  - $1$: 산림/수목 (trees/forest)
  - $2$: 초지 (grass)
  - $3$: 침수식생/맹그로브 (flooded vegetation/mangrove)
  - $4$: 농경지 (crops)
  - $5$: 관목 (shrub & scrub)
  - $6$: 시가화/건성 (built-up)
  - $7$: 나지 (bare land)
  - $8$: 설빙 (snow & ice)

- **총 유효 면적 (Total Valid Area)**:
  $$A_{\text{total}} = \sum_{i=0}^{8} \sum_{j=0}^{8} T_{i, j}$$

- **총 전이 면적 (Net Transition / Changed Area)**:
  대각선(무변화 화소)을 제외한 오프 대각합(Off-diagonal sum):
  $$A_{\text{changed}} = \sum_{i \ne j} T_{i, j}$$

- **총 산림 손실량 (Gross Forest Loss)**:
  산림(클래스 1)에서 타 피복으로 전이된 총면적:
  $$A_{\text{loss, forest}} = \sum_{j \ne 1} T_{1, j}$$

- **총 시가지 확장량 (Gross Built-up Increase)**:
  타 피복에서 시가지(클래스 6)로 신규 전이된 총면적:
  $$A_{\text{gain, built}} = \sum_{i \ne 6} T_{i, 6}$$

- **헥타르(ha) 변환**:
  $$1\text{ ha} = 10,000\text{ m}^2$$
  화면 표시 시 소수점 2자리 정밀도(`maximumFractionDigits: 2`)로 반올림하여 부동소수점 오차 없는 일관된 통계를 제공합니다.

### 2.3 MapLibre GL 렌더링 무결성 및 WebGL 안전성
기존 `ResearchMap`은 정적 위성 기저지도(`imagery`)와 점선 연구 경계(`study-line`)만 표시했습니다.
통합 어댑터는 MapLibre GL의 선언적 스타일 사양(`createMapLibreOverlaySpec`)을 사용하여:
- `to_class` 기반 9색 동적 표현식(`match` expression) 생성
- `GeoJSONSource.setData()`를 활용한 무중단 데이터 교체
- WebGL 컨텍스트 유실(`webglcontextlost`) 또는 지도 미준수 예외 발생 시 에러가 화면 전체로 전파되지 않도록 완충하는 안전 계층(`try-catch` fallback)을 보장합니다.

---

## 3. 코드·데이터 동작 (Architecture & Integration Flow)

### 3.1 파일 구성 (`evidence/integration/lcluc-ui-workspace-20261019/`)

| 파일 | 역할 및 주요 기능 |
| :--- | :--- |
| `lclucIntegratedWorkspaceAdapter.ts` | **핵심 상태 어댑터**: 요청 자동 합성, 비동기 워크플로 실행 오케스트레이션, 전이 통계 및 KPI 계산, MapLibre GL 레이어 바인딩, `WorkflowFlight` 생명주기 관리 |
| `lclucIntegratedWorkspaceAdapter.test.mjs` | **18개 전 항목 검증 테스트**: 요청 합성, 파라미터 경계 검사, KPI 계산, MapLibre 바인딩, 백엔드 오류 복구, 취소 비행 시험 |
| `LclucIntegratedWorkspace.tsx` | **통합 UI 컴포넌트**: 상단 필터바, 원클릭 분석 실행 버튼, 4개 상단 KPI 카드, Gap 1 요약 카드, 실시간 위성+전이벡터 지도 결합 화면 |

### 3.2 핵심 인터페이스 및 데이터 흐름

#### (1) 상단 드롭다운 → exact6 워크플로 요청 생성
```typescript
export function constructLclucWorkflowRequest(
  selection: LclucWorkspaceSelection,
  options: LclucBuildOptions = {}
): LclucValidationResult
```
- `selection.region`: "South Sulawesi", "West Java", "Banten" 등 10대 지원 주 자동 해석
- `selection.startYear`, `selection.endYear`: 1900~2200년 범위, 시작연도 < 종료연도 검증
- `options.seriesMode`: 2개 시점 직접 비교(`endpoints_only`) 또는 최대 6개 연도 연속 시계열(`consecutive_series`)
- 출력: `requestShape()`를 100% 통과하는 고정 exact6 JSON 객체

#### (2) 엔드투엔드 워크플로 오케스트레이션
```typescript
export async function executeIntegratedLclucWorkflow(
  selection: LclucWorkspaceSelection,
  deps: IntegratedWorkflowClientDeps,
  options: LclucBuildOptions = {},
  live: () => boolean = () => true
)
```
1. `constructLclucWorkflowRequest`로 입력 검증
2. `prepareWorkflow`로 규격 해시(`digest`) 및 멱등키 해시(`id`) 산출
3. `deps.fetchWorkflow('', prepared.request)`로 백엔드 제출 (`/v1/lcluc/workflows`)
4. `workflowResponse()`로 영수증 검증 (`SUCCEEDED`, `BLOCKED`, `FAILED`)
5. `deps.fetchWorkflow('/{id}/report')`로 정량 보고서 조회
6. `workflowTransitionStats()`로 9×9 전이 통계 도출
7. `deps.fetchGeoJSON()`으로 타깃 변화쌍 GeoJSON 다운로드 및 `parseWorkflowChangeGeoJSON()` 검증
8. `computeLclucKpis()`로 핵심 KPI 카드 데이터 도출
9. `createMapLibreOverlaySpec()`로 지도 오버레이 사양 반환

#### (3) 상단 KPI 카드 계산 (`computeLclucKpis`)
- **ModelAnalysisWorkspace 4대 슬롯**:
  - 슬롯 0: 산림 면적 (`forestAreaHa`, 순변화량, 총 손실량 및 복원량)
  - 슬롯 1: 맹그로브/습지 면적 (`mangroveAreaHa`, 순변화량)
  - 슬롯 2: 시가화 면적 (`builtUpAreaHa`, 순변화량, 신규 개발 면적)
  - 슬롯 3: 총 지역 면적 (`totalValidAreaHa`, 변화율 %, 유효 픽셀 수)
- **Gap 1 핵심 요약 카드**:
  - `forestLossCard`: Forest Loss (산림 감소)
  - `builtUpIncreaseCard`: Built-up Increase (시가지 증가)
  - `netTransitionAreaCard`: Net Transition Area (전환 면적)

#### (4) MapLibre GL 실시간 레이어 바인딩 (`applyWorkflowChangeToMap`)
- 소스 ID: `lcluc-workflow-change`
- 채우기 레이어 ID: `lcluc-workflow-change-fill` (`to_class` 기반 9개 고유 색상 매핑)
- 테두리 레이어 ID: `lcluc-workflow-change-line` (`#075499`, width: 1.8)
- 이미 소스가 존재하면 `setData()`로 고속 갱신, 취소/초기화 시 레이어와 소스를 안전 제거

---

## 4. 테스트 증거 (Test Evidence)

격리 작업공간에서 Node.js 기본 테스트 러너(`node --test`)를 통해 18개 항목을 실행하고 100% 통과를 확인했습니다.

### 4.1 테스트 실행 명령
```powershell
node --test evidence/integration/lcluc-ui-workspace-20261019/lclucIntegratedWorkspaceAdapter.test.mjs
```

### 4.2 테스트 결과 (TAP Version 13)
```
TAP version 13
# Subtest: constructLclucWorkflowRequest builds valid exact6 request from standard dropdowns
ok 1 - constructLclucWorkflowRequest builds valid exact6 request from standard dropdowns
# Subtest: constructLclucWorkflowRequest supports all 10 provinces in ModelAnalysisWorkspace
ok 2 - constructLclucWorkflowRequest supports all 10 provinces in ModelAnalysisWorkspace
# Subtest: constructLclucWorkflowRequest validates consecutive_series mode bounded by 6 years
ok 3 - constructLclucWorkflowRequest validates consecutive_series mode bounded by 6 years
# Subtest: constructLclucWorkflowRequest rejects invalid dropdown selections cleanly
ok 4 - constructLclucWorkflowRequest rejects invalid dropdown selections cleanly
# Subtest: constructLclucWorkflowRequest supports custom catalog pins override
ok 5 - constructLclucWorkflowRequest supports custom catalog pins override
# Subtest: computeLclucKpis accurately computes Forest Loss, Built-up Increase, and Transition Area
ok 6 - computeLclucKpis accurately computes Forest Loss, Built-up Increase, and Transition Area
# Subtest: computeLclucKpis handles zero change pair without dividing by zero
ok 7 - computeLclucKpis handles zero change pair without dividing by zero
# Subtest: createMapLibreOverlaySpec constructs compliant source and layers
ok 8 - createMapLibreOverlaySpec constructs compliant source and layers
# Subtest: applyWorkflowChangeToMap binds layer to MapLibre instance and supports removal
ok 9 - applyWorkflowChangeToMap binds layer to MapLibre instance and supports removal
# Subtest: applyWorkflowChangeToMap handles WebGL errors gracefully without throw
ok 10 - applyWorkflowChangeToMap handles WebGL errors gracefully without throw
# Subtest: executeIntegratedLclucWorkflow executes full pipeline and returns all deliverables
ok 11 - executeIntegratedLclucWorkflow executes full pipeline and returns all deliverables
# Subtest: executeIntegratedLclucWorkflow throws structured error on BLOCKED receipt
ok 12 - executeIntegratedLclucWorkflow throws structured error on BLOCKED receipt
# Subtest: LclucIntegratedWorkspaceManager initializes, updates, and notifies listeners
ok 13 - LclucIntegratedWorkspaceManager initializes, updates, and notifies listeners
# Subtest: LclucIntegratedWorkspaceManager runAnalysis executes end-to-end and binds map
ok 14 - LclucIntegratedWorkspaceManager runAnalysis executes end-to-end and binds map
# Subtest: LclucIntegratedWorkspaceManager handles backend error with fallback
ok 15 - LclucIntegratedWorkspaceManager handles backend error with fallback
# Subtest: LclucIntegratedWorkspaceManager abort and selection change cancel in-flight executions
ok 16 - LclucIntegratedWorkspaceManager abort and selection change cancel in-flight executions
# Subtest: createMapLibreOverlaySpec produces exact 9-class color mapping and styling invariants
ok 17 - createMapLibreOverlaySpec produces exact 9-class color mapping and styling invariants
# Subtest: constructLclucWorkflowRequest prevents unexpected extra keys and produces strictly serializable JSON
ok 18 - constructLclucWorkflowRequest prevents unexpected extra keys and produces strictly serializable JSON
1..18
# tests 18
# suites 0
# pass 18
# fail 0
# cancelled 0
# skipped 0
# todo 0
```

### 4.3 기존 통합 테스트 회귀 무결성 검증
기존 LCLUC 워크플로 어댑터 핵심 시험(`frontend/src/lclucWorkflowAdapter.test.mjs`) 역시 15개 전 항목 통과하여 기존 API 및 어댑터 무결성이 완벽히 유지됨을 확인했습니다.

---

## 5. 발표 스크립트 (Presentation Script)

> **"심사위원 및 동료 엔지니어 여러분, 안녕하십니까. UI/UX 통합 엔지니어링 세션을 시작하겠습니다.**
>
> 기존 GeoAI SDSS 플랫폼에서는 상단의 WebGIS 대시보드와 하단의 LCLUC 분석 워크플로가 단절되어 있었습니다. 사용자가 대시보드에서 분석 대상 지역과 연도를 선택해도 워크플로가 자동 실행되지 않았고, 복잡한 JSON 코드를 수동으로 타이핑해야만 실행할 수 있었습니다. 또한 분석 결과가 나와도 상단 지도와 지표 카드에 연동되지 않는 'UX 단절(Gap 1)' 문제가 있었습니다.
>
> 이번 337 구현에서는 **통합 워크플로 어댑터(`lclucIntegratedWorkspaceAdapter`)**를 도입하여 이 문제를 완전히 해결했습니다.
>
> 첫째, 사용자가 상단 드롭다운에서 주(Province)와 시작·종료 연도를 선택하면 시스템이 백엔드 엄격 규격인 `exact6` JSON을 즉시 자동 검증·합성합니다.
>
> 둘째, 상단 **'분석 실행' 버튼 하나로 워크플로 제출, 상태 영수증 검증, 정량 보고서 조회, 변화 GeoJSON 다운로드까지의 전 과정이 원클릭 파이프라인으로 연결**됩니다.
>
> 셋째, 분석이 완료되는 즉시 변화 폴리곤이 상단의 **MapLibre GL 위성 지도 위에 9개 토지피복 클래스 고유 색상으로 매끄럽게 오버레이**되며, 상단 KPI 카드에 **산림 감소량(Forest Loss), 시가지 증가량(Built-up Increase), 순 전이 면적(Net Transition Area)**이 실시간 갱신됩니다.
>
> 18개의 단위 및 통합 테스트를 통해 백엔드 409 차단, 503 리소스 부족, 지도 WebGL 오류 상황에서도 시스템이 멈추지 않고 안전하게 회복됨을 입증했습니다. 감사합니다."

---

## 6. Q&A (자주 묻는 질문)

**Q1. 기존 하단 `LclucWorkflowPanel`의 JSON 수동 입력 방식과 충돌하지 않나요?**
> A: 전혀 충돌하지 않습니다. 통합 어댑터는 내부적으로 `lclucWorkflowAdapter`의 검증 함수(`parseWorkflowRequest`, `prepareWorkflow`, `workflowResponse`)를 그대로 재사용하므로, 하단의 고급 연구자용 수동 JSON 입력 패널과 상단의 일반 사용자용 원클릭 대시보드가 동일한 백엔드 계약을 공유하며 공존할 수 있습니다.

**Q2. 사용자가 시작 연도를 종료 연도보다 크게 선택하거나, 지원하지 않는 지역을 입력하면 어떻게 처리되나요?**
> A: `constructLclucWorkflowRequest`가 즉각적인 입력 검증을 수행하여, 유효하지 않은 요청은 백엔드로 전송되지 않고 상단 안내창에 친절한 한국어 안내(예: "시작 연도(2024)는 종료 연도(2020)보다 작아야 합니다")를 표시하고 분석 실행 버튼을 비활성화합니다.

**Q3. 네트워크 지연 중 사용자가 드롭다운을 바꾸거나 취소하면 어떻게 되나요?**
> A: `WorkflowFlight` 취소 메커니즘이 적용되어 있어, 진행 중이던 비동기 요청의 응답은 안전하게 폐기(invalidation)되며 최신 사용자 선택에 따른 상태만 반영됩니다. 불필요한 백엔드 재시도나 좀비 렌더링이 발생하지 않습니다.

**Q4. MapLibre GL 렌더링 시 브라우저 WebGL 성능 저하는 없나요?**
> A: GeoJSON 소스 갱신 시 전체 지도를 다시 그리지 않고 `setData()` API를 사용하여 변화된 레이어만 고속 갱신합니다. 또한 WebGL 컨텍스트 유실 시 예외를 흡수하여 전체 UI가 크래시되지 않도록 방어 코드가 완비되어 있습니다.
