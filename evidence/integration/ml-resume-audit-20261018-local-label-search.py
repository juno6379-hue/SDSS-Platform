"""Find weak-label bare pixels in already downloaded Banten crops. No HTTP."""
import os
os.environ['PROJ_NETWORK']='OFF'
os.environ['GDAL_PAM_ENABLED']='NO'
import hashlib,json
from pathlib import Path
import rasterio
import numpy as np
from rasterio.windows import Window,bounds
from rasterio.warp import transform_bounds
from shapely.geometry import box,shape
from shapely.ops import transform
from pyproj import Transformer
ROOT=Path(__file__).resolve().parents[2]
source=ROOT/'data/first-group-training-esri-v1/annual-window-report.json'
raw=source.read_bytes();pin=hashlib.sha256(raw).hexdigest()
assert pin=='cdc374b2779dee749b57689fd90ef27e3525a48e59062343537327d0f4859a8f'
rows=json.loads(raw)['scenes']
boundary=ROOT/'data/first-group-boundaries/selected-six.geojson'
feature=next(f for f in json.loads(boundary.read_text(encoding='utf-8'))['features'] if f['properties']['province_id']=='banten')
polygon=transform(Transformer.from_crs(4326,32748,always_xy=True).transform,shape(feature['geometry']))
unique={};existing={}
for row in rows:
    sw=row.get('source_window',{});crop=sw.get('raw_source_crops',{}).get('raw-esri_io.tif')
    if row['province']=='banten' and crop:unique.setdefault(crop['path'],{'crop':crop,'year':int(row['year'])})
    if row['province']=='banten':
        b02=sw.get('raw_source_crops',{}).get('raw-B02.tif',{}).get('metadata',{})
        if b02.get('bounds'):existing[tuple(b02['bounds'])]=box(*b02['bounds'])
found=[];inventory=[]
for path,item in sorted(unique.items()):
    crop=item['crop'];path=Path(path);sha=hashlib.sha256(path.read_bytes()).hexdigest()
    assert sha==crop['sha256']
    with rasterio.open(path) as ds:
        assert ds.crs.to_epsg()==32748
        values=ds.read(1)
        inventory.append({'path':str(path.relative_to(ROOT)),'sha256':sha,'year':item['year'],'bare_pixels_in_expanded_crop':int(np.count_nonzero(values==8))})
        for y in range(0,ds.height-255,256):
            for x in range(0,ds.width-255,256):
                count=int(np.count_nonzero(values[y:y+256,x:x+256]==8))
                if count<256:continue
                bb=bounds(Window(x,y,256,256),ds.transform);footprint=box(*bb)
                inside=polygon.intersection(footprint).area/footprint.area
                if inside<.95:continue
                xx=(bb[0]+bb[2])/2;yy=(bb[1]+bb[3])/2
                future=box(xx-5120,yy-5120,xx+5120,yy+5120)
                found.append({'year':item['year'],'province':'banten','fixed_split':'val','source_crop_path':str(path.relative_to(ROOT)),'source_crop_sha256':sha,'local_window_xy':[x,y],'bbox_wgs84':list(transform_bounds(ds.crs,4326,*bb)),'declared_weak_label_bare_pixels':count,'geometric_inside_fraction':inside,'patch_overlaps_existing_imagery':any(footprint.intersection(p).area>0 for p in existing.values()),'centered_1024_window_overlaps_existing_imagery':any(future.intersection(p).area>0 for p in existing.values()),'same_year_clear_sentinel_selected':False,'actual_quality_eligible':False,'scientifically_verified_bare':False})
    assert hashlib.sha256(path.read_bytes()).hexdigest()==sha
found.sort(key=lambda row:(row['patch_overlaps_existing_imagery'],-row['declared_weak_label_bare_pixels'],row['year']))
result={'schema_version':1,'kind':'LOCAL_EXPANDED_BANTEN_WEAK_LABEL_SEARCH','status':'VERIFIED_REAL_LOCAL_LABEL_BYTES_NOT_IMAGE_OR_SCIENTIFIC_QA','source_manifest_sha256':pin,'boundary_sha256':hashlib.sha256(boundary.read_bytes()).hexdigest(),'local_label_crops_read':len(inventory),'inventory':inventory,'windows_with_256_bare_and_95_percent_inside':len(found),'windows_outside_existing_imagery':sum(not r['patch_overlaps_existing_imagery'] for r in found),'windows_suitable_for_existing_nonoverlapping_1024_candidate_contract':sum(not r['centered_1024_window_overlaps_existing_imagery'] for r in found),'ranked_windows':found,'network_requests':0,'collection_executed':False,'training_executed':False,'source_files_written':0,'ready_for_training':False,'limitations':['Actual local ESRI weak-label pixels read and pinned, but no Sentinel quality or class-label truth verified.','256 windows outside imagery may still overlap an existing source when expanded to a 1024 collection window. Do not pass as compliant lane-B plan.','New aligned 256-target collection/dedup integration or farther spatial candidates must be implemented and validated before collection.','Same locations across years remain repeated locations.','Initial exploratory console output failed CP949 on an en dash; it wrote no evidence or data. This script uses ASCII stdout and evidence JSON.']}
output=ROOT/'evidence/integration/ml-resume-audit-20261018-local-banten-label-search.json'
with output.open('x',encoding='utf-8') as stream:json.dump(result,stream,ensure_ascii=False,indent=2,allow_nan=False);stream.write('\n')
assert hashlib.sha256(source.read_bytes()).hexdigest()==pin
print(json.dumps({k:result[k] for k in ['local_label_crops_read','windows_with_256_bare_and_95_percent_inside','windows_outside_existing_imagery','windows_suitable_for_existing_nonoverlapping_1024_candidate_contract']},ensure_ascii=True))
