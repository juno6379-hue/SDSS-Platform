"""Root one-batch249 supervisor; requires a separately reviewed request and approval."""
from pathlib import Path
from datetime import datetime,timezone
import copy,hashlib,json,os,subprocess,sys,time
R=Path(__file__).resolve().parents[2];E=R/'evidence/integration';D=R/'data'
def read(p):return json.loads(p.read_text('utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canonical(v):return hashlib.sha256(json.dumps(v,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode()).hexdigest()
def write(p,v):
    with p.open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2)
def launch_and_wait(command,record,launch_path,out,err,process_options):
    # Journal failure must never abandon a child that may already hold a budget reservation.
    p=subprocess.Popen(command,stdout=out,stderr=err,**process_options)
    record['pid']=p.pid
    try:
        try:write(launch_path,record)
        except Exception as exc:
            record['launch_record_write_error']=type(exc).__name__
            print(json.dumps({'status':'LAUNCH_RECORD_WRITE_FAILED_CHILD_STILL_OWNED','pid':p.pid}),flush=True)
        print(json.dumps({'pid':p.pid,'status':record['status']}),flush=True)
    except Exception as exc:
        record['supervisor_notification_error']=type(exc).__name__
    finally:
        code=p.wait()
    return code
approval=read(E/'deficit249-reviewed-code-pins-root-20261018.json')
assert approval['status']=='ROOT_APPROVED_ONE_SE2024_BATCH_AFTER_AUDITED_ZERO235'
assert approval['maximum_batches']==1 and approval['maximum_new_physical_patches']==16
assert all(sha(R/n)==pin for n,pin in approval['source_pins'].items())
assert not (E/'deficit249-launch-root-20261018.json').exists()
lock=D/'first-group-training-budget/global-ledger.execution.lock'
assert not lock.exists()
active=subprocess.check_output(['powershell','-NoProfile','-Command',"Get-CimInstance Win32_Process | Where-Object {$_.Name -match 'python' -and $_.CommandLine -match 'scripts[\\\\/](collect_training_(parallel|priority)|collect_targeted_bare|collect_deficit_guarded|prepare_priority_candidate164)\\.py'} | Select-Object ProcessId | ConvertTo-Json"],text=True)
assert not active.strip()
audit=E/'deficit235-native-root-20261018.json'
assert sha(audit)==approval['prior235_audit_sha256']
a=read(audit);assert a['new_physical_patches']==0 and a['new_eligible_patches']==0 and all(a['checks'].values())
mp=D/'first-group-training-esri-v1/annual-window-report.json';lp=D/'first-group-training-budget/global-ledger.json'
mr=mp.read_bytes();lr=lp.read_bytes();state=json.loads(lr)
assert sha(mp)==approval['source_sha256'] and sha(lp)==approval['ledger_sha256']
pending={k:v for k,v in state['batches'].items() if v['status']=='pending'}
assert len(pending)==2 and sum(v['reserved_bytes'] for v in pending.values())==136314880
assert pending==read(E/'deficit235-terminal-root-20261018.json')['pending_before']
assert state['additional_maximum_bytes']==4*1024**3 and not state['rate_limit_active']
assert state['additional_maximum_bytes']-state['new_charged_bytes']>=68157440
request=read(E/'deficit249-prepared-request-root-20261018.json');pin=canonical(request)
assert pin==approval['request_sha256'] and request['maximum_batches']==1
for name in ['proposal_ref','current_manifest_ref','ledger_ref','boundary_ref','config_ref','prior_plan_ref']:
    assert sha(R/request[name]['path'])==request[name]['sha256']
assert request['current_manifest_ref']['sha256']==sha(mp) and request['ledger_ref']['sha256']==sha(lp)
proposal=read(R/request['proposal_ref']['path']);selected=request['selected'][0]
candidates=[c for c in proposal['candidates'] if c['spatial_window_id']==selected['spatial_window_id']]
assert len(request['selected'])==len(candidates)==1
c=candidates[0];assert c['province']=='southeast_sulawesi' and c['years']==[2024] and selected['year']==2024
identifier=c['spatial_window_id'];idsha=canonical(identifier)
template=read(E/'centers205-review-result-root-20261018.json')['review']['job_proposals'][0]
assert sha(E/'centers205-review-result-root-20261018.json')==approval['config_template_ref']['sha256']
assert sha(E/'centers205-review-request-root-20261018.json')==approval['config_template_request_ref']['sha256']
assert template['province']=='southeast_sulawesi' and template['year']==2024
assert request['config_ref']==read(E/'centers205-review-request-root-20261018.json')['config_ref']
config=copy.deepcopy(template['config']);config['aois'][0].update(id=identifier,bbox=c['bbox'])
configsha=hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest()
job={'key':f'center1024-southeast_sulawesi-2024-{pin[:12]}-{idsha[:8]}','province':'southeast_sulawesi','year':2024,'split':'train','nominal_patches':16,'spatial_window_id':identifier,'config_sha256':configsha}
assert job['key'] not in state['batches']
rp=E/'deficit249-request-root-20261018.json';write(rp,request)
assert mp.read_bytes()==mr and lp.read_bytes()==lr
command=[sys.executable,'-X','faulthandler',str(R/'scripts/collect_deficit_guarded.py'),'--request',rp.relative_to(R).as_posix(),'--expected-request-sha256',pin,'--execute']
record={'started_at':datetime.now(timezone.utc).isoformat(),'status':'STARTED_FRESH_PREFLIGHT_NOT_COLLECTION_SUCCESS','manifest_before_sha256':sha(mp),'ledger_before_sha256':sha(lp),'source_rows_before':len(json.loads(mr)['scenes']),'pending_before':pending,'request_sha256':pin,'selected_jobs':[job],'command':command,'source_pins':approval['source_pins'],'new_budget_added':False,'training_started':False,'maximum_new_physical_patches':16,'expected_config_derivation':{'template_proof_sha256':sha(E/'centers205-review-result-root-20261018.json'),'changes':['AOI id','AOI bbox'],'scope':'Config derivation only; fresh200 inventory under lock required'}}
started=time.monotonic()
with (E/'deficit249-live-root-20261018-stdout.log').open('xb') as out,(E/'deficit249-live-root-20261018-stderr.log').open('xb') as err:
    code=launch_and_wait(command,record,E/'deficit249-launch-root-20261018.json',out,err,{'cwd':R,'env':dict(os.environ,PYTHONIOENCODING='utf-8',PYTHONFAULTHANDLER='1'),'stdin':subprocess.DEVNULL,'creationflags':subprocess.CREATE_NO_WINDOW})
record.update(status='PROCESS_TERMINATED_REQUIRES_SETTLEMENT_AUDIT',exit_code=code,seconds=time.monotonic()-started,finished_at=datetime.now(timezone.utc).isoformat(),lock_present=lock.exists())
write(E/'deficit249-terminal-root-20261018.json',record)
print(json.dumps({'exit_code':code,'seconds':record['seconds'],'lock_present':record['lock_present']}),flush=True)
