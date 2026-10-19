"""저장 Job의 고정 입력을 현재 전이 계보로 진단한다. 제출 snapshot은 변경하지 않는다."""
import copy

from .job_snapshot import _identity
from .dataset_lineage import verify_dataset_lineage
from .lineage_batch import inspect_lineage_bindings


def validate_job_lineage(store, job_id, *, max_depth=32, max_nodes_per_root=64,
                         max_total_nodes=256, max_input_refs=64, max_unique_roots=32):
    limits = dict(max_depth=max_depth, max_nodes_per_root=max_nodes_per_root,
        max_total_nodes=max_total_nodes, max_input_refs=max_input_refs, max_unique_roots=max_unique_roots)
    output = {'schema_version': 1, 'job_id': job_id, 'trace_id': 'unknown', 'available': False,
        'reason': 'JOB_REQUEST_INVALID', 'status': 'BLOCKED', 'bindings': [], 'diagnostics': [], 'blockers': [],
        'limits': dict(limits, node_checks_performed=0, unique_roots_checked=0),
        'current_assets_revalidated': False, 'lineage_integrity_verified': False,
        'authorization_verified': False, 'execution_authorized': False, 'scientific_approval': False,
        'network_requests': 0, 'source_files_written': 0}
    caps = {'max_depth': (0, 32), 'max_nodes_per_root': (1, 64), 'max_total_nodes': (1, 256),
            'max_input_refs': (1, 64), 'max_unique_roots': (1, 32)}
    if any(type(value) is not int or not caps[key][0] <= value <= caps[key][1] for key, value in limits.items()):
        output['limits'] = {key: value if type(value) is int else None for key, value in output['limits'].items()}
        output['blockers'] = [{'input_index': None, 'code': 'INVALID_LIMITS'}]
        return output
    try:
        record = store.get('gmais_jobs', job_id)
    except (ValueError, TypeError):
        output['blockers'] = [{'input_index': None, 'code': 'JOB_REQUEST_INVALID'}]
        return output
    try:
        if not isinstance(record, dict):
            raise ValueError('Job 객체가 아님')
        # 저장된 input_resolution과 원문 확장 필드는 읽기 투영에 포함하지 않는다.
        job = {key: copy.deepcopy(record[key]) for key in ('id', 'job_id', 'agent_id', 'status') if key in record}
        status = job['status']
        if (not isinstance(status, dict) or job['id'] != job_id or job['job_id'] != job_id
                or status['job_id'] != job_id or not isinstance(job['agent_id'], str) or not job['agent_id']
                or job['agent_id'] != status['agent_id'] or not isinstance(status['trace_id'], str) or not status['trace_id']):
            raise ValueError('Job 신원이 올바르지 않음')
        if 'request' not in record:
            output.update(trace_id=status['trace_id'], reason='LEGACY_REQUEST_NOT_RECORDED')
            return output
        request = record['request']
        if not isinstance(request, dict):
            raise ValueError('요청 객체가 아님')
        context = request['execution_context']
        if (not isinstance(context, dict) or request['agent_id'] != job['agent_id']
                or context['trace_id'] != status['trace_id']):
            raise ValueError('Job 요청의 Agent/Trace가 올바르지 않음')
        output['trace_id'] = status['trace_id']
        refs = request.get('input_refs')
        # 큰 레거시 요청은 개별 참조 복제·해시 전에 닫는다.
        if isinstance(refs, list) and len(refs) > max_input_refs:
            output.update(reason='CHECK_LIMIT_REACHED')
            output['blockers'] = [{'input_index': None, 'code': 'JOB_INPUT_REF_LIMIT'}]
            return output
        job['request'] = {'agent_id': request['agent_id'], 'execution_context': {'trace_id': context['trace_id']},
                          'input_refs': copy.deepcopy(refs)}
        trace, refs = _identity(job, job_id)
        output['trace_id'] = trace
    except (ValueError, KeyError, TypeError):
        output['blockers'] = [{'input_index': None, 'code': 'JOB_REQUEST_INVALID'}]
        return output
    keys = [(ref['id'], ref['version'], ref['sha256']) for ref in refs]
    if len(set(keys)) > max_unique_roots:
        output.update(reason='CHECK_LIMIT_REACHED')
        output['blockers'] = [{'input_index': None, 'code': 'JOB_UNIQUE_ROOT_LIMIT'}]
        return output
    bindings = [{'input_index': index, 'ref': dict(zip(('id', 'version', 'sha256'), key))}
                for index, key in enumerate(keys)]
    output.update(inspect_lineage_bindings(store, bindings, limits, verify=verify_dataset_lineage, code_prefix='JOB'))
    return output
