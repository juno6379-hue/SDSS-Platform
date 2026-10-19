# 337. LCLUC 대시보드-워크플로우 UI/UX 통합 어댑터

상태: **TESTED_SYNTHETIC** (격리 작업공간 `evidence/integration/lcluc-ui-workspace-20261019`에서 18/18 단위/통합 테스트 통과, 프론트엔드 TypeScript 빌드 통과, 메인 미반영)

---

## 1. 쉬운 설명

기존 LCLUC 토지피복 변화 탐지 화면에는 심각한 사용성 단절(Gap 1)이 있었습니다.
상단에는 사용자가 조작하는 직관적인 지역(10개 주) 및 관측 연도 드롭다운 필터바가 있고 "분석 실행" 버튼이 있었지만, 이 버튼을 눌러도 하단의 복잡한 16KB JSON 입력 폼과 전혀 연동되지 않았습니다. 즉, 상단 지도에서 시각적으로 분석을 요청하더라도 실제 백엔드 분석 파이프라인이 실행되지 않고 결과도 상단 지도에 반영되지 않는 "UX의 단절"이 발생했습니다.

Unit 337 구현은 상단 필터바와 하단 실행 엔진을 하나로 이어주는 통합 상태 어댑터(`lclucIntegratedWorkspaceAdapter.ts`)를 구축했습니다.
사용자가 상단에서 지역과 기간을 선택하고 "분석 실행" 버튼을 누르면:
1. 백엔드가 요구하는 정밀한 6개 필드 워크플로우 요청 JSON을 자동 구성하여 전송하고,
2. 백엔드에서 생성된 GeoJSON 변화 폴리곤을 상단 MapLibre GL 지도에 9개 토지피복 색상으로 실시간 오버레이하며,
3. 9×9 전이 행렬로부터 산림 손실, 시가지 증가, 순 전이 면적 등 핵심 KPI 카드를 상단 화면에 즉시 계산하여 표출합니다.

---

## 2. 이론적 배경

### 2.1 단방향 데이터 흐름과 상태 머신
웹 애플리케이션의 복잡한 비동기 지리공간 워크플로우는 경쟁 상태(Race Condition)와 메모리 누수를 방지하기 위해 엄격한 상태 머신으로 관리됩니다:
$$\text{IDLE} \xrightarrow{\text{SUBMIT}} \text{PENDING} \xrightarrow{\text{RECEIPT}} \text{RUNNING} \xrightarrow{\text{POLL}} \text{SUCCEEDED} \lor \text{FAILED}$$
사용자가 분석 중 다른 지역을 선택하거나 재실행하는 경우, 이전 비행(Flight)을 취소 토큰(`AbortController`)으로 즉시 무효화하여 과거 결과가 최신 화면을 덮어쓰는 Out-of-order 렌더링을 차단합니다.

### 2.2 MapLibre GL 벡터 레이어 동적 바인딩 및 WebGL 방어
- GeoJSON 피처 컬렉션을 MapLibre의 `GeoJSONSource`에 원자적으로 주입.
- 전이 코드에 따른 동적 스타일링:
  `['match', ['get', 'to_class'], 0, '#2563eb', 1, '#15803d', ...]`
- 사용자가 선택한 지역의 공간 경계(`bbox`)를 계산하여 지도 카메라를 자동으로 이동(`fitBounds`)시키는 뷰포트 어댑터 적용.
- WebGL 컨텍스트 소실 시 부드러운 폴백 처리.

---

## 3. 코드·데이터 동작

1. **워크플로우 요청 자동 생성 (`constructLclucWorkflowRequest`)**:
   ```typescript
   export function constructLclucWorkflowRequest(input: IntegratedWorkspaceInput): LclucWorkflowRequest {
     // exact6 규격 검증: province, start_year, end_year, baseline_model_id, target_class_ids, confidence_threshold
     ...
   }
   ```
2. **원클릭 통합 실행기 (`executeIntegratedLclucWorkflow`)**:
   - 백엔드 `POST /v1/lcluc/workflows` 요청 발송 및 Receipt 검증.
   - 폴링 후 성공 시 `GET /v1/lcluc/workflows/{id}/report` 및 GeoJSON 취득.
   - 9개 토지피복별 전이 통계 및 상단 4대 KPI 카드 데이터 피딩.
