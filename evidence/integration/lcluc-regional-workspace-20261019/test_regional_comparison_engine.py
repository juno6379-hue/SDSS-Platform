"""Unit tests for LCLUC Regional Comparison & Benchmarking Engine.

Verifies:
1. Rate calculations, zero-division guards, unit conversions (m2 to ha).
2. Comparative ranking correctness and tied scores handling.
3. 10 Canonical Indonesian province benchmark profiles.
4. Radar and bar chart JSON schemas matching frontend expectations.
5. JSON and CSV export integrity.
"""

import csv
import json
import math
from pathlib import Path
import numpy as np
import pytest

from regional_comparison_engine import (
    DEFAULT_CLASS_NAMES,
    M2_PER_HA,
    ProvinceRecord,
    RegionalMetrics,
    RegionalComparisonEngine,
    RiskStatus,
    ha_to_m2,
    m2_to_ha,
)


# ============================================================================
# 1. Unit Conversions & Zero-Division Guard Tests
# ============================================================================

class TestUnitConversionsAndGuards:
    def test_m2_to_ha(self):
        assert m2_to_ha(10000.0) == 1.0
        assert m2_to_ha(0.0) == 0.0
        assert m2_to_ha(50000.0) == 5.0
        with pytest.raises(ValueError):
            m2_to_ha(-1.0)

    def test_ha_to_m2(self):
        assert ha_to_m2(1.0) == 10000.0
        assert ha_to_m2(0.0) == 0.0
        assert ha_to_m2(3.5) == 35000.0
        with pytest.raises(ValueError):
            ha_to_m2(-5.0)

    def test_zero_initial_forest_guard(self):
        # Province with zero forest (e.g. urban metro like DKI Jakarta)
        mat = np.zeros((9, 9), dtype=np.float64)
        mat[6, 6] = ha_to_m2(500.0)  # built-up only
        mat[4, 4] = ha_to_m2(200.0)  # crops only

        rec = ProvinceRecord(
            province_id="jakarta",
            name_ko="자카르타",
            name_en="DKI Jakarta",
            from_year=2020,
            to_year=2025,
            matrix_m2=mat,
        )
        engine = RegionalComparisonEngine()
        metrics = engine.compute_province_metrics(rec)

        assert metrics.initial_forest_ha == 0.0
        assert metrics.annual_deforestation_rate_pct == 0.0
        assert metrics.forest_retention_rate_pct == 100.0
        assert not math.isnan(metrics.annual_deforestation_rate_pct)

    def test_zero_initial_built_guard(self):
        # Province with zero initial built-up
        mat = np.zeros((9, 9), dtype=np.float64)
        mat[1, 1] = ha_to_m2(1000.0)
        # New built-up emerges from forest
        mat[1, 6] = ha_to_m2(50.0)

        rec = ProvinceRecord(
            province_id="wilderness",
            name_ko="원시림",
            name_en="Wilderness",
            from_year=2020,
            to_year=2025,
            matrix_m2=mat,
        )
        engine = RegionalComparisonEngine()
        metrics = engine.compute_province_metrics(rec)

        assert metrics.initial_built_ha == 0.0
        assert metrics.gross_urban_gain_ha == 50.0
        assert metrics.urban_expansion_growth_pct == 0.0
        assert not math.isnan(metrics.urban_expansion_growth_pct)

    def test_zero_total_change_guard(self):
        # Identity matrix: no change at all
        mat = np.eye(9) * ha_to_m2(200.0)
        rec = ProvinceRecord(
            province_id="stable",
            name_ko="안정",
            name_en="Stable",
            from_year=2020,
            to_year=2025,
            matrix_m2=mat,
        )
        engine = RegionalComparisonEngine()
        metrics = engine.compute_province_metrics(rec)

        assert metrics.gross_forest_loss_ha == 0.0
        assert metrics.agricultural_conversion_ratio_pct == 0.0
        assert metrics.landscape_stability_index == 100.0
        assert metrics.forest_retention_rate_pct == 100.0
        assert metrics.risk_status == RiskStatus.STABLE


# ============================================================================
# 2. ProvinceRecord Validation Tests
# ============================================================================

