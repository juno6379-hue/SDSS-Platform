"""Read-only catalog rows are fed to the pure helper; no registration occurs."""
from pathlib import Path
import datetime,hashlib,json,sqlite3
from app.model_registration_provenance import inspect_model_registration_provenance
ROOT=Path(__file__).resolve().parents[2]
def rows():
    with sqlite3.connect((ROOT/'data/catalog.sqlite3').as_uri()+'?mode=ro',uri=True) as con:
        return con.execute('SELECT kind,id,body FROM records ORDER BY kind,id').fetchall()
def sha(value):return hashlib.sha256(json.dumps(value,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
before=rows()
observations=[inspect_model_registration_provenance(json.loads(body)) for kind,identifier,body in before if kind=='models']
after=rows()
assert before==after
out={'observed_at':datetime.datetime.now().astimezone().isoformat(),'status':'VERIFIED_REAL_LOCAL_STORED_METADATA_ONLY','catalog_records':len(before),'catalog_sha256_before':sha(before),'catalog_sha256_after':sha(after),'models_observed':len(observations),'observations':observations,'scope':'Only in-memory stored metadata observation. No source bytes, registration authenticity, institutional authority or scientific execution approval established.','catalog_unchanged':True,'operating_registrations':0,'model_resolver_connected':False}
(ROOT/'evidence/integration/model-provenance-catalog-observation-20261017.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps(out,ensure_ascii=False))
