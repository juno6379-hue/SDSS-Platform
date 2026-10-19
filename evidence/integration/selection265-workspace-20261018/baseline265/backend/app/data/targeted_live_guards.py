"""Live STAC scene veto and native window exclusions for one coordinator."""
from threading import Lock
from urllib.parse import urlsplit
from datetime import datetime
import copy
import math

from .targeted_scene_claims import SceneClaimRegistry
from .readiness_connectivity_witness import FIXED_PROVINCE_SPLITS


def _need(value, code):
    if not value: raise ValueError(code)


def _metric_crs(value):
    from rasterio.crs import CRS
    try:
        crs=CRS.from_user_input(value)
        valid=crs.is_projected and crs.linear_units_factor[1]==1.0
    except Exception:
        valid=False
    _need(valid,'TARGET_NATIVE_CRS_UNSUPPORTED')
    return crs


def _bounds(geometry):
    from affine import Affine
    from shapely.geometry import Polygon
    t=geometry['window_transform']
    _need(len(t)==6 and all(type(v) in (int,float) and math.isfinite(v) for v in t), 'WINDOW_GRID_INVALID')
    affine=Affine(*t)
    width,height=geometry['window_width'],geometry['window_height']
    _need(type(width) is int and type(height) is int and 1<=width<=2048 and 1<=height<=2048 and
          affine.b==affine.d==0 and affine.a>0 and affine.e<0, 'WINDOW_GRID_INVALID')
    return Polygon([affine@p for p in [(0,0),(width,0),(width,height),(0,height)]]).bounds


class TargetedWindowClaims:
    """Persistent until coordinator exits; failures never release image windows."""
    def __init__(self, assets):
        self._lock=Lock()
        self._history=[(a['crs'],a['bounds'],None) for a in assets]
        self._active=[]

    def claim(self, owner, crs, bounds):
        from shapely.geometry import box
        from rasterio.warp import transform_bounds
        from rasterio.crs import CRS
        with self._lock:
            for old_crs, old_bounds, old_owner in self._history+self._active:
                if old_owner==owner: continue
                if CRS.from_user_input(crs)==CRS.from_user_input(old_crs):
                    projected=bounds
                else:
                    p=transform_bounds(crs,old_crs,*bounds,densify_pts=1024)
                    _need(all(math.isfinite(v) for v in p), 'WINDOW_PROJECTION_INVALID')
                    margin=1e-5 if CRS.from_user_input(old_crs).is_geographic else 1.
                    projected=(p[0]-margin,p[1]-margin,p[2]+margin,p[3]+margin)
                _need(box(*projected).intersection(box(*old_bounds)).area==0, 'LIVE_SUPPORT_WINDOW_OVERLAP')
            self._active.append((crs,list(bounds),owner))


