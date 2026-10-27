#!/usr/bin/env python3
"""Export local fail-closed G10-G14 evidence reports.

The command inspects supplied evidence and writes BLOCKED/null reports when
executed inference or T1/T2 inputs are absent. It never publishes GeoServer
layers, writes an operational registry, or executes change detection.
"""
from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(PROJECT_ROOT / "backend")]

from app.ml.geoserver_secondary_and_change_manager import GeoServerSecondaryAndChangeManager


def main():
    data_root = PROJECT_ROOT / "data"
    output_dir = PROJECT_ROOT / "docs" / "lcluc" / "v3"

    print("=" * 80)
    print(" [G10-G14] CODEX v3.0 Fail-Closed Secondary Evidence Export")
    print(f" Data Root:   {data_root}")
    print(f" Output Dir:  {output_dir}")
    print("=" * 80)

    manager = GeoServerSecondaryAndChangeManager(data_root)
    results = manager.export_all_downstream_deliverables(output_dir)

    print(" [BLOCKED] Reports exported; no model inference, publication, or measured change completed.")
    for k, p in results.items():
        print(f" [OUTPUT] {k:15}: {p} ({p.stat().st_size:,} bytes)")
    print("=" * 80)


if __name__ == "__main__":
    main()
