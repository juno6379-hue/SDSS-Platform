"""Unit tests for LCLUC Downstream Bridge for Net Carbon and Biodiversity Workspaces.

Verifies:
1. IPCC Carbon calculation bounds and scientific constants
2. Unit conversions (m2 to ha, ha to m2, tC to tCO2e, tCO2e to tC)
3. Transition input parsers (report.json, transitions.csv, matrix)
4. Net Carbon calculations (deforestation, peat oxidation, reforestation, sector budgets)
5. Biodiversity landscape metrics (2D patch BFS, core buffering, fragmentation index, connectivity)
6. Standardized JSON schemas compatibility with ModelAnalysisWorkspace.tsx
"""

import csv
import json
import math
from pathlib import Path
import numpy as np
import pytest

from lcluc_downstream_bridge import (
    DEFAULT_CLASS_NAMES,
    M2_PER_HA,
    C_TO_CO2_RATIO,
    IPCCCarbonParameters,
    BiodiversityParameters,
    LCLUCTransitionInput,
    NetCarbonBridge,
    BiodiversityBridge,
    LCLUCDownstreamBridge,
    compute_patch_metrics_2d,
    ha_to_m2,
    m2_to_ha,
    tC_to_tCO2e,
    tCO2e_to_tC,
)


# ============================================================================
# 1. Unit Conversions & Constant Tests
# ============================================================================

class TestUnitConversions:
    def test_m2_to_ha(self):
        assert m2_to_ha(10000.0) == 1.0
        assert m2_to_ha(0.0) == 0.0
        assert m2_to_ha(250000.0) == 25.0
        with pytest.raises(ValueError):
            m2_to_ha(-10.0)

    def test_ha_to_m2(self):
        assert ha_to_m2(1.0) == 10000.0
        assert ha_to_m2(0.0) == 0.0
        assert ha_to_m2(2.5) == 25000.0
        with pytest.raises(ValueError):
            ha_to_m2(-5.0)

    def test_tC_to_tCO2e_and_inverse(self):
        # 12 g C in 44 g CO2
        expected_ratio = 44.0 / 12.0
        assert math.isclose(C_TO_CO2_RATIO, expected_ratio, rel_tol=1e-9)
        assert math.isclose(tC_to_tCO2e(1.0), expected_ratio, rel_tol=1e-9)
        assert math.isclose(tCO2e_to_tC(expected_ratio), 1.0, rel_tol=1e-9)

        # Roundtrip test
        val_tC = 123.456
        assert math.isclose(tCO2e_to_tC(tC_to_tCO2e(val_tC)), val_tC, rel_tol=1e-9)


# ============================================================================
# 2. IPCC Carbon Parameters & Scientific Bounds
# ============================================================================

