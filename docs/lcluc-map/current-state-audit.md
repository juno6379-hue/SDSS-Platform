# LCLUC 연차별 실자료 현황 진단 및 데이터 파이프라인 감사 보고서 (Current State Audit)

- 문서 식별자: `docs/lcluc-map/current-state-audit.md`
- 작성일: 2026-10-19
- 문서 버전: v1.0
- 작성 역할: Data Pipeline & Inventory Specialist (Unit CODEX)
- 연계 규격: `UI/GreenBlue_CODEX_LCLUC_Annual_Map_GeoServer_v1.0.md` (제1조 ~ 제4조)
- 인벤토리 데이터: `docs/lcluc-map/annual-data-inventory.json`
- 표준 클래스 정의: `data/lcluc_class_definitions_v1.0.json`

---

## 1. 개요 및 연구 범위 경계 (Study Scope)

본 감사는 인도네시아 LCLUC(Land Cover / Land Use Change) 연차별 실자료 지도 서비스 및 GeoServer WMS/타일 연계를 위한 물리 래스터 데이터 자산의 현황을 과학적으로 감사하고, 표준 9-Class 체계 및 NoData 처리 정책을 확립하기 위해 수행되었습니다.

### 1.1 First Group 6개 대상 주 엄격 한정
CODEX 제2조에 따라 초기 지도 서비스 및 검증 범위는 기합의된 **First Group 6개 주**로 엄격히 한정합니다:
1. **남술라웨시 (South Sulawesi)**
2. **고론탈로 (Gorontalo)**
3. **동남술라웨시 (Southeast Sulawesi)**
4. **반텐 (Banten)**
5. **서자바 (West Java)**
6. **동자바 (East Java)**

### 1.2 배제 대상 (Rejection of Non-Target Regions)
다음 지역은 LCLUC First Group 연구 대상이 아니며, 인벤토리 및 지도 서비스 대상에서 명시적으로 제외/거부합니다:
- **중부자바 (Central Java)**: `data/baseline2021/central_java_candidate-2021`는 과거 시범 수집 파일이나 First Group 6개 주 범위 밖이므로 제외(`REJECTED_OUTSIDE_SCOPE`).
- **파푸아 (Papua)**, **DKI 자카르타 (DKI Jakarta)**, **동칼리만탄 (East Kalimantan)** 및 10개 주 확장안: 승인된 계약 규격 이전의 임의 확장이므로 인벤토리에서 전면 배제.

---

## 2. 4개 주요 데이터 디렉터리 현황 실사 (Authentic Data Audit)

저장소 내 실제 물리 파일에 대한 무결성 검사(SHA-256, 해상도, 좌표계, 밴드 수, 고유 클래스 값) 결과는 다음과 같습니다.

### 2.1 `data/first-group-2021/` (운영급 2021 참조자료) — [VERIFIED_REAL]
- **현황**: First Group 6개 주 전역에 대해 2021년 기준 Sentinel-2 RGB 영상(`image.tif`) 및 ESA WorldCover 10m v200 참조 레이블(`label-worldcover.tif`)이 완비되어 있습니다.
- **장면 수**: 총 6개 장면 (주당 1개 대표 윈도우)
  - `banten-2021` (EPSG:32748, 256×256, 3밴드 RGB + 1밴드 WorldCover 레이블)
  - `east_java-2021` (EPSG:32749, 256×256, 3밴드 RGB + 1밴드 WorldCover 레이블)
  - `gorontalo-2021` (EPSG:32651, 256×256, 3밴드 RGB + 1밴드 WorldCover + 1밴드 `quality-mask.tif`)
  - `southeast_sulawesi-2021` (EPSG:32751, 256×256, 3밴드 RGB + 1밴드 WorldCover 레이블)
  - `south_sulawesi-2021` (EPSG:32751, 256×256, 3밴드 RGB + 1밴드 WorldCover 레이블)
  - `west_java-2021` (EPSG:32748, 256×256, 3밴드 RGB + 1밴드 WorldCover 레이블)
- **품질**: 유효 화소 비율 100%, NoData 분리 완료.

