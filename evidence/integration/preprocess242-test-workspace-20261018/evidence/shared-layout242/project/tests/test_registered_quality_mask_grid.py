"""Real temporary GTiff headers, no pixel reads during the diagnostic."""
import copy
import unittest
from unittest.mock import patch

import numpy as np
import rasterio
from rasterio.transform import from_origin
import test_registered_quality_mask_files as fixtures
from app.ml import registered_quality_mask_grid as api


class RegisteredQualityMaskGridTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.RegisteredQualityMaskFilesTests()
        self.fixture.setUp(); self.addCleanup(self.fixture.doCleanups)
        self.names = list(api.BAND_NAMES)
        self.write(0); self.write(2)
        self.fixture.manifests[0]['source']['band_names'] = self.names.copy()
        self.bind()

    def write(self, index, **overrides):
        path = self.fixture.paths[index]
        if path.exists(): path.unlink()
        profile = {'driver':'GTiff', 'width':16, 'height':16, 'count':6 if index == 0 else 1,
            'dtype':'uint16' if index == 0 else 'uint8', 'crs':'EPSG:32748', 'transform':from_origin(500000,9000000,10,10)}
        profile.update(overrides)
        with rasterio.open(path, 'w', **profile) as dataset:
            dataset.write(np.zeros((profile['count'], profile['height'], profile['width']), dtype=profile['dtype']))
            if index == 0 and profile['count'] == 6:
                dataset.descriptions = tuple(self.names)

    def bind(self):
        f = self.fixture
        for i in (0, 2):
            f.refs[i]['sha256'] = fixtures.sha(f.paths[i].read_bytes())
            f.manifests[i]['sha256'] = f.refs[i]['sha256']; f.save(i)
        f.envelope['image_ref'] = dict(f.refs[0]); f.envelope['mask_ref'] = dict(f.refs[2])
        f.manifests[1]['lineage'] = [{**f.refs[0],'role':'quality_input_image'}, {**f.refs[2],'role':'quality_input_mask'}]
        f.report()

    def read(self):
        return api.inspect_registered_quality_mask_grid(self.fixture.store, *self.fixture.refs)

    def test_actual_headers_exact20_three_get_and_no_pixel_reads_or_writes(self):
        f = self.fixture; before = copy.deepcopy(f.refs)
        with (patch.object(f.store,'get',wraps=f.store.get) as get,
              patch.object(f.store,'put',side_effect=AssertionError('write')),
              patch('rasterio.io.DatasetReader.read',side_effect=AssertionError('pixels')),
              patch('rasterio.io.DatasetReader.read_masks',side_effect=AssertionError('mask pixels'))):
            result = self.read()
        self.assertEqual(len(result),20); self.assertEqual(get.call_count,3)
        self.assertEqual(result['status'],'REGISTERED_QUALITY_MASK_GRID_MATCHED_UNVERIFIED')
        self.assertTrue(result['artifact_bytes_verified']); self.assertTrue(result['image_mask_grid_verified'])
        self.assertEqual(result['mask_header']['count'],1); self.assertEqual(result['mask_header']['dtype'],'uint8')
        self.assertTrue(all(result[key] is False for key in api.FALSE_FIELDS)); self.assertEqual(before,f.refs)

    def test_original131_failure_prevents_all_header_reads(self):
        self.fixture.paths[1].write_bytes(b'changed')
        with patch.object(api,'_header',side_effect=AssertionError('header')):
            result = self.read()
        self.assertFalse(result['quality_mask_observation']['artifact_bytes_verified'])
        self.assertIsNone(result['image_header']); self.assertIsNone(result['mask_header'])

    def test_mask_shift_crs_shape_mismatch_keeps_parsed_headers_and_base_success(self):
        for values in ({'transform':from_origin(500010,9000000,10,10)}, {'width':17}, {'crs':'EPSG:32749'}):
            self.write(2,**values); self.bind(); result = self.read()
            self.assertEqual(result['issue']['code'],'IMAGE_MASK_GRID_MISMATCH')
            self.assertTrue(result['quality_mask_observation']['artifact_bytes_verified'])
            self.assertIsNotNone(result['image_header']); self.assertIsNotNone(result['mask_header'])
            self.assertFalse(result['image_mask_headers_verified']); self.assertFalse(result['artifact_bytes_verified'])

    def test_mask_count_dtype_geographic_rotated_and_oversize_block(self):
        for values in ({'count':2}, {'dtype':'uint16'}, {'crs':'EPSG:4326'}, {'width':1025},
                       {'transform':rasterio.Affine(10,1,500000,0,-10,9000000)}):
            self.write(2,**values); self.bind(); result = self.read()
            self.assertEqual(result['issue']['code'],'MASK_HEADER_INVALID')
            self.assertFalse(result['image_mask_grid_verified'])

    def test_opaque_and_vrt_do_not_enter_memoryfile(self):
        for raw in (b'opaque mask', b'<VRTDataset rasterXSize="16" rasterYSize="16"/>'):
            self.fixture.paths[2].write_bytes(raw); self.bind()
            # The image header legitimately opens; only mask parser must reject before GDAL.
            with patch('rasterio.io.MemoryFile',wraps=rasterio.io.MemoryFile) as memory:
                result = self.read()
            self.assertEqual(result['issue']['code'],'MASK_FORMAT_UNSUPPORTED'); self.assertEqual(memory.call_count,1)

    def test_source_band_declaration_absent_or_changed_not_invented(self):
        source = self.fixture.manifests[0]['source']
        for names in (None, list(reversed(self.names))):
            source.pop('band_names',None)
            if names is not None: source['band_names'] = names
            self.fixture.save(0)
            with patch.object(api,'_header',side_effect=AssertionError('no image header')):
                result = self.read()
            self.assertEqual(result['issue']['code'],'RASTER_BAND_SIGNATURE_INVALID')
            self.assertTrue(result['quality_mask_observation']['artifact_bytes_verified'])

    def test_image_actual_descriptions_and_legacy_parser_role_mapping(self):
        with rasterio.open(self.fixture.paths[0],'r+') as dataset:
            dataset.descriptions = (None,)*6
        self.bind(); result = self.read()
        self.assertEqual(result['issue'],{'code':'RASTER_BAND_SIGNATURE_INVALID','field':'image'})
        self.assertIsNone(result['image_header']); self.assertTrue(result['quality_mask_observation']['artifact_bytes_verified'])

    def test_post131_byte_change_is_rechecked_without_store_reread(self):
        original = api.read_registered_quality_mask_files
        for index in (0,2):
            old = self.fixture.paths[index].read_bytes()
            def change(*args):
                result = original(*args)
                self.fixture.paths[index].write_bytes(b'changed after131')
                return result
            with patch.object(api,'read_registered_quality_mask_files',side_effect=change):
                result = self.read()
            self.assertTrue(result['quality_mask_observation']['artifact_bytes_verified'])
            self.assertEqual(result['issue'],{'code':'SHA256_MISMATCH','field':'image' if index==0 else 'mask'})
            self.assertFalse(result['artifact_bytes_verified']); self.fixture.paths[index].write_bytes(old)

    def test_physical_alias_fails_six_vs_one_band_requirement(self):
        self.fixture.manifests[2]['artifact_uri'] = self.fixture.paths[0].name
        self.fixture.refs[2]['sha256'] = self.fixture.refs[0]['sha256']
        self.fixture.manifests[2]['sha256'] = self.fixture.refs[2]['sha256']; self.fixture.save(2)
        self.fixture.envelope['mask_ref'] = dict(self.fixture.refs[2])
        self.fixture.manifests[1]['lineage'][1] = {**self.fixture.refs[2],'role':'quality_input_mask'}
        self.fixture.report(); result = self.read()
        self.assertTrue(result['quality_mask_observation']['artifact_bytes_verified'])
        self.assertEqual(result['issue']['code'],'MASK_HEADER_INVALID')

    def test_same_captured_manifest_copy_and_input_invalid_io0(self):
        original = self.fixture.store.get
        record = original('dataset_versions',api.version_key(self.fixture.refs[0]['id'],self.fixture.refs[0]['version']))
        class MutatingStore:
            root = self.fixture.root
            def get(inner,kind,key):
                if key == record['id']: return record
                record['manifest']['source'].pop('band_names',None)
                return original(kind,key)
        result = api.inspect_registered_quality_mask_grid(MutatingStore(),*self.fixture.refs)
        self.assertTrue(result['artifact_bytes_verified'])
        with patch.object(self.fixture.store,'get',side_effect=AssertionError('IO')):
            result = api.inspect_registered_quality_mask_grid(self.fixture.store,None,None,None)
        self.assertEqual(result['issue']['code'],'INVALID_INPUT')


if __name__ == '__main__':
    unittest.main()
