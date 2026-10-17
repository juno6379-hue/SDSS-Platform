"""Independent144: real temporary collector outputs; explicitly mocked network.

No operating collection or existing raster rewriting. Prior142 fixture metadata
helpers are reused, but none of its test cases are executed or counted.
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
from rasterio.enums import MaskFlags
from rasterio.transform import from_origin
from app.ml.registry_raster_grid_normalization import _header, _RasterBlocked
from app.ml.per_scene_normalization_contract import BAND_NAMES
from app.data.quality_report_storage import write_quality_report_files
from app.data.quality_report_preflight import inspect_stored_quality_report
from app.data.quality_report_registration import register_stored_quality_report
from app.dataset_registry import register_version
from app.store import Store

ROOT=Path(__file__).resolve().parents[2]
BASE='bd03292ea12f642839c96b753b752061725ef8d2'
SOURCE='scripts/collect_samples.py'
TEST='tests/test_collection_raster_declarations.py'
SOURCE_SHA='a78d0293736780e70402b85714f38964c2ef09e1253cf7453e292ca9a2551c98'
TEST_SHA='469ff453b37a91a4f6d7cf890e5721b9c0aeec31df2a28b215c1017e9f8c821e'
OBS=[]

def sha(raw):return hashlib.sha256(raw).hexdigest()
def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

fixture142=load(ROOT/'evidence/integration/quality-report-registration-independent-20261018.py','ind144_fixture142')
collector=load(ROOT/SOURCE,'ind144_collector')
LOGICAL=['blue','green','red','nir','swir16','swir22']
PC=dict(zip(LOGICAL,BAND_NAMES))
SEMANTICS={'schema_version':1,'kind':'binary_validity','valid_value':1,'invalid_value':0}

class Independent(unittest.TestCase):
    def test_00_frozen_source_test_and_only_collect_windows_ast_changed(self):
        self.assertEqual(sha((ROOT/SOURCE).read_bytes()),SOURCE_SHA)
        self.assertEqual(sha((ROOT/TEST).read_bytes()),TEST_SHA)
        original=subprocess.run(['git','show',BASE+':'+SOURCE],cwd=ROOT,capture_output=True,check=True).stdout
        before=ast.parse(original.decode('utf-8'));after=ast.parse((ROOT/SOURCE).read_text(encoding='utf-8'))
        def other(tree):return [ast.dump(node,include_attributes=False) for node in tree.body if not (isinstance(node,ast.FunctionDef) and node.name=='collect_windows')]
        self.assertEqual(other(before),other(after))
        OBS.append({'source_AST':'all top-level nodes other than collect_windows unchanged against baseline','baseline':BASE})

    def collect(self,*,bands=None,endpoint='planetary-computer',finite=True,scl=True,module=None):
        module=collector if module is None else module
        temp=tempfile.TemporaryDirectory(prefix='geoai-independent144-');self.addCleanup(temp.cleanup)
        root=Path(temp.name).resolve();bands=list(LOGICAL if bands is None else bands)
        pc=endpoint=='planetary-computer';assets=[PC.get(b,b) if pc else b for b in bands]
        item={'id':'EXPLICIT_NETWORK_MOCK_ONLY','datetime':'2022-06-01T00:00:00Z','cloud_cover':0,'license':'TEST_ONLY',
            'properties':{},'assets':{b:{'href':'mock:'+b} for b in assets}}
        if scl:item['assets']['SCL' if pc else 'scl']={'href':'mock:SCL'}
        config={'bands':bands,'endpoint':endpoint,'collection':'sentinel-2-l2a','window_size':4,
            'min_valid_fraction':0,'max_total_bytes':8*1024**2,'max_asset_bytes':1024**2,
            'periods':{'2022':{'start_date':'2022-01-01','end_date':'2022-12-31'}},
            'aois':[{'id':'explicit-test','bbox':[107,-7,107.01,-6.99]}],
            'download_worldcover':False,'preserve_source_crops':True,'transient_asset_retries':0}
        calls=[];original={}
        def window(url,bbox,pixels,reservation):
            name=url.removeprefix('mock:');calls.append({'asset':name,'requested_pixels':pixels})
            values=np.full((1,4,4),100+assets.index(name) if name in assets else 4,dtype='float32')
            if name=='SCL':values=np.array([0,1,3,8,9,10,11,2,4,5,6,7,4,4,4,4],dtype='float32').reshape(1,4,4)
            elif not finite and name==assets[0]:values[0,0,:]=[0,np.nan,np.inf,-np.inf]
            original[name]=values.copy()
            profile={'driver':'GTiff','dtype':'float32','count':1,'height':4,'width':4,'crs':'EPSG:32748',
                'transform':from_origin(500000,9200000,10,10),'nodata':0}
            return values,profile,{'http_body_bytes':10}
        with patch.object(module.service,'search_stac',return_value={'items':[item]}) as search,patch.object(module.service,'read_cog_window',side_effect=window) as fetch,patch.object(socket,'create_connection',side_effect=AssertionError('network forbidden')):
            report=module.collect_windows(config,root,execute=True)
        self.assertEqual(search.call_count,1);self.assertEqual(fetch.call_count,len(assets)+(1 if scl else 0))
        row=report['scenes'][0];self.assertEqual(row['status'],'rgb_window_downloaded',row.get('error'))
        return root,row,report,original,calls

    def test_01_pc_six_bands_actual_descriptions_nodata_and_values(self):
        root,row,report,original,calls=self.collect(scl=False)
        with rasterio.open(row['image_path']) as src:
            self.assertEqual(src.descriptions,tuple(BAND_NAMES));self.assertEqual(src.count,6)
            for index,name in enumerate(BAND_NAMES,1):np.testing.assert_array_equal(src.read(index),original[name][0])
        with rasterio.open(row['quality_mask_path']) as src:
            self.assertEqual(src.descriptions,('binary_validity',));self.assertIsNone(src.nodata)
            self.assertEqual(src.mask_flag_enums,([MaskFlags.all_valid],));self.assertEqual(src.dtypes,('uint8',))
            np.testing.assert_array_equal(src.read(1),np.ones((4,4),dtype='uint8'))
        self.assertEqual(row['quality_mask_semantics'],SEMANTICS);self.assertEqual(row['bands'],list(BAND_NAMES))
        self.assertFalse(row['reflectance_conversion_verified']);self.assertFalse(report['learning_ready'])
        self.assertFalse(report['grid_plan']['executed']);self.assertEqual(report['verified_patch_count'],0)
        _header(Path(row['image_path']).read_bytes(),list(BAND_NAMES))
        OBS.append({'actual':'collect_windows execute=True on new Temp GTiffs','network':'search_stac/read_cog_window explicitly mocked','normal_mask_counts':{'valid':16,'invalid':0,'total':16},'model_approval':False})

    def test_02_finite_nonzero_without_scl_and_original_crops_preserved(self):
        root,row,report,original,calls=self.collect(finite=False,scl=False)
        with rasterio.open(row['quality_mask_path']) as src:mask=src.read(1)
        expected=np.ones((4,4),dtype='uint8');expected[0,:]=0;np.testing.assert_array_equal(mask,expected)
        self.assertEqual(row['invalid_pixel_count'],4);self.assertEqual(row['valid_pixel_ratio'],.75)
        with rasterio.open(root/'explicit-test-2022/raw-B02.tif') as src:
            np.testing.assert_array_equal(src.read(),original['B02']);self.assertEqual(src.descriptions,(None,));self.assertEqual(src.nodata,0)
        self.assertEqual(row['quality_status'],'quality_unverified')

    def test_03_scl_codes_separate_from_finite_predicate(self):
        root,row,report,original,calls=self.collect(scl=True)
        expected=(~np.isin(original['SCL'][0],[0,1,3,8,9,10,11])).astype('uint8')
        with rasterio.open(row['quality_mask_path']) as src:np.testing.assert_array_equal(src.read(1),expected)
        self.assertEqual(row['invalid_pixel_count'],7);self.assertEqual(int(expected.sum()),9)
        root2,row2,_,original2,_=self.collect(scl=True,finite=False)
        expected2=(np.isfinite(original2['B02'][0])&(original2['B02'][0]!=0)&~np.isin(original2['SCL'][0],[0,1,3,8,9,10,11])).astype('uint8')
        with rasterio.open(row2['quality_mask_path']) as src:np.testing.assert_array_equal(src.read(1),expected2)

    def test_04_earth_search_logical_order_unknown_and_permutation_not_repaired(self):
        for endpoint,bands,names in (('earth-search',LOGICAL,list(BAND_NAMES)),
            ('planetary-computer',['red','MysteryAsset','blue'],['B04','MysteryAsset','B02']),
            ('planetary-computer',list(reversed(LOGICAL)),list(reversed(BAND_NAMES)))):
            root,row,_,original,calls=self.collect(endpoint=endpoint,bands=bands,scl=False)
            with rasterio.open(row['image_path']) as src:
                self.assertEqual(list(src.descriptions),names)
                for index,asset in enumerate(row['bands'],1):np.testing.assert_array_equal(src.read(index),original[asset][0])
            if names!=list(BAND_NAMES):
                with self.assertRaises(_RasterBlocked):_header(Path(row['image_path']).read_bytes(),names)
        OBS.append({'actual':'PC and EarthSearch ordered names plus unknown/permuted inputs','unknown_asset':'preserved verbatim','permuted_129_gate':'BLOCKED; producer did not reorder'})

    def test_05_actual_new_outputs_explicit_setup_report_registration_and_consumption(self):
        root,row,report,original,calls=self.collect(scl=True)
        image_path=Path(row['image_path']);mask_path=Path(row['quality_mask_path']);before_sources={str(p):sha(p.read_bytes()) for p in (image_path,mask_path)}
        image=fixture142.manifest('explicit-image',image_path.relative_to(root).as_posix(),sha(image_path.read_bytes()))
        mask=fixture142.manifest('explicit-mask',mask_path.relative_to(root).as_posix(),sha(mask_path.read_bytes()),True)
        mask['source']['mask_semantics']=copy.deepcopy(row['quality_mask_semantics'])
        image['quality_report_ref']='explicit-test-2022/quality.json'
        identity={'id':'explicit-report','version':'explicit-v1','artifact_uri':image['quality_report_ref']}
        metadata=fixture142.metadata();uri='explicit-test-2022/manifest.json'
        arguments=(root,image,mask,identity,metadata,uri)
        self.assertEqual(write_quality_report_files(*arguments)['status'],'FILES_WRITTEN_UNREGISTERED')
        self.assertEqual(inspect_stored_quality_report(*arguments)['status'],'STORED_REPORT_FILES_VERIFIED_UNREGISTERED')
        store=Store(root,recover_jobs=False);register_version(store,image);register_version(store,mask)
        registered=register_stored_quality_report(store,*arguments)
        self.assertEqual(registered['status'],'REPORT_REGISTERED_UNAPPROVED');refs=registered['fixed_refs']
        pins=tuple(refs[k] for k in ('image_ref','quality_report_ref','mask_ref'));before=fixture142.files(root)
        with patch.object(store,'connect',lambda:fixture142.ro(store)),patch.object(store,'put',side_effect=AssertionError('consumer write')):
            result=fixture142.inspect_registered_binary_mask_values(store,*pins)
        self.assertEqual(result['counts'],{'valid_pixels':9,'invalid_pixels':7,'total_pixels':16})
        self.assertFalse(result['scientific_accuracy_validated']);self.assertFalse(result['execution_authorized'])
        self.assertEqual(fixture142.files(root),before);self.assertEqual({str(p):sha(p.read_bytes()) for p in (image_path,mask_path)},before_sources)
        OBS.append({'actual':'new collector outputs -> explicit caller manifest/metadata/semantics ->140141142 ->133 readonly',
            'separate_setup_registry_writes':2,'report_registration':1,'counts':result['counts'],'automatic_collector_registration':False,'calibration_units_and_scientific_approval':False})

    def test_06_baseline_comparison_raw_source_bytes_and_old_nan_limitation(self):
        raw=subprocess.run(['git','show',BASE+':'+SOURCE],cwd=ROOT,capture_output=True,check=True).stdout
        old=types.ModuleType('ind144_baseline_collector');old.__file__=str(ROOT/SOURCE)
        exec(compile(raw,str(ROOT/SOURCE),'exec'),old.__dict__)
        oldroot,oldrow,_,_,_=self.collect(module=old,finite=False,scl=False)
        newroot,newrow,_,_,_=self.collect(finite=False,scl=False)
        rawpaths=[p.relative_to(oldroot) for p in oldroot.rglob('raw-*.tif')]
        self.assertEqual(len(rawpaths),6)
        for relative in rawpaths:self.assertEqual((oldroot/relative).read_bytes(),(newroot/relative).read_bytes())
        with rasterio.open(oldrow['image_path']) as src:self.assertEqual(src.descriptions,(None,)*6)
        with rasterio.open(oldrow['quality_mask_path']) as src:
            self.assertEqual(src.nodata,0);self.assertEqual(int(src.read(1).sum()),15)
        with rasterio.open(newrow['quality_mask_path']) as src:
            self.assertIsNone(src.nodata);self.assertEqual(int(src.read(1).sum()),12)
        OBS.append({'actual_baseline_comparison':'same mocked arrays, separate Temp outputs; baseline module loaded from git bytes without product edits',
            'raw_source_crop_bytes_identical':6,'baseline_nonzero_nan_inf_valid_pixels':15,'new_finite_nonzero_valid_pixels':12,'total_pixels':16})

if __name__=='__main__':
    old=fixture142.OLD+[fixture142.SOURCE,fixture142.TEST,'scripts/collect_training_grid.py','scripts/collect_training_parallel.py','backend/app/data/budget.py']
    before={p:sha((ROOT/p).read_bytes()) for p in old}
    baseline={p:sha(subprocess.run(['git','show',BASE+':'+p],cwd=ROOT,capture_output=True,check=True).stdout)==h for p,h in before.items()}
    started=time.perf_counter();result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Independent));seconds=time.perf_counter()-started
    unchanged={p:sha((ROOT/p).read_bytes())==h for p,h in before.items()}
    report={'schema_version':1,'scope':'INDEPENDENT_NEW_COLLECT_WINDOWS_DECLARATIONS_TEMP_ONLY','git_baseline':BASE,
      'tests':result.testsRun,'passed':result.testsRun-len(result.failures)-len(result.errors)-len(result.skipped),
      'skipped':len(result.skipped),'failures':len(result.failures),'errors':len(result.errors),'seconds':seconds,
      'source_sha256':sha((ROOT/SOURCE).read_bytes()),'test_sha256':sha((ROOT/TEST).read_bytes()),
      'test_names':unittest.defaultTestLoader.getTestCaseNames(Independent),'old_sources_unchanged':unchanged,
      'separate_git_baseline_matches':baseline,'observations':OBS,
      'actual_scope':'new temporary GTiff header and pixel outputs; separate caller metadata and temporary report storage/registration/readonly consumption',
      'mock_scope':'STAC search and COG window arrays are explicit service mocks; socket network guard; no real collection or source download',
      'operating_collection':0,'operating_writes':0,'network_requests':0,'training':0,'inference':0,
      'api_ui_changed':False,'frontend_build_browser_required':False,
      'limitations':['Band names preserve requested order and unknown asset names; no taxonomy/calibration/unit or physical source authenticity is established.',
        'Explicit binary mask validity is finite/nonzero and existing SCL exclusions, not independent quality truth or scientific/model/execution approval.',
        'Integration manifests/metadata and Registry source setup are explicit temporary caller steps, not automatic collector registration.',
        'Only new collect_windows outputs change. Existing datasets/raw source crops/grid label masks and operating ledgers/reservations are not migrated.']}
    Path(__file__).with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    raise SystemExit(0 if result.wasSuccessful() and all(baseline.values()) and all(unchanged.values()) else 1)
