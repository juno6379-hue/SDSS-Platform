from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from backend.app.ml.province_year_collection_orchestrator import (
    AUTOMATED_BATCH_SIZE,
    AUTOMATED_RESERVATION_BYTES,
    AUTOMATED_WINDOW_SIDE,
    CollectionOrchestrationError,
    estimate_remaining_scale,
    validate_orchestration_decision,
)
from backend.app.ml.province_year_coverage import PinnedFile, sha256_file


class ProvinceYearCollectionOrchestratorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.decision = self.root / "decision.json"
        self.boundary_sha = "1" * 64
        self.mosaic_sha = "2" * 64
        self.document = {
            "schema_version": "province-year-collection-orchestration-decision/1.0",
            "authorized_by": "USER_EXPLICIT_INSTRUCTION",
            "decision": "AUTOMATE_GAP_COLLECTION_WITH_APPROVAL_GATED_TRAINING_DEPLOYMENT",
            "batch_run_id": "unit365-auto-retry1",
            "boundary_sha256": self.boundary_sha,
            "starting_mosaic_sha256": self.mosaic_sha,
            "policy": {
                "max_windows_per_batch": AUTOMATED_BATCH_SIZE,
                "window_side_scl20m": AUTOMATED_WINDOW_SIDE,
                "reservation_bytes_per_window": AUTOMATED_RESERVATION_BYTES,
                "stop_on_first_failure": True,
                "stop_on_http_429": True,
                "distinct_province_year_per_batch": True,
            },
            "approvals": {
                "collection_batch": True,
                "automatic_training": False,
                "automatic_deployment": False,
            },
        }

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self):
        self.decision.write_text(json.dumps(self.document), encoding="utf-8")
        return PinnedFile(self.decision, sha256_file(self.decision))

    def test_decision_keeps_training_and_deployment_approval_gated(self):
        result = validate_orchestration_decision(
            self._write(), boundary_sha256=self.boundary_sha,
            starting_mosaic_sha256=self.mosaic_sha,
        )
        self.assertFalse(result["approvals"]["automatic_training"])
        self.assertFalse(result["approvals"]["automatic_deployment"])

    def test_policy_drift_is_rejected(self):
        self.document["policy"]["max_windows_per_batch"] = 4
        with self.assertRaisesRegex(CollectionOrchestrationError, "POLICY_MISMATCH"):
            validate_orchestration_decision(
                self._write(), boundary_sha256=self.boundary_sha,
                starting_mosaic_sha256=self.mosaic_sha,
            )

    def test_scale_estimate_is_explicitly_rough(self):
        manifest = self.root / "manifest.json"
        manifest.write_text(json.dumps({
            "cells": [{"cause_pixels": {"OUTSIDE_FOOTPRINT": 1600}}],
        }), encoding="utf-8")
        result = estimate_remaining_scale(manifest)
        self.assertEqual(result["planning_gain_pixels_per_2048_window"], 1600)
        self.assertEqual(result["rough_windows_to_full_inventory_coverage"], 1)
        self.assertTrue(result["estimate_limitations"])


if __name__ == "__main__":
    unittest.main()
