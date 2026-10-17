"""Independent bounded reader checks on disposable files, not operating data."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from app.ml import per_scene_normalization_files as reader

SOURCE = ROOT / 'backend/app/ml/per_scene_normalization_files.py'
FROZEN = '77b6d844aa1a71304826d34f492780b80a8b0b7c7f21740856510d8acd463366'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == FROZEN
FLAGS = ('checkpoint_artifact_verified', 'source_authority_verified',
         'scientific_accuracy_validated', 'execution_authorized', 'workflow_supported')
JUNCTION = {'attempted': False, 'created': False, 'link_only_removed': False, 'target_preserved': False}


def sha(value):
    return hashlib.sha256(value).hexdigest()


class Independent(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='geoai-123-independent-')
        self.root = Path(self.temp.name).resolve()
        self.image = self.root / '影像 image.bin'
        self.image.write_bytes(b'opaque image bytes, not raster validation')
        self.meta = self.root / '원 metadata.xml'
        self.meta.write_bytes(b'<caller-claimed-metadata/>')
        names = ['B02', 'B03', 'B04', 'B08', 'B11', 'B12']
        self.manifest = dict(normalization_mode='per_scene_product_metadata', bands=list(range(1, 7)), band_names=names[:])
        self.scene = dict(scene_id='제품 α', image_sha256=sha(self.image.read_bytes()), band_names=names[:])
        self.norm = dict(scale=.0001, offset=0, evidence_path='보정 evidence.json', evidence_sha256='b' * 64)
        self.evidence = dict(status='verified_product_metadata', product_id='제품 α', band_names=names[:],
            scale=[.0001] * 6, offset=[0.] * 6, source_url='https://example.invalid/not-contacted',
            source_metadata_path=self.meta.name, source_metadata_sha256=sha(self.meta.read_bytes()))
        self.write_evidence()

    def tearDown(self):
        self.temp.cleanup()

    def write_evidence(self, raw=None):
        raw = json.dumps(self.evidence, ensure_ascii=False).encode() if raw is None else raw
        (self.root / self.norm['evidence_path']).write_bytes(raw)
        self.norm['evidence_sha256'] = sha(raw)

    def read(self, **overrides):
        args = dict(data_root=self.root, checkpoint_manifest=self.manifest,
                    source_scene=self.scene, normalization=self.norm, image_path=self.image.name)
        args.update(overrides)
        result = reader.verify_per_scene_normalization_files(**args)
        self.assertEqual(set(result), {'schema_version', 'scope', 'status', 'issue', 'declaration_observation',
                                     'file_bindings', 'artifact_bytes_verified', *FLAGS})
        self.assertEqual(result['schema_version'], 1)
        self.assertEqual(result['scope'], 'PER_SCENE_NORMALIZATION_FILE_SNAPSHOTS_ONLY')
        self.assertEqual(set(result['file_bindings']), {'image', 'normalization_evidence', 'source_metadata'})
        for flag in FLAGS:
            self.assertIs(result[flag], False)
        if result['declaration_observation'] is not None:
            for flag in ('execution_authorized', 'artifact_bytes_verified', 'source_authority_verified',
                         'scientific_accuracy_validated', 'workflow_supported'):
                self.assertIs(result['declaration_observation'][flag], False)
        return result

    def blocked(self, result, code, field):
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertIs(result['artifact_bytes_verified'], False)
        self.assertEqual(result['issue'], dict(code=code, field=field))

    def test_three_role_success_is_bytes_only_and_input_immutable(self):
        before = copy.deepcopy([self.manifest, self.scene, self.norm, self.evidence])
        result = self.read()
        self.assertEqual(result['status'], 'FILES_MATCHED_UNVERIFIED')
        self.assertIs(result['artifact_bytes_verified'], True)
        self.assertEqual(set(result['file_bindings'].values()), {'MATCH'})
        self.assertIsNone(result['issue'])
        self.assertEqual(before, [self.manifest, self.scene, self.norm, self.evidence])
        # Opaque non-raster image bytes succeed: no header/mask/science claim.
        self.assertEqual(result['declaration_observation']['status'], 'DECLARATIONS_CONSISTENT_UNVERIFIED')

    def test_global_1_to_16_and_missing_declaration_have_no_file_io(self):
        with patch.object(Path, 'open', side_effect=AssertionError('unexpected open')), \
             patch.object(Path, 'resolve', side_effect=AssertionError('unexpected resolve')):
            for count in range(1, 17):
                result = self.read(data_root=object(), checkpoint_manifest=dict(normalization_mode='global', bands=list(range(count))),
                                   source_scene=object(), normalization=object(), image_path=object())
                self.assertEqual(result['status'], 'OUT_OF_SCOPE')
                self.assertEqual(set(result['file_bindings'].values()), {'NOT_CHECKED'})
            result = self.read(normalization={})
            self.blocked(result, 'DECLARATION_NOT_CONSISTENT', 'declarations')

    def test_role_sha_mismatch_and_partial_binding_priority(self):
        self.norm['evidence_sha256'] = '0' * 64
        result = self.read()
        self.blocked(result, 'SHA256_MISMATCH', 'normalization_evidence')
        self.assertEqual(result['file_bindings']['normalization_evidence'], 'MISMATCH')
        self.write_evidence(); self.scene['image_sha256'] = '0' * 64
        result = self.read()
        self.blocked(result, 'SHA256_MISMATCH', 'image')
        self.assertEqual(result['file_bindings'], dict(normalization_evidence='MATCH', image='MISMATCH', source_metadata='NOT_CHECKED'))
        self.scene['image_sha256'] = sha(self.image.read_bytes())
        self.evidence['source_metadata_sha256'] = '0' * 64; self.write_evidence()
        result = self.read()
        self.blocked(result, 'SHA256_MISMATCH', 'source_metadata')
        self.assertEqual(result['file_bindings']['image'], 'MATCH')

    def test_strict_json_before_semantics(self):
        for raw in (b'{"status":1,"status":2}', b'{"x":NaN}', b'{"x":Infinity}', b'{"x":1e999}',
                    b'[]', b'\xff', b'\xef\xbb\xbf{}', b'{"x":"\\ud800"}',
                    b'{"x":' + b'[' * 66 + b'0' + b']' * 66 + b'}',
                    b'{"x":[' + b'0,' * 65536 + b'0]}'):
            self.write_evidence(raw)
            result = self.read()
            self.blocked(result, 'EVIDENCE_JSON_INVALID', 'normalization_evidence')
            self.assertEqual(result['file_bindings']['normalization_evidence'], 'MATCH')
            self.assertEqual(result['file_bindings']['image'], 'NOT_CHECKED')

    def test_declaration_mismatch_stops_before_image(self):
        self.evidence['product_id'] = 'different'; self.write_evidence(); self.image.unlink()
        result = self.read()
        self.blocked(result, 'DECLARATION_NOT_CONSISTENT', 'declarations')
        self.assertEqual(result['declaration_observation']['issue']['field'], 'evidence.product_id')
        self.assertEqual(result['file_bindings']['image'], 'NOT_CHECKED')

    def test_path_escape_and_alias_spellings(self):
        for value in ('../escape', './image', '/absolute', r'C:\image', r'\\server\share', 'a//b',
                      'a/../b', 'https://example.invalid/x', 'x.', 'x ', 'x\x00', '\ud800', 'x' * 129):
            self.blocked(self.read(image_path=value), 'PATH_INVALID', 'image')
        self.evidence['source_metadata_path'] = '../escape'; self.write_evidence()
        self.blocked(self.read(), 'PATH_INVALID', 'source_metadata')
        with patch.object(Path, 'resolve', side_effect=AssertionError('UNC must be rejected before I/O')):
            for value in (r'\\server\share', '//server/share'):
                self.blocked(self.read(data_root=value), 'ROOT_UNAVAILABLE', 'data_root')

    def test_each_file_limit_and_missing_or_nonregular(self):
        for role, name, limit in (('normalization_evidence', self.norm['evidence_path'], 2 * 1024**2),
                                  ('image', self.image.name, 64 * 1024**2),
                                  ('source_metadata', self.meta.name, 2 * 1024**2)):
            path = self.root / name
            original = path.read_bytes()
            with path.open('wb') as stream: stream.truncate(limit + 1)
            self.blocked(self.read(), 'FILE_LIMIT', role)
            path.write_bytes(original)
        self.image.unlink()
        self.blocked(self.read(), 'FILE_UNAVAILABLE', 'image')
        self.image.mkdir()
        self.blocked(self.read(), 'FILE_UNAVAILABLE', 'image')

    def test_growth_stream_limit_not_just_pre_stat(self):
        self.image.write_bytes(b'12345678')
        self.scene['image_sha256'] = sha(b'12345678')
        original_open = Path.open
        target = self.image
        class Growing:
            def __init__(self, stream): self.stream, self.grown = stream, False
            def __enter__(self): return self
            def __exit__(self, *args): self.stream.close()
            def fileno(self): return self.stream.fileno()
            def read(self, size):
                if not self.grown:
                    self.grown = True
                    with original_open(target, 'ab') as output: output.write(b'9')
                return self.stream.read(size)
        def patched(path, *args, **kwargs):
            stream = original_open(path, *args, **kwargs)
            return Growing(stream) if path == target and args == ('rb',) else stream
        with patch.object(reader, 'MAX_IMAGE', 8), patch.object(Path, 'open', patched):
            self.blocked(self.read(), 'FILE_LIMIT', 'image')

    def test_actual_windows_junction_is_rejected_and_target_preserved(self):
        if os.name != 'nt':
            self.skipTest('Windows-only actual junction')
        JUNCTION['attempted'] = True
        target, link = self.root / 'target', self.root / 'junction'
        target.mkdir(); sentinel = target / 'sentinel.bin'; sentinel.write_bytes(b'preserve')
        created = subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), str(target)], capture_output=True)
        self.assertEqual(created.returncode, 0, created.stderr.decode(errors='replace'))
        JUNCTION['created'] = True
        try:
            self.assertEqual(os.lstat(link).st_reparse_tag, 0xA0000003)
            self.blocked(self.read(image_path='junction/sentinel.bin'), 'PATH_INVALID', 'image')
            self.blocked(self.read(data_root=link), 'ROOT_UNAVAILABLE', 'data_root')
        finally:
            # Verify lexical absolute target is this explicitly named Temp link;
            # remove only that junction, never recurse or remove resolved target.
            self.assertEqual(link.absolute().parent, self.root)
            self.assertEqual(link.name, 'junction')
            self.assertEqual(os.lstat(link).st_reparse_tag, 0xA0000003)
            os.rmdir(link)
            JUNCTION['link_only_removed'] = not link.exists()
            JUNCTION['target_preserved'] = sentinel.read_bytes() == b'preserve'
        self.assertTrue(JUNCTION['target_preserved'])


if __name__ == '__main__':
    begin = time.perf_counter()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Independent))
    elapsed = time.perf_counter() - begin
    baseline = '9c5acb431392f3e94e7e6e361737c0e8ef4002ed'
    checks = []
    for name in ('backend/app/ml/per_scene_normalization_contract.py', 'backend/app/lcluc_workflow.py',
                 'backend/app/ml/normalization.py', 'backend/app/ml/service.py', 'backend/app/main.py',
                 'frontend/src/LclucWorkflowPanel.tsx', 'frontend/src/lclucWorkflowAdapter.ts', 'frontend/src/api.ts'):
        old = subprocess.check_output(['git', 'show', baseline + ':' + name], cwd=ROOT)
        current = (ROOT / name).read_bytes()
        checks.append(dict(path=name, baseline_sha256=sha(old), current_sha256=sha(current), unchanged=old == current))
    diff = subprocess.check_output(['git', 'diff', '--name-only', baseline, '--', 'backend', 'frontend', 'scripts', 'tests'], cwd=ROOT, text=True).splitlines()
    payload = dict(scope='SYNTHETIC_TEMP_FILE_SNAPSHOTS_ONLY', tests=result.testsRun,
        failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped), seconds=elapsed,
        passed=result.wasSuccessful() and all(c['unchanged'] for c in checks) and not diff,
        source_sha256=sha(SOURCE.read_bytes()), frozen_source_matches=sha(SOURCE.read_bytes()) == FROZEN,
        baseline_commit=baseline, old_source_byte_checks=checks, tracked_source_differences=diff,
        windows_junction=JUNCTION, operating_Store_API_reads_or_writes=0, raster_header_reads=0,
        inference_training_downloads=0, UI_API_changes=0, frontend_build_browser_runs=0,
        limitations=['Three sequential snapshots, not an atomic file set or complete TOCTOU elimination.',
          'Opaque image bytes deliberately pass hash observation; no raster header/mask/calibration/authority/approval/science claim.',
          'Checkpoint manifest bytes are not read or authenticated. Mapped-drive physical locality is not established.',
          'Unwired helper requires no UI/API changes or frontend/browser rerun. Existing1184 backend is historical, not rerun here. Do not sum overlapping suites.'])
    destination = ROOT / 'evidence/integration/per-scene-files-independent-20261018.json'
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    raise SystemExit(0 if payload['passed'] and payload['frozen_source_matches'] else 1)
