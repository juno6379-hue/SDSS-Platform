"""Real tiny local GTiff discovery; no HTTP, image selection, or authorization."""
import hashlib,json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import numpy as np
import rasterio
from rasterio.transform import from_origin
from scripts import find_bare_targets173 as subject


class BareTargets173Tests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.data=self.root/'data';self.data.mkdir()
        self.source=self.data/'source.json';self.boundary=self.data/'boundary.geojson'
        self.geo={'type':'FeatureCollection','features':[{'type':'Feature','properties':{'province_id':p},'geometry':{'type':'Polygon','coordinates':[[[-1,-1],[1,-1],[1,1],[-1,1],[-1,-1]]]}} for p in subject.SPLITS]}
        self.boundary.write_text(json.dumps(self.geo),encoding='utf8')
        self.crop=self.data/'label.tif';self.make_crop(self.crop,256)
        self.rows=[self.row(self.crop)]

    def digest(self,path):return hashlib.sha256(path.read_bytes()).hexdigest()

    def make_crop(self,path,bare,width=256):
        values=np.ones((256,width),dtype='uint8');values.reshape(-1)[:bare]=8
        with rasterio.open(path,'w',driver='GTiff',width=width,height=256,count=1,dtype='uint8',crs='EPSG:3857',transform=from_origin(0,2560,10,10)) as ds:ds.write(values,1)

    def row(self,path,province='banten',year=2020):
        url=f'https://example.invalid/lc{year}/51N_{year}0101-{year+1}0101.tif'
        return {'province':province,'year':year,'label_year':year,'label_source':'esri_io','label_source_url':url,'quality_status':'quality_insufficient','source_window':{'raw_source_crops':{'raw-esri_io.tif':{'path':str(path),'sha256':self.digest(path),'source':url}}}}

    def scan(self,limits=None):
        self.source.write_text(json.dumps({'scenes':self.rows}),encoding='utf8')
        return subject.discover(self.root,self.source,self.digest(self.source),self.boundary,self.digest(self.boundary),limits=limits)

    def test_native_threshold_and_false_approval(self):
        result=self.scan();self.assertEqual(result['qualified_dense_inside_windows'],1)
        candidate=result['ranked_windows'][0]
        self.assertEqual(candidate['declared_weak_label_bare_pixels'],256)
        self.assertEqual(candidate['local_window_xy'],[0,0])
        self.assertFalse(candidate['execution_supported']);self.assertFalse(candidate['actual_quality_eligible'])
        self.assertFalse(result['ready_for_training'])

    def test_below_threshold_is_not_dense(self):
        self.make_crop(self.crop,255);self.rows=[self.row(self.crop)]
        self.assertEqual(self.scan()['qualified_dense_inside_windows'],0)

    def test_year_mismatch_rejected(self):
        self.rows[0]['label_year']=2021
        with self.assertRaises(ValueError):self.scan()

    def test_stale_crop_pin_rejected(self):
        self.make_crop(self.crop,65536)
        with self.assertRaises(ValueError):self.scan()

    def test_duplicate_sha_window_excluded(self):
        other=self.data/'copy.tif';other.write_bytes(self.crop.read_bytes())
        self.rows.append(self.row(other))
        result=self.scan();self.assertEqual(result['qualified_dense_inside_windows'],1)
        self.assertEqual(result['duplicate_sha_windows_excluded'],1)

    def test_byte_and_window_caps_rejected(self):
        limits={**subject.LIMITS,'max_total_bytes':1}
        with self.assertRaises(ValueError):self.scan(limits)
        self.make_crop(self.crop,65536,width=512);self.rows=[self.row(self.crop)]
        with self.assertRaises(ValueError):self.scan({**subject.LIMITS,'max_windows':1})

    def test_inside_fraction_filters_and_missing_boundary_rejects(self):
        self.geo['features']=[{**f,'geometry':{'type':'Polygon','coordinates':[[[20,20],[21,20],[21,21],[20,21],[20,20]]]}} for f in self.geo['features']]
        self.boundary.write_text(json.dumps(self.geo),encoding='utf8')
        self.assertEqual(self.scan()['qualified_dense_inside_windows'],0)
        self.geo['features'].pop();self.boundary.write_text(json.dumps(self.geo),encoding='utf8')
        with self.assertRaises(ValueError):self.scan()

    def test_priority_gap_then_density_and_train_unconnected(self):
        dense=self.data/'dense.tif';self.make_crop(dense,65536)
        self.rows=[self.row(dense,'south_sulawesi'),self.row(self.crop,'banten')]
        # South Sulawesi's plan cell is already at28; Banten remains empty.
        self.rows += [{**self.row(dense,'south_sulawesi'),'quality_status':'quality_eligible'} for _ in range(28)]
        result=self.scan();self.assertEqual(result['ranked_windows'][0]['province'],'banten')
        train=next(r for r in result['ranked_windows'] if r['province']=='south_sulawesi')
        self.assertEqual(train['consumer_scope'],'PLANNED_CONSUMER_NOT_CONNECTED')

    def test_local_files_unchanged(self):
        # Collector's aggregate uses exact four-digit year strings.
        self.rows[0]['year']='2020'
        pins={p:self.digest(p) for p in (self.crop,self.boundary)}
        result=self.scan()
        self.assertEqual(result['network_requests'],0)
        self.assertEqual(pins,{p:self.digest(p) for p in pins})
        self.assertEqual(list(self.data.glob('*.aux.xml')),[])


if __name__=='__main__':unittest.main()
