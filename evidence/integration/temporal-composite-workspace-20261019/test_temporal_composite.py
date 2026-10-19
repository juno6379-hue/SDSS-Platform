"""
Unit tests for Temporal Composite & Cloud-Masking Pipeline.
Workspace: evidence/integration/temporal-composite-workspace-20261019/test_temporal_composite.py
"""

import copy
import math
import unittest
import numpy as np

from composite_pipeline import (
    SCLMaskEvaluator,
    TemporalCompositeEngine,
    AnnualPolicyValidator,
    SyntheticSliceGenerator,
    AnnualCellBatchRunner,
    MultiTemporalConsistencyChecker,
    SCL_CLASSES,
    INVALID_SCL_CODES,
    VALID_SCL_CODES,
    PROVINCES,
    YEARS,
    BANDS,
)


class TestSCLMaskEvaluator(unittest.TestCase):
    """Tests SCL class interpretation, binary quality mask creation, and count contracts."""

    def test_all_12_scl_classes_exact_classification(self):
        """Verify each of the 12 SCL classes maps exactly to valid or invalid."""
        # 12 classes arranged in a 3x4 grid
        scl_grid = np.arange(12, dtype=np.uint8).reshape((3, 4))
        mask = SCLMaskEvaluator.compute_binary_mask(scl_grid)

        # Expected:
        # Invalid (0): 0 (nodata), 1 (defective), 3 (shadow), 8 (cloud med), 9 (cloud high), 10 (cirrus), 11 (snow)
        # Valid (1): 2 (dark features), 4 (vegetation), 5 (not-vegetated), 6 (water), 7 (unclassified)
        for code in range(12):
            r, c = divmod(code, 4)
            val = mask[r, c]
            if code in VALID_SCL_CODES:
                self.assertEqual(val, 1, f"SCL code {code} ({SCL_CLASSES[code]}) should be valid (1).")
            else:
                self.assertIn(code, INVALID_SCL_CODES)
                self.assertEqual(val, 0, f"SCL code {code} ({SCL_CLASSES[code]}) should be invalid (0).")

    def test_nodata_and_nan_spectral_override(self):
        """Even if SCL is vegetation (4), spectral nodata or NaN must force mask to 0."""
        scl = np.full((4, 4), 4, dtype=np.uint8)  # All vegetation
        band_validity = np.ones((4, 4), dtype=bool)
        band_validity[0, 0] = False  # Spectral nodata at (0, 0)
        band_validity[2, 3] = False  # Spectral nodata at (2, 3)

        mask = SCLMaskEvaluator.compute_binary_mask(scl, band_nodata_mask=band_validity)
        self.assertEqual(mask[0, 0], 0)
        self.assertEqual(mask[2, 3], 0)
        self.assertEqual(mask[1, 1], 1)
        self.assertEqual(int(np.count_nonzero(mask == 1)), 14)

    def test_evaluate_mask_counts_contract(self):
        """Mask counts dictionary must match backend/app/ml/annual_mask_policy.py schema."""
        mask = np.array([
            [1, 1, 0, 0],
            [1, 0, 0, 0],
            [1, 1, 1, 0],
            [1, 1, 1, 1],
        ], dtype=np.uint8)
        counts = SCLMaskEvaluator.evaluate_mask_counts(mask)

        self.assertEqual(counts["total_pixels"], 16)
        self.assertEqual(counts["valid_pixels"], 10)
        self.assertEqual(counts["invalid_pixels"], 6)
        self.assertEqual(counts["valid_ratio"], round(10 / 16, 6))

    def test_scl_distribution_breakdown(self):
        """Test calculation of SCL class percentages."""
        scl = np.array([
            [4, 4, 4, 4],
            [9, 9, 9, 9],
            [0, 0, 5, 5],
            [6, 6, 3, 10],
        ], dtype=np.uint8)
        dist = SCLMaskEvaluator.evaluate_scl_distribution(scl)
        self.assertEqual(dist["VEGETATION"]["count"], 4)
        self.assertEqual(dist["VEGETATION"]["percentage"], 25.0)
        self.assertEqual(dist["CLOUD_HIGH_PROBABILITY"]["count"], 4)
        self.assertEqual(dist["NO_DATA"]["count"], 2)


