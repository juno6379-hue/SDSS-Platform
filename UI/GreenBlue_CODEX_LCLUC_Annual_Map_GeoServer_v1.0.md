# Codex 개발 명령서: LCLUC 연차별 실자료 지도 서비스 및 Swipe·Animate 구현

- 문서 버전: 1.0 / 작성일: 2026-10-19
- 상태: 그린블루 내부 개발 지시안. 컨소시엄·BIG의 승인된 계약 규격을 대체하지 않는다.
- 적용 대상: 기존 SDSS-Platform의 LCLUC Workspace, Data/Result Catalog, GIS 서비스, 통계 API
- 직접 개발 범위: LCLUC 지도 서비스. 외부 5개 과학모델의 알고리즘 개발을 추가하지 않는다.
- 목적: 큰 관리용 격자를 색칠한 화면을 실제 연차별 토지피복 래스터와 필요한 벡터 레이어를 서비스하는 화면으로 변경한다.

## 0. 가장 중요한 명령

기존 화면의 스와이프 손잡이와 그래프만 개선하지 말고, 다음 데이터-서비스-화면 연결을 실제 구현하라.

연차별 토지피복 원본/모델 분류 결과
→ 정수 클래스 래스터·품질 마스크·출처 검증
→ 버전이 고정된 Result/Dataset Registry
→ GeoServer GeoTIFF 또는 ImageMosaic 게시
→ WMS 지도 제공, 필요 시 GeoWebCache/WMTS 캐시
→ LCLUC Workspace의 T1/T2 지도·Swipe·Animate
→ 동일한 원본과 유효영역을 사용하는 연차별 통계·변화행렬·픽셀 조회
→ 검토된 변화영역 벡터 및 WebGIS·보고서 연계

GeoServer는 분류 모델을 대신하지 않는다. 실제 분류 결과가 없는 연도·지역을 지도 서버나 프런트엔드에서 만들어내지 마라.
기존 UI 인포그래픽은 화면 배치 참고자료일 뿐 지리참조 데이터나 검증된 통계가 아니다. 시안 이미지와 시안의 면적·정확도·준비율 수치를 실제 레이어로 사용하지 마라.

## 1. 먼저 저장소와 현재 실자료를 조사하라

1. 현재 브랜치·commit SHA·실행환경·지도 라이브러리·백엔드·저장소·GeoServer 유무를 조사한다.
2. 현재 Swipe가 실제 분류 타일, 픽셀 기반 결과, 임의 격자, 캔버스 목업 중 무엇을 표시하는지 코드와 네트워크 요청으로 확인한다.
3. 연도별 GeoTIFF/COG, 모델 checkpoint, 클래스 정의, 품질 마스크, 기존 API 및 테스트를 확인한다.
4. 사용자가 제공한 2026-10-16 기록은 과거 기준이다. 최신 파일과 대조하지 않은 채 현재 실적으로 복사하지 않는다.
5. 기존 학습 차단·원본 해시·다운로드 원장·모델 승인 규칙과 정상 동작하는 API를 보존한다.
6. 보고서에는 '확인된 코드/파일', '기존 보고만 존재', '자료 없음', '실행 미검증'을 구분한다.

필수 산출물:
- `docs/lcluc-map/current-state-audit.md`
- `docs/lcluc-map/annual-data-inventory.json`
- `docs/lcluc-map/implementation-plan.md`

## 2. 지역·연도·사용 목적을 분리한다

초기 화면과 소규모 실증 범위는 기존 프로젝트에서 정한 First Group 6개 주를 따른다.
South Sulawesi, Gorontalo, Southeast Sulawesi, Banten, West Java, East Java.

