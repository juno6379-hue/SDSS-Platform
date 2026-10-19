"""Local additional1024 centers only; no collection or consumption approval."""
import argparse
from collections import Counter
import hashlib,json,math,os,re,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'.runtime'),str(ROOT/'backend'),str(ROOT/'scripts')]
from backend.app.data.targeted_bare_plan import _json
from backend.app.ml.per_scene_normalization_files import _root,_snapshot
from backend.app.data.candidates import validate_candidate_plan
from backend.app.ml.readiness import default_policy
from backend.app.ml.split_json_io import _local
from backend.app.ml.manifest_resource_profile import active,entry as profile_entry,pinned_source_bytes,NAME,MARKER,read_metadata,bounded_json_digest
from backend.app.ml.manifest_resource_profile import write_new_json_bytes
from collect_training_grid import spatial_centers

TARGETS=(('southeast_sulawesi',2024),('gorontalo',2024),('gorontalo',2025))
MAX_FILES=256;MAX_BYTES=2*1024**3;MAX_GRID=100000


def pinned(root,path,sha,cap,allow_config=False,json_role=None):
    path=Path(path)
    if not path.is_absolute() or not (path.resolve().is_relative_to(root/'data') or (allow_config and path.resolve().is_relative_to(root/'configs'))):raise ValueError('Explicit local input scope required')
    if active() is not None:
        if json_role=='source':return _json(pinned_source_bytes(path,sha))
        if json_role not in ('boundary','local_config','local_plan') or cap!=2*1024**2:raise ValueError('Explicit small JSON role/cap required')
        return read_metadata(path,json_role,sha)[0]
    actual,raw=_snapshot(root,path,cap,'centers182',True)
    if actual!=sha:raise ValueError('Caller pin differs')
    return _json(raw)