class TestTemporalCompositeEngine(unittest.TestCase):
    """Tests multi-temporal compositing algorithms and gap-filling logic."""

    def setUp(self):
        self.engine = TemporalCompositeEngine(default_method="median")

    def _make_dummy_slice(self, scl_val: int, red_val: float, nir_val: float, h: int = 4, w: int = 4, name: str = "s"):
        scl = np.full((h, w), scl_val, dtype=np.uint8)
        bands = {
            "blue": np.full((h, w), red_val * 0.8, dtype=np.float32),
            "green": np.full((h, w), red_val * 0.9, dtype=np.float32),
            "red": np.full((h, w), red_val, dtype=np.float32),
            "nir": np.full((h, w), nir_val, dtype=np.float32),
            "swir16": np.full((h, w), nir_val * 0.6, dtype=np.float32),
            "swir22": np.full((h, w), nir_val * 0.4, dtype=np.float32),
        }
        return {"scene_id": name, "datetime": "2023-06-01T00:00:00Z", "bands": bands, "scl": scl}

    def test_single_slice_identity(self):
        """With 1 clear slice, output bands and mask must strictly match that slice."""
        s1 = self._make_dummy_slice(scl_val=4, red_val=500.0, nir_val=3500.0)
        result = self.engine.composite_slice_stack([s1])
        
        self.assertTrue(np.all(result["quality_mask"] == 1))
        self.assertTrue(np.all(result["observation_count"] == 1))
        self.assertTrue(np.all(result["provenance_mask"] == 0))
        self.assertTrue(np.allclose(result["composite_bands"]["red"], 500.0))
        self.assertTrue(np.allclose(result["composite_bands"]["nir"], 3500.0))

    def test_temporal_median_filters_cloud_and_shadow_outliers(self):
        """
        In a 5-slice stack at a pixel:
        Slice 1: SCL 4, Red 500 (clear)
        Slice 2: SCL 4, Red 520 (clear)
        Slice 3: SCL 4, Red 490 (clear)
        Slice 4: SCL 9 (cloud, Red 6000) -> masked out
        Slice 5: SCL 3 (shadow, Red 100) -> masked out
        The median should be computed only over valid slices 1, 2, 3 (median of 490, 500, 520 = 500).
        """
        s1 = self._make_dummy_slice(4, 500.0, 3500.0, name="s1")
        s2 = self._make_dummy_slice(4, 520.0, 3550.0, name="s2")
        s3 = self._make_dummy_slice(4, 490.0, 3480.0, name="s3")
        s4 = self._make_dummy_slice(9, 6000.0, 6000.0, name="s4")  # Cloud
        s5 = self._make_dummy_slice(3, 100.0, 300.0, name="s5")    # Shadow

        result = self.engine.composite_slice_stack([s1, s2, s3, s4, s5])
        
        self.assertTrue(np.all(result["quality_mask"] == 1))
        self.assertTrue(np.all(result["observation_count"] == 3))  # 3 valid slices
        self.assertTrue(np.allclose(result["composite_bands"]["red"], 500.0))
        self.assertTrue(np.allclose(result["composite_bands"]["nir"], 3500.0))

    def test_gap_filling_from_fallback_adjacent_year(self):
        """
        Target year has 100% persistent cloud in all slices (N_valid = 0).
        Fallback slice from adjacent year has valid pixels.
        Test verifies:
        - Target cloud gap is filled from fallback.
        - Provenance mask marks filled pixels as 1 (gap filled).
        - Quality mask marks pixels as valid (1).
        - Persistent nodata (e.g. SCL 0 in both) remains 0 with provenance 2.
        """
        # Target year: 2 slices, both 100% cloud (SCL 9)
        t1 = self._make_dummy_slice(9, 7000.0, 7000.0, name="t1")
        t2 = self._make_dummy_slice(9, 7500.0, 7500.0, name="t2")

        # Fallback slice: mostly clear (SCL 4), but (0, 0) is true nodata (SCL 0)
        fb = self._make_dummy_slice(4, 600.0, 3200.0, name="fb")
        fb["scl"][0, 0] = 0
        fb["bands"]["red"][0, 0] = 0.0

        result = self.engine.composite_slice_stack(
            slices=[t1, t2],
            fallback_slices=[fb]
        )

        # (0, 0) was nodata in fallback -> remains persistent gap (0, prov=2)
        self.assertEqual(result["quality_mask"][0, 0], 0)
        self.assertEqual(result["provenance_mask"][0, 0], 2)
        self.assertEqual(result["composite_bands"]["red"][0, 0], 0.0)

        # All other pixels filled from fallback -> quality 1, prov 1
        self.assertEqual(result["quality_mask"][1, 1], 1)
        self.assertEqual(result["provenance_mask"][1, 1], 1)
        self.assertEqual(result["composite_bands"]["red"][1, 1], 600.0)
        self.assertEqual(result["metrics"]["gap_filled_pixels"], 15)
        self.assertEqual(result["metrics"]["persistent_gap_pixels"], 1)

    def test_medoid_and_max_ndvi_blending_options(self):
        """Verify medoid and max_ndvi blending execute without error and produce valid output."""
        s1 = self._make_dummy_slice(4, 500.0, 3000.0, name="s1")
        s2 = self._make_dummy_slice(4, 450.0, 3800.0, name="s2")  # Higher NDVI
        s3 = self._make_dummy_slice(4, 550.0, 2500.0, name="s3")

        # Medoid
        res_medoid = self.engine.composite_slice_stack([s1, s2, s3], method="medoid")
        self.assertTrue(np.all(res_medoid["quality_mask"] == 1))
        self.assertEqual(res_medoid["metrics"]["blending_method"], "medoid")

        # Max NDVI: should pick s2 since it has highest NDVI
        res_ndvi = self.engine.composite_slice_stack([s1, s2, s3], method="max_ndvi")
        self.assertTrue(np.all(res_ndvi["quality_mask"] == 1))
        self.assertTrue(np.allclose(res_ndvi["composite_bands"]["nir"], 3800.0))
        self.assertTrue(np.allclose(res_ndvi["composite_bands"]["red"], 450.0))


