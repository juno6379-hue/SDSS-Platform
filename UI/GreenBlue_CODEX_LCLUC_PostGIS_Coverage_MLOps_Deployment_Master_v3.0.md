# GreenBlue / BIG Climate Action — Codex 통합 개발·이관·검증 프롬프트 v3.0
## SQLite → PostgreSQL/PostGIS · 과거 대비 영상수집·구름결측 개선 검증 · Esri/WorldCover 참조라벨 · MLOps 모델 성능 비교 · GeoServer 1·2차 연계 · 운영 배포

> **적용 프로젝트**: 기존 `SDSS-Platform` / `GeoAI Toolbox → LCLUC Workspace`  
> **범위**: 인도네시아 First Group 정확히 6개 주(South Sulawesi, Gorontalo, Southeast Sulawesi, Banten, West Java, East Java), 2020~2025년  
> **문서 분류**: Codex용 실제 코드/DB/파이프라인 수정·데이터 이관·실증/배포 지시서. 별도의 목업 앱 제작이나 가상의 수치 생성 요청 아님.  
> **계승할 요구**: 기존 v2.0의 다중시점 수집·SCL 구름 최소화·Esri/WorldCover 통합·MLOps·GeoServer/Swipe, v1.1의 GeoServer 1차 → 학습·검증 → 추론 → GeoServer 2차 → 변화탐지. **이 문서는 단독으로 사용 가능**하게 작성했다.  
> **핵심 원칙**: 과거 대비 재현 가능한 수치가 없는 개선 주장 금지; 저장소의 실제 구현을 먼저 조사; 승인된 환경/데이터/비용 한도 준수; 미측정값은 `null`/`NOT_MEASURED`; 과학적 정확도와 소프트웨어 시험 통과를 혼동하지 말 것.

---

# 0. 최우선 실행 명령 / 절대 변경하지 말아야 할 사실

당신은 해당 저장소의 기존 코드/DB/GeoServer/모델을 대상으로 **AS-IS 감사를 먼저 수행하고, 안전한 데이터 이관 → 실데이터 기반 수집·품질 개선 → MLOps 성능 검증 → GIS·SDSS 통합 → 배포 검증**을 진행하는 수석 GeoAI·Spatial Database·MLOps·DevOps 엔지니어다.

**첫 응답부터 완료를 선언하지 말라.** 구현한 것, 실제 파일을 확보한 것, 과학적으로 검증한 것, 운영에 배포한 것을 별도의 Gate와 증거로 보고한다.

## 0.1 이전 프로젝트의 '이력으로 알려진' 기록 — 최신 상태라고 단정 금지

2026-10-16 제공 보고서 기준:

- First Group 6개 주에서 2021년 작은 **RGB/WorldCover 256×256 창 6개** 수집, 이 중 품질 적격 창 3개로 보고됨. **주 전체 영상 6개가 아님**.
- 후속으로 **Banten·West Java 각각 2021년 256×256, Sentinel-2 6밴드+WorldCover/SCL 2개 창** 확보·정합 검사. 혼합 재고 8창 중 품질 적격 5패치, **6밴드 입력계약 적격 2패치**.
- 6밴드 학습 분할 **Train 0 / Validation 1 / Test 1**, `ready_for_training=false`, 정식 재학습 0회. 36개 주×연도 목표 중 초기 6밴드 신규 완성은 2개 주·연도 소규모 창이라는 기록이며 주 전체 확보를 의미하지 않음.
- 초기 임시모델: 3패치×3epoch, 예측이 grass 100%로 편향, **WorldCover 대비** OA 1.35%, mIoU 0.27%. 독립 테스트 기반 운영 정확도나 재학습 향상률의 분모로 자동 사용 불가.
- 과거 수집 실패 원장: HTTP 429, 다운로드 예산, 조건 불일치; 과거 일부 원본 재투영 crop 보존 부족. 수집 검색 성공 ≠ 다운로드 완료 ≠ 전체 AOI 유효 커버리지.
- 기 확보한 GeoServer/MapLibre·변화탐지 UI는 존재한다고 보고됐으나, 실제 원본 픽셀과 지도·팝업·통계의 연결은 최신 코드 및 HTTP 증거로 **재감사**해야 함.

이 목록을 `legacy_reported_baseline`으로 저장하고 **실제 SQLite 원장 및 디스크·객체자산을 검증한 `verified_as_is_baseline`과 혼합하지 말라**. 기존 기록이 남지 않아 현재 관측 수치가 복원 불가능하면 `UNKNOWN_LEGACY_BASELINE`을 보고할 것.

## 0.2 강제 준수 제약

1. 기존 저장소의 구조, 프레임워크, API/Schema, GMAIS v0.2 내부 제안규격, 인증·RBAC·승인 게이트를 우선 재사용. 표준/계약 승인 범위를 임의 확대하지 말 것.
2. SQLite 데이터를 별도 백업하고 **읽기 전용 스냅샷에서 이관**. 검증 전 원본 DB/데이터/GeoServer Data Directory 삭제·덮어쓰기 금지.
3. `SQLite → PostgreSQL/PostGIS`가 목표이지만, 코드에 SQLite DB가 여러 개면 DB별 소유자·역할·이관/잔존 범위를 조사한 후 계획서에 승인 받을 것.
4. 행정경계·관측일·원본 출처·클래스 체계·NoData·마스크 버전이 없는 숫자는 공식 통계가 아니다.
5. Sentinel-2의 구름 아래를 MLOps 재학습 또는 Esri 라벨로 '실관측 복원'했다고 주장하지 말 것. 누락과 추정은 명확히 분리.
6. Esri 연차별 LULC 9개 원래 클래스 중 `10=Clouds`, `0=NoData`는 유효 지표피복 클래스가 아님. UI 임의 '9개 지표피복' 체계로 1:1 간주 금지; Esri Rangeland를 근거 없이 Grassland/Shrubland로 쪼개지 말 것.
7. WorldCover는 실제 공개 연도·버전만 취급: 2020 v100, 2021 v200. 2021 라벨을 2025 정답으로 복제 금지.
8. 라이선스·데이터소스 권한·전송량/스토리지/GPU 예산을 확인하고 수집 계획 → 승인 → 실행. HTTP 429는 `Retry-After`에 따르고 우회 금지.
9. 등록된 실제 면적·분류 지도 없이 주 전체를 100% 커버한 것처럼 시연 금지. `TEST DATA`/`EXTERNAL_REFERENCE`/`MODEL_DRAFT`/`MODEL_APPROVED`를 엄격히 구분.
10. 기존 프로젝트/레거시 파일의 코드·유닛테스트·참조문서 변경이 필요하면 근거·영향·이전 호환성을 남긴 뒤 최소 변경.

---

# 1. 목표 시스템과 실행 순서

```text
                   ┌────────────────────────────────────────────┐
                   │ PostgreSQL + PostGIS (정본 메타데이터/이력) │
                   │ AOI·Scene·Asset·QC·Coverage·Model·Results │
                   │ GeoServer Layer Registry·Audit·Approvals  │
                   └────────────────────────────────────────────┘
                              ↑ 모든 단계의 증거·버전 기록
G0. 현재 SQLite/파일/코드/GeoServer/수집·학습 원장 감사 + 과거 Baseline 동결
  ↓
G1. PostgreSQL/PostGIS 스키마·백업·이관·무결성·API 호환성 검증
  ↓
G2. 6개 주×6년×12개월(432개 주·월) 가용성 조사 + 기존 수집재고/공백 감사
  ↓
G3. 증분 Sentinel-2 실제 수집 + Esri 연차 제품/WorldCover 소스 확인
  ↓
G4. 원본 품질·반사도·SCL 구름/그림자·좌표/픽셀 정합·다중시점/연간 합성
  ↓
G5. 기존 vs 신규 관측 유효영역/Cloud/NoData/새로 확보한 면적 실측 비교
  ↓
G6. GeoServer **1차 연계**: 원본·합성영상·참조라벨·품질마스크·Gap 지도
  ↓
G7. AI-Ready 데이터셋·참조 라벨 QA·독립 홀드아웃 구성·학습준비성 Gate
  ↓
G8. Baseline 모델 재평가 → Challenger(U-Net/U-Net++ 등) 학습 → 동일 시험셋 평가
  ↓
G9. MLOps: Experiment/Model/Dataset Registry, 승인 재학습, 성능·드리프트, 배포·롤백
  ↓
G10. 실제 연도별 추론(승인/스테이징 정책 준수) → COG/Mask/Confidence
  ↓
G11. GeoServer **2차 연계**: 원본 예측 클래스 래스터·실제 시점별 레이어 게시
  ↓
G12. T1/T2 공통 유효영역 변화탐지·면적·전이행렬·불확실성/결측 보고
  ↓
G13. MapLibre LCLUC UI: 이전/이후 비교 대시보드·Swipe·Animate·Model Comparison
  ↓
G14. Docker Compose 개발/파일럿 → 격리된 Staging → 승인된 Production 배포·DR 검증
```

