# GeoServer WMS 1.3.0 & Authoritative Pixel Service Specification

## 1. 개요 및 목적 (Overview & Purpose)

본 문서는 `UI/GreenBlue_CODEX_LCLUC_Annual_Map_GeoServer_v1.0.md` (섹션 4, 5, 10, 15)의 요구사항에 따라, 연간 토지피복/토지이용 변화(LCLUC, Land Cover / Land Use Change) 분류 지도 및 전이(Transitions) 래스터를 **이산형(Discrete Categorical) 9개 클래스**로 무결하게 서빙하고, 프론트엔드 화면의 RGB 색상 추정이 아닌 **실제 소스 GeoTIFF로부터 1×1 픽셀의 정수 클래스 ID를 직접 조회(Authoritative Pixel Query)**하는 WMS 1.3.0 및 Pixel API 서비스의 기술 규격서입니다.

### 1.1 핵심 과제 및 설계 원칙
1. **이산형 범주형 데이터 보존 (Discrete Classification Integrity)**:
   - 연속형(Continuous) 영상과 달리 LCLUC 분류 결과(`label-worldcover.tif`, `transitions.tif`)는 0~8의 정수 클래스 ID입니다.
   - Bilinear나 Bicubic 등 보간(Interpolation) 리샘플링을 적용할 경우 클래스 경계면에서 존재하지 않는 소수점/가상 클래스(예: 수역 0과 산림 1 사이의 0.5)가 왜곡 렌더링되므로, **GeoServer SLD 및 VRT 엔진 전반에서 Nearest-Neighbor (최근접 이웃) 리샘플링을 엄격히 강제**합니다.
