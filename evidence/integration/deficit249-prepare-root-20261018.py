"""Prepare and authorize one bounded249 request; never starts a collector."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
R=Path(__file__).resolve().parents[2];D=R/'data';E=R/'evidence/integration'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text('utf-8-sig'))
def ref(p):return {'path':p.relative_to(R).as_posix(),'sha256':sha(p)}
def write(p,v):
    with p.open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2)
work=D/'centers245-fresh-20261018';source=D/'first-group-training-esri-v1/annual-window-report.json';ledger=D/'first-group-training-budget/global-ledger.json'
assert not (ledger.parent/'global-ledger.execution.lock').exists()
assert sha(source)==sha(work/'source.json')=='4f8fcaff71868539aff16b3c351992696a6464b9cb229a5ff0f243778b7cd3e8'
assert sha(ledger)=='9c452bfb3773dddf08dc1091640ed33cb7885b30bdd6b1f7b7ebb58616646c86'
result=read(E/'centers245-result-20261018.json');assert result['status']=='LOCAL_PROPOSAL_COMPLETE_UNAPPROVED' and all(result['pins_stable_after'].values())
assert result['cli_invocations']==1 and result['prior_candidates_preserved']==44
assert sha(work/'proposal.json')==result['proposal_sha256']=='22cb58cc4b60b393d3f18ea2f31d30332b323f56113ec565bdc35710fbf84cd0'
assert sha(work/'prior-merged.json')=='380ac7849963558798fb5edd7e8f2dbff4ba55adc4ecd08f5dccfd8535dc9b4c'
proposal=read(work/'proposal.json');candidate=proposal['candidates'][0]
assert candidate['province']=='southeast_sulawesi' and candidate['years']==[2024]
assert read(E/'profile247-api-checks-root-20261018.json')['status']=='REAL_API_ZERO_PATCH_STALE_CANDIDATE_VERIFIED'
ui=read(E/'service247-post235-final-ui-20261018.json')
assert 'BLOCKED' not in ui.get('status','')
assert read(E/'deficit249-supervisor-final-failure-tests-root-20261018.json')['status']=='SUPERVISOR_FINAL_FAILURE_TESTS_PASSED'
assert sha(E/'deficit249-supervisor-root-20261018.py')=='3506f3f9baacb83c4d984582fdc2dd6ca906e50bd6a0ee5c5e5e5d14368b374d'
old=read(E/'deficit235-reviewed-code-pins-root-20261018.json')['source_pins']
assert all(sha(R/p)==pin for p,pin in old.items())
request={'schema_version':1,'kind':'GUARDED_DEFICIT_1024_REQUEST','proposal_ref':ref(work/'proposal.json'),'current_manifest_ref':ref(work/'source.json'),'ledger_ref':ref(ledger),'boundary_ref':ref(D/'first-group-boundaries/selected-six.geojson'),'config_ref':ref(R/'configs/first-group.collection.json'),'prior_plan_ref':ref(work/'prior-merged.json'),'selected':[{'spatial_window_id':candidate['spatial_window_id'],'year':2024}],'maximum_batches':1}
pin=hashlib.sha256(json.dumps(request,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode()).hexdigest()
write(E/'deficit249-prepared-request-root-20261018.json',request)
names=set(old)|{'evidence/integration/deficit249-supervisor-root-20261018.py'}
approval={'status':'ROOT_APPROVED_ONE_SE2024_BATCH_AFTER_AUDITED_ZERO235','at_utc':datetime.now(timezone.utc).isoformat(),'maximum_batches':1,'maximum_new_physical_patches':16,'request_sha256':pin,'source_sha256':sha(source),'ledger_sha256':sha(ledger),'source_pins':{p:sha(R/p) for p in sorted(names)},'prior235_audit_sha256':sha(E/'deficit235-native-root-20261018.json'),'config_template_ref':ref(E/'centers205-review-result-root-20261018.json'),'config_template_request_ref':ref(E/'centers205-review-request-root-20261018.json'),'supervisor_failure_tests_sha256':sha(E/'deficit249-supervisor-final-failure-tests-root-20261018.json'),'actual_api_ref':ref(E/'profile247-api-checks-root-20261018.json'),'actual_ui_ref':ref(E/'service247-post235-final-ui-20261018.json'),'existing_budget_maximum_bytes':4294967296,'oldpending_preserved_bytes':136314880,'new_budget_added':False,'training_approved':False,'fresh200_under_lock_required':True,'prior_template_scope':'Expected config only, never a fresh inventory proof','candidate_qa_not_repeated_for_zero_patch235':True}
write(E/'deficit249-reviewed-code-pins-root-20261018.json',approval)
print(json.dumps({'status':'REQUEST_APPROVED_NOT_STARTED','request_sha256':pin,'selected':request['selected'],'maximum_batches':1,'maximum_physical':16,'source_pins':len(names),'collector_started':False}),flush=True)
