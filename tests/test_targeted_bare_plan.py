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
from app.data.readiness_connectivity_witness import FIXED_PROVINCE_SPLITS


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
        rebind();self.assertEqual(self.run_plan()['issue'],'LABEL_GRID_MISMATCH')
        (self.root/'data/label.tif').write_bytes(b'<VRTDataset><SourceFilename>https://example.invalid/secret</SourceFilename></VRTDataset>')
        rebind();self.assertEqual(self.run_plan()['issue'],'LABEL_GRID_INVALID')

    def configure_target(self,province='banten',year=2020,crs='EPSG:32748',bare=65536,resolution=10):
        affine=from_origin(500000,100000 if crs=='EPSG:32651' else 9300000,resolution,resolution)
        values=np.ones((512,512),dtype='uint8');values[:256,:256]=1
        flat=values[:256,:256].copy().reshape(-1);flat[:bare]=8;values[:256,:256]=flat.reshape(256,256)
        with rasterio.open(self.root/'data/label.tif','w',driver='GTiff',count=1,dtype='uint8',width=512,height=512,transform=affine,crs=crs) as ds:ds.write(values,1)
        inverse=Transformer.from_crs(crs,4326,always_xy=True);native=[affine*p for p in ((0,0),(256,0),(256,256),(0,256))]
        xy=[inverse.transform(*p) for p in native];bbox=[min(p[0] for p in xy),min(p[1] for p in xy),max(p[0] for p in xy),max(p[1] for p in xy)]
        geometry={'type':'Polygon','coordinates':[[[bbox[0]-.2,bbox[1]-.2],[bbox[2]+.2,bbox[1]-.2],[bbox[2]+.2,bbox[3]+.2],[bbox[0]-.2,bbox[3]+.2],[bbox[0]-.2,bbox[1]-.2]]]}
        self.write('data/boundary.json',{'features':[{'properties':{'province_id':province},'geometry':geometry}]})
        lineage={'scenes':[{'year':str(year),'label_year':year,'label_source_url':f'https://example.invalid/lc{year}/reference.tif','source_crops':{'raw-esri_io.tif':{'path':str(self.root/'data/label.tif'),'sha256':self.sha('data/label.tif')}}}]}
        self.write('data/lineage.json',lineage)
        proposed={'year':year,'province':province,'fixed_split':FIXED_PROVINCE_SPLITS[province],'source_crop_path':'data/label.tif','source_crop_sha256':self.sha('data/label.tif'),'local_window_xy':[0,0],'declared_weak_label_bare_pixels':bare}
        self.write('evidence/integration/proposal.json',{'ranked_windows':[proposed]})
        target=self.plan['targets'][0]
        target.update(province=province,fixed_split=FIXED_PROVINCE_SPLITS[province],year=year,source_label_ref=self.ref('data/label.tif'),source_lineage_ref=self.ref('data/lineage.json'),source_label_grid={'crs':crs,'transform':list(affine)[:6],'width':512,'height':512},target_footprint_native={'crs':crs,'corners':[list(p) for p in native]},target_bbox_wgs84=bbox,declared_bare_pixels=bare)
        self.plan.update(proposal_ref=self.ref('evidence/integration/proposal.json'),boundary_ref=self.ref('data/boundary.json'))
        self.base['aois']=[{'id':province,'bbox':bbox,'province_marker':province}]
        return geometry

    def test_six_provinces_six_years_native_metre_crs_and_fixed_splits(self):
        crs={'south_sulawesi':'EPSG:32750','gorontalo':'EPSG:32651','southeast_sulawesi':'EPSG:32751','east_java':'EPSG:32749','banten':'EPSG:32748','west_java':'EPSG:32748'}
        for province,split in FIXED_PROVINCE_SPLITS.items():
            for year in range(2020,2026):
                with self.subTest(province=province,year=year):
                    geometry=self.configure_target(province,year,crs[province]);out=self.run_plan()
                    self.assertEqual(out['status'],'LOCAL_TARGETS_VERIFIED_EXECUTION_BLOCKED',out)
                    job=out['job_proposals'][0]
                    self.assertEqual((job['province'],job['split'],job['year']),(province,split,year))
                    self.assertEqual(job['geometry'],geometry)
                    self.assertEqual(job['config']['aois'][0]['province_id'],province)
                    self.assertTrue(job['key'].startswith(f'target256-bare-{province}-{year}-'))
                    self.assertFalse(out['execution_supported']);self.assertFalse(out['training_ready'])

    def test_unknown_province_wrong_fixed_split_and_missing_or_duplicate_bindings(self):
        self.configure_target('west_java',2024)
        original=copy.deepcopy(self.plan)
        for province,split in [('west_java','train'),('banten','test'),('unknown','train')]:
            self.plan=copy.deepcopy(original);self.plan['targets'][0].update(province=province,fixed_split=split)
            self.assertEqual(self.run_plan()['issue'],'TARGET_INVALID')
        self.plan=original
        for features in ([],[{'properties':{'province_id':'west_java'},'geometry':{} }]*2):
            self.write('data/boundary.json',{'features':features});self.plan['boundary_ref']=self.ref('data/boundary.json')
            self.assertEqual(self.run_plan()['issue'],'BOUNDARY_INVALID')
        self.configure_target('west_java',2024)
        original=copy.deepcopy(self.base)
        for aois in ([],original['aois']*2,[{'id':'banten'}]):
            self.base['aois']=aois;self.assertEqual(self.run_plan()['issue'],'BASE_AOI_INVALID')

    def test_bare_255_rejected_and_256_accepted(self):
        for count in (255,256):
            self.configure_target('south_sulawesi',2022,'EPSG:32750',bare=count)
            out=self.run_plan()
            self.assertEqual(out['status'],'BLOCKED' if count==255 else 'LOCAL_TARGETS_VERIFIED_EXECUTION_BLOCKED',out)
            if count==255:self.assertEqual(out['issue'],'BARE_COUNT_MISMATCH')

    def test_non_metre_or_wrong_resolution_and_geographic_labels_block(self):
        for crs,resolution in [('EPSG:2277',10),('EPSG:4326',.001),('EPSG:32749',9),('EPSG:32749',20)]:
            self.configure_target('east_java',2025,crs,resolution=resolution)
            self.assertEqual(self.run_plan()['status'],'BLOCKED')

    def test_mixed_province_geometry_is_bound_to_each_target(self):
        first_geometry=self.configure_target('banten',2020)
        first_plan=copy.deepcopy(self.plan);first_base=copy.deepcopy(self.base)
        for name in ('label.tif','lineage.json'):
            (self.root/'data'/('first-'+name)).write_bytes((self.root/'data'/name).read_bytes())
        first=copy.deepcopy(first_plan['targets'][0]);first['source_label_ref']=self.ref('data/first-label.tif')
        source=json.loads((self.root/'data/first-lineage.json').read_text());source['scenes'][0]['source_crops']['raw-esri_io.tif']['path']=str(self.root/'data/first-label.tif');self.write('data/first-lineage.json',source);first['source_lineage_ref']=self.ref('data/first-lineage.json')
        proposed=json.loads((self.root/'evidence/integration/proposal.json').read_text())['ranked_windows'][0];proposed['source_crop_path']='data/first-label.tif'
        second_geometry=self.configure_target('east_java',2025,'EPSG:32749')
        second_proposed=json.loads((self.root/'evidence/integration/proposal.json').read_text())['ranked_windows'][0]
        second=copy.deepcopy(self.plan['targets'][0]);second.update(target_id='local-b',proposal_window_index=1)
        self.plan['targets']=[first,second]
        self.write('evidence/integration/proposal.json',{'ranked_windows':[proposed,second_proposed]});self.plan['proposal_ref']=self.ref('evidence/integration/proposal.json')
        self.write('data/boundary.json',{'features':[{'properties':{'province_id':'banten'},'geometry':first_geometry},{'properties':{'province_id':'east_java'},'geometry':second_geometry}]});self.plan['boundary_ref']=self.ref('data/boundary.json')
        self.base['aois']=first_base['aois']+self.base['aois']
        out=self.run_plan();self.assertEqual(out['status'],'LOCAL_TARGETS_VERIFIED_EXECUTION_BLOCKED',out)
        self.assertEqual([j['geometry'] for j in out['job_proposals']],[first_geometry,second_geometry])
        self.assertEqual([j['config']['aois'][0]['province_marker'] for j in out['job_proposals']],['banten','east_java'])
        self.assertEqual([j['split'] for j in out['job_proposals']],['val','train'])

    def test_existing_banten_complete_job_and_key_contract_remains_unchanged(self):
        original_plan=copy.deepcopy(self.plan);original_base=copy.deepcopy(self.base)
        out=self.run_plan();job=out['job_proposals'][0]
        digest=hashlib.sha256(json.dumps(self.plan,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode()).hexdigest()
        self.assertEqual(job['key'],f'target256-bare-banten-2020-local-a-{digest[:12]}')
        expected=copy.deepcopy(self.base);aoi=copy.deepcopy(self.base['aois'][0]);aoi.update(id='bare-local-a',province_id='banten',bbox=self.plan['targets'][0]['target_bbox_wgs84'])
        expected.update(aois=[aoi],years=[2020],annual_reference='esri_io',window_size=256,bands=['blue','green','red','nir','swir16','swir22'],max_total_bytes=64*1024**2,prior_download_budget_bytes=0,candidate_limit=5,min_valid_fraction=.8,candidate_valid_fraction=.65,verify_product_metadata=True,preserve_source_crops=True,transient_asset_retries=0,minimum_complete_scenes=1,search_limit=20,sort_by_cloud=True,collection_policy_version='targeted-bare-256-PLAN-ONLY')
        self.assertEqual(job['config'],expected)
        self.assertEqual(job['config_sha256'],hashlib.sha256(json.dumps(expected,sort_keys=True).encode()).hexdigest())
        self.assertEqual(job,{'province':'banten','year':2020,'split':'val','nominal_patches':1,
            'geometry':json.loads((self.root/'data/boundary.json').read_text())['features'][0]['geometry'],
            'config':expected,'target_id':'local-a','selection_context':{'priority_source_classes':[8]},
            'key':f'target256-bare-banten-2020-local-a-{digest[:12]}',
            'config_sha256':hashlib.sha256(json.dumps(expected,sort_keys=True).encode()).hexdigest()})
        self.assertEqual(self.plan,original_plan);self.assertEqual(self.base,original_base)

    def test_actual_gcp_rpc_and_nonfinite_native_transform_are_rejected(self):
        from affine import Affine
        from rasterio.control import GroundControlPoint
        for kind in ('gcp','rpc','nan'):
            self.configure_target('east_java',2025,'EPSG:32749')
            with rasterio.open(self.root/'data/label.tif','r+') as ds:
                if kind=='gcp':
                    ds.gcps=([GroundControlPoint(0,0,500000,9300000),GroundControlPoint(0,512,505120,9300000),GroundControlPoint(512,0,500000,9294880)],rasterio.crs.CRS.from_epsg(32749))
                elif kind=='rpc':
                    tags={key:'0' for key in ('HEIGHT_OFF','LAT_OFF','LONG_OFF','LINE_OFF','SAMP_OFF')}
                    tags.update({key:'1' for key in ('HEIGHT_SCALE','LAT_SCALE','LONG_SCALE','LINE_SCALE','SAMP_SCALE')})
                    tags.update({key:'1 '+'0 '*19 for key in ('LINE_NUM_COEFF','LINE_DEN_COEFF','SAMP_NUM_COEFF','SAMP_DEN_COEFF')})
                    ds.update_tags(ns='RPC',**tags)
                else:ds.transform=Affine(float('nan'),0,500000,0,-10,9300000)
            digest=self.sha('data/label.tif')
            proposed=json.loads((self.root/'evidence/integration/proposal.json').read_text());proposed['ranked_windows'][0]['source_crop_sha256']=digest;self.write('evidence/integration/proposal.json',proposed)
            lineage=json.loads((self.root/'data/lineage.json').read_text());lineage['scenes'][0]['source_crops']['raw-esri_io.tif']['sha256']=digest;self.write('data/lineage.json',lineage)
            self.plan['proposal_ref']=self.ref('evidence/integration/proposal.json');self.plan['targets'][0]['source_label_ref']=self.ref('data/label.tif');self.plan['targets'][0]['source_lineage_ref']=self.ref('data/lineage.json')
            out=self.run_plan();self.assertEqual(out['status'],'BLOCKED',(kind,out));self.assertEqual(out['job_proposals'],[])

    def test_synthetic_local_read_only_with_network_unavailable(self):
        self.configure_target('gorontalo',2024,'EPSG:32651')
        before={str(p):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        with patch('socket.socket',side_effect=AssertionError('HTTP forbidden')):
            out=self.run_plan()
        self.assertEqual(out['status'],'LOCAL_TARGETS_VERIFIED_EXECUTION_BLOCKED',out)
        self.assertEqual(before,{str(p):p.read_bytes() for p in self.root.rglob('*') if p.is_file()})


if __name__=='__main__':unittest.main()
