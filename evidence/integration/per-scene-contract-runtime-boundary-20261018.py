"""Root comparison of declaration-only observation and existing real file checks.

Only TempDirectory six-band rasters from the explicit synthetic readiness fixture
are used. No inference, checkpoint loading, training or operating Store access.
"""
import copy
import hashlib
import json
from pathlib import Path

from backend.app.ml.normalization import verify_inference_normalization
from backend.app.ml.per_scene_normalization_contract import inspect_per_scene_normalization_contract as inspect
from backend.app.ml.dataset import file_digest
from test_ml_readiness import ReadinessTests

ROOT = Path(__file__).resolve().parents[2]
fixture = ReadinessTests()
fixture.setUp()
checks = []
try:
    row = fixture.rows[0]
    image = fixture.root/row['image_path']
    normalization = copy.deepcopy(row['normalization'])
    evidence_path = fixture.root/normalization['evidence_path']
    evidence = json.loads(evidence_path.read_text('utf-8'))
    metadata_path = fixture.root/evidence['source_metadata_path']
    source = {'scene_id': row['scene_id'], 'image_sha256': file_digest(image), 'band_names': row['bands']}
    manifest = {'normalization_mode': 'per_scene_product_metadata', 'bands': list(range(1, 7)),
                'band_names': row['bands'], 'scale': 1, 'offset': 0}
    arguments = [manifest, source, normalization, evidence]
    before = copy.deepcopy(arguments)

    def observe():
        result = inspect(*arguments)
        assert result['status'] == 'DECLARATIONS_CONSISTENT_UNVERIFIED'
        for field in ('execution_authorized', 'artifact_bytes_verified', 'source_authority_verified',
                      'scientific_accuracy_validated', 'workflow_supported'):
            assert result[field] is False
        return result

    def runtime_pass():
        value = verify_inference_normalization(normalization, source, image, row['bands'], fixture.root)
        assert value['scene_id'] == source['scene_id']

    def runtime_reject():
        try:
            runtime_pass()
        except ValueError:
            return
        raise AssertionError('actual file verifier unexpectedly accepted altered bytes/declaration')

    observe()
    runtime_pass()
    checks.append('consistent_supplied_metadata_and_actual_temp_files_both_accepted_at_their_own_scope')
    assert arguments == before
    for label, path in [('image', image), ('evidence', evidence_path), ('source_metadata', metadata_path)]:
        original = path.read_bytes()
        try:
            path.write_bytes(original+b' ')
            observe()  # A pure observer must not claim that it noticed actual file changes.
            runtime_reject()
            checks.append(label+'_byte_tamper_invisible_to_pure_observer_but_rejected_by_existing_file_verifier')
        finally:
            path.write_bytes(original)
    original_sha = source['image_sha256']
    source['image_sha256'] = '0'*64
    observe()
    runtime_reject()
    source['image_sha256'] = original_sha
    checks.append('syntactically_valid_unobserved_image_sha_is_not_a_verified_file_binding')
    original_scene = source['scene_id']
    source['scene_id'] = 'different_product'
    assert inspect(*arguments)['status'] == 'DECLARATION_MISMATCH'
    runtime_reject()
    source['scene_id'] = original_scene
    checks.append('declared_product_mismatch_rejected_by_both_layers')
    runtime_pass()
    assert arguments == before
    result = {'scope': 'TESTED_SYNTHETIC_TEMP_FILES_DECLARATION_VS_ACTUAL_HASH_BOUNDARY',
              'checks_passed': checks, 'all_actual_fixture_files_restored_before_cleanup': True,
              'helper_input_metadata_unchanged': True, 'checkpoint_loaded': False,
              'training_inference_executed': False, 'operating_data_contact': False,
              'scientific_accuracy_validated': False, 'source_authority_verified': False}
    (ROOT/'evidence/integration/per-scene-contract-runtime-boundary-20261018.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(f'PASS {len(checks)} declaration/file-verifier boundary scenarios; synthetic Temp files only.')
finally:
    fixture.tearDown()
