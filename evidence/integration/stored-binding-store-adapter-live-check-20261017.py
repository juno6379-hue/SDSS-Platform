"""Reuse Store.get with mode=ro connections and no live Store constructor/DDL."""
from contextlib import contextmanager
from pathlib import Path
import copy,datetime,hashlib,json,sqlite3
from app.store import Store
from app.stored_job_binding_handoff_store import inspect_stored_job_binding_handoff
ROOT=Path(__file__).resolve().parents[2]

class ReadOnlyStore(Store):
    def __init__(self,root):
        self.root=root.resolve();self.db=self.root/'catalog.sqlite3';self.calls=0
    @contextmanager
    def connect(self):
        connection=sqlite3.connect(self.db.resolve().as_uri()+'?mode=ro',uri=True)
        try:yield connection
        finally:connection.close()
    def get(self,kind,identifier):
        self.calls+=1
        return super().get(kind,identifier)
    def put(self,*args,**kwargs):raise AssertionError('Writes forbidden.')
    def list(self,*args,**kwargs):raise AssertionError('Enumeration forbidden.')

def records():
    with sqlite3.connect((ROOT/'data/catalog.sqlite3').resolve().as_uri()+'?mode=ro',uri=True) as con:
        return con.execute('SELECT kind,id,body FROM records ORDER BY kind,id').fetchall()
def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode()).hexdigest()

before=records();store=ReadOnlyStore(ROOT/'data');observations=[]
for kind,job_id,raw in before:
    if kind!='gmais_jobs':continue
    job=json.loads(raw);request=job['request'];selected=[]
    assert 'execution_input_binding_capture' not in job
    for index,ref in enumerate(request['input_refs']):
        row={key:ref[key] for key in ('id','version','sha256')};row['input_index']=index
        if 'role' in ref:row['role']=ref['role']
        selected.append(row)
    supplied={'job_id':job_id,'agent_id':request['agent_id'],'trace_id':request['execution_context']['trace_id'],'bindings':selected}
    fabricated=copy.deepcopy(supplied)
    for row in fabricated['bindings']:row['manifest_sha256']='a'*64
    mismatch=copy.deepcopy(supplied);mismatch['trace_id']='replay-other-trace'
    malformed=copy.deepcopy(supplied);malformed['bindings'][0]['input_index']=False
    cases=[('selected_request','UNKNOWN',supplied,True),('fabricated_pin_stays_unknown','UNKNOWN',fabricated,True),('trace_mismatch','BLOCKED',mismatch,True),('malformed_supplied','BLOCKED',malformed,False)]
    results=[]
    for name,wanted,value,valid in cases:
        original=copy.deepcopy(value);calls_before=store.calls
        result=inspect_stored_job_binding_handoff(store,job_id,value)
        assert result['store_status']=='OBSERVED' and result['store_read_attempted'] is True and result['store_read_observed'] is True
        assert result['store_get_calls']==store.calls-calls_before==1 and result['issues']==[]
        assert result['request_job_sha256']==hashlib.sha256(job_id.encode()).hexdigest()
        assert all(flag is False for key,flag in result.items() if type(flag) is bool and key not in ('store_read_attempted','store_read_observed'))
        comparison=result['comparison'];assert comparison['status']==wanted and comparison['stored_capture_status']=='LEGACY'
        assert comparison['supplied_bindings_sha256']==(digest(value['bindings']) if valid else None)
        assert comparison['expected_bindings_sha256'] is None and all(flag is False for flag in comparison.values() if type(flag) is bool)
        assert value==original
        for identifier in (job_id,request['agent_id'],request['execution_context']['trace_id']):assert identifier not in json.dumps(result)
        results.append({'case':name,'supplied_source':'LOCAL_REQUEST_COPY_NOT_EXECUTOR_CAPTURE','result':result})
    observations.append({'stored_job_body_sha256':hashlib.sha256(raw.encode()).hexdigest(),'cases':results})

calls=store.calls
missing=inspect_stored_job_binding_handoff(store,'stored-adapter-missing-job-20261017',{})
assert missing['store_status']=='NOT_FOUND' and missing['store_get_calls']==store.calls-calls==1
assert missing['store_read_attempted'] is True and missing['store_read_observed'] is False and missing['comparison'] is None
assert missing['issues']==[{'code':'JOB_NOT_FOUND'}]
calls=store.calls
invalid=inspect_stored_job_binding_handoff(store,'x'*257,{})
assert invalid['store_status']=='INVALID_REQUEST' and invalid['store_get_calls']==store.calls-calls==0
assert invalid['store_read_attempted'] is False and invalid['store_read_observed'] is False and invalid['comparison'] is None
assert invalid['request_job_sha256'] is None and invalid['issues']==[{'code':'INVALID_JOB_ID'}]
after=records();assert before==after
canonical=hashlib.sha256(json.dumps(before,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
out={'recorded_at':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(),'scope':'Actual existing legacy records read by inherited Store.get through mode=ro subclass; supplied declarations remain local replay, not executor capture','live_store_constructor_called':False,'ddl_or_writes_performed':False,'store_get_calls':store.calls,'jobs':observations,'local_comparison_cases':8,'unknown':4,'blocked':4,'missing_job':missing,'invalid_literal':invalid,'catalog_rows':len(before),'catalog_canonical_sha256_before':canonical,'catalog_canonical_sha256_after':canonical,'catalog_unchanged':True,'actual_executor_connected':False,'new_job_posts':0,'api_calls':0,'capture_backfills':0,'qa_or_training_started':False}
(ROOT/'evidence/integration/stored-binding-store-adapter-live-validation-20261017.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps({key:out[key] for key in ('store_get_calls','local_comparison_cases','unknown','blocked','catalog_rows','catalog_unchanged')}))