class TestIPCCCarbonParameters:
    def test_default_parameters_are_valid(self):
        params = IPCCCarbonParameters()
        params.validate()
        assert params.forest_loss_biomass_c_density_tC_ha == 300.0
        assert params.peat_oxidation_ef_tCO2e_ha_yr == 55.0
        assert params.plantation_c_stock_tC_ha == 60.0

    def test_forest_biomass_bounds(self):
        # Bound [280, 350]
        IPCCCarbonParameters(forest_loss_biomass_c_density_tC_ha=280.0).validate()
        IPCCCarbonParameters(forest_loss_biomass_c_density_tC_ha=350.0).validate()

        with pytest.raises(ValueError, match="forest_loss_biomass_c_density_tC_ha"):
            IPCCCarbonParameters(forest_loss_biomass_c_density_tC_ha=279.0).validate()

        with pytest.raises(ValueError, match="forest_loss_biomass_c_density_tC_ha"):
            IPCCCarbonParameters(forest_loss_biomass_c_density_tC_ha=351.0).validate()

    def test_peat_oxidation_bounds(self):
        # Bound [40, 70]
        IPCCCarbonParameters(peat_oxidation_ef_tCO2e_ha_yr=40.0).validate()
        IPCCCarbonParameters(peat_oxidation_ef_tCO2e_ha_yr=70.0).validate()

        with pytest.raises(ValueError, match="peat_oxidation_ef_tCO2e_ha_yr"):
            IPCCCarbonParameters(peat_oxidation_ef_tCO2e_ha_yr=39.0).validate()

        with pytest.raises(ValueError, match="peat_oxidation_ef_tCO2e_ha_yr"):
            IPCCCarbonParameters(peat_oxidation_ef_tCO2e_ha_yr=71.0).validate()

    def test_plantation_bounds(self):
        # Bound [50, 80]
        IPCCCarbonParameters(plantation_c_stock_tC_ha=50.0).validate()
        IPCCCarbonParameters(plantation_c_stock_tC_ha=80.0).validate()

        with pytest.raises(ValueError, match="plantation_c_stock_tC_ha"):
            IPCCCarbonParameters(plantation_c_stock_tC_ha=49.0).validate()

    def test_stock_for_class_name(self):
        p = IPCCCarbonParameters()
        assert p.get_stock_for_class_name("trees") == 300.0
        assert p.get_stock_for_class_name("Tropical Rainforest") == 300.0
        assert p.get_stock_for_class_name("산림 (Forest)") == 300.0
        assert p.get_stock_for_class_name("flooded_vegetation") == 320.0
        assert p.get_stock_for_class_name("맹그로브 (Mangrove)") == 320.0
        assert p.get_stock_for_class_name("plantation") == 60.0
        assert p.get_stock_for_class_name("shrub_and_scrub") == 35.0
        assert p.get_stock_for_class_name("grass") == 6.0
        assert p.get_stock_for_class_name("crops") == 5.0
        assert p.get_stock_for_class_name("built") == 0.0
        assert p.get_stock_for_class_name("bare") == 0.0
        assert p.get_stock_for_class_name("water") == 0.0


# ============================================================================
# 3. LCLUCTransitionInput Tests
# ============================================================================

class TestLCLUCTransitionInput:
    def test_transition_matrix_properties(self):
        mat = np.zeros((9, 9), dtype=np.float64)
        np.fill_diagonal(mat, 100000.0)  # 10 ha each = 90 ha total
        mat[1, 4] = 50000.0              # 5 ha trees -> crops
        mat[4, 1] = 20000.0              # 2 ha crops -> trees

        inp = LCLUCTransitionInput(
            matrix_m2=mat,
            from_year=2020,
            to_year=2025,
            region="South Sulawesi",
        )

        assert inp.num_classes == 9
        assert inp.elapsed_years == 5.0
        assert inp.total_area_m2 == 900000.0 + 70000.0
        assert inp.total_area_ha == 97.0
        assert inp.changed_area_m2 == 70000.0
        assert inp.changed_area_ha == 7.0
        assert math.isclose(inp.change_rate, 70000.0 / 970000.0)

    def test_validation_errors(self):
        with pytest.raises(ValueError, match="square 2D"):
            LCLUCTransitionInput(matrix_m2=np.zeros((9, 8)))

        with pytest.raises(ValueError, match="non-negative"):
            bad_mat = np.zeros((3, 3))
            bad_mat[0, 0] = -10.0
            LCLUCTransitionInput(matrix_m2=bad_mat)

        with pytest.raises(ValueError, match="to_year"):
            LCLUCTransitionInput(matrix_m2=np.zeros((3, 3)), from_year=2025, to_year=2020)

    def test_from_report_dict(self):
        report = {
            "transition_area_m2": [
                [10000.0, 0.0],
                [5000.0, 20000.0],
            ],
            "transition_pixels": [
                [100, 0],
                [50, 200],
            ],
            "class_names": ["water", "trees"],
            "area_method": "projected_grid_area_m2",
        }
        inp = LCLUCTransitionInput.from_report_dict(report, from_year=2020, to_year=2023)
        assert inp.num_classes == 2
        assert inp.total_area_ha == 3.5
        assert inp.changed_area_ha == 0.5
        assert inp.elapsed_years == 3.0

    def test_from_transitions_csv(self, tmp_path):
        csv_file = tmp_path / "transitions.csv"
        with csv_file.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["from_class", "to_class", "pixels", "area_m2"])
            writer.writerow([0, 0, 100, 10000.0])
            writer.writerow([0, 1, 20, 2000.0])
            writer.writerow([1, 0, 10, 1000.0])
            writer.writerow([1, 1, 300, 30000.0])

        inp = LCLUCTransitionInput.from_transitions_csv(csv_file, class_names=["water", "trees"])
        assert inp.num_classes == 2
        assert inp.total_area_ha == 4.3
        assert inp.changed_area_ha == 0.3

    def test_from_timeseries_dict(self):
        timeseries = {
            "years": [2020, 2021],
            "adjacent_pairs": ["2020-2021"],
            "class_names": list(DEFAULT_CLASS_NAMES),
            "changes": {
                "2020-2021": {
                    "transition_area_m2": (np.eye(9) * 10000.0).tolist(),
                    "transition_pixels": (np.eye(9) * 100).tolist(),
                    "valid_pixels": 900,
                    "total_area_m2": 90000.0,
                    "changed_area_m2": 0.0,
                    "area_method": "projected_grid_area_m2",
                }
            }
        }
        inp = LCLUCTransitionInput.from_timeseries_dict(timeseries, pair="2020-2021")
        assert inp.from_year == 2020
        assert inp.to_year == 2021
        assert inp.total_area_ha == 9.0
        assert inp.changed_area_ha == 0.0

    def test_from_timeseries_json(self, tmp_path):
        ts_file = tmp_path / "timeseries.json"
        timeseries = {
            "adjacent_pairs": ["2020-2022"],
            "class_names": list(DEFAULT_CLASS_NAMES),
            "changes": {
                "2020-2022": {
                    "transition_area_m2": (np.eye(9) * 50000.0).tolist(),
                    "transition_pixels": (np.eye(9) * 500).tolist(),
                    "valid_pixels": 4500,
                    "total_area_m2": 450000.0,
                    "changed_area_m2": 0.0,
                    "area_method": "projected_grid_area_m2",
                }
            }
        }
        ts_file.write_text(json.dumps(timeseries), encoding="utf-8")
        inp = LCLUCTransitionInput.from_timeseries_json(ts_file)
        assert inp.from_year == 2020
        assert inp.to_year == 2022
        assert inp.total_area_ha == 45.0


