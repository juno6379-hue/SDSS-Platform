"""Root explicitly rebinds the source profile after audited zero-patch249; no QA/pointer promotion."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, os, urllib.request, time
R=Path(__file__).resolve().parents[2];D=R/'data';E=R/'evidence/integration'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):
    with p.open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2)
source=D/'first-group-training-esri-v1/annual-window-report.json'
ledger=D/'first-group-training-budget/global-ledger.json'
config=D/'first-group-training-priority/source-profile237-root-20261018.json'
names=[source,ledger,D/'first-group-training-priority/latest-candidate.json',D/'first-group-training-priority/latest-bare-review.json']
pins={str(p.relative_to(D)):sha(p) for p in names}
assert pins[str(source.relative_to(D))]=='6899f9019670e9eff3e40cd9e5441a91bbaf11fae236cbbc8c2eac27ffa31e15'
assert pins[str(ledger.relative_to(D))]=='c7ef4985a0c7f55a4a0a48c1db2b8ab4bef8d87be3a91e5175a948f56d613f4f'
assert not (ledger.parent/'global-ledger.execution.lock').exists()
terminal=json.loads((E/'deficit249-terminal-root-20261018.json').read_text('utf-8'))
assert terminal['exit_code']==0 and terminal['lock_present'] is False
old=config.read_bytes();assert hashlib.sha256(old).hexdigest()=='5ce66d6bf2a4e3f3f615ca22eeda45f4113cca00d7ad8d2e446e0bdc6562c08f'
with (E/'profile253-before249-config-root-20261018.json').open('xb') as f:f.write(old)
value=json.loads(old);assert value['source_manifest_sha256']==terminal['manifest_before_sha256']
value['source_manifest_sha256']=sha(source)
payload=(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
temporary=config.with_name(config.name+'.root253-new')
with temporary.open('xb') as f:f.write(payload)
assert config.read_bytes()==old and all(sha(D/n)==pin for n,pin in pins.items())
os.replace(temporary,config)
write(E/'profile253-selection-root-20261018.json',{'status':'EXPLICIT_SOURCE_PROFILE_REBOUND_AFTER_ZERO_PATCH249','at_utc':datetime.now(timezone.utc).isoformat(),'source_sha256':sha(source),'old_config_sha256':hashlib.sha256(old).hexdigest(),'new_config_sha256':sha(config),'raw_pointers_unchanged':all(sha(D/n)==p for n,p in pins.items()),'candidate_qa_repeated':False,'candidate_promoted':False,'native_executed':False})
request=urllib.request.Request('http://127.0.0.1:8002/api/data/collection-status',headers={'Origin':'http://127.0.0.1:5174'})
start=time.monotonic()
with urllib.request.urlopen(request,timeout=150) as response:
    raw=response.read(2*1024**2+1);code=response.status
assert len(raw)<=2*1024**2
with (E/'profile253-api-response-root-20261018.json').open('xb') as f:f.write(raw)
v=json.loads(raw);t=v.get('collection_targets',{});c=v.get('candidate_quality',{});b=t.get('budget_status',{});bare=t.get('bare_target_review',{})
checks={'http200':code==200,'raw1358':t.get('eligible_total')==1358,'gap21':t.get('cell_gap_total')==21,'candidate1342':c.get('eligible_total')==1342,'candidate_stale':c.get('source_matches_current_manifest') is False,'bare50_stale':bare.get('candidate_total')==50 and bare.get('source_matches_current_manifest') is False,'not_ready':c.get('ready_for_training') is False and c.get('blocker_count')==3,'budget_remaining':b.get('remaining_bytes')==1893950211,'oldpending':b.get('old_pending_bytes')==136314880,'operating_pins_preserved':all(sha(D/n)==p for n,p in pins.items()),'config_preserved':config.read_bytes()==payload}
result={'status':'REAL_API_ZERO_PATCH_STALE_CANDIDATE_VERIFIED' if all(checks.values()) else 'REAL_API_CHECK_INCOMPLETE','at_utc':datetime.now(timezone.utc).isoformat(),'seconds':round(time.monotonic()-start,3),'checks':checks,'recorded_at':v.get('recorded_at'),'budget_observed_at':b.get('observed_at'),'config_sha256':sha(config),'source_sha256':sha(source),'response_sha256':hashlib.sha256(raw).hexdigest(),'training_started':False,'browser_verified':False,'candidate_qa_repeated':False}
write(E/'profile253-api-checks-root-20261018.json',result);print(json.dumps(result),flush=True)
if not all(checks.values()):raise SystemExit(2)
