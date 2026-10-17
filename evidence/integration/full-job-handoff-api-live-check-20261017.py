"""Actual local HTTP with synthetic full Job drafts; no submission or execution."""
from pathlib import Path
import copy,datetime,hashlib,json,sqlite3,urllib.request,urllib.error
ROOT=Path(__file__).resolve().parents[2]
BASE='http://127.0.0.1:8002';PATH='/v1/workflows/full-job-input-handoff'
def dump(v):return json.dumps(v,ensure_ascii=False,separators=(',',':')).encode('utf-8')
def canonical(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def sha(b):return hashlib.sha256(b).hexdigest()
def records():
 with sqlite3.connect((ROOT/'data/catalog.sqlite3').as_uri()+'?mode=ro',uri=True) as c:return c.execute('SELECT kind,id,body FROM records ORDER BY kind,id').fetchall()
def send(raw,path=PATH):
 req=urllib.request.Request(BASE+path,data=raw,headers={'Content-Type':'application/json'},method='POST')
 try:res=urllib.request.urlopen(req,timeout=30)
 except urllib.error.HTTPError as error:res=error
 with res:return res.status,json.load(res),res.headers.get('Cache-Control')
def clean(v):
 if type(v) is dict:return {k:clean(x) for k,x in v.items() if k not in {'assessed_at','evaluated_at','assessment_started_at','assessment_finished_at'}}
 if type(v) is list:return [clean(x) for x in v]
 return v
before=records()
ref={'id':'synthetic-full-job-input-20261017','version':'v1','sha256':'a'*64,'role':'imagery','uri':'file:///synthetic/no-read.tif'}
w={'schema_version':'0.2.0','workflow_run_id':'synthetic-full-job-api-20261017','trace_id':'synthetic-full-job-trace','nodes':[{'node_id':'n1','agent_id':'lcluc-agent','capability_id':'landcover.change_detection','depends_on':[],'input_bindings':[ref]}],'policy':{'on_blocked':'STOP_DEPENDENTS','max_parallel':1,'require_human_approval':True}}
j={'schema_version':'0.2.0','agent_id':'lcluc-agent','capability_id':'landcover.change_detection','input_refs':[copy.deepcopy(ref)],'aoi':{'bbox':[106.125,-6.875,106.225,-6.775],'crs':'EPSG:4326'},'requested_outputs':['map'],'execution_context':{'trace_id':w['trace_id'],'purpose':'synthetic draft check','environment':'development','workflow_run_id':w['workflow_run_id']},'parameters':{'rate':0.01,'unit':1.0,'signed_zero':-0.0}}
env={'workflow_request_json':json.dumps(w,ensure_ascii=False,indent=2),'pinned_workflow_request_sha256':sha(canonical(w).encode()),'selected_node_id':'n1','full_job_request_json':dump(j).decode().replace('"rate":0.01','"rate":1e-2')}
cases=[]
def test(label,payload,status_expected,result_expected=None):
 raw=payload if type(payload) is bytes else dump(payload)
 status,value,cache=send(raw);assert status==status_expected,(label,status,value);assert cache=='no-store',(label,cache)
 if status==200:
  assert set(value)=={'extension','approval_status','present_in_upstream_openapi','request_sha256','result'}
  assert value['extension']=='greenblue.workflow-full-job-input-handoff.rfc1' and value['request_sha256']==sha(raw) and value['present_in_upstream_openapi'] is False
  result=value['result'];assert result['status']==result_expected
  assert result['schema_files_read'] is None
  for k in ('network_requests','source_files_read','source_files_written','database_calls','registry_calls','resolver_calls','executor_calls'):assert type(result[k]) is int and result[k]==0
  assert all(v is False for k,v in result.items() if type(v) is bool and k not in {'declarations_match','full_job_schema_validated','bbox_numeric_order_validated','validator_attempted'})
  assert 'file:///' not in json.dumps(value)
 else:
  code,message={400:('INVALID_REQUEST','Invalid full Job handoff request.'),413:('REQUEST_TOO_LARGE','Full Job handoff request exceeds limits.')}[status]
  assert value=={'error':{'code':code,'message':message,'retryable':False}},(label,value)
 cases.append({'case':label,'status':status,'cache_control':cache,'request_sha256':sha(raw),'response':value})
 return value
first=test('decimal_exponent_negative_zero_match',env,200,'MATCH')
changed=copy.deepcopy(env);other=copy.deepcopy(j);other['aoi']['bbox'][0]=106.15;changed['full_job_request_json']=dump(other).decode();second=test('changed_aoi_is_observation_not_workflow_aoi_comparison',changed,200,'MATCH')
assert first['result']['full_job_request_sha256']!=second['result']['full_job_request_sha256'] and first['result']['extracted_metadata_sha256']==second['result']['extracted_metadata_sha256']
for label,mutate in [('missing_required_aoi',lambda v:v.pop('aoi')),('invalid_datetime',lambda v:v.update(time_range={'start':'2026-10-17T00:00:00+00:60'})),('role_presence_drift',lambda v:v['input_refs'][0].pop('role'))]:
 changed=copy.deepcopy(env);other=copy.deepcopy(j);mutate(other);changed['full_job_request_json']=dump(other).decode();test(label,changed,200,'BLOCKED')
changed=copy.deepcopy(env);changed['pinned_workflow_request_sha256']='0'*64;test('wrong_workflow_pin',changed,200,'BLOCKED')
changed=copy.deepcopy(env);other=copy.deepcopy(w);other['nodes'][0]['input_bindings']=[];changed.update(workflow_request_json=dump(other).decode(),pinned_workflow_request_sha256=sha(canonical(other).encode()));test('selected_empty_not_invented',changed,200,'BLOCKED')
test('outer_duplicate',b'{"x":1,"x":2}',400)
for key in ('workflow_request_json','full_job_request_json'):
 changed=copy.deepcopy(env);changed[key]='{"duplicate":1,"duplicate":2}';test('duplicate_'+key,changed,400)
test('invalid_utf8',b'\xff',400)
for label,token,status in [('nonfinite','NaN',400),('overflow','1e999',400),('nonzero_underflow','1e-999',400),('huge_exponent','0e'+'9'*64,400),('numeric_token_limit','0.'+'1'*128,413)]:
 changed=copy.deepcopy(env);changed['full_job_request_json']='{"value":'+token+'}';test(label,changed,status)
changed=copy.deepcopy(env);changed['full_job_request_json']='['*25+'0'+']'*25;test('full_job_depth_limit',changed,413)
changed=copy.deepcopy(env);changed['full_job_request_json']=' '*(524288+1);test('full_job_text_limit',changed,413)
test('body_byte_limit',b' '*(1048576+1),413)
old=json.loads((ROOT/'evidence/integration/full-job-handoff-api-old-workflow-before-20261017.json').read_text('utf-8'));old_checks=[]
for row in old['records']:
 status,value,cache=send(row['request_body_utf8'].encode(),row['path']);assert status==row['status'] and clean(value)==row['response_without_volatile_timestamps'],row['path'];old_checks.append({'path':row['path'],'status':status,'response_unchanged_except_volatile_timestamps':True})
after=records();assert before==after
out={'recorded_at':datetime.datetime.now().astimezone().isoformat(),'scope':'REAL_LOCAL_HTTP_WITH_SYNTHETIC_FULL_JOB_DRAFTS_NOT_SUBMISSION_OR_OPERATING_WORKFLOW','new_endpoint_posts':len(cases),'old_diagnostic_posts_before':3,'old_diagnostic_posts_after':len(old_checks),'cases':cases,'old_response_comparison':old_checks,'catalog_records':len(after),'catalog_canonical_sha256_before':sha(dump(before)),'catalog_canonical_sha256_after':sha(dump(after)),'catalog_unchanged':True,'full_job_observed_sha_changed_for_aoi_change':True,'metadata_sha_unchanged_for_aoi_change':True,'new_job_posts':0,'actual_executor_connected':False,'new_qa_or_training_executed':False,'limits':['Schema resource HTTP503, authentication and corrupted reply tests use isolated fixtures.','New comparison asset/DB counters0 excludes local schema reads; schema_files_read remains unmeasured null.']}
(ROOT/'evidence/integration/full-job-handoff-api-live-api-20261017.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps({k:out[k] for k in ('new_endpoint_posts','old_diagnostic_posts_after','catalog_records','catalog_unchanged')},ensure_ascii=False))
