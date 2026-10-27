"""Deterministic synthetic tests for pinned province coverage measurement."""
from pathlib import Path
import json
import sys
import tempfile
import unittest

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.transform import from_origin

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.ml.province_year_coverage import (
    BOUNDARY_SCHEMA_VERSION, CAUSE_MASK_POLICY_VERSION, CAUSE_MASK_SEMANTICS,
    QUALITY_MASK_POLICY_VERSION, QUALITY_MASK_SEMANTICS, SOURCE_SCHEMA_VERSION,
    CoverageEvidenceError, PinnedFile, measure_province_year_coverage, sha256_file,
)

PROVINCES = ["banten","west_java","east_java","south_sulawesi","gorontalo","southeast_sulawesi"]
YEARS = list(range(2020, 2026))


class TestProvinceYearCoverage(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)
        transform = from_origin(0, 20, 10, 10)
        profile = dict(driver="GTiff", height=2, width=2, count=1, dtype="uint8", crs="EPSG:6933", transform=transform)
        self.quality, self.cause = self.root / "quality.tif", self.root / "cause.tif"
        with rasterio.open(self.quality, "w", **profile) as ds:
            ds.write(np.array([[1, 0], [0, 0]], dtype="uint8"), 1)
        with rasterio.open(self.cause, "w", **profile) as ds:
            ds.write(np.array([[0, 1], [2, 3]], dtype="uint8"), 1)
        inv = Transformer.from_crs("EPSG:6933", "EPSG:4326", always_xy=True)
        ring = [inv.transform(x, y) for x, y in [(0,0),(20,0),(20,20),(0,20),(0,0)]]
        boundaries = {
            "type":"FeatureCollection", "schema_version":BOUNDARY_SCHEMA_VERSION,
            "crs":{"type":"name","properties":{"name":"EPSG:4326"}},
            "features":[{"type":"Feature","properties":{"province_id":p},
                         "geometry":{"type":"Polygon","coordinates":[ring]}} for p in PROVINCES],
        }
        self.boundary = self.root / "boundaries.geojson"
        self.boundary.write_text(json.dumps(boundaries), encoding="utf-8")
        rows = []
        for p in PROVINCES:
            for y in YEARS:
                rows.append({
                    "province":p, "year":str(y), "scene_id":f"{p}-{y}", "patch_id":f"{p}-{y}-p0",
                    "quality_status":"quality_eligible", "quality_mask_path":str(self.quality),
                    "patch_sha256":{"quality":sha256_file(self.quality)},
                    "quality_mask_contract":{"semantics":QUALITY_MASK_SEMANTICS,"version":QUALITY_MASK_POLICY_VERSION,"nodata":None},
                    "coverage_cause_mask":{"path":str(self.cause),"sha256":sha256_file(self.cause)},
                    "coverage_cause_contract":{"semantics":CAUSE_MASK_SEMANTICS,"version":CAUSE_MASK_POLICY_VERSION,"nodata":None},
                })
        self.source = self.root / "source.json"
        self.source.write_text(json.dumps({"schema_version":SOURCE_SCHEMA_VERSION,"scenes":rows}), encoding="utf-8")

    def tearDown(self): self.tmp.cleanup()

    def measure(self):
        return measure_province_year_coverage(
            root=self.root, source=PinnedFile(self.source, sha256_file(self.source)),
            boundaries=PinnedFile(self.boundary, sha256_file(self.boundary)),
            expected_provinces=PROVINCES, expected_years=YEARS, evidence_status="TESTED_SYNTHETIC",
        )

    def _rewrite_rows(self, mutate):
        doc = json.loads(self.source.read_text(encoding="utf-8")); mutate(doc["scenes"])
        self.source.write_text(json.dumps(doc), encoding="utf-8")

    def test_36_cells_and_invalid_causes_block_completeness(self):
        report = self.measure(); self.assertEqual(report.schema_version, "1.1"); self.assertEqual(len(report.cells), 36)
        for cell in report.cells:
            self.assertAlmostEqual(cell.observed_coverage_pct, 25.0, delta=0.5)
            self.assertAlmostEqual(cell.cloud_area_ha, cell.shadow_area_ha, delta=0.002)
            self.assertAlmostEqual(cell.shadow_area_ha, cell.nodata_area_ha, delta=0.002)
            self.assertTrue(cell.readiness_status.startswith("BLOCKED_"))
            self.assertNotEqual(cell.readiness_status, "COVERAGE_COMPLETE")

    def test_complete_requires_full_observed_boundary(self):
        with rasterio.open(self.quality, "r+") as ds:
            ds.write(np.ones((2,2), dtype="uint8"), 1)
        with rasterio.open(self.cause, "r+") as ds:
            ds.write(np.zeros((2,2), dtype="uint8"), 1)
        self._rewrite_rows(lambda rows: [(
            r["patch_sha256"].update(quality=sha256_file(self.quality)),
            r["coverage_cause_mask"].update(sha256=sha256_file(self.cause)),
        ) for r in rows])
        self.assertTrue(all(c.readiness_status == "COVERAGE_COMPLETE" for c in self.measure().cells))

    def test_source_sha_mismatch_fails_before_measurement(self):
        with self.assertRaisesRegex(CoverageEvidenceError, "SHA256_MISMATCH"):
            measure_province_year_coverage(root=self.root, source=PinnedFile(self.source, "0"*64),
                boundaries=PinnedFile(self.boundary, sha256_file(self.boundary)), expected_provinces=PROVINCES, expected_years=YEARS)

    def test_missing_cause_mask_is_not_guessed(self):
        self._rewrite_rows(lambda rows: [(r.pop("coverage_cause_mask"), r.pop("coverage_cause_contract")) for r in rows])
        report = self.measure()
        self.assertEqual(report.cause_semantics, "QUALITY_MASK_ONLY_INVALID_CAUSE_IS_NOT_MEASURED")
        self.assertTrue(all(c.not_measured_area_ha > 0 and "NOT_MEASURED" in c.readiness_status for c in report.cells))

    def test_non_binary_quality_mask_is_rejected(self):
        with rasterio.open(self.quality, "r+") as ds:
            ds.write(np.array([[2,0],[0,0]], dtype="uint8"), 1)
        self._rewrite_rows(lambda rows: [r["patch_sha256"].update(quality=sha256_file(self.quality)) for r in rows])
        with self.assertRaisesRegex(CoverageEvidenceError, "VALUE_DOMAIN_INVALID"):
            self.measure()

    def test_quality_mask_nodata_must_match_contract(self):
        with rasterio.open(self.quality, "r+") as ds:
            ds.nodata = 255
        self._rewrite_rows(lambda rows: [r["patch_sha256"].update(quality=sha256_file(self.quality)) for r in rows])
        with self.assertRaisesRegex(CoverageEvidenceError, "NODATA_MUST_BE_UNSET"):
            self.measure()

    def test_duplicate_patch_is_rejected(self):
        self._rewrite_rows(lambda rows: rows.append(dict(rows[0])))
        with self.assertRaisesRegex(CoverageEvidenceError, "DUPLICATE_PATCH_ID"):
            self.measure()

    def test_unknown_quality_status_is_rejected(self):
        self._rewrite_rows(lambda rows: rows[0].update(quality_status="unknown"))
        with self.assertRaisesRegex(CoverageEvidenceError, "QUALITY_STATUS_UNKNOWN"):
            self.measure()


if __name__ == "__main__": unittest.main()