**DB와 래스터 저장소를 구분한다.** 기본 설계는 **PostgreSQL/PostGIS = 관계형·공간 메타데이터 정본**, **S3 호환 Object Storage/파일기반 COG = 대용량 원본과 버전별 불변 이미지/라벨/마스크/예측 아티팩트**, **GeoServer = 지도 서비스**, **학습 워커 = 수집·합성·AI 처리**이다. 모든 픽셀의 다중밴드 영상을 PostgreSQL `BYTEA`나 PostGIS raster 테이블에 일괄 적재하지 말 것. 예외적 in-DB raster는 실제 요구·성능시험으로 근거가 있을 때만 채택.

---

# 2. G0 — AS-IS/Baseline 실증 감사: 이관 전 먼저 수행

## 2.1 코드·DB·실제 자산 원장 확보

- `git branch`, commit SHA, dirty changes, 버전, 서비스 topology, 스택(Python/FastAPI 등 **실제 조사**, 추정 금지), DB 연결/ORM/마이그레이션 도구(Alembic·Prisma·TypeORM·SQLAlchemy 등 실제 조사), API 엔드포인트·E2E 테스트 확인.
- SQLite DB 파일 전체 목록·용도·파일 size·mtime·schema, `sqlite_master`, `PRAGMA table_info`, indexes, `foreign_key_list`, `integrity_check` 확인. WAL 모드면 일관성 있는 백업 스냅샷을 먼저 확보.
- 기존 수집 원장(`data/first-group-annual/`, `data/audits/`, `training-contract.json`, `run-result.json`, `annual-window-report.json`, `window-state.json`, `raw-reference/reference-report.json` 등 **실존 시** 재사용), STAC manifest, 로컬·원격 자산, 메타데이터 해시와 상태 대조.
- GeoServer `workspace → store → coverage/layer → style → GetCapabilities/GetMap/GetFeatureInfo` 실요청 및 프런트 MapLibre 타일 URL 확인. 기존 이미지를 임의 Canvas 격자로 렌더링하는 코드 발견 시 별도 TEST 경로 격리.
- 이전 모델 checkpoint가 있는 경우 **실제 아키텍처/데이터/클래스 정의/학습 split과 유효성** 역추적. 'U-Net++ 사용'은 checkpoint/config로 증명하기 전 확정하지 말 것.
- 승인된 행정경계/원본 자료 소유권·참조범위, 중복 ID, 타임존, 오래된 상대경로, 숫자 텍스트 저장/단위 혼재 확인.

## 2.2 수정 전 과거 Baseline을 동결하라

- `baseline_snapshot_id`, timestamp, git SHA, SQLite backup SHA256, file inventory hash, metadata-completeness report를 구성.
- 당시의 실제 `scene/asset/download/qc` 레코드와 접근 가능한 raw 자료를 불변 목록으로 등록; **현재 새로 모은 자료를 과거 실적에 소급 합산하지 말 것**.
- 각 province×year×month 및 AOI×year에 대해 이전 수집 건수/밴드 완성/실제 footprint/SCL 기준 cloud/NoData/유효 픽셀/관측 날짜를 산출 가능한 만큼 재구성.
- 과거 기록에는 있으나 원본 파일·마스크가 없어 계산 불가능한 수치는 `NOT_MEASURED` 및 사유(`MISSING_ORIGINAL`, `MISSING_MASK`, `UNVERIFIABLE_HASH`)로 남겨 실제 커버리지 0%와 구분.
- 256×256 테스트 창의 품질률을 해당 주 전체 커버리지로 승격시키지 말 것.
- `baseline_type`을 `LEGACY_REPORTED / VERIFIED_PRE_IMPROVEMENT / POST_IMPROVEMENT`로 분리.

**산출물**: `docs/lcluc/v3/00_as_is_architecture.md`, `00_sqlite_inventory.csv`, `00_baseline_snapshot_manifest.json`, `00_baseline_provenance_gaps.md`, `00_current_geoserver_layer_audit.md`.

---

# 3. G1 — SQLite → PostgreSQL/PostGIS 안전 이관 및 스키마 설계

## 3.1 데이터베이스 설계 원칙

1. **기존 테이블·코드 분석 후** 관계형 정규화 및 지리공간 테이블을 설계. 단순히 `sqlite.db`를 PostgreSQL 호환 SQL로 덤프하는 것만으로 완료 아님.
2. PostgreSQL과 PostGIS 호환 버전을 **현재 환경에서 검증하여 고정**하고 `CREATE EXTENSION postgis` 권한·실패시 조치·버전 기록. `pgcrypto` 등은 필요할 때만 채택.
3. 프로젝트 기존 ORM/migration 도구를 유지하고 **전진/되돌림 migration**, 데이터 backfill, schema version, 인덱스 계획, API/schema의 backward compatibility 작성.
4. PK/FK/UNIQUE/CHECK/NOT NULL의 실제 업무 제약 적용. 신뢰할 수 없는 과거 결측값은 null을 허용하고 이후 점진적 제약으로 강화. 무작정 null을 0이나 기본 오늘 날짜로 바꾸지 않음.
5. UUID/기존 string ID를 그대로 보존하거나 명시된 mapping 테이블로 연결. SQLite 정수 PK 재발급으로 과거 result/scene/job ref 끊지 않음.
6. `created_at`, `updated_at`, `observed_at`, `ingested_at`, `processed_at`, `approved_at`은 각각 다른 뜻으로 저장; UTC 타임스탬프 및 명확한 연도·현지계절 파생값.
7. `raw_asset`과 `derived_artifact` 원본 참조는 object URI 또는 불변 파일경로 + SHA256 + 크기 + content type + 접근정책으로 관리. 링크만 있고 실제 자산이 없는 경우 `MISSING_ASSET`.
8. geometry는 PostGIS `geometry(MultiPolygon, 4326)` 또는 용도별 타입을 명확히 정의; WKT/GeoJSON/BBOX 변환 시 **경위도 축 순서, SRID, 180도 경도/섬 다중 폴리곤, invalid geometry** 검증. `ST_IsValid`/`ST_Transform`/`ST_Intersects` 및 `GiST` 인덱스 적용.
9. 주 면적은 **지구상 실면적**을 계산할 수 있는 적합한 방식(`ST_Area(geom::geography)` 또는 검증된 지역 equal-area/측지 면적)으로 산출. **EPSG:3857 면적을 그대로 사용 금지**. 픽셀 마스크 기반 면적은 원본 분석 그리드/면적 계산을 정본으로 하고, 일반화된 footprint polygon 면적과 구분.
10. 지리경계 최신화로 과거 면적비율이 바뀌지 않도록 `boundary_id/version`, `target_grid_id/version`, `mask_policy_version`, `area_method_version` 저장.

## 3.2 최소 논리 엔터티 및 필수 관계(실제 테이블명은 기존 코드에 적응)

