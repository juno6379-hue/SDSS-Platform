"""Prospective tiny metadata only: no readiness, data file or geometry engine IO."""
import copy
import math
import random
import unittest
from unittest.mock import patch
from backend.app.data import readiness_connectivity_witness as module

POLICY=dict(module.FIXED_PROVINCE_SPLITS)


def scene(index,province='south_sulawesi',group=None,scene_id=None,bounds=None):
    return {'scene_index':index,'province':province,'source_group':f'g{index}' if group is None else group,'scene_id':f's{index}' if scene_id is None else scene_id,'bounds_wgs84':[index*3,0,index*3+1,1] if bounds is None else bounds}


def reference(scenes):
    # Literal bounded union section from current readiness semantics, without IO.
    parents={p:p for p in module.PROVINCES}
    def find(p):
        while parents[p]!=p:p=parents[p]
        return p
    owner={}
    for row in scenes:
        if not row['source_group']:continue
        for token in (str(row['source_group']),str(row['scene_id'])):
            if token in owner:
                first,second=find(row['province']),find(owner[token]);parents[max(first,second)]=min(first,second)
            owner[token]=row['province']
    for i,row in enumerate(scenes):
        a=row['bounds_wgs84']
        for other in scenes[:i]:
            b=other['bounds_wgs84']
            if min(a[2],b[2])>max(a[0],b[0]) and min(a[3],b[3])>max(a[1],b[1]):
                first,second=find(row['province']),find(other['province']);parents[max(first,second)]=min(first,second)
    return {p:find(p) for p in parents}


