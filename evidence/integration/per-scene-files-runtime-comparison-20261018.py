"""Root comparison using actual temporary six-band rasters and synthetic metadata.

No inference, checkpoint load, operating Store access, training or network call.
"""
import copy
import hashlib
import json
from pathlib import Path

from backend.app.ml.normalization import verify_inference_normalization
from backend.app.ml.per_scene_normalization_files import verify_per_scene_normalization_files as verify
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
    before = {p.relative_to(fixture.root).as_posix(): file_digest(p) for p in fixture.root.rglob('*') if p.is_file()}
    metadata_before = copy.deepcopy([manifest, source, normalization])

    def inspect():
        result = verify(fixture.root, manifest, source, normalization, row['image_path'])
        for name in ('checkpoint_artifact_verified', 'execution_authorized', 'workflow_supported',
                     'scientific_accuracy_validated', 'source_authority_verified'):
            assert result[name] is False
        return result

    result = inspect()
    assert result['status'] == 'FILES_MATCHED_UNVERIFIED' and result['artifact_bytes_verified'] is True
    assert set(result['file_bindings'].values()) == {'MATCH'}
    assert verify_inference_normalization(normalization, source, image, row['bands'], fixture.root)['scene_id'] == source['scene_id']
    checks.append('new_reader_and_existing_file_verifier_match_same_actual_temp_six_band_fixture')
    for role, path in [('image', image), ('normalization_evidence', evidence_path), ('source_metadata', metadata_path)]:
        original = path.read_bytes()
        try:
            path.write_bytes(original+b' ')
            altered = inspect()
            assert altered['status'] == 'BLOCKED' and altered['artifact_bytes_verified'] is False
            assert altered['file_bindings'][role] == 'MISMATCH'
            checks.append(role+'_actual_byte_tamper_rejected_without_implicit_repin_or_write')
        finally:
            path.write_bytes(original)
    original_evidence = evidence_path.read_bytes()
    original_sha = normalization['evidence_sha256']
    try:
        evidence_path.write_text(json.dumps({**evidence, 'product_id': 'different_product'}), encoding='utf-8')
        normalization['evidence_sha256'] = file_digest(evidence_path)
        altered = inspect()
        assert altered['status'] == 'BLOCKED' and altered['artifact_bytes_verified'] is False
        assert altered['declaration_observation']['status'] == 'DECLARATION_MISMATCH'
        checks.append('repinned_changed_evidence_still_rejected_when_product_declaration_disagrees')
    finally:
        evidence_path.write_bytes(original_evidence)
        normalization['evidence_sha256'] = original_sha
    image_raw = image.read_bytes()
    original_image_sha = source['image_sha256']
    try:
        # Matching bytes do not establish raster format. This limitation is explicit.
        image.write_bytes(b'NOT A RASTER; HASH-ONLY SYNTHETIC FIXTURE')
        source['image_sha256'] = file_digest(image)
        not_raster = inspect()
        assert not_raster['status'] == 'FILES_MATCHED_UNVERIFIED' and not_raster['artifact_bytes_verified'] is True
        checks.append('matching_non_raster_bytes_demonstrate_header_and_scientific_validity_not_checked')
    finally:
        image.write_bytes(image_raw)
        source['image_sha256'] = original_image_sha
    assert before == {p.relative_to(fixture.root).as_posix(): file_digest(p) for p in fixture.root.rglob('*') if p.is_file()}
    assert metadata_before == [manifest, source, normalization]
    result = {'scope': 'TESTED_SYNTHETIC_ACTUAL_TEMP_RASTER_AND_METADATA_BYTES_NO_INFERENCE',
              'checks_passed': checks, 'fixture_files_and_input_metadata_restored': True,
              'checkpoint_loaded': False, 'training_inference_executed': False,
              'operating_data_contact': False, 'scientific_accuracy_validated': False}
    (ROOT/'evidence/integration/per-scene-files-runtime-comparison-20261018.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(f'PASS {len(checks)} actual Temp file comparison scenarios; no model execution.')
finally:
    fixture.tearDown()