- 공식/승인 경계가 있으면 해당 경계 ID·버전·출처를 사용한다. 없으면 사각 AOI를 주 전체 경계로 표시하지 않는다.
- 주의 위치, 촬영 장면 범위, 실제 분석 유효범위, 패치 범위를 별개로 표시한다.
- 작은 256×256 창을 주 전체 분류 결과로 확대하거나 반복 배치하지 않는다.
- 한국 지도·한국 지명·무관한 인도네시아 지역을 분석 예시로 대체하지 않는다.
- 연도 목록은 서버에 실제 등록된 자료에서 가져온다. 2020~2025는 목표 기간일 수 있으나 모든 연도가 확보되었다는 뜻은 아니다.
- 선택한 연도에 자료가 없으면 '자료 없음'을 표시한다. 다른 연도 레이어로 자동 대체하거나 중간 연도를 합성하지 않는다.
- 연차 대표 영상/합성영상이면 대표 연도와 실제 관측 시작·종료일, 합성방법, 유효관측 수를 구분한다.

다음 권한·준비도를 독립적으로 판정한다.
- 참조 토지피복도 열람
- 권한이 있는 Draft 예측의 개발 미리보기
- 신규 모델 학습
- 모델 추론 실행
- 두 연도 변화량 계산
- 운영/정책용 결과 승인 및 게시

`ready_for_training=false`가 기존의 합법적인 참조지도 열람까지 막는 이유가 되어서는 안 된다.
반대로 참조지도 표시 성공을 당사 AI 학습·성능검증 완료로 바꾸어 보고하지 않는다.

## 3. 자료 유형과 클래스 체계

### 3.1 자료 유형

모든 프레임에 `source_kind`를 기록한다.
- `reference_landcover`: 외부기관이 제작한 실제 토지피복 자료
- `model_prediction`: 당사/인수 모델의 실제 추론 결과
- `synthetic_fixture`: 기능·계약시험용 합성자료

한 화면에서 이 유형을 숨기지 않는다. 합성자료에는 전체 화면과 내보내기에 지속적으로 시험자료 표시를 한다.
외부 분류지도의 연도별 알고리즘·자료 버전이 다르면 비교 제약을 기록한다.

### 3.2 9개 클래스 검증

UI의 '9-Class'는 모델/원본 클래스 정의와 일치해야 한다.
`class_id`, 국문·영문명, 정의, 원천코드, 목표코드, 색상, NoData 코드를 가진 클래스 파일을 단일 관리한다.

- 실제 9개 클래스가 확인되면 그 순서·코드·색상을 양쪽 지도·범례·그래프·행렬·내보내기에 동일 적용한다.
- 11개 등 다른 원천 분류를 9개로 통합할 경우 승인된 매핑표와 버전을 기록한다.
- '습지/맹그로브' 등의 병합을 그림의 범례만 보고 확정하지 않는다.
- 원본에서 식별하지 못하는 클래스는 임의로 생성하지 않는다.
- NoData는 유효한 토지피복 클래스와 별도다. 0을 자동 NoData로 가정하지 않는다.
- 나무피복 분류를 법적 산림구역·자연림 판정과 자동 동일시하지 않는다.

## 4. 래스터를 기본 데이터로 구현한다

연차별 원본 분류 결과는 지리참조가 있는 단일밴드 정수 GeoTIFF/COG로 보존한다.
색상 이미지(PNG/JPEG)는 표시용 파생물이며 분석의 원본이 아니다.

필수 검사:
- 정수형 클래스 값 및 허용 코드
- CRS, affine transform, 너비·높이, 픽셀 중심/경계, NoData
- 실제 footprint, 유효 마스크, 시기, 클래스체계 버전
- 모델 ID/버전(해당 시), 입력 데이터 버전, 처리 설정, checksum
- T1/T2 분석을 위한 공통 격자 정합

래스터 전처리·재투영·확대 표시에는 범주형 값을 보존하는 방식을 사용한다.
기본 nearest neighbor, 저해상도 개요영상(overviews)은 nearest 또는 검토된 mode 정책을 사용하고 기록한다.
연속값용 bilinear/average를 정수 클래스 ID에 적용하지 않는다.
저해상도 개요영상은 표시 성능을 위한 것이며 원해상도 통계의 대체 자료가 아니다.

