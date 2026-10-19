"""Job/Workflow 공통 고정 입력 계보 배치 검사. 호출 단위 캐시와 총 node 예산을 공유한다."""
from .dataset_lineage_api import _project


def inspect_lineage_bindings(store, bindings, limits, *, verify, code_prefix):
    output = {'bindings': [], 'diagnostics': [], 'blockers': [],
        'limits': dict(limits, node_checks_performed=0, unique_roots_checked=0)}
    keys = [(binding['ref']['id'], binding['ref']['version'], binding['ref']['sha256']) for binding in bindings]
    variants = {}
    for key in keys:
        variants.setdefault(key[:2], set()).add(key[2])
    cache = {}
    exhausted = False
    for source, key in zip(bindings, keys):
        binding = dict(source, diagnostic_index=None, reused=False, checked=False)
        output['bindings'].append(binding)

        def issue(code):
            return dict({key: binding[key] for key in ('node_id', 'input_index') if key in binding}, code=code)

        if len(variants[key[:2]]) > 1:
            output['blockers'].append(issue(code_prefix + '_INPUT_REFERENCE_CONFLICT'))
            continue
        if key in cache:
            diagnostic_index = cache[key]
            binding['reused'] = True
        else:
            remaining = limits['max_total_nodes'] - output['limits']['node_checks_performed']
            if remaining == 0:
                exhausted = True
                output['blockers'].append(issue(code_prefix + '_TOTAL_NODE_CHECK_LIMIT'))
                continue
            quota = min(limits['max_nodes_per_root'], remaining)
            diagnostic = _project(verify(store, *key, max_depth=limits['max_depth'], max_nodes=quota),
                                  binding['ref'], limits['max_depth'], quota)
            if len(diagnostic['nodes']) > quota:
                raise ValueError('검사 한도에 맞지 않는 계보 응답')
            diagnostic_index = len(output['diagnostics'])
            cache[key] = diagnostic_index
            output['diagnostics'].append(diagnostic)
            output['limits']['node_checks_performed'] += len(diagnostic['nodes'])
            output['limits']['unique_roots_checked'] += 1
            if quota < limits['max_nodes_per_root'] and diagnostic['limits']['node_limit_reached']:
                exhausted = True
        binding.update(diagnostic_index=diagnostic_index, checked=True)
        diagnostic = output['diagnostics'][diagnostic_index]
        output['blockers'].extend(issue(problem['code']) for problem in diagnostic['blockers'])
    output['available'] = True
    output['reason'] = 'CHECK_LIMIT_REACHED' if exhausted else 'CURRENT_LINEAGE_CHECKED'
    output['current_assets_revalidated'] = any(result['current_assets_revalidated'] for result in output['diagnostics'])
    output['lineage_integrity_verified'] = bool(bindings) and not output['blockers'] and all(
        binding['checked'] and output['diagnostics'][binding['diagnostic_index']]['lineage_integrity_verified']
        for binding in output['bindings'])
    output['status'] = 'INTEGRITY_VERIFIED' if output['lineage_integrity_verified'] else 'BLOCKED'
    return output
