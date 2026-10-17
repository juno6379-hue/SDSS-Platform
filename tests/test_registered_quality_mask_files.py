"""Temporary registered declarations and opaque bytes; no raster/model execution."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.dataset_registry import canonical_manifest, version_key
from app.store import Store
from app.ml import registered_quality_mask_files as api


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class RegisteredQualityMaskFilesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve(); self.store = Store(self.root)
        self.paths = [self.root / name for name in ('image.bin', 'quality.json', 'mask.bin')]
        self.paths[0].write_bytes(b'opaque image'); self.paths[2].write_bytes(b'opaque mask')
        self.refs = [{'id': name, 'version': ' v1 ', 'sha256': sha(path.read_bytes()) if path.exists() else '0' * 64}
            for name, path in zip(('image', 'quality', 'mask'), self.paths)]
        self.envelope = {'schema_version': 1, 'scope': 'LCLUC_QUALITY_MASK_EVIDENCE',
            'image_ref': dict(self.refs[0]), 'mask_ref': dict(self.refs[2]), 'quality_status': 'RAW'}
        self.paths[1].write_text(json.dumps(self.envelope), encoding='utf-8')
        self.refs[1]['sha256'] = sha(self.paths[1].read_bytes())
        self.manifests = []
        for ref, path, kind in zip(self.refs, self.paths, ('raster', 'document', 'raster')):
            self.manifests.append({'schema_version': '0.2.0', 'dataset_id': ref['id'], 'version': ref['version'],
                'source': {'institution': 'TEST_ONLY', 'product': 'fixture', 'license': 'fixture'},
                'data_type': kind, 'spatial': {'bbox': [100, -10, 110, 0], 'crs': 'EPSG:4326'},
                'temporal': {'start': '2020-01-01T00:00:00Z', 'end': '2020-12-31T00:00:00Z', 'calendar': 'gregorian'},
                'quality_status': 'RAW', 'access_class': 'PUBLIC', 'sha256': ref['sha256'],
                'artifact_uri': path.name, 'lineage': []})
        self.manifests[0]['quality_report_ref'] = self.paths[1].name
        self.manifests[1]['lineage'] = [{**self.refs[0], 'role': 'quality_input_image'},
            {**self.refs[2], 'role': 'quality_input_mask'}]
        for i in range(3): self.save(i)

    def save(self, i):
        manifest, digest = canonical_manifest(self.manifests[i])
        self.store.put('dataset_versions', {'id': version_key(manifest['dataset_id'], manifest['version']),
            'manifest': manifest, 'manifest_sha256': digest})

    def report(self, raw=None):
        self.paths[1].write_bytes(json.dumps(self.envelope).encode() if raw is None else raw)
        self.refs[1]['sha256'] = sha(self.paths[1].read_bytes())
        self.manifests[1]['sha256'] = self.refs[1]['sha256']; self.save(1)

    def read(self, refs=None):
        return api.read_registered_quality_mask_files(self.store, *(self.refs if refs is None else refs))

    def test_exact18_three_get_no_writes_no_resolver_and_opaque_mask_not_qa(self):
        before = copy.deepcopy(self.refs)
        with (patch.object(self.store, 'get', wraps=self.store.get) as get,
              patch.object(self.store, 'put', side_effect=AssertionError('write')),
              patch('app.dataset_registry.resolve_version', side_effect=AssertionError('resolve')),
              patch('app.dataset_registry.verify_artifact', side_effect=AssertionError('unbounded'))):
            result = self.read()
        self.assertEqual(get.call_count, 3); self.assertEqual(len(result), 18)
        self.assertEqual(result['status'], 'REGISTERED_QUALITY_MASK_MATCHED_UNVERIFIED')
        self.assertTrue(result['artifact_bytes_verified']); self.assertTrue(result['report_bindings_verified'])
        self.assertEqual([v['status'] for v in result['file_bindings']], ['MATCH'] * 3)
        self.assertTrue(all(result[key] is False for key in api.FALSE_FIELDS)); self.assertEqual(self.refs, before)

    def test_all_quality_states_are_declarations_only(self):
        for quality in ('RAW', 'STAGED', 'STANDARDIZED', 'VALIDATED', 'REJECTED'):
            self.manifests[0]['quality_status'] = quality; self.save(0)
            self.envelope['quality_status'] = quality; self.report()
            result = self.read(); self.assertTrue(result['artifact_bytes_verified'])
            self.assertFalse(result['quality_report_verified']); self.assertFalse(result['quality_mask_verified'])

    def test_invalid_refs_no_store_and_snapshot_before_get(self):
        for value in (None, True, {}, {**self.refs[0], 'version': 'latest'}, {**self.refs[0], 'sha256': 'A'*64}):
            with patch.object(self.store, 'get', side_effect=AssertionError('no IO')):
                self.assertEqual(self.read([value, self.refs[1], self.refs[2]])['issue']['code'], 'INVALID_INPUT')
        with patch.object(self.store, 'get', side_effect=AssertionError('no IO')):
            self.assertEqual(self.read([self.refs[0]]*3)['issue']['code'], 'INVALID_INPUT')
        original = self.store.get
        def mutate(*args):
            self.refs[2]['sha256'] = '0'*64
            return original(*args)
        with patch.object(self.store, 'get', side_effect=mutate):
            self.assertTrue(self.read()['artifact_bytes_verified'])

    def test_all_three_registry_types_public_and_pin_checked_before_files(self):
        for i in range(3):
            for key, value, code in (('access_class', 'RESTRICTED', 'ACCESS_DECLARATION_BLOCKED'),
                                     ('data_type', 'table', 'REGISTRY_TYPE_MISMATCH'),
                                     ('sha256', '0'*64, 'REGISTRY_REFERENCE_CONFLICT')):
                old = self.manifests[i][key]; self.manifests[i][key] = value; self.save(i)
                with patch.object(api, '_snapshot', side_effect=AssertionError('file before gate')):
                    self.assertEqual(self.read()['issue']['code'], code)
                self.manifests[i][key] = old; self.save(i)

    def test_lineage_exact_one_and_other_parent_not_resolved(self):
        original = copy.deepcopy(self.manifests[1]['lineage'])
        for parents in ([], original + [original[0]], [{**original[0], 'sha256': '0'*64}, original[1]]):
            self.manifests[1]['lineage'] = parents; self.save(1)
            with patch.object(api, '_snapshot', side_effect=AssertionError('early')):
                result = self.read()
            self.assertEqual(result['issue']['code'], 'LINEAGE_BINDING_INVALID')
            self.assertTrue(result['registry_references_verified'])
        self.manifests[1]['lineage'] = original + [{'id':'other','version':'v1','sha256':'0'*64,'role':'unresolved'}]
        self.save(1); self.assertTrue(self.read()['artifact_bytes_verified'])

    def test_report_path_is_registered_not_guessed_and_normalized(self):
        for value in (None, '../quality.json', 'other.json', 'https://secret/report'):
            self.manifests[0]['quality_report_ref'] = value
            if value is None: del self.manifests[0]['quality_report_ref']
            self.save(0)
            result = self.read(); self.assertFalse(result['artifact_bytes_verified'])
            self.assertFalse(result['report_bindings_verified'])
        self.manifests[0]['quality_report_ref'] = 'quality.json'; self.save(0)
        self.assertTrue(self.read()['artifact_bytes_verified'])

    def test_exact_envelope_and_strict_json_not_legacy_or_command(self):
        original = copy.deepcopy(self.envelope)
        for envelope in ({}, {'pass': []}, {**original, 'command': 'execute'}, {**original, 'schema_version': True},
                         {**original, 'scope': 'other'}):
            self.envelope = envelope; self.report(); result = self.read()
            self.assertFalse(result['report_bindings_verified']); self.assertEqual(result['file_bindings'][1]['status'], 'MATCH')
        for raw in (b'{"schema_version":1,"schema_version":1}', b'{"a":NaN}', b'{"a":1e999}', b'{"a":"\\ud800"}'):
            self.report(raw); result = self.read()
            self.assertFalse(result['report_bindings_verified'])
            self.assertEqual(result['issue']['field'], 'quality_report')
        deep = {}
        for _ in range(18): deep = {'nested': deep}
        self.report(json.dumps(deep).encode())
        self.assertEqual(self.read()['issue']['field'], 'quality_report')

    def test_report_bindings_exact_pins_and_quality(self):
        for key, value in (('image_ref', {**self.refs[0], 'sha256': '0'*64}),
                           ('mask_ref', {**self.refs[2], 'version': 'v2'}), ('quality_status', 'VALIDATED')):
            old = self.envelope[key]; self.envelope[key] = value; self.report()
            self.assertEqual(self.read()['issue']['code'], 'QUALITY_REPORT_BINDING_MISMATCH')
            self.envelope[key] = old

    def test_three_byte_tampers_and_partial_history(self):
        for i in (1, 0, 2):
            old = self.paths[i].read_bytes(); self.paths[i].write_bytes(b'changed')
            result = self.read(); self.assertFalse(result['artifact_bytes_verified'])
            self.assertEqual(result['issue'], {'code':'SHA256_MISMATCH','field':api.ROLES[i]})
            self.assertEqual(result['report_bindings_verified'], i != 1)
            self.assertTrue(result['registry_references_verified']); self.paths[i].write_bytes(old)

    def test_size_caps_missing_nonregular_escape_and_safe_exception(self):
        for i in (1, 0, 2):
            limits = list(api.MAXIMUMS); limits[i] = 1
            with patch.object(api, 'MAXIMUMS', tuple(limits)):
                self.assertFalse(self.read()['artifact_bytes_verified'])
        self.paths[2].unlink(); self.assertFalse(self.read()['artifact_bytes_verified'])
        self.paths[2].mkdir(); self.assertFalse(self.read()['artifact_bytes_verified'])
        with patch.object(self.store, 'get', side_effect=RuntimeError('SECRET PATH')):
            result = self.read()
        self.assertNotIn('SECRET', json.dumps(result)); self.assertEqual(result['issue']['code'], 'REGISTRY_RECORD_UNAVAILABLE')


if __name__ == '__main__':
    unittest.main()
