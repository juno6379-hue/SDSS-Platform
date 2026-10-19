"""Explicit registration in initialized temporary Stores, never operating data."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.data import quality_report_registration as api
from app.dataset_registry import register_version, version_key
from app.ml.registered_binary_mask_values import inspect_registered_binary_mask_values
from app.store import Store
import test_quality_report_storage as fixtures


class QualityReportRegistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.QualityReportStorageTests.setUpClass()
        cls.addClassCleanup(fixtures.QualityReportStorageTests.doClassCleanups)

    def setUp(self):
        self.fixture = fixtures.QualityReportStorageTests(); self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root; self.f = self.fixture.fixture; self.sidecar = self.fixture.sidecar
        self.f.image['quality_report_ref'] = self.f.identity['artifact_uri']
        self.store = Store(self.root)  # Caller-owned explicit initialization; not the adapter.
        for value in (self.f.image,self.f.mask): register_version(self.store,value)
        self.assertEqual(self.fixture.write()['status'],'FILES_WRITTEN_UNREGISTERED')

    def register(self,store=None,root=None):
        return api.register_stored_quality_report(self.store if store is None else store,self.root if root is None else root,
            self.f.image,self.f.mask,self.f.identity,self.f.metadata,self.sidecar)

    def snapshot(self):
        return {p.name:p.read_bytes() for p in self.root.iterdir() if p.is_file()}

    def test_actual_report_insert_exact22_sources_unchanged_then_readonly_consumer(self):
        files = self.snapshot(); before = copy.deepcopy(self.store.list('dataset_versions'))
        with (patch.object(api,'register_version',wraps=api.register_version) as insert,
              patch.object(api,'resolve_version',wraps=api.resolve_version) as resolve,
              patch.object(api,'inspect_stored_quality_report',wraps=api.inspect_stored_quality_report) as preflight,
              patch.object(Store,'__init__',side_effect=AssertionError('no new Store'))):
            result = self.register()
        self.assertEqual(len(result),22); self.assertEqual(result['status'],'REPORT_REGISTERED_UNAPPROVED')
        self.assertTrue(result['registry_registered']); self.assertTrue(result['registry_outcome_verified'])
        self.assertTrue(result['registration_attempted']); self.assertTrue(result['source_dataset_refs_verified'])
        self.assertTrue(result['stored_report_files_verified']); self.assertTrue(result['manifest_schema_verified'])
        self.assertTrue(all(result[k] is False for k in api.FALSE_FIELDS if k != 'registry_registered'))
        insert.assert_called_once(); preflight.assert_called_once(); self.assertEqual(resolve.call_count,2)
        self.assertEqual(insert.call_args.args[1]['data_type'],'document')
        for record in before: self.assertEqual(self.store.get('dataset_versions',record['id']),record)
        after = self.snapshot()
        self.assertEqual({k:v for k,v in files.items() if k != 'catalog.sqlite3'},{k:v for k,v in after.items() if k != 'catalog.sqlite3'})
        self.assertEqual(len(self.store.list('dataset_versions')),3)
        refs = result['fixed_refs']; before_read = self.snapshot()
        observed = inspect_registered_binary_mask_values(self.store,refs['image_ref'],refs['quality_report_ref'],refs['mask_ref'])
        self.assertEqual(observed['status'],'REGISTERED_BINARY_MASK_VALUES_MATCHED_UNVERIFIED')
        self.assertEqual(observed['counts'],{'valid_pixels':0,'invalid_pixels':256,'total_pixels':256})
        self.assertEqual(self.snapshot(),before_read)

    def test_replay_same_record_same_registered_at_database_and_files_unchanged(self):
        first = self.register(); before = self.snapshot(); second = self.register()
        self.assertEqual(second,first); self.assertEqual(self.snapshot(),before)
        self.assertEqual(first['registration_record']['registered_at'],second['registration_record']['registered_at'])

    def test_missing_db_root_mismatch_and_nonexact_store_zero_connect_register(self):
        self.store.db.unlink()
        with patch.object(Store,'connect',side_effect=AssertionError('no connect')),patch.object(api,'register_version') as insert:
            result = self.register()
        self.assertEqual(result['issue']['code'],'STORE_DB_UNAVAILABLE'); self.assertFalse(self.store.db.exists()); insert.assert_not_called()
        with tempfile.TemporaryDirectory() as name:
            with patch.object(api,'register_version') as insert: result = self.register(root=Path(name).resolve())
            self.assertEqual(result['issue']['code'],'STORE_ROOT_MISMATCH'); insert.assert_not_called()
        class Other: pass
        self.assertEqual(self.register(store=Other())['issue']['code'],'STORE_INVALID')

    def test_missing_source_or_native_bytes_changed_no_registration_attempt(self):
        key = version_key(self.f.mask['dataset_id'],self.f.mask['version'])
        with self.store.connect() as conn: conn.execute('DELETE FROM records WHERE kind=? AND id=?',('dataset_versions',key))
        with patch.object(api,'register_version') as insert: result = self.register()
        self.assertEqual(result['issue']['code'],'SOURCE_DATASET_BINDING_FAILED'); self.assertFalse(result['registration_attempted']); insert.assert_not_called()
        register_version(self.store,self.f.mask)
        (self.root/self.f.mask['artifact_uri']).write_bytes(b'TAMPERED_MASK')
        with patch.object(api,'register_version') as insert: result = self.register()
        self.assertFalse(result['registration_attempted']); self.assertFalse(result['source_dataset_refs_verified']); insert.assert_not_called()

    def test_caller_manifest_mismatch_and_untrusted_resolve_records_no_insert(self):
        self.f.image['source']['license'] = 'CALLER_CHANGED_ONLY'
        with patch.object(api,'register_version') as insert: result = self.register()
        self.assertEqual(result['issue']['code'],'SOURCE_DATASET_BINDING_FAILED'); insert.assert_not_called()
        self.f.image['source']['license'] = self.store.get('dataset_versions',version_key(self.f.image['dataset_id'],self.f.image['version']))['manifest']['source']['license']
        original = api.resolve_version
        def poison(*args):
            record = original(*args); record['scientific_accuracy_validated'] = 0; return record
        with patch.object(api,'resolve_version',side_effect=poison),patch.object(api,'register_version') as insert:
            self.assertFalse(self.register()['registration_attempted']); insert.assert_not_called()

    def test_bad_preflight_and_mutation_after_validation_uses_expected_snapshot(self):
        original = api.inspect_stored_quality_report
        def poison(*args):
            value = original(*args); value['manifest_schema_verified'] = 1; return value
        with patch.object(api,'inspect_stored_quality_report',side_effect=poison),patch.object(api,'resolve_version') as resolve:
            result = self.register()
        self.assertEqual(result['issue']['code'],'STORED_REPORT_PREFLIGHT_FAILED'); resolve.assert_not_called()
        producer = original(self.root,self.f.image,self.f.mask,self.f.identity,self.f.metadata,self.sidecar)
        original_same = api._same
        def mutate(actual,expected):
            equal = original_same(actual,expected)
            if actual is producer: producer['report_manifest_draft']['source']['product'] = 'POISON_AFTER_CHECK'
            return equal
        with patch.object(api,'inspect_stored_quality_report',return_value=producer),patch.object(api,'_same',side_effect=mutate):
            result = self.register()
        self.assertEqual(result['status'],'REPORT_REGISTERED_UNAPPROVED')
        self.assertNotEqual(result['registration_record']['manifest']['source']['product'],'POISON_AFTER_CHECK')

    def test_conflicting_same_report_version_preserved_outcome_unconfirmed(self):
        report = api.inspect_stored_quality_report(self.root,self.f.image,self.f.mask,self.f.identity,self.f.metadata,self.sidecar)['report_manifest_draft']
        report['source']['product'] = 'EXISTING_DIFFERENT_REPORT_DECLARATION'
        existing = register_version(self.store,report); before = self.snapshot()
        result = self.register()
        self.assertEqual(result['status'],'REGISTRATION_OUTCOME_UNCONFIRMED'); self.assertTrue(result['registration_attempted'])
        self.assertFalse(result['registry_registered']); self.assertIsNone(result['registration_record'])
        self.assertEqual(self.store.get('dataset_versions',existing['id']),existing); self.assertEqual(self.snapshot(),before)

    def test_post_commit_exception_preserves_inserted_row_no_retry_or_false_rollback(self):
        original = api.register_version; calls = []
        def commit_then_fail(*args):
            calls.append(1); original(*args); raise RuntimeError('PRIVATE_PATH_SECRET')
        with patch.object(api,'register_version',side_effect=commit_then_fail): result = self.register()
        self.assertEqual(calls,[1]); self.assertEqual(result['status'],'REGISTRATION_OUTCOME_UNCONFIRMED')
        self.assertTrue(result['registration_attempted']); self.assertFalse(result['registry_outcome_verified'])
        self.assertEqual(len(self.store.list('dataset_versions')),3); self.assertNotIn('PRIVATE_PATH_SECRET',str(result))

    def test_register_return_invalid_and_readback_failure_after_real_commit(self):
        original = api.register_version
        def poison(*args):
            record = original(*args); record['deployment_approval'] = 0; return record
        with patch.object(api,'register_version',side_effect=poison): result = self.register()
        self.assertEqual(result['status'],'REGISTRATION_OUTCOME_UNCONFIRMED'); self.assertEqual(len(self.store.list('dataset_versions')),3)
        original_get = Store.get; report_key = version_key(self.f.identity['id'],self.f.identity['version'])
        def no_readback(store,kind,key):
            if key == report_key: raise RuntimeError('SECRET_READBACK')
            return original_get(store,kind,key)
        with patch.object(Store,'get',no_readback): result = self.register()
        self.assertEqual(result['status'],'REGISTRATION_OUTCOME_UNCONFIRMED'); self.assertIsNone(result['registration_record'])
        self.assertNotIn('SECRET_READBACK',str(result))

    def test_root_retarget_between_source_resolves_blocked_before_register(self):
        original = api.resolve_version; calls = []
        def retarget(*args):
            record = original(*args); calls.append(1)
            if len(calls) == 2: self.store.db = self.root/'not-the-catalog.sqlite3'
            return record
        with patch.object(api,'resolve_version',side_effect=retarget),patch.object(api,'register_version') as insert:
            result = self.register()
        self.assertEqual(result['issue']['code'],'STORE_ROOT_MISMATCH'); self.assertFalse(result['registration_attempted']); insert.assert_not_called()
        self.assertFalse((self.root/'not-the-catalog.sqlite3').exists())


if __name__ == '__main__': unittest.main()
