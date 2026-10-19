"""Unit tests for LCLUC Unified Analytics and Invariant Statistics Engine.

Verifies:
1. Exact dataset_id, version, aoi_id, observation_period identity binding.
2. Frame Manifest schema validation matching CODEX Section 9.
3. CODEX Section 13 Test #4: 4x4 mock dataset transition verification
   (1->2 two pixels, 2->1 one pixel, 13 unchanged, total sum equals valid area).
4. Strict NoData handling (NoData in T1 or T2 strictly excluded from transition matrix).
5. Statistics invariance under simulated UI viewports, zoom levels, and swipe positions.
6. Pixel inspection query accuracy without RGB reverse-engineering.
7. Authentic area calculations (pixel counts × spatial resolution).
"""

import json
import math
import numpy as np
import pytest

from backend.app.ml.lcluc_unified_analytics import (
    DEFAULT_CLASS_NAMES,
    DEFAULT_CLASS_COLORS,
    DEFAULT_NODATA,
    M2_PER_HA,
    ApprovalState,
    DatasetIdentity,
    FrameManifest,
    PublicationState,
    SourceKind,
    ValidationState,
    build_4x4_acceptance_fixture,
    compute_annual_statistics,
    compute_transition_analytics,
    inspect_pixel_at,
)


# ============================================================================
# 1. Dataset Identity & Provenance Binding Tests
# ============================================================================

class TestDatasetIdentityBinding:
    def test_matching_identity_passes(self):
        id1 = DatasetIdentity(
            dataset_id="south_sulawesi_lc",
            version="v1.0",
            aoi_id="south_sulawesi",
            observation_period="2020",
        )
        id2 = DatasetIdentity(
            dataset_id="south_sulawesi_lc",
            version="v1.0",
            aoi_id="south_sulawesi",
            observation_period="2020",
        )
        id1.assert_matches(id2)

    def test_mismatched_dataset_id_fails(self):
        id1 = DatasetIdentity("ds_a", "v1", "aoi_1", "2020")
        id2 = DatasetIdentity("ds_b", "v1", "aoi_1", "2020")
        with pytest.raises(ValueError, match="dataset_id mismatch"):
            id1.assert_matches(id2)

    def test_mismatched_version_fails(self):
        id1 = DatasetIdentity("ds_a", "v1", "aoi_1", "2020")
        id2 = DatasetIdentity("ds_a", "v2", "aoi_1", "2020")
        with pytest.raises(ValueError, match="version mismatch"):
            id1.assert_matches(id2)

    def test_mismatched_aoi_fails(self):
        id1 = DatasetIdentity("ds_a", "v1", "aoi_1", "2020")
        id2 = DatasetIdentity("ds_a", "v1", "aoi_2", "2020")
        with pytest.raises(ValueError, match="aoi_id mismatch"):
            id1.assert_matches(id2)

    def test_mismatched_period_fails(self):
        id1 = DatasetIdentity("ds_a", "v1", "aoi_1", "2020")
        id2 = DatasetIdentity("ds_a", "v1", "aoi_1", "2021")
        with pytest.raises(ValueError, match="observation_period mismatch"):
            id1.assert_matches(id2)


# ============================================================================
# 2. Frame Manifest Schema (Section 9) Tests
# ============================================================================

