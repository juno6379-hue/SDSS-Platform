"""Reassess fixed candidate only; do not conflate concurrently changing collector state."""
import os
for key,value in {'PROJ_NETWORK':'OFF','GDAL_PAM_ENABLED':'NO','GDAL_DISABLE_READDIR_ON_OPEN':'EMPTY_DIR','GDAL_VRT_ENABLE_PYTHON':'NO'}.items():os.environ[key]=value
import hashlib,json,sys,time
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from backend.app.ml.readiness import assess
PREFIX=ROOT/'evidence/integration/ml-resume-audit-20261018-candidate-only'
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(suffix,value):
    with Path(str(PREFIX)+suffix).open('x',encoding='utf-8') as stream:json.dump(value,stream,ensure_ascii=False,indent=2,allow_nan=False);stream.write('\n')
candidate=ROOT/'data/first-group-candidate-qa-stage-20261017/candidate.json'
policy=ROOT/'data/first-group/experiment-esri-v003-2020-2025.json'
oldqa=ROOT/'data/first-group-candidate-readiness-qa-20261017/readiness.json'
backup=ROOT/'data/collection-continuation-backup-20261018/annual-window-report.json'
pins={candidate:'2ff7be093db3930d99f10cdc7687809222ef7f525ec6e9cf6248ec144725d158',policy:'01991d69bc26487d4ef890de72689da092806bc58cc80ca5f6d6026cf3c79ed7',oldqa:'847343e1aa4ab9b67fd3bba36a2a9f91d716c2fd411af244e55bbfe1a8414019',backup:'cdc374b2779dee749b57689fd90ef27e3525a48e59062343537327d0f4859a8f'}
assert all(digest(p)==sha for p,sha in pins.items())
active=[ROOT/'data/first-group-training-esri-v1/annual-window-report.json',ROOT/'data/first-group-training-budget/global-ledger.json']
active_before={str(p.relative_to(ROOT)):digest(p) for p in active}
write('-preflight.json',{'at':datetime.now(timezone.utc).isoformat(),'candidate_inputs_and_historical_provenance_pins':{str(p.relative_to(ROOT)):sha for p,sha in pins.items()},'active_collector_observation_only':active_before,'prior_run_failed_stability':'ml-resume-audit-20261018-failed-stability.json','scope':'FIXED_HISTORICAL_CANDIDATE_NOT_CURRENT_COLLECTOR_AGGREGATE_QA'})
start=time.monotonic();print('Fixed historical candidate raster reassessment started',flush=True)
report=assess([candidate],ROOT/'data',json.loads(policy.read_text(encoding='utf-8')),connectivity_diagnostics=True)
seconds=round(time.monotonic()-start,3)
# Preserve returned observation before any final stability assessment. Never call it completed on failed pins.
write('-returned-readiness-observation.json',report)
stable={str(p.relative_to(ROOT)):digest(p)==sha for p,sha in pins.items()}
previous=json.loads(oldqa.read_text(encoding='utf-8'))
keys=['status','ready_for_training','scientific_accuracy_validated','blockers','patch_counts_by_split','class_counts_by_split','class_patch_counts_by_split','reference_balance_by_split','policy','coverage','province_unique_locations','province_patch_counts','verified_files']
same={k:previous[k]==report[k] for k in keys}
summary={'at':datetime.now(timezone.utc).isoformat(),'status':'FIXED_CANDIDATE_QA_REOBSERVED' if all(stable.values()) else 'FAILED_FIXED_INPUT_STABILITY','scope':'HISTORICAL_FIXED_CANDIDATE_ONLY_NOT_CURRENT_COLLECTOR_AGGREGATE_QA','seconds':seconds,'fixed_pins_stable':stable,'same_as_stored_candidate_QA':same,'observed_status':report['status'],'ready_for_training':report['ready_for_training'],'eligible':report['patch_counts_by_split'],'blockers':report['blockers'],'verified_file_records':len(report['verified_files']),'active_collector_before':active_before,'active_collector_after':{str(p.relative_to(ROOT)):digest(p) for p in active},'active_collector_stability_required_for_this_candidate_run':False,'original_attempt_stability_failure_preserved':True,'network_requests':0,'training_executed':False,'collection_executed_by_this_worker':False,'source_files_written_by_this_worker':0,'scientific_accuracy_validated':False}
write('-summary.json',summary)
assert all(stable.values()),'Fixed candidate pins changed'
print(json.dumps({'seconds':seconds,'status':summary['status'],'same_stored_fields':all(same.values()),'eligible':summary['eligible'],'blockers':len(summary['blockers'])}),flush=True)
