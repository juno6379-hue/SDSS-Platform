# LCLUC 데이터 계보 및 출처 감사 인벤토리 보고서
## Data Provenance & Physical Raster Inventory (CODEX v1.1 Section 2 & 8)

- **문서 식별자**: `docs/lcluc/data_provenance_inventory.md`
- **작성 일자**: 2026-10-19
- **문서 버전**: v1.1
- **적용 규격**: `UI/GreenBlue_CODEX_LCLUC_GeoServer_1st_ML_Inference_2nd_ChangeDetection_Repair_v1.1.md` (제2조, 제8조)
- **연계 데이터**:
  - `data/lcluc_class_definitions_v1.0.json` (표준 9-클래스 및 크로스워크 규격)
  - `docs/lcluc-map/annual-data-inventory.json` (물리 래스터 상세 메타데이터)
- **상태 판정**: **VERIFIED_REAL_PROVENANCE_AUDIT**

---

## 1. 개요 및 데이터 출처 감사 목적 (Purpose of Audit)

본 문서는 인도네시아 LCLUC(Land Cover / Land Use Change) 연구 및 GeoServer 지도 서비스에 사용되는 모든 물리 래스터 데이터 자산의 **계보(Provenance), 출처 제품(Source Product), 관측 기간, 품질 마스크 정책, 클래스 크로스워크**를 명확히 규정하고, 데이터 오용 및 과학적 사칭을 원천 차단하기 위해 작성되었습니다.

---

## 2. 4대 핵심 데이터 출처 명확한 구분 (4 Core Data Provenance Categories)

