"""Run one budgeted Sentinel-2 SCL pilot and rebuild the 36-cell inventory mosaic."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.ml.province_year_coverage import PinnedFile  # noqa: E402
from app.ml.province_year_pilot_collector import run_provisional_pilot  # noqa: E402


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--boundary", type=Path, required=True)
    parser.add_argument("--boundary-sha256", required=True)
    parser.add_argument("--mosaic-manifest", type=Path, required=True)
    parser.add_argument("--mosaic-manifest-sha256", required=True)
    parser.add_argument("--cross-check-decision", type=Path, required=True)
    parser.add_argument("--cross-check-decision-sha256", required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument(
        "--ledger", type=Path,
        default=ROOT / "data/first-group-training-budget/global-ledger.json",
    )
    parser.add_argument(
        "--execution-lock", type=Path,
        default=ROOT / "data/first-group-training-budget/global-ledger.execution.lock",
    )
    args = parser.parse_args()
    try:
        completion = run_provisional_pilot(
            workspace=ROOT,
            boundary=PinnedFile(args.boundary, args.boundary_sha256),
            mosaic_manifest=PinnedFile(args.mosaic_manifest, args.mosaic_manifest_sha256),
            cross_check_decision=PinnedFile(args.cross_check_decision, args.cross_check_decision_sha256),
            source_root=args.source_root,
            evidence_dir=args.evidence_dir,
            ledger_path=args.ledger,
            execution_lock=args.execution_lock,
        )
    except Exception as exc:
        print(json.dumps({"status": "FAILED", "error_type": type(exc).__name__, "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(completion, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