분석용 CRS는 AOI에 맞춰 정하고 표시용 Web Mercator와 구분한다.
First Group 전체에 하나의 UTM zone을 무조건 강제하지 않는다.

## 5. GeoServer 게시 구조

### 5.1 초기 수직 통합: 연도별 독립 레이어

처음에는 같은 AOI의 실제 두 시점 자료를 개별 GeoTIFF Store/Layer로 게시하여 연결을 검증한다.
Layer Registry가 연도와 실제 레이어명을 연결한다. 파일명에서 연도를 추측하지 않는다.
모든 예시 이름은 설계용이며 해당 파일이 존재한다는 뜻이 아니다.

예시 구조:
`lcluc/<aoi_id>/<series_version>/<year>/<artifact_version>/landcover.tif`
`lcluc/<aoi_id>/<series_version>/<year>/<artifact_version>/valid_mask.tif`
`lcluc/<aoi_id>/<series_version>/<year>/<artifact_version>/manifest.json`

### 5.2 확장: ImageMosaic + TIME

두 시점 게시 검증 후 지역·연도·타일이 늘어나면 ImageMosaic 인덱스로 전환 또는 확장한다.
- granule별 시간, footprint, 파일 참조를 관리한다.
- TIME dimension을 구성하여 특정 시점의 프레임만 요청한다.
- 동일 시간에 서로 다른 모델/자료 버전을 우연히 합성하지 않도록 series/version 별 레이어 또는 명시적인 인덱스 필터를 둔다.
- 연차 대표 timestamp의 의미와 실제 관측 기간을 manifest에 명시한다.
- TIME 미지정 시 기본 최신연도로 조용히 대체되지 않도록 애플리케이션에서 명시적으로 요청한다.
- '가장 가까운 시간 자동 선택'은 기본 비활성화하고 미존재 연도를 검출한다.

초기에는 로컬/승인된 공유볼륨의 GeoTIFF를 사용해 게시를 검증한다.
원격 COG/Object Storage를 GeoServer에서 직접 읽는 구성은 배포 버전의 COG 모듈·Range Reader·인증 호환성을 별도 확인한다. URL만 등록하면 항상 읽힌다고 가정하지 않는다.

### 5.3 렌더링 및 캐시

- SLD RasterSymbolizer의 `ColorMap type="values"`로 정수 클래스별 이산 색상을 지정한다.
- NoData/제외영역은 투명 처리하고 필요 시 품질 마스크를 별도 레이어로 표시한다.
- 서버의 범주형 WMS 보간은 nearest neighbor로 설정한다.
- WMTS/GeoWebCache는 WMS 정상 동작 이후 도입한다.
- TIME/STYLES 등의 파라미터 필터와 캐시 키를 설정한다. 연도·레이어버전·스타일버전·권한에 따른 캐시 혼선을 방지한다.
- 클래스 필터는 명세화된 스타일/렌더링 정책으로 구현한다. RGB 이미지 위 CSS 색상조작으로 클래스 선택을 흉내 내지 않는다.
- 클래스 조합별 타일 캐시의 폭증을 고려해 캐시 가능한 프리셋과 동적 요청을 분리한다.
- 제한자료의 타일은 공개 캐시에 노출하지 않는다.

## 6. 벡터는 목적별 보조 결과로 생성한다

전체 10m 분류지도를 무조건 거대한 GeoJSON으로 브라우저에 전달하지 않는다.
기본 지도는 래스터, 선택한 변화영역·행정구역 통계·검색 대상은 벡터로 관리한다.

변화 폴리곤에 저장할 필드:
`feature_id`, `comparison_id`, `from_class`, `to_class`, `area_ha`,
`aoi_id`, `t1_result_id`, `t2_result_id`, `geometry_version`, `quality_status`.

