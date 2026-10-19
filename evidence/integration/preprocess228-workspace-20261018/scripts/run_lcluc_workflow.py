"""Explicit local LCLUC tile workflow. No downloads, training, or implicit DATA root."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from app.lcluc_workflow import WorkflowError, execute_lcluc_workflow, strict_request_json
from app.store import Store


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--data-root', type=Path, required=True)
    parser.add_argument('--request', type=Path, required=True)
    args = parser.parse_args()
    if not args.execute:
        parser.error('--execute is required; no implicit execution is allowed')
    try:
        with args.request.open('rb') as stream:
            request = strict_request_json(stream.read(16385))
        result = execute_lcluc_workflow(Store(args.data_root, recover_jobs=False), request)
        print(json.dumps(result, ensure_ascii=True, allow_nan=False))
        return 0 if result['status'] == 'SUCCEEDED' else 2
    except WorkflowError as error:
        print(json.dumps({'status': 'REJECTED', 'issue': str(error)}))
        return 2
    except Exception:
        print(json.dumps({'status': 'REJECTED', 'issue': 'LOCAL_WORKFLOW_UNAVAILABLE'}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
