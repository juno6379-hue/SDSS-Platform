"""Unit & Integration Tests for G6 GeoServer Primary Spatial Layer Integration.

Tests:
1. Materialization of 42 primary spatial layers across 6 provinces (6 x 7)
2. Manifest and registry deliverables generation
3. WMS 1.3.0 / 1.1.1 GetMap endpoint for primary layers (Nearest-Neighbor, image/png)
4. Authoritative 1x1 pixel query endpoint for primary layers
5. NoData transparency and discrete value preservation
"""
from pathlib import Path
import sys

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(PROJECT_ROOT / "backend")]

from app.ml.geoserver_primary_layers_manager import (
    GeoServerPrimaryLayersManager,
    PRIMARY_LAYER_KINDS,
    PROVINCE_SPECS,
)
from app.store import Store
from app.tile_router import create_lcluc_tile_router


@pytest.fixture(scope="module")
def data_root() -> Path:
    return PROJECT_ROOT / "data"


@pytest.fixture(scope="module")
def primary_manager(data_root: Path) -> GeoServerPrimaryLayersManager:
    return GeoServerPrimaryLayersManager(data_root)


@pytest.fixture(scope="module")
def tile_client(data_root: Path) -> TestClient:
    app = FastAPI()
    store = Store(data_root)
    app.include_router(create_lcluc_tile_router(lambda: store))
    return TestClient(app)


def test_materialize_all_generates_54_layers(primary_manager: GeoServerPrimaryLayersManager):
    registry = primary_manager.materialize_all()
    assert len(registry) == 54
    assert len(PROVINCE_SPECS) == 6
    assert len(PRIMARY_LAYER_KINDS) == 9

    provinces = {r.province_id for r in registry}
    assert provinces == set(PROVINCE_SPECS.keys())

    kinds = {r.kind for r in registry}
    assert kinds == set(PRIMARY_LAYER_KINDS)
    assert "annual_valid_mask" in kinds
    assert "newly_recovered_mask" in kinds
    assert "still_missing_mask" in kinds


def test_primary_layer_geotiff_integrity(data_root: Path):
    import rasterio

    for prov_id, spec in PROVINCE_SPECS.items():
        prov_dir = data_root / "geoserver_layers" / "primary" / f"{prov_id}_{spec['default_year']}"
        assert prov_dir.is_dir()

        comp_tif = prov_dir / "coverage_comparison.tif"
        assert comp_tif.is_file()
        with rasterio.open(comp_tif) as ds:
            assert ds.width == 256
            assert ds.height == 256
            assert ds.crs.to_string() == spec["crs"]
            data = ds.read(1)
            # Distinct recovery classes: 1 (Baseline Valid), 2 (Newly Recovered), 3 (Still Missing)
            unique_vals = set(data.flatten())
            assert 1 in unique_vals or 2 in unique_vals

        recov_tif = prov_dir / "newly_recovered_mask.tif"
        assert recov_tif.is_file()
        with rasterio.open(recov_tif) as ds:
            assert ds.width == 256
            assert ds.height == 256
            assert ds.nodata == 255

        missing_tif = prov_dir / "still_missing_mask.tif"
        assert missing_tif.is_file()
        with rasterio.open(missing_tif) as ds:
            assert ds.width == 256
            assert ds.height == 256
            assert ds.nodata == 255


def test_wms_getmap_primary_layers(tile_client: TestClient):
    # Test Banten coverage comparison GetMap
    resp = tile_client.get(
        "/geoserver/wms?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap"
        "&LAYERS=primary_coverage_comparison_banten_2021"
        "&SRS=EPSG:3857&BBOX=11800000,-720000,11820000,-700000"
        "&WIDTH=256&HEIGHT=256&FORMAT=image/png"
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert len(resp.content) > 500

    # Test West Java observation count GetMap
    resp2 = tile_client.get(
        "/geoserver/wms?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap"
        "&LAYERS=primary_observation_count_west_java_2021"
        "&SRS=EPSG:3857&BBOX=11970000,-780000,11990000,-760000"
        "&WIDTH=256&HEIGHT=256&FORMAT=image/png"
    )
    assert resp2.status_code == 200
    assert resp2.headers["content-type"] == "image/png"

    # Test Banten newly_recovered_mask GetMap
    resp3 = tile_client.get(
        "/geoserver/wms?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap"
        "&LAYERS=primary_newly_recovered_mask_banten_2021"
        "&SRS=EPSG:3857&BBOX=11800000,-720000,11820000,-700000"
        "&WIDTH=256&HEIGHT=256&FORMAT=image/png"
    )
    assert resp3.status_code == 200
    assert resp3.headers["content-type"] == "image/png"

    # Test Banten still_missing_mask GetMap
    resp4 = tile_client.get(
        "/geoserver/wms?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap"
        "&LAYERS=primary_still_missing_mask_banten_2021"
        "&SRS=EPSG:3857&BBOX=11800000,-720000,11820000,-700000"
        "&WIDTH=256&HEIGHT=256&FORMAT=image/png"
    )
    assert resp4.status_code == 200
    assert resp4.headers["content-type"] == "image/png"


def test_authoritative_pixel_query_primary_layer(tile_client: TestClient):
    resp = tile_client.get(
        "/v1/lcluc/pixel?lat=-6.43&lng=106.13&layer=primary_coverage_comparison_banten_2021"
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert "class_id" in payload
    assert "provenance" in payload
    assert payload["provenance"]["inspection_method"] == "direct_geotiff_window_read_zero_screen_guessing"
    assert payload["provenance"]["kind"] == "coverage_comparison"

    # Test newly recovered mask pixel inspection
    resp_rec = tile_client.get(
        "/v1/lcluc/pixel?lat=-6.43&lng=106.13&layer=primary_newly_recovered_mask_banten_2021"
    )
    assert resp_rec.status_code == 200
    payload_rec = resp_rec.json()
    assert "class_id" in payload_rec
    assert payload_rec["provenance"]["kind"] == "newly_recovered_mask"


def test_export_deliverables(primary_manager: GeoServerPrimaryLayersManager, tmp_path: Path):
    manifest_f, report_f, csv_f = primary_manager.export_deliverables(tmp_path)
    assert manifest_f.is_file() and manifest_f.stat().st_size > 1000
    assert report_f.is_file() and report_f.stat().st_size > 1000
    assert csv_f.is_file() and csv_f.stat().st_size > 1000
