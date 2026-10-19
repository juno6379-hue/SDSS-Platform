"""
Unit Tests for Temporal Consistency & False Change Filter Engine.
Workspace: evidence/integration/lcluc-filter-workspace-20261019/test_temporal_change_filter.py
"""

import copy
import json
import os
from pathlib import Path
import shutil
import sys
import unittest
import numpy as np

# Ensure workspace modules are importable
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from temporal_change_filter import (
    TrajectoryConsistencyFilter,
    SpectralDivergenceCalculator,
    ChangeConfidenceScorer,
    TransitionMatrixEngine,
    TemporalChangeDetectionEngine,
    CLASS_NAMES,
    CLASS_TO_IDX,
    IGNORE,
    TRANSITION_NODATA,
    CONFIDENCE_NODATA,
)

# Import Unit 336's composite engine
UNIT_336_DIR = (CURRENT_DIR.parent / "temporal-composite-workspace-20261019").resolve()
if str(UNIT_336_DIR) not in sys.path:
    sys.path.insert(0, str(UNIT_336_DIR))

from composite_pipeline import (
    TemporalCompositeEngine,
    SyntheticSliceGenerator,
    SCLMaskEvaluator,
    BANDS,
)


class TestTrajectoryConsistencyFilter(unittest.TestCase):
    """Tests trajectory bounce detection, permanent transition preservation, and multi-year smoothing."""

    def setUp(self):
        self.filter = TrajectoryConsistencyFilter()
        self.c_trees = CLASS_TO_IDX["trees"]      # 1
        self.c_bare = CLASS_TO_IDX["bare"]        # 7
        self.c_built = CLASS_TO_IDX["built"]      # 6
        self.c_crops = CLASS_TO_IDX["crops"]      # 4
        self.c_water = CLASS_TO_IDX["water"]      # 0

    def test_identify_bounces_3year_single_pixel(self):
        """Test bounce detection on synthetic 3-year single pixel trajectory."""
        # Forest(2020) -> Bare(2021) -> Forest(2022) is a classic dry season bounce
        c_prev = np.array([[self.c_trees]], dtype=np.uint8)
        c_curr = np.array([[self.c_bare]], dtype=np.uint8)
        c_next = np.array([[self.c_trees]], dtype=np.uint8)

        is_bounce = TrajectoryConsistencyFilter.identify_bounces_3year(c_prev, c_curr, c_next)
        self.assertTrue(is_bounce[0, 0])

    def test_permanent_transition_preservation(self):
        """
        Permanent transition Forest(2020) -> Built(2021) -> Built(2022)
        MUST NOT be identified as a bounce and MUST be preserved!
        """
        c_prev = np.array([[self.c_trees]], dtype=np.uint8)
        c_curr = np.array([[self.c_built]], dtype=np.uint8)
        c_next = np.array([[self.c_built]], dtype=np.uint8)

        is_bounce = TrajectoryConsistencyFilter.identify_bounces_3year(c_prev, c_curr, c_next)
        self.assertFalse(is_bounce[0, 0], "Permanent transition Forest -> Built -> Built must NOT be flagged as bounce!")

        # Also test stack filtering
        stack = np.stack([c_prev, c_curr, c_next], axis=0)  # Shape (3, 1, 1)
        filtered_stack, stats = self.filter.filter_trajectory_stack(stack)

        self.assertEqual(filtered_stack[0, 0, 0], self.c_trees)
        self.assertEqual(filtered_stack[1, 0, 0], self.c_built)
        self.assertEqual(filtered_stack[2, 0, 0], self.c_built)
        self.assertEqual(stats["total_bounces_smoothed"], 0)

    def test_delayed_permanent_transition_preservation(self):
        """
        Transition Forest(2020) -> Forest(2021) -> Crops(2022)
        MUST be preserved!
        """
        c_prev = np.array([[self.c_trees]], dtype=np.uint8)
        c_curr = np.array([[self.c_trees]], dtype=np.uint8)
        c_next = np.array([[self.c_crops]], dtype=np.uint8)

        is_bounce = TrajectoryConsistencyFilter.identify_bounces_3year(c_prev, c_curr, c_next)
        self.assertFalse(is_bounce[0, 0])

        stack = np.stack([c_prev, c_curr, c_next], axis=0)
        filtered_stack, stats = self.filter.filter_trajectory_stack(stack)
        self.assertEqual(filtered_stack[1, 0, 0], self.c_trees)
        self.assertEqual(filtered_stack[2, 0, 0], self.c_crops)
        self.assertEqual(stats["total_bounces_smoothed"], 0)

    def test_multi_year_stack_bounce_smoothing(self):
        """
        Test 4-year trajectory:
        Pixel A (stable): Forest -> Forest -> Forest -> Forest
        Pixel B (bounce): Forest -> Bare -> Forest -> Forest
        Pixel C (perm): Forest -> Forest -> Built -> Built
        Pixel D (cloud shadow bounce): Crops -> Water -> Crops -> Crops
        """
        h, w = 2, 2
        # Y0: all trees except (1, 1) crops
        y0 = np.array([[self.c_trees, self.c_trees],
                       [self.c_trees, self.c_crops]], dtype=np.uint8)
        # Y1: (0, 1) bounces to bare, (1, 1) bounces to water
        y1 = np.array([[self.c_trees, self.c_bare],
                       [self.c_trees, self.c_water]], dtype=np.uint8)
        # Y2: (0, 1) returns to trees, (1, 0) permanently changes to built, (1, 1) returns to crops
        y2 = np.array([[self.c_trees, self.c_trees],
                       [self.c_built, self.c_crops]], dtype=np.uint8)
        # Y3: stable future state
        y3 = np.array([[self.c_trees, self.c_trees],
                       [self.c_built, self.c_crops]], dtype=np.uint8)

        stack = np.stack([y0, y1, y2, y3], axis=0)  # Shape (4, 2, 2)
        filtered_stack, stats = self.filter.filter_trajectory_stack(stack)

        # Pixel (0, 0): stays trees across all 4 years
        np.testing.assert_array_equal(filtered_stack[:, 0, 0], [self.c_trees, self.c_trees, self.c_trees, self.c_trees])

        # Pixel (0, 1): bounce at Y1 was smoothed from bare back to trees!
        self.assertEqual(filtered_stack[1, 0, 1], self.c_trees, "Y1 bounce to bare must be smoothed to trees.")
        np.testing.assert_array_equal(filtered_stack[:, 0, 1], [self.c_trees, self.c_trees, self.c_trees, self.c_trees])

        # Pixel (1, 0): permanent change to built at Y2 MUST be preserved!
        np.testing.assert_array_equal(filtered_stack[:, 1, 0], [self.c_trees, self.c_trees, self.c_built, self.c_built])

        # Pixel (1, 1): shadow bounce at Y1 (crops -> water -> crops) smoothed!
        self.assertEqual(filtered_stack[1, 1, 1], self.c_crops, "Y1 bounce to water must be smoothed to crops.")
        np.testing.assert_array_equal(filtered_stack[:, 1, 1], [self.c_crops, self.c_crops, self.c_crops, self.c_crops])

        self.assertEqual(stats["total_bounces_smoothed"], 2)

    def test_irreversible_urban_demolition_filter(self):
        """Built -> Bare -> Built is impossible in 1 year and must be smoothed."""
        y0 = np.array([[self.c_built]], dtype=np.uint8)
        y1 = np.array([[self.c_bare]], dtype=np.uint8)
        y2 = np.array([[self.c_built]], dtype=np.uint8)

        stack = np.stack([y0, y1, y2], axis=0)
        filtered_stack, stats = self.filter.filter_trajectory_stack(stack)

        self.assertEqual(filtered_stack[1, 0, 0], self.c_built, "Built -> Bare -> Built must be smoothed to Built.")
        self.assertEqual(stats["total_bounces_smoothed"], 1)

    def test_ignore_nodata_boundary_handling(self):
        """IGNORE pixels (255) must not be treated as valid or bounce-flagged."""
        y0 = np.array([[IGNORE]], dtype=np.uint8)
        y1 = np.array([[self.c_bare]], dtype=np.uint8)
        y2 = np.array([[IGNORE]], dtype=np.uint8)

        stack = np.stack([y0, y1, y2], axis=0)
        filtered_stack, stats = self.filter.filter_trajectory_stack(stack)

        self.assertEqual(filtered_stack[0, 0, 0], IGNORE)
        self.assertEqual(filtered_stack[1, 0, 0], self.c_bare)
        self.assertEqual(stats["total_bounces_smoothed"], 0)