class TargetedLiveGuard:
    """Callbacks run inside the existing metered collector, never call HTTP.

    Candidate SCL reads may precede scene selection; they receive spatial checks
    but do not constitute a selected-scene claim. Labels are reusable references.
    Only a selected item's exact declared B02 URL can satisfy the B02 witness.
    """
    def __init__(self, job, target, scenes, windows):
        self.job,self.target=copy.deepcopy(job),copy.deepcopy(target)
        self.scenes,self.windows=scenes,windows
        self.selected=None;self.assets=set();self.blue=None;self.label_url=None;self.b02_checked=False

    def _binding(self):
        """Recheck fixed province/split and pinned target AOI before any pixel hook."""
        province=self.job.get('province');year=self.job.get('year')
        _need(type(province) is str and province in FIXED_PROVINCE_SPLITS and
              self.job.get('split')==FIXED_PROVINCE_SPLITS[province] and
              self.target.get('province')==province and self.target.get('fixed_split')==self.job['split'] and
              type(year) is int and 2020<=year<=2025 and
              type(self.target.get('year')) is int and self.target['year']==year,
              'TARGET_SCENE_YEAR_OR_SPLIT_INVALID')
        aois=self.job['config']['aois']
        _need(type(aois) is list and len(aois)==1 and aois[0].get('province_id')==province and
              type(aois[0].get('id')) is str and bool(aois[0]['id']) and
              aois[0].get('bbox')==self.target.get('target_bbox_wgs84'), 'TARGET_SCENE_AOI_CHANGED')
        bbox=aois[0]['bbox']
        _need(type(bbox) is list and len(bbox)==4 and all(type(v) in (int,float) and math.isfinite(v) for v in bbox) and
              -180<=bbox[0]<bbox[2]<=180 and -90<bbox[1]<bbox[3]<90,'TARGET_SCENE_AOI_CHANGED')
        _metric_crs(self.target['target_footprint_native']['crs'])
        return aois[0]

    def on_scene(self, item, aoi, year):
        planned_aoi=self._binding()
        _need(type(year) is int or (type(year) is str and year in {str(y) for y in range(2020,2026)}),
              'TARGET_SCENE_YEAR_OR_SPLIT_INVALID')
        observed=datetime.fromisoformat(item['datetime'].replace('Z','+00:00'))
        _need('T' in item['datetime'] and observed.tzinfo is not None and
              int(year)==self.job['year']==observed.year, 'TARGET_SCENE_YEAR_OR_SPLIT_INVALID')
        _need(aoi.get('id')==planned_aoi['id'] and aoi.get('province_id')==self.job['province'] and
              aoi.get('bbox')==planned_aoi['bbox'], 'TARGET_SCENE_AOI_CHANGED')
        blue=item['assets'].get('blue',item['assets'].get('B02',{})).get('href')
        _need(type(blue) is str and bool(blue), 'TARGET_B02_MISSING')
        result=self.scenes.claim({'schema_version':1,'scene_id':item['id'],
                                 'split':self.job['split'],'owner_id':self.job['key']})
        _need(result['claim'] is not None and not result['replayed'], 'TARGET_SCENE_SPLIT_OR_CLAIM_CONFLICT')
        self.selected=item['id'];self.blue=blue
        from .references import esri_annual_plan
        self.label_url=esri_annual_plan(self.job['year'],item['id'])['url']
        self.assets={a['href'] for a in item['assets'].values() if type(a) is dict and type(a.get('href')) is str}

    def on_window(self, url, geometry):
        planned_aoi=self._binding()
        _need(geometry['requested_bbox_wgs84']==planned_aoi['bbox'], 'TARGET_WINDOW_AOI_CHANGED')
        _metric_crs(geometry['crs'])
        if self.selected is not None and url==self.label_url:
            return  # Larger year-matched reference coverage may be reused.
        if self.selected is None:
            _need('scl' in urlsplit(url).path.lower(), 'SCENE_REQUIRED_BEFORE_IMAGERY')
        else:
            _need(url in self.assets, 'UNDECLARED_SELECTED_ASSET')
        bounds=_bounds(geometry)
        if url==self.blue:
            from shapely.geometry import Polygon
            _need(_metric_crs(geometry['crs'])==_metric_crs(self.target['target_footprint_native']['crs']) and
                  geometry['window_width']==geometry['window_height']==256 and
                  geometry['window_transform'][0]==10 and geometry['window_transform'][4]==-10,
                  'TARGET_B02_GRID_INVALID')
            planned=Polygon(self.target['target_footprint_native']['corners']).bounds
            _need(all(abs(a-b)<=10.000001 for a,b in zip(bounds,planned)), 'TARGET_B02_ALIGNMENT_SHORTFALL')
        self.windows.claim(self.job['key'],geometry['crs'],bounds)
        if url==self.blue:self.b02_checked=True


def scene_registry(manifest, source_sha256):
    rows=manifest['scenes']+manifest.get('historical_noneligible_patches',[])
    history=sorted({(r['scene_id'],r['split']) for r in rows if r.get('scene_id') and r.get('split')})
    return SceneClaimRegistry({'schema_version':1,'kind':'DECLARED_SCENE_SPLIT_HISTORY',
                               'source_manifest_sha256':source_sha256,
                               'scenes':[{'scene_id':scene,'split':split} for scene,split in history]})
