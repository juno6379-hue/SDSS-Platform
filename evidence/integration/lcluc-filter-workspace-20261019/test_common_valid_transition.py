"""Unit Tests for Common Valid Area & Strict NoData Exclusion Transition Matrix Engine.

Verifies:
1. Spatial Grid & Transform Alignment Preflight (detects sub-pixel shifts and CRS mismatches).
2. Strict Common Valid Domain Filtering (valid_common = valid_T1 & valid_T2 & aoi_mask).
3. Absolute NoData Masquerading Prevention (NoData never masquerades as unchanged, forest loss, or valid class).
4. Explicit 4-Way Area Partitioning (Total AOI, T1 Valid, T2 Valid, Common Valid, Incomparable).
5. Mathematical Conservation Proofs:
   - Sum of transition matrix == common_valid_pixels
   - Row sums == T1 common valid class counts
   - Column sums == T2 common valid class counts
   - Sum of net changes == 0 (zero-sum conservation)
   - common_valid_pixels + incomparable_pixels == total_aoi_pixels
6. Missing Ratio Governance:
   - Missing ratio <= 15% -> CERTIFIED_RELIABLE
   - Missing ratio > 15% -> PROVISIONAL_UNCERTAIN with explicit warning.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import numpy as np
import pytest

# Ensure local workspace is on sys.path
WORKSPACE_DIR = Path(__file__).resolve().parent
if str(WORKSPACE_DIR) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_DIR))

from common_valid_transition import (
    DEFAULT_CLASS_NAMES,
    DEFAULT_CLASS_COLORS,
    DEFAULT_NODATA,
    TRANSITION_NODATA,
    M2_PER_HA,
    PROVISIONAL_MISSING_RATIO_THRESHOLD,
    ReliabilityStatus,
    CertificationBlockedError,
    assert_raster_alignment,
    compute_common_valid_transition,
)


class TestPreflightSpatialAlignment:
    """Preflight alignment verification tests."""

    def test_identical_profiles_pass(self):
        p1 = {
            "crs": "EPSG:32748",
            "transform": (10.0, 0.0, 500000.0, 0.0, -10.0, 9300000.0),
            "width": 256,
            "height": 256,
        }
        p2 = dict(p1)
        # Must not raise
        assert_raster_alignment(p1, p2)

    def test_crs_mismatch_raises_value_error(self):
        p1 = {
            "crs": "EPSG:32748",
            "transform": (10.0, 0.0, 500000.0, 0.0, -10.0, 9300000.0),
            "width": 256,
            "height": 256,
        }
        p2 = dict(p1, crs="EPSG:4326")
        with pytest.raises(ValueError, match="래스터 공간 정합 불일치: crs"):
            assert_raster_alignment(p1, p2)

    def test_dimensions_mismatch_raises_value_error(self):
        p1 = {
            "crs": "EPSG:32748",
            "transform": (10.0, 0.0, 500000.0, 0.0, -10.0, 9300000.0),
            "width": 256,
            "height": 256,
        }
        p2 = dict(p1, width=257)
        with pytest.raises(ValueError, match="래스터 공간 정합 불일치: dimensions"):
            assert_raster_alignment(p1, p2)

    def test_half_pixel_offset_raises_value_error(self):
        p1 = {
            "crs": "EPSG:32748",
            "transform": (10.0, 0.0, 500000.0, 0.0, -10.0, 9300000.0),
            "width": 256,
            "height": 256,
        }
        # 5m shift (half of 10m resolution)
        p2 = dict(p1, transform=(10.0, 0.0, 500005.0, 0.0, -10.0, 9300000.0))
        with pytest.raises(ValueError, match="래스터 공간 정합 불일치: transform"):
            assert_raster_alignment(p1, p2)


class TestStrictNoDataExclusionAndMasqueradePrevention:
    """Tests preventing NoData from masquerading as unchanged, forest loss, or valid classes."""

    def test_nodata_in_t1_or_t2_strictly_excluded_from_matrix(self):
        # 4x4 setup:
        # T1 has Forest (class 1) everywhere except:
        # (0, 0): NoData (255)
        # (0, 1): NoData (255)
        # T2 has Built (class 6) everywhere except:
        # (0, 0): NoData (255)
        # (1, 0): NoData (255)
        t1 = np.full((4, 4), 1, dtype=np.uint8)
        t1[0, 0] = 255
        t1[0, 1] = 255

        t2 = np.full((4, 4), 6, dtype=np.uint8)
        t2[0, 0] = 255
        t2[1, 0] = 255

        result = compute_common_valid_transition(
            t1, t2,
            nodata=255,
            resolution_m=10.0,
            from_year=2020,
            to_year=2025,
        )

        # Total pixels: 16
        # Distinct missing pixels: (0,0), (0,1), (1,0) -> 3 pixels
        # Common valid pixels: 16 - 3 = 13
        assert result.partition.total_aoi_pixels == 16
        assert result.partition.common_valid_pixels == 13
        assert result.partition.incomparable_pixels == 3
        assert result.partition.incomparable.t1_only_missing_pixels == 1  # (0, 1)
        assert result.partition.incomparable.t2_only_missing_pixels == 1  # (1, 0)
        assert result.partition.incomparable.both_missing_pixels == 1     # (0, 0)

        # Transition matrix sum must be exactly 13
        matrix = np.array(result.transition_pixels)
        assert int(matrix.sum()) == 13
        # 1 (Forest) -> 6 (Built) must be exactly 13
        assert matrix[1, 6] == 13

    def test_t2_cloud_over_forest_is_not_falsely_counted_as_forest_loss(self):
        """CRITICAL: If a forest pixel in T1 is obscured by cloud (NoData) in T2,

        it MUST NOT be counted as Deforestation / Forest Loss.
        """
        # 4x4 raster: 10 pixels of Forest (1) in T1, 6 pixels of Water (0)
        t1 = np.array([
            [1, 1, 1, 1],
            [1, 1, 1, 1],
            [1, 1, 0, 0],
            [0, 0, 0, 0],
        ], dtype=np.uint8)

        # In T2, 4 forest pixels are obscured by heavy cloud (NoData = 255),
        # remaining 6 forest pixels stay forest, water stays water.
        t2 = np.array([
            [255, 255, 1, 1],  # (0,0) and (0,1) obscured by cloud
            [255, 255, 1, 1],  # (1,0) and (1,1) obscured by cloud
            [1, 1, 0, 0],      # stays forest and water
            [0, 0, 0, 0],      # stays water
        ], dtype=np.uint8)

        result = compute_common_valid_transition(t1, t2, nodata=255)

        # Forest class summary (class_id = 1)
        forest = next(c for c in result.classes if c.class_id == 1)

        # Common valid forest in T1 is 6 (the 4 cloud-covered pixels are excluded!)
        assert forest.t1_pixels == 6
        assert forest.t2_pixels == 6
        assert forest.unchanged_pixels == 6
        # Gross loss must be ZERO, not 4!
        assert forest.gross_loss_pixels == 0
        assert forest.gross_loss_ha == 0.0
        assert forest.net_change_pixels == 0
        assert forest.net_change_ha == 0.0

        # Incomparable pixels must be exactly 4
        assert result.partition.incomparable_pixels == 4
        assert result.partition.incomparable.t2_only_missing_pixels == 4

    def test_nodata_in_both_years_is_not_counted_as_unchanged_persistence(self):
        """If a pixel is NoData in both T1 and T2, it must NEVER be counted as unchanged."""
        t1 = np.full((3, 3), 255, dtype=np.uint8)  # All NoData
        t2 = np.full((3, 3), 255, dtype=np.uint8)  # All NoData

        result = compute_common_valid_transition(t1, t2, nodata=255)

        assert result.partition.total_aoi_pixels == 9
        assert result.partition.common_valid_pixels == 0
        assert result.partition.incomparable_pixels == 9
        assert result.partition.incomparable.both_missing_pixels == 9

        # Unchanged pixels must be 0, NOT 9!
        assert result.unchanged_pixels == 0
        assert result.changed_pixels == 0
        assert np.all(np.array(result.transition_pixels) == 0)

        # Raster map must be all TRANSITION_NODATA (65535)
        assert result.transition_raster is not None
        assert np.all(result.transition_raster == TRANSITION_NODATA)

    def test_quality_mask_excludes_cloud_and_shadow_pixels(self):
        """External binary quality mask (e.g. SCL cloud/shadow mask) strictly excludes invalid pixels."""
        t1 = np.full((4, 4), 1, dtype=np.uint8)
        t2 = np.full((4, 4), 2, dtype=np.uint8)

        # Quality mask: 0 means cloud/shadow, 1 means clear
        q1 = np.ones((4, 4), dtype=np.uint8)
        q1[0, 0] = 0  # Cloud in T1
        q2 = np.ones((4, 4), dtype=np.uint8)
        q2[1, 1] = 0  # Shadow in T2

        result = compute_common_valid_transition(
            t1, t2,
            quality_mask_t1=q1,
            quality_mask_t2=q2,
            nodata=255,
        )

        assert result.partition.total_aoi_pixels == 16
        assert result.partition.common_valid_pixels == 14
        assert result.partition.incomparable_pixels == 2
        assert result.partition.incomparable.t1_only_missing_pixels == 1
        assert result.partition.incomparable.t2_only_missing_pixels == 1


class TestMathematicalConservationInvariants:
    """Verifies all mathematical conservation proofs and identities."""

    def test_mathematical_conservation_laws(self):
        """Proof of mathematical identities:

        1. Total matrix sum == common_valid_pixels
        2. Row sum == T1 common valid counts
        3. Column sum == T2 common valid counts
        4. Sum of net changes == 0
        5. common_valid_pixels + incomparable_pixels == total_aoi_pixels
        """
        np.random.seed(42)
        shape = (50, 50)  # 2,500 pixels
        t1 = np.random.randint(0, 9, size=shape, dtype=np.uint8)
        t2 = np.random.randint(0, 9, size=shape, dtype=np.uint8)

        # Inject realistic NoData patterns
        t1[0:5, :] = 255  # North border missing
        t2[:, -5:] = 255  # East border missing
        # Random clouds
        cloud_t1 = np.random.rand(*shape) < 0.05
        cloud_t2 = np.random.rand(*shape) < 0.08
        t1[cloud_t1] = 255
        t2[cloud_t2] = 255

        # AOI mask: circle in center
        y, x = np.ogrid[:shape[0], :shape[1]]
        dist = np.sqrt((x - 25) ** 2 + (y - 25) ** 2)
        aoi_mask = dist <= 22  # Circular AOI

        result = compute_common_valid_transition(
            t1, t2,
            aoi_mask=aoi_mask,
            nodata=255,
            resolution_m=10.0,
            aoi_id="circular_test_aoi",
        )

        # Verify Conservation Check Badge
        assert result.conservation_check_passed is True

        matrix = np.array(result.transition_pixels)
        common_px = result.partition.common_valid_pixels

        # 1. Total matrix sum == common_valid_pixels
        assert int(matrix.sum()) == common_px

        # 2. Row sums == T1 common valid counts
        row_sums = matrix.sum(axis=1)
        for cid in range(9):
            assert row_sums[cid] == result.classes[cid].t1_pixels

        # 3. Column sums == T2 common valid counts
        col_sums = matrix.sum(axis=0)
        for cid in range(9):
            assert col_sums[cid] == result.classes[cid].t2_pixels

        # 4. Sum of net changes == 0
        sum_net = sum(c.net_change_pixels for c in result.classes)
        assert sum_net == 0

        # 5. Domain partition: common_valid + incomparable == total_aoi
        assert common_px + result.partition.incomparable_pixels == result.partition.total_aoi_pixels

        # 6. Incomparable partition identity
        inc = result.partition.incomparable
        assert inc.total_incomparable_pixels == (
            inc.t1_only_missing_pixels + inc.t2_only_missing_pixels + inc.both_missing_pixels
        )


class TestMissingRatioAndProvisionalFlag:
    """Tests governing the missing ratio threshold and provisional/uncertain badge."""

    def test_low_missing_ratio_is_certified_reliable(self):
        # 100 pixels, 5 missing (5% < 15%)
        t1 = np.full((10, 10), 1, dtype=np.uint8)
        t2 = np.full((10, 10), 2, dtype=np.uint8)
        t1[0, :5] = 255  # 5 pixels missing

        result = compute_common_valid_transition(
            t1, t2,
            nodata=255,
            provisional_threshold=0.15,
        )

        assert result.is_provisional is False
        assert result.reliability_status == ReliabilityStatus.CERTIFIED_RELIABLE.value
        assert result.provisional_warning is None
        assert pytest.approx(result.missing_ratio_pct, abs=1e-2) == 5.0

    def test_high_missing_ratio_triggers_provisional_uncertain_flag(self):
        # 100 pixels, 20 missing (20% > 15%)
        t1 = np.full((10, 10), 1, dtype=np.uint8)
        t2 = np.full((10, 10), 2, dtype=np.uint8)
        t1[0:2, :] = 255  # 20 pixels missing

        result = compute_common_valid_transition(
            t1, t2,
            nodata=255,
            provisional_threshold=0.15,
        )

        assert result.is_provisional is True
        assert result.reliability_status == ReliabilityStatus.PROVISIONAL_UNCERTAIN.value
        assert result.provisional_warning is not None
        assert "미확정(Provisional/Uncertain)" in result.provisional_warning
        assert pytest.approx(result.missing_ratio_pct, abs=1e-2) == 20.0

    def test_zero_aoi_pixels_handled_gracefully(self):
        """Edge case: Empty AOI mask returns zero-division safe result."""
        t1 = np.full((4, 4), 1, dtype=np.uint8)
        t2 = np.full((4, 4), 2, dtype=np.uint8)
        aoi_mask = np.zeros((4, 4), dtype=bool)

        result = compute_common_valid_transition(t1, t2, aoi_mask=aoi_mask)
        assert result.partition.total_aoi_pixels == 0
        assert result.partition.common_valid_pixels == 0
        assert result.partition.incomparable_pixels == 0
        assert result.missing_ratio_pct == 0.0
        assert result.is_provisional is False
        assert result.changed_pixels == 0
        assert result.unchanged_pixels == 0


class TestSerializationAndExport:
    """Tests JSON serialization and dictionary export."""

    def test_to_dict_and_to_json(self):
        t1 = np.array([[1, 2], [3, 4]], dtype=np.uint8)
        t2 = np.array([[1, 3], [3, 4]], dtype=np.uint8)

        result = compute_common_valid_transition(t1, t2, nodata=255)
        d = result.to_dict(include_raster=True)
        assert "partition" in d
        assert "transition_pixels" in d
        assert "conservation_identity" in d
        assert d["transition_raster_shape"] == [2, 2]

        json_str = result.to_json()
        parsed = json.loads(json_str)
        assert parsed["aoi_id"] == "custom_aoi"
        assert parsed["conservation_check_passed"] is True
        assert "certification_blocked" in parsed
        assert "year_mismatch_detected" in parsed


class TestMissingRateScenarios:
    """Verifies transition engine across comprehensive missing-rate scenarios (0%, 5%, 15%, 35%, 60%)."""

    @pytest.fixture
    def synthetic_landscape(self):
        """Creates a deterministic 100x100 (10,000 pixels) landscape with 9 land cover classes."""
        np.random.seed(42)
        h, w = 100, 100
        t1 = np.random.randint(0, 9, size=(h, w), dtype=np.uint8)
        t2 = t1.copy()
        # Create transitions on 1,500 pixels (15% true changes)
        change_idx = np.random.choice(10000, size=1500, replace=False)
        for idx in change_idx:
            r, c = divmod(idx, w)
            t2[r, c] = (t1[r, c] + np.random.randint(1, 9)) % 9
        return t1, t2

    @pytest.mark.parametrize(
        "missing_rate_pct,expected_status,expected_blocked",
        [
            (0.0, ReliabilityStatus.CERTIFIED_RELIABLE.value, False),
            (5.0, ReliabilityStatus.CERTIFIED_RELIABLE.value, False),
            (15.0, ReliabilityStatus.CERTIFIED_RELIABLE.value, False),
            (35.0, ReliabilityStatus.PROVISIONAL_UNCERTAIN.value, True),
            (60.0, ReliabilityStatus.PROVISIONAL_UNCERTAIN.value, True),
        ],
    )
    def test_missing_rate_scenarios_governance_and_partition(
        self, synthetic_landscape, missing_rate_pct, expected_status, expected_blocked
    ):
        t1, t2 = synthetic_landscape
        t1_masked = t1.copy()
        t2_masked = t2.copy()
        total_pixels = 10000

        missing_pixels = int(total_pixels * (missing_rate_pct / 100.0))
        if missing_pixels > 0:
            # Distribute missing pixels across T1-only (40%), T2-only (40%), and both (20%)
            t1_only_count = int(missing_pixels * 0.4)
            t2_only_count = int(missing_pixels * 0.4)
            both_count = missing_pixels - t1_only_count - t2_only_count

            np.random.seed(101)
            all_indices = np.random.choice(total_pixels, size=missing_pixels, replace=False)
            t1_indices = all_indices[:t1_only_count]
            t2_indices = all_indices[t1_only_count:t1_only_count + t2_only_count]
            both_indices = all_indices[t1_only_count + t2_only_count:]

            for idx in t1_indices:
                r, c = divmod(idx, 100)
                t1_masked[r, c] = 255
            for idx in t2_indices:
                r, c = divmod(idx, 100)
                t2_masked[r, c] = 255
            for idx in both_indices:
                r, c = divmod(idx, 100)
                t1_masked[r, c] = 255
                t2_masked[r, c] = 255

        result = compute_common_valid_transition(
            t1_masked, t2_masked,
            nodata=255,
            resolution_m=10.0,
            provisional_threshold=0.15,
        )

        # 1. 4-Way Area Partitioning Validation:
        part = result.partition
        assert part.total_aoi_pixels == total_pixels
        assert part.common_valid_pixels == total_pixels - missing_pixels
        assert part.incomparable_pixels == missing_pixels
        # Identity: Total = Common + Incomparable
        assert part.common_valid_pixels + part.incomparable_pixels == part.total_aoi_pixels
        # Identity: Incomparable = T1_only + T2_only + Both
        assert part.incomparable.total_incomparable_pixels == (
            part.incomparable.t1_only_missing_pixels
            + part.incomparable.t2_only_missing_pixels
            + part.incomparable.both_missing_pixels
        )
        assert pytest.approx(result.missing_ratio_pct, abs=1e-2) == missing_rate_pct

        # 2. Certification Gating Enforcement:
        assert result.reliability_status == expected_status
        assert result.certification_blocked is expected_blocked
        assert result.is_provisional is expected_blocked
        assert result.is_certified_usable is (not expected_blocked)

        if expected_blocked:
            with pytest.raises(CertificationBlockedError, match="공식 변경분석 인증 차단"):
                result.assert_certified_usable()
        else:
            result.assert_certified_usable()

        # 3. Zero-Sum Transition Identity Enforcement:
        assert result.conservation_check_passed is True
        matrix = np.array(result.transition_pixels)
        assert int(matrix.sum()) == part.common_valid_pixels
        assert matrix.shape == (9, 9)

        sum_gross_loss = sum(c.gross_loss_pixels for c in result.classes)
        sum_gross_gain = sum(c.gross_gain_pixels for c in result.classes)
        sum_net_changes = sum(c.net_change_pixels for c in result.classes)

        assert sum_gross_loss == sum_gross_gain
        assert sum_gross_gain - sum_gross_loss == sum_net_changes == 0
        for c in result.classes:
            assert c.gross_gain_pixels - c.gross_loss_pixels == c.net_change_pixels


class TestYearMismatchDetectionAndCertificationGating:
    """Verifies detection and gating of year mismatches (e.g. requested T2=2025 vs provenance 2021 ESA WorldCover)."""

    def test_matching_provenance_years_passes_certification(self):
        t1 = np.full((10, 10), 1, dtype=np.uint8)
        t2 = np.full((10, 10), 2, dtype=np.uint8)

        t1_meta = {"source_kind": "reference_landcover", "provenance_year": 2020}
        t2_meta = {"source_kind": "reference_landcover", "provenance_year": 2025}

        result = compute_common_valid_transition(
            t1, t2,
            from_year=2020,
            to_year=2025,
            t1_metadata=t1_meta,
            t2_metadata=t2_meta,
        )

        assert result.year_mismatch_detected is False
        assert result.year_mismatch_details is None
        assert result.certification_blocked is False
        assert result.reliability_status == ReliabilityStatus.CERTIFIED_RELIABLE.value
        assert result.is_certified_usable is True
        result.assert_certified_usable()

    def test_mismatched_t2_provenance_year_degrades_and_blocks_certification(self):
        """Requested T2=2025, but underlying raster provenance is 2021 ESA WorldCover."""
        t1 = np.full((10, 10), 1, dtype=np.uint8)
        t2 = np.full((10, 10), 2, dtype=np.uint8)

        t1_meta = {"source_kind": "reference_landcover", "provenance_year": 2020}
        t2_meta = {"source_kind": "reference_landcover", "provenance_year": 2021, "dataset_name": "ESA WorldCover"}

        result = compute_common_valid_transition(
            t1, t2,
            from_year=2020,
            to_year=2025,  # Requesting 2025!
            t1_metadata=t1_meta,
            t2_metadata=t2_meta,
        )

        assert result.year_mismatch_detected is True
        assert result.year_mismatch_details is not None
        assert result.year_mismatch_details["t2_requested_year"] == 2025
        assert result.year_mismatch_details["t2_provenance_year"] == 2021
        assert result.certification_blocked is True
        assert result.is_provisional is True
        assert result.reliability_status == ReliabilityStatus.PROVISIONAL_UNCERTAIN.value
        assert result.is_certified_usable is False
        assert "연도 불일치" in result.provisional_warning

        with pytest.raises(CertificationBlockedError, match="공식 변경분석 인증 차단.*연도 불일치"):
            result.assert_certified_usable()

    def test_enforce_year_match_raises_value_error(self):
        t1 = np.full((5, 5), 1, dtype=np.uint8)
        t2 = np.full((5, 5), 2, dtype=np.uint8)

        with pytest.raises(ValueError, match="요청 연도와 래스터 출처 연도 불일치"):
            compute_common_valid_transition(
                t1, t2,
                from_year=2020,
                to_year=2025,
                t2_provenance_year=2021,
                enforce_year_match=True,
            )

    def test_combined_high_missing_and_year_mismatch(self):
        """Simultaneous >15% missing data and provenance year mismatch."""
        t1 = np.full((10, 10), 1, dtype=np.uint8)
        t2 = np.full((10, 10), 2, dtype=np.uint8)
        t1[:3, :] = 255  # 30% missing

        t2_meta = {"provenance_year": 2021}
        result = compute_common_valid_transition(
            t1, t2,
            from_year=2020,
            to_year=2025,
            t2_metadata=t2_meta,
            provisional_threshold=0.15,
        )

        assert result.certification_blocked is True
        assert result.is_provisional is True
        assert result.year_mismatch_detected is True
        assert result.missing_ratio_pct == 30.0
        assert "결측률" in result.provisional_warning
        assert "연도 불일치" in result.provisional_warning

