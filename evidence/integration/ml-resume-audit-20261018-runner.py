"""Read-only live candidate QA; new evidence only. No collection/training path."""
import os
for key, value in {'PROJ_NETWORK':'OFF','GDAL_PAM_ENABLED':'NO','GDAL_DISABLE_READDIR_ON_OPEN':'EMPTY_DIR','GDAL_VRT_ENABLE_PYTHON':'NO'}.items():
    os.environ[key] = value
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from backend.app.ml.readiness import assess

PREFIX = ROOT / 'evidence/integration/ml-resume-audit-20261018'
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def write(suffix, value):
    with Path(str(PREFIX) + suffix).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')

candidate = ROOT/'data/first-group-candidate-qa-stage-20261017/candidate.json'
policy = ROOT/'data/first-group/experiment-esri-v003-2020-2025.json'
source = ROOT/'data/first-group-training-esri-v1/annual-window-report.json'
old = ROOT/'data/first-group/readiness-resume-20261017.json'
stored_qa = ROOT/'data/first-group-candidate-readiness-qa-20261017/readiness.json'
pins = {
    candidate:'2ff7be093db3930d99f10cdc7687809222ef7f525ec6e9cf6248ec144725d158',
    policy:'01991d69bc26487d4ef890de72689da092806bc58cc80ca5f6d6026cf3c79ed7',
    source:'cdc374b2779dee749b57689fd90ef27e3525a48e59062343537327d0f4859a8f',
    old:'6e59c3aee00f53609237b889bfc304a811d298b464b6d6ae2c8e563cc29a34db',
    stored_qa:'847343e1aa4ab9b67fd3bba36a2a9f91d716c2fd411af244e55bbfe1a8414019',
}
protected = list(pins)
protected += list((ROOT/'data/first-group-training-budget').glob('*'))
protected = [p for p in protected if p.is_file()]
before = {str(p.relative_to(ROOT)):digest(p) for p in protected}
assert all(digest(path)==pin for path,pin in pins.items()), 'Pinned input changed'
write('-preflight.json', {'at':datetime.now(timezone.utc).isoformat(),'pins':before,'scope':'READONLY_ACTUAL_RASTER_QA_NEW_EVIDENCE_ONLY'})
commands = [
    [sys.executable, 'scripts/validate_training_split_repair.py', '--saved-plan','evidence/integration/ml-split-repair-plan-20261017.json','--manifest',str(source),'--expected-sha256',pins[source],'--plan',str(policy),'--readiness',str(old),'--readiness-sha256',pins[old],'--candidate',str(candidate),'--candidate-sha256',pins[candidate],'--output',str(PREFIX)+'-split-validation.json'],
    [sys.executable, 'scripts/inspect_bare_patch_feasibility.py','--data-root','data','--expected-report-sha256',pins[stored_qa],'--output',str(PREFIX)+'-bare-feasibility.json'],
]
executions=[]
for index, command in enumerate(commands):
    started=time.monotonic()
    result=subprocess.run(command,cwd=ROOT,capture_output=True,timeout=90)
    for name, data in [('stdout',result.stdout),('stderr',result.stderr)]:
        with Path(str(PREFIX)+f'-command-{index}-{name}.log').open('xb') as stream:stream.write(data)
    executions.append({'command':command,'exit_code':result.returncode,'seconds':round(time.monotonic()-started,3)})
    assert result.returncode==0, result.stderr.decode('utf-8',errors='replace')
started=time.monotonic()
print('Starting actual raster QA (no execute/resume path)',flush=True)
report=assess([candidate],ROOT/'data',json.loads(policy.read_text(encoding='utf-8')),connectivity_diagnostics=True)
elapsed=round(time.monotonic()-started,3)
assert all(digest(path)==pin for path,pin in pins.items()), 'Pinned input changed during QA'
write('-readiness.json',report)
previous=json.loads(stored_qa.read_text(encoding='utf-8'))
unchanged_fields=['status','ready_for_training','scientific_accuracy_validated','blockers','patch_counts_by_split','class_counts_by_split','class_patch_counts_by_split','reference_balance_by_split','policy','coverage','province_unique_locations','province_patch_counts']
field_equality={key:report[key]==previous[key] for key in unchanged_fields}
after={str(p.relative_to(ROOT)):digest(p) for p in protected}
cells=json.loads(ROOT.joinpath('data/first-group-candidate-qa-stage-20261017/staging-receipt.json').read_text(encoding='utf-8'))['projected_after']['eligible_by_province_year']
deficits=[{'province':key.split('/')[0],'year':int(key.split('/')[1]),'eligible':value,'shortfall_to_planning_floor_28':28-value} for key,value in cells.items() if value<28]
write('-summary.json',{'at':datetime.now(timezone.utc).isoformat(),'executions':executions,'actual_raster_qa_seconds':elapsed,'status':report['status'],'ready_for_training':report['ready_for_training'],'blockers':report['blockers'],'eligible':report['patch_counts_by_split'],'same_stored_fields':field_equality,'protected_sha_unchanged':before==after,'protected_files':after,'verified_file_records':len(report['verified_files']),'spatial_location_counts':report['province_unique_locations'],'coverage':report['coverage'],'deficits_to_planning_floor_28':deficits,'total_planning_floor_shortfall':sum(row['shortfall_to_planning_floor_28'] for row in deficits),'network_requests':0,'training_executed':False,'registry_called':False,'collection_executed':False,'original_split_written':False,'scientific_accuracy_validated':False,'scope':'ACTUAL_CANDIDATE_READONLY_RASTER_REASSESSMENT_NOT_SCIENTIFIC_AUTHORIZATION'})
print(json.dumps({'seconds':elapsed,'status':report['status'],'eligible':report['patch_counts_by_split'],'blockers':len(report['blockers']),'all_compared_fields_equal':all(field_equality.values()),'protected_sha_unchanged':before==after}),flush=True)
