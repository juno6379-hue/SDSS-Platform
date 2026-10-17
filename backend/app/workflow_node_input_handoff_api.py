"""Bounded strict-JSON RFC transport for pure Workflow input declarations.

Never constructs a Job or reads a Store. Authentication is inherited from main.
"""
import hashlib
import json

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from .execution_input_binding import _sha, _text
from .workflow_node_input_handoff import compare_workflow_node_input_handoff, _FALSE_FLAGS, _digest, _workflow_error

MAX_BODY_BYTES = 1048576
MAX_INNER_BYTES = 524288
MAX_ATOMS = 32768
ENVELOPE_KEYS = {'workflow_request_json', 'pinned_workflow_request_sha256',
    'selected_node_id', 'proposed_job_metadata_json'}
IO_KEYS = {'network_requests', 'source_files_read', 'source_files_written',
    'database_calls', 'registry_calls', 'resolver_calls', 'executor_calls'}
HASH_KEYS = {'workflow_request_sha256', 'pinned_workflow_request_sha256',
    'selected_node_sha256', 'expected_metadata_sha256', 'proposed_metadata_sha256'}
RESULT_KEYS = {'schema_version', 'scope', 'status', 'declarations_match',
    'selected_node_index', 'expected_input_count', 'proposed_input_count', 'issues'} | HASH_KEYS | IO_KEYS | set(_FALSE_FLAGS)
CODES = {'WORKFLOW_PIN_INVALID', 'SELECTED_NODE_INVALID', 'WORKFLOW_SCHEMA_INVALID',
    'WORKFLOW_IDENTITY_INVALID', 'WORKFLOW_POLICY_INVALID', 'WORKFLOW_NODE_COUNT_INVALID',
    'NODE_SCHEMA_INVALID', 'NODE_IDENTITY_INVALID', 'NODE_ID_AMBIGUOUS', 'NODE_POLICY_INVALID',
    'NODE_DEPENDENCY_INVALID', 'WORKFLOW_INPUT_LIMIT', 'INPUT_COUNT_INVALID',
    'INPUT_SCHEMA_INVALID', 'INPUT_IDENTITY_INVALID', 'INPUT_VERSION_NOT_PINNED',
    'INPUT_SHA_INVALID', 'INPUT_ROLE_INVALID', 'INPUT_URI_INVALID', 'INPUT_IDENTITY_CONFLICT',
    'WORKFLOW_PIN_MISMATCH', 'SELECTED_NODE_NOT_FOUND', 'SELECTED_INPUTS_REQUIRED',
    'PROPOSED_METADATA_SCHEMA_INVALID', 'PROPOSED_IDENTITY_INVALID', 'AGENT_ID_MISMATCH',
    'CAPABILITY_ID_MISMATCH', 'TRACE_ID_MISMATCH', 'INPUT_COUNT_MISMATCH',
    'INPUT_ID_MISMATCH', 'INPUT_VERSION_MISMATCH', 'INPUT_SHA256_MISMATCH',
    'INPUT_ROLE_MISMATCH', 'INPUT_URI_MISMATCH'}


class RequestTooLarge(ValueError):
    """Transport byte/depth/atom budget exceeded."""


def _reject(_value):
    raise ValueError('Invalid JSON scalar.')


def _integer(value):
    if len(value.lstrip('-')) > 10:
        raise RequestTooLarge('Integer digit budget exceeded.')
    parsed = int(value)
    if not -2147483648 <= parsed <= 2147483647:
        raise ValueError('Invalid JSON integer.')
    return parsed


def _pairs(pairs):
    if len(pairs) > 128:
        raise RequestTooLarge('Object key budget exceeded.')
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key.')
        result[key] = value
    return result


def _check_depth(text, maximum):
    depth, string, escaped = 0, False, False
    for char in text:
        if string:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '"':
                string = False
        elif char == '"':
            string = True
        elif char in '{[':
            depth += 1
            if depth > maximum:
                raise RequestTooLarge('JSON depth budget exceeded.')
        elif char in '}]':
            depth -= 1


