"""Bounded manual Workflow/model-record observation; no Store or Job access."""
import hashlib

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from .execution_input_binding import _sha, _text
from .model_reference_record_comparison import compare_model_reference_record
from .workflow_job_model_record_handoff import compare_workflow_job_model_record_handoff
from .workflow_job_request_handoff_api import _strict_full_job, validate_full_job_handoff_response
from .workflow_node_input_handoff_api import (
    MAX_BODY_BYTES, MAX_INNER_BYTES, RequestTooLarge, _strict_json,
    _exact, _require, _enum,
)


ENVELOPE_KEYS = {'workflow_request_json', 'pinned_workflow_request_sha256',
                 'selected_node_id', 'full_job_request_json'}
FALSE_FLAGS = ('authority_verified', 'artifact_bytes_verified', 'execution_authorized',
               'scientific_accuracy_validated', 'model_verified')
RESULT_KEYS = {'schema_version', 'scope', 'status', 'full_job_comparison',
    'model_reference_comparison', 'identity_projection_performed', 'model_comparison_calls', *FALSE_FLAGS}


def parse_workflow_model_record_request(raw):
    if type(raw) is not bytes:
        raise ValueError('Request bytes required.')
    if len(raw) > MAX_BODY_BYTES:
        raise RequestTooLarge('Body budget.')
    envelope = _strict_json(raw.decode('utf-8', errors='strict'), inner=False)
    if type(envelope) is not dict or set(envelope) not in (ENVELOPE_KEYS, ENVELOPE_KEYS | {'model_record_json'}):
        raise ValueError('Envelope shape.')
    if not _sha(envelope['pinned_workflow_request_sha256']) or not _text(envelope['selected_node_id']):
        raise ValueError('Identity.')
    for key in ('workflow_request_json', 'full_job_request_json', 'model_record_json'):
        if key not in envelope:
            continue
        value = envelope[key]
        if type(value) is not str:
            raise ValueError('Source text.')
        if len(value) > MAX_INNER_BYTES or len(value.encode('utf-8')) > MAX_INNER_BYTES:
            raise RequestTooLarge('Source budget.')
    workflow = _strict_json(envelope['workflow_request_json'], inner=True)
    job = _strict_full_job(envelope['full_job_request_json'])
    record = _strict_full_job(envelope['model_record_json']) if 'model_record_json' in envelope else None
    return envelope, workflow, job, record


def _same_typed_value(actual, expected):
    """Compare the small trusted expected shape; reject bool/int equivalence."""
    if type(actual) is not type(expected):
        return False
    if type(expected) is dict:
        return (len(actual) == len(expected) and actual.keys() == expected.keys()
                and all(_same_typed_value(actual[key], value) for key, value in expected.items()))
    if type(expected) is list:
        return len(actual) == len(expected) and all(_same_typed_value(a, e) for a, e in zip(actual, expected))
    return type(expected) in (str, int, bool, type(None)) and actual == expected


def validate_workflow_model_record_response(result, envelope, workflow, job, record):
    _exact(result, RESULT_KEYS)
    _require(type(result['schema_version']) is int and result['schema_version'] == 1)
    _require(_enum(result['scope'], {'WORKFLOW_FULL_JOB_MODEL_RECORD_OBSERVATION_ONLY'}))
    _require(_enum(result['status'], {'HANDOFF_BLOCKED', 'MODEL_REFERENCE_ABSENT', 'MODEL_REFERENCE_OBSERVED'}))
    _require(type(result['identity_projection_performed']) is bool)
    _require(type(result['model_comparison_calls']) is int and result['model_comparison_calls'] in (0, 1))
    for field in FALSE_FLAGS:
        _require(result[field] is False)
    inner = result['full_job_comparison']
    validate_full_job_handoff_response(inner, envelope, workflow, job)
    observed = inner['status'] == 'MATCH' and 'model_ref' in job
    expected_status = ('HANDOFF_BLOCKED' if inner['status'] != 'MATCH'
                       else 'MODEL_REFERENCE_OBSERVED' if observed else 'MODEL_REFERENCE_ABSENT')
    _require(result['status'] == expected_status)
    _require(result['identity_projection_performed'] is observed)
    _require(result['model_comparison_calls'] == int(observed))
    if not observed:
        _require(result['model_reference_comparison'] is None)
    else:
        identity = {key: job['model_ref'][key] for key in ('id', 'version', 'sha256')}
        expected = compare_model_reference_record(identity, record)
        _require(_same_typed_value(result['model_reference_comparison'], expected))
    return result


def _compare_and_validate(envelope, workflow, job, record):
    result = compare_workflow_job_model_record_handoff(workflow,
        envelope['pinned_workflow_request_sha256'], envelope['selected_node_id'], job, record)
    return validate_workflow_model_record_response(result, envelope, workflow, job, record)


def _error(code, status):
    messages = {
        'INVALID_REQUEST': 'Invalid Workflow model-record handoff request.',
        'REQUEST_TOO_LARGE': 'Workflow model-record handoff request exceeds limits.',
        'RESOURCE_UNAVAILABLE': 'Workflow model-record observation is unavailable.',
    }
    return JSONResponse({'error': {'code': code, 'message': messages[code], 'retryable': False}},
                        status_code=status, headers={'Cache-Control': 'no-store'})


def create_workflow_job_model_record_handoff_router():
    router = APIRouter()

    @router.post('/v1/workflows/full-job-model-record-handoff')
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
            envelope, workflow, job, record = parse_workflow_model_record_request(raw)
        except RequestTooLarge:
            return _error('REQUEST_TOO_LARGE', 413)
        except (ValueError, UnicodeError, RecursionError):
            return _error('INVALID_REQUEST', 400)
        except Exception:
            return _error('RESOURCE_UNAVAILABLE', 503)
        try:
            result = await run_in_threadpool(_compare_and_validate, envelope, workflow, job, record)
            if result['full_job_comparison']['validator_status'] == 'RESOURCE_UNAVAILABLE':
                return _error('RESOURCE_UNAVAILABLE', 503)
            return JSONResponse({
                'extension': 'greenblue.workflow-full-job-model-record-handoff.rfc1',
                'approval_status': 'INTERNAL_REVIEW', 'present_in_upstream_openapi': False,
                'request_sha256': hashlib.sha256(raw).hexdigest(), 'result': result,
            }, headers={'Cache-Control': 'no-store'})
        except Exception:
            return _error('RESOURCE_UNAVAILABLE', 503)

    return router
