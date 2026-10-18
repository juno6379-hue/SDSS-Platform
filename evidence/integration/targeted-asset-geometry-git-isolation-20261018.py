"""Commit only160 files on a separate ref; preserve shared HEAD, index and files."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
def git(*args, env=None):
    return subprocess.check_output(['git', *args], cwd=root, env=env, text=True, encoding='utf-8').strip()
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None

files = ['backend/app/data/targeted_asset_geometry.py','tests/test_targeted_asset_geometry.py',
         'docs/implementation/160_targeted_asset_geometry.md','docs/understanding/160_TARGETED_ASSET_GEOMETRY.md']
files += ['evidence/integration/'+name for name in [
    'targeted-asset-geometry-agent-20261018.log','targeted-asset-geometry-independent-20261018.json',
    'targeted-asset-geometry-root-related-20261018.log','targeted-asset-geometry-preflight-20261018.json',
    'targeted-asset-geometry-real-20261018.py','targeted-asset-geometry-real-20261018.json',
    'targeted-asset-geometry-git-isolation-20261018.py']]
assert all((root/name).is_file() for name in files)
base = git('rev-parse','HEAD')
git('cat-file','-e',base+':backend/app/data/targeted_bare_plan.py')
head = git('symbolic-ref','HEAD')
index = Path(git('rev-parse','--path-format=absolute','--git-path','index'))
before_index = sha(index)
before_files = {name:sha(root/name) for name in files}
branch = 'refs/heads/codex/targeted-asset-geometry-20261018'
with tempfile.TemporaryDirectory(prefix='geoai160-git-') as folder:
    env = dict(os.environ, GIT_INDEX_FILE=str(Path(folder)/'index'))
    git('read-tree',base,env=env)
    git('add','--',*files,env=env)
    tree = git('write-tree',env=env)
    changed = git('diff-tree','--no-commit-id','--name-only','-r',base,tree).splitlines()
    assert set(changed) == set(files), changed
    message = Path(folder)/'message.txt'
    message.write_text('Validate pinned local imagery and label coverage without execution\n\nAdd independent asset geometry observations with fail-closed input guards.\nVerify10 focused tests,18 related tests and one preserved real local pair.\nKeep collector execution, pixel quality and pending footprint guards separate.\n',encoding='utf-8')
    commit = git('commit-tree',tree,'-p',base,'-F',str(message),env=env)
    git('update-ref',branch,commit,'0'*40)
assert git('rev-parse','HEAD') == base and git('symbolic-ref','HEAD') == head
assert sha(index) == before_index
assert {name:sha(root/name) for name in files} == before_files
result = {'base':base,'commit':commit,'branch':branch,'files':files,
          'shared_head_preserved':True,'shared_index_sha256_preserved':True,
          'working_files_preserved':True,'pushed':False}
(root/'evidence/integration/targeted-asset-geometry-git-isolation-20261018.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'commit':commit,'branch':branch,'shared_index_preserved':True,'pushed':False}))
