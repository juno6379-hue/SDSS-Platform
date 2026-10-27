from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.ml.province_year_evidence_builder import (  # noqa: E402
    ProvinceEvidenceError,
    build_evidence_bundle,
)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(
        description="Build a six-province boundary candidate, GISTARU probe, and 36 local SCL mosaics."
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        default=ROOT / "data" / "first-group-training-esri-v1" / "sources",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--resolution-m", type=float, default=1000.0)
    parser.add_argument("--boundary-timeout", type=float, default=120.0)
    parser.add_argument("--gistaru-timeout", type=float, default=20.0)
    parser.add_argument(
        "--resume", action="store_true",
        help="Reuse already pinned boundary/GISTARU artifacts after an interrupted build.",
    )
    args = parser.parse_args()
    try:
        result = build_evidence_bundle(
            source_root=args.source_root,
            output_dir=args.output_dir,
            resolution_m=args.resolution_m,
            boundary_timeout=args.boundary_timeout,
            gistaru_timeout=args.gistaru_timeout,
            resume=args.resume,
        )
    except ProvinceEvidenceError as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