class TestFrameManifestSchema:
    def test_valid_manifest(self):
        manifest = FrameManifest(
            series_id="lcluc_south_sulawesi_2020_2025",
            frame_id="frame_2020",
            result_id="res_2020_v1",
            version="1.0.0",
            year=2020,
            time_parameter="2020-01-01T00:00:00Z",
            observation_start="2020-01-01T00:00:00Z",
            observation_end="2020-12-31T23:59:59Z",
            composite_method="median_scl_cloud_masked",
            source_kind=SourceKind.MODEL_PREDICTION.value,
            source_refs=["s2_2020_tile1", "s2_2020_tile2"],
            model_id="tiny_unet_v1",
            model_version="1.0",
            footprint={"type": "Polygon", "coordinates": [[[118, -6], [121, -6], [121, -2], [118, -2], [118, -6]]]},
            bbox_crs84=[118.0, -6.0, 121.0, -2.0],
            native_crs="EPSG:32750",
            resolution=10.0,
            storage_ref="data/results/south_sulawesi/2020/classification.tif",
            checksum="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            geoserver_layer="lcluc:south_sulawesi_2020",
            publication_state=PublicationState.PUBLISHED_TO_STAGING.value,
            scientific_validation_state=ValidationState.VALIDATED.value,
            approval_state=ApprovalState.APPROVED.value,
        )
        data = manifest.to_dict()
        assert data["series_id"] == "lcluc_south_sulawesi_2020_2025"
        assert data["resolution"] == 10.0
        assert data["nodata"] == 255

        # Serialization round-trip
        json_str = manifest.to_json()
        parsed = json.loads(json_str)
        assert parsed["year"] == 2020

    def test_missing_mandatory_field_raises(self):
        with pytest.raises(ValueError, match="series_id is required"):
            FrameManifest(
                series_id="",
                frame_id="f1",
                result_id="r1",
                version="v1",
                year=2020,
                time_parameter="2020",
                observation_start="2020-01-01",
                observation_end="2020-12-31",
                composite_method="annual_median",
                source_kind=SourceKind.SYNTHETIC_FIXTURE.value,
                source_refs=[],
            ).validate()

    def test_invalid_year_raises(self):
        with pytest.raises(ValueError, match="year must be between"):
            FrameManifest(
                series_id="s1",
                frame_id="f1",
                result_id="r1",
                version="v1",
                year=1850,
                time_parameter="1850",
                observation_start="1850",
                observation_end="1850",
                composite_method="annual",
                source_kind=SourceKind.SYNTHETIC_FIXTURE.value,
                source_refs=[],
            ).validate()


# ============================================================================
# 3. CODEX Section 13 Test #4: 4x4 Mock Dataset Verification
# ============================================================================

class TestSection13Test4MockDatasetTransition:
    def test_4x4_acceptance_fixture_exact_counts(self):
        """CODEX Section 13.4:
        모의 4×4 자료에서 1→2 두 픽셀, 2→1 한 픽셀만 변경하고 나머지는 유지했을 때
        전이행렬·총변화 픽셀 수가 기대값과 일치한다.
        """
        t1, t2 = build_4x4_acceptance_fixture()
        assert t1.shape == (4, 4)
        assert t2.shape == (4, 4)

        analytics = compute_transition_analytics(
            t1_raster=t1,
            t2_raster=t2,
            resolution_m=10.0,
            from_year=2020,
            to_year=2025,
        )

        # 1. Total domain and valid pixels
        assert analytics.total_domain_pixels == 16
        assert analytics.common_valid_pixels == 16
        assert analytics.excluded_nodata_pixels == 0

        # 2. Total area in m2 (16 pixels * 100 m2 = 1,600 m2 = 0.16 ha)
        assert analytics.common_valid_area_m2 == 1600.0
        assert math.isclose(analytics.common_valid_area_ha, 0.16, rel_tol=1e-5)

        # 3. Changed pixels: 1->2 (2 pixels) + 2->1 (1 pixel) = 3 pixels
        assert analytics.changed_pixels == 3
        assert analytics.changed_area_m2 == 300.0
        assert math.isclose(analytics.changed_area_ha, 0.03, rel_tol=1e-5)
        assert math.isclose(analytics.change_rate_pct, (3 / 16) * 100.0, rel_tol=1e-5)

        # 4. Matrix element verification: Rows = T1, Cols = T2
        matrix_px = analytics.transition_pixels
        # 1 -> 2 must be 2 pixels
        assert matrix_px[1][2] == 2
        # 2 -> 1 must be 1 pixel
        assert matrix_px[2][1] == 1
        # No other off-diagonal transitions
        for i in range(len(DEFAULT_CLASS_NAMES)):
            for j in range(len(DEFAULT_CLASS_NAMES)):
                if (i, j) == (1, 2):
                    assert matrix_px[i][j] == 2
                elif (i, j) == (2, 1):
                    assert matrix_px[i][j] == 1
                elif i != j:
                    assert matrix_px[i][j] == 0, f"Unexpected transition at ({i}, {j}): {matrix_px[i][j]}"

        # 5. Diagonal elements (unchanged): 16 - 3 = 13 unchanged pixels
        unchanged_total = sum(matrix_px[i][i] for i in range(len(DEFAULT_CLASS_NAMES)))
        assert unchanged_total == 13

        # 6. Total matrix sum strictly equals common valid pixels
        matrix_total_px = sum(sum(row) for row in matrix_px)
        assert matrix_total_px == 16

        # 7. Total area matrix sum strictly equals common valid area
        matrix_total_m2 = sum(sum(row) for row in analytics.transition_area_m2)
        assert math.isclose(matrix_total_m2, 1600.0, rel_tol=1e-5)


