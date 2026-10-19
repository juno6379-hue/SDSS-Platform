"""Validate available auxiliary byte hashes while preserving missing-reference UNKNOWN coverage."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.data.recovery_auxiliary_content import inspect_recovery_auxiliary_content


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root', type=Path, default=ROOT / 'data')
    parser.add_argument('--expected-manifest-sha256', required=True)
    parser.add_argument('--max-local-bytes', type=int, default=64 * 1024 ** 2)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        if args.output:
            output = args.output.resolve()
            if not output.is_relative_to((ROOT / 'evidence').resolve()) or output.exists() or output.is_relative_to(args.data_root.resolve()):
                raise ValueError('Output must be a new file under project evidence and outside inspected data')
        report = inspect_recovery_auxiliary_content(args.data_root, args.expected_manifest_sha256, max_local_bytes=args.max_local_bytes)
        if args.output:
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open('x', encoding='utf-8') as stream:
                json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
                stream.write('\n')
        print(json.dumps(report, ensure_ascii=True, indent=2, allow_nan=False))
        return 0
    except (ValueError, OSError, TypeError, KeyError) as exc:
        print(('Auxiliary content inspection failed: ' + str(exc)).encode('ascii', errors='backslashreplace').decode('ascii'), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
