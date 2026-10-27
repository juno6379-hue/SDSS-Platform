"""Recovery calculations require pinned same-grid observed masks."""
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
import rasterio
from rasterio.transform import from_origin

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))
from app.ml.province_year_coverage import PinnedFile, ProvinceCoverageReport, ProvinceYearCoverage, sha256_file
from app.ml.recovery_rate_engine import ObservedMaskTransition, compute_recovery_metrics
from g5_recovery_rate_report import _metric as format_recovery_metric

PROVINCES = ["banten","west_java","east_java","south_sulawesi","gorontalo","southeast_sulawesi"]


def report(observed_area, source_sha="a"*64):
    boundary = 0.04; missing = boundary - observed_area
    observed_pct = 100 * observed_area / boundary
    cells = []
    for pid in PROVINCES:
        for year in range(2020, 2026):
            cells.append(ProvinceYearCoverage(
                pid, year, boundary, 1, 1, boundary, observed_area, missing,
                0, 0, 0, 0, missing, observed_pct, 100-observed_pct,
                "TESTED_SYNTHETIC", "BLOCKED_NOT_MEASURED", "fixture",
            ))
    return ProvinceCoverageReport("1.1", "now", "TESTED_SYNTHETIC", source_sha, "b"*64, "fixture", cells)


class TestRecoveryRateEngine(unittest.TestCase):
    def test_cli_formats_blocked_null_safely(self):
        self.assertEqual(format_recovery_metric(None, "%"), "null")
        self.assertEqual(format_recovery_metric(1.25, "%", 1), "1.2%")

    def test_default_is_blocked_and_null(self):
        summary = compute_recovery_metrics(ROOT)
        self.assertEqual(summary.evidence_status, "BLOCKED")
        self.assertEqual(summary.schema_version, "4.1")
        self.assertIsNone(summary.mean_after_valid_pct)
        self.assertEqual(len(summary.cells), 36)
        self.assertTrue(all(c.recovery_rate_pct is None for c in summary.cells))

    def test_aggregate_reports_do_not_claim_recovery(self):
        summary = compute_recovery_metrics(before_report=report(0.01), after_report=report(0.02, "c"*64))
        self.assertEqual(summary.evidence_status, "BLOCKED")
        self.assertEqual(summary.blocking_reason, "MISSING_SAME_GRID_OBSERVED_MASK_TRANSITIONS")
        self.assertEqual(summary.aggregate_change_status, "TESTED_SYNTHETIC")
        self.assertEqual(summary.mean_aggregate_net_coverage_change_pct_point, 25.0)
        self.assertAlmostEqual(summary.total_aggregate_net_observed_area_change_ha, 0.36)
        self.assertIsNone(summary.mean_increase_pct_point)
        self.assertIsNone(summary.total_newly_recovered_ha)
        self.assertIsNone(summary.mean_recovery_rate_pct)
        self.assertTrue(all(c.status.startswith("BLOCKED_") and c.newly_recovered_area_ha is None for c in summary.cells))

    def test_pinned_same_grid_masks_measure_difference(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); profile = dict(driver="GTiff",height=2,width=2,count=1,dtype="uint8",crs="EPSG:6933",transform=from_origin(0,20,10,10))
            before_path, after_path, boundary_path = root/"before.tif", root/"after.tif", root/"boundary.tif"
            for path, arr in [
                (before_path, np.array([[1,0],[0,0]],dtype="uint8")),
                (after_path, np.array([[1,1],[0,0]],dtype="uint8")),
                (boundary_path, np.ones((2,2),dtype="uint8")),
            ]:
                with rasterio.open(path,"w",**profile) as ds: ds.write(arr,1)
            transitions = [ObservedMaskTransition(pid, year,
                PinnedFile(before_path,sha256_file(before_path)), PinnedFile(after_path,sha256_file(after_path)),
                PinnedFile(boundary_path,sha256_file(boundary_path))) for pid in PROVINCES for year in range(2020,2026)]
            summary = compute_recovery_metrics(before_report=report(0.01), after_report=report(0.02,"c"*64),
                                               observed_mask_transitions=transitions)
        self.assertEqual(summary.evidence_status,"TESTED_SYNTHETIC")
        self.assertIsNone(summary.blocking_reason)
        self.assertAlmostEqual(summary.total_newly_recovered_ha,0.36)
        self.assertAlmostEqual(summary.mean_recovery_rate_pct,33.3333,places=3)
        self.assertTrue(all(c.gap_reason_resolved=="PINNED_SAME_GRID_OBSERVED_MASK_DIFFERENCE" for c in summary.cells))

    def test_boundary_pin_must_match(self):
        after=report(0.02); after.boundary_sha256="c"*64
        with self.assertRaisesRegex(ValueError,"BOUNDARY_SHA256_MISMATCH"):
            compute_recovery_metrics(before_report=report(0.01),after_report=after)

    def test_duplicate_cell_and_bad_invariant_are_rejected(self):
        before=report(0.01); before.cells.append(before.cells[0])
        with self.assertRaisesRegex(ValueError,"DUPLICATE_CELL"):
            compute_recovery_metrics(before_report=before,after_report=report(0.02))
        before=report(0.01); before.cells[0].missing_area_ha=0
        with self.assertRaisesRegex(ValueError,"OBSERVED_MISSING_INVARIANT"):
            compute_recovery_metrics(before_report=before,after_report=report(0.02))


if __name__ == "__main__": unittest.main()