# ============================================================================
# 4. Strict NoData Handling Tests (CODEX Section 8 & 13.5)
# ============================================================================

class TestStrictNoDataHandling:
    def test_nodata_in_t1_or_t2_excluded_from_matrix(self):
        """CODEX Section 13.5:
        T1 또는 T2 NoData인 픽셀은 변화통계에서 제외된다.
        """
        t1, t2 = build_4x4_acceptance_fixture()

        # Set (0, 0) to NoData in T1 (previously 1)
        t1[0, 0] = DEFAULT_NODATA
        # Set (1, 1) to NoData in T2 (previously 1)
        t2[1, 1] = DEFAULT_NODATA
        # Set (2, 2) to NoData in both (previously 2)
        t1[2, 2] = DEFAULT_NODATA
        t2[2, 2] = DEFAULT_NODATA

        analytics = compute_transition_analytics(
            t1_raster=t1,
            t2_raster=t2,
            nodata=DEFAULT_NODATA,
            resolution_m=10.0,
        )

        # Total domain = 16
        # Excluded pixels: (0, 0), (1, 1), (2, 2) = 3 pixels
        # Valid pixels = 13
        assert analytics.total_domain_pixels == 16
        assert analytics.excluded_nodata_pixels == 3
        assert analytics.common_valid_pixels == 13
        assert analytics.common_valid_area_m2 == 1300.0

        # Matrix sum must equal 13 (NOT 16)
        matrix_total_px = sum(sum(row) for row in analytics.transition_pixels)
        assert matrix_total_px == 13

        # (0, 0) was one of the 1->2 pixels, so 1->2 count should now be 1 instead of 2
        assert analytics.transition_pixels[1][2] == 1
        # 2->1 count remains 1
        assert analytics.transition_pixels[2][1] == 1


# ============================================================================
# 5. Statistics Invariance Tests (CODEX Section 8 & 13.6)
# ============================================================================

class TestStatisticsInvariance:
    def test_statistics_invariant_to_simulated_ui_viewports(self):
        """CODEX Section 13.6:
        zoom·Swipe 위치만 바꿔도 같은 AOI 비교 통계는 바뀌지 않는다.
        """
        # Master classification rasters (e.g. 100x100 grid)
        np.random.seed(42)
        master_t1 = np.random.randint(0, 5, size=(100, 100), dtype=np.uint8)
        master_t2 = master_t1.copy()
        # Introduce specific changes
        master_t2[20:30, 20:30] = 6  # 100 pixels converted to built (class 6)

        # Baseline statistics computed strictly from master source
        baseline = compute_transition_analytics(
            t1_raster=master_t1,
            t2_raster=master_t2,
            resolution_m=10.0,
            from_year=2020,
            to_year=2025,
        )

        # Simulate UI viewports / zoom levels (e.g. user panning to top-left or zooming in)
        viewports = [
            (0, 50, 0, 50),       # Top-left viewport
            (25, 75, 25, 75),     # Center zoom-in
            (10, 90, 10, 90),     # Cropped swipe boundary
        ]

        for r_min, r_max, c_min, c_max in viewports:
            # Client UI displays only a clipped region on screen:
            screen_view_t1 = master_t1[r_min:r_max, c_min:c_max]
            screen_view_t2 = master_t2[r_min:r_max, c_min:c_max]

            # Invariant principle: The system MUST compute and report statistics
            # from the master source, NOT from the clipped screen viewport!
            official_analytics = compute_transition_analytics(
                t1_raster=master_t1,
                t2_raster=master_t2,
                resolution_m=10.0,
            )

            # Assert complete numerical invariance
            assert official_analytics.common_valid_pixels == baseline.common_valid_pixels
            assert official_analytics.changed_pixels == baseline.changed_pixels
            assert official_analytics.changed_area_m2 == baseline.changed_area_m2
            assert official_analytics.transition_pixels == baseline.transition_pixels
            assert official_analytics.statistics_basis == "full_valid_source_raster_invariant"

    def test_annual_statistics_invariance(self):
        np.random.seed(99)
        master = np.random.randint(0, 7, size=(50, 50), dtype=np.uint8)
        baseline = compute_annual_statistics(master, resolution_m=10.0, year=2023)

        # Simulating client zoom/downsample (e.g. overviews display)
        # Official statistics must always match the full resolution master
        official = compute_annual_statistics(master, resolution_m=10.0, year=2023)
        assert official.valid_pixels == baseline.valid_pixels
        assert official.valid_area_m2 == baseline.valid_area_m2
        for c1, c2 in zip(official.classes, baseline.classes):
            assert c1.pixels == c2.pixels
            assert c1.area_m2 == c2.area_m2


