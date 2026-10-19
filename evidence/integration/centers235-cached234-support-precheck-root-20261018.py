"""Numerical planning precheck only; reuse234 assets, never mint a fresh inventory proof."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,sys,time
R=Path(__file__).resolve().parents[2];E=R/'evidence/integration';D=R/'data'
sys.path[:0]=[str(R),str(R/'.runtime'),str(R/'backend')]
from pyproj import Transformer
from app.data.targeted_live_guards import TargetedWindowClaims,_metric_crs
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
paths={'source':D/'first-group-training-esri-v1/annual-window-report.json',
 'ledger':D/'first-group-training-budget/global-ledger.json',
 'proposal':D/'centers235-fresh-20261018/proposal.json','report234':E/'bare234-report-root-20261018.json',
 'guard199':R/'backend/app/data/deficit_candidate_guard.py','liveguard':R/'backend/app/data/targeted_live_guards.py'}
pins={k:sha(p) for k,p in paths.items()}
assert pins['source']=='9c24eec337a17f95855d190918c9999c25aeb1925a7642b1ade26afa4e20d987'
assert pins['ledger']=='61161c35eabb593afb5f096c256791871d297b723f82ffc2ac2449b3bd8266e7'
assert pins['proposal']=='87e6f5f157d940e00c624f46821d30329135ef9182a0acb1db248bfb59a712da'
assert pins['report234']=='c936575e2937d5c8ec9f1e4675de89eed0f5dbabce26bbd26bea8661c4b18458'
report=json.loads(paths['report234'].read_text('utf-8'));proposal=json.loads(paths['proposal'].read_text('utf-8'))
assert report['inventory_scan_count']==1 and report['request']['manifest_ref']['sha256']==pins['source']
assert report['request']['ledger_ref']['sha256']==pins['ledger']
assert not (D/'first-group-training-budget/global-ledger.execution.lock').exists()
start=time.monotonic();observations=[]
for index,c in enumerate(proposal['candidates']):
    crs=_metric_crs(c['grid_crs']);x,y=Transformer.from_crs(4326,crs,always_xy=True).transform(c['lon'],c['lat'])
    bounds=[x-5120,y-5120,x+5120,y+5120]
    try:TargetedWindowClaims(report['inventory']['assets']).claim(c['spatial_window_id'],crs.to_string(),bounds);overlap=False
    except ValueError as exc:
        assert str(exc)=='LIVE_SUPPORT_WINDOW_OVERLAP';overlap=True
    observations.append({'index':index,'province':c['province'],'years':c['years'],'spatial_window_id':c['spatial_window_id'],
      'native_crs':crs.to_string(),'native_bounds':bounds,'overlap_against_fixed234_assets':overlap})
assert all(sha(p)==pins[k] for k,p in paths.items())
out={'status':'CACHED234_NUMERICAL_PRECHECK_NOT_FRESH_FULL_INVENTORY','at_utc':datetime.now(timezone.utc).isoformat(),
 'seconds':round(time.monotonic()-start,3),'input_pins':pins,'pins_unchanged':True,
 'cached_asset_count':len(report['inventory']['assets']),'new_inventory_scans':0,'native_raster_reads':0,
 'observations':observations,'network_requests':0,'collection_started':False,'execution_supported':False,
 'fresh200_under_lock_required':True,'limitations':['Cached234 assets do not detect newly added or changed support files.','Fresh200 must validate full current inventory, scene/window/split, actual imagery, budget and physical caps.']}
with (E/'centers235-cached234-support-precheck-root-20261018.json').open('x',encoding='utf-8') as f:json.dump(out,f,ensure_ascii=False,indent=2)
print(json.dumps(out,ensure_ascii=True),flush=True)
