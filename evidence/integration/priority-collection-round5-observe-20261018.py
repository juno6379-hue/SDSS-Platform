"""Observe an active/final priority collection without changing operating data."""
from pathlib import Path
import json,hashlib,datetime,sys
R=Path(__file__).resolve().parents[2];E=R/'evidence/integration';D=R/'data'
read=lambda p:json.loads(p.read_text('utf-8'))
launch=read(E/'priority-collection-round5-launch-20261018.json')
raw=(D/'first-group-training-esri-v1/annual-window-report.json').read_bytes();manifest=json.loads(raw)
ledger=read(D/'first-group-training-budget/global-ledger.json')
old=manifest['scenes'][:launch['manifest_before_rows']]
assert hashlib.sha256(json.dumps(old,sort_keys=True).encode()).hexdigest()==launch['old_rows_canonical_sha256']
for key,value in launch['pending_before'].items():assert ledger['batches'][key]==value
selected={j['key']:ledger['batches'].get(j['key']) for j in launch['selected_jobs']}
complete=all(v and v['status']=='settled' for v in selected.values())
eligible=[x for x in manifest['scenes'] if x.get('quality_status')=='quality_eligible']
new=manifest['scenes'][launch['manifest_before_rows']:]
counts={(p,y):sum(x['province']==p and int(x['year'])==y for x in eligible) for p in ('south_sulawesi','gorontalo','southeast_sulawesi','east_java','banten','west_java') for y in range(2020,2026)}
result={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'SETTLED' if complete else 'RUNNING_NOT_FINAL',
 'manifest_sha256':hashlib.sha256(raw).hexdigest(),'physical_total':len(manifest['scenes']),'eligible_total':len(eligible),
 'cell_gap_total':sum(max(0,28-n) for n in counts.values()),'new_physical':len(new),'new_eligible':sum(x.get('quality_status')=='quality_eligible' for x in new),
 'new_bare_declared_pixels':sum(x.get('sample_class_coverage',{}).get('8',0) for x in new if x.get('quality_status')=='quality_eligible'),
 'old_rows_unchanged':True,'old_pending_rows_unchanged':True,'old_pending_reserved_bytes':sum(v['reserved_bytes'] for v in launch['pending_before'].values()),
 'selected_ledger_rows':selected,'new_charged_total':ledger['new_charged_bytes'],
 'charged_delta_from_launch':ledger['new_charged_bytes']-launch['new_charged_before'],
 'remaining_budget':ledger['additional_maximum_bytes']-ledger['new_charged_bytes'],
 'rate_limit_active':ledger.get('rate_limit_active'),'execution_lock_present':(D/'first-group-training-budget/global-ledger.execution.lock').exists(),
 'scientific_accuracy_validated':False,'learning_ready':False,
 'observation_limit':'Sequential reads, not atomic OS snapshot. Stored quality counts, not a new native raster QA. Child stdout is forwarded; source history/state and central ledger are independent evidence.'}
target=E/('priority-collection-round5-final-20261018.json' if '--final' in sys.argv and complete else 'priority-collection-round5-observation-'+datetime.datetime.now().strftime('%Y%m%dT%H%M%S')+'.json')
if target.exists():raise RuntimeError('Evidence already exists')
target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='selected_ledger_rows'},ensure_ascii=True))
