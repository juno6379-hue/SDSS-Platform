"""Prepare one Root258 request with reviewed255 diagnostics; never dispatches."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
R=Path(__file__).resolve().parents[2];D=R/'data';E=R/'evidence/integration'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text('utf-8-sig'))
def ref(p):return {'path':p.relative_to(R).as_posix(),'sha256':sha(p)}
def write(p,v):
    with p.open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2)
work=D/'centers257-fresh-20261018';source=D/'first-group-training-esri-v1/annual-window-report.json';ledger=D/'first-group-training-budget/global-ledger.json'
assert not (ledger.parent/'global-ledger.execution.lock').exists()
assert sha(source)==sha(work/'source.json')=='6899f9019670e9eff3e40cd9e5441a91bbaf11fae236cbbc8c2eac27ffa31e15'
assert sha(ledger)=='c7ef4985a0c7f55a4a0a48c1db2b8ab4bef8d87be3a91e5175a948f56d613f4f'
result=read(E/'centers257-result-root-20261018.json')
assert result['status']=='LOCAL_PLAN_COMPLETE_UNAPPROVED' and all(result['pins_stable'].values()) and result['prior_count']==48
assert sha(work/'proposal.json')==result['proposal_sha256']
proposal=read(work/'proposal.json');candidate=proposal['candidates'][0]
assert candidate['province']=='southeast_sulawesi' and candidate['years']==[2024]
assert read(E/'profile253-api-checks-root-20261018.json')['status']=='REAL_API_ZERO_PATCH_STALE_CANDIDATE_VERIFIED'
assert read(E/'service253-post249-final-ui-20261018.json')['status']=='VERIFIED_REAL_POST249_BROWSER_STALE_WARNINGS'
review=read(E/'alignment255-root-review-20261018.json');assert review['status']=='ROOT_INDEPENDENT_STATIC_REVIEW_NO_REQUIRED_FIX_FOUND' and all(review['checks'].values())
freeze=read(E/'alignment255-20261018/freeze255.json')
assert all(sha(R/n)==v['sha256'] for n,v in freeze['products'].items())
assert sha(E/'deficit258-supervisor-root-20261018.py')=='d25e50aabce5613a605ccce4475b2a078a695830a38358039113ff0114934753'
old=read(E/'deficit249-reviewed-code-pins-root-20261018.json')['source_pins']
changed={'backend/app/data/deficit_candidate_guard.py','scripts/collect_deficit_guarded.py'}
assert all(sha(R/n)==v for n,v in old.items() if n not in changed)
request={'schema_version':1,'kind':'GUARDED_DEFICIT_1024_REQUEST','proposal_ref':ref(work/'proposal.json'),'current_manifest_ref':ref(work/'source.json'),'ledger_ref':ref(ledger),'boundary_ref':ref(D/'first-group-boundaries/selected-six.geojson'),'config_ref':ref(R/'configs/first-group.collection.json'),'prior_plan_ref':ref(work/'prior-merged.json'),'selected':[{'spatial_window_id':candidate['spatial_window_id'],'year':2024}],'maximum_batches':1}
pin=hashlib.sha256(json.dumps(request,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode()).hexdigest()
write(E/'deficit258-prepared-request-root-20261018.json',request)
names=set(old)|{'evidence/integration/deficit258-supervisor-root-20261018.py'}
approval={'status':'ROOT_APPROVED_ONE_SE2024_BATCH_AFTER_AUDITED_ZERO249','at_utc':datetime.now(timezone.utc).isoformat(),'maximum_batches':1,'maximum_new_physical_patches':16,'request_sha256':pin,'source_sha256':sha(source),'ledger_sha256':sha(ledger),'source_pins':{n:sha(R/n) for n in sorted(names)},'prior249_audit_sha256':sha(E/'deficit249-native-root-20261018-run2.json'),'config_template_ref':ref(E/'centers205-review-result-root-20261018.json'),'config_template_request_ref':ref(E/'centers205-review-request-root-20261018.json'),'diagnostic255_freeze_ref':ref(E/'alignment255-20261018/freeze255.json'),'diagnostic255_review_ref':ref(E/'alignment255-root-review-20261018.json'),'actual_api_ref':ref(E/'profile253-api-checks-root-20261018.json'),'actual_ui_ref':ref(E/'service253-post249-final-ui-20261018.json'),'existing_budget_maximum_bytes':4294967296,'oldpending_preserved_bytes':136314880,'new_budget_added':False,'training_approved':False,'fresh200_under_lock_required':True,'config_template_not_inventory_proof':True,'actual255_diagnostic_recording_not_yet_verified':True}
write(E/'deficit258-reviewed-code-pins-root-20261018.json',approval)
print(json.dumps({'status':'REQUEST_APPROVED_NOT_STARTED','request_sha256':pin,'selected':request['selected'],'maximum_physical':16,'source_pins':len(names),'collector_started':False}),flush=True)
