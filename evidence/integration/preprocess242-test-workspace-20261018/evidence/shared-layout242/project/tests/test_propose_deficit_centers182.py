"""Synthetic local source-header and official-shape style geometry fixtures."""
import hashlib,json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import numpy as np
import rasterio
from rasterio.transform import from_origin
from pyproj import Transformer
from scripts import propose_deficit_centers182 as subject


class DeficitCenters182Tests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.data=self.root/'data';self.data.mkdir()
        self.source=self.data/'source.json';self.boundary=self.data/'boundary.geojson';self.config=self.data/'config.json';self.prior=self.data/'prior.json';self.output=self.data/'new.json'
        # Disjoint synthetic polygons around the target provinces; no operating data.
        centers={'south_sulawesi':(119,-5),'gorontalo':(123,.5),'southeast_sulawesi':(122,-4),'banten':(106,-6),'west_java':(108,-7),'east_java':(113,-8)}
        features=[]
        for p,(x,y) in centers.items():
            features.append({'type':'Feature','properties':{'province_id':p},'geometry':{'type':'Polygon','coordinates':[[[x-.8,y-.8],[x+.8,y-.8],[x+.8,y+.8],[x-.8,y+.8],[x-.8,y-.8]]]}})
        self.boundary.write_text(json.dumps({'type':'FeatureCollection','features':features}),encoding='utf8')
        self.config.write_text(json.dumps({'aois':[{'id':p} for p in centers]}),encoding='utf8')
        self.prior.write_text(json.dumps({'schema_version':1,'executed_network':False,'collector_consumption_approved':False,'candidates':[]}),encoding='utf8')
        self.rows=[];self.source.write_text('{"scenes":[]}',encoding='utf8')

    def sha(self,p):return hashlib.sha256(p.read_bytes()).hexdigest()

    def run_proposal(self,**overrides):
        self.source.write_text(json.dumps({'scenes':self.rows}),encoding='utf8')
        values={'root':self.root,'source':self.source,'source_sha':self.sha(self.source),'boundary':self.boundary,'boundary_sha':self.sha(self.boundary),'config':self.config,'config_sha':self.sha(self.config),'prior_plan':self.prior,'prior_sha':self.sha(self.prior),'output':self.output}
        values.update(overrides);return subject.propose(**values)

    def test_deterministic_bounded_candidates_pass_existing_validator(self):
        first,checked=self.run_proposal()
        self.assertEqual(len(first['candidates']),4)
        self.assertEqual([c['province'] for c in first['candidates']],['southeast_sulawesi','gorontalo','gorontalo','southeast_sulawesi'])
        self.assertEqual([c['years'] for c in first['candidates']],[[2024],[2024],[2025],[2024]])
        self.assertTrue(all(c['inside_fraction_native']>=.95 and c['fixed_split']=='train' for c in first['candidates']))
        self.assertFalse(first['collector_consumption_approved']);self.assertTrue(checked['validated_spatial_only'])
        second,_=self.run_proposal(output=self.data/'again.json')
        self.assertEqual(first,second)

    def test_explicit_cells_preserve_requested_order_and_years(self):
        targets=[('southeast_sulawesi',2021),('gorontalo',2022)]
        doc,_=self.run_proposal(targets=targets)
        self.assertEqual([(c['province'],c['years'][0]) for c in doc['candidates']],targets*2)
        self.assertEqual(doc['requested_targets'],[{'province':p,'year':y} for p,y in targets])
        self.assertFalse(doc['collector_consumption_approved'])
        self.assertFalse(doc['full_pending_support_inventory_verified'])

    def test_explicit_default_matches_legacy_candidates(self):
        legacy,_=self.run_proposal()
        explicit,_=self.run_proposal(output=self.data/'explicit.json',targets=subject.TARGETS)
        self.assertNotIn('requested_targets',legacy)
        explicit.pop('requested_targets')
        self.assertEqual(legacy,explicit)

    def test_invalid_explicit_cells_refuse_before_input_read(self):
        invalid=[[],[('gorontalo',True)],[('unknown',2024)],[('gorontalo',2019)],
                 [('gorontalo','2024')],[('gorontalo',2024),('gorontalo',2024)],
                 [('gorontalo',2024,1)],'gorontalo:2024']
        for targets in invalid:
            with self.subTest(targets=targets),patch.object(subject,'pinned',side_effect=AssertionError('must reject first')):
                with self.assertRaises(ValueError):self.run_proposal(targets=targets)
        self.assertFalse(self.output.exists())

    def test_stale_source_pin_refuses_before_output(self):
        with self.assertRaises(ValueError):self.run_proposal(source_sha='0'*64)
        self.assertFalse(self.output.exists())

    def test_existing_output_not_overwritten(self):
        self.output.write_bytes(b'existing')
        with self.assertRaises(ValueError):self.run_proposal()
        self.assertEqual(self.output.read_bytes(),b'existing')

    def test_covered_target_not_proposed(self):
        image=self.data/'image.tif'
        with rasterio.open(image,'w',driver='GTiff',width=16,height=16,count=1,dtype='uint8',crs='EPSG:32751',transform=from_origin(500000,9600000,10,10)) as ds:ds.write(np.zeros((16,16),dtype='uint8'),1)
        self.rows=[{'province':'southeast_sulawesi','year':'2024','quality_status':'quality_eligible','source_window':{'path':str(image),'sha256':self.sha(image)}} for _ in range(28)]
        doc,_=self.run_proposal()
        self.assertFalse(any(c['province']=='southeast_sulawesi' for c in doc['candidates']))
        self.assertEqual(len(doc['candidates']),2)
        self.assertEqual(doc['target_status'][0]['deficit_to_28'],0)

    def test_actual_source_header_excludes_same_window_all_years(self):
        first,_=self.run_proposal();c=first['candidates'][0]
        x,y=Transformer.from_crs(4326,c['grid_crs'],always_xy=True).transform(c['lon'],c['lat'])
        image=self.data/'source-image.tif'
        with rasterio.open(image,'w',driver='GTiff',width=1024,height=1024,count=1,dtype='uint8',crs=c['grid_crs'],transform=from_origin(x-5120,y+5120,10,10)) as ds:ds.write(np.zeros((1024,1024),dtype='uint8'),1)
        self.rows=[{'province':c['province'],'year':'2020','quality_status':'quality_insufficient','source_window':{'path':str(image),'sha256':self.sha(image)}}]
        new,_=self.run_proposal(output=self.data/'with-source.json')
        self.assertNotIn((c['lon'],c['lat']),[(r['lon'],r['lat']) for r in new['candidates']])
        self.assertGreater(new['rejections']['existing_center_or_source_overlap'],0)

    def test_prior_candidate_not_reused(self):
        first,_=self.run_proposal();c=first['candidates'][0]
        self.prior.write_text(json.dumps({'schema_version':1,'executed_network':False,'candidates':[c]}),encoding='utf8')
        new,_=self.run_proposal(output=self.data/'with-prior.json')
        self.assertNotIn(c['spatial_window_id'],[r['spatial_window_id'] for r in new['candidates']])
        self.assertNotIn((c['lon'],c['lat']),[(r['lon'],r['lat']) for r in new['candidates']])

    def test_prior_plan_must_pass_existing_year_contract(self):
        first,_=self.run_proposal();c=first['candidates'][0];c['years']=[2019]
        self.prior.write_text(json.dumps({'schema_version':1,'executed_network':False,'candidates':[c]}),encoding='utf8')
        with self.assertRaises(ValueError):self.run_proposal(output=self.data/'bad-prior.json')
        self.assertFalse((self.data/'bad-prior.json').exists())

    def test_scope_and_header_caps_fail_closed(self):
        self.config.write_text('{"aois":[]}',encoding='utf8')
        with self.assertRaises(ValueError):self.run_proposal()
        self.assertFalse(self.output.exists())
        self.config.write_text(json.dumps({'aois':[{'id':p} for p in subject.default_policy()['province_splits']]}),encoding='utf8')
        self.rows=[{'province':'southeast_sulawesi','year':'2024','source_window':{'path':str(self.data/'missing.tif'),'sha256':'0'*64}}]
        with patch.object(subject,'MAX_FILES',0),self.assertRaisesRegex(ValueError,'file cap'):self.run_proposal()
        with patch.object(subject,'MAX_GRID',1),self.assertRaisesRegex(ValueError,'grid budget'):self.run_proposal()

    def test_input_bytes_preserved_and_network_flags_false(self):
        before={p:self.sha(p) for p in (self.boundary,self.config,self.prior)}
        configs=self.root/'configs';configs.mkdir();official=configs/'first-group.collection.json';official.write_bytes(self.config.read_bytes())
        doc,_=self.run_proposal(config=official,config_sha=self.sha(official))
        self.assertEqual(before,{p:self.sha(p) for p in before})
        self.assertEqual(doc['network_requests'],0)
        self.assertFalse(doc['full_pending_support_inventory_verified'])
        self.assertFalse(doc['training_ready'])


if __name__=='__main__':unittest.main()
