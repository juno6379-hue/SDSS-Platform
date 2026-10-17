# 카탈로그 활용 인사이트의 실제 데이터 계약

작성: 2026-10-17, data_pipeline. 읽기 독립 검토이며 backend/frontend/원본 자료를 수정하지 않았다. `UI/catalogu_insite`의 PNG 5개를 직접 열어 확인하고 현재 소스·SQLite 읽기 전용 연결·API8002의 Dataset 응답을 대조했다. UI 구현·실제 브라우저 검증은 web_ui/root 담당이다.

## 실제 카탈로그와 불변 버전 Registry

`GET /api/datasets`는 Store의 `datasets` namespace를 반환한다. 이번 조회에서 API6행과 `file:data/catalog.sqlite3?mode=ro`의 동일 순서6행이 완전히 같았다. 이6행은 불변 버전 Registry의6개 manifest가 아니다. DB에는 `dataset_versions` 행이 없었다. 따라서 기존6행을 고정 id/version/SHA 조합으로 자동 추정해 계보 검증에 등록하거나 연결하면 안 된다.

| 실제 Dataset ID | 기록 내용과 결측 |
|---|---|
| `first-group-training-smoke-source-v1` | source-crop-collection. 수집창/파일 수 등의 기록이며 표준 version/SHA·기간·품질·접근분류는 없음 |
| `first-group-recovery32-source-v1` | 위와 같은 수집 요약 종류. 이름의32를 현재 전체 재고나 준비율로 해석하지 않음 |
| `first-group-2021-source-v1` | 위와 같은 수집 요약 종류. ID의2021을 필터용 공식 기간으로 추정하지 않음 |
| `reference-pc-full-b04-20210921` | B04 단일 band 원본, SHA 있음/version 없음. EPSG:32748,10980×10980,10m 기록 |
| `baseline2021_cpu_v1_dataset` | prepared patch Dataset, version `717e5e1cce1a6d56` 있음/표준 artifact SHA 없음. 그룹·patch·정규화 등의 기록 |
| `validation-pc-b04-20230921` | B04 단일 band crop, SHA 있음/version 없음. EPSG:32748,64×64,10m 기록 |

6행 모두 `access_class`, `quality_status`, 정규 `provider`, 명시적 `time_range`/시작·종료 연도는 없다. B04 두 행의 source는 각각 URL 또는 설명 문자열이다. 이를 기관 객체와 동일하게 처리하거나 URI 호스트에서 공식 제공기관·재사용 권한을 추정하지 않는다. 파일의 CRS/해상도는 해당 파일 기록이며 모든 Dataset·전국·6개 주의 공통 속성이 아니다.

B04 두 행의 license는 `SEE_COLLECTION_TERMS`, `license_verified=false`, `training_ready=false`다. 이는 확정된 CC BY나 무승인 다운로드 허가를 의미하지 않는다. 나머지 행도 라이선스가 미상이다. source URI/로컬 path/원문 자격정보를 화면이나 CSV로 직접 노출하지 않는다. 생성/등록 시각을 데이터 관측기간·최신 업데이트 주기로 표시하지 않는다.

별도 `dataset_registry.py`는 id/version manifest snapshot과 실제 자산 SHA를 확인하는 불변 등록/해석 코어다. 읽기 전용 `POST /v1/datasets/lineage/verify`는 완전한 고정 root_ref가 있을 때 현재 전이계보를 검사한다. 기존 카탈로그의 허용 여부·기관 ACL·과학 승인·전체 AOI 적합성을 제공하는 API가 아니다. 현재6행에 결측 version/SHA를 생성하지 않는다.

추가 실제 읽기에서 `/api/tools`는 LCLUC1개 baseline-development와 나머지5개 interface-only를 반환했다. `/api/models`의 모델1개는 Draft, independent_evaluation=false였다. `/api/data/collection-status`는 최신 명시 준비도와 manifest/evidence 일치를 확인했으나 ready_for_training=false, train628/val233/test250, scene split 충돌·bare 부족의5개 blocker를 반환했다. 따라서 최신 재고와 입력 형식이 있어도 시안의 모델 준비완료/실행가능으로 승격할 수 없다.

## 5개 PNG의 표현별 구현 경계

| PNG | 가능한 읽기 기능 | 실측으로 복제하면 안 되는 시안 내용 |
|---|---|---|
| `10_56_25-1` 모델 입력자료 확인 | 실제6행의 선택·메타데이터 확인,6개 Agent 등록 목록, 준비도/차단 근거로 이동 | 총128/준비108/보완20,6모델별78–92%, BMKG/ERA5/Peatland 등 입력 체크를 실제 보유·적합 판정으로 표시 |
| `10_56_27-2` 다운로드 이용조건 | 실제 license/access 원문값 또는 미확인, 출처 표기·이용범위 검토 안내 | 시안의6개 대표자료·CC 라이선스·공개/승인불필요·재배포 권한을 실제6행에 대입 |
| `10_56_28-3` 메타데이터/품질 | 명시된 CRS·해상도 등 선택 Dataset 필드 표시, 결측 표시, 현재 계보 진단 별도 | Sentinel6-band/전국2017–2024/5일 주기/품질82점·완전성92%·국가평균 막대·공식검증통과·바로 활용 가능 |
| `10_56_32-4` Toolbox 전환 | 선택 ID 유지, 기존 Toolbox/Agent Center 이동, 요구입력·준비도 차단 표시 | 선택3개2.1GB/3주, 형식·공간·시간 적합 자동확정,6개 모델 준비완료/부분준비, 분석 실행 성공 |
| `10_56_33-5` WebGIS 연계 | 공개 참조6주 선택/강조, 실제 가용 layer·분석 화면 이동, 참조경계 출처 표시 | AOI99.2%·628,417/633,542km²·자동일치/연계성공·2024고정시각·모든 주를 덮는 실제 위성영상 |

