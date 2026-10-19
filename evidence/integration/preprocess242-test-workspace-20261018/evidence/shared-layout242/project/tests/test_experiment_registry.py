"""실험 등록의 해시·완료 상태·Draft 강제를 임시 파일로 확인한다."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from app.experiment_registry import register_experiment
from app.store import Store


class ExperimentRegistryTests(unittest.TestCase):
    def setup_files(self, root):
        # 직렬화 계약용 바이트 fixture이며 학습·성능 시험 자료가 아니다.
        directory = root / 'models' / 'fixture_model'
        directory.mkdir(parents=True)
        checkpoint = directory / 'best.pt'
        checkpoint.write_bytes(b'explicit-serialization-test-fixture')
        trained = {'model_id': 'fixture_model', 'training_state': 'completed', 'dataset_version': 'v1',
            'checkpoint_path': 'models/fixture_model/best.pt', 'checkpoint_sha256': hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
            'status': 'Approved', 'independent_evaluation': True, 'synthetic': True}
        (directory / 'report.json').write_text(json.dumps(trained), encoding='utf-8')
        manifest = root / 'datasets' / 'fixture_dataset' / 'manifest.json'
        manifest.parent.mkdir(parents=True)
        manifest.write_text(json.dumps({'dataset_id': 'fixture_dataset', 'version': 'v1'}), encoding='utf-8')
        report = root / 'experiment.json'
        report.write_text(json.dumps({'status': 'completed_weak_label_experiment', 'training': trained,
            'dataset': {'dataset_id': 'fixture_dataset', 'version': 'v1', 'manifest_path': 'datasets/fixture_dataset/manifest.json'}}), encoding='utf-8')
        return report, checkpoint

    def test_registration_forces_draft_and_cannot_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report, _ = self.setup_files(root)
            store = Store(root)
            result = register_experiment(store, str(report))
            self.assertEqual(result['model']['status'], 'Draft')
            self.assertFalse(result['model']['independent_evaluation'])
            self.assertFalse(result['model']['scientific_accuracy_validated'])
            with self.assertRaises(ValueError):
                register_experiment(store, str(report))

    def test_modified_checkpoint_never_registers_model_or_dataset(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report, checkpoint = self.setup_files(root)
            checkpoint.write_bytes(b'changed')
            store = Store(root)
            with self.assertRaises(ValueError):
                register_experiment(store, str(report))
            self.assertEqual(store.list('models'), [])
            self.assertEqual(store.list('datasets'), [])

    def test_paused_report_is_not_registered_as_completed_model(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report, _ = self.setup_files(root)
            value = json.loads(report.read_text())
            value['training']['training_state'] = 'paused'
            report.write_text(json.dumps(value))
            with self.assertRaises(ValueError):
                register_experiment(Store(root), str(report))
