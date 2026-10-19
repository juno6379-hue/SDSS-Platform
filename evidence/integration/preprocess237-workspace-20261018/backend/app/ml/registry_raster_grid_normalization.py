"""Actual GTiff header and strict cross-scene grid observations; no pixels."""
import math

from ..dataset_registry import canonical_manifest, version_key
from .model_checkpoint_manifest import _manifest
from .pinned_annual_normalization import _request
from .per_scene_normalization_contract import BAND_NAMES
from .per_scene_normalization_files import _root, _relative, _snapshot, _Blocked, MAX_IMAGE
from .registry_temporal_normalization import inspect_registry_temporal_normalization


class _RasterBlocked(Exception):
    def __init__(self,code,field):self.code,self.field=code,field


def _need(value,code,field):
    if not value:raise _RasterBlocked(code,field)


def _header(raw,names):
    _need(raw[:4] in (b'II*\x00',b'MM\x00*',b'II+\x00',b'MM\x00+'),'RASTER_FORMAT_UNSUPPORTED','image')
    try:
        import rasterio
        from rasterio.io import MemoryFile
        with rasterio.Env(GDAL_PAM_ENABLED='NO',GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR',GDAL_GEOREF_SOURCES='INTERNAL'):
            with MemoryFile(raw) as memory:
                with memory.open(driver='GTiff') as dataset:
                    _need(dataset.driver=='GTiff','RASTER_FORMAT_UNSUPPORTED','image')
                    _need(1<=dataset.width<=1024 and 1<=dataset.height<=1024 and dataset.count==6,'RASTER_HEADER_INVALID','shape')
                    _need(list(dataset.descriptions)==list(BAND_NAMES)==names,'RASTER_BAND_SIGNATURE_INVALID','band_names')
                    crs=dataset.crs
                    _need(crs is not None and crs.is_projected,'RASTER_HEADER_INVALID','crs')
                    units,factor=crs.linear_units_factor
                    _need(units.lower() in ('metre','meter','metres','meters') and factor==1.0,'RASTER_HEADER_INVALID','crs')
                    wkt=crs.to_wkt()
                    _need(type(wkt) is str and 1<=len(wkt)<=32768,'RASTER_HEADER_INVALID','crs')
                    transform=list(dataset.transform)[:6];a,b,c,d,e,f=transform
                    _need(all(math.isfinite(v) for v in transform) and a>0 and e<0 and b==0 and d==0
                          and math.isfinite(a*e) and a*e!=0,'RASTER_HEADER_INVALID','transform')
                    corners=[(a*x+b*y+c,d*x+e*y+f) for x,y in ((0,0),(dataset.width,0),(0,dataset.height),(dataset.width,dataset.height))]
                    _need(all(math.isfinite(v) for point in corners for v in point),'RASTER_HEADER_INVALID','bounds')
                    xs,ys=zip(*corners)
                    _need(min(xs)<max(xs) and min(ys)<max(ys),'RASTER_HEADER_INVALID','bounds')
                    return {'width':dataset.width,'height':dataset.height,'count':dataset.count,'crs_wkt':wkt,
                        'transform':transform,'bounds':[min(xs),min(ys),max(xs),max(ys)],'band_names':list(dataset.descriptions)}
    except _RasterBlocked:raise
    except Exception:raise _RasterBlocked('RASTER_HEADER_INVALID','image') from None


class _HeaderStore:
    def __init__(self,store,rows):
        self.store,self.rows,self.dataset_calls=store,rows,0
        self.observations=[];self.first_issue=None;self.reference=None

    @property
    def root(self):return self.store.root

    def get(self,kind,identifier):
        record=self.store.get(kind,identifier)
        if kind!='dataset_versions':return record
        position=self.dataset_calls;self.dataset_calls+=1
        if position%3:return record
        row=self.rows[position//3];ref=row['image_ref'];header=None
        try:
            key=version_key(ref['id'],ref['version'])
            _need(identifier==key and type(record) is dict and len(record)<=128 and all(type(k) is str for k in record)
                  and type(record.get('id')) is str and record['id']==key,'REGISTRY_RECORD_INVALID','image')
            try:manifest,digest=canonical_manifest(_manifest(record.get('manifest')))
            except Exception:raise _RasterBlocked('REGISTRY_RECORD_INVALID','image') from None
            _need(type(record.get('manifest_sha256')) is str and record['manifest_sha256']==digest
                  and manifest['dataset_id']==ref['id'] and manifest['version']==ref['version'] and manifest['sha256']==ref['sha256'],
                  'REGISTRY_REFERENCE_CONFLICT','image')
            _need(manifest['data_type']=='raster','REGISTRY_TYPE_MISMATCH','image')
            _need(manifest['access_class']=='PUBLIC','ACCESS_DECLARATION_BLOCKED','image')
            names=manifest['source'].get('band_names')
            _need(type(names) is list and len(names)==6 and all(type(n) is str for n in names)
                  and names==list(BAND_NAMES),'RASTER_BAND_SIGNATURE_INVALID','band_names')
            root=_root(self.root);path=_relative(root,manifest['artifact_uri'],'image')
            actual,raw=_snapshot(root,path,MAX_IMAGE,'image',True)
            _need(actual==ref['sha256'],'SHA256_MISMATCH','image')
            header=_header(raw,names)
            signature=(header['crs_wkt'],header['width'],header['height'],tuple(header['transform']))
            if self.reference is None:self.reference=signature
            _need(signature==self.reference,'RASTER_GRID_MISMATCH','grid')
            self.observations.append({'year':row['year'],'status':'MATCHED_UNVERIFIED','header':header,'issue':None})
            return {**record,'manifest':manifest}
        except (_RasterBlocked,_Blocked) as error:
            issue={'code':error.code,'field':error.field}
            self.observations.append({'year':row['year'],'status':'BLOCKED','header':header,'issue':issue})
            self.first_issue={'code':error.code,'field':error.field,'year':row['year']}
            raise


def inspect_registry_raster_grid_normalization(store,model_ref,training_report_sha256,requested_years):
    """Observe GTiff metadata/grid only; no raster values, masks or AOI truth."""
    result={'schema_version':1,'scope':'PINNED_YEARS_RASTER_GRID_READ_ONLY','status':'INVALID_INPUT','issue':None,
        'temporal_batch_observation':None,'header_observations':[],'raster_header_verified':False,
        'cross_scene_grid_verified':False,'artifact_bytes_verified':False,'registry_temporal_year_verified':False}
    result.update({key:False for key in ('registry_aoi_verified','quality_report_verified','quality_mask_verified',
        'pixel_values_verified','state_dict_verified','source_authority_verified','scientific_accuracy_validated',
        'execution_authorized','workflow_supported')})
    try:ref,rows=_request(model_ref,training_report_sha256,requested_years)
    except Exception:
        result['temporal_batch_observation']=inspect_registry_temporal_normalization(store,None,None,None)
        result['issue']={'code':'INVALID_INPUT','field':'request','year':None};return result
    proxy=_HeaderStore(store,rows)
    base=inspect_registry_temporal_normalization(proxy,ref,training_report_sha256,rows)
    result['temporal_batch_observation']=base;result['header_observations']=proxy.observations
    result['registry_temporal_year_verified']=base['registry_temporal_year_verified'] is True
    if proxy.first_issue is not None:
        result['status']='RASTER_BLOCKED';result['issue']=proxy.first_issue
    elif base['status']=='REGISTRY_YEARS_MATCHED_UNVERIFIED':
        result['status']='RASTER_GRID_MATCHED_UNVERIFIED'
        full=len(proxy.observations)==len(rows) and all(row['status']=='MATCHED_UNVERIFIED' for row in proxy.observations)
        result['raster_header_verified']=full;result['cross_scene_grid_verified']=full
        result['artifact_bytes_verified']=full and base['artifact_bytes_verified'] is True
    else:result['status']=base['status'];result['issue']=base['issue']
    return result
