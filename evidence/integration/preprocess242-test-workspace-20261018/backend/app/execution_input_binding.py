"""고정 ordered 입력 전달 선언만 비교한다. IO·Registry·실행 승인을 수행하지 않는다."""
import hashlib
import json
import re

_REQUIRED = {'input_index', 'id', 'version', 'sha256'}
_OPTIONAL = {'role', 'manifest_sha256'}
_ENVELOPE = {'job_id', 'agent_id', 'trace_id', 'bindings'}
_FALSE = ('execution_authorized', 'ready_for_execution', 'ready_for_training',
          'scientific_approval', 'acl_verified', 'registry_verified', 'training_authorized',
          'pixels_verified', 'toc_tou_protected', 'executor_connected',
          'artifact_bytes_verified', 'manifest_bytes_verified')


def _text(value):
    # Length precedes scanning/encoding. No coercion or normalization.
    return (type(value) is str and 1 <= len(value) <= 256
            and bool(value.strip())
            and all(ord(c) >= 32 and not 127 <= ord(c) <= 159 and not 0xD800 <= ord(c) <= 0xDFFF for c in value))


def _sha(value):
    return type(value) is str and len(value) == 64 and re.fullmatch('[a-f0-9]{64}', value) is not None


def _validate(value, side, issues):
    def issue(code, index=None):
        issues.append({'side': side, 'input_index': index, 'code': code})
    if type(value) is not dict or len(value) != 4 or set(value) != _ENVELOPE:
        issue('ENVELOPE_SCHEMA_INVALID')
        return False
    if any(not _text(value[k]) for k in ('job_id', 'agent_id', 'trace_id')):
        issue('IDENTITY_SCHEMA_INVALID')
    rows = value['bindings']
    if type(rows) is not list or not 1 <= len(rows) <= 64:
        issue('BINDING_COUNT_INVALID')
        return False
    identities = {}
    for index, row in enumerate(rows):
        if type(row) is not dict or not 4 <= len(row) <= 6 or not _REQUIRED <= set(row) or set(row) - (_REQUIRED | _OPTIONAL):
            issue('BINDING_SCHEMA_INVALID', index)
            continue
        if type(row['input_index']) is not int or row['input_index'] != index:
            issue('BINDING_INDEX_INVALID', index)
        if not _text(row['id']) or not _text(row['version']):
            issue('BINDING_IDENTITY_INVALID', index)
            continue
        if row['version'].strip().lower() in {'latest', 'current'}:
            issue('BINDING_VERSION_NOT_PINNED', index)
        if not _sha(row['sha256']):
            issue('BINDING_SHA_INVALID', index)
        if 'role' in row and not _text(row['role']):
            issue('BINDING_ROLE_INVALID', index)
        if 'manifest_sha256' in row and not _sha(row['manifest_sha256']):
            issue('BINDING_MANIFEST_SHA_INVALID', index)
        # Only bounded validated scalar fields enter hashable keys/sets.
        if _sha(row['sha256']) and ('manifest_sha256' not in row or _sha(row['manifest_sha256'])):
            key = (row['id'], row['version'])
            prior = identities.setdefault(key, {'sha': set(), 'manifest': set()})
            prior['sha'].add(row['sha256'])
            if 'manifest_sha256' in row:
                prior['manifest'].add(row['manifest_sha256'])
            if len(prior['sha']) > 1 or len(prior['manifest']) > 1:
                issue('BINDING_IDENTITY_CONFLICT', index)
    return not any(item['side'] == side for item in issues)


def compare_execution_input_bindings(expected, supplied):
    """새 내부 RFC v1. Missing expected manifest pin stays unknown; never backfilled."""
    issues = []
    valid_expected = _validate(expected, 'expected', issues)
    valid_supplied = _validate(supplied, 'supplied', issues)
    digest = None
    if valid_expected:
        encoded = json.dumps(expected['bindings'], sort_keys=True, ensure_ascii=False,
                             allow_nan=False, separators=(',', ':')).encode('utf-8')
        digest = hashlib.sha256(encoded).hexdigest()
    missing = 0
    if valid_expected and valid_supplied:
        for field, code in (('job_id', 'JOB_ID_MISMATCH'), ('agent_id', 'AGENT_ID_MISMATCH'),
                            ('trace_id', 'TRACE_ID_MISMATCH')):
            if expected[field] != supplied[field]:
                issues.append({'side': 'comparison', 'input_index': None, 'code': code})
        left, right = expected['bindings'], supplied['bindings']
        if len(left) != len(right):
            issues.append({'side': 'comparison', 'input_index': None, 'code': 'BINDING_COUNT_MISMATCH'})
        for index, row in enumerate(left):
            if 'manifest_sha256' not in row:
                missing += 1
            if index >= len(right):
                continue
            actual = right[index]
            for field, code in (('id', 'BINDING_ID_MISMATCH'), ('version', 'BINDING_VERSION_MISMATCH'),
                                ('sha256', 'BINDING_SHA_MISMATCH'), ('role', 'BINDING_ROLE_MISMATCH')):
                if (field in row) != (field in actual) or (field in row and row[field] != actual[field]):
                    issues.append({'side': 'comparison', 'input_index': index, 'code': code})
            if 'manifest_sha256' in row and row['manifest_sha256'] != actual.get('manifest_sha256'):
                issues.append({'side': 'comparison', 'input_index': index, 'code': 'BINDING_MANIFEST_PIN_MISMATCH'})
    status = 'BLOCKED' if issues else ('UNKNOWN' if missing else 'MATCH')
    if not issues and missing:
        issues = [{'side': 'expected', 'input_index': i, 'code': 'LEGACY_MANIFEST_PIN_NOT_RECORDED'}
                  for i, row in enumerate(expected['bindings']) if 'manifest_sha256' not in row]
    return dict(schema_version=1, scope='ORDERED_BINDING_DECLARATIONS_ONLY', status=status,
                issues=issues, expected_bindings_sha256=digest,
                expected_binding_count=len(expected['bindings']) if valid_expected else None,
                supplied_binding_count=len(supplied['bindings']) if valid_supplied else None,
                missing_expected_manifest_pin_count=missing if valid_expected and valid_supplied else None,
                declarations_match=status == 'MATCH', network_requests=0, source_files_written=0,
                database_calls=0, resolver_calls=0, executor_calls=0,
                **{key: False for key in _FALSE})