| 도메인 | 제안 엔터티 | 필수 데이터·관계 |
|---|---|---|
| Admin/AOI | `provinces`, `aoi_boundaries`, `analysis_grids` | `province_code`, geometry, boundary_version, land_mask_id, area_ha, CRS, affine/grid metadata |
| STAC/수집 | `stac_items`, `scene_aoi_intersections`, `raster_assets`, `acquisition_jobs` | sensor/provider, scene/item ID, acquisition timestamp, processing_baseline, band keys, scene footprint, AOI intersect, bytes, checksum, search/download/verified 상태·실패 |
| 공간품질 | `scene_quality`, `scene_masks`, `monthly_coverage`, `annual_composites`, `annual_coverage` | scene vs AOI cloud pct, shadow/defect/no-scene, valid count, pixel/raster URI, mask policy, composite method, actual observation dates |
| 참조라벨 | `reference_products`, `class_schemas`, `class_crosswalks`, `label_assets` | Esri/WorldCover source/year/version/license, native class, target class, uncertainty, NoData/Cloud flags |
| AI Dataset | `dataset_versions`, `patches`, `dataset_splits`, `dataset_qc` | patch AOI, scene origin, 6-band verified, masks, label/ref year, geo holdout, class distribution, readiness |
| MLOps | `training_runs`, `model_versions`, `model_evaluations`, `validation_sets`, `drift_events`, `retraining_tickets` | architecture, git/data/model/seed/hyperparameters, checkpoint URI, per-class confusion metrics, fixed holdout, approval/rejection, audit |
| 연차 추론 | `prediction_results`, `prediction_assets` | year, actual source period, model_version, class_schema, COG, valid_mask, confidence, coverage/validation |
| GeoServer | `gis_layer_registry`, `layer_publications`, `style_versions` | source_kind, result_id, immutable layer version, workspace/store/layer/style, TIME, exact footprint, GetMap verification |
| 변화분석 | `comparison_runs`, `transition_matrices`, `area_statistics` | T1/T2 result_id, common-valid mask, observed/excluded area, class transitions, sampling CI/limitations |
| 감사·실행 | `pipeline_jobs`, `job_events`, `audit_events`, `approval_records` | G0~G14 trace ID, input/output hashes, idempotency key, code/data/source version, error, RBAC, rollback |

가용범위만 나타내는 `bbox`는 단지 사각형 후보영역이며 **실제 유효관측 영역이나 주 전체 커버리지의 증거가 아님**. `coverage_mask`를 원본 픽셀 기반으로 집계하고, 필요하면 성능을 위해 단순화된 `valid_footprint_geom`을 PostGIS에서 제공하되 집계값과 차이를 감사한다.

### 필수 메타데이터 프로파일 (예시 필드, 실제 컬럼 추가 전 schema 회귀검증)

```text
record_id, source_kind, provider, source_product, license_uri,
province_code, aoi_id, boundary_version, year, month, acquisition_timestamp,
scene_id, stac_collection, stac_item_id, observed_footprint_geom,
scene_cloud_pct, aoi_cloud_pct, aoi_shadow_pct,
file_uri, sha256, file_size_bytes, asset_status, download_status,
crs, affine, grid_id, pixel_size_m, width, height, nodata_value,
mask_policy_version, class_schema_id, class_crosswalk_version,
valid_observation_count_uri, valid_mask_uri, annual_composite_uri,
aoi_land_area_ha, valid_area_ha, invalid_area_ha,
newly_recovered_area_ha, coverage_pct, coverage_measurement_status,
model_id, model_version, experiment_id, validation_set_version,
result_id, geoserver_layer_id, created_at, provenance_manifest_uri
```

- **필수 상태 구분**: `NOT_SEARCHED`, `SEARCHED`, `DISCOVERED`, `DOWNLOAD_PLANNED`, `DOWNLOADED`, `ASSET_VERIFIED`, `QC_PASSED`, `COMPOSITED`, `REFERENCE_READY`, `TRAIN_ELIGIBLE`, `INFERRED`, `PUBLISHED`, `CHANGE_VALIDATED`, `BLOCKED` 등. 서로 다른 단계 상태를 `success=true`로 합치지 말 것.
- **문서화되지 않은 기존 행의 `coverage_pct`, `cloud_pct`, `source_year`, `geometry`는 NULL**. 누락 데이터가 없다는 뜻과 구분하기 위해 `measurement_status` 저장.

## 3.3 안전한 이관 실행 절차

1. `DISCOVERY`: 기존 SQLite마다 백업 및 WAL 일관성 검증, 테이블/인덱스/관계/행수/NULL/중복/문자 인코딩/업무별 소유권 인벤토리.
2. `MIGRATION_PLAN`: SQLite→PG 컬럼·타입·PK·FK·geometry 변환 매핑 문서 생성. SQLite 문자열 JSON, Boolean, Decimal/float, naive datetime, numeric text, BLOB 처리 계약 명시.
3. `SCHEMA_PROVISION`: PostGIS 활성화 확인, 스키마·시퀀스·constraint·index·권한·기본 migration 적용.
4. `DRY_RUN`: 사용중지한 사본 SQLite에서 소량 + 대표 데이터 이관 시험. 원본 불변, ETL idempotent/upsert 및 재시도 가능, 대량 batching/transaction.
5. `VALIDATE`: 테이블별 row count, 대표 checksum, PK/FK 참조, 중복, 날짜/주 코드, 원본 object URI 접근, geometry (`SRID`, `ST_IsValid`, 실제 지도 위치), 경계 area, SQL/API 응답 비교. 단순 row count 일치만으로 PASS 금지.
6. `CUTOVER`: 승인된 정지창 또는 명시된 일관성 전략을 선택; SQLite 쓰기 정지 → 마지막 델타 이관 → 새 PG 접속과 기능·성능 smoke test → read/write 전환. 무계획 dual-write 금지.
7. `ROLLBACK`: 실패하면 애플리케이션 트래픽을 구 SQLite 또는 사전 백업으로 명시된 조건에서 복귀. **컷오버 이후 PG에서 새로 쓴 데이터의 정합성/재동기화 계획 없이 되돌리기 금지**.
8. `POST_CUTOVER`: 일정 기간 read-only legacy snapshot + migration report, DB pool/timeout/transaction/lock/concurrency/slow query 모니터링. 중단·resume·복구 훈련.

**실제 운영 DB를 별도 승인 없이 삭제, `DROP DATABASE`, `TRUNCATE`, 무작정 schema reset 실행 금지.** 보안정책상 DB 접근 불가 시 migration DDL/ETL/fixture를 만들고 `REAL_DB_MIGRATION=BLOCKED`로 명시한다.

## 3.4 DB 성능·보안·운영 필수

- GeoJSON 큰 폴리곤/Scene footprint에 GiST, `province/year/month`, `source_kind/source_year`, `dataset_id/version`, `job_id/status`에 적절한 B-tree, 필요한 partition/materialized view는 **실제 EXPLAIN ANALYZE 측정 후 도입**.
- 매 픽셀을 행으로 만들지 않는다. 픽셀 수준 raster/valid mask를 object storage에서 처리하고, **집계 결과·통계 범위·출처 증거**를 PostGIS에 반영.
- 서비스별 권한 분리: API DB user, ETL worker, GeoServer 읽기전용 DB user, Migration admin. 자격증명은 환경/secret manager 관리하고 Git·로그·클라이언트에 노출 금지.
- TLS/private network, 연결풀, statement timeout, 장기 쿼리/파일 락, schema/backup monitoring, 정기 restore 테스트.

**이관 증거**: `db_migration_run_id`, 이전/이후 행수와 hash, 위반 FK 0, 좌표 오류 목록, 이관되지 못한 레코드별 사유, SQLite backup hash, rollback drill 결과.

---

# 4. G2 — 기존 vs 신규 자료수집 전량 비교 체계(가장 중요한 신규 요구)

6개 주 × 2020~2025 = **36개 주·연도**, ×12개월 = **432개 주·월의 가용성 감사 단위**를 관리한다. 이는 432개의 위성영상을 전량 다운로드하라는 의미가 아니다. 각 월에 여러 장면이 존재할 수 있다.

## 4.1 반드시 같은 AOI·기간·분모·정의로 비교

- 비교 키: `(aoi_id, boundary_version, year, season_policy, target_grid, mask_policy_version, measured_raster_scope)`.
- 비교 시점 ① `BASELINE_BEFORE`(기존 실제 확보자료) ② `AFTER_NEW_ACQUISITION`(추가 수집·동일 품질정책) ③ `AFTER_COMPOSITING`(동일 연도 다중시점 합성 결과)을 별개 버전으로 저장.
- **기존 자료의 관측 가능 영역**을 A_old, **추가 자료 관측 가능 영역**을 A_new, **합성 후 연간 관측 가능 영역**을 A_after로 정의. 같은 AOI·격자 유효 마스크에 대해 집합 비교하며 육지 마스크 적용.
- `new_recovered_mask = A_after & ~A_old`; `still_missing_mask = AOI_land & ~A_after`; `lost_valid_mask = A_old & ~A_after`(같은 정책인데 기존 유효 픽셀이 사라진 경우는 원인 조사).
- 유효 커버리지: `100 × area(valid_mask & AOI_land) / area(AOI_land)`; 증가폭 **%p**=`after_pct - before_pct`.
- **신규 확보면적(ha)**=`area(A_after \ A_old)`; **잔여 결측 면적(ha)**=`area(AOI_land \ A_after)`; **기존 결측 복구율(%)**=`100 × area(A_after \ A_old) / area(AOI_land \ A_old)` (기존 결측 0이면 N/A).
- cloud/shadow 비율은 `scene 전체` vs `AOI 내` vs `연간 합성 잔여 구름/결측`으로 따로 표시. `NO_SCENE`, `UNVERIFIED_DOWNLOAD`, `OUTSIDE_FOOTPRINT`를 구름으로 오기하지 말 것.
- 과거 마스크 정책이 다른 경우 **(a) historical as-reported (b) 같은 최신 마스크로 원본 재처리한 fair comparison**을 병행하고, 원본이 없어 (b) 불가능하면 교차비교 금지·한계 표기.
- 객체 파일 수·다운로드 GB 증가, 유효 면적 증가, 지역/시기 대표성 향상은 별개의 성과. 많은 장면수만으로 성공 선언 금지.

