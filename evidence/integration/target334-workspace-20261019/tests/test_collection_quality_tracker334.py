import json
from pathlib import Path
import sys
import unittest

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE / "scripts"))

from track_collection_quality import (
    FIRST_GROUP_6_PROVINCES,
    FIRST_GROUP_IDS,
    REJECTED_PROVINCES,
    YEARS,
    CollectionQualityTracker,
)

ROOT = Path(__file__).resolve().parents[4]


class TestCollectionQualityTracker(unittest.TestCase):
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

        # Verify tracker validation method
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

        for cell in cells:
            self.assertIn("cell_id", cell)
            self.assertIn("province", cell)
            self.assertIn("year", cell)
            self.assertIn("period", cell)
            self.assertIn(cell["period"], ("T1_BASELINE", "T2_MONITORING"))
            self.assertIn("quality_status", cell)
            self.assertIn(cell["quality_status"], ("NOMINAL", "DEGRADED"))
            self.assertIn("patches", cell)
            self.assertIn("cloud_metrics", cell)
            self.assertIn("scl_atmospheric_percentages", cell)
            self.assertIn("valid_pixel_metrics", cell)
            self.assertIn("satellite_acquisition", cell)
            self.assertIn("provenance", cell)

    def test_patch_inventory_totals(self):
        """Verify patch inventory totals: 1,779 patches, 1,407 eligible, 372 insufficient."""
        summary = self.report.get("summary", {})
        self.assertEqual(summary.get("total_cells"), 36)
        self.assertEqual(summary.get("total_patches"), 1779)
        self.assertEqual(summary.get("eligible_patches"), 1407)
        self.assertEqual(summary.get("insufficient_patches"), 372)

        # Verify sum of patch counts matches cell sum
        cells = self.report.get("cells_36", [])
        sum_total = sum(c["patches"]["total"] for c in cells)
        sum_eligible = sum(c["patches"]["quality_eligible"] for c in cells)
        sum_insufficient = sum(c["patches"]["quality_insufficient"] for c in cells)
        self.assertEqual(sum_total, 1779)
        self.assertEqual(sum_eligible, 1407)
        self.assertEqual(sum_insufficient, 372)

    def test_degraded_zones_identification(self):
        """Verify degraded quality zones detection criteria and flagged cells."""
        registry = self.report.get("degraded_zones_registry", {})
        zones = registry.get("zones", [])
        self.assertTrue(len(zones) >= 10, "Expected at least 10 degraded cells")

        # Specific known severely degraded cells:
        # Southeast Sulawesi 2024: high cloud (19.7%), severe shadow (7.3%), valid ratio 0.70
        se_2024 = [z for z in zones if z["cell_id"] == "southeast_sulawesi_2024"]
        self.assertEqual(len(se_2024), 1)
        self.assertGreater(se_2024[0]["avg_cloud_cover_pct"], 18.0)
        self.assertGreater(se_2024[0]["avg_cloud_shadow_pct"], 5.0)

        # South Sulawesi 2022: high cloud (16.9%), high shadow (5.4%)
        ss_2022 = [z for z in zones if z["cell_id"] == "south_sulawesi_2022"]
        self.assertEqual(len(ss_2022), 1)
        self.assertGreater(ss_2022[0]["avg_cloud_cover_pct"], 15.0)

        # Gorontalo 2021: high cloud (18.2%)
        gor_2021 = [z for z in zones if z["cell_id"] == "gorontalo_2021"]
        self.assertEqual(len(gor_2021), 1)
        self.assertGreater(gor_2021[0]["avg_cloud_cover_pct"], 17.0)

    def test_scl_metrics_validity(self):
        """Verify SCL atmospheric interference percentages are within logical bounds."""
        for cell in self.report["cells_36"]:
            scl = cell["scl_atmospheric_percentages"]
            self.assertGreaterEqual(scl["cloud_shadow_pct"], 0.0)
            self.assertLessEqual(scl["cloud_shadow_pct"], 100.0)
            self.assertGreaterEqual(scl["high_proba_cloud_pct"], 0.0)
            self.assertLessEqual(scl["high_proba_cloud_pct"], 100.0)
            self.assertGreaterEqual(scl["medium_proba_cloud_pct"], 0.0)
            self.assertLessEqual(scl["medium_proba_cloud_pct"], 100.0)
            self.assertGreaterEqual(scl["thin_cirrus_pct"], 0.0)
            self.assertLessEqual(scl["thin_cirrus_pct"], 100.0)

            valid = cell["valid_pixel_metrics"]
            self.assertGreaterEqual(valid["avg_valid_pixel_ratio"], 0.0)
            self.assertLessEqual(valid["avg_valid_pixel_ratio"], 1.0)

    def test_provenance_matrix_and_year_integrity(self):
        """Verify provenance matrix details, WorldCover availability, and zero temporal drift."""
        prov_mat = self.report.get("provenance_matrix", {})
        self.assertEqual(prov_mat["T1_baseline_years"], [2020, 2021])
        self.assertEqual(prov_mat["T2_monitoring_years"], [2022, 2023, 2024, 2025])

        # ESA WorldCover: confirmed not released for 2022-2025
        wc = prov_mat["label_datasets"]["esa_worldcover_10m"]
        self.assertIn("Not released by ESA", wc["official_versions"]["2022_to_2025"])

        # Temporal integrity: zero discrepancies
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
