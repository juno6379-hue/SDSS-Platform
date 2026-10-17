"""Root actual temporary GeoTIFF + three immutable DatasetVersion references.

Actual untrained CPU checkpoint and synthetic scene metadata; no inference/training/operating DB.
"""
import copy
import json
from pathlib import Path
from unittest.mock import patch

from backend.app.store import Store
from backend.app.dataset_registry import register_version
from backend.app.ml.dataset import file_digest
import torch
from backend.app.ml.network import TinyUNet
from backend.app.ml.pinned_scene_normalization import inspect_pinned_scene_normalization as read
from test_ml_readiness import ReadinessTests

ROOT = Path(__file__).resolve().parents[2]
fixture = ReadinessTests()
fixture.setUp()
checks = []
try:
    store = Store(fixture.root)
    row = fixture.rows[0]
    image = fixture.root/row['image_path']
    evidence = fixture.root/row['normalization']['evidence_path']
    evidence_body = json.loads(evidence.read_text('utf-8'))
    metadata = fixture.root/evidence_body['source_metadata_path']
    names = row['bands']
    checkpoint_manifest = {'normalization_mode': 'per_scene_product_metadata', 'bands': list(range(1, 7)),
                           'band_names': names, 'scale': 1, 'offset': 0}

    def manifest(identifier, path, kind, source=None, lineage=None):
        return {'schema_version': '0.2.0', 'dataset_id': identifier, 'version': 'v1',
                'source': source or {'institution': 'synthetic fixture', 'product': 'document fixture', 'license': 'test only'},
                'data_type': kind, 'spatial': {'bbox': [106, -7, 107, -6], 'crs': 'OGC:CRS84'},
                'temporal': {'start': '2021-01-01T00:00:00Z', 'end': '2021-12-31T00:00:00Z', 'calendar': 'gregorian'},
                'quality_status': 'RAW', 'access_class': 'PUBLIC', 'sha256': file_digest(path),
                'artifact_uri': path.relative_to(fixture.root).as_posix(), 'lineage': lineage or []}

    image_manifest = manifest('registered-image-fixture', image, 'raster', {
        'institution': 'synthetic fixture', 'product': 'generic product name deliberately NOT scene0',
        'license': 'test only', 'scene_id': row['scene_id'], 'band_names': names})
    metadata_manifest = manifest('registered-metadata-fixture', metadata, 'document')
    image_ref = {'id': image_manifest['dataset_id'], 'version': 'v1', 'sha256': image_manifest['sha256']}
    metadata_ref = {'id': metadata_manifest['dataset_id'], 'version': 'v1', 'sha256': metadata_manifest['sha256']}
    evidence_manifest = manifest('registered-evidence-fixture', evidence, 'document', lineage=[
        {**image_ref, 'role': 'normalization_input_image'},
        {**metadata_ref, 'role': 'normalization_source_metadata'}])
    evidence_ref = {'id': evidence_manifest['dataset_id'], 'version': 'v1', 'sha256': evidence_manifest['sha256']}
    for value in (image_manifest, metadata_manifest, evidence_manifest):
        register_version(store, value)
    legacy_manifest = copy.deepcopy(image_manifest)
    legacy_manifest['dataset_id'] = 'legacy-without-scene-fixture'
    legacy_manifest['source'].pop('scene_id')
    register_version(store, legacy_manifest)
    legacy_ref = {'id': legacy_manifest['dataset_id'], 'version': 'v1', 'sha256': legacy_manifest['sha256']}
    identifier='root-pinned-scene-fixture'
    folder=fixture.root/'models'/identifier;folder.mkdir(parents=True)
    checkpoint=folder/'best.pt'
    torch.save({'architecture':'tiny_unet','manifest':checkpoint_manifest,'state_dict':TinyUNet(6).state_dict()},checkpoint)
    ref={'id':identifier,'version':'v1','sha256':file_digest(checkpoint)}
    report_path=folder/'report.json'
    report_path.write_text(json.dumps({'model_id':identifier,'training_state':'completed','checkpoint_sha256':ref['sha256'],
        'fixture_only_no_actual_training':True,'input_signature':{'normalization_mode':'global','bands':[1,2,3]}}),encoding='utf-8')
    report_sha=file_digest(report_path)
    store.put('models',{'id':identifier,'status':'Draft','checkpoint_path':f'models/{identifier}/best.pt',
        'checkpoint_sha256':ref['sha256'],'training_report_sha256':report_sha,'model_version_declaration':{
        'schema_version':1,'source':'CALLER_EXPLICIT_REGISTRATION','version':'v1',
        'checkpoint_sha256':ref['sha256'],'training_report_sha256':report_sha}})
    before = {p.relative_to(fixture.root).as_posix(): file_digest(p) for p in fixture.root.rglob('*') if p.is_file()}
    inputs_before = copy.deepcopy([checkpoint_manifest, image_ref, evidence_ref, metadata_ref])

    def observe(selected=image_ref):
        with patch.object(store, 'put', side_effect=AssertionError('reader cannot write Store')), patch.object(TinyUNet,'forward',side_effect=AssertionError('no inference')):
            result = read(store, ref, report_sha, selected, evidence_ref, metadata_ref)
        for field in ('raster_header_verified', 'quality_report_verified',
                      'quality_mask_verified', 'source_authority_verified', 'access_authorization_verified',
                      'other_lineage_parents_verified', 'state_dict_verified', 'scientific_accuracy_validated',
                      'execution_authorized', 'workflow_supported'):
            assert result[field] is False
        return result

    result = observe()
    assert result['status'] == 'PINNED_SCENE_MATCHED_UNVERIFIED'
    assert result['registry_references_verified'] is True and result['artifact_bytes_verified'] is True
    checks.append('three_actual_temp_registry_versions_and_raster_evidence_metadata_hashes_match')
    assert result['model_observation']['checkpoint_manifest'] == checkpoint_manifest
    assert result['checkpoint_artifact_verified'] and result['training_report_artifact_verified']
    assert image_manifest['source']['product'] != row['scene_id']
    checks.append('explicit_registered_scene_id_used_without_guessing_from_generic_product_name')
    legacy = observe(legacy_ref)
    assert legacy['status'] == 'SCENE_BLOCKED' and legacy['artifact_bytes_verified'] is False
    assert legacy['scene_observation']['issue']['code'] == 'SCENE_DECLARATION_MISSING'
    checks.append('legacy_missing_scene_declaration_blocked_without_backfill_or_registry_write')
    for role, path in [('image', image), ('normalization_evidence', evidence), ('source_metadata', metadata)]:
        original = path.read_bytes()
        try:
            path.write_bytes(original+b' ')
            changed = observe()
            assert changed['status'] == 'SCENE_BLOCKED' and changed['artifact_bytes_verified'] is False
            checks.append(role+'_actual_tamper_rejected_against_immutable_role_reference')
        finally:
            path.write_bytes(original)
    assert before == {p.relative_to(fixture.root).as_posix(): file_digest(p) for p in fixture.root.rglob('*') if p.is_file()}
    assert inputs_before == [checkpoint_manifest, image_ref, evidence_ref, metadata_ref]
    proof = {'scope': 'TESTED_SYNTHETIC_TEMP_REGISTERED_VERSIONS_AND_ACTUAL_SIX_BAND_RASTER',
             'checks_passed': checks, 'quality_status': 'RAW_NOT_A_QUALITY_APPROVAL',
             'checkpoint_manifest_source': 'Actual pinned checkpoint bytes, decoy report signature ignored',
             'fixture_files_and_caller_metadata_unchanged_after_restoration': True,
             'temporary_untrained_model_loaded': True, 'operating_model_loaded': False, 'torch_version': torch.__version__, 'training_inference_executed': False, 'operating_registry_contact': False,
             'scientific_accuracy_validated': False}
    (ROOT/'evidence/integration/pinned-scene-runtime-20261018.json').write_text(
        json.dumps(proof, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(f'PASS {len(checks)} isolated registered scene/file scenarios; actual temporary model read, no execution.')
finally:
    fixture.tearDown()
