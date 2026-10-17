"""Independent145: real temporary patch outputs and isolated Git baseline.

No existing product tests, Store, network, operating collection or training.
Low-level consumer checks are not full Registry workflow verification.
"""
import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import socket
import subprocess
import tempfile
import time
import types
import unittest
from unittest.mock import patch
import numpy as np
import rasterio
from rasterio.transform import from_origin
from app.ml.per_scene_normalization_contract import BAND_NAMES
from app.ml.registry_raster_grid_normalization import _header, _RasterBlocked
from app.ml.registered_binary_mask_values import _binary_counts
from app.ml.registered_per_scene_files import _Issue

ROOT=Path(__file__).resolve().parents[2]
BASE='a3f4a94a69ad0f5c54a9af76bf6af82053e1a419'
SOURCE='scripts/collect_training_grid.py';TEST='tests/test_grid_patch_declarations.py'
SOURCE_SHA='d312660f1a25fb6a9477f101e09aacd14f543636614726fb13092f42bceda3d6'
TEST_SHA='f183ba9e6469e5fff225d2ebd163fea2c54bcadf3f6bc604f53046aa2af38805'
OBS=[]
SCENE={'schema_version':1,'kind':'binary_validity','valid_value':1,'invalid_value':0}
TRAINING={'schema_version':1,'kind':'training_support','valid_value':1,'invalid_value':0}
def sha(raw):return hashlib.sha256(raw).hexdigest()
def files(root):return {p.relative_to(root).as_posix():sha(p.read_bytes()) for p in root.rglob('*') if p.is_file()}
def gitraw(path):return subprocess.run(['git','show',BASE+':'+path],cwd=ROOT,capture_output=True,check=True).stdout
def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
producer=load(ROOT/SOURCE,'ind145_producer')
baseline=types.ModuleType('ind145_baseline');baseline.__file__=str(ROOT/SOURCE)
exec(compile(gitraw(SOURCE),str(ROOT/SOURCE),'exec'),baseline.__dict__)