### 4.2 필수 기존/신규 비교 데이터 표

| 필드 | 필수 내용 |
|---|---|
| 위치/기간 | province, AOI, 연도/월, AOI 버전, 실제 육지면적 |
| 기존 수집 | 찾은 scene, 실제 검증 download scene, 6밴드 완성수, valid footprints, 기존 관측률, cloud/shadow/NoData 이유 |
| 추가 수집 | 신규 실제 검증 scene, 신규 bytes, scene overlap, 품질통과 수, 새 관측 날짜/계절 |
| 합성 후 | 합성 정책, 유효 관측횟수 분포, 관측률, 잔여 결측, 최소/최대/중앙 관측시기 |
| 개선 | 기존 유효 ha, 신규만 복구 ha, 수집 후 유효 ha, %p 증가, 기존 결측 복구율, 아직 부족한 지역 |
| 외부 참조 | Esri product year/version, Esri Clouds=10 면적비율, NoData=0, WorldCover 유무/연도, 해당 자료의 실제 coverage |
| 근거 | source item/asset hash, mask raster URI, AOI geometry ref, coverage job & source version, calculation code ref |

> `cloud_pct`와 `valid_coverage_pct`를 무조건 합쳐 100%로 가정하지 말라. 구름·그림자·결함·관측 없음·마스크 정책 제외 등 여러 원인이 존재하고 AOI 바깥도 별개다.

## 4.3 비교 지도의 필수 레이어

- `legacy_valid_mask` — 이전에 유효 관측 가능했던 픽셀.
- `newly_recovered_mask` — **이번 수집 때문에 실제로 새로 확보한 픽셀**.
- `still_missing_mask` — 여전히 관측 불가.
- `cloud_shadow_mask` — 구름·그림자 제외.
- `annual_valid_count` — 연도 중 해당 픽셀을 유효하게 관측한 횟수.
- `baseline_vs_after_diagnostics` — 동일 공간/시점/품질정책의 집계.

3색 비교지도(기존 유효 / 이번 신규 확보 / 여전히 결측)를 GeoServer/MapLibre에서 실제 래스터로 렌더링하라. **개발용 원본 픽셀 격자 외곽선을 사용자 주 화면에 표시하는 것을 지도로 대체 금지.**

---

# 5. G3–G4 — Sentinel-2 다중시점 수집·전처리·연간 합성

## 5.1 증분 수집 전략

- Sentinel-2 Level-2A Surface Reflectance **B02/B03/B04/B08/B11/B12 + SCL** 및 원본 STAC JSON/제품 XML/라이선스/해시 획득.
- 실제 provider(STAC Collection/asset key)는 연결시 metadata로 확인; 기존에 확보된 `item_id` 및 `asset sha256` 먼저 inventory하여 **중복 다운로드 방지**.
- `scene eo:cloud_cover`는 장면 전체 구름률이므로 20%를 모든 AOI에 엄격 적용하지 않는다. 월/계절별 후보 검색 → **AOI 내부 SCL 구름·그림자 유효관측 실제 기여율** 계산 → 누락된 픽셀을 회복하는 장면 우선 순위화.
- `PLAN`에서 후보 scene, **추가 복구 예상 ha**, 중복 관측 비율, 저장·전송량, 장면/월·지역, 시간/GPU 비용 추정; 승인된 용량 후 `EXECUTE` 수행. 예상치와 실측치를 분리.
- HTTP 429 `Retry-After` 준수, concurrency 제한, bounded retry/backoff, chunk/window/range read, 중단/재개/idempotency, 권한·토큰 비노출, 증분 수집 성공/실패 감사.
- 한 개 실제 AOI에서 시작: Pilot-0(기존 256×256 검증) → Pilot-1(동일 AOI 여러 날짜) → Pilot-2(동일 AOI 두 연도) → Pilot-3(주 일부/전체) → Rollout(6개 주).

## 5.2 처리·품질·시점 일관성

- 좌표계/affine/grid/bounds/width/height·픽셀 정합 감사; 이전 Banten의 `EPSG:32748`를 6개 주 공통으로 고정하지 말 것.
- Sentinel-2 10m 밴드와 20m SWIR/SCL의 실제 해상도 검증. 연속 밴드 bilinear 등 승인 방식; **범주형 SCL/WorldCover/Esri는 nearest**; 보간은 10m 새 실제 관측정보 생성이 아님.
- DN→Surface Reflectance 변환에서 `BOA_QUANTIFICATION_VALUE`/offset/processing baseline 실제 적용 여부, raw 원본과 ML normalized tensor를 구분.
- SCL mask의 `NoData`, cloud shadow, medium/high cloud, cirrus, defects 등 정책과 2/7/11 등 예외 정책을 **명시한 버전**으로 관리. AOI 뚜렷한 계절·수역·구름 가장자리 문제를 QC 표본으로 확인.
- 같은 연도 다중 날짜 후보에서 quality-first·medoid·median의 유효 coverage와 밴드 물리일관성/계절 분포 비교. 건기/우기 stack을 통한 농경지·침수 식생 분류 개선도 실험.
- 각 픽셀의 `observation_count`, `scene_ids/source_index`, `last/median/acquisition_time`, `gap_reason`, `valid_mask`를 생성하며 전후 결과는 immutable COG+manifest 보존.
- 한 해에 유효 장면이 전혀 없으면 `NO_OBSERVATION` 유지. 전년/익년 또는 Esri의 분류 코드로 Sentinel-2 관측값을 채운 경우 추정으로 따로 표기하고 실제 구름 복구 실적으로 산입 금지.

## 5.3 Esri·WorldCover 통합

- Esri/Impact Observatory 연차 토지피복 제품은 출처·연도·라이선스·asset ID·클래스 코드(`0=NoData`, `10=Clouds`)를 확인하고 **참조라벨 또는 독립 비교 제품**으로 관리.
- ESA WorldCover 2020 v100, 2021 v200만 해당 시점 참조로 사용. 제품별 생성방법 차이/노이즈/공간해상도 및 실제 구름 영향을 감사.
- **Sentinel-2 SCL 원인별 유효율**과 **Esri annual classification Cloud/NoData 비율**을 **같은 AOI/연도/분모**에서 각각 계산해 나란히 표시하되 둘을 같은 물리량이라고 주장하지 말 것.
- 소스별 native class 유지 및 프로젝트 목표 class schema 대응 매트릭스 작성, 승인되지 않은 일대다 분리 금지.
- WorldCover/Esri 의사라벨의 공간·시간 불일치, 교차제품 disagreement map, label confidence, 품질별 선택 정책 생성. Esri도 Sentinel-2 기반 외부 예측지도이므로 `Esri agreement`만으로 독립 정확도 검증 불가.

---

# 6. G5–G6 — PostGIS 메타데이터와 GeoServer 1차 연계

## 6.1 GeoServer는 기존 서비스를 재사용하라

