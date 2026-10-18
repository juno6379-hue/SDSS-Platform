from pathlib import Path
import json,hashlib,time,sys
r=Path.cwd();sys.path.insert(0,str(r/'backend'))
from app.data.targeted_inventory import inspect_targeted_inventory
folder=r/'data/targeted-inventory167-20261018';folder.mkdir(exist_ok=False)
e=r/'evidence/integration'
manifest=r/'data/priority164-cohort-20261018/source.json';ledger=r/'data/first-group-training-budget/global-ledger.json';raw=ledger.read_bytes();(folder/'ledger.json').write_bytes(raw)
plan=json.loads((e/'targeted-bare-plan-local-20261018-request.json').read_text('utf-8'))
def ref(p):return {'path':p.relative_to(r).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
request={'manifest_ref':ref(manifest),'ledger_ref':ref(folder/'ledger.json'),'target':plan['targets'][0]['target_footprint_native']}
(e/'targeted-inventory-real-request-20261018.json').write_text(json.dumps(request,indent=2)+'\n',encoding='utf-8')
a=time.perf_counter();out=inspect_targeted_inventory(r,request);out['seconds']=time.perf_counter()-a;out['captured_ledger_sha256']=hashlib.sha256(raw).hexdigest();out['active_collector_may_change_inventory']=True
(e/'targeted-inventory-real-20261018.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:out[k] for k in ['status','issue','support_files_verified','seconds']}))
