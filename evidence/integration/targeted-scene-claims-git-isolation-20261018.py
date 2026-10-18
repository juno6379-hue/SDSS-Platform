"""Snapshot only162 on top of160; never checkout, reset or change shared index."""
from pathlib import Path
import os
import subprocess
import hashlib
import tempfile
import json

root = Path(__file__).resolve().parents[2]
def git(*args, env=None):
    return subprocess.check_output(['git',*args],cwd=root,env=env,text=True,encoding='utf-8').strip()
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None

files = ['backend/app/data/targeted_scene_claims.py','tests/test_targeted_scene_claims.py',
         'docs/implementation/162_targeted_scene_claims.md','docs/understanding/162_TARGETED_SCENE_CLAIMS.md']
files += ['evidence/integration/'+name for name in [
    'targeted-scene-claims-agent-20261018.log','targeted-scene-claims-independent-20261018.json',
    'targeted-scene-claims-root-related-20261018.log','targeted-scene-claims-real-history-20261018.py',
    'targeted-scene-claims-real-history-20261018.json','targeted-scene-claims-git-isolation-20261018.py']]
assert all((root/name).is_file() for name in files)
base = git('rev-parse','codex/targeted-asset-geometry-20261018')
head = git('rev-parse','HEAD')
head_ref = git('symbolic-ref','HEAD')
index = Path(git('rev-parse','--path-format=absolute','--git-path','index'))
index_sha = sha(index)
file_shas = {name:sha(root/name) for name in files}
branch = 'refs/heads/codex/targeted-scene-claims-20261018'
with tempfile.TemporaryDirectory(prefix='geoai162-git-') as folder:
    env = dict(os.environ,GIT_INDEX_FILE=str(Path(folder)/'index'))
    git('read-tree',base,env=env)
    git('add','--',*files,env=env)
    tree = git('write-tree',env=env)
    changed = git('diff-tree','--no-commit-id','--name-only','-r',base,tree).splitlines()
    assert set(changed) == set(files), changed
    message = Path(folder)/'message.txt'
    message.write_text('Add process-local atomic scene claims with execution kept blocked\n\nCheck declared history, quarantine, ownership and capacity under one lock.\nValidate10 focused tests,28 related tests and94 stored scene declarations.\nKeep verified inventory and collector integration as separate work.\n',encoding='utf-8')
    commit = git('commit-tree',tree,'-p',base,'-F',str(message),env=env)
    git('update-ref',branch,commit,'0'*40)
assert git('rev-parse','HEAD') == head and git('symbolic-ref','HEAD') == head_ref
assert sha(index) == index_sha
assert {name:sha(root/name) for name in files} == file_shas
report = {'base':base,'commit':commit,'branch':branch,'files':files,
          'shared_head_preserved':True,'shared_index_preserved':True,'working_files_preserved':True,'pushed':False}
(root/'evidence/integration/targeted-scene-claims-git-isolation-20261018.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'commit':commit,'branch':branch,'shared_index_preserved':True,'pushed':False}))
