"""Manual full Job draft handoff RFC transport; never submits a Job."""
import hashlib
import json
import math
from decimal import Decimal, DecimalException

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from .execution_input_binding import _sha, _text
from .workflow_job_request_handoff import compare_workflow_job_request_handoff, _bounded_json
from .workflow_job_registration_handoff import (
    compare_workflow_job_registration_handoff, validate_registration_handoff_response,
)
from .workflow_node_input_handoff import _FALSE_FLAGS, _digest
from .workflow_node_input_handoff_api import (
    MAX_BODY_BYTES, MAX_INNER_BYTES, IO_KEYS, RequestTooLarge, _strict_json,
    _check_depth, _reject, _require, _exact, _enum, validate_handoff_response,
)

ENVELOPE_KEYS = {'workflow_request_json', 'pinned_workflow_request_sha256',
    'selected_node_id', 'full_job_request_json'}
FALSE_FLAGS = _FALSE_FLAGS + ('full_job_origin_verified', 'full_job_pin_verified',
    'agent_capability_verified', 'model_verified')
RESULT_KEYS = {'schema_version', 'scope', 'status', 'declarations_match',
    'full_job_request_sha256', 'extracted_metadata_sha256', 'full_job_schema_validated',
    'bbox_numeric_order_validated', 'validator_attempted', 'validator_status',
    'schema_files_read', 'comparator_calls', 'metadata_comparison', 'issues'} | IO_KEYS | set(FALSE_FLAGS)
CODES = {'FULL_JOB_JSON_BOUNDS_INVALID', 'WORKFLOW_JSON_BOUNDS_INVALID',
    'FULL_JOB_SCHEMA_INVALID', 'RESOURCE_UNAVAILABLE', 'FULL_JOB_BBOX_INVALID',
    'MODEL_REFERENCE_INVALID', 'MODEL_VERSION_NOT_PINNED', 'WORKFLOW_RUN_ID_MISMATCH',
    'METADATA_HANDOFF_BLOCKED'}


def _job_integer(token):
    if len(token) > 128:
        raise RequestTooLarge('Numeric token limit.')
    # Bound before int conversion; no quoted scalar coercion.
    if len(token.lstrip('-')) > 16:
        raise ValueError('Integer range.')
    value = int(token)
    if value.bit_length() > 53 or abs(value) > 9007199254740991:
        raise ValueError('Integer range.')
    return value


def _job_float(token):
    if len(token) > 128:
        raise RequestTooLarge('Numeric token limit.')
    value = float(token)
    if not math.isfinite(value):
        raise ValueError('Finite representable number required.')
    if value == 0:
        try:
            is_zero = Decimal(token).is_zero()
        except DecimalException as error:
            raise ValueError('Unsupported numeric exponent.') from error
        if not is_zero:
            raise ValueError('Finite representable number required.')
    return value


def _job_pairs(pairs):
    if len(pairs) > 16384:
        raise RequestTooLarge('Object budget.')
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate key.')
        if len(key) > 256:
            raise RequestTooLarge('Key budget.')
        result[key] = value
    return result


def _strict_full_job(text):
    _check_depth(text, 24)
    value = json.loads(text, object_pairs_hook=_job_pairs, parse_int=_job_integer,
        parse_float=_job_float, parse_constant=_reject)
    stack, atoms = [value], 0
    while stack:
        current = stack.pop(); atoms += 1
        if atoms > 16384:
            raise RequestTooLarge('Atom budget.')
        if type(current) is dict:
            stack.extend(current.keys()); stack.extend(current.values())
        elif type(current) is list:
            stack.extend(current)
        elif type(current) is str:
            if len(current) > 4096:
                raise RequestTooLarge('String budget.')
            if any(0xD800 <= ord(c) <= 0xDFFF for c in current):
                raise ValueError('Invalid Unicode.')
    return value


