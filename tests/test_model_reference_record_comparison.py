"""Supplied metadata comparison only; no model resolution or operating writes."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app import model_reference_record_comparison as comparison
from app.experiment_registry import register_experiment
from app.model_registration_provenance import inspect_model_registration_provenance
from app.store import Store
import test_model_registration_provenance as provenance_fixtures
import test_model_version_declaration as registration_fixtures


FLAGS = (*provenance_fixtures.FLAGS, 'model_verified')
KEYS = {'schema_version', 'scope', 'status', 'bindings', 'record_provenance',
        'issue', 'inspection_calls', *FLAGS}


def identity():
    return {'id': 'private-model', 'version': ' v2 ', 'sha256': 'a' * 64}


class ModelReferenceRecordComparisonTests(unittest.TestCase):
    def checked(self, reference, record, status, calls=0, code=None, field=None, side=None):
        result = comparison.compare_model_reference_record(reference, record)
        self.assertEqual(set(result), KEYS)
        self.assertIs(type(result['schema_version']), int)
        self.assertEqual(result['schema_version'], 1)
        self.assertEqual(result['scope'], 'DECLARED_MODEL_IDENTITY_TO_SUPPLIED_RECORD_ONLY')
        self.assertEqual(result['status'], status)
        self.assertEqual(set(result['bindings']), {'id', 'version', 'sha256'})
        self.assertIs(type(result['inspection_calls']), int)
        self.assertEqual(result['inspection_calls'], calls)
        for flag in FLAGS: self.assertIs(result[flag], False)
        if code is None:
            self.assertIsNone(result['issue'])
        else:
            self.assertEqual(result['issue'], {'code': code, 'field': field, 'side': side})
        if calls == 0: self.assertIsNone(result['record_provenance'])
        return result

    def test_exact_three_key_identity_and_full_model_ref_is_not_this_contract(self):
        class Dictionary(dict): pass
        for reference in (None, True, [], 'model', {}, Dictionary(identity()),
                          dict(identity(), role='model'), dict(identity(), uri='file:///private'),
                          {'id': 'm', 'version': 'v1'}):
            result = self.checked(reference, None, 'REFERENCE_INVALID', code='REFERENCE_IDENTITY_INVALID',
                                  field='reference_identity', side='REFERENCE')
            self.assertEqual(set(result['bindings'].values()), {'NOT_CHECKED'})

    def test_reference_text_alias_bounds_and_before_sha_priority(self):
        for field in ('id', 'version'):
            for value in (None, True, 1, '', ' ', '\ud800', 'x\x00', 'x\x7f', 'x\x9f', 'x' * 257):
                reference = identity(); reference[field] = value
                self.checked(reference, None, 'REFERENCE_INVALID', code='MODEL_REFERENCE_INVALID',
                             field='reference_identity', side='REFERENCE')
        for version in ('latest', ' Current '):
            reference = identity(); reference.update(version=version, sha256='bad')
            self.checked(reference, None, 'REFERENCE_INVALID', code='MODEL_VERSION_NOT_PINNED',
                         field='reference_identity', side='REFERENCE')
        reference = identity(); reference.update(id='x' * 256, version='v' * 256)
        self.checked(reference, None, 'RECORD_NOT_PROVIDED', code='RECORD_NOT_PROVIDED',
                     field='model_record', side='RECORD')

    def test_reference_sha_exact_type_lowercase_hex_and_length(self):
        for value in (None, True, 1, '', 'A' * 64, 'g' * 64, 'a' * 63, 'a' * 65, 'a' * 64 + '\n'):
            reference = identity(); reference['sha256'] = value
            self.checked(reference, None, 'REFERENCE_INVALID', code='SHA256_INVALID',
                         field='sha256', side='REFERENCE')

    def test_default_candidate_means_not_provided_not_database_not_found(self):
        with patch.object(comparison, 'inspect_model_registration_provenance', side_effect=AssertionError('no inspection')):
            result = comparison.compare_model_reference_record(identity())
            self.assertEqual(result, self.checked(identity(), None, 'RECORD_NOT_PROVIDED',
                code='RECORD_NOT_PROVIDED', field='model_record', side='RECORD'))
        self.assertEqual(set(result['bindings'].values()), {'NOT_CHECKED'})

    def test_candidate_type_or_invalid_id_does_not_inspect(self):
        class Dictionary(dict): pass
        with patch.object(comparison, 'inspect_model_registration_provenance', side_effect=AssertionError('no inspection')):
            for record in (True, [], 'model', Dictionary(id='private-model')):
                self.checked(identity(), record, 'RECORD_INVALID', code='RECORD_INVALID', field='model_record', side='RECORD')
            for model_id in (None, True, 1, '', ' ', '\ud800', 'x\x00', 'x' * 257):
                result = self.checked(identity(), {'id': model_id}, 'RECORD_INVALID',
                    code='MODEL_REFERENCE_INVALID', field='id', side='RECORD')
                self.assertEqual(set(result['bindings'].values()), {'NOT_CHECKED'})

    def test_valid_different_id_does_not_inspect_even_bad_declaration(self):
        record = {'id': 'other-model', 'model_version_declaration': None}
        with patch.object(comparison, 'inspect_model_registration_provenance', side_effect=AssertionError('no inspection')):
            result = self.checked(identity(), record, 'REFERENCE_CONFLICT', code='ID_MISMATCH', field='id', side='COMPARISON')
        self.assertEqual(result['bindings'], dict(id='MISMATCH', version='NOT_CHECKED', sha256='NOT_CHECKED'))

    def test_same_id_inspects_once_and_embeds_each_noncomparable_intrinsic_state(self):
        cases = [{'id': 'private-model'}, dict(provenance_fixtures.fixture(), model_version_declaration=None)]
        conflict = provenance_fixtures.fixture(); conflict['training_report_sha256'] = 'c' * 64; cases.append(conflict)
        missing = provenance_fixtures.fixture(); del missing['checkpoint_sha256']; cases.append(missing)
        for record in cases:
            with patch.object(comparison, 'inspect_model_registration_provenance', wraps=inspect_model_registration_provenance) as inspect:
                result = self.checked(identity(), record, 'REFERENCE_NOT_COMPARABLE', calls=1,
                    code='REGISTRATION_NOT_COMPARABLE', field='model_version_declaration', side='RECORD')
            inspect.assert_called_once_with(record)
            self.assertEqual(result['record_provenance'], inspect_model_registration_provenance(record))
            self.assertEqual(result['bindings'], dict(id='MATCH', version='NOT_CHECKED', sha256='NOT_CHECKED'))

    def test_consistent_record_match_is_unverified_and_inspects_exactly_once(self):
        record = provenance_fixtures.fixture()
        before = copy.deepcopy(record)
        with patch.object(comparison, 'inspect_model_registration_provenance', wraps=inspect_model_registration_provenance) as inspect:
            result = self.checked(identity(), record, 'MATCH_UNVERIFIED', calls=1)
        inspect.assert_called_once_with(record)
        self.assertEqual(result['bindings'], dict(id='MATCH', version='MATCH', sha256='MATCH'))
        self.assertEqual(result['record_provenance']['status'], 'CONSISTENT_UNVERIFIED')
        self.assertEqual(record, before)

    def test_version_and_checkpoint_comparisons_both_compute_version_issue_first(self):
        for version, sha, code, field in (
            ('different', 'a' * 64, 'VERSION_MISMATCH', 'version'),
            (' v2 ', 'c' * 64, 'CHECKPOINT_SHA256_MISMATCH', 'sha256'),
            ('different', 'c' * 64, 'VERSION_MISMATCH', 'version')):
            reference = identity(); reference.update(version=version, sha256=sha)
            result = self.checked(reference, provenance_fixtures.fixture(), 'REFERENCE_CONFLICT', calls=1,
                                  code=code, field=field, side='COMPARISON')
            self.assertEqual(result['bindings']['version'], 'MATCH' if version == ' v2 ' else 'MISMATCH')
            self.assertEqual(result['bindings']['sha256'], 'MATCH' if sha == 'a' * 64 else 'MISMATCH')

    def test_padding_is_not_normalized_in_id_or_version(self):
        reference = identity(); reference['version'] = 'v2'
        self.checked(reference, provenance_fixtures.fixture(), 'REFERENCE_CONFLICT', calls=1,
                     code='VERSION_MISMATCH', field='version', side='COMPARISON')
        reference = identity(); reference['id'] = ' private-model '
        self.checked(reference, provenance_fixtures.fixture(), 'REFERENCE_CONFLICT',
                     code='ID_MISMATCH', field='id', side='COMPARISON')

    def test_unknown_cycles_dataset_version_approval_and_forgery_are_not_authority(self):
        record = provenance_fixtures.fixture(); record['unknown'] = record
        record.update(dataset_version=provenance_fixtures.Poison(), model_id=provenance_fixtures.Poison(),
                      status='Approved', scientific_accuracy_validated=True, independent_evaluation=True,
                      huge_unknown='x' * 1048576)
        reference = identity(); original_reference = dict(reference)
        declaration_before = dict(record['model_version_declaration'])
        with patch('copy.deepcopy', side_effect=AssertionError('no copying')), \
             patch('json.dumps', side_effect=AssertionError('no serialization')):
            result = self.checked(reference, record, 'MATCH_UNVERIFIED', calls=1)
        self.assertEqual(reference, original_reference)
        self.assertEqual(record['model_version_declaration'], declaration_before)
        self.assertIs(record['unknown'], record)
        encoded = json.dumps(result)
        for private in ('private-model', ' v2 ', 'a' * 64, 'b' * 64): self.assertNotIn(private, encoded)
        for flag in provenance_fixtures.FLAGS: self.assertIs(result['record_provenance'][flag], False)

    def test_no_file_store_network_or_resolution_io(self):
        with patch('builtins.open', side_effect=AssertionError('no file open')), \
             patch.object(Path, 'open', side_effect=AssertionError('no Path.open')), \
             patch.object(Store, 'get', side_effect=AssertionError('no Store.get')), \
             patch.object(Store, 'list', side_effect=AssertionError('no Store.list')), \
             patch.object(Store, 'put', side_effect=AssertionError('no Store.put')), \
             patch('socket.socket', side_effect=AssertionError('no network')):
            self.checked(identity(), provenance_fixtures.fixture(), 'MATCH_UNVERIFIED', calls=1)

    def test_same_id_inspection_exception_propagates_without_fabricated_result(self):
        error = RuntimeError('private-internal-error')
        with patch.object(comparison, 'inspect_model_registration_provenance', side_effect=error) as inspect:
            with self.assertRaises(RuntimeError) as caught:
                comparison.compare_model_reference_record(identity(), provenance_fixtures.fixture())
        self.assertIs(caught.exception, error)
        self.assertEqual(inspect.call_count, 1)

    def test_tiny_registered_record_matches_but_later_file_tampering_is_unobserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); files = registration_fixtures.ModelVersionDeclarationTests()
            report, checkpoint = files.fixture(root); store = Store(root)
            record = register_experiment(store, str(report), model_version=' caller-model-v3 ')['model']
            reference = dict(id=record['id'], version=' caller-model-v3 ', sha256=record['checkpoint_sha256'])
            before = files.stored_bytes(store)
            self.checked(reference, record, 'MATCH_UNVERIFIED', calls=1)
            checkpoint.write_bytes(b'changed-after-registration')
            self.checked(reference, record, 'MATCH_UNVERIFIED', calls=1)
            self.assertEqual(files.stored_bytes(store), before)
