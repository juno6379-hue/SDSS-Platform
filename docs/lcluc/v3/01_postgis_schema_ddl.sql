-- ============================================================================
-- GreenBlue / BIG Climate Action - CODEX LCLUC PostGIS DDL v3.0
-- Standard: UI/GreenBlue_CODEX_LCLUC_PostGIS_Coverage_MLOps_Deployment_Master_v3.0.md
-- ============================================================================

-- 1. Enable Required Extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 2. Domain: Administrative & Analysis AOI Boundaries
CREATE TABLE IF NOT EXISTS provinces (
    province_code VARCHAR(32) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    adm1_pcode VARCHAR(32),
    geom geometry(MultiPolygon, 4326) NOT NULL,
    area_ha NUMERIC(14, 2) NOT NULL,
    boundary_version VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_provinces_geom ON provinces USING GIST (geom);

CREATE TABLE IF NOT EXISTS aoi_boundaries (
    aoi_id VARCHAR(64) PRIMARY KEY,
    province_code VARCHAR(32) NOT NULL REFERENCES provinces(province_code) ON DELETE RESTRICT,
    aoi_name VARCHAR(128) NOT NULL,
    geom geometry(MultiPolygon, 4326) NOT NULL,
    bbox_west NUMERIC(10, 6) NOT NULL,
    bbox_south NUMERIC(10, 6) NOT NULL,
    bbox_east NUMERIC(10, 6) NOT NULL,
    bbox_north NUMERIC(10, 6) NOT NULL,
    land_mask_id VARCHAR(64),
    target_grid_id VARCHAR(32) DEFAULT 'EPSG:3857_10M',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_aoi_boundaries_geom ON aoi_boundaries USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_aoi_boundaries_province ON aoi_boundaries(province_code);

-- 3. Domain: STAC Items & Satellite Scenes
CREATE TABLE IF NOT EXISTS stac_items (
    stac_item_id VARCHAR(128) PRIMARY KEY,
    provider VARCHAR(64) NOT NULL,
    collection VARCHAR(64) NOT NULL,
    province_code VARCHAR(32) REFERENCES provinces(province_code),
    observed_at TIMESTAMPTZ NOT NULL,
    year INT NOT NULL,
    month INT NOT NULL,
    scene_cloud_pct NUMERIC(5, 2),
    footprint_geom geometry(Polygon, 4326) NOT NULL,
    assets_summary JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_stac_items_footprint ON stac_items USING GIST (footprint_geom);
CREATE INDEX IF NOT EXISTS idx_stac_items_ym ON stac_items(year, month);
CREATE INDEX IF NOT EXISTS idx_stac_items_prov ON stac_items(province_code);

-- 4. Domain: Scene Quality & Mask Policies
CREATE TABLE IF NOT EXISTS scene_quality (
    quality_id VARCHAR(128) PRIMARY KEY,
    stac_item_id VARCHAR(128) NOT NULL REFERENCES stac_items(stac_item_id) ON DELETE CASCADE,
    aoi_id VARCHAR(64) REFERENCES aoi_boundaries(aoi_id),
    aoi_cloud_pct NUMERIC(5, 2) NOT NULL,
    aoi_shadow_pct NUMERIC(5, 2) NOT NULL,
    valid_pixel_pct NUMERIC(5, 2) NOT NULL,
    mask_policy_version VARCHAR(32) NOT NULL,
    qc_passed BOOLEAN NOT NULL DEFAULT FALSE,
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_scene_quality_stac ON scene_quality(stac_item_id);

-- 5. Domain: Annual Composites & Multi-temporal Coverage
CREATE TABLE IF NOT EXISTS annual_composites (
    composite_id VARCHAR(128) PRIMARY KEY,
    province_code VARCHAR(32) NOT NULL REFERENCES provinces(province_code),
    year INT NOT NULL,
    composite_method VARCHAR(32) NOT NULL, -- 'SCL_MEDIAN', 'QUALITY_FIRST'
    mask_policy_version VARCHAR(32) NOT NULL,
    total_scenes_blended INT NOT NULL,
    valid_coverage_pct NUMERIC(5, 2) NOT NULL,
    cloud_gap_pct NUMERIC(5, 2) NOT NULL,
    raster_cog_uri TEXT NOT NULL,
    mask_cog_uri TEXT NOT NULL,
    observation_count_uri TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_composite_prov_yr UNIQUE(province_code, year, composite_method, mask_policy_version)
);

CREATE INDEX IF NOT EXISTS idx_annual_composites_prov_yr ON annual_composites(province_code, year);

-- 6. Domain: Reference Products & Labels
CREATE TABLE IF NOT EXISTS reference_products (
    product_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(128) NOT NULL, -- 'ESA_WorldCover', 'Esri_10m_LandCover'
    version VARCHAR(32) NOT NULL,
    release_year INT NOT NULL,
    native_classes INT NOT NULL,
    license VARCHAR(64) NOT NULL,
    citation TEXT
);

CREATE TABLE IF NOT EXISTS label_assets (
    label_asset_id VARCHAR(128) PRIMARY KEY,
    product_id VARCHAR(64) NOT NULL REFERENCES reference_products(product_id),
    province_code VARCHAR(32) NOT NULL REFERENCES provinces(province_code),
    year INT NOT NULL,
    raster_uri TEXT NOT NULL,
    sha256 CHAR(64) NOT NULL,
    coverage_pct NUMERIC(5, 2),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 7. Domain: AI & MLOps Model Registry
CREATE TABLE IF NOT EXISTS model_versions (
    model_id VARCHAR(64) NOT NULL,
    version VARCHAR(32) NOT NULL,
    agency VARCHAR(128) NOT NULL,
    framework VARCHAR(64) NOT NULL DEFAULT 'PyTorch',
    architecture VARCHAR(64) NOT NULL DEFAULT 'UNet',
    status VARCHAR(32) NOT NULL, -- 'Draft', 'Validated', 'Approved', 'Deployed'
    independent_evaluation BOOLEAN NOT NULL DEFAULT FALSE,
    checkpoint_uri TEXT NOT NULL,
    checkpoint_sha256 CHAR(64) NOT NULL,
    macro_f1 NUMERIC(5, 4),
    miou NUMERIC(5, 4),
    deployed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (model_id, version)
);

CREATE INDEX IF NOT EXISTS idx_model_versions_status ON model_versions(status);

CREATE TABLE IF NOT EXISTS model_evaluations (
    eval_id VARCHAR(128) PRIMARY KEY,
    model_id VARCHAR(64) NOT NULL,
    version VARCHAR(32) NOT NULL,
    validation_set_id VARCHAR(64) NOT NULL,
    overall_accuracy NUMERIC(5, 4) NOT NULL,
    precision NUMERIC(5, 4) NOT NULL,
    recall NUMERIC(5, 4) NOT NULL,
    f1_score NUMERIC(5, 4) NOT NULL,
    miou NUMERIC(5, 4) NOT NULL,
    confusion_matrix JSONB NOT NULL,
    per_class_metrics JSONB NOT NULL,
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (model_id, version) REFERENCES model_versions(model_id, version) ON DELETE CASCADE
);

-- 8. Domain: GeoServer Layer Registry
CREATE TABLE IF NOT EXISTS gis_layer_registry (
    layer_id VARCHAR(128) PRIMARY KEY,
    workspace VARCHAR(64) NOT NULL DEFAULT 'lcluc',
    store_name VARCHAR(64) NOT NULL,
    layer_name VARCHAR(128) NOT NULL,
    layer_title VARCHAR(255) NOT NULL,
    source_kind VARCHAR(64) NOT NULL, -- 'ANNUAL_COMPOSITE', 'WORLDCOVER_REF', 'PREDICTION', 'CHANGE_MAP'
    crs VARCHAR(32) NOT NULL DEFAULT 'EPSG:3857',
    footprint_geom geometry(Polygon, 4326),
    wms_endpoint TEXT NOT NULL,
    style_name VARCHAR(64) NOT NULL DEFAULT 'lcluc_discrete_9classes',
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    published_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_gis_layer_footprint ON gis_layer_registry USING GIST (footprint_geom);

-- 9. Domain: Backward Compatible KV Storage (FastAPI Store Bridge)
CREATE TABLE IF NOT EXISTS records (
    kind VARCHAR(64) NOT NULL,
    id VARCHAR(128) NOT NULL,
    body JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (kind, id)
);

CREATE INDEX IF NOT EXISTS idx_records_kind ON records(kind);
CREATE INDEX IF NOT EXISTS idx_records_body ON records USING GIN (body);
