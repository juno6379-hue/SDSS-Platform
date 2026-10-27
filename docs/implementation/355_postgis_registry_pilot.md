# Unit 355 PostGIS Registry 시범 구현

## 쉬운 설명과 현재 상태

Unit 355는 운영 저장소를 PostgreSQL/PostGIS로 바꾸는 작업을 완료한 것이 아니다. 현재 구현은 승인된 별도 DB의 구조를 **읽기 전용으로 검사**하고, 그 구조가 맞더라도 애플리케이션 쓰기를 차단한다. 실제 typed column mapping과 backend-neutral transaction API가 없기 때문이다.

| 범위 | 상태 |
|---|---|
| SQLite 개발 저장소와 명시적 개발 fallback | `TESTED_SYNTHETIC` |
| PostGIS 전체 schema metadata 검사 | `TESTED_SYNTHETIC` |
| 0355 DDL, psycopg v3 연결, 이미지 driver 설치 | `IMPLEMENTED_UNVERIFIED` |
| `postgres-inspect` 읽기 전용 시작 | `TESTED_SYNTHETIC` |
| PostgreSQL CRUD/cutover | `BLOCKED` |
| 실제 DB provisioning·DDL 적용·이관 | `BLOCKED` |

실제 DB 접속, 운영 데이터 이관, 운영 Registry 쓰기는 0건이다.

## 설계와 구현 계약

`migrations/0355_postgis_registry_pilot.sql`은 `geoai_registry` 안에 9개 도메인 테이블과 `schema_migrations`, 제한된 `operational_records`를 선언한다. 모든 PK, source unique, FK, 범위·SHA·공간 유효성 CHECK에 고정 이름을 부여했다. 공간 열은 다음 세 개뿐이며 모두 `geometry(MultiPolygon,4326)`이다.

- `aois.geometry`
- `scenes.footprint`
- `coverage.valid_footprint`

`backend/app/postgis_registry.py`는 DB를 변경하지 않고 다음 metadata를 조회한다.

1. PostGIS extension 버전 3 이상
2. migration `0355`와 `IMPLEMENTED_UNVERIFIED` 상태
3. 11개 테이블의 정확한 열 집합과 PostgreSQL UDT 타입
4. 명명된 PK/unique/FK/CHECK의 종류와 대상 열·참조 테이블 marker
5. index 이름과 table/column/unique/GiST 정의 marker
6. 세 geometry 열의 타입과 SRID

하나라도 다르면 `POSTGIS_SCHEMA_NOT_READY:*`이고 상태는 `BLOCKED`다. 모두 맞아도 schema 상태는 `IMPLEMENTED_UNVERIFIED`이며 실제 쓰기 준비 상태로 승격하지 않는다.

`backend/app/store.py`의 mode는 다음과 같다.

| mode | 동작 |
|---|---|
| `sqlite-dev` | development/test에서만 CRUD 허용 |
| `postgres-inspect` | schema SELECT 검사만 실행; `put/get/list` 모두 `POSTGRES_INSPECTION_READ_ONLY` |
| `postgres` | schema가 맞아도 `POSTGRES_CUTOVER_BLOCKED`로 시작 차단 |

PostgreSQL 연결은 psycopg v3만 사용하고 `default_transaction_read_only=on`을 강제한다. 모든 연결은 명시적으로 `close()`한다. DSN·driver 원문이 traceback chain에 남지 않도록 외부 예외 원인을 숨기고 고정 오류 코드만 반환한다. 개발 fallback은 `development`와 명시적 opt-in이 모두 있을 때만 가능하며 상태는 `DEGRADED_DEV_FALLBACK`이다.

## 설정과 API 사용법

로컬 개발:

```powershell
$env:GEOAI_ENVIRONMENT = 'development'
$env:GEOAI_STORAGE_MODE = 'sqlite-dev'
```

승인된 별도 DB의 구조만 검사:

