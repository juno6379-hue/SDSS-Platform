"""Prepare a pinned request only; never scan support files or dispatch."""
from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parents[2];E=R/'evidence/integration'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
old=json.loads((E/'bare179-report-20261018.json').read_text('utf-8'))['request']
descriptor={'name':'TARGETED_LOCAL_SUPPORT_3G_V1','max_files':10000,
            'max_support_bytes':3*1024**3,'max_file_bytes':64*1024**2}
marker={'name':descriptor['name'],'sha256':hashlib.sha256(json.dumps(descriptor,sort_keys=True,separators=(',',':')).encode()).hexdigest()}
source=R/'data/priority164-guarded227-20261018/source.json'
active=R/'data/first-group-training-esri-v1/annual-window-report.json'
ledger=R/'data/first-group-training-budget/global-ledger.json'
assert sha(source)==sha(active)=='9c24eec337a17f95855d190918c9999c25aeb1925a7642b1ade26afa4e20d987'
assert sha(ledger)=='61161c35eabb593afb5f096c256791871d297b723f82ffc2ac2449b3bd8266e7'
assert sha(R/old['proposal_ref']['path'])==old['proposal_ref']['sha256']
request={**old,'schema_version':2,'local_support_profile':marker,
 'manifest_ref':{'path':source.relative_to(R).as_posix(),'sha256':sha(source)},
 'ledger_ref':{'path':ledger.relative_to(R).as_posix(),'sha256':sha(ledger)}}
with (E/'bare234-prepared-request-root-20261018.json').open('x',encoding='utf-8') as f:json.dump(request,f,ensure_ascii=False,indent=2)
print(json.dumps({'status':'PREPARED_ONLY_CODE232_REVIEW_REQUIRED','profile':marker,
 'proposal':request['proposal_ref'],'network_requests':0,'inventory_scans':0,'collection_started':False}))
