"""Independent TempStore-only cases; no training or operating calls."""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))
from test_lcluc_workflow import LclucWorkflowTests as Base
from backend.app import lcluc_workflow as w


class Independent(unittest.TestCase):
    setUpClass = classmethod(Base.setUpClass.__func__)
    tearDownClass = classmethod(Base.tearDownClass.__func__)
    setUp, tearDown = Base.setUp, Base.tearDown
    sha, save_checkpoint = Base.sha, Base.save_checkpoint
    gate_reject, update_model = Base.gate_reject, Base.update_model

    def test_declaration_source_is_not_authority_and_must_match_existing_format(self):
        self.model['model_version_declaration']['source'] = 'OFFICIAL_AUTHENTICATED'
        self.update_model()
        self.assertEqual(self.gate_reject()['issue'], 'MODEL_VERSION_NOT_BOUND')

    def test_actual_parent_training_report_bytes_not_only_declared_sha(self):
        (self.model_dir / 'report.json').write_text('changed report', encoding='utf-8')
        self.assertEqual(self.gate_reject()['issue'], 'TRAINING_REPORT_MISMATCH')

    def test_quality_report_byte_change_blocks_before_claim(self):
        (self.root / 'quality-2020.json').write_text('changed quality', encoding='utf-8')
        self.assertEqual(self.gate_reject()['issue'], 'QUALITY_REPORT_MISMATCH')

    def test_model_key_and_body_identity_disagreement_blocks(self):
        corrupted = {**self.model, 'id': 'different-model'}
        with self.store.connect() as connection:
            connection.execute('UPDATE records SET body=? WHERE kind=? AND id=?',
                               (json.dumps(corrupted), 'models', self.model['id']))
        self.assertEqual(self.gate_reject()['issue'], 'MODEL_IDENTITY_MISMATCH')

    def test_metadata_change_between_real_admission_passes_is_failed_no_retry(self):
        original = w._gate
        count = 0
        def change_after_first(*args):
            nonlocal count
            value = original(*args)
            count += 1
            if count == 1:
                self.model['evaluation']['reviewer'] = 'changed reviewer'
                self.update_model()
            return value
        runner = unittest.mock.Mock(side_effect=AssertionError('runner forbidden'))
        with patch.object(w, '_gate', side_effect=change_after_first):
            result = w.execute_lcluc_workflow(self.store, self.request, _runner=runner)
        self.assertEqual(result['status'], 'FAILED')
        self.assertEqual(result['issue'], 'ADMISSION_CHANGED_AFTER_CLAIM')
        replay = w.execute_lcluc_workflow(self.store, self.request, _runner=runner)
        self.assertTrue(replay['replayed'])
        runner.assert_not_called()
        self.assertFalse((self.root / 'results').exists())

    def test_orphan_running_is_historical_observation_not_new_approval(self):
        _, digest = w._request(copy.deepcopy(self.request))
        identifier = w.hashlib.sha256(self.request['idempotency_key'].encode()).hexdigest()
        self.store.put(w.KIND, {'id': identifier, 'request_sha256': digest, 'status': 'RUNNING'})
        with patch.object(w, '_gate', side_effect=AssertionError('no new gate')), \
             patch.object(w, '_output', side_effect=AssertionError('no output')):
            result = w.execute_lcluc_workflow(self.store, self.request)
        self.assertEqual(result['status'], 'RUNNING')
        self.assertTrue(result['replayed'])

    def test_model_explicit_synthetic_kind_is_rejected_even_with_false_flag(self):
        self.update_model(reference_kind=' Synthetic_fixture_only ')
        self.assertEqual(self.gate_reject()['issue'], 'SYNTHETIC_MODEL_BLOCKED')


if __name__ == '__main__':
    suite = unittest.TestSuite((unittest.defaultTestLoader.loadTestsFromTestCase(Base),
                               unittest.defaultTestLoader.loadTestsFromTestCase(Independent)))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(not result.wasSuccessful())
