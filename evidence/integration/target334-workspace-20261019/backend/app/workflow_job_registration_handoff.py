"""Opt-in RFC2 local manifest observation; never capability support or approval."""
from . import gmais_api
from .agent_capability_contract import agent_capability_issue
from .workflow_job_request_handoff import compare_workflow_job_request_handoff
from .workflow_node_input_handoff_api import _exact, _require, _enum

SCOPE = 'WORKFLOW_FULL_JOB_LOCAL_REGISTRATION_OBSERVATION_ONLY'
SOURCE = 'LOCAL_STATIC_AGENT_MANIFESTS'
RESULT_KEYS = {'schema_version', 'scope', 'status', 'full_job_comparison',
    'local_manifest_registration', 'actual_capability_supported',
    'institution_acl_verified', 'execution_authorized'}
AXIS_KEYS = {'source', 'status', 'checked'}
AXIS_STATUSES = {'NOT_RUN', 'REGISTERED', 'AGENT_UNKNOWN', 'CAPABILITY_UNREGISTERED'}


def _local_registration(job):
    """Inspect only in-memory static manifests, preserving Job first-match choice."""
    manifests = gmais_api._agent_manifests()
    _require(type(manifests) is list)
    for agent in manifests:
        _require(type(agent) is dict and type(agent.get('agent_id')) is str and bool(agent['agent_id'].strip()))
        capabilities = agent.get('capabilities')
        _require(type(capabilities) is list)
        for capability in capabilities:
            _require(type(capability) is dict and type(capability.get('capability_id')) is str
                     and bool(capability['capability_id'].strip()))
    selected = next((agent for agent in manifests if agent['agent_id'] == job['agent_id']), None)
    issue = agent_capability_issue(selected, job['capability_id'])
    _require(issue in (None, 'AGENT_NOT_IMPLEMENTED', 'INVALID_REQUEST'))
    status = {None: 'REGISTERED', 'AGENT_NOT_IMPLEMENTED': 'AGENT_UNKNOWN',
              'INVALID_REQUEST': 'CAPABILITY_UNREGISTERED'}[issue]
    return {'source': SOURCE, 'status': status, 'checked': True}


def compare_workflow_job_registration_handoff(workflow_request,
        pinned_workflow_request_sha256, selected_node_id, full_job_request):
    """Run comparator 89 once, then observe registration only after its MATCH."""
    inner = compare_workflow_job_request_handoff(workflow_request,
        pinned_workflow_request_sha256, selected_node_id, full_job_request)
    axis = (_local_registration(full_job_request) if inner['status'] == 'MATCH'
            else {'source': SOURCE, 'status': 'NOT_RUN', 'checked': False})
    return {'schema_version': 2, 'scope': SCOPE,
        'status': 'MATCH' if inner['status'] == 'MATCH' and axis['status'] == 'REGISTERED' else 'BLOCKED',
        'full_job_comparison': inner, 'local_manifest_registration': axis,
        'actual_capability_supported': False, 'institution_acl_verified': False,
        'execution_authorized': False}


def validate_registration_handoff_response(result, envelope, workflow, job, validate_inner):
    """Recheck safe inner result and static observation without rerunning comparator.

    MATCH has two in-memory manifest reads: producer and independent validation.
    A blocked inner result has none. No Store/remote Registry is consulted.
    """
    _exact(result, RESULT_KEYS)
    _require(type(result['schema_version']) is int and result['schema_version'] == 2)
    _require(_enum(result['scope'], {SCOPE}))
    _require(_enum(result['status'], {'MATCH', 'BLOCKED'}))
    for key in ('actual_capability_supported', 'institution_acl_verified', 'execution_authorized'):
        _require(result[key] is False)
    inner = result['full_job_comparison']
    validate_inner(inner, envelope, workflow, job)
    axis = result['local_manifest_registration']
    _exact(axis, AXIS_KEYS)
    _require(_enum(axis['source'], {SOURCE}) and _enum(axis['status'], AXIS_STATUSES))
    _require(type(axis['checked']) is bool)
    expected = (_local_registration(job) if inner['status'] == 'MATCH'
                else {'source': SOURCE, 'status': 'NOT_RUN', 'checked': False})
    _require(axis == expected)
    _require(result['status'] == ('MATCH' if inner['status'] == 'MATCH'
             and axis['status'] == 'REGISTERED' else 'BLOCKED'))
    return result
