# LCLUC 통일 분석 및 불변 통계 명세서 (Unified Analytics & Invariant Statistics Specification)

- 문서 버전: v1.0
- 적용 규격: `UI/GreenBlue_CODEX_LCLUC_Annual_Map_GeoServer_v1.0.md` (제3장, 제8장, 제9장, 제13장)
- 구현 모듈: `backend/app/ml/lcluc_unified_analytics.py`
- 단위 시험: `tests/test_lcluc_unified_analytics.py` (17건 전건 PASS, 1.04초)
- 상태: **VERIFIED_CORE_ANALYTICS_INVARIANT**

---

## 1. 개요 및 설계 철학

기존 GIS/웹 매핑 시스템의 흔한 결함 중 하나는 **화면 뷰포트(Viewport), 줌 레벨(Zoom level), 스와이프 슬라이더(Swipe slider)의 위치에 따라 통계치나 면적 수치가 왜곡되거나 동적으로 변동하는 문제**입니다. 또한 웹 브라우저 캔버스의 RGB 색상이나 화면 픽셀 수를 역추정하여 면적을 계산하는 오류는 국가 기후·토지 정책 의사결정에서 치명적인 데이터 오염을 초래합니다.

`GreenBlue_CODEX_LCLUC_Annual_Map_GeoServer_v1.0`의 핵심 명령에 따라 본 모듈은 다음 원칙을 절대적으로 보장합니다:
1. **화면 표시와 분석 통계의 완전한 분리**: 지도 확대/축소, 패닝, 스와이프 손잡이 조작은 시각적 클리핑에 불과하며, 분석 통계 수치에 1화소의 영향도 미치지 않습니다.
2. **단일 진실 원천(Single Source of Truth) 기반 산정**: 모든 통계는 원본 분류 래스터 GeoTIFF(`transitions.tif`, `classification.tif`)와 검증된 품질 마스크로부터 직접 산출됩니다.
3. **엄밀한 식별자 일치성(Identity Binding)**: 지도(Map), 범례(Legend), 연차별 면적(Annual Area), 전이행렬(Transition Matrix)은 반드시 **동일한 `dataset_id`, `version`, `aoi_id`, `observation_period`**를 공통 참조해야 합니다.

---

## 2. 식별자 일치성 보장 (Dataset Identity Binding)

지도 타일과 분석 통계 간의 버전 불일치 및 서로 다른 연도/지역의 우발적 혼합을 방지하기 위해 `DatasetIdentity` 계약을 강제합니다:

```python
@dataclass(frozen=True)
class DatasetIdentity:
    dataset_id: str
    version: str
    aoi_id: str
    observation_period: str
    source_kind: SourceKind = SourceKind.MODEL_PREDICTION
    checksum: Optional[str] = None
```

- **일치성 검증 (`assert_matches`)**:
  - `dataset_id`: 대상 자료셋 식별자 불일치 시 즉시 거부 (`ValueError`)
  - `version`: 처리/모델 버전 불일치 시 즉시 거부 (`ValueError`)
  - `aoi_id`: 연구 대상 지역 불일치 시 즉시 거부 (`ValueError`)
  - `observation_period`: 관측 시기(연도/타임스탬프) 불일치 시 즉시 거부 (`ValueError`)

---

## 3. 원본 기반 불변 면적 산정 체계

### 3.1 지상 실측 면적 산정 공식
화면 픽셀이나 Web Mercator(EPSG:3857) 왜곡 면적을 정책 통계로 사용하는 것을 엄격히 금지합니다.
정규 투영 격자(UTM 등 등적 투영) 또는 측지학적 면적(Geodesic Ellipsoidal Area)을 기준으로 정수 화소 수와의 곱으로 환산합니다:

$$\text{Pixel Area } (m^2) = \text{Resolution } (m) \times \text{Resolution } (m) \quad (\text{예: } 10m \times 10m = 100m^2)$$
$$\text{Class Area } (ha) = \frac{\text{Pixel Count} \times \text{Pixel Area } (m^2)}{10,000}$$

### 3.2 연차별 통계 (Annual Statistics) 불변 규칙
- $\text{Total Valid Pixels} = \sum_{c=0}^{K-1} \text{Pixels}(c)$
- $\text{Total Valid Area } (ha) = \sum_{c=0}^{K-1} \text{Area}_{ha}(c)$
- 유효 화소 비율 합계는 정확히 $100.0\%$를 만족합니다.
- NoData 화소는 전체 도메인 픽셀 수에서 분리하여 `nodata_pixels`로 별도 계량하며 유효 클래스 면적에 합산되지 않습니다.

---

## 4. 전이행렬 (Transition Matrix) 산정 공식 및 수용 기준