# ============================================================================
# 4. Net Carbon Bridge Tests (Deforestation, Peat Oxidation, Removals)
# ============================================================================

class TestNetCarbonBridge:
    def test_deforestation_emissions(self):
        # 100 ha forest (class 1) converted to cropland (class 4)
        mat = np.zeros((9, 9), dtype=np.float64)
        mat[1, 1] = ha_to_m2(1000.0)  # 1000 ha intact forest
        mat[1, 4] = ha_to_m2(100.0)   # 100 ha deforested to crops

        inp = LCLUCTransitionInput(matrix_m2=mat, from_year=2020, to_year=2021)
        params = IPCCCarbonParameters(
            forest_loss_biomass_c_density_tC_ha=300.0,
            crops_c_stock_tC_ha=5.0,
        )
        bridge = NetCarbonBridge(inp, params=params)
        res = bridge.calculate()

        # Expected biomass loss: 100 ha * (300 - 5) tC/ha = 29,500 tC
        # Expected CO2e = 29,500 * (44 / 12) = 108,166.67 tCO2e
        expected_tCO2e = 100.0 * 295.0 * (44.0 / 12.0)
        actual_gross = res["kpis"][0]["value"]
        assert math.isclose(actual_gross, expected_tCO2e, rel_tol=1e-3)
        assert res["activity_data"]["deforestation_ha"] == 100.0

    def test_peatland_oxidation_emissions(self):
        # 50 ha flooded_vegetation (class 3) converted to crops over 2 years
        mat = np.zeros((9, 9), dtype=np.float64)
        mat[3, 4] = ha_to_m2(50.0)

        inp = LCLUCTransitionInput(matrix_m2=mat, from_year=2020, to_year=2022)
        params = IPCCCarbonParameters(
            mangrove_c_stock_tC_ha=320.0,
            crops_c_stock_tC_ha=5.0,
            peat_oxidation_ef_tCO2e_ha_yr=55.0,
        )
        bridge = NetCarbonBridge(inp, params=params)
        res = bridge.calculate()

        # Biomass loss: 50 ha * (320 - 5) * (44 / 12) = 57,750 tCO2e
        # Peat oxidation: 50 ha * 55 tCO2e/ha/yr * 2 yrs = 5,500 tCO2e
        # Total: 63,250 tCO2e
        expected_total = (50.0 * 315.0 * (44.0 / 12.0)) + (50.0 * 55.0 * 2.0)
        assert math.isclose(res["kpis"][0]["value"], expected_total, rel_tol=1e-3)
        assert res["activity_data"]["peat_loss_ha"] == 50.0

    def test_reforestation_removals(self):
        # 80 ha crops (class 4) converted to forest (class 1) over 3 years
        mat = np.zeros((9, 9), dtype=np.float64)
        mat[4, 1] = ha_to_m2(80.0)

        inp = LCLUCTransitionInput(matrix_m2=mat, from_year=2020, to_year=2023)
        params = IPCCCarbonParameters(reforestation_accumulation_tC_ha_yr=6.5)
        bridge = NetCarbonBridge(inp, params=params)
        res = bridge.calculate()

        # Expected removal: 80 ha * 6.5 tC/ha/yr * (44 / 12) * 3 yrs = 5,720 tCO2e
        expected_removals = 80.0 * 6.5 * (44.0 / 12.0) * 3.0
        assert math.isclose(res["kpis"][1]["value"], expected_removals, rel_tol=1e-3)
        assert res["activity_data"]["reforestation_ha"] == 80.0

    def test_zero_change_yields_zero_emissions(self):
        # Non-zero diagonal, zero off-diagonal
        mat = np.eye(9) * ha_to_m2(500.0)
        inp = LCLUCTransitionInput(matrix_m2=mat, from_year=2020, to_year=2025)
        bridge = NetCarbonBridge(inp)
        res = bridge.calculate()

        assert res["kpis"][0]["value"] == 0.0  # Gross emissions
        assert res["kpis"][1]["value"] == 0.0  # Gross removals
        assert res["kpis"][2]["value"] == 0.0  # Net carbon balance

    def test_sectoral_carbon_balance_rows(self):
        mat = np.eye(9) * ha_to_m2(100.0)
        mat[1, 4] = ha_to_m2(20.0)
        inp = LCLUCTransitionInput(matrix_m2=mat, from_year=2020, to_year=2021)
        bridge = NetCarbonBridge(inp)
        res = bridge.calculate()

        sector_table = res["bottom_panels"]["sector_balance"]
        assert sector_table["columns"] == ["부문", "배출", "흡수", "수지"]
        sectors = [row[0] for row in sector_table["rows"]]
        assert sectors == ["산업·에너지", "교통", "건물", "농업", "토지이용·산림", "폐기물"]


