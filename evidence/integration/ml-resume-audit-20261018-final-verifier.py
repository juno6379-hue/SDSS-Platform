"""Independent post-run hash comparison of every frozen-candidate verified record."""
import hashlib,json,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PREFIX=ROOT/'evidence/integration/ml-resume-audit-20261018'
report_path=Path(str(PREFIX)+'-candidate-only-returned-readiness-observation.json')
summary=json.loads(Path(str(PREFIX)+'-candidate-only-summary.json').read_text(encoding='utf-8'))
assert summary['status']=='FIXED_CANDIDATE_QA_REOBSERVED'
report=json.loads(report_path.read_text(encoding='utf-8'))
old=ROOT/'data/first-group/readiness-resume-20261017.json'
assert hashlib.sha256(old.read_bytes()).hexdigest()=='6e59c3aee00f53609237b889bfc304a811d298b464b6d6ae2c8e563cc29a34db'
start=time.monotonic();mismatches=[]
for record in report['verified_files']:
    path=(ROOT/'data'/record['path']).resolve()
    assert path.is_relative_to((ROOT/'data').resolve())
    with path.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
    if digest!=record['sha256']:mismatches.append(record['path'])
cells=json.loads(ROOT.joinpath('data/first-group-candidate-qa-stage-20261017/staging-receipt.json').read_text(encoding='utf-8'))['projected_after']['eligible_by_province_year']
deficits=[{'province':key.split('/')[0],'year':int(key.split('/')[1]),'eligible':value,'shortfall_to_planning_floor_28':28-value} for key,value in cells.items() if value<28]
result={'status':'FINAL_FROZEN_CANDIDATE_FILES_MATCH' if not mismatches else 'FAILED_POST_QA_RASTER_DIGEST','actual_final_file_rehash_count':len(report['verified_files']),'post_QA_rehash_seconds':round(time.monotonic()-start,3),'mismatch_paths':mismatches,'report_sha256':hashlib.sha256(report_path.read_bytes()).hexdigest(),'old_readiness_sha256':hashlib.sha256(old.read_bytes()).hexdigest(),'fixed_historical_candidate_only':True,'current_collector_aggregate_reassessed':False,'eligible':report['patch_counts_by_split'],'blocker_count':len(report['blockers']),'all_compared_fields_equal_stored_QA':all(summary['same_as_stored_candidate_QA'].values()),'planning_floor_deficits':deficits,'planning_floor_shortfall_total':sum(row['shortfall_to_planning_floor_28'] for row in deficits),'training_executed':False,'network_requests':0,'source_files_written':0,'scientific_accuracy_validated':False}
output=Path(str(PREFIX)+'-final-verification.json')
with output.open('x',encoding='utf-8') as stream:json.dump(result,stream,ensure_ascii=False,indent=2,allow_nan=False);stream.write('\n')
assert not mismatches
print(json.dumps({key:result[key] for key in ['status','actual_final_file_rehash_count','post_QA_rehash_seconds','eligible','blocker_count','planning_floor_shortfall_total']},ensure_ascii=True))
