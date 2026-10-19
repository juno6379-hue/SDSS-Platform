"""Root unit tests for First Group 6 Collection Status & Degraded Quality Tracker."""

import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "evidence/integration/target334-workspace-20261019/scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from track_collection_quality import (
    FIRST_GROUP_6_PROVINCES,
    FIRST_GROUP_IDS,
    REJECTED_PROVINCES,
    YEARS,
    CollectionQualityTracker,
)


class TestCollectionQualityTrackerRoot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tracker = CollectionQualityTracker(data_root=ROOT)
        cls.report = cls.tracker.build_tracker_report()
        cls.json_path_target = ROOT / "evidence/integration/target334-workspace-20261019/collection_quality_status.json"
        cls.json_path_data = ROOT / "data/collection_quality_status.json"

    def test_scope_first_group_6_only(self):
        """Verify that scope strictly consists of First Group 6 provinces."""
        expected_ids = {"banten", "west_java", "east_java", "south_sulawesi", "gorontalo", "southeast_sulawesi"}
        self.assertEqual(FIRST_GROUP_IDS, expected_ids)
        self.assertEqual(len(FIRST_GROUP_6_PROVINCES), 6)

        # Check rejected provinces list contains Central Java and Papua
        rejected_ids = {p["id"] for p in REJECTED_PROVINCES}
        self.assertIn("central_java", rejected_ids)
        self.assertIn("papua", rejected_ids)
        self.assertIn("dki_jakarta", rejected_ids)
        self.assertIn("east_kalimantan", rejected_ids)

        for pid in expected_ids:
            self.assertTrue(self.tracker.validate_scope(pid))
        self.assertFalse(self.tracker.validate_scope("central_java"))
        self.assertFalse(self.tracker.validate_scope("papua"))

    def test_36_cells_structure_and_coverage(self):
        """Verify exactly 36 cells (6 provinces x 6 years: 2020-2025)."""
        cells = self.report.get("cells_36", [])
        self.assertEqual(len(cells), 36)

        cell_keys = {(c["province"], c["year"]) for c in cells}
        expected_keys = {(p["id"], y) for p in FIRST_GROUP_6_PROVINCES for y in YEARS}
        self.assertEqual(cell_keys, expected_keys)

    def test_patch_inventory_totals(self):
        """Verify patch inventory totals: 1,779 patches, 1,407 eligible, 372 insufficient."""
        summary = self.report.get("summary", {})
        self.assertEqual(summary.get("total_cells"), 36)
        self.assertEqual(summary.get("total_patches"), 1779)
        self.assertEqual(summary.get("eligible_patches"), 1407)
        self.assertEqual(summary.get("insufficient_patches"), 372)

    def test_degraded_zones_identification(self):
        """Verify degraded quality zones detection criteria and flagged cells."""
        registry = self.report.get("degraded_zones_registry", {})
        zones = registry.get("zones", [])
        self.assertTrue(len(zones) >= 10, "Expected at least 10 degraded cells")

    def test_scl_metrics_validity(self):
        """Verify SCL atmospheric interference percentages are within logical bounds."""
        for cell in self.report["cells_36"]:
            scl = cell["scl_atmospheric_percentages"]
            self.assertGreaterEqual(scl["cloud_shadow_pct"], 0.0)
            self.assertLessEqual(scl["cloud_shadow_pct"], 100.0)
            self.assertGreaterEqual(scl["high_proba_cloud_pct"], 0.0)
            self.assertLessEqual(scl["high_proba_cloud_pct"], 100.0)

    def test_provenance_matrix_and_year_integrity(self):
        """Verify provenance matrix details, WorldCover availability, and zero temporal drift."""
        prov_mat = self.report.get("provenance_matrix", {})
        self.assertEqual(prov_mat["T1_baseline_years"], [2020, 2021])
        self.assertEqual(prov_mat["T2_monitoring_years"], [2022, 2023, 2024, 2025])

        integrity = prov_mat["observation_year_integrity"]
        self.assertEqual(integrity["discrepancies_count"], 0)
        self.assertEqual(integrity["verification_status"], "VERIFIED_MATCH")

    def test_persisted_json_files(self):
        """Verify that JSON status files exist and match."""
        self.assertTrue(self.json_path_target.exists(), f"Target JSON missing at {self.json_path_target}")
        self.assertTrue(self.json_path_data.exists(), f"Data JSON missing at {self.json_path_data}")

        d1 = json.loads(self.json_path_target.read_text(encoding="utf-8"))
        d2 = json.loads(self.json_path_data.read_text(encoding="utf-8"))

        self.assertEqual(d1["summary"], d2["summary"])
        self.assertEqual(len(d1["cells_36"]), 36)
        self.assertEqual(len(d2["cells_36"]), 36)


if __name__ == "__main__":
    unittest.main()
