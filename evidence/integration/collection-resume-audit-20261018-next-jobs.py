"""Read-only exact coordinator queue reconstruction with actual validated configs."""
import json
import hashlib
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'.runtime'),str(ROOT/'backend')]
from scripts.collect_training_parallel import extra_jobs,v2_jobs,continuation_jobs,COG_BATCH,METADATA_BATCH

data=ROOT/'data'
out=data/'first-group-training-esri-v1'
ledger=json.loads((data/'first-group-training-budget/global-ledger.json').read_text(encoding='utf-8'))
base=json.loads((ROOT/'configs/first-group.collection.json').read_text(encoding='utf-8'))
aggregate=json.loads((out/'annual-window-report.json').read_text(encoding='utf-8'))
jobs=extra_jobs(base,[data/'first-group-training-esri-v2/lane-b-candidates.json'],4)+v2_jobs(base,4)
jobs,metadata=continuation_jobs(jobs,ledger,True)
provinces=[a['id'] for a in base['aois']]
queues={p:[] for p in provinces}
for j in jobs:
    prefix=f"{j['province']}/{j['spatial_window_id']}/"
    if not any(s.get('province')==j['province'] and int(s['year'])==j['year'] and s.get('spatial_location_id','').startswith(prefix) and s.get('quality_status')=='quality_eligible' for s in aggregate['scenes']):
        queues[j['province']].append(j)
for q in queues.values():
    q.sort(key=lambda j:(j.get('candidate_rank',int(j['spatial_window_id']) if j['spatial_window_id'].isdigit() else 0),j['year'],j['key']))
ordered=[queues[p][i] for i in range(max(map(len,queues.values()),default=0)) for p in provinces if i<len(queues[p])]
unreserved=[j for j in ordered if j['key'] not in ledger['batches']]
next_jobs=[]
for j in unreserved[:2]:
    directory=out/'sources'/j['key']
    next_jobs.append({'key':j['key'],'province':j['province'],'year':j['year'],'split':j['split'],
                     'config_sha256':hashlib.sha256(json.dumps(j['config'],sort_keys=True).encode()).hexdigest(),
                     'ledger_entry_exists':j['key'] in ledger['batches'],'source_directory_exists':directory.exists(),
                     'existing_source_files':[str(p.relative_to(directory)) for p in directory.rglob('*') if p.is_file()],
                     'maximum_reservation_bytes':COG_BATCH+METADATA_BATCH})
result={'scope':'READ_ONLY_EXACT_QUEUE_RECONSTRUCTION','pending_continuation':metadata,
        'next_jobs':next_jobs,'new_budget_remaining_before':ledger['additional_maximum_bytes']-ledger['new_charged_bytes'],
        'new_budget_remaining_after_two_full_reservations':ledger['additional_maximum_bytes']-ledger['new_charged_bytes']-2*(COG_BATCH+METADATA_BATCH),
        'physical_patch_count_before':len(aggregate['scenes']),'physical_patch_count_upper_after_two':len(aggregate['scenes'])+32,
        'physical_patch_limit':3000,'network_requests':0,'source_files_written':0}
with (ROOT/'evidence/integration/collection-resume-audit-20261018-next-jobs.json').open('x',encoding='utf-8') as f:
    json.dump(result,f,ensure_ascii=False,indent=2)
print(json.dumps(result,ensure_ascii=True))
