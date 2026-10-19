"""Prepare fresh local geometry proposals; never dispatch or modify the ledger."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,subprocess,sys,time
R=Path(__file__).resolve().parents[2];D=R/'data';E=R/'evidence/integration'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text('utf-8-sig'))
def write(p,v):
    with p.open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
source=D/'first-group-training-esri-v1/annual-window-report.json'
ledger=D/'first-group-training-budget/global-ledger.json'
snapshot=D/'priority164-guarded227-20261018/source.json'
assert sha(source)==sha(snapshot)=='9c24eec337a17f95855d190918c9999c25aeb1925a7642b1ade26afa4e20d987'
assert source.stat().st_size<=64*1024**2
assert sha(ledger)=='61161c35eabb593afb5f096c256791871d297b723f82ffc2ac2449b3bd8266e7'
assert not (ledger.parent/'global-ledger.execution.lock').exists()
code=R/'scripts/propose_deficit_centers182.py'
assert sha(code)=='c8ab85d7e3f39cda8a0c5a8259bf212a5bf9bc699e7f7b17652a90cfdacd6cf9'
old=D/'centers222-fresh-20261018';prior=read(old/'prior-merged.json');proposal=read(old/'proposal.json')
assert len(prior['candidates'])==36 and len(proposal['candidates'])==4
merged={**prior,'candidates':prior['candidates']+proposal['candidates'],
 'provenance':[{'path':p.relative_to(R).as_posix(),'sha256':sha(p)} for p in [old/'prior-merged.json',old/'proposal.json']],
 'scope':'FORTY_PRIOR_PROPOSALS_PRESERVED_EXCLUDED_NOT_EXECUTION_APPROVAL'}
work=D/'centers235-fresh-20261018';work.mkdir(exist_ok=False)
prior_path=work/'prior-merged.json';write(prior_path,merged)
boundary=D/'first-group-boundaries/selected-six.geojson';config=R/'configs/first-group.collection.json'
paths={'source':source,'snapshot':snapshot,'ledger':ledger,'boundary':boundary,'config':config,'prior':prior_path,'code':code}
pins={k:sha(p) for k,p in paths.items()}
assert pins['boundary']=='de7722bfa88ddff3e12137d271c28717c23b3077a87b7dc36c66d1d8c522c909'
assert pins['config']=='8b0c1b2aad13a3344200998ec62a18853c5308adf4ec57b1af835333845fd7e3'
command=[sys.executable,'-X','utf8',str(code),'--source',str(snapshot),'--source-sha256',pins['source'],
 '--boundary',str(boundary),'--boundary-sha256',pins['boundary'],'--config',str(config),'--config-sha256',pins['config'],
 '--prior-plan',str(prior_path),'--prior-plan-sha256',pins['prior'],'--output',str(work/'proposal.json'),
 '--target','southeast_sulawesi:2024','--target','gorontalo:2025','--target','gorontalo:2022']
write(E/'centers235-preflight-root-20261018.json',{'at_utc':datetime.now(timezone.utc).isoformat(),'pins':pins,
 'prior_candidates_preserved':40,'network_approved':False,'collection_approved':False,'source_snapshot_reused':True})
start=time.monotonic()
with (E/'centers235-cli-root-20261018.log').open('x',encoding='utf-8') as log:
    child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,cwd=R)
    print(json.dumps({'status':'LOCAL_PROPOSAL_STARTED_NOT_COLLECTION','pid':child.pid}),flush=True)
    exit_code=child.wait()
stable={k:sha(p)==pins[k] for k,p in paths.items()}
output=work/'proposal.json';doc=read(output) if exit_code==0 and output.exists() else None
result={'status':'LOCAL_PROPOSAL_COMPLETE_UNAPPROVED' if exit_code==0 and all(stable.values()) else 'LOCAL_PROPOSAL_BLOCKED',
 'at_utc':datetime.now(timezone.utc).isoformat(),'seconds':round(time.monotonic()-start,3),'exit_code':exit_code,
 'pins_stable_after':stable,'prior_candidates_preserved':40,'proposal_sha256':sha(output) if output.exists() else None,
 'candidate_count':len(doc['candidates']) if doc else None,'target_status':doc['target_status'] if doc else None,
 'headers_verified':len(doc['source_header_inventory']) if doc else None,'network_requests':0,
 'full_pending_support_inventory_verified':False,'collection_started':False,'source_or_ledger_written':False}
write(E/'centers235-result-root-20261018.json',result)
print(json.dumps(result,ensure_ascii=True),flush=True)
if result['status']!='LOCAL_PROPOSAL_COMPLETE_UNAPPROVED':raise SystemExit(2)