class TestAnnualPolicyValidator(unittest.TestCase):
    """Tests exact integer rational policy evaluation."""

    def test_exact_rational_boundaries(self):
        # 65 / 100 threshold
        # 649 out of 1000 = 64.9% < 65% -> NOT MET
        res1 = AnnualPolicyValidator.evaluate_policy(649, 1000, 65, 100)
        self.assertFalse(res1["caller_policy_met"])
        self.assertEqual(res1["deficit_pixels"], 1)

        # 650 out of 1000 = 65.0% == 65% -> MET
        res2 = AnnualPolicyValidator.evaluate_policy(650, 1000, 65, 100)
        self.assertTrue(res2["caller_policy_met"])
        self.assertEqual(res2["deficit_pixels"], 0)

        # 651 out of 1000 = 65.1% > 65% -> MET
        res3 = AnnualPolicyValidator.evaluate_policy(651, 1000, 65, 100)
        self.assertTrue(res3["caller_policy_met"])

    def test_fractional_precision_no_float_rounding_errors(self):
        # 1/3 threshold: 333333 / 1000000 = 33.3333% < 1/3 (333333 * 3 = 999999 < 1000000) -> NOT MET
        res1 = AnnualPolicyValidator.evaluate_policy(333333, 1000000, 1, 3)
        self.assertFalse(res1["caller_policy_met"])

        # 333334 / 1000000 -> (333334 * 3 = 1000002 >= 1000000) -> MET
        res2 = AnnualPolicyValidator.evaluate_policy(333334, 1000000, 1, 3)
        self.assertTrue(res2["caller_policy_met"])

    def test_invalid_policy_inputs_rejected(self):
        with self.assertRaises(ValueError):
            AnnualPolicyValidator.evaluate_policy(10, 100, 0, 0)  # denominator 0
        with self.assertRaises(ValueError):
            AnnualPolicyValidator.evaluate_policy(10, 100, -1, 10)  # negative numerator
        with self.assertRaises(ValueError):
            AnnualPolicyValidator.evaluate_policy(10, 100, 15, 10)  # numerator > denominator
        with self.assertRaises(ValueError):
            AnnualPolicyValidator.evaluate_policy(101, 100, 5, 10)  # valid > total