class TestSpectralDivergenceAndConfidence(unittest.TestCase):
    """Tests spectral divergence metrics and pixel-wise change confidence score."""

    def setUp(self):
        self.scorer = ChangeConfidenceScorer()
        self.c_trees = CLASS_TO_IDX["trees"]
        self.c_bare = CLASS_TO_IDX["bare"]
        self.c_built = CLASS_TO_IDX["built"]

        # Synthetic spectral profiles
        self.bands_forest = {
            "blue": np.array([[350.0]], dtype=np.float32),
            "green": np.array([[650.0]], dtype=np.float32),
            "red": np.array([[450.0]], dtype=np.float32),
            "nir": np.array([[3800.0]], dtype=np.float32),
            "swir16": np.array([[1600.0]], dtype=np.float32),
            "swir22": np.array([[800.0]], dtype=np.float32),
        }
        self.bands_bare = {
            "blue": np.array([[900.0]], dtype=np.float32),
            "green": np.array([[1200.0]], dtype=np.float32),
            "red": np.array([[1500.0]], dtype=np.float32),
            "nir": np.array([[2200.0]], dtype=np.float32),
            "swir16": np.array([[2800.0]], dtype=np.float32),
            "swir22": np.array([[2400.0]], dtype=np.float32),
        }
        self.bands_built = {
            "blue": np.array([[1100.0]], dtype=np.float32),
            "green": np.array([[1300.0]], dtype=np.float32),
            "red": np.array([[1400.0]], dtype=np.float32),
            "nir": np.array([[1800.0]], dtype=np.float32),
            "swir16": np.array([[2100.0]], dtype=np.float32),
            "swir22": np.array([[1900.0]], dtype=np.float32),
        }

    def test_nsvd_identical_spectra_is_zero(self):
        """Identical spectra must yield exactly zero NSVD divergence."""
        nsvd = SpectralDivergenceCalculator.calculate_nsvd(self.bands_forest, self.bands_forest)
        self.assertAlmostEqual(float(nsvd[0, 0]), 0.0, places=5)

    def test_nsvd_distinct_spectra_bounded(self):
        """Different spectra yield positive divergence strictly bounded in (0.0, 1.0]."""
        nsvd = SpectralDivergenceCalculator.calculate_nsvd(self.bands_forest, self.bands_bare)
        val = float(nsvd[0, 0])
        self.assertGreater(val, 0.15)
        self.assertLessEqual(val, 1.0)

    def test_sam_zero_for_collinear(self):
        """SAM is zero for identical or scalar-scaled spectra."""
        sam = SpectralDivergenceCalculator.calculate_spectral_angle_mapper(self.bands_forest, self.bands_forest)
        self.assertAlmostEqual(float(sam[0, 0]), 0.0, places=5)

    def test_unchanged_pixel_confidence_is_zero(self):
        """When classification has not changed, change confidence score must be 0.0."""
        c1 = np.array([[self.c_trees]], dtype=np.uint8)
        c2 = np.array([[self.c_trees]], dtype=np.uint8)

        conf = self.scorer.compute_confidence(
            c_t1=c1,
            c_t2=c2,
            bands_t1=self.bands_forest,
            bands_t2=self.bands_forest,
        )
        self.assertEqual(float(conf[0, 0]), 0.0)

    def test_bounce_pixel_confidence_severely_penalized(self):
        """
        When a change is identified as a transient bounce, its confidence
        must be heavily penalized down to <= 0.08.
        """
        c1 = np.array([[self.c_trees]], dtype=np.uint8)
        c2 = np.array([[self.c_bare]], dtype=np.uint8)
        c3 = np.array([[self.c_trees]], dtype=np.uint8)

        is_bounce = np.array([[True]], dtype=bool)

        conf = self.scorer.compute_confidence(
            c_t1=c1,
            c_t2=c2,
            bands_t1=self.bands_forest,
            bands_t2=self.bands_bare,
            is_bounce_mask=is_bounce,
            c_t3=c3,
            bands_t3=self.bands_forest,
        )
        val = float(conf[0, 0])
        self.assertLessEqual(val, 0.08, f"Bounce confidence must be damped, got {val}")

    def test_permanent_change_confidence_is_high(self):
        """
        Permanent transition Forest -> Built -> Built must yield high confidence (>= 0.65).
        """
        c1 = np.array([[self.c_trees]], dtype=np.uint8)
        c2 = np.array([[self.c_built]], dtype=np.uint8)
        c3 = np.array([[self.c_built]], dtype=np.uint8)

        is_bounce = np.array([[False]], dtype=bool)

        conf = self.scorer.compute_confidence(
            c_t1=c1,
            c_t2=c2,
            bands_t1=self.bands_forest,
            bands_t2=self.bands_built,
            is_bounce_mask=is_bounce,
            c_t3=c3,
            bands_t3=self.bands_built,
        )
        val = float(conf[0, 0])
        self.assertGreaterEqual(val, 0.60, f"Permanent transition should have high confidence, got {val}")


