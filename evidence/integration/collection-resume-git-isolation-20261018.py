"""Commit only this completed unit using an isolated Git index.

The shared working tree/index/main branch stay untouched. A second chat is
currently extending the same collector and UI; those edits are not this unit.
"""
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / 'evidence/integration'
branch = 'codex/collection-resume-20261018'
git_dir = Path(subprocess.check_output(['git', 'rev-parse', '--absolute-git-dir'], cwd=ROOT, text=True, encoding='utf-8').strip())
index = git_dir / 'collection-resume-20261018.index'
if index.exists():
    raise RuntimeError('Isolated index already exists; inspect before retrying.')
if subprocess.run(['git', 'show-ref', '--verify', '--quiet', 'refs/heads/' + branch], cwd=ROOT).returncode == 0:
    raise RuntimeError('Completed-unit branch already exists; do not create a second commit blindly.')
parent = json.loads((EVIDENCE / 'collection-resume-closeout-20261018.json').read_text('utf-8'))['source_parent_commit']
current = (ROOT / 'scripts/collect_training_parallel.py').read_bytes()
# Strip only the other chat's known priority-mode additions in memory. Never
# write this reconstruction back over that chat's live working-tree file.
text = current.decode('utf-8')
text = re.sub(r'^    parser\.add_argument\("--priority-(?:deficit|plan-sha256)"[^\n]*\n', '', text, flags=re.M)
text = re.sub(r'^    if args\.priority_deficit and[^\n]*\n.*?(?=    service\._integer)', '', text, flags=re.M | re.S)
text = re.sub(r'^    if args\.priority_deficit:\r?\n        try:\r?\n.*?(?=    observed_threads)', '', text, flags=re.M | re.S)
tested = text.encode('utf-8')
baseline = json.loads((EVIDENCE / 'collection-resume-root-baseline-20261018.json').read_text('utf-8'))
expected = baseline['files'][str(ROOT / 'scripts/collect_training_parallel.py')]['sha256']
variants = [tested, tested.replace(b'\r\n', b'\n'), tested.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')]
tested = next((value for value in variants if hashlib.sha256(value).hexdigest() == expected), tested)
assert hashlib.sha256(tested).hexdigest() == expected, 'Cannot reconstruct the exact tested collector; stop without changing main/index.'

owned = [
    'CONTINUOUS_DEVELOPMENT.md', 'docs/implementation/00_next_session_handoff.md',
    'docs/16_충분학습자료_단계별수집계획.md', 'docs/20_대량수집_학습_통합실행.md',
    'tests/test_collection_continue_pending.py',
    'docs/implementation/148_collection_resume_audit.md',
    'docs/implementation/149_training_data_remediation_audit.md',
    'docs/implementation/150_service_recovery_audit.md',
    'docs/implementation/151_development_resume_runbook.md',
    'docs/implementation/152_targeted_bare_collection_rfc.md',
]
owned += ['docs/understanding/' + name for name in (
    '01_DATA_PIPELINE.md', '02_LCLUC_ML.md', '06_GEOLLM_SDSS.md', 'CHANGELOG.md',
    'CURRENT_ARCHITECTURE.md', 'GLOSSARY_KO_EN.md', 'INDEX.md',
    'presentations/1MIN_5MIN_SCRIPT.md', 'presentations/DEMO_STORY.md', 'presentations/FAQ.md',
    'gate-notes/GATE_RESUME_AND_DATA_REMEDIATION_20261018.md')]
prefixes = ('collection-resume-', 'ml-resume-audit-20261018', '147-local-service-restore-20261018',
            '147-closeout-service-audit-20261018')
owned += [str(path.relative_to(ROOT)).replace('\\', '/') for path in EVIDENCE.iterdir()
          if path.is_file() and path.name.startswith(prefixes)
          and path.name != 'collection-resume-host-diagnostics-20261018.json']
assert all((ROOT / path).is_file() for path in owned)
env = os.environ.copy()
env['GIT_INDEX_FILE'] = str(index)


def git(*args, data=None):
    result = subprocess.run(['git', *args], cwd=ROOT, env=env, input=data, capture_output=True, check=True)
    return result.stdout.decode('utf-8').strip()


git('read-tree', parent)
git('add', '--', *sorted(set(owned)))
blob = git('hash-object', '-w', '--path', 'scripts/collect_training_parallel.py', '--stdin', data=tested)
git('update-index', '--cacheinfo', '100644', blob, 'scripts/collect_training_parallel.py')
changed = git('diff', '--cached', '--name-only', parent).splitlines()
assert not any(path.startswith(('backend/', 'frontend/')) for path in changed), changed
assert git('diff', '--cached', '--numstat', parent, '--', 'scripts/collect_training_parallel.py') == '32\t0\tscripts/collect_training_parallel.py'
git('-c', 'core.whitespace=cr-at-eol', 'diff', '--cached', '--check', parent)
tree = git('write-tree')
message = ('Continue unrelated collection batches while preserving interrupted reservations\n\n'
           'Add an explicit pending-preserving queue option, record a bounded live collection, '
           'frozen-candidate QA, local-service restoration, and linked implementation/understanding evidence.\n\n'
           'Validation: 1450 backend tests passed, 2 Windows symlink-permission skips; '
           '16 live patches generated, 11 eligible; 4285 frozen-candidate files rehashed without mismatch.\n\n'
           'Isolated snapshot excludes concurrent priority-collection and UI work in the shared checkout.\n')
commit = git('commit-tree', tree, '-p', parent, data=message.encode('utf-8'))
git('update-ref', 'refs/heads/' + branch, commit, '0' * 40)
record = {'at': datetime.now().astimezone().isoformat(), 'branch': branch, 'commit': commit,
          'parent': parent, 'tested_collector_raw_sha256': expected, 'collector_git_blob': blob,
          'shared_worktree_untouched': True, 'shared_index_untouched': True,
          'main_branch_untouched': True, 'concurrent_changes_excluded':
          ['backend/app/collection_status.py', 'frontend/src/CollectionStatus.tsx',
           'frontend/src/ModelReview.tsx', 'collector priority-deficit additions'],
          'files_committed': len(changed), 'local_host_detail_xml_excluded': True}
target = EVIDENCE / 'collection-resume-git-isolation-20261018.json'
with target.open('x', encoding='utf-8') as stream:
    json.dump(record, stream, ensure_ascii=False, indent=2)
print(json.dumps(record, ensure_ascii=True))
