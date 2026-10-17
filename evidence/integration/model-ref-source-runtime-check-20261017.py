"""Fresh-source synthetic declaration check without operating app or Store calls."""
from pathlib import Path
import copy,datetime,importlib.util,json
from app.gmais_api import _validate_job
from test_schema_formats import job_fixture
r=Path.cwd();p=r/'evidence/integration/model-ref-original-gmais-20261017.py';spec=importlib.util.spec_from_file_location('app._model_ref_source_original',p);old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
rows=[]
cases=[('fixed','v1',True),('padded_fixed',' v1 ',True),('boundary256','v'*256,True),('floating_latest','latest',False),('floating_padded_current',' CuRrEnT ',False),('whitespace',' ',False),('control','v\n1',False),('surrogate','v\ud800',False),('length257','v'*257,False)]
for label,version,valid in cases:
 j=job_fixture();j['model_ref']={'id':'synthetic-model','version':version,'sha256':'b'*64};before=copy.deepcopy(j)
 _,old_issue=old._validate_job(j,'lcluc-agent','source-only-model-ref');_,new_issue=_validate_job(j,'lcluc-agent','source-only-model-ref')
 assert (new_issue is None)==valid,(label,new_issue);assert j==before
 rows.append({'label':label,'old_common_validator_accepted':old_issue is None,'new_common_validator_accepted':new_issue is None,'expected_valid':valid})
assert all(row['old_common_validator_accepted']for row in rows)
o={'recorded_at':datetime.datetime.now().astimezone().isoformat(),'status':'TESTED_SYNTHETIC','scope':'fresh source process common _validate_job vs pinned pre96 module; no full operating route/Store/app.main or submission','cases':rows,'source_job_immutable':True,'store_calls':0,'operating_job_posts':0,'registry_or_checkpoint_reads':0,'actual_model_version_binding':'BLOCKED_NO_AUTHORITATIVE_MODEL_VERSION_FIELD','warning':'Old common validator acceptance is not evidence that every old full route would successfully store or run such a request; no operating route exercised','live_server_common_submit_behavior':'UNVERIFIED'}
(r/'evidence/integration/model-ref-source-runtime-20261017.json').write_text(json.dumps(o,ensure_ascii=True,indent=2),'utf-8');print(json.dumps({'cases':len(rows),'status':'PASS','new_invalid_rejected':sum(not a['new_common_validator_accepted']for a in rows)}))