# ============================================================================
# 5. Biodiversity Landscape Metrics & Spatial Fragmentation Tests
# ============================================================================

class TestBiodiversityBridge:
    def test_2d_raster_patch_metrics_solid_core(self):
        # 50x50 solid grid of forest (1)
        grid = np.ones((50, 50), dtype=np.uint8)
        # Resolution 10m, buffer 100m (10 pixels)
        metrics = compute_patch_metrics_2d(grid, habitat_values=[1], resolution_m=10.0, edge_depth_m=100.0)

        assert metrics["patch_count"] == 1
        assert metrics["total_habitat_ha"] == 2500 * (100.0 / 10000.0)  # 25 ha
        # Interior core after 10 pixels erosion: (50-20)x(50-20) = 30x30 = 900 pixels = 9 ha
        assert metrics["core_habitat_ha"] == 900 * 0.01  # 9 ha
        assert math.isclose(metrics["core_area_ratio"], 900.0 / 2500.0, rel_tol=1e-3)
        assert metrics["fragmentation_index"] == round(1.0 - (900.0 / 2500.0), 4)
        assert metrics["largest_patch_index_pct"] == 100.0
        assert metrics["connectivity_index"] > 0.3

    def test_2d_raster_patch_metrics_fragmented_checkerboard(self):
        # Highly fragmented checkerboard pattern (all pixels touch edges)
        grid = np.zeros((20, 20), dtype=np.uint8)
        grid[::2, ::2] = 1  # isolated single pixels

        metrics = compute_patch_metrics_2d(grid, habitat_values=[1], resolution_m=10.0, edge_depth_m=10.0)
        assert metrics["patch_count"] == 100
        assert metrics["core_habitat_ha"] == 0.0
        assert metrics["core_area_ratio"] == 0.0
        assert metrics["fragmentation_index"] == 1.0
        assert metrics["connectivity_index"] == 0.0

    def test_2d_raster_empty_habitat(self):
        grid = np.zeros((30, 30), dtype=np.uint8)
        metrics = compute_patch_metrics_2d(grid, habitat_values=[1])
        assert metrics["patch_count"] == 0
        assert metrics["core_habitat_ha"] == 0.0
        assert metrics["fragmentation_index"] == 1.0

    def test_biodiversity_bridge_with_matrix_analytical_proxy(self):
        mat = np.zeros((9, 9), dtype=np.float64)
        mat[1, 1] = ha_to_m2(800.0)  # 800 ha intact forest
        mat[1, 4] = ha_to_m2(200.0)  # 200 ha lost forest
        mat[3, 3] = ha_to_m2(100.0)  # 100 ha mangrove
        mat[4, 4] = ha_to_m2(400.0)  # 400 ha cropland

        inp = LCLUCTransitionInput(matrix_m2=mat, from_year=2020, to_year=2025)
        bridge = BiodiversityBridge(inp)
        res = bridge.calculate()

        # Check KPIs
        kpis = {k["label"]: k["value"] for k in res["kpis"]}
        assert "보호지역 면적" in kpis
        assert "적합 서식지 비율" in kpis
        assert "연결성 지수" in kpis
        assert "보전 우선지역 수" in kpis

        # Habitat loss metrics
        assert res["habitat_metrics"]["forest_loss_ha"] == 200.0
        assert res["habitat_metrics"]["final_habitat_ha"] == 900.0  # 800 forest + 100 mangrove

        # Donut classes check
        donut_grades = [c["grade"] for c in res["bottom_panels"]["suitability_distribution"]["classes"]]
        assert "매우 높음 (0.8–1.0)" in donut_grades
        assert "높음 (0.6–0.8)" in donut_grades
        assert "보호구역" in donut_grades

        # Threat items check
        threat_names = [t["name"] for t in res["bottom_panels"]["threats"]["items"]]
        assert threat_names == ["산림 벌채", "토지이용 변화", "광업", "도로·인프라", "불법 포획", "침입종"]


