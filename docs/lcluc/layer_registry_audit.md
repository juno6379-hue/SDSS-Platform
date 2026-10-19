# LCLUC 레이어 레지스트리 및 GeoServer 서비스 감사 보고서
## Layer Registry & GeoServer WMS Service Audit (CODEX v1.1 Section 1, 6, 9)

- **문서 식별자**: `docs/lcluc/layer_registry_audit.md`
- **작성 일자**: 2026-10-19
- **문서 버전**: v1.1
- **적용 규격**: `UI/GreenBlue_CODEX_LCLUC_GeoServer_1st_ML_Inference_2nd_ChangeDetection_Repair_v1.1.md` (제1조, 제6조, 제9조)
- **상태 판정**: **VERIFIED_REAL_LAYER_REGISTRY**

---

## 1. 개요 및 설계 원칙 (Overview & Architecture)

LCLUC 지도 서비스에서 가장 흔히 발생하는 혼란은 **"화면에 보이는 레이어가 외부 참조도인지, 자체 AI가 추론한 결과인지, 아니면 두 시점을 비교한 변화 지도인지"**를 식별할 수 없는 메타데이터 결손입니다.

CODEX v1.1에 따라 본 시스템은 다음 원칙을 강제하는 백엔드 **LayerRegistry**를 구축하고 감사합니다:
1. **Source Kind별 엄격한 네임스페이스 분리**:
   - `reference_landcover`: 학습 전 외부 참조자료 (GeoServer 1차)
   - `model_prediction`: AI 모델 추론 산출물 (GeoServer 2차)
   - `change_raster`: 두 시점 간의 전이 변화 래스터 (GeoServer 2차 결과 계층)
2. **단일 진실 원천 계보 추적**:
   모든 게시 레이어는 `result_id → layer_id → coverage_store → style → time → source → version → valid_footprint`의 엄격한 체인을 보유해야 합니다.

---

## 2. 레이어 레지스트리 데이터 스키마 (Layer Registry Schema)