2. **단일 표준 9-클래스 팔레트 일원화 (Standard Color Palette)**:
   - 프로젝트 표준 9개 분류 색상(#2563eb, #15803d, #84cc16, #14b8a6, #eab308, #a16207, #dc2626, #a8a29e, #a5d8f3)을 GeoServer SLD(`<ColorMap type="values">`)와 백엔드 래스터 엔진(`get_discrete_lut`)에 동일하게 적용합니다.
   - 배경/NoData(255, 65535)는 완전 투명(Opacity 0.0)으로 처리합니다.
3. **신뢰할 수 있는 픽셀 검사 (Authoritative Pixel Query without Screen RGB Guessing)**:
   - 브라우저 캔버스의 축척/압축된 렌더링 RGB를 역추정(Screen RGB reverse lookup)하는 방식은 모바일/고DPI/안티에일리어싱 환경에서 오탐을 유발합니다.
   - WGS84 (경도, 위도) 좌표를 래스터 원본 좌표계(예: 인도네시아 UTM Zone 48S / EPSG:32748)로 직접 투영한 뒤, 디스크 상의 GeoTIFF로부터 `Window(col, row, 1, 1)` 크기로 원시 정수값을 즉시 읽어 정확한 클래스 정보를 응답합니다.

---

## 2. GeoServer 아키텍처 및 SLD 스타일 규격

### 2.1 GeoServer / GeoWebCache (GWC) 구성
- **GeoServer 버전**: 2.24+ (또는 2.25+)
- **Workspace**: `sdss_lcluc`
- **CoverageStore**: Cloud Optimized GeoTIFF (COG) 또는 타일드 GeoTIFF 피라미드
- **레이어 구성**:
  - `sdss_lcluc:lcluc_discrete_9classes`: 연도별 9-클래스 토지피복 분류도
  - `sdss_lcluc:transitions_annual`: 연간 변화 전이 래스터
- **WMS 버전**: 1.3.0 (CRS:84, EPSG:4326, EPSG:3857 지원)
- **GWC 격자셋 (Gridset)**: EPSG:3857 (Google Maps 호환), 타일 크기 256×256 또는 512×512, 포맷 `image/png`

### 2.2 공인 SLD 파일: `evidence/geoserver/sld/lcluc_discrete_9classes.sld`
GeoServer에 등록되는 공인 스타일 규격입니다. `<ColorMap type="values">`와 `<VendorOption name="resampling">nearest</VendorOption>`이 필수 선언되어 있습니다.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<StyledLayerDescriptor version="1.0.0" 
    xmlns="http://www.opengis.net/sld" 
    xmlns:ogc="http://www.opengis.net/ogc"
    xmlns:xlink="http://www.w3.org/1999/xlink" 
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://www.opengis.net/sld StyledLayerDescriptor.xsd">
  <NamedLayer>
    <Name>lcluc_discrete_9classes</Name>
    <UserStyle>
      <Title>LCLUC Discrete 9-Class Classification Style</Title>
      <Abstract>Authoritative discrete 9-class land cover classification style for GeoServer WMS 1.3.0</Abstract>
      <FeatureTypeStyle>
        <Rule>
          <RasterSymbolizer>
            <Opacity>1.0</Opacity>
            <ColorMap type="values">
              <!-- Class 0: Water -->
              <ColorMapEntry color="#2563eb" quantity="0" label="Water" opacity="1.0"/>
              <!-- Class 1: Trees / Forest -->
              <ColorMapEntry color="#15803d" quantity="1" label="Trees" opacity="1.0"/>
              <!-- Class 2: Flooded vegetation -->
              <ColorMapEntry color="#84cc16" quantity="2" label="Flooded vegetation" opacity="1.0"/>
              <!-- Class 3: Crops -->
              <ColorMapEntry color="#14b8a6" quantity="3" label="Crops" opacity="1.0"/>
              <!-- Class 4: Built area -->
              <ColorMapEntry color="#eab308" quantity="4" label="Built area" opacity="1.0"/>
              <!-- Class 5: Bare ground -->
              <ColorMapEntry color="#a16207" quantity="5" label="Bare ground" opacity="1.0"/>
              <!-- Class 6: Snow / Ice -->
              <ColorMapEntry color="#dc2626" quantity="6" label="Snow / Ice" opacity="1.0"/>
              <!-- Class 7: Clouds -->
              <ColorMapEntry color="#a8a29e" quantity="7" label="Clouds" opacity="1.0"/>
              <!-- Class 8: Rangeland -->
              <ColorMapEntry color="#a5d8f3" quantity="8" label="Rangeland" opacity="1.0"/>
              <!-- Transparent NoData Values -->
              <ColorMapEntry color="#000000" quantity="255" label="NoData" opacity="0.0"/>
              <ColorMapEntry color="#000000" quantity="65535" label="NoData 16-bit" opacity="0.0"/>
            </ColorMap>
            <VendorOption name="resampling">nearest</VendorOption>
          </RasterSymbolizer>
        </Rule>
      </FeatureTypeStyle>
    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>
```

### 2.3 9개 표준 클래스 정의표

| Class ID | Class Name | Hex Color | Description | ESA WorldCover Raw Code |
| :---: | :---: | :---: | :---: | :---: |
| **0** | Water | `#2563eb` | 수역 (하천, 호수, 바다) | 80 |
| **1** | Trees | `#15803d` | 산림 / 수목 밀집지 | 10 |
| **2** | Flooded vegetation | `#84cc16` | 침수 식생 / 습지 식물 | 90 |
| **3** | Crops | `#14b8a6` | 농경지 / 경작지 | 40 |
| **4** | Built area | `#eab308` | 인공 건축지 / 도시화 지역 | 50 |
| **5** | Bare ground | `#a16207` | 나지 / 불모지 | 60 |
| **6** | Snow / Ice | `#dc2626` | 설빙 (인도네시아 만년설/빙하) | 70 |
| **7** | Clouds | `#a8a29e` | 구름 차폐 | N/A |
| **8** | Rangeland | `#a5d8f3` | 관목초지 / 방목지 | 20, 30 |
| **255 / 65535** | NoData | `#000000` (Opacity 0) | 결측치 및 경계 외 영역 | 255 |

---

## 3. 백엔드 WMS 래스터 엔진 구현

### 3.1 모듈 위치: `backend/app/ml/raster_tile_engine.py`

GeoServer를 모방하거나 직접 서빙 가능한 내장 고성능 WMS 1.3.0 렌더러와 원본 픽셀 질의 엔진이 구현되어 있습니다.

#### 주요 핵심 함수:
1. `get_discrete_lut(style="standard") -> Tuple[List[int], List[int], List[int], List[int]]`:
   - 256개 인덱스에 대한 RGBA 룩업테이블을 반환합니다.
   - 팔레트 이미지(PIL Mode 'P') 생성을 지원하며 255번 인덱스는 알파 0(완전 투명)으로 설정됩니다.
2. `render_bbox(tif_path, minx, miny, maxx, maxy, src_srs="EPSG:4326", width=256, height=256, format="image/png", transparent=True) -> bytes`:
   - 주어진 BBOX(EPSG:4326 또는 EPSG:3857)에 대해 `rasterio.vrt.WarpedVRT`를 생성합니다.
   - `resampling=Resampling.nearest`를 강제하여 임의의 클래스 보간 왜곡을 원천 차단합니다.
   - ESA WorldCover 원시 클래스(10, 20, 30...)가 포함된 GeoTIFF의 경우 0..8 표준 클래스로 자동 매핑합니다.
   - 투명 배경을 보장하는 최적화된 8-bit PNG 바이트를 반환합니다.
3. `query_pixel(tif_path, lng, lat) -> Dict[str, Any]`:
   - 입력된 WGS84 좌표 `(lng, lat)`를 소스 GeoTIFF의 네이티브 좌표계(CRS)로 실시간 투영합니다.
   - 래스터의 Affine 변환 행렬을 적용하여 정확한 `(col, row)` 정수 인덱스를 계산합니다.
   - `rasterio.windows.Window(col, row, 1, 1)`를 이용해 단 1개 픽셀만 디스크에서 읽어옵니다.
   - 반환값에 원시값(`raw_value`), 9-클래스 ID(`class_id`), 클래스명(`class_name`), 표준 색상코드(`color`), NoData 여부(`is_nodata`), 소스 파일 경로(`source_file`), 좌표계(`source_crs`)를 구조화하여 제공합니다.

---

## 4. API 엔드포인트 규격서

`backend/app/tile_router.py`에 구현되어 FastAPI 앱에 마운트된 엔드포인트 명세입니다.

### 4.1 OGC WMS 1.3.0 엔드포인트: `GET /v1/lcluc/wms`

#### [Case A] GetCapabilities 요청
- **URL**: `GET /v1/lcluc/wms?SERVICE=WMS&REQUEST=GetCapabilities`
- **Response**: `text/xml; charset=utf-8`
- **내용**: WMS 1.3.0 표준 메타데이터, 지원 CRS(EPSG:4326, EPSG:3857), 인도네시아 전국 및 First Group 6개 주 레이어 목록, `lcluc_discrete_9classes` 스타일 명세 반환.

#### [Case B] GetMap 렌더링 요청
- **URL**: `GET /v1/lcluc/wms?SERVICE=WMS&REQUEST=GetMap&VERSION=1.3.0&LAYERS={layer}&CRS={crs}&BBOX={miny,minx,maxy,maxx}&WIDTH={w}&HEIGHT={h}&FORMAT=image/png&TRANSPARENT=TRUE`
- **파라미터**:
  - `SERVICE`: `WMS` (필수)
  - `REQUEST`: `GetMap` (필수)
  - `VERSION`: `1.3.0` (기본값)
  - `LAYERS`: 레이어 식별자 (예: `banten-2021`, `transitions-2021`, `jawa_barat-2021`)
  - `CRS` 또는 `SRS`: `EPSG:4326` 또는 `EPSG:3857` (WMS 1.3.0 기준 EPSG:4326은 `miny,minx,maxy,maxx` 순서 지원)
  - `BBOX`: 쉼표로 구분된 경계 좌표
  - `WIDTH`, `HEIGHT`: 출력 이미지 크기 (픽셀)
  - `FORMAT`: `image/png`
  - `TRANSPARENT`: `TRUE` (기본값)
- **Response**: `image/png` (Nearest-neighbor 리샘플링 적용된 8-bit 팔레트 PNG)

---

### 4.2 공인 픽셀 조회 엔드포인트: `GET /v1/lcluc/pixel`

프론트엔드 지도에서 마우스 클릭 또는 마우스오버 시 해당 지점의 진짜 토지피복 클래스를 검사하는 엔드포인트입니다.

#### 요청 파라미터
| Parameter | Type | Required | Description | Example |
| :--- | :---: | :---: | :--- | :--- |
| `lng` | Float | Yes | WGS84 경도 (Longitude) | `106.1343` |
| `lat` | Float | Yes | WGS84 위도 (Latitude) | `-6.4375` |
| `layer` | String | No | 레이어 지정 (생략 시 자동 검색) | `banten-2021` |
| `province` | String | No | 프로빈스명 (소문자, 언더스코어) | `banten` |
| `year` | Integer | No | 조회 연도 (기본값: `2021`) | `2021` |

#### 응답 스키마 (JSON)
```json
{
  "status": "success",
  "coordinates": {
    "lng": 106.1343,
    "lat": -6.4375
  },
  "raw_value": 10,
  "class_id": 1,
  "class_name": "Trees",
  "color": "#15803d",
  "is_nodata": false,
  "source_file": "banten-2021/label-worldcover.tif",
  "source_crs": "EPSG:32748"
}
```

#### NoData / 래스터 범위 외 클릭 시 응답
```json
{
  "status": "nodata",
  "coordinates": {
    "lng": 100.0,
    "lat": 0.0
  },
  "raw_value": null,
  "class_id": null,
  "class_name": "NoData",
  "color": "#00000000",
  "is_nodata": true,
  "source_file": "banten-2021/label-worldcover.tif",
  "source_crs": "EPSG:32748"
}
```

---

## 5. 시험 및 검증 증거 (Verification & Test Evidence)

`tests/test_geoserver_wms_pixel_service.py`를 통해 모든 기능이 자동화 테스트로 철저히 검증되었습니다.

### 5.1 테스트 결과
- **테스트 파일**: `tests/test_geoserver_wms_pixel_service.py`
- **테스트 케이스 수**: 9개
- **결과**: `Ran 9 tests in 3.375s — OK (All Passed)`

```text
test_sld_file_structure_and_colormap (tests.test_geoserver_wms_pixel_service.TestGeoServerSLDAndStyle)
  - SLD XML 루트, NamedLayer, ColorMap type='values' 검증 통과
  - 9개 표준 클래스 및 255/65535 NoData 투명도 선언 검증 통과
  - VendorOption name='resampling' nearest 선언 검증 통과

test_discrete_lut_definitions (tests.test_geoserver_wms_pixel_service.TestRasterEngineDiscreteMapping)
  - 256 엔트리 RGBA LUT 생성 및 9개 표준 색상 RGB 매핑 검증 통과
  - 인덱스 255의 Alpha=0 투명 처리 검증 통과

test_worldcover_and_esri_class_remapping (tests.test_geoserver_wms_pixel_service.TestRasterEngineDiscreteMapping)
  - ESA WorldCover 코드(10, 20, 30, 40, 50, 60, 70, 80, 90) -> 프로젝트 0..8 클래스 변환 검증 통과

test_authoritative_pixel_query_on_real_geotiff (tests.test_geoserver_wms_pixel_service.TestRasterEngineDiscreteMapping)
  - 실제 First Group Banten GeoTIFF(data/first-group-2021/banten-2021/label-worldcover.tif) 기반 검증
  - 중심 좌표(106.1343, -6.4375) 질의 시 raw_value=10, class_id=1, class_name='Trees' 정확 검증 통과
  - 래스터 범위 외 좌표 질의 시 is_nodata=True 정상 응답 검증 통과

test_render_bbox_discrete_png (tests.test_geoserver_wms_pixel_service.TestRasterEngineDiscreteMapping)
  - BBOX 영역 렌더링 시 투명 PNG 생성 및 Nearest-Neighbor 이산형 픽셀 무결성 검증 통과

test_wms_getcapabilities (tests.test_geoserver_wms_pixel_service.TestTileRouterWmsPixelEndpoints)
  - GET /v1/lcluc/wms?SERVICE=WMS&REQUEST=GetCapabilities WMS 1.3.0 XML 응답 검증 통과

test_wms_getmap_success (tests.test_geoserver_wms_pixel_service.TestTileRouterWmsPixelEndpoints)
  - GET /v1/lcluc/wms GetMap PNG 200 OK 및 이미지 헤더 검증 통과

test_wms_getmap_missing_params (tests.test_geoserver_wms_pixel_service.TestTileRouterWmsPixelEndpoints)
  - 필수 BBOX 파라미터 누락 시 400 Bad Request 검증 통과

test_pixel_query_endpoint_real_banten (tests.test_geoserver_wms_pixel_service.TestTileRouterWmsPixelEndpoints)
  - GET /v1/lcluc/pixel?lng=106.1343&lat=-6.4375 엔드포인트 200 OK 및 구조화된 정수 클래스 응답 검증 통과
```

---

## 6. 클라이언트(웹 UI) 연동 가이드

### 6.1 MapLibre GL JS / Mapbox GL 레이어 연동
MapLibre GL에서는 WMS 타일 소스를 다음과 같이 등록하여 왜곡 없는 이산형 타일을 수신할 수 있습니다.

```javascript
map.addSource('lcluc-wms-source', {
  type: 'raster',
  tiles: [
    '/v1/lcluc/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=banten-2021' +
    '&CRS=EPSG:3857&BBOX={bbox-epsg-3857}&WIDTH=256&HEIGHT=256&FORMAT=image/png&TRANSPARENT=TRUE'
  ],
  tileSize: 256
});

map.addLayer({
  id: 'lcluc-wms-layer',
  type: 'raster',
  source: 'lcluc-wms-source',
  paint: {
    'raster-resampling': 'nearest' // 클라이언트 렌더링 보간 방지
  }
});
```

### 6.2 클릭 이벤트 시 신뢰할 수 있는 픽셀 질의 (Click Inspection)
화면 RGB를 분석하지 않고, 클릭된 지점의 지리 좌표를 `/v1/lcluc/pixel`로 전송합니다:

```javascript
map.on('click', async (e) => {
  const { lng, lat } = e.lngLat;
  const res = await fetch(`/v1/lcluc/pixel?lng=${lng}&lat=${lat}&layer=banten-2021`);
  const data = await res.json();
  
  if (data.status === 'success' && !data.is_nodata) {
    new maplibregl.Popup()
      .setLngLat([lng, lat])
      .setHTML(`
        <div style="font-family: sans-serif; padding: 4px;">
          <h4 style="margin: 0 0 6px 0; color: #1e293b;">${data.class_name}</h4>
          <div style="display: flex; align-items: center; gap: 8px;">
            <span style="display: inline-block; width: 14px; height: 14px; background: ${data.color}; border: 1px solid #94a3b8; border-radius: 2px;"></span>
            <span>Class ID: <b>${data.class_id}</b> (Raw: ${data.raw_value})</span>
          </div>
          <div style="font-size: 11px; color: #64748b; margin-top: 6px;">CRS: ${data.source_crs}</div>
        </div>
      `)
      .addTo(map);
  }
});
```

---

## 7. 결론 및 산출물 요약

| 구성 요소 | 산출물 파일 경로 | 상태 |
| :--- | :--- | :---: |
| **GeoServer SLD** | `evidence/geoserver/sld/lcluc_discrete_9classes.sld` | VERIFIED_REAL |
| **래스터 타일 엔진** | `backend/app/ml/raster_tile_engine.py` | VERIFIED_REAL |
| **WMS & Pixel API** | `backend/app/tile_router.py` | VERIFIED_REAL |
| **종합 단위 테스트** | `tests/test_geoserver_wms_pixel_service.py` | VERIFIED_REAL (9/9 Pass) |
| **기술 규격 문서** | `docs/lcluc-map/geoserver-wms-service-spec.md` | VERIFIED_REAL |
