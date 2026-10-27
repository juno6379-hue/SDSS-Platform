#!/usr/bin/env python3
"""CLI runner for the fail-closed G8-G9 deterministic scenario fixture.

Writes five explicitly TESTED_SYNTHETIC records. It does not train, predict,
verify holdout independence, approve a model, or deploy anything.
"""
from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(PROJECT_ROOT / "backend")]

from app.ml.model_benchmark_evaluator import ModelBenchmarkEvaluator


def main():
    data_root = PROJECT_ROOT / "data"
    output_dir = PROJECT_ROOT / "docs" / "lcluc" / "v3"

    print("=" * 80)
    print(" [G8-G9] Deterministic Scenario Export (TESTED_SYNTHETIC / PROMOTION BLOCKED)")
    print(f" Data Root:   {data_root}")
    print(f" Output Dir:  {output_dir}")
    print("=" * 80)

    evaluator = ModelBenchmarkEvaluator(data_root)
    manifest_f, csv_f, conf_f, card_f, gov_f = evaluator.export_deliverables(output_dir)

    print(" [PASS] Fail-closed scenario records exported; no model promotion authorized.")
    print(f" [OUTPUT] Manifest:   {manifest_f} ({manifest_f.stat().st_size:,} bytes)")
    print(f" [OUTPUT] CSV:        {csv_f} ({csv_f.stat().st_size:,} bytes)")
    print(f" [OUTPUT] Confusion:  {conf_f} ({conf_f.stat().st_size:,} bytes)")
    print(f" [OUTPUT] Model Card: {card_f} ({card_f.stat().st_size:,} bytes)")
    print(f" [OUTPUT] Governance: {gov_f} ({gov_f.stat().st_size:,} bytes)")
    print("=" * 80)


if __name__ == "__main__":
    main()
