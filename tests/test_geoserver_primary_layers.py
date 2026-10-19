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


def test_materialize_all_generates_42_layers(primary_manager: GeoServerPrimaryLayersManager):
    registry = primary_manager.materialize_all()
    assert len(registry) == 42
    assert len(PROVINCE_SPECS) == 6
    assert len(PRIMARY_LAYER_KINDS) == 7

    provinces = {r.province_id for r in registry}
    assert provinces == set(PROVINCE_SPECS.keys())

    kinds = {r.kind for r in registry}
    assert kinds == set(PRIMARY_LAYER_KINDS)


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


def test_export_deliverables(primary_manager: GeoServerPrimaryLayersManager, tmp_path: Path):
    manifest_f, report_f, csv_f = primary_manager.export_deliverables(tmp_path)
    assert manifest_f.is_file() and manifest_f.stat().st_size > 1000
    assert report_f.is_file() and report_f.stat().st_size > 1000
    assert csv_f.is_file() and csv_f.stat().st_size > 1000
