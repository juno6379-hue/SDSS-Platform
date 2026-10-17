"""Fresh-process membership observation; does not construct Store or operating app."""
from pathlib import Path
import datetime,hashlib,json
from app.agent_capability_contract import agent_capability_issue
from app.gmais_api import _agent_manifests
r=Path.cwd();manifests=_agent_manifests();before=json.dumps(manifests,ensure_ascii=False,sort_keys=True);cases=[]
for agent in manifests:
 for value,expected in [(agent['capabilities'][0]['capability_id'],None),('unregistered-capability','INVALID_REQUEST')]:
  actual=agent_capability_issue(agent,value);assert actual==expected
  cases.append({'agent_id':agent['agent_id'],'capability_id':value,'issue':actual,'manifest_readiness_unchanged':agent['readiness']})
assert agent_capability_issue(None,'anything')=='AGENT_NOT_IMPLEMENTED';assert json.dumps(manifests,ensure_ascii=False,sort_keys=True)==before
out={'recorded_at':datetime.datetime.now().astimezone().isoformat(),'status':'TESTED_SYNTHETIC','scope':'fresh process actual local configured manifests; no app.main import, Store construction or HTTP submission','registered_agents':len(manifests),'cases':cases,'absent_agent_issue':'AGENT_NOT_IMPLEMENTED','source_manifests_unchanged':True,'live_operating_job_posts':0,'store_calls':0,'approval_or_execution_granted':False,'runtime_server_code_application':'UNVERIFIED; source-process observation only'}
(r/'evidence/integration/agent-capability-source-runtime-20261017.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),'utf-8');print(json.dumps(out,ensure_ascii=False))
