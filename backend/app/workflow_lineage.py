"""원문 Workflow schema/DAG를 먼저 확인하고 전역 예산으로 현재 입력 계보만 진단한다."""
from .gmais_api import _workflow_plan_validator
from .dataset_lineage import verify_dataset_lineage
from .lineage_batch import inspect_lineage_bindings
from .workflow_dependency_order import topological_order


class WorkflowLineageRequestError(ValueError):
    """요청 schema/DAG 오류만 구분해 내부 검사 실패를 400으로 오인하지 않는다."""


def validate_workflow_lineage(store, payload, *, max_depth=32, max_nodes_per_root=64,
        max_total_nodes=256, max_input_refs=64, max_unique_roots=32, max_workflow_nodes=128):
    # 자세한 jsonschema 예외에는 URI 등 원문 값이 포함될 수 있어 HTTP로 전달하지 않는다.
    if not isinstance(payload, dict) or not _workflow_plan_validator().is_valid(payload):
        raise WorkflowLineageRequestError('Workflow 요청 형식이 올바르지 않습니다.')
    values = locals()
    bounds = {'max_depth':(0,32),'max_nodes_per_root':(1,64),'max_total_nodes':(1,256),
              'max_input_refs':(1,64),'max_unique_roots':(1,32),'max_workflow_nodes':(1,128)}
    limits = {key:values[key] for key in bounds}
    if any(type(value) is not int or not bounds[key][0] <= value <= bounds[key][1] for key,value in limits.items()):
        raise WorkflowLineageRequestError('Workflow 검사 한도가 올바르지 않습니다.')
    output = {'schema_version':1,'workflow_run_id':payload['workflow_run_id'],'trace_id':payload['trace_id'],
        'mode':'PLAN_ONLY','status':'BLOCKED','execution_started':False,'can_execute':False,
        'available':False,'reason':'CHECK_LIMIT_REACHED','dag_validated':False,'topological_order':[],
        'bindings':[],'diagnostics':[],'nodes':[],'blockers':[],
        'limits':dict(limits,node_checks_performed=0,unique_roots_checked=0),
        'current_assets_revalidated':False,'lineage_integrity_verified':False,
        'authorization_verified':False,'execution_authorized':False,'scientific_approval':False,
        'network_requests':0,'source_files_written':0}
    nodes = payload['nodes']
    if len(nodes) > max_workflow_nodes:
        output['blockers'] = [{'node_id':None,'input_index':None,'code':'WORKFLOW_NODE_LIMIT'}]
        return output
    identifiers = [node['node_id'] for node in nodes]
    if len(set(identifiers)) != len(identifiers):
        raise WorkflowLineageRequestError('중복된 Workflow node_id입니다.')
    known = set(identifiers)
    remaining = {}
    for node in nodes:
        dependencies = set(node['depends_on'])
        if node['node_id'] in dependencies or dependencies - known:
            raise WorkflowLineageRequestError('Workflow 의존 노드가 올바르지 않습니다.')
        remaining[node['node_id']] = dependencies
    ordered = topological_order(remaining)
    if ordered is None:
        raise WorkflowLineageRequestError('Workflow 의존 순환이 있습니다.')
    output.update(dag_validated=True,topological_order=ordered)
    if sum(len(node['input_bindings']) for node in nodes) > max_input_refs:
        output['blockers'] = [{'node_id':None,'input_index':None,'code':'WORKFLOW_INPUT_REF_LIMIT'}]
        return output
    bindings = []
    for node in nodes:
        bindings.extend({'node_id':node['node_id'],'input_index':index,
            'ref':{key:reference[key] for key in ('id','version','sha256')}}
            for index,reference in enumerate(node['input_bindings']))
    if len({tuple(binding['ref'].values()) for binding in bindings}) > max_unique_roots:
        output['blockers'] = [{'node_id':None,'input_index':None,'code':'WORKFLOW_UNIQUE_ROOT_LIMIT'}]
        return output
    batch = inspect_lineage_bindings(store,bindings,limits,verify=verify_dataset_lineage,code_prefix='WORKFLOW')
    output.update(batch)
    for node in nodes:
        node_bindings = [row for row in output['bindings'] if row['node_id']==node['node_id']]
        blockers = [row for row in output['blockers'] if row['node_id']==node['node_id']]
        if not node_bindings:
            empty = {'node_id':node['node_id'],'input_index':None,'code':'INPUT_REFS_REQUIRED'}
            blockers.append(empty); output['blockers'].append(empty)
        complete = bool(node_bindings) and not blockers and all(binding['checked'] and
            output['diagnostics'][binding['diagnostic_index']]['lineage_integrity_verified'] for binding in node_bindings)
        output['nodes'].append({'node_id':node['node_id'],'bindings':node_bindings,'blockers':blockers,
            'inputs_complete':complete,'status':'BLOCKED','execution_authorized':False})
    output['lineage_integrity_verified'] = all(node['inputs_complete'] for node in output['nodes'])
    output['status'] = 'BLOCKED'
    return output