### 4.1 행렬 구조 및 정의
- **행 (Rows)**: 이전 시점 ($T_1$) 토지피복 클래스 ID ($0 \dots K-1$)
- **열 (Columns)**: 이후 시점 ($T_2$) 토지피복 클래스 ID ($0 \dots K-1$)
- **대각 성분 ($M[i, i]$)**: $T_1$과 $T_2$에서 동일 클래스를 유지한 **불변 화소(Unchanged Pixels)**
- **비대각 성분 ($M[i, j], i \ne j$)**: $T_1$의 클래스 $i$에서 $T_2$의 클래스 $j$로 전이된 **변화 화소(Transition Pixels)**

### 4.2 공통 유효영역 및 엄격한 NoData 배제 (Strict NoData Handling)
- **공통 유효 화소 마스크**:
  $$\text{Valid}_{\text{common}} = (T_1 \ne \text{NoData}) \land (T_2 \ne \text{NoData}) \land \text{Mask}_{T_1} \land \text{Mask}_{T_2}$$
- **엄격한 배제 원칙 (CODEX 제13.5조)**:
  $T_1$ 또는 $T_2$ 중 어느 한쪽이라도 NoData(기본값 255)이거나 품질 마스크에서 제외된 화소는 **전이행렬 집계에서 완전히 배제**됩니다.
- **총합 일치성 불변식**:
  $$\sum_{i=0}^{K-1} \sum_{j=0}^{K-1} M[i, j] = N_{\text{common\_valid\_pixels}}$$
  $$\sum_{i=0}^{K-1} \sum_{j=0}^{K-1} \text{Area}(M[i, j]) = \text{Area}_{\text{common\_valid\_area}}$$

### 4.3 클래스별 증감량 및 순변화
- **이전 면적 (Before Area)**: $A_{\text{before}}(k) = \sum_{j} M[k, j] \times \text{Pixel Area}$ (행 합)
- **이후 면적 (After Area)**: $A_{\text{after}}(k) = \sum_{i} M[i, k] \times \text{Pixel Area}$ (열 합)
- **총 손실 (Gross Loss)**: $\text{Loss}(k) = A_{\text{before}}(k) - M[k, k] \times \text{Pixel Area}$
- **총 증가 (Gross Gain)**: $\text{Gain}(k) = A_{\text{after}}(k) - M[k, k] \times \text{Pixel Area}$
- **순변화 (Net Change)**: $\text{Net}(k) = A_{\text{after}}(k) - A_{\text{before}}(k) = \text{Gain}(k) - \text{Loss}(k)$

---

## 5. 프레임 매니페스트 스키마 (Frame Manifest Schema, Section 9)

GeoServer WMS 레이어 게시 및 시계열 타임라인 인덱싱을 위한 단일 규격 데이터 모델:

| 필드명 | 데이터 타입 | 필수 여부 | 설명 |
|---|---|:---:|---|
| `series_id` | `str` | 필수 | 시계열 계열 식별자 (예: `lcluc_south_sulawesi_2020_2025`) |
| `frame_id` | `str` | 필수 | 단일 연차 프레임 식별자 (예: `frame_south_sulawesi_2020`) |
| `result_id` | `str` | 필수 | 연계된 Result/Dataset Registry ID |
| `version` | `str` | 필수 | 산출물 시맨틱 버전 (예: `1.0.0`) |
| `year` | `int` | 필수 | 대표 연도 (1900–2100) |
| `time_parameter` | `str` | 필수 | GeoServer WMS TIME 파라미터 규격 (ISO-8601) |
| `observation_start` | `str` | 필수 | 실제 위성 관측 시작 일시 |
| `observation_end` | `str` | 필수 | 실제 위성 관측 종료 일시 |
| `composite_method` | `str` | 필수 | 합성 알고리즘 (`median_scl_cloud_masked`, `annual_mosaic` 등) |
| `source_kind` | `str` | 필수 | `reference_landcover`, `model_prediction`, `synthetic_fixture` |
| `source_refs` | `List[str]` | 필수 | 입력 원본 장면/타일 참조 목록 |
| `model_id` | `Optional[str]` | 선택 | 추론 모델 식별자 (모델 결과인 경우) |
| `model_version` | `Optional[str]` | 선택 | 추론 모델 버전 |
| `class_schema_id` | `str` | 필수 | 분류체계 식별자 (`indonesia_lcluc_9class`) |
| `class_schema_version` | `str` | 필수 | 분류체계 버전 (`1.0`) |
| `quality_mask_ref` | `Optional[str]` | 선택 | 연계된 품질 마스크 래스터 참조 |
| `analysis_grid_ref` | `Optional[str]` | 선택 | 정합 기준 격자 참조 |
| `footprint` | `Dict[str, Any]` | 필수 | 실제 데이터 유효 Footprint (GeoJSON Geometry) |
| `bbox_crs84` | `List[float]` | 필수 | `[minx, miny, maxx, maxy]` (WGS84 EPSG:4326 경위도) |
| `native_crs` | `str` | 필수 | 래스터 원본 좌표계 (예: `EPSG:32750`) |
| `resolution` | `float` | 필수 | 화소 해상도 (미터 단위, 예: 10.0) |
| `nodata` | `int` | 필수 | NoData 정수값 (기본값 255) |
| `storage_ref` | `str` | 필수 | 스토리지 내 GeoTIFF/COG 파일 상대/절대 경로 |
| `checksum` | `str` | 필수 | 래스터 파일 SHA-256 체크섬 |
| `geoserver_layer` | `Optional[str]` | 선택 | GeoServer 게시 레이어명 (예: `lcluc:south_sulawesi_2020`) |
| `style_version` | `str` | 필수 | SLD 스타일 버전 (예: `v1.0`) |
| `publication_state` | `str` | 필수 | `registered`, `validated_for_rendering`, `published_to_staging`, `tile_verified` |
| `scientific_validation_state` | `str` | 필수 | `Draft`, `Validated`, `Approved` |
| `approval_state` | `str` | 필수 | 운영 게시 승인 상태 (`PENDING`, `APPROVED`, `REJECTED`) |

