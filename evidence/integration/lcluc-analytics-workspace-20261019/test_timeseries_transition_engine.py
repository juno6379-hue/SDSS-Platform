"""
Comprehensive Unit Tests for Time-Series Trajectory & Transition Matrix Analytics Engine.
Workspace: evidence/integration/lcluc-analytics-workspace-20261019/test_timeseries_transition_engine.py
"""

import copy
import json
import math
from pathlib import Path
import shutil
import sys
import unittest
import numpy as np

# Ensure workspace modules are importable
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from timeseries_transition_engine import (
    TimeSeriesTrajectoryAnalyzer,
    AdvancedTransitionMatrixAnalytics,
    TimeSeriesTransitionAnalyticsEngine,
    TrendType,
    CLASS_NAMES,
    CLASS_TO_IDX,
)


class TestTimeSeriesTrajectoryAnalyzer(unittest.TestCase):
    """Tests time-series trajectory metrics, growth rates, and trend classifications."""

    def setUp(self):
        self.analyzer = TimeSeriesTrajectoryAnalyzer()

    def test_trend_classification_steady(self):
        """Constant or near-constant series (< 4% relative variation) must be STEADY."""
        steady_series = [100.0, 101.0, 99.5, 100.5, 100.2, 99.8]
        trend = TimeSeriesTrajectoryAnalyzer.classify_trend(steady_series)
        self.assertEqual(trend, TrendType.STEADY)

    def test_trend_classification_monotonic_increase(self):
        """Strictly non-decreasing sequence with net increase must be MONOTONIC_INCREASE."""
        inc_series = [50.0, 60.0, 75.0, 90.0, 110.0, 130.0]
        trend = TimeSeriesTrajectoryAnalyzer.classify_trend(inc_series)
        self.assertEqual(trend, TrendType.MONOTONIC_INCREASE)

    def test_trend_classification_monotonic_decrease(self):
        """Strictly non-increasing sequence with net decrease must be MONOTONIC_DECREASE."""
        dec_series = [500.0, 480.0, 450.0, 410.0, 380.0, 350.0]
        trend = TimeSeriesTrajectoryAnalyzer.classify_trend(dec_series)
        self.assertEqual(trend, TrendType.MONOTONIC_DECREASE)

    def test_trend_classification_sudden_transition(self):
        """Abrupt drop or surge in a single year interval must be SUDDEN_TRANSITION."""
        # Forest stable at ~1000 ha, then massive deforestation in 2023 to ~200 ha, staying stable
        sudden_drop = [1000.0, 1002.0, 998.0, 205.0, 201.0, 199.0]
        trend = TimeSeriesTrajectoryAnalyzer.classify_trend(sudden_drop)
        self.assertEqual(trend, TrendType.SUDDEN_TRANSITION)

        # Sudden surge (e.g. water reservoir filling)
        sudden_surge = [10.0, 12.0, 11.0, 850.0, 852.0, 849.0]
        trend_surge = TimeSeriesTrajectoryAnalyzer.classify_trend(sudden_surge)
        self.assertEqual(trend_surge, TrendType.SUDDEN_TRANSITION)

    def test_trend_classification_fluctuating_seasonal(self):
        """Multiple direction reversals must be FLUCTUATING_SEASONAL."""
        fluct_series = [150.0, 280.0, 140.0, 290.0, 145.0, 275.0]
        trend = TimeSeriesTrajectoryAnalyzer.classify_trend(fluct_series)
        self.assertEqual(trend, TrendType.FLUCTUATING_SEASONAL)

    def test_cagr_and_puyravaud_rate_calculations(self):
        """Verify CAGR and continuous exponential rate mathematical formulas."""
        start_a = 100.0
        end_a = 200.0
        years = 5

        # Doubling in 5 years: CAGR = (200/100)**(1/5) - 1 = 2**0.2 - 1 ~= 0.148698 (14.87%)
        cagr = TimeSeriesTrajectoryAnalyzer.calculate_cagr(start_a, end_a, years)
        expected_cagr = (2.0 ** 0.2) - 1.0
        self.assertAlmostEqual(cagr, expected_cagr, places=5)

        # Puyravaud continuous exponential rate: (1/5) * ln(2) * 100 ~= 13.8629%
        puy = TimeSeriesTrajectoryAnalyzer.calculate_puyravaud_rate(start_a, end_a, years)
        expected_puy = (1.0 / 5.0) * math.log(2.0) * 100.0
        self.assertAlmostEqual(puy, expected_puy, places=4)

        # Boundary: zero end area gives CAGR = -1.0 (-100%)
        zero_end_cagr = TimeSeriesTrajectoryAnalyzer.calculate_cagr(100.0, 0.0, years)
        self.assertEqual(zero_end_cagr, -1.0)

    def test_analyze_trajectory_series_structure(self):
        """Test full trajectory series analysis across 6 years."""
        years = [2020, 2021, 2022, 2023, 2024, 2025]
        annual_data = {}
        for y in years:
            annual_data[y] = {c: 100.0 for c in CLASS_NAMES}

        # Modify trees to decrease and built to increase
        for idx, y in enumerate(years):
            annual_data[y]["trees"] = 500.0 - idx * 50.0   # 500 down to 250
            annual_data[y]["built"] = 100.0 + idx * 50.0   # 100 up to 350

        res = self.analyzer.analyze_trajectory_series(annual_data, years=years)

        self.assertEqual(res["time_horizon"]["span_years"], 5)
        self.assertEqual(res["class_trajectories"]["trees"]["trend_type"], TrendType.MONOTONIC_DECREASE.value)
        self.assertEqual(res["class_trajectories"]["built"]["trend_type"], TrendType.MONOTONIC_INCREASE.value)
        self.assertEqual(res["class_trajectories"]["water"]["trend_type"], TrendType.STEADY.value)

        # Trees net change = 250 - 500 = -250 ha, rate = -50 ha/yr
        self.assertEqual(res["class_trajectories"]["trees"]["net_change_ha"], -250.0)
        self.assertEqual(res["class_trajectories"]["trees"]["annual_net_rate_ha_yr"], -50.0)


