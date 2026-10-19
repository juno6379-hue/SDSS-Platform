"""Independent completed-batch observation, never executes or edits collector data."""
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json

root = Path(__file__).resolve().parents[2]
read = lambda path: json.loads((root/path).read_text(encoding='utf-8'))
digest = lambda raw: hashlib.sha256(raw).hexdigest()
launch = read('evidence/integration/priority-collection-round5-launch-20261018.json')
path = root/'data/first-group-training-esri-v1/annual-window-report.json'
raw = path.read_bytes()
rows = json.loads(raw)['scenes']
ledger_path = root/'data/first-group-training-budget/global-ledger.json'
ledger_bytes = ledger_path.read_bytes()
ledger = json.loads(ledger_bytes)
old = rows[:launch['manifest_before_rows']]
assert digest(json.dumps(old,sort_keys=True).encode()) == launch['old_rows_canonical_sha256']
assert all(ledger['batches'][key] == value for key,value in launch['pending_before'].items())
selected = {job['key']:ledger['batches'][job['key']] for job in launch['selected_jobs']}
assert all(value['status'] == 'settled' for value in selected.values())
new = rows[launch['manifest_before_rows']:]
eligible = [row for row in rows if row.get('quality_status') == 'quality_eligible']
new_eligible = [row for row in new if row.get('quality_status') == 'quality_eligible']
counts = Counter((row['province'],int(row['year'])) for row in eligible)
provinces = ('south_sulawesi','gorontalo','southeast_sulawesi','banten','west_java','east_java')
gaps = {province:sum(max(0,28-counts[province,year]) for year in range(2020,2026)) for province in provinces}
bare = {}
for split in ('train','val','test'):
    group = [row for row in eligible if row['split'] == split]
    hist = [row.get('sample_class_coverage',{}) for row in group]
    pixels = sum(item.get('8',0) for item in hist)
    total = sum(sum(item.values()) for item in hist)
    bare[split] = {'pixels':pixels,'ratio':pixels/total if total else None,
                   'contributing_patches':sum(item.get('8',0)>=256 for item in hist)}
assert path.read_bytes() == raw and ledger_path.read_bytes() == ledger_bytes
report = {'at_utc':datetime.now(timezone.utc).isoformat(),
    'classification':'VERIFIED_REAL_STORED_RECORDS_NOT_NATIVE_QA',
    'manifest_sha256':digest(raw),'physical_total':len(rows),'eligible_total':len(eligible),
    'ineligible_total':len(rows)-len(eligible),'goal_gap':max(0,1200-len(eligible)),
    'cell_gap_total':sum(gaps.values()),'cell_gap_by_province':gaps,
    'new_physical':len(new),'new_eligible':len(new_eligible),
    'new_bare_declared_pixels':sum(row.get('sample_class_coverage',{}).get('8',0) for row in new_eligible),
    'bare_by_split':bare,'selected_batches':selected,
    'old_rows_unchanged':True,'pending_rows_unchanged':True,
    'old_pending_reserved_bytes':sum(value['reserved_bytes'] for value in launch['pending_before'].values()),
    'charged_delta':ledger['new_charged_bytes']-launch['new_charged_before'],
    'remaining_budget':ledger['additional_maximum_bytes']-ledger['new_charged_bytes'],
    'rate_limit_active':ledger.get('rate_limit_active'),
    'execution_lock_present':(ledger_path.parent/'global-ledger.execution.lock').exists(),
    'two_reads_bytes_stable':True,'operating_writes':0,'collectors_started':0,
    'limit':'Sequential bounded observations, not atomic OS snapshot, native QA or training approval. Candidate1125 belongs to fixed1432-row source.'}
with (root/'evidence/integration/heartbeat-1055-round5-audit-20261018.json').open('x',encoding='utf-8') as stream:
    json.dump(report,stream,ensure_ascii=False,indent=2)
    stream.write('\n')
print(json.dumps({key:report[key] for key in ('physical_total','eligible_total','new_eligible','goal_gap','cell_gap_total','remaining_budget')},ensure_ascii=True))
