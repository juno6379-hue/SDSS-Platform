"""Bounded full Job draft schema check and selected Workflow metadata comparison.

This is not submission, authorization, source authentication, or execution.
"""
import json
import math
from .execution_input_binding import _text
from .schema_formats import create_format_checker

from jsonschema.exceptions import SchemaError

from .gmais_api import _job_request_validator
from .workflow_node_input_handoff import (
    _digest, _FALSE_FLAGS, compare_workflow_node_input_handoff,
)

_MAX_BYTES = 524288
_MAX_ATOMS = 16384
_MAX_DEPTH = 24
_MAX_STRING = 4096
_MAX_KEY = 256
_MAX_INT = 9007199254740991


def _draft_format_checker():
    """Compatibility wrapper; each draft keeps its own detached checker."""
    return create_format_checker()


def _bounded_json(value):
    """Exact builtins only; bound work before encoding, reject cycles and surrogates."""
    atoms = 0
    encoded_bytes = 0
    stack = [(value, 0, frozenset())]
    while stack:
        item, depth, ancestors = stack.pop()
        atoms += 1
        if atoms > _MAX_ATOMS or depth > _MAX_DEPTH:
            return False
        kind = type(item)
        if kind in (dict, list):
            if id(item) in ancestors or len(item) > _MAX_ATOMS:
                return False
            encoded_bytes += 2 + max(0, len(item) - 1)
            lineage = ancestors | {id(item)}
            if kind is dict:
                for key, child in item.items():
                    if (type(key) is not str or len(key) > _MAX_KEY
                            or any(0xD800 <= ord(c) <= 0xDFFF for c in key)):
                        return False
                    encoded_bytes += len(json.dumps(key, ensure_ascii=False).encode('utf-8')) + 1
                    atoms += 1
                    stack.append((child, depth + 1, lineage))
            else:
                stack.extend((child, depth + 1, lineage) for child in item)
            if atoms + len(stack) > _MAX_ATOMS:
                return False
        elif kind is str:
            if len(item) > _MAX_STRING or any(0xD800 <= ord(c) <= 0xDFFF for c in item):
                return False
            encoded_bytes += len(json.dumps(item, ensure_ascii=False).encode('utf-8'))
        elif kind is int:
            if item.bit_length() > 53 or not -_MAX_INT <= item <= _MAX_INT:
                return False
            encoded_bytes += len(str(item))
        elif kind is float:
            if not math.isfinite(item):
                return False
            encoded_bytes += len(repr(item))
        elif item is not None and kind is not bool:
            return False
        else:
            encoded_bytes += 5
        if encoded_bytes > _MAX_BYTES:
            return False
    return len(json.dumps(value, sort_keys=True, ensure_ascii=False,
        allow_nan=False, separators=(',', ':')).encode('utf-8')) <= _MAX_BYTES


def compare_workflow_job_request_handoff(workflow_request,
        pinned_workflow_request_sha256, selected_node_id, full_job_request):
    """Validate a caller draft, extract only metadata, invoke comparator 86 once.

    No full-Job pin argument exists: full_job_request_sha256 is an observation.
    A caller must retain/compare that hash itself to detect later draft changes.
    """
    result = dict(schema_version=1, scope='WORKFLOW_NODE_TO_FULL_JOB_DRAFT_HANDOFF_ONLY',
        status='BLOCKED', declarations_match=False, full_job_request_sha256=None,
        extracted_metadata_sha256=None, full_job_schema_validated=False,
        bbox_numeric_order_validated=False, validator_attempted=False,
        validator_status='NOT_RUN', schema_files_read=None, comparator_calls=0,
        metadata_comparison=None, issues=[], network_requests=0, source_files_read=0,
        source_files_written=0, database_calls=0, registry_calls=0,
        resolver_calls=0, executor_calls=0,
        **{key: False for key in _FALSE_FLAGS},
        full_job_origin_verified=False, full_job_pin_verified=False,
        agent_capability_verified=False, model_verified=False)

    def blocked(code):
        result['issues'].append({'code': code})
        return result

    if not _bounded_json(full_job_request):
        return blocked('FULL_JOB_JSON_BOUNDS_INVALID')
    if not _bounded_json(workflow_request):
        return blocked('WORKFLOW_JSON_BOUNDS_INVALID')
    if type(full_job_request) is not dict:
        return blocked('FULL_JOB_SCHEMA_INVALID')
    result['full_job_request_sha256'] = _digest(full_job_request)
    result['validator_attempted'] = True
    # The existing cached factory may read the vendored schema on its cold path.
    # No count is inferred from cache state, and raw exception text is not exposed.
    try:
        validator = _job_request_validator()
    except RuntimeError as error:
        if str(error) != 'GMAIS v0.2 job-request \uc6d0\ubb38 schema\ub97c \ucc3e\uc744 \uc218 \uc5c6\uc2b5\ub2c8\ub2e4.':
            raise
        result['validator_status'] = 'RESOURCE_UNAVAILABLE'
        return blocked('RESOURCE_UNAVAILABLE')
    except (OSError, UnicodeError, json.JSONDecodeError, SchemaError, MemoryError):
        result['validator_status'] = 'RESOURCE_UNAVAILABLE'
        return blocked('RESOURCE_UNAVAILABLE')
    try:
        draft_validator = validator.evolve(format_checker=_draft_format_checker())
        invalid = next(draft_validator.iter_errors(full_job_request), None) is not None
    except (OSError, MemoryError):
        result['validator_status'] = 'RESOURCE_UNAVAILABLE'
        return blocked('RESOURCE_UNAVAILABLE')
    if invalid:
        result['validator_status'] = 'INVALID'
        return blocked('FULL_JOB_SCHEMA_INVALID')
    result['validator_status'] = 'VALID'
    result['full_job_schema_validated'] = True
    bbox = full_job_request['aoi']['bbox']
    if (any(type(v) not in (int, float) or not math.isfinite(v) for v in bbox)
            or not bbox[0] < bbox[2] or not bbox[1] < bbox[3]):
        return blocked('FULL_JOB_BBOX_INVALID')
    result['bbox_numeric_order_validated'] = True
    model = full_job_request.get('model_ref')
    if model is not None:
        if any(not _text(model[key]) for key in ('id', 'version')) or ('role' in model and not _text(model['role'])):
            return blocked('MODEL_REFERENCE_INVALID')
        if model['version'].strip().lower() in {'latest', 'current'}:
            return blocked('MODEL_VERSION_NOT_PINNED')
    context = full_job_request['execution_context']
    if ('workflow_run_id' in context and (type(workflow_request) is not dict
            or context['workflow_run_id'] != workflow_request.get('workflow_run_id'))):
        return blocked('WORKFLOW_RUN_ID_MISMATCH')
    metadata = dict(agent_id=full_job_request['agent_id'],
        capability_id=full_job_request['capability_id'],
        execution_context={'trace_id': context['trace_id']},
        input_refs=full_job_request['input_refs'])
    result['extracted_metadata_sha256'] = _digest(metadata)
    result['comparator_calls'] = 1
    comparison = compare_workflow_node_input_handoff(workflow_request,
        pinned_workflow_request_sha256, selected_node_id, metadata)
    result['metadata_comparison'] = comparison
    if comparison['status'] == 'MATCH':
        result.update(status='MATCH', declarations_match=True)
    else:
        blocked('METADATA_HANDOFF_BLOCKED')
    return result
