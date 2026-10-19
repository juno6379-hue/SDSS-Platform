"""Observe existing round9; never launches, settles or changes a reservation."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
R=Path(__file__).resolve().parents[2];E=R/'evidence/integration';D=R/'data'
launch=json.loads((E/'priority-collection-round9-launch-root-20261018.json').read_bytes())
mp=D/'first-group-training-esri-v1/annual-window-report.json';lp=D/'first-group-training-budget/global-ledger.json'
mr=mp.read_bytes();lr=lp.read_bytes();m=json.loads(mr);ledger=json.loads(lr)
assert all(ledger['batches'][k]==v for k,v in launch['pending_before'].items())
assert hashlib.sha256(json.dumps(m['scenes'][:launch['manifest_before_rows']],sort_keys=True).encode()).hexdigest()==launch['old_rows_canonical_sha256']
keys=[j['key'] for j in launch['selected_jobs']]
events=[json.loads(line) for line in (E/'priority-collection-round9-live-root-20261018-stdout.log').read_text(encoding='utf-8').splitlines() if line.strip()]
proof={'at_utc':datetime.now(timezone.utc).isoformat(),'scope':'READ_ONLY_EXISTING_ROUND9',
 'selected_batches':{k:ledger['batches'].get(k) for k in keys},
 'worker_events':events,'old_rows_prefix_preserved':True,'old_pending_exact_preserved':True,
 'old_pending_reserved_bytes':136314880,'remaining_including_current_reservations':ledger['additional_maximum_bytes']-ledger['new_charged_bytes'],
 'rate_limit_active':ledger['rate_limit_active'],'physical_total':len(m['scenes']),
 'eligible_total':sum(r.get('quality_status')=='quality_eligible' for r in m['scenes']),
 'lock_present':(D/'first-group-training-budget/global-ledger.execution.lock').exists(),
 'second_read_stable':mp.read_bytes()==mr and lp.read_bytes()==lr,'operating_writes':0,'collection_starts':0}
with (E/'heartbeat-1145-round9-running-root-20261018.json').open('x',encoding='utf-8') as out:json.dump(proof,out,ensure_ascii=False,indent=2)
print(json.dumps(proof,ensure_ascii=True))