class ReadinessConnectivityWitnessTests(unittest.TestCase):
    def diagnose(self,rows,**kwargs):return module.diagnose_readiness_connectivity(rows,POLICY,**kwargs)
    def test_none_unknown_not_empty_or_historical_reconstruction(self):
        r=module.diagnose_readiness_connectivity(None)
        self.assertEqual(r['diagnostic_status'],'UNKNOWN_NOT_PERSISTED');self.assertIsNone(r['scene_count']);self.assertIsNone(r['province_components']);self.assertFalse(r['union_complete']);self.assertEqual(r['witness_edge_coverage'],'NOT_STARTED')
        self.assertIsNone(r['no_cross_split_connectivity_found_in_supplied_metadata']);self.assertFalse(r['historical_readiness_cause_reconstructed']);self.assertIsNone(r['union_change_count']);self.assertFalse(r['fixed_split_assignments_changed']);self.assertEqual(set(r['witness_edge_counts_by_kind']),{'TOKEN_SHARED_NAMESPACE','BBOX_STRICT_POSITIVE_OVERLAP'})
    def test_empty_explicit_input_distinct_unknown_and_no_separation_claim(self):
        r=self.diagnose([]);self.assertEqual(r['diagnostic_status'],'NO_SUPPLIED_ELIGIBLE_SCENES');self.assertTrue(r['union_complete']);self.assertEqual(len(r['components']),6);self.assertIsNone(r['no_cross_split_connectivity_found_in_supplied_metadata']);self.assertFalse(r['complete_spatial_separation_claimed'])
    def test_cross_role_shared_namespace_and_last_seen_actual_indexes(self):
        rows=[scene(100,'south_sulawesi',group='x',scene_id='a'),scene(205,'banten',group='b',scene_id='x'),scene(901,'west_java',group='x',scene_id='c')]
        # Bounds deliberately disjoint, independent from caller index identifiers.
        for i,r in enumerate(rows):r['bounds_wgs84']=[i*3,0,i*3+1,1]
        r=self.diagnose(rows);edges=r['witness_edges'];self.assertEqual(len(edges),2)
        self.assertEqual(edges[0]['right'],{'scene_index':100,'eligible_position':0,'province':'south_sulawesi','token_role':'source_group'})
        self.assertEqual(edges[0]['left']['token_role'],'scene_id');self.assertEqual(edges[1]['right']['scene_index'],205);self.assertEqual(edges[1]['right']['token_role'],'scene_id')
        self.assertEqual(r['province_components']['west_java'],'banten');self.assertTrue(r['fixed_split_conflicts']);self.assertEqual(r['province_components'],reference(rows))
    def test_same_scene_same_token_noop_still_updates_last_role(self):
        rows=[scene(0,group='same',scene_id='same'),scene(1,'banten',group='same')]
        r=self.diagnose(rows);first,second=r['witness_edges'];self.assertEqual(first['left']['scene_index'],0);self.assertEqual(first['right']['scene_index'],0);self.assertFalse(first['component_union_changed']);self.assertEqual(second['right']['token_role'],'scene_id')
    def test_duplicate_scene_id_is_allowed_and_literal_tokens_not_prefixed(self):
        rows=[scene(0,scene_id='shared'),scene(1,'banten',scene_id='shared')]
        r=self.diagnose(rows);self.assertEqual(r['witness_edge_counts_by_kind']['TOKEN_SHARED_NAMESPACE'],1);self.assertFalse(r['no_cross_split_connectivity_found_in_supplied_metadata'])
    def test_empty_group_skips_both_tokens_but_bbox_still_unions(self):
        rows=[scene(0,group='other',scene_id='shared',bounds=[0,0,2,2]),scene(1,'banten',group='',scene_id='shared',bounds=[1,1,3,3])]
        r=self.diagnose(rows);self.assertEqual(r['token_occurrences_processed'],2);self.assertEqual(r['witness_edge_counts_by_kind'],{'TOKEN_SHARED_NAMESPACE':0,'BBOX_STRICT_POSITIVE_OVERLAP':1});self.assertEqual(r['issues'][0]['code'],'SOURCE_GROUP_MISSING');self.assertFalse(r['input_token_metadata_complete']);self.assertTrue(r['union_complete'])
        rows[1]['bounds_wgs84']=[10,0,11,1];r=self.diagnose(rows);self.assertIsNone(r['no_cross_split_connectivity_found_in_supplied_metadata'])
    def test_whitespace_and_empty_scene_id_literal_shared_tokens(self):
        rows=[scene(0,group=' ',scene_id=''),scene(1,'banten',group='x',scene_id='')]
        r=self.diagnose(rows);self.assertEqual(r['witness_edges'][0]['token'],'');self.assertEqual(r['witness_edges'][0]['kind'],'TOKEN_SHARED_NAMESPACE')
    def test_bbox_strict_touch_disjoint_and_tiny_positive(self):
        rows=[scene(0,bounds=[0,0,1,1]),scene(1,'banten',bounds=[1,0,2,1])]
        r=self.diagnose(rows);self.assertEqual(r['witness_edge_count_total'],0);self.assertTrue(r['no_cross_split_connectivity_found_in_supplied_metadata'])
        rows[1]['bounds_wgs84']=[1-1e-15,0,2,1];r=self.diagnose(rows);self.assertEqual(r['witness_edge_count_total'],1);self.assertEqual(r['witness_edges'][0]['comparison'],'STRICT_POSITIVE_BOTH_AXES')
    def test_within_split_transitive_union_is_preserved(self):
        rows=[scene(0,'south_sulawesi',group='within',bounds=[0,0,2,2]),scene(1,'east_java',group='within',bounds=[10,0,12,2]),scene(2,'banten',bounds=[11,0,13,2])]
        r=self.diagnose(rows);self.assertEqual(r['province_components']['south_sulawesi'],'banten');self.assertEqual(r['province_components']['east_java'],'banten');self.assertEqual(r['union_change_count'],2);self.assertEqual(r['province_components'],reference(rows))
    def test_all_province_union_lex_root_and_fixed_conflict_events(self):
        rows=[scene(i,p,group='all') for i,p in enumerate(module.PROVINCES)]
        r=self.diagnose(rows);self.assertEqual(set(r['province_components'].values()),{'banten'});self.assertEqual(r['fixed_split_conflicts'][0]['fixed_splits'],['test','train','val']);self.assertEqual([x['province'] for x in r['fixed_split_conflict_events']],['banten','west_java','east_java']);self.assertFalse(r['fixed_split_assignments_changed'])
    def test_witness_truncation_and_zero_storage_keep_full_union(self):
        rows=[scene(i,p,group='same',scene_id='same',bounds=[0,0,1,1]) for i,p in enumerate(module.PROVINCES)]
        complete=self.diagnose(rows)
        for cap in [0,1,3]:
            r=self.diagnose(rows,max_witness_edges=cap);self.assertTrue(r['union_complete']);self.assertTrue(r['witness_edges_truncated']);self.assertEqual(r['witness_edge_count_stored'],cap);self.assertEqual(r['witness_edge_count_total'],complete['witness_edge_count_total']);self.assertEqual(r['province_components'],complete['province_components']);self.assertEqual(r['fixed_split_conflicts'],complete['fixed_split_conflicts']);self.assertFalse(r['complete_spatial_separation_claimed'])
    def test_budget_limits_bool_negative_hardcaps_and_full_pair_plan(self):
        rows=[scene(0),scene(1),scene(2)]
        for key in module.CAPS:
            for value in [True,-1,module.CAPS[key]+1,1.0]:
                with self.subTest(key=key,value=value),self.assertRaises(ValueError):self.diagnose(rows,**{key:value})
        with self.assertRaises(ValueError):self.diagnose(rows,max_bbox_pairs=2)
        with self.assertRaises(ValueError):self.diagnose(rows,max_scenes=2)
        self.assertEqual(self.diagnose(rows,max_bbox_pairs=3)['bbox_pairs_evaluated'],3)
    def test_typed_strings_province_indexes_duplicate_and_none_policy(self):
        for key,value in [('scene_index',True),('scene_index',-1),('scene_index',2**63),('province','unknown'),('source_group',1),('scene_id',None),('source_group','x'*4097)]:
            rows=[scene(0)];rows[0][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):self.diagnose(rows)
        with self.assertRaises(ValueError):self.diagnose([scene(1),scene(1)])
        with self.assertRaises(ValueError):module.diagnose_readiness_connectivity([scene(0)])
        for mapping in [[],{**POLICY,'banten':'train'},{**POLICY,'banten':True},{}]:
            with self.assertRaises(ValueError):module.diagnose_readiness_connectivity([scene(0)],mapping)
    def test_numeric_bounds_bool_nan_infinity_huge_int_range_reversed_degenerate(self):
        for bounds in [[False,0,1,1],[0,0,float('nan'),1],[0,0,float('inf'),1],[0,0,10**400,1],[0,0,181,1],[0,-91,1,1],[2,0,1,1],[0,0,0,1],[0,0,1],(0,0,1,1)]:
            with self.subTest(bounds=str(bounds)[:80]),self.assertRaises(ValueError):self.diagnose([scene(0,bounds=bounds)])
    def test_full_validation_before_union_and_no_input_mutation_or_file_engine_io(self):
        rows=[scene(0),scene(1,'banten',group='g0')];before=copy.deepcopy(rows);policy=copy.deepcopy(POLICY)
        with patch('builtins.open',side_effect=AssertionError('No source file access')):
            r=self.diagnose(rows)
        self.assertEqual(rows,before);self.assertEqual(POLICY,policy)
        r['witness_edges'][0]['left']['province']='tampered';self.assertEqual(rows,before)
        self.assertFalse(r['readiness_assess_called']);self.assertFalse(r['geometry_engine_called']);self.assertEqual(r['source_files_read'],0)
        for key in ['ready_for_training','scientific_accuracy_validated','training_executed','training_split_leakage_resolved','settlement_authorized','execution_authorized','automatic_resume_allowed','historical_readiness_cause_reconstructed']:self.assertIs(r[key],False)
    def test_seeded_small_cases_match_literal_existing_metadata_union(self):
        rng=random.Random(58)
        for count in range(1,25):
            rows=[]
            for i in range(count):
                x,y=rng.randrange(8),rng.randrange(8)
                rows.append(scene(i,rng.choice(module.PROVINCES),group=rng.choice(['','a','b','c']),scene_id=rng.choice(['a','b','z','']),bounds=[x,y,x+2,y+2]))
            self.assertEqual(self.diagnose(rows,max_witness_edges=2)['province_components'],reference(rows))


if __name__=='__main__':unittest.main()
