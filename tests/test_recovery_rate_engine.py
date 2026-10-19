"""Unit tests for G5 Recovery Rate Engine."""

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.ml.recovery_rate_engine import (
    PROVINCE_LAND_AREAS_HA,
    PROVINCE_METADATA,
    RecoverySummary,
    compute_recovery_metrics,
)


class TestRecoveryRateEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = compute_recovery_metrics(ROOT)

    def test_cells_count(self):
        """Verify exactly 36 cells (6 provinces x 6 years)."""
        self.assertEqual(len(self.summary.cells), 36)
        self.assertEqual(self.summary.total_cells, 36)

    def test_province_rollups_count(self):
        """Verify exactly 6 province rollups matching First Group 6."""
        self.assertEqual(len(self.summary.province_rollups), 6)
        prov_ids = {r.province_id for r in self.summary.province_rollups}
        self.assertEqual(prov_ids, set(PROVINCE_METADATA.keys()))

    def test_mathematical_consistency(self):
        """Verify CODEX Section 4.1 formulas: A_after = A_old + recovered; missing = total - A_after."""
        for c in self.summary.cells:
            # before_valid + newly_recovered == after_valid
            self.assertAlmostEqual(
                c.before_valid_area_ha + c.newly_recovered_area_ha,
                c.after_valid_area_ha,
                delta=1.0,
            )
            # after_valid + still_missing == total_land_area
            self.assertAlmostEqual(
                c.after_valid_area_ha + c.still_missing_area_ha,
                c.total_land_area_ha,
                delta=1.0,
            )
            # increase %p == after_pct - before_pct
            self.assertAlmostEqual(
                c.coverage_increase_pct_point,
                c.after_valid_coverage_pct - c.before_valid_coverage_pct,
                delta=0.05,
            )
            # recovery rate between 90% and 100%
            self.assertGreaterEqual(c.recovery_rate_pct, 90.0)
            self.assertLessEqual(c.recovery_rate_pct, 100.0)

    def test_mean_performance_bounds(self):
        """Verify composite coverage exceeds 98% and recovery rate exceeds 95%."""
        self.assertGreater(self.summary.mean_after_valid_pct, 98.0)
        self.assertGreater(self.summary.mean_increase_pct_point, 40.0)
        self.assertGreater(self.summary.mean_recovery_rate_pct, 95.0)

    def test_to_dict_serialization(self):
        """Verify to_dict returns serializable JSON dictionary."""
        d = self.summary.to_dict()
        self.assertIn("mean_before_valid_pct", d)
        self.assertIn("mean_after_valid_pct", d)
        self.assertIn("mean_increase_pct_point", d)
        self.assertEqual(len(d["cells"]), 36)
        self.assertEqual(len(d["province_rollups"]), 6)


if __name__ == "__main__":
    unittest.main()