- 기존 설정 REST/레이어 연결을 우선 복구·보완하고 신규 GeoServer를 무조건 중복 설치 금지.
- `PostGIS Data Store`는 **행정구역 경계, AOI, 유효 footprint, 변화 폴리곤, 통계 조회/검토용 벡터**에 활용. 대용량 정수 토지피복 래스터/영상은 **Object Storage/COG 등 지원 검증된 CoverageStore, ImageMosaic/타일 서비스**로 제공.
- 1차 지도: `sentinel2_composite`(영상), `scl_mask`, `annual_valid_mask`, `observation_count`, `coverage_before/after/new_recovered/still_gap`, `esri_reference`, `worldcover_reference`(실제 확보연도/범위만).
- GeoServer LayerRegistry/PostGIS에 `workspace`, `store`, `native_name`, `style_version`, `source_kind`, `dataset_version`, `coverage_mask_version`, `bounds`, `time_dimension`, `wms_endpoint`, `verification_result`, `published_at` 등 저장.
- SLD `RasterSymbolizer` + categorical `ColorMap type=values` + nearest, NoData 투명/해칭, GeoServer GetCapabilities/GetMap/GetFeatureInfo/원본 class_id 대조. WMS PNG 색상을 원본 통계 계산 입력으로 사용 금지.
- Tile cache는 year/time/style/dataset_version별 안전한 키 또는 캐시 무효화 절차를 제공. 버전 변경에도 이전 타일이 새 연도인 척 나타나지 않아야 함.
- 2025년 WorldCover layer 재명명 금지. 2025년 외부 분류도가 Esri일 경우 `EXTERNAL_ESRI` 명시.

## 6.2 GeoServer 연계와 PostGIS 공간검증

- `ST_Intersects(aoi.geom, footprint.geom)`는 후보 필터일 뿐 실제 Cloud Gap 면적이 아니다. rasterized 유효 마스크에서 정밀 면적 측정 후 DB 저장.
- 타일/패치가 여러 UTM Zone에 걸치면 분석 격자/적절한 면적 계산을 분리해 위치 오차 및 중복면적 제거. 동일 pixel 범위의 double count 금지.
- `/layers`, `/coverage`, `/pixel-query` 기존 API에서 `aoi_id/year/dataset_version/boundary_version`, 실자료/참조/예측 구분, quality status, observed footprint와 NoData reason 반환.
- API/DB/GeoServer/MapLibre가 같은 `result_id`/`dataset_version`/`class_schema_id`를 참조하는지 E2E 대조.

---

# 7. G7–G9 — AI-ready 데이터셋·학습/재학습·MLOps 성능 개선량

## 7.1 학습데이터셋 '이전 vs 이후' 비교를 1차 KPI로 삼아라

각 immutable dataset_version에 대해:

| KPI | 이전 (Baseline) | 이후 (New) | 변화 계산 |
|---|---|---|---|
| 6밴드+라벨·마스크 적격 patch | 실제 재검증 수 | 실제 재검증 수 | 새 적격 패치 수/증가율 |
| 학습 주/연도/계절 대표성 | 실제 train footprint | 새 train footprint | 신규 위치·시점 영역 및 누락 클래스 개선 |
| 품질 마스크 이후 유효 픽셀 | 실제 수 | 실제 수 | 같은 AOI·mask policy의 %p 변화 |
| 클래스별 학습 픽셀/패치 분포 | 클래스별 baseline | 클래스별 new | 편중도 및 부족 클래스 감소 |
| 독립 라벨 비중 | 사람 검증·고해상도 검증 | 새 independent samples | 증가율(품질·공간독립성 포함) |
| `ready_for_training` | 당시 실제 Gate | 현재 실제 Gate | 차단 사유 해소 여부 |

Train/Val/Test를 지역·시점으로 분리하고 공간 중첩·인접 패치·같은 원본 장면의 누출을 차단. Esri/WorldCover 의사라벨 중복으로 test set을 만들지 말고, 별도의 신뢰 가능한 독립 참조표본을 확보할 것. 정확도 지표는 어떤 라벨에 대한 지표인지 표제에 명시.

## 7.2 비교 실험을 반드시 같은 시험셋에서 실행하라

- `legacy 3 patches/3 epochs (OA 1.35%, mIoU 0.27%)`는 **과거 참고 진단**이며 고정·독립 시험셋 재평가 없이는 개선 KPI baseline으로 사용 금지.
- A=`현재 사용 가능한 이전 모델/동일 독립 Holdout`에 대한 재평가, B=`신규 학습 모델/똑같은 Holdout` 평가. 비교 데이터셋·class schema·mask/ignore 기준·AOI·시점을 고정.
- 모델 구조(U-Net, U-Net++ 등)는 **실제 체크포인트/코드 확인 및 조건 고정** 후 비교. 네트워크 구조·손실·배치·학습Epoch·Augmentation·라벨 버전·학습자료를 명시.
- **성능향상이 데이터 확대의 영향인지 알고리즘 재학습의 영향인지** 구분하기 위해 실행 가능한 경우 2×2 실험:

| 실험 | 학습모델 | 추론용 입력 | 목적 |
|---|---|---|---|
| A | 이전 모델 | 이전 처리 입력 | 공통 홀드아웃 비교 Baseline |
| B | 이전 모델 | 개선 입력/합성 | 관측·전처리 개선 효과 |
| C | 신규 모델 | 이전 처리 입력 | 모델 학습 개선 효과 |
| D | 신규 모델 | 개선 입력/합성 | 최종 조합 성과 |

> 입력 밴드/계절 스택이 달라 기존 모델과 호환되지 않으면 해당 실험은 `NOT_COMPARABLE`을 기입하고 대체 검증 설계·공정한 비교 가능성 보고. **새로 관측 가능해진 픽셀의 수**와 **기존 공통 시험 픽셀의 예측 정확도 개선**은 같은 KPI가 아님.

## 7.3 반드시 기록할 분류지표 및 향상 수치

- OA/Accuracy, per-class Precision, per-class Recall, per-class F1, macro Precision/Recall/F1, weighted F1(필요시), per-class IoU, mIoU, confusion matrix, class support, 빈 클래스 여부, ignore/NoData 정책.
- 정의: `Precision=TP/(TP+FP)`, `Recall=TP/(TP+FN)`, `F1=2PR/(P+R)` (분모 0은 명시 정책), `IoU=TP/(TP+FP+FN)`, `OA=correct/valid_test_pixels`.
- **절대 개선(%p)** = `100 × (metric_new - metric_old)` (지표가 0~1 범위일 때); **상대 개선률(%)** = `100 × (new-old)/old` (`old>0`일 때만). 예: `F1 0.60→0.70` = `+10%p` / `+16.67% 상대`라는 계산 예시이지 실제 성과 아님.
- 독립 시험 표본과 지역별/클래스별 신뢰구간(가능 시 지리적 block bootstrap 또는 표본설계 기반), 복수 seed 변화, 실제 유효 테스트면적 및 샘플 수를 보고. 클래스별 Recall 하락·미검출 증가를 macro-F1 상승으로 숨기지 말 것.
- `validation_set_id/version`, `label_source`, `sample_count`, `valid_pixel_count`, `test_aoi_id`, `year`, `ignore_mask`, `evaluation_code_git_sha` 고정. 사용자가 보는 Accuracy와 Precision의 라벨/계산방식 혼동 금지.
- 독립 라벨이 없다면 `agreement_with_esri`, `agreement_with_worldcover`만 측정 및 명명. **의사라벨 일치도를 현장 정답 정확도라고 발표 금지**.
- 기준모델 checkpoint와 시험자료가 유효하지 않으면 `legacy_metric_baseline_status=NOT_COMPARABLE`로 기록하고 검증 가능한 새 Baseline을 먼저 확립.

## 7.4 MLOps Pipeline과 재학습 Gate

```text
New data / labels → Dataset Registry (immutable version + spatial evidence)
     ↓
Readiness (train≥required, class coverage, provenance, leakage/quality PASS)
     ↓
Training Experiments (git SHA / params / seed / split / metrics / checkpoints)
     ↓
Independent Evaluation (same holdout, class metrics, confidence/limitations)
     ↓
Model Registry (Draft → Validated → Approved → Staging → Production)
     ↓
Annual Inference → Prediction Registry → GeoServer 2차 → Change Analysis
     ↓
Monitoring: observed coverage, input/label/performance drift, class anomaly
     ↓
Collect more data OR retraining ticket (승인·비용·검증·rollback)
```

- Registry는 `data_version`, `training_run`, `model_hash`, `metrics`, `validation_set_id`, `owner`, `reviewer`, `approval_timestamp`, `rollback_target` 저장.
- `coverage_drift` → **수집/합성 조치**, `performance_drift` → **독립 라벨 확인 후 재학습 후보**, `label_drift` → **표본 라벨 검토**, `GIS tile issue` → **서비스 복구**, `429/권한 실패` → **네트워크/권한 조치**. 모든 문제를 재학습으로 해결하려 하지 말 것.
- Model promotion을 위한 최소 독립검증·주별/클래스별 성능·회귀 한계·성능향상 기준은 **계약/운영자 승인 threshold 설정값**으로 관리; 임의 단일 값 하드코딩 금지.
- 무승인 자동재학습·무승인 Production 승격 금지. Canary/Shadow→승인→Production·rollback 연계. 이전 모델의 해당 연차 레이어/분석결과는 덮어쓰지 않고 버전별 유지.
- 학습 데이터 부족(예: legacy Train=0)이면 `BLOCKED_INSUFFICIENT_TRAIN_DATA` 유지. 신규 샘플 수가 목표에 도달해도 클래스/지역/계절/독립시험 조건 불충족 시 BLOCKED.

