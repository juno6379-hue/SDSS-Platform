"""190: bounded local half-stride discovery in two provinces; no support audit or HTTP."""
import hashlib,json,os,sys,time
from datetime import datetime,timezone,timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT),str(ROOT/'.runtime'),str(ROOT/'backend')]
from scripts.find_bare_targets173 import discover,pin,LIMITS
SOURCE_SHA='3d5ae7d2c75e169a2bcf8b3e5dfbb1e854145f73f26d75a5549608e9fa4969d8'
BOUNDARY_SHA='de7722bfa88ddff3e12137d271c28717c23b3077a87b7dc36c66d1d8c522c909'
source=ROOT/'data/first-group-training-esri-v1/annual-window-report.json'
boundary=ROOT/'data/first-group-boundaries/selected-six.geojson'
data=ROOT/'data/bare190-gap-20261018'
out=ROOT/'evidence/integration/bare190-gap-20261018'
def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def write(path,value):
    raw=(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf-8')
    if len(raw)>2*1024**2:raise ValueError('Evidence JSON exceeds2MiB')
    with path.open('xb') as stream:stream.write(raw)
    return {'path':str(path.relative_to(ROOT)),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
start=time.monotonic()
assert not data.exists() and not data.is_symlink()
assert set(p.name for p in out.iterdir())=={'run.py'},'New output scope required'
raw=pin(ROOT,source,SOURCE_SHA,64*1024**2)
pin(ROOT,boundary,BOUNDARY_SHA,2*1024**2)
assert digest(source)==SOURCE_SHA,'Active source changed before snapshot'
protected=[ROOT/'evidence/integration/bare173-verified-20261018/proposal.json',ROOT/'evidence/integration/bare173-verified-20261018/receipt.json',ROOT/'evidence/integration/bare179-report-20261018.json']
before={str(p.relative_to(ROOT)):digest(p) for p in protected}
data.mkdir(exist_ok=False)
with (data/'source.json').open('xb') as stream:stream.write(raw)
assert digest(data/'source.json')==SOURCE_SHA
write(out/'preflight.json',{'at_kst':datetime.now(timezone(timedelta(hours=9))).isoformat(),'status':'FIXED_LOCAL_SOURCE_SNAPSHOT_CREATED','source_sha256':SOURCE_SHA,'source_bytes':len(raw),'boundary_sha256':BOUNDARY_SHA,'protected_pins':before,'prior_native_owner_completed':'priority188-native-root-20261018.json','active_collector_may_append_later':True,'no_179_support_audit':True})
del raw
limits={**LIMITS,'max_candidates':50,'max_total_bytes':50*1024**2}
result=discover(ROOT,data/'source.json',SOURCE_SHA,boundary,BOUNDARY_SHA,limits=limits,window_stride=128,provinces=['gorontalo','west_java'])
proposal=write(out/'proposal.json',result)
# Recount only returned local-label windows. No image/SCL/support inventory or179 reader.
import numpy as np
import rasterio
from rasterio.io import MemoryFile
from rasterio.windows import Window
verified=[]
for candidate in result['ranked_windows']:
    path=ROOT/candidate['source_crop_path']
    payload=pin(ROOT,path,candidate['source_crop_sha256'],64*1024**2)
    x,y=candidate['local_window_xy']
    assert x%128==0 and y%128==0
    with rasterio.Env(GDAL_PAM_ENABLED='NO',GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR',GDAL_GEOREF_SOURCES='INTERNAL'):
        with MemoryFile(payload) as memory:
            with memory.open(driver='GTiff') as ds:
                n=int(np.count_nonzero(ds.read(1,window=Window(x,y,256,256))==8))
    assert n==candidate['declared_weak_label_bare_pixels'] and n>=256
    verified.append({'province':candidate['province'],'year':candidate['year'],'crop_sha256':candidate['source_crop_sha256'],'xy':[x,y],'bare_pixels':n})
assert digest(data/'source.json')==SOURCE_SHA and digest(boundary)==BOUNDARY_SHA
assert all(digest(ROOT/item['path'])==item['sha256'] for item in result['inventory'])
after={str(p.relative_to(ROOT)):digest(p) for p in protected}
assert before==after,'Historical50proposal/report changed'
assert digest(out/'proposal.json')==proposal['sha256']
summary={'status':'LOCAL_OFFSET_DISCOVERY_COMPLETE_UNAPPROVED','at_kst':datetime.now(timezone(timedelta(hours=9))).isoformat(),'seconds':round(time.monotonic()-start,3),'source_snapshot_sha256':SOURCE_SHA,'source_snapshot_bytes':(data/'source.json').stat().st_size,'source_row_count':result['source_row_count'],'source_eligible_rows':sum(row.get('quality_status')=='quality_eligible' for row in json.loads((data/'source.json').read_text(encoding='utf-8'))['scenes']),'boundary_sha256':BOUNDARY_SHA,'active_source_sha256_after_observation':digest(source),'scope':'FROZEN_188_POST_NATIVE_SNAPSHOT_EXCLUDES_LATER189_COLLECTION','window_size':256,'window_stride':128,'province_filter':result['province_filter'],'limits':limits,'local_label_crops_read':result['local_label_crops_read'],'label_bytes_read':result['label_bytes_read'],'windows_scanned':result['windows_scanned'],'duplicate_sha_windows_excluded':result['duplicate_sha_windows_excluded'],'qualified_dense_inside_windows':result['qualified_dense_inside_windows'],'returned_ranked_windows':len(result['ranked_windows']),'split_qualified_counts':result['split_qualified_counts'],'province_summary':result['province_summary'],'proposal':proposal,'ranked_native_label_recounts':len(verified),'ranked_recount_results':verified,'original50proposal_and179report_unchanged':before==after,'historical_output_pins':after,'snapshot_and_boundary_and_label_pins_stable':True,'full179_support_audit_executed':False,'past_or_mutual_overlap_approved':False,'execution_supported':False,'actual_quality_eligible':False,'spatial_independence_verified':False,'scientifically_verified_bare':False,'ready_for_training':False,'network_requests':0,'collection_executed':False,'training_executed':False,'ledger_or_lock_written':False,'source_files_written':0,'limits_note':'label_bytes_read counts compressed first payloads; final hashes and recounts add local IO, not hard total-IO/RSS/time limits.'}
receipt=write(out/'receipt.json',summary)
print(json.dumps({k:summary[k] for k in ['status','seconds','source_row_count','local_label_crops_read','label_bytes_read','windows_scanned','qualified_dense_inside_windows','returned_ranked_windows','duplicate_sha_windows_excluded','split_qualified_counts','ranked_native_label_recounts']},ensure_ascii=True),flush=True)
print(json.dumps({'proposal':proposal,'receipt':receipt},ensure_ascii=True),flush=True)
