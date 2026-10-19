#!/usr/bin/env python3
"""CLI Runner for G7 AI Dataset Splits & Training Readiness Gate (CODEX v3.0 Section 7.1).

Scans the dataset patches, partitions into Geographic Holdout (Train/Val/Test),
evaluates zero-leakage and readiness criteria, and writes the 3 G7 deliverables to docs/lcluc/v3/.
"""
from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(PROJECT_ROOT / "backend")]

from app.ml.ai_dataset_splits_manager import AIDatasetSplitsManager


def main():
    data_root = PROJECT_ROOT / "data"
    output_dir = PROJECT_ROOT / "docs" / "lcluc" / "v3"

    print("=" * 80)
    print(" [G7] CODEX v3.0 AI Dataset Geographic Holdout Splits & Readiness Gate")
    print(f" Data Root:   {data_root}")
    print(f" Output Dir:  {output_dir}")
    print("=" * 80)

    manager = AIDatasetSplitsManager(data_root)
    manifest_f, csv_f, report_f = manager.export_deliverables(output_dir)

    print(f" [PASS] Geographic Holdout Splits Evaluated.")
    print(f" [OUTPUT] Manifest: {manifest_f} ({manifest_f.stat().st_size:,} bytes)")
    print(f" [OUTPUT] CSV:      {csv_f} ({csv_f.stat().st_size:,} bytes)")
    print(f" [OUTPUT] Report:   {report_f} ({report_f.stat().st_size:,} bytes)")
    print("=" * 80)


if __name__ == "__main__":
    main()
