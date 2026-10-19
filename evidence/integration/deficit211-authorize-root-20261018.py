from pathlib import Path
from datetime import datetime, timezone
import json, hashlib
R=Path(__file__).resolve().parents[2]; E=R/'evidence/integration'
def read(p): return json.loads(p.read_text('utf-8-sig'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
prior=read(E/'deficit209-reviewed-code-pins-root-20261018.json')
assert all(sha(R/p)==h for p,h in prior['source_pins'].items())
ui=read(E/'service207-candidate-final-ui-20261018.json')
assert ui['status']=='VERIFIED_REAL_PUBLISHED207_CANDIDATE_BROWSER'
assert ui['candidate']['eligible']==1339 and ui['candidate']['source_matches_current']
assert ui['current']['cell_gap']==24 and ui['checks']['logs']==[]
record={**prior,'at_utc':datetime.now(timezone.utc).isoformat(),
 'separate_execution_run':'211','maximum_batches':1,'maximum_new_physical_patches':16,
 'selected_cells':[['southeast_sulawesi',2024]],
 'publication207_sha256':sha(E/'priority207-publication-root-20261018.json'),
 'actual_ui207_sha256':sha(E/'service207-candidate-final-ui-20261018.json'),
 'supervisor_sha256':sha(E/'deficit211-supervisor-root-20261018.py'),
 'request_file_sha256':sha(E/'deficit211-prepared-request-root-20261018.json'),
 'fresh_guard_required':True,'old_pending_preserved_bytes':136314880}
with (E/'deficit211-reviewed-code-pins-root-20261018.json').open('x',encoding='utf-8') as f:
 json.dump(record,f,ensure_ascii=False,indent=2)
print(json.dumps({'status':record['status'],'maximum_batches':1,'maximum_new_physical_patches':16}))
