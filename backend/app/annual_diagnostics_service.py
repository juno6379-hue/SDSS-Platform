"""Bounded bytes-to-summary service; no HTTP routes or raw diagnostic disclosure."""
import hashlib
import json

from .ml.annual_quality_mask_diagnostics import _snapshot_request
from .ml.annual_mask_policy import _policy, _counts, _keys, FALSE_FIELDS, inspect_annual_mask_policy

MAX_REQUEST_BYTES = 16384
SCOPE = 'LCLUC_ANNUAL_DIAGNOSTIC_SUMMARY_READ_ONLY'
CAPABILITY = 'landcover.input_diagnostics'
PARENT_SCOPE = 'CALLER_EXPLICIT_ANNUAL_MASK_POLICY_READ_ONLY'


def _reject(_):
    raise ValueError('invalid JSON number')


def _integer(text):
    if len(text.lstrip('-')) > 16:
        raise ValueError('integer limit')
    value = int(text)
    if abs(value) > 2**53-1:
        raise ValueError('integer limit')
    return value


def _pairs(items):
    value = {}
    for key, item in items:
        if key in value:
            raise ValueError('duplicate')
        value[key] = item
    return value


def _parse(raw):
    if type(raw) is not bytes or len(raw) > MAX_REQUEST_BYTES:
        raise ValueError('bytes limit')
    text = raw.decode('utf-8', errors='strict')
    depth = 0; quoted = False; escaped = False
    for char in text:
        if quoted:
            if escaped: escaped = False
            elif char == '\\': escaped = True
            elif char == '"': quoted = False
        elif char == '"': quoted = True
        elif char in '[{':
            depth += 1
            if depth > 16: raise ValueError('depth')
        elif char in ']}': depth -= 1
    value = json.loads(text, object_pairs_hook=_pairs, parse_float=_reject, parse_int=_integer, parse_constant=_reject)
    stack = [value]; nodes = 0
    while stack:
        item = stack.pop(); nodes += 1
        if nodes > 4096: raise ValueError('nodes')
        if type(item) is dict: stack.extend(item.keys()); stack.extend(item.values())
        elif type(item) is list: stack.extend(item)
        elif type(item) is str:
            if len(item) > 512 or any(0xD800 <= ord(c) <= 0xDFFF for c in item):
                raise ValueError('text')
    return value


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(',', ':')).encode('utf-8')


def _summary():
    result = {'schema_version': 1, 'scope': SCOPE, 'status': 'INVALID_REQUEST', 'request_sha256': None,
        'blocking_stage': 'REQUEST', 'issue': {'code': 'INVALID_REQUEST', 'year': None}, 'per_year_observations': [],
        'caller_policy_evaluated': False, 'caller_policy_met': False, 'artifact_bytes_verified': False}
    result.update({key: False for key in FALSE_FIELDS})
    return result


def _need(condition):
    if not condition: raise ValueError('invalid output')


