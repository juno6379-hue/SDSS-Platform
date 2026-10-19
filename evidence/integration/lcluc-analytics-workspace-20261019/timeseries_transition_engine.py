"""
Advanced Time-Series Trajectory & Transition Matrix Analytics Engine.
Workspace: evidence/integration/lcluc-analytics-workspace-20261019/timeseries_transition_engine.py

Provides comprehensive analytical capabilities for multi-year LCLUC:
1. Multi-Year Trajectory Analysis:
   - Annual class area trajectories (hectares & percentages).
   - Trajectory trend classification: STEADY, MONOTONIC_INCREASE, MONOTONIC_DECREASE,
     FLUCTUATING_SEASONAL, SUDDEN_TRANSITION.
   - Annual Net Rate of Change and Compound Annual Growth Rate (CAGR).
2. Advanced Transition Matrix Decomposition (Pontius et al. 2004):
   - Persistence (diagonal), Gains, Losses, Net Change, and Total Swap.
   - Total Change = |Net Change| + Swap conservation identity.
   - Class vulnerability and persistence rankings.
   - Markov chain transition probability matrix (row-stochastic P_ij).
   - Sankey / Flow diagram data generator for visualization.
"""

from enum import Enum
import json
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
import numpy as np

# Standard 9 LCLUC classes aligned with backend/app/ml/raster.py
CLASS_NAMES = [
    "water",                # 0
    "trees",                # 1
    "grass",                # 2
    "flooded_vegetation",   # 3
    "crops",                # 4
    "shrub_and_scrub",      # 5
    "built",                # 6
    "bare",                 # 7
    "snow_and_ice",         # 8
]

CLASS_TO_IDX = {name: idx for idx, name in enumerate(CLASS_NAMES)}

# Area conversion constants
M2_PER_HA = 10000.0
HA_PER_M2 = 1.0 / M2_PER_HA


class TrendType(str, Enum):
    STEADY = "STEADY"
    MONOTONIC_INCREASE = "MONOTONIC_INCREASE"
    MONOTONIC_DECREASE = "MONOTONIC_DECREASE"
    FLUCTUATING_SEASONAL = "FLUCTUATING_SEASONAL"
    SUDDEN_TRANSITION = "SUDDEN_TRANSITION"


