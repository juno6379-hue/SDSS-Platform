"""Source-runtime synthetic validation without importing app.main or any Store."""
from pathlib import Path
import datetime,hashlib,json
from jsonschema import FormatChecker
from app.gmais_api import _job_request_validator,_validate_job
from test_schema_formats import VALID,INVALID,job_fixture
r=Path.cwd();v=_job_request_validator();before=dict(FormatChecker.checkers);rows=[]
for valid,values in [(True,VALID),(False,INVALID)]:
 for value in values:
  job=job_fixture();job['time_range']={'start':value};accepted,issue=_validate_job(job,'lcluc-agent','isolated-direct-validator-only')
  assert (issue is None)==valid,(value,issue)
  rows.append({'value':value,'expected_valid':valid,'accepted':issue is None,'schema_errors':len(list(v.iter_errors(job)))})
assert dict(FormatChecker.checkers)==before
out={'recorded_at':datetime.datetime.now().astimezone().isoformat(),'status':'TESTED_SYNTHETIC','scope':'fresh Python process, actual vendored schema and direct common _validate_job; no operating app import, Store or HTTP submission','optional_default_date_time_registered':'date-time' in FormatChecker().checkers,'shared_checker_date_time_registered':'date-time' in v.format_checker.checkers,'cases':rows,'operating_job_posts':0,'store_calls':0,'class_registry_unchanged':True,'live_non_reload_process_code_application':'UNVERIFIED','limits':'supported zoned subset only; leap seconds/year0000 rejected, no interval ordering or science policy'}
(r/'evidence/integration/common-datetime-source-runtime-20261017.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),'utf-8');print(json.dumps(out,ensure_ascii=False))
