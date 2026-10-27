"""Unit tests for MLOps FastAPI Router endpoints."""

from pathlib import Path
import hashlib
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app import main
from app.store import Store


class TestMlopsRouter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_store = main.store
        cls.temp = tempfile.TemporaryDirectory()
        temp_root = Path(cls.temp.name)
        source_dir = temp_root / "first-group-training-esri-v1"
        source_dir.mkdir(parents=True)
        shutil.copyfile(
            ROOT / "data/first-group-training-esri-v1/annual-window-report.json",
            source_dir / "annual-window-report.json",
        )
        manifest_dir = temp_root / "docs/lcluc/v3"
        manifest_dir.mkdir(parents=True)
        shutil.copyfile(
            ROOT / "docs/lcluc/v3/06_model_experiments_manifest.json",
            manifest_dir / "06_model_experiments_manifest.json",
        )
        main.store = Store(temp_root)
        main.store.put(
            "mlops_approvals",
            {
                "id": "TEST-APPROVAL-1",
                "model_id": "lcluc_segmentation",
                "status": "pending",
                "notes": "isolated test approval",
            },
        )
        cls.client = TestClient(main.app)

    @classmethod
    def tearDownClass(cls):
        main.store = cls.original_store
        cls.temp.cleanup()

    def test_mlops_summary_endpoint(self):
        """Summary exposes actual inventory while blocking unmeasured claims."""
        resp = self.client.get("/v1/mlops/summary")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["schema_version"], "2.1")
        self.assertEqual(data["status"], "blocked")
        self.assertIn("BLOCKED_NOT_MEASURED", data["reason_codes"])

        kpis = data["kpis"]
        self.assertEqual(kpis["models_in_production"]["value"], 0)
        self.assertEqual(kpis["training_in_queue"]["value"], 0)
        self.assertEqual(kpis["deployments_30d"]["value"], 0)
        self.assertIsNone(kpis["mean_f1_score"]["value"])
        self.assertIsNone(kpis["mean_miou"]["value"])

        coverage = data["coverage_audit"]
        self.assertEqual(coverage["status"], "BLOCKED_NOT_MEASURED")
        self.assertEqual(coverage["total_cells"], 432)
        self.assertEqual(coverage["total_unique_scenes"], 107)
        self.assertEqual(coverage["total_patches_inventory"], 1779)
        self.assertEqual(coverage["total_eligible_patches"], 1407)
        self.assertEqual(len(coverage["provinces"]), 6)
        for province in coverage["provinces"]:
            self.assertIsNone(province["valid_coverage_pct"])
            self.assertIsNone(province["cloud_pct"])
            self.assertIsNone(province["missing_pct"])

        evidence = data["model_evidence"]
        self.assertFalse(evidence["training_executed"])
        self.assertFalse(evidence["predictions_verified"])
        self.assertFalse(evidence["metrics_verified"])
        self.assertFalse(evidence["promotion_authorized"])
        self.assertFalse(evidence["deployment_executed"])
        self.assertEqual(evidence["model_prediction_layers"], 0)
        self.assertEqual(data["models"], [])
        self.assertEqual(data["experiments"], [])
        self.assertFalse(data["actions"]["retrain_allowed"])
        self.assertFalse(data["actions"]["approval_allowed"])
        self.assertTrue(all(step["status"] == "blocked" for step in data["pipeline_steps"]))
        self.assertTrue(all(item["status"] == "blocked" for item in data["deployments"].values()))

        approvals = data["approvals"]
        self.assertTrue(any(item["id"] == "TEST-APPROVAL-1" for item in approvals))
        self.assertFalse(any(str(item["id"]).startswith("APP-2024-") for item in approvals))
        self.assertTrue(all(item["status_code"] == "unverified" for item in approvals))
        self.assertTrue(all(item["human_approval_verified"] is False for item in approvals))
        self.assertEqual(data["approval_evidence"]["verified_approval_count"], 0)

        readiness = data["retraining_readiness"]
        self.assertEqual(readiness["schema_version"], "retraining-readiness/1.0")
        self.assertEqual(readiness["status"], "blocked")
        self.assertFalse(readiness["pipeline_complete"])
        self.assertFalse(readiness["retrain_allowed"])
        self.assertFalse(readiness["automatic_gate_bypass_allowed"])
        self.assertFalse(readiness["weak_labels_can_measure_accuracy"])
        self.assertFalse(readiness["reference_landcover_can_replace_observations"])
        self.assertIsNone(readiness["confidence"]["value"])
        self.assertEqual(
            readiness["confidence"]["meaning"],
            "MODEL_PROBABILITY_CALIBRATION_NOT_CORRECTNESS",
        )
        self.assertIsNone(readiness["accuracy"]["overall_accuracy"])
        self.assertIsNone(readiness["accuracy"]["macro_f1"])
        self.assertIsNone(readiness["accuracy"]["miou"])
        self.assertTrue(readiness["accuracy"]["independent_ground_truth_required"])
        stage_by_id = {stage["id"]: stage for stage in readiness["stages"]}
        self.assertEqual(
            stage_by_id["gap_measurement"]["reason_code"],
            "BLOCKED_MISSING_AUTHORITATIVE_BOUNDARY_AND_CAUSE_MOSAICS",
        )
        self.assertEqual(
            stage_by_id["collection_execution"]["reason_code"],
            "NO_EXECUTED_PROVINCE_GAP_COLLECTION",
        )
        self.assertEqual(
            stage_by_id["confidence_calibration"]["reason_code"],
            "NO_VERIFIED_CONFIDENCE_CALIBRATION",
        )
        self.assertEqual(
            stage_by_id["independent_accuracy"]["reason_code"],
            "NO_INDEPENDENT_GROUND_TRUTH_EVALUATION",
        )

    def test_mlops_summary_degrades_to_stable_blocked_contract(self):
        """Evidence reader errors remain explicit and never become optimistic defaults."""
        with patch(
            "app.mlops_router.build_province_month_audit",
            side_effect=RuntimeError("fixture failure"),
        ):
            resp = self.client.get("/v1/mlops/summary")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "blocked")
        self.assertIn("COVERAGE_AUDIT_UNAVAILABLE", data["reason_codes"])
        self.assertEqual(data["coverage_audit"]["status"], "BLOCKED_AUDIT_UNAVAILABLE")
        self.assertEqual(data["coverage_audit"]["provinces"], [])
        self.assertIsNone(data["kpis"]["mean_f1_score"]["value"])

    def test_mlops_summary_does_not_write_workspace_catalog(self):
        """Summary reads the isolated store and leaves the workspace catalog byte-identical."""
        catalog = ROOT / "data/catalog.sqlite3"
        before = hashlib.sha256(catalog.read_bytes()).hexdigest() if catalog.is_file() else None
        resp = self.client.get("/v1/mlops/summary")
        self.assertEqual(resp.status_code, 200)
        after = hashlib.sha256(catalog.read_bytes()).hexdigest() if catalog.is_file() else None
        self.assertEqual(after, before)

    def test_mlops_coverage_audit_endpoint(self):
        """Verify GET /v1/mlops/coverage/audit returns 432 cells and rollups."""
        resp = self.client.get("/v1/mlops/coverage/audit")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")
        audit = data["audit"]
        self.assertEqual(audit["total_cells"], 432)
        self.assertEqual(len(audit["cells"]), 432)
        self.assertEqual(len(audit["province_rollups"]), 6)
        self.assertEqual(len(audit["year_rollups"]), 6)

    def test_mlops_recovery_rate_endpoint(self):
        """Recovery stays blocked until pinned before/after measurements exist."""
        resp = self.client.get("/v1/mlops/recovery-rate")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "blocked")
        self.assertEqual(data["schema_version"], "4.1")
        self.assertEqual(
            data["reason_code"],
            "MISSING_EXPLICIT_PINNED_BEFORE_AND_AFTER_COVERAGE_REPORTS",
        )
        summary = data["recovery_summary"]
        self.assertEqual(summary["total_cells"], 36)
        self.assertEqual(summary["evidence_status"], "BLOCKED")
        self.assertEqual(
            summary["blocking_reason"],
            "MISSING_EXPLICIT_PINNED_BEFORE_AND_AFTER_COVERAGE_REPORTS",
        )
        self.assertIsNone(summary["mean_before_valid_pct"])
        self.assertIsNone(summary["mean_after_valid_pct"])
        self.assertIsNone(summary["mean_recovery_rate_pct"])
        self.assertTrue(all(cell["status"] == "BLOCKED" for cell in summary["cells"]))

    def test_mlops_experiments_are_blocked_without_executed_runs(self):
        resp = self.client.get("/v1/mlops/experiments")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "blocked")
        self.assertEqual(data["runs"], [])
        self.assertIsNone(data["best_run"])
        self.assertIsNone(data["metrics"])

    def test_mlops_retrain_trigger_is_fail_closed_and_write_free(self):
        """Retraining cannot be queued without executed evidence."""
        payload = {
            "model_id": "flood_drought_hazard",
            "target_version": "v1.0.5",
            "dataset_version": "fg-annual-2020-2025-v2",
            "epochs": 40,
            "holdout_split": "test_west_java_val_banten",
        }
        before_jobs = self.main_store_rows("jobs")
        before_retrains = self.main_store_rows("mlops_retrain_jobs")
        resp = self.client.post("/v1/mlops/retrain", json=payload)
        self.assertEqual(resp.status_code, 409)
        detail = resp.json()["detail"]
        self.assertEqual(detail["status"], "blocked")
        self.assertEqual(
            detail["reason_code"],
            "BLOCKED_NO_EXECUTED_TRAINING_OR_MEASURED_PREDICTIONS",
        )
        self.assertEqual(self.main_store_rows("jobs"), before_jobs)
        self.assertEqual(self.main_store_rows("mlops_retrain_jobs"), before_retrains)

    def test_mlops_approval_request_is_fail_closed_and_write_free(self):
        """Approval cannot be requested without an evidence-backed candidate."""
        payload = {
            "model_id": "lcluc_segmentation",
            "version": "v1.2.1",
            "target_env": "production",
            "requested_by": "Senior GeoAI Engineer",
            "rationale": "99.2% SCL multi-temporal composite verified on test holdout",
        }
        before = self.main_store_rows("mlops_approvals")
        resp = self.client.post("/v1/mlops/approval", json=payload)
        self.assertEqual(resp.status_code, 409)
        detail = resp.json()["detail"]
        self.assertEqual(detail["status"], "blocked")
        self.assertEqual(
            detail["reason_code"],
            "BLOCKED_NO_VERIFIED_CANDIDATE_OR_HUMAN_APPROVAL_BASIS",
        )
        self.assertEqual(self.main_store_rows("mlops_approvals"), before)

    @staticmethod
    def main_store_rows(kind):
        return main.store.list(kind)


if __name__ == "__main__":
    unittest.main()