- 벡터화 연결규칙(4/8 connectivity), 최소면적, dissolve, 단순화 허용오차와 버전을 명시한다.
- 지도 표시용 단순화 geometry와 분석·면적계산 geometry를 분리한다.
- 면적·전이통계의 기준 원본은 래스터 또는 검증된 분석 geometry임을 고정한다.
- PostGIS에 보관하고 소량은 GeoJSON/WFS, 대규모 표시는 검증된 벡터 타일 경로를 사용한다.
- GeoServer Vector Tiles extension은 실제 설치 버전과 호환성을 확인한다.
- 공식 원본이 벡터인 토지피복 자료는 그 provenance를 유지하여 직접 서비스할 수 있다.

## 7. 프런트엔드: 진짜 T1/T2 비교

기존 MapLibre/OpenLayers/Leaflet 등 지도 엔진을 먼저 확인하고 재사용한다.
MapLibre는 WMS 타일 소스를 연결할 수 있다. 설치 버전에 맞는 API를 사용한다.

### 7.1 Swipe

1. 두 지도는 동일한 중심·zoom·bearing·pitch·viewport 크기를 유지한다.
2. 양쪽에 동일 지리범위의 완전한 T1/T2 레이어를 각각 준비하고 화면 경계만 clip한다.
3. 한 이미지의 왼쪽 절반과 다른 공간의 오른쪽 절반을 붙이거나 래스터를 늘려 맞추지 않는다.
4. 이동·확대·화면 크기 변경 후에도 경계가 일치해야 한다.
5. 기본 비교는 토지피복 T1 ↔ 토지피복 T2다.
6. 위성영상 ↔ 분류도는 별도의 보기 모드로 제공하고 각 측의 실제 날짜와 자료 종류를 표시한다.
7. 확대 시 범주형 래스터 경계의 불필요한 색상 혼합을 방지한다. MapLibre의 설치 버전에 맞는 nearest 렌더링 옵션을 사용한다.
8. 사용자가 빠르게 연도를 변경하면 이전 요청을 취소/무효화하여 이전 응답이 새 연도에 덮이지 않게 한다.
9. 타일·제목·범례·통계가 같은 프레임을 가리킬 때 화면 상태를 확정한다.

### 7.2 Animate

- Registry가 반환한 실제 가용연도만 순차 재생한다.
- 재생·정지·속도·루프·앞뒤 프레임·현재연도 표시를 구현한다.
- 필요한 화면 범위만 제한적으로 prefetch한다.
- 새로운 프레임의 화면 범위 타일이 준비되지 않으면 로딩 상태를 표시한다. 이전 지도에 새 연도 라벨을 붙이지 않는다.
- 없는 연도를 건너뛸 경우 '2022 자료 없음' 등 누락 표시를 유지한다.
- 교차 페이드/보간은 실제 중간연도 결과가 아니다. 기본은 프레임 전환으로 한다.
- Animate는 지도 표시 기능으로서 매 프레임마다 모델 재학습·추론을 호출하지 않는다.

### 7.3 기본 UI 구성

기존 7개 전체 메뉴와 `GeoAI Toolbox → LCLUC Workspace` 진입 구조를 유지한다.
상단: AOI, T1, T2, source/model/version, Land Cover/Imagery/Change, Swipe/Animate, 실제 유효면적.
중앙: 지도, 클래스 범례, 투명도, 픽셀 조회, 품질 마스크, 디버그 격자 토글.
하단/측면: 연차별 클래스 면적, 전이행렬, 총증가·총감소·순변화, 변화 핫스팟, 출처/검증.
큰 작업용 격자는 기본 숨김이며 '개발자: 패치/타일 경계'에서만 표시한다.

## 8. 통계·변화행렬·픽셀 조회

Swipe 위치/화면 크기/zoom 변경은 분석 통계값을 바꾸지 않아야 한다.
지도 PNG의 색상이나 브라우저 화면 픽셀 수로 면적을 계산하지 마라.

