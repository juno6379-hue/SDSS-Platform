"""Explicit bounded deficit-priority entry to the existing shared coordinator."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
for location in (ROOT/'backend', ROOT/'scripts'):
    sys.path.insert(0, str(location))
TARGET_PER_CELL = 28


def _digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,allow_nan=False).encode()).hexdigest()


def _limit(value):
    if type(value) is not int or not 1 <= value <= 2:
        raise ValueError('PRIORITY_BATCH_LIMIT_INVALID')


def _ranked(jobs, scenes, snapshot, limit):
    _limit(limit)
    counts = {}
    eligible = [row for row in scenes if row.get('quality_status') == 'quality_eligible']
    for row in eligible:
        cell = (row['province'],int(row['year']))
        counts[cell] = counts.get(cell,0)+1
    ranked = []
    seen = set()
    for job in jobs:
        key = job['key']
        if key in seen:
            raise ValueError('PRIORITY_DUPLICATE_BATCH_KEY')
        seen.add(key)
        old = snapshot['batches'].get(key)
        if old is not None:
            if old['config_sha256'] != _digest(job['config']):
                raise ValueError('PRIORITY_EXISTING_CONFIG_CHANGED')
            if old['status'] == 'settled':
                continue
            # Explicit continuation must remove pending keys before this function.
            raise ValueError('PRIORITY_PENDING_REQUIRES_EXPLICIT_CONTINUATION')
        province,year = job['province'],job['year']
        prefix = f"{province}/{job['spatial_window_id']}/"
        if any(row['province']==province and int(row['year'])==year and
               row.get('spatial_location_id','').startswith(prefix) for row in eligible):
            continue
        count = counts.get((province,year),0)
        deficit = max(0,TARGET_PER_CELL-count)
        if deficit:
            ranked.append((job,count,deficit))
    ranked.sort(key=lambda item:(-item[2],item[0]['province'],item[0]['year'],
        item[0].get('candidate_rank',0),item[0]['key']))
    return ranked[:limit],counts


def prioritize_jobs(jobs, scenes, snapshot, *, limit):
    """Return at most two original jobs; no config/context/ledger mutation or I/O."""
    selected,_ = _ranked(jobs,scenes,snapshot,limit)
    return [item[0] for item in selected]


def build_priority_plan(jobs, scenes, snapshot, *, limit):
    selected,counts = _ranked(jobs,scenes,snapshot,limit)
    plan = {'schema_version':1,'scope':'EXPLICIT_BOUNDED_PROVINCE_YEAR_DEFICIT_PRIORITY',
        'target_eligible_patches_per_cell':TARGET_PER_CELL,'max_batches':limit,
        'scenes_sha256':_digest(scenes),'ledger_snapshot_sha256':_digest(snapshot),
        'eligible_cells':[{'province':province,'year':year,'eligible_patches':count,
            'deficit':max(0,TARGET_PER_CELL-count)} for (province,year),count in sorted(counts.items())],
        'selected_jobs':[{'key':job['key'],'province':job['province'],'year':job['year'],
            'split':job['split'],'spatial_window_id':job['spatial_window_id'],
            'eligible_patches':count,'deficit':deficit,'config_sha256':_digest(job['config'])}
            for job,count,deficit in selected],
        'pending_reservations_preserved':[{'key':key,'reserved_bytes':row['reserved_bytes'],
            'charged_bytes':row['charged_bytes'],'config_sha256':row['config_sha256']}
            for key,row in sorted(snapshot['batches'].items()) if row['status']=='pending'],
        'bare_targeted_256_supported':False,'new_budget_added':False,'learning_ready':False}
    plan['plan_sha256'] = _digest(plan)
    return plan


def verify_priority_plan(jobs, scenes, snapshot, *, limit, expected_sha256):
    if type(expected_sha256) is not str or len(expected_sha256)!=64 or any(c not in '0123456789abcdef' for c in expected_sha256):
        raise ValueError('PRIORITY_PLAN_PIN_REQUIRED')
    if build_priority_plan(jobs,scenes,snapshot,limit=limit)['plan_sha256'] != expected_sha256:
        raise ValueError('PRIORITY_PLAN_CHANGED')
    return prioritize_jobs(jobs,scenes,snapshot,limit=limit)


def _load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,allow_abbrev=False)
    parser.add_argument('--output',type=Path,default=ROOT/'data/first-group-training-esri-v1')
    parser.add_argument('--centers-per-province',type=int,default=4)
    parser.add_argument('--candidate-plan',type=Path,action='append',default=[])
    parser.add_argument('--max-batches',type=int,required=True)
    parser.add_argument('--continue-unrelated-pending',action='store_true')
    parser.add_argument('--expected-plan-sha256')
    parser.add_argument('--execute',action='store_true')
    args = parser.parse_args(argv)
    try:
        _limit(args.max_batches)
        if not 1 <= args.centers_per_province <= 16:
            raise ValueError('PRIORITY_CENTER_COUNT_INVALID')
        output=args.output.resolve(); output.relative_to(ROOT/'data')
        from collect_training_parallel import v2_jobs,extra_jobs,continuation_jobs
        base=_load(ROOT/'configs/first-group.collection.json')
        snapshot=_load(ROOT/'data/first-group-training-budget/global-ledger.json')
        aggregate=_load(output/'annual-window-report.json')
        jobs=extra_jobs(base,args.candidate_plan,args.centers_per_province)+v2_jobs(base,args.centers_per_province)
        jobs,continuation=continuation_jobs(jobs,snapshot,args.continue_unrelated_pending)
        plan=build_priority_plan(jobs,aggregate['scenes'],snapshot,limit=args.max_batches)
        if not args.execute:
            print(json.dumps({'executed':False,'priority_plan':plan,'pending_continuation':continuation},ensure_ascii=True))
            return 0
        verify_priority_plan(jobs,aggregate['scenes'],snapshot,limit=args.max_batches,
            expected_sha256=args.expected_plan_sha256)
        command=[sys.executable,str(ROOT/'scripts/collect_training_parallel.py'),'--execute',
            '--priority-deficit','--priority-plan-sha256',plan['plan_sha256'],
            '--output',str(output),'--centers-per-province',str(args.centers_per_province),
            '--max-batches',str(args.max_batches)]
        if args.continue_unrelated_pending:command.append('--continue-unrelated-pending')
        for path in args.candidate_plan:command.extend(['--candidate-plan',str(path)])
        return subprocess.run(command,check=False,stdout=sys.stdout,stderr=sys.stderr).returncode
    except Exception:
        print(json.dumps({'executed':False,'status':'BLOCKED','issue':'PRIORITY_REQUEST_OR_SNAPSHOT_INVALID'}))
        return 2


if __name__=='__main__':
    raise SystemExit(main())
