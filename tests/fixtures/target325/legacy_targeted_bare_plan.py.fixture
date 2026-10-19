"""Local 256-window proposal validation; never authorizes a collector dispatch."""
import copy
import hashlib
import json
import math
from pathlib import Path
import re

from ..ml.per_scene_normalization_files import _root,_relative,_snapshot,_Blocked
from .quality_mask_bundle import _copy_json,_Invalid
from .readiness_connectivity_witness import FIXED_PROVINCE_SPLITS

TOP={'schema_version','kind','proposal_ref','current_manifest_ref','boundary_ref','policy','targets'}
TARGET={'target_id','proposal_window_index','province','fixed_split','year','source_label_ref','source_lineage_ref',
    'source_label_window','source_label_grid','target_bbox_wgs84','target_footprint_native','declared_bare_pixels'}
POLICY={'window_size':256,'source_taxonomy_code':8,'minimum_declared_bare_pixels':256,
    'minimum_valid_fraction':.8,'minimum_inside_fraction':.95}


def _need(condition,code):
    if not condition:raise ValueError(code)


def _keys(value,keys):
    return type(value) is dict and len(value)==len(keys) and all(type(k) is str for k in value) and value.keys()==keys


def _sha(value):
    return type(value) is str and re.fullmatch('[a-f0-9]{64}',value) is not None


def _json(raw):
    def pairs(items):
        result={}
        for key,value in items:
            _need(key not in result,'JSON_INVALID');result[key]=value
        return result
    return json.loads(raw.decode('utf-8'),object_pairs_hook=pairs,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError('JSON_INVALID')))


def _pinned(root,ref,maximum,*,proposal=False):
    _need(_keys(ref,{'path','sha256'}) and _sha(ref['sha256']),'REFERENCE_INVALID')
    path=_relative(root,ref['path'],'reference')
    permitted=root/'evidence/integration' if proposal else root/'data'
    _need(path.is_relative_to(permitted),'PATH_INVALID')
    digest,raw=_snapshot(root,path,maximum,'reference',True)
    _need(digest==ref['sha256'],'FILE_PIN_MISMATCH')
    return path,raw


def _polygon(dataset):
    from shapely.geometry import Polygon
    t=dataset.transform
    _need(dataset.crs is not None and dataset.crs.is_projected and t.b==t.d==0 and t.a>0 and t.e<0,'RASTER_GRID_INVALID')
    corners=[t*(0,0),t*(dataset.width,0),t*(dataset.width,dataset.height),t*(0,dataset.height)]
    _need(all(math.isfinite(v) for pair in corners for v in pair),'RASTER_GRID_INVALID')
    return Polygon(corners)