def _project(parent, policy, rows, result):
    keys = {'schema_version', 'scope', 'status', 'issue', 'parent_annual_observation', 'policy',
        'per_year_observations', 'annual_observation_calls', 'caller_policy_evaluated', 'caller_policy_met',
        'artifact_bytes_verified', *FALSE_FIELDS}
    _need(_keys(parent, keys))
    _need(type(parent['schema_version']) is int and parent['schema_version'] == 1
        and type(parent['scope']) is str and parent['scope'] == PARENT_SCOPE)
    _need(all(parent[key] is False for key in FALSE_FIELDS))
    _need(_policy(parent['policy']) == policy)
    _need(type(parent['annual_observation_calls']) is int and parent['annual_observation_calls'] == 1)
    _need(all(type(parent[key]) is bool for key in ('caller_policy_evaluated', 'caller_policy_met', 'artifact_bytes_verified')))
    issue = parent['issue']
    _need(issue is None or (_keys(issue, ('code', 'field', 'year')) and type(issue['code']) is str and len(issue['code']) <= 128
        and type(issue['field']) is str and len(issue['field']) <= 128
        and (issue['year'] is None or (type(issue['year']) is int and issue['year'] in [row['year'] for row in rows]))))
    observations = parent['per_year_observations']
    _need(type(observations) is list and len(observations) == len(rows))
    safe = []
    for row, observation in zip(rows, observations):
        _need(_keys(observation, ('year', 'status', 'counts', 'policy_met'))
            and type(observation['year']) is int and observation['year'] == row['year']
            and type(observation['status']) is str and observation['status'] in ('NOT_CHECKED', 'MET', 'NOT_MET'))
        safe.append({'year': row['year'], 'status': observation['status'], 'counts': observation['counts'], 'policy_met': observation['policy_met']})
    status = parent['status']
    _need(type(status) is str)
    if status in ('ANNUAL_DIAGNOSTICS_BLOCKED', 'POLICY_INPUT_BLOCKED'):
        _need(issue is not None and parent['caller_policy_evaluated'] is False and parent['caller_policy_met'] is False
            and parent['artifact_bytes_verified'] is False)
        _need(all(row['status'] == 'NOT_CHECKED' and row['counts'] is None and row['policy_met'] is None for row in safe))
        result.update(status='SOURCE_BLOCKED', blocking_stage='ANNUAL' if status == 'ANNUAL_DIAGNOSTICS_BLOCKED' else 'COUNTS',
            issue={'code': 'SOURCE_BLOCKED', 'year': issue['year']}, per_year_observations=safe)
        return result
    _need(status in ('CALLER_POLICY_MET_UNVERIFIED', 'CALLER_POLICY_NOT_MET') and parent['caller_policy_evaluated'] is True)
    first = None
    for row in safe:
        count = _counts(row['counts'])
        met = count['valid_pixels'] * policy['minimum_valid_denominator'] >= count['total_pixels'] * policy['minimum_valid_numerator']
        _need(type(row['policy_met']) is bool and row['policy_met'] is met and row['status'] == ('MET' if met else 'NOT_MET'))
        row['counts'] = count
        if not met and first is None: first = row['year']
    met = first is None
    _need(parent['caller_policy_met'] is met and parent['artifact_bytes_verified'] is met
        and status == ('CALLER_POLICY_MET_UNVERIFIED' if met else 'CALLER_POLICY_NOT_MET'))
    _need(issue is None if met else issue is not None and issue['year'] == first)
    result.update(status=status, blocking_stage=None if met else 'POLICY', issue=None if met else {'code':'CALLER_POLICY_NOT_MET','year':first},
        per_year_observations=safe, caller_policy_evaluated=True, caller_policy_met=met, artifact_bytes_verified=met)
    return result


def read_annual_diagnostic_service(store, request_json: bytes):
    """One135 invocation, safe summary only. Does not install any API endpoint."""
    result = _summary()
    try:
        request = _parse(request_json)
        _need(_keys(request, ('schema_version', 'capability', 'model_ref', 'training_report_sha256', 'requested_years', 'policy'))
            and type(request['schema_version']) is int and request['schema_version'] == 1
            and request['capability'] == CAPABILITY)
        policy = _policy(request['policy'])
        ref, rows, _ = _snapshot_request(request['model_ref'], request['training_report_sha256'], request['requested_years'])
        fixed = {'schema_version': 1, 'capability': CAPABILITY, 'model_ref': ref,
            'training_report_sha256': request['training_report_sha256'], 'requested_years': rows, 'policy': policy}
        result['request_sha256'] = hashlib.sha256(_canonical(fixed)).hexdigest()
    except Exception:
        return result
    try:
        core_ref, core_rows, _ = _snapshot_request(ref, fixed['training_report_sha256'], rows)
        parent = inspect_annual_mask_policy(store, core_ref, fixed['training_report_sha256'], core_rows, _policy(policy))
        return _project(parent, policy, rows, result)
    except Exception:
        failure = _summary()
        failure.update(status='OUTPUT_INVALID', request_sha256=result['request_sha256'], blocking_stage='OUTPUT',
            issue={'code':'OUTPUT_INVALID','year':None})
        return failure
