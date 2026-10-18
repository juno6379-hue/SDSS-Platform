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
from app.data.targeted_bare_plan import prepare_targeted_bare_jobs,POLICY


class TargetedBarePlanTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        (self.root/'data').mkdir();(self.root/'evidence/integration').mkdir(parents=True)
        self.affine=from_origin(500000,9300000,10,10)
        values=np.ones((512,512),dtype='uint8');values[:256,:256]=8
        self.raster('data/label.tif',values,self.affine)
        self.raster('data/existing.tif',np.ones((16,16),dtype='uint8'),from_origin(470000,9300000,10,10))
        convert=Transformer.from_crs(32748,4326,always_xy=True)
        native=[self.affine*p for p in ((0,0),(256,0),(256,256),(0,256))]
        xy=[convert.transform(*p) for p in native]
        bbox=[min(p[0] for p in xy),min(p[1] for p in xy),max(p[0] for p in xy),max(p[1] for p in xy)]
        boundary={'features':[{'properties':{'province_id':'banten'},'geometry':{'type':'Polygon',
            'coordinates':[[[bbox[0]-.2,bbox[1]-.2],[bbox[2]+.2,bbox[1]-.2],[bbox[2]+.2,bbox[3]+.2],[bbox[0]-.2,bbox[3]+.2],[bbox[0]-.2,bbox[1]-.2]]]}}]}
        self.write('data/boundary.json',boundary)
        self.write('data/aggregate.json',{'scenes':[{'image_path':str(self.root/'data/existing.tif'),
            'patch_sha256':{'image':self.sha('data/existing.tif')},'year':2025,'quality_status':'quality_insufficient'}]})
        source={'year':'2020','label_year':2020,'label_source_url':'https://example.invalid/lc2020/reference.tif',
            'source_crops':{'raw-esri_io.tif':{'path':str(self.root/'data/label.tif'),'sha256':self.sha('data/label.tif')}}}
        self.write('data/lineage.json',{'scenes':[source]})
        proposal={'ranked_windows':[{'year':2020,'province':'banten','fixed_split':'val','source_crop_path':'data/label.tif',
            'source_crop_sha256':self.sha('data/label.tif'),'local_window_xy':[0,0],'declared_weak_label_bare_pixels':65536}]}
        self.write('evidence/integration/proposal.json',proposal)
        target={'target_id':'local-a','proposal_window_index':0,'province':'banten','fixed_split':'val','year':2020,
            'source_label_ref':self.ref('data/label.tif'),'source_lineage_ref':self.ref('data/lineage.json'),
            'source_label_window':[0,0,256,256],'source_label_grid':{'crs':'EPSG:32748','transform':list(self.affine)[:6],'width':512,'height':512},
            'target_bbox_wgs84':bbox,'target_footprint_native':{'crs':'EPSG:32748','corners':[list(p) for p in native]},'declared_bare_pixels':65536}
        self.plan={'schema_version':1,'kind':'TARGETED_BARE_256_COLLECTION_PLAN','proposal_ref':self.ref('evidence/integration/proposal.json'),
            'current_manifest_ref':self.ref('data/aggregate.json'),'boundary_ref':self.ref('data/boundary.json'),
            'policy':{**POLICY,'maximum_new_batches':2},'targets':[target]}
        self.base={'aois':[{'id':'banten','bbox':bbox}],'endpoint':'earth-search'}

    def tearDown(self):self.temp.cleanup()
    def raster(self,name,values,transform):
        with rasterio.open(self.root/name,'w',driver='GTiff',count=1,dtype=values.dtype,width=values.shape[1],height=values.shape[0],transform=transform,crs='EPSG:32748') as ds:ds.write(values,1)
    def write(self,name,value):(self.root/name).write_text(json.dumps(value),encoding='utf-8')
    def sha(self,name):return hashlib.sha256((self.root/name).read_bytes()).hexdigest()
    def ref(self,name):return {'path':name,'sha256':self.sha(name)}
    def run_plan(self):return prepare_targeted_bare_jobs(self.root,self.plan,self.base)

    def test_actual_local_pixels_geometry_and_proposal_jobs_not_execution(self):
        before={p:self.sha(p.relative_to(self.root)) for p in self.root.rglob('*') if p.is_file()};inputs=copy.deepcopy((self.plan,self.base))
        out=self.run_plan();self.assertEqual(out['status'],'LOCAL_TARGETS_VERIFIED_EXECUTION_BLOCKED',out)
        self.assertTrue(out['local_label_bytes_verified']);self.assertTrue(out['listed_image_overlap_checked'])
        self.assertEqual(out['targets'][0]['local_bare_pixels'],65536)
        job=out['job_proposals'][0];self.assertEqual((job['split'],job['nominal_patches'],job['config']['window_size']),('val',1,256))
        self.assertEqual(job['selection_context']['priority_source_classes'],[8]);self.assertFalse(out['execution_supported'])
        self.assertFalse(out['source_scene_split_verified']);self.assertFalse(out['pending_footprints_verified'])
        self.assertEqual((self.plan,self.base),inputs)
        self.assertEqual({p:self.sha(p.relative_to(self.root)) for p in self.root.rglob('*') if p.is_file()},before)

    def test_strict_target_count_policy_bool_and_extra_fail_before_file_io(self):
        original=copy.deepcopy(self.plan)
        variants=[]
        value=copy.deepcopy(original);value['targets'][0]['year']=True;variants.append(value)
        value=copy.deepcopy(original);value['targets']*=3;variants.append(value)
        value=copy.deepcopy(original);value['policy']['window_size']=1024;variants.append(value)
        value=copy.deepcopy(original);value['targets'][0]['source_label_grid']['width']=True;variants.append(value)
        value=copy.deepcopy(original);value['execute']=True;variants.append(value)
        with patch('app.data.targeted_bare_plan._snapshot',side_effect=AssertionError('I/O forbidden')) as read:
            for value in variants:
                self.assertEqual(prepare_targeted_bare_jobs(self.root,value,self.base)['status'],'BLOCKED')
            read.assert_not_called()

    def test_changed_label_or_proposal_pin_blocks_no_partial_jobs(self):
        with (self.root/'data/label.tif').open('ab') as stream:stream.write(b'changed')
        out=self.run_plan();self.assertEqual(out['issue'],'FILE_PIN_MISMATCH');self.assertEqual(out['job_proposals'],[])

    def test_actual_noneligible_different_year_image_overlap_is_rejected(self):
        self.raster('data/existing.tif',np.ones((16,16),dtype='uint8'),self.affine)
        aggregate=json.loads((self.root/'data/aggregate.json').read_text());aggregate['scenes'][0]['patch_sha256']['image']=self.sha('data/existing.tif')
        self.write('data/aggregate.json',aggregate);self.plan['current_manifest_ref']=self.ref('data/aggregate.json')
        out=self.run_plan();self.assertEqual(out['issue'],'EXISTING_IMAGE_OVERLAP');self.assertFalse(out['listed_image_overlap_checked'])

    def test_same_space_across_requested_years_not_counted_as_independent(self):
        second=copy.deepcopy(self.plan['targets'][0]);second.update(target_id='local-b',year=2021,proposal_window_index=1)
        source=json.loads((self.root/'data/lineage.json').read_text());source['scenes'][0].update(year='2021',label_year=2021,label_source_url='https://example.invalid/lc2021/reference.tif')
        self.write('data/lineage2021.json',source);second['source_lineage_ref']=self.ref('data/lineage2021.json')
        proposal=json.loads((self.root/'evidence/integration/proposal.json').read_text());row=copy.deepcopy(proposal['ranked_windows'][0]);row['year']=2021;proposal['ranked_windows'].append(row)
        self.write('evidence/integration/proposal.json',proposal);self.plan['proposal_ref']=self.ref('evidence/integration/proposal.json');self.plan['targets'].append(second)
        self.assertEqual(self.run_plan()['issue'],'TARGET_OVERLAP')

    def test_bbox_native_window_counts_and_lineage_are_not_inferred(self):
        original=copy.deepcopy(self.plan)
        for field,value,issue in [('declared_bare_pixels',256,'BARE_COUNT_MISMATCH'),('target_bbox_wgs84',[0,0,1,1],'TARGET_GEOMETRY_MISMATCH'),('source_label_window',[1,0,256,256],'PROPOSAL_MISMATCH')]:
            self.plan=copy.deepcopy(original);self.plan['targets'][0][field]=value
            self.assertEqual(self.run_plan()['issue'],issue)
        self.plan=original
        source=json.loads((self.root/'data/lineage.json').read_text());source['scenes'][0]['label_year']=2021
        self.write('data/lineage.json',source);self.plan['targets'][0]['source_lineage_ref']=self.ref('data/lineage.json')
        self.assertEqual(self.run_plan()['issue'],'LABEL_YEAR_INVALID')

    def test_path_escape_does_not_return_original_path_or_partial_payload(self):
        self.plan['targets'][0]['source_label_ref']['path']='data/../private-secret.tif'
        out=self.run_plan();self.assertEqual(out['status'],'BLOCKED');self.assertEqual(out['job_proposals'],[])
        self.assertNotIn('private-secret',json.dumps(out));self.assertFalse(out['local_label_bytes_verified'])

    def test_wrong_label_crs_and_opaque_label_rejected_with_rebound_pins(self):
        def rebind():
            digest=self.sha('data/label.tif')
            proposal=json.loads((self.root/'evidence/integration/proposal.json').read_text())
            proposal['ranked_windows'][0]['source_crop_sha256']=digest
            self.write('evidence/integration/proposal.json',proposal)
            source=json.loads((self.root/'data/lineage.json').read_text())
            source['scenes'][0]['source_crops']['raw-esri_io.tif']['sha256']=digest
            self.write('data/lineage.json',source)
            self.plan['proposal_ref']=self.ref('evidence/integration/proposal.json')
            self.plan['targets'][0]['source_label_ref']=self.ref('data/label.tif')
            self.plan['targets'][0]['source_lineage_ref']=self.ref('data/lineage.json')
        with rasterio.open(self.root/'data/label.tif','r+') as dataset:dataset.crs='EPSG:32648'
        rebind();self.assertEqual(self.run_plan()['issue'],'LABEL_GRID_INVALID')
        (self.root/'data/label.tif').write_bytes(b'<VRTDataset><SourceFilename>https://example.invalid/secret</SourceFilename></VRTDataset>')
        rebind();self.assertEqual(self.run_plan()['issue'],'LABEL_GRID_INVALID')


if __name__=='__main__':unittest.main()