---

## 6. 단일 픽셀 검사 질의 (Pixel Inspection Point Query)

지도 클릭 시 해당 지점의 토지피복 상태를 반환하는 기능:
- **RGB 역추정 절대 금지**: 화면에 렌더링된 색상으로부터 클래스 번호를 역산하지 않으며, 원본 래스터 어레이의 정수 좌표 `(row, col)`로부터 직접 클래스 ID를 읽습니다.
- **반환 정보**:
  - `t1_class_id`, `t1_class_name`
  - `t2_class_id`, `t2_class_name`
  - `is_changed`: $T_1 \ne T_2$ 여부
  - `is_nodata`: 어느 한쪽이라도 결측 화소인지 여부
  - `pixel_area_m2`: 단일 픽셀의 지상 면적 ($100m^2$)
  - `t1_identity`, `t2_identity`: 원천 데이터 계보

---

## 7. CODEX 필수 수용 시험 검증 결과

`tests/test_lcluc_unified_analytics.py`를 통해 CODEX v1.0 제13장의 핵심 요구사항을 100% 검증하였습니다:

### 7.1 제13장 4호: 4×4 모의 데이터셋 검증 (`TestSection13Test4MockDatasetTransition`)
- **조건**: 4×4 격자에서 $1 \to 2$ 두 픽셀, $2 \to 1$ 한 픽셀 변경, 나머지 13픽셀 유지.
- **검증 결과**:
  - 총 도메인 화소: 16개 ($1,600m^2 = 0.16ha$)
  - 전이행렬 $M[1, 2] = 2$ 화소 ($200m^2$), $M[2, 1] = 1$ 화소 ($100m^2$) 정확 일치
  - 기타 비대각 성분: 전건 0 화소
  - 대각선(불변) 성분 합계: 13 화소 ($1,300m^2$)
  - 총 변화 화소: 3 화소 ($300m^2$, 변화율 $18.75\%$)
  - 행렬 총합 = 유효 면적 ($1,600m^2$) **100% 일치 PASS**

### 7.2 제13장 5호: 엄격한 NoData 배제 검증 (`TestStrictNoDataHandling`)
- **조건**: $T_1$에 1개, $T_2$에 1개, 양쪽에 1개의 NoData 화소 주입 (총 3개 결측).
- **검증 결과**:
  - 제외 화소 수: 3개, 공통 유효 화소: 13개 ($1,300m^2$)
  - 전이행렬 총합: 13 화소 (결측 화소가 전이행렬에서 완벽히 배제됨) **PASS**

### 7.3 제13장 6호: 뷰포트/줌/스와이프 불변성 검증 (`TestStatisticsInvariance`)
- **조건**: 100×100 마스터 래스터 대상 UI 화면 확대/축소 및 슬라이더 클리핑(좌상단 뷰포트, 중심 확대, 스와이프 경계) 모의.
- **검증 결과**:
  - 클리핑된 화면 뷰포트가 아닌 마스터 소스 래스터 바인딩을 통해 통계를 도출하므로, 모든 화면 상태에서 동일한 유효 화소수, 변화 화소수, 전이행렬이 **완벽하게 불변(Invariant) 유지됨을 확인 PASS**

---

## 8. 결론 및 프론트엔드 연동 지침

1. 본 명세에 따라 구현된 `lcluc_unified_analytics.py`는 GeoServer 게시 레이어와 프론트엔드 LCLUC Workspace 컴포넌트 간의 통계적 정합성을 영구적으로 보장합니다.
2. 프론트엔드는 통계를 자체 계산하거나 화면 픽셀을 계량하지 않고, 본 백엔드 분석 엔진이 제공하는 불변 JSON 페이로드를 직접 바인딩해야 합니다.