저장소 내의 모든 래스터 자산은 다음 4가지 범주 중 하나로 명확히 분류되며, 서로 다른 출처의 데이터를 혼동하거나 명칭을 변경하여 사용하는 것을 엄격히 금지합니다:

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        LCLUC 데이터 자산 분류 체계                      │
├───────────────────────────────┬────────────────────────────────────────┤
│ 1. ESA WorldCover 2020 (v100) │ 2020년 단일 시점 10m 글로벌 토지피복 참조│
├───────────────────────────────┼────────────────────────────────────────┤
│ 2. ESA WorldCover 2021 (v200) │ 2021년 단일 시점 10m 글로벌 토지피복 참조│
├───────────────────────────────┼────────────────────────────────────────┤
│ 3. Esri 10m Annual Land Cover │ 2020~2025 연차별 10m 시계열 토지피복    │
├───────────────────────────────┼────────────────────────────────────────┤
│ 4. 자체 AI 모델 예측도 (TinyUNet)│ 위성영상 추론 산출물 (model_prediction)│
└───────────────────────────────┴────────────────────────────────────────┘
```

### 2.1 ESA WorldCover 2020 v100
- **생산 기관**: ESA (European Space Agency) / VITO Consortium
- **버전**: v100 (알고리즘 v1.0)
- **해상도 및 공간 기준**: 10m GSD, EPSG:4326 격자 타일
- **관측 시점**: 2020-01-01 ~ 2020-12-31
- **분류 체계**: 11개 클래스 (10 Tree cover, 20 Shrubland, 30 Grassland, 40 Cropland, 50 Built-up, 60 Bare, 70 Snow/Ice, 80 Water, 90 Herbaceous wetland, 95 Mangroves, 100 Moss/lichen)
- **역할**: 2020년 기준점 외부 참조자료 (`source_kind: reference_landcover`).

### 2.2 ESA WorldCover 2021 v200
- **생산 기관**: ESA / VITO Consortium
- **버전**: v200 (알고리즘 개선판)
- **해상도 및 공간 기준**: 10m GSD, EPSG:4326 타일 $\to$ 인도네시아 UTM 로컬 투영
- **관측 시점**: 2021-01-01 ~ 2021-12-31
- **보관 위치**: `data/first-group-2021/*/label-worldcover.tif` (6개 주)
- **역할**: First Group 6개 주 2021년 공인 참조 베이스라인 (`source_kind: reference_landcover`).

> [!CAUTION]
> **절대 금지: WorldCover 2021의 2025년 관측자료 사칭 금지**:
> 1. ESA WorldCover v200은 **2021년 관측 데이터**입니다.
> 2. 2025년 위성 데이터가 없다는 이유로 WorldCover 2021을 '2025년 관측자료' 또는 '2025 AI 추론 결과'로 이름만 바꾸어 표기하거나 변화탐지에 사용하는 행위는 절대 금지됩니다 (`STRICTLY_PROHIBITED`).
> 3. 2025년 실제 관측 및 모델 결과가 없으면 UI 및 시스템 상에 **"2025년 자료 미확보/비교 불가"**로 정직하게 표기해야 합니다.

### 2.3 Esri 10m Annual Land Cover (2020~2025)
- **생산 기관**: Impact Observatory / Esri / Microsoft
- **해상도**: 10m GSD, 256×256 패치
- **관측 시점**: 2020년부터 2025년까지 매년 1회 발행
- **보관 위치**: `data/first-group-training-esri-v1/` (총 1,779개 패치)
- **분류 체계**: 8개 클래스 (1 Water, 2 Trees, 4 Flooded veg, 5 Crops, 7 Built Area, 8 Bare ground, 9 Snow/Ice, 11 Rangeland)
- **분류 한계**: Esri는 초지와 관목을 단일 `11 Rangeland`로 통합 분류함. 따라서 Esri 자료 사용 시 표준 9-Class 중 `5 관목(shrub_and_scrub)`이 0으로 집계되는 제약이 존재함.

### 2.4 자체 AI 모델 예측도 (`model_prediction`)
- **모델 아키텍처**: TinyUNet / FPN 기반 멀티스펙트럴 분광 분할 모델
- **입력 밴드**: Sentinel-2 MSI Level-2A BOA 반사도 6개 밴드 (B02, B03, B04, B08, B11, B12)
- **출력 산출물**: `prediction_class.tif` (0~8 정수 래스터), `prediction_valid_mask.tif`
- **현재 검증 상태**: `Draft / Validated` (현지 지상 정답 검증 전 단계, `IMPLEMENTED_UNVERIFIED`).

---

## 3. SCL 구름 결측과 라벨 NoData의 엄격한 분리 (Disambiguation)

위성 영상 분석에서 가장 빈번하게 발생하는 데이터 왜곡을 방지하기 위해 다음 세 가지 상태를 비트 수준에서 엄격히 분리합니다:

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        화소 무효화(Masking) 3대 구분                   │
├────────────────────────────────────────────────────────────────────────┤
│ 1. SCL 구름/그림자/결함  → quality_mask = 0 (분석 불가 무효 관측)        │
│ 2. 토지피복 라벨 NoData  → class_id = 255 (결측치 / 투명 배경)          │
│ 3. 정규 수역 (Water)    → class_id = 0 (유효한 개방 수면, #2563eb)     │
└────────────────────────────────────────────────────────────────────────┘
```

### 3.1 Sentinel-2 Level-2A SCL (Scene Classification Layer) 마스킹
유럽우주국(ESA) Sen2Cor 처리 산출물인 SCL의 12개 값 중 다음 화소는 유효 관측에서 제외합니다:
- **무효 코드 (품질 마스크 = 0)**:
  - `0`: NO_DATA (미관측)
  - `1`: SATURATED_OR_DEFECTIVE (센서 포화/결함)
  - `3`: CLOUD_SHADOWS (구름 그림자)
  - `8`: CLOUD_MEDIUM_PROBABILITY (중간 확률 구름)
  - `9`: CLOUD_HIGH_PROBABILITY (높은 확률 구름)
  - `10`: THIN_CIRRUS (권운)
  - `11`: SNOW_OR_ICE (적도부 오탐 적설)
- **유효 코드 (품질 마스크 = 1)**:
  - `2`: DARK_AREA_PIXELS (암흑 픽셀)
  - `4`: VEGETATION (식생)
  - `5`: NOT_VEGETATED (비식생/토양)
  - `6`: WATER (수역)
  - `7`: UNCLASSIFIED (미분류 유효)

### 3.2 라벨 NoData (255) vs 수역 (Class 0)
- **위험**: ESA WorldCover 및 Esri 원본 래스터에서 파일 외곽 빈 공간이나 결측치가 화소값 `0`으로 인코딩되어 있습니다.
- **해결**: 표준 9-Class 체계에서 `0`은 유효한 **수역(Water)**이므로, 원본 화소값 `0`을 절대 수역으로 변환해서는 안 됩니다.
- **정책**: 원본 결측치 `0`은 시스템 유입 즉시 **NoData 코드 255 (uint8) 또는 65535 (uint16)**로 리매핑되며, WMS 타일 렌더링 시 **완전 투명(Alpha 0)** 처리됩니다.

---

## 4. 연구 대상 지역 한정 및 배제 감사 (Scope & Rejections)

### 4.1 First Group 6개 대상 주 (공식 승인 대상)
CODEX 제2조 및 계약 명세에 따라 다음 6개 주에 한정하여 데이터를 관리합니다:
1. **남술라웨시 (South Sulawesi)**: UTM Zone 50S/51S (`EPSG:32750`/`32751`)
2. **고론탈로 (Gorontalo)**: UTM Zone 51N (`EPSG:32651`)
3. **동남술라웨시 (Southeast Sulawesi)**: UTM Zone 51S (`EPSG:32751`)
4. **반텐 (Banten)**: UTM Zone 48S (`EPSG:32748`)
5. **서자바 (West Java)**: UTM Zone 48S (`EPSG:32748`)
6. **동자바 (East Java)**: UTM Zone 49S (`EPSG:32749`)

### 4.2 명시적 배제 대상 (Rejections)
다음 지역의 파일은 First Group 범위 외 자료이므로 인벤토리 및 서비스에서 영구 거부합니다:
- **중부자바 (Central Java)**: `data/baseline2021/central_java_candidate-2021`는 과거 시범 파일이나 6개 주 범위 밖이므로 전면 제외 (`REJECTED_OUTSIDE_SCOPE`).
- **파푸아 (Papua)**, **DKI 자카르타 (DKI Jakarta)**, **동칼리만탄 (East Kalimantan)**: 미승인 확장 지역으로 인벤토리 등록 거절.

---

## 5. 저장소 내 물리 래스터 파일 실사 인벤토리 (Physical Assets)

### 5.1 `data/first-group-2021/` (운영급 2021 베이스라인) — [VERIFIED_REAL]
총 6개 장면 (256×256 GeoTIFF, 해상도 10.0m):

| 디렉터리명 | 대상 주 | 좌표계 (CRS) | 포함 파일 | 유효 화소율 |
|---|---|:---:|---|:---:|
| `banten-2021/` | 반텐 (Banten) | `EPSG:32748` | `image.tif`, `label-worldcover.tif` | 100.0% |
| `east_java-2021/` | 동자바 (East Java) | `EPSG:32749` | `image.tif`, `label-worldcover.tif` | 100.0% |
| `gorontalo-2021/` | 고론탈로 (Gorontalo) | `EPSG:32651` | `image.tif`, `label-worldcover.tif`, `quality-mask.tif` | 100.0% |
| `southeast_sulawesi-2021/` | 동남술라웨시 (SE Sulawesi) | `EPSG:32751` | `image.tif`, `label-worldcover.tif` | 100.0% |
| `south_sulawesi-2021/` | 남술라웨시 (South Sulawesi) | `EPSG:32751` | `image.tif`, `label-worldcover.tif` | 100.0% |
| `west_java-2021/` | 서자바 (West Java) | `EPSG:32748` | `image.tif`, `label-worldcover.tif` | 100.0% |

### 5.2 `data/first-group-training-esri-v1/` (연차별 대규모 패치셋) — [VERIFIED_REAL]
- **총 패치 수**: **1,779개** (주당 248~338개, 연도별 232~337개)
- **구성 파일**: 패치 폴더당 `image.tif`(Sentinel-2 반사도 합성), `label.tif`(Esri 10m 연차별 라벨), `quality.tif`(화소 유효성 마스크) 3종 세트 완비.
- **품질 현황**: 적격(`quality_eligible`) 1,407개, 부적격(`quality_insufficient`, 구름/결측) 372개.

---

## 6. 결론

본 데이터 계보 감사를 통해:
1. 2020~2021 참조 데이터와 2020~2025 연차별 패치셋의 물리적 실재를 입증했습니다.
2. 2021 WorldCover의 2025년 사칭 및 SCL 구름 결측의 NoData 혼동을 차단하는 기술적 안전장치를 확립했습니다.
3. 본 인벤토리를 `docs/lcluc/layer_registry_audit.md` 및 GeoServer 게시 파이프라인의 단일 진실 원천으로 선언합니다.
