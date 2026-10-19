"""
Unit tests for Annual Composite Quality Tracker & Observation Count Pipeline.
Workspace: evidence/integration/temporal-composite-workspace-20261019/test_composite_quality_tracker.py
"""

from datetime import datetime
import unittest
import numpy as np

from composite_quality_tracker import (
    CompositeQualityTracker,
    TemporalWindow,
    MissingReason,
    SCL_CLASSES,
    INVALID_SCL_CODES,
    VALID_SCL_CODES,
)


class TestCompositeQualityTracker(unittest.TestCase):
    """Exhaustive tests for CompositeQualityTracker and quality contracts."""

    def setUp(self):
        self.tracker = CompositeQualityTracker(nodata_value=0.0)

    def _create_slice(
        self,
        scene_id: str,
        dt_str: str,
        scl_array: np.ndarray,
        red_val: float = 500.0,
        nir_val: float = 3000.0,
        blue_val: float = 400.0,
        green_val: float = 600.0,
    ):
        h, w = scl_array.shape
        bands = {
            "blue": np.full((h, w), blue_val, dtype=np.float32),
            "green": np.full((h, w), green_val, dtype=np.float32),
            "red": np.full((h, w), red_val, dtype=np.float32),
            "nir": np.full((h, w), nir_val, dtype=np.float32),
        }
        return {
            "scene_id": scene_id,
            "datetime": dt_str,
            "bands": bands,
            "scl": scl_array.copy(),
        }

    def test_scl_cloud_and_shadow_filtering(self):
        """Test that cloud, shadow, and defective pixels are strictly filtered out."""
        # 4x4 grid:
        # (0, 0): SCL 4 (Veg) -> VALID
        # (0, 1): SCL 9 (Cloud High) -> INVALID
        # (1, 0): SCL 3 (Cloud Shadow) -> INVALID
        # (1, 1): SCL 10 (Thin Cirrus) -> INVALID
        # (2, 0): SCL 0 (NoData) -> INVALID
        # (2, 1): SCL 1 (Defective) -> INVALID
        # (3, 0): SCL 5 (Bare) -> VALID
        # (3, 1): SCL 6 (Water) -> VALID
        scl = np.array([
            [4, 9, 4, 4],
            [3, 10, 4, 4],
            [0, 1, 4, 4],
            [5, 6, 4, 4],
        ], dtype=np.uint8)

        s1 = self._create_slice("s1", "2024-06-01T03:00:00Z", scl)
        result = self.tracker.process_annual_observations([s1], method="median")

        qmask = result["quality_mask"]
        self.assertEqual(qmask[0, 0], 1)  # Veg
        self.assertEqual(qmask[0, 1], 0)  # Cloud
        self.assertEqual(qmask[1, 0], 0)  # Shadow
        self.assertEqual(qmask[1, 1], 0)  # Cirrus
        self.assertEqual(qmask[2, 0], 0)  # NoData
        self.assertEqual(qmask[2, 1], 0)  # Defective
        self.assertEqual(qmask[3, 0], 1)  # Bare
        self.assertEqual(qmask[3, 1], 1)  # Water

    def test_spectral_nodata_and_nan_override(self):
        """Even if SCL is vegetation (4), spectral NaN or 0.0 must force invalidity."""
        scl = np.full((3, 3), 4, dtype=np.uint8)
        s1 = self._create_slice("s1", "2024-06-01T03:00:00Z", scl)
        # Inject NaN at (0, 0) and 0.0 at (1, 1)
        s1["bands"]["red"][0, 0] = np.nan
        s1["bands"]["nir"][1, 1] = 0.0

        result = self.tracker.process_annual_observations([s1])
        qmask = result["quality_mask"]
        vcounts = result["valid_count_mask"]

        self.assertEqual(qmask[0, 0], 0)
        self.assertEqual(vcounts[0, 0], 0)
        self.assertEqual(qmask[1, 1], 0)
        self.assertEqual(vcounts[1, 1], 0)
        self.assertEqual(qmask[0, 1], 1)
        self.assertEqual(vcounts[0, 1], 1)

    def test_temporal_window_filtering(self):
        """Verify that observations outside the specified window are excluded."""
        scl = np.full((2, 2), 4, dtype=np.uint8)
        # Slices across different dates: Q1 (Feb), Q2 (May), Q3 (Aug), Q4 (Nov)
        s1 = self._create_slice("s1", "2024-02-15T00:00:00Z", scl, red_val=100.0)
        s2 = self._create_slice("s2", "2024-05-15T00:00:00Z", scl, red_val=200.0)
        s3 = self._create_slice("s3", "2024-08-15T00:00:00Z", scl, red_val=300.0)
        s4 = self._create_slice("s4", "2024-11-15T00:00:00Z", scl, red_val=400.0)

        # Window restricted to dry season (June to September)
        dry_window = TemporalWindow(name="dry_season", start_date="2024-06-01", end_date="2024-09-30")
        result = self.tracker.process_annual_observations([s1, s2, s3, s4], window=dry_window)

        # Only s3 (Aug) should be included!
        self.assertEqual(result["metadata"]["temporal_window"]["total_slices_evaluated"], 1)
        self.assertTrue(np.allclose(result["composite_bands"]["red"], 300.0))
        self.assertTrue(np.all(result["valid_count_mask"] == 1))

    def test_median_blending_and_valid_counts(self):
        """Test multi-temporal median blending and per-pixel observation count accumulation."""
        scl_clear = np.full((2, 2), 4, dtype=np.uint8)
        scl_cloud = np.full((2, 2), 9, dtype=np.uint8)

        # Pixel (0, 0): clear in all 3 slices (values 400, 500, 600) -> median 500, count 3
        # Pixel (0, 1): clear in 2 slices (values 400, 600), cloud in s2 -> median 500, count 2
        # Pixel (1, 0): clear only in s1 (value 400) -> value 400, count 1
        # Pixel (1, 1): cloudy in all 3 slices -> NoData (0.0), count 0
        scl1 = scl_clear.copy()
        scl1[1, 1] = 9

        scl2 = scl_clear.copy()
        scl2[0, 1] = 9
        scl2[1, 0] = 9
        scl2[1, 1] = 9

        scl3 = scl_clear.copy()
        scl3[1, 0] = 9
        scl3[1, 1] = 9

        s1 = self._create_slice("s1", "2024-03-01T00:00:00Z", scl1, red_val=400.0)
        s2 = self._create_slice("s2", "2024-06-01T00:00:00Z", scl2, red_val=500.0)
        s3 = self._create_slice("s3", "2024-09-01T00:00:00Z", scl3, red_val=600.0)

        result = self.tracker.process_annual_observations([s1, s2, s3], method="median")
        vcounts = result["valid_count_mask"]
        red = result["composite_bands"]["red"]

        self.assertEqual(vcounts[0, 0], 3)
        self.assertAlmostEqual(red[0, 0], 500.0)

        self.assertEqual(vcounts[0, 1], 2)
        self.assertAlmostEqual(red[0, 1], 500.0)

        self.assertEqual(vcounts[1, 0], 1)
        self.assertAlmostEqual(red[1, 0], 400.0)

        self.assertEqual(vcounts[1, 1], 0)
        self.assertAlmostEqual(red[1, 1], 0.0)  # Strictly preserved as NoData!

    def test_priority_blending_highest_ndvi(self):
        """Test priority compositing selecting the observation with highest valid NDVI."""
        scl = np.full((2, 2), 4, dtype=np.uint8)
        # s1: NIR 3000, Red 1000 -> NDVI = (3000-1000)/(3000+1000) = 0.50
        s1 = self._create_slice("s1", "2024-04-01T00:00:00Z", scl, red_val=1000.0, nir_val=3000.0)
        # s2: NIR 4000, Red 500 -> NDVI = (4000-500)/(4000+500) = 0.777 (Highest!)
        s2 = self._create_slice("s2", "2024-07-01T00:00:00Z", scl, red_val=500.0, nir_val=4000.0)
        # s3: NIR 2500, Red 1200 -> NDVI = 0.351
        s3 = self._create_slice("s3", "2024-10-01T00:00:00Z", scl, red_val=1200.0, nir_val=2500.0)

        result = self.tracker.process_annual_observations([s1, s2, s3], method="priority")
        red = result["composite_bands"]["red"]
        nir = result["composite_bands"]["nir"]
        sel_doy = result["selected_observation_doy"]

        # All pixels should take values from s2 (DOY ~ 183)
        self.assertTrue(np.allclose(red, 500.0))
        self.assertTrue(np.allclose(nir, 4000.0))
        doy_s2 = datetime.fromisoformat("2024-07-01T00:00:00+00:00").timetuple().tm_yday
        self.assertTrue(np.all(sel_doy == doy_s2))

    def test_observation_dates_tracking(self):
        """Verify tracking of first_valid_doy and last_valid_doy."""
        scl_clear = np.full((2, 2), 4, dtype=np.uint8)
        scl_cloud = np.full((2, 2), 9, dtype=np.uint8)

        # s1: DOY 61 (March 1)
        # s2: DOY 153 (June 1)
        # s3: DOY 275 (Oct 1)
        d1 = datetime(2024, 3, 1).timetuple().tm_yday
        d2 = datetime(2024, 6, 1).timetuple().tm_yday
        d3 = datetime(2024, 10, 1).timetuple().tm_yday

        # Pixel (0, 0): valid in s1 and s3 -> first = d1, last = d3
        # Pixel (0, 1): valid only in s2 -> first = d2, last = d2
        # Pixel (1, 1): cloud in all -> first = -1, last = -1
        scl1 = scl_cloud.copy(); scl1[0, 0] = 4
        scl2 = scl_cloud.copy(); scl2[0, 1] = 4
        scl3 = scl_cloud.copy(); scl3[0, 0] = 4

        s1 = self._create_slice("s1", "2024-03-01T00:00:00Z", scl1)
        s2 = self._create_slice("s2", "2024-06-01T00:00:00Z", scl2)
        s3 = self._create_slice("s3", "2024-10-01T00:00:00Z", scl3)

        result = self.tracker.process_annual_observations([s1, s2, s3])
        first_doy = result["first_valid_doy"]
        last_doy = result["last_valid_doy"]

        self.assertEqual(first_doy[0, 0], d1)
        self.assertEqual(last_doy[0, 0], d3)

        self.assertEqual(first_doy[0, 1], d2)
        self.assertEqual(last_doy[0, 1], d2)

        self.assertEqual(first_doy[1, 1], -1)
        self.assertEqual(last_doy[1, 1], -1)

    def test_missing_reason_mask_classification(self):
        """Test accurate classification of missingness reasons for unobserved pixels."""
        # Create a single slice where different pixels are missing for different reasons
        # (0, 0): Cloud (SCL 9) -> MissingReason.CLOUD (1)
        # (0, 1): Shadow (SCL 3) -> MissingReason.CLOUD_SHADOW (2)
        # (1, 0): Cirrus (SCL 10) -> MissingReason.THIN_CIRRUS (3)
        # (1, 1): Defective (SCL 1) -> MissingReason.DEFECTIVE_OR_SNOW (4)
        # (2, 0): NoData (SCL 0) -> MissingReason.SENSOR_NODATA (5)
        # (2, 1): Valid (SCL 4) -> MissingReason.NOT_MISSING (0)
        scl = np.array([
            [9, 3],
            [10, 1],
            [0, 4],
        ], dtype=np.uint8)

        s1 = self._create_slice("s1", "2024-05-01T00:00:00Z", scl)
        result = self.tracker.process_annual_observations([s1])
        reasons = result["missing_reason_mask"]

        self.assertEqual(reasons[0, 0], int(MissingReason.CLOUD))
        self.assertEqual(reasons[0, 1], int(MissingReason.CLOUD_SHADOW))
        self.assertEqual(reasons[1, 0], int(MissingReason.THIN_CIRRUS))
        self.assertEqual(reasons[1, 1], int(MissingReason.DEFECTIVE_OR_SNOW))
        self.assertEqual(reasons[2, 0], int(MissingReason.SENSOR_NODATA))
        self.assertEqual(reasons[2, 1], int(MissingReason.NOT_MISSING))

        # Check metadata breakdown
        diag = result["metadata"]["missingness_diagnostics"]
        self.assertFalse(diag["procedural_interpolation_applied"])
        self.assertTrue(diag["nodata_strictly_preserved"])
        self.assertEqual(diag["missing_reasons_breakdown"]["CLOUD"]["count"], 1)
        self.assertEqual(diag["missing_reasons_breakdown"]["CLOUD_SHADOW"]["count"], 1)
        self.assertEqual(diag["missing_reasons_breakdown"]["THIN_CIRRUS"]["count"], 1)

    def test_strict_nodata_preservation_no_interpolation(self):
        """
        Verify requirement 4:
        '실제 관측이 없는 픽셀은 임의로 보간하거나 절차적으로 채우지 않고 NoData로 보존한다.'
        """
        # 3 slices, center pixel (1, 1) is cloudy/shadow in ALL 3 slices
        scl1 = np.full((3, 3), 4, dtype=np.uint8); scl1[1, 1] = 9   # Cloud
        scl2 = np.full((3, 3), 4, dtype=np.uint8); scl2[1, 1] = 3   # Shadow
        scl3 = np.full((3, 3), 4, dtype=np.uint8); scl3[1, 1] = 10  # Cirrus

        s1 = self._create_slice("s1", "2024-02-01T00:00:00Z", scl1, red_val=500.0)
        s2 = self._create_slice("s2", "2024-05-01T00:00:00Z", scl2, red_val=520.0)
        s3 = self._create_slice("s3", "2024-08-01T00:00:00Z", scl3, red_val=510.0)

        result = self.tracker.process_annual_observations([s1, s2, s3], method="median")

        # Center pixel must be STRICTLY 0.0 (NoData) in all composite bands
        for bname, band_arr in result["composite_bands"].items():
            self.assertEqual(band_arr[1, 1], 0.0, f"Band {bname} at (1, 1) must be preserved as 0.0 NoData.")
            # Neighbor pixels must have valid composite values (> 0.0)
            self.assertGreater(band_arr[0, 0], 0.0)

        # Quality mask must be 0 for center pixel, 1 for neighbors
        self.assertEqual(result["quality_mask"][1, 1], 0)
        self.assertEqual(result["quality_mask"][0, 0], 1)
        self.assertEqual(result["valid_count_mask"][1, 1], 0)
        self.assertEqual(result["valid_count_mask"][0, 0], 3)

        # Missing reason must indicate dominant cause
        self.assertIn(result["missing_reason_mask"][1, 1], [
            int(MissingReason.CLOUD), int(MissingReason.CLOUD_SHADOW), int(MissingReason.THIN_CIRRUS)
        ])


if __name__ == "__main__":
    unittest.main()