def _strict_json(text, *, inner):
    _check_depth(text, 12 if inner else 8)
    value = json.loads(text, object_pairs_hook=_pairs, parse_constant=_reject,
        parse_float=_reject, parse_int=_integer)
    stack, atoms = [value], 0
    while stack:
        current = stack.pop()
        atoms += 1
        if atoms > MAX_ATOMS:
            raise RequestTooLarge('JSON atom budget exceeded.')
        if type(current) is dict:
            stack.extend(current.keys()); stack.extend(current.values())
        elif type(current) is list:
            stack.extend(current)
        elif type(current) is str:
            if any(0xD800 <= ord(c) <= 0xDFFF for c in current):
                raise ValueError('Invalid JSON Unicode.')
            if inner and (len(current) > 256 or any(ord(c) < 32 or 127 <= ord(c) <= 159 for c in current)):
                raise ValueError('Invalid JSON text.')
    return value


def parse_handoff_request(raw):
    """Strict transport parser. Does not normalize either supplied source text."""
    if type(raw) is not bytes:
        raise ValueError('Invalid request bytes.')
    if len(raw) > MAX_BODY_BYTES:
        raise RequestTooLarge('Body budget exceeded.')
    envelope = _strict_json(raw.decode('utf-8', errors='strict'), inner=False)
    if type(envelope) is not dict or len(envelope) != 4 or set(envelope) != ENVELOPE_KEYS:
        raise ValueError('Invalid request envelope.')
    if not _sha(envelope['pinned_workflow_request_sha256']) or not _text(envelope['selected_node_id']):
        raise ValueError('Invalid request identity.')
    parsed = []
    for key in ('workflow_request_json', 'proposed_job_metadata_json'):
        text = envelope[key]
        if type(text) is not str:
            raise ValueError('Invalid source text.')
        if len(text) > MAX_INNER_BYTES or len(text.encode('utf-8')) > MAX_INNER_BYTES:
            raise RequestTooLarge('Source text budget exceeded.')
        parsed.append(_strict_json(text, inner=True))
    return envelope, parsed[0], parsed[1]


def _require(condition):
    if not condition:
        raise ValueError('Invalid safe response.')


def _exact(value, keys):
    _require(type(value) is dict and len(value) == len(keys) and set(value) == keys)


def _enum(value, allowed):
    return type(value) is str and len(value) <= 80 and value in allowed


def _index(value, maximum):
    return type(value) is int and 0 <= value <= maximum


