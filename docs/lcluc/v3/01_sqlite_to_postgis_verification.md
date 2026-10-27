# G1 SQLite → PostgreSQL/PostGIS 검증 상태 교정

상태: `IMPLEMENTED_UNVERIFIED` / `BLOCKED_NO_POSTGIS_PILOT_EXECUTION`

기존 문서의 `STANDALONE_DRY_RUN_VERIFIED`, `100% MATCH`, `11 tables provisioned`, 자동 dual-mode·zero-downtime 보장은 실제 PostgreSQL/PostGIS 연결, DDL 적용, backfill, reconcile 증거 없이 작성되어 철회한다. 당시 14행은 현재 운영 catalog 전체 상태도 아니다.

## 현재 구현 범위

Unit355는 다음 코드와 계약만 구현했다.

- `migrations/0355_postgis_registry_pilot.sql`: 11개 테이블, 명명된 제약조건·인덱스·MultiPolygon/SRID4326 DDL
- `backend/app/postgis_registry.py`: psycopg v3 기반 registry adapter
- `backend/app/postgis_reconcile.py`: SQLite read-only snapshot과 PostGIS pilot schema/reconcile 검사
- `backend/app/store.py`: `sqlite-dev`, `postgres-inspect`, `postgres` 모드의 실패폐쇄 선택

`postgres-inspect`는 조회 전용이며 put/get/list를 차단한다. writable `postgres`는 승인된 cutover가 없으므로 항상 `POSTGRES_CUTOVER_BLOCKED`다. DSN과 traceback은 응답에 노출하지 않는다.

## 검증한 것

- 임시 fixture에서 DDL parser·schema inspection·reconcile·오류 차단: `TESTED_SYNTHETIC`
- SQLite snapshot을 WAL/SHM 확인 후 read-only·immutable 방식으로 읽고 전후 size/mtime/SHA 비교: 구현 및 fixture 시험 완료
- API health가 PostgreSQL inspection-only를 `blocked`, SQLite fallback을 `degraded`로 표시: 시험 완료

## 검증하지 않은 것

- 실제 PostgreSQL/PostGIS 서버 연결: `BLOCKED`
- DDL 실제 적용 및 PostGIS extension 확인: `BLOCKED`
- 현재 SQLite 29행의 typed backfill/reconcile: `BLOCKED`
- dual-write, read switch, cutover, rollback drill: `BLOCKED`
- 운영 성능·고가용성·zero downtime: `BLOCKED`

실제 pilot은 별도 승인된 DB, 고정 DSN, DDL SHA, SQLite snapshot SHA, before/after reconcile 결과를 갖춰야 한다. 그 전에는 `provisioned`, `parity`, `migration complete`를 사용하지 않는다.

상세 계약과 시험 근거는 `docs/implementation/355_postgis_registry_pilot.md`에 기록한다.
