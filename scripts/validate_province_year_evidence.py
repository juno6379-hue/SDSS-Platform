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
    validate_local_scl_mosaic_manifest,
)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Validate all 36 province-year SCL mosaic pairs and pins.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--allow-execution", action="store_true",
        help="Accept a manifest that truthfully records an authorized collector/ledger execution.",
    )
    args = parser.parse_args()
    try:
        result = validate_local_scl_mosaic_manifest(
            args.manifest, output_path=args.output, allow_execution=args.allow_execution,
        )
    except ProvinceEvidenceError as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