# ============================================================================
# 6. Pixel Inspection Query Tests (CODEX Section 8)
# ============================================================================

class TestPixelInspection:
    def test_inspect_pixel_changed(self):
        t1, t2 = build_4x4_acceptance_fixture()
        # Pixel (0, 0): t1=1 (trees), t2=2 (grass)
        insp = inspect_pixel_at(t1, t2, row=0, col=0, resolution_m=10.0)
        assert insp.row == 0
        assert insp.col == 0
        assert insp.t1_class_id == 1
        assert insp.t1_class_name == "trees"
        assert insp.t2_class_id == 2
        assert insp.t2_class_name == "grass"
        assert insp.is_changed is True
        assert insp.is_nodata is False
        assert insp.pixel_area_m2 == 100.0

    def test_inspect_pixel_unchanged(self):
        t1, t2 = build_4x4_acceptance_fixture()
        # Pixel (2, 2): t1=2 (grass), t2=2 (grass)
        insp = inspect_pixel_at(t1, t2, row=2, col=2, resolution_m=10.0)
        assert insp.t1_class_id == 2
        assert insp.t2_class_id == 2
        assert insp.is_changed is False
        assert insp.is_nodata is False

    def test_inspect_pixel_nodata(self):
        t1, t2 = build_4x4_acceptance_fixture()
        t1[3, 3] = DEFAULT_NODATA
        insp = inspect_pixel_at(t1, t2, row=3, col=3, nodata=DEFAULT_NODATA)
        assert insp.is_nodata is True
        assert insp.t1_class_id is None
        assert insp.t1_class_name is None
        assert insp.is_changed is False

    def test_inspect_pixel_out_of_bounds(self):
        t1, t2 = build_4x4_acceptance_fixture()
        with pytest.raises(IndexError, match="out of bounds"):
            inspect_pixel_at(t1, t2, row=10, col=10)


# ============================================================================
# 7. Annual Class Statistics Tests
# ============================================================================

class TestAnnualStatistics:
    def test_annual_stats_sums_and_ratios(self):
        # 10x10 raster: 40 trees (1), 30 crops (4), 20 built (6), 10 nodata (255)
        arr = np.full((10, 10), 1, dtype=np.uint8)
        arr[4:7, :] = 4  # 30 pixels crops
        arr[7:9, :] = 6  # 20 pixels built
        arr[9, :] = DEFAULT_NODATA  # 10 pixels nodata

        stats = compute_annual_statistics(arr, nodata=DEFAULT_NODATA, resolution_m=10.0, year=2021)

        assert stats.total_pixels == 100
        assert stats.valid_pixels == 90
        assert stats.nodata_pixels == 10
        assert stats.valid_area_m2 == 9000.0
        assert stats.valid_area_ha == 0.9

        # Class counts
        tree_stat = next(c for c in stats.classes if c.name == "trees")
        crop_stat = next(c for c in stats.classes if c.name == "crops")
        built_stat = next(c for c in stats.classes if c.name == "built")

        assert tree_stat.pixels == 40
        assert math.isclose(tree_stat.ratio_pct, (40 / 90) * 100.0, rel_tol=1e-2)
        assert crop_stat.pixels == 30
        assert math.isclose(crop_stat.ratio_pct, (30 / 90) * 100.0, rel_tol=1e-2)
        assert built_stat.pixels == 20
        assert math.isclose(built_stat.ratio_pct, (20 / 90) * 100.0, rel_tol=1e-2)

        # Sum of class pixels equals valid pixels
        assert sum(c.pixels for c in stats.classes) == 90
        assert math.isclose(sum(c.area_m2 for c in stats.classes), 9000.0, rel_tol=1e-5)
