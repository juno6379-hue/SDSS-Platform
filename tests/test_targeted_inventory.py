import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import rasterio
from rasterio.transform import from_origin

from app.data import targeted_inventory as module


class TargetedInventoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.folder = self.root/module.SOURCE
        self.folder.mkdir(parents=True)
        self.image = self.raster('settled/image.tif', 470000)
        self.b02 = self.raster('old-pending/raw-B02.tif', 460000)
        self.label = self.raster('settled/raw-esri_io.tif', 500000)
        self.config = {'aois':[{'id':'banten','bbox':[105,-7,106,-6]}], 'window_size':256}
        (self.folder/'old-pending/config.json').write_text(json.dumps(self.config),encoding='utf-8')
        self.manifest = {'scenes':[{'source_window':{'path':str(self.image),'sha256':self.sha(self.image)},
                                     'quality_status':'quality_insufficient','year':2020}]}
        self.ledger = {'batches':{'old-pending':{'status':'pending','reserved_bytes':68157440,
                    'charged_bytes':68157440,'config_sha256':hashlib.sha256(json.dumps(self.config,sort_keys=True).encode()).hexdigest()}}}
        self.write_documents()
        self.request = {'manifest_ref':self.ref(self.mp),'ledger_ref':self.ref(self.lp),
                        'target':{'crs':'EPSG:32748','corners':[[500000,9300000],[502560,9300000],
                                    [502560,9297440],[500000,9297440]]}}

    def tearDown(self): self.tmp.cleanup()
    def sha(self,p): return hashlib.sha256(p.read_bytes()).hexdigest()
    def ref(self,p): return {'path':p.relative_to(self.root).as_posix(),'sha256':self.sha(p)}
    def write_documents(self):
        self.mp = self.root/'data/manifest.json';self.lp=self.root/'data/ledger.json'
        self.mp.write_text(json.dumps(self.manifest),encoding='utf-8')
        self.lp.write_text(json.dumps(self.ledger),encoding='utf-8')
    def raster(self,name,x):
        p=self.folder/name;p.parent.mkdir(parents=True,exist_ok=True)
        with rasterio.open(p,'w',driver='GTiff',width=256,height=256,count=1,dtype='uint8',
                           crs='EPSG:32748',transform=from_origin(x,9300000,10,10)) as ds:
            ds.write(np.ones((256,256),dtype='uint8'),1)
        return p
    def run_guard(self,**kw): return module.inspect_targeted_inventory(self.root,self.request,**kw)

    def test_actual_pending_support_and_reusable_reference_labels_readonly(self):
        before={p:p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        out=self.run_guard()
        self.assertEqual(out['status'],'LOCAL_INVENTORY_VERIFIED_EXECUTION_BLOCKED',out)
        self.assertEqual(out['support_files_verified'],2)
        self.assertEqual(out['pending'][0]['reserved_bytes'],68157440)
        self.assertEqual(len(out['label_files_excluded']),1)
        self.assertTrue(out['inventory_verified']);self.assertTrue(out['pending_footprints_verified'])
        self.assertFalse(out['execution_supported']);self.assertFalse(out['scientific_independence_proven'])
        self.assertEqual(before,{p:p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_unreported_scl_support_overlap_blocks(self):
        self.raster('unreported/qa-candidate-00-SCL.tif',500000)
        out=self.run_guard();self.assertEqual(out['issue'],'EXISTING_SUPPORT_OVERLAP',out)
        self.assertTrue(out['overlaps'])

    def test_noneligible_source_window_hash_is_enforced(self):
        self.manifest['scenes'][0]['source_window']['sha256']='0'*64
        self.write_documents();self.request['manifest_ref']=self.ref(self.mp)
        self.assertEqual(self.run_guard()['issue'],'SOURCE_PIN_MISMATCH')

    def test_historical_source_window_participates(self):
        p=self.raster('old/image.tif',500000)
        self.manifest['historical_noneligible_patches']=[{'source_window':{'path':str(p),'sha256':self.sha(p)}}]
        self.write_documents();self.request['manifest_ref']=self.ref(self.mp)
        self.assertEqual(self.run_guard()['issue'],'EXISTING_SUPPORT_OVERLAP')

    def test_missing_pending_b02_is_unknown_not_clear(self):
        self.b02.rename(self.b02.with_name('raw-B03.tif'))
        self.assertEqual(self.run_guard()['issue'],'PENDING_IMAGE_FOOTPRINT_MISSING')

    def test_pending_configuration_mismatch_blocks(self):
        self.ledger['batches']['old-pending']['config_sha256']='0'*64
        self.write_documents();self.request['ledger_ref']=self.ref(self.lp)
        self.assertEqual(self.run_guard()['issue'],'PENDING_CONFIG_MISMATCH')

    def test_budget_cannot_be_raised_and_inventory_is_not_truncated(self):
        self.assertEqual(self.run_guard(max_files=1)['issue'],'INVENTORY_LIMIT')
        self.assertEqual(self.run_guard(max_bytes=1)['issue'],'INVENTORY_LIMIT')
        self.assertEqual(self.run_guard(max_files=True)['issue'],'INVENTORY_LIMIT')

    def test_target_invalid_and_missing_source_reference_block(self):
        request=copy.deepcopy(self.request);request['target']['corners'][0][0]=float('nan')
        self.assertEqual(module.inspect_targeted_inventory(self.root,request)['issue'],'TARGET_INVALID')
        self.manifest['scenes']=[{}];self.write_documents();self.request['manifest_ref']=self.ref(self.mp)
        self.assertEqual(self.run_guard()['issue'],'SOURCE_REFERENCE_MISSING')

    def test_alias_rejected_even_if_outside_active_scene_list(self):
        original=module._links
        with patch.object(module,'_links',side_effect=lambda p:p==self.b02 or original(p)):
            self.assertEqual(self.run_guard()['issue'],'INVENTORY_PATH_INVALID')

    def test_new_partial_support_during_read_blocks(self):
        original=module._snapshot;done=[]
        def changed(*a,**kw):
            result=original(*a,**kw)
            if a[1]==self.image and not done:
                done.append(True);self.raster('late/raw-B04.tif',480000)
            return result
        with patch.object(module,'_snapshot',side_effect=changed):
            self.assertEqual(self.run_guard()['issue'],'INVENTORY_CHANGED')

    def test_ledger_drift_after_pinned_read_blocks(self):
        original=module._snapshot;done=[]
        def changed(*a,**kw):
            result=original(*a,**kw)
            if a[1]==self.image and not done:
                done.append(True);self.lp.write_text('{}',encoding='utf-8')
            return result
        with patch.object(module,'_snapshot',side_effect=changed):
            self.assertEqual(self.run_guard()['issue'],'INVENTORY_CHANGED')

    def test_older_ledger_report_source_directory_is_not_omitted(self):
        old=self.root/'data/old-v1/sources/old-key'
        old.mkdir(parents=True)
        target=old/'raw-B02.tif'
        target.write_bytes(self.label.read_bytes())
        self.ledger['batches']['old-key']={'status':'settled','report_path':str(old/'annual-window-report.json')}
        self.write_documents();self.request['ledger_ref']=self.ref(self.lp)
        self.assertEqual(self.run_guard()['issue'],'EXISTING_SUPPORT_OVERLAP')


    def test_geographic_support_is_checked_and_worldcover_is_reference_only(self):
        p=self.folder/'old-geographic/raw-B02.tif';p.parent.mkdir()
        with rasterio.open(p,'w',driver='GTiff',width=16,height=16,count=1,dtype='uint8',
                           crs='EPSG:4326',transform=from_origin(110,-1,.01,.01)) as ds:
            ds.write(np.ones((16,16),dtype='uint8'),1)
        (self.folder/'settled/raw-worldcover.tif').write_bytes(self.label.read_bytes())
        out=self.run_guard()
        self.assertEqual(out['status'],'LOCAL_INVENTORY_VERIFIED_EXECUTION_BLOCKED',out)
        self.assertEqual(out['support_files_verified'],3)
        self.assertEqual(len(out['label_files_excluded']),2)


if __name__=='__main__': unittest.main()
