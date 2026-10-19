"""Root one-batch279 supervisor; requires a separately reviewed request and approval."""
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
approval=read(E/'deficit279-reviewed-code-pins-root-20261018.json')
assert approval['status']=='ROOT_APPROVED_ONE_GORO2025_V2_BATCH_AFTER_AUDITED_270'
assert approval['maximum_batches']==1 and approval['maximum_new_physical_patches']==16
assert read(R/approval['runtime_validation_ref']['path'])['status']=='SHARED_PROJECT96_VERIFIED_AFTER_ROOT_ENVIRONMENT_CORRECTION'
assert sha(R/approval['runtime_validation_ref']['path'])==approval['runtime_validation_ref']['sha256']
assert all(sha(R/n)==pin for n,pin in approval['source_pins'].items())
assert not (E/'deficit279-launch-root-20261018.json').exists()
lock=D/'first-group-training-budget/global-ledger.execution.lock'
assert not lock.exists()
active=subprocess.check_output(['powershell','-NoProfile','-Command',"Get-CimInstance Win32_Process | Where-Object {$_.Name -match 'python' -and $_.CommandLine -match 'scripts[\\\\/](collect_training_(parallel|priority)|collect_targeted_bare|collect_deficit_guarded|prepare_priority_candidate164)\\.py'} | Select-Object ProcessId | ConvertTo-Json"],text=True)
assert not active.strip()
audit=E/'deficit270-native-root-20261018.json'
assert sha(audit)==approval['prior270_audit_sha256']
a=read(audit);assert a['status']=='COMPLETED_BOUNDED_NATIVE_AND_TRACE_CHECKED' and a['native_validation_complete'] is True and a['product165']['native_patches_checked']==16 and a['product165']['native_eligible_patches']==6 and a['old_rows_exact'] and a['old_pending_exact']
mp=D/'first-group-training-esri-v1/annual-window-report.json';lp=D/'first-group-training-budget/global-ledger.json'
mr=mp.read_bytes();lr=lp.read_bytes();state=json.loads(lr)
assert sha(mp)==approval['source_sha256'] and sha(lp)==approval['ledger_sha256']
pending={k:v for k,v in state['batches'].items() if v['status']=='pending'}
assert len(pending)==2 and sum(v['reserved_bytes'] for v in pending.values())==136314880
assert pending==read(E/'deficit235-terminal-root-20261018.json')['pending_before']
assert state['additional_maximum_bytes']==4*1024**3 and not state['rate_limit_active']
assert state['additional_maximum_bytes']-state['new_charged_bytes']>=68157440
request=read(E/'deficit279-prepared-request-root-20261018.json');pin=canonical(request)
assert pin==approval['request_sha256'] and request['maximum_batches']==1
for name in ['proposal_ref','current_manifest_ref','ledger_ref','boundary_ref','config_ref','prior_plan_ref']:
    assert sha(R/request[name]['path'])==request[name]['sha256']
assert request['schema_version']==2 and request['candidate_metadata_policy']=='DEFICIT_AOI_BBOX_CONTAINS_V1'
assert request['current_manifest_ref']['sha256']==sha(mp) and request['ledger_ref']['sha256']==sha(lp)
proposal=read(R/request['proposal_ref']['path']);selected=request['selected'][0]
candidates=[c for c in proposal['candidates'] if c['spatial_window_id']==selected['spatial_window_id']]
assert len(request['selected'])==len(candidates)==1
c=candidates[0];assert c['province']=='gorontalo' and c['years']==[2025] and selected['year']==2025
identifier=c['spatial_window_id'];idsha=canonical(identifier)
# Derive expected config from the pinned six-province base, matching current guard391-406.
config=copy.deepcopy(read(R/request['config_ref']['path']))
base_aois=[x for x in config['aois'] if x['id']=='gorontalo'];assert len(base_aois)==1
aoi=copy.deepcopy(base_aois[0]);aoi.update(id=identifier,province_id='gorontalo',bbox=copy.deepcopy(c['bbox']))
config.update(aois=[aoi],years=[2025],bands=['blue','green','red','nir','swir16','swir22'],annual_reference='esri_io',
 window_size=1024,max_total_bytes=64*1024**2,prior_download_budget_bytes=0,candidate_limit=5,search_limit=20,
 sort_by_cloud=True,min_valid_fraction=.8,candidate_valid_fraction=.65,cloud_cover=60,label_first=True,
 verify_product_metadata=True,preserve_source_crops=True,transient_asset_retries=0,
 collection_policy_version='deficit-center-1024-PLAN-ONLY')
config['candidate_metadata_policy']='DEFICIT_AOI_BBOX_CONTAINS_V1'
configsha=hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest()
assert configsha==approval['expected_config_sha256']
job={'key':f'center1024-gorontalo-2025-{pin[:12]}-{idsha[:8]}','province':'gorontalo','year':2025,'split':'train','nominal_patches':16,'spatial_window_id':identifier,'config_sha256':configsha}
assert job['key'] not in state['batches']
rp=E/'deficit279-request-root-20261018.json';write(rp,request)
assert mp.read_bytes()==mr and lp.read_bytes()==lr
command=[sys.executable,'-X','faulthandler',str(R/'scripts/collect_deficit_guarded.py'),'--request',rp.relative_to(R).as_posix(),'--expected-request-sha256',pin,'--execute']
record={'started_at':datetime.now(timezone.utc).isoformat(),'status':'STARTED_FRESH_PREFLIGHT_NOT_COLLECTION_SUCCESS','manifest_before_sha256':sha(mp),'ledger_before_sha256':sha(lp),'source_rows_before':len(json.loads(mr)['scenes']),'pending_before':pending,'request_sha256':pin,'selected_jobs':[job],'command':command,'source_pins':approval['source_pins'],'new_budget_added':False,'training_started':False,'maximum_new_physical_patches':16,'expected_config_derivation':{'pinned_base_config_sha256':request['config_ref']['sha256'],'changes':['gorontalo base AOI id/province/bbox','year2025/sixbands/1024 bounded guards','explicit candidate metadata policy marker'],'scope':'Config derivation only; fresh200 inventory under lock required'}}
started=time.monotonic()
with (E/'deficit279-live-root-20261018-stdout.log').open('xb') as out,(E/'deficit279-live-root-20261018-stderr.log').open('xb') as err:
    code=launch_and_wait(command,record,E/'deficit279-launch-root-20261018.json',out,err,{'cwd':R,'env':dict(os.environ,PYTHONIOENCODING='utf-8',PYTHONFAULTHANDLER='1'),'stdin':subprocess.DEVNULL,'creationflags':subprocess.CREATE_NO_WINDOW})
record.update(status='PROCESS_TERMINATED_REQUIRES_SETTLEMENT_AUDIT',exit_code=code,seconds=time.monotonic()-started,finished_at=datetime.now(timezone.utc).isoformat(),lock_present=lock.exists())
write(E/'deficit279-terminal-root-20261018.json',record)
print(json.dumps({'exit_code':code,'seconds':record['seconds'],'lock_present':record['lock_present']}),flush=True)
