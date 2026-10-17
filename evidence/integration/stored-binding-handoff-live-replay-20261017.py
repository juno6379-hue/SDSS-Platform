"""Replay selected existing legacy declarations locally; not actual executor capture."""
from pathlib import Path
import copy,datetime,hashlib,json,sqlite3
from app.stored_job_binding_handoff import compare_stored_job_binding_handoff
ROOT=Path(__file__).resolve().parents[2]
def records():
    with sqlite3.connect((ROOT/'data/catalog.sqlite3').resolve().as_uri()+'?mode=ro',uri=True) as con:
        return con.execute('SELECT kind,id,body FROM records ORDER BY kind,id').fetchall()
def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode()).hexdigest()
before=records();observations=[]
for kind,job_id,raw in before:
    if kind!='gmais_jobs':continue
    job=json.loads(raw);original=copy.deepcopy(job)
    assert 'execution_input_binding_capture' not in job
    request=job['request']
    selected=[]
    for index,ref in enumerate(request['input_refs']):
        row={key:ref[key] for key in ('id','version','sha256')}
        row['input_index']=index
        if 'role' in ref:row['role']=ref['role']
        selected.append(row)
    supplied={'job_id':job_id,'agent_id':request['agent_id'],'trace_id':request['execution_context']['trace_id'],'bindings':selected}
    fabricated=copy.deepcopy(supplied)
    for row in fabricated['bindings']:row['manifest_sha256']='a'*64
    mismatch=copy.deepcopy(supplied);mismatch['trace_id']='replay-other-trace'
    malformed=copy.deepcopy(supplied);malformed['bindings'][0]['input_index']=False
    cases=[('selected_request_declarations','UNKNOWN',supplied,True),('fabricated_manifest_not_backfilled','UNKNOWN',fabricated,True),('trace_mismatch','BLOCKED',mismatch,True),('malformed_supplied_precedes_legacy','BLOCKED',malformed,False)]
    results=[]
    for name,wanted,value,valid in cases:
        supplied_before=copy.deepcopy(value)
        result=compare_stored_job_binding_handoff(job,job_id,value)
        assert result['status']==wanted,(name,result)
        assert result['stored_capture_status']=='LEGACY'
        assert result['expected_bindings_sha256'] is None
        assert result['request_job_sha256']==hashlib.sha256(job_id.encode()).hexdigest()
        assert result['declarations_match'] is False
        assert result['supplied_bindings_sha256']==(digest(value['bindings']) if valid else None)
        assert all(value is False for key,value in result.items() if type(value) is bool)
        assert job==original and value==supplied_before
        encoded=json.dumps(result,ensure_ascii=False)
        for raw_value in (job_id,request['agent_id'],request['execution_context']['trace_id']):
            assert raw_value not in encoded
        results.append({'case':name,'supplied_source':'LOCAL_COPY_OF_SELECTED_REQUEST_NOT_EXECUTOR_CAPTURE','result':result})
    observations.append({'stored_job_body_sha256':hashlib.sha256(raw.encode()).hexdigest(),'cases':results})
after=records();assert before==after
canonical=hashlib.sha256(json.dumps(before,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
out={'recorded_at':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(),'scope':'Actual stored legacy declarations read only; local supplied replay is not actual executor handoff or capture','jobs':observations,'cases':sum(len(o['cases']) for o in observations),'unknown':sum(c['result']['status']=='UNKNOWN' for o in observations for c in o['cases']),'blocked':sum(c['result']['status']=='BLOCKED' for o in observations for c in o['cases']),'catalog_rows':len(before),'catalog_canonical_sha256_before':canonical,'catalog_canonical_sha256_after':canonical,'catalog_unchanged':True,'actual_executor_connected':False,'new_job_posts':0,'api_calls':0,'capture_backfills':0,'qa_or_training_started':False}
(ROOT/'evidence/integration/stored-binding-handoff-live-validation-20261017.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps({key:out[key] for key in ('cases','unknown','blocked','catalog_rows','catalog_unchanged')}))
