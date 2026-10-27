"""Focused tests for fail-closed G6 primary-layer materialization.

All raster writes use pytest temporary directories. FastAPI TestClient checks
exercise only the local compatibility router and do not count as external
GeoServer publication or GetCapabilities named-layer verification.
"""

import csv
import json
from pathlib import Path
import sys

import numpy as np
import pytest
import rasterio
from fastapi import FastAPI
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(PROJECT_ROOT / "backend")]

from app.ml.geoserver_primary_layers_manager import (
    G5_LINEAGE_LAYER_KINDS,
    GeoServerPrimaryLayersManager,
    PRIMARY_LAYER_KINDS,
    PROVINCE_SPECS,
    REGISTRY_FIELDNAMES,
)
from app.store import Store
from app.tile_router import create_lcluc_tile_router


def _write_raster(path: Path, data: np.ndarray, spec: dict, *, nodata: int = 0) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if data.ndim == 2:
        data = data[np.newaxis, :, :]
    _, height, width = data.shape
    transform = rasterio.transform.from_bounds(*spec["bounds"], width, height)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=width,
        height=height,
        count=data.shape[0],
        dtype=data.dtype,
        crs=spec["crs"],
        transform=transform,
        nodata=nodata,
        compress="deflate",
    ) as dst:
        dst.write(data)


def _prepare_input_sources(data_root: Path) -> None:
    for prov_id, spec in PROVINCE_SPECS.items():
        src_dir = data_root / "first-group-2021" / f"{prov_id}-2021"
        image = np.full((3, 16, 16), 100, dtype=np.uint16)
        quality = np.ones((16, 16), dtype=np.uint8)
        quality[:2, :2] = 0
        worldcover = np.full((16, 16), 10, dtype=np.uint8)
        _write_raster(src_dir / "image.tif", image, spec)
        _write_raster(src_dir / "quality-mask.tif", quality, spec, nodata=255)
        _write_raster(src_dir / "label-worldcover.tif", worldcover, spec, nodata=255)


@pytest.fixture(scope="module")
def data_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("g6-primary") / "data"
    _prepare_input_sources(root)
    return root


@pytest.fixture(scope="module")
def primary_manager(data_root: Path) -> GeoServerPrimaryLayersManager:
    return GeoServerPrimaryLayersManager(data_root, allow_synthetic_fixtures=True)


@pytest.fixture(scope="module")
def materialized_registry(primary_manager: GeoServerPrimaryLayersManager):
    return primary_manager.materialize_all()


@pytest.fixture(scope="module")
def tile_client(data_root: Path, materialized_registry) -> TestClient:
    app = FastAPI()
    store = Store(data_root)
    app.include_router(create_lcluc_tile_router(lambda: store))
    return TestClient(app)


def test_default_mode_blocks_unverified_g5_materialization(tmp_path: Path):
    root = tmp_path / "data"
    _prepare_input_sources(root)

    registry = GeoServerPrimaryLayersManager(root).materialize_all()

    assert len(registry) == 54
    g5_records = [record for record in registry if record.kind in G5_LINEAGE_LAYER_KINDS]
    assert len(g5_records) == 24
    assert all(record.evidence_status == "BLOCKED" for record in g5_records)
    assert all(record.published_status == "BLOCKED" for record in g5_records)
    assert all(record.source_lineage_verified is False for record in g5_records)
    assert all(record.synthetic_fixture is None for record in g5_records)
    assert all(record.local_artifact_materialized is False for record in g5_records)
    assert all(record.source_product == "MISSING - VERIFIED G5 LINEAGE REQUIRED" for record in g5_records)

    for prov_id, spec in PROVINCE_SPECS.items():
        prov_dir = root / "geoserver_layers" / "primary" / f"{prov_id}_{spec['default_year']}"
        for kind in G5_LINEAGE_LAYER_KINDS:
            assert not (prov_dir / f"{kind}.tif").exists()


def test_default_mode_with_no_sources_materializes_no_synthetic_fallbacks(tmp_path: Path):
    root = tmp_path / "data"

    registry = GeoServerPrimaryLayersManager(root).materialize_all()

    assert len(registry) == 54
    assert all(record.evidence_status == "BLOCKED" for record in registry)
    assert all(record.published_status == "BLOCKED" for record in registry)
    assert all(record.synthetic_fixture is None for record in registry)
    assert all(record.local_artifact_materialized is False for record in registry)
    assert list((root / "geoserver_layers" / "primary").rglob("*.tif")) == []


