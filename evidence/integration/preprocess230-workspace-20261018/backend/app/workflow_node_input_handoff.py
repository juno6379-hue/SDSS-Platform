"""Pure selected Workflow node to proposed Job metadata declaration comparison.

No Job construction, source authentication, Registry lookup, or execution occurs.
"""
import hashlib
import json

from .execution_input_binding import _FALSE, _sha, _text

_WORKFLOW = {'schema_version', 'workflow_run_id', 'trace_id', 'nodes', 'policy'}
_NODE = {'node_id', 'agent_id', 'capability_id', 'depends_on', 'input_bindings'}
_REF = {'id', 'version', 'sha256'}
_PROPOSAL = {'agent_id', 'capability_id', 'execution_context', 'input_refs'}
_FALSE_FLAGS = _FALSE + ('workflow_origin_verified', 'executor_bindings_compared',
    'transitive_lineage_verified', 'complete_job_validated', 'aoi_verified',
    'requested_outputs_verified', 'predecessor_results_bound', 'dag_validated')


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
        allow_nan=False, separators=(',', ':')).encode('utf-8')).hexdigest()


def _shape(value, required, optional=()):
    return (type(value) is dict and len(value) <= len(required) + len(optional)
        and required <= value.keys() and not value.keys() - (required | set(optional)))


def _refs(rows, identities, *, allow_empty=False):
    if type(rows) is not list or not (0 if allow_empty else 1) <= len(rows) <= 64:
        return 'INPUT_COUNT_INVALID', None
    for index, row in enumerate(rows):
        if not _shape(row, _REF, {'role', 'uri'}):
            return 'INPUT_SCHEMA_INVALID', index
        if not _text(row['id']) or not _text(row['version']):
            return 'INPUT_IDENTITY_INVALID', index
        if row['version'].strip().lower() in {'latest', 'current'}:
            return 'INPUT_VERSION_NOT_PINNED', index
        if not _sha(row['sha256']):
            return 'INPUT_SHA_INVALID', index
        if 'role' in row and not _text(row['role']):
            return 'INPUT_ROLE_INVALID', index
        # An explicitly empty URI is permitted by the source schema; absence differs.
        if 'uri' in row and not (type(row['uri']) is str
                and (row['uri'] == '' or _text(row['uri']))):
            return 'INPUT_URI_INVALID', index
        identity = (row['id'], row['version'])
        prior = identities.setdefault(identity, row['sha256'])
        if prior != row['sha256']:
            return 'INPUT_IDENTITY_CONFLICT', index
    return None


def _workflow_error(value):
    if (not _shape(value, _WORKFLOW) or type(value['schema_version']) is not str
            or value['schema_version'] != '0.2.0'):
        return 'WORKFLOW_SCHEMA_INVALID', None, None
    if not _text(value['workflow_run_id']) or not _text(value['trace_id']):
        return 'WORKFLOW_IDENTITY_INVALID', None, None
    policy = value['policy']
    if (not _shape(policy, {'on_blocked', 'max_parallel'}, {'require_human_approval'})
            or not _text(policy['on_blocked'])
            or policy['on_blocked'] not in {'STOP_DEPENDENTS', 'FAIL_ALL'}
            or type(policy['max_parallel']) is not int
            or not 1 <= policy['max_parallel'] <= 2147483647
            or ('require_human_approval' in policy and type(policy['require_human_approval']) is not bool)):
        return 'WORKFLOW_POLICY_INVALID', None, None
    nodes = value['nodes']
    if type(nodes) is not list or not 1 <= len(nodes) <= 128:
        return 'WORKFLOW_NODE_COUNT_INVALID', None, None
    identities, names, edges, total = {}, set(), {}, 0
    for index, node in enumerate(nodes):
        if not _shape(node, _NODE, {'timeout_seconds', 'max_retries'}):
            return 'NODE_SCHEMA_INVALID', index, None
        if any(not _text(node[key]) for key in ('node_id', 'agent_id', 'capability_id')):
            return 'NODE_IDENTITY_INVALID', index, None
        if node['node_id'] in names:
            return 'NODE_ID_AMBIGUOUS', index, None
        names.add(node['node_id'])
        for field, low, high in (('timeout_seconds', 1, 2147483647), ('max_retries', 0, 5)):
            if field in node and (type(node[field]) is not int or not low <= node[field] <= high):
                return 'NODE_POLICY_INVALID', index, None
        deps = node['depends_on']
        if (type(deps) is not list or len(deps) > 128 or any(not _text(dep) for dep in deps)):
            return 'NODE_DEPENDENCY_INVALID', index, None
        edges[node['node_id']] = set(deps)
        problem = _refs(node['input_bindings'], identities, allow_empty=True)
        if problem:
            return problem[0], index, problem[1]
        total += len(node['input_bindings'])
        if total > 64:
            return 'WORKFLOW_INPUT_LIMIT', index, None
    for index, node in enumerate(nodes):
        if node['node_id'] in edges[node['node_id']] or edges[node['node_id']] - names:
            return 'NODE_DEPENDENCY_INVALID', index, None
    return None


