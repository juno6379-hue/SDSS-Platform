"""임시 Dataset 계보의 읽기 검증. 합성 계보 통과는 실행·과학·기관 승인 근거가 아니다."""
import copy
import hashlib
import json
import sqlite3
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.dataset_registry import register_version,version_key
from app.dataset_lineage import verify_dataset_lineage
from app.store import Store


class DatasetLineageTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.store=Store(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def content(self,identifier,version):
        return f'explicit-synthetic-lineage-fixture:{identifier}:{version}'.encode()

    def ref(self,identifier,version='1'):
        return {'id':identifier,'version':version,'sha256':hashlib.sha256(self.content(identifier,version)).hexdigest()}

    def dataset(self,identifier,version='1',parents=(),access='PUBLIC',store=None):
        store=store or self.store;ref=self.ref(identifier,version)
        asset=store.root/f'PRIVATE-ASSET-{identifier}-{version}.bin'
        asset.write_bytes(self.content(identifier,version))
        quality=store.root/'PRIVATE-QUALITY.json';quality.write_bytes(b'{"explicit_contract_fixture":true}')
        manifest={'schema_version':'0.2.0','dataset_id':identifier,'version':version,
            'source':{'institution':'contract test','product':'explicit lineage fixture','license':'test only',
                      'source_uri':'https://example.invalid/PRIVATE-CREDENTIAL'},
            'data_type':'document','spatial':{'bbox':[106,-7,107,-6],'crs':'OGC:CRS84'},
            'temporal':{'start':'2024-01-01T00:00:00Z','end':'2024-12-31T00:00:00Z','calendar':'gregorian'},
            'quality_status':'VALIDATED','quality_report_ref':quality.name,'access_class':access,
            'sha256':ref['sha256'],'artifact_uri':asset.name,'lineage':copy.deepcopy(list(parents))}
        register_version(store,manifest)
        return ref

    def files(self,store):
        return {str(path.relative_to(store.root)):path.read_bytes() for path in store.root.rglob('*') if path.is_file()}

    def verify(self,ref,store=None,**limits):
        store=store or self.store;before=self.files(store)
        with patch.object(store,'put',side_effect=AssertionError('계보 검증이 Registry를 변경했습니다.')):
            result=verify_dataset_lineage(store,ref['id'],ref['version'],ref['sha256'],**limits)
        self.assertEqual(self.files(store),before)
        self.assertEqual(result['scope'],'DATASET_LINEAGE_INTEGRITY_ONLY')
        self.assertEqual(result['edge_direction'],'PARENT_TO_CHILD')
        for field in ('authorization_verified','execution_authorized','scientific_approval'):
            self.assertIs(result[field],False)
        self.assertEqual(result['network_requests'],0);self.assertEqual(result['source_files_written'],0)
        for node in result['nodes']:
            self.assertFalse(node['authorization_verified'])
        encoded=json.dumps(result)
        for secret in ('PRIVATE-ASSET','PRIVATE-QUALITY','PRIVATE-CREDENTIAL',str(store.root),'artifact_uri','source_uri'):
            self.assertNotIn(secret,encoded)
        return result

    def codes(self,result):
        return {item['code'] for item in result['blockers']}

    def identity(self,ref):
        return (ref['id'],ref['version'],ref['sha256'])

    def test_root_and_transitive_parents_are_revalidated_without_writes_or_approval(self):
        leaf=self.dataset('leaf');parent=self.dataset('parent',parents=[leaf]);root=self.dataset('root',parents=[parent])
        result=self.verify(root)
        self.assertEqual(result['status'],'INTEGRITY_VERIFIED');self.assertTrue(result['lineage_integrity_verified'])
        self.assertTrue(result['current_assets_revalidated']);self.assertEqual(result['blockers'],[])
        self.assertEqual({self.identity(node) for node in result['nodes']},{self.identity(x) for x in (root,parent,leaf)})
        self.assertEqual({(self.identity(edge['source']),self.identity(edge['target'])) for edge in result['edges']},
                         {(self.identity(leaf),self.identity(parent)),(self.identity(parent),self.identity(root))})

    def test_missing_root_or_parent_and_wrong_hash_are_blocked(self):
        missing=self.ref('missing');root=self.dataset('root',parents=[missing])
        for ref in (root,missing):
            result=self.verify(ref)
            self.assertIn('DATASET_VERSION_NOT_FOUND',self.codes(result));self.assertFalse(result['lineage_integrity_verified'])
        parent=self.dataset('parent');wrong=dict(parent,sha256='a'*64)
        child=self.dataset('wrong-parent-root',parents=[wrong])
        self.assertIn('LINEAGE_INTEGRITY_FAILED',self.codes(self.verify(child)))
        self.assertIn('LINEAGE_INTEGRITY_FAILED',self.codes(self.verify(dict(parent,sha256='b'*64))))

    def test_changed_parent_asset_is_detected_on_a_later_request(self):
        parent=self.dataset('parent');root=self.dataset('root',parents=[parent])
        self.assertTrue(self.verify(root)['lineage_integrity_verified'])
        (self.root/'PRIVATE-ASSET-parent-1.bin').write_bytes(b'changed between requests')
        result=self.verify(root)
        self.assertIn('LINEAGE_INTEGRITY_FAILED',self.codes(result));self.assertFalse(result['lineage_integrity_verified'])

    def test_dynamic_or_malformed_root_references_fail_closed(self):
        root=self.dataset('root')
        for version in ('latest','current',' LATEST '):
            with self.subTest(version=version):
                result=self.verify(dict(root,version=version))
                self.assertIn('LINEAGE_REF_NOT_PINNED',self.codes(result));self.assertFalse(result['current_assets_revalidated'])
        for ref in (dict(root,id=''),dict(root,version=''),dict(root,sha256='not-a-sha')):
            with self.subTest(ref=ref):
                result=self.verify(ref)
                self.assertIn('INVALID_ROOT_REF',self.codes(result));self.assertFalse(result['lineage_integrity_verified'])

    def test_cycle_is_detected_but_same_dataset_distinct_fixed_versions_are_allowed(self):
        a=self.ref('a');b=self.ref('b')
        self.dataset('a',parents=[b]);self.dataset('b',parents=[a])
        result=self.verify(a)
        self.assertIn('LINEAGE_CYCLE',self.codes(result));self.assertFalse(result['lineage_integrity_verified'])
        first=self.dataset('temporal',version='1');second=self.dataset('temporal',version='2',parents=[first])
        valid=self.verify(second)
        self.assertEqual(valid['blockers'],[])
        self.assertEqual({node['version'] for node in valid['nodes']},{'1','2'})

    def test_diamond_duplicate_parents_are_resolved_once_and_deduplicated(self):
        common=self.dataset('common');left=self.dataset('left',parents=[common,common]);right=self.dataset('right',parents=[common])
        root=self.dataset('root',parents=[right,left,right])
        original_get=self.store.get;lookups=[]
        def get(kind,key):
            self.assertEqual(kind,'dataset_versions');lookups.append(key)
            return original_get(kind,key)
        with patch.object(self.store,'get',side_effect=get):
            result=self.verify(root)
        self.assertEqual(len(result['nodes']),4);self.assertEqual(len(result['edges']),4)
        self.assertEqual(lookups.count(version_key('common','1')),1)
        self.assertEqual(len(lookups),4);self.assertTrue(result['lineage_integrity_verified'])

    def test_same_version_conflicting_hashes_are_not_mistaken_for_distinct_versions(self):
        parent=self.dataset('parent')
        root=self.dataset('root',parents=[parent,dict(parent,sha256='f'*64)])
        result=self.verify(root)
        self.assertIn('LINEAGE_REFERENCE_CONFLICT',self.codes(result));self.assertFalse(result['lineage_integrity_verified'])

    def test_depth_and_node_limits_bound_resolution_including_the_root(self):
        grand=self.dataset('grand');parent=self.dataset('parent',parents=[grand]);root=self.dataset('root',parents=[parent])
        self.assertTrue(self.verify(root,max_depth=2,max_nodes=3)['lineage_integrity_verified'])
        for limits,code in (({'max_depth':1},'LINEAGE_DEPTH_LIMIT'),({'max_nodes':2},'LINEAGE_NODE_LIMIT')):
            with self.subTest(limits=limits),patch.object(self.store,'get',wraps=self.store.get) as get:
                result=self.verify(root,**limits)
                self.assertIn(code,self.codes(result));self.assertFalse(result['lineage_integrity_verified'])
                self.assertNotIn(version_key('grand','1'),[call.args[1] for call in get.call_args_list])
        for limits in ({'max_depth':-1},{'max_depth':65},{'max_nodes':0},{'max_nodes':1025},{'max_depth':True},{'max_nodes':False}):
            with self.subTest(limits=limits):
                result=self.verify(root,**limits)
                self.assertIn('INVALID_LIMITS',self.codes(result));self.assertFalse(result['current_assets_revalidated'])

    def test_restricted_or_confidential_ancestors_block_and_do_not_disclose_their_parents(self):
        for access in ('RESTRICTED','CONFIDENTIAL'):
            with self.subTest(access=access):
                private_parent=self.dataset('undisclosed-'+access)
                protected=self.dataset('protected-'+access,parents=[private_parent],access=access)
                root=self.dataset('root-'+access,parents=[protected])
                with patch.object(self.store,'get',wraps=self.store.get) as get:
                    result=self.verify(root)
                self.assertIn('LINEAGE_ACL_NOT_IMPLEMENTED',self.codes(result));self.assertFalse(result['lineage_integrity_verified'])
                self.assertNotIn(private_parent['id'],json.dumps(result))
                self.assertNotIn(version_key(private_parent['id'],'1'),[call.args[1] for call in get.call_args_list])
                protected_result=self.verify(protected)
                self.assertIn('LINEAGE_ACL_NOT_IMPLEMENTED',self.codes(protected_result))
                self.assertNotIn(private_parent['id'],json.dumps(protected_result))

    def test_parent_order_does_not_change_sorted_projection_across_equivalent_catalogs(self):
        leaf=self.dataset('leaf');a=self.dataset('a',parents=[leaf]);b=self.dataset('b',parents=[leaf])
        root=self.dataset('root',parents=[b,a,b])
        first=self.verify(root)
        with tempfile.TemporaryDirectory() as directory:
            other=Store(Path(directory))
            other_leaf=self.dataset('leaf',store=other)
            other_b=self.dataset('b',parents=[other_leaf,other_leaf],store=other)
            other_a=self.dataset('a',parents=[other_leaf],store=other)
            other_root=self.dataset('root',parents=[other_a,other_b],store=other)
            second=self.verify(other_root,store=other)
        self.assertEqual(first,second)
        self.assertEqual([self.identity(node) for node in first['nodes']],sorted(self.identity(node) for node in first['nodes']))

    def test_shared_parent_cache_does_not_bypass_a_later_deeper_path_limit(self):
        leaf=self.dataset('leaf');shared=self.dataset('shared',parents=[leaf])
        a=self.dataset('a',parents=[shared]);z2=self.dataset('z2',parents=[shared]);z=self.dataset('z',parents=[z2])
        root=self.dataset('root',parents=[z,a])
        with patch.object(self.store,'get',wraps=self.store.get) as get:
            result=self.verify(root,max_depth=3)
        self.assertIn('LINEAGE_DEPTH_LIMIT',self.codes(result))
        self.assertFalse(result['lineage_integrity_verified'])
        self.assertTrue(result['limits']['depth_limit_reached'])
        keys=[call.args[1] for call in get.call_args_list]
        self.assertEqual(len(keys),6)
        self.assertEqual(len(keys),len(set(keys)),'더 깊은 경로 확인이 자산 재해시를 중복했습니다.')

    def test_optional_parent_uri_and_role_are_not_fetched_or_exposed(self):
        parent=self.dataset('parent')
        private_ref=dict(parent,uri='https://example.invalid/SIGNED-PARENT-URL?token=secret',role='PRIVATE-PARENT-ROLE')
        root=self.dataset('root',parents=[private_ref])
        result=self.verify(root)
        self.assertTrue(result['lineage_integrity_verified'])
        encoded=json.dumps(result)
        for secret in ('SIGNED-PARENT-URL','PRIVATE-PARENT-ROLE','token=secret'):
            self.assertNotIn(secret,encoded)

    def test_corrupt_record_and_registry_failure_are_structured_without_native_error_leaks(self):
        root=self.dataset('root')
        self.store.put('dataset_versions',{'id':version_key('root','1')})
        corrupt=self.verify(root)
        self.assertIn('DATASET_RECORD_CORRUPT',self.codes(corrupt))
        with patch.object(self.store,'get',side_effect=sqlite3.DatabaseError('PRIVATE-DB-LOCATION')):
            unavailable=self.verify(root)
        self.assertIn('DATASET_REGISTRY_UNAVAILABLE',self.codes(unavailable))
        self.assertNotIn('PRIVATE-DB-LOCATION',json.dumps(unavailable))


if __name__=='__main__':
    unittest.main()
