"""Independent read-only observation of Root's single bounded continuation."""
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[2]
base=ROOT/'evidence/integration'
before=json.loads((base/'collection-resume-audit-20261018-independent-before.json').read_text(encoding='utf-8'))
snapshot=json.loads((base/'collection-resume-audit-20261018-snapshot.json').read_text(encoding='utf-8'))
next_jobs=json.loads((base/'collection-resume-audit-20261018-next-jobs.json').read_text(encoding='utf-8'))
handover=json.loads((base/'collection-resume-handover-20261018.json').read_text(encoding='utf-8-sig'))
ledger_path=ROOT/'data/first-group-training-budget/global-ledger.json'
ledger_raw=ledger_path.read_bytes()
ledger=json.loads(ledger_raw)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
old_paths=[x for x in snapshot['protected_before'] if '/sources/' in x['path'].replace('\\','/')]
old_changes=[]
for x in old_paths:
    p=ROOT/x['path']
    if p.exists()!=x['exists'] or (x['exists'] and sha(p)!=x['sha256']):old_changes.append(x['path'])
original=json.loads((ROOT/'data/collection-continuation-backup-20261018/global-ledger.json').read_text(encoding='utf-8'))
new_keys=sorted(set(ledger['batches'])-set(original['batches']))
expected_keys=[x['key'] for x in next_jobs['next_jobs']]
new_states={}
for k in expected_keys:
    d=ROOT/'data/first-group-training-esri-v1/sources'/k
    new_states[k]={'ledger':ledger['batches'].get(k),'files':[]}
    for p in sorted(d.rglob('*')):
        if p.is_file():
            info={'path':str(p.relative_to(d)),'bytes':p.stat().st_size}
            if p.name in ('window-state.json','worker-result.json','annual-window-report.json','collection-history.jsonl'):
                info['text']=p.read_text(encoding='utf-8')
            new_states[k]['files'].append(info)
observed={
 'at':datetime.now(timezone.utc).isoformat(),'handover':handover,
 'old_pending_records_unchanged':all(ledger['batches'].get(k)==v for k,v in before['oldpending_records'].items()),
 'old_partial_path_count':len(old_paths),'old_partial_changes':old_changes,
 'fixed_input_changes':[x['path'] for x in before['pins'] if sha(Path(x['path']))!=x['sha256']],
 'backup_checks':[{'path':x['backup'],'sha_matches_record':sha(Path(x['backup']))==x['sha256']} for x in handover['backups']],
 'new_keys':new_keys,'new_keys_within_expected_two':set(new_keys).issubset(expected_keys),
 'original_existing_ledger_record_changes':[k for k,v in original['batches'].items() if ledger['batches'].get(k)!=v],
 'new_budget_maximum_bytes':ledger['additional_maximum_bytes'],'new_charged_bytes':ledger['new_charged_bytes'],
 'within_same_4gib_budget':ledger['additional_maximum_bytes']==4294967296 and ledger['new_charged_bytes']<=4294967296,
 'rate_limit_active':ledger['rate_limit_active'],'new_job_states':new_states,
 'ledger_stable_during_observation':ledger_path.read_bytes()==ledger_raw,
 'stdout':(base/'collection-resume-live-20261018-stdout.log').read_text(encoding='utf-8'),
 'stderr':(base/'collection-resume-live-20261018-stderr.log').read_text(encoding='utf-8'),
 'network_requests_by_observer':0,'source_files_written_by_observer':0,
 'request_spacing_scope':'Configured 2s spacing is retained in existing collector/service code; this filesystem observation is not packet-level timing measurement.'}
filename=base/('collection-resume-audit-20261018-observation-'+datetime.now(timezone.utc).strftime('%H%M%S%f')+'.json')
with filename.open('x',encoding='utf-8') as f:json.dump(observed,f,ensure_ascii=False,indent=2)
print(json.dumps({'evidence':str(filename),'old_pending_unchanged':observed['old_pending_records_unchanged'],'old_partial_changes':old_changes,
                  'fixed_input_changes':observed['fixed_input_changes'],'new_keys':new_keys,'new_keys_within_expected_two':observed['new_keys_within_expected_two'],
                  'rate_limit_active':ledger['rate_limit_active'],'stdout':observed['stdout'],'stderr':observed['stderr']}))
