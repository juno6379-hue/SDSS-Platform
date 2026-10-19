"""Seal isolated 332 code/evidence only; never reads operational datasets."""
import ast
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent
PROJECT = WORKSPACE.parents[2]
DOC = PROJECT/'docs/implementation/332_ledger_metadata_io_isolated.md'


def pin(path):
    data = path.read_bytes()
    return {'path': str(path.relative_to(PROJECT)).replace('\\', '/'), 'bytes': len(data),
            'sha256': hashlib.sha256(data).hexdigest()}


def save(path, value):
    if path.exists(): raise RuntimeError('FINAL_ARTIFACT_ALREADY_EXISTS')
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


baseline = json.loads((WORKSPACE/'baseline-manifest332.json').read_text(encoding='utf-8-sig'))
checks = []
for entry in baseline['files']:
    name = entry['path']
    paths = [PROJECT/name, WORKSPACE/'baseline'/name]
    if name != 'backend/app/data/budget.py': paths.append(WORKSPACE/name)
    for path in paths:
        if pin(path)['sha256'] != entry['sha256']: raise RuntimeError('BASELINE_CHANGED '+name)
    checks.append(dict(entry, main_and_baseline_equal=True))
fixture = WORKSPACE/'tests/fixtures/budget332_legacy.py'
if pin(fixture)['sha256'] != baseline['files'][0]['sha256']: raise RuntimeError('FIXTURE_NOT_LEGACY')
new_products = ['backend/app/data/ledger_metadata_io.py']
changed_products = ['backend/app/data/budget.py']
tests = ['tests/test_ledger_metadata332.py', 'tests/fixtures/budget332_legacy.py']
for name in new_products+tests:
    if (PROJECT/name).exists(): raise RuntimeError('MAIN_NEW_FILE_PRESENT '+name)
for name in new_products+changed_products+tests:
    ast.parse((WORKSPACE/name).read_text(encoding='utf-8'))
for name in ['focused332-final-result.json', 'portable332-final-result.json']:
    if json.loads((WORKSPACE/name).read_text(encoding='utf-8'))['exit_code'] != 0: raise RuntimeError('TEST_FAILED')
diff = ''.join(difflib.unified_diff((WORKSPACE/'baseline'/changed_products[0]).read_text(encoding='utf-8').splitlines(True),
                                    (WORKSPACE/changed_products[0]).read_text(encoding='utf-8').splitlines(True),
                                    fromfile='a/'+changed_products[0], tofile='b/'+changed_products[0]))
diff += ''.join(''.join(difflib.unified_diff([], (WORKSPACE/name).read_text(encoding='utf-8').splitlines(True),
                fromfile='/dev/null', tofile='b/'+name)) for name in new_products+tests)
(WORKSPACE/'patch332.diff').write_text(diff, encoding='utf-8')
manifest = {'unit': 332, 'status': 'TESTED_SYNTHETIC_REVIEWED',
            'runtime_new': [pin(WORKSPACE/n) for n in new_products],
            'runtime_changed': [dict(pin(WORKSPACE/n), baseline_sha256=checks[0]['sha256']) for n in changed_products],
            'tests_new': [pin(WORKSPACE/n) for n in tests], 'copied_unchanged_dependencies': checks,
            'diff': pin(WORKSPACE/'patch332.diff'), 'operating_io': False, 'http': False,
            'collector_connected': False, 'real_ledger_connected': False, 'main_applied': False}
save(WORKSPACE/'patch332-manifest.json', manifest)
names = ['baseline-manifest332.json', 'patch332-manifest.json', 'patch332.diff', 'finalize332.py', 'run332.py',
         'focused332-launcher-import-error.log', 'focused332-first.log',
         'pre-review332/budget.py', 'pre-review332/ledger_metadata_io.py', 'pre-review332/test_ledger_metadata332.py',
         'pre-review332/focused332-final.log', 'pre-review332/focused332-final-result.json',
         'pre-review332/portable332-final.log', 'pre-review332/portable332-final-result.json',
         'mutation332-pre-review-code.log', 'review332-static.md',
         'focused332-final.log', 'focused332-final-result.json',
         'portable332-final.log', 'portable332-final-result.json'] + new_products + changed_products + tests
freeze = {'unit': 332, 'at': datetime.now(timezone.utc).isoformat(), 'status': 'FROZEN_REVIEWED_NO_BLOCKING',
          'unique_synthetic_cases': 45, 'focused_pass': 45, 'portable_same_cases_pass': 45, 'skip': 0,
          'pre_review_cases_pass': 34, 'mutation_failures_on_pre_review_code': 7,
          'review': 'independent static review: round1 F1-F3 fixed, F4-F9 documented; round2 no blocking',
          'document': pin(DOC), 'files': [pin(WORKSPACE/n) for n in names], 'baseline_checks': checks,
          'operating_io': False, 'http': False, 'native': False, 'main_applied': False,
          'coverage': 'Explicit opt-in ledger metadata_io adapter; no 170 coordinator/worker/real ledger connection'}
save(WORKSPACE/'freeze332.json', freeze)
print(json.dumps({'freeze': pin(WORKSPACE/'freeze332.json'), 'manifest': pin(WORKSPACE/'patch332-manifest.json'),
                  'document': pin(DOC)}, ensure_ascii=False, indent=2))
