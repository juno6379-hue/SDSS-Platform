"""Read-only operating GETs; no registration, artifact access or model mutation."""
from pathlib import Path
import datetime,hashlib,json,sqlite3,urllib.request,urllib.error,urllib.parse
from app.model_registration_provenance import inspect_model_registration_provenance
ROOT=Path(__file__).resolve().parents[2]
def rows():
    with sqlite3.connect((ROOT/'data/catalog.sqlite3').as_uri()+'?mode=ro',uri=True) as con:
        return con.execute('SELECT kind,id,body FROM records ORDER BY kind,id').fetchall()
def sha(value):return hashlib.sha256(json.dumps(value,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
before=rows();models=[(identifier,json.loads(body)) for kind,identifier,body in before if kind=='models']
assert len(models)==1
identifier,model=models[0];expected=inspect_model_registration_provenance(model)
results=[]
for origin in ['http://127.0.0.1:8002','http://127.0.0.1:5174']:
    for label,model_id in [('existing',identifier),('missing','__missing_model_provenance_20261017__')]:
        endpoint=origin+'/api/models/'+urllib.parse.quote(model_id,safe='')+'/registration-provenance'
        try:
            response=urllib.request.urlopen(endpoint,timeout=20);code=response.status;body=response.read().decode()
        except urllib.error.HTTPError as exc:
            code=exc.code;body=exc.read().decode()
        value=json.loads(body)
        assert code==(200 if label=='existing' else 404),(endpoint,code,value)
        if label=='existing':assert value==expected
        results.append({'origin':origin,'case':label,'status':code,'response':value})
after=rows();assert before==after
out={'observed_at':datetime.datetime.now().astimezone().isoformat(),'scope':'VERIFIED_REAL_READ_ONLY_STORED_METADATA_NOT_BYTES_OR_AUTHORITY','requests':results,'catalog_records':len(before),'catalog_sha256_before':sha(before),'catalog_sha256_after':sha(after),'catalog_unchanged':True,'successful_operating_registrations':0,'job_posts':0,'operating_503_or_auth_failure_injection':False,'limits':'503, auth401 and non-ABSENT observation states tested in isolated synthetic API tests only; operating Store/data not fault-injected.'}
(ROOT/'evidence/integration/model-provenance-api-live-api-20261017.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps(out,ensure_ascii=False))