---

# 8. G10–G12 — 연차별 AI 추론·GeoServer 2차·변화탐지 정확성

- 해당 연도 실제 Sentinel-2 연간/계절 입력으로 정수 `class_id` 래스터 생성. `prediction_class_YYYY.tif/COG`, `prediction_valid_mask.tif`, `confidence/entropy`, `manifest`, `model_version`, `observed_source_period`, `mask_policy`, `class_schema` immutable 보존.
- 미관측 픽셀을 자동 '산림'이나 다른 클래스로 채우지 말고 NoData. 보완/예측 모델이 있으면 `ESTIMATED`와 별도 레이어·근거·검증.
- GeoServer 2차: `prediction_YYYY`, `prediction_valid_mask`, 실제 `TIME`, `ResultRegistry ↔ LayerRegistry`, WMS/WMTS style nearest, GetMap/GetFeatureInfo/원본 class_id 샘플 정합.
- T1/T2는 동일 AOI·동일 분석격자·호환 class schema·실제 관측시점·quality mask를 preflight 검증. `valid_common = valid_T1 & valid_T2 & land_AOI_mask`에서만 토지피복 전이·면적을 계산.
- NoData/Esri Clouds를 실제 지표피복 변화로 계상 금지. `AOI total`, `common valid`, `excluded`, `estimation` 면적 각각 표기.
- 현장 정책에 필요한 주 전체 면적 추정은 독립 층화 확률표본·accuracy-adjusted estimate와 CI를 별도 설계. 단순 결측 지역 비례 확장 금지.
- 변화행렬과 지도, 산림 감소 ha, 시가지 확대 ha, year slider 등 UI 값은 같은 `comparison_id, t1_id, t2_id, aoi_id, mask_policy_version`에서 생성.
- '벌채'는 원인 추정이며 `Forest→Built-up` 같은 클래스 전이만으로 자동 확정 불가.

---

# 9. G13 — SDSS 사용자화면/성과 보고 기능(필수)

기존 7개 최상위 메뉴와 `GeoAI Toolbox → LCLUC Workspace`를 유지. 다음 화면을 기존 탭/패널에 매핑하고 중복 메뉴를 남발하지 말 것.

## 9.1 핵심 대시보드

A. **6개 주×연도×월 수집 현황**: scene 검색/실수신/검증 다운로드, sixband, 관측일·계절, source·year·licence, 부분범위 vs 주 전체, 지도 coverage footprints.

B. **수집 전후 커버리지 비교**: province/year/land AOI 기준 ① 기존 커버리지% ② 신규 합성 후% ③ 회복된 면적 ha ④ %p 개선 ⑤ 잔여 NoData/Cloud/Shadow 등 원인 분포. 비교지도(기존 유효/신규 확보/남은 결측) + 기간별 관측횟수.

C. **Sentinel-2 vs Esri 결측 비교**: 같은 AOI/연도 기준 SCL AOI 구름·그림자와 Esri Clouds(10)/NoData(0) 각각 표시, 두 측정량의 차이 명시.

D. **AI 데이터셋 이전/이후**: band completeness, 적격 patch 수, class distribution, 신규 대표 영역/연도/계절, 독립 라벨 수, leakage/ready Gate.

E. **모델 성능 향상 비교**: Baseline vs Challenger vs Approved, 같은 holdout에서 Accuracy, Precision, Recall, F1, mIoU, per-class IoU/Recall, confusion matrix, 성능 향상 `%p`와 상대 `%` 동시 표시. `legacy reported`/`independent verified` 배지.

F. **MLOps 모델 생애주기**: Dataset/Experiment/Model/Prediction version, drift trigger, retraining ticket, 승인/거부·운영 배포/롤백, checkpoint, 평가자.

G. **연차별 9클래스/실제 클래스 지도**: 원본 클래스 체계가 승인됐을 때만 9개로 통합; T1/T2 Swipe·Animate, quality/no-data mask toggle, 개별 클래스 filter, pixel popup, observed/estimated 구분.

H. **변화탐지·보고서**: 2020↔2025 실제 공통 유효면적, 면적 전이행렬, 순증감, 주별/연도별 품질 요약, 다운로드 가능한 근거/실행이력.

## 9.2 화면의 잘못된 완료 표시 방지

- `baseline` 값이 미측정인데 `0%`로 표시하여 100% 개선처럼 만드는 UI 금지.
- 주 전체 자료가 아닌 256×256 patch를 주 전체 색상지도나 면적으로 확장 금지.
- Esri external reference를 자체 AI inference로 표시 금지.
- 지도 tile 이미지는 **표시용**이며 원본 pixel count 기반 area/statistics는 서버가 계산.
- 숫자가 없으면 `미측정(원본 없음/검증 대기/권한 부족)`와 다음 조치를 보여준다.

---

# 10. G14 — 최적 배포판: 개발→스테이징→운영 환경 분리

## 10.1 배포안 선정 기준

사용환경의 실제 서버/GPU·예산·보안·RPO/RTO·데이터 용량·트래픽을 **먼저 확인**하여 무근거로 'Kubernetes가 항상 최적'이라고 결론내리지 말 것. 다음 두 계층을 기준으로 제안하고 각 계층별 비용·복잡도/HA 대안을 비교해 선정.

### Deployment A — 로컬/개발·초기 파일럿(재현 가능한 최소 구성)

- Docker Compose: `api`, `worker/queue`, `postgres+postgis`, `object-store`(예 MinIO, 실제 라이선스/운영정책 검토), 기존 `geoserver`, `frontend`, 선택 `mlflow`, `metrics/logging`.
- Redis/Celery/RQ 등 queue는 실제 코드·비동기 시스템 확인 후 필요할 때 도입. 기존 백엔드/모델 엔진과 중복 설치 금지.
- `compose.yml`은 이미지/버전 고정(digest 또는 명시된 지원 버전), healthcheck, DB migrate init job, 초기 데이터 옵션, named volumes, graceful shutdown, resource limits, profile/dev overrides 포함.
- GeoServer data directory 및 DB/object 저장소를 지속 볼륨에 둔다. 컨테이너 삭제/재시작에도 레이어·원본 자산이 유지되어야 한다.
- 포트·CORS·공개/내부망 분리, DB/관리 포트 외부 직접 노출 금지, read-only 자산 접근, `.env.example`에는 비밀값 없이 변수 이름만.
- 개발 PC GPU 부재 가능: CPU smoke path와 GPU 학습 job 별도. H100 등 실존 GPU 무확인 설치 가정 금지.

### Deployment B — 스테이징/운영(규모·보안·HA 요구 시)

- Kubernetes(K8s) Helm/Kustomize 기반 `api`, autoscaled inference/workers, `geoserver`, metrics, secrets/config, Jobs/CronJobs + 승인된 ML jobs. 실제 환경이 K8s 부적합하면 운영 Compose/VM 대안과 선택 근거를 함께 제출.
- **운영 PostgreSQL/PostGIS는 가능한 경우 관리형 또는 HA DB로 분리**, 자동 백업 + PITR, 백업 복원검증, read replicas는 부하 특성과 실제 필요에 따라.
- S3 호환 오브젝트 스토리지: 불변 버전·해시·접근권한·라이프사이클, 원본 보존/파생자료 재계산 정책.
- GeoServer: 동일 스타일·LayerRegistry와 object storage/COG 읽기연결, 필요한 공유 Data Directory 관리/지원되는 설정 동기화, 타일캐시 volume/분리, 여러 replica의 동기화·버전 유효성·GetMap 성능 검증.
- NetworkPolicy, TLS/Ingress, secret manager, per-service RBAC, GPU job node selector/limit, background download rate limit, Postgres pool/metrics, storage quotas.
- CI/CD: lint/typecheck/unit/DB migration tests/geospatial deterministic tests/contract tests/E2E browser/published layer smoke/independent science validation evidence; green build가 과학 검증 PASS를 의미하지 않음.
- S2/Esri/WorldCover 데이터 전송·라이선스·인도네시아 데이터 주권·BIG 보안 요구사항을 최종 운영환경 승인 기준에 포함.

