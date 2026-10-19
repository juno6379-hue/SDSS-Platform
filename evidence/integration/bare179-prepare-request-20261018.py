"""Explicitly authorized stable source/ledger copies, no operational writes."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sha=lambda raw:hashlib.sha256(raw).hexdigest()
folder=ROOT/'data/bare179-review-20261018'
folder.mkdir(exist_ok=False)
refs={};pins={}
for name,relative in [('manifest','data/first-group-training-esri-v1/annual-window-report.json'),('ledger','data/first-group-training-budget/global-ledger.json')]:
    source=ROOT/relative;raw=source.read_bytes();target=folder/('source.json' if name=='manifest' else 'ledger.json')
    with target.open('xb') as f:f.write(raw)
    assert source.read_bytes()==raw==target.read_bytes()
    refs[name+'_ref']={'path':target.relative_to(ROOT).as_posix(),'sha256':sha(raw)}
    pins[relative]=sha(raw)
for name,relative in [('proposal','evidence/integration/bare173-verified-20261018/proposal.json'),('boundary','data/first-group-boundaries/selected-six.geojson')]:
    raw=(ROOT/relative).read_bytes();refs[name+'_ref']={'path':relative,'sha256':sha(raw)};pins[relative]=sha(raw)
request={'schema_version':1,**refs}
path=ROOT/'evidence/integration/bare179-request-20261018.json'
raw=(json.dumps(request,ensure_ascii=False,indent=2)+'\n').encode()
with path.open('xb') as f:f.write(raw)
for relative,pin in pins.items():assert sha((ROOT/relative).read_bytes())==pin
receipt={'request_path':str(path),'request_sha256':sha(raw),'original_pins':pins,'source_or_ledger_operational_writes':0}
with (ROOT/'evidence/integration/bare179-request-pin-20261018.json').open('x',encoding='utf8') as f:json.dump(receipt,f,indent=2)
print(json.dumps(receipt,ensure_ascii=True))
