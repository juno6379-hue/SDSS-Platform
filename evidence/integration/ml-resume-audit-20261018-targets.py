"""Build an explicit review queue from pinned local metadata; never collect."""
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[2]
source=ROOT/'data/first-group-training-esri-v1/annual-window-report.json'
raw=source.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='cdc374b2779dee749b57689fd90ef27e3525a48e59062343537327d0f4859a8f'
document=json.loads(raw)
splits={'south_sulawesi':'train','gorontalo':'train','southeast_sulawesi':'train','east_java':'train','banten':'val','west_java':'test'}
queue=[]
stats={split:{'rows_with_any_declared_bare':0,'eligible_rows_with_256_declared_bare':0,'ineligible_rows_with_256_declared_bare':0,'max_eligible_declared_bare':0} for split in ('train','val','test')}
for index,row in enumerate(document['scenes']):
    n=row.get('sample_class_coverage',{}).get('8',0)
    split=splits[row['province']]
    eligible=row.get('quality_status')=='quality_eligible'
    if n:stats[split]['rows_with_any_declared_bare']+=1
    if eligible:stats[split]['max_eligible_declared_bare']=max(stats[split]['max_eligible_declared_bare'],n)
    if n>=256:
        stats[split]['eligible_rows_with_256_declared_bare' if eligible else 'ineligible_rows_with_256_declared_bare']+=1
        queue.append({'source_row_index':index,'province':row['province'],'fixed_split':split,'year':int(row['year']),'patch_id':row.get('patch_id'),'spatial_location_id':row['spatial_location_id'],'bbox_declared':row['bbox'],'source_scene_id':row['scene_id'],'source_window':row.get('source_window'),'declared_source_taxonomy_code':'8','mapped_model_class':7,'declared_bare_pixels':n,'recorded_quality_status':row.get('quality_status'),'recorded_valid_fraction':row.get('valid_pixel_ratio'),'recorded_inside_fraction':row.get('province_inside_fraction'),'label_year':row.get('label_year'),'label_dataset_version':row.get('label_dataset_version'),'next_action':'Review a different same-year Sentinel acquisition for this existing low-quality area; verify against current processed windows before any selection','execution_authorized':False,'new_scene_identified':False,'bare_presence_in_future_scene_verified':False,'collector_job_ready':False})
queue.sort(key=lambda item:(item['fixed_split'],-item['declared_bare_pixels']))
result={'schema_version':1,'kind':'LOCAL_BARE_SCREENING_REVIEW_QUEUE','status':'PLANNED_NOT_EXECUTABLE','recorded_at':datetime.now(timezone.utc).isoformat(),'source_manifest_sha256':hashlib.sha256(raw).hexdigest(),'source_taxonomy':'ESRI_IO_v003','source_code_8_is_model_class_7':True,'scope':'STORED_PATCH_METADATA_SCREENING_NOT_NEW_RASTER_OR_FUTURE_CLASS_VALIDATION','by_fixed_split':stats,'local_low_quality_area_review_queue':queue,'validation_split_new_spatial_search_required':not any(item['fixed_split']=='val' for item in queue),'required_future_acceptance':{'same_year_image_and_esri_v003':True,'preserve_fixed_province_split':True,'actual_patch_size':256,'minimum_valid_fraction':.8,'minimum_inside_fraction':.95,'bare_pixels_per_contributing_patch':256,'minimum_bare_contributing_patches_per_split':5,'minimum_bare_fraction_per_split':.005,'source_identity_and_spatial_checks_required':True,'new_full_candidate_QA_required':True},'limitations':['Stored sample_class_coverage is a preliminary source-taxonomy summary; not the final QA histogram or an independent field label.','Three areas have >=256 declared bare pixels but all are quality-insufficient. Never change them to eligible or lower quality thresholds.','Validation has no existing patch with >=256 declared bare pixels. New same-year bare-bearing spatial candidates must be identified.','Existing lane-B geometric intentions do not certify bare class presence.','Collector currently has no CLI that executes this review queue or targets bare-specific source acquisition; an explicit isolated job-selection integration remains needed.','This queue does not authorize stale lock deletion, pending settlement/refund, download, training or source rewriting.'],'network_requests':0,'source_files_written':0,'training_executed':False,'collection_executed':False,'ready_for_training':False,'scientific_accuracy_validated':False}
target=ROOT/'evidence/integration/ml-resume-audit-20261018-bare-review-queue.json'
with target.open('x',encoding='utf-8') as stream:json.dump(result,stream,ensure_ascii=False,indent=2,allow_nan=False);stream.write('\n')
assert hashlib.sha256(source.read_bytes()).hexdigest()==result['source_manifest_sha256']
print(json.dumps({'queue':len(queue),'by_split':stats},ensure_ascii=True))
