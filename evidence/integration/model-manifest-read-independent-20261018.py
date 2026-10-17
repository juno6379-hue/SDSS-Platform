"""Independent Temp checkpoint/record observation; no operating Store or ML run."""
import copy
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
import warnings
import zipfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / '.runtime'), str(ROOT / 'backend')]
import torch
from app.ml.network import TinyUNet
from app.ml import model_checkpoint_manifest as module

SOURCE = ROOT / 'backend/app/ml/model_checkpoint_manifest.py'
FROZEN = 'c62cb01364cc60ab481c16a8b31dfa4d57085f435b1442cb6001ec37325f591d'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == FROZEN
FLAGS = ('state_dict_verified', 'source_authority_verified', 'scientific_accuracy_validated',
         'execution_authorized', 'workflow_supported')


def digest(value): return hashlib.sha256(value).hexdigest()


class Unsupported:
    pass


class ReadStore:
    def __init__(self, root): self.root, self.record, self.calls = root, None, []
    def get(self, kind, key):
        self.calls.append((kind, key))
        if self.record is None: raise KeyError(key)
        return copy.deepcopy(self.record)
    def put(self, *args): raise AssertionError('write forbidden')


class Independent(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='geoai-124-independent-')
        self.root = Path(self.temp.name).resolve()
        self.directory = self.root / 'models' / 'independent_model'
        self.directory.mkdir(parents=True)
        self.store = ReadStore(self.root)
        self.version = '  정규화-고정 α  '
        self.saved = dict(architecture='tiny_unet', manifest=dict(normalization_mode='per_scene_product_metadata',
             bands=[1, 2, 3, 4, 5, 6], band_names=['B02', 'B03', 'B04', 'B08', 'B11', 'B12'],
             synthetic=True, marker='actual checkpoint manifest'), state_dict=TinyUNet(6).state_dict())
        self.save()

    def tearDown(self): self.temp.cleanup()

    def save(self, raw=None, report_override=None):
        if raw is None:
            buffer = io.BytesIO(); torch.save(self.saved, buffer); raw = buffer.getvalue()
        self.raw = raw
        checkpoint_sha = digest(raw)
        report = dict(model_id='independent_model', checkpoint_sha256=checkpoint_sha,
                      training_state='completed', model_version=self.version,
                      input_signature=dict(marker='report copy must not replace checkpoint manifest'))
        if report_override: report.update(report_override)
        report_raw = json.dumps(report, ensure_ascii=False).encode()
        self.report_sha = digest(report_raw)
        (self.directory / 'best.pt').write_bytes(raw)
        (self.directory / 'report.json').write_bytes(report_raw)
        self.ref = dict(id='independent_model', version=self.version, sha256=checkpoint_sha)
        self.store.record = dict(id='independent_model', status='Draft', synthetic=True,
             checkpoint_path=r'models\independent_model\best.pt', checkpoint_sha256=checkpoint_sha,
             training_report_sha256=self.report_sha, model_version_declaration=dict(schema_version=1,
               source='CALLER_EXPLICIT_REGISTRATION', version=self.version,
               checkpoint_sha256=checkpoint_sha, training_report_sha256=self.report_sha))

    def read(self, ref=None):
        result = module.read_pinned_model_checkpoint_manifest(self.store, self.ref if ref is None else ref, self.report_sha)
        self.assertEqual(set(result), {'schema_version', 'scope', 'status', 'issue',
             'registration_observation', 'model_ref', 'training_report_sha256', 'checkpoint_manifest',
             'checkpoint_artifact_verified', 'training_report_artifact_verified', *FLAGS})
        self.assertEqual(result['schema_version'], 1)
        self.assertEqual(result['scope'], 'PINNED_MODEL_CHECKPOINT_MANIFEST_READ_ONLY')
        for flag in FLAGS: self.assertIs(result[flag], False)
        return result

    def blocked(self, value, code, field):
        self.assertEqual(value['status'], 'BLOCKED')
        self.assertEqual(value['issue'], dict(code=code, field=field))

    def test_actual_cpu_weights_only_snapshot_no_inference_or_state_validation(self):
        original = torch.load
        seen = []
        def loader(source, *args, **kwargs):
            self.assertIs(type(source), io.BytesIO)
            self.assertEqual(source.getvalue(), self.raw)
            self.assertEqual(kwargs, dict(map_location='cpu', weights_only=True))
            seen.append(True)
            return original(source, *args, **kwargs)
        before = copy.deepcopy(self.store.record)
        allowlist = list(torch.serialization.get_safe_globals())
        with patch.object(torch, 'load', loader), \
             patch.object(TinyUNet, 'forward', side_effect=AssertionError('inference forbidden')), \
             patch.object(TinyUNet, 'load_state_dict', side_effect=AssertionError('state validation forbidden')):
            result = self.read()
        self.assertEqual(result['status'], 'MANIFEST_BOUND_UNVERIFIED')
        self.assertEqual(result['checkpoint_manifest'], self.saved['manifest'])
        self.assertEqual(result['model_ref']['version'], self.version)
        self.assertEqual(len(seen), 1)
        self.assertIs(result['checkpoint_artifact_verified'], True)
        self.assertIs(result['training_report_artifact_verified'], True)
        self.assertEqual(before, self.store.record)
        self.assertEqual(allowlist, torch.serialization.get_safe_globals())
        result['checkpoint_manifest']['bands'][0] = 99
        self.assertEqual(self.read()['checkpoint_manifest']['bands'][0], 1)

    def test_model_pin_identity_namespace_and_missing(self):
        for key, value in (('id', '../escape'), ('version', 'LATEST'), ('sha256', 'A' * 64)):
            ref = dict(self.ref); ref[key] = value
            before = len(self.store.calls)
            self.blocked(self.read(ref), 'INVALID_INPUT', 'model_ref')
            self.assertEqual(len(self.store.calls), before)
        ref = dict(self.ref); ref['version'] = 'other'
        self.blocked(self.read(ref), 'PIN_CONFLICT', 'model_ref')
        self.store.record['id'] = 'wrong'
        self.blocked(self.read(), 'MODEL_RECORD_INVALID', 'model_record')
        self.store.record = None
        self.blocked(self.read(), 'MODEL_NOT_FOUND', 'model_ref')

    def test_declaration_and_fixed_path_not_inferred(self):
        del self.store.record['model_version_declaration']
        self.blocked(self.read(), 'REGISTRATION_NOT_BOUND', 'model_record')
        self.save(); self.store.record['checkpoint_path'] = 'elsewhere/best.pt'
        self.blocked(self.read(), 'CHECKPOINT_PATH_INVALID', 'checkpoint')

    def test_checkpoint_and_report_hash_tampering_before_load(self):
        (self.directory / 'best.pt').write_bytes(self.raw + b'changed')
        with patch.object(torch, 'load', side_effect=AssertionError('must not load mismatch')):
            result = self.read()
        self.blocked(result, 'SHA256_MISMATCH', 'checkpoint')
        self.assertIs(result['checkpoint_artifact_verified'], False)
        self.save(); (self.directory / 'report.json').write_bytes(b'{}')
        with patch.object(torch, 'load', side_effect=AssertionError('must not load mismatch')):
            result = self.read()
        self.blocked(result, 'SHA256_MISMATCH', 'training_report')
        self.assertIs(result['checkpoint_artifact_verified'], True)
        self.assertIs(result['training_report_artifact_verified'], False)

    def test_report_body_semantics_and_strict_json(self):
        for override in (dict(model_id='different'), dict(checkpoint_sha256='0' * 64),
                         dict(training_state='running'), dict(model_version='other')):
            self.save(report_override=override)
            self.blocked(self.read(), 'TRAINING_REPORT_INVALID', 'training_report')
        self.save()
        raw = b'{"model_id":"independent_model","model_id":"duplicate"}'
        (self.directory / 'report.json').write_bytes(raw)
        self.report_sha = digest(raw)
        self.store.record['training_report_sha256'] = self.report_sha
        self.store.record['model_version_declaration']['training_report_sha256'] = self.report_sha
        self.blocked(self.read(), 'TRAINING_REPORT_INVALID', 'training_report')

    def test_zip_legacy_compressed_duplicate_traversal_and_count_reject_before_load(self):
        variants = [b'legacy-not-zip']
        for mode in ('compressed', 'duplicate', 'traversal', 'too_many', 'no_pickle'):
            output = io.BytesIO()
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', UserWarning)
                with zipfile.ZipFile(output, 'w') as archive:
                    if mode == 'compressed': archive.writestr('archive/data.pkl', b'anything', compress_type=zipfile.ZIP_DEFLATED)
                    elif mode == 'duplicate':
                        archive.writestr('archive/data.pkl', b'a'); archive.writestr('archive/data.pkl', b'b')
                    elif mode == 'traversal': archive.writestr('archive/../data.pkl', b'a')
                    elif mode == 'no_pickle': archive.writestr('archive/version', b'3')
                    else:
                        archive.writestr('archive/data.pkl', b'a')
                        for i in range(512): archive.writestr(f'archive/data/{i}', b'')
            variants.append(output.getvalue())
        for raw in variants:
            self.save(raw)
            with patch.object(torch, 'load', side_effect=AssertionError('invalid archive must not load')):
                self.blocked(self.read(), 'CHECKPOINT_ARCHIVE_INVALID', 'checkpoint')

    def test_unsupported_pickle_no_fallback_or_allowlist_mutation(self):
        self.saved['unapproved_object'] = Unsupported()
        self.save()
        before = list(torch.serialization.get_safe_globals())
        original = torch.load
        calls = []
        def loader(*args, **kwargs):
            calls.append(dict(kwargs)); return original(*args, **kwargs)
        with patch.object(torch, 'load', loader):
            self.blocked(self.read(), 'CHECKPOINT_LOAD_UNAVAILABLE', 'checkpoint')
        self.assertEqual(calls, [dict(map_location='cpu', weights_only=True)])
        self.assertEqual(before, torch.serialization.get_safe_globals())

    def test_manifest_json_limits_and_not_state_dict_compatibility(self):
        for value in (None, [], dict(x=float('nan')), dict(x=float('inf')), dict(x=torch.tensor([1])),
                      dict(x='a' * 4097), dict(x=2 ** 53), dict(x='\ud800')):
            self.saved['manifest'] = value; self.save()
            self.blocked(self.read(), 'MANIFEST_INVALID', 'checkpoint_manifest')
        cycle = {}; cycle['self'] = cycle
        self.saved['manifest'] = cycle; self.save()
        self.blocked(self.read(), 'MANIFEST_INVALID', 'checkpoint_manifest')
        self.saved = dict(architecture='tiny_unet', manifest={})
        self.save()
        result = self.read()
        self.assertEqual(result['status'], 'MANIFEST_BOUND_UNVERIFIED')
        self.assertEqual(result['checkpoint_manifest'], {})
        self.assertIs(result['state_dict_verified'], False)


