"""Read-only round4 native increment and round1 byte preservation; no execution pins."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import time
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
import numpy as np
import rasterio
from rasterio.features import geometry_mask
from rasterio.warp import transform_geom
from collect_training_parallel import v2_jobs,continuation_jobs
from collect_training_priority import prioritize_jobs

ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/integration';D=ROOT/'data'
start=time.perf_counter()
def sha(raw):return hashlib.sha256(raw).hexdigest()
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def canonical(value):return sha(json.dumps(value,sort_keys=True).encode())

launch=read(E/'priority-collection-round4-launch-20261018.json')
first=read(E/'priority-collection-round4-final-20261018.json')
round2=read(E/'priority-collection-round2-launch-20261018.json')
aggregate_path=D/'first-group-training-esri-v1/annual-window-report.json'
ledger_path=D/'first-group-training-budget/global-ledger.json'
aggregate_raw=aggregate_path.read_bytes();aggregate= json.loads(aggregate_raw)
ledger_raw=ledger_path.read_bytes();ledger=json.loads(ledger_raw)
assert launch['manifest_before_rows']==1464
assert canonical(aggregate['scenes'][:1464])==launch['old_rows_canonical_sha256']
for key,value in launch['pending_before'].items():assert ledger['batches'][key]==value
assert sum(v['reserved_bytes'] for v in launch['pending_before'].values())==136314880
assert canonical(aggregate['scenes'][:round2['manifest_before_rows']])==round2['old_rows_canonical_sha256']
print(json.dumps({'stage':'old_rows_and_pending_verified','rows':len(aggregate['scenes'])}),flush=True)
initial_launch=read(E/'priority-collection-launch-20261018.json')
initial_audit=read(E/'priority-collection-independent-20261018.json')
assert canonical(aggregate['scenes'][:1400])==initial_launch['old_rows_canonical_sha256']
first_native_files=0
for observed in initial_audit['first_round_observations']:
    key=observed['key']
    prior=[r for r in aggregate['scenes'] if r.get('patch_id','').startswith(key+'-')]
    assert len(prior)==16
    for row in prior:
        for role in ('image','label','quality'):
            path=Path(row['quality_mask_path' if role=='quality' else role+'_path'])
            assert sha(path.read_bytes())==row['patch_sha256'][role]
            first_native_files+=1
    folder=D/'first-group-training-esri-v1/sources'/key
    for name,digest in observed['source_and_terminal_files'].items():assert sha((folder/name).read_bytes())==digest
boundary=read(D/'first-group-boundaries/selected-six.geojson')
geometries={f['properties']['province_id']:f['geometry'] for f in boundary['features']}
observations=[];checked_files={};pixels_checked=0
for selected in launch['selected_jobs']:
    key=selected['key'];row=ledger['batches'][key]
    assert row==first['selected_ledger_rows'][key] and row['status']=='settled'
    folder=D/'first-group-training-esri-v1/sources'/key
    configuration=read(folder/'config.json')
    assert canonical(configuration)==selected['config_sha256']==row['config_sha256']
    report=read(Path(row['report_path']));terminal=read(folder/'worker-result.json');state=read(folder/'window-state.json')
    assert terminal['charged_bytes']==row['charged_bytes']==state['http_body_bytes']+terminal['metadata_budget']['charged_bytes']
    patches=[p for p in aggregate['scenes'] if p.get('patch_id','').startswith(key+'-')]
    assert len(patches)==16
    histogram={};eligible=0;patch_records=[]
    for item in patches:
        for role in ('image','label','quality'):
            path=Path(item['quality_mask_path' if role=='quality' else role+'_path']);raw=path.read_bytes()
            assert sha(raw)==item['patch_sha256'][role]
            checked_files[str(path.relative_to(ROOT))]=sha(raw)
        with rasterio.open(item['image_path']) as image,rasterio.open(item['label_path']) as label,rasterio.open(item['quality_mask_path']) as quality:
            assert (image.width,image.height)==(256,256) and image.count==6
            assert (image.crs,image.transform,image.width,image.height)==(label.crs,label.transform,label.width,label.height)==(quality.crs,quality.transform,quality.width,quality.height)
            values=image.read();labels=label.read(1);mask=quality.read(1)
            valid=(mask==1)&(labels!=0)&np.all(np.isfinite(values)&(values!=0),axis=0)
            inside=geometry_mask([transform_geom('EPSG:4326',image.crs,geometries[item['province']])],(256,256),image.transform,invert=True)
            assert float(valid.mean())==item['valid_pixel_ratio']
            assert float(inside.mean())==item['province_inside_fraction']
            status='quality_eligible' if valid.mean()>=.8 and inside.mean()>=.95 else 'quality_insufficient'
            assert status==item['quality_status']
            classes,counts=np.unique(labels[valid],return_counts=True)
            actual={str(int(code)):int(count) for code,count in zip(classes,counts)}
            assert actual==item['sample_class_coverage']
            if status=='quality_eligible':
                eligible+=1
                for code,count in actual.items():histogram[code]=histogram.get(code,0)+count
            patch_records.append({'patch_id':item['patch_id'],'quality_status':status,'valid_pixels':int(valid.sum()),'bare_pixels':actual.get('8',0)})
            pixels_checked+=256*256
    source_records=[]
    for source in report['scenes']:
        crops=source.get('source_crops',{})
        if source.get('image_path'):
            with rasterio.open(source['image_path']) as image,rasterio.open(source['quality_mask_path']) as mask:
                assert image.count==6 and image.width==image.height==1024
                assert mask.count==1 and mask.dtypes==('uint8',) and mask.nodata is None
                assert mask.descriptions==('binary_validity',)
                assert set(image.descriptions)=={'B02','B03','B04','B08','B11','B12'}
        for name,crop in crops.items():
            path=Path(crop['path']);raw=path.read_bytes();assert sha(raw)==crop['sha256']
            checked_files[str(path.relative_to(ROOT))]=sha(raw)
        source_records.append({'scene_id':source.get('scene_id'),'crop_files':len(crops),'image_present':bool(source.get('image_path')),
            'candidate_selection_entries':len(source.get('candidate_selection',[]))})
    history=folder/'collection-history.jsonl'
    observations.append({'key':key,'settled_charged_bytes':row['charged_bytes'],'patches':len(patches),'eligible_patches':eligible,
        'eligible_bare_pixels':histogram.get('8',0),'patch_observations':patch_records,'source_observations':source_records,
        'history_exists':history.is_file(),'history_lines':len(history.read_text(encoding='utf-8').splitlines()) if history.is_file() else 0,
        'source_and_terminal_files':{p.name:sha(p.read_bytes()) for p in (folder/'config.json',folder/'worker-result.json',folder/'window-state.json',Path(row['report_path']))}})
assert sum(r['eligible_patches'] for r in observations)==32
assert sum(r['eligible_bare_pixels'] for r in observations)==391
assert all(sha((ROOT/path).read_bytes())==digest for path,digest in checked_files.items())

base=read(ROOT/'configs/first-group.collection.json')
jobs=v2_jobs(base,4)
jobs,continuation=continuation_jobs(jobs,ledger,True)
remaining=[]
while jobs:
    selected=prioritize_jobs(jobs,aggregate['scenes'],ledger,limit=2)
    if not selected:break
    remaining.extend(selected);keys={j['key'] for j in selected};jobs=[j for j in jobs if j['key'] not in keys]
eligible=[s for s in aggregate['scenes'] if s.get('quality_status')=='quality_eligible']
pool=[{'key':j['key'],'province':j['province'],'year':j['year'],
    'eligible_patches':sum(s['province']==j['province'] and int(s['year'])==j['year'] for s in eligible)} for j in remaining]
for entry in pool:entry['deficit']=max(0,28-entry['eligible_patches'])
second_rows={j['key']:ledger['batches'].get(j['key']) for j in round2['selected_jobs']}
second_settled=all(v and v['status']=='settled' for v in second_rows.values())
proof={'schema_version':1,'recorded_at':datetime.now().astimezone().isoformat(),'seconds':time.perf_counter()-start,
    'status':'READONLY_INDEPENDENT_ROUND4_AND_CURRENT_POOL_AUDIT','old1464_canonical_sha256_verified':launch['old_rows_canonical_sha256'],
    'old1400_canonical_sha256_verified':initial_launch['old_rows_canonical_sha256'],
    'round1_32_patch_bytes_preserved':True,'round1_native_files_rehashed':first_native_files,'round1_source_terminal_files_preserved':True,
    'old_pending_exact_rows_preserved':True,'old_pending_reserved_bytes':136314880,'first_two_settled_verified':True,
    'round4_observations':observations,'round4_native_patches_checked':32,'round4_pixels_checked':pixels_checked,
    'round4_eligible_patches':sum(r['eligible_patches'] for r in observations),'round4_eligible_bare_pixels':sum(r['eligible_bare_pixels'] for r in observations),'file_sha_checks_repeated_unchanged':len(checked_files),
    'round2_status':'ALL_SELECTED_SETTLED' if second_settled else 'PENDING_OR_RUNNING_NOT_FINAL',
    'round2_selected_ledger_observation':second_rows,
    'read_snapshot_physical_rows':len(aggregate['scenes']),'read_snapshot_eligible_rows':len(eligible),
    'centers4_remaining_deficit_jobs_count':len(pool),'centers4_remaining_job_observations':pool,
    'nominal_upper_bound_patches_not_eligible_prediction':16*len(pool),
    'metadata_pins_at_read':{'aggregate_sha256':sha(aggregate_raw),'ledger_sha256':sha(ledger_raw)},
    'metadata_changed_by_other_collector_during_audit':{'aggregate':sha(aggregate_path.read_bytes())!=sha(aggregate_raw),'ledger':sha(ledger_path.read_bytes())!=sha(ledger_raw)},
    'executed_collection':False,'published_execution_plan_pin':False,'reservations_created':0,'source_or_ledger_writes':0,
    'limitations':['Metadata reads are sequential, not an atomic snapshot. Round2 may change after the captured observation.',
        'Round4 32 native patch arrays and recorded source crops are checked; first-round 32 patches are rehashed only, old1400 are metadata-only checks.',
        'Remaining centers4 jobs are an unreserved candidate-pool upper bound, not clear-scene availability, independent geometry or eligible yield.',
        'No centers16 expansion or old laneB geometry compatibility is recommended or executed.',
        'Esri weak labels and binary support-mask counts are not independent scientific truth or model/QA approval.']}
target=E/'priority-collection-independent-round4-20261018.json'
with target.open('x',encoding='utf-8') as stream:json.dump(proof,stream,ensure_ascii=False,indent=2);stream.write('\n')
print(json.dumps({'first32_native_and_metadata_match':True,'old1400_and_pending_preserved':True,'round2_status':proof['round2_status'],
    'remaining_deficit_jobs':len(pool),'nominal_patch_upper_bound':16*len(pool),'seconds':proof['seconds']},ensure_ascii=True),flush=True)