- 연차별 통계: AOI와 해당 연도의 실제 유효영역을 기록하여 클래스별 면적·비율을 계산한다.
- 변화통계: T1·T2의 공통 유효영역에서 정합된 클래스 ID를 비교한다.
- 연차별 추세 비교는 연도마다 다른 유효면적의 영향을 드러낸다. 공통 유효영역 기준과 연도별 유효영역 기준을 구분한다.
- 면적은 적절한 면적 계산 방법(검증된 투영/등적/측지적 방법)을 사용하며 EPSG:3857 면적을 그대로 정책 통계로 쓰지 않는다.
- 변화행렬: 행=T1, 열=T2, 대각선=같은 클래스, 비대각선=전이. 전체합은 공통 유효영역 면적과 일치한다.
- 특정 클래스 감소/증가/순변화를 구분하고 비교 기준 면적을 표시한다.
- 경계 픽셀 포함 정책(all_touched 등), 면적 허용오차, NoData 제외 수를 기록한다.
- 픽셀 클릭은 동일 좌표의 원본 클래스와 T1/T2 상태·NoData·출처를 반환한다. 화면 RGB에서 클래스를 역추정하지 않는다.
- 픽셀 팝업에 주 전체 면적을 해당 픽셀 면적으로 표시하지 않는다.
- 독립 검증자료가 없으면 변화지도에 정책적 확정 사실이나 인과관계를 부여하지 않는다.

## 9. 최소 데이터·API 계약

기존 GMAIS 및 프로젝트 API 경로와 충돌하면 기존 계약을 우선 확인하고 확장안을 승인받는다.
아래는 신규 설계안이며 현재 구현된 API라는 뜻이 아니다.

| 기능 | 예시 API | 핵심 동작 |
|---|---|---|
| 실제 자료 목록 | `GET /api/v1/lcluc/series` | AOI/자료종류/버전별 가용연도·상태 조회 |
| 지도 프레임 | `GET /api/v1/lcluc/series/{series_id}/frames` | 프레임별 layer_id, TIME, footprint, 출처 |
| 범례 | `GET /api/v1/layers/{layer_id}/legend` | 코드·명칭·색상·클래스체계 버전 |
| 비교 전 검사 | `POST /api/v1/lcluc/comparisons/preflight` | 격자·시기·분류체계·권한·유효영역 검사 |
| 변경분석 실행 | 기존 Agent/Job 생성 API 재사용 | 승인된 작업만 비동기 실행 |
| 분석통계 | `GET /api/v1/lcluc/comparisons/{comparison_id}/statistics` | 고정된 입력 참조 기반 전이행렬·면적 |
| 픽셀 조회 | `GET /api/v1/lcluc/comparisons/{comparison_id}/pixel` | 동일 지점 T1/T2 클래스 및 품질 |

Frame Manifest 필수 필드:
`series_id`, `frame_id`, `result_id/dataset_id`, `version`, `year`,
`time_parameter`, `observation_start`, `observation_end`, `composite_method`,
`source_kind`, `source_refs`, `model_id/model_version`(해당 시),
`class_schema_id/version`, `quality_mask_ref`, `analysis_grid_ref`,
`footprint`, `bbox_crs84`, `native_crs`, `resolution`, `nodata`,
`storage_ref`, `checksum`, `geoserver_layer`, `style_version`,
`publication_state`, `scientific_validation_state`, `approval_state`.

- API 경위도는 경도·위도 순서를 명시한다. 투영좌표와 혼용하지 않는다.
- WMS 1.3.0의 CRS 축순서는 별도 테스트한다. EPSG:3857 타일 bbox와 경위도 bbox를 혼동하지 않는다.
- 화면에 장기 유효한 관리자 자격증명이나 원격 SAS query를 노출하지 않는다.
- 사용자 입력 URL을 서버가 임의 fetch하지 않게 Registry의 승인된 asset만 해석한다.
- 캐시 키/비교 식별자는 입력 버전, AOI, 클래스체계, 마스크, 시간과 정책을 포함한다.

