"""계획 단계의 차단 원인 진단. 실행·저장·권한 검사를 수행하지 않는 순수 함수다."""
import copy
import json


def diagnose_workflow_blocking(reviewed_nodes, policy):
    """local 차단을 실제 의존 경로와 FAIL_ALL 정책으로 구분하여 전파한다."""
    if not isinstance(policy,dict) or policy.get('on_blocked') not in ('STOP_DEPENDENTS','FAIL_ALL'):
        raise ValueError('on_blocked는 STOP_DEPENDENTS 또는 FAIL_ALL이어야 합니다.')
    if not isinstance(reviewed_nodes,list) or not reviewed_nodes:
        raise ValueError('비어 있지 않은 reviewed_nodes 목록이 필요합니다.')
    nodes={}
    for node in reviewed_nodes:
        if not isinstance(node,dict) or not isinstance(node.get('node_id'),str) or not node['node_id']:
            raise ValueError('각 노드에는 비어 있지 않은 node_id가 필요합니다.')
        identifier=node['node_id']
        if identifier in nodes:
            raise ValueError('node_id는 중복될 수 없습니다.')
        dependencies=node.get('depends_on');blockers=node.get('blockers')
        if not isinstance(dependencies,list) or any(not isinstance(dep,str) or not dep for dep in dependencies):
            raise ValueError('depends_on은 비어 있지 않은 node_id의 목록이어야 합니다.')
        if not isinstance(blockers,list) or any(not isinstance(b,dict) or not isinstance(b.get('code'),str) or not b['code'].strip() for b in blockers):
            raise ValueError('blockers는 code가 있는 객체 목록이어야 합니다.')
        try:
            # 입력 순서가 달라도 같게 표시하고 반환 객체의 변경이 원본에 영향을 주지 않는다.
            copied=copy.deepcopy(blockers)
            copied.sort(key=lambda value:json.dumps(value,sort_keys=True,ensure_ascii=False,allow_nan=False))
        except (TypeError,ValueError):
            raise ValueError('local blocker는 유효한 JSON 객체여야 합니다.') from None
        # 원문 schema가 허용하는 반복 dependency는 같은 간선으로 정규화한다.
        nodes[identifier]={'depends_on':set(dependencies),'local_blockers':copied}
    known=set(nodes)
    for identifier,node in nodes.items():
        if identifier in node['depends_on'] or node['depends_on']-known:
            raise ValueError('자기 의존 또는 존재하지 않는 dependency입니다.')
    remaining={identifier:set(node['depends_on']) for identifier,node in nodes.items()}
    ordered=[]
    while remaining:
        ready=sorted(identifier for identifier,dependencies in remaining.items() if not dependencies)
        if not ready:
            raise ValueError('Workflow dependency graph에 cycle이 있습니다.')
        ordered.extend(ready)
        for identifier in ready:
            remaining.pop(identifier)
        for dependencies in remaining.values():
            dependencies.difference_update(ready)
    ancestors={}
    for identifier in ordered:
        ancestors[identifier]=set(nodes[identifier]['depends_on'])
        for dependency in nodes[identifier]['depends_on']:
            ancestors[identifier].update(ancestors[dependency])
    seeds={identifier for identifier,node in nodes.items() if node['local_blockers']}
    result=[]
    for identifier in sorted(nodes):
        upstream=ancestors[identifier]&seeds
        # FAIL_ALL의 추가 원인은 실제 upstream과 자기 local 원인을 중복 표기하지 않는다.
        policy_causes=seeds-upstream-{identifier} if policy['on_blocked']=='FAIL_ALL' else set()
        causes=upstream|policy_causes|({identifier} if identifier in seeds else set())
        result.append({'node_id':identifier,'local_blockers':nodes[identifier]['local_blockers'],
                       'upstream_blocked_by':sorted(upstream),'policy_blocked_by':sorted(policy_causes),
                       'blocking_cause_node_ids':sorted(causes),
                       'diagnostic_status':'BLOCKING_CAUSES_PRESENT' if causes else 'NO_BLOCKING_CAUSE_IDENTIFIED',
                       'execution_authorized':False})
    return {'schema_version':1,'scope':'PLAN_ONLY_DEPENDENCY_DIAGNOSTICS',
            'on_blocked':policy['on_blocked'],'topological_order':ordered,
            'local_blocking_node_ids':sorted(seeds),'nodes':result,'execution_authorized':False}
