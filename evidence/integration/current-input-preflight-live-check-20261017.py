"""Read-only live new route and unchanged legacy routes; no Job submission."""
from pathlib import Path
import datetime,hashlib,json,sqlite3,urllib.request,urllib.error
ROOT=Path(__file__).resolve().parents[2]
def records():
    with sqlite3.connect((ROOT/'data/catalog.sqlite3').resolve().as_uri()+'?mode=ro',uri=True) as con:
        return con.execute('SELECT kind,id,body FROM records ORDER BY kind,id').fetchall()
def get(path):
    try:
        with urllib.request.urlopen('http://127.0.0.1:8002'+path,timeout=20) as response:
            return response.status,{k.lower():v for k,v in response.headers.items()},json.load(response)
    except urllib.error.HTTPError as error:
        return error.code,{k.lower():v for k,v in error.headers.items()},json.load(error)
before=records()
prior=json.loads((ROOT/'evidence/integration/current-input-preflight-old-api-before-20261017.json').read_text('utf-8'))
prior_cases={case['request_job_sha256']:case['outputs'] for case in prior['cases']}
observations=[]
for kind,job_id,raw in before:
    if kind!='gmais_jobs':continue
    assert 'execution_input_binding_capture' not in json.loads(raw)
    sha=hashlib.sha256(job_id.encode()).hexdigest()
    status,headers,result=get('/v1/jobs/'+job_id+'/input-preflight')
    assert status==200 and headers.get('cache-control')=='no-store'
    assert result['scope']=='STORED_TO_CURRENT_DIRECT_INPUT_PREFLIGHT_ONLY'
    assert result['status']=='UNKNOWN' and result['stored_capture_status']=='LEGACY'
    assert result['request_job_sha256']==sha and result['store_get_calls']==1 and result['resolver_pass_calls']==0
    assert result['current_resolution_status']=='NOT_RUN' and result['current_capture_status']=='NOT_RUN'
    assert result['current_input_count'] is None and result['current_integrity_verified_count'] is None
    assert result['current_quality_public_observed_count'] is None and result['current_quality_public_diagnostics_passed'] is None
    assert result['current_blocker_count'] is None and result['current_blockers']==[] and result['binding_comparison'] is None
    assert all(value is False for key,value in result.items() if type(value) is bool and key not in ('store_read_attempted','store_read_observed'))
    old_outputs={}
    for suffix in ['execution-input-binding','','input-resolution']:
        path='/v1/jobs/'+job_id+('/'+suffix if suffix else '')
        old_status,_,body=get(path);old_outputs[suffix or 'status']={'http_status':old_status,'body':body}
    assert old_outputs==prior_cases[sha]
    observations.append({'request_job_sha256':sha,'http_status':status,'cache_control':headers['cache-control'],'preflight':result,'old_capture_status_input_resolution_exact_match':True})
errors=[]
for name,literal,status,code,message in [
    ('missing','current-preflight-missing-job-20261017',404,'JOB_NOT_FOUND','Job was not found.'),
    ('oversized','x'*257,400,'INVALID_REQUEST','Invalid preflight request.'),
    ('control','invalid%0Ajob',400,'INVALID_REQUEST','Invalid preflight request.')]:
    actual,headers,body=get('/v1/jobs/'+literal+'/input-preflight')
    assert actual==status and headers.get('cache-control')=='no-store'
    assert body=={'error':{'code':code,'message':message,'retryable':False}}
    errors.append({'case':name,'http_status':actual,'body':body})
after=records();assert before==after
canonical=hashlib.sha256(json.dumps(before,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
assert canonical==prior['catalog_canonical_sha256']
out={'recorded_at':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(),'scope':'Actual existing legacy route observations only; MATCH/blocked current file verification and429/503/cancellation remain synthetic tests','jobs':observations,'safe_errors':errors,'get_requests':len(observations)*4+3,'old_api_baseline_get_requests':prior['get_requests'],'catalog_rows':len(before),'catalog_canonical_sha256_before':canonical,'catalog_canonical_sha256_after':canonical,'catalog_unchanged':True,'old_api_responses_unchanged':True,'actual_resolver_passes_for_legacy':0,'new_job_posts':0,'capture_backfills':0,'qa_or_training_started':False,'actual_executor_connected':False}
(ROOT/'evidence/integration/current-input-preflight-live-api-20261017.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps({key:out[key] for key in ('get_requests','catalog_rows','catalog_unchanged','old_api_responses_unchanged')}))
