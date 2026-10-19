"""Prepare, but never execute, the first fresh SE2024 bounded request."""
from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parents[2];D=R/'data';E=R/'evidence/integration'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return {'path':p.relative_to(R).as_posix(),'sha256':sha(p)}
work=D/'centers235-fresh-20261018';proposal=work/'proposal.json'
assert sha(proposal)=='87e6f5f157d940e00c624f46821d30329135ef9182a0acb1db248bfb59a712da'
p=json.loads(proposal.read_text('utf-8'));candidate=p['candidates'][0]
assert candidate['province']=='southeast_sulawesi' and candidate['years']==[2024]
source=D/'priority164-guarded227-20261018/source.json';ledger=D/'first-group-training-budget/global-ledger.json'
assert sha(source)==sha(D/'first-group-training-esri-v1/annual-window-report.json')=='9c24eec337a17f95855d190918c9999c25aeb1925a7642b1ade26afa4e20d987'
assert sha(ledger)=='61161c35eabb593afb5f096c256791871d297b723f82ffc2ac2449b3bd8266e7'
request={'schema_version':1,'kind':'GUARDED_DEFICIT_1024_REQUEST','proposal_ref':ref(proposal),
 'current_manifest_ref':ref(source),'ledger_ref':ref(ledger),
 'boundary_ref':ref(D/'first-group-boundaries/selected-six.geojson'),
 'config_ref':ref(R/'configs/first-group.collection.json'),'prior_plan_ref':ref(work/'prior-merged.json'),
 'selected':[{'spatial_window_id':candidate['spatial_window_id'],'year':2024}],'maximum_batches':1}
with (E/'deficit235-prepared-request-root-20261018.json').open('x',encoding='utf-8') as f:json.dump(request,f,ensure_ascii=False,indent=2)
canonical=hashlib.sha256(json.dumps(request,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode()).hexdigest()
print(json.dumps({'status':'PREPARED_ONLY_EXECUTION_BLOCKED_PENDING230_REVIEW','request_sha256':canonical,
 'selected':request['selected'],'maximum_physical_patches':16,'collector_started':False,'network_requests':0}))
