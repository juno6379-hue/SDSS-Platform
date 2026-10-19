"""Read-only resume observation; no raster QA, reconciliation or reservation."""
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
import json,hashlib
R=Path(__file__).resolve().parents[2];D=R/'data';E=R/'evidence/integration'
def digest(raw):return hashlib.sha256(raw).hexdigest()
paths={'source':D/'first-group-training-esri-v1/annual-window-report.json',
       'ledger':D/'first-group-training-budget/global-ledger.json',
       'pointer':D/'first-group-training-priority/latest-candidate.json'}
raw={k:p.read_bytes() for k,p in paths.items()}
assert all(p.read_bytes()==raw[k] for k,p in paths.items())
assert not (D/'first-group-training-budget/global-ledger.execution.lock').exists()
source,ledger,pointer=(json.loads(raw[k]) for k in ('source','ledger','pointer'))
assert digest(raw['source'])=='9c24eec337a17f95855d190918c9999c25aeb1925a7642b1ade26afa4e20d987'
assert digest(raw['ledger'])=='61161c35eabb593afb5f096c256791871d297b723f82ffc2ac2449b3bd8266e7'
assert digest(raw['pointer'])=='920ceb52dca0aba32f11389fd2f9c5f2719ca40b47f44e650c3a38b57c3b3d40'
eligible=[x for x in source['scenes'] if x.get('quality_status')=='quality_eligible']
counts=Counter((x['province'],int(x['year'])) for x in eligible)
provinces=['south_sulawesi','gorontalo','southeast_sulawesi','east_java','banten','west_java']
gaps=[{'province':p,'year':y,'eligible':counts[p,y],'missing':28-counts[p,y]}
      for p in provinces for y in range(2020,2026) if counts[p,y]<28]
pending={k:v for k,v in ledger['batches'].items() if v['status']=='pending'}
assert len(pending)==2 and sum(v['reserved_bytes'] for v in pending.values())==136314880
assert ledger['additional_maximum_bytes']==4*1024**3 and not ledger['rate_limit_active']
assert len(eligible)==1358 and sum(x['missing'] for x in gaps)==21
assert sum(pointer['by_split'].values())==1342 and pointer['ready_for_training'] is False
record={'status':'VERIFIED_METADATA_ONLY_RESUME_OBSERVATION','at_utc':datetime.now(timezone.utc).isoformat(),
 'pins':{k:digest(v) for k,v in raw.items()},'source_bytes':len(raw['source']),
 'registered_rows':len(source['scenes']),'eligible_rows':len(eligible),'cell_shortfalls':gaps,
 'total_cell_shortfall':sum(x['missing'] for x in gaps),'published_candidate':1342,
 'candidate_blockers':pointer['blocker_count'],'candidate_source_current':pointer['source_manifest_sha256']==digest(raw['source']),
 'additional_budget':ledger['additional_maximum_bytes'],'charged_including_pending':ledger['new_charged_bytes'],
 'remaining':ledger['additional_maximum_bytes']-ledger['new_charged_bytes'],
 'pending_count':len(pending),'pending_reserved':sum(x['reserved_bytes'] for x in pending.values()),
 'lock_present':False,'native_runs':0,'physical_recount_performed':False,'last_native_verified_physical':1716,
 'source_or_ledger_writes':False,'training_started':False}
assert all(p.read_bytes()==raw[k] for k,p in paths.items())
with (E/'resume233-live-state-root-20261018.json').open('x',encoding='utf-8') as f:json.dump(record,f,ensure_ascii=False,indent=2)
print(json.dumps(record,ensure_ascii=True))
