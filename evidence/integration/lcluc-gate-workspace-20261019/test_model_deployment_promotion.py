"""Unit tests for ModelDeploymentPromotionManager and lcluc_workflow._gate compliance.

Verifies:
1. Unpromoted Draft models trigger MODEL_NOT_DEPLOYED_OR_EVALUATED.
2. Incompatible or unverified evaluations trigger MODEL_EVALUATION_MISMATCH.
3. Promoted models transition through Draft -> Validated -> Approved -> Deployed.
4. Promoted models pass the strict _gate in backend/app/lcluc_workflow.py.
5. Baseline model records (e.g. baseline2021_cpu_v1_model) can be promoted with full lineage.
6. Checkpoint and report tampering are fail-closed rejected.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
WORKSPACE_DIR = Path(__file__).resolve().parent
if str(WORKSPACE_DIR) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_DIR))

import numpy as np
import rasterio
from rasterio.transform import from_origin
import torch

from backend.app import lcluc_workflow as workflow
from backend.app.dataset_registry import register_version
from backend.app.lcluc_workflow import _gate, WorkflowError
from backend.app.ml.network import TinyUNet
from backend.app.ml.raster import CLASS_NAMES
from backend.app.model_registration_provenance import inspect_model_registration_provenance
from backend.app.store import Store

from model_deployment_promotion import (
    ModelDeploymentPromotionManager,
    ModelPromotionError,
    _sha256_file,
)


class TestModelDeploymentPromotion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old_threads = torch.get_num_threads()
        torch.set_num_threads(1)

    @classmethod
    def tearDownClass(cls):
        torch.set_num_threads(cls.old_threads)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = Store(self.root)
        self.manager = ModelDeploymentPromotionManager(self.store)

        # Create model directory and fixture checkpoint
        self.model_dir = self.root / "models" / "test_model_v1"
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_path = self.model_dir / "best.pt"
        self.report_path = self.model_dir / "report.json"

        self.signature = {
            "bands": [1, 2, 3],
            "band_names": ["blue", "green", "red"],
            "scale": 0.0001,
            "offset": 0.0,
            "patch_size": 16,
            "class_names": CLASS_NAMES,
            "version": "training-v1",
            "normalization_mode": "global",
            "synthetic": False,
            "reference_kind": "worldcover_weak_label",
        }

        # Build genuine TinyUNet checkpoint
        unet = TinyUNet(3)
        with torch.no_grad():
            for param in unet.parameters():
                param.zero_()
            unet.head.bias[1] = 1.0
        torch.save(
            {
                "architecture": "tiny_unet",
                "state_dict": unet.state_dict(),
                "manifest": self.signature,
            },
            self.checkpoint_path,
        )

        self.report_path.write_text(
            json.dumps({
                "model_id": "test_model_v1",
                "status": "Draft",
                "training_state": "completed",
                "checkpoint_path": "models/test_model_v1/best.pt",
            }, indent=2),
            encoding="utf-8",
        )

        self.ckpt_sha = _sha256_file(self.checkpoint_path)
        self.report_sha = _sha256_file(self.report_path)

        # Register unpromoted Draft model in store
        self.draft_model = {
            "id": "test_model_v1",
            "status": "Draft",
            "independent_evaluation": False,
            "synthetic": False,
            "reference_kind": "worldcover_weak_label",
            "checkpoint_path": "models/test_model_v1/best.pt",
            "checkpoint_sha256": self.ckpt_sha,
            "training_report_sha256": self.report_sha,
        }
        self.store.put("models", self.draft_model)

        # Build valid raster inputs and dataset versions for _gate
        self.input_manifests = []
        self.request_images = []
        for year in (2020, 2021):
            img_path = self.root / f"raster-{year}.tif"
            with rasterio.open(
                img_path,
                "w",
                driver="GTiff",
                width=16,
                height=16,
                count=3,
                dtype="uint16",
                crs="EPSG:3857",
                transform=from_origin(100, 200, 10, 10),
                nodata=0,
            ) as ds:
                ds.write(np.full((3, 16, 16), 100 + (year - 2020), dtype="uint16"))
                ds.descriptions = tuple(self.signature["band_names"])

            qual_path = self.root / f"quality-{year}.json"
            qual_path.write_text('{"quality": "verified"}', encoding="utf-8")

            manifest = {
                "schema_version": "0.2.0",
                "dataset_id": f"input-dataset-{year}",
                "version": "v1",
                "source": {"institution": "LAPAN/BRIN", "product": "Sentinel-2 Surface Reflectance", "license": "open"},
                "data_type": "raster",
                "spatial": {"bbox": [100, 40, 101, 41], "crs": "EPSG:4326"},
                "temporal": {"start": f"{year}-01-01T00:00:00Z", "end": f"{year}-12-31T00:00:00Z", "calendar": "gregorian"},
                "quality_status": "VALIDATED",
                "quality_report_ref": qual_path.name,
                "access_class": "PUBLIC",
                "sha256": _sha256_file(img_path),
                "artifact_uri": img_path.name,
                "lineage": [],
            }
            register_version(self.store, manifest)
            self.input_manifests.append(manifest)
            self.request_images.append({
                "year": year,
                "input_ref": {"id": manifest["dataset_id"], "version": "v1", "sha256": manifest["sha256"]},
                "quality_report_sha256": _sha256_file(qual_path),
            })

        self.request = {
            "schema_version": 1,
            "capability": workflow.CAPABILITY,
            "trace_id": "trace-promote-test",
            "idempotency_key": "idemp-promote-test",
            "model_ref": {
                "id": "test_model_v1",
                "version": "v1",
                "sha256": self.ckpt_sha,
            },
            "images": self.request_images,
        }

    def tearDown(self):
        self.temp.cleanup()

    def test_unpromoted_draft_model_blocked_by_gate_with_gap2_code(self):
        """Proof of Gap 2: Unpromoted Draft model fails gate with MODEL_NOT_DEPLOYED_OR_EVALUATED."""
        with self.assertRaises(WorkflowError) as ctx:
            _gate(self.store, self.request, "wf-output-gap2")
        self.assertEqual(str(ctx.exception), "MODEL_NOT_DEPLOYED_OR_EVALUATED")

    def test_evaluation_mismatch_blocks_gate(self):
        """Evaluation with reference_kind != 'expert_independent' fails gate with MODEL_EVALUATION_MISMATCH."""
        bad_model = dict(self.draft_model, status="Deployed", independent_evaluation=True)
        bad_model["evaluation"] = {
            "reference_kind": "pseudo_label_test",
            "checkpoint_sha256": self.ckpt_sha,
        }
        self.store.put("models", bad_model)

        with self.assertRaises(WorkflowError) as ctx:
            _gate(self.store, self.request, "wf-output-eval-mismatch")
        self.assertEqual(str(ctx.exception), "MODEL_EVALUATION_MISMATCH")

    def test_evaluation_checkpoint_hash_mismatch_blocks_gate(self):
        """Evaluation checkpoint_sha256 differing from model_ref sha256 fails gate with MODEL_EVALUATION_MISMATCH."""
        bad_model = dict(self.draft_model, status="Deployed", independent_evaluation=True)
        bad_model["evaluation"] = {
            "reference_kind": "expert_independent",
            "checkpoint_sha256": "0000000000000000000000000000000000000000000000000000000000000000",
        }
        self.store.put("models", bad_model)

        with self.assertRaises(WorkflowError) as ctx:
            _gate(self.store, self.request, "wf-output-hash-mismatch")
        self.assertEqual(str(ctx.exception), "MODEL_EVALUATION_MISMATCH")

    def test_authoritative_promotion_enables_gate_acceptance(self):
        """Promoted model passes strict _gate without MODEL_NOT_DEPLOYED_OR_EVALUATED or MODEL_EVALUATION_MISMATCH."""
        expert_eval = {
            "reference_kind": "expert_independent",
            "reviewer": "Dr. A. Sudirman (Indonesian Center for Environmental Informatics)",
            "label_provenance": "2021 Multi-agency validated field reference points",
            "group": "independent_borneo_reference",
            "evaluated_pixels": 4096,
            "overall_accuracy": 0.884,
        }

        result = self.manager.promote_to_deployed(
            "test_model_v1",
            version="v1",
            evaluation=expert_eval,
            promotion_reason="Passed 2021 field reference audit with 88.4% OA",
        )

        self.assertEqual(result["status"], "PROMOTED_DEPLOYED")
        self.assertEqual(result["version"], "v1")
        self.assertTrue(result["independent_evaluation"])

        # Check stored state in Store
        promoted = self.store.get("models", "test_model_v1")
        self.assertEqual(promoted["status"], "Deployed")
        self.assertTrue(promoted["independent_evaluation"])
        self.assertEqual(promoted["evaluation"]["reference_kind"], "expert_independent")
        self.assertEqual(promoted["evaluation"]["checkpoint_sha256"], self.ckpt_sha)

        # Check provenance declaration
        provenance = inspect_model_registration_provenance(promoted)
        self.assertEqual(provenance["status"], "CONSISTENT_UNVERIFIED")

        # Check lifecycle history trail: Draft -> Validated -> Approved -> Deployed
        statuses = [entry["status"] for entry in promoted["history"]]
        self.assertEqual(statuses, ["Validated", "Approved", "Deployed"])

        # Execute genuine _gate from backend/app/lcluc_workflow.py
        payload, pins = _gate(self.store, self.request, "wf-output-success")
        self.assertIn("checkpoint_path", payload)
        self.assertEqual(len(payload["images"]), 2)
        self.assertIn("model", pins)
        self.assertIn("2020", pins)
        self.assertIn("2021", pins)

    def test_baseline2021_model_import_and_promotion(self):
        """Simulate baseline2021_cpu_v1_model registration and authoritative promotion."""
        # Create baseline model setup in isolated store
        base_dir = self.root / "models" / "baseline2021_cpu_v1_model"
        base_dir.mkdir(parents=True, exist_ok=True)
        base_ckpt = base_dir / "best.pt"
        base_report = base_dir / "report.json"

        # Build checkpoint with full gate-compliant signature
        base_sig = copy.deepcopy(self.signature)
        base_sig["version"] = "717e5e1cce1a6d56"
        base_sig["band_names"] = ["B02", "B03", "B04"]

        unet = TinyUNet(3)
        torch.save(
            {
                "architecture": "tiny_unet",
                "state_dict": unet.state_dict(),
                "manifest": base_sig,
            },
            base_ckpt,
        )

        base_report.write_text(
            json.dumps({
                "model_id": "baseline2021_cpu_v1_model",
                "training_state": "completed",
                "architecture": "tiny_unet",
            }, indent=2),
            encoding="utf-8",
        )

        base_ckpt_sha = _sha256_file(base_ckpt)
        base_report_sha = _sha256_file(base_report)

        # Record as registered baseline (similar to data/catalog.sqlite3)
        self.store.put("models", {
            "id": "baseline2021_cpu_v1_model",
            "model_id": "baseline2021_cpu_v1_model",
            "status": "Draft",
            "independent_evaluation": False,
            "synthetic": False,
            "reference_kind": "worldcover_weak_label",
            "checkpoint_path": "models/baseline2021_cpu_v1_model/best.pt",
            "checkpoint_sha256": base_ckpt_sha,
        })

        # Run promotion
        eval_data = {
            "reference_kind": "expert_independent",
            "reviewer": "Field Verification Expert Panel",
            "label_provenance": "Ground Truth Sampling 2021",
            "group": "independent_ground_truth",
            "evaluated_pixels": 8192,
        }

        result = self.manager.promote_to_deployed(
            "baseline2021_cpu_v1_model",
            version="v1",
            evaluation=eval_data,
        )

        self.assertEqual(result["status"], "PROMOTED_DEPLOYED")
        promoted = self.store.get("models", "baseline2021_cpu_v1_model")
        self.assertEqual(promoted["status"], "Deployed")
        self.assertEqual(promoted["training_report_sha256"], base_report_sha)
        self.assertEqual(promoted["checkpoint_sha256"], base_ckpt_sha)

        # Preflight verification passes
        verified = self.manager.verify_gate_acceptance("baseline2021_cpu_v1_model", "v1")
        self.assertEqual(verified["gate_compliance"], "PASSED")

    def test_promotion_demotes_prior_deployed_model(self):
        """Promoting model B demotes previously deployed model A to Approved."""
        eval_data = {
            "reference_kind": "expert_independent",
            "reviewer": "Dr. Reviewer",
            "label_provenance": "Field Proof",
            "group": "grp-1",
        }

        # Promote first model
        self.manager.promote_to_deployed("test_model_v1", version="v1", evaluation=eval_data)
        self.assertEqual(self.store.get("models", "test_model_v1")["status"], "Deployed")

        # Create second model
        m2_dir = self.root / "models" / "test_model_v2"
        m2_dir.mkdir(parents=True, exist_ok=True)
        m2_ckpt = m2_dir / "best.pt"
        m2_rep = m2_dir / "report.json"

        torch.save(
            {"architecture": "tiny_unet", "state_dict": TinyUNet(3).state_dict(), "manifest": self.signature},
            m2_ckpt,
        )
        m2_rep.write_text('{"model_id": "test_model_v2"}', encoding="utf-8")

        self.store.put("models", {
            "id": "test_model_v2",
            "status": "Draft",
            "independent_evaluation": False,
            "synthetic": False,
            "reference_kind": "worldcover_weak_label",
            "checkpoint_path": "models/test_model_v2/best.pt",
            "checkpoint_sha256": _sha256_file(m2_ckpt),
            "training_report_sha256": _sha256_file(m2_rep),
        })

        # Promote second model
        self.manager.promote_to_deployed("test_model_v2", version="v2", evaluation=eval_data)

        # First model should now be demoted to Approved
        m1 = self.store.get("models", "test_model_v1")
        self.assertEqual(m1["status"], "Approved")

        # Second model should now be Deployed
        m2 = self.store.get("models", "test_model_v2")
        self.assertEqual(m2["status"], "Deployed")

    def test_tampered_checkpoint_fails_promotion(self):
        """Tampered checkpoint byte hash is detected and rejected during audit/promotion."""
        # Mutate checkpoint
        self.checkpoint_path.write_bytes(self.checkpoint_path.read_bytes() + b"corruption")

        with self.assertRaises(ModelPromotionError) as ctx:
            self.manager.audit_model_draft("test_model_v1")
        self.assertEqual(ctx.exception.code, "CHECKPOINT_MISMATCH")

    def test_synthetic_model_rejected_from_promotion(self):
        """Models marked synthetic are strictly blocked from operational deployment."""
        synth_dir = self.root / "models" / "synth_model"
        synth_dir.mkdir(parents=True, exist_ok=True)
        synth_ckpt = synth_dir / "best.pt"
        synth_rep = synth_dir / "report.json"

        synth_sig = copy.deepcopy(self.signature)
        synth_sig["synthetic"] = True

        torch.save(
            {"architecture": "tiny_unet", "state_dict": TinyUNet(3).state_dict(), "manifest": synth_sig},
            synth_ckpt,
        )
        synth_rep.write_text('{"synthetic": true}', encoding="utf-8")

        self.store.put("models", {
            "id": "synth_model",
            "status": "Draft",
            "independent_evaluation": False,
            "synthetic": True,
            "checkpoint_path": "models/synth_model/best.pt",
            "checkpoint_sha256": _sha256_file(synth_ckpt),
            "training_report_sha256": _sha256_file(synth_rep),
        })

        with self.assertRaises(ModelPromotionError) as ctx:
            self.manager.audit_model_draft("synth_model")
        self.assertEqual(ctx.exception.code, "SYNTHETIC_MODEL_BLOCKED")

    def test_legacy_baseline_harmonization_and_gate_pass(self):
        """Legacy baseline models missing band_names are audited, harmonized, promoted, and pass _gate."""
        legacy_dir = self.root / "models" / "legacy_baseline"
        legacy_dir.mkdir(parents=True, exist_ok=True)
        legacy_ckpt = legacy_dir / "best.pt"
        legacy_rep = legacy_dir / "report.json"

        # Manifest with missing band_names (identical to original baseline2021 best.pt)
        legacy_sig = {
            "bands": [1, 2, 3],
            "scale": 0.0001,
            "offset": 0.0,
            "patch_size": 16,
            "class_names": CLASS_NAMES,
            "version": "legacy-2021",
            "normalization_mode": "global",
            "synthetic": False,
            "reference_kind": "worldcover_weak_label",
        }

        torch.save(
            {"architecture": "tiny_unet", "state_dict": TinyUNet(3).state_dict(), "manifest": legacy_sig},
            legacy_ckpt,
        )
        legacy_rep.write_text('{"model_id": "legacy_baseline"}', encoding="utf-8")

        self.store.put("models", {
            "id": "legacy_baseline",
            "status": "Draft",
            "independent_evaluation": False,
            "synthetic": False,
            "reference_kind": "worldcover_weak_label",
            "checkpoint_path": "models/legacy_baseline/best.pt",
            "checkpoint_sha256": _sha256_file(legacy_ckpt),
        })

        # 1. Audit detects missing band_names
        audit = self.manager.audit_model_draft("legacy_baseline")
        self.assertFalse(audit["band_signature_valid"])

        # 2. Harmonize with explicit band names
        harm = self.manager.harmonize_checkpoint_manifest(
            "legacy_baseline",
            band_names=["blue", "green", "red"],
        )
        self.assertTrue(harm["harmonized"])

        # 3. Post-harmonization audit passes
        audit_after = self.manager.audit_model_draft("legacy_baseline")
        self.assertTrue(audit_after["band_signature_valid"])
        self.assertTrue(audit_after["weights_loadable"])

        # 4. Promote model
        eval_data = {
            "reference_kind": "expert_independent",
            "reviewer": "Field Verification Panel",
            "label_provenance": "Ground Truth Survey",
            "group": "independent_ground_truth",
            "evaluated_pixels": 4096,
        }
        prom = self.manager.promote_to_deployed("legacy_baseline", version="v1", evaluation=eval_data)
        self.assertEqual(prom["status"], "PROMOTED_DEPLOYED")

        # 5. Formulate request and pass to genuine workflow _gate
        req = copy.deepcopy(self.request)
        req["model_ref"] = {
            "id": "legacy_baseline",
            "version": "v1",
            "sha256": harm["checkpoint_sha256"],
        }
        payload, pins = _gate(self.store, req, "wf-output-legacy")
        self.assertIn("checkpoint_path", payload)
        self.assertIn("model", pins)

    def test_timeseries_2020_2025_enforces_deployed_status_and_independent_evaluation(self):
        """Enforces that 1st ML inference across full 6-year (2020-2025) time-series strictly requires status='Deployed' and independent_evaluation=True."""
        # 1. Register 6-year images (2020 to 2025)
        timeseries_images = []
        for year in range(2020, 2026):
            img_path = self.root / f"raster-ts-{year}.tif"
            with rasterio.open(
                img_path,
                "w",
                driver="GTiff",
                width=16,
                height=16,
                count=3,
                dtype="uint16",
                crs="EPSG:3857",
                transform=from_origin(100, 200, 10, 10),
                nodata=0,
            ) as ds:
                ds.write(np.full((3, 16, 16), 100 + (year - 2020), dtype="uint16"))
                ds.descriptions = tuple(self.signature["band_names"])

            qual_path = self.root / f"quality-ts-{year}.json"
            qual_path.write_text('{"quality": "verified"}', encoding="utf-8")

            manifest = {
                "schema_version": "0.2.0",
                "dataset_id": f"input-dataset-ts-{year}",
                "version": "v1",
                "source": {"institution": "LAPAN/BRIN", "product": "Sentinel-2 Surface Reflectance", "license": "open"},
                "data_type": "raster",
                "spatial": {"bbox": [100, 40, 101, 41], "crs": "EPSG:4326"},
                "temporal": {"start": f"{year}-01-01T00:00:00Z", "end": f"{year}-12-31T00:00:00Z", "calendar": "gregorian"},
                "quality_status": "VALIDATED",
                "quality_report_ref": qual_path.name,
                "access_class": "PUBLIC",
                "sha256": _sha256_file(img_path),
                "artifact_uri": img_path.name,
                "lineage": [],
            }
            register_version(self.store, manifest)
            timeseries_images.append({
                "year": year,
                "input_ref": {"id": manifest["dataset_id"], "version": "v1", "sha256": manifest["sha256"]},
                "quality_report_sha256": _sha256_file(qual_path),
            })

        req_6yr = {
            "schema_version": 1,
            "capability": workflow.CAPABILITY,
            "trace_id": "trace-6yr-timeseries",
            "idempotency_key": "idemp-6yr-timeseries",
            "model_ref": {
                "id": "test_model_v1",
                "version": "v1",
                "sha256": self.ckpt_sha,
            },
            "images": timeseries_images,
        }

        # Case A: Model is Draft -> fail-closed with MODEL_NOT_DEPLOYED_OR_EVALUATED
        self.assertEqual(self.store.get("models", "test_model_v1")["status"], "Draft")
        with self.assertRaises(WorkflowError) as ctx:
            _gate(self.store, req_6yr, "wf-output-6yr-draft")
        self.assertEqual(str(ctx.exception), "MODEL_NOT_DEPLOYED_OR_EVALUATED")

        # Case B: Model has status 'Deployed' but independent_evaluation is False -> fail-closed
        unverified_deployed = dict(self.draft_model, status="Deployed", independent_evaluation=False)
        self.store.put("models", unverified_deployed)
        with self.assertRaises(WorkflowError) as ctx:
            _gate(self.store, req_6yr, "wf-output-6yr-unverified")
        self.assertEqual(str(ctx.exception), "MODEL_NOT_DEPLOYED_OR_EVALUATED")

        # Case C: Model is properly promoted through authoritative pipeline
        eval_data = {
            "reference_kind": "expert_independent",
            "reviewer": "National LCLUC Scientific Review Board",
            "label_provenance": "2020-2025 Multi-year Ground Observation Network",
            "group": "independent_pan_indonesia",
            "evaluated_pixels": 65536,
            "overall_accuracy": 0.912,
        }
        res = self.manager.promote_to_deployed("test_model_v1", version="v1", evaluation=eval_data)
        self.assertEqual(res["status"], "PROMOTED_DEPLOYED")

        # Case D: Gate passes for all 6 years (2020-2025)
        payload, pins = _gate(self.store, req_6yr, "wf-output-6yr-success")
        self.assertEqual(len(payload["images"]), 6)
        self.assertEqual([img["year"] for img in payload["images"]], list(range(2020, 2026)))
        self.assertIn("model", pins)
        for year in range(2020, 2026):
            self.assertIn(str(year), pins)

    def test_checkpoint_sha256_immutable_binding_to_evaluation_certificate(self):
        """Verifies that checkpoint SHA-256 hashes are immutable and bound to evaluation certificates and version declarations."""
        eval_data = {
            "reference_kind": "expert_independent",
            "reviewer": "Audit Authority",
            "label_provenance": "Strict Proof",
            "group": "audit-grp",
        }
        # Promote model successfully
        self.manager.promote_to_deployed("test_model_v1", version="v1", evaluation=eval_data)
        promoted = self.store.get("models", "test_model_v1")

        # Verify 4-way hash equality
        disk_sha = _sha256_file(self.checkpoint_path)
        self.assertEqual(promoted["checkpoint_sha256"], disk_sha)
        self.assertEqual(promoted["evaluation"]["checkpoint_sha256"], disk_sha)
        self.assertEqual(promoted["model_version_declaration"]["checkpoint_sha256"], disk_sha)

        # Mutate evaluation certificate checkpoint hash -> _gate must fail-closed with MODEL_EVALUATION_MISMATCH
        tampered_eval_model = copy.deepcopy(promoted)
        tampered_eval_model["evaluation"]["checkpoint_sha256"] = "f" * 64
        self.store.put("models", tampered_eval_model)
        with self.assertRaises(WorkflowError) as ctx:
            _gate(self.store, self.request, "wf-eval-tampered")
        self.assertEqual(str(ctx.exception), "MODEL_EVALUATION_MISMATCH")

        # Mutate model version declaration checkpoint hash -> inspect_model_registration_provenance rejects
        tampered_decl_model = copy.deepcopy(promoted)
        tampered_decl_model["model_version_declaration"]["checkpoint_sha256"] = "e" * 64
        self.store.put("models", tampered_decl_model)
        with self.assertRaises(WorkflowError) as ctx:
            _gate(self.store, self.request, "wf-decl-tampered")
        self.assertEqual(str(ctx.exception), "MODEL_VERSION_NOT_BOUND")


if __name__ == "__main__":
    unittest.main()

