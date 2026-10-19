"""Root-owned bounded235 approval after runtime, project tests and real UI verification."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
R=Path(__file__).resolve().parents[2];E=R/'evidence/integration';D=R/'data'
def read(p):return json.loads(p.read_text('utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
main=read(E/'profile242-shared-application-root-20261018.json')
assert main['status']=='TEST_SOURCES_APPLIED_AND_PROJECT_REGRESSION_VERIFIED'
assert main['runtime18_unchanged'] and main['operating_pins_unchanged']
log=(E/'profile242-main-regression-root-20261018.log').read_text('utf-8')
assert 'Ran 93 tests' in log and log.rstrip().endswith('OK')
runtime=read(E/'profile243-runtime-approval-root-20261018.json')['runtime_files']
assert all(sha(R/x['path'])==x['final237']['sha256'] for x in runtime)
assert read(E/'profile243-api-status-checks-root-20261018.json')['status']=='REAL_LOCAL_API_PROFILE_STATUS_VERIFIED'
ui=read(E/'service243-profile-final-ui-20261018.json')
assert ui['status']=='VERIFIED_REAL_CURRENT243_BROWSER_RENDER'
assert ui['browser']['horizontal_overflow'] is False and ui['browser']['console_warn_error_logs']==[]
old=read(E/'deficit223-reviewed-code-pins-root-20261018.json')['source_pins']
allowed={x['path'] for x in runtime}|{'scripts/collect_targeted_bare.py'}
for name,pin in old.items():assert sha(R/name)==pin or name in allowed,name
assert sha(R/'scripts/collect_targeted_bare.py')=='9ff831366a8a9e101a90eacbdcae57858d13aa1d0b1a3b9c6f2bec5b9e6d18d8'
assert sha(R/'backend/app/data/targeted_inventory_profile.py')=='dc947980dc4fe69930ebd1bbd66a2b0e32f99432749754c55b27327ed78d8c6d'
text=(E/'deficit223-supervisor-root-20261018.py').read_text('utf-8')
text=text.replace('223','235').replace('centers222-fresh-20261018','centers235-fresh-20261018')
mapping={'priority207-publication-root-20261018':'priority227-publication-root-20261018',
 '80eef2d274942c7a7f9bf8ee2483af070a729060d84ceb1a19baacb52ae4976a':'9c24eec337a17f95855d190918c9999c25aeb1925a7642b1ade26afa4e20d987',
 '9e4c6a43fdcf49b00d266bae3f14c4b843465a1b339059c52823b24d6bdf74d0':'87e6f5f157d940e00c624f46821d30329135ef9182a0acb1db248bfb59a712da',
 'f85925ebf188675060598352ffaa658d82b6dc6f6a1fb4b9025ec01433c92efc':'9c24eec337a17f95855d190918c9999c25aeb1925a7642b1ade26afa4e20d987',
 '60ae5217d3c4b4cc59a5806ddda60010e3583122a4a9b64cc95efd297ec5ebf0':'61161c35eabb593afb5f096c256791871d297b723f82ffc2ac2449b3bd8266e7'}
for a,b in mapping.items():assert a in text;text=text.replace(a,b)
gate="""assert read(E/'profile242-shared-application-root-20261018.json')['status']=='TEST_SOURCES_APPLIED_AND_PROJECT_REGRESSION_VERIFIED'
assert read(E/'profile243-api-status-checks-root-20261018.json')['status']=='REAL_LOCAL_API_PROFILE_STATUS_VERIFIED'
assert read(E/'service243-profile-final-ui-20261018.json')['status']=='VERIFIED_REAL_CURRENT243_BROWSER_RENDER'
"""
anchor="assert not (E/'deficit235-launch-root-20261018.json').exists()"
assert anchor in text;text=text.replace(anchor,gate+anchor)
text=text.replace('Bounded one-SE execution from fresh222 proposal after audited219 zero-patch run.',
 'Bounded235 SE2024 execution after profile243 runtime and242 main-layout tests; fresh200 preflight required.')
supervisor=E/'deficit235-supervisor-root-20261018.py'
with supervisor.open('x',encoding='utf-8') as stream:stream.write(text)
source_names=set(old)|{x['path'] for x in runtime}|{'backend/app/data/targeted_inventory_profile.py',supervisor.relative_to(R).as_posix()}
approval={'status':'REVIEWED_TESTED_BOUNDED_EXECUTION_APPROVED','at_utc':datetime.now(timezone.utc).isoformat(),
 'source_pins':{n:sha(R/n) for n in sorted(source_names)},'maximum_batches':1,'maximum_new_physical_patches':16,
 'requested_order':['southeast_sulawesi:2024'],'new_budget_added':False,'training_approved':False,
 'request_sha256':'fc824e2465d1f4128f8f473576c0e9087b2950ab3c7a5da4cee4a8f18e8af704',
 'project_tests':{'tests':93,'log_sha256':sha(E/'profile242-main-regression-root-20261018.log')},
 'runtime_application_sha256':sha(E/'profile243-runtime-application-root-20261018.json'),
 'actual_status_sha256':sha(E/'profile243-api-status-checks-root-20261018.json'),
 'actual_browser_sha256':sha(E/'service243-profile-final-ui-20261018.json'),
 'cached234_precheck_is_not_fresh_inventory':True,'fresh200_under_lock_required':True,
 'oldpending_reserved_bytes':136314880,'existing_budget_maximum_bytes':4294967296,
 'source_profile_config_sha256':sha(D/'first-group-training-priority/source-profile237-root-20261018.json')}
with (E/'deficit235-reviewed-code-pins-root-20261018.json').open('x',encoding='utf-8') as stream:json.dump(approval,stream,ensure_ascii=False,indent=2)
print(json.dumps({'status':approval['status'],'source_pins':len(source_names),'supervisor_sha256':sha(supervisor),
 'maximum_batches':1,'maximum_physical':16,'collector_started':False}),flush=True)