if __name__ == '__main__':
    begin = time.perf_counter()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Independent))
    elapsed = time.perf_counter() - begin
    baseline = '816515ead72faa53eda2e96a9826748aed0896f7'
    checks = []
    for name in ('backend/app/ml/per_scene_normalization_files.py', 'backend/app/ml/per_scene_normalization_contract.py',
                 'backend/app/lcluc_workflow.py', 'backend/app/ml/service.py', 'backend/app/ml/normalization.py',
                 'backend/app/main.py', 'frontend/src/LclucWorkflowPanel.tsx', 'frontend/src/lclucWorkflowAdapter.ts'):
        old = subprocess.check_output(['git', 'show', baseline + ':' + name], cwd=ROOT)
        current = (ROOT / name).read_bytes()
        checks.append(dict(path=name, baseline_sha256=digest(old), current_sha256=digest(current), unchanged=old == current))
    changes = subprocess.check_output(['git', 'diff', '--name-only', baseline, '--', 'backend', 'frontend', 'scripts', 'tests'], cwd=ROOT, text=True).splitlines()
    record = dict(scope='SYNTHETIC_TEMP_CPU_CHECKPOINT_READ_ONLY', tests=result.testsRun,
        failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped), seconds=elapsed,
        passed=result.wasSuccessful() and all(c['unchanged'] for c in checks) and not changes,
        frozen_source_matches=digest(SOURCE.read_bytes()) == FROZEN, source_sha256=digest(SOURCE.read_bytes()),
        baseline_commit=baseline, old_source_byte_checks=checks, tracked_source_differences=changes,
        installed_torch=torch.__version__, inherited_safe_globals_count=len(torch.serialization.get_safe_globals()),
        operating_Store_API_checkpoint_reads_or_writes=0, training_inference_state_load_calls=0,
        UI_API_changes=0, frontend_build_browser_runs=0,
        limitations=['weights_only inherits installed/caller safe_globals; no clear/add/replace or isolation guarantee.',
          'ZIP and snapshot bounds do not guarantee CPU/RSS/time limits or block every tensor metadata denial of service.',
          'Checkpoint/report hashes bind snapshots; state_dict compatibility, approval, authority, raster/mask, science and workflow execution remain unverified.',
          'Internal unwired reader: no frontend/build/browser or full backend rerun;1184 is previous evidence. Do not sum overlapping suites.'])
    (ROOT / 'evidence/integration/model-manifest-read-independent-20261018.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(record, ensure_ascii=False, indent=2))
    raise SystemExit(0 if record['passed'] and record['frozen_source_matches'] else 1)
