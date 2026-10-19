from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
R=Path(__file__).resolve().parents[2];E=R/'evidence/integration';F=E/'targeted232-20261018'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
freeze=json.loads((F/'freeze232.json').read_text('utf-8'))
assert sha(F/'freeze232.json')=='67ef6e1f0ca6d81e23b5f54371eec5f619bc16b7c81d1e9b685a2ab726f5e3ed'
assert freeze['tests']['passed']==103 and freeze['tests']['skipped']==0
assert all(sha(R/x['path'])==x['sha256'] and (R/x['path']).stat().st_size==x['bytes'] for x in freeze['files'])
assert all(sha(R/k)==h for k,h in freeze['protected_unchanged'].items())
assert sha(F/'regression-final.log')==freeze['tests']['log']['sha256']
assert sha(F/'patch232.diff')==freeze['patch']['sha256']
req=E/'bare234-prepared-request-root-20261018.json'
request=json.loads(req.read_text('utf-8'))
assert request['local_support_profile']==freeze['profile_marker']
pins={x['path']:x['sha256'] for x in freeze['files'] if x['path'].endswith('.py')}
pins.update(freeze['protected_unchanged'])
record={'status':'REVIEWED_TESTED_LOCAL_FULL_REVIEW_ONLY','at_utc':datetime.now(timezone.utc).isoformat(),
 'source_pins':pins,'request_file_sha256':sha(req),'local_support_profile':freeze['profile_marker'],
 'freeze232_sha256':sha(F/'freeze232.json'),'runner_sha256':sha(E/'bare234-review-runner-root-20261018.py'),
 'maximum_inventory_scans':1,'network_requests_approved':0,'collection_approved':False,
 'training_approved':False,'budget_increased':False,
 'root_review':['strict v1/v2 request fields and canonical binding','fixed marker/descriptor and kwargs',
 'all target inventory calls retain defaults or explicit3GiB','legacy plan/split/quality guards unchanged',
 '103 Temp regression cases including CLI positive/negative and source preservation',
 'five changed file/four protected file SHA and baseline diff checked']}
with (E/'bare234-reviewed-code-pins-root-20261018.json').open('x',encoding='utf-8') as f:json.dump(record,f,ensure_ascii=False,indent=2)
print(json.dumps({'status':record['status'],'collection_approved':False}))
