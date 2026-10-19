"""Read-only final round 8 inventory/accounting observation; no HTTP or product writes."""
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).with_suffix('.json')
sha = lambda raw: hashlib.sha256(raw).hexdigest()
def read(rel):
    raw = (ROOT / rel).read_bytes()
    return raw, json.loads(raw.decode('utf-8-sig'))

native_raw, native = read('evidence/integration/priority178-round8-native-20261018.json')
assert native['status'] == 'COMPLETED_NATIVE_CHECKED'
aggregate_raw, aggregate = read('data/first-group-training-esri-v1/annual-window-report.json')
ledger_raw, ledger = read('data/first-group-training-budget/global-ledger.json')
_, launch = read('evidence/integration/priority-collection-round8-launch-20261018.json')
assert sha(aggregate_raw) == native['aggregate_sha256_at_read']
assert sha(ledger_raw) == native['ledger_sha256_at_read']
rows = aggregate['scenes']
eligible = [r for r in rows if r.get('quality_status') == 'quality_eligible']
assert sha(json.dumps(rows[:launch['manifest_before_rows']], sort_keys=True).encode()) == launch['old_rows_canonical_sha256']
assert all(ledger['batches'][k] == v for k, v in launch['pending_before'].items())
provinces = ['south_sulawesi','gorontalo','southeast_sulawesi','east_java','banten','west_java']
cells = {p: {str(y): sum(r['province'] == p and str(r['year']) == str(y) for r in eligible) for y in range(2020,2026)} for p in provinces}
bare = {}
for split in ('train','val','test'):
    selected = [r for r in eligible if r.get('split') == split]
    hist = [r.get('sample_class_coverage',{}) for r in selected]
    bare[split] = {'eligible_patches':len(selected),'bare_pixels':sum(h.get('8',0) for h in hist),
                   'bare_contributing_patches_at_least_256':sum(h.get('8',0)>=256 for h in hist),
                   'valid_labeled_pixels':sum(sum(h.values()) for h in hist)}
    bare[split]['bare_fraction'] = bare[split]['bare_pixels'] / bare[split]['valid_labeled_pixels']
charges = sum(ledger['batches'][j['key']]['charged_bytes'] for j in launch['selected_jobs'])
assert charges == ledger['new_charged_bytes'] - launch['new_charged_before'] == 45131651
result = {'schema_version':1,'recorded_at':datetime.now(timezone.utc).isoformat(),
 'status':'VERIFIED_REAL_FIXED_ROUND8_INCREMENT_AND_METADATA_INVENTORY',
 'native_audit':{'path':str(Path(__file__).with_name('priority178-round8-native-20261018.json').relative_to(ROOT)), 'sha256':sha(native_raw),'seconds':native['seconds'], 'native_patches':32,'native_eligible_patches':26,'eligible_bare_pixels':199,'files_sha_rechecked':104},
 'source_sha256':{'aggregate':sha(aggregate_raw),'ledger':sha(ledger_raw)},
 'physical_total':len(rows),'eligible_total':len(eligible),'other_total':len(rows)-len(eligible),
 'eligible_by_province_year':cells,'eligible_by_province':dict(Counter(r['province'] for r in eligible)),
 'deficit_by_province':{p:sum(max(0,28-n) for n in cs.values()) for p,cs in cells.items()},
 'bare_by_split_metadata':bare,'cell_floor':28,'cell_gap_total':sum(max(0,28-n) for cs in cells.values() for n in cs.values()),
 'accounting':{'round_charge_bytes':charges,'new_charged_bytes':ledger['new_charged_bytes'],'additional_maximum_bytes':ledger['additional_maximum_bytes'],'remaining_bytes':ledger['additional_maximum_bytes']-ledger['new_charged_bytes'],'old_pending_preserved':True,'old_pending_bytes':sum(v['reserved_bytes'] for v in launch['pending_before'].values())},
 'collector_execution_lock_present':(ROOT/'data/first-group-training-budget/global-ledger.execution.lock').exists(),
 'learning_ready':False,'scientific_accuracy_validated':False,'source_or_ledger_writes':0,'http_calls':0,
 'limitations':['Only 32 newly collected patches received native raster QA here; older pool class figures are metadata aggregation.','Fixed minimum 28 per cell is coverage floor, not exact balancing or independent accuracy approval.','ESRI class 8 is weak reference label; split bare fraction and contributing-patch gates remain unmet.','Existing cross-split raw scene remains excluded from the separate 1219 eligible frozen candidate.']}
with OUT.open('x',encoding='utf-8') as stream:
    json.dump(result,stream,ensure_ascii=False,indent=2)
print(json.dumps(result,ensure_ascii=True,indent=2))