def test_default_mode_recognizes_existing_tagged_g5_fixtures(tmp_path: Path):
    root = tmp_path / "data"
    _prepare_input_sources(root)
    GeoServerPrimaryLayersManager(root, allow_synthetic_fixtures=True).materialize_all()

    registry = GeoServerPrimaryLayersManager(root).materialize_all()
    g5_records = [record for record in registry if record.kind in G5_LINEAGE_LAYER_KINDS]

    assert len(g5_records) == 24
    assert all(record.evidence_status == "TESTED_SYNTHETIC" for record in g5_records)
    assert all(record.synthetic_fixture is True for record in g5_records)
    assert all(record.source_lineage_verified is False for record in g5_records)
    assert all(record.published_status == "BLOCKED" for record in g5_records)


def test_untagged_existing_g5_artifact_remains_unknown_and_blocked(tmp_path: Path):
    root = tmp_path / "data"
    spec = PROVINCE_SPECS["banten"]
    artifact = root / "geoserver_layers" / "primary" / "banten_2021" / "coverage_comparison.tif"
    _write_raster(artifact, np.ones((16, 16), dtype=np.uint8), spec, nodata=255)

    registry = GeoServerPrimaryLayersManager(root).materialize_all()
    record = next(
        item
        for item in registry
        if item.province_id == "banten" and item.kind == "coverage_comparison"
    )

    assert record.local_artifact_materialized is True
    assert record.evidence_status == "BLOCKED"
    assert record.synthetic_fixture is None
    assert record.source_lineage_verified is False
    assert record.source_product == "UNVERIFIED LOCAL ARTIFACT - G5 LINEAGE NOT VERIFIED"


def test_synthetic_fixture_mode_is_explicit_and_never_published(materialized_registry):
    assert len(materialized_registry) == 54
    assert len(PROVINCE_SPECS) == 6
    assert len(PRIMARY_LAYER_KINDS) == 9
    assert {record.province_id for record in materialized_registry} == set(PROVINCE_SPECS)
    assert {record.kind for record in materialized_registry} == set(PRIMARY_LAYER_KINDS)
    assert all(record.external_publication_verified is False for record in materialized_registry)
    assert all(record.getcapabilities_named_listing_verified is False for record in materialized_registry)
    assert all(record.published_status != "PUBLISHED_ONLINE" for record in materialized_registry)

    fixtures = [record for record in materialized_registry if record.kind in G5_LINEAGE_LAYER_KINDS]
    assert len(fixtures) == 24
    assert all(record.evidence_status == "TESTED_SYNTHETIC" for record in fixtures)
    assert all(record.synthetic_fixture is True for record in fixtures)
    assert all(record.source_lineage_verified is False for record in fixtures)
    assert all(record.published_status == "BLOCKED" for record in fixtures)
    assert all(record.source_product == "TEST FIXTURE - NO VERIFIED G5 LINEAGE" for record in fixtures)

    esri_slots = [record for record in materialized_registry if record.kind == "esri_reference"]
    assert len(esri_slots) == 6
    assert all(record.evidence_status == "BLOCKED" for record in esri_slots)
    assert all(record.file_rel_path is None for record in esri_slots)
    assert all(record.wms_getmap_url is None for record in esri_slots)

    source_backed = [
        record
        for record in materialized_registry
        if record.kind not in G5_LINEAGE_LAYER_KINDS | {"esri_reference"}
    ]
    assert len(source_backed) == 24
    assert all(record.evidence_status == "IMPLEMENTED_UNVERIFIED" for record in source_backed)
    assert all(record.synthetic_fixture is False for record in source_backed)


def test_synthetic_geotiffs_carry_provenance_tags(data_root: Path, materialized_registry):
    for prov_id, spec in PROVINCE_SPECS.items():
        prov_dir = data_root / "geoserver_layers" / "primary" / f"{prov_id}_{spec['default_year']}"
        for kind in G5_LINEAGE_LAYER_KINDS:
            path = prov_dir / f"{kind}.tif"
            assert path.is_file()
            with rasterio.open(path) as dataset:
                assert dataset.width == 16
                assert dataset.height == 16
                assert dataset.crs.to_string() == spec["crs"]
                tags = dataset.tags()
                assert tags["evidence_status"] == "TESTED_SYNTHETIC"
                assert tags["synthetic_fixture"] == "true"
                assert tags["source_lineage_verified"] == "false"