def parse_full_job_handoff_request(raw):
    if type(raw) is not bytes:
        raise ValueError('Request bytes required.')
    if len(raw) > MAX_BODY_BYTES:
        raise RequestTooLarge('Body budget.')
    envelope = _strict_json(raw.decode('utf-8', errors='strict'), inner=False)
    if type(envelope) is not dict:
        raise ValueError('Envelope shape.')
    if 'contract_version' in envelope:
        if (set(envelope) != ENVELOPE_KEYS | {'contract_version'}
                or type(envelope['contract_version']) is not int or envelope['contract_version'] != 2):
            raise ValueError('Envelope version.')
    elif set(envelope) != ENVELOPE_KEYS:
        raise ValueError('Envelope shape.')
    if not _sha(envelope['pinned_workflow_request_sha256']) or not _text(envelope['selected_node_id']):
        raise ValueError('Identity.')
    for key in ('workflow_request_json', 'full_job_request_json'):
        text = envelope[key]
        if type(text) is not str:
            raise ValueError('Source text.')
        if len(text) > MAX_INNER_BYTES or len(text.encode('utf-8')) > MAX_INNER_BYTES:
            raise RequestTooLarge('Source budget.')
    return (envelope, _strict_json(envelope['workflow_request_json'], inner=True),
        _strict_full_job(envelope['full_job_request_json']))


def validate_full_job_handoff_response(result, envelope, workflow, job):
    _exact(result, RESULT_KEYS)
    _require(type(result['schema_version']) is int and result['schema_version'] == 1)
    _require(_enum(result['scope'], {'WORKFLOW_NODE_TO_FULL_JOB_DRAFT_HANDOFF_ONLY'}))
    _require(_enum(result['status'], {'MATCH', 'BLOCKED'}))
    _require(type(result['declarations_match']) is bool and result['declarations_match'] == (result['status'] == 'MATCH'))
    for key in FALSE_FLAGS:
        _require(result[key] is False)
    for key in IO_KEYS:
        _require(type(result[key]) is int and result[key] == 0)
    _require(result['schema_files_read'] is None)
    for key in ('full_job_schema_validated', 'bbox_numeric_order_validated', 'validator_attempted'):
        _require(type(result[key]) is bool)
    _require(type(result['comparator_calls']) is int and result['comparator_calls'] in (0, 1))
    _require(_enum(result['validator_status'], {'NOT_RUN', 'INVALID', 'VALID', 'RESOURCE_UNAVAILABLE'}))
    for key in ('full_job_request_sha256', 'extracted_metadata_sha256'):
        _require(result[key] is None or _sha(result[key]))
    issues = result['issues']
    _require(type(issues) is list and len(issues) <= 1)
    for issue in issues:
        _exact(issue, {'code'}); _require(_enum(issue['code'], CODES))
    _require((result['status'] == 'MATCH') == (not issues))
    code = issues[0]['code'] if issues else None
    full_bounded = _bounded_json(job)
    workflow_bounded = _bounded_json(workflow) if full_bounded else False
    attempted = full_bounded and workflow_bounded and type(job) is dict
    _require(result['validator_attempted'] == attempted)
    _require(result['full_job_request_sha256'] == (_digest(job) if attempted else None))
    if not attempted:
        expected = ('FULL_JOB_JSON_BOUNDS_INVALID' if not full_bounded else
            'WORKFLOW_JSON_BOUNDS_INVALID' if not workflow_bounded else 'FULL_JOB_SCHEMA_INVALID')
        _require(code == expected and result['validator_status'] == 'NOT_RUN')
    else:
        _require(result['validator_status'] != 'NOT_RUN')
    valid = result['validator_status'] == 'VALID'
    _require(result['full_job_schema_validated'] == valid)
    if result['validator_status'] == 'INVALID':
        _require(code == 'FULL_JOB_SCHEMA_INVALID')
    if result['validator_status'] == 'RESOURCE_UNAVAILABLE':
        _require(code == 'RESOURCE_UNAVAILABLE')
    bbox_valid = False
    if valid:
        aoi = job.get('aoi')
        _require(type(aoi) is dict and type(aoi.get('bbox')) is list and len(aoi['bbox']) == 4)
        bbox = aoi['bbox']
        bbox_valid = all(type(v) in (int, float) and math.isfinite(v) for v in bbox) and bbox[0] < bbox[2] and bbox[1] < bbox[3]
    _require(result['bbox_numeric_order_validated'] == bbox_valid)
    if valid and not bbox_valid:
        _require(code == 'FULL_JOB_BBOX_INVALID')
    expected_early = None
    if bbox_valid:
        model = job.get('model_ref')
        if model is not None:
            _require(type(model) is dict and {'id', 'version'} <= model.keys())
            if any(not _text(model[k]) for k in ('id', 'version')) or ('role' in model and not _text(model['role'])):
                expected_early = 'MODEL_REFERENCE_INVALID'
            elif model['version'].strip().lower() in {'latest', 'current'}:
                expected_early = 'MODEL_VERSION_NOT_PINNED'
        context = job.get('execution_context')
        _require(type(context) is dict and 'trace_id' in context)
        if expected_early is None and 'workflow_run_id' in context and (type(workflow) is not dict or context['workflow_run_id'] != workflow.get('workflow_run_id')):
            expected_early = 'WORKFLOW_RUN_ID_MISMATCH'
    compare = bbox_valid and expected_early is None
    _require(result['comparator_calls'] == int(compare))
    if expected_early is not None:
        _require(code == expected_early)
    if not compare:
        _require(result['metadata_comparison'] is None and result['extracted_metadata_sha256'] is None)
    else:
        _require({'agent_id', 'capability_id', 'input_refs'} <= job.keys())
        metadata = dict(agent_id=job['agent_id'], capability_id=job['capability_id'],
            execution_context={'trace_id':job['execution_context']['trace_id']}, input_refs=job['input_refs'])
        _require(result['extracted_metadata_sha256'] == _digest(metadata))
        validate_handoff_response(result['metadata_comparison'], envelope, workflow, metadata)
        _require(result['status'] == result['metadata_comparison']['status'])
        _require(code == ('METADATA_HANDOFF_BLOCKED' if result['status'] == 'BLOCKED' else None))
    return result


