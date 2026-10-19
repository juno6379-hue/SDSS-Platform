"""Single bounded continuation after round8 native QA. Preserve old pending reservations."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,subprocess,sys
R=Path(__file__).resolve().parents[2];E=R/'evidence/integration';D=R/'data'
def read(path):return json.loads(path.read_bytes())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
receipt=E/'priority-collection-round9-launch-root-20261018.json'
assert not receipt.exists(),'Existing launch: inspect rather than repeat'
assert not (D/'first-group-training-budget/global-ledger.execution.lock').exists(),'Existing lock preserved'
processes=subprocess.check_output(['powershell','-NoProfile','-Command',
    "Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^python.*\\.exe$' -and $_.CommandLine -match 'scripts[\\\\/](collect_training_(parallel|priority)|collect_targeted_bare|audit_priority_increment165)\\.py' } | Select-Object ProcessId,CommandLine | ConvertTo-Json"],text=True,encoding='utf-8',errors='replace')
assert not processes.strip(),'Existing collector/audit; no duplicate'
native=read(E/'priority165-round8-native-root-20261018.json')
assert native['status']=='COMPLETED_NATIVE_CHECKED' and native['native_patches_checked']==32 and native['native_eligible_patches']==26
mp=D/'first-group-training-esri-v1/annual-window-report.json';lp=D/'first-group-training-budget/global-ledger.json'
manifest=read(mp);ledger=read(lp)
assert sha(mp)=='c68b0fcc79dd1a97ab1e0b42c66955ee6dfd0a8fe45489280207cdc01f1d05d8'
assert sha(lp)=='e0557f3d22a3f7ea82218344b83a01d8962320105cbe8fdacc1d42522fae8858'
assert ledger['additional_maximum_bytes']==4*1024**3 and ledger['rate_limit_active'] is False
pending={k:v for k,v in ledger['batches'].items() if v['status']=='pending'}
assert len(pending)==2 and sum(v['reserved_bytes'] for v in pending.values())==136314880
assert ledger['additional_maximum_bytes']-ledger['new_charged_bytes']>=2*68157440
plan=read(E/'priority-collection-round9-dryrun-root-20261018.json')['priority_plan']
assert [(j['province'],j['year'],j['spatial_window_id']) for j in plan['selected_jobs']]==[('east_java',2020,'02'),('east_java',2020,'03')]
assert plan['plan_sha256']=='3bdc4a17dbc7e9f97bcbeadcfe2fb2a572e499ca5f17279e01a44cec1fcc9363'
assert all(j['key'] not in ledger['batches'] and j['split']=='train' for j in plan['selected_jobs'])
assert len(manifest['scenes'])+32<=3000
record={'started_at':datetime.now(timezone.utc).isoformat(),'status':'STARTED_NOT_COMPLETED',
 'plan_sha256':plan['plan_sha256'],'selected_jobs':plan['selected_jobs'],'pending_before':pending,
 'manifest_before_rows':len(manifest['scenes']),'manifest_before_sha256':sha(mp),
 'old_rows_canonical_sha256':hashlib.sha256(json.dumps(manifest['scenes'],sort_keys=True).encode()).hexdigest(),
 'ledger_before_sha256':sha(lp),'new_charged_before':ledger['new_charged_bytes'],
 'budget_remaining_before':ledger['additional_maximum_bytes']-ledger['new_charged_bytes'],
 'source_pins':{p:sha(R/p) for p in ['scripts/collect_training_priority.py','scripts/collect_training_parallel.py','backend/app/data/parallel.py']},
 'round8_native_qa_sha256':sha(E/'priority165-round8-native-root-20261018.json'),
 'new_budget_added':False,'training_started':False,'pending_refund':False}
command=[sys.executable,str(R/'scripts/collect_training_priority.py'),'--max-batches','2',
 '--continue-unrelated-pending','--expected-plan-sha256',plan['plan_sha256'],'--execute']
env=dict(os.environ,PYTHONIOENCODING='utf-8')
with (E/'priority-collection-round9-live-root-20261018-stdout.log').open('xb') as out,(E/'priority-collection-round9-live-root-20261018-stderr.log').open('xb') as err:
    process=subprocess.Popen(command,cwd=R,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,
        creationflags=subprocess.DETACHED_PROCESS|subprocess.CREATE_NO_WINDOW)
record.update(wrapper_pid=process.pid,command=command)
with receipt.open('x',encoding='utf-8') as output:json.dump(record,output,ensure_ascii=False,indent=2)
print(json.dumps({'wrapper_pid':process.pid,'status':record['status'],'jobs':plan['selected_jobs']}))
