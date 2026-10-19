"""278 prepared local geometry plan. No execution without a separate exact Root GO."""
import argparse,hashlib,json,os,stat,subprocess,sys,time
from datetime import datetime,timezone
from pathlib import Path
R=Path(__file__).resolve().parents[2];D=R/'data';E=R/'evidence/integration'
PREPARED=E/'centers278-prepared-20261018.json'
PREPARED_SHA='e33676f1589ffac3318614eb44ca1acedb581799f34249f276904a43ef79d492'
PROFILE='bounded128m-3000-v1'
SOURCE_MAX=128*1024**2

def digest(raw):return hashlib.sha256(raw).hexdigest()
def stamp(value):
    if not stat.S_ISREG(value.st_mode):raise ValueError('REGULAR_FILE_REQUIRED')
    return (value.st_dev,value.st_ino,value.st_size,value.st_mtime_ns,value.st_ctime_ns)
def local(value):
    path=Path(value)
    if not path.is_absolute():path=R/path
    if not path.is_relative_to(R) or path.resolve()!=path:raise ValueError('LOCAL_EXACT_PATH_REQUIRED')
    for part in (path,*path.parents):
        if part.is_symlink() or getattr(part.lstat(),'st_file_attributes',0)&0x400:raise ValueError('LINKED_INPUT')
    return path
def read_pin(path,maximum,keep=False):
    path=local(path);before=stamp(path.stat())
    if before[2]>maximum:raise ValueError('INPUT_CAP_EXCEEDED')
    h=hashlib.sha256();parts=[];count=0
    with path.open('rb',buffering=0) as stream:
        if stamp(os.fstat(stream.fileno()))!=before:raise ValueError('OPENED_INPUT_CHANGED')
        while count<before[2]:
            raw=stream.read(min(65536,before[2]-count))
            if not raw:raise ValueError('INPUT_SHORT_READ')
            count+=len(raw);h.update(raw)
            if keep:parts.append(raw)
        if stamp(os.fstat(stream.fileno()))!=before:raise ValueError('INPUT_CHANGED')
    if stamp(path.stat())!=before or path.resolve()!=path:raise ValueError('INPUT_CHANGED')
    return h.hexdigest(),before,b''.join(parts) if keep else None
def read_json(path,maximum):
    pin,identity,raw=read_pin(path,maximum,True)
    def pairs(items):
        out={}
        for key,value in items:
            if key in out:raise ValueError('DUPLICATE_JSON_KEY')
            out[key]=value
        return out
    value=json.loads(raw.decode('utf-8-sig'),object_pairs_hook=pairs,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('NONFINITE_JSON')))
    if type(value) is not dict:raise ValueError('JSON_OBJECT_REQUIRED')
    return value,pin,identity
