"""운영자료 없이 외부 baseline 없는 Temp 배치에서 회귀한다. 제품 파일 아님."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

WS=Path(__file__).resolve().parent
baseline=json.loads((WS/'baseline265.json').read_text(encoding='utf-8'))
paths=[r['path'] for r in baseline['files']]+[
    'tests/selection265_fixtures.py','tests/test_selection265_contract.py',
    'tests/fixtures/selection265/manifest.json','tests/fixtures/selection265/guard.py.fixture',
    'tests/fixtures/selection265/collector.py.fixture']
pins={p:hashlib.sha256((WS/p).read_bytes()).hexdigest() for p in paths}
modules=['test_selection265_contract','test_deficit_metadata_selection260','test_deficit_candidate_guard',
         'test_collect_deficit_guarded','test_targeted_collection_hooks','test_targeted_candidate_quality_policy',
         'test_data_recovery']
with tempfile.TemporaryDirectory(prefix='selection265-portable-') as directory:
    deploy=Path(directory)/'project';deploy.mkdir()
    for rel in paths:
        dest=deploy/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(WS/rel,dest)
    assert not (deploy/'baseline').exists() and not (deploy/'baseline265').exists()
    assert not (deploy.parent/'selection260-workspace-20261018').exists()
    environment=dict(os.environ)
    environment.update(PYTHONPATH=os.pathsep.join(map(str,[deploy,WS.parents[2]/'.runtime',deploy/'backend',
                                                        deploy/'scripts',deploy/'tests'])),
                       PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf-8')
    print(json.dumps({'status':'PORTABLE_TEMP_REGRESSION_STARTED','files':len(paths),
                      'external_baseline_present':False}),flush=True)
    start=time.monotonic()
    result=subprocess.run([sys.executable,'-X','utf8','-m','unittest',*modules,'-q'],cwd=deploy,
                          env=environment,capture_output=True,text=True,encoding='utf-8',timeout=240)
    elapsed=time.monotonic()-start
    (WS/'portable265-regression.log').write_text(result.stdout+result.stderr,encoding='utf-8',newline='\n')
    for rel,sha in pins.items():
        assert hashlib.sha256((WS/rel).read_bytes()).hexdigest()==sha
        assert hashlib.sha256((deploy/rel).read_bytes()).hexdigest()==sha
    report={'status':'PORTABLE_REGRESSION_PASSED' if result.returncode==0 else 'PORTABLE_REGRESSION_FAILED',
            'exit_code':result.returncode,'actual_wall_seconds':round(elapsed,3),
            'files':len(paths),'external_baseline_present':False,'inputs_unchanged':True,
            'rss_observed':False,'operating_data_copied':False,'http':0,'operational_collection':0,
            'pins':pins}
    (WS/'portable265-result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in report.items() if k!='pins'}),flush=True)
    print((result.stdout+result.stderr)[-1800:],flush=True)
    raise SystemExit(result.returncode)
