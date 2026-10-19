"""Bounded, local ESRI weak-label search. Discovery never authorizes collection."""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'.runtime'),str(ROOT/'backend')]
from backend.app.data.targeted_bare_plan import _json
from backend.app.ml.per_scene_normalization_files import _root,_relative,_snapshot
from backend.app.ml.readiness import esri_reference_matches_year,default_policy
from backend.app.ml.manifest_resource_profile import active,entry as profile_entry,pinned_source_bytes,NAME,MARKER,write_new_json_bytes

LIMITS={'max_files':256,'max_total_bytes':768*1024**2,'max_windows':32768,'max_candidates':128}
SPLITS=default_policy()['province_splits']


def pin(root,path,expected,cap):
    digest,raw=_snapshot(root,path,cap,'bare173',True)
    if digest!=expected:raise ValueError('Pinned local bytes differ')
    return raw



def source_pin(root,path,expected):
    if active() is None:return pin(root,path,expected,64*1024**2)
    path=Path(path)
    if not path.is_absolute() or not path.resolve().is_relative_to(root/'data'):raise ValueError('Local DATA source required')
    return pinned_source_bytes(path,expected)

@profile_entry
def discover(root,manifest,manifest_sha,boundary,boundary_sha,*,limits=None,window_stride=256,provinces=None,label_refs=None):
    """Read only local pinned files; return candidates with execution=false."""
    root=_root(root);limits=dict(LIMITS if limits is None else limits)
    if set(limits)!=set(LIMITS) or any(type(v) is not int or not 1<=v<=LIMITS[k] for k,v in limits.items()):
        raise ValueError('Bounded positive limits required')
    if type(window_stride) is not int or window_stride not in (128,256):raise ValueError('Explicit128or256 stride required')
    if provinces is not None and (type(provinces) is not list or not provinces or any(type(p) is not str or p not in SPLITS for p in provinces) or len(set(provinces))!=len(provinces)):
        raise ValueError('Unique fixed province filter required')
    requested_labels=None
    if label_refs is not None:
        if type(label_refs) is not list or not 1<=len(label_refs)<=LIMITS['max_files']:
            raise ValueError('Explicit1to256 label references required')
        requested_labels={}
        for ref in label_refs:
            if type(ref) is not dict or ref.keys()!={'path','sha256'} or any(type(k) is not str for k in ref) or type(ref['path']) is not str or type(ref['sha256']) is not str or re.fullmatch('[a-f0-9]{64}',ref['sha256']) is None:
                raise ValueError('Exact path and SHA label reference required')
            try:path=_relative(root,ref['path'],'label_filter')
            except Exception:raise ValueError('Local DATA label filter path required') from None
            if not path.is_relative_to(root/'data') or path in requested_labels:
                raise ValueError('Unique local DATA label filter paths required')
            requested_labels[path]=ref['sha256']
    selected=set(SPLITS if provinces is None else provinces)
    manifest=Path(manifest);boundary=Path(boundary)
    for path in (manifest,boundary):
        if not path.is_absolute() or not path.resolve().is_relative_to(root/'data'):raise ValueError('Local DATA input required')
    raw=source_pin(root,manifest,manifest_sha);document=_json(raw);del raw
    geo=_json(pin(root,boundary,boundary_sha,2*1024**2))
    rows=document['scenes']+document.get('historical_noneligible_patches',[])
    if len(rows)>3000:raise ValueError('Manifest row cap exceeded')
    coverage=Counter((r['province'],int(r['year'])) for r in rows if r.get('quality_status')=='quality_eligible')
    geometries={}
    for feature in geo['features']:
        province=feature['properties']['province_id']
        if province in SPLITS:
            if province in geometries:raise ValueError('Duplicate province boundary')
            geometries[province]=feature['geometry']
    if set(geometries)!=set(SPLITS):raise ValueError('Six fixed province boundaries required')
    refs={};skipped=Counter()
    for row in rows:
        province=row.get('province');year=row.get('year')
        if type(year) is str and re.fullmatch('202[0-5]',year):year=int(year)
        if province not in SPLITS or type(year) is not int or not 2020<=year<=2025:raise ValueError('Fixed province/year required')
        if province not in selected:continue
        crop=row.get('source_window',{}).get('raw_source_crops',{}).get('raw-esri_io.tif')
        if not crop:skipped['missing_raw_label_reference']+=1;continue
        if row.get('label_source')!='esri_io' or row.get('label_year')!=year or row.get('label_source_url')!=crop.get('source') or f'/lc{year}/' not in crop.get('source','') or not esri_reference_matches_year(crop['source'],year):
            raise ValueError('Year-matched ESRI lineage required')
        path=Path(crop['path'])
        if not path.is_absolute():path=_relative(root,crop['path'],'label')
        if not path.resolve().is_relative_to(root/'data'):raise ValueError('Local DATA crop required')
        sha=crop['sha256']
        if type(sha) is not str or re.fullmatch('[a-f0-9]{64}',sha) is None:raise ValueError('Crop SHA required')
        key=str(path)
        value={'path':path,'sha256':sha,'province':province,'year':year}
        if key in refs and refs[key]!=value:raise ValueError('Conflicting raw label lineage')
        refs[key]=value
    available_label_refs=len(refs)
    if requested_labels is not None:
        indexed={Path(key):value for key,value in refs.items()}
        if any(path not in indexed or indexed[path]['sha256']!=sha for path,sha in requested_labels.items()):
            raise ValueError('Selected label ref must exactly match manifest province-scope lineage')
        refs={str(indexed[path]['path']):indexed[path] for path in requested_labels}
    if len(refs)>limits['max_files']:raise ValueError('Local label file cap exceeded')
    import numpy as np
    import rasterio
    from rasterio.io import MemoryFile
    from rasterio.windows import Window
    from shapely.geometry import shape,Polygon
    from shapely.ops import transform as transform_geometry
    from pyproj import Transformer
    candidates=[];inventory=[];total=0;windows=0;duplicates=0;seen=set();projected={}
    summaries={p:{'fixed_split':SPLITS[p],'label_files':0,'windows_scanned':0,'dense_windows':0,'dense_inside_windows':0,'maximum_bare_pixels':0} for p in SPLITS}
    os.environ['PROJ_NETWORK']='OFF'
    for item in sorted(refs.values(),key=lambda r:str(r['path'])):
        path=item['path'];sha=item['sha256'];province=item['province'];year=item['year']
        size=path.stat().st_size
        if total+size>limits['max_total_bytes']:raise ValueError('Cumulative label byte cap exceeded')
        raw=pin(root,path,sha,64*1024**2);total+=len(raw)
        inventory.append({'path':str(path.relative_to(root)),'sha256':sha,'bytes':len(raw),'province':province,'year':year})
        summaries[province]['label_files']+=1
        with rasterio.Env(GDAL_PAM_ENABLED='NO',GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR',GDAL_GEOREF_SOURCES='INTERNAL'):
            with MemoryFile(raw) as memory:
                with memory.open(driver='GTiff') as ds:
                    t=ds.transform
                    if ds.count!=1 or ds.width>8192 or ds.height>8192 or ds.crs is None or not ds.crs.is_projected or ds.crs.linear_units_factor[1]!=1.0 or t.a!=10 or t.e!=-10 or t.b!=0 or t.d!=0 or ds.dtypes[0] not in ('uint8','uint16','int16','int32'):
                        raise ValueError('Single integer 10m projected label grid required')
                    count=len(range(0,ds.width-255,window_stride))*len(range(0,ds.height-255,window_stride))
                    if windows+count>limits['max_windows']:raise ValueError('Local window cap exceeded')
                    cache=(province,ds.crs.to_string())
                    if cache not in projected:projected[cache]=transform_geometry(Transformer.from_crs(4326,ds.crs,always_xy=True).transform,shape(geometries[province]))
                    inverse=Transformer.from_crs(ds.crs,4326,always_xy=True)
                    for y in range(0,ds.height-255,window_stride):
                        for x in range(0,ds.width-255,window_stride):
                            windows+=1;summaries[province]['windows_scanned']+=1
                            key=(sha,x,y)
                            if key in seen:duplicates+=1;continue
                            seen.add(key)
                            values=ds.read(1,window=Window(x,y,256,256));bare=int(np.count_nonzero(values==8))
                            summaries[province]['maximum_bare_pixels']=max(summaries[province]['maximum_bare_pixels'],bare)
                            if bare<256:continue
                            summaries[province]['dense_windows']+=1
                            affine=ds.window_transform(Window(x,y,256,256));corners=[affine*p for p in ((0,0),(256,0),(256,256),(0,256))]
                            polygon=Polygon(corners);inside=projected[cache].intersection(polygon).area/polygon.area
                            if inside<.95:continue
                            summaries[province]['dense_inside_windows']+=1
                            xy=[inverse.transform(*p) for p in corners]
                            candidates.append({'year':year,'province':province,'fixed_split':SPLITS[province],'source_crop_path':str(path.relative_to(root)),'source_crop_sha256':sha,'local_window_xy':[x,y],'declared_weak_label_bare_pixels':bare,'bare_density':bare/65536,'cell_eligible_at_snapshot':coverage[province,year],'cell_deficit_to_28':max(0,28-coverage[province,year]),'geometric_inside_fraction':inside,'bbox_wgs84':[min(p[0] for p in xy),min(p[1] for p in xy),max(p[0] for p in xy),max(p[1] for p in xy)],'source_label_grid':{'crs':ds.crs.to_string(),'transform':list(t)[:6],'width':ds.width,'height':ds.height},'target_footprint_native':{'crs':ds.crs.to_string(),'corners':[list(p) for p in corners]},'execution_supported':False,'actual_quality_eligible':False,'scientifically_verified_bare':False,'spatial_independence_verified':False,'existing_image_overlap_checked':False,'pending_inventory_checked':False,'consumer_scope':'BANTEN_157_REVALIDATION_REQUIRED' if province=='banten' else 'PLANNED_CONSUMER_NOT_CONNECTED'})
        if _snapshot(root,path,64*1024**2,'bare173')[0]!=sha:raise ValueError('Label changed after scan')
    candidates.sort(key=lambda c:(-int(c['cell_deficit_to_28']>0),-c['declared_weak_label_bare_pixels'],-c['cell_deficit_to_28'],c['province'],c['year'],c['source_crop_sha256'],c['local_window_xy']))
    source_pin(root,manifest,manifest_sha);pin(root,boundary,boundary_sha,2*1024**2)
    result={'schema_version':1,'kind':'LOCAL_SIX_PROVINCE_WEAK_LABEL_BARE_DISCOVERY','status':'LOCAL_LABEL_BYTES_VERIFIED_EXECUTION_UNAPPROVED','source_manifest_sha256':manifest_sha,'boundary_sha256':boundary_sha,'source_row_count':len(rows),'scope':'PINNED_SNAPSHOT_EXCLUDES_LATER_COLLECTION','limits':limits,'local_label_crops_read':len(inventory),'label_bytes_read':total,'windows_scanned':windows,'duplicate_sha_windows_excluded':duplicates,'qualified_dense_inside_windows':len(candidates),'rank_policy':'cell deficit present, bare pixels descending, cell deficit descending, fixed stable ties','ranked_windows':candidates[:limits['max_candidates']],'province_summary':summaries,'split_qualified_counts':dict(Counter(c['fixed_split'] for c in candidates)),'inventory':inventory,'skipped_row_references':dict(skipped),'execution_supported':False,'actual_quality_eligible':False,'scientifically_verified_bare':False,'ready_for_training':False,'network_requests':0,'collection_executed':False,'training_executed':False,'source_files_written':0,'limitations':['Weak ESRI labels are not independent field truth.','Existing image/SCL/B02/pending/support inventory and spatial overlaps require167/170 revalidation.','Current157 consumer accepts Banten/val only; train/test candidates remain PLANNED and unconnected.','Only aligned256 windows are searched; sliding or smaller-offset windows are outside this bounded scan.']}
    if window_stride!=256 or provinces is not None or label_refs is not None:
        result.update(window_stride=window_stride,province_filter=[p for p in SPLITS if p in selected])
        for candidate in result['ranked_windows']:candidate['consumer_scope']='SIX_PROVINCE_175_176_REVALIDATION_REQUIRED'
        result['limitations'][2]='All six provinces require175/176/170 fresh final validation; discovery never authorizes dispatch.'
        result['limitations'][-1]=f'Only256windows on declared{window_stride}-pixel stride within selected provinces are searched; no arbitrary offsets.'
    if requested_labels is not None:
        result.update(label_ref_filter=[{'path':str(item['path'].relative_to(root)).replace('\\','/'),'sha256':item['sha256']}
                                       for item in sorted(refs.values(),key=lambda item:str(item['path']))],
                      label_filter_scope='ONLY_SELECTED_MANIFEST_LABEL_REFS',
                      requested_province_filter=[p for p in SPLITS if p in selected],
                      province_filter=[p for p in SPLITS if any(item['province']==p for item in refs.values())],
                      available_label_crops_in_province_scope=available_label_refs,
                      label_crops_excluded_by_filter=available_label_refs-len(refs))
    if active() is not None:result['manifest_profile']=dict(MARKER)
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__,allow_abbrev=False)
    parser.add_argument('--source',type=Path,required=True);parser.add_argument('--source-sha256',required=True)
    parser.add_argument('--boundary',type=Path,required=True);parser.add_argument('--boundary-sha256',required=True)
    parser.add_argument('--run-id',required=True)
    parser.add_argument('--window-stride',type=int,choices=(128,256),default=256)
    parser.add_argument('--province',action='append',choices=tuple(SPLITS))
    parser.add_argument('--manifest-profile',choices=[NAME],default=None)
    args=parser.parse_args(argv)
    if re.fullmatch('[a-z0-9][a-z0-9-]{0,39}',args.run_id) is None:parser.error('Safe explicit run ID required')
    return _run(args,manifest_profile=args.manifest_profile)


