"""Real HTTP transport with explicitly synthetic diagnostic inputs; no Jobs."""
from pathlib import Path
import copy,datetime,hashlib,json,sqlite3,urllib.request,urllib.error
from app.workflow_node_input_handoff import _digest
ROOT=Path(__file__).resolve().parents[2]
def rows():
    with sqlite3.connect((ROOT/'data/catalog.sqlite3').as_uri()+'?mode=ro',uri=True) as con:
        return con.execute('SELECT kind,id,body FROM records ORDER BY kind,id').fetchall()
def sha(value):return hashlib.sha256(json.dumps(value,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
ref={'id':'synthetic-dataset','version':'v1','sha256':'a'*64,'role':'imagery','uri':'file:///synthetic/not-opened.tif'}
workflow={'schema_version':'0.2.0','workflow_run_id':'synthetic-workflow-model-record-20261017','trace_id':'synthetic-workflow-model-record-20261017','nodes':[{'node_id':'synthetic-node','agent_id':'lcluc-agent','capability_id':'landcover.change_detection','depends_on':[],'input_bindings':[ref]}],'policy':{'on_blocked':'STOP_DEPENDENTS','max_parallel':1,'require_human_approval':True}}
job={'schema_version':'0.2.0','agent_id':'lcluc-agent','capability_id':'landcover.change_detection','input_refs':[copy.deepcopy(ref)],'aoi':{'bbox':[106.1,-6.8,106.2,-6.7],'crs':'EPSG:4326'},'requested_outputs':['COG'],'parameters':{'threshold':0.5},'execution_context':{'trace_id':workflow['trace_id'],'purpose':'synthetic nonexecuting UI contract observation','environment':'development'},'model_ref':{'id':'synthetic-model','version':'v1','sha256':'b'*64}}
record={'id':'synthetic-model','checkpoint_sha256':'b'*64,'training_report_sha256':'c'*64,'model_version_declaration':{'schema_version':1,'source':'CALLER_EXPLICIT_REGISTRATION','version':'v1','checkpoint_sha256':'b'*64,'training_report_sha256':'c'*64}}
def packet(j=job):return {'workflow_request_json':json.dumps(workflow,ensure_ascii=False),'pinned_workflow_request_sha256':_digest(workflow),'selected_node_id':'synthetic-node','full_job_request_json':json.dumps(j,ensure_ascii=False)}
base=packet();matched={**base,'model_record_json':json.dumps(record)}
absent_job=copy.deepcopy(job);del absent_job['model_ref']
blocked_job=copy.deepcopy(job);blocked_job['input_refs'][0]['sha256']='d'*64
cases=[('match_unverified',matched,200,'MODEL_REFERENCE_OBSERVED','MATCH_UNVERIFIED'),('record_omitted',base,200,'MODEL_REFERENCE_OBSERVED','RECORD_NOT_PROVIDED'),('json_null',{**base,'model_record_json':'null'},200,'MODEL_REFERENCE_OBSERVED','RECORD_NOT_PROVIDED'),('record_without_declaration',{**base,'model_record_json':json.dumps({'id':'synthetic-model'})},200,'MODEL_REFERENCE_OBSERVED','REFERENCE_NOT_COMPARABLE'),('reference_absent',packet(absent_job),200,'MODEL_REFERENCE_ABSENT',None),('handoff_blocked',{**packet(blocked_job),'model_record_json':json.dumps(record)},200,'HANDOFF_BLOCKED',None),('transport_null',{**base,'model_record_json':None},400,None,None),('record_duplicate',{**base,'model_record_json':'{"id":"one","id":"two"}'},400,None,None),('record_overflow',{**base,'model_record_json':'{"ignored":1e400}'},400,None,None),('record_budget',{**base,'model_record_json':' '*524289},413,None,None)]
before=rows();results=[]
for name,payload,expected,outer,nested in cases:
    raw=json.dumps(payload,ensure_ascii=False,separators=(',',':')).encode()
    req=urllib.request.Request('http://127.0.0.1:8002/v1/workflows/full-job-model-record-handoff',data=raw,headers={'Content-Type':'application/json'},method='POST')
    try:
        response=urllib.request.urlopen(req,timeout=30);code=response.status;value=json.loads(response.read())
    except urllib.error.HTTPError as exc:code=exc.code;value=json.loads(exc.read())
    assert code==expected,(name,code,value)
    if code==200:
        assert value['request_sha256']==hashlib.sha256(raw).hexdigest()
        assert value['result']['status']==outer
        comparison=value['result']['model_reference_comparison']
        assert (comparison['status'] if comparison else None)==nested
        assert all(value['result'][k] is False for k in ['authority_verified','artifact_bytes_verified','execution_authorized','scientific_accuracy_validated','model_verified'])
    results.append({'case':name,'http_status':code,'expected_outer':outer,'expected_nested':nested,'response':value})
after=rows();assert before==after
out={'observed_at':datetime.datetime.now().astimezone().isoformat(),'scope':'REAL_HTTP_WITH_SYNTHETIC_DIAGNOSTIC_INPUTS_NOT_REAL_WORKFLOW_OR_MODELS','cases':results,'catalog_records':len(before),'catalog_sha256_before':sha(before),'catalog_sha256_after':sha(after),'catalog_unchanged':True,'diagnostic_posts':len(cases),'job_or_workflow_creation_posts':0,'successful_operating_registrations':0,'actual_model_bytes_verified':False,'operating_auth_or_resource_fault_injection':False}
(ROOT/'evidence/integration/workflow-model-record-api-live-api-20261017.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps({'cases':len(results),'catalog_records':len(before),'catalog_unchanged':before==after,'statuses':[x['http_status'] for x in results]},ensure_ascii=False))
