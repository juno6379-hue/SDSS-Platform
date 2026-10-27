-- Unit 355: normalized PostGIS registry pilot (forward-only, no destructive DDL).
-- Status: IMPLEMENTED_UNVERIFIED. Apply only to an approved pilot database.
BEGIN;

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE SCHEMA IF NOT EXISTS geoai_registry;

CREATE TABLE IF NOT EXISTS geoai_registry.schema_migrations (
    version TEXT CONSTRAINT pk_schema_migrations PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    description TEXT NOT NULL,
    code_status TEXT NOT NULL CONSTRAINT ck_schema_migrations_code_status
        CHECK (code_status IN ('IMPLEMENTED_UNVERIFIED', 'VERIFIED_REAL'))
);

-- Non-domain workflow state is isolated from the nine authoritative entity
-- tables.  The CHECK list prevents arbitrary domain kinds returning to a
-- single catch-all JSONB table.
CREATE TABLE IF NOT EXISTS geoai_registry.operational_records (
    record_id TEXT CONSTRAINT pk_operational_records PRIMARY KEY,
    source_kind TEXT NOT NULL CONSTRAINT ck_operational_source_kind CHECK (source_kind IN (
        'jobs', 'analyses', 'gmais_idempotency', 'gmais_jobs',
        'gmais_results', 'lcluc-workflows', 'mlops_retrain_jobs'
    )),
    source_record_id TEXT NOT NULL,
    created_at TIMESTAMPTZ,
    raw_payload JSONB NOT NULL,
    source_payload_sha256 CHAR(64) NOT NULL CONSTRAINT ck_operational_payload_sha
        CHECK (source_payload_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT uq_operational_source UNIQUE (source_kind, source_record_id)
);

DO $$
DECLARE postgis_major INTEGER;
BEGIN
    SELECT split_part(extversion, '.', 1)::INTEGER INTO postgis_major
      FROM pg_extension WHERE extname = 'postgis';
    IF postgis_major IS NULL OR postgis_major < 3 THEN
        RAISE EXCEPTION 'PostGIS 3 or newer is required';
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS geoai_registry.aois (
    record_id TEXT CONSTRAINT pk_aois PRIMARY KEY,
    source_kind TEXT NOT NULL,
    source_record_id TEXT NOT NULL,
    province_code TEXT,
    boundary_version TEXT,
    geometry geometry(MultiPolygon, 4326),
    area_ha DOUBLE PRECISION CONSTRAINT ck_aois_area CHECK (area_ha IS NULL OR area_ha >= 0),
    area_method_version TEXT,
    legal_boundary_certified BOOLEAN,
    created_at TIMESTAMPTZ,
    raw_payload JSONB NOT NULL,
    source_payload_sha256 CHAR(64) NOT NULL CONSTRAINT ck_aois_payload_sha CHECK (source_payload_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT uq_aois_source UNIQUE (source_kind, source_record_id),
    CONSTRAINT ck_aois_geometry_valid CHECK (geometry IS NULL OR ST_IsValid(geometry))
);

CREATE TABLE IF NOT EXISTS geoai_registry.scenes (
    record_id TEXT CONSTRAINT pk_scenes PRIMARY KEY,
    source_kind TEXT NOT NULL,
    source_record_id TEXT NOT NULL,
    provider TEXT,
    collection_id TEXT,
    acquisition_timestamp TIMESTAMPTZ,
    processing_baseline TEXT,
    footprint geometry(MultiPolygon, 4326),
    scene_cloud_pct DOUBLE PRECISION CONSTRAINT ck_scenes_cloud CHECK (scene_cloud_pct IS NULL OR scene_cloud_pct BETWEEN 0 AND 100),
    status TEXT NOT NULL DEFAULT 'DISCOVERED',
    created_at TIMESTAMPTZ,
    raw_payload JSONB NOT NULL,
    source_payload_sha256 CHAR(64) NOT NULL CONSTRAINT ck_scenes_payload_sha CHECK (source_payload_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT uq_scenes_source UNIQUE (source_kind, source_record_id),
    CONSTRAINT ck_scenes_footprint_valid CHECK (footprint IS NULL OR ST_IsValid(footprint))
);

CREATE TABLE IF NOT EXISTS geoai_registry.datasets (
    record_id TEXT CONSTRAINT pk_datasets PRIMARY KEY,
    source_kind TEXT NOT NULL,
    source_record_id TEXT NOT NULL,
    dataset_id TEXT,
    dataset_version TEXT,
    class_schema_id TEXT,
    boundary_version TEXT,
    mask_policy_version TEXT,
    status TEXT NOT NULL DEFAULT 'BLOCKED',
    learning_ready BOOLEAN,
    created_at TIMESTAMPTZ,
    raw_payload JSONB NOT NULL,
    source_payload_sha256 CHAR(64) NOT NULL CONSTRAINT ck_datasets_payload_sha CHECK (source_payload_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT uq_datasets_source UNIQUE (source_kind, source_record_id)
);

CREATE TABLE IF NOT EXISTS geoai_registry.assets (
    record_id TEXT CONSTRAINT pk_assets PRIMARY KEY,
    source_kind TEXT NOT NULL,
    source_record_id TEXT NOT NULL,
    dataset_record_id TEXT CONSTRAINT fk_assets_dataset REFERENCES geoai_registry.datasets(record_id),
    scene_record_id TEXT CONSTRAINT fk_assets_scene REFERENCES geoai_registry.scenes(record_id),
    asset_role TEXT,
    immutable_uri TEXT,
    sha256 CHAR(64) CONSTRAINT ck_assets_sha CHECK (sha256 IS NULL OR sha256 ~ '^[0-9a-f]{64}$'),
    size_bytes BIGINT CONSTRAINT ck_assets_size CHECK (size_bytes IS NULL OR size_bytes >= 0),
    content_type TEXT,
    crs TEXT,
    affine DOUBLE PRECISION[],
    width INTEGER CONSTRAINT ck_assets_width CHECK (width IS NULL OR width > 0),
    height INTEGER CONSTRAINT ck_assets_height CHECK (height IS NULL OR height > 0),
    nodata_value DOUBLE PRECISION,
    status TEXT NOT NULL DEFAULT 'MISSING_ASSET',
    created_at TIMESTAMPTZ,
    raw_payload JSONB NOT NULL,
    source_payload_sha256 CHAR(64) NOT NULL CONSTRAINT ck_assets_payload_sha CHECK (source_payload_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT uq_assets_source UNIQUE (source_kind, source_record_id)
);

CREATE TABLE IF NOT EXISTS geoai_registry.coverage (
    record_id TEXT CONSTRAINT pk_coverage PRIMARY KEY,
    source_kind TEXT NOT NULL,
    source_record_id TEXT NOT NULL,
    dataset_record_id TEXT CONSTRAINT fk_coverage_dataset REFERENCES geoai_registry.datasets(record_id),
    aoi_record_id TEXT CONSTRAINT fk_coverage_aoi REFERENCES geoai_registry.aois(record_id),
    year SMALLINT CONSTRAINT ck_coverage_year CHECK (year IS NULL OR year BETWEEN 1900 AND 2200),
    month SMALLINT CONSTRAINT ck_coverage_month CHECK (month IS NULL OR month BETWEEN 1 AND 12),
    target_grid_version TEXT,
    mask_policy_version TEXT,
    measurement_status TEXT NOT NULL DEFAULT 'NOT_MEASURED',
    aoi_land_area_ha DOUBLE PRECISION CONSTRAINT ck_coverage_aoi_area CHECK (aoi_land_area_ha IS NULL OR aoi_land_area_ha >= 0),
    valid_area_ha DOUBLE PRECISION CONSTRAINT ck_coverage_valid_area CHECK (valid_area_ha IS NULL OR valid_area_ha >= 0),
    invalid_area_ha DOUBLE PRECISION CONSTRAINT ck_coverage_invalid_area CHECK (invalid_area_ha IS NULL OR invalid_area_ha >= 0),
    newly_recovered_area_ha DOUBLE PRECISION CONSTRAINT ck_coverage_recovered_area CHECK (newly_recovered_area_ha IS NULL OR newly_recovered_area_ha >= 0),
    coverage_pct DOUBLE PRECISION CONSTRAINT ck_coverage_pct CHECK (coverage_pct IS NULL OR coverage_pct BETWEEN 0 AND 100),
    valid_footprint geometry(MultiPolygon, 4326),
    created_at TIMESTAMPTZ,
    raw_payload JSONB NOT NULL,
    source_payload_sha256 CHAR(64) NOT NULL CONSTRAINT ck_coverage_payload_sha CHECK (source_payload_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT uq_coverage_source UNIQUE (source_kind, source_record_id),
    CONSTRAINT ck_coverage_footprint_valid CHECK (valid_footprint IS NULL OR ST_IsValid(valid_footprint))
);

CREATE TABLE IF NOT EXISTS geoai_registry.experiments (
    record_id TEXT CONSTRAINT pk_experiments PRIMARY KEY,
    source_kind TEXT NOT NULL,
    source_record_id TEXT NOT NULL,
    dataset_record_id TEXT CONSTRAINT fk_experiments_dataset REFERENCES geoai_registry.datasets(record_id),
    experiment_id TEXT,
    git_sha CHAR(40),
    random_seed BIGINT,
    training_executed BOOLEAN NOT NULL DEFAULT FALSE,
    status TEXT NOT NULL DEFAULT 'BLOCKED',
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ,
    raw_payload JSONB NOT NULL,
    source_payload_sha256 CHAR(64) NOT NULL CONSTRAINT ck_experiments_payload_sha CHECK (source_payload_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT uq_experiments_source UNIQUE (source_kind, source_record_id)
);

CREATE TABLE IF NOT EXISTS geoai_registry.models (
    record_id TEXT CONSTRAINT pk_models PRIMARY KEY,
    source_kind TEXT NOT NULL,
    source_record_id TEXT NOT NULL,
    experiment_record_id TEXT CONSTRAINT fk_models_experiment REFERENCES geoai_registry.experiments(record_id),
    model_id TEXT,
    model_version TEXT,
    checkpoint_asset_record_id TEXT CONSTRAINT fk_models_checkpoint_asset REFERENCES geoai_registry.assets(record_id),
    class_schema_id TEXT,
    independent_evaluation BOOLEAN NOT NULL DEFAULT FALSE,
    status TEXT NOT NULL DEFAULT 'Draft',
    created_at TIMESTAMPTZ,
    raw_payload JSONB NOT NULL,
    source_payload_sha256 CHAR(64) NOT NULL CONSTRAINT ck_models_payload_sha CHECK (source_payload_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT uq_models_source UNIQUE (source_kind, source_record_id)
);

CREATE TABLE IF NOT EXISTS geoai_registry.predictions (
    record_id TEXT CONSTRAINT pk_predictions PRIMARY KEY,
    source_kind TEXT NOT NULL,
    source_record_id TEXT NOT NULL,
    model_record_id TEXT CONSTRAINT fk_predictions_model REFERENCES geoai_registry.models(record_id),
    dataset_record_id TEXT CONSTRAINT fk_predictions_dataset REFERENCES geoai_registry.datasets(record_id),
    aoi_record_id TEXT CONSTRAINT fk_predictions_aoi REFERENCES geoai_registry.aois(record_id),
    result_id TEXT,
    year SMALLINT CONSTRAINT ck_predictions_year CHECK (year IS NULL OR year BETWEEN 1900 AND 2200),
    prediction_asset_record_id TEXT CONSTRAINT fk_predictions_asset REFERENCES geoai_registry.assets(record_id),
    measured_predictions BOOLEAN NOT NULL DEFAULT FALSE,
    status TEXT NOT NULL DEFAULT 'BLOCKED',
    created_at TIMESTAMPTZ,
    raw_payload JSONB NOT NULL,
    source_payload_sha256 CHAR(64) NOT NULL CONSTRAINT ck_predictions_payload_sha CHECK (source_payload_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT uq_predictions_source UNIQUE (source_kind, source_record_id)
);

CREATE TABLE IF NOT EXISTS geoai_registry.approvals (
    record_id TEXT CONSTRAINT pk_approvals PRIMARY KEY,
    source_kind TEXT NOT NULL,
    source_record_id TEXT NOT NULL,
    subject_type TEXT,
    subject_record_id TEXT,
    decision TEXT NOT NULL DEFAULT 'PENDING' CONSTRAINT ck_approvals_decision
        CHECK (decision IN ('PENDING', 'APPROVED', 'REJECTED', 'REVOKED', 'BLOCKED')),
    approved_by TEXT,
    reason TEXT,
    approved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ,
    raw_payload JSONB NOT NULL,
    source_payload_sha256 CHAR(64) NOT NULL CONSTRAINT ck_approvals_payload_sha CHECK (source_payload_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT uq_approvals_source UNIQUE (source_kind, source_record_id)
);

CREATE INDEX IF NOT EXISTS idx_0355_aoi_geometry ON geoai_registry.aois USING GIST (geometry);
CREATE INDEX IF NOT EXISTS idx_0355_scene_footprint ON geoai_registry.scenes USING GIST (footprint);
CREATE INDEX IF NOT EXISTS idx_0355_scene_time ON geoai_registry.scenes (acquisition_timestamp);
CREATE INDEX IF NOT EXISTS idx_0355_asset_sha ON geoai_registry.assets (sha256);
CREATE UNIQUE INDEX IF NOT EXISTS idx_0355_dataset_identity
    ON geoai_registry.datasets (dataset_id, dataset_version)
    WHERE dataset_id IS NOT NULL AND dataset_version IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_0355_coverage_aoi_year_month ON geoai_registry.coverage (aoi_record_id, year, month);
CREATE INDEX IF NOT EXISTS idx_0355_coverage_footprint ON geoai_registry.coverage USING GIST (valid_footprint);
CREATE INDEX IF NOT EXISTS idx_0355_model_status ON geoai_registry.models (status);
CREATE UNIQUE INDEX IF NOT EXISTS idx_0355_model_identity
    ON geoai_registry.models (model_id, model_version)
    WHERE model_id IS NOT NULL AND model_version IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_0355_prediction_aoi_year ON geoai_registry.predictions (aoi_record_id, year);
CREATE INDEX IF NOT EXISTS idx_0355_approval_subject ON geoai_registry.approvals (subject_type, subject_record_id);

INSERT INTO geoai_registry.schema_migrations(version, description, code_status)
VALUES ('0355', 'Normalized GeoAI PostGIS registry pilot', 'IMPLEMENTED_UNVERIFIED')
ON CONFLICT (version) DO NOTHING;

COMMIT;