def test_local_testclient_getmap_does_not_imply_external_publication(
    tile_client: TestClient, materialized_registry
):
    response = tile_client.get(
        "/geoserver/wms?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap"
        "&LAYERS=primary_coverage_comparison_banten_2021"
        "&SRS=EPSG:3857&BBOX=11800000,-720000,11820000,-700000"
        "&WIDTH=256&HEIGHT=256&FORMAT=image/png"
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert len(response.content) > 500

    record = next(
        item
        for item in materialized_registry
        if item.province_id == "banten" and item.kind == "coverage_comparison"
    )
    assert record.evidence_status == "TESTED_SYNTHETIC"
    assert record.external_publication_verified is False
    assert record.getcapabilities_named_listing_verified is False


def test_local_direct_pixel_query_keeps_fixture_status_visible(
    tile_client: TestClient, materialized_registry
):
    response = tile_client.get(
        "/v1/lcluc/pixel?lat=-6.43&lng=106.13&layer=primary_coverage_comparison_banten_2021"
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["provenance"]["inspection_method"] == "direct_geotiff_window_read_zero_screen_guessing"
    assert payload["provenance"]["kind"] == "coverage_comparison"

    record = next(
        item
        for item in materialized_registry
        if item.province_id == "banten" and item.kind == "coverage_comparison"
    )
    assert record.synthetic_fixture is True
    assert record.published_status == "BLOCKED"


def _secondary_rows() -> list[dict[str, str]]:
    rows = []
    for index in range(18):
        rows.append(
            {
                "layer_id": f"lcluc:secondary_fixture_{index:02d}",
                "stage": "2nd_secondary",
                "kind": "prediction_discrete",
                "province_id": "banten",
                "province_name": "Banten",
                "year": "2021",
                "crs": "EPSG:32748",
                "file_rel_path": f"geoserver_layers/secondary/fixture_{index:02d}.tif",
                "width": "16",
                "height": "16",
                "nodata_value": "255",
                "resampling": "nearest",
                "colormap_style": "lcluc_discrete_9classes",
                "source_product": "preserved-secondary-fixture",
                "license": "test-only",
                "published_status": "BLOCKED",
                "wms_getmap_url": f"http://example.invalid/fixture/{index:02d}",
            }
        )
    return rows


def test_export_is_fail_closed_and_preserves_secondary_rows(
    primary_manager: GeoServerPrimaryLayersManager, tmp_path: Path
):
    csv_path = tmp_path / "08_geoserver_1st_2nd_layer_registry.csv"
    expected_secondary = _secondary_rows()
    with open(csv_path, "w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=REGISTRY_FIELDNAMES)
        writer.writeheader()
        writer.writerows(expected_secondary)

    manifest_path, report_path, exported_csv = primary_manager.export_deliverables(tmp_path)
    # A repeated export replaces primary rows and must not append secondary rows again.
    primary_manager.export_deliverables(tmp_path)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["evidence_status"] == "TESTED_SYNTHETIC"
    assert manifest["g5_source_lineage_verified"] is False
    assert manifest["external_publication_verified"] is False
    assert manifest["getcapabilities_named_listing_verified"] is False
    assert manifest["publication_status"] == "BLOCKED_NO_EXTERNAL_PUBLICATION_VERIFICATION"
    assert manifest["total_layers"] == 54
    assert manifest["preserved_non_primary_layers"] == 18
    assert manifest["combined_registry_total_layers"] == 72

    with open(exported_csv, newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 72
    assert [row for row in rows if row["stage"] == "2nd_secondary"] == expected_secondary
    assert len([row for row in rows if row["stage"] == "1st_primary"]) == 54
    assert all(row["published_status"] != "PUBLISHED_ONLINE" for row in rows[:54])

    report = report_path.read_text(encoding="utf-8")
    assert "BLOCKED_NO_EXTERNAL_PUBLICATION_VERIFICATION" in report
    assert "GetCapabilities 명명 레이어 검증**: `NOT_CHECKED`" in report
    assert "PUBLISHED_ONLINE" not in report
    assert "HTTP 200 OK" not in report


def test_export_rejects_registry_schema_drift(primary_manager: GeoServerPrimaryLayersManager, tmp_path: Path):
    csv_path = tmp_path / "08_geoserver_1st_2nd_layer_registry.csv"
    csv_path.write_text("layer_id,stage\nbroken,2nd_secondary\n", encoding="utf-8")

    with pytest.raises(ValueError, match="schema"):
        primary_manager.export_deliverables(tmp_path)


def test_export_rejects_preserved_non_primary_id_collision(
    primary_manager: GeoServerPrimaryLayersManager, tmp_path: Path
):
    csv_path = tmp_path / "08_geoserver_1st_2nd_layer_registry.csv"
    rows = _secondary_rows()
    rows[0]["layer_id"] = "lcluc:primary_sentinel2_composite_banten_2021"
    with open(csv_path, "w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=REGISTRY_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    with pytest.raises(ValueError, match="collides with primary replacement"):
        primary_manager.export_deliverables(tmp_path)
