"""Actual local diagnostic HTTP only. Never submit/create an operating Job."""
from pathlib import Path
import copy,datetime,hashlib,json,urllib.request,urllib.error
from test_workflow_job_request_handoff import full_fixture
from app.workflow_node_input_handoff import _digest
r=Path.cwd();url='http://127.0.0.1:8002/v1/workflows/full-job-input-handoff';results=[]
def call(label,w,j,version=None,expected_status=200,expected_axis=None,expected_outer=None,raw_override=None):
 e={'workflow_request_json':json.dumps(w,ensure_ascii=False,indent=2),'pinned_workflow_request_sha256':_digest(w),'selected_node_id':'private-node','full_job_request_json':json.dumps(j,ensure_ascii=False,indent=2)}
 if version is not None:e['contract_version']=version
 raw=json.dumps(e,ensure_ascii=False,separators=(',',':')).encode() if raw_override is None else raw_override
 try:
  with urllib.request.urlopen(urllib.request.Request(url,data=raw,headers={'Content-Type':'application/json'}),timeout=30) as response:code=response.status;body=response.read();headers=dict(response.headers)
 except urllib.error.HTTPError as response:code=response.code;body=response.read();headers=dict(response.headers)
 data=json.loads(body);assert code==expected_status,(label,code,data)
 assert next(v for k,v in headers.items() if k.lower()=='cache-control')=='no-store'
 if code==200:
  assert data['request_sha256']==hashlib.sha256(raw).hexdigest()
  if version==2 and type(version)is int:
   out=data['result'];assert out['local_manifest_registration']['status']==expected_axis,(label,out)
   assert out['status']==expected_outer
   assert all(out[k]is False for k in ['actual_capability_supported','institution_acl_verified','execution_authorized'])
  else:assert data['extension'].endswith('.rfc1')
 results.append({'label':label,'http_status':code,'request_sha256':hashlib.sha256(raw).hexdigest(),'response':data})
 return data
w,j=full_fixture();a=call('legacy_unknown_agent_still_match',w,j,expected_outer='MATCH');assert a['result']['status']=='MATCH'
call('rfc2_unknown_agent',w,j,2,expected_axis='AGENT_UNKNOWN',expected_outer='BLOCKED')
w['nodes'][0].update(agent_id='lcluc-agent',capability_id='landcover.change_detection');j.update(agent_id='lcluc-agent',capability_id='landcover.change_detection')
call('rfc2_registered_lcluc_not_execution',w,j,2,expected_axis='REGISTERED',expected_outer='MATCH')
w['nodes'][0]['capability_id']=j['capability_id']='unregistered-capability';call('rfc2_known_agent_unknown_capability',w,j,2,expected_axis='CAPABILITY_UNREGISTERED',expected_outer='BLOCKED')
w['nodes'][0].update(agent_id='flood-drought-agent',capability_id='flood-drought');j.update(agent_id='flood-drought-agent',capability_id='flood-drought');call('rfc2_registered_external_not_implemented',w,j,2,expected_axis='REGISTERED',expected_outer='MATCH')
j['time_range']={'start':'not-a-date'};call('rfc2_schema_blocked_registration_not_run',w,j,2,expected_axis='NOT_RUN',expected_outer='BLOCKED');del j['time_range']
j['input_refs'][0]['role']='different-role';call('rfc2_metadata_blocked_registration_not_run',w,j,2,expected_axis='NOT_RUN',expected_outer='BLOCKED')
for version in [True,False,1,3,'2',2.0]:call('invalid_contract_version_'+repr(version),w,j,version,400)
call('malformed_outer_json',w,j,expected_status=400,raw_override=b'{')
w0,j0=full_fixture();z=call('legacy_unknown_agent_after_rfc2_calls',w0,j0);assert a==z
out={'recorded_at':datetime.datetime.now().astimezone().isoformat(),'status':'TESTED_SYNTHETIC','scope':'Actual local HTTP diagnostic on synthetic drafts; no Job submission, Store or Workflow execution','url':url,'cases':results,'v1_before_after_byte_equivalent_json':a==z,'operating_job_posts':0,'training_or_collection':False,'non_reload_api_8000_8001_applied':'UNVERIFIED'}
(r/'evidence/integration/full-job-registration-api-live-api-20261017.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),'utf-8');print(json.dumps({'cases':len(results),'status':'PASS','v1_before_after_equal':a==z}))
