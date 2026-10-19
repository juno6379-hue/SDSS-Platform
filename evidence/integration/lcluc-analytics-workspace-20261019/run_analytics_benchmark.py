"""
Benchmark & Verification Runner for Time-Series Trajectory & Transition Matrix Analytics Engine.
Workspace: evidence/integration/lcluc-analytics-workspace-20261019/run_analytics_benchmark.py

Executes:
1. 6-province (Banten, East Java, Gorontalo, South Sulawesi, Southeast Sulawesi, West Java)
   6-year (2020-2025) multi-temporal trajectory analytics.
2. Pontius (2004) matrix decomposition across baseline (2020-2025) and adjacent (2024-2025) pairs.
3. Rigorous conservation identity verifications:
   - TotalChange_k = |NetChange_k| + Swap_k
   - Landscape Total Change = Landscape Net + Landscape Swap
   - Sum of Net Changes = 0
   - Markov row stochasticity (sum_j P_ij = 1.0)
4. Sankey diagram flow generation and flow volume conservation.
5. Exports structured JSON reports and audit logs.
"""

import copy
import json
import math
from pathlib import Path
import sys
import time
from typing import Dict, Any, List, Tuple, Optional
import numpy as np

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

WORKSPACE_DIR = Path(__file__).resolve().parent
if str(WORKSPACE_DIR) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_DIR))

from timeseries_transition_engine import (
    TimeSeriesTransitionAnalyticsEngine,
    TimeSeriesTrajectoryAnalyzer,
    AdvancedTransitionMatrixAnalytics,
    TrendType,
    CLASS_NAMES,
    CLASS_TO_IDX,
    HA_PER_M2,
)

PROVINCES = [
    "banten",
    "east_java",
    "gorontalo",
    "south_sulawesi",
    "southeast_sulawesi",
    "west_java",
]

YEARS = [2020, 2021, 2022, 2023, 2024, 2025]


def simulate_province_multiyear_data(
    province: str,
    years: List[int],
    total_landscape_ha: float = 100000.0,
    seed: Optional[int] = None,
) -> Tuple[Dict[int, Dict[str, float]], np.ndarray]:
    """
    Generate realistic 6-year multi-temporal land cover trajectory and 2020-2025 transition matrix.
    Reflects tropical Indonesian land use dynamics:
    - Gradual deforestation and expansion of oil palm / crops and settlements.
    - Water and flooded vegetation seasonal stability.
    """
    rng = np.random.RandomState(seed if seed is not None else abs(hash(province)) % (2**31))

    # Base year (2020) distribution
    base_shares = {
        "water": 0.05,
        "trees": 0.45,
        "grass": 0.08,
        "flooded_vegetation": 0.04,
        "crops": 0.22,
        "shrub_and_scrub": 0.06,
        "built": 0.07,
        "bare": 0.03,
        "snow_and_ice": 0.00,
    }

    annual_data = {}
    k = len(CLASS_NAMES)

    # Simulate trajectory year by year
    current_areas = {c: base_shares[c] * total_landscape_ha for c in CLASS_NAMES}
    annual_data[years[0]] = copy.deepcopy(current_areas)

    for y in years[1:]:
        # Annual deforestation rate: 0.8% ~ 1.5%
        deforest_rate = rng.uniform(0.008, 0.015)
        forest_loss = current_areas["trees"] * deforest_rate
        current_areas["trees"] -= forest_loss

        # 60% of lost forest converted to crops/plantations, 30% to built, 10% to bare/shrub
        crop_gain = forest_loss * 0.60
        built_gain = forest_loss * 0.30
        bare_gain = forest_loss * 0.10

        # Urban expansion also absorbs some crop/grass land
        crop_to_urban = current_areas["crops"] * 0.005
        current_areas["crops"] += (crop_gain - crop_to_urban)
        current_areas["built"] += (built_gain + crop_to_urban)
        current_areas["bare"] += bare_gain

        # Fluctuations in grass/shrub/bare
        grass_change = rng.normal(0, current_areas["grass"] * 0.02)
        current_areas["grass"] = max(100.0, current_areas["grass"] + grass_change)
        current_areas["bare"] = max(100.0, current_areas["bare"] - grass_change)

        annual_data[y] = copy.deepcopy(current_areas)

    # Build 2020 -> 2025 Transition Matrix (in ha)
    mat = np.zeros((k, k), dtype=np.float64)
    start_areas = annual_data[years[0]]
    end_areas = annual_data[years[-1]]

    # 1. Diagonal persistence: min of start and end, minus transition pool
    for i, c in enumerate(CLASS_NAMES):
        mat[i, i] = min(start_areas[c], end_areas[c])

    # 2. Deforestation off-diagonals: Trees (1) to Crops (4) and Built (6)
    trees_loss_total = start_areas["trees"] - end_areas["trees"]
    mat[1, 1] = end_areas["trees"]
    mat[1, 4] = trees_loss_total * 0.65  # Trees -> Crops
    mat[1, 6] = trees_loss_total * 0.30  # Trees -> Built
    mat[1, 7] = trees_loss_total * 0.05  # Trees -> Bare

    # 3. Crops to Built
    crops_to_built = 800.0
    mat[4, 6] += crops_to_built
    mat[4, 4] = max(0.0, start_areas["crops"] - crops_to_built)

    # 4. Grass to Bare & Bare to Grass swap
    swap_vol = 150.0
    mat[2, 7] = swap_vol
    mat[7, 2] = swap_vol
    mat[2, 2] = max(0.0, start_areas["grass"] - swap_vol)
    mat[7, 7] = max(0.0, start_areas["bare"] - swap_vol)

    return annual_data, mat


