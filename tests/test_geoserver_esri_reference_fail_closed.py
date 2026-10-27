"""Regression tests for the quarantined WorldCover-as-Esri legacy path."""

from pathlib import Path
import csv
import json
import sys

import numpy as np
import pytest
import rasterio
from fastapi import FastAPI
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(PROJECT_ROOT / "backend")]

from app.ml.geoserver_primary_layers_manager import (
    ESRI_AUTHORITY_REPORT,
    ESRI_PRIMARY_BLOCK_REASON,
    EVIDENCE_REGISTRY_FIELDNAMES,
    GeoServerPrimaryLayersManager,
    PROVINCE_SPECS,
)
from app.store import Store
from app.tile_router import create_lcluc_tile_router


def _write_raster(path: Path, value: int = 10) -> None:
    spec = PROVINCE_SPECS["banten"]
    path.parent.mkdir(parents=True, exist_ok=True)
    transform = rasterio.transform.from_bounds(*spec["bounds"], 8, 8)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=8,
        height=8,
        count=1,
        dtype="uint8",
        crs=spec["crs"],
        transform=transform,
        nodata=255,
    ) as dataset:
        dataset.write(np.full((8, 8), value, dtype=np.uint8), 1)


def _banten_esri_record(root: Path):
    return next(
        record
        for record in GeoServerPrimaryLayersManager(root).materialize_all()
        if record.province_id == "banten" and record.kind == "esri_reference"
    )


def test_worldcover_source_never_materializes_an_esri_named_artifact(tmp_path: Path):
    root = tmp_path / "data"
    worldcover = root / "first-group-2021" / "banten-2021" / "label-worldcover.tif"
    _write_raster(worldcover)

    record = _banten_esri_record(root)

    assert not (root / "geoserver_layers/primary/banten_2021/esri_reference.tif").exists()
    assert record.evidence_status == "BLOCKED"
    assert record.published_status == "BLOCKED"
    assert record.file_rel_path is None
    assert record.wms_getmap_url is None
    assert record.asset_role == "weak_training_label_pointer_only"
    assert record.authority_report == ESRI_AUTHORITY_REPORT
    assert record.blocked_reason == ESRI_PRIMARY_BLOCK_REASON
    assert record.local_artifact_materialized is False
    assert record.independent_ground_truth is False
    assert record.model_prediction is False


def test_existing_legacy_file_is_quarantined_even_when_authority_report_exists(tmp_path: Path):
    root = tmp_path / "data"
    legacy = root / "geoserver_layers/primary/banten_2021/esri_reference.tif"
    _write_raster(legacy, value=1)
    authority = root / ESRI_AUTHORITY_REPORT
    authority.parent.mkdir(parents=True, exist_ok=True)
    authority.write_text(json.dumps({"scenes": []}), encoding="utf-8")

    record = _banten_esri_record(root)

    assert legacy.is_file()  # The audit guard does not mutate operational data.
    assert record.legacy_artifact_quarantined is True
    assert record.authority_report_present is True
    assert record.local_artifact_materialized is False
    assert record.file_rel_path is None
    assert record.wms_getmap_url is None


def test_retired_private_worldcover_crosswalk_api_raises(tmp_path: Path):
    manager = GeoServerPrimaryLayersManager(tmp_path / "data")
    spec = PROVINCE_SPECS["banten"]
    transform = rasterio.transform.from_bounds(*spec["bounds"], 8, 8)

    with pytest.raises(RuntimeError, match=ESRI_PRIMARY_BLOCK_REASON):
        manager._ensure_esri_reference(
            tmp_path,
            tmp_path / "worldcover.tif",
            transform,
            rasterio.crs.CRS.from_string(spec["crs"]),
            8,
            8,
        )


def test_export_accepts_evidence_registry_schema_and_keeps_esri_rows_pathless(tmp_path: Path):
    root = tmp_path / "data"
    output = tmp_path / "docs"
    output.mkdir()
    csv_path = output / "08_geoserver_1st_2nd_layer_registry.csv"
    secondary = {field: "" for field in EVIDENCE_REGISTRY_FIELDNAMES}
    secondary.update(
        layer_id="lcluc:secondary_fixture",
        stage="2nd_secondary",
        kind="prediction_discrete",
        province_id="banten",
        published_status="BLOCKED",
    )
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=EVIDENCE_REGISTRY_FIELDNAMES)
        writer.writeheader()
        writer.writerow(secondary)

    _, _, exported = GeoServerPrimaryLayersManager(root).export_deliverables(output)

    with exported.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    esri = [row for row in rows if row["kind"] == "esri_reference"]
    assert len(esri) == 6
    assert all(row["published_status"] == "BLOCKED" for row in esri)
    assert all(row["file_rel_path"] == "" for row in esri)
    assert all(row["file_sha256"] == "" for row in esri)
    assert rows[-1]["layer_id"] == "lcluc:secondary_fixture"


@pytest.mark.parametrize(
    "path",
    [
        "/geoserver/wms?SERVICE=WMS&REQUEST=GetMap&LAYERS=lcluc:primary_esri_reference_banten_2021"
        "&BBOX=11800000,-720000,11820000,-700000&WIDTH=256&HEIGHT=256&FORMAT=image/png",
        "/v1/lcluc/pixel?lat=-6.43&lng=106.13&layer=primary_esri_reference_banten_2021",
        "/v1/lcluc/pixel?lat=-6.43&lng=106.13"
        "&layer=geoserver_layers/primary/banten_2021/esri_reference.tif",
        "/v1/lcluc/pixel?lat=-6.43&lng=106.13&layer=esri",
    ],
)
def test_wms_and_pixel_routes_reject_legacy_esri_name_even_if_file_exists(
    tmp_path: Path, path: str
):
    root = tmp_path / "data"
    _write_raster(root / "geoserver_layers/primary/banten_2021/esri_reference.tif", value=1)
    app = FastAPI()
    app.include_router(create_lcluc_tile_router(lambda: Store(root)))

    response = TestClient(app).get(path)

    assert response.status_code == 409
    payload = response.json()
    assert payload["error"]["code"] == "UNVERIFIED_REFERENCE_PROVENANCE"
    assert payload["error"]["retryable"] is False


def test_generic_direct_path_cannot_bypass_authority_report_registration(tmp_path: Path):
    root = tmp_path / "data"
    label = root / "first-group-training-esri-v1/sources/batch/window/label.tif"
    _write_raster(label, value=1)
    app = FastAPI()
    app.include_router(create_lcluc_tile_router(lambda: Store(root)))

    response = TestClient(app).get(
        "/v1/lcluc/pixel?lat=-6.43&lng=106.13"
        "&layer=first-group-training-esri-v1/sources/batch/window/label.tif"
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "UNVERIFIED_REFERENCE_PROVENANCE"
