"""Temporary explicit binary masks; this diagnostic reads only the mask band."""
import copy
import unittest
from unittest.mock import patch

import numpy as np
import rasterio
import test_registered_quality_mask_grid as fixtures
from app.ml import registered_binary_mask_values as api


class RegisteredBinaryMaskValuesTests(unittest.TestCase):
    def setUp(self):
        self.grid = fixtures.RegisteredQualityMaskGridTests()
        self.grid.setUp(); self.addCleanup(self.grid.doCleanups)
        self.fixture = self.grid.fixture
        self.declaration = {'schema_version':1,'kind':'binary_validity','valid_value':1,'invalid_value':0}
        self.fixture.manifests[2]['source']['mask_semantics'] = copy.deepcopy(self.declaration)
        self.fixture.save(2)

    def read(self):
        return api.inspect_registered_binary_mask_values(self.fixture.store,*self.fixture.refs)

    def values(self, array):
        with rasterio.open(self.fixture.paths[2],'r+') as dataset:
            dataset.write(array,1)
        self.grid.bind()

    def test_actual_mixed_counts_exact19_get3_mask_read1_image_read0(self):
        values = np.zeros((16,16),dtype='uint8'); values[:5,:] = 1
        self.values(values)
        original = rasterio.io.DatasetReader.read
        calls = []
        def read(dataset,*args,**kwargs):
            calls.append((dataset.count,args,kwargs))
            return original(dataset,*args,**kwargs)
        with (patch.object(self.fixture.store,'get',wraps=self.fixture.store.get) as get,
              patch.object(self.fixture.store,'put',side_effect=AssertionError('write')),
              patch('rasterio.io.DatasetReader.read',new=read),
              patch('rasterio.io.DatasetReader.read_masks',side_effect=AssertionError('read_masks'))):
            result = self.read()
        self.assertEqual(len(result),19); self.assertEqual(get.call_count,3)
        self.assertEqual(calls,[(1,(1,),{'masked':False})])
        self.assertEqual(result['counts'],{'valid_pixels':80,'invalid_pixels':176,'total_pixels':256})
        self.assertTrue(result['mask_values_verified']); self.assertTrue(result['artifact_bytes_verified'])
        self.assertTrue(all(result[key] is False for key in api.FALSE_FIELDS))

    def test_all_zero_and_all_one_no_minimum_validity_policy(self):
        for value in (0,1):
            self.values(np.full((16,16),value,dtype='uint8')); result = self.read()
            self.assertEqual(result['counts']['valid_pixels'],256*value)
            self.assertFalse(result['minimum_validity_policy_verified'])

    def test_255_scl_and_arbitrary_values_block_without_counts(self):
        for value in (2,4,255):
            values = np.zeros((16,16),dtype='uint8'); values[0,0] = value
            self.values(values); result = self.read()
            self.assertEqual(result['issue']['code'],'MASK_VALUES_NOT_BINARY')
            self.assertTrue(result['mask_declaration_verified']); self.assertIsNone(result['counts'])
            self.assertFalse(result['artifact_bytes_verified'])

    def test_missing_extra_bool_or_swapped_declaration_never_inferred(self):
        source = self.fixture.manifests[2]['source']
        for value in (None, {}, {**self.declaration,'extra':0}, {**self.declaration,'schema_version':True},
                      {**self.declaration,'valid_value':True}, {**self.declaration,'invalid_value':False},
                      {**self.declaration,'valid_value':0,'invalid_value':1}, {**self.declaration,'kind':'SCL'}):
            source.pop('mask_semantics',None)
            if value is not None: source['mask_semantics'] = value
            self.fixture.save(2)
            with patch('rasterio.io.DatasetReader.read',side_effect=AssertionError('no read')):
                result = self.read()
            self.assertEqual(result['issue']['code'],'MASK_DECLARATION_INVALID')
            self.assertTrue(result['grid_observation']['artifact_bytes_verified'])
            self.assertFalse(result['mask_declaration_verified'])

    def test_nodata_and_internal_mask_rejected_before_pixel_read(self):
        self.grid.write(2,nodata=0); self.grid.bind()
        with patch('rasterio.io.DatasetReader.read',side_effect=AssertionError('no read')):
            result = self.read()
        self.assertEqual(result['issue']['code'],'MASK_INTRINSIC_VALIDITY_UNSUPPORTED')
        self.grid.write(2); self.grid.bind()
        with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=True):
            with rasterio.open(self.fixture.paths[2],'r+') as dataset:
                dataset.write_mask(np.full((16,16),255,dtype='uint8'))
        self.grid.bind()
        with patch('rasterio.io.DatasetReader.read',side_effect=AssertionError('no read')):
            result = self.read()
        self.assertEqual(result['issue']['code'],'MASK_INTRINSIC_VALIDITY_UNSUPPORTED')

    def test_132_failure_prevents_value_reader(self):
        self.fixture.paths[1].write_bytes(b'changed')
        with patch.object(api,'_binary_counts',side_effect=AssertionError('no values')):
            result = self.read()
        self.assertFalse(result['grid_observation']['artifact_bytes_verified'])
        self.assertIsNone(result['counts']); self.assertFalse(result['mask_declaration_verified'])

    def test_mask_changed_after132_rejected_third_sha_nested_success_preserved(self):
        original = api.inspect_registered_quality_mask_grid
        def changed(*args):
            result = original(*args)
            self.fixture.paths[2].write_bytes(b'changed after132')
            return result
        with patch.object(api,'inspect_registered_quality_mask_grid',side_effect=changed):
            result = self.read()
        self.assertTrue(result['grid_observation']['artifact_bytes_verified'])
        self.assertEqual(result['issue'],{'code':'SHA256_MISMATCH','field':'mask'})
        self.assertTrue(result['mask_declaration_verified']); self.assertIsNone(result['counts'])

    def test_same_get_snapshot_and_no_extra_store_or_file_mutation(self):
        original = self.fixture.store.get
        key = api.version_key(self.fixture.refs[2]['id'],self.fixture.refs[2]['version'])
        record = original('dataset_versions',key)
        original_call = api.inspect_registered_quality_mask_grid
        def observe(store,*refs):
            result = original_call(store,*refs)
            record['manifest']['source'].pop('mask_semantics',None)
            return result
        def getter(kind,identifier):
            return record if identifier == key else original(kind,identifier)
        before = {str(path):path.read_bytes() for path in self.fixture.root.rglob('*') if path.is_file()}
        with (patch.object(self.fixture.store,'get',side_effect=getter) as get,
              patch.object(api,'inspect_registered_quality_mask_grid',side_effect=observe)):
            result = self.read()
        self.assertTrue(result['artifact_bytes_verified']); self.assertEqual(get.call_count,3)
        self.assertEqual(before,{str(path):path.read_bytes() for path in self.fixture.root.rglob('*') if path.is_file()})

    def test_invalid_refs_io0_and_headers_rechecked_without_extra_open(self):
        with patch.object(self.fixture.store,'get',side_effect=AssertionError('IO')):
            result = api.inspect_registered_binary_mask_values(self.fixture.store,None,None,None)
        self.assertEqual(result['issue']['code'],'INVALID_INPUT')
        raw = self.fixture.paths[2].read_bytes()
        original = api.inspect_registered_quality_mask_grid
        def tamper_header(*args):
            result = original(*args); result['mask_header']['width'] += 1
            return result
        with patch.object(api,'inspect_registered_quality_mask_grid',side_effect=tamper_header):
            result = self.read()
        self.assertEqual(result['issue']['code'],'MASK_HEADER_CHANGED')
        with patch('rasterio.io.MemoryFile',wraps=rasterio.io.MemoryFile) as memory:
            self.assertEqual(api._binary_counts(raw,original(self.fixture.store,*self.fixture.refs)['mask_header'])['total_pixels'],256)
        # Two132 header opens plus exactly one133 mask metadata/read open.
        self.assertEqual(memory.call_count,3)


if __name__ == '__main__':
    unittest.main()
