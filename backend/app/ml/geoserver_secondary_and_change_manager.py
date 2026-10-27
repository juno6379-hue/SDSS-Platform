"""Fail-closed inspection of secondary inference and change-detection evidence.

This module never creates predictions, confidence rasters, validity masks, or
GeoServer publications.  It only inspects explicitly supplied inference
evidence and otherwise returns BLOCKED records with null measurements.
"""
from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

import numpy as np
import rasterio

from app.ml.geoserver_primary_layers_manager import PROVINCE_SPECS
from app.ml.recovery_rate_engine import PROVINCE_LAND_AREAS_HA

SECONDARY_KINDS = (
    "prediction_discrete", "prediction_confidence", "prediction_valid_mask",
)
STYLE_BY_KIND = {
    "prediction_discrete": "lcluc_discrete_9classes",
    "prediction_confidence": "confidence_ramp_0_100",
    "prediction_valid_mask": "valid_mask_binary",
}
SHA256_LENGTH = 64


class SecondaryEvidenceError(RuntimeError):
    """Supplied model-inference evidence is incomplete or inconsistent."""


@dataclass(frozen=True)
class ProvinceChangeSummary:
    province_id: str
    province_name: str
    total_land_ha: float
    status: str = "BLOCKED"
    reason: str = "BLOCKED_NO_VERIFIED_T1_T2_MODEL_PREDICTIONS"
    common_valid_ha: float | None = None
    common_valid_pct: float | None = None
    forest_loss_ha: float | None = None
    forest_gain_ha: float | None = None
    net_forest_change_ha: float | None = None
    built_increase_ha: float | None = None
    cropland_shift_ha: float | None = None
    net_carbon_emission_tco2e: float | None = None
    habitat_fragmentation_index: float | None = None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _valid_sha(value: Any) -> bool:
    return isinstance(value, str) and len(value) == SHA256_LENGTH and all(c in "0123456789abcdef" for c in value)


def _safe_child(root: Path, relative: Any) -> Path:
    if not isinstance(relative, str) or not relative:
        raise SecondaryEvidenceError("ASSET_PATH_REQUIRED")
    path = (root / relative).resolve()
    if path != root and root not in path.parents:
        raise SecondaryEvidenceError("ASSET_PATH_OUTSIDE_DATA_ROOT")
    return path


