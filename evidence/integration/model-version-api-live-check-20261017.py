"""Negative-only local API observation; never registers a successful model."""
from pathlib import Path
import datetime, hashlib, json, sqlite3, urllib.request, urllib.error
ROOT = Path(__file__).resolve().parents[2]
report = 'results/__ui_model_version_missing_20261017__/experiment.json'
assert not (ROOT / 'data' / report).exists()
def catalog():
    with sqlite3.connect((ROOT/'data/catalog.sqlite3').as_uri()+'?mode=ro', uri=True) as con:
        rows=con.execute('SELECT kind,id,body FROM records ORDER BY kind,id').fetchall()
    return {'records':len(rows),'sha256':hashlib.sha256(json.dumps(rows,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()}
before=catalog()
results=[]
for name,extra in [('omitted',{}),('explicit_fixed',{'model_version':' v1 '}),('explicit_null',{'model_version':None}),('alias',{'model_version':'latest'})]:
    body={'report_path':report,**extra}
    request=urllib.request.Request('http://127.0.0.1:8002/api/models/register-experiment',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'},method='POST')
    try:
        response=urllib.request.urlopen(request,timeout=20)
        code=response.status; content=response.read().decode()
    except urllib.error.HTTPError as exc:
        code=exc.code;content=exc.read().decode()
    results.append({'case':name,'status':code,'response':json.loads(content)})
    assert code==422,(name,code,content)
after=catalog()
assert before==after
out={'observed_at':datetime.datetime.now().astimezone().isoformat(),'scope':'LIVE_NEGATIVE_ONLY_MISSING_REPORT_ERROR_PRECEDES_VERSION_VALIDATION','requests':results,'catalog_before':before,'catalog_after':after,'successful_operating_registrations':0,'positive_version_branch_proven_here':False,'positive_evidence':'AST-isolated actual route and TempStore/mock tests, not operating registration','browser_requests_separate':True}
(ROOT/'evidence/integration/model-version-api-live-api-20261017.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps(out,ensure_ascii=False))