### 2.2 `data/baseline2021/` (시범 수집 후보군) — [VERIFIED_REAL (부분 선별)]
- **현황**: 2021년 단일 시점 3개 후보 윈도우 수집 파일 존재.
- **선별 내역**:
  - `west_java_candidate-2021`: 수용 (서자바, First Group 6 포함)
  - `south_sulawesi_candidate-2021`: 수용 (남술라웨시, First Group 6 포함)
  - `central_java_candidate-2021`: **제외 (중부자바, First Group 6 범위 외 지역으로 탈락)**

### 2.3 `data/first-group-annual/` (연차별 미정제 수집 시험) — [REPORT_ONLY / NO_DATA]
- **현황**: `chunk-01`, `chunk-02`, `chunk-03` 세 개 청크에 걸쳐 2020~2025년 연차별 수집 시도가 기록되어 있으나, 대부분의 셀이 `status: failed` 또는 `status: search_failed`로 기록됨.
- **물리 파일**: 2020년 3개 장면(`south_sulawesi-2020`, `gorontalo-2020`, `southeast_sulawesi-2020`)에 한해 개별 분광 밴드(`raw-B02.tif`, `raw-B03.tif`, `raw-B04.tif`, `raw-B08.tif`)만 존재함.
- **토지피복 레이블 부재**: 본 디렉터리에는 토지피복 분류 GeoTIFF(`label*.tif`)가 전무함. GeoServer 지도 게시용 유효 연차 래스터로 채택 불가.

### 2.4 `data/first-group-training-esri-v1/` (연차별 10m 실자료 대규모 패치셋) — [VERIFIED_REAL]
- **현황**: First Group 6개 주 전체에 대해 2020년부터 2025년까지 6개 연도 전 기간에 걸친 실자료 패치 세트 완비.
- **패치 수**: 총 **1,779개 패치** (256×256 GeoTIFF)
  - 2020년: 337개
  - 2021년: 292개
  - 2022년: 332개
  - 2023년: 232개
  - 2024년: 305개
  - 2025년: 281개
- **주별 분포**:
  - 반텐 (Banten): 337개 패치
  - 동자바 (East Java): 248개 패치
  - 고론탈로 (Gorontalo): 272개 패치
  - 남술라웨시 (South Sulawesi): 320개 패치
  - 동남술라웨시 (Southeast Sulawesi): 338개 패치
  - 서자바 (West Java): 264개 패치
- **파일 구성**: 각 패치 폴더마다 `image.tif`(Sentinel-2 반사도 합성), `label.tif`(Esri 10m 연차별 토지피복), `quality.tif`(화소 유효성 마스크) 3종 세트가 물리적으로 실재함.
- **데이터셋 분할**: 학습(train) 1,178개, 검증(val) 337개, 시험(test) 264개.
- **품질 상태**: `quality_eligible` 1,407개 (품질 통과), `quality_insufficient` 372개 (구름/결측으로 인한 비적격).

---

## 3. 표준 9-Class 체계 및 크로스워크 매핑 (Class Definitions & Crosswalk)

CODEX 제3조에 따라 단일화된 공통 분류 체계 `data/lcluc_class_definitions_v1.0.json`을 제정했습니다.

### 3.1 9개 표준 클래스 규격