class Independent(unittest.TestCase):
    def fixture(self,descriptions=tuple(BAND_NAMES),scene_semantics=True,half_aoi=False):
        temp=tempfile.TemporaryDirectory(prefix='geoai-independent145-');self.addCleanup(temp.cleanup)
        root=Path(temp.name).resolve();inputs=root/'explicit-input';inputs.mkdir()
        boundary=root/'data/first-group-boundaries';boundary.mkdir(parents=True)
        geometry={'type':'Polygon','coordinates':[[[100,-20],[120,-20],[120,0],[100,0],[100,-20]]]}
        if half_aoi:
            from rasterio.warp import transform_geom
            geometry=transform_geom('EPSG:32748','EPSG:4326',{'type':'Polygon','coordinates':[[[500000,9197440],[502560,9197440],[502560,9200000],[500000,9200000],[500000,9197440]]]})
        (boundary/'selected-six.geojson').write_text(json.dumps({'type':'FeatureCollection','features':[{'type':'Feature','properties':{'explicit_fixture':True},'geometry':geometry}]}),encoding='utf-8')
        profile={'driver':'GTiff','height':256,'width':512,'crs':'EPSG:32748','transform':from_origin(500000,9200000,10,10)}
        image=np.stack([np.full((256,512),100+i,dtype='float32') for i in range(6)])
        image[0,0,0]=0;image[1,0,1]=np.nan;image[2,0,2]=np.inf
        label=np.full((256,512),10,dtype='uint8');label[:,256:]=20;label[1,0]=0
        quality=np.ones((256,512),dtype='uint8');quality[2,:8]=0
        with rasterio.open(inputs/'image.tif','w',**profile,count=6,dtype='float32',nodata=0) as dst:
            dst.write(image)
            for index,name in enumerate(descriptions,1):
                if name is not None:dst.set_band_description(index,name)
        with rasterio.open(inputs/'label.tif','w',**profile,count=1,dtype='uint8',nodata=0) as dst:dst.write(label,1)
        with rasterio.open(inputs/'quality.tif','w',**profile,count=1,dtype='uint8',nodata=None) as dst:
            dst.write(quality,1);dst.set_band_description(1,'binary_validity')
        source={'status':'rgb_window_downloaded','scene_id':'explicit-scene','year':'2021','image_path':str(inputs/'image.tif'),
            'label_path':str(inputs/'label.tif'),'quality_mask_path':str(inputs/'quality.tif'),'quality_status':'quality_eligible',
            'reflectance_conversion_verified':False,'unrelated_metadata':{'keep':['원형','🌏']}}
        if scene_semantics:source['quality_mask_semantics']=copy.deepcopy(SCENE)
        report={'status':'explicit-fixture','scenes':[source],'learning_ready':False}
        report_path=inputs/'scene-report.json';report_path.write_text(json.dumps(report,ensure_ascii=False),encoding='utf-8')
        batch={'province':'banten','split':'val','key':'explicit-banten-2021-g00','geometry':geometry}
        return root,inputs,report_path,report,batch

    def produce(self,fixture,module=producer,name='new'):
        root,inputs,report_path,report,batch=fixture;before=files(inputs);snapshot=copy.deepcopy(report)
        output=root/name
        with patch.object(module,'ROOT',root),patch.object(socket,'create_connection',side_effect=AssertionError('network forbidden')):
            rows=module.materialize_patches(report,batch,output)
        self.assertEqual(report,snapshot);self.assertEqual(files(inputs),before)
        return rows

    def test_00_source_hash_and_ast_scope(self):
        self.assertEqual(sha((ROOT/SOURCE).read_bytes()),SOURCE_SHA);self.assertEqual(sha((ROOT/TEST).read_bytes()),TEST_SHA)
        before=ast.parse(gitraw(SOURCE).decode('utf-8'));after=ast.parse((ROOT/SOURCE).read_text(encoding='utf-8'))
        def other(tree):return [ast.dump(node,include_attributes=False) for node in tree.body if not (isinstance(node,ast.FunctionDef) and node.name=='materialize_patches')]
        self.assertEqual(other(before),other(after))

    def test_01_actual_descriptions_none_unknown_and_permutation_unchanged(self):
        cases=[tuple(BAND_NAMES),(None,)*6,('B02',None,'caller-unknown 🌏','B08',None,'B12'),tuple(reversed(BAND_NAMES))]
        for names in cases:
            fixture=self.fixture(names);rows=self.produce(fixture);self.assertEqual(len(rows),2)
            for row in rows:
                with rasterio.open(row['image_path']) as dataset:self.assertEqual(dataset.descriptions,names)
                for key in ('label_path','quality_mask_path'):
                    with rasterio.open(row[key]) as dataset:self.assertEqual(dataset.descriptions,(None,));self.assertEqual(dataset.nodata,0)
            self.assertNotIn('quality_mask_semantics',rows[0]);self.assertEqual(rows[0]['training_support_mask_semantics'],TRAINING)
        OBS.append({'actual':'six ordered/None/mixed unknown/permuted image descriptions, two patches each','label_and_quality_descriptions':[None],'source_inputs_and_report_unchanged':True})

    def test_02_baseline_arrays_profiles_label_quality_bytes_and_rows_equal(self):
        fixture=self.fixture();old=self.produce(fixture,baseline,'old');new=self.produce(fixture)
        for before,after in zip(old,new):
            for key in ('image_path','label_path','quality_mask_path'):
                with rasterio.open(before[key]) as left,rasterio.open(after[key]) as right:
                    self.assertEqual(left.profile,right.profile);np.testing.assert_array_equal(left.read(),right.read())
                if key!='image_path':self.assertEqual(Path(before[key]).read_bytes(),Path(after[key]).read_bytes())
            left=copy.deepcopy(before);right=copy.deepcopy(after)
            for row in (left,right):
                for key in ('image_path','label_path','quality_mask_path','patch_sha256','quality_mask_semantics','training_support_mask_semantics'):row.pop(key,None)
            self.assertEqual(left,right)
            self.assertEqual(after['split'],'val');self.assertFalse(after['reflectance_conversion_verified'])
        OBS.append({'actual_baseline_comparison':'isolated Git module with same Temp inputs','patches':2,'image_arrays_profiles_equal':True,'label_quality_raw_bytes_equal':True,'rows_split_classcounts_equal_except_explicit_declarations_paths_and_hashes':True})

    def test_03_no_scene_semantics_still_training_support_and_detached(self):
        fixture=self.fixture(scene_semantics=False);rows=self.produce(fixture)
        for row in rows:self.assertNotIn('quality_mask_semantics',row);self.assertEqual(row['training_support_mask_semantics'],TRAINING)
        rows[0]['training_support_mask_semantics']['kind']='modified-output-only'
        self.assertEqual(rows[1]['training_support_mask_semantics'],TRAINING)
        self.assertNotIn('training_support_mask_semantics',fixture[3]['scenes'][0])
        self.assertEqual(json.loads(fixture[2].read_text(encoding='utf-8')),fixture[3])

    def test_04_actual_pixel_intersection_label_support_and_class_counts(self):
        fixture=self.fixture();rows=self.produce(fixture);first,second=rows
        expected=np.ones((256,256),dtype='uint8');expected[0,:3]=0;expected[1,0]=0;expected[2,:8]=0
        with rasterio.open(first['quality_mask_path']) as dataset:np.testing.assert_array_equal(dataset.read(1),expected)
        with rasterio.open(first['label_path']) as dataset:np.testing.assert_array_equal(dataset.read(1),expected*10)
        self.assertEqual(first['sample_class_coverage'],{'10':65524});self.assertEqual(second['sample_class_coverage'],{'20':65536})
        self.assertEqual(first['valid_pixel_ratio'],65524/65536);self.assertEqual(first['province_inside_fraction'],1)
        self.assertEqual(second['valid_pixel_ratio'],1);self.assertEqual(first['window_in_source'],[0,0,256,256])
        self.assertEqual(second['window_in_source'],[256,0,256,256])

    def test_05_actual_aoi_intersection_matches_baseline_no_default_reclassification(self):
        fixture=self.fixture(half_aoi=True);old=self.produce(fixture,baseline,'old');new=self.produce(fixture)
        self.assertEqual(len(new),2)
        for left,right in zip(old,new):
            self.assertEqual(left['valid_pixel_ratio'],right['valid_pixel_ratio']);self.assertEqual(left['province_inside_fraction'],right['province_inside_fraction'])
            self.assertEqual(left['quality_status'],right['quality_status']);self.assertEqual(left['sample_class_coverage'],right['sample_class_coverage'])
            self.assertEqual(Path(left['quality_mask_path']).read_bytes(),Path(right['quality_mask_path']).read_bytes())
        self.assertLess(new[1]['province_inside_fraction'],.05);self.assertEqual(new[1]['sample_class_coverage'],{})

    def test_06_actual_low_level_consumer_header_and_intrinsic_nodata_boundary(self):
        rows=self.produce(self.fixture());row=rows[0]
        observed=_header(Path(row['image_path']).read_bytes(),list(BAND_NAMES));self.assertEqual(observed['band_names'],list(BAND_NAMES))
        path=Path(row['quality_mask_path'])
        with rasterio.open(path) as dataset:
            expected={'width':dataset.width,'height':dataset.height,'count':1,'dtype':'uint8','crs_wkt':dataset.crs.to_wkt(),
                'transform':list(dataset.transform)[:6],'bounds':list(dataset.bounds)}
        with self.assertRaises(_Issue) as error:_binary_counts(path.read_bytes(),expected)
        self.assertEqual(error.exception.code,'MASK_INTRINSIC_VALIDITY_UNSUPPORTED')
        bad=self.produce(self.fixture(tuple(reversed(BAND_NAMES))))[0]
        with self.assertRaises(_RasterBlocked) as error2:_header(Path(bad['image_path']).read_bytes(),list(reversed(BAND_NAMES)))
        self.assertEqual(error2.exception.code,'RASTER_BAND_SIGNATURE_INVALID')
        OBS.append({'actual_low_level_consumers':{'129_header':'MATCHED ordered six-band header only','129_permutation':'RASTER_BAND_SIGNATURE_INVALID','133_binary_counts':'MASK_INTRINSIC_VALIDITY_UNSUPPORTED'},
            'full_registry_consumer_executed':False,'Store_calls':0,'training_support_is_not_pure_quality_mask':True})

