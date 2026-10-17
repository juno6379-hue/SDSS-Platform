"""Root isolated untrained CPU checkpoint -> actual manifest ->123 file reader.

The report intentionally contains a decoy copied signature to establish that the
returned manifest comes from checkpoint bytes. No operating data or inference.
"""
import copy
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import torch
from backend.app.store import Store
from backend.app.ml.network import TinyUNet
from backend.app.ml.raster import CLASS_NAMES
from backend.app.ml.model_checkpoint_manifest import read_pinned_model_checkpoint_manifest as read_manifest
from backend.app.ml.per_scene_normalization_files import verify_per_scene_normalization_files
from backend.app.ml.dataset import file_digest
from test_ml_readiness import ReadinessTests

ROOT = Path(__file__).resolve().parents[2]
fixture = ReadinessTests()
fixture.setUp()
checks = []
try:
    store = Store(fixture.root)
    identifier, version = 'manifest-root-fixture', ' v1 '
    folder = fixture.root/'models'/identifier
    folder.mkdir(parents=True)
    checkpoint = folder/'best.pt'
    names = ['B02', 'B03', 'B04', 'B08', 'B11', 'B12']
    manifest = {'bands': list(range(1, 7)), 'band_names': names,
                'normalization_mode': 'per_scene_product_metadata', 'scale': 1, 'offset': 0,
                'patch_size': 16, 'class_names': CLASS_NAMES, 'synthetic': True,
                'fixture_provenance': 'UNTRAINED_RANDOM_CPU_TINYUNET_TEMP_ONLY'}
    torch.save({'architecture': 'tiny_unet', 'manifest': manifest, 'state_dict': TinyUNet(6).state_dict()}, checkpoint)
    checkpoint_sha = file_digest(checkpoint)
    report = {'model_id': identifier, 'checkpoint_sha256': checkpoint_sha, 'training_state': 'completed',
              'fixture_only_not_actual_training': True,
              'input_signature': {'bands': [1, 2, 3], 'normalization_mode': 'global', 'decoy_not_checkpoint_manifest': True}}
    report_path = folder/'report.json'
    report_path.write_text(json.dumps(report), encoding='utf-8')
    report_sha = file_digest(report_path)
    model = {'id': identifier, 'status': 'Draft', 'independent_evaluation': False,
             'checkpoint_path': f'models/{identifier}/best.pt', 'checkpoint_sha256': checkpoint_sha,
             'training_report_sha256': report_sha, 'model_version_declaration': {
                'schema_version': 1, 'source': 'CALLER_EXPLICIT_REGISTRATION', 'version': version,
                'checkpoint_sha256': checkpoint_sha, 'training_report_sha256': report_sha}}
    store.put('models', model)
    ref = {'id': identifier, 'version': version, 'sha256': checkpoint_sha}
    before = {p.relative_to(fixture.root).as_posix(): file_digest(p) for p in fixture.root.rglob('*') if p.is_file()}
    original_metadata = copy.deepcopy([ref, model])

    def observe(request=ref):
        with patch.object(store, 'put', side_effect=AssertionError('reader must never write Store')), \
             patch.object(TinyUNet, 'forward', side_effect=AssertionError('no inference')):
            result = read_manifest(store, request, report_sha)
        for field in ('state_dict_verified', 'source_authority_verified', 'scientific_accuracy_validated',
                      'execution_authorized', 'workflow_supported'):
            assert result[field] is False
        return result

    result = observe()
    assert result['status'] == 'MANIFEST_BOUND_UNVERIFIED' and result['checkpoint_manifest'] == manifest
    assert result['checkpoint_artifact_verified'] is True and result['training_report_artifact_verified'] is True
    checks.append('actual_untrained_six_band_checkpoint_manifest_returned_instead_of_report_decoy_signature')
    row = fixture.rows[0]
    source = {'scene_id': row['scene_id'], 'image_sha256': file_digest(fixture.root/row['image_path']), 'band_names': names}
    scene = verify_per_scene_normalization_files(fixture.root, result['checkpoint_manifest'], source,
                                                 row['normalization'], row['image_path'])
    assert scene['status'] == 'FILES_MATCHED_UNVERIFIED' and scene['artifact_bytes_verified'] is True
    assert scene['execution_authorized'] is False and scene['workflow_supported'] is False
    checks.append('actual_checkpoint_manifest_manually_composes_with123_temp_scene_files_without_execution_permission')
    result['checkpoint_manifest']['band_names'][0] = 'caller_changed_detached_copy'
    assert observe()['checkpoint_manifest'] == manifest
    checks.append('returned_manifest_is_detached_and_repeat_read_still_matches_unchanged_checkpoint')
    for label, path in [('checkpoint', checkpoint), ('training_report', report_path)]:
        original = path.read_bytes()
        try:
            path.write_bytes(original+b' ')
            changed = observe()
            assert changed['status'] == 'BLOCKED' and changed['checkpoint_manifest'] is None
            assert changed['issue']['code'] == 'SHA256_MISMATCH' and changed['issue']['field'] == label
            checks.append(label+'_byte_tamper_rejected_without_repin_or_model_state_change')
        finally:
            path.write_bytes(original)
    changed = observe({**ref, 'version': 'v1'})
    assert changed['status'] == 'BLOCKED' and changed['issue']['code'] == 'PIN_CONFLICT'
    checks.append('padded_explicit_version_preserved_and_unpadded_alias_rejected')
    assert original_metadata == [ref, model]
    assert before == {p.relative_to(fixture.root).as_posix(): file_digest(p) for p in fixture.root.rglob('*') if p.is_file()}
    proof = {'scope': 'TESTED_SYNTHETIC_UNTRAINED_CPU_TINYUNET_CHECKPOINT_AND_TEMP_RASTER_NO_INFERENCE',
             'torch_version': torch.__version__, 'checks_passed': checks,
             'checkpoint_manifest_source': 'Actual SHA-verified copied checkpoint bytes, not report input_signature',
             'manual_composition_is_not_workflow_or_api_binding': True,
             'fixture_files_and_caller_metadata_unchanged_after_restoration': True,
             'operating_checkpoint_loaded': False, 'inference_training_executed': False,
             'operating_store_contact': False, 'scientific_accuracy_validated': False}
    (ROOT/'evidence/integration/model-manifest-read-runtime-20261018.json').write_text(
        json.dumps(proof, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(f'PASS {len(checks)} isolated CPU checkpoint/scene read scenarios; no inference or training.')
finally:
    fixture.tearDown()