class TestProvinceRecordValidation:
    def test_valid_record(self):
        mat = np.eye(9) * 10000.0
        rec = ProvinceRecord("p1", "테스트", "Test", 2020, 2025, mat)
        assert rec.num_classes if hasattr(rec, "num_classes") else rec.matrix_m2.shape[0] == 9
        assert rec.elapsed_years == 5.0
        assert rec.total_area_ha == 9.0

    def test_non_square_matrix_rejected(self):
        with pytest.raises(ValueError, match="square 2D"):
            ProvinceRecord("p1", "테스트", "Test", 2020, 2025, np.zeros((9, 8)))

    def test_negative_values_rejected(self):
        mat = np.eye(9) * 1000.0
        mat[0, 0] = -50.0
        with pytest.raises(ValueError, match="non-negative"):
            ProvinceRecord("p1", "테스트", "Test", 2020, 2025, mat)

    def test_invalid_year_range_rejected(self):
        with pytest.raises(ValueError, match="to_year"):
            ProvinceRecord("p1", "테스트", "Test", 2025, 2020, np.eye(9))


# ============================================================================
# 3. Known Analytical Metrics Calculation Tests
# ============================================================================

class TestRegionalMetricsComputation:
    def test_known_analytical_metrics(self):
        # Setup:
        # Initial forest = 1000 ha
        # Preserved forest = 900 ha
        # Forest to crops = 70 ha
        # Forest to built = 30 ha
        # Initial built = 200 ha
        # Built gain = 30 ha (from forest) + 20 ha (from grass) = 50 ha
        # Elapsed = 5 years
        mat = np.zeros((9, 9), dtype=np.float64)
        mat[1, 1] = ha_to_m2(900.0)
        mat[1, 4] = ha_to_m2(70.0)
        mat[1, 6] = ha_to_m2(30.0)
        mat[2, 6] = ha_to_m2(20.0)  # grass -> built
        mat[6, 6] = ha_to_m2(200.0) # preserved built
        mat[4, 4] = ha_to_m2(500.0) # preserved crops

        rec = ProvinceRecord(
            province_id="analyt",
            name_ko="해석지역",
            name_en="Analytical",
            from_year=2020,
            to_year=2025,
            matrix_m2=mat,
        )
        engine = RegionalComparisonEngine()
        m = engine.compute_province_metrics(rec)

        # Deforestation:
        # Gross loss = 70 + 30 = 100 ha over 5 years
        assert m.gross_forest_loss_ha == 100.0
        assert m.annual_deforestation_ha_yr == 20.0
        # Deforestation rate = (100 / 1000) * (100 / 5) = 2.0 %/yr
        assert math.isclose(m.annual_deforestation_rate_pct, 2.0, rel_tol=1e-3)
        # Forest retention = 900 / 1000 = 90.0 %
        assert math.isclose(m.forest_retention_rate_pct, 90.0, rel_tol=1e-3)

        # Urbanization:
        # Gross urban gain = 30 + 20 = 50 ha over 5 yrs = 10 ha/yr
        assert m.gross_urban_gain_ha == 50.0
        assert m.annual_urban_expansion_ha_yr == 10.0
        # Urban growth % = 50 / 200 = 25.0 %
        assert math.isclose(m.urban_expansion_growth_pct, 25.0, rel_tol=1e-3)

        # Agri conversion:
        assert m.agricultural_conversion_ha == 70.0

        # High risk flag since deforest rate >= 2.0%
        assert m.risk_status == RiskStatus.HIGH_RISK


# ============================================================================
# 4. Comparative Rankings & Ties Handling Tests
# ============================================================================

class TestComparativeRankingsAndTies:
    def test_ranking_descending_by_rtpi(self):
        engine = RegionalComparisonEngine()

        # Province A: High deforest (10% loss)
        mat_a = np.zeros((9, 9), dtype=np.float64)
        mat_a[1, 1] = ha_to_m2(800.0)
        mat_a[1, 4] = ha_to_m2(200.0)
        engine.add_province("pA", "고위험", "HighRisk", mat_a, 2020, 2025)

        # Province B: Moderate deforest (2% loss)
        mat_b = np.zeros((9, 9), dtype=np.float64)
        mat_b[1, 1] = ha_to_m2(980.0)
        mat_b[1, 4] = ha_to_m2(20.0)
        engine.add_province("pB", "보통", "Moderate", mat_b, 2020, 2025)

        # Province C: Zero deforest
        mat_c = np.eye(9) * ha_to_m2(100.0)
        engine.add_province("pC", "안정", "Stable", mat_c, 2020, 2025)

        results = engine.compute_all()
        assert results["pA"].rank == 1
        assert results["pB"].rank == 2
        assert results["pC"].rank == 3

        assert results["pA"].percentile == 100.0
        assert results["pB"].percentile == 50.0
        assert results["pC"].percentile == 0.0

    def test_tied_rtpi_secondary_sort(self):
        engine = RegionalComparisonEngine()
        # Two identical zero-change provinces
        mat = np.eye(9) * ha_to_m2(100.0)
        engine.add_province("p1", "지역1", "Region 1", mat, 2020, 2025)
        engine.add_province("p2", "지역2", "Region 2", mat, 2020, 2025)

        results = engine.compute_all()
        assert {results["p1"].rank, results["p2"].rank} == {1, 2}