## 10. 운영·게시의 완료 상태

`registered → validated_for_rendering → published_to_staging → tile_verified`와
과학적 `Draft/Validated/Approved` 및 운영 게시 승인은 별도 상태로 관리한다.

GeoServer REST 등록 응답 성공만으로 게시 완료라 하지 않는다.
GetCapabilities, GetMap, 실제 타일 내용/범위, 범례, 픽셀 조회 및 프런트 표시까지 확인한다.
등록 작업은 재실행 안전하게 만들고 실패 시 반쯤 게시된 자료가 운영 목록에 노출되지 않게 한다.
처음은 Docker Compose/로컬 Staging으로 검증하고 Kubernetes 매니페스트는 기존 운영 규격에 통합한다.
실행 버전·확장모듈·이미지 digest·스토리지 마운트·백업·복구·권한을 기록한다.
지도 관리 REST와 공개 지도/타일 서비스의 권한을 분리한다.

## 11. 역할 분담

| 개발 파트 | 변경 업무 | 완료 증거 |
|---|---|---|
| Data Pipeline | 연차별 실제 자료 inventory, AOI/격자/클래스/품질/출처 | 파일·해시·검사보고서 |
| ML Pipeline | 실제 모델이 있을 때 연차별 추론·모자이크 및 manifest | 실제 inference run과 산출물 |
| GIS Service | GeoTIFF/ImageMosaic·SLD·TIME·GWC·필요 벡터 게시 | 서비스 응답·지도 타일 검사 |
| Backend/Orchestrator | 자료 준비성·비교 Job·원본 통계·픽셀 API | API/계약/통계 시험 |
| Frontend | 실제 레이어 연결, Swipe/Animate, 범례·차트 동기화 | 브라우저 E2E·네트워크 trace |
| QA | 출처·위치·연도·색상·통계·오류/권한 검사 | fixture 및 실제 자료 시험 구분 |
| Understanding Agent | 무엇을 왜 바꿨는지·실자료와 시안 차이 해설 | 코드 연결 설명·발표문 |

## 12. 실행 순서

### Gate 0 — 현황 확인
원래 코드를 진단하고 자료 inventory 및 개선계획을 작성한다.

### Gate 1 — 한 AOI·한 시점의 실제 지도 게시
실제 분류 래스터 한 개를 게시하고, 원본 픽셀값·색상·범례·위치·NoData가 맞는지 검증한다.
당사 모델 결과가 없으면 이용권한이 확인된 참조자료로 지도 경로를 검증하되 참조자료라고 표시한다.
자료가 아예 없으면 합성 fixture로 코드만 검증하고 실자료 Gate를 완료 처리하지 않는다.

### Gate 2 — 동일 AOI의 두 시점 비교
두 실제 프레임을 등록하고 카메라 동기화 Swipe 및 정확한 연도 전환을 검증한다.
한 시점만 있거나 두 패치의 위치가 다르면 연차 변화 실증 완료로 표시하지 않는다.

### Gate 3 — 원본 기반 통계 연결
공통 유효영역, 클래스별 증가·감소, 전이행렬, 픽셀 팝업을 연결한다.

### Gate 4 — 연차 Animate·캐시
실제 가용연도 기반 재생, 없는 연도 처리, TIME/STYLES 캐시, stale response 방지를 시험한다.

### Gate 5 — 변화 벡터·WebGIS·보고서
필요한 변화 패치만 벡터화하고 같은 comparison_id로 지도·통계·보고서를 연결한다.

### Gate 6 — 운영 준비
권한·캐시·장애·버전교체·게시취소·성능을 검증하고 운영 승인을 별도로 요청한다.

## 13. 필수 수용시험

