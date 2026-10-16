#!/usr/bin/env python3
"""GMAIS v0.2 local reference adapter — MOCK/contract testing only.
Not a real LCLUC model or production-approved agent.
"""
import json, uuid, datetime, os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

JOBS = {}; IDEMPOTENCY = {}
AGENTS = {
 'lcluc-agent': {'agent_id':'lcluc-agent','readiness':'BLOCKED','model_approval_status':'DRAFT','capabilities':[{'capability_id':'landcover.change_detection'}], 'reason':'TRAIN_DATA_INSUFFICIENT'},
 'contract-test-agent': {'agent_id':'contract-test-agent','readiness':'READY','model_approval_status':'DRAFT','capabilities':[{'capability_id':'contract.echo'}], 'reason':'SANDBOX_ONLY_MOCK'}
}
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00','Z')
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def response(self,code,data,headers=None):
  raw=json.dumps(data,ensure_ascii=False).encode('utf-8');self.send_response(code);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(raw)))
  for k,v in (headers or {}).items():self.send_header(k,v)
  self.end_headers();self.wfile.write(raw)
 def error(self,status,code,trace='unknown',retryable=False):self.response(status,{'error':{'code':code,'message':code.replace('_',' '),'trace_id':trace,'retryable':retryable}})
 def auth(self):return self.headers.get('Authorization') == 'Bearer local-contract-test-token'
 def do_GET(self):
  p=self.path.split('?')[0]; parts=p.strip('/').split('/')
  if p in ['/healthz','/readyz']:return self.response(200,{'status':'UP','scope':'reference-contract-only'})
  if not self.auth():return self.error(401,'UNAUTHORIZED')
  if p=='/v1/agents':return self.response(200,{'items':list(AGENTS.values())})
  if len(parts)>=3 and parts[:2]==['v1','agents']:
   a=AGENTS.get(parts[2]);
   if not a:return self.error(404,'AGENT_NOT_IMPLEMENTED')
   if len(parts)==3:return self.response(200,a)
   if parts[3]=='capabilities':return self.response(200,{'items':a['capabilities']})
   if parts[3]=='readiness':return self.response(200,{'agent_id':parts[2],'data_ready':a['readiness']=='READY','model_approved':a['model_approval_status']=='APPROVED','scope':'MOCK' if parts[2]=='contract-test-agent' else 'REAL_BLOCKED','blocking_reasons':[a['reason']]})
  if len(parts)>=3 and parts[:2]==['v1','jobs']:
   job=JOBS.get(parts[2]);
   if not job:return self.error(404,'JOB_NOT_FOUND')
   if len(parts)==3:return self.response(200,job['status'])
   if len(parts)==4 and parts[3]=='results':return self.response(200,job['result'])
  if len(parts)==3 and parts[:2]==['v1','results']:
   for j in JOBS.values():
    if j['result']['result_id']==parts[2]:return self.response(200,j['result'])
  return self.error(404,'JOB_NOT_FOUND')
 def do_POST(self):
  p=self.path.split('?')[0]; parts=p.strip('/').split('/')
  if not self.auth():return self.error(401,'UNAUTHORIZED')
  try:
   n=int(self.headers.get('Content-Length','0'))
   if n>1024*1024:return self.error(400,'INVALID_REQUEST')
   payload=json.loads(self.rfile.read(n) or b'{}')
  except Exception:return self.error(400,'INVALID_REQUEST')
  if len(parts)==4 and parts[:2]==['v1','agents'] and parts[3]=='jobs':
   agent=parts[2];trace=payload.get('execution_context',{}).get('trace_id','unknown'); key=self.headers.get('Idempotency-Key')
   if not key:return self.error(400,'INVALID_REQUEST',trace)
   if payload.get('agent_id')!=agent:return self.error(400,'INVALID_REQUEST',trace)
   if agent!='contract-test-agent':return self.error(409,'MODEL_NOT_READY',trace)
   ctx=payload.get('execution_context',{})
   if ctx.get('environment')!='development' or ctx.get('purpose')!='contract-test':return self.error(409,'MODEL_NOT_APPROVED',trace)
   if payload.get('capability_id')!='contract.echo' or not payload.get('input_refs'):return self.error(400,'INVALID_REQUEST',trace)
   from hashlib import sha256
   digest=sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
   if key in IDEMPOTENCY:
    oldhash,jid=IDEMPOTENCY[key]
    if oldhash!=digest:return self.error(409,'SCHEMA_MISMATCH',trace)
    return self.response(202,JOBS[jid]['status'],{'Location':'/v1/jobs/'+jid})
   jid='job-'+uuid.uuid4().hex[:12];rid='res-'+uuid.uuid4().hex[:12]
   status={'schema_version':'0.2.0','job_id':jid,'agent_id':agent,'status':'SUCCEEDED','trace_id':trace,'submitted_at':now(),'progress':1.0,'result_id':rid}
   result={'schema_version':'0.2.0','result_id':rid,'job_id':jid,'agent_id':agent,'status':'MOCK_ONLY','output_assets':[], 'input_refs':payload['input_refs'],'spatial':payload.get('aoi'), 'validation':{'validation_level':'CONTRACT_ONLY','report_ref':'local://contract-test'},'provenance':{'trace_id':trace,'processing_version':'0.2.0'},'limitations':['MOCK contract test result. Never use for policy or scientific analysis.']}
   JOBS[jid]={'status':status,'result':result};IDEMPOTENCY[key]=(digest,jid)
   return self.response(202,status,{'Location':'/v1/jobs/'+jid})
  if len(parts)==4 and parts[:2]==['v1','jobs'] and parts[3]=='cancel':return self.error(409,'INVALID_REQUEST')
  return self.error(404,'JOB_NOT_FOUND')

def run_server(port=8787):
 server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
 try: server.serve_forever()
 finally:server.server_close()
if __name__=='__main__':run_server(int(os.environ.get('GMAIS_PORT','8787')))
