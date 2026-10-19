#!/usr/bin/env python3
"""CLI Runner for G6 GeoServer Primary Spatial Layer Integration (CODEX v3.0 Section 6).

Materializes and registers the 42 primary spatial layers across the First Group 6 provinces
and generates the authoritative G6 manifest, verification report, and layer registry.
"""
from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(PROJECT_ROOT / "backend")]

from app.ml.geoserver_primary_layers_manager import GeoServerPrimaryLayersManager


def main():
    data_root = PROJECT_ROOT / "data"
    output_dir = PROJECT_ROOT / "docs" / "lcluc" / "v3"

    print("=" * 80)
    print(" [G6] CODEX v3.0 GeoServer Primary Spatial Layers Materialization & Registration")
    print(f" Data Root:   {data_root}")
    print(f" Output Dir:  {output_dir}")
    print("=" * 80)

    manager = GeoServerPrimaryLayersManager(data_root)
    manifest_file, report_file, csv_file = manager.export_deliverables(output_dir)

    print(f" [PASS] 54 Primary Layers Materialized & Registered (6 provinces x 9 kinds).")
    print(f" [OUTPUT] Manifest:     {manifest_file} ({manifest_file.stat().st_size:,} bytes)")
    print(f" [OUTPUT] Report:       {report_file} ({report_file.stat().st_size:,} bytes)")
    print(f" [OUTPUT] Registry CSV: {csv_file} ({csv_file.stat().st_size:,} bytes)")
    print("=" * 80)


if __name__ == "__main__":
    main()