@profile_entry
def propose(root,source,source_sha,boundary,boundary_sha,config,config_sha,prior_plan,prior_sha,output,targets=None):
    """Write a new plan after bounded pinned local geometry checks only."""
    explicit_targets=targets is not None
    if targets is None:targets=TARGETS
    if type(targets) not in (list,tuple) or not 1<=len(targets)<=6:raise ValueError('One to six explicit target cells required')
    checked=[]
    for target in targets:
        if type(target) not in (list,tuple) or len(target)!=2:raise ValueError('Province/year pair required')
        province,year=target
        if type(province) is not str or province not in default_policy()['province_splits'] or type(year) is not int or not 2020<=year<=2025:raise ValueError('Official province and integer year2020-2025 required')
        if (province,year) in checked:raise ValueError('Duplicate target cell')
        checked.append((province,year))
    targets=tuple(checked)
    root=_root(root);output=Path(output)
    _local(output)
    _root(output.parent)
    if not output.is_absolute() or not output.resolve().is_relative_to(root/'data') or output.exists() or output.is_symlink() or not output.parent.is_dir():raise ValueError('New DATA output with existing parent required')
    pins=[(source,source_sha,64*1024**2,False,'source'),(boundary,boundary_sha,2*1024**2,False,'boundary'),(config,config_sha,2*1024**2,True,'local_config'),(prior_plan,prior_sha,2*1024**2,False,'local_plan')]
    aggregate,geo,base,prior=[pinned(root,*values) for values in pins]
    split=default_policy()['province_splits']
    features={}
    for f in geo['features']:
        p=f['properties']['province_id']
        if p in features:raise ValueError('Duplicate province boundary')
        features[p]=f['geometry']
    if set(features)!=set(split) or set(a['id'] for a in base['aois'])!=set(split) or len(base['aois'])!=6:raise ValueError('Fixed six boundaries/config AOIs required')
    if prior.get('schema_version')!=1 or prior.get('executed_network') is not False:raise ValueError('Existing local candidate plan required')
    rows=aggregate['scenes']+aggregate.get('historical_noneligible_patches',[])
    if len(rows)>3000:raise ValueError('Source row cap exceeded')
    counts=Counter((r['province'],int(r['year'])) for r in rows if r.get('quality_status')=='quality_eligible')
    import rasterio
    from rasterio.io import MemoryFile
    from rasterio.warp import transform_bounds
    from shapely.geometry import shape,box,Point
    from shapely.ops import transform as gt
    from pyproj import Transformer
    os.environ['PROJ_NETWORK']='OFF'
    blocked=[];existing=[];existing_ids=set()
    def center_block(c):
        crs=c['grid_crs'];forward=Transformer.from_crs(4326,crs,always_xy=True)
        x,y=forward.transform(c['lon'],c['lat']);blocked.append((crs,(x-5120,y-5120,x+5120,y+5120)))
        existing.append({k:c[k] for k in ('province','lon','lat','grid_crs')})
    # Recreate the exact deterministic first four v2 centers, across all years.
    for p,geometry in features.items():
        polygon=shape(geometry);rep=polygon.representative_point();epsg=(32600 if rep.y>=0 else 32700)+int((rep.x+180)//6)+1
        projected=gt(Transformer.from_crs(4326,epsg,always_xy=True).transform,polygon)
        xmin,ymin,xmax,ymax=projected.bounds
        if (math.ceil((xmax-xmin)/10400)+3)*(math.ceil((ymax-ymin)/10400)+3)>MAX_GRID:raise ValueError('Projected grid budget exceeded')
        for c in spatial_centers(geometry,4):center_block({'province':p,**c})
    validate_candidate_plan(prior_plan,boundary,existing)
    for c in prior.get('candidates',[]):
        if c.get('boundary_sha256')!=boundary_sha or c.get('window_size')!=1024 or c.get('reference')!='esri_io' or c['province'] not in split:raise ValueError('Prior candidate boundary/scope differs')
        existing_ids.add(c['spatial_window_id']);center_block(c)
    refs={}
    for row in rows:
        ref=row.get('source_window')
        if type(ref) is not dict:raise ValueError('Every source row needs source-window lineage')
        path=Path(ref['path'])
        if not path.is_absolute():path=root/path
        if not path.resolve().is_relative_to(root/'data'):raise ValueError('Local source header required')
        if path in refs and refs[path]!=ref['sha256']:raise ValueError('Conflicting source-window pin')
        refs[path]=ref['sha256']
    if len(refs)>MAX_FILES:raise ValueError('Source header file cap exceeded')
    total=0;header_inventory=[]
    with rasterio.Env(GDAL_PAM_ENABLED='NO',GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR',GDAL_GEOREF_SOURCES='INTERNAL'):
        for path,expected in sorted(refs.items()):
            if total+path.stat().st_size>MAX_BYTES:raise ValueError('Header payload byte cap exceeded')
            actual,raw=_snapshot(root,path,64*1024**2,'source_header',True)
            if actual!=expected:raise ValueError('Source-window SHA differs')
            total+=len(raw)
            with MemoryFile(raw) as mem,mem.open(driver='GTiff') as ds:
                t=ds.transform
                if ds.crs is None or not ds.crs.is_projected or abs(ds.crs.linear_units_factor[1]-1)>1e-9 or t.b or t.d or t.a<=0 or t.e>=0 or not all(math.isfinite(v) for v in ds.bounds) or ds.subdatasets or ds.gcps[0] or ds.rpcs is not None:raise ValueError('Native metric source grid required')
                blocked.append((ds.crs.to_string(),tuple(ds.bounds)))
                header_inventory.append({'path':str(path.relative_to(root)),'sha256':actual,'crs':ds.crs.to_string(),'bounds':list(ds.bounds)})
    grids={};projected_boundaries={};rejections=Counter();index={p:0 for p,_ in targets}
    for p,_ in targets:
        if p in grids:continue
        polygon=shape(features[p]);rep=polygon.representative_point();crs=f'EPSG:{(32600 if rep.y>=0 else 32700)+int((rep.x+180)//6)+1}'
        forward=Transformer.from_crs(4326,crs,always_xy=True);inverse=Transformer.from_crs(crs,4326,always_xy=True)
        projected=gt(forward.transform,polygon);projected_boundaries[p]=(crs,projected,inverse)
        interior=projected.buffer(-(10240/math.sqrt(2)+100));points=[]
        if not interior.is_empty:
            xmin,ymin,xmax,ymax=interior.bounds
            for ix in range(math.floor(xmin/10400),math.ceil(xmax/10400)+1):
                for iy in range(math.floor(ymin/10400),math.ceil(ymax/10400)+1):
                    if interior.covers(Point(ix*10400,iy*10400)):points.append((ix*10400,iy*10400))
        if len(points)>MAX_GRID:raise ValueError('Candidate center grid budget exceeded')
        rx,ry=forward.transform(rep.x,rep.y);points.sort(key=lambda xy:((xy[0]-rx)**2+(xy[1]-ry)**2,xy))
        grids[p]=points
    candidates=[];per_province=Counter()
    for _round in range(2):
        for p,year in targets:
            if len(candidates)>=4 or per_province[p]>=2 or counts[p,year]>=28:continue
            crs,province,inverse=projected_boundaries[p]
            while index[p]<len(grids[p]):
                x,y=grids[p][index[p]];index[p]+=1;window=box(x-5120,y-5120,x+5120,y+5120)
                inside=province.intersection(window).area/window.area
                if inside<.95:rejections['inside_fraction']+=1;continue
                overlap=False
                for old_crs,bounds in blocked:
                    projected=tuple(bounds) if old_crs==crs else transform_bounds(old_crs,crs,*bounds,densify_pts=1024)
                    if not all(math.isfinite(v) for v in projected):raise ValueError('Nonfinite support projection')
                    # One metre conservative padding retains source/header uncertainty.
                    if window.intersection(box(projected[0]-1,projected[1]-1,projected[2]+1,projected[3]+1)).area>0:overlap=True;break
                if overlap:rejections['existing_center_or_source_overlap']+=1;continue
                lon,lat=inverse.transform(x,y)
                identity=hashlib.sha256(json.dumps([p,year,x,y,source_sha,boundary_sha,config_sha],sort_keys=True).encode()).hexdigest()[:12]
                identifier=f'centers182-{p}-{identity}'
                if identifier in existing_ids:raise ValueError('Existing spatial ID collision')
                corners=[inverse.transform(px,py) for px,py in ((x-5120,y-5120),(x+5120,y-5120),(x+5120,y+5120),(x-5120,y+5120))]
                c={'province':p,'fixed_split':split[p],'spatial_window_id':identifier,'lon':lon,'lat':lat,'bbox':[min(a for a,b in corners),min(b for a,b in corners),max(a for a,b in corners),max(b for a,b in corners)],'window_size':1024,'grid_crs':crs,'boundary_sha256':boundary_sha,'years':[year],'reference':'esri_io','inside_fraction_native':inside,'source_snapshot_sha256':source_sha,'deficit_at_snapshot':28-counts[p,year],'class_presence_verified':False,'actual_quality_eligible':False,'execution_supported':False}
                candidates.append(c);per_province[p]+=1;existing_ids.add(identifier);blocked.append((crs,window.bounds));break
    document={'schema_version':1,'executed_network':False,'collector_consumption_approved':False,'candidates':candidates,'scope':'PINNED_LOCAL_GEOMETRY_ONLY_NOT_PENDING_SUPPORT_OR_QUALITY','source_sha256':source_sha,'boundary_sha256':boundary_sha,'config_sha256':config_sha,'prior_plan_sha256':prior_sha,'source_header_inventory':header_inventory,'limits':{'maximum_candidates':4,'maximum_per_province':2,'maximum_header_files':MAX_FILES,'maximum_header_payload_bytes':MAX_BYTES,'maximum_grid_points_per_province':MAX_GRID},'rejections':dict(rejections),'target_status':[{'province':p,'year':year,'fixed_split':split[p],'eligible_at_snapshot':counts[p,year],'deficit_to_28':max(0,28-counts[p,year]),'proposed_candidates':sum(c['province']==p and year in c['years'] for c in candidates)} for p,year in targets],'full_pending_support_inventory_verified':False,'training_ready':False,'network_requests':0}
    if active() is not None:document['manifest_profile']=dict(MARKER)
    if explicit_targets:document['requested_targets']=[{'province':p,'year':year} for p,year in targets]
    for values in pins:pinned(root,*values)
    for path,sha in refs.items():
        if _snapshot(root,path,64*1024**2,'header')[0]!=sha:raise ValueError('Source header changed')
    payload=(json.dumps(document,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf8')
    if len(payload)>2*1024**2:raise ValueError('Proposal byte cap exceeded')
    if active() is not None:write_new_json_bytes(output,payload,'evidence')
    else:
        with output.open('xb') as stream:stream.write(payload)
    validated=validate_candidate_plan(output,boundary,existing,json_role='proposal')
    if len(validated['candidates'])!=len(candidates):raise ValueError('Candidate validator disagreement')
    for values in pins:pinned(root,*values)
    actual=bounded_json_digest(output,'proposal') if active() is not None else hashlib.sha256(output.read_bytes()).hexdigest()
    if actual!=validated['source_sha256']:raise ValueError('Proposal changed')
    return document,validated


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__,allow_abbrev=False)
    for name in ('source','boundary','config','prior-plan'):
        parser.add_argument('--'+name,type=Path,required=True);parser.add_argument('--'+name+'-sha256',required=True)
    parser.add_argument('--target',action='append',help='Explicit province:year, repeat in priority order; default legacy targets')
    parser.add_argument('--manifest-profile',choices=[NAME],default=None)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args(argv)
    try:
        targets=None
        if args.target is not None:
            targets=[]
            for value in args.target:
                province,year=value.split(':')
                if not re.fullmatch(r'202[0-5]',year):raise ValueError('Target year must be2020-2025')
                targets.append((province,int(year)))
        doc,verified=propose(ROOT,args.source,args.source_sha256,args.boundary,args.boundary_sha256,args.config,args.config_sha256,args.prior_plan,args.prior_plan_sha256,args.output,targets=targets,manifest_profile=args.manifest_profile)
        print(json.dumps({'status':'LOCAL_CENTERS_PROPOSED_UNAPPROVED','candidates':len(doc['candidates']),'proposal_sha256':verified['source_sha256'],'target_status':doc['target_status'],'execution_supported':False}),flush=True);return 0
    except (ValueError,OSError,KeyError,TypeError):
        print(json.dumps({'status':'PROPOSAL_INCOMPLETE','partial_output_preserved':True,'execution_supported':False}),file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())
