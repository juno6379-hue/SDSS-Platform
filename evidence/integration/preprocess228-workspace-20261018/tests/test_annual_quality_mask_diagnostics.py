"""Real temporary annual model/registry/GTiff + explicit binary masks."""
import copy
import hashlib
import json
import unittest
from unittest.mock import patch

import numpy as np
import rasterio
from rasterio.transform import from_origin
from app.dataset_registry import version_key
from app.ml import annual_quality_mask_diagnostics as api
import test_registry_raster_grid_normalization as fixtures


class AnnualQualityMaskDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.raster = fixtures.RegistryRasterGridNormalizationTests()
        self.raster.setUp(); self.addCleanup(self.raster.doCleanups)
        self.store = self.raster.store; self.rows = copy.deepcopy(self.raster.rows)
        self.model = self.raster.annual.fixture
        self.mask_paths = []
        for row in self.rows:
            key = version_key(row['image_ref']['id'],row['image_ref']['version'])
            image = self.store.get('dataset_versions',key)
            image['manifest']['spatial']['bbox'] = [100,-20,120,0]
            image_path = self.store.root / image['manifest']['artifact_uri']
            mask_path = image_path.parent / 'mask.tif'; self.mask_paths.append(mask_path)
            with rasterio.open(mask_path,'w',driver='GTiff',width=16,height=16,count=1,dtype='uint8',crs='EPSG:32748',
                               transform=from_origin(500000,9200000,10,10)) as target:
                target.write(np.ones((1,16,16),dtype='uint8'))
            mask_ref = {'id':f"mask-{row['year']}",'version':'v1','sha256':hashlib.sha256(mask_path.read_bytes()).hexdigest()}
            report_path = image_path.parent / 'quality.json'
            report_path.write_text(json.dumps({'schema_version':1,'scope':'LCLUC_QUALITY_MASK_EVIDENCE',
                'image_ref':row['image_ref'],'mask_ref':mask_ref,'quality_status':image['manifest']['quality_status']}),encoding='utf-8')
            quality_ref = {'id':f"quality-{row['year']}",'version':'v1','sha256':hashlib.sha256(report_path.read_bytes()).hexdigest()}
            image['manifest']['quality_report_ref'] = report_path.relative_to(self.store.root).as_posix()
            self.raster.save(image)
            for ref,path,kind in ((mask_ref,mask_path,'raster'),(quality_ref,report_path,'document')):
                manifest = copy.deepcopy(image['manifest'])
                manifest.update(dataset_id=ref['id'],version=ref['version'],sha256=ref['sha256'],data_type=kind,
                    artifact_uri=path.relative_to(self.store.root).as_posix(),lineage=[])
                if kind == 'raster':
                    manifest['source']['mask_semantics'] = {'schema_version':1,'kind':'binary_validity','valid_value':1,'invalid_value':0}
                else:
                    manifest['lineage'] = [{**row['image_ref'],'role':'quality_input_image'},{**mask_ref,'role':'quality_input_mask'}]
                self.raster.save({'id':version_key(ref['id'],ref['version']),'manifest':manifest})
            row.update(quality_report_ref=quality_ref,mask_ref=mask_ref)

    def inspect(self,rows=None):
        return api.inspect_annual_quality_mask_diagnostics(self.store,self.model.model_ref,self.model.report_sha,
            self.rows[:2] if rows is None else rows)

    def test_actual_two_six_rows_one_model_get1plus6n_full_flags(self):
        for count in (2,6):
            with patch.object(self.store,'get',wraps=self.store.get) as get:
                result = self.inspect(self.rows[:count])
            self.assertEqual(result['status'],'ANNUAL_QUALITY_MASK_MATCHED_UNVERIFIED')
            self.assertEqual(len(result),22); self.assertEqual(get.call_count,1+6*count)
            self.assertEqual(result['spatial_observation_calls'],1); self.assertEqual(result['mask_observation_calls'],count)
            self.assertEqual(result['checked_rows'],count); self.assertTrue(result['registry_manifest_join_verified'])
            self.assertTrue(all(result[key] is False for key in api.FALSE_FIELDS))
            self.assertEqual([row['mask_observation']['counts']['valid_pixels'] for row in result['mask_observations']],[256]*count)

    def test_all_rows_validated_before_any_store_io(self):
        bad = []
        for key,value in (('year',True),('mask_ref',None),('quality_report_ref',{**self.rows[0]['quality_report_ref'],'version':'latest'})):
            rows = copy.deepcopy(self.rows); rows[-1][key] = value; bad.append(rows)
        for mutate in ('extra','duplicate','reverse'):
            rows = copy.deepcopy(self.rows[:2])
            if mutate == 'extra': rows[0]['command'] = 'run'
            elif mutate == 'duplicate': rows[0]['mask_ref'] = dict(rows[0]['image_ref'])
            else: rows.reverse()
            bad.append(rows)
        with patch.object(self.store,'get',side_effect=AssertionError('noIO')):
            for rows in bad:
                result = self.inspect(rows); self.assertEqual(result['status'],'INVALID_INPUT')
                self.assertEqual(result['spatial_observation_calls'],0); self.assertEqual(result['mask_observations'],[])

    def test_spatial_fail_prevents_all_mask_calls_but_retains_original(self):
        key = version_key(self.rows[0]['image_ref']['id'],self.rows[0]['image_ref']['version'])
        record = self.store.get('dataset_versions',key); record['manifest']['spatial']['bbox'] = [0,-20,1,0]; self.raster.save(record)
        with patch.object(api,'inspect_registered_binary_mask_values',side_effect=AssertionError('no mask')) as mask:
            result = self.inspect()
        mask.assert_not_called(); self.assertEqual(result['status'],'ANNUAL_SPATIAL_BLOCKED')
        self.assertEqual(result['annual_spatial_observation']['status'],'SPATIAL_BLOCKED')
        self.assertTrue(all(row['status']=='NOT_CHECKED' for row in result['mask_observations']))

    def test_middle_mask_failure_partial_and_later_not_checked_after_all130_io(self):
        self.mask_paths[1].write_bytes(b'changed')
        result = self.inspect(self.rows[:3])
        self.assertEqual(result['status'],'MASK_BLOCKED'); self.assertEqual(result['checked_rows'],2)
        self.assertEqual([r['status'] for r in result['mask_observations']],['MATCHED_UNVERIFIED','BLOCKED','NOT_CHECKED'])
        self.assertTrue(result['annual_spatial_observation']['artifact_bytes_verified'])
        self.assertTrue(result['mask_observations'][0]['registry_manifest_join_verified'])
        self.assertFalse(result['artifact_bytes_verified']); self.assertFalse(result['mask_values_verified'])

    def test_registry_metadata_change_same_filepins_rejected_after_count_observation(self):
        original = api.inspect_registry_spatial_normalization
        def change(*args):
            result = original(*args)
            key = version_key(self.rows[1]['image_ref']['id'],self.rows[1]['image_ref']['version'])
            record = self.store.get('dataset_versions',key)
            record['manifest']['source']['institution'] = 'CHANGED_CALLER_DECLARATION'
            self.raster.save(record)
            return result
        with patch.object(api,'inspect_registry_spatial_normalization',side_effect=change):
            result = self.inspect(self.rows[:3])
        self.assertEqual(result['issue'],{'code':'REGISTRY_IMAGE_MANIFEST_CHANGED','field':'image_manifest','year':2021})
        self.assertTrue(result['mask_observations'][1]['mask_observation']['mask_values_verified'])
        self.assertFalse(result['mask_observations'][1]['registry_manifest_join_verified'])
        self.assertEqual(result['mask_observations'][2]['status'],'NOT_CHECKED')

    def test_missing_or_duplicate_image_bindings_fail_closed_no_join(self):
        original = api.inspect_registered_binary_mask_values
        for duplicate in (False,True):
            def corrupt(*args):
                result = original(*args)
                bindings = result['grid_observation']['quality_mask_observation']['registry_bindings']
                if duplicate: bindings.append(copy.deepcopy(bindings[0]))
                else: bindings[:] = [v for v in bindings if v['role'] != 'image']
                return result
            with patch.object(api,'inspect_registered_binary_mask_values',side_effect=corrupt):
                result = self.inspect()
            self.assertEqual(result['issue']['code'],'REGISTRY_IMAGE_MANIFEST_CHANGED')
            self.assertFalse(result['registry_manifest_join_verified'])

    def test_input_snapshot_survives_mutation_and_no_writes_during_success(self):
        rows = copy.deepcopy(self.rows[:2]); original = api.inspect_registry_spatial_normalization
        def change(*args):
            rows[1]['mask_ref']['sha256'] = '0'*64
            return original(*args)
        with (patch.object(api,'inspect_registry_spatial_normalization',side_effect=change),
              patch.object(self.store,'put',side_effect=AssertionError('no write'))):
            result = self.inspect(rows)
        self.assertTrue(result['artifact_bytes_verified'])

    def test_join_missing_malformed_digests_or_temporal_year_fail_closed(self):
        spatial = api.inspect_registry_spatial_normalization
        mask = api.inspect_registered_binary_mask_values
        base = spatial(self.store,self.model.model_ref,self.model.report_sha,
            [{k:r[k] for k in ('year','image_ref','evidence_ref','metadata_ref')} for r in self.rows[:2]])
        observation = mask(self.store,self.rows[0]['image_ref'],self.rows[0]['quality_report_ref'],self.rows[0]['mask_ref'])
        for bad in (None,True,'A'*64,'short'):
            fake_spatial = copy.deepcopy(base); fake_mask = copy.deepcopy(observation)
            fake_spatial['raster_batch_observation']['temporal_batch_observation']['temporal_observations'][0]['manifest_sha256'] = bad
            fake_mask['grid_observation']['quality_mask_observation']['registry_bindings'][0]['manifest_sha256'] = bad
            with (patch.object(api,'inspect_registry_spatial_normalization',return_value=fake_spatial),
                  patch.object(api,'inspect_registered_binary_mask_values',return_value=fake_mask)):
                result = self.inspect()
            self.assertEqual(result['issue']['code'],'REGISTRY_IMAGE_MANIFEST_CHANGED')
        fake_spatial = copy.deepcopy(base)
        fake_spatial['raster_batch_observation']['temporal_batch_observation']['temporal_observations'][0]['year'] = 2000
        with patch.object(api,'inspect_registry_spatial_normalization',return_value=fake_spatial),patch.object(api,'inspect_registered_binary_mask_values') as masks:
            result = self.inspect()
        masks.assert_not_called(); self.assertEqual(result['status'],'ANNUAL_SPATIAL_BLOCKED')

    def test_global_model_wrapped_and_stage_exception_sanitized(self):
        self.model.manifest['normalization_mode'] = 'global'; self.model.bind_model()
        with patch.object(self.store,'get',wraps=self.store.get) as get:
            result = self.inspect()
        self.assertEqual(get.call_count,1); self.assertEqual(result['status'],'ANNUAL_SPATIAL_BLOCKED')
        self.assertEqual(result['annual_spatial_observation']['status'],'OUT_OF_SCOPE')
        self.assertEqual(result['mask_observation_calls'],0)
        with patch.object(api,'inspect_registry_spatial_normalization',side_effect=RuntimeError('SECRET')):
            result = self.inspect()
        self.assertNotIn('SECRET',str(result)); self.assertEqual(result['issue']['code'],'ANNUAL_SPATIAL_BLOCKED')


if __name__ == '__main__':
    unittest.main()