if __name__=='__main__':
    old=['scripts/collect_samples.py','scripts/collect_training_parallel.py','backend/app/data/budget.py','backend/app/main.py',
        'backend/app/ml/registered_binary_mask_values.py','backend/app/ml/registry_raster_grid_normalization.py','frontend/src/AnnualInputDiagnostics.tsx']
    before={p:sha((ROOT/p).read_bytes()) for p in old};pins={p:sha(gitraw(p))==h for p,h in before.items()}
    started=time.perf_counter();result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Independent));seconds=time.perf_counter()-started
    unchanged={p:sha((ROOT/p).read_bytes())==h for p,h in before.items()}
    report={'schema_version':1,'scope':'INDEPENDENT_GRID_PATCH_DECLARATIONS_TEMP_ONLY','git_baseline':BASE,
      'tests':result.testsRun,'passed':result.testsRun-len(result.failures)-len(result.errors)-len(result.skipped),
      'skipped':len(result.skipped),'failures':len(result.failures),'errors':len(result.errors),'seconds':seconds,
      'source_sha256':sha((ROOT/SOURCE).read_bytes()),'test_sha256':sha((ROOT/TEST).read_bytes()),
      'test_names':unittest.defaultTestLoader.getTestCaseNames(Independent),'old_sources_unchanged':unchanged,'separate_git_baseline_matches':pins,
      'observations':OBS,'actual_scope':'Temp source GTiffs/scene-report/explicit boundary fixture; native patch writer and baseline pixel/profile/label-quality bytes; low-level129/133 readers only',
      'mock_scope':'Only module ROOT redirected to explicit Temp provenance GeoJSON and socket network denial guard; no mocked raster arrays or full Registry success claim',
      'operating_writes':0,'operating_collection':0,'network_requests':0,'Store_calls':0,'training':0,'inference':0,
      'api_ui_changed':False,'frontend_build_browser_required':False,
      'limitations':['Patch quality is training support combining label/AOI/source quality and image finite/nonzero, not a pure image validity or GMAIS approval.',
       'materialize_patches already uses mkdir(exist_ok=True) and open(w); this change does not enforce new-file-only or no-overwrite semantics.',
       'No existing datasets/headers/scene reports are migrated and no scientific/model/execution approval is granted.',
       'Low-level129 header/133 intrinsic-validity checks do not execute full Registry consumers or verify complete source semantics.']}
    Path(__file__).with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    raise SystemExit(0 if result.wasSuccessful() and all(pins.values()) and all(unchanged.values()) else 1)
