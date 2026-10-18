"""실제 target170 완료 파일만 독립 읽기 감사. HTTP/collector/Store/원장 쓰기0."""
from pathlib import Path
import sys,json,time,hashlib
from datetime import datetime,timezone
R=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(R/".runtime"),str(R),str(R/"backend")]
import numpy as np
import rasterio
from rasterio.io import MemoryFile
from rasterio.warp import transform_bounds
from scripts.audit_priority_increment165 import snapshot,sha,canonical,effective_config,native_patch,local
from app.data.targeted_inventory import inspect_targeted_inventory
E=R/'evidence/integration';D=R/'data';started=time.perf_counter()
key='target256-bare-banten-2020-local-rank0-2020-4e7f2a1411cc'
checked={}
def read(path,limit=128<<20):
    raw=snapshot(path,limit);checked[str(path)]=sha(raw)
    return json.loads(raw)
proof={'schema_version':1,'recorded_at':datetime.now(timezone.utc).isoformat(),
 'scope':'READONLY_ACTUAL_TARGET170_INDEPENDENT_NATIVE_AND_ACCOUNTING',
 'status':'INCOMPLETE','operating_writes':0,'collection_executed':False,'scientific_accuracy_validated':False,'learning_ready':False}
try:
    launch=read(E/'targeted170-execute-launch-20261018.json')
    request=read(E/'targeted170-live-request-20261018.json')
    assert canonical(request)==launch['request_sha256']
    aggregate_path=D/'first-group-training-esri-v1/annual-window-report.json'
    ledger_path=D/'first-group-training-budget/global-ledger.json'
    aggregate=read(aggregate_path);ledger=read(ledger_path)
    before=aggregate['scenes'][:launch['source_rows_before']]
    assert len(before)==1568 and canonical(before)==launch['old_rows_canonical_sha256']
    for old,value in launch['pending_before'].items():assert ledger['batches'][old]==value
    assert sum(v['reserved_bytes'] for v in launch['pending_before'].values())==136314880
    entry=ledger['batches'].get(key)
    if not entry or entry.get('status')!='settled':
        proof['issue']='TARGET_NOT_SETTLED';raise RuntimeError('incomplete')
    folder=D/'first-group-training-esri-v1/sources'/key
    config=read(folder/'config.json');worker=read(folder/'worker-result.json');state=read(folder/'window-state.json');report=read(folder/'annual-window-report.json')
    assert canonical(config)==entry['config_sha256']
    assert canonical(effective_config(config))==state['config_sha256']
    assert worker['key']==key and worker['live_b02_checked'] is True and 'error' not in worker
    assert entry['charged_bytes']==worker['charged_bytes']==state['http_body_bytes']+worker['metadata_budget']['charged_bytes']==worker['cog_charged_bytes']+worker['metadata_budget']['charged_bytes']==3827633
    assert ledger['new_charged_bytes']-launch['charged_before']==entry['charged_bytes']
    assert ledger['rate_limit_active'] is False and worker['circuit'] is None
    rows=[row for row in aggregate['scenes'] if row.get('patch_id','').startswith(key+'-')]
    assert len(rows)==1 and worker['targeted_unenrolled_patches']==[]
    row=rows[0];assert row['province']=='banten' and row['split']=='val' and str(row['year'])=='2020'
    assert row['bands']==['B02','B03','B04','B08','B11','B12']
    boundary=read(local(R,request['plan']['boundary_ref']['path']))
    assert checked[str(local(R,request['plan']['boundary_ref']['path']))]==request['plan']['boundary_ref']['sha256']==row['source_window']['boundary_sha256']
    geometry=next(f['geometry'] for f in boundary['features'] if f['properties']['province_id']=='banten')
    native=native_patch(D,row,geometry,checked)
    assert native['quality_status']=='quality_eligible' and native['eligible_bare_pixels']==row['targeted_bare_pixels']==2199
    assert native['eligible_bare_pixels']>=256 and native['valid_pixels']==64908 and row['valid_pixel_ratio']>=.8 and row['province_inside_fraction']>=.95
    source=row['source_window'];assert sha(snapshot(local(D,source['path']),64<<20))==source['sha256']
    assert sha(snapshot(local(D,source['quality_mask_path']),16<<20))==source['quality_mask_sha256']
    crop_records=[]
    for name,ref in source['raw_source_crops'].items():
        path=local(D,ref['path']);raw=snapshot(path,64<<20);assert sha(raw)==ref['sha256'];checked[str(path)]=sha(raw)
        with MemoryFile(raw) as mem,mem.open(driver='GTiff') as ds:
            crop_records.append({'name':name,'sha256':sha(raw),'shape':[ds.width,ds.height,ds.count],'crs':str(ds.crs),'bounds':list(ds.bounds)})
            if name=='raw-B02.tif':
                actual_b02_bounds=list(ds.bounds);actual_crs=str(ds.crs)
                assert (ds.width,ds.height,ds.count)==(256,256,1) and ds.transform.a==10 and ds.transform.e==-10
                with MemoryFile(snapshot(local(D,row['image_path']),64<<20)) as im,im.open(driver='GTiff') as image:
                    assert np.array_equal(ds.read(1),image.read(1)) and ds.crs==image.crs and ds.transform==image.transform
    for name in ('stac_item','calibration'):
        ref=source[name];raw=snapshot(local(D,ref['path']),2<<20);assert sha(raw)==ref['sha256'];checked[str(local(D,ref['path']))]=sha(raw)
    stac=read(local(D,source['stac_item']['path']),2<<20)
    feature=stac.get('feature',stac)
    # Collector stores the selected raw feature. A persisted true guard flag is
    # a code-path witness, not independent OS/network tracing.
    assert feature.get('id')==row['scene_id']
    for path,expected in [(source['path'],source['sha256']),(source['quality_mask_path'],source['quality_mask_sha256'])]:checked[str(local(D,path))]=expected
    old_raw_files=0
    for old in before:
        for role,field in (('image','image_path'),('label','label_path'),('quality','quality_mask_path')):
            assert sha(snapshot(local(D,old[field]),64<<20))==old['patch_sha256'][role]
            old_raw_files+=1
    scene_conflicts=sorted({old['split'] for old in before if old.get('scene_id')==row['scene_id'] and old.get('split')!='val'})
    assert not scene_conflicts
    # Physical inventory now includes the target's own support files. Its own
    # overlaps are expected; exclude by exact source directory for post-audit,
    # not to modify the production execution gate.
    w,s,e,n=actual_b02_bounds
    inventory=inspect_targeted_inventory(R,{'manifest_ref':request['plan']['current_manifest_ref'],
        'ledger_ref':request['ledger_ref'],'target':{'crs':actual_crs,'corners':[[w,n],[e,n],[e,s],[w,s]]}})
    assert inventory['inventory_verified'] is True and inventory['pending_footprints_verified'] is True
    own='data/first-group-training-esri-v1/sources/'+key+'/'
    prior_overlaps=[name for name in inventory['overlaps'] if not name.startswith(own)]
    assert prior_overlaps==[]
    events=[json.loads(line) for line in (E/'targeted170-execute-20261018-stdout.log').read_text(encoding='utf-8').splitlines() if line.strip()]
    finished=next(x for x in events if x.get('status')=='targeted_worker_finished' and x['key']==key)
    assert finished['patches']==finished['eligible']==1 and finished['live_b02_checked'] is True and finished['charged_bytes']==entry['charged_bytes'] and finished['rate_limited'] is False
    for path,digest in checked.items():assert sha(snapshot(Path(path),128<<20))==digest
    proof.update(status='ACTUAL_TARGET_NATIVE_VERIFIED_UNAPPROVED',issue=None,physical_increment=1,eligible_increment=1,
      native_patch=native,valid_fraction=row['valid_pixel_ratio'],inside_fraction=row['province_inside_fraction'],
      bare_pixels=2199,minimum_bare_pixels=256,bare_threshold_met=True,source_crops=crop_records,
      persisted_b02_guard_witness=True,raw_B02_matches_output_band1=True,actual_B02_bounds=actual_b02_bounds,
      selected_scene_id=row['scene_id'],selected_scene_datetime=row['datetime'],new_scene_conflicting_prior_splits=scene_conflicts,
      old_rows_canonical_verified=1568,old_raw_files_rehashed=old_raw_files,old_pending_exact_rows_preserved=2,pending_reserved_bytes=136314880,
      selected_ledger_record=entry,charged_delta=3827633,inventory_assets_verified=inventory['support_files_verified'],
      inventory_status_with_own_new_output=inventory['status'],own_new_output_overlaps=[x for x in inventory['overlaps'] if x.startswith(own)],
      prior_support_overlaps=prior_overlaps,physical_total=len(aggregate['scenes']),eligible_total=sum(x.get('quality_status')=='quality_eligible' for x in aggregate['scenes']),
      metadata_sha256_at_read={'aggregate':checked[str(aggregate_path)],'ledger':checked[str(ledger_path)]},
      checked_file_sha256=checked,source_crop_count=len(crop_records),execution_lock_present=(D/'first-group-training-budget/global-ledger.execution.lock').exists(),
      limitations=['Esri annual weak labels are not independent ground truth; original local2411 differs from actual valid aligned2199',
       'Source DN with SWIR resampling is not reflectance calibration/20m information becoming10m',
       'Overlap exclusion is strict internal source-window policy, not scientific spatial independence',
       'Persisted guard witness is not independent HTTP syscall trace; no new network was performed by this audit',
       'No training/approval/pointer change; whole-pool quality/class balance remains separate'])
except Exception as exc:
    proof.update(status='INCOMPLETE' if proof.get('issue')=='TARGET_NOT_SETTLED' else 'INDEPENDENT_CHECK_FAILED',failure_type=type(exc).__name__)
    raise
finally:
    proof['seconds']=time.perf_counter()-started
    with (E/'targeted170-independent-20261018.json').open('x',encoding='utf-8') as stream:json.dump(proof,stream,ensure_ascii=False,indent=2)
    print(json.dumps({k:v for k,v in proof.items() if k not in ('checked_file_sha256','source_crops','native_patch','limitations')},ensure_ascii=True),flush=True)
