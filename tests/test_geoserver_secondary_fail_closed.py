import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

from app.ml.geoserver_primary_layers_manager import PROVINCE_SPECS
from app.ml.geoserver_secondary_and_change_manager import (
    GeoServerSecondaryAndChangeManager, SECONDARY_KINDS,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tif(path: Path, values: np.ndarray, *, nodata: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(
        path, "w", driver="GTiff", width=values.shape[1], height=values.shape[0],
        count=1, dtype="uint8", crs="EPSG:32748", transform=from_origin(100, 200, 10, 10),
        nodata=nodata,
    ) as dataset:
        dataset.write(values.astype("uint8"), 1)


def _evidence(root: Path, province_id: str = "banten", *, publish: bool = True) -> Path:
    year = PROVINCE_SPECS[province_id]["default_year"]
    relative_dir = Path("geoserver_layers") / "secondary" / f"{province_id}_{year}"
    paths = {
        "prediction_discrete": root / relative_dir / "prediction_discrete.tif",
        "prediction_confidence": root / relative_dir / "prediction_confidence.tif",
        "prediction_valid_mask": root / relative_dir / "prediction_valid_mask.tif",
    }
    prediction = np.array([[0, 1, 2, 3], [4, 5, 6, 7], [8, 1, 2, 3], [4, 5, 6, 255]], dtype=np.uint8)
    confidence = np.array([[91, 92, 93, 94], [95, 96, 97, 98], [90, 89, 88, 87], [86, 85, 84, 0]], dtype=np.uint8)
    mask = np.ones((4, 4), dtype=np.uint8); mask[3, 3] = 0
    _tif(paths["prediction_discrete"], prediction, nodata=255)
    _tif(paths["prediction_confidence"], confidence, nodata=0)
    _tif(paths["prediction_valid_mask"], mask, nodata=255)
    checkpoint = root / "evidence" / "checkpoint.bin"
    input_asset = root / "evidence" / "input-asset.bin"
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    checkpoint.write_bytes(b"executed-checkpoint-fixture")
    input_asset.write_bytes(b"inference-input-fixture")
    named = [f"lcluc:secondary_{kind}_{province_id}_{year}" for kind in SECONDARY_KINDS]
    capabilities = root / "evidence" / "get-capabilities.xml"
    if publish:
        capabilities.write_text(
            "<WMS_Capabilities><Capability><Layer>" + "".join(
                f"<Layer><Name>{name}</Name></Layer>" for name in named
            ) + "</Layer></Capability></WMS_Capabilities>",
            encoding="utf-8",
        )
    manifest = {
        "schema_version": "1.0", "evidence_status": "VERIFIED_REAL",
        "source_type": "EXECUTED_MODEL_INFERENCE", "model_id": "model-real",
        "checkpoint_path": str(checkpoint.relative_to(root)).replace("\\", "/"),
        "checkpoint_sha256": _sha(checkpoint),
        "input_asset_path": str(input_asset.relative_to(root)).replace("\\", "/"),
        "input_asset_sha256": _sha(input_asset),
        "confidence_source": "MODEL_SOFTMAX_MAX_PROBABILITY",
        "valid_mask_source": "INFERENCE_INPUT_VALID_MASK",
        "capabilities_path": str(capabilities.relative_to(root)).replace("\\", "/") if publish else None,
        "capabilities_sha256": _sha(capabilities) if publish else None,
        "provinces": {province_id: {"year": year, "assets": {
            kind: {"file_rel_path": str(path.relative_to(root)).replace("\\", "/"), "sha256": _sha(path)}
            for kind, path in paths.items()
        }}},
    }
    path = root / "secondary-evidence.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def test_default_path_is_read_only_blocked_and_creates_no_fake_rasters(tmp_path):
    manager = GeoServerSecondaryAndChangeManager(tmp_path)
    records = manager.materialize_secondary_layers()
    assert len(records) == len(PROVINCE_SPECS) * 3
    assert not manager.sec_dir.exists()
    assert all(record["evidence_status"] == "BLOCKED" for record in records)
    assert all(record["model_prediction"] is False for record in records)
    assert all(record["file_rel_path"] is None for record in records)
    assert all(record["published_status"] is None for record in records)
    assert all(record["wms_getmap_url"] is None for record in records)


def test_verified_assets_and_named_layers_are_distinct_gates(tmp_path):
    evidence = _evidence(tmp_path, publish=False)
    records = GeoServerSecondaryAndChangeManager(tmp_path, evidence_manifest=evidence).materialize_secondary_layers()
    banten = [record for record in records if record["province_id"] == "banten"]
    assert all(record["evidence_status"] == "VERIFIED_REAL" for record in banten)
    assert all(record["file_sha256"] for record in banten)
    assert all(record["published_status"] is None for record in banten)
    assert all(record["evidence_status"] == "BLOCKED" for record in records if record["province_id"] != "banten")


def test_named_layer_status_requires_capabilities_sha_and_exact_enumeration(tmp_path):
    evidence = _evidence(tmp_path, publish=True)
    records = GeoServerSecondaryAndChangeManager(tmp_path, evidence_manifest=evidence).materialize_secondary_layers()
    banten = [record for record in records if record["province_id"] == "banten"]
    assert {record["published_status"] for record in banten} == {"VERIFIED_NAMED_LAYER_ENUMERATION"}
    assert all(record["wms_getmap_url"] is None for record in banten)


def test_manifest_named_layer_claim_without_capabilities_file_is_not_verified(tmp_path):
    evidence = _evidence(tmp_path, publish=True)
    manifest = json.loads(evidence.read_text(encoding="utf-8"))
    capabilities = tmp_path / manifest["capabilities_path"]
    capabilities.unlink()
    manifest["named_layers"] = [
        f"lcluc:secondary_{kind}_banten_{PROVINCE_SPECS['banten']['default_year']}"
        for kind in SECONDARY_KINDS
    ]
    evidence.write_text(json.dumps(manifest), encoding="utf-8")
    records = GeoServerSecondaryAndChangeManager(tmp_path, evidence_manifest=evidence).materialize_secondary_layers()
    banten = [record for record in records if record["province_id"] == "banten"]
    assert all(record["evidence_status"] == "VERIFIED_REAL" for record in banten)
    assert all(record["published_status"] is None for record in banten)


def test_checkpoint_sha_must_resolve_to_a_real_pinned_file(tmp_path):
    evidence = _evidence(tmp_path, publish=False)
    manifest = json.loads(evidence.read_text(encoding="utf-8"))
    (tmp_path / manifest["checkpoint_path"]).unlink()
    evidence.write_text(json.dumps(manifest), encoding="utf-8")
    records = GeoServerSecondaryAndChangeManager(tmp_path, evidence_manifest=evidence).materialize_secondary_layers()
    assert all(record["evidence_status"] == "BLOCKED" for record in records)
    assert {record["reason"] for record in records} == {"INFERENCE_PROVENANCE_ASSET_SHA_MISMATCH"}


def test_worldcover_copy_is_rejected_as_model_prediction(tmp_path):
    evidence = _evidence(tmp_path)
    year = PROVINCE_SPECS["banten"]["default_year"]
    prediction = tmp_path / "geoserver_layers" / "secondary" / f"banten_{year}" / "prediction_discrete.tif"
    reference = tmp_path / "geoserver_layers" / "primary" / f"banten_{year}" / "worldcover_reference.tif"
    reference.parent.mkdir(parents=True, exist_ok=True)
    reference.write_bytes(prediction.read_bytes())
    records = GeoServerSecondaryAndChangeManager(tmp_path, evidence_manifest=evidence).materialize_secondary_layers()
    banten = [record for record in records if record["province_id"] == "banten"]
    assert {record["reason"] for record in banten} == {"PREDICTION_EQUALS_REFERENCE_LABEL"}


def test_change_statistics_remain_null_without_verified_t1_t2_inputs(tmp_path):
    summaries = GeoServerSecondaryAndChangeManager(tmp_path).compute_annual_changes()
    assert len(summaries) == len(PROVINCE_SPECS)
    assert all(summary.status == "BLOCKED" for summary in summaries)
    assert all(summary.common_valid_ha is None for summary in summaries)
    assert all(summary.forest_loss_ha is None for summary in summaries)
    assert all(summary.net_carbon_emission_tco2e is None for summary in summaries)


def test_export_replaces_registry_instead_of_appending_and_keeps_metrics_null(tmp_path):
    output = tmp_path / "out"
    output.mkdir()
    registry = output / "08_geoserver_1st_2nd_layer_registry.csv"
    registry.write_text("stale,PUBLISHED_ONLINE\n", encoding="utf-8")
    result = GeoServerSecondaryAndChangeManager(tmp_path / "data").export_all_downstream_deliverables(output)
    text = result["csv_registry"].read_text(encoding="utf-8")
    assert "stale" not in text and "PUBLISHED_ONLINE" not in text
    assert "BLOCKED" in text
    assert "98.8" not in result["change_csv"].read_text(encoding="utf-8")