class TestMultiTemporalConsistency(unittest.TestCase):
    """Tests radiometric range and temporal smoothness validation."""

    def test_radiometric_bounds_pass_and_fail(self):
        good_bands = {
            "blue": np.full((8, 8), 400.0, dtype=np.float32),
            "red": np.full((8, 8), 500.0, dtype=np.float32),
        }
        res_good = MultiTemporalConsistencyChecker.check_radiometric_bounds(good_bands)
        self.assertTrue(res_good["passed"])

        bad_bands = {
            "blue": np.array([[np.nan, 400.0], [400.0, 400.0]], dtype=np.float32),
            "red": np.array([[12000.0, 500.0], [500.0, 500.0]], dtype=np.float32),
        }
        res_bad = MultiTemporalConsistencyChecker.check_radiometric_bounds(bad_bands)
        self.assertFalse(res_bad["passed"])
        self.assertEqual(len(res_bad["issues"]), 2)

    def test_temporal_smoothness_across_years(self):
        # Stable forest over 3 years: NIR 4000, Red 500 -> NDVI ~ 0.77
        h, w = 16, 16
        c2020 = {"nir": np.full((h, w), 4000.0, dtype=np.float32), "red": np.full((h, w), 500.0, dtype=np.float32)}
        c2021 = {"nir": np.full((h, w), 4100.0, dtype=np.float32), "red": np.full((h, w), 520.0, dtype=np.float32)}
        c2022 = {"nir": np.full((h, w), 3950.0, dtype=np.float32), "red": np.full((h, w), 490.0, dtype=np.float32)}

        res = MultiTemporalConsistencyChecker.check_temporal_smoothness([c2020, c2021, c2022], [2020, 2021, 2022])
        self.assertTrue(res["passed"])
        self.assertLess(res["overall_excessive_jump_rate"], 0.01)

        # Simulate year 2021 contaminated with unmasked cloud (NIR 7000, Red 6500 -> NDVI ~ 0.03)
        c2021_bad = {"nir": np.full((h, w), 7000.0, dtype=np.float32), "red": np.full((h, w), 6500.0, dtype=np.float32)}
        res_bad = MultiTemporalConsistencyChecker.check_temporal_smoothness([c2020, c2021_bad, c2022], [2020, 2021, 2022])
        self.assertFalse(res_bad["passed"])
        self.assertGreater(res_bad["overall_excessive_jump_rate"], 0.50)


class TestAnnualCellBatchRunner(unittest.TestCase):
    """Tests the full 36-cell batch execution across 6 provinces and 6 years."""

    def test_all_36_cells_evaluated_and_coverage_improved(self):
        runner = AnnualCellBatchRunner(
            provinces=PROVINCES,
            years=YEARS,
            grid_size=(16, 16),
            slices_per_year=4,
            policy_threshold=(65, 100)
        )
        report = runner.run_all_cells()

        self.assertEqual(report["schema_version"], 1)
        self.assertEqual(report["status"], "BATCH_VERIFICATION_COMPLETE")
        self.assertEqual(report["cell_matrix"]["total_expected_cells"], 36)
        self.assertEqual(report["cell_matrix"]["evaluated_cells"], 36)
        self.assertEqual(len(report["cell_results"]), 36)

        # Check aggregate metrics
        metrics = report["summary_metrics"]
        self.assertEqual(metrics["total_cells"], 36)
        self.assertGreater(metrics["mean_post_composite_valid_ratio"], metrics["mean_pre_composite_valid_ratio"])
        self.assertGreaterEqual(metrics["mean_gap_reduction_ratio"], 0.70)
        self.assertGreaterEqual(metrics["cell_policy_pass_rate"], 0.90)


if __name__ == "__main__":
    unittest.main()