def compare_workflow_node_input_handoff(workflow_request, pinned_workflow_request_sha256,
        selected_node_id, proposed_job_metadata):
    """Compare a caller-pinned request to selected metadata, never a complete Job.

    All containers and scalars are bounded and validated before canonical hashing.
    Strict shapes also reject recursive containers without traversing arbitrary data.
    """
    result = dict(schema_version=1, scope='WORKFLOW_NODE_TO_PROPOSED_JOB_INPUT_DECLARATIONS_ONLY',
        status='BLOCKED', declarations_match=False, workflow_request_sha256=None,
        pinned_workflow_request_sha256=None, selected_node_sha256=None,
        expected_metadata_sha256=None, proposed_metadata_sha256=None,
        selected_node_index=None, expected_input_count=None, proposed_input_count=None,
        issues=[], network_requests=0, source_files_read=0, source_files_written=0,
        database_calls=0, registry_calls=0, resolver_calls=0, executor_calls=0,
        **{key: False for key in _FALSE_FLAGS})

    def issue(code, side, node_index=None, input_index=None):
        result['issues'].append(dict(code=code, side=side, node_index=node_index, input_index=input_index))
        return result

    if not _sha(pinned_workflow_request_sha256):
        return issue('WORKFLOW_PIN_INVALID', 'caller')
    result['pinned_workflow_request_sha256'] = pinned_workflow_request_sha256
    if not _text(selected_node_id):
        return issue('SELECTED_NODE_INVALID', 'caller')
    result['selected_node_sha256'] = _digest(selected_node_id)
    problem = _workflow_error(workflow_request)
    if problem:
        return issue(problem[0], 'workflow', problem[1], problem[2])
    result['workflow_request_sha256'] = _digest(workflow_request)
    if result['workflow_request_sha256'] != pinned_workflow_request_sha256:
        return issue('WORKFLOW_PIN_MISMATCH', 'comparison')
    selected = [(index, node) for index, node in enumerate(workflow_request['nodes'])
        if node['node_id'] == selected_node_id]
    if not selected:
        return issue('SELECTED_NODE_NOT_FOUND', 'caller')
    index, node = selected[0]
    if not node['input_bindings']:
        return issue('SELECTED_INPUTS_REQUIRED', 'workflow', index)
    result['selected_node_index'] = index
    expected = dict(agent_id=node['agent_id'], capability_id=node['capability_id'],
        execution_context={'trace_id': workflow_request['trace_id']}, input_refs=node['input_bindings'])
    result['expected_input_count'] = len(expected['input_refs'])
    result['expected_metadata_sha256'] = _digest(expected)
    proposal = proposed_job_metadata
    if not _shape(proposal, _PROPOSAL):
        return issue('PROPOSED_METADATA_SCHEMA_INVALID', 'proposal')
    if any(not _text(proposal[key]) for key in ('agent_id', 'capability_id')) or not (
            _shape(proposal['execution_context'], {'trace_id'})
            and _text(proposal['execution_context']['trace_id'])):
        return issue('PROPOSED_IDENTITY_INVALID', 'proposal')
    problem = _refs(proposal['input_refs'], {})
    if problem:
        return issue(problem[0], 'proposal', None, problem[1])
    result['proposed_input_count'] = len(proposal['input_refs'])
    result['proposed_metadata_sha256'] = _digest(proposal)
    for field in ('agent_id', 'capability_id', 'execution_context'):
        if expected[field] != proposal[field]:
            issue({'agent_id':'AGENT_ID_MISMATCH', 'capability_id':'CAPABILITY_ID_MISMATCH',
                'execution_context':'TRACE_ID_MISMATCH'}[field], 'comparison')
    if len(expected['input_refs']) != len(proposal['input_refs']):
        issue('INPUT_COUNT_MISMATCH', 'comparison')
    for ref_index, (left, right) in enumerate(zip(expected['input_refs'], proposal['input_refs'])):
        for field in ('id', 'version', 'sha256', 'role', 'uri'):
            if (field in left) != (field in right) or (field in left and left[field] != right[field]):
                issue('INPUT_' + field.upper() + '_MISMATCH', 'comparison', index, ref_index)
    if not result['issues']:
        result.update(status='MATCH', declarations_match=True)
    return result
