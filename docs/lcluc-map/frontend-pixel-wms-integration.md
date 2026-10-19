# Frontend WebGIS WMS 픽셀 래스터 연동 및 통계 불변성 구현 보고서

## 1. 개요 및 구현 범위

본 문서는 CODEX 규격(`UI/GreenBlue_CODEX_LCLUC_Annual_Map_GeoServer_v1.0.md` 제2장, 제7장, 제8장)에 따라 프론트엔드 WebGIS UI/UX를 실제 GeoServer WMS 래스터 타일 및 단일 픽셀 검사 시스템으로 업그레이드한 내역을 기술합니다.

기존 프론트엔드에 존재하던 임의 좌표 기반의 절차적 캔버스(procedural canvas simulation) 렌더링을 완전히 제거하고, MapLibre GL의 정규 래스터 소스(`type: 'raster'`) 및 최근접 이웃 리샘플링(`'raster-resampling': 'nearest'`) 기반의 표준 WMS 1.1.1 GetMap 파이프라인으로 전환하였습니다.

또한, 뷰포트 조작(Swipe 분할바 위치, 레이어 투명도 슬라이더, 줌 확대/축소) 시 분석 통계가 왜곡되는 문제를 방지하기 위해 **통계 불변성(Invariance Guaranteed)** 원칙을 확립하였습니다.

---

## 2. 주요 변경 사항 및 규격 준수

### 2.1 First Group 6개 주 엄격 제한 (Section 2)
LCLUC 지역 선택 드롭다운(`Province`)에서 미승인 지역 및 타 분석 대상(파푸아, 자카르타, 중부 자바, 동칼리만탄)을 완전히 배제하고, First Group 6개 주만 선택 가능하도록 강제하였습니다.

- **승인된 6개 주 (First Group)**:
  1. `South Sulawesi` (남부 술라웨시) — `[118.8, -6.6, 121.1, -2.4]`
  2. `Gorontalo` (고론탈로) — `[121.1, 0.2, 123.6, 1.1]`
  3. `Southeast Sulawesi` (동남 술라웨시) — `[121.0, -6.3, 124.7, -2.7]`
  4. `Banten` (반텐) — `[105.1, -7.5, 106.8, -5.7]`
  5. `West Java` (서부 자바) — `[106.3, -8.0, 108.9, -5.8]`
  6. `East Java` (동부 자바) — `[110.8, -8.8, 114.6, -6.6]`
- **제외 지역 차단**: `Papua`, `DKI Jakarta`, `Central Java`, `East Kalimantan` 선택 불가 및 세션 스토리지에 유효하지 않은 값이 있는 경우 즉시 `South Sulawesi`로 자동 폴백.

### 2.2 실제 픽셀 래스터 타일 연동 (Section 4 & 5)
절차적 캔버스 데이터 URL 생성을 배제하고, GeoServer WMS 1.1.1 및 REST 타일 서비스 규격에 부합하는 소스/레이어를 구현하였습니다.

```typescript
// MapLibre GL 래스터 소스 규격 (lclucWmsRasterAdapter.ts)
export function createLclucRasterSourceSpec(
  configOrProvince: LclucRasterTileConfig | string,
  year = 2024,
  isT2 = false
): maplibregl.RasterSourceSpecification {
  const config = normalizeTileConfig(configOrProvince, year, isT2);
  return {
    type: 'raster',
    tiles: [buildLclucWmsTileUrl(config), buildLclucRestTileUrl(config)],
    tileSize: 256,
    attribution: `LCLUC ${config.province} ${config.year} · GeoServer WMS / Raster Tile`,
  };
}

// 이산 분류 경계 번짐 방지를 위한 최근접 이웃 리샘플링 레이어
export function createLclucRasterLayerSpec(layerId: string, sourceId: string, opacity = 0.65) {
  return {
    id: layerId,
    type: 'raster',
    source: sourceId,
    paint: {
      'raster-opacity': opacity,
      'raster-resampling': 'nearest', // 필수: 경계 번짐 방지
      'raster-fade-duration': 0,
    },
  };
}
```

### 2.3 통계 불변성(Invariance) 보장 (Section 2 & 8)
- **핵심 원칙**: 지도상의 Swipe 분할바 이동(10%~90%), 레이어 투명도 변경(10%~100%), 줌 확대/축소 등 어떠한 시각적 조작도 우측 KPI 카드, 시계열 연차별 차트, 9×9 전이 행렬, 피복 도넛 차트의 수치를 변경시키지 않습니다.
- **구현 방식**:
  - `generateMasterPayload` 및 통합 분석 응답에 `datasetId` (`lcluc_{aoi_id}_{startYear}_{endYear}`), `version: '1.0.0'`, `isStatsInvariant: true`, `statisticsBasis: 'full_valid_source_raster_invariant'` 명시.
  - UI 상단에 **통계 불변성 보장 (Invariance Verified)** 상태 배지 컴포넌트(`mw-stats-invariance-badge`) 배치.

### 2.4 Swipe 듀얼 지도 및 양방향 카메라 동기화 (Section 7.1)
- Map A (T1)와 Map B (T2) 두 지도의 중심 좌표(`center`), 줌 레벨(`zoom`), 방위각(`bearing`), 경사각(`pitch`)을 양방향 락(`isSyncing`) 기반으로 완벽히 동기화.
- 중앙 수직 분할바(`dividerRatio`)를 드래그하거나 터치할 때 Map A 컨테이너의 `clipPath`(`inset(0 ${100 - dividerRatio * 100}% 0 0)`)를 실시간 계산하여 매끄러운 비교 뷰 제공.

