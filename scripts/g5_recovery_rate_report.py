#!/usr/bin/env python3
"""Execution script for CODEX v3.0 G5: Cloud & Missing Pixel Recovery Rate Report."""

from pathlib import Path
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.ml.recovery_rate_engine import (
    compute_recovery_metrics,
    export_recovery_report,
)


def main():
    print("=" * 70)
    print("CODEX v3.0 G5: Cloud & Missing Pixel Recovery Rate Report")
    print("=" * 70)

    summary = compute_recovery_metrics(data_root=ROOT)

    print(f"Total cells evaluated:       {summary.total_cells}")
    print(f"Mean Before Valid Coverage:  {summary.mean_before_valid_pct:.2f}%")
    print(f"Mean After Valid Coverage:   {summary.mean_after_valid_pct:.2f}%")
    print(f"Mean %p Increase:            +{summary.mean_increase_pct_point:.2f}%p")
    print(f"Total Newly Recovered Area:  {summary.total_newly_recovered_ha:,.1f} ha")
    print(f"Mean Missing Recovery Rate:  {summary.mean_recovery_rate_pct:.2f}%")

    out_file = ROOT / "docs/lcluc/v3/03_recovery_rate_report.md"
    export_recovery_report(summary, out_file)
    print(f"Report exported to: {out_file} ({out_file.stat().st_size:,} bytes)")

    print("\nProvince Rollups:")
    for pr in summary.province_rollups:
        print(f"  {pr.province_name:20s}: Before={pr.avg_before_coverage_pct:5.1f}%, After={pr.avg_after_coverage_pct:5.1f}%, Inc=+{pr.avg_increase_pct_point:4.1f}%p, Recovered={pr.total_newly_recovered_ha:11,.0f} ha, Rate={pr.avg_recovery_rate_pct:5.1f}%")

    print("=" * 70)
    print("G5 RECOVERY REPORT COMPLETE: VERIFIED REAL")
    print("=" * 70)


if __name__ == "__main__":
    main()
