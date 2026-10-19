"""Read-only bounded native candidate review; emits plan-only targets, never dispatches."""
import argparse
from collections import Counter
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'.runtime'),str(ROOT/'backend')]
from app.data.targeted_bare_plan import _pinned,_json,_need,POLICY
from app.data.readiness_connectivity_witness import FIXED_PROVINCE_SPLITS
from app.data.targeted_inventory import inspect_targeted_inventory
from app.data.targeted_live_guards import TargetedWindowClaims
from app.ml.per_scene_normalization_files import _root,_relative,_snapshot,_Blocked
from app.ml.readiness import esri_reference_matches_year

LIMITS={'maximum_candidates':128,'maximum_label_bytes':768*1024**2,'maximum_label_files':128}


def _ref(root,path):
    digest,_=_snapshot(root,path,8*1024**2,'lineage',True)
    return {'path':path.relative_to(root).as_posix(),'sha256':digest}


def review(root,request):
    """All-or-nothing input/native validation; overlaps are per-candidate observations.

    Exactly one full167 scan, then cached native label reads and 170 numerical
    claims. Current metadata, labels and lineage are pinned before/after. Final
    collector must revalidate because this sequential report cannot reserve data.
    """
    root=_root(root);request=copy.deepcopy(request)
    _need(type(request) is dict and request.keys()=={'schema_version','proposal_ref','manifest_ref','ledger_ref','boundary_ref'},'REQUEST_INVALID')
    _need(type(request['schema_version']) is int and request['schema_version']==1,'REQUEST_INVALID')
    paths={};docs={}
    for name,cap in [('proposal',2*1024**2),('manifest',128*1024**2),('ledger',8*1024**2),('boundary',2*1024**2)]:
        path,raw=_pinned(root,request[name+'_ref'],cap,proposal=name=='proposal')
        paths[name]=path;docs[name]=_json(raw)
    proposal,manifest,ledger,boundary=(docs[k] for k in ('proposal','manifest','ledger','boundary'))
    candidates=proposal['ranked_windows']
    stride=proposal.get('window_stride',256)
    _need(type(stride) is int and stride in (128,256),'PROPOSAL_STRIDE_INVALID')
    scope=proposal.get('province_filter',list(FIXED_PROVINCE_SPLITS))
    _need(type(scope) is list and bool(scope) and all(type(p) is str and p in FIXED_PROVINCE_SPLITS for p in scope) and len(scope)==len(set(scope)),'PROPOSAL_SCOPE_INVALID')
    _need(stride!=128 or 'province_filter' in proposal,'PROPOSAL_SCOPE_INVALID')
    _need(type(candidates) is list and 1<=len(candidates)<=LIMITS['maximum_candidates'],'CANDIDATE_LIMIT')
    _need(type(manifest.get('scenes')) is list and len(manifest['scenes'])<=3000 and type(ledger.get('batches')) is dict,'INPUT_INVALID')
    _need(proposal.get('boundary_sha256')==request['boundary_ref']['sha256'],'BOUNDARY_PIN_MISMATCH')
    from shapely.geometry import shape,Polygon,box
    from shapely.ops import transform as gt
    from pyproj import Transformer
    import numpy as np
    import rasterio
    from rasterio.io import MemoryFile
    from rasterio.windows import Window
    geometries={}
    for feature in boundary['features']:
        province=feature['properties']['province_id']
        if province in FIXED_PROVINCE_SPLITS:
            _need(province not in geometries,'BOUNDARY_INVALID');geometries[province]=shape(feature['geometry'])
    _need(set(geometries)==set(FIXED_PROVINCE_SPLITS) and all(g.is_valid and not g.is_empty for g in geometries.values()),'BOUNDARY_INVALID')
    report_paths=set()
    for batch in ledger['batches'].values():
        if batch.get('report_path') is not None:
            p=Path(batch['report_path'])
            if not p.is_absolute():p=_relative(root,batch['report_path'],'lineage')
            _need(p.is_relative_to(root/'data'),'LINEAGE_PATH_INVALID');report_paths.add(p)
    cache={};lineage_pins={};total=0;seen=set();targets=[];observations=[]
    with rasterio.Env(GDAL_PAM_ENABLED='NO',GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR',GDAL_GEOREF_SOURCES='INTERNAL',PROJ_NETWORK='OFF'):
        for index,c in enumerate(candidates):
            province=c['province'];year=c['year']
            _need(type(province) is str and province in FIXED_PROVINCE_SPLITS and province in scope and c['fixed_split']==FIXED_PROVINCE_SPLITS[province] and type(year) is int and 2020<=year<=2025,'PROVINCE_YEAR_SPLIT_INVALID')
            label_ref={'path':c['source_crop_path'],'sha256':c['source_crop_sha256']}
            path=_relative(root,label_ref['path'],'label')
            _need(path.is_relative_to(root/'data'),'PATH_INVALID')
            xy=c['local_window_xy']
            _need(type(xy) is list and len(xy)==2 and all(type(v) is int and v>=0 and v%stride==0 for v in xy),'WINDOW_INVALID')
            identity=(label_ref['sha256'],*xy)
            _need(identity not in seen,'DUPLICATE_SHA_WINDOW');seen.add(identity)
            if path not in cache:
                _need(len(cache)<LIMITS['maximum_label_files'],'LABEL_LIMIT')
                _,raw=_pinned(root,label_ref,64*1024**2)
                total+=len(raw);_need(total<=LIMITS['maximum_label_bytes'],'LABEL_LIMIT')
                cache[path]=(label_ref['sha256'],raw)
            _need(cache[path][0]==label_ref['sha256'],'LABEL_PIN_CONFLICT')
            lineage=path.parent.parent/'annual-window-report.json'
            _need(lineage in report_paths,'LINEAGE_NOT_LEDGER_BOUND')
            if lineage not in lineage_pins:
                ref=_ref(root,lineage);_,raw=_pinned(root,ref,8*1024**2)
                lineage_pins[lineage]=(ref,_json(raw))
            lineage_ref,source_doc=lineage_pins[lineage]
            matches=[r for r in source_doc['scenes'] if r.get('source_crops',{}).get('raw-esri_io.tif',{}).get('sha256')==label_ref['sha256']]
            _need(len(matches)==1,'LABEL_LINEAGE_AMBIGUOUS')
            source=matches[0];crop=source['source_crops']['raw-esri_io.tif'];crop_path=Path(crop['path'])
            if not crop_path.is_absolute():crop_path=_relative(root,crop['path'],'label')
            _need(crop_path==path and source.get('province',source.get('aoi'))==province and str(source['year'])==str(year) and type(source['label_year']) is int and source['label_year']==year and source.get('label_source')=='esri_io' and crop.get('source')==source['label_source_url'] and esri_reference_matches_year(source['label_source_url'],year),'LABEL_LINEAGE_INVALID')
            with MemoryFile(cache[path][1]) as memory,memory.open(driver='GTiff') as ds:
                t=ds.transform
                _need(ds.count==1 and ds.width<=8192 and ds.height<=8192 and ds.crs is not None and ds.crs.is_projected and ds.crs.linear_units_factor[1]==1.0 and (t.a,t.b,t.d,t.e)==(10,0,0,-10) and ds.dtypes[0] in ('uint8','uint16','int16','int32') and not ds.subdatasets and not ds.gcps[0] and ds.rpcs is None,'LABEL_GRID_INVALID')
                _need(xy[0]+256<=ds.width and xy[1]+256<=ds.height,'WINDOW_INVALID')
                grid={'crs':ds.crs.to_string(),'transform':list(t)[:6],'width':ds.width,'height':ds.height}
                _need(grid==c['source_label_grid'],'LABEL_GRID_MISMATCH')
                affine=ds.window_transform(Window(*xy,256,256));corners=[list(affine*p) for p in ((0,0),(256,0),(256,256),(0,256))]
                native={'crs':ds.crs.to_string(),'corners':corners};polygon=Polygon(corners)
                _need(native==c['target_footprint_native'],'GEOMETRY_MISMATCH')
                transform=Transformer.from_crs(ds.crs,4326,always_xy=True)
                points=[transform.transform(*p) for p in corners];bbox=[min(p[0] for p in points),min(p[1] for p in points),max(p[0] for p in points),max(p[1] for p in points)]
                _need(c['bbox_wgs84']==bbox,'GEOMETRY_MISMATCH')
                projected=gt(Transformer.from_crs(4326,ds.crs,always_xy=True).transform,geometries[province])
                inside=projected.intersection(polygon).area/polygon.area
                _need(inside>=.95,'BOUNDARY_SHORTFALL')
                bare=int(np.count_nonzero(ds.read(1,window=Window(*xy,256,256))==8))
                _need(type(c['declared_weak_label_bare_pixels']) is int and bare==c['declared_weak_label_bare_pixels'] and bare>=256,'BARE_COUNT_MISMATCH')
                target={'target_id':f'local-rank{index}-{year}','proposal_window_index':index,'province':province,'fixed_split':FIXED_PROVINCE_SPLITS[province],'year':year,'source_label_ref':label_ref,'source_lineage_ref':lineage_ref,'source_label_window':[*xy,256,256],'source_label_grid':grid,'target_bbox_wgs84':bbox,'target_footprint_native':native,'declared_bare_pixels':bare}
                targets.append(target);observations.append({'target_id':target['target_id'],'native_bare_pixels':bare,'geometric_inside_fraction':inside,'bounds':list(polygon.bounds)})
    inventory=inspect_targeted_inventory(root,{'manifest_ref':request['manifest_ref'],'ledger_ref':request['ledger_ref'],'target':targets[0]['target_footprint_native']})
    _need(inventory.get('inventory_verified') is True and inventory.get('pending_footprints_verified') is True and inventory.get('source_pins_verified') is True,'INVENTORY_NOT_VERIFIED')
    assets=inventory['assets'];mutual=[]
    for i,(target,observation) in enumerate(zip(targets,observations)):
        crs=target['target_footprint_native']['crs'];bounds=observation['bounds']
        try:
            TargetedWindowClaims(assets).claim(target['target_id'],crs,bounds)
            observation['historical_overlap']=False
        except ValueError as exc:
            _need(str(exc)=='LIVE_SUPPORT_WINDOW_OVERLAP','HISTORICAL_PROJECTION_FAILED');observation['historical_overlap']=True
        observation.update(execution_supported=False,actual_quality_eligible=False,scientifically_verified_bare=False)
        for j in range(i):
            previous=targets[j];claims=TargetedWindowClaims([{'crs':previous['target_footprint_native']['crs'],'bounds':observations[j]['bounds']}])
            try:claims.claim(target['target_id'],crs,bounds)
            except ValueError as exc:
                _need(str(exc)=='LIVE_SUPPORT_WINDOW_OVERLAP','MUTUAL_PROJECTION_FAILED');mutual.append([previous['target_id'],target['target_id']])
    for name,path in paths.items():_pinned(root,request[name+'_ref'],128*1024**2,proposal=name=='proposal')
    for path,(digest,_) in cache.items():_need(_snapshot(root,path,64*1024**2,'label')[0]==digest,'LABEL_CHANGED')
    for path,(ref,_) in lineage_pins.items():_need(_snapshot(root,path,8*1024**2,'lineage')[0]==ref['sha256'],'LINEAGE_CHANGED')
    summary=[]
    for province in FIXED_PROVINCE_SPLITS:
        selected=[o for t,o in zip(targets,observations) if t['province']==province]
        overlaps=sum(o['historical_overlap'] for o in selected)
        summary.append({'province':province,'candidates':len(selected),'support_clear':len(selected)-overlaps,'overlap':overlaps,'local_invalid':0})
    ui={'schema_version':1,'status':'LOCAL_TARGET_REVIEW_FINISHED','recorded_at':datetime.now(timezone.utc).isoformat(),'current_manifest_sha256':request['manifest_ref']['sha256'],'execution_supported':False,'actual_quality_verified':False,'scientific_accuracy_validated':False,'summary_by_province':summary,'candidate_total':len(targets)}
    return {'schema_version':1,'kind':'SIX_PROVINCE_BARE_PLAN_ONLY_REVIEW','status':'LOCAL_NATIVE_REVIEW_COMPLETE_EXECUTION_UNAPPROVED','request':request,'limits':LIMITS,'targets':targets,'observations':observations,'candidate_mutual_overlap_pairs':mutual,'historical_clear_count':sum(not o['historical_overlap'] for o in observations),'province_counts':dict(Counter(t['province'] for t in targets)),'inventory':inventory,'inventory_scan_count':1,'native_label_files_read':len(cache),'native_label_bytes_read':total,'native_label_recheck':True,'ui_summary':ui,'execution_supported':False,'actual_quality_eligible':False,'scientifically_verified_bare':False,'network_requests':0,'source_or_ledger_writes':0,'limitations':['Weak labels and numerical overlap checks are not independent ground truth.','Candidate mutual overlaps are reported separately; historical-clear does not mean mutually independent.','All selected plans require175/176/170 fresh validation and live B02/scene/quality/budget guards.','Sequential metadata and byte checks are not an atomic snapshot; collector must revalidate inventory.']}


def select_plan(result,indices):
    _need(type(indices) is list and 1<=len(indices)<=2 and all(type(i) is int and 0<=i<len(result['targets']) for i in indices) and len(set(indices))==len(indices),'SELECTION_INVALID')
    targets=[result['targets'][i] for i in indices];ids={t['target_id'] for t in targets}
    _need(all(not result['observations'][i]['historical_overlap'] for i in indices),'HISTORICAL_OVERLAP')
    _need(not any(set(pair)<=ids for pair in result['candidate_mutual_overlap_pairs']),'MUTUAL_OVERLAP')
    req=result['request']
    return {'schema_version':1,'kind':'TARGETED_BARE_256_COLLECTION_PLAN','proposal_ref':copy.deepcopy(req['proposal_ref']),'current_manifest_ref':copy.deepcopy(req['manifest_ref']),'boundary_ref':copy.deepcopy(req['boundary_ref']),'policy':{**POLICY,'maximum_new_batches':len(targets)},'targets':copy.deepcopy(targets)}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__,allow_abbrev=False)
    p.add_argument('--request',type=Path,required=True);p.add_argument('--request-sha256',required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args(argv)
    try:
        root=_root(ROOT);path=args.request.absolute();out=args.output.absolute()
        _need(path.is_relative_to(root/'evidence/integration') and out.is_relative_to(root/'evidence/integration') and out.suffix=='.json','PATH_INVALID')
        _need(not out.exists() and not out.is_symlink() and out.parent.resolve()==out.parent,'NEW_OUTPUT_REQUIRED')
        digest,raw=_snapshot(root,path,2*1024**2,'request',True);_need(digest==args.request_sha256,'REQUEST_PIN_MISMATCH')
        result=review(root,_json(raw))
        _need(_snapshot(root,path,2*1024**2,'request')[0]==digest,'REQUEST_CHANGED')
        payload=(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode()
        _need(len(payload)<=2*1024**2,'OUTPUT_LIMIT')
        with out.open('xb') as stream:stream.write(payload)
        print(json.dumps({'status':result['status'],'targets':len(result['targets']),'historical_clear_count':result['historical_clear_count'],'output_sha256':hashlib.sha256(payload).hexdigest(),'execution_supported':False}));return 0
    except (_Blocked,ValueError,KeyError,TypeError,OSError):
        print(json.dumps({'status':'REVIEW_BLOCKED','execution_supported':False,'source_or_ledger_writes':0}),file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())
