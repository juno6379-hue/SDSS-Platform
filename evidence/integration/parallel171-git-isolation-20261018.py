"""171 소유 파일만 별도 로컬 branch에 고정. 공유 index/HEAD/WIP 보존."""
from pathlib import Path
import hashlib,json,os,subprocess,tempfile
root=Path(__file__).resolve().parents[2]
def git(*args,env=None):
    return subprocess.check_output(['git',*args],cwd=root,env=env,text=True,encoding='utf-8').strip()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
files=['backend/app/data/parallel.py','tests/test_data_parallel.py',
       'docs/implementation/171_parallel_finalization_recovery.md',
       'docs/understanding/171_PARALLEL_FINALIZATION_RECOVERY.md']
files+=['evidence/integration/'+name for name in [
    'parallel-finalization-recovery-agent-20261018.log',
    'parallel171-root-related-20261018.py','parallel171-root-related-20261018.json',
    'parallel171-root-related-20261018.log','parallel171-git-isolation-20261018.py']]
assert all((root/p).is_file() for p in files)
head=git('rev-parse','HEAD');head_ref=git('symbolic-ref','HEAD')
index=Path(git('rev-parse','--path-format=absolute','--git-path','index'));index_sha=sha(index)
pins={p:sha(root/p) for p in files}
branch='refs/heads/codex/parallel-finalization-20261018'
with tempfile.TemporaryDirectory(prefix='geoai-parallel171-git-') as folder:
    env=dict(os.environ,GIT_INDEX_FILE=str(Path(folder)/'index'))
    git('read-tree',head,env=env)
    git('add','--',*files,env=env)
    tree=git('write-tree',env=env)
    changed=git('diff-tree','--no-commit-id','--name-only','-r',head,tree).splitlines()
    assert set(changed)==set(files),changed
    message=Path(folder)/'message.txt'
    message.write_text('Finalize submitted collection workers before propagating coordinator failures\n\nStop new submissions on reservation, iterator, submission or finalization errors.\nAttempt each existing finalization once; preserve the first exception without replay.\nValidate12 focused and50 related synthetic tests; preserve real pending reservations.\nRelated tests used the shared working tree including separately owned targeted modules.\n',encoding='utf-8')
    commit=git('commit-tree',tree,'-p',head,'-F',str(message),env=env)
    git('update-ref',branch,commit,'0'*40)
assert git('rev-parse','HEAD')==head and git('symbolic-ref','HEAD')==head_ref
assert sha(index)==index_sha
assert {p:sha(root/p) for p in files}==pins
report={'base':head,'commit':commit,'branch':branch,'files':files,'file_sha256':pins,
        'shared_head_preserved':True,'shared_index_preserved':True,'working_files_preserved':True,
        'other_targeted_wip_included':False,'pushed':False,
        'validation_scope':'Shared working tree;50 related synthetic tests include separately owned targeted modules.'}
with (root/'evidence/integration/parallel171-git-isolation-20261018.json').open('x',encoding='utf-8') as output:
    json.dump(report,output,ensure_ascii=False,indent=2)
print(json.dumps({'commit':commit,'branch':branch,'files':len(files),'shared_index_preserved':True,'pushed':False}))
