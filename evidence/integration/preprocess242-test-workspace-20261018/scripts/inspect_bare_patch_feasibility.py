"""Inspect stored bare-patch necessary bounds; never collect, assess or train."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.ml.bare_patch_feasibility import inspect_bare_patch_feasibility, REPORT_RELATIVE, OUTPUT_CAP
from backend.app.ml.split_json_io import BoundedJSONIO
from scripts.inspect_readiness_connectivity_lineage import _output_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root', type=Path, default=ROOT / 'data')
    parser.add_argument('--expected-report-sha256', required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        if args.output:
            logical, target, parent = _output_path(args.output, args.data_root, [args.data_root / REPORT_RELATIVE])
        result = inspect_bare_patch_feasibility(args.data_root, args.expected_report_sha256)
        if args.output:
            io = BoundedJSONIO({'input_caps': {role: OUTPUT_CAP for role in ['source', 'readiness', 'saved_plan', 'candidate']},
                'output_caps': {'plan': OUTPUT_CAP, 'candidate': OUTPUT_CAP}, 'max_depth': 32})
            size = io.measure(result, 'plan')
            if logical.resolve() != target or logical.parent.resolve() != parent or logical.is_symlink() or logical.exists():
                raise ValueError('새 evidence 경로가 변경됐거나 존재합니다.')
            target.parent.mkdir(parents=True, exist_ok=True)
            if logical.resolve() != target or logical.parent.resolve() != parent:
                raise ValueError('evidence parent changed')
            io.write(target, result, 'plan', size)
        print(json.dumps(result, ensure_ascii=True, allow_nan=False))
        return 0
    except (ValueError, OSError, TypeError, KeyError, IndexError, AttributeError, RecursionError, OverflowError) as error:
        print(('Bare patch feasibility failed: ' + str(error)).encode('ascii', errors='backslashreplace').decode('ascii'), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
