"""Independent proposal pin, crop byte pins and all declared window counts."""
import hashlib,json,time
from pathlib import Path
import numpy as np
import rasterio
from rasterio.io import MemoryFile
from rasterio.windows import Window
ROOT=Path(__file__).resolve().parents[2]
proposal=ROOT/'evidence/integration/bare173-verified-20261018/proposal.json'
receipt=proposal.with_name('receipt.json')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
start=time.monotonic();before=sha(proposal);p=json.loads(proposal.read_text(encoding='utf8'));r=json.loads(receipt.read_text(encoding='utf8'))
assert before==r['proposal_sha256']
assert sha(ROOT/'data/bare173-verified-20261018/source.json')==p['source_manifest_sha256']
assert sha(ROOT/'data/bare173-verified-20261018/boundary.geojson')==p['boundary_sha256']
assert all(sha(ROOT/i['path'])==i['sha256'] for i in p['inventory'])
seen=set()
with rasterio.Env(GDAL_PAM_ENABLED='NO',GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR',GDAL_GEOREF_SOURCES='INTERNAL'):
    for c in p['ranked_windows']:
        key=(c['source_crop_sha256'],*c['local_window_xy']);assert key not in seen;seen.add(key)
        raw=(ROOT/c['source_crop_path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==c['source_crop_sha256']
        with MemoryFile(raw) as mem:
            with mem.open(driver='GTiff') as ds:
                x,y=c['local_window_xy'];count=int(np.count_nonzero(ds.read(1,window=Window(x,y,256,256))==8))
        assert count==c['declared_weak_label_bare_pixels']>=256
        assert c['geometric_inside_fraction']>=.95 and c['execution_supported'] is False and c['actual_quality_eligible'] is False
assert sha(proposal)==before
result={'status':'PROPOSAL_AND_LOCAL_BYTES_REVERIFIED','seconds':round(time.monotonic()-start,3),'proposal_sha256':before,'source_sha256':p['source_manifest_sha256'],'boundary_sha256':p['boundary_sha256'],'crop_pins_rechecked':len(p['inventory']),'candidate_windows_recounted':len(p['ranked_windows']),'duplicate_sha_windows':0,'count_mismatches':0,'proposal_unchanged':True,'execution_supported':False,'geometry_recomputed_by_this_verifier':False,'network_requests':0,'scope':'LOCAL_WEAK_LABEL_COUNTS_NOT_IMAGE_QUALITY_OR_SPATIAL_INDEPENDENCE'}
with (ROOT/'evidence/integration/bare173-final-verification-20261018.json').open('x',encoding='utf8') as stream:json.dump(result,stream,ensure_ascii=False,indent=2);stream.write('\n')
print(json.dumps(result),flush=True)
