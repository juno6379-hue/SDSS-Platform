"""완료된 로컬 실험의 실제 파일을 확인하고 Draft로만 등록한다."""
import hashlib
import json
from pathlib import Path
import re


def checked_path(root, value):
    path = (root / str(value)).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError('데이터 루트 안의 실제 실험 산출물이 필요합니다.')
    return path


def digest(path):
    checksum = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            checksum.update(chunk)
    return checksum.hexdigest()


def register_experiment(store, report_path):
    root = Path(store.root).resolve()
    path = checked_path(root, report_path)
    report = json.loads(path.read_text(encoding='utf-8'))
    trained = report.get('training') or {}
    prepared = report.get('dataset') or {}
    if not str(report.get('status', '')).startswith('completed_') or trained.get('training_state') != 'completed':
        raise ValueError('중단·미완료 실험은 완료 모델로 등록할 수 없습니다.')
    model_id, dataset_id = trained.get('model_id'), prepared.get('dataset_id')
    if any(not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', value) for value in (model_id, dataset_id)):
        raise ValueError('실험의 모델/데이터셋 ID를 확인하세요.')
    if any(item['id'] == model_id for item in store.list('models')) or any(item['id'] == dataset_id for item in store.list('datasets')):
        raise ValueError('기존 모델/데이터셋을 덮어쓰지 않습니다.')
    checkpoint = checked_path(root, trained.get('checkpoint_path'))
    checkpoint_hash = digest(checkpoint)
    if checkpoint_hash != trained.get('checkpoint_sha256'):
        raise ValueError('실험 체크포인트 해시가 기록과 다릅니다.')
    training_report_path = checkpoint.parent / 'report.json'
    if json.loads(checked_path(root, training_report_path).read_text(encoding='utf-8')) != trained:
        raise ValueError('실험에 포함된 학습 결과가 실제 학습 보고서와 다릅니다.')
    manifest_path = checked_path(root, prepared.get('manifest_path'))
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if (manifest.get('dataset_id') != dataset_id or manifest.get('version') != trained.get('dataset_version')
            or manifest.get('version') != prepared.get('version')):
        raise ValueError('학습 데이터셋 버전과 실험의 출처가 다릅니다.')
    lineage = {'experiment_report_path': str(path.relative_to(root)), 'experiment_report_sha256': digest(path),
               'dataset_manifest_sha256': digest(manifest_path), 'training_report_sha256': digest(training_report_path)}
    dataset = store.put('datasets', {**prepared, 'id': dataset_id, 'kind': 'prepared-training-dataset', **lineage})
    model = store.put('models', {**trained, 'id': model_id, 'status': 'Draft', 'independent_evaluation': False,
        'scientific_accuracy_validated': False, 'history': [], 'training_history': trained.get('history', []),
        'checkpoint_path': str(checkpoint.relative_to(root)), 'checkpoint_sha256': checkpoint_hash,
        'dataset_id': dataset['id'], **lineage})
    return {'model': model, 'dataset': dataset, 'claim': '의사라벨 실험 등록이며 독립 검증·승인·배포가 아닙니다.'}
