"""Build a fail-closed, non-executing province-year gap acquisition plan."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.ml.province_year_coverage import PinnedFile
from app.ml.province_year_gap_acquisition_planner import (
    GapPlanningEvidenceError, build_gap_acquisition_plan, write_plan_json,
)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--boundaries", type=Path, required=True)
    parser.add_argument("--boundaries-sha256", required=True)
    cross_check = parser.add_mutually_exclusive_group(required=True)
    cross_check.add_argument("--gistaru-reference", type=Path)
    cross_check.add_argument("--cross-check-decision", type=Path)
    parser.add_argument("--gistaru-reference-sha256")
    parser.add_argument("--cross-check-decision-sha256")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--evidence-status", choices=("VERIFIED_REAL", "TESTED_SYNTHETIC", "PROVISIONAL_REAL"),
                        default="VERIFIED_REAL")
    args = parser.parse_args(argv)
    try:
        if args.gistaru_reference and not args.gistaru_reference_sha256:
            parser.error("--gistaru-reference-sha256 is required with --gistaru-reference")
        if args.cross_check_decision and not args.cross_check_decision_sha256:
            parser.error("--cross-check-decision-sha256 is required with --cross-check-decision")
        plan = build_gap_acquisition_plan(
            root=args.root,
            source=PinnedFile(args.source, args.source_sha256),
            boundaries=PinnedFile(args.boundaries, args.boundaries_sha256),
            gistaru_reference=(
                PinnedFile(args.gistaru_reference, args.gistaru_reference_sha256)
                if args.gistaru_reference else None
            ),
            cross_check_decision=(
                PinnedFile(args.cross_check_decision, args.cross_check_decision_sha256)
                if args.cross_check_decision else None
            ),
            evidence_status=args.evidence_status,
        )
        write_plan_json(plan, args.output)
    except (GapPlanningEvidenceError, OSError) as exc:
        print(json.dumps({
            "status": "BLOCKED", "reason": str(exc), "output_written": False,
            "collector_invoked": False, "ledger_written": False,
            "execution_lock_acquired": False, "remote_downloads_performed": False,
            "retraining_ready": False,
        }, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps({
        "status": plan.planning_status, "target_count": plan.target_count,
        "output": str(args.output), "execution_authorized": False,
        "collector_invoked": False, "ledger_written": False,
        "execution_lock_acquired": False, "remote_downloads_performed": False,
        "mlops_handoff_status": plan.mlops_handoff.status,
        "retraining_ready": plan.mlops_handoff.retraining_ready,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
