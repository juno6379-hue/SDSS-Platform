"""Native tiny GTiff tests; full167 inventory mocked, numerical170 overlap real."""
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
from pyproj import Transformer
from scripts import review_bare_targets179 as s


class Review179Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);(self.root/'evidence/integration').mkdir(parents=True)
        self.folder=self.root/'data/job';(self.folder/'crop').mkdir(parents=True)
        self.label=self.folder/'crop/raw-esri_io.tif'
        self.affine=from_origin(500000,9300000,10,10)
        values=np.full((256,512),8,dtype='uint8')
        with rasterio.open(self.label,'w',driver='GTiff',width=512,height=256,count=1,dtype='uint8',crs='EPSG:32748',transform=self.affine) as ds:ds.write(values,1)
        url='https://example.invalid/lc2020/51N_20200101-20210101.tif'
        source={'province':'banten','year':'2020','label_year':2020,'label_source':'esri_io','label_source_url':url,'source_crops':{'raw-esri_io.tif':{**self.ref(self.label),'path':str(self.label),'source':url}}}
        self.lineage=self.write('data/job/annual-window-report.json',{'scenes':[source]})
        self.manifest=self.write('data/source.json',{'scenes':[]})
        self.ledger=self.write('data/ledger.json',{'batches':{'job':{'status':'settled','report_path':str(self.lineage)}}})
        geo={'features':[{'properties':{'province_id':p},'geometry':{'type':'Polygon','coordinates':[[[104,-8],[106,-8],[106,-5],[104,-5],[104,-8]]]}} for p in s.FIXED_PROVINCE_SPLITS]}
        self.boundary=self.write('data/boundary.json',geo)
        self.proposal=self.write('evidence/integration/proposal.json',{'boundary_sha256':self.sha(self.boundary),'ranked_windows':[self.candidate(0),self.candidate(256)]})
        self.request={'schema_version':1,**{k+'_ref':self.ref(v) for k,v in [('proposal',self.proposal),('manifest',self.manifest),('ledger',self.ledger),('boundary',self.boundary)]}}
        self.inventory={'inventory_verified':True,'pending_footprints_verified':True,'source_pins_verified':True,'assets':[],'status':'LOCAL_INVENTORY_VERIFIED_EXECUTION_BLOCKED'}

    def sha(self,p):return hashlib.sha256(p.read_bytes()).hexdigest()
    def ref(self,p):return {'path':p.relative_to(self.root).as_posix(),'sha256':self.sha(p)}
    def write(self,name,obj):
        p=self.root/name;p.write_text(json.dumps(obj),encoding='utf8');return p
    def candidate(self,x):
        corners=[list(self.affine*(x+dx,dy)) for dx,dy in ((0,0),(256,0),(256,256),(0,256))]
        inverse=Transformer.from_crs(32748,4326,always_xy=True);xy=[inverse.transform(*p) for p in corners]
        return {'year':2020,'province':'banten','fixed_split':'val','source_crop_path':self.label.relative_to(self.root).as_posix(),'source_crop_sha256':self.sha(self.label),'local_window_xy':[x,0],'declared_weak_label_bare_pixels':65536,'source_label_grid':{'crs':'EPSG:32748','transform':list(self.affine)[:6],'width':512,'height':256},'target_footprint_native':{'crs':'EPSG:32748','corners':corners},'bbox_wgs84':[min(p[0] for p in xy),min(p[1] for p in xy),max(p[0] for p in xy),max(p[1] for p in xy)]}
    def alter_proposal(self,mutate):
        obj=json.loads(self.proposal.read_text());mutate(obj);self.write('evidence/integration/proposal.json',obj);self.request['proposal_ref']=self.ref(self.proposal)
    def run_review(self,inventory=None):
        with patch.object(s,'inspect_targeted_inventory',return_value=inventory or self.inventory) as call:
            result=s.review(self.root,self.request);self.assertEqual(call.call_count,1);return result

    def test_native_two_candidates_one_inventory_plan_exact(self):
        before={p:self.sha(p) for p in self.root.rglob('*') if p.is_file()}
        out=self.run_review();self.assertEqual(out['historical_clear_count'],2)
        self.assertEqual(out['native_label_files_read'],1);self.assertEqual(out['candidate_mutual_overlap_pairs'],[])
        self.assertFalse(out['execution_supported']);self.assertFalse(out['actual_quality_eligible'])
        plan=s.select_plan(out,[0,1]);self.assertEqual(plan['policy']['maximum_new_batches'],2)
        self.assertEqual(plan['targets'][0]['source_lineage_ref'],self.ref(self.lineage))
        self.assertEqual(before,{p:self.sha(p) for p in self.root.rglob('*') if p.is_file()})

    def test_overlap_history_is_observation_not_global_abort(self):
        assets=[{'crs':'EPSG:32748','bounds':[500000,9297440,502560,9300000]}]
        out=self.run_review({**self.inventory,'status':'BLOCKED','issue':'EXISTING_SUPPORT_OVERLAP','assets':assets})
        self.assertEqual([o['historical_overlap'] for o in out['observations']],[True,False])
        with self.assertRaisesRegex(ValueError,'HISTORICAL_OVERLAP'):s.select_plan(out,[0])
        self.assertEqual(len(s.select_plan(out,[1])['targets']),1)

    def test_mutual_overlap_report_separate_from_history(self):
        other=self.root/'data/job2/crop/raw-esri_io.tif';other.parent.mkdir(parents=True);other.write_bytes(self.label.read_bytes())
        with rasterio.open(other,'r+') as ds:ds.update_tags(test='independent bytes, same footprint')
        lineage=json.loads(self.lineage.read_text());crop=lineage['scenes'][0]['source_crops']['raw-esri_io.tif'];crop.update(path=str(other),sha256=self.sha(other))
        other_lineage=self.write('data/job2/annual-window-report.json',lineage)
        ledger=json.loads(self.ledger.read_text());ledger['batches']['job2']={'status':'settled','report_path':str(other_lineage)}
        self.write('data/ledger.json',ledger);self.request['ledger_ref']=self.ref(self.ledger)
        candidate=self.candidate(0);candidate.update(source_crop_path=other.relative_to(self.root).as_posix(),source_crop_sha256=self.sha(other))
        self.alter_proposal(lambda p:p['ranked_windows'].__setitem__(1,candidate))
        out=self.run_review();self.assertEqual(len(out['candidate_mutual_overlap_pairs']),1);self.assertEqual(out['historical_clear_count'],2)
        with self.assertRaisesRegex(ValueError,'MUTUAL_OVERLAP'):s.select_plan(out,[0,1])

    def test_bad_split_year_duplicate_and_geometry_fail(self):
        mutations=[lambda p:p['ranked_windows'][0].update(fixed_split='train'),lambda p:p['ranked_windows'][0].update(year=True),lambda p:p['ranked_windows'].__setitem__(1,copy.deepcopy(p['ranked_windows'][0])),lambda p:p['ranked_windows'][0].update(declared_weak_label_bare_pixels=999)]
        original=self.proposal.read_bytes()
        for mutate in mutations:
            self.proposal.write_bytes(original);self.alter_proposal(mutate)
            with self.assertRaises(ValueError):self.run_review()

    def test_missing_lineage_or_ambiguous_lineage(self):
        document=json.loads(self.lineage.read_text());document['scenes']*=2
        self.lineage.write_text(json.dumps(document),encoding='utf8')
        with self.assertRaisesRegex(ValueError,'LABEL_LINEAGE_AMBIGUOUS'):self.run_review()
        self.lineage.unlink()
        with self.assertRaises((s._Blocked,ValueError,OSError)):self.run_review()

    def test_unverified_inventory_rejected(self):
        with self.assertRaisesRegex(ValueError,'INVENTORY_NOT_VERIFIED'):self.run_review({**self.inventory,'pending_footprints_verified':False})

    def test_stale_metadata_and_label_pin(self):
        self.manifest.write_text('{"scenes":[],"new":true}')
        with self.assertRaises(ValueError):self.run_review()
        self.request['manifest_ref']=self.ref(self.manifest)
        self.label.write_bytes(b'changed')
        with self.assertRaises(ValueError):self.run_review()

    def test_metadata_changed_during_inventory_rejected(self):
        def mutate(*args,**kwargs):
            self.manifest.write_text('{"scenes":[],"new":true}');return self.inventory
        with patch.object(s,'inspect_targeted_inventory',side_effect=mutate):
            with self.assertRaises(ValueError):s.review(self.root,self.request)

    def test_bounds_cap_and_extra_request_fields(self):
        with patch.dict(s.LIMITS,maximum_candidates=1):
            with self.assertRaisesRegex(ValueError,'CANDIDATE_LIMIT'):self.run_review()
        self.request['execute']=True
        with self.assertRaisesRegex(ValueError,'REQUEST_INVALID'):self.run_review()

    def test_label_mutated_after_inventory_rejected(self):
        def mutate(*args,**kwargs):
            self.label.write_bytes(b'changed after native reads');return self.inventory
        with patch.object(s,'inspect_targeted_inventory',side_effect=mutate):
            with self.assertRaisesRegex(ValueError,'LABEL_CHANGED'):s.review(self.root,self.request)

    def test_cli_existing_output_refused_before_review(self):
        request=self.write('evidence/integration/request.json',self.request)
        output=self.write('evidence/integration/output.json',{'existing':'preserve'})
        before=output.read_bytes()
        with patch.object(s,'ROOT',self.root),patch.object(s,'review',side_effect=AssertionError('should not execute')) as call:
            self.assertEqual(s.main(['--request',str(request),'--request-sha256',self.sha(request),'--output',str(output)]),2)
            call.assert_not_called()
        self.assertEqual(output.read_bytes(),before)

    def test_all_six_fixed_province_splits_native(self):
        for province,split in s.FIXED_PROVINCE_SPLITS.items():
            with self.subTest(province=province):
                lineage=json.loads(self.lineage.read_text());lineage['scenes'][0]['province']=province
                self.lineage.write_text(json.dumps(lineage),encoding='utf8')
                candidate=self.candidate(0);candidate.update(province=province,fixed_split=split)
                self.alter_proposal(lambda p:p.update(ranked_windows=[candidate]))
                out=self.run_review();self.assertEqual(out['targets'][0]['fixed_split'],split)
                self.assertEqual(len(out['ui_summary']['summary_by_province']),6)
                self.assertEqual(out['ui_summary']['candidate_total'],1)

    def test186_explicit128_offset_accepted_default256_rejects(self):
        candidate=self.candidate(128)
        self.alter_proposal(lambda p:p.update(ranked_windows=[candidate]))
        with self.assertRaisesRegex(ValueError,'WINDOW_INVALID'):self.run_review()
        self.alter_proposal(lambda p:p.update(window_stride=128,province_filter=['banten']))
        out=self.run_review();self.assertEqual(out['targets'][0]['source_label_window'],[128,0,256,256])
        self.assertFalse(out['actual_quality_eligible']);self.assertEqual(len(s.select_plan(out,[0])['targets']),1)

    def test186_stride_and_scope_cannot_widen_silently(self):
        original=self.proposal.read_bytes()
        variants=[{'window_stride':True},{'window_stride':64},{'window_stride':128},{'window_stride':128,'province_filter':[]},{'window_stride':128,'province_filter':['gorontalo']},{'window_stride':128,'province_filter':['banten','banten']},{'window_stride':256,'province_filter':['unknown']}]
        for variant in variants:
            self.proposal.write_bytes(original);self.alter_proposal(lambda p:p.update(variant))
            with self.assertRaises(ValueError):self.run_review()


if __name__=='__main__':unittest.main()
