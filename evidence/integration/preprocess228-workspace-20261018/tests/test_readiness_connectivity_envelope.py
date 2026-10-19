"""Tiny in-memory serialization tests; no actual source/file/eligibility verification."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
from backend.app.data import readiness_connectivity_envelope as module
from backend.app.data.readiness_connectivity_witness import FIXED_PROVINCE_SPLITS

HELPER_SHA='a'*64
PROVENANCE={'source_report_sha256':'b'*64,'source_manifest_sha256':'c'*64,'eligible_scene_reference_sha256':None}
POLICY=dict(FIXED_PROVINCE_SPLITS)


def scene(index,province='south_sulawesi',group='공유–원본',scene_id=None):
    return {'scene_index':index,'province':province,'source_group':group,'scene_id':str(index) if scene_id is None else scene_id,'bounds_wgs84':[index*3,0,index*3+1,1]}


class ReadinessConnectivityEnvelopeTests(unittest.TestCase):
    def setUp(self):self.rows=[scene(4),scene(7,'banten')];self.envelope=self.build(self.rows)
    def build(self,rows,**kwargs):return module.build_readiness_connectivity_envelope(rows,POLICY,provenance=PROVENANCE,helper_sha256=HELPER_SHA,expected_helper_sha256=HELPER_SHA,**kwargs)
    def pins(self,envelope=None):return {'expected_helper_sha256':HELPER_SHA,'expected_provenance':copy.deepcopy(PROVENANCE),'expected_input_sha256':(envelope or self.envelope)['input_sha256']}
    def validate(self,envelope):return module.validate_readiness_connectivity_envelope(envelope,**self.pins())
    def rehash(self,e):
        e['provenance_sha256']=module._digest(e['provenance']);e['input_sha256']=module._digest(e['input']);e['witness_sha256']=module._digest(e['witness']);e['envelope_sha256']=module._digest({k:e[k] for k in module.BODY_KEYS})
    def test_canonical_roundtrip_utf8_stability_and_input_unchanged_no_io(self):
        before=copy.deepcopy(self.rows);policy=copy.deepcopy(POLICY)
        with patch('builtins.open',side_effect=AssertionError('No file IO')):
            e=self.build(self.rows);raw=module.encode_readiness_connectivity_envelope(e,**self.pins(e));decoded=module.decode_readiness_connectivity_envelope(raw,**self.pins(e))
        self.assertEqual(decoded,e);self.assertIn('공유'.encode(),raw);self.assertEqual(self.rows,before);self.assertEqual(POLICY,policy)
        self.assertEqual(raw,json.dumps(e,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode());self.assertEqual(raw,module.encode_readiness_connectivity_envelope(decoded,**self.pins(e)))
        decoded['input']['eligible_scenes'][0]['source_group']='other';self.assertEqual(self.rows,before)
    def test_none_source_hash_does_not_replace_scene_evidence(self):
        e=module.build_readiness_connectivity_envelope(None,provenance=PROVENANCE,helper_sha256=HELPER_SHA,expected_helper_sha256=HELPER_SHA)
        self.assertIsNone(e['input']['eligible_scenes']);self.assertEqual(e['witness']['diagnostic_status'],'UNKNOWN_NOT_PERSISTED');self.assertFalse(e['witness']['union_complete'])
        self.assertEqual(module.decode_readiness_connectivity_envelope(module.encode_readiness_connectivity_envelope(e,**self.pins(e)),**self.pins(e)),e)
        p={**PROVENANCE,'eligible_scene_reference_sha256':'d'*64};e=module.build_readiness_connectivity_envelope(None,provenance=p,helper_sha256=HELPER_SHA,expected_helper_sha256=HELPER_SHA);self.assertEqual(e['witness']['diagnostic_status'],'UNKNOWN_NOT_PERSISTED')
    def test_none_empty_and_order_are_distinct_input_identities(self):
        none=self.build(None);empty=self.build([]);reverse=self.build(list(reversed(self.rows)))
        self.assertEqual(len({none['input_sha256'],empty['input_sha256'],self.envelope['input_sha256'],reverse['input_sha256']}),4)
        self.assertEqual(empty['witness']['diagnostic_status'],'NO_SUPPLIED_ELIGIBLE_SCENES');self.assertNotEqual(reverse['witness']['witness_edges'],self.envelope['witness']['witness_edges'])
    def test_helper_pin_and_three_external_pins_required(self):
        with self.assertRaises(ValueError):module.build_readiness_connectivity_envelope(self.rows,POLICY,provenance=PROVENANCE,helper_sha256='f'*64,expected_helper_sha256=HELPER_SHA)
        for key,value in [('expected_helper_sha256','d'*64),('expected_input_sha256','d'*64),('expected_provenance',{**PROVENANCE,'source_manifest_sha256':'d'*64})]:
            pins=self.pins();pins[key]=value
            with self.assertRaises(ValueError):module.validate_readiness_connectivity_envelope(self.envelope,**pins)
        with self.assertRaises(TypeError):module.validate_readiness_connectivity_envelope(self.envelope)
    def test_lineage_retarget_rehashed_envelope_still_rejected(self):
        e=copy.deepcopy(self.envelope);e['provenance']['source_report_sha256']='d'*64;self.rehash(e)
        with self.assertRaises(ValueError):self.validate(e)
        e=self.build([scene(4,group='retarget'),scene(7,'banten')])
        with self.assertRaises(ValueError):self.validate(e)
    def test_witness_tamper_rehash_and_boolean_integer_distinctions(self):
        for mutate in [lambda e:e['witness'].update(witness_edge_count_total=0),lambda e:e['witness']['witness_edges'][0]['left'].update(scene_index=999),lambda e:e['witness'].update(union_complete=1),lambda e:e['witness'].update(proposed_refund_bytes=False),lambda e:e['witness'].update(new_unknown_key=True)]:
            e=copy.deepcopy(self.envelope);mutate(e);self.rehash(e)
            with self.assertRaises(ValueError):self.validate(e)
    def test_truncation_zero_and_partial_recomputed_exactly(self):
        for cap in [0,1]:
            e=self.build([scene(0,scene_id='공유–원본'),scene(1,'banten',scene_id='공유–원본')],limits={'max_scenes':2,'max_bbox_pairs':1,'max_witness_edges':cap})
            self.assertTrue(e['witness']['union_complete']);self.assertTrue(e['witness']['witness_edges_truncated']);self.assertEqual(e['witness']['witness_edge_count_stored'],cap)
            self.assertEqual(module.validate_readiness_connectivity_envelope(e,**self.pins(e)),e)
            e['witness']['witness_edges_truncated']=False;self.rehash(e)
            with self.assertRaises(ValueError):module.validate_readiness_connectivity_envelope(e,**self.pins(e))
    def test_literal_bbox_scene_index_and_position_binding(self):
        for mutate in [lambda rows:rows[0].update(scene_index=5),lambda rows:rows[0].update(source_group='different'),lambda rows:rows[0].update(bounds_wgs84=[12.0,0,13,1])]:
            rows=copy.deepcopy(self.rows);mutate(rows);e=self.build(rows)
            self.assertNotEqual(e['input_sha256'],self.envelope['input_sha256'])
            with self.assertRaises(ValueError):self.validate(e)
    def test_unknown_schema_top_input_scene_provenance_and_limits_keys(self):
        for mutate in [lambda e:e.update(schema_version=2),lambda e:e.update(unknown=True),lambda e:e['input'].update(extra=1),lambda e:e['input']['eligible_scenes'][0].update(extra=1),lambda e:e['provenance'].update(extra=None),lambda e:e['input']['limits'].update(extra=1)]:
            e=copy.deepcopy(self.envelope);mutate(e)
            with self.assertRaises(ValueError):self.validate(e)
        with self.assertRaises(ValueError):self.build([{**self.rows[0],'extra':1}])
    def test_type_policy_limits_and_provenance_malformed(self):
        for limits in [{'max_scenes':True,'max_bbox_pairs':1,'max_witness_edges':1},{'max_scenes':2,'max_bbox_pairs':1,'max_witness_edges':10001}]:
            with self.assertRaises(ValueError):self.build(self.rows,limits=limits)
        for provenance in [{**PROVENANCE,'source_report_sha256':False},{**PROVENANCE,'source_report_sha256':'A'*64},{}]:
            with self.assertRaises(ValueError):module.build_readiness_connectivity_envelope(None,provenance=provenance,helper_sha256=HELPER_SHA,expected_helper_sha256=HELPER_SHA)
        with self.assertRaises(ValueError):module.build_readiness_connectivity_envelope(self.rows,{**POLICY,'banten':'train'},provenance=PROVENANCE,helper_sha256=HELPER_SHA,expected_helper_sha256=HELPER_SHA)
    def test_decoder_preparse_depth_utf16_escape_and_huge_number_before_loads(self):
        text=json.dumps({'escaped':'"','deep':json.loads('['*40+'0'+']'*40)})
        for raw in [text.encode(),text.encode('utf-16'),text.encode('utf-32'),b'{"n":'+b'9'*100+b'}',b'{"s":"'+b'a'*25000+b'"}']:
            with self.subTest(raw=raw[:30]),patch.object(module.json,'loads',side_effect=AssertionError('Parser must not run')),self.assertRaises(ValueError):module.decode_readiness_connectivity_envelope(raw,**self.pins())
    def test_decoder_duplicate_bom_nan_infinity_noncanonical_and_invalid_unicode(self):
        raw=module.encode_readiness_connectivity_envelope(self.envelope,**self.pins())
        for altered in [b'\xef\xbb\xbf'+raw,raw+b'\n',b'{"a":1,"a":2}',b'{"a":NaN}',b'{"a":Infinity}',b'{"a":1e999}',b'\xff',b'{"a":"\x00"}',b'{"a":"\\ud800"}',bytearray(raw)]:
            with self.subTest(raw=str(altered)[:60]),self.assertRaises(ValueError):module.decode_readiness_connectivity_envelope(altered,**self.pins())
        noncanonical=json.dumps(self.envelope,ensure_ascii=True).encode()
        with self.assertRaises(ValueError):module.decode_readiness_connectivity_envelope(noncanonical,**self.pins())
    def test_size_node_and_string_budget_before_dumps_loads_or_helper(self):
        with patch.object(module,'MAX_BYTES',64),patch.object(module,'diagnose_readiness_connectivity',side_effect=AssertionError('No helper work')),patch.object(module.json,'dumps',side_effect=AssertionError('No huge serialize')):
            # Oversized raw decoder is rejected even before UTF8/json parser.
            with self.assertRaises(ValueError):module.decode_readiness_connectivity_envelope(b'x'*65,**self.pins())
        with patch.object(module,'MAX_BYTES',64),patch.object(module,'diagnose_readiness_connectivity',side_effect=AssertionError('No helper work')):
            with self.assertRaises(ValueError):self.build(self.rows)
        for value in ['a'*4097,10**400,float('nan'),float('inf')]:
            with self.assertRaises(ValueError):module._canonical({'x':value})
        with patch.object(module,'MAX_NODES',3),self.assertRaises(ValueError):module._canonical([1,2,3])
    def test_cyclic_alias_and_nonexact_json_objects_are_bounded(self):
        cyclic=[];cyclic.append(cyclic)
        with self.assertRaises(ValueError):module._canonical(cyclic)
        row=copy.deepcopy(self.rows[0]);row['bounds_wgs84']=row
        with self.assertRaises(ValueError):self.build([row])
        alias=[0,0,1,1];rows=[scene(0),scene(1,'banten')];rows[0]['bounds_wgs84']=alias;rows[1]['bounds_wgs84']=alias
        e=self.build(rows);e['input']['eligible_scenes'][0]['bounds_wgs84'][0]=-.5;self.assertEqual(alias,[0,0,1,1])
        class DictSubclass(dict):pass
        with self.assertRaises(ValueError):module._canonical(DictSubclass(a=1))
    def test_envelope_digest_and_input_identity_digest_independently_guarded(self):
        for key in ['envelope_sha256','input_sha256','witness_sha256','provenance_sha256']:
            e=copy.deepcopy(self.envelope);e[key]='0'*64
            with self.assertRaises(ValueError):self.validate(e)
    def test_final_envelope_size_and_declared_scene_limit_before_row_traversal(self):
        body={k:self.envelope[k] for k in module.BODY_KEYS};body_size=len(module._canonical(body))
        with patch.object(module,'MAX_BYTES',body_size),self.assertRaises(ValueError):self.build(self.rows)
        class RowDict(dict):
            def __iter__(self):raise AssertionError('Over-limit rows must not be traversed')
        rows=[RowDict() for _ in range(3)]
        with self.assertRaises(ValueError):self.build(rows,limits={'max_scenes':2,'max_bbox_pairs':3,'max_witness_edges':1})
    def test_cp949_ascii_summary_and_utf8_serialized_payload(self):
        code='''import json
from backend.app.data.readiness_connectivity_envelope import build_readiness_connectivity_envelope,encode_readiness_connectivity_envelope
from backend.app.data.readiness_connectivity_witness import FIXED_PROVINCE_SPLITS
p={'source_report_sha256':'b'*64,'source_manifest_sha256':'c'*64,'eligible_scene_reference_sha256':None}
s=[{'scene_index':0,'province':'banten','source_group':'\uacf5\uc720\u2013','scene_id':'id','bounds_wgs84':[0,0,1,1]}]
e=build_readiness_connectivity_envelope(s,FIXED_PROVINCE_SPLITS,provenance=p,helper_sha256='a'*64,expected_helper_sha256='a'*64)
r=encode_readiness_connectivity_envelope(e,expected_helper_sha256='a'*64,expected_provenance=p,expected_input_sha256=e['input_sha256'])
print(json.dumps({'status':e['status'],'utf8_bytes':len(r),'unicode_in_bytes':not r.isascii()},ensure_ascii=True))
'''
        result=subprocess.run([sys.executable,'-c',code],cwd=Path(__file__).resolve().parents[1],env={**os.environ,'PYTHONIOENCODING':'cp949'},capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr);self.assertTrue(result.stdout.isascii());self.assertTrue(json.loads(result.stdout)['unicode_in_bytes'])
    def test_all_claims_diagnostic_and_no_positive_provenance_authentication(self):
        e=self.envelope
        for key in ['provenance_verified','executing_helper_code_verified','eligibility_verified','historical_readiness_cause_reconstructed','ready_for_training','scientific_accuracy_validated','training_executed','training_split_leakage_resolved','settlement_authorized','execution_authorized','automatic_resume_allowed']:self.assertIs(e[key],False)
        self.assertEqual(e['status'],'BLOCKED');self.assertEqual(e['proposed_refund_bytes'],0);self.assertIn('NOT_FILE_VERIFIED',e['provenance_claim']);self.assertIn('NOT_EXECUTING_CODE_VERIFIED',e['helper_binding_claim'])


if __name__=='__main__':unittest.main()