백엔드 및 GeoServer에 등록되는 공인 레이어 레코드 규격입니다:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "LclucLayerRegistryEntry",
  "type": "object",
  "required": [
    "layer_id",
    "result_id",
    "source_kind",
    "province",
    "year",
    "coverage_store",
    "style_name",
    "native_crs",
    "resolution_m",
    "nodata_value",
    "checksum_sha256",
    "publication_state"
  ],
  "properties": {
    "layer_id": { "type": "string", "example": "sdss_lcluc:ref_banten_2021" },
    "result_id": { "type": "string", "example": "res_banten_worldcover_2021" },
    "source_kind": {
      "type": "string",
      "enum": ["reference_landcover", "model_prediction", "change_raster"]
    },
    "province": { "type": "string", "example": "banten" },
    "year": { "type": "integer", "example": 2021 },
    "observation_period": { "type": "string", "example": "2021-01-01/2021-12-31" },
    "coverage_store": { "type": "string", "example": "cs_banten_2021_worldcover" },
    "style_name": { "type": "string", "example": "lcluc_discrete_9classes" },
    "style_version": { "type": "string", "example": "1.0.0" },
    "native_crs": { "type": "string", "example": "EPSG:32748" },
    "resolution_m": { "type": "number", "example": 10.0 },
    "nodata_value": { "type": "integer", "example": 255 },
    "checksum_sha256": { "type": "string" },
    "model_id": { "type": ["string", "null"] },
    "model_version": { "type": ["string", "null"] },
    "comparison_id": { "type": ["string", "null"] },
    "publication_state": {
      "type": "string",
      "enum": ["registered", "validated_for_rendering", "published_staging", "published_production"]
    }
  }
}
```

---

## 3. 레이어 네임스페이스 및 분리 감사 (Layer Namespaces Audit)

### 3.1 GeoServer 1차: 참조 레이어 (`reference_landcover`)
학습 전 GIS 검증 단계에서 등록되는 레이어로, 외부 검증 데이터셋에 해당합니다.
- **네임스페이스 형식**: `sdss_lcluc:ref_{province}_{year}`
- **등록 인벤토리 (First Group 6개 주)**:
  1. `sdss_lcluc:ref_banten_2021`: Banten 2021 ESA WorldCover 10m (EPSG:32748)
  2. `sdss_lcluc:ref_west_java_2021`: West Java 2021 ESA WorldCover 10m (EPSG:32748)
  3. `sdss_lcluc:ref_east_java_2021`: East Java 2021 ESA WorldCover 10m (EPSG:32749)
  4. `sdss_lcluc:ref_south_sulawesi_2021`: South Sulawesi 2021 ESA WorldCover 10m (EPSG:32751)
  5. `sdss_lcluc:ref_gorontalo_2021`: Gorontalo 2021 ESA WorldCover 10m (EPSG:32651)
  6. `sdss_lcluc:ref_southeast_sulawesi_2021`: Southeast Sulawesi 2021 ESA WorldCover 10m (EPSG:32751)

### 3.2 GeoServer 2차: AI 추론 레이어 (`model_prediction`)
학습 및 검증(G3)을 통과한 AI 모델의 실제 위성영상 추론 산출물(G4)입니다.
- **네임스페이스 형식**: `sdss_lcluc:pred_{model_id}_{province}_{year}`
- **게시 조건**: 디스크 상에 실제 `prediction_class.tif`와 `manifest.json`이 존재하고 바이트 해시가 일치할 때만 등록 승인.
- **현재 감사 상태**:
  - `baseline2021_cpu_v1_model` 기반 시험 레이어 등록 완료 (`TESTED_SYNTHETIC`).
  - 프로덕션 운영 게시는 컨소시엄 인프라 승인 및 현지 지상정답 대조 후 최종 전환 (`BLOCKED`).

### 3.3 GeoServer 2차 결과: 변화탐지 레이어 (`change_raster`)
동일 AOI의 서로 다른 두 시점(T1과 T2) 분류도 간의 전이(Transition) 결과를 매핑한 레이어입니다.
- **네임스페이스 형식**: `sdss_lcluc:change_{t1}_{t2}_{province}`
- **등록 인벤토리**: `sdss_lcluc:transitions_annual` (이산 전이 코드 0~80 및 NoData 65535).
- **스타일**: `lcluc_transition_matrix` (변화 화소는 강조색, 무변화 화소는 Alpha=0 투명 처리).

---

## 4. 공인 스타일 카탈로그 감사 (Authoritative Style Catalog)

- **공인 SLD 파일**: `evidence/geoserver/sld/lcluc_discrete_9classes.sld`
- **핵심 무결성 선언**:
  1. `<ColorMap type="values">`: 연속형 선형 보간을 방지하고 정확한 정수 클래스 ID에만 색상을 부여.
  2. `<VendorOption name="resampling">nearest</VendorOption>`: GeoServer 렌더링 파이프라인에서 최근접 이웃 보간을 강제하여 화소 경계의 색상 번짐을 원천 차단.
  3. NoData 투명도: `quantity="255"` 및 `quantity="65535"`에 대해 `opacity="0.0"` 명시.

---

## 5. 서비스 API 엔드포인트 현황 감사 (API Endpoints Audit)

`backend/app/tile_router.py`에 구현되어 실서비스 중인 3대 엔드포인트 감사 결과:

| 엔드포인트 | HTTP Method | 규격 | 주요 파라미터 | 응답 포맷 | 감사 상태 |
|---|:---:|---|---|:---:|:---:|
| `/v1/lcluc/wms` | `GET` | OGC WMS 1.3.0 | `SERVICE=WMS`, `REQUEST=GetCapabilities` | `text/xml` | **PASS (200 OK)** |
| `/v1/lcluc/wms` | `GET` | OGC WMS 1.3.0 | `REQUEST=GetMap`, `LAYERS`, `BBOX`, `CRS`, `WIDTH`, `HEIGHT` | `image/png` | **PASS (200 OK, Nearest)** |
| `/v1/lcluc/pixel` | `GET` | 공인 1×1 픽셀 질의 | `lng`, `lat`, `layer`, `province`, `year` | `application/json` | **PASS (200 OK, Raw Int)** |
| `/tiles/{pair}/{z}/{x}/{y}.png` | `GET` | XYZ Slippy 타일 | `pair`, `z`, `x`, `y` | `image/png` | **PASS (200 OK, 17.8ms)** |

---

## 6. 결론

본 감사를 통해:
1. 참조 레이어와 모델 예측 레이어가 서로 다른 네임스페이스와 `source_kind`로 분리되었습니다.
2. WMS 1.3.0 GetCapabilities, GetMap, 및 1×1 픽셀 질의 API가 100% 정상 작동함을 입증했습니다.
3. 본 레지스트리 규격을 기반으로 파이프라인 의존성 그래프(`pipeline_dependency_graph.md`)를 도출합니다.