# ============================================================================
# 6. JSON Schema Compatibility & Full Orchestration Tests
# ============================================================================

class TestOrchestratorAndSchemaCompatibility:
    def test_orchestrator_process(self):
        mat = np.eye(9) * ha_to_m2(500.0)
        mat[1, 4] = ha_to_m2(50.0)  # Deforestation
        mat[4, 1] = ha_to_m2(10.0)  # Reforestation

        inp = LCLUCTransitionInput(matrix_m2=mat, from_year=2020, to_year=2025, region="South Sulawesi")
        orchestrator = LCLUCDownstreamBridge()
        result = orchestrator.process(inp)

        assert "carbon_workspace" in result
        assert "biodiversity_workspace" in result
        assert "provenance" in result

        carbon_ws = result["carbon_workspace"]
        bio_ws = result["biodiversity_workspace"]

        # 1. Carbon Workspace schema
        assert carbon_ws["workspace"] == "carbon"
        assert len(carbon_ws["kpis"]) == 4
        carbon_kpi_labels = [k["label"] for k in carbon_ws["kpis"]]
        assert carbon_kpi_labels == ["총 배출량", "총 흡수량", "순 탄소 배출", "감축 잠재량"]

        assert carbon_ws["summary"]["title"] == "탄소 배출 핫스팟"
        assert carbon_ws["summary"]["columns"] == ["지역", "순 배출량", "변화", "주요 기여 부문"]

        assert "trend" in carbon_ws["bottom_panels"]
        assert "absorption" in carbon_ws["bottom_panels"]
        assert "sector_balance" in carbon_ws["bottom_panels"]
        assert "mitigation_options" in carbon_ws["bottom_panels"]

        # 2. Biodiversity Workspace schema
        assert bio_ws["workspace"] == "biodiversity"
        assert len(bio_ws["kpis"]) == 4
        bio_kpi_labels = [k["label"] for k in bio_ws["kpis"]]
        assert bio_kpi_labels == ["보호지역 면적", "적합 서식지 비율", "연결성 지수", "보전 우선지역 수"]

        assert bio_ws["summary"]["title"] == "보전 우선순위"
        assert bio_ws["summary"]["columns"] == ["지역 / 구역", "우선순위 점수", "면적 (ha)", "분류"]

        assert "trend" in bio_ws["bottom_panels"]
        assert "suitability_distribution" in bio_ws["bottom_panels"]
        assert "connectivity" in bio_ws["bottom_panels"]
        assert "threats" in bio_ws["bottom_panels"]

    def test_json_roundtrip_serialization(self, tmp_path):
        mat = np.eye(9) * ha_to_m2(100.0)
        inp = LCLUCTransitionInput(matrix_m2=mat, from_year=2020, to_year=2022)
        orchestrator = LCLUCDownstreamBridge()
        result = orchestrator.process(inp)

        # Ensure valid JSON encoding
        serialized = json.dumps(result, ensure_ascii=False)
        parsed = json.loads(serialized)
        assert parsed["region"] == "South Sulawesi"
        assert parsed["carbon_workspace"]["workspace"] == "carbon"

    def test_export_payloads_to_disk(self, tmp_path):
        mat = np.eye(9) * ha_to_m2(200.0)
        mat[1, 4] = ha_to_m2(30.0)
        inp = LCLUCTransitionInput(matrix_m2=mat, from_year=2020, to_year=2024)
        orchestrator = LCLUCDownstreamBridge()

        files = orchestrator.export_payloads(inp, output_dir=tmp_path)
        assert files["carbon"].is_file()
        assert files["biodiversity"].is_file()
        assert files["integrated"].is_file()

        # Check content of files
        carbon_data = json.loads(files["carbon"].read_text(encoding="utf-8"))
        bio_data = json.loads(files["biodiversity"].read_text(encoding="utf-8"))
        integrated_data = json.loads(files["integrated"].read_text(encoding="utf-8"))

        assert carbon_data["workspace"] == "carbon"
        assert bio_data["workspace"] == "biodiversity"
        assert integrated_data["bridge_version"] == "1.0.0"


