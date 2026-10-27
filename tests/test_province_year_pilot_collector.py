from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import rasterio
from rasterio.transform import from_origin

from backend.app.ml.province_year_pilot_collector import (
    _scl_quality, search_stac_with_retry, select_pilot_target,
)
from backend.app.ml.province_year_evidence_builder import PROVINCES, YEARS


class ProvinceYearPilotCollectorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_priority_selects_largest_outside_footprint_cell(self):
        cause = self.root / "cause.tif"
        with rasterio.open(
            cause, "w", driver="GTiff", width=5, height=5, count=1, dtype="uint8",
            crs="EPSG:6933", transform=from_origin(0, 5000, 1000, 1000),
        ) as dataset:
            dataset.write(np.array([
                [0, 0, 0, 0, 0],
                [0, 4, 4, 4, 0],
                [0, 4, 4, 4, 0],
                [0, 4, 4, 4, 0],
                [0, 0, 0, 0, 0],
            ], dtype="uint8"), 1)
        cells = []
        for province in PROVINCES:
            for year in YEARS:
                outside = 9 if (province, year) == ("east_java", 2023) else 1
                cells.append({
                    "province_id": province, "year": year,
                    "boundary_pixels": 25, "observed_pixels": 1,
                    "source_asset_count": 1, "cause_path": cause.name,
                    "cause_pixels": {"OUTSIDE_FOOTPRINT": outside},
                })
        manifest = self.root / "manifest.json"
        manifest.write_text(json.dumps({"cells": cells}), encoding="utf-8")
        result = select_pilot_target(manifest)
        self.assertEqual(result["selected"]["province_id"], "east_java")
        self.assertEqual(result["selected"]["year"], 2023)
        self.assertEqual(result["selected"]["cause"], "OUTSIDE_FOOTPRINT")
        self.assertGreaterEqual(result["selected"]["distance_from_existing_or_boundary_pixels_1km"], 1)

    def test_scl_quality_keeps_clear_and_cause_classes_separate(self):
        values = np.array([[4, 5, 8, 3], [6, 7, 9, 0]], dtype="uint8")
        result = _scl_quality(values)
        self.assertEqual(result["clear_pixels"], 4)
        self.assertEqual(result["cloud_pixels"], 2)
        self.assertEqual(result["shadow_pixels"], 1)
        self.assertEqual(result["nodata_pixels"], 1)
        self.assertEqual(result["quality_status"], "OBSERVATION_ELIGIBLE")

    def test_stac_transient_failure_retries_with_bound(self):
        sleeps = []
        with patch(
            "backend.app.ml.province_year_pilot_collector.service.search_stac",
            side_effect=[RuntimeError("transient"), {"items": []}],
        ) as search:
            result, audit = search_stac_with_retry(
                {"bbox": [1, 1, 2, 2]}, sleeper=lambda seconds: sleeps.append(seconds),
            )
        self.assertEqual(result, {"items": []})
        self.assertEqual(search.call_count, 2)
        self.assertEqual(sleeps, [1.0])
        self.assertEqual([row["status"] for row in audit], ["FAILED", "SUCCESS"])


if __name__ == "__main__":
    unittest.main()
