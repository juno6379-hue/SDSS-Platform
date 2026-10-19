"""Bounded one-SE execution after207 candidate QA/publication and210 local proposal."""
from pathlib import Path
from datetime import datetime,timezone
import copy,hashlib,json,os,subprocess,sys,time
R=Path(__file__).resolve().parents[2];E=R/'evidence/integration';D=R/'data'
def read(p):return json.loads(p.read_text('utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert not (E/'deficit211-launch-root-20261018.json').exists()
assert not (D/'first-group-training-budget/global-ledger.execution.lock').exists()
active=subprocess.check_output(['powershell','-NoProfile','-Command',"Get-CimInstance Win32_Process | Where-Object {$_.Name -match 'python' -and $_.CommandLine -match 'scripts[\\\\/](collect_training_(parallel|priority)|collect_targeted_bare|collect_deficit_guarded|prepare_priority_candidate164)\\.py'} | Select-Object ProcessId | ConvertTo-Json"],text=True)
assert not active.strip()
published=read(E/'priority207-publication-root-20261018.json')
assert published['status']=='COMPLETED_QA_PUBLISHED_AND_READER_VERIFIED'
assert published['source_snapshot_sha256']=='80eef2d274942c7a7f9bf8ee2483af070a729060d84ceb1a19baacb52ae4976a'
assert published['candidate_view']['available'] and published['candidate_view']['source_matches_current_manifest']
proposal=read(D/'centers210-fresh-20261018/proposal.json')
assert sha(D/'centers210-fresh-20261018/proposal.json')=='ac8eee26a5902b1eb1bf2f65bfa9a7895d4d25d7231e78632bcaab6638c42d37'
mp=D/'first-group-training-esri-v1/annual-window-report.json';lp=D/'first-group-training-budget/global-ledger.json'
mr=mp.read_bytes();lr=lp.read_bytes();state=json.loads(lr)
assert hashlib.sha256(mr).hexdigest()=='80eef2d274942c7a7f9bf8ee2483af070a729060d84ceb1a19baacb52ae4976a'
assert hashlib.sha256(lr).hexdigest()=='6e9e27b0ba9e4d222f9fde6b1e22f2adfd604701163d8e2c4653617c47af02fc'
pending={k:v for k,v in state['batches'].items() if v['status']=='pending'}
assert len(pending)==2 and sum(v['reserved_bytes'] for v in pending.values())==136314880
assert state['additional_maximum_bytes']==4*1024**3 and not state['rate_limit_active']
assert state['additional_maximum_bytes']-state['new_charged_bytes']>=68157440
approval=read(E/'deficit211-reviewed-code-pins-root-20261018.json')
assert approval['status']=='REVIEWED_TESTED_BOUNDED_EXECUTION_APPROVED'
assert all(sha(R/p)==pin for p,pin in approval['source_pins'].items())
request=read(E/'deficit211-prepared-request-root-20261018.json')
pin=hashlib.sha256(json.dumps(request,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode()).hexdigest()
candidate=proposal['candidates'][0]
assert request['selected']==[{'spatial_window_id':candidate['spatial_window_id'],'year':2024}] and request['maximum_batches']==1
identifier=candidate['spatial_window_id'];idsha=hashlib.sha256(json.dumps(identifier,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
template=read(E/'centers205-review-result-root-20261018.json')['review']['job_proposals'][0]
template_request=read(E/'centers205-review-request-root-20261018.json')
assert request['config_ref']==template_request['config_ref'] and sha(R/request['config_ref']['path'])==request['config_ref']['sha256']
assert template['province']=='southeast_sulawesi' and template['year']==2024 and template['nominal_patches']==16
expected_config=copy.deepcopy(template['config'])
expected_config['aois'][0].update(id=identifier,bbox=candidate['bbox'])
expected_config_sha=hashlib.sha256(json.dumps(expected_config,sort_keys=True).encode()).hexdigest()
jobs=[{'key':f'center1024-southeast_sulawesi-2024-{pin[:12]}-{idsha[:8]}','province':'southeast_sulawesi','year':2024,'split':'train','nominal_patches':16,'spatial_window_id':identifier,'config_sha256':expected_config_sha}]
assert candidate['province']=='southeast_sulawesi' and candidate['years']==[2024]
assert all(j['key'] not in state['batches'] for j in jobs)
rp=E/'deficit211-request-root-20261018.json'
with rp.open('x',encoding='utf-8') as f:json.dump(request,f,ensure_ascii=False,indent=2)
assert mp.read_bytes()==mr and lp.read_bytes()==lr
command=[sys.executable,'-X','faulthandler',str(R/'scripts/collect_deficit_guarded.py'),'--request',rp.relative_to(R).as_posix(),'--expected-request-sha256',pin,'--execute']
record={'started_at':datetime.now(timezone.utc).isoformat(),'status':'STARTED_PREFLIGHT_NOT_COMPLETED','manifest_before_sha256':sha(mp),'ledger_before_sha256':sha(lp),'source_rows_before':len(json.loads(mr)['scenes']),'pending_before':pending,'request_sha256':pin,'selected_jobs':[{k:j[k] for k in ('key','province','year','split','nominal_patches','spatial_window_id','config_sha256')} for j in jobs],'command':command,'new_budget_added':False,'training_started':False,'source_pins':approval['source_pins'],'maximum_new_physical_patches':16}
record['expected_config_derivation']={'template_proof_sha256':sha(E/'centers205-review-result-root-20261018.json'),'template_key':template['key'],'changes':['AOI id','AOI bbox'],'scope':'Expected config only;200 still performs fresh real full preflight'}
started=time.monotonic()
with (E/'deficit211-live-root-20261018-stdout.log').open('xb') as out,(E/'deficit211-live-root-20261018-stderr.log').open('xb') as err:
    p=subprocess.Popen(command,cwd=R,env=dict(os.environ,PYTHONIOENCODING='utf-8',PYTHONFAULTHANDLER='1'),stdin=subprocess.DEVNULL,stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
    record['pid']=p.pid
    with (E/'deficit211-launch-root-20261018.json').open('x',encoding='utf-8') as f:json.dump(record,f,ensure_ascii=False,indent=2)
    print(json.dumps({'pid':p.pid,'status':record['status']}),flush=True)
    code=p.wait()
record.update(status='PROCESS_TERMINATED_REVIEW_STDOUT_AND_LEDGER',exit_code=code,seconds=time.monotonic()-started,finished_at=datetime.now(timezone.utc).isoformat(),lock_present=(D/'first-group-training-budget/global-ledger.execution.lock').exists())
with (E/'deficit211-terminal-root-20261018.json').open('x',encoding='utf-8') as f:json.dump(record,f,ensure_ascii=False,indent=2)
print(json.dumps({'exit_code':code,'seconds':record['seconds'],'lock_present':record['lock_present']}),flush=True)
