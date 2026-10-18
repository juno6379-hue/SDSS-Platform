"""Read-only live collection audit; writes only this task's new evidence files."""
import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'backend')]
from backend.app.data.recovery import inspect_recovery
from backend.app.data.recovery_terminal import inspect_recovery_terminal
from backend.app.data.recovery_aggregate import inspect_recovery_aggregate

PREFIX = ROOT / 'evidence/integration/collection-resume-audit-20261018-'
def save(suffix, value):
    with Path(str(PREFIX) + suffix + '.json').open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def entry(path):
    if not path.exists():
        return {'path': str(path.relative_to(ROOT)), 'exists': False}
    st = path.stat()
    return {'path': str(path.relative_to(ROOT)), 'exists': True, 'bytes': st.st_size,
            'sha256': sha(path), 'mtime_utc': datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(),
            'mtime_kst': datetime.fromtimestamp(st.st_mtime, timezone(timedelta(hours=9))).isoformat()}

ledger_path = ROOT / 'data/first-group-training-budget/global-ledger.json'
output = ROOT / 'data/first-group-training-esri-v1'
ledger = json.loads(ledger_path.read_text(encoding='utf-8'))
keys = [k for k, v in ledger['batches'].items() if v['status'] == 'pending']
protected = [ledger_path, ledger_path.with_suffix('.execution.lock'), ledger_path.with_suffix('.lock'),
             output/'annual-window-report.json', output/'run-result.json', output/'parallel-v2-plan.json']
for k in keys:
    d = output / 'sources' / k
    protected += list(p for p in d.rglob('*') if p.is_file())
    protected += [d/'worker-result.json', d/'annual-window-report.json']
protected = sorted(set(protected))
before = [entry(p) for p in protected]
start = datetime.now(timezone.utc).isoformat()
recovery = inspect_recovery(ROOT/'data')
terminal = inspect_recovery_terminal(ROOT/'data')
aggregate_inspection = inspect_recovery_aggregate(ROOT/'data')
save('recovery', recovery)
save('terminal', terminal)
save('aggregate', aggregate_inspection)

aggregate = json.loads((output/'annual-window-report.json').read_text(encoding='utf-8'))
plan = json.loads((output/'parallel-v2-plan.json').read_text(encoding='utf-8'))
pending = []
for k in keys:
    d = output/'sources'/k
    cfg = json.loads((d/'config.json').read_text(encoding='utf-8'))
    state = json.loads((d/'window-state.json').read_text(encoding='utf-8'))
    files = [entry(p) for p in sorted(d.rglob('*')) if p.is_file()]
    histories = [p.read_text(encoding='utf-8') for p in d.rglob('collection-history.jsonl')]
    pending.append({'key':k, 'reservation':ledger['batches'][k], 'config':cfg, 'window_state':state,
                    'files':files, 'history_text':histories,
                    'aggregate_source_references': [p for p in aggregate.get('source_manifests',[]) if k in p],
                    'aggregate_patch_ids': [r.get('id') for r in aggregate['scenes'] if k in json.dumps(r)]})

# Reproduce current coordinator's queue filters from the stored plan metadata only.
provinces = [a['id'] for a in json.loads((ROOT/'configs/first-group.collection.json').read_text(encoding='utf-8'))['aois']]
queues = {p:[] for p in provinces}
eligible = [r for r in aggregate['scenes'] if r.get('quality_status') == 'quality_eligible']
for job in plan['jobs']:
    prefix = f"{job['province']}/{job['spatial_window_id']}/"
    if not any(r.get('province')==job['province'] and int(r['year'])==job['year'] and r.get('spatial_location_id','').startswith(prefix) for r in eligible):
        queues[job['province']].append(job)
for queue in queues.values():
    queue.sort(key=lambda j:(j.get('candidate_rank',int(j['spatial_window_id']) if j['spatial_window_id'].isdigit() else 0),j['year'],j['key']))
queue = [queues[p][i] for i in range(max(map(len,queues.values()),default=0)) for p in provinces if i<len(queues[p])]
for j in queue:
    j['ledger_state'] = ledger['batches'].get(j['key'],{}).get('status','UNRESERVED')
new = [j for j in queue if j['ledger_state']=='UNRESERVED']
after = [entry(p) for p in protected]
save('snapshot', {'started_at':start,'finished_at':datetime.now(timezone.utc).isoformat(),
                 'protected_before':before, 'protected_after':after, 'protected_unchanged':before==after,
                 'pending':pending, 'stored_plan_queue_after_eligible_filter':queue,
                 'first_unreserved_candidates':new[:12], 'unreserved_candidate_count':len(new),
                 'new_budget_remaining_bytes': ledger['additional_maximum_bytes']-ledger['new_charged_bytes'],
                 'network_requests':0,'source_files_written':0,
                 'queue_scope':'Stored plan metadata only; not current full job-config revalidation or execution authorization'})
print(json.dumps({'protected_unchanged':before==after, 'protected_count':len(before), 'pending':len(keys),
                  'first_unreserved_keys':[j['key'] for j in new[:6]], 'unreserved_count':len(new)}))