@profile_entry
def _run(args):
    data=ROOT/'data'/('bare173-'+args.run_id);out=ROOT/'evidence/integration'/('bare173-'+args.run_id)
    try:
        if any(p.exists() or p.is_symlink() for p in (data,out)):raise ValueError('New paths required')
        source_raw=source_pin(ROOT,args.source,args.source_sha256);boundary_raw=pin(ROOT,args.boundary,args.boundary_sha256,2*1024**2)
        data.mkdir(exist_ok=False);out.mkdir(exist_ok=False)
        for path,raw in ((data/'source.json',source_raw),(data/'boundary.geojson',boundary_raw)):
            if active() is not None:write_new_json_bytes(path,raw,'source' if path.name=='source.json' else 'evidence')
            else:
                with path.open('xb') as stream:stream.write(raw)
        result=discover(ROOT,data/'source.json',args.source_sha256,data/'boundary.geojson',args.boundary_sha256,window_stride=args.window_stride,provinces=args.province)
        proposal=out/'proposal.json'
        payload=(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf8')
        if len(payload)>2*1024**2:raise ValueError('Proposal byte cap exceeded')
        source_pin(ROOT,args.source,args.source_sha256);pin(ROOT,args.boundary,args.boundary_sha256,2*1024**2)
        if active() is not None:write_new_json_bytes(proposal,payload,'evidence')
        else:
            with proposal.open('xb') as stream:stream.write(payload)
        sha=hashlib.sha256(payload).hexdigest()
        if _snapshot(ROOT,proposal,2*1024**2,'proposal')[0]!=sha:raise ValueError('Proposal changed')
        receipt={'status':'LOCAL_DISCOVERY_COMPLETE_UNAPPROVED','at':datetime.now(timezone.utc).isoformat(),'proposal_sha256':sha,'proposal_bytes':len(payload),'source_sha256':args.source_sha256,'boundary_sha256':args.boundary_sha256,'source_original_unchanged_at_publication':True,'label_file_pins_checked_before_and_after':True,'execution_supported':False,'training_executed':False}
        if active() is not None:
            raw=(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n').replace('\n',os.linesep).encode('utf8')
            write_new_json_bytes(out/'receipt.json',raw,'receipt')
        else:
            with (out/'receipt.json').open('x',encoding='utf8') as stream:json.dump(receipt,stream,ensure_ascii=False,indent=2);stream.write('\n')
        print(json.dumps({'status':receipt['status'],'crops':result['local_label_crops_read'],'windows':result['windows_scanned'],'qualified':result['qualified_dense_inside_windows'],'split_counts':result['split_qualified_counts'],'proposal_sha256':sha}),flush=True);return 0
    except (ValueError,OSError,KeyError,TypeError):
        print(json.dumps({'status':'DISCOVERY_INCOMPLETE','partial_outputs_preserved':True,'execution_supported':False}),file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())
