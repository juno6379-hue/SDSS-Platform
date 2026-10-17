"""Freeze authenticated diagnostic API/UI evidence; never operate original data."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote

ROOT=Path(__file__).resolve().parents[2]
P='evidence/integration/'
def load(name):return json.loads((ROOT/P/name).read_text('utf-8-sig'))
def record(name):
    raw=(ROOT/name).read_bytes()
    return {'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
def unittest(name):
    raw=(ROOT/P/name).read_text('utf-8',errors='replace')
    m=re.search(r'Ran (\d+) tests in ([\d.]+)s',raw)
    assert m and re.search(r'^OK(?: \(skipped=\d+\))?\s*$',raw,re.M),name
    s=re.search(r'^OK \(skipped=(\d+)\)',raw,re.M)
    return {'run':int(m[1]),'passed':int(m[1])-(int(s[1]) if s else 0),'skipped':int(s[1]) if s else 0,'seconds':float(m[2]),'log':P+name}

focused=unittest('diagnostic-api-agent-20261018-focused-final3.log')
compat=unittest('diagnostic-api-compat-tests-final2-20261018.log')
backend=unittest('diagnostic-api-root-full-backend-final2-20261018.log')
front=(ROOT/P/'annual-input-diagnostics-ui-front-20261018.log').read_text('utf-8',errors='replace')
assert re.search(r'# pass 271\b',front) and re.search(r'# fail 0\b',front)
build=(ROOT/P/'annual-input-diagnostics-ui-build-final2-20261018.log').read_text('utf-8',errors='replace')
assert '112 modules transformed' in build and '13.48s' in build
integrity=load('diagnostic-api-live-integrity-final-20261018.json')
assert not integrity['protected_changes'] and not integrity['existing_source_changes'] and not integrity['previous_evidence_changes']
assert {r['path'] for r in integrity['expected_changed_existing_sources']}=={'backend/app/main.py','frontend/src/ModelReview.tsx','tests/test_model_registration_provenance_api.py','tests/test_model_version_registration_api.py','tests/test_workflow_job_model_record_handoff_api.py'}
inventory=load('diagnostic-api-operating-inventory-20261018.json')
assert inventory['dataset_versions_count']==0 and inventory['operating_writes']==0
browser=load('diagnostic-api-browser-20261018.json')
assert browser['passed'] and len(browser['checks'])==6 and all(c['passed'] for c in browser['checks'])
http=load('diagnostic-api-live-http-20261018.json')
expected={'missing_token':401,'wrong_token':401,'policy_met':200,'policy_not_met':200,'invalid':422,'oversize':413}
assert all(http['checks'][k]['http_status']==v for k,v in expected.items())
processes=load('diagnostic-api-final-processes-20261018.json')
assert processes['automation_status']=='ACTIVE' and processes['automation_interval_minutes']==10
assert processes['collector_training_processes_observed']==0
cleanup=load('diagnostic-api-live-cleanup-20261018.json')
assert cleanup['process_alive_after'] is False and cleanup['port_listening_after'] is False
assert cleanup['temp_exists_after'] is False and cleanup['operating_data_writes']==0
assert cleanup['further_deletion_attempts_after_stop_message']==0

documents=list((ROOT/'docs/understanding').rglob('*.md'))
errors=[];links=references=0
for path in documents+[ROOT/'docs/implementation/137_annual_diagnostics_api_ui.md']:
    text=path.read_text('utf-8')
    if 'understanding' in path.parts and path.name!='GATE_TEMPLATE.md':
        for field in ('updated_at','source_commit','evidence_paths','confidence','status'):
            if not re.search(r'^\|\s*'+field+r'\s*\|',text,re.M):errors.append(path.name+': missing '+field)
        for line in text.splitlines():
            if re.match(r'^\|\s*evidence_paths\s*\|',line):
                for name in re.findall(r'`([^`]+)`',line):
                    references+=1
                    if not (ROOT/name).exists():errors.append('missing evidence '+name)
    for value in re.findall(r'\]\(([^)]+)\)',text):
        name=unquote(value.strip('<>').split('#',1)[0])
        if not name or re.match(r'^[a-zA-Z][\w+.-]*:',name):continue
        links+=1
        if not (path.parent/name).exists():errors.append(path.name+': missing link '+name)
faq=len(re.findall(r'^## \d+\.',(ROOT/'docs/understanding/presentations/FAQ.md').read_text('utf-8'),re.M))
assert faq==10 and not errors,errors
assert (ROOT/'docs/understanding/GATE_TEMPLATE.md').read_bytes()==(ROOT/'UI/GreenBlue_Understanding_Agent/docs/understanding/GATE_TEMPLATE.md').read_bytes()
audit={'checked_at':datetime.now().astimezone().isoformat(),'understanding_markdown':len(documents),'implementation_markdown':1,'local_links':links,'metadata_evidence_references':references,'numbered_faq':faq,'errors':errors,'reference_templates_byte_identical':True}
paths=['backend/app/annual_diagnostics_api.py','backend/app/main.py','tests/test_annual_diagnostics_api.py','frontend/src/AnnualInputDiagnostics.tsx','frontend/src/annualInputDiagnosticsAdapter.ts','frontend/src/annualInputDiagnosticsClient.ts','frontend/src/annual-input-diagnostics.css','frontend/src/annualInputDiagnosticsAdapter.test.mjs','frontend/src/ModelReview.tsx','tests/test_model_registration_provenance_api.py','tests/test_model_version_registration_api.py','tests/test_workflow_job_model_record_handoff_api.py']
for name,digest in {
    'backend/app/annual_diagnostics_api.py':'c110dd9c70bfafcb2a7dfdf2ee0f1c0f3b1f30e1b2f7f0c4651eb300cda6dfd8',
    'backend/app/main.py':'d5efc3acb269ab1397ff0e32b829f7ce8820799bcb16ed3e64d59121ccc27467',
    'tests/test_annual_diagnostics_api.py':'25204c7c4db8357e2653979f828e3754fbc5f53e00788de5dc2ac95c28ba5eae',
    'frontend/src/ModelReview.tsx':'c845118bed7dc06b5f84fedc8960c18d16015677bfeb968f88c304decc0e94fd',
    'tests/test_model_registration_provenance_api.py':'54128292af789549c334899800bca249049a44cd6f5c04d0b86dd25fcfa2c81e',
    'tests/test_model_version_registration_api.py':'c115202858f631bcb358f8fb6c57e984f1667e9ca8733419a96d7085f90a0f73',
    'tests/test_workflow_job_model_record_handoff_api.py':'1abdf3a475e5e48559b2f1039bf06e8995c08edf00cc4162cb9f92ccf4f91ed5',
}.items():assert record(name)['sha256']==digest,name
closeout={'recorded_at':audit['checked_at'],'status':'137_AUTHENTICATED_READ_ONLY_ANNUAL_DIAGNOSTIC_API_AND_MANUAL_UI',
    'confidence':'TESTED_SYNTHETIC_TEMP_ACTUAL_HTTP_AND_UI_OPERATING_DIAGNOSTIC_BLOCKED',
    'focused':focused,'compatibility_tests':compat,'full_backend':backend,'initial_full_backend':{'log':P+'diagnostic-api-root-full-backend-20261018.log','run':1358,'passed':1354,'legacy_ast_guard_failures':3,'skipped':1,'seconds':490.787,'preserved':True},'frontend':{'passed':271,'failed':0,'seconds':25.6785829,'focused10_included':True,'build_modules':112,'build_seconds':13.48},
    'overlapping_test_bundles_are_not_additive':True,'source_records':{n:record(n) for n in paths},
    'documentation_validation':audit,'integrity':integrity,'operating_inventory':inventory,'live_processes':processes,
    'actual_http_evidence':P+'diagnostic-api-live-http-20261018.json','browser':browser,'temporary_server_cleanup':cleanup,
    'cross_review_blocking_findings':0,'existing_global_401_detail_and_absent_cache_headers_preserved':True,
    'whitespace_truthy_global_token_may_401_before_strict_router_configuration_503':True,
    'new_router_own_responses_no_store_nosniff':True,'new_api_strict_authentication_required':True,
    'request_response_16kib_limits':True,'worker_limit_one_per_process_not_global':True,
    'client_abort_or_route_change_does_not_guarantee_server_read_cancellation':True,
    'manual_policy_and_refs_no_default_no_automatic_post_or_retry':True,
    'operating_model_missing_pins_disables_query':True,
    'quality_report_verified':False,'quality_mask_verified':False,'mask_semantics_verified':False,
    'registry_aoi_verified':False,'source_authority_verified':False,'scientific_accuracy_validated':False,
    'execution_authorized':False,'state_dict_verified':False,'workflow_supported':False,
    'sequential_file_registry_observations_not_atomic':True,'store_predecode_and_native_parser_resources_not_os_isolated':True,
    'operating_collection_training_registry_approval_deployment_workflow_dispatch':0,
    'original_published136_process_evidence_restored_from_git_new137_observation_preserved':True,
    'understanding_updated':True,'automation_status':'ACTIVE','automation_interval_minutes':10,
    'next_internal_candidate':'138_REVIEW_LCLUC_PRODUCER_QUALITY_MASK_AND_PINNED_INPUT_CONTRACT_GAPS'}
snapshot_path=ROOT/'docs/understanding/EVIDENCE_SNAPSHOT.json'
snapshot=json.loads(snapshot_path.read_text('utf-8'))
subprocess.run(['python','.git/codex_prepare_publish.py'],cwd=ROOT,check=True)
publish={n for n in (ROOT/'.git/codex-publish-paths').read_bytes().decode().split('\0') if n}
tracked={n for n in subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0') if n}
changed={n for n in subprocess.check_output(['git','diff','--name-only','-z'],cwd=ROOT).decode().split('\0') if n}
names=set(snapshot['files'])|(publish-tracked)|changed
target=ROOT/P/'diagnostic-api-closeout-20261018.json';names.add(target.relative_to(ROOT).as_posix())
names.discard('docs/understanding/EVIDENCE_SNAPSHOT.json')
closeout['snapshot_files']=len(names)
target.write_text(json.dumps(closeout,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
snapshot['updated_at']=audit['checked_at'];snapshot['source_commit']='bec226ec460ca2497e092e34c21c64bd9ab0da99'
snapshot['source_commit_reason']='Published136 baseline plus137 working files pinned by raw SHA; subsequent Git publication must preserve these bytes.'
snapshot['reported_status']['full_regression_rerun_in_latest_unit']=True
snapshot['reported_status']['latest_authenticated_annual_diagnostic_api_ui']=closeout
snapshot['reported_status']['operating_dataset_versions_count']=0
snapshot['documentation_validation']=audit;snapshot['files']={n:record(n) for n in sorted(names)}
snapshot_path.write_text(json.dumps(snapshot,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
assert all(record(n)==v for n,v in snapshot['files'].items())
print(json.dumps({'audit':audit,'snapshot_files':len(names),'snapshot_mismatches':[]},ensure_ascii=True))