1. GeoServer 요청을 끊으면 지도는 연결 실패/자료 없음이 되며 임의 격자로 대체되지 않는다.
2. 한 자료의 클래스 ID별 테스트 픽셀이 범례 색상과 일치한다. 시험조건에서 불필요한 색상 보간이 없다.
3. 같은 좌표의 T1/T2 원본 픽셀 조회 결과와 화면 선택 결과가 일치한다.
4. 모의 4×4 자료에서 1→2 두 픽셀, 2→1 한 픽셀만 변경하고 나머지는 유지했을 때 전이행렬·총변화 픽셀 수가 기대값과 일치한다. 이 시험은 과학 정확도 검증이 아니다.
5. T1 또는 T2 NoData인 픽셀은 변화통계에서 제외된다.
6. zoom·Swipe 위치만 바꿔도 같은 AOI 비교 통계는 바뀌지 않는다.
7. 고의 반픽셀 격자 오프셋, 잘못된 CRS·분류체계·불일치 버전은 비교 전 검사에서 검출된다.
8. 자료 없는 연도를 요청하면 최신연도로 자동 대체하지 않는다.
9. 빠른 연도 전환·네트워크 지연 시 레이어 연도와 KPI 연도가 엇갈리지 않는다.
10. TIME별 캐시 분리와 스타일 변경 후 캐시 갱신이 검증된다.
11. 제한자료 타일·통계·원본 다운로드에 동일 접근정책이 적용된다.
12. 원본 없는 승인·정확도·면적 수치를 화면에 넣지 않는다.
13. 반텐/서자바의 작은 자료가 First Group 6개 주 전체 결과로 표시되지 않는다.
14. 실제 입력·출력·코드버전·테스트 명령·실행 환경·미완료 조건이 보고된다.

## 14. 최종 산출물 및 보고

- 기존 코드 변경 및 회귀시험
- GeoServer 게시 스크립트와 설정/복구 지침
- 클래스 파일·SLD·Layer Manifest Schema
- 실제 가용연도·타일·통계·픽셀 API 및 UI 연결
- Swipe/Animate E2E 시험
- 필요한 변화 벡터 처리·연계
- 실제 데이터 검증과 합성시험을 구분한 완료표
- 1분/5분 발표 해설: 데이터 생성, 게시, 표시, 비교, 과학적 검증의 차이

보고 시 '개발 완료', '실자료 지도 표시', '실자료 두 시점 비교', '과학적 정확도 검증', '운영 승인'을 각각 판정한다.
지금 Gate 0부터 시작하고, 가능한 최소 실제 자료 경로를 먼저 완성하라.

## 15. 공식 기술 참고자료

아래 문서는 기능 확인용이다. 실제 배포 버전과 확장모듈 호환성을 확인하여 적용한다. 문서의 예시 버전을 그대로 운영버전으로 확정하지 않는다.

```text
GeoServer GeoTIFF
https://docs.geoserver.org/main/en/user/data/raster/geotiff/
GeoServer ImageMosaic time-series
https://docs.geoserver.org/stable/en/user/tutorials/imagemosaic_timeseries/imagemosaic_timeseries.html
GeoServer WMS TIME
https://docs.geoserver.org/stable/en/user/services/wms/time/
GeoServer RasterSymbolizer / discrete ColorMap
https://docs.geoserver.org/stable/en/user/styling/sld/reference/rastersymbolizer.html
GeoServer categorical raster interpolation
https://docs.geoserver.org/main/en/user/services/wms/webadmin/
GeoWebCache parameter handling
https://docs.geoserver.org/stable/en/user/geowebcache/using/
GeoServer vector tile extension
https://docs.geoserver.org/stable/en/user/extensions/vectortiles/
GeoServer COG support and range readers
https://docs.geoserver.org/main/en/user/community/cog/cog/
MapLibre WMS source
https://maplibre.org/maplibre-gl-js/docs/examples/add-a-wms-source/
MapLibre raster rendering style
https://maplibre.org/maplibre-style-spec/layers/
```