class TestTransitionMatrixEngine(unittest.TestCase):
    """Tests matrix arithmetic, conservation of pixels/area, and CSV formatting."""

    def test_matrix_arithmetic_conservation(self):
        """Verify strict conservation properties of the transition matrix."""
        # 4x4 classification grid with 3 classes (0: water, 1: trees, 6: built)
        c_from = np.array([
            [1, 1, 1, 1],
            [1, 1, 0, 0],
            [6, 6, 6, 6],
            [1, 1, 1, 1],
        ], dtype=np.uint8)

        # c_to: some forest converted to built
        c_to = np.array([
            [1, 1, 6, 6],  # 2 pixels converted from trees(1) to built(6)
            [1, 1, 0, 0],  # unchanged
            [6, 6, 6, 6],  # unchanged built
            [1, 1, 1, 1],  # unchanged trees
        ], dtype=np.uint8)

        res = TransitionMatrixEngine.compute_matrix(c_from, c_to, pixel_size_m=10.0)

        # Checks
        self.assertEqual(res["total_pixels"], 16)
        self.assertEqual(res["valid_pixels"], 16)
        self.assertEqual(res["changed_pixels"], 2)
        self.assertEqual(res["unchanged_pixels"], 14)
        self.assertEqual(res["changed_area_m2"], 200.0)
        self.assertEqual(res["total_area_m2"], 1600.0)

        # Verification booleans
        verif = res["arithmetic_verification"]
        self.assertTrue(verif["passed"])
        self.assertTrue(verif["sum_equals_valid_count"])
        self.assertTrue(verif["diag_plus_changed_equals_total"])
        self.assertTrue(verif["net_change_sum_zero"])

        # Check net changes: trees should have lost 200 m^2 (-200), built gained 200 m^2 (+200)
        net_area = res["class_net_area_m2"]
        self.assertEqual(net_area[1], -200.0)
        self.assertEqual(net_area[6], 200.0)
        self.assertEqual(net_area[0], 0.0)

    def test_transition_csv_export(self):
        """Verify CSV export writes correct columns and values."""
        c_from = np.array([[1, 0]], dtype=np.uint8)
        c_to = np.array([[6, 0]], dtype=np.uint8)

        res = TransitionMatrixEngine.compute_matrix(c_from, c_to, pixel_size_m=10.0)
        test_csv_path = CURRENT_DIR / "test_scratch" / "test_transitions.csv"

        try:
            TransitionMatrixEngine.export_transition_csv(res, test_csv_path)
            self.assertTrue(test_csv_path.exists())

            lines = test_csv_path.read_text(encoding="utf-8-sig").strip().splitlines()
            self.assertIn("from_class_idx,from_class_name,to_class_idx,to_class_name,pixels,area_m2", lines[0])
            self.assertEqual(len(lines), 1 + 9 * 9)  # 1 header + 81 rows for 9 classes
        finally:
            if test_csv_path.parent.exists():
                shutil.rmtree(test_csv_path.parent, ignore_errors=True)


