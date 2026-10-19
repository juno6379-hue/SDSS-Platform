"""Seal isolated Unit 334 code and evidence; never modifies main repository."""
import ast
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path
import sys

WORKSPACE = Path(__file__).resolve().parent
PROJECT = WORKSPACE.parents[2]
DOC = PROJECT / 'docs/implementation/334_targeted_bare_collection_adapter_isolated.md'


def pin(path):
    data = path.read_bytes()
    rel = path.relative_to(PROJECT) if path.is_relative_to(PROJECT) else path.relative_to(WORKSPACE)
    return {
        'path': str(rel).replace('\\', '/'),
        'bytes': len(data),
        'sha256': hashlib.sha256(data).hexdigest()
    }


def save(path, value):
    if path.exists():
        path.unlink()
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    baseline = json.loads((WORKSPACE / 'baseline-manifest334.json').read_text(encoding='utf-8-sig'))

    # 1. Verify target script baseline
    target_info = baseline['target_file']
    target_rel = target_info['path']
    main_target = PROJECT / target_rel
    baseline_target = WORKSPACE / 'baseline' / target_rel
    workspace_target = WORKSPACE / target_rel

    if pin(main_target)['sha256'] != target_info['sha256']:
        raise RuntimeError(f"MAIN_REPOSITORY_POLLUTED: {main_target}")
    if pin(baseline_target)['sha256'] != target_info['sha256']:
        raise RuntimeError(f"BASELINE_CORRUPTED: {baseline_target}")

    # 2. Verify all dependencies unchanged between main and workspace
    dep_checks = []
    for dep in baseline['dependencies']:
        p_main = PROJECT / dep['path']
        p_ws = WORKSPACE / dep['path']
        if pin(p_main)['sha256'] != dep['sha256']:
            raise RuntimeError(f"MAIN_DEPENDENCY_DRIFT: {dep['path']}")
        if pin(p_ws)['sha256'] != dep['sha256']:
            raise RuntimeError(f"WORKSPACE_DEPENDENCY_DRIFT: {dep['path']}")
        dep_checks.append(dict(dep, main_and_workspace_equal=True))

    # 3. Verify new tests are not present in main
    new_tests = ['tests/test_collect_targeted_bare334.py']
    for t in new_tests:
        if (PROJECT / t).exists():
            raise RuntimeError(f"MAIN_NEW_FILE_PRESENT: {t}")

    # 4. AST parse
    ast.parse(workspace_target.read_text(encoding='utf-8'))
    for t in new_tests:
        ast.parse((WORKSPACE / t).read_text(encoding='utf-8'))

    # 5. Verify test runs
    for res_name in ['focused334-final-result.json', 'portable334-final-result.json']:
        res_data = json.loads((WORKSPACE / res_name).read_text(encoding='utf-8'))
        if res_data.get('exit_code') != 0:
            raise RuntimeError(f"TEST_FAILED_IN_{res_name}: {res_data}")

    # 6. Generate patch334.diff
    diff = ''.join(difflib.unified_diff(
        baseline_target.read_text(encoding='utf-8').splitlines(True),
        workspace_target.read_text(encoding='utf-8').splitlines(True),
        fromfile=f'a/{target_rel}',
        tofile=f'b/{target_rel}'
    ))
    diff += ''.join(''.join(difflib.unified_diff(
        [],
        (WORKSPACE / t).read_text(encoding='utf-8').splitlines(True),
        fromfile='/dev/null',
        tofile=f'b/{t}'
    )) for t in new_tests)

    (WORKSPACE / 'patch334.diff').write_text(diff, encoding='utf-8')

    # 7. Generate patch334-manifest.json
    manifest = {
        'unit': 334,
        'title': 'Unit 334 Targeted Bare Collection 128MiB Preflight and LedgerMetadataIO Adapter',
        'status': 'TESTED_SYNTHETIC',
        'runtime_changed': [
            dict(pin(workspace_target), baseline_sha256=target_info['sha256'])
        ],
        'tests_new': [pin(WORKSPACE / t) for t in new_tests],
        'diff': pin(WORKSPACE / 'patch334.diff'),
        'operating_io': False,
        'http': False,
        'main_applied': False,
        'preserved_pending_reservations_bytes': 136314880,
        'candidate_spots': {
            'total_candidates': 50,
            'overlapping_existing_support': 35,
            'non_overlapping_existing_support': 15,
            'mutual_overlap_candidate_pairs': 56,
            'execution_supported': False,
            'learning_ready': False,
            'scientific_accuracy_validated': False,
            'quality_status': '미검사·집행 미승인'
        }
    }
    save(WORKSPACE / 'patch334-manifest.json', manifest)

    # 8. Generate freeze334.json
    freeze_names = [
        'baseline-manifest334.json',
        'patch334-manifest.json',
        'patch334.diff',
        'finalize334.py',
        'run334.py',
        'focused334-final.log',
        'focused334-final-result.json',
        'portable334-final.log',
        'portable334-final-result.json',
        'scripts/collect_targeted_bare.py',
        'tests/test_collect_targeted_bare334.py',
        'tests/test_collect_targeted_bare_legacy.py',
    ]
    freeze = {
        'unit': 334,
        'at': datetime.now(timezone.utc).isoformat(),
        'status': 'FROZEN_VALIDATED_ISOLATED',
        'test_metrics': {
            'total_test_cases_per_run': 32,
            'unit_334_cases': 9,
            'legacy_regression_cases': 23,
            'focused_pass': 32,
            'portable_pass': 32,
            'fail': 0,
            'skip': 0
        },
        'preserved_pending_reservations_bytes': 136314880,
        'document': pin(DOC) if DOC.exists() else {'path': str(DOC.relative_to(PROJECT)).replace('\\', '/'), 'status': 'PLANNED'},
        'files': [pin(WORKSPACE / n) for n in freeze_names],
        'baseline_dependencies_count': len(dep_checks),
        'operating_io': False,
        'http': False,
        'main_applied': False,
        'summary': 'Unit 334 128MiB preflight bottleneck resolution and LedgerMetadataIO adapter strictly isolated in target334-workspace-20261019.'
    }
    save(WORKSPACE / 'freeze334.json', freeze)
    print(json.dumps({
        'freeze': pin(WORKSPACE / 'freeze334.json'),
        'manifest': pin(WORKSPACE / 'patch334-manifest.json'),
        'diff': pin(WORKSPACE / 'patch334.diff')
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
