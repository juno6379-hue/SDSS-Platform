"""Regional Comparison and Benchmarking Engine for LCLUC.

Ingests transition matrices across multiple Indonesian provinces, calculates comparative
rates (deforestation, urbanization, retention, agricultural conversion, transition pressure),
and produces multi-province benchmarking tables, comparative bar charts, and 5-axis radar charts.

Strictly isolated module developed for SDSS Regional Comparison & Benchmarking.
"""

from __future__ import annotations

import csv
import json
import math
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np

# Standard 9-Class Taxonomy
DEFAULT_CLASS_NAMES: Tuple[str, ...] = (
    "water",               # 0
    "trees",               # 1
    "grass",               # 2
    "flooded_vegetation",  # 3
    "crops",               # 4
    "shrub_and_scrub",     # 5
    "built",               # 6
    "bare",                # 7
    "snow_and_ice",        # 8
)

M2_PER_HA: float = 10000.0


def m2_to_ha(m2: float) -> float:
    """Converts square meters to hectares."""
    if m2 < 0:
        raise ValueError(f"Area in m2 must be non-negative, got {m2}")
    return float(m2) / M2_PER_HA


def ha_to_m2(ha: float) -> float:
    """Converts hectares to square meters."""
    if ha < 0:
        raise ValueError(f"Area in ha must be non-negative, got {ha}")
    return float(ha) * M2_PER_HA


class RiskStatus(str, Enum):
    HIGH_RISK = "HIGH_RISK"
    MODERATE = "MODERATE"
    STABLE = "STABLE"


@dataclass
class ProvinceRecord:
    """Input transition and land cover record for a single province."""
    province_id: str
    name_ko: str
    name_en: str
    from_year: int
    to_year: int
    matrix_m2: np.ndarray
    class_names: List[str] = field(default_factory=lambda: list(DEFAULT_CLASS_NAMES))
    total_area_m2: float = 0.0

    def __post_init__(self):
        self.matrix_m2 = np.asarray(self.matrix_m2, dtype=np.float64)
        if self.matrix_m2.ndim != 2 or self.matrix_m2.shape[0] != self.matrix_m2.shape[1]:
            raise ValueError(f"matrix_m2 must be a square 2D matrix, got shape {self.matrix_m2.shape}")
        if np.any(self.matrix_m2 < 0):
            raise ValueError("matrix_m2 area values must be non-negative")
        if self.to_year <= self.from_year:
            raise ValueError(f"to_year ({self.to_year}) must be greater than from_year ({self.from_year})")
        if self.total_area_m2 <= 0.0:
            self.total_area_m2 = float(self.matrix_m2.sum())

    @property
    def elapsed_years(self) -> float:
        return float(self.to_year - self.from_year)

    @property
    def matrix_ha(self) -> np.ndarray:
        return self.matrix_m2 / M2_PER_HA

    @property
    def total_area_ha(self) -> float:
        return self.total_area_m2 / M2_PER_HA

    def find_class_index(self, pattern: str) -> Optional[int]:
        pat = pattern.lower().strip()
        for idx, name in enumerate(self.class_names):
            if pat in name.lower():
                return idx
        return None


@dataclass
class RegionalMetrics:
    """Calculated comparative metrics for a single province."""
    province_id: str
    name_ko: str
    name_en: str
    period: str
    elapsed_years: float
    total_area_ha: float
    # Deforestation metrics
    initial_forest_ha: float
    final_forest_ha: float
    gross_forest_loss_ha: float
    net_forest_loss_ha: float
    annual_deforestation_ha_yr: float
    annual_deforestation_rate_pct: float
    # Urbanization metrics
    initial_built_ha: float
    final_built_ha: float
    gross_urban_gain_ha: float
    annual_urban_expansion_ha_yr: float
    urban_expansion_growth_pct: float
    # Retention & Agricultural metrics
    forest_retention_rate_pct: float  # preserved / initial forest
    agricultural_conversion_ha: float  # forest/grass/shrub -> crops
    agricultural_conversion_ratio_pct: float  # ag conversion / total change
    # Landscape & Vulnerability
    landscape_stability_index: float  # unchanged area / total area (0-100)
    carbon_risk_score: float  # 0-100 based on forest & peat loss
    rtpi_score: float  # Regional Transition Pressure Index (0-100)
    risk_status: RiskStatus
    # Ranking attributes (populated during multi-province benchmarking)
    rank: int = 0
    percentile: float = 0.0