class GeoServerSecondaryAndChangeManager:
    """Inspect model outputs without mutating data or GeoServer."""

    def __init__(self, data_root: Path, *, evidence_manifest: Path | None = None):
        self.data_root = Path(data_root).resolve()
        self.sec_dir = self.data_root / "geoserver_layers" / "secondary"
        self.evidence_manifest = Path(evidence_manifest).resolve() if evidence_manifest else None

    def _load_manifest(self) -> tuple[dict[str, Any] | None, str | None]:
        if self.evidence_manifest is None or not self.evidence_manifest.is_file():
            return None, "MISSING_INFERENCE_EVIDENCE_MANIFEST"
        try:
            raw = self.evidence_manifest.read_bytes()
            manifest = json.loads(raw)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return None, "INVALID_INFERENCE_EVIDENCE_MANIFEST"
        if not isinstance(manifest, dict):
            return None, "INVALID_INFERENCE_EVIDENCE_MANIFEST"
        required = {
            "schema_version": "1.0",
            "evidence_status": "VERIFIED_REAL",
            "source_type": "EXECUTED_MODEL_INFERENCE",
            "confidence_source": "MODEL_SOFTMAX_MAX_PROBABILITY",
            "valid_mask_source": "INFERENCE_INPUT_VALID_MASK",
        }
        if any(manifest.get(key) != value for key, value in required.items()):
            return None, "INFERENCE_PROVENANCE_NOT_VERIFIED"
        if not all(_valid_sha(manifest.get(key)) for key in ("checkpoint_sha256", "input_asset_sha256")):
            return None, "INFERENCE_SHA_PROVENANCE_MISSING"
        try:
            for path_key, sha_key in (
                ("checkpoint_path", "checkpoint_sha256"),
                ("input_asset_path", "input_asset_sha256"),
            ):
                evidence_path = _safe_child(self.data_root, manifest.get(path_key))
                if not evidence_path.is_file() or _sha256(evidence_path) != manifest[sha_key]:
                    raise SecondaryEvidenceError("INFERENCE_PROVENANCE_ASSET_SHA_MISMATCH")
        except (OSError, SecondaryEvidenceError) as exc:
            return None, str(exc) if isinstance(exc, SecondaryEvidenceError) else "INFERENCE_PROVENANCE_ASSET_UNREADABLE"
        if not isinstance(manifest.get("provinces"), dict):
            return None, "PROVINCE_EVIDENCE_MISSING"
        manifest["_named_layers"] = self._verified_capabilities_layers(manifest)
        manifest["_manifest_sha256"] = hashlib.sha256(raw).hexdigest()
        return manifest, None

    def _verified_capabilities_layers(self, manifest: dict[str, Any]) -> set[str]:
        """Return layers parsed from a SHA-pinned capabilities file, or none."""
        if not _valid_sha(manifest.get("capabilities_sha256")):
            return set()
        try:
            path = _safe_child(self.data_root, manifest.get("capabilities_path"))
            if not path.is_file() or _sha256(path) != manifest["capabilities_sha256"]:
                return set()
            document = ElementTree.fromstring(path.read_bytes())
        except (OSError, ElementTree.ParseError, SecondaryEvidenceError):
            return set()
        return {
            (node.text or "").strip()
            for node in document.iter()
            if node.tag.rsplit("}", 1)[-1] == "Name" and (node.text or "").strip()
        }

    def _blocked_records(self, province_id: str, reason: str) -> list[dict[str, Any]]:
        spec = PROVINCE_SPECS[province_id]
        year = spec["default_year"]
        return [self._record(province_id, year, kind, reason=reason) for kind in SECONDARY_KINDS]

    def _record(
        self, province_id: str, year: int, kind: str, *, reason: str | None = None,
        asset: dict[str, Any] | None = None, published: bool = False,
        manifest_sha256: str | None = None,
    ) -> dict[str, Any]:
        spec = PROVINCE_SPECS[province_id]
        layer_id = f"lcluc:secondary_{kind}_{province_id}_{year}"
        return {
            "layer_id": layer_id,
            "stage": "2nd_secondary",
            "kind": kind,
            "province_id": province_id,
            "province_name": spec["name"],
            "year": year,
            "evidence_status": "BLOCKED" if reason else "VERIFIED_REAL",
            "reason": reason,
            "model_prediction": False if reason else True,
            "file_rel_path": None if reason else asset["file_rel_path"],
            "file_sha256": None if reason else asset["sha256"],
            "manifest_sha256": manifest_sha256,
            "crs": None if reason else asset["crs"],
            "width": None if reason else asset["width"],
            "height": None if reason else asset["height"],
            "nodata_value": None if reason else asset["nodata_value"],
            "resampling": "nearest" if not reason else None,
            "colormap_style": STYLE_BY_KIND[kind] if not reason else None,
            "source_product": None if reason else "EXECUTED_MODEL_INFERENCE",
            "published_status": "VERIFIED_NAMED_LAYER_ENUMERATION" if published else None,
            "wms_getmap_url": None,
        }

    def _inspect_province(self, province_id: str, manifest: dict[str, Any]) -> list[dict[str, Any]]:
        spec = PROVINCE_SPECS[province_id]
        province = manifest["provinces"].get(province_id)
        if not isinstance(province, dict):
            return self._blocked_records(province_id, "PROVINCE_INFERENCE_EVIDENCE_MISSING")
        year = province.get("year")
        if year != spec["default_year"] or not isinstance(province.get("assets"), dict):
            return self._blocked_records(province_id, "PROVINCE_INFERENCE_EVIDENCE_INVALID")

        inspected: dict[str, dict[str, Any]] = {}
        arrays: dict[str, np.ndarray] = {}
        grid: tuple[Any, ...] | None = None
        try:
            for kind in SECONDARY_KINDS:
                declared = province["assets"].get(kind)
                if not isinstance(declared, dict) or not _valid_sha(declared.get("sha256")):
                    raise SecondaryEvidenceError("ASSET_SHA_REQUIRED")
                path = _safe_child(self.data_root, declared.get("file_rel_path"))
                if not path.is_file() or _sha256(path) != declared["sha256"]:
                    raise SecondaryEvidenceError("ASSET_SHA_MISMATCH")
                with rasterio.open(path) as dataset:
                    if dataset.count != 1 or dataset.crs is None:
                        raise SecondaryEvidenceError("ASSET_RASTER_CONTRACT_INVALID")
                    current_grid = (
                        dataset.crs.to_string(), tuple(dataset.transform), tuple(dataset.bounds),
                        dataset.width, dataset.height,
                    )
                    if grid is not None and current_grid != grid:
                        raise SecondaryEvidenceError("SECONDARY_GRID_MISMATCH")
                    grid = current_grid
                    values = dataset.read(1)
                    arrays[kind] = values
                    inspected[kind] = {
                        "file_rel_path": declared["file_rel_path"], "sha256": declared["sha256"],
                        "crs": current_grid[0], "width": dataset.width, "height": dataset.height,
                        "nodata_value": dataset.nodata,
                    }
            mask_values = set(int(value) for value in np.unique(arrays["prediction_valid_mask"]))
            if not mask_values <= {0, 1, 255} or 1 not in mask_values:
                raise SecondaryEvidenceError("VALID_MASK_VALUES_INVALID")
            valid = arrays["prediction_valid_mask"] == 1
            prediction_values = arrays["prediction_discrete"][valid]
            confidence_values = arrays["prediction_confidence"][valid]
            if prediction_values.size == 0 or np.any((prediction_values < 0) | (prediction_values > 8)):
                raise SecondaryEvidenceError("PREDICTION_CLASS_VALUES_INVALID")
            if np.any((confidence_values < 0) | (confidence_values > 100)):
                raise SecondaryEvidenceError("CONFIDENCE_VALUES_INVALID")

            reference = self.data_root / "geoserver_layers" / "primary" / f"{province_id}_{year}" / "worldcover_reference.tif"
            if reference.is_file():
                if _sha256(reference) == inspected["prediction_discrete"]["sha256"]:
                    raise SecondaryEvidenceError("PREDICTION_EQUALS_REFERENCE_LABEL")
                with rasterio.open(reference) as dataset:
                    if dataset.count == 1 and dataset.shape == arrays["prediction_discrete"].shape:
                        if np.array_equal(dataset.read(1), arrays["prediction_discrete"]):
                            raise SecondaryEvidenceError("PREDICTION_EQUALS_REFERENCE_LABEL")
        except (KeyError, OSError, rasterio.errors.RasterioError, SecondaryEvidenceError) as exc:
            reason = str(exc) if isinstance(exc, SecondaryEvidenceError) else "SECONDARY_EVIDENCE_INSPECTION_FAILED"
            return self._blocked_records(province_id, reason)

        layer_ids = {f"lcluc:secondary_{kind}_{province_id}_{year}" for kind in SECONDARY_KINDS}
        named_layers = manifest.get("_named_layers", set())
        published = layer_ids <= named_layers
        return [
            self._record(
                province_id, year, kind, asset=inspected[kind], published=published,
                manifest_sha256=manifest["_manifest_sha256"],
            )
            for kind in SECONDARY_KINDS
        ]

    def materialize_secondary_layers(self) -> list[dict[str, Any]]:
        """Compatibility name: inspect evidence; never materialize or publish files."""
        manifest, reason = self._load_manifest()
        if manifest is None:
            return [
                record
                for province_id in PROVINCE_SPECS
                for record in self._blocked_records(province_id, str(reason))
            ]
        return [
            record
            for province_id in PROVINCE_SPECS
            for record in self._inspect_province(province_id, manifest)
        ]

    def compute_annual_changes(self) -> list[ProvinceChangeSummary]:
        """Return null metrics until verified T1/T2 predictions and masks exist."""
        return [
            ProvinceChangeSummary(
                province_id=province_id, province_name=spec["name"],
                total_land_ha=PROVINCE_LAND_AREAS_HA[province_id],
            )
            for province_id, spec in PROVINCE_SPECS.items()
        ]

    def export_all_downstream_deliverables(self, output_dir: Path) -> dict[str, Path]:
        """Write local fail-closed reports only; never write GeoServer or a registry."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        records = self.materialize_secondary_layers()
        summaries = self.compute_annual_changes()

        csv_file = output_dir / "08_geoserver_1st_2nd_layer_registry.csv"
        fields = list(records[0]) if records else []
        with csv_file.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(records)

        audit_file = output_dir / "08_pixel_map_audit.md"
        verified_local = sum(record["evidence_status"] == "VERIFIED_REAL" for record in records)
        verified_published = sum(record["published_status"] == "VERIFIED_NAMED_LAYER_ENUMERATION" for record in records)
        audit_file.write_text(
            "# G11 secondary evidence audit\n\n"
            "- overall_status: `BLOCKED`\n"
            f"- secondary_records: `{len(records)}`\n"
            f"- verified_local_artifacts: `{verified_local}`\n"
            f"- verified_named_layers: `{verified_published}`\n"
            "- measured_pixel_queries: `0`\n"
            "- note: local file verification and named-layer publication are separate gates.\n",
            encoding="utf-8",
        )

        change_csv = output_dir / "09_annual_change_and_common_valid_area.csv"
        with change_csv.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(asdict(summaries[0])))
            writer.writeheader()
            writer.writerows(asdict(summary) for summary in summaries)

        safe_docs = {
            "deploy_doc": ("10_deployment_architecture_and_decisions.md", "# Deployment\n\n`BLOCKED`: no production deployment evidence.\n"),
            "e2e_doc": ("11_e2e_test_evidence.md", "# E2E evidence\n\n`BLOCKED`: no exhaustive secondary named-layer or pixel evidence.\n"),
            "exec_summary": ("12_executive_summary_before_after.md", "# Executive summary\n\n`BLOCKED`: no executed model inference or measured change statistics.\n"),
        }
        result = {"csv_registry": csv_file, "audit_report": audit_file, "change_csv": change_csv}
        for key, (name, content) in safe_docs.items():
            path = output_dir / name
            path.write_text(content, encoding="utf-8")
            result[key] = path
        return result
