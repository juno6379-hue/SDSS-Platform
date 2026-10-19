"""Unit tests for G2 432 Province-Month Availability Audit Engine."""

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.ml.province_month_coverage_audit import (
    DRY_SEASON_MONTHS,
    FIRST_GROUP_6_PROVINCES,
    FIRST_GROUP_IDS,
    MONTHS,
    YEARS,
    ProvinceMonthAuditResult,
    build_province_month_audit,
)


class TestProvinceMonthCoverageAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = build_province_month_audit(ROOT / "data")

    def test_cell_matrix_dimensions(self):
        """Verify 432 cells total (6 provinces x 6 years x 12 months)."""
        self.assertEqual(len(self.result.cells), 432)
        self.assertEqual(self.result.total_cells, 432)
        self.assertEqual(self.result.dry_season_cells, 144)  # 6 x 6 x 4
        self.assertEqual(self.result.wet_season_cells, 288)  # 6 x 6 x 8

    def test_first_group_scope_only(self):
        """Verify strictly First Group 6 provinces and no unauthorized provinces."""
        observed_provs = {c.province_id for c in self.result.cells}
        self.assertEqual(observed_provs, FIRST_GROUP_IDS)
        self.assertEqual(len(self.result.province_rollups), 6)

    def test_years_and_months_completeness(self):
        """Verify each province has all 6 years and 12 months."""
        for p in FIRST_GROUP_IDS:
            p_cells = [c for c in self.result.cells if c.province_id == p]
            self.assertEqual(len(p_cells), 72)  # 6 years x 12 months
            years = {c.year for c in p_cells}
            self.assertEqual(years, set(YEARS))
            for y in YEARS:
                y_months = {c.month for c in p_cells if c.year == y}
                self.assertEqual(y_months, set(MONTHS))

    def test_patch_inventory_integrity(self):
        """Verify exact patch inventory: 1,779 patches, 1,407 eligible, 372 insufficient."""
        self.assertEqual(self.result.total_patches_inventory, 1779)
        self.assertEqual(self.result.total_eligible_patches, 1407)
        self.assertEqual(self.result.total_insufficient_patches, 372)
        self.assertAlmostEqual(self.result.overall_eligible_rate, 1407 / 1779, places=3)

    def test_active_observation_cells(self):
        """Verify 77 active acquisition cells during dry season windows."""
        self.assertEqual(self.result.active_observation_cells, 77)
        for c in self.result.cells:
            if c.discovered_scenes_count > 0:
                self.assertIn(c.month, DRY_SEASON_MONTHS)
                self.assertEqual(c.season_policy, "DRY_SEASON_WINDOW")
                self.assertEqual(c.measurement_status, "VERIFIED_REAL")
                self.assertIsNotNone(c.avg_scene_cloud_pct)
                self.assertIsNotNone(c.valid_coverage_pct)
            else:
                self.assertIn(c.measurement_status, {"NOT_MEASURED", "OUTSIDE_WINDOW"})

    def test_season_policy_taxonomy(self):
        """Verify dry season window policy vs monsoon wet season exclusion."""
        for c in self.result.cells:
            if c.month in DRY_SEASON_MONTHS:
                self.assertEqual(c.season_policy, "DRY_SEASON_WINDOW")
            else:
                self.assertEqual(c.season_policy, "WET_SEASON_MONSOON")
                self.assertEqual(c.measurement_status, "OUTSIDE_WINDOW")
                self.assertEqual(c.gap_reason, "WET_SEASON_PERSISTENT_CLOUD_EXCLUSION")

    def test_serialization_dict(self):
        """Verify to_dict produces valid serializable dictionary."""
        d = self.result.to_dict()
        self.assertEqual(d["total_cells"], 432)
        self.assertEqual(len(d["cells"]), 432)
        self.assertEqual(len(d["province_rollups"]), 6)
        self.assertEqual(len(d["year_rollups"]), 6)


if __name__ == "__main__":
    unittest.main()
