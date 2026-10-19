"""Seal isolated code/evidence only; never read operational datasets."""
import ast
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent
PROJECT = WORKSPACE.parents[2]
DOC = PROJECT / 'docs/implementation/329_fixed_role_atomic_json_writer_isolated.md'


def pin(path):
    data = path.read_bytes()
    return {'path': str(path.relative_to(PROJECT)).replace('\\','/'),
            'bytes':len(data), 'sha256':hashlib.sha256(data).hexdigest()}


def save(path, value):
    if path.exists(): raise RuntimeError('FINAL_ARTIFACT_ALREADY_EXISTS')
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


baseline = json.loads((WORKSPACE/'baseline-manifest329.json').read_text(encoding='utf-8-sig'))
checks = []
for entry in baseline['files']:
    name = entry['path']
    for path in (PROJECT/name, WORKSPACE/name, WORKSPACE/'baseline'/name):
        actual = pin(path)
        if actual['sha256'] != entry['sha256']: raise RuntimeError('BASELINE_CHANGED')
    checks.append(dict(entry,main_and_archive_and_isolated_equal=True))
parent = PROJECT/'evidence/integration/target325-workspace-20261018/freeze325.json'
if pin(parent)['sha256'] != baseline['parent325_freeze_sha256']: raise RuntimeError('PARENT_CHANGED')
products = ['backend/app/data/targeted_atomic_json.py']
tests = ['tests/test_target329_atomic_json.py']
for name in products+tests:
    if (PROJECT/name).exists(): raise RuntimeError('MAIN_NEW_FILE_PRESENT')
    ast.parse((WORKSPACE/name).read_text(encoding='utf-8'))
for name in ['focused329-final-result.json','portable329-final-result.json']:
    if json.loads((WORKSPACE/name).read_text())['exit_code'] != 0: raise RuntimeError('TEST_FAILED')
diff = ''.join(''.join(difflib.unified_diff([], (WORKSPACE/name).read_text(encoding='utf-8').splitlines(True),
             fromfile='/dev/null',tofile=name)) for name in products+tests)
(WORKSPACE/'patch329.diff').write_text(diff,encoding='utf-8')
manifest = {'unit':329,'status':'TESTED_SYNTHETIC_SHARED_APPLICATION_BLOCKED',
    'runtime_new':[pin(WORKSPACE/name) for name in products],
    'tests_new':[pin(WORKSPACE/name) for name in tests], 'existing_code_changed':[],
    'copied_unchanged_dependencies':checks,'main_preconditions_new_files_absent':products+tests,
    'diff':pin(WORKSPACE/'patch329.diff'),'operating_io':False,'http':False,
    'collector_connected':False,'ledger_connected':False,'main_applied':False}
save(WORKSPACE/'patch329-manifest.json',manifest)
names = ['baseline-manifest329.json','patch329-manifest.json','patch329.diff','finalize329.py',
         'focused329-first.log','focused329-first-result.json',
         'focused329-parent-fixture-failure.log','focused329-parent-fixture-failure-result.json',
         'test329-before-parent-fixture-fix.py','focused329-final.log','focused329-final-result.json',
         'portable329-final.log','portable329-final-result.json'] + products+tests
freeze = {'unit':329,'at':datetime.now(timezone.utc).isoformat(),
    'status':'FROZEN_FOR_INDEPENDENT_REVIEW','unique_synthetic_cases':30,
    'focused_pass':30,'portable_same_cases_pass':30,'skip':0,
    'historical_failure':'Windows open-fd parent rename fixture, retained; test-only timing fix',
    'document':pin(DOC),'files':[pin(WORKSPACE/name) for name in names],
    'baseline_checks':checks,'parent325':pin(parent),
    'operating_io':False,'http':False,'native':False,'shared_edits':False,
    'coverage':'Existing-file atomic JSON replacement only; no coordinator/ledger connection',
    'rss_observed':False,'main_applied':False}
save(WORKSPACE/'freeze329.json',freeze)
print(json.dumps({'freeze':pin(WORKSPACE/'freeze329.json'),'manifest':pin(WORKSPACE/'patch329-manifest.json'),
                  'document':pin(DOC),'runtime':pin(WORKSPACE/products[0])},ensure_ascii=False,indent=2))