def write_new(path,value):
    payload=(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf-8')
    with path.open('xb') as stream:
        if stream.write(payload)!=len(payload):raise OSError('SHORT_OUTPUT_WRITE')
    return digest(payload)
def array_pin(value):return digest(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode())
def code_check(plan):
    for name,expected in plan['code_pins'].items():
        if read_pin(R/name,256*1024)[0]!=expected:raise ValueError('CODE_PIN_CHANGED')
def snapshot_once(source,target,expected):
    actual,before,_=read_pin(source,SOURCE_MAX)
    if actual!=expected:raise ValueError('SOURCE_PIN_MISMATCH')
    h=hashlib.sha256();count=0
    with source.open('rb',buffering=0) as src,target.open('xb',buffering=0) as dst:
        if stamp(os.fstat(src.fileno()))!=before:raise ValueError('SOURCE_CHANGED_BEFORE_COPY')
        while count<before[2]:
            raw=src.read(min(65536,before[2]-count))
            if not raw:raise ValueError('SOURCE_SHORT_COPY')
            if dst.write(raw)!=len(raw):raise OSError('SOURCE_PARTIAL_COPY')
            count+=len(raw);h.update(raw)
        if stamp(os.fstat(src.fileno()))!=before:raise ValueError('SOURCE_CHANGED_DURING_COPY')
    if h.hexdigest()!=expected or stamp(source.stat())!=before or read_pin(target,SOURCE_MAX)[0]!=expected:raise ValueError('SOURCE_SNAPSHOT_MISMATCH')
    return count

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__,allow_abbrev=False)
    parser.add_argument('--run-local-plan',action='store_true');parser.add_argument('--approval',type=Path)
    args=parser.parse_args(argv)
    if not args.run_local_plan:
        print(json.dumps({'status':'PLANNED_AWAITING_ROOT_GO','local_cli_invocations':0,'collector_started':False,'network_requests':0}));return 0
    if args.approval is None:parser.error('--approval is required for the explicitly authorized local plan')
    plan,plan_pin,_=read_json(PREPARED,65536)
    if plan_pin!=PREPARED_SHA:raise ValueError('PREPARED_PLAN_CHANGED')
    approval_path=local(args.approval)
    if not approval_path.is_relative_to(E):raise ValueError('ROOT_GO_EVIDENCE_PATH_REQUIRED')
    go,go_pin,_=read_json(approval_path,65536)
    expected_keys={'schema_version','kind','local_plan_approved','maximum_cli_invocations','source_sha256','ledger_sha256','main_validation_ref','runner_sha256','main_validation_passed'}
    if set(go)!=expected_keys or type(go['schema_version']) is not int or go['schema_version']!=1 or go['kind']!='ROOT_AUTHORIZED_LOCAL_CENTERS278_PLAN' or go['local_plan_approved'] is not True or type(go['maximum_cli_invocations']) is not int or go['maximum_cli_invocations']!=1:raise ValueError('ROOT_GO_CONTRACT_INVALID')
    if go['main_validation_passed'] is not True:raise ValueError('ROOT_MAIN_VALIDATION_PASS_REQUIRED')
    if read_pin(Path(__file__).resolve(),65536)[0]!=go['runner_sha256']:raise ValueError('RUNNER_PIN_MISMATCH')
    if go['source_sha256']!=plan['source_sha256_reported_by_root_not_read_at_prepare'] or go['ledger_sha256']!=plan['ledger_sha256_reported_by_root_not_read_at_prepare']:raise ValueError('ROOT_GO_SOURCE_OR_LEDGER_PIN_CHANGED')
    audit=go['main_validation_ref']
    if type(audit) is not dict or set(audit)!={'path','sha256'}:raise ValueError('ROOT_AUDIT_REF_INVALID')
    audit_path=local(audit['path'])
    if not audit_path.is_relative_to(E) or read_pin(audit_path,2*1024**2)[0]!=audit['sha256']:raise ValueError('ROOT_AUDIT_PIN_MISMATCH')
    code_check(plan)
    source=local(plan['source_path']);ledger=local(plan['ledger_path'])
    if (ledger.parent/'global-ledger.execution.lock').exists():raise ValueError('EXECUTION_LOCK_PRESENT')
    original={}
    for key,path,limit,expected in [('source',source,SOURCE_MAX,go['source_sha256']),('ledger',ledger,8*1024**2,go['ledger_sha256'])]:
        actual,identity,_=read_pin(path,limit)
        if actual!=expected:raise ValueError('CURRENT_'+key.upper()+'_PIN_MISMATCH')
        original[key]=(path,limit,actual,identity)
    documents={}
    for key in ('prior','proposal'):
        ref=plan['inputs'][key];doc,pin,_=read_json(local(ref['path']),2*1024**2)
        if pin!=ref['sha256'] or len(doc.get('candidates',[]))!=ref['candidate_count'] or array_pin(doc['candidates'])!=ref['candidate_array_sha256']:raise ValueError('PRIOR_INPUT_CHANGED')
        documents[key]=doc
    combined=documents['prior']['candidates']+documents['proposal']['candidates']
    if len(combined)!=56 or len({row['spatial_window_id'] for row in combined})!=56 or array_pin(combined)!=plan['merged_candidate_array_sha256']:raise ValueError('PRIOR56_IDENTITY_CHANGED')
    for role in ('boundary','config'):
        ref=plan[role+'_ref']
        if read_pin(local(ref['path']),2*1024**2)[0]!=ref['sha256']:raise ValueError('BOUNDARY_OR_CONFIG_PIN_CHANGED')
    work=D/'centers278-fresh-20261018'
    outputs=[work,E/'centers278-local-plan-claim-20261018.json',E/'centers278-preflight-20261018.json',E/'centers278-cli-20261018.log',E/'centers278-result-20261018.json']
    if any(path.exists() or path.is_symlink() for path in outputs):raise ValueError('NEW_PATHS_REQUIRED_NO_AUTOMATIC_RETRY')
    write_new(outputs[1],{'kind':'SINGLE_LOCAL_PLAN_CLAIM','at_utc':datetime.now(timezone.utc).isoformat(),'approval_sha256':go_pin,'maximum_cli_invocations':1,'collector_started':False})
    start=time.monotonic();child=None;exit_code=None
    try:
        work.mkdir(exist_ok=False)
        snapshot=work/'source.json';snapshot_bytes=snapshot_once(source,snapshot,go['source_sha256'])
        merged={**documents['prior'],'candidates':combined,'provenance':[plan['inputs'][key]|{'candidate_count':plan['inputs'][key]['candidate_count']} for key in ('prior','proposal')],'scope':'FIFTY_SIX_PRIOR_PROPOSALS_PRESERVED_EXCLUDED_NOT_EXECUTION_APPROVAL'}
        prior_path=work/'prior-merged.json';prior_pin=write_new(prior_path,merged)
        if array_pin(merged['candidates'][:52])!=plan['inputs']['prior']['candidate_array_sha256'] or array_pin(merged['candidates'][52:])!=plan['inputs']['proposal']['candidate_array_sha256']:raise ValueError('PRIOR_ARRAY_ORDER_CHANGED')
        code_check(plan)
        for key,(path,limit,expected,identity) in original.items():
            current,current_identity,_=read_pin(path,limit)
            if current!=expected or current_identity!=identity:raise ValueError('PRELAUNCH_INPUT_CHANGED')
        output=work/'proposal.json'
        command=[sys.executable,'-X','utf8',str(R/'scripts/propose_deficit_centers182.py'),'--source',str(snapshot),'--source-sha256',go['source_sha256'],'--boundary',str(local(plan['boundary_ref']['path'])),'--boundary-sha256',plan['boundary_ref']['sha256'],'--config',str(local(plan['config_ref']['path'])),'--config-sha256',plan['config_ref']['sha256'],'--prior-plan',str(prior_path),'--prior-plan-sha256',prior_pin,'--output',str(output),'--manifest-profile',PROFILE]
        for target in plan['targets']:command+=['--target',target]
        write_new(outputs[2],{'at_utc':datetime.now(timezone.utc).isoformat(),'approval_sha256':go_pin,'main_validation_ref':audit,'source_sha256':go['source_sha256'],'ledger_sha256':go['ledger_sha256'],'snapshot_ref':{'path':snapshot.relative_to(R).as_posix(),'sha256':go['source_sha256'],'bytes':snapshot_bytes},'prior_ref':{'path':prior_path.relative_to(R).as_posix(),'sha256':prior_pin},'prior_candidates_preserved':56,'manifest_profile':plan['manifest_profile'],'maximum_cli_invocations':1,'collector_started':False,'network_requests':0})
        with outputs[3].open('x',encoding='utf-8') as log:
            child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,cwd=R)
            try:
                print(json.dumps({'status':'LOCAL_PROPOSAL_STARTED_NOT_COLLECTION','pid':child.pid,'maximum_cli_invocations':1}),flush=True)
            finally:
                exit_code=child.wait()
        stable={key:(read_pin(path,limit)[:2]==(expected,identity)) for key,(path,limit,expected,identity) in original.items()}
        code_check(plan)
        if read_pin(PREPARED,65536)[0]!=plan_pin or read_pin(approval_path,65536)[0]!=go_pin or read_pin(audit_path,2*1024**2)[0]!=audit['sha256']:raise ValueError('APPROVAL_OR_AUDIT_CHANGED')
        for key in ('prior','proposal'):
            if read_pin(local(plan['inputs'][key]['path']),2*1024**2)[0]!=plan['inputs'][key]['sha256']:raise ValueError('OLD_PRIOR_INPUT_CHANGED')
        doc,proposal_pin,_=read_json(output,2*1024**2) if exit_code==0 and output.exists() else (None,None,None)
        success=exit_code==0 and all(stable.values()) and doc is not None and len(doc.get('candidates',[]))<=4 and doc.get('manifest_profile')==plan['manifest_profile'] and doc.get('executed_network') is False and doc.get('collector_consumption_approved') is False
        result={'status':'LOCAL_PROPOSAL_COMPLETE_UNAPPROVED' if success else 'LOCAL_PROPOSAL_BLOCKED','at_utc':datetime.now(timezone.utc).isoformat(),'seconds':round(time.monotonic()-start,3),'exit_code':exit_code,'cli_invocations':1,'pins_stable_after':stable,'prior_candidates_preserved':56,'source_snapshot_ref':{'path':snapshot.relative_to(R).as_posix(),'sha256':go['source_sha256']},'proposal_sha256':proposal_pin,'candidate_count':len(doc['candidates']) if doc else None,'target_status':doc.get('target_status') if doc else None,'headers_verified':len(doc['source_header_inventory']) if doc else None,'network_requests':0,'full_pending_support_inventory_verified':False,'collection_started':False,'source_or_ledger_written':False,'training_started':False}
        write_new(outputs[4],result);print(json.dumps(result,ensure_ascii=True),flush=True)
        return 0 if success else 2
    except Exception as exc:
        if not outputs[4].exists():write_new(outputs[4],{'status':'LOCAL_PROPOSAL_BLOCKED','seconds':round(time.monotonic()-start,3),'exit_code':exit_code,'error_code':type(exc).__name__,'partial_outputs_preserved':True,'automatic_retry_allowed':False,'cli_invocations':int(child is not None),'network_requests':0,'collector_started':False,'source_or_ledger_written':False})
        raise
if __name__=='__main__':raise SystemExit(main())