def run_analytics_benchmark() -> Dict[str, Any]:
    start_time = time.time()
    artifacts_dir = WORKSPACE_DIR / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    log_lines = []
    def log(msg: str):
        t_str = time.strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{t_str}] {msg}"
        log_lines.append(line)
        print(line)

    log("=" * 80)
    log("Starting Time-Series Trajectory & Transition Matrix Analytics Benchmark")
    log(f"Workspace Directory: {WORKSPACE_DIR}")
    log(f"Provinces: {len(PROVINCES)} | Time Horizon: 2020-2025 (6 years)")
    log("=" * 80)

    engine = TimeSeriesTransitionAnalyticsEngine()
    province_results = []
    all_identities_passed = True
    all_stochastic_passed = True

    for prov in PROVINCES:
        prov_start = time.time()
        log(f"\nProcessing Province: {prov.upper()}...")
        prov_dir = artifacts_dir / prov
        prov_dir.mkdir(parents=True, exist_ok=True)

        annual_data, mat_2020_2025 = simulate_province_multiyear_data(
            province=prov,
            years=YEARS,
            total_landscape_ha=100000.0,
            seed=abs(hash(prov)) % (2**31),
        )

        # Run complete analytics engine
        report = engine.run_full_analytics(
            annual_area_dict=annual_data,
            transition_matrix_ha=mat_2020_2025,
            years=YEARS,
            from_year=2020,
            to_year=2025,
            output_dir=prov_dir,
        )

        traj = report["trajectory_analysis"]
        decomp = report["transition_matrix_decomposition"]
        markov = report["markov_transition_model"]
        sankey = report["sankey_flows"]

        identities = decomp["conservation_identities"]
        p_passed = identities["mathematical_integrity_verified"]
        stoch_passed = markov["row_stochasticity_verified"]

        all_identities_passed &= p_passed
        all_stochastic_passed &= stoch_passed

        # Key metrics for summary
        trees_traj = traj["class_trajectories"]["trees"]
        built_traj = traj["class_trajectories"]["built"]
        land_summary = decomp["landscape_summary"]

        prov_elapsed = time.time() - prov_start
        log(f"  > Trees Trend: {trees_traj['trend_type']} | Net Change: {trees_traj['net_change_ha']} ha | CAGR: {trees_traj['cagr']}")
        log(f"  > Built Trend: {built_traj['trend_type']} | Net Change: +{built_traj['net_change_ha']} ha | CAGR: {built_traj['cagr']}")
        log(f"  > Landscape Total Area: {land_summary['total_area_ha']} ha | Total Change: {land_summary['total_change_ha']} ha")
        log(f"  > Landscape Net Change: {land_summary['landscape_net_change_ha']} ha | Landscape Swap: {land_summary['landscape_swap_ha']} ha")
        log(f"  > Pontius Identity (Total = Net + Swap): {'VERIFIED' if p_passed else 'FAILED'}")
        log(f"  > Markov Row Stochasticity (sum_j P_ij = 1.0): {'VERIFIED' if stoch_passed else 'FAILED'}")
        log(f"  > Sankey Links Generated: {sankey['metadata']['link_count']} flows")
        log(f"  > Province Processed in {round(prov_elapsed, 3)}s")

        province_results.append({
            "province": prov,
            "trees_trend": trees_traj["trend_type"],
            "built_trend": built_traj["trend_type"],
            "trees_cagr": trees_traj["cagr"],
            "built_cagr": built_traj["cagr"],
            "total_landscape_ha": land_summary["total_area_ha"],
            "total_change_ha": land_summary["total_change_ha"],
            "landscape_net_ha": land_summary["landscape_net_change_ha"],
            "landscape_swap_ha": land_summary["landscape_swap_ha"],
            "pontius_identities_verified": p_passed,
            "markov_stochasticity_verified": stoch_passed,
            "sankey_links_count": sankey["metadata"]["link_count"],
            "elapsed_seconds": round(prov_elapsed, 3),
        })

    total_elapsed = time.time() - start_time

    log("\n" + "=" * 80)
    log("OVERALL ANALYTICS BENCHMARK SUMMARY")
    log("=" * 80)
    log(f"Total Provinces Evaluated: {len(PROVINCES)}")
    log(f"Pontius (2004) Conservation Identities: {'100% PASSED' if all_identities_passed else 'FAILED'}")
    log(f"Markov Row Stochasticity (sum_j P_ij = 1.0): {'100% PASSED' if all_stochastic_passed else 'FAILED'}")
    log(f"Total Execution Time: {round(total_elapsed, 2)}s")
    log("=" * 80)

    summary = {
        "schema_version": 1,
        "title": "LCLUC Time-Series Trajectory & Transition Matrix Analytics Benchmark",
        "status": "ANALYTICS_BENCHMARK_COMPLETE",
        "scope": {
            "provinces": PROVINCES,
            "province_count": len(PROVINCES),
            "years": YEARS,
            "year_count": len(YEARS),
            "baseline_period": {"start_year": 2020, "end_year": 2025},
        },
        "overall_verification": {
            "pontius_identities_pass_rate": 1.0 if all_identities_passed else 0.0,
            "markov_stochasticity_pass_rate": 1.0 if all_stochastic_passed else 0.0,
            "total_execution_seconds": round(total_elapsed, 3),
        },
        "province_benchmark_details": province_results,
    }

    (WORKSPACE_DIR / "analytics_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    (WORKSPACE_DIR / "analytics_verification.log").write_text(
        "\n".join(log_lines),
        encoding="utf-8"
    )

    return summary


if __name__ == "__main__":
    run_analytics_benchmark()
