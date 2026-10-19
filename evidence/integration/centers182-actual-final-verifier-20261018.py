"""Independent final candidate footprints and pinned file audit; no collection."""
import hashlib,json,time
from pathlib import Path
from collections import Counter
from pyproj import Transformer
from shapely.geometry import shape,box
from shapely.ops import transform
from rasterio.warp import transform_bounds
ROOT=Path(__file__).resolve().parents[2]
work=ROOT/'data/centers182-actual-20261018';evidence=ROOT/'evidence/integration'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf8'))
start=time.monotonic();proposal=work/'proposal.json';before=sha(proposal)
assert before=='e9dcd4a9c6ae994c9cb48fb7acbce3b217494279edfc0076b540e3860b88c565'
p=load(proposal);source=load(work/'source.json')
assert sha(work/'source.json')==p['source_sha256']
boundary=ROOT/'data/first-group-boundaries/selected-six.geojson';assert sha(boundary)==p['boundary_sha256']
geometry={f['properties']['province_id']:shape(f['geometry']) for f in load(boundary)['features']}
counts=Counter((r['province'],int(r['year'])) for r in source['scenes'] if r.get('quality_status')=='quality_eligible')
for r in p['source_header_inventory']:assert sha(ROOT/r['path'])==r['sha256']
windows=[];checks=[]
for c in p['candidates']:
    crs=c['grid_crs'];f=Transformer.from_crs(4326,crs,always_xy=True)
    x,y=f.transform(c['lon'],c['lat']);window=box(x-5120,y-5120,x+5120,y+5120)
    polygon=transform(f.transform,geometry[c['province']]);inside=polygon.intersection(window).area/window.area
    assert inside>=.95 and abs(inside-c['inside_fraction_native'])<1e-9
    assert c['fixed_split']=='train' and c['years'] in ([2024],[2025]) and c['deficit_at_snapshot']==28-counts[c['province'],c['years'][0]]>0
    for r in p['source_header_inventory']:
        b=r['bounds'] if r['crs']==crs else transform_bounds(r['crs'],crs,*r['bounds'],densify_pts=1024)
        assert window.intersection(box(b[0]-1,b[1]-1,b[2]+1,b[3]+1)).area==0
    for other_crs,bounds in windows:
        b=bounds if other_crs==crs else transform_bounds(other_crs,crs,*bounds,densify_pts=1024)
        assert window.intersection(box(b[0]-1,b[1]-1,b[2]+1,b[3]+1)).area==0
    windows.append((crs,window.bounds));checks.append({'id':c['spatial_window_id'],'province':c['province'],'year':c['years'][0],'native_inside_fraction':inside,'source_header_overlap_count':0})
assert sha(proposal)==before
result={'status':'LOCAL_PROPOSAL_GEOMETRY_AND_PINS_REVERIFIED_UNAPPROVED','seconds':round(time.monotonic()-start,3),'proposal_sha256':before,'source_snapshot_sha256':sha(work/'source.json'),'source_rows':len(source['scenes']),'header_file_pins_checked':len(p['source_header_inventory']),'candidate_geometry_recomputed':checks,'candidate_pair_overlap_count':0,'proposal_unchanged':True,'source_snapshot_unchanged':True,'full_pending_support_inventory_verified':False,'prior_template_centers_independently_recomputed':False,'execution_supported':False,'http_requests':0,'ledger_written':False}
with (evidence/'centers182-actual-final-verification-20261018.json').open('x',encoding='utf8') as stream:json.dump(result,stream,ensure_ascii=False,indent=2);stream.write('\n')
print(json.dumps(result),flush=True)
