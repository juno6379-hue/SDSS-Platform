# 344. LCLUC 다중 포맷 내보내기(Export) 서비스 — 격리 구현·시험

상태: **TESTED_SYNTHETIC**. 격리 작업공간(`evidence/integration/lcluc-export-workspace-20261019`)에서 5대 표준 내보내기 포맷 엔진과 FastAPI 라우터 구현을 완료하고 13개 단위 시험을 전원 통과(`OK`)했습니다. 메인 브랜치 코드(`backend/app/`, `frontend/src/`)는 직접 수정하지 않고 규격 및 통합 어댑터로 격리 작성되었습니다.

---

## 1. 쉬운 설명

LCLUC(토지피복 및 토지이용 변화 탐지) 워크플로가 생성한 분석 결과(`transitions.tif`, `changes.geojson`, `report.json`)는 연구원, 지자체 실무자, 보고서 작성자, GIS 전문가 등 다양한 이해관계자에 의해 서로 다른 도구(QGIS, ArcGIS, Excel, 웹 브라우저 등)에서 활용됩니다.

기존 시스템은 브라우저 상의 기본 시각화와 원시 파일 다운로드만 제공하여, 다음과 같은 실무적 공백이 존재했습니다:
1. **GIS 시각화 공백**: GeoTIFF를 QGIS에 올렸을 때 색상표가 없어 흑백으로 열리며, 사용자가 일일이 81개 범주별 색상을 수동 지정해야 함.
2. **벡터 속성 공백**: GeoJSON 파일에 단순 숫자 코드만 들어 있어, 어떤 범주에서 어떤 범주로 바뀌었는지(`trees -> built`)와 헥타르(ha) 단위 면적 속성이 누락됨.
3. **학술·행정 보고서 공백**: 9×9 전이 행렬의 초기면적, 최종면적, 총유입(Gain), 총유출(Loss), 순변화(Net Change)가 정리된 표준 CSV와 시각 차트가 포함된 원클릭 요약 보고서 부재.
4. **일괄 패키징 부재**: 분석 결과를 관련자에게 전달할 때 모든 산출물과 무결성 해시(SHA256)를 담은 단일 압축 파일(ZIP Bundle) 생성 기능 부재.

**344 구현**은 이 문제를 해결하기 위해 **통합 다중 포맷 내보내기 서비스(`export_service_engine.py` 및 `export_router.py`)**를 도입합니다.
- 표준 Color Table이 내장된 **GeoTIFF** (`.tif`)
- 헥타르 단위 면적과 전이 명칭이 부여된 **Enriched GeoJSON** (`.geojson`)
- 수학적 대차 균형과 요약 통계가 완비된 **9×9 전이행렬 CSV** (`.csv`)
- 외부 인터넷 연결 없이 오프라인에서 열리는 **독립형 임원 요약 HTML 보고서** (`.html`, 내장 SVG 차트 포함)
- 기계 판독용 전체 메트릭 **JSON 보고서** (`.json`)
- 모든 산출물과 SHA256 체크섬 매니페스트를 담은 **통합 ZIP 번들** (`.zip`)

---

## 2. 이론적 배경

### 2.1 GeoTIFF 표준 색상표(RGBA Color Table)와 메타데이터 태그
`transitions.tif`에 저장된 uint16 전이 코드($0..80$, nodata $65535$)를 8비트 인덱스 색상 래스터(`uint8`, nodata $255$)로 변환하고 TIFF 사양(TIFF 6.0 ColorMap Tag 320)에 따라 표준 색상표를 밴드에 직접 기록합니다.
- 무변화 화소 및 결측치: Nodata $255$로 마스킹되고 RGBA `(0, 0, 0, 0)` 투명 처리.
- 전이 화소: 도달 범주(`to_class`)의 고유 색상(`WORKFLOW_CLASS_COLORS`) 매핑.
- GeoTIFF 헤더 태그: `workflow_id`, `date_range`, `classes`, `software`를 기록하여 QGIS/ArcGIS Pro에서 파일을 열자마자 추가 설정 없이 투명도가 적용된 주제도가 즉시 표출됩니다.

### 2.2 GeoJSON 속성 보강(Property Enrichment)
기존의 최소 속성(`from_class`, `to_class`, `transition_code`)에 실무 분석용 필드를 보강합니다:
- `from_class_name`, `to_class_name`: 영문 표준 범주명 (예: `trees`, `built`).
- `transition_name`: 직관적 전이 표현 (예: `trees -> built`).
- `area_ha`: 폴리곤 투영/타원체 면적을 헥타르 단위($\text{ha} = \text{m}^2 / 10,000$)로 환산하여 소수점 4자리까지 제공.
- `confidence`: 분류 차이 신뢰도 메트릭.