표시할 메타데이터가 없으면 `미확인` 또는 `—`로 표시한다.0%·통과·공개로 치환하지 않는다. 필수 필터가 지정되면 해당 필드가 없는 행은 일치한다고 추정하지 않는다.6행을12개 입력유형·6개 모델별 보유율로 환산할 근거는 없다. UI의 메타데이터 존재율은 사용할 경우 분모와 명시 필드 기준을 설명하고 과학 품질점수와 구별한다.

## API가 실제로 제공하는 기능

- `GET /api/datasets`: 기존 메타데이터 읽기. 현재 목록 CSV는 프론트에서 표시 메타데이터를 내보내는 기능이며 원본 자산 다운로드가 아니다.
- `GET /api/tools`, `GET /v1/agents`:6개 영역 인터페이스. LCLUC는 baseline 구현 범위이고 다른5개는 인터페이스 영역이다.6개 승인 모델 완료가 아니다. 준비도는 별도 모델/학습 gate를 통과해야 한다.
- `GET /api/models`, `GET /api/models/{id}/readiness`: 모델 상태·checkpoint/evaluation 근거. Dataset 선택 수나 파일 형식만으로 준비완료를 만들지 않는다.
- `POST /v1/workflows/plan`, `POST /v1/workflows/lineage-validation`: 계획 및 현재 고정입력 계보 진단. PLAN_ONLY/BLOCKED, 실행 false가 유지된다. AOI/시간/product의 의미 적합성·모델 추천 또는 학습/실행 성공으로 해석하지 않는다.
- `GET /api/data/landcover-series` 및 대응 tile 경로: 실제 가용 연차 layer 목록/타일. 공개 참조라벨과 모델 예측을 구별하며 선택 Dataset 전체를 자동 렌더링하는 API는 아니다.
- `GET /api/analyses/{id}/map-data`, `/report`: 존재하는 분석 레코드의 지도/보고서 읽기. Dataset 선택만으로 새 분석 결과를 생성하지 않는다.
- `GET /v1/results/{id}/sdss`, `/assets/{index}`: Result·Trace·모델/입력 연결 및 자산 SHA gate 뒤 결과 자산을 제공하는 경로. 승인 Result가 없는데 시안의 다운로드/성공 결과를 만들지 않는다.

`/api/data/download`, `/api/data/register`, `/api/datasets/prepare`, `/api/training`, `/api/inference`, `/api/change`, `/api/timeseries` 등 쓰기/실행 경로가 소스에 존재한다는 사실은 이번 조회용 UI 연결의 실행 허가나 준비도 증거가 아니다. 이번 검토에서는 호출하지 않았다. PNG의 분석시작·원본다운로드·보고서생성 버튼은 기존 명시 gate를 보존하거나 조회 화면 이동/미구현 사유를 표시해야 한다.

CSV는 현재 선택/필터된 표시 행만, 결측은 미확인, 쉼표·따옴표·개행 quoting 및 `= + - @`/탭 등 수식 prefix 처리를 유지한다. 실제 raster/GeoTIFF·보고서·지도 이미지 다운로드와 동일한 버튼명으로 표시하지 않는다. 제공기관 막대는 실제 명시 provider 집계만 사용하며 고정기관 순위·가짜 수치를 만들지 않는다.

## 공간 선택과 라이선스

`frontend/public/first-group-provinces.source.json`은 geoBoundaries gbOpen의 공개 참조 ADM1 경계6개를 기록한다. 대표연도2017, 원출처 OpenStreetMap/Wambacher, ODbL1.0, attribution URL과 선택 GeoJSON SHA가 있으며 `legal_boundary_certification=false`다. Banten/West Java/East Java/South Sulawesi/Southeast Sulawesi/Gorontalo를 선택·강조할 수 있으나 공식 사업 승인 AOI나 Dataset footprint로 보지 않는다.

참조경계와 registry Dataset의 면적/포함관계가 확인되지 않았으므로 AOI 일치율·자료 coverage 면적·전국 보유를 계산한 것처럼 표시하지 않는다. 지도 레이어 on/off와 투명도 조작은 화면 상태이며 새 분석·공식 공간검증 완료가 아니다. 원문 기관자료 또는 사업확정 AOI 연결은 후속이다.

## 인계·검증 상태

web_ui에 API6행=DB6행, 불변 Registry0행, 고정 ref 결측, quality/access/license 미상,5PNG의 가짜 준비율·품질·AOI·모델완료 금지를 전달했다. **VERIFIED_REAL**은 이번 읽기 조회의 행/메타데이터 대조에 한정한다. **TESTED_SYNTHETIC**인 계보·Job/Workflow 기능의 시험 결과를 실제 승인자료/실행 검증으로 바꾸지 않는다. 새 UI의 실제 화면 반영·브라우저 동작·보호파일 SHA 전후 근거는 root/web_ui의 별도 문서를 따른다.

이 문서는 읽기 검토 결과이며 새 API·자료 등록·모델 학습·수집·Job/Trace 생성은 구현하거나 실행하지 않았다. 기관 라이선스/권한 확정, 모델별 요구입력 매핑·AOI/기간 적합성 검사·공간 내보내기 계약은 후속 범위다.