class TimeSeriesTrajectoryAnalyzer:
    """
    Analyzes multi-year land cover area trajectories, computes growth rates,
    and classifies trajectory trends.
    """

    def __init__(self, class_names: List[str] = CLASS_NAMES):
        self.class_names = class_names
        self.num_classes = len(class_names)

    @staticmethod
    def classify_trend(
        areas: List[float],
        relative_steady_threshold: float = 0.04,
        sudden_jump_threshold: float = 0.60,
    ) -> TrendType:
        """
        Classify trajectory trend of a 1D sequence of class areas across time.
        
        Args:
            areas: List or array of class areas over T >= 3 years.
            relative_steady_threshold: Max relative range (range/mean) to be considered STEADY.
            sudden_jump_threshold: Fraction of total range occurring in a single step for SUDDEN_TRANSITION.
            
        Returns:
            TrendType enum value.
        """
        arr = np.asarray(areas, dtype=np.float64)
        n = len(arr)
        if n < 2:
            return TrendType.STEADY

        min_val = float(np.min(arr))
        max_val = float(np.max(arr))
        total_range = max_val - min_val
        mean_val = float(np.mean(arr))

        # Check for steady / constant state
        if mean_val <= 1e-9:
            return TrendType.STEADY
        if (total_range / (mean_val + 1e-9)) <= relative_steady_threshold:
            return TrendType.STEADY

        deltas = np.diff(arr)

        # Check for monotonic increase / decrease
        # Allow tiny numerical tolerance
        tol = 1e-6 * max(1.0, mean_val)
        all_non_decreasing = np.all(deltas >= -tol)
        all_non_increasing = np.all(deltas <= tol)
        strict_change = total_range > tol

        if all_non_decreasing and strict_change:
            return TrendType.MONOTONIC_INCREASE
        if all_non_increasing and strict_change:
            return TrendType.MONOTONIC_DECREASE

        # Check for sudden transition (e.g. sharp drop or surge in 1 year that remains)
        max_single_step = float(np.max(np.abs(deltas)))
        if total_range > 0 and (max_single_step / total_range) >= sudden_jump_threshold:
            # Check if other steps are significantly smaller
            other_steps = np.abs(deltas)[np.abs(deltas) < (max_single_step - tol)]
            mean_other = float(np.mean(other_steps)) if len(other_steps) > 0 else 0.0
            if mean_other < 0.25 * max_single_step:
                return TrendType.SUDDEN_TRANSITION

        # Check for fluctuating / seasonal reversals
        # Count sign changes in deltas (ignoring near-zero steps)
        active_deltas = deltas[np.abs(deltas) > tol]
        if len(active_deltas) >= 2:
            sign_changes = np.count_nonzero(np.diff(np.sign(active_deltas)) != 0)
            if sign_changes >= 1:
                return TrendType.FLUCTUATING_SEASONAL

        # Fallback to dominant direction
        if arr[-1] > arr[0]:
            return TrendType.MONOTONIC_INCREASE
        elif arr[-1] < arr[0]:
            return TrendType.MONOTONIC_DECREASE
        return TrendType.STEADY

    @staticmethod
    def calculate_cagr(start_area: float, end_area: float, num_years: int) -> Optional[float]:
        """
        Calculate Compound Annual Growth Rate (CAGR):
        CAGR = (end_area / start_area) ** (1 / num_years) - 1.0
        """
        if num_years <= 0:
            return 0.0
        if start_area <= 1e-9:
            return None if end_area <= 1e-9 else float("inf")
        if end_area <= 1e-9:
            return -1.0
        return float((end_area / start_area) ** (1.0 / num_years) - 1.0)

    @staticmethod
    def calculate_puyravaud_rate(start_area: float, end_area: float, num_years: int) -> Optional[float]:
        """
        Calculate FAO/Puyravaud (2003) continuous rate of change (%/yr):
        r = (1 / num_years) * ln(end_area / start_area) * 100.0
        """
        if num_years <= 0:
            return 0.0
        if start_area <= 1e-9 or end_area <= 1e-9:
            return None
        return float((1.0 / num_years) * math.log(end_area / start_area) * 100.0)

    def analyze_trajectory_series(
        self,
        annual_area_dict: Dict[int, Dict[str, float]],
        years: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """
        Compute multi-year area trends, annual rates, and CAGRs for all classes.
        
        Args:
            annual_area_dict: Dict mapping year -> {class_name -> area_ha}
            years: Sorted list of years (defaults to sorted keys of annual_area_dict)
            
        Returns:
            Dict containing detailed trajectory metrics per class and overall landscape.
        """
        eval_years = sorted(years if years is not None else annual_area_dict.keys())
        if len(eval_years) < 2:
            raise ValueError(f"Need at least 2 observation years for trajectory analysis, got {eval_years}")

        t_span = eval_years[-1] - eval_years[0]
        y_start, y_end = eval_years[0], eval_years[-1]

        # Calculate annual landscape totals
        annual_totals_ha = {}
        for y in eval_years:
            annual_totals_ha[y] = sum(annual_area_dict[y].get(c, 0.0) for c in self.class_names)

        class_trajectories = {}

        for c_idx, c_name in enumerate(self.class_names):
            area_series = [annual_area_dict[y].get(c_name, 0.0) for y in eval_years]
            pct_series = [
                round(area_series[i] / annual_totals_ha[eval_years[i]] * 100.0, 4)
                if annual_totals_ha[eval_years[i]] > 0 else 0.0
                for i in range(len(eval_years))
            ]

            a_start = area_series[0]
            a_end = area_series[-1]
            net_change_ha = a_end - a_start
            net_rate_ha_per_yr = round(net_change_ha / t_span, 4) if t_span > 0 else 0.0
            pct_change_total = round((net_change_ha / a_start) * 100.0, 4) if a_start > 1e-9 else (100.0 if a_end > 0 else 0.0)

            cagr = self.calculate_cagr(a_start, a_end, t_span)
            puyravaud = self.calculate_puyravaud_rate(a_start, a_end, t_span)
            trend = self.classify_trend(area_series)

            class_trajectories[c_name] = {
                "class_idx": c_idx,
                "class_name": c_name,
                "area_series_ha": [round(a, 4) for a in area_series],
                "percentage_series": pct_series,
                "initial_area_ha": round(a_start, 4),
                "final_area_ha": round(a_end, 4),
                "net_change_ha": round(net_change_ha, 4),
                "pct_change_total": pct_change_total,
                "annual_net_rate_ha_yr": net_rate_ha_per_yr,
                "cagr": round(cagr, 6) if cagr is not None and math.isfinite(cagr) else None,
                "puyravaud_rate_pct_yr": round(puyravaud, 4) if puyravaud is not None else None,
                "trend_type": trend.value,
            }

        return {
            "time_horizon": {
                "years": eval_years,
                "start_year": y_start,
                "end_year": y_end,
                "span_years": t_span,
            },
            "annual_landscape_totals_ha": {y: round(tot, 4) for y, tot in annual_totals_ha.items()},
            "class_trajectories": class_trajectories,
        }


class AdvancedTransitionMatrixAnalytics:
    """
    Implements Pontius et al. (2004) matrix decomposition (Persistence, Gains, Losses, Net, Swap),
    class vulnerability/persistence rankings, and Markov chain transition probability matrices.
    """

    def __init__(self, class_names: List[str] = CLASS_NAMES):
        self.class_names = class_names
        self.num_classes = len(class_names)

    def decompose_matrix(
        self,
        matrix_ha: np.ndarray,
        round_decimals: int = 4,
    ) -> Dict[str, Any]:
        """
        Perform complete Pontius decomposition of a KxK transition matrix in hectares.
        
        Args:
            matrix_ha: 2D numpy array of shape (K, K) where matrix_ha[i, j] is area from class i to j.
            round_decimals: Decimals for output rounding.
            
        Returns:
            Dict containing detailed decomposition components and conservation checks.
        """
        mat = np.asarray(matrix_ha, dtype=np.float64)
        k = self.num_classes
        if mat.shape != (k, k):
            raise ValueError(f"Matrix shape {mat.shape} must match ({k}, {k})")

        total_area = float(np.sum(mat))
        row_sums = np.sum(mat, axis=1)  # Area at t1 (Initial)
        col_sums = np.sum(mat, axis=0)  # Area at t2 (Final)
        persistence = np.diag(mat)      # Unchanged area per class

        gains = col_sums - persistence   # Gross Gain: sum(N_ik for i != k)
        losses = row_sums - persistence  # Gross Loss: sum(N_kj for j != k)
        net_changes = gains - losses     # Net Change: Gain - Loss = Final - Initial
        swaps = 2.0 * np.minimum(gains, losses) # Total Swap: 2 * min(Gain, Loss)
        total_changes = gains + losses   # Total Change per class = |Net| + Swap

        # Check per-class identity: TotalChange_k = |NetChange_k| + Swap_k
        identity_per_class = np.isclose(total_changes, np.abs(net_changes) + swaps, atol=1e-5)

        # Overall Landscape Change Metrics
        total_persistence = float(np.sum(persistence))
        total_landscape_change = float(total_area - total_persistence)
        total_landscape_net = float(0.5 * np.sum(np.abs(net_changes)))
        total_landscape_swap = float(0.5 * np.sum(swaps))

        # Overall Landscape Identity: Total Change = Landscape Net + Landscape Swap
        identity_landscape = np.isclose(total_landscape_change, total_landscape_net + total_landscape_swap, atol=1e-5)
        net_sum_zero = np.isclose(float(np.sum(net_changes)), 0.0, atol=1e-5)

        # Vulnerability and Persistence Indicators
        # Persistence ratio: Persistence / Initial Area
        p_ratio = np.divide(persistence, row_sums, out=np.zeros_like(persistence), where=row_sums > 1e-9)
        # Vulnerability to loss: Loss / Initial Area = 1 - p_ratio
        v_loss = np.divide(losses, row_sums, out=np.zeros_like(losses), where=row_sums > 1e-9)
        # Expansion ratio: Gain / Initial Area
        e_gain = np.divide(gains, row_sums, out=np.zeros_like(gains), where=row_sums > 1e-9)

        # Build class summaries
        class_metrics = []
        for i, c_name in enumerate(self.class_names):
            class_metrics.append({
                "class_idx": i,
                "class_name": c_name,
                "initial_area_ha": round(float(row_sums[i]), round_decimals),
                "final_area_ha": round(float(col_sums[i]), round_decimals),
                "persistence_ha": round(float(persistence[i]), round_decimals),
                "gain_ha": round(float(gains[i]), round_decimals),
                "loss_ha": round(float(losses[i]), round_decimals),
                "net_change_ha": round(float(net_changes[i]), round_decimals),
                "swap_ha": round(float(swaps[i]), round_decimals),
                "total_change_ha": round(float(total_changes[i]), round_decimals),
                "persistence_ratio": round(float(p_ratio[i]), 6),
                "vulnerability_to_loss": round(float(v_loss[i]), 6),
                "expansion_ratio": round(float(e_gain[i]), 6),
                "change_type_dominance": "NET_DOMINATED" if np.abs(net_changes[i]) > swaps[i] else "SWAP_DOMINATED",
            })

        # Rankings with tie-breaking by area
        active_classes = [c for c in class_metrics if c["initial_area_ha"] > 1e-6]
        persistence_ranking = sorted(
            active_classes,
            key=lambda x: (x["persistence_ratio"], x["persistence_ha"]),
            reverse=True,
        )
        vulnerability_ranking = sorted(
            active_classes,
            key=lambda x: (x["vulnerability_to_loss"], x["loss_ha"]),
            reverse=True,
        )

        return {
            "landscape_summary": {
                "total_area_ha": round(total_area, round_decimals),
                "total_persistence_ha": round(total_persistence, round_decimals),
                "total_change_ha": round(total_landscape_change, round_decimals),
                "landscape_net_change_ha": round(total_landscape_net, round_decimals),
                "landscape_swap_ha": round(total_landscape_swap, round_decimals),
                "landscape_change_rate": round(total_landscape_change / total_area, 6) if total_area > 0 else 0.0,
                "net_vs_swap_ratio": round(total_landscape_net / (total_landscape_swap + 1e-9), 4),
            },
            "conservation_identities": {
                "all_class_identities_passed": bool(np.all(identity_per_class)),
                "landscape_identity_passed": bool(identity_landscape),
                "net_changes_sum_to_zero": bool(net_sum_zero),
                "mathematical_integrity_verified": bool(np.all(identity_per_class) and identity_landscape and net_sum_zero),
            },
            "class_decomposition": class_metrics,
            "rankings": {
                "most_persistent": [c["class_name"] for c in persistence_ranking],
                "most_vulnerable_to_loss": [c["class_name"] for c in vulnerability_ranking],
            },
        }

    def compute_markov_probabilities(
        self,
        matrix_ha: np.ndarray,
        round_decimals: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Compute row-stochastic Markov transition probability matrix P:
        P_ij = N_ij / RowSum_i
        Satisfies sum_j P_ij = 1.0 for all i.
        """
        mat = np.asarray(matrix_ha, dtype=np.float64)
        k = self.num_classes
        row_sums = np.sum(mat, axis=1)

        p_mat = np.zeros((k, k), dtype=np.float64)
        for i in range(k):
            if row_sums[i] > 1e-9:
                p_mat[i, :] = mat[i, :] / row_sums[i]
            else:
                # Absorbing identity state for empty class
                p_mat[i, i] = 1.0

        # Verify row stochasticity
        row_totals = np.sum(p_mat, axis=1)
        is_row_stochastic = bool(np.allclose(row_totals, 1.0, atol=1e-6))

        out_mat = np.round(p_mat, round_decimals).tolist() if round_decimals is not None else p_mat.tolist()
        out_sums = np.round(row_totals, round_decimals).tolist() if round_decimals is not None else row_totals.tolist()

        return {
            "transition_probability_matrix": out_mat,
            "row_stochasticity_verified": is_row_stochastic,
            "row_sums": out_sums,
            "class_names": self.class_names,
        }

    @staticmethod
    def project_markov_steps(
        initial_distribution: np.ndarray,
        transition_probability_matrix: np.ndarray,
        steps: int = 1,
    ) -> np.ndarray:
        """
        Project future land cover distribution: v(t + m*dt) = v(t) * (P ** m)
        """
        p = np.asarray(transition_probability_matrix, dtype=np.float64)
        v = np.asarray(initial_distribution, dtype=np.float64)
        p_m = np.linalg.matrix_power(p, steps)
        projected = np.dot(v, p_m)
        return projected

    def generate_sankey_data(
        self,
        matrix_ha: np.ndarray,
        from_year: int = 2020,
        to_year: int = 2025,
        min_flow_ha: float = 0.10,
        include_persistence: bool = True,
    ) -> Dict[str, Any]:
        """
        Generate Sankey / Flow diagram node and link data for UI charts.
        
        Args:
            matrix_ha: KxK transition matrix in hectares.
            from_year: Start year.
            to_year: End year.
            min_flow_ha: Minimum flow volume in ha to include in output.
            include_persistence: Whether to include diagonal flows (from class i to class i).
            
        Returns:
            Dict formatted with 'nodes' and 'links' for Sankey diagrams.
        """
        mat = np.asarray(matrix_ha, dtype=np.float64)
        total_area = float(np.sum(mat))
        nodes = []
        node_id_map = {}

        # Source nodes (from_year)
        for i, c_name in enumerate(self.class_names):
            nid = f"{from_year}_{c_name}"
            node_id_map[f"src_{i}"] = len(nodes)
            nodes.append({
                "id": nid,
                "label": f"{c_name.replace('_', ' ').title()} ({from_year})",
                "class_name": c_name,
                "class_idx": i,
                "year": from_year,
                "role": "source",
            })

        # Target nodes (to_year)
        for j, c_name in enumerate(self.class_names):
            nid = f"{to_year}_{c_name}"
            node_id_map[f"dst_{j}"] = len(nodes)
            nodes.append({
                "id": nid,
                "label": f"{c_name.replace('_', ' ').title()} ({to_year})",
                "class_name": c_name,
                "class_idx": j,
                "year": to_year,
                "role": "target",
            })

        links = []
        for i in range(self.num_classes):
            for j in range(self.num_classes):
                flow = float(mat[i, j])
                if flow < min_flow_ha:
                    continue
                if not include_persistence and i == j:
                    continue

                links.append({
                    "source": node_id_map[f"src_{i}"],
                    "target": node_id_map[f"dst_{j}"],
                    "source_id": f"{from_year}_{self.class_names[i]}",
                    "target_id": f"{to_year}_{self.class_names[j]}",
                    "from_class": self.class_names[i],
                    "to_class": self.class_names[j],
                    "is_persistence": (i == j),
                    "value_ha": round(flow, 4),
                    "percentage_of_total": round(flow / total_area * 100.0, 4) if total_area > 0 else 0.0,
                })

        # Sort links by flow value descending
        links.sort(key=lambda x: x["value_ha"], reverse=True)

        return {
            "metadata": {
                "from_year": from_year,
                "to_year": to_year,
                "total_landscape_area_ha": round(total_area, 4),
                "node_count": len(nodes),
                "link_count": len(links),
                "min_flow_threshold_ha": min_flow_ha,
                "includes_persistence": include_persistence,
            },
            "nodes": nodes,
            "links": links,
        }


class TimeSeriesTransitionAnalyticsEngine:
    """
    Unified Analytics Engine coordinating time-series trajectories,
    advanced transition matrix decomposition, and Sankey visualization data.
    """

    def __init__(self, class_names: List[str] = CLASS_NAMES):
        self.class_names = class_names
        self.trajectory_analyzer = TimeSeriesTrajectoryAnalyzer(class_names)
        self.matrix_analyzer = AdvancedTransitionMatrixAnalytics(class_names)

    def run_full_analytics(
        self,
        annual_area_dict: Dict[int, Dict[str, float]],
        transition_matrix_ha: np.ndarray,
        years: List[int],
        from_year: int,
        to_year: int,
        output_dir: Optional[Union[str, Path]] = None,
    ) -> Dict[str, Any]:
        """
        Execute comprehensive analytics and export summary report and JSON artifacts.
        """
        # 1. Trajectory analysis
        trajectory_res = self.trajectory_analyzer.analyze_trajectory_series(
            annual_area_dict=annual_area_dict,
            years=years,
        )

        # 2. Transition matrix decomposition
        decomposition_res = self.matrix_analyzer.decompose_matrix(transition_matrix_ha)

        # 3. Markov chain transition probabilities
        markov_res = self.matrix_analyzer.compute_markov_probabilities(transition_matrix_ha)

        # 4. Sankey flow diagram data
        sankey_res = self.matrix_analyzer.generate_sankey_data(
            matrix_ha=transition_matrix_ha,
            from_year=from_year,
            to_year=to_year,
            include_persistence=True,
        )

        report = {
            "schema_version": 1,
            "engine": "TimeSeriesTransitionAnalyticsEngine",
            "status": "ANALYTICS_COMPLETE",
            "scope": {
                "evaluated_years": years,
                "transition_pair": {"from_year": from_year, "to_year": to_year},
                "num_classes": len(self.class_names),
                "class_names": self.class_names,
            },
            "trajectory_analysis": trajectory_res,
            "transition_matrix_decomposition": decomposition_res,
            "markov_transition_model": markov_res,
            "sankey_flows": sankey_res,
        }

        if output_dir is not None:
            out_path = Path(output_dir)
            out_path.mkdir(parents=True, exist_ok=True)
            (out_path / "analytics_report.json").write_text(
                json.dumps(report, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            (out_path / "sankey_data.json").write_text(
                json.dumps(sankey_res, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            (out_path / "markov_probabilities.json").write_text(
                json.dumps(markov_res, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )

        return report