| Class ID | 키값 (Key) | 국문 명칭 | 영문 명칭 | 대표 색상 (Hex) | 정의 및 판정 기준 | NoData 코드 |
|:---:|:---:|:---:|:---:|:---:|:---|:---:|
| **0** | `water` | 수역 | Water | `#419bdf` | 연중 개방 수면이 지배적인 하천, 호수, 저수지, 해양 수역 | 255 |
| **1** | `trees` | 수목·산림 | Trees | `#397d49` | 교목 수관 피복지 (자연림, 식재림, 맹그로브 포함; 법적 산림과 구별) | 255 |
| **2** | `grass` | 초지 | Grass | `#88b053` | 자연 초원, 목초지, 사바나 초본 식생 및 이끼·지의류 | 255 |
| **3** | `flooded_vegetation` | 침수식생·습지 | Flooded vegetation | `#7a87c6` | 정기적/영구적 침수 습지, 하천변 초본 습지 식생 | 255 |
| **4** | `crops` | 농경지 | Crops | `#e49635` | 논, 밭, 과수, 일년생 및 다년생 인위적 경작지 | 255 |
| **5** | `shrub_and_scrub` | 관목·덤불 | Shrub & scrub | `#c2a867` | 연속적 교목 수관이 없는 낮은 목본 식생 및 저목 덤불 | 255 |
| **6** | `built_area` | 시가지·인공구조물 | Built area | `#c4281b` | 건물, 포장 도로, 산업시설 등 불투수 인공 구조물 | 255 |
| **7** | `bare_ground` | 나지·토양 | Bare ground | `#a59b8f` | 식생 피복이 극히 희박한 토양, 암석, 모래, 개간 나지 | 255 |
| **8** | `snow_and_ice` | 설빙 | Snow & ice | `#e8f4fa` | 영구/계절성 적설 및 빙하 (적도부 푼착자야 등 국지적) | 255 |

---

### 3.2 ESA WorldCover (11 클래스) 크로스워크 매핑표

| WorldCover 코드 | 소스 클래스명 | 타깃 Class ID | 타깃 키값 | 매핑 정책 및 분류 한계 (Limitations) |
|:---:|:---|:---:|:---:|:---|
| **10** | Tree cover | **1** | `trees` | 직결. 위성 분광 기반 수관 피복 판정이며 인도네시아 산림부(KLHK) 법적 산림구역과 동일시 불가. |
| **20** | Shrubland | **5** | `shrub_and_scrub` | 직결. 관목림 피복지. |
| **30** | Grassland | **2** | `grass` | 직결. 초본 식생. |
| **40** | Cropland | **4** | `crops` | 직결. 경작지. |
| **50** | Built-up | **6** | `built_area` | 직결. 인공 불투수면. |
| **60** | Bare / sparse vegetation | **7** | `bare_ground` | 직결. 나지 및 희소 식생지. |
| **70** | Snow and ice | **8** | `snow_and_ice` | 직결. 적설 및 빙하. |
| **80** | Permanent water bodies | **0** | `water` | **중요 직결: 원본 코드 80이 타깃 0(Water)으로 매핑됨. 원본 NoData(0)와 절대 혼동 금지.** |
| **90** | Herbaceous wetland | **3** | `flooded_vegetation` | 초본 습지를 침수식생·습지로 매핑. |
| **95** | Mangroves | **1** | `trees` | **분류 한계**: 9-Class 체계에 독자 맹그로브 클래스가 없으므로 수목(1)으로 통합. 침수식생(3)과의 혼재 가능성이 존재함. |
| **100** | Moss and lichen | **2** | `grass` | **분류 한계**: 지표 피복 특성을 고려하여 초지(2)로 통합 매핑. |

---

### 3.3 Esri 10m Annual Land Cover (8 클래스) 크로스워크 매핑표

| Esri 코드 | 소스 클래스명 | 타깃 Class ID | 타깃 키값 | 매핑 정책 및 분류 한계 (Limitations) |
|:---:|:---|:---:|:---:|:---|
| **1** | Water | **0** | `water` | 직결 (Esri 1 -> 9-Class 0). |
| **2** | Trees | **1** | `trees` | 직결. |
| **4** | Flooded vegetation | **3** | `flooded_vegetation` | 직결. |
| **5** | Crops | **4** | `crops` | 직결. |
| **7** | Built Area | **6** | `built_area` | 직결. |
| **8** | Bare ground | **7** | `bare_ground` | 직결. |
| **9** | Snow/Ice | **8** | `snow_and_ice` | 직결. |
| **11** | Rangeland | **2** | `grass` | **분류 한계**: Esri는 초지와 관목을 단일 Rangeland(11)로 병합 분류함. 표준 9-Class 초지(2)로 매핑되므로 Esri 자료 사용 시 관목(5)이 0으로 집계되는 제약이 발생함. |

---