class RegionalComparisonEngine:
    """Multi-province comparison and benchmarking engine for LCLUC."""

    def __init__(self):
        self.provinces: Dict[str, ProvinceRecord] = {}

    def add_province(
        self,
        province_id: str,
        name_ko: str,
        name_en: str,
        matrix_m2: np.ndarray,
        from_year: int = 2020,
        to_year: int = 2025,
        class_names: Optional[Sequence[str]] = None,
    ) -> None:
        """Adds a province transition record."""
        record = ProvinceRecord(
            province_id=province_id,
            name_ko=name_ko,
            name_en=name_en,
            from_year=from_year,
            to_year=to_year,
            matrix_m2=matrix_m2,
            class_names=list(class_names) if class_names else list(DEFAULT_CLASS_NAMES),
        )
        self.provinces[province_id] = record

    def compute_province_metrics(self, record: ProvinceRecord) -> RegionalMetrics:
        """Computes comprehensive comparative metrics for a single province with strict guards."""
        mat_ha = record.matrix_ha
        n = mat_ha.shape[0]
        elapsed = max(1.0, record.elapsed_years)
        total_ha = max(1e-6, record.total_area_ha)

        forest_idx = record.find_class_index("tree") or (1 if n > 1 else 0)
        crop_idx = record.find_class_index("crop") or (4 if n > 4 else 0)
        built_idx = record.find_class_index("built") or (6 if n > 6 else 0)
        grass_idx = record.find_class_index("grass") or (2 if n > 2 else 0)
        shrub_idx = record.find_class_index("shrub") or (5 if n > 5 else 0)
        wetland_idx = record.find_class_index("flooded") or (3 if n > 3 else 0)

        # 1. Forest metrics
        initial_forest = float(mat_ha[forest_idx, :].sum())
        final_forest = float(mat_ha[:, forest_idx].sum())
        preserved_forest = float(mat_ha[forest_idx, forest_idx])

        # Gross forest loss: forest to non-forest
        gross_forest_loss = 0.0
        for j in range(n):
            if j != forest_idx:
                gross_forest_loss += float(mat_ha[forest_idx, j])

        net_forest_loss = max(0.0, initial_forest - final_forest)
        annual_deforest_ha = gross_forest_loss / elapsed

        # Annual Deforestation Rate (%/yr) with zero-division guard
        if initial_forest > 0.0:
            annual_deforest_rate_pct = (gross_forest_loss / initial_forest) * (100.0 / elapsed)
            forest_retention_pct = (preserved_forest / initial_forest) * 100.0
        else:
            annual_deforest_rate_pct = 0.0
            forest_retention_pct = 100.0

        forest_retention_pct = max(0.0, min(100.0, forest_retention_pct))

        # 2. Urbanization metrics
        initial_built = float(mat_ha[built_idx, :].sum())
        final_built = float(mat_ha[:, built_idx].sum())

        gross_urban_gain = 0.0
        for i in range(n):
            if i != built_idx:
                gross_urban_gain += float(mat_ha[i, built_idx])

        annual_urban_expansion_ha = gross_urban_gain / elapsed

        # Urban expansion growth (% over period) with zero-division guard
        if initial_built > 0.0:
            urban_growth_pct = (gross_urban_gain / initial_built) * 100.0
        else:
            urban_growth_pct = 0.0

        # 3. Agricultural Conversion metrics (forest, grass, shrub -> crops)
        agri_conv_ha = 0.0
        for src_idx in (forest_idx, grass_idx, shrub_idx):
            if src_idx != crop_idx:
                agri_conv_ha += float(mat_ha[src_idx, crop_idx])

        # Total changed area
        total_changed_ha = float(mat_ha.sum() - np.trace(mat_ha))
        if total_changed_ha > 0.0:
            agri_conv_ratio_pct = (agri_conv_ha / total_changed_ha) * 100.0
        else:
            agri_conv_ratio_pct = 0.0

        # 4. Landscape Stability Index (unchanged area / total area, 0-100)
        unchanged_ha = float(np.trace(mat_ha))
        stability_index = (unchanged_ha / total_ha) * 100.0
        stability_index = max(0.0, min(100.0, stability_index))

        # 5. Carbon Risk Score (0-100)
        # Based on deforestation rate, wetland loss, and agricultural conversion
        wetland_loss = float(mat_ha[wetland_idx, :].sum() - mat_ha[wetland_idx, wetland_idx])
        c_risk = (
            min(50.0, annual_deforest_rate_pct * 15.0)
            + min(30.0, (wetland_loss / total_ha) * 200.0)
            + min(20.0, (agri_conv_ha / total_ha) * 100.0)
        )
        carbon_risk_score = round(max(0.0, min(100.0, c_risk)), 2)

        # 6. Regional Transition Pressure Index (RTPI, 0.0 to 100.0)
        # Weights: Deforestation (0.35), Urbanization (0.20), Agri Expansion (0.25), Carbon Risk (0.20)
        norm_deforest = min(100.0, annual_deforest_rate_pct * 25.0)
        norm_urban = min(100.0, (annual_urban_expansion_ha / max(100.0, total_ha * 0.01)) * 50.0)
        norm_agri = min(100.0, (agri_conv_ha / max(100.0, total_ha * 0.05)) * 100.0)

        rtpi = (
            0.35 * norm_deforest
            + 0.20 * norm_urban
            + 0.25 * norm_agri
            + 0.20 * carbon_risk_score
        )
        rtpi = round(max(0.0, min(100.0, rtpi)), 2)

        # Status Flag
        if rtpi >= 50.0 or annual_deforest_rate_pct >= 0.8 or annual_deforest_ha >= 15000.0:
            status = RiskStatus.HIGH_RISK
        elif rtpi >= 25.0 or annual_deforest_rate_pct >= 0.4 or annual_deforest_ha >= 4000.0:
            status = RiskStatus.MODERATE
        else:
            status = RiskStatus.STABLE

        return RegionalMetrics(
            province_id=record.province_id,
            name_ko=record.name_ko,
            name_en=record.name_en,
            period=f"{record.from_year}–{record.to_year}",
            elapsed_years=elapsed,
            total_area_ha=round(total_ha, 2),
            initial_forest_ha=round(initial_forest, 2),
            final_forest_ha=round(final_forest, 2),
            gross_forest_loss_ha=round(gross_forest_loss, 2),
            net_forest_loss_ha=round(net_forest_loss, 2),
            annual_deforestation_ha_yr=round(annual_deforest_ha, 2),
            annual_deforestation_rate_pct=round(annual_deforest_rate_pct, 3),
            initial_built_ha=round(initial_built, 2),
            final_built_ha=round(final_built, 2),
            gross_urban_gain_ha=round(gross_urban_gain, 2),
            annual_urban_expansion_ha_yr=round(annual_urban_expansion_ha, 2),
            urban_expansion_growth_pct=round(urban_growth_pct, 2),
            forest_retention_rate_pct=round(forest_retention_pct, 2),
            agricultural_conversion_ha=round(agri_conv_ha, 2),
            agricultural_conversion_ratio_pct=round(agri_conv_ratio_pct, 2),
            landscape_stability_index=round(stability_index, 2),
            carbon_risk_score=carbon_risk_score,
            rtpi_score=rtpi,
            risk_status=status,
        )

    def compute_all(self) -> Dict[str, RegionalMetrics]:
        """Computes metrics and rankings for all registered provinces."""
        if not self.provinces:
            return {}

        results: Dict[str, RegionalMetrics] = {}
        for pid, record in self.provinces.items():
            results[pid] = self.compute_province_metrics(record)

        # Sort by RTPI descending for ranking (highest pressure = rank 1)
        sorted_items = sorted(
            results.values(),
            key=lambda m: (m.rtpi_score, m.annual_deforestation_rate_pct),
            reverse=True,
        )

        n = len(sorted_items)
        for rank_idx, metric in enumerate(sorted_items, start=1):
            metric.rank = rank_idx
            # Percentile: percentage of provinces with lower score
            metric.percentile = round(((n - rank_idx) / max(1, n - 1)) * 100.0, 1) if n > 1 else 100.0

        return results

    def generate_benchmarking_table(self) -> Dict[str, Any]:
        """Generates the standardized multi-province benchmarking table.

        Matches ModelAnalysisWorkspace.tsx layout:
        ['순위', '지역 (Province)', '산림 벌채율 (%/년)', '도시 확장 (ha/년)', '산림 보존율 (%)', '농업 전환 (ha)', '전이 압력 (RTPI)', '위험 등급']
        """
        metrics_dict = self.compute_all()
        sorted_metrics = sorted(metrics_dict.values(), key=lambda m: m.rank)

        columns = [
            "순위",
            "지역 (Province)",
            "산림 벌채율 (%/년)",
            "도시 확장 (ha/년)",
            "산림 보존율 (%)",
            "농업 전환 (ha)",
            "전이 압력 (RTPI)",
            "위험 등급",
        ]

        rows = []
        for m in sorted_metrics:
            rows.append([
                str(m.rank),
                f"{m.name_ko} ({m.name_en})",
                f"{m.annual_deforestation_rate_pct:.2f}%",
                f"{m.annual_urban_expansion_ha_yr:,.1f}",
                f"{m.forest_retention_rate_pct:.1f}%",
                f"{m.agricultural_conversion_ha:,.1f}",
                f"{m.rtpi_score:.1f}",
                m.risk_status.value,
            ])

        return {
            "title": "인도네시아 주별 LCLUC 비교 벤치마킹",
            "columns": columns,
            "rows": rows,
            "total_provinces": len(rows),
            "high_risk_count": sum(1 for m in sorted_metrics if m.risk_status == RiskStatus.HIGH_RISK),
            "moderate_count": sum(1 for m in sorted_metrics if m.risk_status == RiskStatus.MODERATE),
            "stable_count": sum(1 for m in sorted_metrics if m.risk_status == RiskStatus.STABLE),
        }

    def generate_bar_chart_data(self) -> Dict[str, Any]:
        """Generates comparative bar chart dataset comparing Deforestation vs Urbanization."""
        metrics_dict = self.compute_all()
        sorted_metrics = sorted(metrics_dict.values(), key=lambda m: m.rank)

        categories = [f"{m.name_ko}" for m in sorted_metrics]
        deforestation_rates = [m.annual_deforestation_rate_pct for m in sorted_metrics]
        deforestation_ha = [m.annual_deforestation_ha_yr for m in sorted_metrics]
        urban_growth_ha = [m.annual_urban_expansion_ha_yr for m in sorted_metrics]
        rtpi_scores = [m.rtpi_score for m in sorted_metrics]

        return {
            "chart_type": "comparative_bar",
            "title": "주별 산림 벌채율 대 도시 확장 속도 비교",
            "categories": categories,
            "series": [
                {
                    "name": "연간 산림 벌채율 (%/년)",
                    "unit": "%/년",
                    "color": "#dc2626",
                    "data": deforestation_rates,
                },
                {
                    "name": "연간 도시 확장 (ha/년)",
                    "unit": "ha/년",
                    "color": "#f97316",
                    "data": urban_growth_ha,
                },
                {
                    "name": "전이 압력 지수 (RTPI)",
                    "unit": "점수 (0–100)",
                    "color": "#7c3aed",
                    "data": rtpi_scores,
                },
            ],
        }

    def generate_radar_chart_data(self) -> Dict[str, Any]:
        """Generates 5-axis multi-dimensional radar chart data across provinces.

        5 Axes:
        1. Forest Retention (산림 보존율, 0-100)
        2. Urban Growth Velocity (도시 성장도, 0-100)
        3. Landscape Stability (경관 안정성, 0-100)
        4. Agri Expansion Pressure (농업 확장 압력, 0-100)
        5. Carbon Risk (탄소 배출 위험도, 0-100)
        """
        metrics_dict = self.compute_all()
        axes = [
            "산림 보존율 (Retention)",
            "도시 성장도 (Urban Growth)",
            "경관 안정성 (Stability)",
            "농업 확장 압력 (Agri Pressure)",
            "탄소 위험도 (Carbon Risk)",
        ]

        provinces_radar = []
        for m in sorted(metrics_dict.values(), key=lambda x: x.rank):
            # Normalize urban growth to 0-100 scale based on growth %
            urban_growth_score = min(100.0, m.urban_expansion_growth_pct * 2.0)
            # Normalize agri pressure based on conversion ratio
            agri_pressure_score = min(100.0, m.agricultural_conversion_ratio_pct * 1.5)

            values = [
                round(m.forest_retention_rate_pct, 1),
                round(urban_growth_score, 1),
                round(m.landscape_stability_index, 1),
                round(agri_pressure_score, 1),
                round(m.carbon_risk_score, 1),
            ]

            provinces_radar.append({
                "province_id": m.province_id,
                "name": f"{m.name_ko} ({m.name_en})",
                "values": values,
                "risk_status": m.risk_status.value,
            })

        return {
            "chart_type": "radar_5axis",
            "title": "지역별 LCLUC 다차원 전이 프로파일",
            "axes": axes,
            "provinces": provinces_radar,
        }

    def generate_full_comparison_payload(self) -> Dict[str, Any]:
        """Generates the unified JSON payload for frontend Regional Comparison tab."""
        metrics_dict = self.compute_all()
        table_data = self.generate_benchmarking_table()
        bar_data = self.generate_bar_chart_data()
        radar_data = self.generate_radar_chart_data()

        metrics_list = [asdict(m) for m in sorted(metrics_dict.values(), key=lambda x: x.rank)]
        for item in metrics_list:
            item["risk_status"] = item["risk_status"].value

        return {
            "workspace": "lcluc_regional_comparison",
            "timestamp": "2026-10-19T05:00:00Z",
            "summary_kpis": [
                {
                    "label": "분석 대상 주",
                    "value": len(metrics_dict),
                    "unit": "개 주",
                },
                {
                    "label": "고위험 지역 (High Risk)",
                    "value": table_data["high_risk_count"],
                    "unit": "개 주",
                },
                {
                    "label": "평균 산림 보존율",
                    "value": round(float(np.mean([m.forest_retention_rate_pct for m in metrics_dict.values()])), 1) if metrics_dict else 0.0,
                    "unit": "%",
                },
                {
                    "label": "최고 전이 압력 지역",
                    "value": table_data["rows"][0][1] if table_data["rows"] else "N/A",
                    "unit": "1위",
                },
            ],
            "benchmarking_table": table_data,
            "charts": {
                "bar": bar_data,
                "radar": radar_data,
            },
            "provinces_metrics": metrics_list,
        }

    def export_payloads(self, output_dir: Union[str, Path]) -> Dict[str, Path]:
        """Exports JSON and CSV artifacts to disk."""
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        full_payload = self.generate_full_comparison_payload()
        json_file = out / "regional_comparison_payload.json"
        json_file.write_text(json.dumps(full_payload, ensure_ascii=False, indent=2), encoding="utf-8")

        # Export benchmarking CSV
        csv_file = out / "regional_benchmarking_table.csv"
        table = full_payload["benchmarking_table"]
        with csv_file.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(table["columns"])
            for row in table["rows"]:
                writer.writerow(row)

        return {
            "payload_json": json_file,
            "benchmarking_csv": csv_file,
        }

    def load_canonical_indonesia_benchmarks(
        self,
        from_year: int = 2020,
        to_year: int = 2025,
    ) -> None:
        """Loads canonical baseline benchmark profiles for 10 key Indonesian provinces.

        Provinces included:
        1. Banten
        2. West Java (Jawa Barat)
        3. East Java (Jawa Timur)
        4. Central Java (Jawa Tengah)
        5. South Sulawesi (Sulawesi Selatan)
        6. Southeast Sulawesi (Sulawesi Tenggara)
        7. Gorontalo
        8. Aceh
        9. North Sumatra (Sumatera Utara)
        10. Riau
        """
        # Baseline configurations: [id, ko, en, total_ha, forest_pct, built_pct, deforest_ha_yr, urban_ha_yr, ag_conv_ha]
        benchmarks = [
            ("riau", "리우", "Riau", 8702366.0, 0.42, 0.05, 34500.0, 4800.0, 42000.0),
            ("north_sumatra", "북수마트라", "North Sumatra", 7298123.0, 0.38, 0.08, 18500.0, 6200.0, 21000.0),
            ("south_sulawesi", "남술라웨시", "South Sulawesi", 4671748.0, 0.48, 0.07, 9800.0, 3900.0, 11500.0),
            ("southeast_sulawesi", "동남술라웨시", "Southeast Sulawesi", 3806770.0, 0.58, 0.04, 12400.0, 2100.0, 8900.0),
            ("gorontalo", "고론탈로", "Gorontalo", 1125707.0, 0.62, 0.04, 4200.0, 850.0, 5100.0),
            ("west_java", "서자바", "West Java", 3537776.0, 0.22, 0.24, 6200.0, 14500.0, 8200.0),
            ("central_java", "중앙자바", "Central Java", 3280069.0, 0.18, 0.26, 3100.0, 9800.0, 4500.0),
            ("east_java", "동자바", "East Java", 4779975.0, 0.25, 0.19, 5800.0, 11200.0, 7800.0),
            ("banten", "반텐", "Banten", 966292.0, 0.20, 0.22, 2900.0, 6100.0, 3400.0),
            ("aceh", "아체", "Aceh", 5795600.0, 0.65, 0.04, 8500.0, 1800.0, 9200.0),
        ]

        elapsed = float(to_year - from_year)

        for pid, ko, en, tot_ha, f_pct, b_pct, def_yr, urb_yr, ag_conv in benchmarks:
            # Synthesize realistic 9x9 transition matrix in m2
            mat_ha = np.zeros((9, 9), dtype=np.float64)
            # Initial stocks guaranteed to partition 100% of province area
            f_ha = tot_ha * f_pct
            b_ha = tot_ha * b_pct
            rem_pct = max(0.01, 1.0 - (f_pct + b_pct))
            c_ha = tot_ha * (rem_pct * 0.55)
            w_ha = tot_ha * (rem_pct * 0.10)
            sh_ha = tot_ha * (rem_pct * 0.20)
            gr_ha = max(0.0, tot_ha - (f_ha + b_ha + c_ha + w_ha + sh_ha))

            total_loss = def_yr * elapsed
            total_urban_gain = urb_yr * elapsed

            # Preserved
            mat_ha[1, 1] = max(0.0, f_ha - total_loss)
            mat_ha[4, 4] = c_ha
            mat_ha[6, 6] = b_ha
            mat_ha[0, 0] = w_ha
            mat_ha[2, 2] = gr_ha
            mat_ha[5, 5] = sh_ha

            # Conversions
            # Forest loss distributed to conversions (sum = 100% of total_loss)
            mat_ha[1, 4] = total_loss * 0.65  # agricultural conversion / crops
            mat_ha[1, 5] = total_loss * 0.10  # shrub / degraded scrub
            mat_ha[1, 6] = total_loss * 0.05  # built-up / infrastructure
            mat_ha[1, 7] = total_loss * 0.20  # bare ground / mining / clearcut

            # Urban growth from crops and grass
            mat_ha[4, 6] = total_urban_gain * 0.65
            mat_ha[2, 6] = total_urban_gain * 0.35

            self.add_province(
                province_id=pid,
                name_ko=ko,
                name_en=en,
                matrix_m2=mat_ha * M2_PER_HA,
                from_year=from_year,
                to_year=to_year,
            )
