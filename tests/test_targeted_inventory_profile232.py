"""232: Temp/모의 크기만 사용. 운영 inventory/원장/HTTP 실행 없음."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from app.data import targeted_inventory_profile as profile
import test_review_bare_targets179 as rf
import test_collect_targeted_bare as cf
import test_targeted_inventory as inf

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'evidence/integration/targeted232-20261018/baseline/scripts'


def original(name):
    spec = importlib.util.spec_from_file_location('baseline232_'+name, BASE/(name+'.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def explicit(request):
    return {**copy.deepcopy(request), 'schema_version': 2,
            'local_support_profile': dict(profile.MARKER)}


class TargetedProfile232Tests(unittest.TestCase):
    def review_fixture(self):
        fixture = rf.Review179Tests(); fixture.setUp(); self.addCleanup(fixture.doCleanups)
        return fixture

    def collector_fixture(self):
        fixture = cf.CollectTargetedBareTests(); fixture.setUp(); self.addCleanup(fixture.tearDown)
        config = fixture.root/'configs'; config.mkdir()
        fixture.write(config/'first-group.collection.json', {})
        return fixture

    def test_exact_profile_default_and_contaminated_marker(self):
        fields = {'schema_version', 'value'}; old = {'schema_version': 1, 'value': 1}
        self.assertEqual(profile.inventory_kwargs(old, fields, 'BAD'), {})
        good = explicit(old)
        self.assertEqual(profile.inventory_kwargs(good, fields, 'BAD'),
                         {'max_files': 10000, 'max_bytes': 3*1024**3})
        variants = [dict(old, schema_version=True), dict(old, schema_version=3),
                    dict(old, local_support_profile=dict(profile.MARKER)),
                    {'schema_version': 2, 'value': 1}]
        for marker in [None, True, 3*1024**3, profile.NAME, {},
                       dict(profile.MARKER, max_bytes=3*1024**3),
                       {'name': profile.NAME, 'sha256': 'f'*64},
                       {'name': 'unknown', 'sha256': profile.SHA256},
                       {'name': True, 'sha256': profile.SHA256}]:
            variants.append(dict(good, local_support_profile=marker))
        variants.append(dict(good, execute=True))
        for value in variants:
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'BAD'):
                profile.inventory_kwargs(value, fields, 'BAD')
        self.assertNotEqual(profile.request_sha256(old), profile.request_sha256(good))
        with self.assertRaises(TypeError): profile.DESCRIPTOR['max_files'] = 1

    def test_review_legacy_exact_output_matches_archived_code(self):
        f = self.review_fixture(); old = original('review_bare_targets179')
        fixed = SimpleNamespace(now=lambda tz: SimpleNamespace(isoformat=lambda: 'fixed232'))
        with patch.object(rf.s, 'datetime', fixed), patch.object(old, 'datetime', fixed), \
             patch.object(rf.s, 'inspect_targeted_inventory', return_value=f.inventory) as new_scan, \
             patch.object(old, 'inspect_targeted_inventory', return_value=f.inventory) as old_scan:
            new = rf.s.review(f.root, f.request); before = old.review(f.root, f.request)
        self.assertEqual(new, before)
        self.assertEqual(new_scan.call_args.kwargs, old_scan.call_args.kwargs)
        self.assertEqual(new_scan.call_args.kwargs, {})
        self.assertEqual(rf.s.select_plan(new, [0, 1]), old.select_plan(before, [0, 1]))

    def test_review_v2_cap_canonical_binding_and_plan_stays256_v1(self):
        f = self.review_fixture(); request = explicit(f.request)
        with patch.object(rf.s, 'inspect_targeted_inventory', return_value=f.inventory) as scan:
            result = rf.s.review(f.root, request)
        self.assertEqual(scan.call_count, 1)
        self.assertEqual(scan.call_args.kwargs, {'max_files': 10000, 'max_bytes': 3*1024**3})
        self.assertEqual(result['schema_version'], 2)
        self.assertEqual(result['request_sha256'], profile.request_sha256(request))
        self.assertEqual(result['local_support_profile'], profile.MARKER)
        self.assertFalse(result['execution_supported']); self.assertFalse(result['actual_quality_eligible'])
        plan = rf.s.select_plan(result, [0]); self.assertEqual(plan['schema_version'], 1)
        self.assertEqual(plan['targets'][0]['source_label_window'][2:], [256, 256])
        bad = dict(request, local_support_profile=dict(profile.MARKER, extra=True))
        with patch.object(rf.s, '_pinned') as pinned, self.assertRaisesRegex(ValueError, 'REQUEST_INVALID'):
            rf.s.review(f.root, bad)
        pinned.assert_not_called()

    def validate(self, fixture, request, jobs, module=cf.module):
        proof = {'status': 'LOCAL_INVENTORY_VERIFIED_EXECUTION_BLOCKED', 'issue': None, 'assets': []}
        physical = {'physical_patch_count': 1, 'limit': 3000, 'observation_sha256': 'a'*64}
        with patch.object(module, 'prepare_targeted_bare_jobs', return_value={
                'status': 'LOCAL_TARGETS_VERIFIED_EXECUTION_BLOCKED', 'issue': None, 'job_proposals': jobs}), \
             patch.object(module, 'inspect_targeted_inventory', return_value=proof) as scan, \
             patch.object(module, 'physical_patch_inventory', return_value=physical):
            checked = module.validate_request(fixture.root, request, module.digest(request))
        return checked, scan.call_args_list

    def test_collector_default_exact_and_every_v2_inventory_uses_same_cap(self):
        f = self.collector_fixture(); jobs = [f.bounded_job(), f.bounded_job('second', 'target-b')]
        request = copy.deepcopy(f.request); request['maximum_batches'] = 2
        request['plan']['targets'] = [{'target_id': j['target_id'], 'target_footprint_native': {}} for j in jobs]
        checked, calls = self.validate(f, request, copy.deepcopy(jobs))
        old = original('collect_targeted_bare')
        old_checked, old_calls = self.validate(f, request, copy.deepcopy(jobs), module=old)
        self.assertEqual(checked, old_checked); self.assertEqual(calls, old_calls)
        self.assertTrue(all(not c.kwargs for c in calls))
        selected = explicit(request); new, calls = self.validate(f, selected, copy.deepcopy(jobs))
        self.assertEqual(len(calls), 2)
        self.assertTrue(all(c.kwargs == {'max_files': 10000, 'max_bytes': 3*1024**3} for c in calls))
        self.assertEqual(new['local_support_profile'], profile.MARKER)
        self.assertEqual(new['maximum_new_physical_patches'], 2)
        oversized = copy.deepcopy(jobs); oversized[0]['config']['window_size'] = 1024
        with self.assertRaisesRegex(ValueError, 'TARGETED_MAXIMUM_NEW_PATCHES_INVALID'):
            self.validate(f, selected, oversized)

    def test_invalid_profile_and_changed_request_pin_reserve_nothing(self):
        f = self.collector_fixture(); request = explicit(f.request)
        before = f.ledger_path.read_bytes(), f.aggregate_path.read_bytes()
        for bad in [dict(request, local_support_profile=True),
                    dict(request, local_support_profile=dict(profile.MARKER, sha256='0'*64))]:
            with patch.object(cf.module, 'CollectionLedger') as ledger, \
                 patch.object(cf.module, 'collect_windows') as collect, \
                 patch.object(cf.module, '_snapshot') as source, \
                 self.assertRaisesRegex(ValueError, 'TARGETED_REQUEST_INVALID'):
                cf.module.run_targeted(f.root, bad, cf.module.digest(bad), execute=True)
            ledger.assert_not_called(); collect.assert_not_called(); source.assert_not_called()
            self.assertFalse(f.lock.exists())
        with patch.object(cf.module, '_snapshot') as source, \
             self.assertRaisesRegex(ValueError, 'TARGETED_REQUEST_PIN_MISMATCH'):
            cf.module.validate_request(f.root, request, cf.module.digest(f.request))
        source.assert_not_called()
        self.assertEqual(before, (f.ledger_path.read_bytes(), f.aggregate_path.read_bytes()))

    def test_mocked_stat_over_two_gib_still_honors_three_gib_boundary(self):
        f = inf.TargetedInventoryTests(); f.setUp(); self.addCleanup(f.tearDown)
        stat, snapshot = f.simulated_support_sizes(34)
        options = profile.inventory_kwargs(explicit({'schema_version': 1}), {'schema_version'}, 'BAD')
        with patch.object(Path, 'stat', stat), patch.object(inf.module, '_snapshot', side_effect=snapshot):
            default = f.run_guard(); selected = f.run_guard(**options)
        self.assertEqual(default['issue'], 'INVENTORY_LIMIT')
        self.assertTrue(selected['inventory_verified'], selected)
        self.assertEqual(selected['support_files_verified'], 34)
        self.assertEqual(selected['resource_limits'], {'max_files': 10000, 'max_support_bytes': 3*1024**3})
        self.assertFalse(selected['execution_supported'])
        over = inf.TargetedInventoryTests(); over.setUp(); self.addCleanup(over.tearDown)
        stat, snapshot = over.simulated_support_sizes(49)
        with patch.object(Path, 'stat', stat), patch.object(inf.module, '_snapshot', side_effect=snapshot):
            blocked = over.run_guard(**options)
        self.assertEqual(blocked['issue'], 'INVENTORY_LIMIT')
        self.assertFalse(blocked['inventory_verified'])

    def test_real_cli_isolated_invalid_v2_never_reaches_operating_inputs(self):
        f = self.review_fixture(); request = f.write('evidence/integration/invalid-v2.json',
            {'schema_version': 2, 'local_support_profile': True})
        (f.root/'data/first-group-training-budget').mkdir()
        driver = f.root/'cli232.py'
        driver.write_text('''import sys
from pathlib import Path
root=Path(sys.argv.pop(1)); workspace=Path(sys.argv.pop(1)); mode=sys.argv.pop(1)
sys.path[:0]=[str(root),str(root/'.runtime'),str(root/'backend'),str(root/'scripts')]
if mode=='review':
 import review_bare_targets179 as m
 m.ROOT=workspace
 raise SystemExit(m.main())
import collect_targeted_bare as m
m.ROOT=workspace
raise SystemExit(m.main())
''', encoding='utf-8')
        for mode in ('review', 'collect'):
            args = ['--request', str(request)]
            if mode == 'review':
                args += ['--request-sha256', f.sha(request), '--output', str(f.root/'evidence/integration/new.json')]
            else: args += ['--expected-request-sha256', cf.module.digest(json.loads(request.read_text())), '--execute']
            child = subprocess.run([sys.executable, '-X', 'utf8', str(driver), str(ROOT), str(f.root), mode, *args],
                                   capture_output=True, text=True, encoding='utf-8', timeout=30)
            self.assertEqual(child.returncode, 2, child.stderr)
            if mode == 'collect':
                result = json.loads(child.stdout)
                self.assertFalse(result['executed'])
                self.assertEqual(result['issue'], 'TARGETED_REQUEST_INVALID')
                self.assertFalse((f.root/'data/first-group-training-budget/global-ledger.execution.lock').exists())
            self.assertFalse((f.root/'evidence/integration/new.json').exists())

    def test_valid_v2_both_cli_temp_contracts(self):
        review = self.review_fixture(); collector = self.collector_fixture()
        request = explicit(review.request)
        review_path = review.write('evidence/integration/v2.json', request)
        output = review.root/'evidence/integration/result.json'
        job = collector.bounded_job()
        selected = explicit(collector.request)
        selected['plan']['targets'] = [{'target_id': job['target_id'], 'target_footprint_native': {}}]
        directory = collector.root/'evidence/integration'; directory.mkdir(parents=True)
        collector_path = directory/'v2.json'; collector.write(collector_path, selected)
        fixture = directory/'jobs.json'; collector.write(fixture, [job])
        driver = review.root/'valid-cli232.py'
        driver.write_text('''import json,sys
from pathlib import Path
root=Path(sys.argv.pop(1)); workspace=Path(sys.argv.pop(1)); mode=sys.argv.pop(1)
sys.path[:0]=[str(root),str(root/'.runtime'),str(root/'backend'),str(root/'scripts')]
def inventory(*args,**kwargs):
 assert kwargs=={'max_files':10000,'max_bytes':3*1024**3},kwargs
 return {'status':'LOCAL_INVENTORY_VERIFIED_EXECUTION_BLOCKED','issue':None,
         'inventory_verified':True,'pending_footprints_verified':True,'source_pins_verified':True,'assets':[]}
if mode=='review':
 import review_bare_targets179 as m
 m.ROOT=workspace; m.inspect_targeted_inventory=inventory
 raise SystemExit(m.main())
import collect_targeted_bare as m
m.ROOT=workspace; m.inspect_targeted_inventory=inventory
jobs=json.loads((workspace/'evidence/integration/jobs.json').read_text())
m.prepare_targeted_bare_jobs=lambda *args:{'status':'LOCAL_TARGETS_VERIFIED_EXECUTION_BLOCKED','issue':None,'job_proposals':jobs}
m.physical_patch_inventory=lambda *args:{'physical_patch_count':1,'limit':3000,'observation_sha256':'a'*64}
raise SystemExit(m.main())
''', encoding='utf-8')
        before = collector.ledger_path.read_bytes(), collector.aggregate_path.read_bytes()
        cases = [('review', review.root, ['--request', str(review_path), '--request-sha256', review.sha(review_path), '--output', str(output)]),
                 ('collect', collector.root, ['--request', str(collector_path), '--expected-request-sha256', cf.module.digest(selected)])]
        for mode, workspace, args in cases:
            child = subprocess.run([sys.executable, '-X', 'utf8', str(driver), str(ROOT), str(workspace), mode, *args],
                                   capture_output=True, text=True, encoding='utf-8', timeout=30)
            self.assertEqual(child.returncode, 0, child.stdout+child.stderr)
            if mode == 'collect':
                result = json.loads(child.stdout)
                self.assertFalse(result['executed']); self.assertEqual(result['local_support_profile'], profile.MARKER)
        result = json.loads(output.read_text())
        self.assertEqual(result['schema_version'], 2)
        self.assertEqual(result['request_sha256'], profile.request_sha256(request))
        self.assertFalse(result['execution_supported'])
        self.assertEqual(before, (collector.ledger_path.read_bytes(), collector.aggregate_path.read_bytes()))
        self.assertFalse(collector.lock.exists())


if __name__ == '__main__': unittest.main()
