"""Unit tests for MLOps FastAPI Router endpoints."""

from pathlib import Path
import sys
import unittest

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.main import app


class TestMlopsRouter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_mlops_summary_endpoint(self):
        """Verify GET /v1/mlops/summary returns KPIs, models, and monitoring."""
        resp = self.client.get("/v1/mlops/summary")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")

        # KPIs
        kpis = data["kpis"]
        self.assertIn("models_in_production", kpis)
        self.assertEqual(kpis["models_in_production"]["value"], 6)
        self.assertIn("mean_f1_score", kpis)
        self.assertIn("mean_miou", kpis)

        # 6 models
        models = data["models"]
        self.assertEqual(len(models), 6)
        model_ids = {m["id"] for m in models}
        self.assertIn("lcluc_segmentation", model_ids)
        self.assertIn("climate_interpolation", model_ids)

        # 9 pipeline steps
        pipeline = data["pipeline_steps"]
        self.assertEqual(len(pipeline), 9)

        # Deployments
        deployments = data["deployments"]
        self.assertIn("dev", deployments)
        self.assertIn("staging", deployments)
        self.assertIn("production", deployments)
        self.assertIn("geoserver", deployments)

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
        """Verify GET /v1/mlops/recovery-rate returns 36 cells and >98% recovery."""
        resp = self.client.get("/v1/mlops/recovery-rate")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")
        summary = data["recovery_summary"]
        self.assertEqual(summary["total_cells"], 36)
        self.assertGreater(summary["mean_after_valid_pct"], 98.0)
        self.assertGreater(summary["mean_recovery_rate_pct"], 95.0)

    def test_mlops_retrain_trigger(self):
        """Verify POST /v1/mlops/retrain triggers and enqueues job."""
        payload = {
            "model_id": "flood_drought_hazard",
            "target_version": "v1.0.5",
            "dataset_version": "fg-annual-2020-2025-v2",
            "epochs": 40,
            "holdout_split": "test_west_java_val_banten",
        }
        resp = self.client.post("/v1/mlops/retrain", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("job_id", data)
        self.assertTrue(data["job_id"].startswith("retrain-flood_drought_hazard-"))
        self.assertEqual(data["job"]["status"], "queued")

    def test_mlops_approval_request(self):
        """Verify POST /v1/mlops/approval submits approval request."""
        payload = {
            "model_id": "lcluc_segmentation",
            "version": "v1.2.1",
            "target_env": "production",
            "requested_by": "Senior GeoAI Engineer",
            "rationale": "99.2% SCL multi-temporal composite verified on test holdout",
        }
        resp = self.client.post("/v1/mlops/approval", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("ticket_id", data)
        self.assertTrue(data["ticket_id"].startswith("APP-"))
        self.assertEqual(data["approval"]["status"], "검토 중")


if __name__ == "__main__":
    unittest.main()
