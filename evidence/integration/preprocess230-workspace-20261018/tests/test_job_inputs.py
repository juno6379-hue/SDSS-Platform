"""임시 Dataset Registry에서 Job 입력 점검과 실행/과학 승인 분리를 검증한다."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.dataset_registry import register_version,version_key
from app.job_inputs import resolve_job_inputs
from app.store import Store


class JobInputTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.store=Store(self.root)
        self.asset=self.root/'private-location.json';self.asset.write_bytes(b'{"contract_fixture":true}')
        (self.root/'quality.json').write_bytes(b'{}')
        self.manifest={'schema_version':'0.2.0','dataset_id':'fixture','version':'1',
            'source':{'institution':'test','product':'fixture','license':'contract test'},
            'data_type':'document','spatial':{'bbox':[106,-7,107,-6],'crs':'OGC:CRS84'},
            'temporal':{'start':'2024-01-01T00:00:00Z','end':'2024-12-31T00:00:00Z','calendar':'gregorian'},
            'quality_status':'VALIDATED','quality_report_ref':'quality.json','access_class':'PUBLIC',
            'sha256':hashlib.sha256(self.asset.read_bytes()).hexdigest(),
            'artifact_uri':self.asset.name,'lineage':[]}
        register_version(self.store,self.manifest)
        self.ref={'id':'fixture','version':'1','sha256':self.manifest['sha256']}

    def tearDown(self):
        self.temp.cleanup()

    def codes(self,result):
        return [blocker['code'] for blocker in result['blockers']]

    def test_public_validated_checks_artifact_sha_without_granting_execution_or_science(self):
        # ref SHA는 manifest 본문의 자산 SHA이며 canonical manifest SHA와 다르다.
        before={p.name:p.read_bytes() for p in self.root.iterdir() if p.is_file()}
        result=resolve_job_inputs(self.store,[self.ref])
        self.assertEqual(result['status'],'INTEGRITY_VERIFIED')
        self.assertTrue(result['input_integrity_verified']);self.assertEqual(result['blockers'],[])
        self.assertFalse(result['ready_for_execution']);self.assertFalse(result['scientific_approval'])
        self.assertFalse(result['resolved'][0]['authorization_verified'])
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.root.iterdir() if p.is_file()})

    def test_distinct_fixed_versions_of_one_dataset_are_valid_temporal_inputs(self):
        next_asset=self.root/'t2.json';next_asset.write_bytes(b'{"contract_fixture":"T2"}')
        next_hash=hashlib.sha256(next_asset.read_bytes()).hexdigest()
        register_version(self.store,dict(self.manifest,version='2',artifact_uri=next_asset.name,sha256=next_hash))
        result=resolve_job_inputs(self.store,[dict(self.ref,role='T1'),dict(self.ref,version='2',sha256=next_hash,role='T2')])
        self.assertEqual(result['blockers'],[])
        self.assertTrue(result['input_integrity_verified'])
        self.assertFalse(result['ready_for_execution'])

    def test_different_hashes_for_one_fixed_version_block_every_conflicting_ref(self):
        result=resolve_job_inputs(self.store,[self.ref,dict(self.ref,sha256='a'*64)])
        self.assertEqual(self.codes(result).count('INPUT_REF_CONFLICT'),2)
        self.assertFalse(result['input_integrity_verified'])
        same=resolve_job_inputs(self.store,[self.ref,dict(self.ref,role='another-role')])
        self.assertEqual(same['blockers'],[])

    def test_dynamic_and_malformed_refs_are_structured_and_do_not_skip_later_inputs(self):
        for version in ('latest','current',' LATEST '):
            result=resolve_job_inputs(self.store,[dict(self.ref,version=version),self.ref])
            self.assertIn('INPUT_REF_NOT_PINNED',self.codes(result))
            self.assertTrue(result['resolved'][1]['integrity_verified'])
        for refs in [None,[],{}]:
            self.assertEqual(self.codes(resolve_job_inputs(self.store,refs)),['INPUT_REFS_REQUIRED'])
        result=resolve_job_inputs(self.store,[dict(self.ref,unknown='secret'),self.ref])
        self.assertIn('INPUT_REF_SCHEMA_MISMATCH',self.codes(result))
        self.assertTrue(result['resolved'][1]['integrity_verified'])

    def test_uri_cannot_replace_registered_asset_or_fetch_remote_content(self):
        other=self.root/'other.json';other.write_bytes(self.asset.read_bytes())
        for uri in [other.name,'https://example.invalid/secret','../outside.json','//server/share/secret']:
            with self.subTest(uri=uri):
                result=resolve_job_inputs(self.store,[dict(self.ref,uri=uri)])
                self.assertIn('INPUT_URI_MISMATCH',self.codes(result));self.assertFalse(result['input_integrity_verified'])
                self.assertEqual(result['network_requests'],0)
                self.assertNotIn(uri,json.dumps(result))
        result=resolve_job_inputs(self.store,[dict(self.ref,uri='./'+self.asset.name)])
        self.assertEqual(result['blockers'],[])

    def test_missing_corrupt_hash_and_changed_asset_fail_closed(self):
        result=resolve_job_inputs(self.store,[dict(self.ref,id='missing'),self.ref])
        self.assertIn('DATASET_VERSION_NOT_FOUND',self.codes(result));self.assertTrue(result['resolved'][1]['integrity_verified'])
        result=resolve_job_inputs(self.store,[dict(self.ref,sha256='a'*64)])
        self.assertIn('INPUT_INTEGRITY_FAILED',self.codes(result))
        self.asset.write_bytes(b'changed')
        self.assertIn('INPUT_INTEGRITY_FAILED',self.codes(resolve_job_inputs(self.store,[self.ref])))

    def test_corrupt_catalog_record_and_missing_asset_are_structured(self):
        self.store.put('dataset_versions',{'id':version_key('fixture','1'),'manifest':{}})
        self.assertIn('INPUT_INTEGRITY_FAILED',self.codes(resolve_job_inputs(self.store,[self.ref])))
        # 손상 레코드의 누락 key도 미등록 자료와 구별한다.
        self.store.put('dataset_versions',{'id':version_key('fixture','1')})
        self.assertIn('DATASET_RECORD_CORRUPT',self.codes(resolve_job_inputs(self.store,[self.ref])))

    def test_missing_asset_or_quality_evidence_and_manifest_hash_as_asset_hash_are_rejected(self):
        record=self.store.get('dataset_versions',version_key('fixture','1'))
        self.assertNotEqual(record['manifest_sha256'],self.ref['sha256'])
        wrong=resolve_job_inputs(self.store,[dict(self.ref,sha256=record['manifest_sha256'])])
        self.assertIn('INPUT_INTEGRITY_FAILED',self.codes(wrong))
        (self.root/'quality.json').unlink()
        self.assertIn('INPUT_INTEGRITY_FAILED',self.codes(resolve_job_inputs(self.store,[self.ref])))
        (self.root/'quality.json').write_bytes(b'{}')
        self.asset.unlink()
        self.assertIn('INPUT_INTEGRITY_FAILED',self.codes(resolve_job_inputs(self.store,[self.ref])))

    def test_all_quality_states_and_restricted_classes_never_authorize(self):
        for quality in ('RAW','STAGED','STANDARDIZED','REJECTED'):
            version='quality-'+quality
            register_version(self.store,dict(self.manifest,version=version,quality_status=quality))
            result=resolve_job_inputs(self.store,[dict(self.ref,version=version)])
            expected='INPUT_QUALITY_REJECTED' if quality=='REJECTED' else 'INPUT_QUALITY_NOT_VALIDATED'
            self.assertIn(expected,self.codes(result));self.assertTrue(result['input_integrity_verified'])
            self.assertFalse(result['ready_for_execution'])
        for access in ('RESTRICTED','CONFIDENTIAL'):
            version='access-'+access
            register_version(self.store,dict(self.manifest,version=version,access_class=access))
            result=resolve_job_inputs(self.store,[dict(self.ref,version=version)])
            self.assertIn('INPUT_ACL_NOT_IMPLEMENTED',self.codes(result))
            self.assertFalse(result['resolved'][0]['authorization_verified'])
            encoded=json.dumps(result)
            for secret in [self.asset.name,str(self.root),'artifact_uri','quality_report_ref','manifest']:
                self.assertNotIn(secret,encoded)

    def test_registry_failure_returns_no_raw_error_or_path(self):
        import sqlite3
        with patch('app.job_inputs.resolve_version',side_effect=sqlite3.DatabaseError('secret internal db path')):
            result=resolve_job_inputs(self.store,[self.ref])
        self.assertIn('DATASET_REGISTRY_UNAVAILABLE',self.codes(result))
        self.assertNotIn('secret',json.dumps(result))
