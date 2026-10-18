"""One-time audited launch of the explicitly pinned, bounded two-batch plan."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,datetime
ROOT=Path(__file__).resolve().parents[2]
E=ROOT/'evidence/integration';D=ROOT/'data'
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text('utf-8'))
if (E/'priority-collection-round7-launch-20261018.json').exists():raise RuntimeError('Launch record exists; inspect, do not repeat')
if (D/'first-group-training-budget/global-ledger.execution.lock').exists():raise RuntimeError('Existing execution lock preserved')
processes=subprocess.check_output(['powershell','-NoProfile','-Command',"Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^python.*\\.exe$' -and $_.CommandLine -match 'scripts[\\\\/]collect_training_(parallel|priority)\\.py' } | Select-Object ProcessId,CommandLine | ConvertTo-Json"],text=True,encoding='utf-8',errors='replace')
if processes.strip():raise RuntimeError('Existing collector; no duplicate launch')
ledger_path=D/'first-group-training-budget/global-ledger.json';manifest_path=D/'first-group-training-esri-v1/annual-window-report.json'
ledger=read(ledger_path);manifest=read(manifest_path)
pending={k:v for k,v in ledger['batches'].items() if v['status']=='pending'}
assert len(pending)==2 and sum(x['reserved_bytes'] for x in pending.values())==136314880
assert ledger['additional_maximum_bytes']-ledger['new_charged_bytes'] >= 2*68157440
assert not ledger.get('rate_limit_active',False)
plan=read(E/'priority-collection-round7-dryrun-20261018.json')['priority_plan']
assert [(j['province'],j['year']) for j in plan['selected_jobs']]==[('southeast_sulawesi',2021),('southeast_sulawesi',2023)]
record={'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PREPARED',
 'plan_sha256':plan['plan_sha256'],'selected_jobs':plan['selected_jobs'],'pending_before':pending,
 'manifest_before_sha256':digest(manifest_path),'manifest_before_rows':len(manifest['scenes']),
 'old_rows_canonical_sha256':hashlib.sha256(json.dumps(manifest['scenes'],sort_keys=True).encode()).hexdigest(),
 'ledger_before_sha256':digest(ledger_path),'new_charged_before':ledger['new_charged_bytes'],
 'budget_remaining_before':ledger['additional_maximum_bytes']-ledger['new_charged_bytes'],
 'source_pins':{name:digest(ROOT/name) for name in ('scripts/collect_training_priority.py','scripts/collect_training_parallel.py')},
 'new_budget_added':False,'training_started':False,'pending_refund':False}
command=[sys.executable,str(ROOT/'scripts/collect_training_priority.py'),'--max-batches','2',
 '--continue-unrelated-pending','--expected-plan-sha256',plan['plan_sha256'],'--execute']
env=os.environ.copy();env['PYTHONIOENCODING']='utf-8'
with (E/'priority-collection-round7-live-20261018-stdout.log').open('xb') as out,(E/'priority-collection-round7-live-20261018-stderr.log').open('xb') as err:
 process=subprocess.Popen(command,cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,
     creationflags=subprocess.DETACHED_PROCESS|subprocess.CREATE_NO_WINDOW)
record.update(status='STARTED_NOT_COMPLETED',wrapper_pid=process.pid,command=command)
(E/'priority-collection-round7-launch-20261018.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'pid':process.pid,'selected_jobs':plan['selected_jobs'],'status':record['status']}))