```powershell
$env:GEOAI_ENVIRONMENT = 'staging'
$env:GEOAI_STORAGE_MODE = 'postgres-inspect'
$env:POSTGRES_DSN = '<secret supplied outside logs>'
```

`Store.storage_status()`의 inspection 결과는 `status=BLOCKED_POSTGRES_INSPECTION_ONLY`, `active_backend=postgres-inspect`, `writable=false`다. `schema_health.status=IMPLEMENTED_UNVERIFIED`는 DDL 호환성 결과일 뿐 cutover 승인이나 실운영 검증이 아니다.

`postgres` mode는 현재 의도적으로 시작하지 않는다. typed mapping과 transaction API가 구현·시험되기 전에 이 차단을 해제해서는 안 된다.

Docker image는 core requirements 뒤 `psycopg[binary]>=3.2,<4`를 명시적으로 설치한다. `requirements-optional.txt`와 같은 major 계약이다.

## SQLite snapshot dry-run

```powershell
Set-Location backend
python -m app.postgis_reconcile E:\approved-snapshots\catalog.sqlite3 > reconcile-0355.json
```

입력은 서비스가 닫힌 별도 snapshot이어야 한다. 도구는 `mode=ro&immutable=1`로 열고 다음을 fail-closed로 검사한다.

- 64 MiB/100,000행/JSON 8 MiB 상한과 정확한 `records(kind,id,body)` schema
- 시작 전 `-wal`/`-shm` sidecar 부재
- 읽기 전후 크기·mtime·전체 SHA-256 동일성과 종료 후 sidecar 부재
- JSON object, canonical round-trip, NULL, timezone-aware `*_at`, source ID
- entity별 허용 geometry field
- AOI/Scene/Coverage geometry의 정확한 MultiPolygon nesting, 4점 이상 ring, 닫힌 ring, 유한 EPSG:4326 좌표
- source/projected 행 수와 명시 kind mapping

Point나 Polygon은 좌표가 정상이어도 차단한다. 이 검사는 GeoJSON 구조 검사이며 실제 PostGIS `ST_IsValid` 검사를 대신하지 않는다.

## 시험 근거

2026-10-21 KST 집중 시험:

```text
python -m pytest tests/test_postgis_registry.py tests/test_postgis_reconcile.py tests/test_store_fail_closed.py -q
20 passed in 2.56s
```

Root의 health 상태 매핑을 포함한 API 회귀:

```text
python -m pytest tests/test_postgis_registry.py tests/test_postgis_reconcile.py tests/test_store_fail_closed.py tests/test_api.py -q
35 passed, 2 subtests passed, 1 warning in 18.80s
```

별도 대표 Store 소비자 회귀는 61 passed, 15 subtests passed였다. 경고 45건은 기존 rasterio pending-deprecation과 Starlette/httpx deprecation이다.

검증에는 schema 열 타입/제약/SRID/index 누락, 잘못된 geometry type/open ring, WAL/SHM, snapshot 동시변경, 명시적 connection close, secret traceback 억제, PostgreSQL writable cutover 차단이 포함된다. 시험은 합성 fixture와 임시 SQLite만 사용했다.

## 남은 차단과 인계

- 실제 PostgreSQL에서 DDL 문법·권한·extension·transaction·index 실행은 아직 검증하지 않았다.
- 현재 metadata 검사는 제약 종류·대상 열과 index 정의 marker까지 확인한다. CHECK 수식 전체의 의미 동등성까지 증명하지 않으므로 승인 전 실제 catalog 정의와 0355 DDL의 별도 DBA diff가 필요하다.
- `Store.connect()`로 SQLite SQL을 직접 쓰는 기존 모듈을 backend-neutral transaction API로 바꿔야 한다.
- 9개 entity의 legacy payload를 typed columns로 옮기는 명시적 mapping, 역직렬화, FK 순서, rollback 시험이 필요하다.
- 운영 snapshot audit, 실제 DB 이관, cutover, 서비스 재시작은 별도 승인 대상이며 이번 작업에서 수행하지 않았다.
