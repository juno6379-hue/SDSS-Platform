"""Metadata-only patch changes with real temporary GeoTIFF and pinned legacy comparison."""
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import types
import unittest
from unittest.mock import patch

import numpy as np
import rasterio
from rasterio.transform import from_origin

from scripts import collect_training_grid as grid

BASELINE = 'a3f4a94a69ad0f5c54a9af76bf6af82053e1a419'
NAMES = ('B02','B03','B04','B08','B11','B12')
SCENE = {'schema_version':1,'kind':'binary_validity','valid_value':1,'invalid_value':0}
SUPPORT = {'schema_version':1,'kind':'training_support','valid_value':1,'invalid_value':0}


class GridPatchDeclarationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[1]
        original = subprocess.run(['git','show',BASELINE+':scripts/collect_training_grid.py'],cwd=root,
            capture_output=True,check=True).stdout.decode('utf-8')
        cls.legacy = types.ModuleType('grid145_legacy')
        cls.legacy.__file__ = str(root/'scripts/collect_training_grid.py')
        exec(compile(original,cls.legacy.__file__,'exec'),cls.legacy.__dict__)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        boundary = self.root/'data/first-group-boundaries/selected-six.geojson'; boundary.parent.mkdir(parents=True)
        boundary.write_text('{"type":"FeatureCollection","features":[]}',encoding='utf-8')
        self.batch = {'province':'banten','split':'val','key':'grid-banten-2021-g00',
            'geometry':{'type':'Polygon','coordinates':[[[100,-20],[120,-20],[120,0],[100,0],[100,-20]]]}}

    def source(self,names=NAMES,width=512,height=256,anomalies=False):
        values = np.stack([np.full((height,width),100+index,dtype='float32') for index in range(len(names))])
        labels = np.full((height,width),10,dtype='uint8'); quality = np.ones((height,width),dtype='uint8')
        if anomalies:
            labels[0,0] = 0; quality[0,1] = 0; values[0,0,2] = 0; values[1,0,3] = np.nan
        profile = {'driver':'GTiff','width':width,'height':height,'crs':'EPSG:32748',
            'transform':from_origin(500000,9000000,10,10)}
        for name,data in (('image',values),('label',labels[None]),('quality',quality[None])):
            with rasterio.open(self.root/(name+'.tif'),'w',**{**profile,'count':len(data),'dtype':data.dtype,'nodata':None if name == 'quality' else 0}) as dst:
                dst.write(data)
                if name == 'image':
                    for index,value in enumerate(names,1):
                        if value is not None: dst.set_band_description(index,value)
                elif name == 'quality': dst.set_band_description(1,'binary_validity')
        row = {'status':'rgb_window_downloaded','scene_id':'TEMP_SOURCE','year':'2021','quality_status':'quality_eligible',
            'image_path':str(self.root/'image.tif'),'label_path':str(self.root/'label.tif'),'quality_mask_path':str(self.root/'quality.tif'),
            'quality_mask_semantics':copy.deepcopy(SCENE),'reflectance_conversion_verified':False}
        return {'scenes':[row]},values,labels,quality

    def materialize(self,report,output='new',module=grid):
        with patch.object(module,'ROOT',self.root): return module.materialize_patches(report,self.batch,self.root/output)

    def test_six_descriptions_arrays_nodata_and_nonoverlap_unchanged(self):
        report,values,labels,quality = self.source(anomalies=True); before = copy.deepcopy(report)
        source_bytes = {name:(self.root/(name+'.tif')).read_bytes() for name in ('image','label','quality')}
        rows = self.materialize(report)
        self.assertEqual(len(rows),2); self.assertEqual(report,before)
        self.assertEqual(source_bytes,{name:(self.root/(name+'.tif')).read_bytes() for name in source_bytes})
        for column,row in enumerate(rows):
            expected_values = values[:,:,column*256:(column+1)*256]
            expected_labels = labels[:,column*256:(column+1)*256].copy()
            expected_valid = (quality[:,column*256:(column+1)*256] == 1) & (expected_labels != 0) & np.all(np.isfinite(expected_values)&(expected_values != 0),axis=0)
            expected_labels[~expected_valid] = 0
            with rasterio.open(row['image_path']) as src:
                self.assertEqual(src.descriptions,NAMES); self.assertEqual(src.nodata,0)
                np.testing.assert_array_equal(src.read(),expected_values)
            with rasterio.open(row['label_path']) as src:
                self.assertEqual(src.descriptions,(None,)); self.assertEqual(src.nodata,0); np.testing.assert_array_equal(src.read(1),expected_labels)
            with rasterio.open(row['quality_mask_path']) as src:
                self.assertEqual(src.descriptions,(None,)); self.assertEqual(src.nodata,0); np.testing.assert_array_equal(src.read(1),expected_valid.astype('uint8'))
            self.assertNotIn('quality_mask_semantics',row); self.assertEqual(row['training_support_mask_semantics'],SUPPORT)
            self.assertEqual(row['split'],'val'); self.assertEqual(row['window_in_source'],[column*256,0,256,256])
            self.assertFalse(row['reflectance_conversion_verified'])

    def test_partial_none_unknown_and_reordered_descriptions_preserved_exactly(self):
        for index,names in enumerate(((None,)*6,('B12',None,'unknown','B02','B11','B08'))):
            report,*_ = self.source(names,width=256)
            row = self.materialize(report,'new'+str(index))[0]
            with rasterio.open(row['image_path']) as src: self.assertEqual(src.descriptions,names)
            self.assertEqual(report['scenes'][0]['quality_mask_semantics'],SCENE)

    def test_pinned_baseline_labels_quality_bytes_rows_and_source_unchanged(self):
        report,*_ = self.source(anomalies=True); before = copy.deepcopy(report)
        original = self.materialize(report,'old',self.legacy); updated = self.materialize(report)
        self.assertEqual(report,before); self.assertEqual(len(original),len(updated))
        for old,new in zip(original,updated):
            for field in ('label_path','quality_mask_path'): self.assertEqual(Path(old[field]).read_bytes(),Path(new[field]).read_bytes())
            with rasterio.open(old['image_path']) as a,rasterio.open(new['image_path']) as b:
                np.testing.assert_array_equal(a.read(),b.read()); self.assertEqual(a.profile,b.profile)
                self.assertEqual(a.descriptions,(None,)*6); self.assertEqual(b.descriptions,NAMES)
            a,b = copy.deepcopy(old),copy.deepcopy(new)
            for value in (a,b):
                for field in ('image_path','label_path','quality_mask_path','patch_sha256','quality_mask_semantics','training_support_mask_semantics'): value.pop(field,None)
            self.assertEqual(a,b)
            self.assertEqual(old['patch_sha256']['label'],new['patch_sha256']['label'])
            self.assertEqual(old['patch_sha256']['quality'],new['patch_sha256']['quality'])
            self.assertNotEqual(old['patch_sha256']['image'],new['patch_sha256']['image'])

    def test_no_scene_declaration_does_not_invent_pure_quality(self):
        report,*_ = self.source(width=256); report['scenes'][0].pop('quality_mask_semantics')
        row = self.materialize(report)[0]
        self.assertNotIn('quality_mask_semantics',row); self.assertEqual(row['training_support_mask_semantics'],SUPPORT)
        self.assertNotIn('training_support_mask_semantics',report['scenes'][0])
        row['training_support_mask_semantics']['kind'] = 'CHANGED_RETURN_ONLY'
        self.assertNotIn('training_support_mask_semantics',report['scenes'][0])

    def test_header_and_semantic_consumer_boundaries_are_not_training_approval(self):
        from app.ml.registry_raster_grid_normalization import _header
        from app.ml.registered_binary_mask_values import _binary_counts
        from app.ml.registered_quality_mask_grid import _mask_header
        from app.ml.registered_per_scene_files import _Issue
        from app.data.quality_report_completion import complete_quality_report
        report,*_ = self.source(width=256)
        row = self.materialize(report)[0]
        header = _header(Path(row['image_path']).read_bytes(),list(NAMES)); self.assertEqual(header['count'],6)
        # A training-support mask is not the pure scene binary-validity artifact;
        # its unchanged nodata=0 is rejected by the existing actual mask reader.
        mask_raw = Path(row['quality_mask_path']).read_bytes()
        with self.assertRaises(_Issue) as blocked: _binary_counts(mask_raw,_mask_header(mask_raw))
        self.assertEqual(blocked.exception.code,'MASK_INTRINSIC_VALIDITY_UNSUPPORTED')
        template = {'schema_version':'0.2.0','dataset_id':'image','version':'v1','source':{'institution':'TEST','product':'TEST','license':'TEST'},
            'data_type':'raster','spatial':{'crs':'EPSG:4326','bbox':[100,-20,120,0]},
            'temporal':{'start':'2021-01-01T00:00:00Z','end':'2021-12-31T00:00:00Z','calendar':'gregorian'},
            'quality_status':'RAW','access_class':'PUBLIC','sha256':'a'*64,'artifact_uri':'image.tif','lineage':[]}
        mask = copy.deepcopy(template); mask.update(dataset_id='mask',artifact_uri='quality.tif'); mask['source']['mask_semantics'] = copy.deepcopy(row['training_support_mask_semantics'])
        metadata = {key:copy.deepcopy(template[key]) for key in ('source','spatial','temporal','quality_status','access_class')}
        rejected = complete_quality_report(template,mask,{'id':'report','version':'v1','artifact_uri':'report.json'},metadata)
        self.assertEqual(rejected['issue']['code'],'MASK_SEMANTICS_INVALID')
        report,*_ = self.source((None,)*6,width=256); unknown = self.materialize(report,'missing-names')[0]
        with self.assertRaises(Exception): _header(Path(unknown['image_path']).read_bytes(),list(NAMES))

    def test_sub256_remainder_and_missing_scene_paths_keep_existing_skip_policy(self):
        report,*_ = self.source(width=300,height=260)
        rows = self.materialize(report); self.assertEqual(len(rows),1); self.assertEqual(rows[0]['window_in_source'],[0,0,256,256])
        report['scenes'][0].pop('label_path'); self.assertEqual(self.materialize(report,'skip'),[])


if __name__ == '__main__': unittest.main()