def _error(code, status):
    messages = {'INVALID_REQUEST':'Invalid full Job handoff request.',
        'REQUEST_TOO_LARGE':'Full Job handoff request exceeds limits.',
        'RESOURCE_UNAVAILABLE':'Full Job handoff comparison is unavailable.'}
    return JSONResponse({'error':{'code':code, 'message':messages[code], 'retryable':False}},
        status_code=status, headers={'Cache-Control':'no-store'})


def create_workflow_job_request_handoff_router():
    router = APIRouter()

    @router.post('/v1/workflows/full-job-input-handoff')
    async def handoff(request: Request):
        try:
            chunks, size = [], 0
            async for chunk in request.stream():
                size += len(chunk)
                if size > MAX_BODY_BYTES:
                    raise RequestTooLarge('Body budget.')
                if chunk:
                    chunks.append(chunk)
            raw = b''.join(chunks)
            envelope, workflow, job = parse_full_job_handoff_request(raw)
        except RequestTooLarge:
            return _error('REQUEST_TOO_LARGE', 413)
        except (ValueError, UnicodeError, RecursionError):
            return _error('INVALID_REQUEST', 400)
        except Exception:
            return _error('RESOURCE_UNAVAILABLE', 503)
        try:
            version_two = envelope.get('contract_version') == 2
            compare = compare_workflow_job_registration_handoff if version_two else compare_workflow_job_request_handoff
            result = await run_in_threadpool(compare, workflow,
                envelope['pinned_workflow_request_sha256'], envelope['selected_node_id'], job)
            if version_two:
                validate_registration_handoff_response(result, envelope, workflow, job, validate_full_job_handoff_response)
                inner = result['full_job_comparison']
            else:
                validate_full_job_handoff_response(result, envelope, workflow, job)
                inner = result
            if inner['validator_status'] == 'RESOURCE_UNAVAILABLE':
                return _error('RESOURCE_UNAVAILABLE', 503)
            return JSONResponse({'extension':('greenblue.workflow-full-job-input-handoff.rfc2' if version_two
                                             else 'greenblue.workflow-full-job-input-handoff.rfc1'),
                'approval_status':'INTERNAL_REVIEW', 'present_in_upstream_openapi':False,
                'request_sha256':hashlib.sha256(raw).hexdigest(), 'result':result},
                headers={'Cache-Control':'no-store'})
        except Exception:
            return _error('RESOURCE_UNAVAILABLE', 503)

    return router