# ============================================================================
# 5. Canonical 10 Indonesian Province Benchmarks Tests
# ============================================================================

class TestCanonicalBenchmarks:
    def test_canonical_benchmarks_loading(self):
        engine = RegionalComparisonEngine()
        engine.load_canonical_indonesia_benchmarks(2020, 2025)

        expected_ids = {
            "riau", "north_sumatra", "south_sulawesi", "southeast_sulawesi",
            "gorontalo", "west_java", "central_java", "east_java", "banten", "aceh"
        }
        assert set(engine.provinces.keys()) == expected_ids
        assert len(engine.provinces) == 10

        metrics = engine.compute_all()
        assert len(metrics) == 10

        # Check all RTPI scores between 0 and 100
        for m in metrics.values():
            assert 0.0 <= m.rtpi_score <= 100.0
            assert 0.0 <= m.forest_retention_rate_pct <= 100.0
            assert m.annual_deforestation_rate_pct >= 0.0
            assert m.annual_urban_expansion_ha_yr >= 0.0
            assert m.rank in range(1, 11)

        # Riau should have high risk due to extensive deforestation
        assert metrics["riau"].risk_status == RiskStatus.HIGH_RISK
        assert metrics["riau"].annual_deforestation_ha_yr > 30000.0

        # Central Java has settled agricultural landscape and lower deforestation
        assert metrics["central_java"].annual_deforestation_ha_yr < 10000.0


# ============================================================================
# 6. Visual Dataset Generators & JSON Schemas Tests
# ============================================================================

class TestVisualDatasetGeneratorsAndJSONSchemas:
    def test_benchmarking_table_format(self):
        engine = RegionalComparisonEngine()
        engine.load_canonical_indonesia_benchmarks()
        table = engine.generate_benchmarking_table()

        assert "columns" in table
        assert "rows" in table
        assert len(table["rows"]) == 10
        assert table["total_provinces"] == 10

        # Verify columns match frontend expectations
        assert table["columns"] == [
            "순위",
            "지역 (Province)",
            "산림 벌채율 (%/년)",
            "도시 확장 (ha/년)",
            "산림 보존율 (%)",
            "농업 전환 (ha)",
            "전이 압력 (RTPI)",
            "위험 등급",
        ]

        # Verify each row has 8 entries
        for row in table["rows"]:
            assert len(row) == 8
            assert row[7] in ("HIGH_RISK", "MODERATE", "STABLE")

    def test_bar_chart_data_format(self):
        engine = RegionalComparisonEngine()
        engine.load_canonical_indonesia_benchmarks()
        bar = engine.generate_bar_chart_data()

        assert bar["chart_type"] == "comparative_bar"
        assert len(bar["categories"]) == 10
        assert len(bar["series"]) == 3

        for s in bar["series"]:
            assert len(s["data"]) == 10
            assert all(isinstance(v, (int, float)) for v in s["data"])

    def test_radar_chart_data_format(self):
        engine = RegionalComparisonEngine()
        engine.load_canonical_indonesia_benchmarks()
        radar = engine.generate_radar_chart_data()

        assert radar["chart_type"] == "radar_5axis"
        assert len(radar["axes"]) == 5
        assert len(radar["provinces"]) == 10

        for p in radar["provinces"]:
            assert len(p["values"]) == 5
            for val in p["values"]:
                assert 0.0 <= val <= 100.0

    def test_full_payload_roundtrip_and_export(self, tmp_path):
        engine = RegionalComparisonEngine()
        engine.load_canonical_indonesia_benchmarks()

        payload = engine.generate_full_comparison_payload()
        assert payload["workspace"] == "lcluc_regional_comparison"
        assert len(payload["summary_kpis"]) == 4

        # Verify round-trip JSON serialization
        json_str = json.dumps(payload, ensure_ascii=False)
        parsed = json.loads(json_str)
        assert parsed["workspace"] == "lcluc_regional_comparison"

        # Verify disk export
        files = engine.export_payloads(tmp_path)
        assert files["payload_json"].is_file()
        assert files["benchmarking_csv"].is_file()

        # Verify CSV contents
        with files["benchmarking_csv"].open("r", encoding="utf-8-sig") as f:
            reader = list(csv.reader(f))
            assert len(reader) == 11  # header + 10 rows
            assert reader[0][0] == "순위"
