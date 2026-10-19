"""Diagnose physical-source corner proxy candidates across the fixed province split policy."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.data.recovery_source_split_overlap import inspect_recovery_source_split_overlap


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root', type=Path, default=ROOT / 'data')
    parser.add_argument('--expected-manifest-sha256', required=True)
    parser.add_argument('--max-source-headers', type=int, default=128)
    parser.add_argument('--max-pairs', type=int, default=10000)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        if args.output:
            output = args.output.resolve()
            if not output.is_relative_to((ROOT / 'evidence').resolve()) or output.exists() or output.is_relative_to(args.data_root.resolve()):
                raise ValueError('Output must be a new file under project evidence and outside inspected data')
        report = inspect_recovery_source_split_overlap(args.data_root, args.expected_manifest_sha256, max_source_headers=args.max_source_headers, max_pairs=args.max_pairs)
        if args.output:
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open('x', encoding='utf-8') as stream:
                json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
                stream.write('\n')
        print(json.dumps(report, ensure_ascii=True, indent=2, allow_nan=False))
        return 0
    except (ValueError, OSError, TypeError, KeyError, RecursionError) as exc:
        print(('Source split overlap inspection failed: ' + str(exc)).encode('ascii', errors='backslashreplace').decode('ascii'), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
