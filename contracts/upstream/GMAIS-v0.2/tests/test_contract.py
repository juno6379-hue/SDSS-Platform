import unittest, json, threading, urllib.request, urllib.error, os
from pathlib import Path
import jsonschema, yaml
from http.server import ThreadingHTTPServer
from reference_adapter.server import Handler, JOBS, IDEMPOTENCY
ROOT = Path(__file__).resolve().parents[1]

def read_json(p):return json.loads((ROOT/p).read_text(encoding='utf-8'))
class GmaisContractTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.httpd=ThreadingHTTPServer(('127.0.0.1',0), Handler);cls.port=cls.httpd.server_address[1]
  cls.thread=threading.Thread(target=cls.httpd.serve_forever, daemon=True);cls.thread.start()
 @classmethod
 def tearDownClass(cls):cls.httpd.shutdown();cls.httpd.server_close();cls.thread.join(timeout=2)
 def request(self,route,method='GET',payload=None,token='local-contract-test-token',extra=None):
  data=json.dumps(payload).encode() if payload is not None else None
  headers={'Authorization':'Bearer '+token,'Content-Type':'application/json',**(extra or {})}
  req=urllib.request.Request(f'http://127.0.0.1:{self.port}{route}', data=data,method=method,headers=headers)
  try:
   with urllib.request.urlopen(req,timeout=5) as r:return r.status,dict(r.headers),json.load(r)
  except urllib.error.HTTPError as e:return e.code,dict(e.headers),json.load(e)
 def test_schemas_compile_and_examples_validate(self):
  for path in (ROOT/'schemas').glob('*.json'):
   schema=json.loads(path.read_text(encoding='utf-8'));jsonschema.Draft202012Validator.check_schema(schema)
  for example,schema in [('dataset-example','dataset-manifest'),('agent-example','agent-manifest'),('job-request-example','job-request'),('workflow-example','workflow-plan'),('update-ticket-example','update-ticket')]:
   jsonschema.validate(read_json(f'examples/{example}.json'),read_json(f'schemas/{schema}.schema.json'), format_checker=jsonschema.FormatChecker())
 def test_openapi_is_well_formed(self):
  api=yaml.safe_load((ROOT/'api/openapi.yaml').read_text(encoding='utf-8'))
  self.assertEqual(api['openapi'],'3.1.0');self.assertIn('/v1/agents/{agent_id}/jobs',api['paths'])
 def test_health_not_model_approval(self):
  status,_,data=self.request('/healthz',token='bad');self.assertEqual(status,200)
  self.assertEqual(data['scope'],'reference-contract-only')
  status,_,data=self.request('/v1/agents/lcluc-agent/readiness');self.assertEqual(status,200);self.assertFalse(data['data_ready']);self.assertFalse(data['model_approved'])
 def test_unauthorized_denied(self):
  status,_,_=self.request('/v1/agents',token='wrong');self.assertEqual(status,401)
 def test_blocked_model_cannot_execute(self):
  status,_,data=self.request('/v1/agents/lcluc-agent/jobs','POST',read_json('examples/job-request-example.json'),extra={'Idempotency-Key':'blocked-x'})
  self.assertEqual(status,409);self.assertEqual(data['error']['code'],'MODEL_NOT_READY')
 def test_mock_only_development_and_idempotency(self):
  p=read_json('examples/job-request-example.json');p['agent_id']='contract-test-agent';p['capability_id']='contract.echo'
  status,headers,r=self.request('/v1/agents/contract-test-agent/jobs','POST',p,extra={'Idempotency-Key':'duplicate-one'})
  self.assertEqual(status,202);self.assertEqual(r['status'],'SUCCEEDED');self.assertIn('Location',headers)
  jsonschema.validate(r,read_json('schemas/job-status.schema.json'),format_checker=jsonschema.FormatChecker())
  status2,_,r2=self.request('/v1/agents/contract-test-agent/jobs','POST',p,extra={'Idempotency-Key':'duplicate-one'})
  self.assertEqual(status2,202);self.assertEqual(r2['job_id'],r['job_id'])
  status3,_,result=self.request('/v1/jobs/'+r['job_id']+'/results')
  self.assertEqual(status3,200);self.assertEqual(result['status'],'MOCK_ONLY')
  jsonschema.validate(result,read_json('schemas/result-manifest.schema.json'),format_checker=jsonschema.FormatChecker())
 def test_no_mock_in_production(self):
  p=read_json('examples/job-request-example.json');p['agent_id']='contract-test-agent';p['capability_id']='contract.echo';p['execution_context']['environment']='production'
  status,_,data=self.request('/v1/agents/contract-test-agent/jobs','POST',p,extra={'Idempotency-Key':'prod-denied'})
  self.assertEqual(status,409);self.assertEqual(data['error']['code'],'MODEL_NOT_APPROVED')
 def test_workflow_must_be_acyclic(self):
  # Reference DAG gate, independent from external model execution.
  nodes=read_json('examples/workflow-example.json')['nodes']; ids={x['node_id'] for x in nodes}
  self.assertTrue(all(set(x['depends_on']).issubset(ids) for x in nodes))
  cycle=[{'node_id':'a','depends_on':['b']},{'node_id':'b','depends_on':['a']}]
  def has_cycle(items):
   graph={x['node_id']:x['depends_on'] for x in items};seen=set();visiting=set()
   def visit(n):
    if n in visiting:return True
    if n in seen:return False
    visiting.add(n)
    for m in graph[n]:
     if m in graph and visit(m):return True
    visiting.remove(n);seen.add(n);return False
   return any(visit(n) for n in graph)
  self.assertTrue(has_cycle(cycle))
if __name__=='__main__':unittest.main()
