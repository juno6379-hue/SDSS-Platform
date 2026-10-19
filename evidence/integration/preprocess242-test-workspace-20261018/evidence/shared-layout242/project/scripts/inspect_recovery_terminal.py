"""Read-only pending batch terminal metadata inspection. Never settles or resumes."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.data.recovery_terminal import inspect_recovery_terminal


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root', type=Path, default=ROOT / 'data')
    parser.add_argument('--output', type=Path, help='Optional new file under project evidence; default stdout only')
    args = parser.parse_args()
    try:
        report = inspect_recovery_terminal(args.data_root)
        if args.output:
            output = args.output.resolve()
            if not output.is_relative_to((ROOT / 'evidence').resolve()) or output.exists():
                raise ValueError('Output must be a new file under project evidence')
            if output.is_relative_to(args.data_root.resolve()):
                raise ValueError('Output cannot be inside inspected data root')
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open('x', encoding='utf-8') as stream:
                json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
                stream.write('\n')
        print(json.dumps(report, ensure_ascii=True, indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        message = ('Recovery terminal inspection failed: ' + str(exc)).encode('ascii', errors='backslashreplace').decode('ascii')
        print(message, file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
