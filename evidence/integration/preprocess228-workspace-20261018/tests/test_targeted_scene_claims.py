import copy
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import unittest
from unittest.mock import patch

from app.data.targeted_scene_claims import SceneClaimRegistry, FALSE_FIELDS


def seed(rows=None):
    return {'schema_version': 1, 'kind': 'DECLARED_SCENE_SPLIT_HISTORY',
            'source_manifest_sha256': 'a'*64, 'scenes': rows or []}


def request(scene='S2_2025_scene', split='train', owner='worker-1'):
    return {'schema_version': 1, 'scene_id': scene, 'split': split, 'owner_id': owner}


class TargetedSceneClaimsTests(unittest.TestCase):
    def race(self, registry, requests):
        barrier = Barrier(len(requests))
        def run(value):
            barrier.wait(timeout=10)
            return registry.claim(value)
        with ThreadPoolExecutor(max_workers=len(requests)) as workers:
            return list(workers.map(run, requests))

    def test_same_unseen_scene_cross_split_race_has_exactly_one_claim(self):
        # Repeat with fresh coordinator objects to exercise either lock winner.
        for _ in range(20):
            registry = SceneClaimRegistry(seed())
            outcomes = self.race(registry, [request(split='train'), request(split='val', owner='worker-2')])
            self.assertEqual(sum(out['claim'] is not None for out in outcomes), 1)
            self.assertEqual([out['issue'] for out in outcomes].count('SCENE_ALREADY_CLAIMED'), 1)
            self.assertEqual(registry.snapshot()['claim_count'], 1)

    def test_existing_cross_split_veto_and_multi_split_quarantine(self):
        registry = SceneClaimRegistry(seed([{'scene_id': 'known', 'split': 'train'},
                                           {'scene_id': 'mixed', 'split': 'train'},
                                           {'scene_id': 'mixed', 'split': 'val'}]))
        self.assertEqual(registry.claim(request('known', 'test'))['issue'], 'DECLARED_SPLIT_CONFLICT')
        self.assertIsNotNone(registry.claim(request('known'))['claim'])
        for split in ('train', 'val', 'test'):
            self.assertEqual(registry.claim(request('mixed', split))['issue'], 'SEEDED_SCENE_QUARANTINED')
        self.assertEqual(registry.snapshot()['quarantined_scene_count'], 1)
        self.assertEqual(registry.snapshot()['claim_count'], 1)

    def test_owner_replay_only_for_same_scene_and_split(self):
        registry = SceneClaimRegistry(seed())
        initial = registry.claim(request())
        replay = registry.claim(request())
        self.assertFalse(initial['replayed']); self.assertTrue(replay['replayed'])
        self.assertEqual(registry.claim(request(owner='other'))['issue'], 'SCENE_ALREADY_CLAIMED')
        self.assertEqual(registry.claim(request(split='val'))['issue'], 'SCENE_ALREADY_CLAIMED')
        another = registry.claim(request(scene='different'))
        self.assertIsNotNone(another['claim']); self.assertFalse(another['replayed'])

    def test_concurrent_cap_and_idempotent_replay_when_full(self):
        registry = SceneClaimRegistry(seed([{'scene_id': 'history', 'split': 'train'}]), max_claims=1)
        outcomes = self.race(registry, [request('new-a'), request('new-b', owner='worker-2')])
        winners = [out for out in outcomes if out['claim'] is not None]
        self.assertEqual(len(winners), 1)
        self.assertEqual([out['issue'] for out in outcomes].count('CLAIM_CAP_REACHED'), 1)
        winner = winners[0]['claim']
        self.assertTrue(registry.claim(request(winner['scene_id'], winner['split'], winner['owner_id']))['replayed'])
        self.assertEqual(registry.snapshot()['claim_count'], 1)

    def test_return_value_pollution_and_input_mutation_do_not_change_registry(self):
        history = seed([{'scene_id': 'known', 'split': 'train'}]); before = copy.deepcopy(history)
        registry = SceneClaimRegistry(history)
        value = request(); value_before = copy.deepcopy(value)
        out = registry.claim(value)
        self.assertEqual(value, value_before); self.assertEqual(history, before)
        out['claim']['split'] = 'test'
        history['scenes'][0]['split'] = 'val'
        value['split'] = 'test'
        snapshot = registry.snapshot(); snapshot['claims'][0]['owner_id'] = 'pollution'
        self.assertEqual(registry.claim(request())['claim'], {'scene_id': 'S2_2025_scene', 'split': 'train', 'owner_id': 'worker-1'})
        self.assertEqual(registry.claim(request('known', 'val'))['issue'], 'DECLARED_SPLIT_CONFLICT')

    def test_invalid_seeds_and_caps_fail_closed_without_partial_state(self):
        variants = []
        for field, value in [('schema_version', True), ('source_manifest_sha256', 'A'*64),
                             ('scenes', [{'scene_id': 'good', 'split': 'train'}, {'scene_id': 'bad', 'split': 'validation'}]),
                             ('scenes', [{'scene_id': 's', 'split': 'train'}]*1025)]:
            row = seed(); row[field] = value; variants.append(row)
        row = seed(); row['extra'] = True; variants.append(row)
        row = seed(); row['loop'] = row; variants.append(row)
        row = seed(); row['scenes'] = [{'scene_id': '../secret', 'split': 'train'}]; variants.append(row)
        for row in variants:
            registry = SceneClaimRegistry(row)
            self.assertEqual(registry.claim(request())['issue'], 'SEED_INVALID')
            self.assertEqual(registry.snapshot()['claim_count'], 0)
            self.assertEqual(registry.snapshot()['declared_history_scene_count'], 0)
        for cap in (True, 0, -1, 1025, '2', float('inf')):
            self.assertEqual(SceneClaimRegistry(seed(), cap).claim(request())['issue'], 'CLAIM_CAP_INVALID')

    def test_invalid_requests_do_not_consume_capacity_or_leak_inputs(self):
        registry = SceneClaimRegistry(seed(), 1)
        variants = []
        for field, value in [('schema_version', True), ('scene_id', True), ('scene_id', '../SECRET'),
                             ('scene_id', 'x'*161), ('owner_id', ''), ('owner_id', 'x'*81),
                             ('owner_id', 'owner\nSECRET'), ('split', True), ('split', 'validation')]:
            row = request(); row[field] = value; variants.append(row)
        row = request(); row['extra'] = float('nan'); variants.append(row)
        for row in variants:
            out = registry.claim(row)
            self.assertEqual(out['issue'], 'CLAIM_REQUEST_INVALID')
            self.assertEqual(out['claim_count'], 0)
            self.assertNotIn('SECRET', str(out))
        self.assertIsNotNone(registry.claim(request())['claim'])

    def test_no_io_and_all_unverified_guards_remain_false(self):
        with patch('builtins.open', side_effect=AssertionError('No file IO')), \
             patch('pathlib.Path.open', side_effect=AssertionError('No file IO')), \
             patch('socket.socket', side_effect=AssertionError('No network')):
            registry = SceneClaimRegistry(seed())
            outputs = [registry.snapshot(), registry.claim(request()), registry.claim(request()),
                       registry.claim(request(split='val'))]
        for out in outputs:
            for field in FALSE_FIELDS:
                self.assertIs(out[field], False)

    def test_separate_coordinators_are_explicitly_not_shared(self):
        first, second = SceneClaimRegistry(seed()), SceneClaimRegistry(seed())
        self.assertIsNotNone(first.claim(request())['claim'])
        self.assertIsNotNone(second.claim(request(split='val'))['claim'])
        self.assertFalse(first.snapshot()['execution_supported'])

    def test_copy_failure_from_concurrent_caller_mutation_is_fixed_and_recoverable(self):
        registry = SceneClaimRegistry(seed())
        with patch('app.data.targeted_scene_claims._copy_json', side_effect=RuntimeError('SECRET caller changed dict size')):
            failed = registry.claim(request())
            uninitialized = SceneClaimRegistry(seed())
        self.assertEqual(failed['issue'], 'CLAIM_REQUEST_INVALID')
        self.assertNotIn('SECRET', str(failed))
        self.assertEqual(uninitialized.snapshot()['issue'], 'SEED_INVALID')
        self.assertIsNotNone(registry.claim(request())['claim'])


if __name__ == '__main__':
    unittest.main()
