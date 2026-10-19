"""Verify a saved split-repair metadata plan without candidate publication or training."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.ml.split_validation import load_json_document, validate_split_repair_plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--saved-plan', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--expected-sha256', required=True)
    parser.add_argument('--plan', type=Path, required=True, help='Caller-selected experiment policy, not saved repair report')
    parser.add_argument('--readiness', type=Path)
    parser.add_argument('--readiness-sha256')
    parser.add_argument('--data-root', type=Path, default=ROOT / 'data')
    parser.add_argument('--candidate', type=Path)
    parser.add_argument('--candidate-sha256')
    parser.add_argument('--output', type=Path, help='Optional new evidence file; default stdout only')
    args = parser.parse_args()
    try:
        policy_sha = hashlib.sha256(args.plan.read_bytes()).hexdigest()
        policy = load_json_document(args.plan)
        report = validate_split_repair_plan(args.saved_plan, args.manifest, args.expected_sha256,
            province_splits=policy['province_splits'], readiness_path=args.readiness,
            readiness_sha256=args.readiness_sha256, data_root=args.data_root,
            candidate_path=args.candidate, candidate_sha256=args.candidate_sha256)
        if hashlib.sha256(args.plan.read_bytes()).hexdigest() != policy_sha:
            raise ValueError('Caller policy changed during validation (stale)')
        report['caller_policy'] = {'path': str(args.plan.resolve()), 'sha256': policy_sha}
        payload = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)
        if args.output:
            protected = [args.plan, args.saved_plan, args.manifest, args.readiness, args.candidate]
            output = args.output.resolve()
            if not output.is_relative_to((ROOT / 'evidence').resolve()):
                raise ValueError('Output must be a new file inside the project evidence directory')
            if any(output == path.resolve() for path in protected if path is not None) or output.exists():
                raise ValueError('Output must be a new path; input/existing files cannot be overwritten')
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open('x', encoding='utf-8') as stream:
                stream.write(payload + '\n')
        # Console code pages (including Windows CP949) may not encode paths.
        print(json.dumps(report, ensure_ascii=True, indent=2, allow_nan=False))
    except (ValueError, OSError, KeyError, TypeError, IndexError, AttributeError) as exc:
        print(('Split repair validation failed: ' + str(exc)).encode('ascii', errors='backslashreplace').decode('ascii'), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
