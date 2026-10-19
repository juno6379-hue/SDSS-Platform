"""Actual new temporary rasters from collect_windows with STAC/COG mocked only."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import rasterio
from rasterio.enums import MaskFlags
from rasterio.transform import from_origin

from scripts import collect_samples as collector

PHYSICAL = ['B02','B03','B04','B08','B11','B12']
LOGICAL = ['blue','green','red','nir','swir16','swir22']
SEMANTICS = {'schema_version':1,'kind':'binary_validity','valid_value':1,'invalid_value':0}


class CollectionRasterDeclarationsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def config(self,endpoint='planetary-computer',bands=None,**updates):
        value = {'endpoint':endpoint,'collection':'sentinel-2-l2a','bands':bands or list(LOGICAL),
            'periods':{'2021':{'start_date':'2021-06-01','end_date':'2021-09-30'}},
            'aois':[{'id':'fixture','bbox':[105,-9.1,105.1,-9]}],'window_size':4,
            'min_valid_fraction':0.25,'max_total_bytes':128*1024**2,'candidate_limit':1,
            'download_worldcover':False,'preserve_source_crops':True}
        value.update(updates); return value

    def collect(self,config=None,anomalies=False,scl=True,root=None):
        config = config or self.config()
        pc = config['endpoint'] == 'planetary-computer'
        assets = [dict(zip(LOGICAL,PHYSICAL)).get(key,key) if pc else key for key in config['bands']]
        scl_key = 'SCL' if pc else 'scl'
        item = {'id':'MOCK_S2_SCENE','datetime':'2021-07-01T00:00:00Z','cloud_cover':0,
            'license':'TESTED_SYNTHETIC','assets':{key:{'href':key} for key in assets}}
        if scl: item['assets'][scl_key] = {'href':scl_key}
        calls = []
        def read(url,bbox,pixels,max_bytes):
            calls.append(url)
            values = np.full((1,4,4),4 if url in ('SCL','scl') else 40 if url == 'labels' else 100+assets.index(url),dtype='float32')
            if anomalies and url in assets:
                index = assets.index(url)
                if index < 4: values[0,0,index] = (0,np.nan,np.inf,-np.inf)[index]
            if anomalies and url in ('SCL','scl'):
                values[0] = np.array([[4,4,4,4],[0,1,3,8],[9,10,11,4],[2,5,6,7]],dtype='float32')
            profile = {'driver':'GTiff','dtype':'float32','count':1,'height':4,'width':4,
                'crs':'EPSG:32748','nodata':0,'transform':from_origin(500000,9000000,10,10)}
            return values,profile,{'http_body_bytes':100}
        with (patch.object(collector.service,'search_stac',return_value={'items':[item]}) as search,
              patch.object(collector.service,'read_cog_window',side_effect=read),
              patch.object(collector.service,'download_asset',side_effect=AssertionError('no actual network'))):
            report = collector.collect_windows(config,root or self.root,execute=True)
        self.assertEqual(report['scenes'][0]['status'],'rgb_window_downloaded',report['scenes'][0])
        return report,report['scenes'][0],calls

    def test_pc_logical_and_earthsearch_asset_order_descriptions_actual_pixels(self):
        for endpoint,bands in (('planetary-computer',LOGICAL),('earth-search',LOGICAL),('earth-search',PHYSICAL)):
            directory = self.root/(endpoint+bands[0]); directory.mkdir()
            report,row,calls = self.collect(self.config(endpoint,list(bands)),root=directory)
            with rasterio.open(row['image_path']) as src:
                self.assertEqual(src.descriptions,tuple(PHYSICAL)); self.assertEqual(src.nodata,0)
                self.assertEqual(src.count,6)
                for index in range(6): np.testing.assert_array_equal(src.read(index+1),np.full((4,4),100+index))
            expected_assets = PHYSICAL if endpoint == 'planetary-computer' else bands
            self.assertEqual(row['bands'],list(expected_assets)); self.assertEqual(row['logical_bands'],list(bands))
            self.assertEqual(calls,list(expected_assets)+(['SCL'] if endpoint == 'planetary-computer' else ['scl']))
            self.assertEqual(report['complete_window_count'],1); self.assertEqual(report['verified_patch_count'],0)
            self.assertFalse(report['learning_ready']); self.assertFalse(row['reflectance_conversion_verified'])
            self.assertTrue(all(not item['scale_offset_applied'] for item in row['band_processing']))

    def test_unknown_and_reordered_assets_not_renamed_or_rearranged(self):
        order = ['B12','B02','custom_asset','B04','B08','B11']
        _,row,_ = self.collect(self.config('earth-search',order))
        with rasterio.open(row['image_path']) as src:
            self.assertEqual(src.descriptions,tuple(order))
            for index in range(6): self.assertTrue(np.all(src.read(index+1) == 100+index))
        self.assertEqual(row['bands'],order); self.assertNotIn('B03',row['bands'])

    def test_finite_nonzero_and_unchanged_scl_exclusions_binary_mask_all_valid(self):
        report,row,_ = self.collect(anomalies=True)
        with rasterio.open(row['quality_mask_path']) as src:
            self.assertEqual((src.count,src.dtypes,src.nodata,src.descriptions),(1,('uint8',),None,('binary_validity',)))
            self.assertEqual(src.mask_flag_enums,([MaskFlags.all_valid],))
            values = src.read(1); self.assertEqual(set(np.unique(values)),{0,1})
            np.testing.assert_array_equal(values,np.array([[0,0,0,0],[0,0,0,0],[0,0,0,1],[1,1,1,1]],dtype='uint8'))
            self.assertFalse(np.ma.getmaskarray(src.read(1,masked=True)).any())
        self.assertEqual(row['quality_mask_semantics'],SEMANTICS)
        self.assertEqual((row['pixel_count'],row['invalid_pixel_count'],row['valid_pixel_ratio']),(16,11,5/16))
        self.assertEqual(row['quality_status'],'quality_eligible'); self.assertEqual(report['quality_eligible_window_count'],1)
        with rasterio.open(row['image_path']) as src:
            self.assertTrue(np.isnan(src.read(2)[0,1])); self.assertTrue(np.isinf(src.read(3)[0,2])); self.assertEqual(src.nodata,0)
        # Source crops retain original write policy, not new assembled descriptions.
        with rasterio.open(row['source_crops']['raw-B02.tif']['path']) as src:
            self.assertEqual(src.descriptions,(None,)); self.assertEqual(src.nodata,0)

    def test_without_scl_finite_predicate_does_not_claim_cloud_verification(self):
        report,row,calls = self.collect(anomalies=True,scl=False)
        with rasterio.open(row['quality_mask_path']) as src: self.assertEqual(int(src.read(1).sum()),12)
        self.assertEqual(row['quality_status'],'quality_unverified'); self.assertEqual(row['quality_mask'],'nodata_only_cloud_unverified')
        self.assertEqual(row['valid_pixel_ratio'],12/16); self.assertEqual(report['quality_eligible_window_count'],0)
        self.assertEqual(len(calls),6); self.assertFalse(row['reflectance_conversion_verified'])

    def test_label_nodata_and_raw_label_crops_unchanged(self):
        tile = {'url':'labels','year':2021}
        with patch.object(collector.service,'worldcover_plan',return_value={'tiles':[tile]}):
            _,row,_ = self.collect(self.config(download_worldcover=True),anomalies=True)
        with rasterio.open(row['label_path']) as src:
            self.assertEqual(src.nodata,0); self.assertEqual(src.descriptions,(None,))
            label = src.read(1); self.assertEqual(int((label != 0).sum()),5); self.assertEqual(set(np.unique(label)),{0,40})
        self.assertEqual(row['label_year'],2021); self.assertEqual(row['label_dataset_version'],'WorldCover2021v200')
        self.assertEqual(row['label_status'],'worldcover_aligned_weak_labels')
        with rasterio.open(row['source_crops']['raw-worldcover.tif']['path']) as src: self.assertEqual(src.nodata,0)

    def test_resume_existing_legacy_rows_and_rasters_not_backfilled(self):
        config = self.config(); _,row,_ = self.collect(config)
        image = Path(row['image_path']); mask = Path(row['quality_mask_path'])
        # Explicit temporary legacy fixture conversion, never operating data.
        with rasterio.open(image,'r+') as dst:
            for index in range(1,7): dst.set_band_description(index,None)
        with rasterio.open(mask,'r+') as dst: dst.nodata = 0; dst.set_band_description(1,None)
        state_path = self.root/'window-state.json'; state = json.loads(state_path.read_text(encoding='utf-8'))
        state['cells']['fixture-2021']['image']['sha256'] = collector.service._sha(image)
        state['cells']['fixture-2021']['row'].pop('quality_mask_semantics')
        state_path.write_text(json.dumps(state),encoding='utf-8'); before = image.read_bytes(),mask.read_bytes()
        with patch.object(collector.service,'search_stac') as search,patch.object(collector.service,'read_cog_window') as read:
            report = collector.collect_windows(config,self.root,execute=True)
        search.assert_not_called(); read.assert_not_called()
        self.assertEqual((image.read_bytes(),mask.read_bytes()),before)
        self.assertNotIn('quality_mask_semantics',report['scenes'][0])
        with rasterio.open(mask) as src: self.assertEqual(src.nodata,0); self.assertEqual(src.descriptions,(None,))

    def test_generated_files_consumed_after_explicit_temp_metadata_and_registry_setup(self):
        from app.data.quality_report_completion import complete_quality_report
        from app.dataset_registry import register_version
        from app.ml.registered_binary_mask_values import inspect_registered_binary_mask_values
        from app.store import Store
        _,row,_ = self.collect(anomalies=True)
        common = {'schema_version':'0.2.0','version':'v1','source':{'institution':'EXPLICIT_TEST_CALLER','product':'MOCK_SCENE','license':'TEST_ONLY'},
            'data_type':'raster','spatial':{'crs':'EPSG:4326','bbox':[105,-9.1,105.1,-9]},
            'temporal':{'start':'2021-07-01T00:00:00Z','end':'2021-07-01T00:00:00Z','calendar':'gregorian'},
            'quality_status':'RAW','access_class':'PUBLIC','lineage':[]}
        manifests = []
        for name,path in (('image',row['image_path']),('mask',row['quality_mask_path'])):
            manifest = copy.deepcopy(common); manifest.update(dataset_id=name,artifact_uri=Path(path).relative_to(self.root).as_posix(),sha256=collector.service._sha(Path(path)))
            manifests.append(manifest)
        manifests[0]['source']['band_names'] = list(PHYSICAL)
        manifests[1]['source']['mask_semantics'] = copy.deepcopy(row['quality_mask_semantics'])
        metadata = {key:copy.deepcopy(common[key]) for key in ('source','spatial','temporal','quality_status','access_class')}
        complete = complete_quality_report(*manifests,{'id':'quality','version':'v1','artifact_uri':'quality.json'},metadata)
        (self.root/'quality.json').write_bytes(complete['report_bytes'])
        store = Store(self.root)
        for manifest in (complete['image_manifest_draft'],complete['mask_manifest_draft'],complete['report_manifest_draft']): register_version(store,manifest)
        before = {p.relative_to(self.root).as_posix():p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        refs = complete['fixed_refs']; result = inspect_registered_binary_mask_values(store,refs['image_ref'],refs['quality_report_ref'],refs['mask_ref'])
        self.assertEqual(result['status'],'REGISTERED_BINARY_MASK_VALUES_MATCHED_UNVERIFIED')
        self.assertEqual(result['counts'],{'valid_pixels':5,'invalid_pixels':11,'total_pixels':16})
        self.assertFalse(result['execution_authorized']); self.assertFalse(result['scientific_accuracy_validated'])
        self.assertEqual(before,{p.relative_to(self.root).as_posix():p.read_bytes() for p in self.root.rglob('*') if p.is_file()})


if __name__ == '__main__': unittest.main()
