"""Pure consistency observations and tiny TempStore registration integration."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.model_registration_provenance import inspect_model_registration_provenance as inspect
from app.experiment_registry import register_experiment
from app.store import Store
import test_model_version_declaration as registration_fixtures


HASH_FIELDS = ('checkpoint_sha256', 'training_report_sha256')
FLAGS = ('authority_verified', 'artifact_bytes_verified', 'execution_authorized',
         'scientific_accuracy_validated')
KEYS = {'schema_version', 'scope', 'status', 'declaration_present', 'bindings', 'issue', *FLAGS}


def fixture():
    declaration = dict(schema_version=1, source='CALLER_EXPLICIT_REGISTRATION',
        version=' v2 ', checkpoint_sha256='a' * 64, training_report_sha256='b' * 64)
    return dict(id='private-model', checkpoint_sha256='a' * 64,
        training_report_sha256='b' * 64, model_version_declaration=declaration)


class Poison:
    def __repr__(self): raise AssertionError('unknown value must not be inspected')
    def __iter__(self): raise AssertionError('unknown value must not be traversed')
    def __eq__(self, value): raise AssertionError('unknown value must not be compared')


class ModelRegistrationProvenanceTests(unittest.TestCase):
    def checked(self, record, status, field=None):
        value = inspect(record)
        self.assertEqual(set(value), KEYS)
        self.assertIs(type(value['schema_version']), int)
        self.assertEqual(value['schema_version'], 1)
        self.assertEqual(value['scope'], 'LOCAL_MODEL_REGISTRATION_METADATA_OBSERVATION_ONLY')
        self.assertEqual(value['status'], status)
        self.assertEqual(set(value['bindings']), {*HASH_FIELDS, 'model_version'})
        for flag in FLAGS: self.assertIs(value[flag], False)
        if status in ('INVALID', 'ABSENT'):
            self.assertEqual(set(value['bindings'].values()), {'NOT_CHECKED'})
        if field is not None:
            self.assertEqual(set(value['issue']), {'code', 'field'})
            self.assertEqual(value['issue']['field'], field)
        else:
            self.assertIsNone(value['issue'])
        return value

    def test_exact_record_and_id_boundary_precede_absence(self):
        class Dictionary(dict): pass
        for record in (None, [], True, 1, Dictionary(id='m')):
            result = self.checked(record, 'INVALID', 'record')
            self.assertIsNone(result['declaration_present'])
        for value in (None, True, 1, '', ' ', '\ud800', 'x\x00', 'a' * 257):
            result = self.checked({'id': value}, 'INVALID', 'id')
            self.assertIs(result['declaration_present'], False)
        self.checked({'id': 'a' * 256}, 'ABSENT')

    def test_absent_does_not_validate_optional_parent_fields_or_infer_dataset_version(self):
        result = self.checked({'id': 'm', 'checkpoint_sha256': None,
            'training_report_sha256': True, 'model_version': 'latest',
            'dataset_version': Poison(), 'model_id': Poison()}, 'ABSENT')
        self.assertIs(result['declaration_present'], False)
        self.checked({'id': 'm', 'model_version_declaration': None}, 'INVALID', 'model_version_declaration')

    def test_exact_declaration_shape_schema_source_and_types(self):
        record = fixture()
        for declaration in (None, True, [], {}, dict(record['model_version_declaration'], extra=True)):
            changed = copy.deepcopy(record); changed['model_version_declaration'] = declaration
            self.checked(changed, 'INVALID', 'model_version_declaration')
        for field, values in (('schema_version', (None, True, '1', 1.0, 2)),
                              ('source', (None, True, 'unknown', 'caller_explicit_registration'))):
            for value in values:
                changed = copy.deepcopy(record); changed['model_version_declaration'][field] = value
                self.checked(changed, 'INVALID', 'model_version_declaration.' + field)

    def test_declaration_version_uses_shared_text_alias_and_raw_padding_contract(self):
        for version in (None, True, 1, '', ' ', 'LATEST', ' Current ', '\ud800', 'x\x9f', 'a' * 257):
            record = fixture(); record['model_version_declaration']['version'] = version
            self.checked(record, 'INVALID', 'model_version_declaration.version')
        for version in ('v1', ' v1 ', 'a' * 256):
            record = fixture(); record['model_version_declaration']['version'] = version
            self.checked(record, 'CONSISTENT_UNVERIFIED')
            self.assertEqual(record['model_version_declaration']['version'], version)

    def test_declaration_and_parent_hash_format_errors_are_invalid(self):
        for field in HASH_FIELDS:
            for value in (None, True, 1, '', 'A' * 64, 'g' * 64, 'a' * 63, 'a' * 65):
                record = fixture(); record['model_version_declaration'][field] = value
                self.checked(record, 'INVALID', 'model_version_declaration.' + field)
                record = fixture(); record[field] = value
                self.checked(record, 'INVALID', field)

    def test_optional_top_version_invalid_match_and_exact_padding_conflict(self):
        for value in (None, True, '', 'latest', 'x\x00', '\ud800', 'a' * 257):
            record = fixture(); record['model_version'] = value
            self.checked(record, 'INVALID', 'model_version')
        record = fixture(); record['model_version'] = ' v2 '
        result = self.checked(record, 'CONSISTENT_UNVERIFIED')
        self.assertEqual(result['bindings']['model_version'], 'MATCH')
        record['model_version'] = 'v2'
        self.checked(record, 'RECORD_CONFLICT', 'model_version')

    def test_parent_missing_is_unknown_optional_top_version_is_not_recorded(self):
        record = fixture(); del record['checkpoint_sha256']
        result = self.checked(record, 'PARENT_BINDING_UNKNOWN', 'checkpoint_sha256')
        self.assertEqual(result['bindings'], dict(checkpoint_sha256='MISSING',
            training_report_sha256='MATCH', model_version='NOT_RECORDED'))
        record = fixture(); del record['training_report_sha256']
        self.checked(record, 'PARENT_BINDING_UNKNOWN', 'training_report_sha256')
        del record['checkpoint_sha256']
        self.checked(record, 'PARENT_BINDING_UNKNOWN', 'checkpoint_sha256')

    def test_format_then_conflict_then_missing_and_fixed_field_order(self):
        record = fixture(); record['checkpoint_sha256'] = 'c' * 64; record['training_report_sha256'] = None
        self.checked(record, 'INVALID', 'training_report_sha256')
        record = fixture(); record['checkpoint_sha256'] = 'c' * 64; record['model_version'] = None
        self.checked(record, 'INVALID', 'model_version')
        record = fixture(); record['checkpoint_sha256'] = 'c' * 64; del record['training_report_sha256']
        result = self.checked(record, 'RECORD_CONFLICT', 'checkpoint_sha256')
        self.assertEqual(result['bindings']['training_report_sha256'], 'MISSING')
        record = fixture(); del record['checkpoint_sha256']; record['training_report_sha256'] = 'c' * 64
        self.checked(record, 'RECORD_CONFLICT', 'training_report_sha256')
        record = fixture(); del record['checkpoint_sha256']; del record['training_report_sha256']; record['model_version'] = 'other'
        self.checked(record, 'RECORD_CONFLICT', 'model_version')
        record = fixture(); record.update(checkpoint_sha256='c' * 64, training_report_sha256='d' * 64, model_version='other')
        self.checked(record, 'RECORD_CONFLICT', 'checkpoint_sha256')

    def test_consistency_and_forged_metadata_never_authenticate_or_echo_values(self):
        record = fixture(); before = copy.deepcopy(record)
        first = self.checked(record, 'CONSISTENT_UNVERIFIED')
        forged = copy.deepcopy(record)
        forged.update(status='Approved', independent_evaluation=True, scientific_accuracy_validated=True,
                      dataset_version='arbitrary', checkpoint_path='file:///private-checkpoint')
        second = self.checked(forged, 'CONSISTENT_UNVERIFIED')
        self.assertEqual(first, second)
        self.assertEqual(record, before)
        self.assertIs(first['declaration_present'], True)
        encoded = json.dumps(first)
        for secret in ('private-model', 'file:///private', ' v2 ', 'a' * 64, 'b' * 64):
            self.assertNotIn(secret, encoded)

    def test_unknown_cycles_large_values_are_not_walked_copied_or_serialized(self):
        record = fixture(); record['unknown'] = record
        record['dataset_version'] = Poison(); record['model_id'] = Poison()
        record['huge_unknown'] = 'x' * 1048576
        declaration_before = dict(record['model_version_declaration'])
        with patch('copy.deepcopy', side_effect=AssertionError('no copy')), \
             patch('json.dumps', side_effect=AssertionError('no serialization')):
            self.checked(record, 'CONSISTENT_UNVERIFIED')
        self.assertIs(record['unknown'], record)
        self.assertEqual(record['model_version_declaration'], declaration_before)

    def test_no_store_file_network_or_resolver_io(self):
        with patch('builtins.open', side_effect=AssertionError('no file open')), \
             patch.object(Path, 'open', side_effect=AssertionError('no Path.open')), \
             patch.object(Store, 'get', side_effect=AssertionError('no Store.get')), \
             patch.object(Store, 'list', side_effect=AssertionError('no Store.list')), \
             patch.object(Store, 'put', side_effect=AssertionError('no Store.put')), \
             patch('socket.socket', side_effect=AssertionError('no network')):
            self.checked(fixture(), 'CONSISTENT_UNVERIFIED')

    def test_tempstore_explicit_registration_connects_without_granting_authority(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            files = registration_fixtures.ModelVersionDeclarationTests()
            report, checkpoint = files.fixture(root)
            store = Store(root)
            registered = register_experiment(store, str(report), model_version=' caller-v3 ')
            before = files.stored_bytes(store)
            self.checked(registered['model'], 'CONSISTENT_UNVERIFIED')
            checkpoint.write_bytes(b'changed-after-registration')
            self.checked(registered['model'], 'CONSISTENT_UNVERIFIED')
            self.assertEqual(files.stored_bytes(store), before)