### 2.3 9×9 전이 행렬의 수학적 대차 평형 (Zero-Sum Net Change)
토지피복 전이 행렬에서 임의의 범주 $i$에 대해 다음과 같은 물리적 보존 법칙이 엄격히 성립해야 합니다:
$$\text{Initial Area}_i = \sum_{j=1}^{K} A_{i,j}, \quad \text{Final Area}_j = \sum_{i=1}^{K} A_{i,j}$$
$$\text{Gross Loss}_i = \text{Initial Area}_i - A_{i,i}, \quad \text{Gross Gain}_j = \text{Final Area}_j - A_{j,j}$$
$$\text{Net Change}_k = \text{Final Area}_k - \text{Initial Area}_k = \text{Gross Gain}_k - \text{Gross Loss}_k$$
전체 영역의 총면적은 보존되므로 모든 범주의 순변화 합은 반드시 0이어야 합니다:
$$\sum_{k=1}^{K} \text{Net Change}_k \equiv 0$$
344 CSV 내보내기 엔진은 이 수식을 완전히 검증하여 마진(Margins) 및 순변화 요약 블록을 자동으로 생성합니다.

### 2.4 오프라인 자립형(Self-Contained) HTML 보고서와 내장 SVG
외부 CDN(Google Fonts, 외부 JS 차트 라이브러리)에 의존하지 않고, 순수 인라인 CSS와 인라인 SVG 벡터 그래픽만으로 차트를 렌더링합니다:
- 범주별 순변화 증감 막대 차트: 증가분은 고유 클래스 색상, 감소분은 붉은색 계열로 대칭 축 기준 렌더링.
- 보안 폐쇄망(Air-gapped) 환경이나 오프라인 브라우저에서도 100% 동일한 비주얼 보장 및 브라우저 원클릭 인쇄(Ctrl+P $\to$ PDF 저장) 완벽 지원.

### 2.5 엄격한 디렉터리 격리(Strict Containment) ZIP 번들
ZIP 파일 내 상대 경로 탈출(`../`) 공격을 원천 차단하고 `export_bundle_{workflow_id[:12]}_{pair}/` 네임스페이스 하위에만 파일을 패키징합니다. 모든 파일의 크기와 SHA256 체크섬을 기록한 `MANIFEST.json`을 동봉하여 전송 중 데이터 위변조를 검증할 수 있습니다.

---

## 3. 코드·데이터 동작 및 API 규격

### 3.1 구현 파일 목록 (`evidence/integration/lcluc-export-workspace-20261019/`)

| 파일 | 역할 및 핵심 기능 |
|---|---|
| `export_service_engine.py` | 5대 포맷 내보내기 코어 엔진: GeoTIFF(색상표·재투영), GeoJSON(속성 보강), CSV(마진·대차평형), HTML(SVG 임베딩), ZIP 번들 |
| `export_router.py` | FastAPI 라우터: `/export/{format}` 단일 엔드포인트 다중 포맷 디스패치 및 네임스페이스 보안 격리 |
| `test_export_service_engine.py` | 13개 단위 시험: 파일 포맷 무결성, 색상표, 수학적 평형, ZIP 무결성, API 통합 검증 |

### 3.2 엔드포인트 규격

```http
GET /v1/lcluc/workflows/{identifier}/export/{format}
```

#### 1) 경로 및 쿼리 파라미터
- **`identifier`** (Path): 64자리 Hex SHA256 워크플로 ID.
- **`format`** (Path): `tif` (또는 `geotiff`), `geojson`, `csv`, `html`, `json`, `zip`.
- **`pair`** (Query, Optional): 분석 연도쌍 (예: `2020-2021`). 생략 시 산출물 디렉터리에서 첫 번째 연도쌍을 자동 탐색.
- **`to_class`** (Query, Optional): 도달 범주 필터 (0..8 정수, 예: 6은 도시 확장지만 추출).
- **`from_class`** (Query, Optional): 출발 범주 필터 (0..8 정수, 예: 1은 산림 훼손지만 추출).
- **`unit`** (Query, Optional): 면적 단위 (`ha` 기본값, `m2`, `km2`).
- **`crs`** (Query, Optional): GeoTIFF 재투영 대상 좌표계 (`EPSG:3857`, `EPSG:4326`).
- **`changes_only`** (Query, Optional, 기본값 `true`): 무변화 화소 투명화 여부.

#### 2) 포맷별 응답 사양

| 포맷 | Content-Type | 첨부 파일명 규칙 | 주요 내용 |
|---|---|---|---|
| `tif` | `image/tiff` | `lcluc_transitions_{pair}.tif` | 8-bit Indexed TIFF, RGBA 색상표, GeoTIFF 태그 |
| `geojson` | `application/geo+json` | `lcluc_changes_{pair}.geojson` | 속성 보강 벡터 폴리곤 (`area_ha`, `transition_name` 등) |
| `csv` | `text/csv; charset=utf-8` | `lcluc_transition_matrix_{pair}_{unit}.csv` | 9×9 전이 행렬, 초기/최종/유입/유출/순변화 및 통계 블록 |
| `html` | `text/html; charset=utf-8` | `lcluc_summary_report_{pair}.html` | 자립형 임원 요약 보고서 (KPI 카드, SVG 순변화 차트) |
| `json` | `application/json` | `lcluc_analytical_report_{pair}.json` | 기계 판독용 전체 메트릭 및 전이 순위 데이터 |
| `zip` | `application/zip` | `lcluc_export_bundle_{id}_{pair}.zip` | 위 5개 파일 + `MANIFEST.json` 통합 압축 패키지 |

