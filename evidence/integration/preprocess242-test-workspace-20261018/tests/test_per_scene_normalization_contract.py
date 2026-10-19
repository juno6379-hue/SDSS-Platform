"""Synthetic declarations only: no source files, image reads or execution."""
import ast
import copy
from pathlib import Path
import unittest
from unittest.mock import patch

from app.ml.per_scene_normalization_contract import inspect_per_scene_normalization_contract as inspect


def fixture():
    names = ['B02', 'B03', 'B04', 'B08', 'B11', 'B12']
    return [
        {'normalization_mode':'per_scene_product_metadata', 'bands':list(range(1,7)), 'band_names':names.copy(), 'synthetic':False},
        {'scene_id':'제품 scene 1', 'image_sha256':'a'*64, 'band_names':names.copy()},
        {'scale':.0001, 'offset':0, 'evidence_path':'evidence.json', 'evidence_sha256':'b'*64},
        {'status':'verified_product_metadata', 'product_id':'제품 scene 1', 'band_names':names.copy(),
         'scale':[.0001]*6, 'offset':[0.0]*6, 'source_url':'https://example.invalid/source',
         'source_metadata_path':'metadata.json', 'source_metadata_sha256':'c'*64}]


class PerSceneNormalizationContractTests(unittest.TestCase):
    def result(self, values=None):
        return inspect(*(fixture() if values is None else values))

    def test_consistent_exact_output_still_all_authority_execution_false(self):
        result=self.result()
        self.assertEqual(set(result), {'schema_version','scope','status','issue','execution_authorized','artifact_bytes_verified',
                                      'source_authority_verified','scientific_accuracy_validated','workflow_supported'})
        self.assertEqual(result['status'],'DECLARATIONS_CONSISTENT_UNVERIFIED')
        self.assertIsNone(result['issue'])
        for key in ('execution_authorized','artifact_bytes_verified','source_authority_verified','scientific_accuracy_validated','workflow_supported'):
            self.assertIs(result[key],False)

    def test_global_missing_mode_and_other_mode_out_of_scope_without_other_inputs(self):
        for manifest in ({}, {'normalization_mode':'global'}, {'normalization_mode':'other_mode'},
                         {'normalization_mode':'global','bands':list(range(1,17))}):
            result=inspect(manifest,object(),object(),object())
            self.assertEqual(result['status'],'OUT_OF_SCOPE')
            self.assertIsNone(result['issue'])

    def test_mode_wrong_type_null_blank_and_control_invalid(self):
        for value in (None,True,1,[],{},'', ' ', 'global\n'):
            result=inspect({'normalization_mode':value},None,None,None)
            self.assertEqual(result['status'],'INVALID')
            self.assertEqual(result['issue']['field'],'checkpoint_manifest.normalization_mode')

    def test_missing_required_fields_distinct_from_explicit_null_malformed(self):
        fields=[(0,'bands'),(0,'band_names'),(1,'scene_id'),(1,'image_sha256'),(1,'band_names'),
                (2,'scale'),(2,'offset'),(2,'evidence_path'),(2,'evidence_sha256'),
                *[(3,k) for k in ('status','product_id','band_names','scale','offset','source_url','source_metadata_path','source_metadata_sha256')]]
        for index,key in fields:
            values=fixture();del values[index][key]
            result=self.result(values)
            self.assertEqual(result['status'],'INCOMPLETE',(index,key,result))
            self.assertEqual(result['issue']['code'],'MISSING_FIELD')
            values=fixture();values[index][key]=None
            self.assertEqual(self.result(values)['status'],'INVALID',(index,key))

    def test_declaration_mismatches_are_value_free_and_ordered_after_shape_checks(self):
        cases=[(0,'bands',[2,1,3,4,5,6]),(0,'band_names',['B03','B02','B04','B08','B11','B12']),
               (1,'band_names',['x']*6),(3,'status','claimed_not_verified'),(3,'product_id','other'),
               (3,'band_names',['x']*6),(3,'scale',.1),(3,'offset',1)]
        for index,key,value in cases:
            values=fixture();values[index][key]=value
            result=self.result(values)
            self.assertEqual(result['status'],'DECLARATION_MISMATCH')
            self.assertEqual(result['issue']['code'],'FIELD_MISMATCH')
            self.assertNotIn('other',str(result))
        values=fixture();values[0]['bands']=[2,1,3,4,5,6];values[3]['scale']=False
        self.assertEqual(self.result(values)['issue'],{'code':'INVALID_FIELD','field':'evidence.scale'})

    def test_numeric_bool_strings_tuple_nan_inf_and_wrong_lengths_rejected(self):
        bad=[True,False,'0.0001',(1,)*6,[],[1]*5,[1]*7,[1,1,1,1,1,True],float('nan'),float('inf'),-float('inf'),10**10000]
        for index in (2,3):
            for key in ('scale','offset'):
                for value in bad:
                    values=fixture();values[index][key]=value
                    self.assertEqual(self.result(values)['status'],'INVALID',(index,key,type(value)))

    def test_scale_strict_positive_offset_finite_signed_and_scalar_vector_equal(self):
        for value in (0,-1,-.0001,[1,1,1,1,1,0]):
            values=fixture();values[2]['scale']=value
            self.assertEqual(self.result(values)['status'],'INVALID')
        values=fixture();values[2]['scale']=[1,2,3,4,5,6];values[3]['scale']=[1.,2.,3.,4.,5.,6.]
        values[2]['offset']=-2;values[3]['offset']=[-2.]*6
        self.assertEqual(self.result(values)['status'],'DECLARATIONS_CONSISTENT_UNVERIFIED')

    def test_six_band_exact_order_types_and_builtin_lists_only(self):
        for bands in ([True,2,3,4,5,6],[1.0,2,3,4,5,6],list(range(1,8)),(1,2,3,4,5,6)):
            values=fixture();values[0]['bands']=bands
            self.assertEqual(self.result(values)['status'],'INVALID')
        values=fixture();values[0]['bands']=[1,2,3,4,5,5]
        self.assertEqual(self.result(values)['status'],'DECLARATION_MISMATCH')

    def test_hash_format_only_all_three_roles_can_have_distinct_valid_hashes(self):
        self.assertEqual(self.result()['status'],'DECLARATIONS_CONSISTENT_UNVERIFIED')
        for index,key in ((1,'image_sha256'),(2,'evidence_sha256'),(3,'source_metadata_sha256')):
            for value in ('a'*63,'A'*64,'g'*64,True,1,b'a'*64):
                values=fixture();values[index][key]=value
                self.assertEqual(self.result(values)['status'],'INVALID')

    def test_text_lengths_controls_surrogates_and_unicode_original_values(self):
        for index,key,limit in ((1,'scene_id',128),(2,'evidence_path',512),(3,'source_url',2048),(3,'source_metadata_path',512)):
            for value in ('','  ','x'*(limit+1),'a\nb','a\x7fb','\ud800'):
                values=fixture();values[index][key]=value
                self.assertEqual(self.result(values)['status'],'INVALID')
        values=fixture();values[1]['scene_id']=' 한글🌍 ';values[3]['product_id']=' 한글🌍 '
        self.assertEqual(self.result(values)['status'],'DECLARATIONS_CONSISTENT_UNVERIFIED')
        values[3]['product_id']='한글🌍'
        self.assertEqual(self.result(values)['status'],'DECLARATION_MISMATCH')

    def test_paths_url_are_opaque_declarations_not_resolved_or_authenticated(self):
        values=fixture();values[2]['evidence_path']='../not-read/evidence.json'
        values[3]['source_metadata_path']='C:\\not-read\\metadata.json';values[3]['source_url']='opaque caller attribution'
        result=self.result(values)
        self.assertEqual(result['status'],'DECLARATIONS_CONSISTENT_UNVERIFIED')
        self.assertFalse(result['artifact_bytes_verified']);self.assertFalse(result['source_authority_verified'])
        self.assertNotIn('not-read',str(result))

    def test_extra_unknown_cyclic_values_not_traversed_and_inputs_immutable(self):
        values=fixture();before=copy.deepcopy(values)
        self.result(values);self.assertEqual(values,before)
        cycle={};cycle['self']=cycle
        for value in values:value['unused_metadata']=cycle
        self.assertEqual(self.result(values)['status'],'DECLARATIONS_CONSISTENT_UNVERIFIED')
        self.assertIs(values[0]['unused_metadata'],cycle)

    def test_bounded_dicts_and_exact_builtin_types_no_custom_key_callback(self):
        class SubDict(dict):pass
        class SubString(str):pass
        class Poison:
            def __hash__(self):return hash('normalization_mode')
            def __eq__(self,other):raise AssertionError('callback forbidden')
        for index in range(4):
            values=fixture();values[index]=SubDict(values[index])
            self.assertEqual(self.result(values)['status'],'INVALID')
            values=fixture();values[index].update({f'extra{i}':None for i in range(129)})
            self.assertEqual(self.result(values)['issue']['code'],'INPUT_LIMIT')
        self.assertEqual(inspect({Poison():1},None,None,None)['status'],'INVALID')
        values=fixture();values[1]['scene_id']=SubString('a')
        self.assertEqual(self.result(values)['status'],'INVALID')

    def test_no_file_io_and_no_numpy_torch_service_dependencies(self):
        with patch('builtins.open',side_effect=AssertionError('I/O forbidden')),patch.object(Path,'open',side_effect=AssertionError('I/O forbidden')):
            self.assertEqual(self.result()['status'],'DECLARATIONS_CONSISTENT_UNVERIFIED')
        source=Path(__file__).resolve().parents[1]/'backend/app/ml/per_scene_normalization_contract.py'
        tree=ast.parse(source.read_text(encoding='utf-8'))
        imports=[node.names[0].name for node in ast.walk(tree) if isinstance(node,ast.Import)]
        self.assertEqual(imports,['math','re'])
        self.assertFalse(any(isinstance(node,ast.ImportFrom) for node in ast.walk(tree)))


if __name__=='__main__':unittest.main()