3. **MapLibre 실시간 레이어 바인딩 (`bindLclucChangeLayerToMap`)**:
   - `workflow-change-source` 등록.
   - `workflow-change-fill` 및 `workflow-change-line` 레이어 추가.

---

## 4. 테스트 증거

격리 작업공간(`evidence/integration/lcluc-ui-workspace-20261019`)에서 실행:
- **신규 어댑터 테스트**: `node --test lclucIntegratedWorkspaceAdapter.test.mjs`
  - 결과: **18 / 18 PASS** (0 fail, 0 skip)
- **기존 회귀 테스트**: `node --test frontend/src/lclucWorkflowAdapter.test.mjs`
  - 결과: **15 / 15 PASS** (0 fail, 0 skip)
- **프론트엔드 빌드 무결성**: `tsc -b ./frontend`
  - 결과: 타입 에러 0건, 빌드 성공

---

## 5. 발표 스크립트

### 1분 스크립트
"Unit 337에서는 WebGIS 지도 대시보드와 변화탐지 워크플로우 엔진 간의 UX 단절을 해결했습니다. 이제 사용자는 상단 드롭다운에서 지역과 연도를 선택하고 '분석 실행' 버튼을 한 번 클릭하는 것만으로, 백엔드 워크플로우 실행, 실시간 진행 상태 조회, GeoJSON 변화 벡터의 지도 오버레이, 그리고 산림 손실과 시가지 확장을 나타내는 KPI 카드 갱신까지 원스톱으로 경험할 수 있습니다. 18개 단위 테스트와 TypeScript 컴파일을 완벽히 통과했습니다."

### 5분 스크립트
"의사결정자를 위한 GeoAI 플랫폼에서 가장 중요한 것은 직관적인 사용자 경험(UX)입니다. 지금까지 우리 플랫폼은 상단의 아름다운 WebGIS 인터페이스와 하단의 정밀한 분석 엔진이 서로 연결되지 못하고 분리되어 있었습니다. 현업 실무자가 분석을 실행하려면 16KB에 달하는 복잡한 JSON 코드를 직접 편집해야만 했습니다.

Unit 337은 이 문제를 완벽하게 해소하는 `lclucIntegratedWorkspaceAdapter`를 선보입니다. 이 어댑터는 사용자의 상단 필터 선택을 백엔드 계약 규격(exact6)에 부합하는 정규화된 워크플로우 요청으로 자동 변환합니다. '분석 실행' 클릭 시 비동기 파이프라인이 즉각 작동하며, 분석이 완료되면 결과 래스터 및 GeoJSON을 받아와 MapLibre GL 지도 엔진에 9개 토지피복 고유 색상으로 오버레이합니다.

동시에 행렬 연산을 통해 산림 손실 면적, 도시화 확장 면적, 총 전이 면적을 실시간 집계하여 대시보드 상단 KPI 카드에 즉각 반영합니다. 또한 작업 도중 다른 연도를 선택하더라도 AbortController 기반의 비행 관리자를 통해 이전 요청을 깔끔하게 무효화함으로써 지도의 일관성을 보장합니다."

---

## 6. 예상 Q&A

**Q1: 상단 필터바에서 지원하는 지역은 몇 개인가요?**
A1: 인도네시아 10개 주(반텐, 서자바, 중자바, 동자바, 욕야카르타, 발리, 아체, 북수마트라, 서수마트라, 리아우 등) 및 2020~2025년 관측 기간을 지원합니다.

**Q2: 대용량 변화 벡터가 전달될 때 브라우저 렌더링 렉(UI 프리징)은 없나요?**
A2: 어댑터는 안전 가드로 벡터 피처 수를 5,000개로 캡핑하여 GeoJSON 레이어를 렌더링하며, 그 이상의 전수 화소 탐색은 Unit 339에서 개발된 고성능 래스터 타일 서비스(`transitions.tif` 타일 스트리밍)로 즉시 전환할 수 있도록 상호 연동 인터페이스를 구비했습니다.
