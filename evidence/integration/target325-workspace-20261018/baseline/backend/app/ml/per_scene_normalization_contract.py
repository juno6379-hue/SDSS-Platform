"""Pure, bounded declaration comparison; no file, NumPy or execution boundary.

This deliberately stricter metadata observer never replaces the existing runtime
normalization verifier. Extra metadata values are not traversed or serialized.
"""
import math
import re

BAND_NAMES = ('B02', 'B03', 'B04', 'B08', 'B11', 'B12')
MODE = 'per_scene_product_metadata'
MAX_FIELDS = 128


def inspect_per_scene_normalization_contract(checkpoint_manifest, source_scene, normalization, evidence):
    """Inspect supplied declarations only. Hashes are syntax, not observed bytes."""
    result = {'schema_version': 1, 'scope': 'PER_SCENE_NORMALIZATION_DECLARATIONS_ONLY',
        'status': 'INVALID', 'issue': None, 'execution_authorized': False,
        'artifact_bytes_verified': False, 'source_authority_verified': False,
        'scientific_accuracy_validated': False, 'workflow_supported': False}

    class Stop(Exception):
        pass

    def stop(status, code, field):
        result.update(status=status, issue={'code': code, 'field': field})
        raise Stop

    def invalid(field):
        stop('INVALID', 'INVALID_FIELD', field)

    def mapping(value, field):
        if type(value) is not dict:
            invalid(field)
        if len(value) > MAX_FIELDS:
            stop('INVALID', 'INPUT_LIMIT', field)
        if not all(type(key) is str for key in value):
            invalid(field)

    def required(value, key, parent):
        if key not in value:
            stop('INCOMPLETE', 'MISSING_FIELD', parent + '.' + key)
        return value[key]

    def text(value, field, maximum):
        if not (type(value) is str and 1 <= len(value) <= maximum and value.strip()
                and all(ord(c) >= 32 and not 127 <= ord(c) <= 159
                        and not 0xD800 <= ord(c) <= 0xDFFF for c in value)):
            invalid(field)
        return value

    def digest(value, field):
        if type(value) is not str or re.fullmatch('[0-9a-f]{64}', value) is None:
            invalid(field)

    def band_names(value, field):
        if type(value) is not list or len(value) != 6:
            invalid(field)
        for name in value:
            text(name, field, 64)
        return value

    def coefficients(value, field, positive):
        if type(value) in (int, float):
            values = [value] * 6
        elif type(value) is list and len(value) == 6:
            values = value
        else:
            invalid(field)
        for item in values:
            # Bound integer conversion explicitly; never accept bool/string or
            # hide precision loss from a huge integer under float conversion.
            if type(item) not in (int, float) or (type(item) is int and item.bit_length() > 53):
                invalid(field)
            if not math.isfinite(item) or (positive and item <= 0):
                invalid(field)
        return values

    def match(condition, field):
        if not condition:
            stop('DECLARATION_MISMATCH', 'FIELD_MISMATCH', field)

    try:
        mapping(checkpoint_manifest, 'checkpoint_manifest')
        if 'normalization_mode' not in checkpoint_manifest:
            result['status'] = 'OUT_OF_SCOPE'
            return result
        mode = text(checkpoint_manifest['normalization_mode'], 'checkpoint_manifest.normalization_mode', 128)
        if mode != MODE:
            result['status'] = 'OUT_OF_SCOPE'
            return result
        bands = required(checkpoint_manifest, 'bands', 'checkpoint_manifest')
        if type(bands) is not list or len(bands) != 6 or any(type(b) is not int for b in bands):
            invalid('checkpoint_manifest.bands')
        model_names = band_names(required(checkpoint_manifest, 'band_names', 'checkpoint_manifest'), 'checkpoint_manifest.band_names')

        mapping(source_scene, 'source_scene')
        scene_id = text(required(source_scene, 'scene_id', 'source_scene'), 'source_scene.scene_id', 128)
        digest(required(source_scene, 'image_sha256', 'source_scene'), 'source_scene.image_sha256')
        source_names = band_names(required(source_scene, 'band_names', 'source_scene'), 'source_scene.band_names')

        mapping(normalization, 'normalization')
        scale = coefficients(required(normalization, 'scale', 'normalization'), 'normalization.scale', True)
        offset = coefficients(required(normalization, 'offset', 'normalization'), 'normalization.offset', False)
        text(required(normalization, 'evidence_path', 'normalization'), 'normalization.evidence_path', 512)
        digest(required(normalization, 'evidence_sha256', 'normalization'), 'normalization.evidence_sha256')

        mapping(evidence, 'evidence')
        status = text(required(evidence, 'status', 'evidence'), 'evidence.status', 128)
        product = text(required(evidence, 'product_id', 'evidence'), 'evidence.product_id', 128)
        evidence_names = band_names(required(evidence, 'band_names', 'evidence'), 'evidence.band_names')
        evidence_scale = coefficients(required(evidence, 'scale', 'evidence'), 'evidence.scale', True)
        evidence_offset = coefficients(required(evidence, 'offset', 'evidence'), 'evidence.offset', False)
        text(required(evidence, 'source_url', 'evidence'), 'evidence.source_url', 2048)
        text(required(evidence, 'source_metadata_path', 'evidence'), 'evidence.source_metadata_path', 512)
        digest(required(evidence, 'source_metadata_sha256', 'evidence'), 'evidence.source_metadata_sha256')

        match(bands == [1, 2, 3, 4, 5, 6], 'checkpoint_manifest.bands')
        match(model_names == list(BAND_NAMES), 'checkpoint_manifest.band_names')
        match(source_names == model_names, 'source_scene.band_names')
        match(status == 'verified_product_metadata', 'evidence.status')
        match(product == scene_id, 'evidence.product_id')
        match(evidence_names == model_names, 'evidence.band_names')
        match(scale == evidence_scale, 'normalization.scale')
        match(offset == evidence_offset, 'normalization.offset')
        result['status'] = 'DECLARATIONS_CONSISTENT_UNVERIFIED'
    except Stop:
        pass
    return result