def prepare_targeted_bare_jobs(project_root,plan,base_config):
    """Return plan-only job proposals or fixed BLOCKED; no HTTP/Store/writes.

    Existing image overlap is observed from the pinned aggregate's listed patch
    and source-image headers. Pending/support/actual STAC geometry is NOT checked;
    execution remains unsupported even when these local checks succeed.
    """
    blocked={'schema_version':1,'scope':'LOCAL_TARGETED_BARE_256_PLAN_ONLY','status':'BLOCKED','issue':None,
        'plan_sha256':None,'targets':[],'job_proposals':[],'existing_images_observed':0,
        'local_label_bytes_verified':False,'listed_image_overlap_checked':False,
        'execution_supported':False,'actual_quality_eligible':False,'scientifically_verified_bare':False,
        'pending_footprints_verified':False,'source_scene_split_verified':False,'training_ready':False}
    result=copy.deepcopy(blocked)
    try:
        plan=_copy_json(plan,'plan');base=_copy_json(base_config,'base_config');root=_root(project_root)
        _need(_keys(plan,TOP) and type(plan['schema_version']) is int and plan['schema_version']==1 and
            plan['kind']=='TARGETED_BARE_256_COLLECTION_PLAN','PLAN_INVALID')
        policy=plan['policy']
        required_policy=set(POLICY)|{'maximum_new_batches'}
        _need(_keys(policy,required_policy) or _keys(policy,required_policy|{'minimum_candidate_valid_fraction'}),'POLICY_INVALID')
        for key,expected in POLICY.items():_need(type(policy[key]) is type(expected) and policy[key]==expected,'POLICY_INVALID')
        candidate_minimum=.65
        if 'minimum_candidate_valid_fraction' in policy:
            candidate_minimum=policy['minimum_candidate_valid_fraction']
            _need(type(candidate_minimum) in (int,float) and math.isfinite(candidate_minimum) and
                .8<=candidate_minimum<=1,'POLICY_INVALID')
        maximum=policy['maximum_new_batches']
        _need(type(maximum) is int and 1<=maximum<=2,'POLICY_INVALID')
        _need(type(plan['targets']) is list and 1<=len(plan['targets'])<=maximum,'TARGETS_INVALID')
        ids=set()
        for target in plan['targets']:
            _need(_keys(target,TARGET),'TARGET_INVALID')
            identifier=target['target_id'];year=target['year'];index=target['proposal_window_index']
            _need(type(identifier) is str and re.fullmatch('[A-Za-z0-9_-]{1,40}',identifier) and identifier not in ids,'TARGET_INVALID');ids.add(identifier)
            province=target['province']
            _need(type(province) is str and province in FIXED_PROVINCE_SPLITS and
                type(target['fixed_split']) is str and target['fixed_split']==FIXED_PROVINCE_SPLITS[province] and
                type(year) is int and 2020<=year<=2025,'TARGET_INVALID')
            _need(type(index) is int and index>=0,'TARGET_INVALID')
            grid=target['source_label_grid'];native=target['target_footprint_native']
            _need(_keys(grid,{'crs','transform','width','height'}) and type(grid['crs']) is str and
                all(type(grid[k]) is int and 1<=grid[k]<=8192 for k in ('width','height')) and
                type(grid['transform']) is list and len(grid['transform'])==6 and
                all(type(v) in (int,float) and math.isfinite(v) for v in grid['transform']),'LABEL_GRID_INVALID')
            _need(_keys(native,{'crs','corners'}) and type(native['crs']) is str and type(native['corners']) is list and len(native['corners'])==4 and
                all(type(pair) is list and len(pair)==2 and all(type(v) in (int,float) and math.isfinite(v) for v in pair) for pair in native['corners']),'TARGET_GEOMETRY_MISMATCH')
        _,raw=_pinned(root,plan['proposal_ref'],2*1024**2,proposal=True);proposal=_json(raw)
        _,raw=_pinned(root,plan['current_manifest_ref'],64*1024**2);aggregate=_json(raw)
        _,raw=_pinned(root,plan['boundary_ref'],2*1024**2);boundary=_json(raw)
        from shapely.geometry import shape,Polygon
        from shapely.ops import transform as geometry_transform
        from pyproj import Transformer
        import numpy as np
        import rasterio
        from rasterio.io import MemoryFile
        from rasterio.windows import Window
        geometries={};aois={}
        _need(type(base.get('aois')) is list,'BASE_AOI_INVALID')
        for province in {t['province'] for t in plan['targets']}:
            features=[f for f in boundary['features'] if f.get('properties',{}).get('province_id')==province]
            _need(len(features)==1,'BOUNDARY_INVALID');geometries[province]=features[0]['geometry']
            matches=[a for a in base['aois'] if type(a) is dict and a.get('id')==province]
            _need(len(matches)==1,'BASE_AOI_INVALID');aois[province]=matches[0]
        # Both eligible and noneligible/history rows participate across ALL years.
        images={}
        for row in aggregate.get('scenes',[])+aggregate.get('historical_noneligible_patches',[]):
            for value,pin in ((row.get('image_path'),row.get('patch_sha256',{}).get('image')),
                (row.get('source_window',{}).get('path'),row.get('source_window',{}).get('sha256'))):
                if value is None:continue
                path=Path(value) if Path(value).is_absolute() else _relative(root,value,'image')
                _need(path.is_relative_to(root/'data') and _sha(pin),'EXISTING_IMAGE_REFERENCE_INVALID')
                key=str(path)
                if key in images:_need(images[key]['sha']==pin,'EXISTING_IMAGE_REFERENCE_INVALID');continue
                digest,raw=_snapshot(root,path,64*1024**2,'image',True)
                _need(digest==pin,'EXISTING_IMAGE_PIN_MISMATCH')
                _need(raw[:4] in (b'II*\x00',b'MM\x00*',b'II+\x00',b'MM\x00+'),'RASTER_GRID_INVALID')
                with rasterio.Env(GDAL_PAM_ENABLED='NO',GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR',GDAL_GEOREF_SOURCES='INTERNAL',PROJ_NETWORK='OFF'):
                    with MemoryFile(raw) as memory:
                        with memory.open(driver='GTiff') as ds:images[key]={'sha':pin,'crs':ds.crs,'polygon':_polygon(ds)}
        checked=[];polygons=[];jobs=[]
        for target in plan['targets']:
            province=target['province'];geometry=geometries[province]
            index=target['proposal_window_index'];_need(index<len(proposal['ranked_windows']),'PROPOSAL_MISMATCH')
            proposed=proposal['ranked_windows'][index]
            for key in ('year','province','fixed_split'):_need(type(proposed[key]) is type(target[key]) and proposed[key]==target[key],'PROPOSAL_MISMATCH')
            label_path,raw=_pinned(root,target['source_label_ref'],64*1024**2)
            _need(raw[:4] in (b'II*\x00',b'MM\x00*',b'II+\x00',b'MM\x00+'),'LABEL_GRID_INVALID')
            _need(label_path==_relative(root,proposed['source_crop_path'],'label') and target['source_label_ref']['sha256']==proposed['source_crop_sha256'],'PROPOSAL_MISMATCH')
            _,lineage_raw=_pinned(root,target['source_lineage_ref'],8*1024**2);lineage=_json(lineage_raw)
            matches=[row for row in lineage['scenes'] if row.get('source_crops',{}).get('raw-esri_io.tif',{}).get('sha256')==target['source_label_ref']['sha256']]
            _need(len(matches)==1,'LABEL_LINEAGE_INVALID');source=matches[0];year=target['year']
            crop=source['source_crops']['raw-esri_io.tif'];crop_path=Path(crop['path'])
            if not crop_path.is_absolute():crop_path=_relative(root,crop['path'],'label')
            _need(crop_path==label_path and str(source['year'])==str(year) and type(source['label_year']) is int and source['label_year']==year and
                f'/lc{year}/' in source['label_source_url'],'LABEL_YEAR_INVALID')
            window=target['source_label_window']
            _need(type(window) is list and len(window)==4 and all(type(v) is int for v in window) and window[0]>=0 and window[1]>=0 and window[2:]==[256,256],'WINDOW_INVALID')
            _need(window[:2]==proposed['local_window_xy'],'PROPOSAL_MISMATCH')
            with rasterio.Env(GDAL_PAM_ENABLED='NO',GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR',GDAL_GEOREF_SOURCES='INTERNAL',PROJ_NETWORK='OFF'):
                with MemoryFile(raw) as memory:
                    with memory.open(driver='GTiff') as ds:
                        _polygon(ds)
                        _need(ds.driver=='GTiff' and not ds.subdatasets and not ds.gcps[0] and ds.rpcs is None and
                            ds.count==1 and ds.crs.linear_units_factor[1]==1.0 and
                            ds.dtypes[0] in ('uint8','uint16','int16','int32') and ds.transform.a==10 and ds.transform.e==-10,'LABEL_GRID_INVALID')
                        _need(window[0]+256<=ds.width and window[1]+256<=ds.height,'WINDOW_INVALID')
                        expected={'crs':ds.crs.to_string(),'transform':list(ds.transform)[:6],'width':ds.width,'height':ds.height}
                        _need(target['source_label_grid']==expected,'LABEL_GRID_MISMATCH')
                        affine=ds.window_transform(Window(*window));corners=[affine*p for p in ((0,0),(256,0),(256,256),(0,256))]
                        polygon=Polygon(corners)
                        native=target['target_footprint_native']
                        _need(_keys(native,{'crs','corners'}) and native['crs']==ds.crs.to_string() and native['corners']==[list(p) for p in corners],'TARGET_GEOMETRY_MISMATCH')
                        inverse=Transformer.from_crs(ds.crs,4326,always_xy=True)
                        xy=[inverse.transform(*p) for p in corners];bbox=[min(p[0] for p in xy),min(p[1] for p in xy),max(p[0] for p in xy),max(p[1] for p in xy)]
                        supplied=target['target_bbox_wgs84']
                        _need(type(supplied) is list and len(supplied)==4 and all(type(a) in (int,float) and math.isfinite(a) and abs(a-b)<=1e-8 for a,b in zip(supplied,bbox)),'TARGET_GEOMETRY_MISMATCH')
                        values=ds.read(1,window=Window(*window));bare=int(np.count_nonzero(values==8))
                        _need(type(target['declared_bare_pixels']) is int and bare==target['declared_bare_pixels']==proposed['declared_weak_label_bare_pixels'] and bare>=256,'BARE_COUNT_MISMATCH')
                        projected_boundary=geometry_transform(Transformer.from_crs(4326,ds.crs,always_xy=True).transform,shape(geometry))
                        inside=projected_boundary.intersection(polygon).area/polygon.area
                        _need(inside>=.95,'BOUNDARY_SHORTFALL')
                        for image in images.values():
                            existing=geometry_transform(Transformer.from_crs(image['crs'],ds.crs,always_xy=True).transform,image['polygon'])
                            _need(polygon.intersection(existing).area==0,'EXISTING_IMAGE_OVERLAP')
                        for crs,other in polygons:
                            other=geometry_transform(Transformer.from_crs(crs,ds.crs,always_xy=True).transform,other)
                            _need(polygon.intersection(other).area==0,'TARGET_OVERLAP')
                        polygons.append((ds.crs,polygon))
            checked.append({'target_id':target['target_id'],'year':year,'local_bare_pixels':bare,'inside_fraction':inside,'source_label_sha256':target['source_label_ref']['sha256']})
            config=copy.deepcopy(base);aoi=copy.deepcopy(aois[province])
            aoi.update(id='bare-'+target['target_id'],province_id=province,bbox=bbox)
            config.update(aois=[aoi],years=[year],annual_reference='esri_io',window_size=256,
                bands=['blue','green','red','nir','swir16','swir22'],max_total_bytes=64*1024**2,prior_download_budget_bytes=0,
                candidate_limit=5,min_valid_fraction=.8,candidate_valid_fraction=candidate_minimum,verify_product_metadata=True,
                preserve_source_crops=True,transient_asset_retries=0,minimum_complete_scenes=1,search_limit=20,sort_by_cloud=True,
                collection_policy_version='targeted-bare-256-PLAN-ONLY')
            jobs.append({'province':province,'year':year,'split':target['fixed_split'],'nominal_patches':1,'geometry':copy.deepcopy(geometry),
                'config':config,'target_id':target['target_id'],'selection_context':{'priority_source_classes':[8]}})
        digest=hashlib.sha256(json.dumps(plan,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode()).hexdigest()
        for job in jobs:
            job['key']=f"target256-bare-{job['province']}-{job['year']}-{job['target_id']}-{digest[:12]}"
            job['config_sha256']=hashlib.sha256(json.dumps(job['config'],sort_keys=True).encode()).hexdigest()
        result.update(status='LOCAL_TARGETS_VERIFIED_EXECUTION_BLOCKED',issue='EXECUTION_GUARDS_NOT_CONNECTED',plan_sha256=digest,
            targets=checked,job_proposals=jobs,existing_images_observed=len(images),local_label_bytes_verified=True,listed_image_overlap_checked=True)
    except _Blocked as exc:result['issue']=exc.code
    except _Invalid:result['issue']='PLAN_INVALID'
    except ValueError as exc:
        code=str(exc);result['issue']=code if re.fullmatch('[A-Z_]{1,64}',code) else 'PLAN_INVALID'
    except Exception:result['issue']='LOCAL_INPUT_UNAVAILABLE'
    return result
