"""Compare an explicitly extracted identity with a caller-supplied record.

This is not a model resolver, full GMAIS model_ref validator, file check, or
authority check. Matching metadata can still be copied or forged.
"""
from .execution_input_binding import _sha
from .model_reference_contract import model_reference_issue
from .model_registration_provenance import inspect_model_registration_provenance


_IDENTITY_KEYS = frozenset(('id', 'version', 'sha256'))


def compare_model_reference_record(reference_identity, model_record=None):
    """Return fixed value-free metadata observations without I/O or coercion."""
    result = {
        'schema_version': 1,
        'scope': 'DECLARED_MODEL_IDENTITY_TO_SUPPLIED_RECORD_ONLY',
        'status': 'REFERENCE_INVALID',
        'bindings': {'id': 'NOT_CHECKED', 'version': 'NOT_CHECKED', 'sha256': 'NOT_CHECKED'},
        'record_provenance': None,
        'issue': None,
        'inspection_calls': 0,
        'authority_verified': False,
        'artifact_bytes_verified': False,
        'execution_authorized': False,
        'scientific_accuracy_validated': False,
        'model_verified': False,
    }

    def finish(status, code=None, field=None, side=None):
        result['status'] = status
        result['issue'] = None if code is None else {'code': code, 'field': field, 'side': side}
        return result

    if (type(reference_identity) is not dict or len(reference_identity) != 3
            or any(type(key) is not str for key in reference_identity)
            or reference_identity.keys() != _IDENTITY_KEYS):
        return finish('REFERENCE_INVALID', 'REFERENCE_IDENTITY_INVALID', 'reference_identity', 'REFERENCE')
    issue = model_reference_issue(reference_identity)
    if issue is not None:
        return finish('REFERENCE_INVALID', issue, 'reference_identity', 'REFERENCE')
    if not _sha(reference_identity['sha256']):
        return finish('REFERENCE_INVALID', 'SHA256_INVALID', 'sha256', 'REFERENCE')
    if model_record is None:
        return finish('RECORD_NOT_PROVIDED', 'RECORD_NOT_PROVIDED', 'model_record', 'RECORD')
    if type(model_record) is not dict:
        return finish('RECORD_INVALID', 'RECORD_INVALID', 'model_record', 'RECORD')
    if model_reference_issue({'id': model_record.get('id'), 'version': 'v1'}) is not None:
        return finish('RECORD_INVALID', 'MODEL_REFERENCE_INVALID', 'id', 'RECORD')
    bindings = result['bindings']
    if reference_identity['id'] != model_record['id']:
        bindings['id'] = 'MISMATCH'
        return finish('REFERENCE_CONFLICT', 'ID_MISMATCH', 'id', 'COMPARISON')
    bindings['id'] = 'MATCH'
    result['inspection_calls'] = 1
    observation = inspect_model_registration_provenance(model_record)
    result['record_provenance'] = observation
    if observation['status'] != 'CONSISTENT_UNVERIFIED':
        return finish('REFERENCE_NOT_COMPARABLE', 'REGISTRATION_NOT_COMPARABLE',
                      'model_version_declaration', 'RECORD')
    declaration = model_record['model_version_declaration']
    bindings['version'] = 'MATCH' if reference_identity['version'] == declaration['version'] else 'MISMATCH'
    bindings['sha256'] = 'MATCH' if reference_identity['sha256'] == declaration['checkpoint_sha256'] else 'MISMATCH'
    if bindings['version'] == 'MISMATCH':
        return finish('REFERENCE_CONFLICT', 'VERSION_MISMATCH', 'version', 'COMPARISON')
    if bindings['sha256'] == 'MISMATCH':
        return finish('REFERENCE_CONFLICT', 'CHECKPOINT_SHA256_MISMATCH', 'sha256', 'COMPARISON')
    return finish('MATCH_UNVERIFIED')
