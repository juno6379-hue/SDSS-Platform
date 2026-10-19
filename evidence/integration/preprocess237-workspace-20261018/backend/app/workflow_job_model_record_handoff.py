"""Opt-in full Job draft to supplied model record metadata observation.

Keep comparator 89 unchanged. A successful metadata handoff only permits
identity projection, never model resolution, artifact checks or execution.
"""
from .workflow_job_request_handoff import compare_workflow_job_request_handoff
from .model_reference_record_comparison import compare_model_reference_record


def compare_workflow_job_model_record_handoff(workflow_request,
        pinned_workflow_request_sha256, selected_node_id, full_job_request,
        model_record=None):
    """Call 89 once, then explicitly project an identity only after its MATCH."""
    inner = compare_workflow_job_request_handoff(workflow_request,
        pinned_workflow_request_sha256, selected_node_id, full_job_request)
    result = {
        'schema_version': 1,
        'scope': 'WORKFLOW_FULL_JOB_MODEL_RECORD_OBSERVATION_ONLY',
        'status': 'HANDOFF_BLOCKED',
        'full_job_comparison': inner,
        'model_reference_comparison': None,
        'identity_projection_performed': False,
        'model_comparison_calls': 0,
        'authority_verified': False,
        'artifact_bytes_verified': False,
        'execution_authorized': False,
        'scientific_accuracy_validated': False,
        'model_verified': False,
    }
    if inner['status'] != 'MATCH':
        return result
    if 'model_ref' not in full_job_request:
        result['status'] = 'MODEL_REFERENCE_ABSENT'
        return result
    reference = full_job_request['model_ref']
    identity = {key: reference[key] for key in ('id', 'version', 'sha256')}
    result['identity_projection_performed'] = True
    result['model_comparison_calls'] = 1
    result['model_reference_comparison'] = compare_model_reference_record(identity, model_record)
    result['status'] = 'MODEL_REFERENCE_OBSERVED'
    return result