# ============================================================================
# 7. Common-Valid Governance (valid_common) Tests
# ============================================================================

class TestCommonValidGovernance:
    def test_from_aligned_rasters_full_clean(self):
        # 10x10 rasters (100 pixels, resolution 10m -> 1 ha total)
        t1 = np.full((10, 10), 1, dtype=np.uint8)  # All trees
        t2 = np.full((10, 10), 1, dtype=np.uint8)
        t2[0:3, :] = 4                              # 30 pixels converted to crops

        inp = LCLUCTransitionInput.from_aligned_rasters(
            t1_raster=t1,
            t2_raster=t2,
            from_year=2020,
            to_year=2025,
            region="South Sulawesi",
            resolution_m=10.0,
        )

        assert inp.num_classes == 9
        assert inp.total_pixels_observed == 100
        assert inp.valid_common_pixels == 100
        assert inp.cloud_masked_pixels == 0
        assert inp.valid_common_ratio == 1.0
        assert math.isclose(inp.total_area_ha, 1.0)
        assert math.isclose(inp.common_valid_ha, 1.0)
        assert math.isclose(inp.cloud_excluded_ha, 0.0)
        assert inp.spurious_cloud_deforest_pixels == 0

        # Check transition counts
        assert inp.pixels[1, 1] == 70  # trees -> trees
        assert inp.pixels[1, 4] == 30  # trees -> crops
        assert math.isclose(inp.matrix_ha[1, 4], 0.3)

    def test_from_aligned_rasters_filters_clouds_and_nodata(self):
        # 100x100 raster (10,000 pixels = 100 ha at 10m resolution)
        # T1: 100% Forest (class 1)
        t1 = np.full((100, 100), 1, dtype=np.uint8)

        # T2:
        # - 50 ha (5,000 pixels) remains Forest (1)
        # - 30 ha (3,000 pixels) real Deforestation to Cropland (4)
        # - 20 ha (2,000 pixels) occluded by clouds (nodata=255)
        t2 = np.full((100, 100), 1, dtype=np.uint8)
        t2[0:30, :] = 4    # 3,000 pixels -> Crops
        t2[30:50, :] = 255  # 2,000 pixels -> Cloud / NoData

        inp = LCLUCTransitionInput.from_aligned_rasters(
            t1_raster=t1,
            t2_raster=t2,
            nodata=255,
            from_year=2020,
            to_year=2025,
            region="South Sulawesi",
            resolution_m=10.0,
        )

        assert inp.total_pixels_observed == 10000
        assert inp.valid_common_pixels == 8000
        assert inp.cloud_masked_pixels == 2000
        assert math.isclose(inp.valid_common_ratio, 0.8)
        assert math.isclose(inp.common_valid_ha, 80.0)
        assert math.isclose(inp.cloud_excluded_ha, 20.0)

        # Certified deforestation is strictly 30 ha (not 50 ha!)
        assert inp.pixels[1, 4] == 3000
        assert math.isclose(inp.matrix_ha[1, 4], 30.0)
        assert inp.spurious_cloud_deforest_pixels == 2000
        assert math.isclose(inp.spurious_cloud_deforest_ha, 20.0)

    def test_spurious_emission_prevention_in_net_carbon_bridge(self):
        # T1 has 100 ha forest. T2 has 30 ha real deforestation to crops, 20 ha cloud gap.
        t1 = np.full((100, 100), 1, dtype=np.uint8)
        t2 = np.full((100, 100), 1, dtype=np.uint8)
        t2[0:30, :] = 4
        t2[30:50, :] = 255  # Cloud gap

        inp = LCLUCTransitionInput.from_aligned_rasters(
            t1_raster=t1,
            t2_raster=t2,
            nodata=255,
            from_year=2020,
            to_year=2025,
            resolution_m=10.0,
        )

        bridge = NetCarbonBridge(inp)
        res = bridge.calculate()

        act = res["activity_data"]
        # Certified deforestation must be 30.0 ha
        assert act["certified_deforestation_ha"] == 30.0
        assert act["deforestation_ha"] == 30.0
        assert act["cloud_excluded_ha"] == 20.0
        assert act["common_valid_ha"] == 80.0
        assert act["valid_common_ratio"] == 0.8

        # In an unmasked naive pipeline, the 20 ha cloud gap would spuriously emit:
        # 20 ha * 300 tC/ha * 44/12 = 22,000.0 tCO2e
        expected_prevented = 20.0 * 300.0 * (44.0 / 12.0)
        assert math.isclose(act["spurious_cloud_emissions_prevented_tCO2e"], expected_prevented, rel_tol=1e-3)

        # Real emissions from 30 ha forest -> crops (300 - 5 = 295 tC/ha):
        # 30 * 295 * (44 / 12) = 32,450.0 tCO2e
        expected_real_emissions = 30.0 * (300.0 - 5.0) * (44.0 / 12.0)
        gross_emissions = res["kpis"][0]["value"]
        assert math.isclose(gross_emissions, expected_real_emissions, rel_tol=1e-3)

        # Governance metadata present
        assert res["scientific_metadata"]["governance"]["cloud_gap_distortion_prevented"] is True
        assert math.isclose(res["scientific_metadata"]["governance"]["common_valid_ha"], 80.0)

    def test_morphological_erosion_neutralizes_cloud_holes(self):
        # 21x21 grid of forest (1)
        grid = np.full((21, 21), 1, dtype=np.uint8)

        # Case A: Without valid_mask, punch a 1-pixel hole at center (10, 10)
        grid_with_hole = grid.copy()
        grid_with_hole[10, 10] = 0  # Treated naively as non-forest

        # 1 step erosion (10m edge depth at 10m resolution)
        metrics_unmasked = compute_patch_metrics_2d(
            grid=grid_with_hole,
            habitat_values=[1],
            resolution_m=10.0,
            edge_depth_m=10.0,
        )

        # Case B: With valid_mask, the center pixel is recognized as unobserved cloud
        valid_mask = np.ones((21, 21), dtype=bool)
        valid_mask[10, 10] = False  # Cloud hole

        metrics_governed = compute_patch_metrics_2d(
            grid=grid,
            habitat_values=[1],
            resolution_m=10.0,
            edge_depth_m=10.0,
            valid_mask=valid_mask,
        )

        # Under naive unmasked erosion, the hole at (10, 10) erodes the 4 surrounding pixels!
        # Under governed erosion, those 4 surrounding pixels are preserved as core.
        assert metrics_governed["core_habitat_ha"] > metrics_unmasked["core_habitat_ha"]
        assert metrics_governed["fragmentation_index"] < metrics_unmasked["fragmentation_index"]
        assert metrics_governed["core_area_ratio"] > metrics_unmasked["core_area_ratio"]

    def test_biodiversity_bridge_with_common_valid_mask(self):
        # Create aligned rasters with cloud mask
        t1 = np.full((50, 50), 1, dtype=np.uint8)
        t2 = np.full((50, 50), 1, dtype=np.uint8)
        t2[0:10, :] = 4    # Deforestation to crops
        t2[40:50, :] = 255 # Cloud

        inp = LCLUCTransitionInput.from_aligned_rasters(
            t1_raster=t1,
            t2_raster=t2,
            nodata=255,
            resolution_m=10.0,
        )

        bridge = BiodiversityBridge(inp, raster_grid=t2)
        res = bridge.calculate()

        assert res["scientific_metadata"]["governance"]["filter_mode"] == "common_valid_mask"
        assert res["scientific_metadata"]["governance"]["morphological_cloud_hole_suppression"] is True
        assert res["habitat_metrics"]["common_valid_ha"] > 0.0
        assert res["habitat_metrics"]["cloud_excluded_ha"] > 0.0
        assert res["bottom_panels"]["connectivity"]["basis"] == "raster_connected_components_common_valid"

    def test_aligned_rasters_validation_errors(self):
        t1 = np.zeros((10, 10), dtype=np.uint8)
        t2 = np.zeros((12, 10), dtype=np.uint8)

        # Mismatched shapes
        with pytest.raises(ValueError, match="must match"):
            LCLUCTransitionInput.from_aligned_rasters(t1, t2)

        # 3D raster
        with pytest.raises(ValueError, match="2-dimensional"):
            LCLUCTransitionInput.from_aligned_rasters(np.zeros((5, 5, 2)), np.zeros((5, 5, 2)))

        # Mask dimension mismatch
        with pytest.raises(ValueError, match="t1_mask shape"):
            LCLUCTransitionInput.from_aligned_rasters(t1, t1, t1_mask=np.ones((8, 8)))

    def test_full_orchestrator_governance_block(self):
        t1 = np.full((50, 50), 1, dtype=np.uint8)
        t2 = np.full((50, 50), 1, dtype=np.uint8)
        t2[0:5, :] = 4   # 250 px crops
        t2[45:, :] = 255 # 250 px cloud

        inp = LCLUCTransitionInput.from_aligned_rasters(t1, t2, nodata=255)
        orchestrator = LCLUCDownstreamBridge()
        payload = orchestrator.process(inp, raster_grid=t2)

        assert "governance" in payload
        assert payload["governance"]["governance_mode"] == "common_valid_certified"
        assert payload["governance"]["valid_common_ratio"] == 0.9
        assert payload["governance"]["cloud_excluded_ha"] == 2.5
        assert payload["governance"]["spurious_cloud_emissions_prevented_tCO2e"] > 0.0
        assert "common_valid_ha" in payload["provenance"]