### 2.5 Animate 모드 다년도 타임라인 (Section 7.2)
- First Group 6개 주 레지스트리에 등록된 실제 연도(`availableYears: 2020~2025`)만 순차 재생(`play`, `pause`, `nextYear`, `prevYear`).
- 미등록 연도 요청 시 즉시 화면에 **"자료 없음 (No Data)"** 오버레이(`mw-nodata-overlay`) 표출.

### 2.6 좌표 기반 정확한 단일 픽셀 검사 (Section 8)
- 화면 픽셀의 단순 모니터 RGB를 추정(Eye-dropper)하는 방식을 엄격히 금지.
- 마우스 호버/클릭 시 지리 좌표 `[lng, lat]`로부터 분석 래스터 공간 격자를 직접 역산하여 다음 정보를 팝업에 표출:
  - 0~8 정수 클래스 번호 및 표준 명칭 (예: `수목 (Trees) (Class 1)`)
  - 표준 색상 배지 (`#15803d`)
  - **단일 픽셀 면적**: `100 m² (0.01 ha)` 명시 (주 전체 면적 표시 금지 규정 준수)
  - 지형 수치고도: `m` 단위
  - 전이 상태: `산림 (Trees/Forest) → 시가화 (Built-up)` 변화 여부
  - 데이터 출처 및 식별자 (`dataset_id`)

---

## 3. 수정 및 생성된 파일 목록

| 파일 경로 | 작업 내용 |
| :--- | :--- |
| `frontend/src/lclucWmsRasterAdapter.ts` | First Group 6개 주 레지스트리, WMS 1.1.1 / REST URL 빌더, MapLibre 소스/레이어 규격, 단일 픽셀 검사기(`inspectPixelAtCoord`), Animate 컨트롤러, 불변성 검증기 |
| `frontend/src/lclucMasterAdapter.ts` | `datasetId`, `version`, `isStatsInvariant`, `statisticsBasis` 불변성 메타데이터 바인딩 |
| `frontend/src/ModelAnalysisWorkspace.tsx` | 6개 주 선택 제한, 불변성 배지 렌더링, `LclucSwipeResearchMap` 및 `ResearchMap` WMS 래스터 연동, 빈 폴백 테이블 6개 주 정렬 |
| `frontend/src/model-workspace.css` | 통계 불변성 배지, No Data 오버레이, 모드 스위처 버튼 스타일 추가 |
| `frontend/src/lclucWmsRasterAdapter.test.mjs` | 5대 핵심 요구조건(6개 주 제한, WMS 규격, 통계 불변성, 픽셀 검사, Animate 제어) 단위 시험 |

---

## 4. 검증 결과

### 4.1 신규 단위 테스트 (`lclucWmsRasterAdapter.test.mjs`)
```
TAP version 13
# Subtest: 1. First Group 6개 주 엄격 제한 검증 (Papua, DKI Jakarta, Central Java, East Kalimantan 제외)
ok 1 - 1. First Group 6개 주 엄격 제한 검증 (Papua, DKI Jakarta, Central Java, East Kalimantan 제외)
# Subtest: 2. GeoServer WMS 1.1.1 및 REST 타일 소스/레이어 규격 검증
ok 2 - 2. GeoServer WMS 1.1.1 및 REST 타일 소스/레이어 규격 검증
# Subtest: 3. 통계 불변성(Invariance) 검증: Swipe/Opacity/Zoom UI 조작과 무관한 분석 일관성
ok 3 - 3. 통계 불변성(Invariance) 검증: Swipe/Opacity/Zoom UI 조작과 무관한 분석 일관성
# Subtest: 4. 좌표 기반 정확한 단일 픽셀 검사(inspectPixelAtCoord) 검증 (화면 RGB 추정 배제)
ok 4 - 4. 좌표 기반 정확한 단일 픽셀 검사(inspectPixelAtCoord) 검증 (화면 RGB 추정 배제)
# Subtest: 5. Animate 모드 제어기(LclucAnimateController) 연속 재생 및 누락 연도 감지 검증
ok 5 - 5. Animate 모드 제어기(LclucAnimateController) 연속 재생 및 누락 연도 감지 검증
1..5
# tests 5
# pass 5
# fail 0
```

### 4.2 전체 프론트엔드 테스트 회귀 검증
- `frontend/src/lclucWmsRasterAdapter.test.mjs`: **5 / 5 통과**
- `frontend/src/lclucWorkflowAdapter.test.mjs`: **15 / 15 통과**
- `frontend/src/lclucMasterAdapter.test.mjs`: **12 / 12 통과**
- `frontend/src/lclucIntegratedWorkspaceAdapter.test.mjs`: **18 / 18 통과**
- `frontend/src/lclucTransitionAdapter.test.mjs`: **12 / 12 통과**
- `frontend/src/lclucLandcoverRaster.test.mjs`: **5 / 5 통과**
- **총 67개 테스트 전부 성공 (0 실패)**

### 4.3 정적 타입 검사 (`tsc -b ./frontend`)
- TypeScript 빌드 검사 수행: **오류 0개 (Clean Build)**
