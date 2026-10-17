from pathlib import Path
import hashlib,json,datetime,sqlite3
ROOT=Path(__file__).resolve().parents[2]
def record(path):
 b=path.read_bytes();return {'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
snapshot=json.loads((ROOT/'docs/understanding/EVIDENCE_SNAPSHOT.json').read_text('utf-8'))
assert all(record(ROOT/n)==p for n,p in snapshot['files'].items())
prior=json.loads((ROOT/'evidence/integration/workflow-model-record-api-preflight-20261017.json').read_text('utf-8'))
protected=prior['protected_references']
for name,p in protected.items():
 path=Path(name);assert path.exists()==p['exists']
 if path.exists():assert record(path)=={k:p[k] for k in ('sha256','bytes')}
names=[]
for name in names:
 p=ROOT/name; target=ROOT/'evidence/integration'/('recovery-commit-contract-original-'+p.stem+'-20261017.py')
 assert not target.exists();target.write_bytes(p.read_bytes())
with sqlite3.connect((ROOT/'data/catalog.sqlite3').as_uri()+'?mode=ro',uri=True) as c:
 rows=c.execute('SELECT kind,id,body FROM records ORDER BY kind,id').fetchall()
sha=hashlib.sha256(json.dumps(rows,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
assert sha=='72cf29dae2c6790907559d38d92ebf43eaf6ede795607637b0a46ccdaa5b754b'
out={'recorded_at':datetime.datetime.now().isoformat(),'tracked_baseline':snapshot['files'],'protected_references':protected,'authorized_existing_code_changes':names,'snapshot_checked':len(snapshot['files']),'snapshot_mismatches':[],'catalog_records':len(rows),'catalog_sha256':sha}
(ROOT/'evidence/integration/recovery-commit-contract-preflight-20261017.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),'utf-8')
print('Baseline1243/protected141/catalog14 unchanged; only new standalone contract files authorized.')
