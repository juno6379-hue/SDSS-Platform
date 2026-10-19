"""One real status GET after runtime/config application; no retry or collection."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,time,urllib.request
R=Path(__file__).resolve().parents[2];D=R/'data';E=R/'evidence/integration'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
names=['first-group-training-esri-v1/annual-window-report.json','first-group-training-budget/global-ledger.json',
 'first-group-training-priority/latest-candidate.json','first-group-training-priority/latest-bare-review.json',
 'first-group-training-priority/source-profile237-root-20261018.json']
pins={n:sha(D/n) for n in names}
assert pins[names[0]]=='9c24eec337a17f95855d190918c9999c25aeb1925a7642b1ade26afa4e20d987'
request=urllib.request.Request('http://127.0.0.1:8002/api/data/collection-status',headers={'Origin':'http://127.0.0.1:5174'})
started=time.monotonic()
with urllib.request.urlopen(request,timeout=150) as response:
    raw=response.read(2*1024**2+1);code=response.status;cors=response.headers.get('Access-Control-Allow-Origin')
    assert len(raw)<=2*1024**2
seconds=time.monotonic()-started;value=json.loads(raw)
with (E/'profile243-api-status-root-20261018.json').open('xb') as f:f.write(raw)
target=value.get('collection_targets',{});candidate=value.get('candidate_quality',{})
budget=target.get('budget_status',{});bare=target.get('bare_target_review',{})
checks={'http200':code==200,'cors_preserved':cors=='http://127.0.0.1:5174',
 'inventory_available':target.get('available') is True,'raw_eligible1358':target.get('eligible_total')==1358,
 'gap21':target.get('cell_gap_total')==21,'candidate1342':candidate.get('eligible_total')==1342,
 'candidate3blocked':candidate.get('blocker_count')==3 and candidate.get('ready_for_training') is False,
 'candidate_current':candidate.get('source_matches_current_manifest') is True,
 'bare50_current':bare.get('candidate_total')==50 and bare.get('source_matches_current_manifest') is True,
 'budget_available':budget.get('available') is True,'remaining_preserved':budget.get('remaining_bytes')==1896944955,
 'oldpending_preserved':budget.get('old_pending_bytes')==136314880,
 'pins_unchanged':all(sha(D/n)==p for n,p in pins.items())}
out={'status':'REAL_LOCAL_API_PROFILE_STATUS_VERIFIED' if all(checks.values()) else 'REAL_LOCAL_API_PROFILE_STATUS_BLOCKED',
 'at_utc':datetime.now(timezone.utc).isoformat(),'http_status':code,'seconds':seconds,'checks':checks,
 'recorded_at':value.get('recorded_at'),'budget_observed_at':budget.get('observed_at'),
 'source_sha256':pins[names[0]],'config_sha256':pins[names[4]],'response_sha256':hashlib.sha256(raw).hexdigest(),
 'source_profile_explicitly_selected':True,'source_bytes':66826849,'real128m_maximum_proven':False,
 'native_qa_executed':False,'browser_render_verified':False,'collector_started':False,'training_started':False}
with (E/'profile243-api-status-checks-root-20261018.json').open('x',encoding='utf-8') as f:json.dump(out,f,ensure_ascii=False,indent=2)
print(json.dumps(out),flush=True)
if not all(checks.values()):raise SystemExit(2)
