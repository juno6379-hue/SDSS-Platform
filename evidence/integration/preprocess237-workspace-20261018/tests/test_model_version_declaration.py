"""Optional caller metadata using tiny synthetic files and temporary catalogs."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app import experiment_registry
from app.store import Store
import test_experiment_registry as previous


ORIGINAL = Path(__file__).resolve().parents[1] / 'evidence/integration/model-version-original-registry-20261017.py'
ORIGINAL_SHA = 'a20468f121900094808112b9c8e783bf2a0ce59f520ff0bffbbcf2438bd12548'


class RecordingStore(Store):
    def __init__(self, root):
        self.puts = []
        super().__init__(root)

    def put(self, kind, record):
        self.puts.append((kind, copy.deepcopy(record)))
        return super().put(kind, record)


class ModelVersionDeclarationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if hashlib.sha256(ORIGINAL.read_bytes()).hexdigest() != ORIGINAL_SHA:
            raise AssertionError('Original registry evidence changed')
        spec = importlib.util.spec_from_file_location('app._model_version_original97', ORIGINAL)
        cls.original = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.original)

    def fixture(self, root, trained_changes=None):
        report, checkpoint = previous.ExperimentRegistryTests.setup_files(self, root)
        if trained_changes:
            value = json.loads(report.read_text(encoding='utf-8'))
            value['training'].update(trained_changes)
            report.write_text(json.dumps(value), encoding='utf-8')
            (checkpoint.parent / 'report.json').write_text(json.dumps(value['training']), encoding='utf-8')
        return report, checkpoint

    def file_hashes(self, root):
        return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in root.rglob('*') if path.is_file() and path.name != 'catalog.sqlite3'}

    def stored_bytes(self, store):
        with store.connect() as connection:
            return connection.execute('SELECT kind,id,body FROM records ORDER BY kind,id').fetchall()

    def test_omitted_exact_original_response_records_and_file_bytes(self):
        for extras in ({}, {'model_version': ' v1 '}, {'model_version': None},
                       {'model_version': 'latest', 'model_version_declaration': {
                           'schema_version': 1, 'source': 'CALLER_EXPLICIT_REGISTRATION', 'version': 'forged',
                           'checkpoint_sha256': '0' * 64, 'training_report_sha256': '0' * 64}}):
            outcomes = []
            for module in (self.original, experiment_registry):
                with tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary); report, _ = self.fixture(root, extras)
                    before = self.file_hashes(root); store = RecordingStore(root)
                    with patch('app.store.now', return_value='2026-10-17T00:00:00Z'):
                        result = module.register_experiment(store, str(report))
                    self.assertEqual(self.file_hashes(root), before)
                    outcomes.append((result, self.stored_bytes(store), store.puts))
                    for key, value in extras.items():
                        self.assertEqual(result['model'][key], value)
                    if not extras:
                        self.assertNotIn('model_version', result['model'])
                        self.assertNotIn('model_version_declaration', result['model'])
            self.assertEqual(outcomes[0], outcomes[1])

    def test_explicit_model_only_exact_five_fields_and_existing_hashes_draft(self):
        for version in ('v2', ' v1 ', 'x' * 256):
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary); report, checkpoint = self.fixture(root)
                before = self.file_hashes(root); store = RecordingStore(root)
                result = experiment_registry.register_experiment(store, str(report), model_version=version)
                declaration = result['model']['model_version_declaration']
                self.assertEqual(declaration, {
                    'schema_version': 1, 'source': 'CALLER_EXPLICIT_REGISTRATION', 'version': version,
                    'checkpoint_sha256': hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
                    'training_report_sha256': hashlib.sha256((checkpoint.parent / 'report.json').read_bytes()).hexdigest(),
                })
                self.assertIs(type(declaration['schema_version']), int)
                self.assertNotIn('model_version', result['model'])
                self.assertNotIn('model_version_declaration', result['dataset'])
                self.assertNotIn('model_version', result['dataset'])
                self.assertEqual(result['model']['status'], 'Draft')
                self.assertIs(result['model']['independent_evaluation'], False)
                self.assertIs(result['model']['scientific_accuracy_validated'], False)
                self.assertEqual([kind for kind, _ in store.puts], ['datasets', 'models'])
                self.assertEqual(self.file_hashes(root), before)

    def test_explicit_reuses_existing_digest_reads_and_no_inferred_dataset_version(self):
        calls = []
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); report, _ = self.fixture(root)
            original_digest = experiment_registry.digest
            def record(path):
                calls.append(path.relative_to(root).as_posix())
                return original_digest(path)
            with patch.object(experiment_registry, 'digest', side_effect=record):
                result = experiment_registry.register_experiment(RecordingStore(root), str(report), model_version='caller-v9')
            self.assertEqual(calls, ['models/fixture_model/best.pt', 'experiment.json',
                                    'datasets/fixture_dataset/manifest.json', 'models/fixture_model/report.json'])
            self.assertEqual(result['model']['dataset_version'], 'v1')
            self.assertEqual(result['model']['model_version_declaration']['version'], 'caller-v9')

    def test_invalid_explicit_values_fail_before_first_put_without_file_changes(self):
        for version in (None, True, 1, 1.5, {}, [], '', ' ', 'latest', ' CURRENT ',
                        'v\x00', 'v\x7f', 'v\x9f', '\ud800', 'x' * 257):
            with self.subTest(version=repr(version)), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary); report, _ = self.fixture(root)
                before = self.file_hashes(root); store = RecordingStore(root)
                with self.assertRaisesRegex(ValueError, 'MODEL_REFERENCE_INVALID|MODEL_VERSION_NOT_PINNED'):
                    experiment_registry.register_experiment(store, str(report), model_version=version)
                self.assertEqual(store.puts, [])
                self.assertEqual(self.stored_bytes(store), [])
                self.assertEqual(self.file_hashes(root), before)

    def test_existing_raw_model_version_requires_exact_string_match(self):
        for raw_version in ('v2', ' v1 ', None, True, 1, {'version': 'v1'}):
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary); report, _ = self.fixture(root, {'model_version': raw_version})
                store = RecordingStore(root)
                with self.assertRaisesRegex(ValueError, 'model_version'):
                    experiment_registry.register_experiment(store, str(report), model_version='v1')
                self.assertEqual(store.puts, [])
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); report, _ = self.fixture(root, {'model_version': ' v1 '})
            result = experiment_registry.register_experiment(RecordingStore(root), str(report), model_version=' v1 ')
            self.assertEqual(result['model']['model_version'], ' v1 ')
            self.assertEqual(result['model']['model_version_declaration']['version'], ' v1 ')

    def test_any_preexisting_declaration_key_conflicts_even_same_shape_or_null(self):
        for declaration in (None, {}, False, {'source': 'CALLER_EXPLICIT_REGISTRATION', 'version': 'v1'}):
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary); report, _ = self.fixture(root, {'model_version_declaration': declaration})
                store = RecordingStore(root)
                with self.assertRaisesRegex(ValueError, 'model_version_declaration'):
                    experiment_registry.register_experiment(store, str(report), model_version='v1')
                self.assertEqual(store.puts, [])

    def test_duplicate_model_or_dataset_keeps_old_error_and_zero_new_puts(self):
        for kind, identifier in (('models', 'fixture_model'), ('datasets', 'fixture_dataset')):
            for explicit in (False, True):
                with tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary); report, _ = self.fixture(root); store = RecordingStore(root)
                    store.put(kind, {'id': identifier, 'unchanged': True}); store.puts.clear()
                    before = self.stored_bytes(store)
                    kwargs = {'model_version': 'v1'} if explicit else {}
                    with self.assertRaises(ValueError) as actual:
                        experiment_registry.register_experiment(store, str(report), **kwargs)
                    with self.assertRaises(ValueError) as expected:
                        self.original.register_experiment(store, str(report))
                    self.assertEqual(str(actual.exception), str(expected.exception))
                    self.assertEqual(store.puts, [])
                    self.assertEqual(self.stored_bytes(store), before)

    def test_prior_file_hash_completion_report_and_manifest_errors_win(self):
        for error in ('checkpoint', 'completion', 'training_report', 'manifest'):
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary); report, checkpoint = self.fixture(root); store = RecordingStore(root)
                if error == 'checkpoint': checkpoint.write_bytes(b'changed')
                if error == 'completion':
                    value = json.loads(report.read_text()); value['status'] = 'paused'; report.write_text(json.dumps(value))
                if error == 'training_report': (checkpoint.parent / 'report.json').write_text('{}')
                if error == 'manifest': (root / 'datasets/fixture_dataset/manifest.json').write_text('{}')
                with self.assertRaises(ValueError) as actual:
                    experiment_registry.register_experiment(store, str(report), model_version='latest')
                with self.assertRaises(ValueError) as expected:
                    self.original.register_experiment(store, str(report))
                self.assertEqual(str(actual.exception), str(expected.exception))
                self.assertEqual(store.puts, [])

    def test_second_write_failure_remains_nontransactional_without_model_record(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); report, _ = self.fixture(root); store = RecordingStore(root)
            original_put = store.put
            def fail_model(kind, record):
                if kind == 'models': raise RuntimeError('isolated second write failure')
                return original_put(kind, record)
            with patch.object(store, 'put', side_effect=fail_model), self.assertRaises(RuntimeError):
                experiment_registry.register_experiment(store, str(report), model_version='v1')
            self.assertEqual(len(store.list('datasets')), 1)
            self.assertEqual(store.list('models'), [])
            self.assertNotIn('model_version_declaration', store.list('datasets')[0])

    def test_explicit_parameter_is_keyword_only(self):
        with self.assertRaises(TypeError):
            experiment_registry.register_experiment(None, 'unused', 'v1')
