"""Pin current aggregate once; reuse existing candidate/QA functions, no execution."""
import os
for key,value in {'PROJ_NETWORK':'OFF','GDAL_PAM_ENABLED':'NO','GDAL_DISABLE_READDIR_ON_OPEN':'EMPTY_DIR','GDAL_VRT_ENABLE_PYTHON':'NO'}.items():os.environ[key]=value
import hashlib,json,sys,time
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'.runtime'),str(ROOT/'backend')]
from backend.app.ml.readiness import assess
from backend.app.ml.split_planning import plan_split_repair,write_plan
from backend.app.ml.candidate_materialization import materialize_split_candidate
from backend.app.ml.candidate_staging import stage_split_candidate
from backend.app.ml.candidate_readiness_qa import assess_staged_candidate
PREFIX=ROOT/'evidence/integration/priority-ml-next-20261018'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):
    with p.open('x',encoding='utf8') as f:json.dump(v,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
def event(text):print(datetime.now(timezone.utc).isoformat()+' '+text,flush=True)
data=ROOT/'data';evidence=ROOT/'evidence'
active=data/'first-group-training-esri-v1/annual-window-report.json'
frozen_dir=data/'priority-ml-next-snapshot-20261018';frozen_dir.mkdir(exist_ok=False)
source=frozen_dir/'annual-window-report.json'
before=sha(active);payload=active.read_bytes();assert hashlib.sha256(payload).hexdigest()==before
assert sha(active)==before,'Active aggregate changed during snapshot; preserve partial and stop'
with source.open('xb') as stream:stream.write(payload)
assert sha(source)==before
policy=data/'first-group/experiment-esri-v003-2020-2025.json'
old=data/'first-group-candidate-qa-stage-20261017/candidate.json'
pins={source:before,policy:sha(policy),old:sha(old)}
assert pins[policy]=='01991d69bc26487d4ef890de72689da092806bc58cc80ca5f6d6026cf3c79ed7'
assert pins[old]=='2ff7be093db3930d99f10cdc7687809222ef7f525ec6e9cf6248ec144725d158'
document=json.loads(payload);rows=document['scenes'];policy_doc=json.loads(policy.read_text(encoding='utf8'))
write(Path(str(PREFIX)+'-preflight.json'),{'at':datetime.now(timezone.utc).isoformat(),'scope':'FROZEN_NEXT_COHORT_SNAPSHOT_NOT_FUTURE_COLLECTOR_AGGREGATE','raw_source_snapshot_sha256':before,'source_bytes':len(payload),'source_row_count':len(rows),'fixed_inputs':{str(p.relative_to(ROOT)):v for p,v in pins.items()},'artifact_paths_absolute':all(Path(r[k]).is_absolute() for r in rows for k in ['image_path','label_path','quality_mask_path']),'collection_executed':False,'training_executed':False,'network_requests':0})
event('Frozen source actual raster QA started')
started=time.monotonic();report=assess([source],data,policy_doc,connectivity_diagnostics=True)
source_seconds=round(time.monotonic()-started,3);readiness=frozen_dir/'readiness.json';write(readiness,report)
assert all(sha(p)==v for p,v in pins.items())
event('Source QA complete '+json.dumps({'seconds':source_seconds,'counts':report['patch_counts_by_split'],'blockers':len(report['blockers'])}))
saved_plan=Path(str(PREFIX)+'-split-plan.json')
plan=plan_split_repair(source,before,province_splits=policy_doc['province_splits'],readiness_path=readiness,readiness_sha256=sha(readiness),data_root=data)
write_plan(plan,saved_plan)
paths={'source':source,'readiness':readiness,'saved_plan':saved_plan};input_pins={k:sha(p) for k,p in paths.items()}
package=Path(str(PREFIX)+'-candidate-package')
receipt=materialize_split_candidate(data,paths,input_pins,package,evidence_root=evidence)
stage_dir=data/'priority-ml-next-stage-20261018'
stage=stage_split_candidate(data,package,sha(package/'receipt.json'),input_pins,stage_dir,evidence_root=evidence)
event('Candidate metadata staged '+json.dumps({'excluded':len(plan['excluded_row_indexes']),'counts':plan['projected_after']}))
qa_paths={'candidate':stage_dir/'candidate.json','staging_receipt':stage_dir/'staging-receipt.json','policy':policy,'old_readiness':readiness}
# Fixed stage receipt basename is selected by existing staging contract.
if not qa_paths['staging_receipt'].exists():
    raise AssertionError('Expected staging-receipt.json missing; do not guess alternate inputs')
qa_pins={k:sha(p) for k,p in qa_paths.items()}
started=time.monotonic();qa_dir=data/'priority-ml-next-readiness-20261018'
event('Staged candidate actual raster QA started')
qa_receipt=assess_staged_candidate(data,qa_paths,qa_pins,qa_dir)
candidate_seconds=round(time.monotonic()-started,3)
candidate_report=json.loads((qa_dir/'readiness.json').read_text(encoding='utf8'))
stable={str(p.relative_to(ROOT)):sha(p)==v for p,v in pins.items()}
assert all(stable.values())
outputs=[readiness,saved_plan,package/'plan.json',package/'candidate.json',package/'receipt.json',stage_dir/'candidate.json',stage_dir/'staging-receipt.json',qa_dir/'readiness.json',qa_dir/'qa-receipt.json']
summary={'at':datetime.now(timezone.utc).isoformat(),'status':'FROZEN_SNAPSHOT_CANDIDATE_QA_COMPLETED','scope':'FIXED_SNAPSHOT_NOT_LATER_COLLECTOR_STATE','raw_source_snapshot_sha256':before,'source_row_count':len(rows),'source_eligible':report['patch_counts_by_split'],'source_blockers':report['blockers'],'candidate_row_count':receipt['candidate_row_count'],'excluded_source_rows':len(plan['excluded_row_indexes']),'excluded_row_indexes':plan['excluded_row_indexes'],'conflicts':plan['conflicts'],'remaining_source_identity_conflicts':plan['remaining_source_identity_conflicts'],'candidate_eligible':candidate_report['patch_counts_by_split'],'candidate_blockers':candidate_report['blockers'],'candidate_bare_pixels':{s:v[7] for s,v in candidate_report['class_counts_by_split'].items()},'candidate_bare_contributing_patches':{s:v[7] for s,v in candidate_report['class_patch_counts_by_split'].items()},'ready_for_training':candidate_report['ready_for_training'],'scientific_accuracy_validated':False,'training_executed':False,'collection_executed_by_this_worker':False,'network_requests':0,'registry_called':False,'frozen_inputs_stable':stable,'active_aggregate_sha256_after_observation_only':sha(active),'source_qa_seconds':source_seconds,'candidate_qa_seconds':candidate_seconds,'verified_file_records':len(candidate_report['verified_files']),'outputs':{str(p.relative_to(ROOT)):{'sha256':sha(p),'bytes':p.stat().st_size} for p in outputs}}
write(Path(str(PREFIX)+'-summary.json'),summary)
event('Completed '+json.dumps({'counts':summary['candidate_eligible'],'blockers':len(summary['candidate_blockers']),'ready':summary['ready_for_training']}))