def validate_handoff_response(result, envelope, workflow, proposal):
    """Reject unsafe, retargeted, or contradictory core output before serializing."""
    _exact(result, RESULT_KEYS)
    _require(type(result['schema_version']) is int and result['schema_version'] == 1)
    _require(_enum(result['scope'], {'WORKFLOW_NODE_TO_PROPOSED_JOB_INPUT_DECLARATIONS_ONLY'}))
    _require(_enum(result['status'], {'MATCH', 'BLOCKED'}))
    _require(type(result['declarations_match']) is bool and result['declarations_match'] == (result['status'] == 'MATCH'))
    for key in _FALSE_FLAGS:
        _require(result[key] is False)
    for key in IO_KEYS:
        _require(type(result[key]) is int and result[key] == 0)
    for key in HASH_KEYS:
        _require(result[key] is None or _sha(result[key]))
    _require(result['pinned_workflow_request_sha256'] == envelope['pinned_workflow_request_sha256'])
    _require(result['selected_node_sha256'] == _digest(envelope['selected_node_id']))
    if result['workflow_request_sha256'] is not None:
        _require(result['workflow_request_sha256'] == _digest(workflow))
    node_index = result['selected_node_index']
    _require(node_index is None or _index(node_index, 127))
    for key in ('expected_input_count', 'proposed_input_count'):
        _require(result[key] is None or (type(result[key]) is int and 1 <= result[key] <= 64))
    _require((result['expected_input_count'] is None) == (result['expected_metadata_sha256'] is None))
    _require((result['proposed_input_count'] is None) == (result['proposed_metadata_sha256'] is None))
    if result['expected_metadata_sha256'] is not None:
        _require(result['workflow_request_sha256'] == result['pinned_workflow_request_sha256'])
        _require(node_index is not None and type(workflow) is dict and type(workflow.get('nodes')) is list
            and node_index < len(workflow['nodes']))
        node = workflow['nodes'][node_index]
        _require(type(node) is dict and node.get('node_id') == envelope['selected_node_id'])
        expected = dict(agent_id=node['agent_id'], capability_id=node['capability_id'],
            execution_context={'trace_id':workflow['trace_id']}, input_refs=node['input_bindings'])
        _require(result['expected_metadata_sha256'] == _digest(expected)
            and result['expected_input_count'] == len(node['input_bindings']))
    else:
        _require(node_index is None)
    if result['proposed_metadata_sha256'] is not None:
        _require(result['expected_metadata_sha256'] is not None and type(proposal) is dict
            and result['proposed_metadata_sha256'] == _digest(proposal)
            and result['proposed_input_count'] == len(proposal['input_refs']))
    issues = result['issues']
    _require(type(issues) is list and len(issues) <= 324)
    _require((result['status'] == 'MATCH') == (len(issues) == 0))
    seen = set()
    for issue in issues:
        _exact(issue, {'code', 'side', 'node_index', 'input_index'})
        _require(_enum(issue['code'], CODES) and _enum(issue['side'], {'caller', 'workflow', 'proposal', 'comparison'}))
        _require(issue['node_index'] is None or _index(issue['node_index'], 127))
        _require(issue['input_index'] is None or _index(issue['input_index'], 63))
        if issue['side'] == 'caller':
            _require(issue['node_index'] is None and issue['input_index'] is None)
        if issue['side'] == 'workflow' and issue['node_index'] is not None:
            _require(type(workflow) is dict and type(workflow.get('nodes')) is list
                and issue['node_index'] < len(workflow['nodes']))
        if issue['side'] == 'workflow' and issue['input_index'] is not None:
            _require(issue['node_index'] is not None)
            issue_node = workflow['nodes'][issue['node_index']]
            _require(type(issue_node) is dict and type(issue_node.get('input_bindings')) is list
                and issue['input_index'] < len(issue_node['input_bindings']))
        if issue['side'] == 'proposal':
            _require(issue['node_index'] is None)
            if issue['input_index'] is not None:
                _require(type(proposal) is dict and type(proposal.get('input_refs')) is list
                    and issue['input_index'] < len(proposal['input_refs']))
        signature = (issue['code'], issue['side'], issue['node_index'], issue['input_index'])
        _require(signature not in seen); seen.add(signature)
        if issue['side'] == 'comparison' and issue['input_index'] is not None:
            _require(node_index is not None and issue['node_index'] == node_index
                and result['expected_input_count'] is not None and result['proposed_input_count'] is not None
                and issue['input_index'] < min(result['expected_input_count'], result['proposed_input_count']))
    if result['status'] == 'MATCH':
        _require(_workflow_error(workflow) is None)
        _require(result['workflow_request_sha256'] == result['pinned_workflow_request_sha256']
            and result['expected_metadata_sha256'] is not None
            and result['expected_metadata_sha256'] == result['proposed_metadata_sha256']
            and result['expected_input_count'] == result['proposed_input_count'])
    return result


def _error(code, status):
    messages = {'INVALID_REQUEST':'Invalid handoff request.', 'REQUEST_TOO_LARGE':'Handoff request exceeds limits.',
        'RESOURCE_UNAVAILABLE':'Handoff comparison is unavailable.'}
    return JSONResponse({'error':{'code':code, 'message':messages[code], 'retryable':False}},
        status_code=status, headers={'Cache-Control':'no-store'})


def create_workflow_node_input_handoff_router():
    router = APIRouter()

    @router.post('/v1/workflows/node-input-handoff')
    async def handoff(request: Request):
        try:
            chunks, size = [], 0
            async for chunk in request.stream():
                size += len(chunk)
                if size > MAX_BODY_BYTES:
                    raise RequestTooLarge('Body budget exceeded.')
                if chunk:
                    chunks.append(chunk)
            raw = b''.join(chunks)
            envelope, workflow, proposal = parse_handoff_request(raw)
        except RequestTooLarge:
            return _error('REQUEST_TOO_LARGE', 413)
        except (ValueError, UnicodeError, RecursionError):
            return _error('INVALID_REQUEST', 400)
        except Exception:
            return _error('RESOURCE_UNAVAILABLE', 503)
        try:
            result = await run_in_threadpool(compare_workflow_node_input_handoff, workflow,
                envelope['pinned_workflow_request_sha256'], envelope['selected_node_id'], proposal)
            validate_handoff_response(result, envelope, workflow, proposal)
            return JSONResponse({'extension':'greenblue.workflow-node-input-handoff.rfc1',
                'approval_status':'INTERNAL_REVIEW', 'present_in_upstream_openapi':False,
                'request_sha256':hashlib.sha256(raw).hexdigest(), 'result':result},
                headers={'Cache-Control':'no-store'})
        except Exception:
            return _error('RESOURCE_UNAVAILABLE', 503)

    return router
