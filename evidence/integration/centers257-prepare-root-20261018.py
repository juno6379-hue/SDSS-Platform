"""Root finite local257 plan after audited249; one snapshot and one CLI, no network."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,importlib.util,json,subprocess,sys,time
R=Path(__file__).resolve().parents[2];D=R/'data';E=R/'evidence/integration'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text('utf-8-sig'))
def write(p,v):
    with p.open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2)
source=D/'first-group-training-esri-v1/annual-window-report.json';ledger=D/'first-group-training-budget/global-ledger.json'
assert not (ledger.parent/'global-ledger.execution.lock').exists()
assert sha(source)=='6899f9019670e9eff3e40cd9e5441a91bbaf11fae236cbbc8c2eac27ffa31e15'
assert sha(ledger)=='c7ef4985a0c7f55a4a0a48c1db2b8ab4bef8d87be3a91e5175a948f56d613f4f'
audit=read(E/'deficit249-native-root-20261018-run2.json');assert all(audit['checks'].values()) and audit['new_physical_patches']==0
assert read(E/'alignment255-root-review-20261018.json')['status']=='ROOT_INDEPENDENT_STATIC_REVIEW_NO_REQUIRED_FIX_FOUND'
helper=E/'centers245-prepare-20261018.py';assert sha(helper)=='15da0d95c6fdc898efcd17cc5b1eb64f2d757a85cdc8a9f12038da0c37a8a655'
spec=importlib.util.spec_from_file_location('root257_snapshot_helper',helper);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
old=D/'centers245-fresh-20261018';prior=read(old/'prior-merged.json');proposal=read(old/'proposal.json')
assert len(prior['candidates'])==44 and len(proposal['candidates'])==4
combined=prior['candidates']+proposal['candidates'];assert len({x['spatial_window_id'] for x in combined})==48
code=R/'scripts/propose_deficit_centers182.py';assert sha(code)=='65fc9419680edbdc4daeb16a321eb8ca82d07df07f961d696b6a6a24a9742697'
boundary=D/'first-group-boundaries/selected-six.geojson';config=R/'configs/first-group.collection.json'
assert sha(boundary)=='de7722bfa88ddff3e12137d271c28717c23b3077a87b7dc36c66d1d8c522c909'
assert sha(config)=='8b0c1b2aad13a3344200998ec62a18853c5308adf4ec57b1af835333845fd7e3'
paths=[source,ledger,code,boundary,config,old/'prior-merged.json',old/'proposal.json']
pins={p.relative_to(R).as_posix():sha(p) for p in paths}
work=D/'centers257-fresh-20261018';work.mkdir(exist_ok=False)
snapshot=work/'source.json';module.snapshot_once(source,snapshot,pins[source.relative_to(R).as_posix()])
merged={**prior,'candidates':combined,'provenance':[{'path':p.relative_to(R).as_posix(),'sha256':sha(p)} for p in [old/'prior-merged.json',old/'proposal.json']],'scope':'48_PRIOR_PROPOSALS_PRESERVED_EXCLUDED_NOT_EXECUTION_APPROVAL'}
priorpath=work/'prior-merged.json';write(priorpath,merged)
command=[sys.executable,'-X','utf8',str(code),'--source',str(snapshot),'--source-sha256',sha(source),'--boundary',str(boundary),'--boundary-sha256',sha(boundary),'--config',str(config),'--config-sha256',sha(config),'--prior-plan',str(priorpath),'--prior-plan-sha256',sha(priorpath),'--manifest-profile','bounded128m-3000-v1','--output',str(work/'proposal.json')]
for target in ['southeast_sulawesi:2024','gorontalo:2025','gorontalo:2022']:command+=['--target',target]
write(E/'centers257-preflight-root-20261018.json',{'at_utc':datetime.now(timezone.utc).isoformat(),'pins':pins,'prior_count':48,'snapshot_ref':{'path':snapshot.relative_to(R).as_posix(),'sha256':sha(snapshot)},'cli_invocations':1,'collector_started':False})
start=time.monotonic()
with (E/'centers257-cli-root-20261018.log').open('xb') as stream:
    p=subprocess.Popen(command,cwd=R,stdout=stream,stderr=subprocess.STDOUT);print(json.dumps({'status':'LOCAL_ONLY_PLAN_STARTED','pid':p.pid}),flush=True);exitcode=p.wait()
stable={name:sha(R/name)==pin for name,pin in pins.items()};output=work/'proposal.json';doc=read(output) if exitcode==0 and output.exists() else None
result={'status':'LOCAL_PLAN_COMPLETE_UNAPPROVED' if exitcode==0 and all(stable.values()) else 'LOCAL_PLAN_BLOCKED','at_utc':datetime.now(timezone.utc).isoformat(),'seconds':round(time.monotonic()-start,3),'exit_code':exitcode,'pins_stable':stable,'prior_count':48,'new_candidates':len(doc['candidates']) if doc else None,'proposal_sha256':sha(output) if output.exists() else None,'headers_verified':len(doc['source_header_inventory']) if doc else None,'target_status':doc.get('target_status') if doc else None,'network_requests':0,'collector_started':False,'source_or_ledger_written':False,'full_support_inventory_verified':False}
write(E/'centers257-result-root-20261018.json',result);print(json.dumps(result),flush=True)
if result['status']!='LOCAL_PLAN_COMPLETE_UNAPPROVED':raise SystemExit(2)
