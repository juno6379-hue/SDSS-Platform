"""Read existing legacy Jobs with mode=ro; prove no resolver/backfill for legacy."""
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
import datetime,hashlib,json,sqlite3
from app.store import Store
from app.stored_current_binding_preflight import inspect_stored_current_binding_preflight
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
        assert kind=='gmais_jobs','Legacy must not query dataset Registry.'
        self.calls+=1
        return super().get(kind,identifier)
    def put(self,*args,**kwargs):raise AssertionError('Writes forbidden.')
    def list(self,*args,**kwargs):raise AssertionError('Enumeration forbidden.')

def records():
    with sqlite3.connect((ROOT/'data/catalog.sqlite3').resolve().as_uri()+'?mode=ro',uri=True) as con:
        return con.execute('SELECT kind,id,body FROM records ORDER BY kind,id').fetchall()

before=records();store=ReadOnlyStore(ROOT/'data');observations=[]
with patch('app.stored_current_binding_preflight.resolve_job_inputs_with_capture',side_effect=AssertionError('Legacy resolver forbidden.')) as resolver:
    for kind,job_id,raw in before:
        if kind!='gmais_jobs':continue
        assert 'execution_input_binding_capture' not in json.loads(raw)
        calls_before=store.calls
        result=inspect_stored_current_binding_preflight(store,job_id)
        assert result['status']=='UNKNOWN' and result['store_status']=='OBSERVED'
        assert result['store_read_attempted'] is True and result['store_read_observed'] is True
        assert result['store_get_calls']==store.calls-calls_before==1
        assert result['stored_capture_status']=='LEGACY'
        assert result['current_resolution_status']=='NOT_RUN' and result['current_capture_status']=='NOT_RUN'
        assert result['binding_comparison'] is None
        assert result['request_job_sha256']==hashlib.sha256(job_id.encode()).hexdigest()
        assert all(flag is False for key,flag in result.items() if type(flag) is bool and key not in ('store_read_attempted','store_read_observed'))
        assert job_id not in json.dumps(result)
        observations.append({'stored_job_body_sha256':hashlib.sha256(raw.encode()).hexdigest(),'result':result})
    calls_before=store.calls
    missing=inspect_stored_current_binding_preflight(store,'stored-current-missing-job-20261017')
    assert missing['store_status']=='NOT_FOUND' and missing['store_get_calls']==store.calls-calls_before==1
    assert missing['status']=='BLOCKED' and missing['current_resolution_status']=='NOT_RUN'
    calls_before=store.calls
    invalid=inspect_stored_current_binding_preflight(store,'x'*257)
    assert invalid['store_status']=='INVALID_REQUEST' and invalid['store_get_calls']==store.calls-calls_before==0
    assert invalid['status']=='BLOCKED' and invalid['request_job_sha256'] is None
    assert resolver.call_count==0
after=records();assert before==after
canonical=hashlib.sha256(json.dumps(before,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
out={'recorded_at':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(),'scope':'Actual existing legacy reads only; positive current-input verification is tested with isolated synthetic fixtures','jobs':observations,'missing_job':missing,'invalid_literal':invalid,'live_store_constructor_called':False,'ddl_or_writes_performed':False,'store_get_calls':store.calls,'resolver_calls':0,'dataset_registry_get_calls':0,'legacy_capture_backfills':0,'catalog_rows':len(before),'catalog_canonical_sha256_before':canonical,'catalog_canonical_sha256_after':canonical,'catalog_unchanged':True,'actual_executor_connected':False,'new_job_posts':0,'api_calls':0,'qa_or_training_started':False}
(ROOT/'evidence/integration/stored-current-binding-live-validation-20261017.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps({key:out[key] for key in ('store_get_calls','resolver_calls','dataset_registry_get_calls','catalog_rows','catalog_unchanged')}))
