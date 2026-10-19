"""완료 실험을 실제 파일 근거와 함께 Draft로 등록하는 로컬 명령."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from app.experiment_registry import register_experiment
from app.store import Store


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', required=True, help='data 안의 완료 experiment.json 경로')
    parser.add_argument('--data-root', type=Path, default=ROOT / 'data')
    args = parser.parse_args()
    result = register_experiment(Store(args.data_root, recover_jobs=False), args.report)
    print(json.dumps({'model_id': result['model']['id'], 'dataset_id': result['dataset']['id'],
        'status': result['model']['status'], 'independent_evaluation': False,
        'checkpoint_sha256': result['model']['checkpoint_sha256'], 'claim': result['claim']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
