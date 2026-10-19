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
OFFICIAL_PROVINCES = ('south_sulawesi','gorontalo','southeast_sulawesi','banten','west_java','east_java')


def _digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,allow_nan=False).encode()).hexdigest()


def _limit(value):
    if type(value) is not int or not 1 <= value <= 2:
        raise ValueError('PRIORITY_BATCH_LIMIT_INVALID')


def validate_province_priority(value):
    """Explicit official slugs only. None preserves the legacy plan exactly."""
    if value is None:
        return None
    if type(value) not in (list,tuple) or not value or any(type(p) is not str or p not in OFFICIAL_PROVINCES for p in value) or len(set(value))!=len(value):
        raise ValueError('PRIORITY_PROVINCE_ORDER_INVALID')
    return tuple(value)


def _ranked(jobs, scenes, snapshot, limit, province_priority=None, *, all_ranked=False):
    _limit(limit)
    order = validate_province_priority(province_priority)
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
    def key(item):
        old = (-item[2],item[0]['province'],item[0]['year'],item[0].get('candidate_rank',0),item[0]['key'])
        if order is None:return old
        return ((order.index(item[0]['province']) if item[0]['province'] in order else len(order)),*old)
    ranked.sort(key=key)
    return (ranked if all_ranked else ranked[:limit]),counts


def prioritize_jobs(jobs, scenes, snapshot, *, limit, province_priority=None):
    """Return at most two original jobs; no config/context/ledger mutation or I/O."""
    selected,_ = _ranked(jobs,scenes,snapshot,limit,province_priority)
    return [item[0] for item in selected]


def build_priority_plan(jobs, scenes, snapshot, *, limit, province_priority=None):
    order = validate_province_priority(province_priority)
    available,counts = _ranked(jobs,scenes,snapshot,limit,order,all_ranked=True)
    selected = available[:limit]
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
    if order is not None:
        plan['province_priority_order'] = list(order)
        plan['priority_region_status'] = []
        for province in order:
            eligible_count = sum(counts.get((province,y),0) for y in range(2020,2026))
            deficit = sum(max(0,TARGET_PER_CELL-counts.get((province,y),0)) for y in range(2020,2026))
            candidate_count = sum(job['province']==province for job,_,_ in available)
            selected_count = sum(job['province']==province for job,_,_ in selected)
            status = ('REGION_TARGET_MET' if deficit==0 else
                'BLOCKED_NO_AVAILABLE_DEFICIT_JOB' if candidate_count==0 else
                'DEFICIT_JOB_SELECTED' if selected_count else 'AVAILABLE_NOT_SELECTED_BATCH_LIMIT')
            plan['priority_region_status'].append({'province':province,'eligible_patches':eligible_count,
                'deficit_to_28':deficit,'available_deficit_jobs':candidate_count,
                'selected_jobs':selected_count,'status':status})
    plan['plan_sha256'] = _digest(plan)
    return plan


def verify_priority_plan(jobs, scenes, snapshot, *, limit, expected_sha256, province_priority=None):
    if type(expected_sha256) is not str or len(expected_sha256)!=64 or any(c not in '0123456789abcdef' for c in expected_sha256):
        raise ValueError('PRIORITY_PLAN_PIN_REQUIRED')
    if build_priority_plan(jobs,scenes,snapshot,limit=limit,province_priority=province_priority)['plan_sha256'] != expected_sha256:
        raise ValueError('PRIORITY_PLAN_CHANGED')
    return prioritize_jobs(jobs,scenes,snapshot,limit=limit,province_priority=province_priority)


def _load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,allow_abbrev=False)
    parser.add_argument('--output',type=Path,default=ROOT/'data/first-group-training-esri-v1')
    parser.add_argument('--centers-per-province',type=int,default=4)
    parser.add_argument('--candidate-plan',type=Path,action='append',default=[])
    parser.add_argument('--max-batches',type=int,required=True)
    parser.add_argument('--priority-province',action='append',choices=OFFICIAL_PROVINCES,default=None,
                        help='명시 순서로 부족 주를 우선; 반복 지정, 생략 시 기존 정렬/SHA 보존')
    parser.add_argument('--continue-unrelated-pending',action='store_true')
    parser.add_argument('--expected-plan-sha256')
    parser.add_argument('--execute',action='store_true')
    args = parser.parse_args(argv)
    try:
        _limit(args.max_batches)
        order = validate_province_priority(args.priority_province)
        if not 1 <= args.centers_per_province <= 16:
            raise ValueError('PRIORITY_CENTER_COUNT_INVALID')
        output=args.output.resolve(); output.relative_to(ROOT/'data')
        from collect_training_parallel import v2_jobs,extra_jobs,continuation_jobs
        base=_load(ROOT/'configs/first-group.collection.json')
        snapshot=_load(ROOT/'data/first-group-training-budget/global-ledger.json')
        aggregate=_load(output/'annual-window-report.json')
        jobs=extra_jobs(base,args.candidate_plan,args.centers_per_province)+v2_jobs(base,args.centers_per_province)
        jobs,continuation=continuation_jobs(jobs,snapshot,args.continue_unrelated_pending)
        plan=build_priority_plan(jobs,aggregate['scenes'],snapshot,limit=args.max_batches,province_priority=order)
        if not args.execute:
            print(json.dumps({'executed':False,'priority_plan':plan,'pending_continuation':continuation},ensure_ascii=True))
            return 0
        verify_priority_plan(jobs,aggregate['scenes'],snapshot,limit=args.max_batches,
            expected_sha256=args.expected_plan_sha256,province_priority=order)
        command=[sys.executable,str(ROOT/'scripts/collect_training_parallel.py'),'--execute',
            '--priority-deficit','--priority-plan-sha256',plan['plan_sha256'],
            '--output',str(output),'--centers-per-province',str(args.centers_per_province),
            '--max-batches',str(args.max_batches)]
        if args.continue_unrelated_pending:command.append('--continue-unrelated-pending')
        for province in order or ():command.extend(['--priority-province',province])
        for path in args.candidate_plan:command.extend(['--candidate-plan',str(path)])
        return subprocess.run(command,check=False,stdout=sys.stdout,stderr=sys.stderr).returncode
    except Exception:
        print(json.dumps({'executed':False,'status':'BLOCKED','issue':'PRIORITY_REQUEST_OR_SNAPSHOT_INVALID'}))
        return 2


if __name__=='__main__':
    raise SystemExit(main())