---

## 4. 테스트 증거

### 4.1 단위 시험 결과 (`python -m unittest`)
13개 단위 시험이 모두 성공(`OK`)했습니다.
```text
Ran 13 tests in 2.217s
OK
```

1. `test_geotiff_export_structure_and_colormap`: TIFF 헤더 매직 바이트, 256개 색상표 엔트리, 255번 Nodata 투명도, 메타데이터 태그(`workflow_id`, `date_range`, `classes`) 검증 통과.
2. `test_geotiff_filter_and_reprojection`: `to_class=6` 필터링 시 비대상 화소 Nodata 변환 및 EPSG:4326 재투영 좌표계 검증 통과.
3. `test_geojson_export_enrichment`: FeatureCollection 구조, 범주명 한글/영문 매핑, `area_ha` 면적 환산 정확도, 클래스 필터링 검증 통과.
4. `test_csv_export_matrix_balance`: 9×9 행렬 수치 일치, 행/열 합산 마진, **전 클래스 순변화 합 $\sum \text{Net Change} = 0.000$ 대차 평형** 및 단위 환산 검증 통과.
5. `test_json_and_html_report_export`: 기계 판독용 JSON 구조 및 자립형 HTML 내장 SVG 차트, KPI 카드, 책임 고지문 렌더링 검증 통과.
6. `test_zip_bundle_export`: ZIP 아카이브 무결성, 상대 경로 탈출 방지 디렉터리 격리, 5개 산출물 실시간 압축 및 **`MANIFEST.json`의 SHA256 체크섬 100% 일치** 검증 통과.
7. `ExportRouterApiTests` (7건): 6개 포맷별 HTTP 200 및 MIME/Content-Disposition 검증, 미지원 포맷 400 거부, 미존재 워크플로 404 거부, 미완료 워크플로 409 거부, 파라미터 생략 시 자동 pair 탐색 검증 통과.

---

## 5. 발표 스크립트 (1~2분 브리핑)

> "기존 시스템에서는 변화 분석 결과를 브라우저 화면에서만 보거나 일부 원시 파일만 따로 받아야 해서, 실무자가 QGIS에서 색상을 일일이 입히거나 엑셀에서 전이 행렬을 수작업으로 계산해야 하는 번거로움이 있었습니다.
> 
> 저희는 오늘 토지피복 변화 탐지 결과를 실무 도구에 맞춰 즉시 활용할 수 있는 **원클릭 다중 포맷 내보내기 엔진**을 완성했습니다.
> 
> QGIS나 ArcGIS에 바로 띄울 수 있는 표준 색상표 내장 **GeoTIFF**, 헥타르 단위 면적과 전이 명칭이 완비된 **GeoJSON**, 대차 평형이 입증된 9×9 **전이행렬 CSV**, 그리고 인터넷이 없는 폐쇄망에서도 열리는 SVG 차트 내장 **임원용 HTML 요약 보고서**를 제공합니다.
> 
> 마지막으로 이 모든 파일과 위변조 검증용 SHA256 매니페스트를 담은 **통합 ZIP 번들**까지 단 한 번의 API 호출로 즉시 다운로드할 수 있어, 연구자와 행정 실무자의 업무 효율을 획기적으로 높였습니다."

---

## 6. 자주 묻는 질문 (FAQ)

**Q1: QGIS나 ArcGIS Pro에서 GeoTIFF를 열었을 때 자동으로 색상이 입혀지나요?**
> A: 네. TIFF 사양에 맞는 8비트 인덱스 팔레트(ColorMap)가 파일 내부에 기록되어 있으므로, GIS 소프트웨어에서 별도의 스타일 파일(.qml, .lyr)을 로드하지 않아도 표준 토지피복 색상(산림=녹색, 수역=청색, 도시=적색 등)과 투명 Nodata가 즉시 적용됩니다.

**Q2: 9×9 전이 행렬 CSV에서 순변화(Net Change)의 합은 항상 0인가요?**
> A: 네, 정확합니다. 분석 대상 영역의 전체 면적은 고정되어 있으므로 어떤 클래스의 면적 증가는 반드시 다른 클래스의 면적 감소로부터 발생합니다. 따라서 모든 클래스의 순변화 합은 오차 없이 정확히 0으로 수렴하는 물리적 보존성을 가집니다.

**Q3: HTML 요약 보고서를 오프라인이나 인터넷이 연결되지 않은 환경에서도 볼 수 있나요?**
> A: 네, 100% 자립형(Self-contained)으로 설계되었습니다. 외부 웹 폰트나 외부 JavaScript 라이브러리를 일절 참조하지 않으며, 모든 시각화 막대 차트는 브라우저 표준 인라인 SVG로 내장되어 있습니다. 이메일 첨부나 파일 공유만으로 누구나 브라우저에서 바로 열람하고 인쇄할 수 있습니다.
