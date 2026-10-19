"""Completed round8 metadata/accounting check only; no native QA or operating writes."""
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone
import hashlib,json
R=Path(__file__).resolve().parents[2]; E=R/'evidence/integration'; D=R/'data'
def sha(raw):return hashlib.sha256(raw).hexdigest()
launch=json.loads((E/'priority-collection-round8-launch-20261018.json').read_bytes())
mp=D/'first-group-training-esri-v1/annual-window-report.json';lp=D/'first-group-training-budget/global-ledger.json'
mr=mp.read_bytes();lr=lp.read_bytes();manifest=json.loads(mr);ledger=json.loads(lr)
rows=manifest['scenes'];old=rows[:launch['manifest_before_rows']]
assert sha(json.dumps(old,sort_keys=True).encode())==launch['old_rows_canonical_sha256']
assert all(ledger['batches'][k]==v for k,v in launch['pending_before'].items())
keys=[j['key'] for j in launch['selected_jobs']]
selected={k:ledger['batches'][k] for k in keys}
assert all(v['status']=='settled' for v in selected.values())
events=[json.loads(x) for x in (E/'priority-collection-round8-live-20261018-stdout.log').read_text(encoding='utf-8').splitlines() if x.strip()]
finished=[x for x in events if x.get('status')=='worker_finished' and x['key'] in keys]
assert len(finished)==2 and len([x for x in events if x.get('status')=='worker_started'])==2
assert sum(x['charged_bytes'] for x in finished)==sum(x['charged_bytes'] for x in selected.values())==ledger['new_charged_bytes']-launch['new_charged_before']
assert len(rows)-len(old)==sum(x['new_patches'] for x in finished)
eligible=[x for x in rows if x.get('quality_status')=='quality_eligible']
old_eligible=sum(x.get('quality_status')=='quality_eligible' for x in old)
counts=Counter((x['province'],int(x['year'])) for x in eligible)
gap=sum(max(0,28-n) for n in counts.values())
assert len(counts)==36 and mp.read_bytes()==mr and lp.read_bytes()==lr
report={'at_utc':datetime.now(timezone.utc).isoformat(),'status':'COMPLETED_METADATA_ACCOUNTING_VERIFIED_NATIVE_QA_SEPARATE',
 'physical_total':len(rows),'eligible_total':len(eligible),'eligible_by_split':dict(Counter(x['split'] for x in eligible)),
 'physical_increment':len(rows)-len(old),'eligible_increment':len(eligible)-old_eligible,'cell_deficit':gap,
 'old_rows_unchanged':True,'old_pending_exact_preserved':True,'old_pending_reserved_bytes':sum(x['reserved_bytes'] for x in launch['pending_before'].values()),
 'selected_settled':selected,'charged_increment':sum(x['charged_bytes'] for x in selected.values()),
 'remaining_after_settlement':ledger['additional_maximum_bytes']-ledger['new_charged_bytes'],
 'rate_limit_active':ledger['rate_limit_active'],'execution_lock_present':(D/'first-group-training-budget/global-ledger.execution.lock').exists(),
 'source_sha256':sha(mr),'ledger_sha256':sha(lr),'stable_second_read':True,
 'bare_increment_metadata_only':sum(x.get('sample_class_coverage',{}).get('8',0) for x in rows[len(old):] if x.get('quality_status')=='quality_eligible'),
 'native_qa_repeated':False,'collection_started':False,'operating_writes':0,'learning_ready':False}
with (E/'heartbeat-1145-round8-final-root-20261018.json').open('x',encoding='utf-8') as output:json.dump(report,output,ensure_ascii=False,indent=2)
print(json.dumps(report,ensure_ascii=True))