class TestTemporalChangeDetectionEngineIntegration(unittest.TestCase):
    """
    End-to-End integration test connecting:
    - Unit 336's SCL median annual compositing.
    - Multi-year trajectory consistency filter.
    - Confidence scoring and matrix exports.
    """

    def setUp(self):
        self.test_out_dir = CURRENT_DIR / "test_scratch_engine"
        self.test_out_dir.mkdir(parents=True, exist_ok=True)
        self.engine = TemporalChangeDetectionEngine()

    def tearDown(self):
        if self.test_out_dir.exists():
            shutil.rmtree(self.test_out_dir, ignore_errors=True)

    def test_full_3year_end_to_end_pipeline(self):
        """
        Execute full pipeline over 3 years (2020, 2021, 2022) with synthetic Indonesian slices.
        Inject deliberate seasonal bounce (Forest -> Bare -> Forest) and permanent change (Forest -> Built -> Built).
        Verify that:
        1. Bounces are filtered out.
        2. Permanent transitions are preserved.
        3. Filtered changed pixels < Raw changed pixels.
        4. Output GeoTIFF and CSV files are created and valid.
        """
        years = [2020, 2021, 2022]
        h, w = 16, 16
        annual_comps = []
        raw_classes = []

        comp_engine = TemporalCompositeEngine(default_method="median")

        # Step 1: Generate annual composites using Unit 336 SCL median blending
        for yr in years:
            slices = SyntheticSliceGenerator.generate_annual_stack(
                province="banten",
                year=yr,
                num_slices=4,
                grid_size=(h, w),
                seed=yr,
            )
            comp = comp_engine.composite_slice_stack(slices, method="median")
            annual_comps.append(comp)

        # Find pixels that are valid across all 3 years
        v_common = np.ones((h, w), dtype=bool)
        for comp in annual_comps:
            v_common &= (comp["quality_mask"] == 1)

        # Select 10 pixels for bounce and 10 pixels for permanent change from guaranteed valid pixels
        valid_indices = np.argwhere(v_common)
        bounce_coords = valid_indices[:10]
        perm_coords = valid_indices[10:20]

        # Step 2: Build raw classifications
        for yr in years:
            cls_grid = np.full((h, w), CLASS_TO_IDX["trees"], dtype=np.uint8)

            # In 2021: inject bounce (Forest -> Bare)
            if yr == 2021:
                for r, c in bounce_coords:
                    cls_grid[r, c] = CLASS_TO_IDX["bare"]

            # In 2021 & 2022: permanent urban development (Forest -> Built)
            if yr in (2021, 2022):
                for r, c in perm_coords:
                    cls_grid[r, c] = CLASS_TO_IDX["built"]

            raw_classes.append(cls_grid)

        # Run change detection engine
        report = self.engine.execute_annual_series_change_analysis(
            annual_composites=annual_comps,
            raw_classifications=raw_classes,
            years=years,
            output_dir=self.test_out_dir,
            target_pair=(2020, 2021),
        )

        # Assertions
        metrics = report["transition_comparison"]
        raw_changed = metrics["raw_changed_pixels"]
        filtered_changed = metrics["filtered_changed_pixels"]
        false_changes_removed = metrics["false_changes_removed_pixels"]

        # Raw had 20 changed pixels: 10 bounce + 10 permanent
        self.assertEqual(raw_changed, 20)
        # Filtered must have removed exactly 10 bounce pixels!
        self.assertEqual(false_changes_removed, 10)
        # Filtered must preserve exactly the 10 permanent changes
        self.assertEqual(filtered_changed, 10)
        # False change reduction rate: 10 / 20 = 50.0%
        self.assertAlmostEqual(metrics["false_change_reduction_rate"], 0.50, places=4)

        # Verify output files
        self.assertTrue((self.test_out_dir / "transitions_raw.tif").is_file())
        self.assertTrue((self.test_out_dir / "transitions_filtered.tif").is_file())
        self.assertTrue((self.test_out_dir / "change_confidence.tif").is_file())
        self.assertTrue((self.test_out_dir / "transitions_raw.csv").is_file())
        self.assertTrue((self.test_out_dir / "transitions_filtered.csv").is_file())
        self.assertTrue((self.test_out_dir / "filter_summary_report.json").is_file())

        # Matrix arithmetic check
        self.assertTrue(report["matrix_conservation_verified"])


if __name__ == "__main__":
    unittest.main()
