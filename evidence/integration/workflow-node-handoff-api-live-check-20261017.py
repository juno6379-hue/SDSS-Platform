"""Local live HTTP transport smoke with explicitly synthetic declarations; no Job creation."""
from pathlib import Path
import copy,datetime,hashlib,json,sqlite3,urllib.request,urllib.error
ROOT=Path(__file__).resolve().parents[2]
BASE='http://127.0.0.1:8002'
PATH='/v1/workflows/node-input-handoff'

def dump(v):return json.dumps(v,ensure_ascii=False,separators=(',',':')).encode('utf-8')
def canonical(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def sha(b):return hashlib.sha256(b).hexdigest()
def records():
 with sqlite3.connect((ROOT/'data/catalog.sqlite3').as_uri()+'?mode=ro',uri=True) as c:return c.execute('SELECT kind,id,body FROM records ORDER BY kind,id').fetchall()
def send(raw,path=PATH):
 req=urllib.request.Request(BASE+path,data=raw,headers={'Content-Type':'application/json'},method='POST')
 try: response=urllib.request.urlopen(req,timeout=30)
 except urllib.error.HTTPError as error:response=error
 with response:return response.status,json.load(response),response.headers.get('Cache-Control')
def clean(v):
 if type(v) is dict:return {k:clean(x) for k,x in v.items() if k not in {'assessed_at','evaluated_at','assessment_started_at','assessment_finished_at'}}
 if type(v) is list:return [clean(x) for x in v]
 return v
before=records()
fixture=json.loads((ROOT/'evidence/integration/workflow-node-handoff-canonical-fixture-20261017.json').read_text('utf-8'))
workflow=fixture['workflow_request'];proposal=fixture['proposed_job_metadata']
assert canonical(workflow)==fixture['canonical_json'] and sha(canonical(workflow).encode())==fixture['sha256']
envelope=dict(workflow_request_json=json.dumps(workflow,ensure_ascii=False,indent=2),pinned_workflow_request_sha256=fixture['sha256'],selected_node_id=fixture['selected_node_id'],proposed_job_metadata_json=json.dumps(proposal,ensure_ascii=False,indent=2))
cases=[]
def test(label,request,expected_status,expected_result=None):
 raw=request if type(request) is bytes else dump(request)
 status,result,cache=send(raw);assert status==expected_status,(label,status,result);assert cache=='no-store',(label,cache)
 if status==200:
  assert set(result)=={'extension','approval_status','present_in_upstream_openapi','request_sha256','result'}
  assert result['request_sha256']==sha(raw) and result['result']['status']==expected_result
  assert result['present_in_upstream_openapi'] is False
  assert all(v is False for k,v in result['result'].items() if type(v) is bool and k!='declarations_match')
  for k in ('network_requests','source_files_read','source_files_written','database_calls','registry_calls','resolver_calls','executor_calls'):assert result['result'][k]==0
  assert 'file:///' not in json.dumps(result)
 else:
  expected={400:('INVALID_REQUEST','Invalid handoff request.'),413:('REQUEST_TOO_LARGE','Handoff request exceeds limits.')}[status]
  assert result=={'error':{'code':expected[0],'message':expected[1],'retryable':False}},(label,result)
 cases.append({'case':label,'status':status,'cache_control':cache,'request_sha256':sha(raw),'response':result})
test('synthetic_unicode_match',envelope,200,'MATCH')
changed=copy.deepcopy(envelope);p=copy.deepcopy(proposal);p['input_refs'][0].pop('role');changed['proposed_job_metadata_json']=json.dumps(p,ensure_ascii=False);test('role_presence_drift',changed,200,'BLOCKED')
changed=copy.deepcopy(envelope);changed['pinned_workflow_request_sha256']='0'*64;test('wrong_caller_pin',changed,200,'BLOCKED')
changed=copy.deepcopy(envelope);w=copy.deepcopy(workflow);w['nodes'][0]['input_bindings']=[];changed.update(workflow_request_json=json.dumps(w,ensure_ascii=False),pinned_workflow_request_sha256=sha(canonical(w).encode()));test('selected_empty_not_backfilled',changed,200,'BLOCKED')
test('duplicate_outer',b'{"workflow_request_json":"{}","workflow_request_json":"{}"}',400)
for key in ('workflow_request_json','proposed_job_metadata_json'):
 changed=copy.deepcopy(envelope);changed[key]='{"duplicate":1,"duplicate":2}';test('duplicate_'+key,changed,400)
changed=copy.deepcopy(envelope);changed['proposed_job_metadata_json']='{"value":NaN}';test('nonfinite_inner',changed,400)
test('invalid_utf8',b'\xff',400)
changed=copy.deepcopy(envelope);changed['proposed_job_metadata_json']='['*13+'0'+']'*13;test('inner_depth_budget',changed,413)
test('body_byte_budget',b' '*(1048576+1),413)
old=json.loads((ROOT/'evidence/integration/workflow-node-handoff-api-old-workflow-before-20261017.json').read_text('utf-8'));old_observations=[]
for item in old['records']:
 status,result,cache=send(json.dumps(old['request']).encode('utf-8'),item['path']);assert status==item['status'] and clean(result)==item['response_without_volatile_timestamps'],item['path'];old_observations.append({'path':item['path'],'status':status,'parsed_response_unchanged_except_volatile_timestamps':True})
after=records();assert before==after
out={'recorded_at':datetime.datetime.now().astimezone().isoformat(),'scope':'REAL_LOCAL_HTTP_WITH_SYNTHETIC_CALLER_DECLARATIONS_NOT_OPERATING_WORKFLOW_EXECUTION','new_endpoint_posts':len(cases),'old_diagnostic_posts_after':len(old_observations),'old_diagnostic_posts_before':2,'cases':cases,'old_response_comparison':old_observations,'catalog_records':len(after),'catalog_canonical_sha256_before':sha(dump(before)),'catalog_canonical_sha256_after':sha(dump(after)),'catalog_unchanged':True,'new_job_posts':0,'capture_backfills':0,'actual_executor_connected':False,'new_qa_or_training_executed':False,'limits':['HTTP503 corruption/failure and auth use isolated tests; no operating Workflow executor verified.']}
(ROOT/'evidence/integration/workflow-node-handoff-api-live-api-20261017.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps({k:out[k] for k in ('new_endpoint_posts','old_diagnostic_posts_after','old_diagnostic_posts_before','catalog_records','catalog_unchanged')},ensure_ascii=False))
