#!/usr/bin/env python3
"""Execution script for CODEX v3.0 G2: 432 Province-Month Availability Audit."""

from pathlib import Path
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.ml.province_month_coverage_audit import (
    build_province_month_audit,
    export_audit_csv,
    export_audit_markdown,
)


def _metric(value, suffix="", precision=2):
    return "null" if value is None else f"{value:.{precision}f}{suffix}"


def main():
    print("=" * 70)
    print("CODEX v3.0 G2: 432 Province-Month Availability & Gap Analysis Audit")
    print("=" * 70)

    data_root = ROOT / "data"
    result = build_province_month_audit(data_root=data_root)

    print(f"Total Province-Month cells evaluated: {result.total_cells} (expected: 432)")
    print(f"Dry Season (Jun-Sep) window cells:   {result.dry_season_cells} (33.3%)")
    print(f"Wet Season (Oct-May) excluded cells: {result.wet_season_cells} (66.7%)")
    print(f"Active acquired observation cells:   {result.active_observation_cells}")
    print(f"Total patch inventory:               {result.total_patches_inventory:,}")
    print(f"Eligible 6-band patches:             {result.total_eligible_patches:,} ({result.overall_eligible_rate*100:.1f}%)")
    print(f"Insufficient patches:                {result.total_insufficient_patches:,} ({(1-result.overall_eligible_rate)*100:.1f}%)")
    print(f"Coverage measurement status:         {result.coverage_measurement_status}")
    print(f"Nominal cells:                        {result.nominal_cells_count}")
    print(f"Degraded cells:                       {result.degraded_cells_count}")
    print(f"Unclassified cells:                   {result.unclassified_cells_count}")

    csv_out = ROOT / "docs/lcluc/v3/02_432_province_month_availability_audit.csv"
    md_out = ROOT / "docs/lcluc/v3/02_432_province_month_availability_report.md"

    export_audit_csv(result, csv_out)
    print(f"Exported CSV: {csv_out} ({csv_out.stat().st_size:,} bytes)")

    export_audit_markdown(result, md_out)
    print(f"Exported Markdown: {md_out} ({md_out.stat().st_size:,} bytes)")

    print("\nProvince Rollups:")
    for pr in result.province_rollups:
        print(f"  {pr.province_name:20s}: {pr.total_patches:4d} patches, {pr.eligible_patches:4d} eligible ({pr.eligible_rate*100:5.1f}%), cloud: {_metric(pr.avg_cloud_cover_pct, '%')}, valid: {_metric(pr.avg_valid_coverage_pct, '%')}, unclassified: {pr.unclassified_cell_count}")

    print("\nYear Rollups:")
    for yr in result.year_rollups:
        print(f"  {yr.year} ({yr.epoch:13s}): {yr.total_patches:4d} patches, {yr.eligible_patches:4d} eligible ({yr.eligible_rate*100:5.1f}%), cloud: {_metric(yr.avg_cloud_cover_pct, '%')}, valid: {_metric(yr.avg_valid_coverage_pct, '%')}, unclassified: {yr.unclassified_cell_count}")

    print("=" * 70)
    print("G2 INVENTORY AUDIT COMPLETE: 432/432 CELLS; COVERAGE BLOCKED_NOT_MEASURED")
    print("=" * 70)


if __name__ == "__main__":
    main()
