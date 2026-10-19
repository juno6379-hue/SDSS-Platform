"""One authorized local proposal scan with live metadata drift veto, no collection."""
from pathlib import Path
import hashlib,json,subprocess,sys,time
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[2]
PREFIX=ROOT/'evidence/integration/centers204-fresh'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def stamp(p):
    s=p.stat();return (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
def write(p,v):
    with p.open('x',encoding='utf8') as f:json.dump(v,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
paths={'source':ROOT/'data/first-group-training-esri-v1/annual-window-report.json','ledger':ROOT/'data/first-group-training-budget/global-ledger.json','boundary':ROOT/'data/first-group-boundaries/selected-six.geojson','config':ROOT/'configs/first-group.collection.json','prior':ROOT/'data/centers204-fresh-20261018/prior-merged.json'}
pins={};stamps={};raw={}
for k,p in paths.items():
    before=stamp(p);payload=p.read_bytes();digest=hashlib.sha256(payload).hexdigest()
    assert before==stamp(p) and sha(p)==digest,'Metadata changed during first pin; no restart'
    pins[k]=digest;stamps[k]=before;raw[k]=payload
assert pins['source']=='39bb0245e586342bd116f5b052428fcf857fb26eae0ee1413c9c5f5275c40ba9','Root-authorized source differs; no repin'
assert sha(ROOT/'scripts/propose_deficit_centers182.py')=='c8ab85d7e3f39cda8a0c5a8259bf212a5bf9bc699e7f7b17652a90cfdacd6cf9'
assert all(stamp(p)==stamps[k] and sha(p)==pins[k] for k,p in paths.items())
work=ROOT/'data/centers204-fresh-20261018';assert work.is_dir() and set(p.name for p in work.iterdir())=={'prior-merged.json'}
source=work/'source.json'
with source.open('xb') as f:f.write(raw['source'])
assert sha(source)==pins['source']
source_doc=json.loads(raw['source']);rows=source_doc['scenes']
preflight={'at':datetime.now(timezone.utc).isoformat(),'status':'AUTHORIZED_LOCAL_PROPOSAL_SNAPSHOT_PINNED','source_rows':len(rows),'source_bytes':len(raw['source']),'metadata':{k:{'path':str(p.relative_to(ROOT)),'sha256':pins[k],'stamp':stamps[k]} for k,p in paths.items()},'snapshot_path':str(source.relative_to(ROOT)),'snapshot_sha256':sha(source),'operating_collector_started':False,'ledger_written':False,'http_requests':0,'frozen_code_sha256':sha(ROOT/'scripts/propose_deficit_centers182.py')}
write(Path(str(PREFIX)+'-preflight-20261018.json'),preflight)
command=[sys.executable,'-X','utf8',str(ROOT/'scripts/propose_deficit_centers182.py'),'--source',str(source),'--source-sha256',pins['source'],'--boundary',str(paths['boundary']),'--boundary-sha256',pins['boundary'],'--config',str(paths['config']),'--config-sha256',pins['config'],'--prior-plan',str(paths['prior']),'--prior-plan-sha256',pins['prior'],'--output',str(work/'proposal.json'),'--target','southeast_sulawesi:2024','--target','southeast_sulawesi:2021','--target','gorontalo:2025','--target','gorontalo:2022']
start=time.monotonic();drift=[]
with Path(str(PREFIX)+'-cli-20261018.log').open('x',encoding='utf8') as log:
    proc=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,cwd=ROOT)
    print(json.dumps({'at':preflight['at'],'pid':proc.pid,'source_rows':len(rows),'source_sha256':pins['source']}),flush=True)
    while proc.poll() is None:
        drift=[k for k,p in paths.items() if stamp(p)!=stamps[k]]
        if drift:
            proc.terminate();proc.wait(timeout=15);break
        time.sleep(.5)
    code=proc.wait()
stable={k:stamp(p)==stamps[k] and sha(p)==pins[k] for k,p in paths.items()}
proposal=work/'proposal.json';doc=json.loads(proposal.read_text(encoding='utf8')) if code==0 and proposal.exists() else None
result={'at':datetime.now(timezone.utc).isoformat(),'status':'LOCAL_PROPOSAL_COMPLETE_UNAPPROVED' if code==0 and not drift and all(stable.values()) else 'LOCAL_PROPOSAL_REJECTED_OR_INCOMPLETE','seconds':round(time.monotonic()-start,3),'exit_code':code,'owned_pid':proc.pid,'metadata_drift_detected':drift,'metadata_pins_stable':stable,'source_sha256':pins['source'],'ledger_sha256':pins['ledger'],'snapshot_sha256':sha(source),'source_rows':len(rows),'proposal_sha256':sha(proposal) if proposal.exists() else None,'candidate_count':len(doc['candidates']) if doc else None,'candidates':doc['candidates'] if doc else None,'target_status':doc['target_status'] if doc else None,'header_files_verified':len(doc['source_header_inventory']) if doc else None,'rejections':doc['rejections'] if doc else None,'full_pending_support_inventory_verified':False,'execution_supported':False,'operating_collector_started':False,'ledger_written':False,'http_requests':0,'source_original_written':False,'training_executed':False}
write(Path(str(PREFIX)+'-result-20261018.json'),result)
assert result['status']=='LOCAL_PROPOSAL_COMPLETE_UNAPPROVED','No automatic repin/retry; preserve outputs and report'
print(json.dumps({'status':result['status'],'seconds':result['seconds'],'candidates':result['candidate_count'],'proposal_sha256':result['proposal_sha256']}),flush=True)
