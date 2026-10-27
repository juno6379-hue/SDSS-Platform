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


def _metric(value, suffix="", precision=2):
    return "null" if value is None else f"{value:.{precision}f}{suffix}"


def main():
    print("=" * 70)
    print("CODEX v3.0 G5: Cloud & Missing Pixel Recovery Rate Report")
    print("=" * 70)

    summary = compute_recovery_metrics(data_root=ROOT)

    print(f"Total cells evaluated:       {summary.total_cells}")
    print(f"Evidence status:             {summary.evidence_status}")
    print(f"Blocking reason:             {summary.blocking_reason}")
    print(f"Mean Before Valid Coverage:  {_metric(summary.mean_before_valid_pct, '%')}")
    print(f"Mean After Valid Coverage:   {_metric(summary.mean_after_valid_pct, '%')}")
    print(f"Aggregate Net Change:        {_metric(summary.mean_aggregate_net_coverage_change_pct_point, '%p')}")
    print(f"Total Newly Recovered Area:  {_metric(summary.total_newly_recovered_ha, ' ha', 1)}")
    print(f"Mean Missing Recovery Rate:  {_metric(summary.mean_recovery_rate_pct, '%')}")

    out_file = ROOT / "docs/lcluc/v3/03_recovery_rate_report.md"
    export_recovery_report(summary, out_file)
    print(f"Report exported to: {out_file} ({out_file.stat().st_size:,} bytes)")

    print("\nProvince Rollups:")
    for pr in summary.province_rollups:
        print(
            f"  {pr.province_name:20s}: status={pr.status}, "
            f"Before={_metric(pr.avg_before_coverage_pct, '%', 1)}, "
            f"After={_metric(pr.avg_after_coverage_pct, '%', 1)}, "
            f"Net={_metric(pr.avg_aggregate_net_coverage_change_pct_point, '%p', 1)}, "
            f"Recovered={_metric(pr.total_newly_recovered_ha, ' ha', 0)}, "
            f"Rate={_metric(pr.avg_recovery_rate_pct, '%', 1)}"
        )

    print("=" * 70)
    print(f"G5 RECOVERY REPORT COMPLETE: {summary.evidence_status}")
    print("=" * 70)


if __name__ == "__main__":
    main()
