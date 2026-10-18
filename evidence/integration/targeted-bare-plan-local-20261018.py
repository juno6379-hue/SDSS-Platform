"""157 real local read-only label/imagery check; new snapshot/evidence only."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import time
import rasterio
from pyproj import Transformer
from app.data.targeted_bare_plan import prepare_targeted_bare_jobs,POLICY
from app.ml.per_scene_normalization_files import _snapshot

ROOT=Path(__file__).resolve().parents[2]
EVIDENCE=ROOT/'evidence/integration'
PREFIX='targeted-bare-plan-local-20261018'
start=time.perf_counter()

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def ref(path):return {'path':path.relative_to(ROOT).as_posix(),'sha256':sha(path)}

proposal_path=EVIDENCE/'ml-resume-audit-20261018-local-banten-label-search.json'
proposal=json.loads(proposal_path.read_text(encoding='utf-8'))
target=proposal['ranked_windows'][0]
label=ROOT/target['source_crop_path'].replace('\\','/')
lineage=label.parent.parent/'annual-window-report.json'
boundary=ROOT/'data/first-group-boundaries/selected-six.geojson'
aggregate=ROOT/'data/first-group-training-esri-v1/annual-window-report.json'
pins_before={str(path.relative_to(ROOT)):sha(path) for path in (proposal_path,label,lineage,boundary)}
aggregate_sha,raw=_snapshot(ROOT,aggregate,64*1024**2,'aggregate',True)
snapshot_directory=ROOT/'data/targeted-bare-plan-157'
snapshot_directory.mkdir(exist_ok=False)
snapshot=snapshot_directory/'annual-window-report-snapshot.json'
with snapshot.open('xb') as stream:stream.write(raw)
del raw
with rasterio.Env(GDAL_PAM_ENABLED='NO',GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR',GDAL_GEOREF_SOURCES='INTERNAL'):
    with rasterio.open(label) as ds:
        x,y=target['local_window_xy'];affine=ds.window_transform(rasterio.windows.Window(x,y,256,256))
        corners=[affine*p for p in ((0,0),(256,0),(256,256),(0,256))]
        grid={'crs':ds.crs.to_string(),'transform':list(ds.transform)[:6],'width':ds.width,'height':ds.height}
        converter=Transformer.from_crs(ds.crs,4326,always_xy=True)
        xy=[converter.transform(*point) for point in corners]
        bbox=[min(p[0] for p in xy),min(p[1] for p in xy),max(p[0] for p in xy),max(p[1] for p in xy)]
plan={'schema_version':1,'kind':'TARGETED_BARE_256_COLLECTION_PLAN',
    'proposal_ref':ref(proposal_path),'current_manifest_ref':ref(snapshot),'boundary_ref':ref(boundary),
    'policy':{**POLICY,'maximum_new_batches':1},'targets':[{
        'target_id':'local-rank0-2020','proposal_window_index':0,'province':'banten','fixed_split':'val','year':target['year'],
        'source_label_ref':ref(label),'source_lineage_ref':ref(lineage),
        'source_label_window':[*target['local_window_xy'],256,256],'source_label_grid':grid,
        'target_bbox_wgs84':bbox,'target_footprint_native':{'crs':grid['crs'],'corners':[list(point) for point in corners]},
        'declared_bare_pixels':target['declared_weak_label_bare_pixels']}]}
with (EVIDENCE/(PREFIX+'-request.json')).open('x',encoding='utf-8') as stream:
    json.dump(plan,stream,ensure_ascii=False,indent=2,allow_nan=False);stream.write('\n')
print(json.dumps({'stage':'snapshot_pinned','aggregate_sha256':aggregate_sha,'target_id':'local-rank0-2020'}),flush=True)
base=json.loads((ROOT/'configs/first-group.collection.json').read_text(encoding='utf-8'))
observation=prepare_targeted_bare_jobs(ROOT,plan,base)
pins_after={str(path.relative_to(ROOT)):sha(path) for path in (proposal_path,label,lineage,boundary)}
assert pins_before==pins_after
assert sha(snapshot)==aggregate_sha
proof={'schema_version':1,'recorded_at':datetime.now().astimezone().isoformat(),
    'status':'REAL_LOCAL_PLAN_OBSERVATION_NOT_COLLECTION','observation':observation,
    'aggregate_snapshot_sha256':aggregate_sha,'proposal_historical_aggregate_sha256':proposal['source_manifest_sha256'],
    'fixed_input_before_sha256':pins_before,'fixed_input_after_sha256':pins_after,
    'current_aggregate_is_mutable_during_root_collection':True,
    'input_source_files_written':0,'ledger_or_lock_writes':0,'HTTP_requests':0,'training_or_inference':0,
    'new_files':['data/targeted-bare-plan-157/annual-window-report-snapshot.json',
        'evidence/integration/'+PREFIX+'-request.json','evidence/integration/'+PREFIX+'.json'],
    'seconds':time.perf_counter()-start,
    'limits':['Only listed aggregate patch/source images are covered, not unlisted/pending/raw-support geometry.',
        'All results remain execution unsupported: no shared scene-veto, actual Sentinel B02 geometry or exclusive output connection.',
        'A local weak-label count is not physical bare truth, independent locations, actual quality or training readiness.']}
with (EVIDENCE/(PREFIX+'.json')).open('x',encoding='utf-8') as stream:
    json.dump(proof,stream,ensure_ascii=False,indent=2,allow_nan=False);stream.write('\n')
print(json.dumps({'status':observation['status'],'issue':observation['issue'],'existing_images_observed':observation['existing_images_observed'],
    'targets':observation['targets'],'seconds':proof['seconds']},ensure_ascii=True),flush=True)
