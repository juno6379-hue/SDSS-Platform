"""Actual temporary GeoTIFF metadata, never model inference or pixel reads."""
import copy
import hashlib
import unittest
from unittest.mock import patch

import numpy as np
import rasterio
from rasterio.io import MemoryFile, DatasetReader
from rasterio.transform import Affine, from_origin
from app.dataset_registry import canonical_manifest,version_key
from app.ml import registry_raster_grid_normalization as api
import test_registry_temporal_normalization as temporal_fixtures


class RegistryRasterGridNormalizationTests(unittest.TestCase):
    def setUp(self):
        self.fixture=temporal_fixtures.RegistryTemporalNormalizationTests();self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.annual=self.fixture.fixture;self.store=self.fixture.store;self.rows=self.fixture.rows
        for row in self.rows:self.raster(row['year'])

    def save(self,record):
        manifest,digest=canonical_manifest(record['manifest']);record.update(manifest=manifest,manifest_sha256=digest)
        self.store.put('dataset_versions',record)

    def bind_image(self,year):
        index=year-2020;row=self.rows[index];raw=self.annual.paths[index][0].read_bytes()
        row['image_ref']['sha256']=hashlib.sha256(raw).hexdigest()
        key=version_key(row['image_ref']['id'],row['image_ref']['version']);record=self.store.get('dataset_versions',key)
        record['manifest']['sha256']=row['image_ref']['sha256'];self.save(record)
        key=version_key(row['evidence_ref']['id'],row['evidence_ref']['version']);record=self.store.get('dataset_versions',key)
        for parent in record['manifest']['lineage']:
            if parent.get('role')=='normalization_input_image':parent['sha256']=row['image_ref']['sha256']
        self.save(record)

    def raster(self,year,width=16,height=16,count=6,crs='EPSG:32748',transform=None,names=True):
        path=self.annual.paths[year-2020][0]
        if path.exists():path.unlink()  # Temp fixture only; do not ask GDAL to parse/delete an old VRT.
        with rasterio.open(path,'w',driver='GTiff',width=width,height=height,count=count,crs=crs,
                           transform=from_origin(500000,9200000,10,10) if transform is None else transform,dtype='uint16') as target:
            target.write(np.zeros((count,height,width),dtype='uint16'))
            if names:target.descriptions=tuple(self.annual.fixture.scene.names[:count])
        self.bind_image(year)

    def inspect(self,**kwargs):
        model=self.annual.fixture
        args={'store':self.store,'model_ref':model.model_ref,'training_report_sha256':model.report_sha,'requested_years':self.rows[:2]}
        args.update(kwargs);return api.inspect_registry_raster_grid_normalization(**args)

    def test_two_six_actual_headers_cross_grid_same_get_and_full_flags_only(self):
        for size in (2,6):
            with patch.object(self.store,'get',wraps=self.store.get) as get:result=self.inspect(requested_years=self.rows[:size])
            self.assertEqual(len(result),19);self.assertEqual(result['status'],'RASTER_GRID_MATCHED_UNVERIFIED')
            self.assertEqual(get.call_count,1+3*size);self.assertTrue(result['raster_header_verified']);self.assertTrue(result['cross_scene_grid_verified'])
            self.assertTrue(result['artifact_bytes_verified']);self.assertTrue(result['registry_temporal_year_verified'])
            self.assertEqual(len(result['header_observations']),size)
            self.assertEqual(result['header_observations'][0]['header']['bounds'],[500000.,9199840.,500160.,9200000.])
            self.assertFalse(result['registry_aoi_verified']);self.assertFalse(result['temporal_batch_observation']['physical_acquisition_year_verified'])

    def test_memoryfile_driver_forced_pam_disabled_and_no_pixel_or_mask_reads(self):
        opened=[];original=MemoryFile.open
        def checked(memory,*args,**kwargs):
            self.assertEqual(kwargs.get('driver'),'GTiff');opened.append(True)
            self.assertEqual(rasterio.env.getenv()['GDAL_PAM_ENABLED'],'NO')
            self.assertEqual(rasterio.env.getenv()['GDAL_DISABLE_READDIR_ON_OPEN'],'EMPTY_DIR')
            return original(memory,*args,**kwargs)
        with (patch.object(MemoryFile,'open',checked),patch.object(DatasetReader,'read',side_effect=AssertionError('no pixel reads')),
              patch.object(DatasetReader,'read_masks',side_effect=AssertionError('no mask reads'))):result=self.inspect()
        self.assertEqual(result['status'],'RASTER_GRID_MATCHED_UNVERIFIED');self.assertEqual(len(opened),2)

    def test_shifted_second_grid_failfast_preserves_first_header_and_later_unchecked(self):
        self.raster(2021,transform=from_origin(500010,9200000,10,10))
        result=self.inspect(requested_years=self.rows[:3]);self.assertEqual(result['status'],'RASTER_BLOCKED')
        self.assertEqual(result['issue'],{'code':'RASTER_GRID_MISMATCH','field':'grid','year':2021})
        self.assertEqual([r['status'] for r in result['header_observations']],['MATCHED_UNVERIFIED','BLOCKED'])
        self.assertIsNotNone(result['header_observations'][1]['header'])
        rows=result['temporal_batch_observation']['batch_observation']['rows']
        self.assertEqual([r['status'] for r in rows],['MATCHED_UNVERIFIED','BLOCKED','NOT_CHECKED'])
        self.assertFalse(result['raster_header_verified']);self.assertFalse(result['cross_scene_grid_verified'])

    def test_descriptions_missing_wrong_order_registered_names_and_count_reject(self):
        self.raster(2020,names=False);self.assertEqual(self.inspect()['issue']['code'],'RASTER_BAND_SIGNATURE_INVALID')
        self.raster(2020)
        path=self.annual.paths[0][0]
        with rasterio.open(path,'r+') as target:target.descriptions=tuple(reversed(self.annual.fixture.scene.names))
        self.bind_image(2020);self.assertEqual(self.inspect()['issue']['code'],'RASTER_BAND_SIGNATURE_INVALID')
        self.raster(2020,count=5);self.assertEqual(self.inspect()['issue']['field'],'shape')
        self.raster(2020)
        key=version_key(self.rows[0]['image_ref']['id'],self.rows[0]['image_ref']['version']);record=self.store.get('dataset_versions',key)
        del record['manifest']['source']['band_names'];self.save(record)
        self.assertEqual(self.inspect()['issue']['code'],'RASTER_BAND_SIGNATURE_INVALID')

    def test_geographic_feet_crs_northup_and_shape_policy(self):
        for crs in ('EPSG:4326','EPSG:2277'):
            self.raster(2020,crs=crs);self.assertEqual(self.inspect()['issue']['field'],'crs')
        for transform in (Affine(10,1,500000,0,-10,9200000),Affine(-10,0,500000,0,-10,9200000),Affine(10,0,500000,0,10,9200000)):
            self.raster(2020,transform=transform);self.assertEqual(self.inspect()['issue']['field'],'transform')
        self.raster(2020,width=1025);self.assertEqual(self.inspect()['issue']['field'],'shape')
        self.raster(2020,width=1,height=1);self.raster(2021,width=1,height=1)
        self.assertEqual(self.inspect()['status'],'RASTER_GRID_MATCHED_UNVERIFIED')

    def test_finite_coefficients_still_reject_overflowed_or_degenerate_computed_bounds(self):
        for transform in (Affine(1e307,0,1e308,0,-1,1),Affine(1,0,1e300,0,-1,1)):
            self.raster(2020,transform=transform)
            result=self.inspect();self.assertEqual(result['issue']['code'],'RASTER_HEADER_INVALID')
            self.assertEqual(result['issue']['field'],'bounds')

    def test_nonraster_vrt_and_tamper_reject_before_memoryfile(self):
        for raw in (b'not a raster',b'<VRTDataset><SourceFilename>/vsicurl/https://example.invalid/private</SourceFilename></VRTDataset>'):
            self.annual.paths[0][0].write_bytes(raw);self.bind_image(2020)
            with patch.object(MemoryFile,'open',side_effect=AssertionError('no GDAL open')):
                self.assertEqual(self.inspect()['issue']['code'],'RASTER_FORMAT_UNSUPPORTED')
        self.raster(2020);self.annual.paths[0][0].write_bytes(b'tampered but no repin')
        self.assertEqual(self.inspect()['issue']['code'],'SHA256_MISMATCH')

    def test_access_and_type_guard_before_image_bytes_and_size_bound(self):
        key=version_key(self.rows[0]['image_ref']['id'],self.rows[0]['image_ref']['version']);original=self.store.get('dataset_versions',key)
        for field,value,code in (('access_class','RESTRICTED','ACCESS_DECLARATION_BLOCKED'),('data_type','document','REGISTRY_TYPE_MISMATCH')):
            record=copy.deepcopy(original);record['manifest'][field]=value;self.save(record)
            with patch.object(api,'_snapshot',side_effect=AssertionError('must not read image')):
                self.assertEqual(self.inspect()['issue']['code'],code)
        self.store.put('dataset_versions',original)
        with patch.object(api,'MAX_IMAGE',1):self.assertEqual(self.inspect()['issue']['code'],'FILE_LIMIT')

    def test_temporal_and_late_file_failure_do_not_promote_header_partial_flags(self):
        self.fixture.temporal(2021,{'start':'2022-01-01T00:00:00Z','end':'2022-12-31T00:00:00Z','calendar':'gregorian'})
        result=self.inspect();self.assertEqual(result['status'],'TEMPORAL_BLOCKED')
        self.assertEqual([row['status'] for row in result['header_observations']],['MATCHED_UNVERIFIED','MATCHED_UNVERIFIED'])
        self.assertFalse(result['raster_header_verified']);self.assertFalse(result['cross_scene_grid_verified'])
        self.fixture.temporal(2021,{'start':'2021-01-01T00:00:00Z','end':'2021-12-31T00:00:00Z','calendar':'gregorian'})
        self.annual.paths[1][2].write_bytes(b'changed metadata')
        result=self.inspect();self.assertEqual(result['status'],'SCENE_BLOCKED');self.assertFalse(result['artifact_bytes_verified'])

    def test_global_model_failure_invalid_no_header_reads_and_mutable_invalid_stays_io_zero(self):
        model=self.annual.fixture;model.manifest['normalization_mode']='global';model.bind_model()
        with patch.object(api,'_snapshot',side_effect=AssertionError('no image snapshots')):result=self.inspect()
        self.assertEqual(result['status'],'OUT_OF_SCOPE');self.assertEqual(result['header_observations'],[])
        model.checkpoint.write_bytes(b'changed model')
        with patch.object(api,'_snapshot',side_effect=AssertionError('no image snapshots')):self.assertEqual(self.inspect()['status'],'MODEL_BLOCKED')
        with patch.object(self.store,'get',side_effect=AssertionError('no I/O')):self.assertEqual(self.inspect(requested_years=[])['status'],'INVALID_INPUT')

    def test_db_files_inputs_unchanged_and_all_nonheader_claims_false(self):
        before=copy.deepcopy(self.rows)
        files={p.relative_to(self.annual.root).as_posix():p.read_bytes() for p in self.annual.root.rglob('*') if p.is_file()}
        with patch.object(self.store,'put',side_effect=AssertionError('no writes')):result=self.inspect()
        self.assertEqual(before,self.rows)
        self.assertEqual(files,{p.relative_to(self.annual.root).as_posix():p.read_bytes() for p in self.annual.root.rglob('*') if p.is_file()})
        for field in ('registry_aoi_verified','quality_report_verified','quality_mask_verified','pixel_values_verified','state_dict_verified',
                      'source_authority_verified','scientific_accuracy_validated','execution_authorized','workflow_supported'):
            self.assertIs(result[field],False)


if __name__=='__main__':unittest.main()
