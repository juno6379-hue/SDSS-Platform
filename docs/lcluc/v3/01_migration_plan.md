# G1 SQLite → PostgreSQL/PostGIS Migration Plan

**Standard**: `GreenBlue_CODEX_LCLUC_PostGIS_Coverage_MLOps_Deployment_Master_v3.0.md` (Section 3)  
**Source Database**: `data/catalog.sqlite3` (155,648 bytes, SHA256: `7c5068be8f430c7cbe10badd9ce7bbf4df94a5045fad788682c96fcb20867b1b`)  
**Target Database**: PostgreSQL 16 + PostGIS 3.4  
**Status**: `MIGRATION_PLAN_PROVISIONED`

---

## 1. Migration Overview & Strategy

The SDSS-Platform stores its catalog in `data/catalog.sqlite3`.
Under G1, we provision a dual-adapter migration model:
1. **Compatibility Layer (`records` Table in PostGIS)**:
   - Stores `(kind, id, body)` with PostgreSQL native `JSONB` and `GIN` indexing.
   - Provides 100% transparent zero-code-break migration for FastAPI `Store.put`, `Store.get`, `Store.list`.
2. **Normalized Geodatabase Tables**:
   - `provinces`, `aoi_boundaries`, `stac_items`, `scene_quality`, `annual_composites`, `model_versions`, `model_evaluations`, `gis_layer_registry`.
   - Populated from existing registered models and catalog datasets.
3. **Fail-Closed Fallback**:
   - If `POSTGRES_DSN` is not provided in environment, `Store` safely operates in local SQLite mode without crashing.
   - When `POSTGRES_DSN` is configured and reachable, `Store` automatically routes transactions to PostgreSQL/PostGIS.

---

## 2. Table & Column Mapping Specification

| SQLite Source Table | SQLite Columns | PostGIS Target Table | PostGIS Columns | Transformation / Validation |
|---|---|---|---|---|
| `records` | `kind` (TEXT) | `records` | `kind` (VARCHAR(64)) | Direct string copy |
| `records` | `id` (TEXT) | `records` | `id` (VARCHAR(128)) | Direct string copy |
| `records` | `body` (TEXT) | `records` | `body` (JSONB) | `json.loads` validate $\to$ JSONB syntax check |
| `records` (`kind='models'`) | `body->model_id` | `model_versions` | `model_id` | Extract from JSON |
| `records` (`kind='models'`) | `body->version` | `model_versions` | `version` | Extract from JSON |
| `records` (`kind='models'`) | `body->status` | `model_versions` | `status` | Extract from JSON |
| `records` (`kind='models'`) | `body->checkpoint_path` | `model_versions` | `checkpoint_uri` | Relative path validation |
| `first-group-provinces.geojson` | `features` | `provinces` | `geom` (MultiPolygon, 4326) | `ST_GeomFromGeoJSON`, `ST_IsValid` check |

---

## 3. Data Integrity & Verification Constraints

1. **Row Count Reconciliation**:
   - Source SQLite count must exactly match migrated target count:
     $$\Delta_{\text{rows}} = N_{\text{PostGIS}} - N_{\text{SQLite}} = 0$$
2. **Payload Checksum Consistency**:
   - For every migrated `(kind, id)`, the normalized canonical JSON SHA-256 in PostGIS must match the source payload hash.
3. **Geometry Validation**:
   - All spatial boundaries must pass `ST_IsValid(geom) = true`.
   - SRID must be explicitly set to `4326`.
   - Bounding boxes must not invert longitude/latitude coordinates.
4. **Idempotency**:
   - Multiple executions of the migration script must execute idempotent upserts (`ON CONFLICT (kind, id) DO UPDATE`) without duplicate record generation.

---

## 4. Rollback Drill

If the migration fails at any stage:
1. Active write transactions are rolled back atomically via standard PostgreSQL transactional DDL.
2. The read-only SQLite database remains unmodified and untouched.
3. Application traffic defaults immediately to SQLite mode.
