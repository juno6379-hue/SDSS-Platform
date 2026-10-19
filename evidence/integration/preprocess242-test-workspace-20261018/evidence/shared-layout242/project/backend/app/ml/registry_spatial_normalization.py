"""Post-read Registry bbox containment of a sampled WGS84 raster envelope."""
import math

from ..dataset_registry import canonical_manifest,version_key
from .model_checkpoint_manifest import _manifest
from .pinned_annual_normalization import _request
from .registry_raster_grid_normalization import inspect_registry_raster_grid_normalization

TOLERANCE_DEGREES=1e-7
POLAR_LIMIT=85.0


class _SpatialBlocked(Exception):
    def __init__(self,code,field):self.code,self.field=code,field


def _need(value,code,field):
    if not value:raise _SpatialBlocked(code,field)


def _bounds(value,field,geographic):
    _need(type(value) in (list,tuple) and len(value)==4 and all(type(v) in (int,float) and math.isfinite(v) for v in value),
          'SPATIAL_BOUNDS_INVALID',field)
    left,bottom,right,top=value
    if geographic:
        _need(-180<=left<=180 and -180<=right<=180 and -90<=bottom<=90 and -90<=top<=90,'SPATIAL_BOUNDS_INVALID',field)
        _need(left<=right and left>-180 and right<180 and right-left<=180,'SPATIAL_DATELINE_UNSUPPORTED',field)
        _need(abs(bottom)<POLAR_LIMIT and abs(top)<POLAR_LIMIT,'SPATIAL_POLAR_UNSUPPORTED',field)
    _need(left<right and bottom<top,'SPATIAL_BOUNDS_INVALID',field)
    return list(value)


def _envelope(header):
    bounds=_bounds(header['bounds'],'raster_bounds',False)
    try:
        import pyproj.network
        # Read only: do not mutate a process/thread's PROJ network preference.
        _need(not pyproj.network.is_network_enabled(),'SPATIAL_TRANSFORM_UNAVAILABLE','transform')
        import rasterio
        from rasterio.warp import transform_bounds
        with rasterio.Env(PROJ_NETWORK='OFF'):
            result=transform_bounds(header['crs_wkt'],'OGC:CRS84',*bounds,densify_pts=21)
    except _SpatialBlocked:raise
    except Exception:raise _SpatialBlocked('SPATIAL_TRANSFORM_UNAVAILABLE','transform') from None
    return _bounds(result,'raster_wgs84_envelope',True)


class _SpatialStore:
    def __init__(self,store,rows):
        self.store,self.rows,self.dataset_calls=store,rows,0
        self.spatial={};self.first_issue=None

    @property
    def root(self):return self.store.root

    def get(self,kind,identifier):
        record=self.store.get(kind,identifier)
        if kind!='dataset_versions':return record
        position=self.dataset_calls;self.dataset_calls+=1
        if position%3:return record
        row=self.rows[position//3];ref=row['image_ref']
        try:
            key=version_key(ref['id'],ref['version'])
            _need(identifier==key and type(record) is dict and len(record)<=128 and all(type(k) is str for k in record)
                  and type(record.get('id')) is str and record['id']==key,'REGISTRY_CAPTURE_INVALID','image')
            try:manifest,digest=canonical_manifest(_manifest(record.get('manifest')))
            except Exception:raise _SpatialBlocked('REGISTRY_CAPTURE_INVALID','image') from None
            _need(type(record.get('manifest_sha256')) is str and record['manifest_sha256']==digest
                  and manifest['dataset_id']==ref['id'] and manifest['version']==ref['version'] and manifest['sha256']==ref['sha256'],
                  'REGISTRY_REFERENCE_CONFLICT','image')
            self.spatial[row['year']]={'crs':manifest['spatial']['crs'],'bbox':list(manifest['spatial']['bbox'])}
            return {**record,'manifest':manifest}
        except _SpatialBlocked as error:
            self.first_issue={'code':error.code,'field':error.field,'year':row['year']};raise


def inspect_registry_spatial_normalization(store,model_ref,training_report_sha256,requested_years):
    """No extra asset/header reads; spatial math happens after full129 success.

    A later spatial NOT_CHECKED row may already have had all file I/O completed.
    The sampled envelope is not a guaranteed bound for the exact footprint.
    """
    result={'schema_version':1,'scope':'PINNED_YEARS_REGISTRY_ENVELOPE_READ_ONLY','status':'INVALID_INPUT','issue':None,
        'raster_batch_observation':None,'spatial_observations':[],'registry_bbox_contains_raster_envelope_verified':False,
        'artifact_bytes_verified':False}
    result.update({field:False for field in ('registry_aoi_verified','physical_coverage_verified','quality_report_verified',
        'quality_mask_verified','pixel_values_verified','source_authority_verified','scientific_accuracy_validated',
        'execution_authorized','workflow_supported')})
    try:ref,rows=_request(model_ref,training_report_sha256,requested_years)
    except Exception:
        result['raster_batch_observation']=inspect_registry_raster_grid_normalization(store,None,None,None)
        result['issue']={'code':'INVALID_INPUT','field':'request','year':None};return result
    result['spatial_observations']=[{'year':row['year'],'status':'NOT_CHECKED','registry_bbox':None,'raster_wgs84_envelope':None,'issue':None} for row in rows]
    proxy=_SpatialStore(store,rows)
    base=inspect_registry_raster_grid_normalization(proxy,ref,training_report_sha256,rows)
    result['raster_batch_observation']=base
    if proxy.first_issue is not None:
        result['status']='SPATIAL_BLOCKED';result['issue']=proxy.first_issue
        row=next(row for row in result['spatial_observations'] if row['year']==proxy.first_issue['year'])
        row.update(status='BLOCKED',issue={key:proxy.first_issue[key] for key in ('code','field')})
        return result
    if base['status']!='RASTER_GRID_MATCHED_UNVERIFIED':
        result['status']=base['status'];result['issue']=base['issue'];return result
    for output,header_observation in zip(result['spatial_observations'],base['header_observations']):
        try:
            declaration=proxy.spatial[output['year']]
            _need(declaration['crs'] in ('EPSG:4326','OGC:CRS84'),'REGISTRY_SPATIAL_CRS_UNSUPPORTED','crs')
            bbox=_bounds(declaration['bbox'],'registry_bbox',True);output['registry_bbox']=bbox
            envelope=_envelope(header_observation['header']);output['raster_wgs84_envelope']=envelope
            t=TOLERANCE_DEGREES
            _need(bbox[0]<=envelope[0]+t and bbox[1]<=envelope[1]+t and bbox[2]>=envelope[2]-t and bbox[3]>=envelope[3]-t,
                  'REGISTRY_BBOX_DOES_NOT_CONTAIN_ENVELOPE','containment')
            output['status']='MATCHED_UNVERIFIED'
        except Exception as error:
            issue={'code':error.code,'field':error.field} if isinstance(error,_SpatialBlocked) else {'code':'SPATIAL_TRANSFORM_UNAVAILABLE','field':'transform'}
            output.update(status='BLOCKED',issue=issue)
            result['status']='SPATIAL_BLOCKED';result['issue']={**issue,'year':output['year']}
            return result
    result['status']='REGISTRY_ENVELOPE_MATCHED_UNVERIFIED'
    result['registry_bbox_contains_raster_envelope_verified']=True
    result['artifact_bytes_verified']=base['artifact_bytes_verified'] is True
    return result
