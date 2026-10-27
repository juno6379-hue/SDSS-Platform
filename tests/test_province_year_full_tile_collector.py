from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from backend.app.ml.province_year_coverage import PinnedFile, sha256_file
from backend.app.ml.province_year_full_tile_collector import (
    FULL_TILE_DECISION_SCHEMA,
    FULL_TILE_MAX_SIDE,
    FULL_TILE_RESERVATION_BYTES,
    FullTileCollectionError,
    validate_full_tile_decision,
)


class ProvinceYearFullTileCollectorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "decision.json"
        self.boundary_sha = "1" * 64
        self.mosaic_sha = "2" * 64
        self.report_sha = "3" * 64
        self.document = {
            "schema_version": FULL_TILE_DECISION_SCHEMA,
            "authorized_by": "USER_EXPLICIT_INSTRUCTION",
            "decision": "RUN_ONE_FULL_TILE_STRATEGY_PILOT",
            "batch_key": "unit366-fulltile-east_java-2021-01",
            "boundary_sha256": self.boundary_sha,
            "starting_mosaic_sha256": self.mosaic_sha,
            "source_report_sha256": self.report_sha,
            "scene_id": "scene",
            "province_id": "east_java",
            "year": 2021,
            "source_window_observed_gain_pixels": 1606,
            "policy": {
                "max_full_tiles": 1,
                "reservation_bytes": FULL_TILE_RESERVATION_BYTES,
                "max_side": FULL_TILE_MAX_SIDE,
                "stop_on_failure": True,
            },
            "approvals": {
                "collection_pilot": True,
                "automatic_training": False,
                "automatic_deployment": False,
            },
        }

    def tearDown(self):
        self.tmp.cleanup()

    def _pin(self):
        self.path.write_text(json.dumps(self.document), encoding="utf-8")
        return PinnedFile(self.path, sha256_file(self.path))

    def test_decision_preserves_approval_boundary(self):
        result = validate_full_tile_decision(
            self._pin(),
            boundary_sha256=self.boundary_sha,
            starting_mosaic_sha256=self.mosaic_sha,
            source_report_sha256=self.report_sha,
        )
        self.assertFalse(result["approvals"]["automatic_training"])
        self.assertFalse(result["approvals"]["automatic_deployment"])

    def test_batch_growth_is_rejected(self):
        self.document["policy"]["max_full_tiles"] = 2
        with self.assertRaisesRegex(FullTileCollectionError, "POLICY_MISMATCH"):
            validate_full_tile_decision(
                self._pin(),
                boundary_sha256=self.boundary_sha,
                starting_mosaic_sha256=self.mosaic_sha,
                source_report_sha256=self.report_sha,
            )

    def test_source_report_pin_drift_is_rejected(self):
        with self.assertRaisesRegex(FullTileCollectionError, "SOURCE_REPORT_SHA_MISMATCH"):
            validate_full_tile_decision(
                self._pin(),
                boundary_sha256=self.boundary_sha,
                starting_mosaic_sha256=self.mosaic_sha,
                source_report_sha256="4" * 64,
            )

    def test_invalid_source_window_gain_is_rejected(self):
        self.document["source_window_observed_gain_pixels"] = True
        with self.assertRaisesRegex(FullTileCollectionError, "SOURCE_WINDOW_GAIN_INVALID"):
            validate_full_tile_decision(
                self._pin(),
                boundary_sha256=self.boundary_sha,
                starting_mosaic_sha256=self.mosaic_sha,
                source_report_sha256=self.report_sha,
            )


if __name__ == "__main__":
    unittest.main()