class TestAdvancedTransitionMatrixAnalytics(unittest.TestCase):
    """Tests Pontius (2004) matrix decomposition, identities, Markov chain, and Sankey data."""

    def setUp(self):
        self.analyzer = AdvancedTransitionMatrixAnalytics()

    def _create_synthetic_transition_matrix(self) -> np.ndarray:
        """
        Create a 9x9 realistic transition matrix (in ha).
        Total landscape = 10,000 ha.
        """
        k = len(CLASS_NAMES)
        mat = np.zeros((k, k), dtype=np.float64)

        # Diagonal persistence
        mat[0, 0] = 800.0   # water persistent
        mat[1, 1] = 4000.0  # trees persistent
        mat[2, 2] = 500.0   # grass persistent
        mat[3, 3] = 200.0   # flooded_veg persistent
        mat[4, 4] = 1800.0  # crops persistent
        mat[5, 5] = 300.0   # shrub persistent
        mat[6, 6] = 1200.0  # built persistent
        mat[7, 7] = 200.0   # bare persistent
        mat[8, 8] = 0.0     # snow/ice 0

        # Transitions:
        # Forest conversion to built (urbanization): 300 ha
        mat[1, 6] = 300.0
        # Forest conversion to crops: 200 ha
        mat[1, 4] = 200.0
        # Crops conversion to built: 100 ha
        mat[4, 6] = 100.0
        # Grass to crops: 50 ha
        mat[2, 4] = 50.0
        # Grass to bare: 30 ha
        mat[2, 7] = 30.0
        # Crops to grass (abandonment / rotation): 40 ha (causes swap with grass)
        mat[4, 2] = 40.0

        return mat

    def test_pontius_decomposition_identities(self):
        """
        Verify fundamental Pontius et al. (2004) conservation identities:
        1. TotalChange_k = |NetChange_k| + Swap_k
        2. sum_k NetChange_k = 0
        3. Landscape Total Change = Landscape Net + Landscape Swap
        """
        mat = self._create_synthetic_transition_matrix()
        res = self.analyzer.decompose_matrix(mat)

        identities = res["conservation_identities"]
        self.assertTrue(identities["all_class_identities_passed"], "TotalChange = |Net| + Swap must hold for every class!")
        self.assertTrue(identities["landscape_identity_passed"], "Landscape Total Change = Net + Swap must hold!")
        self.assertTrue(identities["net_changes_sum_to_zero"], "Sum of class net changes must be 0!")
        self.assertTrue(identities["mathematical_integrity_verified"])

        # Specific numerical checks
        summary = res["landscape_summary"]
        total_ha = summary["total_area_ha"]
        self.assertAlmostEqual(total_ha, float(np.sum(mat)), places=4)

        # Total change = 300 + 200 + 100 + 50 + 30 + 40 = 720 ha
        self.assertAlmostEqual(summary["total_change_ha"], 720.0, places=4)
        self.assertAlmostEqual(summary["landscape_net_change_ha"] + summary["landscape_swap_ha"], 720.0, places=4)

    def test_class_level_swap_and_net_decomposition(self):
        """Test exact decomposition of Grass (class 2) where swap occurs."""
        mat = self._create_synthetic_transition_matrix()
        res = self.analyzer.decompose_matrix(mat)

        # Grass (class 2):
        # Initial = 500 (persist) + 50 (to crops) + 30 (to bare) = 580 ha
        # Loss = 80 ha
        # Gain = 40 ha (from crops)
        # Final = 540 ha
        # Net change = 40 - 80 = -40 ha
        # Swap = 2 * min(40, 80) = 80 ha
        # Total change = Gain + Loss = 120 ha = |-40| + 80 = 120 ha!
        grass_data = next(c for c in res["class_decomposition"] if c["class_name"] == "grass")

        self.assertEqual(grass_data["initial_area_ha"], 580.0)
        self.assertEqual(grass_data["final_area_ha"], 540.0)
        self.assertEqual(grass_data["loss_ha"], 80.0)
        self.assertEqual(grass_data["gain_ha"], 40.0)
        self.assertEqual(grass_data["net_change_ha"], -40.0)
        self.assertEqual(grass_data["swap_ha"], 80.0)
        self.assertEqual(grass_data["total_change_ha"], 120.0)
        self.assertEqual(grass_data["change_type_dominance"], "SWAP_DOMINATED")

    def test_rankings_persistence_and_vulnerability(self):
        """Verify ranking orders for persistence and vulnerability to loss."""
        mat = self._create_synthetic_transition_matrix()
        res = self.analyzer.decompose_matrix(mat)

        rankings = res["rankings"]
        # Built has 0 loss (1200 / 1200 = 1.0 persistence), Water has 0 loss (800 / 800 = 1.0)
        # Built and Water must be among the most persistent
        top_persistent = rankings["most_persistent"][:2]
        self.assertIn("built", top_persistent)
        self.assertIn("water", top_persistent)

        # Grass and Trees experienced loss, so they must be in vulnerability ranking
        top_vulnerable = rankings["most_vulnerable_to_loss"]
        self.assertTrue(len(top_vulnerable) > 0)
        self.assertIn("grass", top_vulnerable)
        self.assertIn("trees", top_vulnerable)

    def test_markov_transition_probability_matrix(self):
        """
        Verify Markov transition probability matrix P:
        1. P_ij = N_ij / RowSum_i
        2. sum_j P_ij = 1.0 for all rows (Row stochasticity)
        3. Multi-step projection conservation
        """
        mat = self._create_synthetic_transition_matrix()
        markov_res = self.analyzer.compute_markov_probabilities(mat)

        self.assertTrue(markov_res["row_stochasticity_verified"])
        p_mat = np.array(markov_res["transition_probability_matrix"])

        # Check each row sums to 1.0
        row_sums = np.sum(p_mat, axis=1)
        np.testing.assert_allclose(row_sums, 1.0, atol=1e-5)

        # Check trees (row 1): Initial = 4500 ha.
        # Persist = 4000/4500 = 0.888889, Built = 300/4500 = 0.066667, Crops = 200/4500 = 0.044444
        self.assertAlmostEqual(p_mat[1, 1], 4000.0 / 4500.0, places=5)
        self.assertAlmostEqual(p_mat[1, 6], 300.0 / 4500.0, places=5)
        self.assertAlmostEqual(p_mat[1, 4], 200.0 / 4500.0, places=5)

        # Verify multi-step projection
        initial_v = np.sum(mat, axis=1)  # Initial class distribution
        proj_step1 = AdvancedTransitionMatrixAnalytics.project_markov_steps(initial_v, p_mat, steps=1)
        expected_final = np.sum(mat, axis=0)  # Col sums
        np.testing.assert_allclose(proj_step1, expected_final, atol=1e-3)

    def test_sankey_flow_generation_integrity(self):
        """
        Verify Sankey generator nodes, links, and flow value conservation.
        """
        mat = self._create_synthetic_transition_matrix()
        sankey_data = self.analyzer.generate_sankey_data(
            matrix_ha=mat,
            from_year=2020,
            to_year=2025,
            min_flow_ha=1.0,
            include_persistence=True,
        )

        nodes = sankey_data["nodes"]
        links = sankey_data["links"]
        metadata = sankey_data["metadata"]

        # 9 classes * 2 years = 18 nodes
        self.assertEqual(len(nodes), 18)
        self.assertTrue(len(links) > 0)

        # Total flow of all links must equal total landscape area
        total_flow = sum(l["value_ha"] for l in links)
        self.assertAlmostEqual(total_flow, metadata["total_landscape_area_ha"], places=2)

        # Verify source and target node indices exist within nodes range
        for l in links:
            self.assertGreaterEqual(l["source"], 0)
            self.assertLess(l["source"], len(nodes))
            self.assertGreaterEqual(l["target"], 0)
            self.assertLess(l["target"], len(nodes))
            self.assertGreater(l["value_ha"], 0.0)

    def test_sankey_flow_excluding_persistence(self):
        """When include_persistence=False, diagonal flows must be omitted."""
        mat = self._create_synthetic_transition_matrix()
        sankey_data = self.analyzer.generate_sankey_data(
            matrix_ha=mat,
            from_year=2020,
            to_year=2025,
            min_flow_ha=1.0,
            include_persistence=False,
        )

        for l in sankey_data["links"]:
            self.assertFalse(l["is_persistence"], "Persistence links must be excluded when include_persistence=False")