## 4. NoData 처리 원칙 (NoData Disambiguation)

> [!CAUTION]
> **NoData 코드와 수역(Water, Class 0) 혼동 방지 절대 준수**:
> 1. ESA WorldCover 및 Esri 10m 원본 래스터에서 화소값 `0`은 유효한 토지피복이 아닌 **NoData(미분류/결측)**를 의미합니다.
> 2. 표준 9-Class 체계에서 화소값 `0`은 **수역(Water)**입니다.
> 3. 따라서 재분류 및 통계 처리 시 원본 화소값 `0`을 수역으로 자동 변환해서는 안 되며, 반드시 **NoData 코드 255 (uint8) 또는 투명 처리**로 분리 변환해야 합니다.

---

## 5. 공간 해상도 및 래스터 보간 한계 (10m Resolution & Interpolation)

1. **10m 고유 해상도 보존**:
   - Sentinel-2 MSI L2A 반사도 및 ESA WorldCover, Esri Land Cover는 모두 10m 지상 표본 거리(GSD)를 가집니다.
   - WMS 타일 렌더링 및 확대/축소 시 **반드시 최근린 보간(Nearest Neighbor)**을 사용해야 합니다.
   - 선형 보간(Bilinear)이나 큐빅(Cubic), 평균(Average) 보간을 적용할 경우 서로 다른 정수 클래스 번호 간에 존재하지 않는 가상의 클래스(예: 수목 1과 농경지 4 사이에 풀 2나 침수식생 3)가 경계선에 인위적으로 생성되는 치명적 왜곡이 발생합니다.
2. **First Group 다중 UTM 좌표계 특성**:
   - First Group 6개 주는 동서로 넓게 분포하여 단일 UTM Zone으로 묶을 수 없습니다:
     - 반텐·서자바: UTM Zone 48S (`EPSG:32748`)
     - 동자바: UTM Zone 49S (`EPSG:32749`)
     - 남술라웨시: UTM Zone 50S (`EPSG:32750`) / 51S (`EPSG:32751`)
     - 고론탈로: UTM Zone 51N (`EPSG:32651`)
     - 동남술라웨시: UTM Zone 51S (`EPSG:32751`)
   - 분석 및 면적 계산은 각 주의 원본 투영 좌표계(등적/등각 UTM 투영)에서 수행하며, 웹 표시(Web Mercator EPSG:3857) 왜곡 면적을 정책 통계로 사용하지 않습니다.

---

## 6. 현황 요약 판정표

| 항목 | 감사 대상 | 실사 결과 판정 | 근거 파일 |
|---|---|:---:|---|
| First Group 6개 주 2021년 참조지도 | `data/first-group-2021/` | **VERIFIED_REAL** | 6개 주 전체 GeoTIFF 완비 (`label-worldcover.tif`) |
| First Group 6개 주 2020~2025 연차별 패치 | `data/first-group-training-esri-v1/` | **VERIFIED_REAL** | 6개 연도 1,779개 패치 완비 (`label.tif`, `image.tif`) |
| 2021 시범 후보군 | `data/baseline2021/` | **VERIFIED_REAL (선별)** | 서자바·남술라웨시 2건 수용, 중부자바 1건 탈락 |
| 연차별 원시 수집 디렉터리 | `data/first-group-annual/` | **NO_DATA (토지피복 레이블 없음)** | 원시 밴드 일부만 존재, 분류 레이블 미보유 |
| 9-Class 표준 정의 및 크로스워크 | `data/lcluc_class_definitions_v1.0.json` | **VERIFIED_REAL** | 9개 클래스, 색상, NoData(255), 2개 소스 크로스워크 완비 |
| 연차별 래스터 인벤토리 | `docs/lcluc-map/annual-data-inventory.json` | **VERIFIED_REAL** | 4,293라인, 6개 주 래스터 메타데이터 및 SHA-256 확정 |

본 감사 결과를 바탕으로 Gate 1 (단일 시점 실자료 GeoServer 게시) 및 Gate 2 (동일 AOI 연차별 비교) 파이프라인 구현 단계로 인계합니다.