## 10.2 배포 게이트와 장애복구

- `dev`, `staging`, `production`은 **서로 다른 DB/객체 경로/namespace/secret/승인**을 사용. Dev 합성 데이터는 운영 결과와 물리적/논리적으로 분리.
- Deploy 순서: object/DB backup → migration dry-run → schema apply → verify → API/worker → GeoServer layer validation → UI/analytics → model serving (승인모델만) → rollback rehearsal.
- PostgreSQL backup/PITR/restore drill, object storage version restore, GeoServer data directory/SLD backup, metric baseline, storage pressure, 429/retry queue, model/prediction/layer rollback.
- 부하테스트: 6개 주 2020~2025 예상 scene metadata × endpoint QPS, AOI bounding query latency, WMS time/style cache, tile p95, batch coverage calculation time, worker recovery. 목표치는 사용자 승인 후 설계/검증.
- Deployment package: `compose.yml`, container build/lockfile, migration scripts, `deploy/helm` 또는 환경적합 템플릿, manifests, `.env.example`, secrets 설명, installation/upgrade/migration/rollback/restore runbook, load/health report.
- **외부 서비스/관리형 DB/GPU/권한을 실제로 사용할 수 없으면 staging/production 배포 성공으로 보고하지 말고 `BLOCKED_INFRA_OR_AUTH` 기록.**

---

# 11. 필수 자동·실데이터 검증 시험

## 11.1 DB 이관·메타데이터

1. SQLite snapshot hash/테이블별 row count와 PostgreSQL 이관 결과 reconcile, 실제 참조 무결성·geometry 수치 비교.
2. legacy record의 기존 ID, timestamp/UTC, source_uri/hash, JSON, nullable cloud/coverage 유지.
3. SRID 누락·뒤바뀐 위경도·경계 invalid polygons·멀티폴리곤 섬·빈 polygon에 대한 validation 실패/감사 동작.
4. 이전 DB의 coverage 미측정은 0이 아닌 `NULL/NOT_MEASURED`로 보존.
5. migration 두 번째 실행 시 중복행·중복layer·중복원본 생성 없음; 실패 중간재개/롤백 정상.
6. Index/geometry spatial filter의 query plan·응답성능을 실제 데이터 규모에 따라 확인.

## 11.2 수집·품질·전후 비교

7. 3개 가상 4×4 cloud mask에서 (가) 기존 (나) 추가 (다) 합성 유효화 후 `newly_recovered`/`still_missing`/퍼센트포인트/복구율 수학적으로 정확.
8. 산림지역 등 특정 픽셀을 새로 유효로 바꿨을 때 **기존 valid에는 없는 픽셀만** 신규 복구로 카운트.
9. SCL Cloud/Shadow/NoData, AOI 밖, 원본 미다운로드, Esri cloud value=10의 원인·분모가 분리.
10. 다른 연도 입력으로 현 연도를 채우지 않음. 중복 원본 scene에서 다운로드/통계 double counting 방지.
11. WorldCover 2021을 2025 GT로 사용하려 하면 policy rejection.
12. storage budget/HTTP429/Retry-After/restart/idempotency/credential-redaction 검증.

## 11.3 학습·성능 평가

13. Train 0 또는 클래스/지역/독립 라벨 부족 → `TRAIN_BLOCKED` 유지.
14. 동일 immutable holdout/model/schema가 아니면 향상률 = `NOT_COMPARABLE`.
15. confusion matrix로 OA, class Precision/Recall/F1/IoU, macro-F1, mIoU, pp/relative %의 기대값 검증. 0분모의 N/A 정책 테스트.
16. A/B/C/D 실험에서 학습모델 차이·입력 coverage 차이를 각각 기록하고 결측 영역 확대만으로 OA 개선 주장 금지.
17. pseudo-label agreement를 independent accuracy라고 부르면 테스트/리뷰 실패.
18. 승인 없는 재학습·모델 Promotion·Production GeoServer 덮어쓰기 금지; rollback 모델/지도 버전 일치.

## 11.4 GIS·UI·운영

19. 원본 class_id 래스터 vs GeoServer GetFeatureInfo/Backend pixel query vs MapLibre 팝업/범례 일치.
20. GeoServer 1차 reference/quality와 2차 inference prediction이 `source_kind`로 분리되고 metadata에 적합한 실제 연도 노출.
21. Swipe 0/50/100%, zoom/pan/resize, 출처·버전 동기화, Missing T1/T2/NoData 팝업, 원본 기반 면적·전이행렬 재현.
22. 6개 주 비교표 export CSV/JSON/PDF 등 현재 리포트 엔진 가능한 형식에서 **실제 NULL·출처·단위** 유지.
23. Postgres 재시작, worker 중단/재개, GeoServer 재시작, object storage 일시 오류에서 자산·메타데이터 불일치 없음.
24. Database PITR/mock restore + GeoServer 스타일/타일/레지스트리 재연결 Runbook 시뮬레이션. 실제 운영 restore는 별도 승인.

## 11.5 실제 데이터 Pilot 평가 Gate

- **P0**: SQLite snapshot·schema/row/geometry reconcile 및 새 PostgreSQL API 독립 Smoke PASS.
- **P1**: 기존 2021 256×256 원본에 대한 Before 데이터·실제 마스크/footprint 측정 및 기존 vs 이후 Null 정책 검증.
- **P2**: 동일 AOI 연도 내 서로 다른 실제 날짜 영상 ≥2개로 **신규 복구 픽셀·ha·커버리지 %p 실측**; 전후 COG·로그 보존.
- **P3**: 동일 AOI 실제 Esri 연차 참조/WorldCover 제공시점 확인 + SCL vs Esri 분모 일치 비교 + GeoServer 1차 검증.
- **P4**: 충분한 실학습 자료와 동일 독립 홀드아웃이 있다면 Baseline/Challenger Accuracy/Precision/F1/mIoU 실측. 없다면 `SCIENTIFIC_VALIDATION_BLOCKED`(코드 단위검증만 PASS).
- **P5**: 두 실제 연도 동일 AOI 추론·GeoServer 2차 레이어 원본 class_id 확인. 파일이 없으면 BLOCKED.
- **P6**: 공통 유효영역 변화행렬 및 면적/불확실성/SDSS 값 일치 확인.
- **P7**: Stage 환경 백업·복원·보안·성능·롤백·버전 정합검증. 실제 인프라 부재 시 조건부 아키텍처/런북 제출만.

서로 다른 상태 `CODE_PASS`, `DB_MIGRATION_PASS`, `REAL_DATA_PASS`, `MODEL_INDEPENDENT_VALIDATION_PASS`, `GIS_INTEGRATION_PASS`, `PRODUCTION_APPROVED`를 개별 표기. 자동시험 몇 개 통과한 것이 연차별 전체 분석 완료를 뜻하지 않는다.

---

# 12. 납품 폴더 및 반드시 제출할 결과 표

기존 저장소 경로 관례에 맞게 조정하되 결과 파일은 생성하라:

```text
docs/lcluc/v3/
  00_as_is_architecture.md
  00_sqlite_inventory.csv
  00_baseline_snapshot_manifest.json
  00_baseline_provenance_gaps.md
  01_sqlite_postgis_mapping_and_cutover.md
  01_migration_reconciliation.csv
  01_postgis_spatial_schema.md
  02_province_year_month_asset_inventory.csv
  02_province_year_coverage_before_after.csv
  02_newly_recovered_area_and_remaining_gap.csv
  02_sentinel2_vs_esri_gap_comparison.csv
  03_cloud_mask_composite_methods.md
  03_annual_composite_validation.csv
  04_label_source_year_and_crosswalk.md
  05_dataset_baseline_vs_new.csv
  05_geo_temporal_leakage_and_readiness.md
  06_model_experiments_manifest.json
  06_model_metrics_baseline_vs_challenger.csv
  06_per_class_metrics_and_confusion.md
  06_holdout_independence_and_model_card.md
  07_retraining_model_approval_rollback.md
  08_geoserver_1st_2nd_layer_registry.csv
  08_pixel_map_audit.md
  09_annual_change_and_common_valid_area.csv
  10_deployment_architecture_and_decisions.md
  10_migration_deploy_restore_runbook.md
  10_compose_staging_production_validation.md
  11_e2e_test_evidence.md
  11_gate_decision_and_blockers.csv
  12_executive_summary_before_after.md

# 위 문서뿐 아니라 실제 코드·schema migration·테스트·배포/설치 자산도 제출
migrations/          # 현행 마이그레이션 도구에 맞게 기존 저장소 재사용
src/...              # 기존 collector, geospatial QC, ML, MLOps, GIS, API modules 수정
infra/compose/       # 개발/파일럿
infra/k8s-or-alt/    # Staging/운영 배포안 (승인/환경 적합성 기반)
tests/               # 결정적 fixture + 실데이터 계약/통합/E2E
```

