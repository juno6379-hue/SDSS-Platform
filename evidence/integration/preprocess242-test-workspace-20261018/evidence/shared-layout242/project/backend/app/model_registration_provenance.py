"""Observe local record metadata consistency without authenticating provenance.

No Store, files, network, resolver or approval checks are performed. Even an
exactly consistent declaration may be copied or forged caller metadata.
"""
from .execution_input_binding import _sha
from .model_reference_contract import model_reference_issue


_DECLARATION_KEYS = frozenset((
    'schema_version', 'source', 'version', 'checkpoint_sha256',
    'training_report_sha256',
))
_HASH_FIELDS = ('checkpoint_sha256', 'training_report_sha256')


def inspect_model_registration_provenance(record):
    """Return a fixed, value-free observation; ignore unrelated record fields."""
    result = {
        'schema_version': 1,
        'scope': 'LOCAL_MODEL_REGISTRATION_METADATA_OBSERVATION_ONLY',
        'status': 'INVALID',
        'declaration_present': 'model_version_declaration' in record if type(record) is dict else None,
        'bindings': {field: 'NOT_CHECKED' for field in (*_HASH_FIELDS, 'model_version')},
        'issue': None,
        'authority_verified': False,
        'artifact_bytes_verified': False,
        'execution_authorized': False,
        'scientific_accuracy_validated': False,
    }

    def finish(status, code=None, field=None):
        result['status'] = status
        result['issue'] = None if code is None else {'code': code, 'field': field}
        return result

    if type(record) is not dict:
        return finish('INVALID', 'RECORD_INVALID', 'record')
    model_id = record.get('id')
    if model_reference_issue({'id': model_id, 'version': 'v1'}) is not None:
        return finish('INVALID', 'MODEL_REFERENCE_INVALID', 'id')
    if not result['declaration_present']:
        return finish('ABSENT')
    declaration = record['model_version_declaration']
    if (type(declaration) is not dict or len(declaration) != 5
            or any(type(key) is not str for key in declaration)
            or declaration.keys() != _DECLARATION_KEYS):
        return finish('INVALID', 'DECLARATION_SCHEMA_INVALID', 'model_version_declaration')
    if type(declaration['schema_version']) is not int or declaration['schema_version'] != 1:
        return finish('INVALID', 'DECLARATION_SCHEMA_INVALID', 'model_version_declaration.schema_version')
    if type(declaration['source']) is not str or declaration['source'] != 'CALLER_EXPLICIT_REGISTRATION':
        return finish('INVALID', 'DECLARATION_SCHEMA_INVALID', 'model_version_declaration.source')
    issue = model_reference_issue({'id': model_id, 'version': declaration['version']})
    if issue is not None:
        return finish('INVALID', issue, 'model_version_declaration.version')
    for field in _HASH_FIELDS:
        if not _sha(declaration[field]):
            return finish('INVALID', 'SHA256_INVALID', 'model_version_declaration.' + field)
    for field in _HASH_FIELDS:
        if field in record and not _sha(record[field]):
            return finish('INVALID', 'SHA256_INVALID', field)
    if 'model_version' in record:
        issue = model_reference_issue({'id': model_id, 'version': record['model_version']})
        if issue is not None:
            return finish('INVALID', issue, 'model_version')
    bindings = result['bindings']
    for field in _HASH_FIELDS:
        bindings[field] = ('MISSING' if field not in record
                           else 'MATCH' if record[field] == declaration[field] else 'MISMATCH')
    bindings['model_version'] = ('NOT_RECORDED' if 'model_version' not in record
        else 'MATCH' if record['model_version'] == declaration['version'] else 'MISMATCH')
    for field in (*_HASH_FIELDS, 'model_version'):
        if bindings[field] == 'MISMATCH':
            return finish('RECORD_CONFLICT', 'RECORD_BINDING_CONFLICT', field)
    for field in _HASH_FIELDS:
        if bindings[field] == 'MISSING':
            return finish('PARENT_BINDING_UNKNOWN', 'PARENT_BINDING_MISSING', field)
    return finish('CONSISTENT_UNVERIFIED')
