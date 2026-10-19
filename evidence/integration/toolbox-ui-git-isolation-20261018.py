"""Commit reviewed Toolbox files only; preserve concurrent pipeline work."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
def git(*args, env=None):
    return subprocess.check_output(['git',*args],cwd=root,env=env,text=True,encoding='utf-8').strip()
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None

base = '8cf7b9421ea3d5916058a9e4622dc19c9075e9f2'
files = ['frontend/src/'+name for name in ['App.tsx','PlatformShell.tsx','GeoAIToolbox.tsx','geoai-toolbox.css','toolboxAdapter.ts','toolboxAdapter.test.mjs']]
files += ['docs/implementation/toolbox_visual_hub_20261018.md','docs/understanding/06_toolbox_visual_hub_20261018.md']
files += ['evidence/integration/'+name for name in [
    'toolbox-ui-preflight-20261018.json','toolbox-ui-independent-20261018.py','toolbox-ui-independent-20261018.json',
    'toolbox-ui-finalize-20261018.py','toolbox-ui-final-20261018.json','toolbox-ui-wire-20261018.py',
    'toolbox-ui-desktop-top-20261018.jpg','toolbox-ui-desktop-20261018.jpg','toolbox-ui-mobile-20261018.jpg',
    'toolbox-ui-current-base-review-20261018.json','toolbox-ui-current-frontend-20261018.log',
    'toolbox-ui-hover-build-20261018.log','toolbox-ui-current-final-20261018.py','toolbox-ui-current-final-20261018.json',
    'toolbox-ui-hover-before-20261018.jpg','toolbox-ui-hover-after-20261018.jpg',
    'toolbox-ui-current-browser-20261018.txt','toolbox-ui-current-browser-20261018.jpg','toolbox-ui-git-isolation-20261018.py']]
assert all((root/name).is_file() for name in files)
index = Path(git('rev-parse','--path-format=absolute','--git-path','index'))
head, head_ref, index_sha = git('rev-parse','HEAD'), git('symbolic-ref','HEAD'), sha(index)
file_shas = {name:sha(root/name) for name in files}
branch = 'refs/heads/codex/toolbox-visual-hub-20261018'
with tempfile.TemporaryDirectory(prefix='geoai-toolbox-git-') as folder:
    env = dict(os.environ,GIT_INDEX_FILE=str(Path(folder)/'index'))
    git('read-tree',base,env=env)
    git('add','--',*files,env=env)
    tree = git('write-tree',env=env)
    changed = git('diff-tree','--no-commit-id','--name-only','-r',base,tree).splitlines()
    assert set(changed) == set(files), changed
    message = Path(folder)/'message.txt'
    message.write_text('Build visual GeoAI Toolbox hub and preserve readable hover states\n\nAdd image model cards, province map, workflow and actual API summaries.\nKeep existing model workspaces intact and separate reference images from results.\nValidate293 frontend tests, final build and actual browser navigation/hover.\n',encoding='utf-8')
    commit = git('commit-tree',tree,'-p',base,'-F',str(message),env=env)
    git('update-ref',branch,commit,'0'*40)
assert git('rev-parse','HEAD') == head and git('symbolic-ref','HEAD') == head_ref
assert sha(index) == index_sha
assert {name:sha(root/name) for name in files} == file_shas
report = {'base':base,'commit':commit,'branch':branch,'files':files,
          'shared_head_preserved':True,'shared_index_preserved':True,'working_files_preserved':True,
          'pipeline_or_guard_wip_included':False,'pushed':False}
(root/'evidence/integration/toolbox-ui-git-isolation-20261018.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'commit':commit,'branch':branch,'file_count':len(files),'shared_index_preserved':True,'pushed':False}))