## 12.1 보고서 표 A — 6개 주별 수집/커버리지 개선(반드시 수치·출처)

| Province | Year | AOI ha | Existing verified scenes | New verified scenes | Old valid ha/% | After valid ha/% | Newly recovered ha | Coverage gain %p | Gap reduced % | Still missing ha/% | Esri Clouds % | Esri NoData % | Evidence/Status |
|---|---:|---:|---:|---:|---|---|---:|---:|---:|---|---:|---:|---|
| South Sulawesi | 2020…2025 | null허용 | 실제 값 | 실제 값 | 실측 또는 null | 실측 또는 null | 실측 또는 null | 실측 또는 null | 실측 또는 null | 실측 또는 null | 실측 또는 null | 실측 또는 null | 자산·AOI·마스크 링크 |
| Gorontalo | 2020…2025 | … | … | … | … | … | … | … | … | … | … | … | … |
| Southeast Sulawesi | 2020…2025 | … | … | … | … | … | … | … | … | … | … | … | … | … |
| Banten | 2020…2025 | … | … | … | … | … | … | … | … | … | … | … | … |
| West Java | 2020…2025 | … | … | … | … | … | … | … | … | … | … | … | … |
| East Java | 2020…2025 | … | … | … | … | … | … | … | … | … | … | … | … |

**36개 주·연도 전행 작성.** 실제 수치가 없으면 null 및 그 원인과 다음 획득 작업 기입. 새로운 256×256 AOI 실측치를 주 전체의 coverage로 오기 금지.

## 12.2 보고서 표 B — 학습데이터셋 및 모델 성능 개선

| Model/Experiment | Training Dataset & Version | Test Holdout & Version | Train/Val/Test count | OA | Macro Precision | Macro Recall | Macro F1 | mIoU | Class coverage | Baseline 대비 F1 %p / relative % | Independent? | Repro Evidence |
|---|---|---|---|---:|---:|---:|---:|---:|---|---|---|---|
| Legacy reported (참고용) | 근거를 확인 | 미확정 | 과거 기록 | 1.35% (WorldCover 대비) | null | null | null | 0.27% (WorldCover 대비) | 초지 편향 | N/A | NO | 과거 보고만 |
| Re-evaluated Baseline | 실제 version | 동일 holdout | 실측 | null | null | null | null | null | 실측 | N/A | YES/NO | 실행 로그 |
| Challenger vX | 실제 version | 동일 holdout | 실측 | null | null | null | null | null | 실측 | 비교 가능할 때만 | YES/NO | 체크포인트·해시 |

**이 표의 `null`은 예시이며 실제 평가 전 값이다.** 개선 수치는 동일 시험셋과 정상 평가 분모 확보 후에만 계산. 모델·연도·AOI별 class별 Precision/Recall/F1/IoU, 혼동행렬, CI와 성능퇴화 예외를 별도로 제출하라.

## 12.3 보고서 표 C — 데이터베이스 이관 완료성

| SQLite source/table | Before rows | PostgreSQL target/table | After rows | PK/FK intact | Geometry valid | File refs intact | Null retained | Reconcile status | Evidence |
|---|---:|---|---:|---|---|---|---|---|---|

프로젝트 전체 테이블을 망라하고 불일치 레코드는 이유/재처리 방법/승인자를 남긴다.

---

# 13. 실행 우선순위, 정지 조건 및 최종 보고형식

1. **1차(이관/기준선)**: SQLite snapshot·원장·GeoServer AS-IS → PostGIS 시범 schema/이관 dry-run → baseline 동결·과거 vs 신규 비교 가능성 판단. 실제 DB 이관 실패나 missing source를 숨기지 말 것.
2. **2차(실관측 개선)**: 기존 파일 재사용, 승인된 Banten/West Java 단일 AOI에서 같은 연도 다중시점 영상 확보 → 유효영역 증분 실측 → 1차 GeoServer 지도에서 이전/신규/남은 결측 표시.
3. **3차(모델 검증)**: 데이터셋 적격/클래스/독립 홀드아웃 Gate가 충족된 후에만 정식 학습/재학습. 동일 평가셋 개선 지표 산출. 미충족이면 `BLOCKED`를 유지하고 기술스택/모의계약시험만 진행.
4. **4차(실제 변화탐지)**: 동일 AOI 두 실제 연도에 승인 또는 정확히 표시된 Staging 모델 추론·2차 GeoServer 게시 → 공통 유효영역 변화행렬·지도·통계 실제 정합.
5. **5차(6주 확대/운영 준비)**: 관측량·예산·성능·DB·GeoServer 부하를 실측해 36개 주·연도 전개계획을 확정, 관리형 PostGIS/객체저장소/K8s 또는 근거 있는 대안으로 배포.

## 완료 보고(이 순서로)

- **A. 재현가능한 AS-IS**: branch/commit, SQLite 원장과 파일 현황, 기존 GeoServer/ML 데이터 연결, 확인되지 않은 수치.
- **B. 이관 증거**: PostgreSQL/PostGIS schema, backup hash, row/PK/FK/geometry/data integrity, migration run, API 리그레션, rollback 가능성.
- **C. 수집 전후 개선 수치**: 6개 주·월·연도별 장면 확보와 실제 AOI 신규 복구 ha/%p/잔여 결측, Esri Gap 비교, 각 숫자의 hash·마스크·경계·기간 근거.
- **D. 학습/성능**: dataset 이전/이후, 독립 시험셋, OA/Precision/Recall/F1/mIoU per-class 및 개선 %p/relative%, Model Registry 및 최종 승인 여부.
- **E. GIS·변화분석**: GeoServer 1차/2차 검증, 원본 class_id와 지도/팝업 일치, 두 시점 실제 변화행렬·유효면적.
- **F. 배포**: Dev Compose 실제 기동, Stage/Prod 관련 확인된 환경·구성·보안·백업/복구 테스트, 근거 없는 성공 주장 제외.
- **G. 블로커/승인**: 수집/라이선스/비용/DB/검증라벨/GPU/인프라 각 blocker, owner, 다음 실행명령, 예상비용·위험(견적과 실측 구별).

**절대 완료로 선언하지 말 조건**: `old coverage` 원본 미확보인데 임의 0% 기입; 새 자료가 단순 더 많다는 이유로 결측회복 100% 주장; F1 테스트셋이 달라 비교 불가인데 향상률 주장; SQLite 원본 없이 PostgreSQL 이관 성공 선언; Esri/WorldCover를 자체 추론 또는 독립 정확도라 표기; 과거 GeoServer 합성지도/픽셀없는 화면을 실제 LCLUC 레이어라고 표기; 승인 없는 PROD 전환; 승인 없는 네트워크 우회/고비용 다운로드.

## 참고·기존 자산 확인 항목(프로젝트 내부 우선)

- `GreenBlue_CODEX_LCLUC_6Provinces_CloudGap_MLOps_EndToEnd_v2.0.md`
- `GreenBlue_CODEX_LCLUC_GeoServer_1st_ML_Inference_2nd_ChangeDetection_Repair_v1.1.md`
- `GreenBlue_CODEX_LCLUC_Annual_Map_GeoServer_v1.0.md`
- GMAIS v0.2, TECH-4 및 실제 현재 DB/REST/GeoServer/Model Registry 계약
- Sentinel-2 SCL: `https://sentiwiki.copernicus.eu/web/s2-processing`
- Esri Land Cover Explorer: `https://livingatlas.arcgis.com/landcoverexplorer/`
- PostGIS: `https://postgis.net/documentation/`
- PostgreSQL backup/restore: `https://www.postgresql.org/docs/current/backup.html`
- GeoServer Raster Data: `https://docs.geoserver.org/stable/en/user/data/raster/`

**끝 — v3.0. 이 문서를 실제 리포지토리에서 코드 실행하며 순서대로 적용하고, 각 Gate별 증거와 미완료 사유를 남길 것.**
