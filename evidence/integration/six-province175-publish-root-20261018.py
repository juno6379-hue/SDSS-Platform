"""Commit only175 completion files; preserve other tracked work and staged paths."""
from pathlib import Path
import hashlib,json,subprocess
R=Path(__file__).resolve().parents[2]
def git(*args):return subprocess.check_output(['git',*args],cwd=R,text=True,encoding='utf-8').strip()
def sha(p):return hashlib.sha256((R/p).read_bytes()).hexdigest()
files=['backend/app/data/targeted_bare_plan.py','tests/test_targeted_bare_plan.py',
 'docs/implementation/157_targeted_bare_plan.md','docs/implementation/174_six_province_targeted_execution_plan.md',
 'docs/implementation/175_six_province_local_target_plan.md','docs/understanding/175_SIX_PROVINCE_LOCAL_TARGET_PLAN.md']
files+=['evidence/integration/'+p for p in ['six-province-local-plan-agent-20261018.log',
 'six-province-local-plan-independent-20261018.json','six-province175-root-related-20261018.py',
 'six-province175-root-related-20261018.json','six-province175-root-related-20261018.log',
 'six-province175-publish-root-20261018.py']]
assert all((R/p).is_file() for p in files)
assert git('symbolic-ref','HEAD')=='refs/heads/main'
base=git('rev-parse','HEAD');assert base=='51194db3398d11e1a490924893ea2b68c1d99f9a'
assert not git('diff','--cached','--name-only'),'Other staged work; preserve and stop'
modified=git('diff','--name-only').splitlines()
protected={p:sha(p) for p in modified if p not in files and (R/p).is_file()}
pins={p:sha(p) for p in files}
git('add','--',*files)
git('commit','--only','-m','Complete six-province local target plan tests and documentation','--',*files)
commit=git('rev-parse','HEAD')
changed=git('diff-tree','--no-commit-id','--name-only','-r',base,commit).splitlines()
assert set(changed)<=set(files) and 'tests/test_targeted_bare_plan.py' in changed
assert {p:sha(p) for p in protected}==protected
assert {p:sha(p) for p in files}==pins
assert not git('diff','--cached','--name-only')
proof={'base':base,'commit':commit,'branch':'main','owned_files':files,'changed_files':changed,
 'protected_tracked_work_sha256':protected,'protected_work_unchanged':True,
 'preexisting_staged_work':False,'post_commit_index_clean':True,'source_sha256':pins[files[0]],
 'scope':'175 local plan only; execution_supported remains false','pushed':False}
with (R/'evidence/integration/six-province175-publish-root-20261018.json').open('x',encoding='utf-8') as out:json.dump(proof,out,indent=2)
print(json.dumps({'commit':commit,'files_changed':len(changed),'protected_work_unchanged':True,'pushed':False}))
