"""Temporary actual rasters and pinned records; only spatial metadata math."""
import copy
import unittest
from unittest.mock import patch

import rasterio
from rasterio.warp import transform_bounds
import pyproj.network
from app.dataset_registry import canonical_manifest,version_key
from app.ml import registry_spatial_normalization as api
import test_registry_raster_grid_normalization as raster_fixtures


class RegistrySpatialNormalizationTests(unittest.TestCase):
    def setUp(self):
        self.fixture=raster_fixtures.RegistryRasterGridNormalizationTests();self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups);self.store=self.fixture.store;self.rows=self.fixture.rows
        self.model=self.fixture.annual.fixture
        with rasterio.Env(PROJ_NETWORK='OFF'):
            self.envelope=list(transform_bounds('EPSG:32748','OGC:CRS84',500000,9199840,500160,9200000,densify_pts=21))

    def bbox(self,year,bounds,crs='EPSG:4326'):
        row=self.rows[year-2020];key=version_key(row['image_ref']['id'],row['image_ref']['version'])
        record=self.store.get('dataset_versions',key);record['manifest']['spatial']={'bbox':list(bounds),'crs':crs}
        manifest,digest=canonical_manifest(record['manifest']);record.update(manifest=manifest,manifest_sha256=digest)
        self.store.put('dataset_versions',record)

    def inspect(self,**kwargs):
        args={'store':self.store,'model_ref':self.model.model_ref,'training_report_sha256':self.model.report_sha,'requested_years':self.rows[:2]}
        args.update(kwargs);return api.inspect_registry_spatial_normalization(**args)

    def test_actual_two_six_scene_contains_same_get_no_new_headers_or_loads(self):
        for size in (2,6):
            opened=[];original=rasterio.io.MemoryFile.open
            def open_header(memory,*args,**kwargs):opened.append(True);return original(memory,*args,**kwargs)
            with patch.object(self.store,'get',wraps=self.store.get) as get,patch.object(rasterio.io.MemoryFile,'open',open_header):
                result=self.inspect(requested_years=self.rows[:size])
            self.assertEqual(len(result),17);self.assertEqual(result['status'],'REGISTRY_ENVELOPE_MATCHED_UNVERIFIED')
            self.assertEqual(get.call_count,1+3*size);self.assertEqual(len(opened),size)
            self.assertTrue(result['registry_bbox_contains_raster_envelope_verified']);self.assertTrue(result['artifact_bytes_verified'])
            self.assertFalse(result['raster_batch_observation']['registry_aoi_verified'])
            self.assertEqual(len(result['spatial_observations']),size)

    def test_exact_bbox_crs84_lonlat_and_broader_bbox_not_physical_coverage(self):
        self.bbox(2020,self.envelope,'OGC:CRS84');self.bbox(2021,[90,-20,130,20])
        result=self.inspect();self.assertEqual(result['status'],'REGISTRY_ENVELOPE_MATCHED_UNVERIFIED')
        self.assertFalse(result['physical_coverage_verified']);self.assertFalse(result['registry_aoi_verified'])

    def test_fixed_degree_tolerance_narrow_failure_post_read_not_checked_is_math_only(self):
        bbox=self.envelope.copy();bbox[0]+=0.5e-7;self.bbox(2020,bbox)
        self.assertEqual(self.inspect()['status'],'REGISTRY_ENVELOPE_MATCHED_UNVERIFIED')
        bbox[0]+=2e-7;self.bbox(2020,bbox)
        with patch.object(self.store,'get',wraps=self.store.get) as get:result=self.inspect(requested_years=self.rows[:3])
        self.assertEqual(result['issue'],{'code':'REGISTRY_BBOX_DOES_NOT_CONTAIN_ENVELOPE','field':'containment','year':2020})
        self.assertEqual(get.call_count,10)
        self.assertTrue(result['raster_batch_observation']['artifact_bytes_verified'])
        self.assertEqual(len(result['raster_batch_observation']['header_observations']),3)
        self.assertEqual([row['status'] for row in result['spatial_observations']],['BLOCKED','NOT_CHECKED','NOT_CHECKED'])
        self.assertFalse(result['artifact_bytes_verified'])

    def test_middle_bbox_mismatch_full_base_io_precedes_spatial_failfast(self):
        self.bbox(2021,[100,-10,104,0])
        result=self.inspect(requested_years=self.rows[:3])
        self.assertEqual([row['status'] for row in result['spatial_observations']],['MATCHED_UNVERIFIED','BLOCKED','NOT_CHECKED'])
        self.assertEqual(result['raster_batch_observation']['status'],'RASTER_GRID_MATCHED_UNVERIFIED')
        self.assertEqual(result['issue']['year'],2021)

    def test_unsupported_registry_crs_and_world_dateline_polar_internal_policy(self):
        for bounds,crs,code in (([100,-10,110,0],'EPSG:3857','REGISTRY_SPATIAL_CRS_UNSUPPORTED'),
             ([-180,-90,180,90],'EPSG:4326','SPATIAL_DATELINE_UNSUPPORTED'),
             ([100,-85,110,0],'EPSG:4326','SPATIAL_POLAR_UNSUPPORTED')):
            self.bbox(2020,bounds,crs);self.assertEqual(self.inspect()['issue']['code'],code)

    def test_transformed_invalid_dateline_polar_and_nonfinite_bounds_fail_closed(self):
        for output,code in (((179,-10,-179,-9),'SPATIAL_DATELINE_UNSUPPORTED'),((105,85,106,86),'SPATIAL_POLAR_UNSUPPORTED'),
                            ((float('nan'),-10,106,-9),'SPATIAL_BOUNDS_INVALID'),((105,-10,105,-9),'SPATIAL_BOUNDS_INVALID')):
            with patch('rasterio.warp.transform_bounds',return_value=output):result=self.inspect()
            self.assertEqual(result['issue']['code'],code);self.assertFalse(result['registry_bbox_contains_raster_envelope_verified'])

    def test_transform_target_densify_network_guard_and_fixed_exception(self):
        calls=[];original=transform_bounds
        def checked(src,dst,*bounds,**kwargs):
            self.assertEqual(dst,'OGC:CRS84');self.assertEqual(kwargs,{'densify_pts':21})
            self.assertEqual(rasterio.env.getenv()['PROJ_NETWORK'],'OFF');calls.append(True)
            return original(src,dst,*bounds,**kwargs)
        with patch('rasterio.warp.transform_bounds',checked):self.assertEqual(self.inspect()['status'],'REGISTRY_ENVELOPE_MATCHED_UNVERIFIED')
        self.assertEqual(len(calls),2)
        with patch.object(pyproj.network,'is_network_enabled',return_value=True),patch('rasterio.warp.transform_bounds',side_effect=AssertionError('no transform')):
            self.assertEqual(self.inspect()['issue']['code'],'SPATIAL_TRANSFORM_UNAVAILABLE')
        with patch('rasterio.warp.transform_bounds',side_effect=RuntimeError('secret root path')):
            result=self.inspect();self.assertEqual(result['issue']['code'],'SPATIAL_TRANSFORM_UNAVAILABLE');self.assertNotIn('secret',str(result))

    def test_base_failure_priority_no_spatial_math_global_model_invalid(self):
        self.fixture.annual.paths[0][0].write_bytes(b'tampered')
        with patch('rasterio.warp.transform_bounds',side_effect=AssertionError('no post math')):result=self.inspect()
        self.assertEqual(result['status'],'RASTER_BLOCKED');self.assertTrue(all(row['status']=='NOT_CHECKED' for row in result['spatial_observations']))
        self.model.manifest['normalization_mode']='global';self.model.bind_model()
        with patch('rasterio.warp.transform_bounds',side_effect=AssertionError('no post math')):self.assertEqual(self.inspect()['status'],'OUT_OF_SCOPE')
        with patch.object(self.store,'get',side_effect=AssertionError('no I/O')):self.assertEqual(self.inspect(requested_years=[])['status'],'INVALID_INPUT')

    def test_same_get_canonical_spatial_copy_cannot_be_replaced_after_capture(self):
        original=self.store.get;canonical=api.canonical_manifest;captured=[];counts={}
        image_key=version_key(self.rows[0]['image_ref']['id'],self.rows[0]['image_ref']['version'])
        def getter(kind,key):
            counts[key]=counts.get(key,0)+1;record=original(kind,key)
            if kind=='dataset_versions' and key==image_key:captured.append(record)
            return record
        def altered(manifest):
            result=canonical(manifest)
            if captured:captured[0]['manifest']['spatial']['bbox']=[0,0,1,1]
            return result
        with patch.object(self.store,'get',getter),patch.object(api,'canonical_manifest',altered):result=self.inspect()
        self.assertEqual(result['status'],'REGISTRY_ENVELOPE_MATCHED_UNVERIFIED');self.assertEqual(counts[image_key],1)
        self.assertEqual(result['spatial_observations'][0]['registry_bbox'],[100.,-10.,110.,0.])

    def test_inputs_db_files_and_environment_preferences_unchanged_all_false_claims(self):
        before=copy.deepcopy(self.rows);network=pyproj.network.is_network_enabled()
        files={p.relative_to(self.fixture.annual.root).as_posix():p.read_bytes() for p in self.fixture.annual.root.rglob('*') if p.is_file()}
        with patch.object(self.store,'put',side_effect=AssertionError('no writes')):result=self.inspect()
        self.assertEqual(before,self.rows);self.assertEqual(network,pyproj.network.is_network_enabled())
        self.assertEqual(files,{p.relative_to(self.fixture.annual.root).as_posix():p.read_bytes() for p in self.fixture.annual.root.rglob('*') if p.is_file()})
        for key in ('registry_aoi_verified','physical_coverage_verified','quality_report_verified','quality_mask_verified','pixel_values_verified',
                    'source_authority_verified','scientific_accuracy_validated','execution_authorized','workflow_supported'):
            self.assertIs(result[key],False)


if __name__=='__main__':unittest.main()
