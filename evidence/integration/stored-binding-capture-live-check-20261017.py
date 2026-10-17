"""Read-only live API observations; never creates or backfills a Job."""
from pathlib import Path
import datetime
import hashlib
import json
import sqlite3
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parents[2]

def catalog():
    with sqlite3.connect((ROOT/'data/catalog.sqlite3').resolve().as_uri()+'?mode=ro', uri=True) as con:
        rows = con.execute('SELECT kind,id,body FROM records ORDER BY kind,id').fetchall()
    digest = hashlib.sha256(json.dumps(rows,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
    return rows,digest

def get(path):
    try:
        with urllib.request.urlopen('http://127.0.0.1:8002'+path,timeout=20) as response:
            return response.status,{k.lower():v for k,v in response.headers.items()},json.load(response)
    except urllib.error.HTTPError as error:
        return error.code,{k.lower():v for k,v in error.headers.items()},json.load(error)

before,sha_before = catalog()
observations=[]
for kind,identifier,raw in before:
    if kind!='gmais_jobs': continue
    stored=json.loads(raw)
    assert 'execution_input_binding_capture' not in stored
    status,headers,body=get('/v1/jobs/'+identifier+'/execution-input-binding')
    assert status==200 and headers.get('cache-control')=='no-store'
    assert body['status']=='LEGACY' and body['request_binding_count']==len(stored['request']['input_refs'])
    assert body['request_job_sha256']==hashlib.sha256(identifier.encode()).hexdigest()
    assert body['capture_binding_count'] is None and body['manifest_pin_count'] is None
    assert body['expected_bindings_sha256'] is None and body['stored_binding_integrity_match'] is False
    assert all(value is False for key,value in body.items() if type(value) is bool)
    old_status,_,old_body=get('/v1/jobs/'+identifier)
    assert old_status==200 and old_body==stored['status']
    resolution_status,_,resolution=get('/v1/jobs/'+identifier+'/input-resolution')
    assert resolution_status==200
    observations.append({'request_job_sha256':body['request_job_sha256'],'http_status':status,'cache_control':headers['cache-control'],'projection':body,'old_status_exact_match':True,'input_resolution_status':resolution_status,'input_resolution':resolution})
missing_status,missing_headers,missing=get('/v1/jobs/stored-capture-missing-job-20261017/execution-input-binding')
assert missing_status==404 and missing_headers.get('cache-control')=='no-store'
assert missing=={'error':{'code':'JOB_NOT_FOUND','message':'Job was not found.','retryable':False}}
invalid_status,invalid_headers,invalid=get('/v1/jobs/'+'x'*257+'/execution-input-binding')
assert invalid_status==200 and invalid_headers.get('cache-control')=='no-store'
assert invalid['status']=='INVALID' and invalid['request_job_sha256'] is None
after,sha_after=catalog()
assert before==after and sha_before==sha_after
result={'recorded_at':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(),'scope':'VERIFIED_REAL existing legacy API reads only; RECORDED generation remains synthetic','jobs':observations,'missing_job':{'http_status':missing_status,'body':missing},'invalid_job_literal':{'http_status':invalid_status,'body':invalid},'catalog_rows':len(before),'canonical_records_sha256_before':sha_before,'canonical_records_sha256_after':sha_after,'catalog_unchanged':True,'actual_job_posts':0,'capture_backfills':0,'executor_started':False,'qa_or_training_started':False}
(ROOT/'evidence/integration/stored-binding-capture-live-api-20261017.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps({'legacy_jobs':len(observations),'get_requests':len(observations)*3+2,'missing_status':missing_status,'invalid_literal_status':invalid_status,'catalog_unchanged':True}))
