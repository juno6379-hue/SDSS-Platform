"""임시 자료로 불변 등록·동시성·고정 참조의 무결성을 확인한다."""
import copy
from concurrent.futures import ThreadPoolExecutor
import hashlib
from pathlib import Path
import tempfile
import unittest

from app.dataset_registry import register_version, resolve_version
from app.store import Store


class DatasetVersionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.store = Store(self.root)
        self.path = self.root / 'contract-fixture.json'
        self.path.write_bytes(b'{"explicit_contract_fixture":true}')
        self.manifest = {
            'schema_version': '0.2.0', 'dataset_id': 'fixture', 'version': '1',
            'source': {'institution': 'contract test', 'product': 'fixture', 'license': 'test only'},
            'data_type': 'document', 'spatial': {'bbox': [106, -7, 107, -6], 'crs': 'OGC:CRS84'},
            'temporal': {'start': '2024-01-01T00:00:00Z', 'end': '2024-12-31T00:00:00Z', 'calendar': 'gregorian'},
            'quality_status': 'RAW', 'access_class': 'RESTRICTED',
            'sha256': hashlib.sha256(self.path.read_bytes()).hexdigest(),
            'artifact_uri': self.path.name, 'lineage': [],
        }

    def tearDown(self):
        self.directory.cleanup()

    def test_idempotent_registration_does_not_modify_other_catalogs(self):
        first = register_version(self.store, self.manifest)
        self.assertEqual(first, register_version(self.store, copy.deepcopy(self.manifest)))
        self.assertEqual(len(self.store.list('dataset_versions')), 1)
        self.assertEqual(self.store.list('datasets'), [])
        self.assertFalse(first['scientific_accuracy_validated'])
        self.assertFalse(first['deployment_approval'])

    def test_existing_version_cannot_be_overwritten(self):
        first = register_version(self.store, self.manifest)
        altered = copy.deepcopy(self.manifest)
        altered['source']['product'] = 'different'
        with self.assertRaisesRegex(ValueError, '새 버전'):
            register_version(self.store, altered)
        self.assertEqual(resolve_version(self.store, 'fixture', '1', self.manifest['sha256']), first)

    def test_distinct_versions_preserve_parent_lineage(self):
        register_version(self.store, self.manifest)
        next_version = dict(self.manifest, version='2', lineage=[{'id': 'fixture', 'version': '1', 'sha256': self.manifest['sha256']}])
        self.assertEqual(register_version(self.store, next_version)['manifest']['lineage'], next_version['lineage'])
        self.assertEqual(len(self.store.list('dataset_versions')), 2)

    def test_wrong_hash_or_changed_file_is_blocked(self):
        register_version(self.store, self.manifest)
        with self.assertRaises(ValueError):
            resolve_version(self.store, 'fixture', '1', 'b' * 64)
        self.path.write_bytes(b'changed')
        with self.assertRaises(ValueError):
            resolve_version(self.store, 'fixture', '1', self.manifest['sha256'])

    def test_dynamic_version_and_lineage_are_blocked(self):
        for value in ('latest', 'current', ' LATEST '):
            with self.subTest(value=value), self.assertRaises(ValueError):
                register_version(self.store, dict(self.manifest, version=value))
        with self.assertRaises(ValueError):
            register_version(self.store, dict(self.manifest, lineage=[{'id': 'parent', 'version': 'latest', 'sha256': 'c' * 64}]))

    def test_schema_spatial_and_temporal_errors_block_registration(self):
        variants = [dict(self.manifest, unknown='no'), dict(self.manifest, spatial={'bbox': [107, -7, 106, -6], 'crs': 'OGC:CRS84'}),
                    dict(self.manifest, spatial={'bbox': [180, -7, 200, -6], 'crs': 'EPSG:4326'}),
                    dict(self.manifest, temporal={**self.manifest['temporal'], 'end': '2023-01-01T00:00:00Z'})]
        for value in variants:
            with self.subTest(value=value), self.assertRaises(ValueError):
                register_version(self.store, value)
        self.assertEqual(self.store.list('dataset_versions'), [])

    def test_remote_unc_and_traversal_are_rejected(self):
        for uri in ('https://example.invalid/fixture', '//server/share/file', '../outside.json'):
            with self.subTest(uri=uri), self.assertRaises(ValueError):
                register_version(self.store, dict(self.manifest, artifact_uri=uri))

    def test_validated_quality_needs_report_but_never_grants_approval(self):
        manifest = dict(self.manifest, quality_status='VALIDATED')
        with self.assertRaises(ValueError):
            register_version(self.store, manifest)
        (self.root / 'quality.json').write_text('{}', encoding='utf-8')
        record = register_version(self.store, dict(manifest, quality_report_ref='quality.json'))
        self.assertFalse(record['scientific_accuracy_validated'])
        self.assertFalse(record['deployment_approval'])

    def test_concurrent_identical_registration_has_one_record(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: register_version(self.store, self.manifest), range(8)))
        self.assertTrue(all(result == results[0] for result in results))
        self.assertEqual(len(self.store.list('dataset_versions')), 1)

    def test_corrupt_stored_manifest_is_rejected_on_resolve(self):
        record = register_version(self.store, self.manifest)
        record['manifest']['source']['product'] = 'tampered'
        self.store.put('dataset_versions', record)
        with self.assertRaises(ValueError):
            resolve_version(self.store, 'fixture', '1', self.manifest['sha256'])

    def test_valid_manifest_from_other_version_cannot_replace_requested_identity(self):
        first = register_version(self.store, self.manifest)
        other = register_version(self.store, dict(self.manifest, dataset_id='other', version='2'))
        first['manifest'] = other['manifest']
        first['manifest_sha256'] = other['manifest_sha256']
        self.store.put('dataset_versions', first)
        with self.assertRaises(ValueError):
            resolve_version(self.store, 'fixture', '1', self.manifest['sha256'])