class TestUnifiedAnalyticsEngine(unittest.TestCase):
    """Integration test for TimeSeriesTransitionAnalyticsEngine."""

    def setUp(self):
        self.test_dir = CURRENT_DIR / "test_scratch_analytics"
        self.test_dir.mkdir(parents=True, exist_ok=True)
        self.engine = TimeSeriesTransitionAnalyticsEngine()

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_full_analytics_run_and_artifact_export(self):
        """Execute run_full_analytics and verify generated JSON artifacts."""
        years = [2020, 2021, 2022, 2023, 2024, 2025]
        annual_data = {
            y: {c: 100.0 for c in CLASS_NAMES} for y in years
        }
        # Simulate Forest decrease and Built increase
        for idx, y in enumerate(years):
            annual_data[y]["trees"] = 400.0 - idx * 30.0
            annual_data[y]["built"] = 150.0 + idx * 30.0

        # Create transition matrix between 2020 and 2025
        k = len(CLASS_NAMES)
        mat = np.zeros((k, k), dtype=np.float64)
        for i in range(k):
            c_name = CLASS_NAMES[i]
            mat[i, i] = annual_data[2025][c_name]  # baseline persistence
        # 150 ha conversion from trees(1) to built(6)
        mat[1, 1] = 250.0
        mat[1, 6] = 150.0

        report = self.engine.run_full_analytics(
            annual_area_dict=annual_data,
            transition_matrix_ha=mat,
            years=years,
            from_year=2020,
            to_year=2025,
            output_dir=self.test_dir,
        )

        self.assertEqual(report["status"], "ANALYTICS_COMPLETE")
        self.assertTrue(report["transition_matrix_decomposition"]["conservation_identities"]["mathematical_integrity_verified"])
        self.assertTrue(report["markov_transition_model"]["row_stochasticity_verified"])

        # Check exported files
        self.assertTrue((self.test_dir / "analytics_report.json").is_file())
        self.assertTrue((self.test_dir / "sankey_data.json").is_file())
        self.assertTrue((self.test_dir / "markov_probabilities.json").is_file())


if __name__ == "__main__":
    unittest.main()
