from .manifest_resource_profile import active,cap as profile_cap,policy as resource_policy,charge as profile_charge,structure as profile_structure,entry as profile_entry,stamp as profile_stamp,receipt as profile_receipt,DESCRIPTOR
"""고정 staging metadata와 동일 정책으로 기존 run을 QA-only 호출한다."""
import copy
from pathlib import Path
import re
from .candidate_staging import _sha,_uint
from .candidate_materialization import _dir_identity,POLICY
from .split_json_io import BoundedJSONIO,_local,_stamp
from .split_validation import _same
from .readiness import default_policy
from ..data.recovery_terminal import _confined
from ..data.readiness_connectivity_witness import FIXED_PROVINCE_SPLITS
from scripts.run_experiment import run

ROLES=('candidate','staging_receipt','policy','old_readiness')
CAPS={'candidate':64*1024**2,'staging_receipt':65536,'policy':1024**2,'old_readiness':16*1024**2}
STAGE_FALSE={'qa_performed','readiness_assess_called','registered','registry_called','executed','learning_ready','ready_for_training','scientific_accuracy_validated','source_authenticity_verified','exact_row_binding_verified','spatial_overlap_rechecked','exact_class_counts_recomputed','training_split_leakage_resolved','source_rows_modified_or_reassigned','execution_authorized','settlement_authorized','automatic_resume_allowed'}
STAGE_FIELDS={'schema_version','kind','status','next_step','qa_status','package_reference','input_pins','verified_package_outputs','staged_candidate','derived_manifest_version','source_row_count','candidate_row_count','projected_after','metadata_integrity_verified','original_candidate_bytes_preserved','proposed_refund_bytes','exactly_once_applied','completion_contract'}|STAGE_FALSE


def _need(value,message):
    if not value:raise ValueError(message)


def _number(value):
    import math
    if type(value) not in (int,float):return False
    try:return math.isfinite(value)
    except OverflowError:return False


def _context(role,cap):
    policy=resource_policy(POLICY);policy['input_caps'][role]=cap;policy['output_caps']['plan']=65536
    return BoundedJSONIO(policy)


def _policy(caller,old):
    _need(type(caller) is dict and type(old) is dict and type(old.get('policy')) is dict,'Policy/readiness objects required')
    base=default_policy();effective={**base,**caller}
    _need(set(caller)<=set(base)|{'label_source'},'Unknown policy keys prohibited')
    if 'label_source' in effective:_need(type(effective['label_source']) is str and effective['label_source'] in {'esri_io','worldcover','dynamic_world','classes'} and type(old.get('input_signature')) is dict and old['input_signature'].get('label_source')==effective['label_source'],'Policy label source differs from old signature')
    _need(_same(effective,old['policy']),'Policy differs from old readiness')
    for key in ['required_provinces','required_years','band_names','required_classes','province_splits','patch_size','limited_period_experiment','scope_statement','class_weighting']:_need(_same(effective[key],base[key]),'Fixed scope/band/class/policy changed: '+key)
    for key,floor in {'min_patches':1000,'min_patches_per_train_province':50,'min_unique_train_locations':32,'min_class_pixels_per_split':256,'min_class_patches_per_split':5,'min_class_pixels_per_patch':256}.items():_need(type(effective[key]) is int and floor<=effective[key]<=9007199254740991,'Integer gate floor invalid: '+key)
    _need(type(effective['seed']) is int and type(effective['max_patches']) is int and effective['min_patches']<=effective['max_patches']<=3000 and effective['min_class_pixels_per_patch']<=65536,'Seed/patch maximum invalid')
    split=effective['min_patches_per_split'];_need(type(split) is dict and set(split)=={'train','val','test'} and all(type(split[s]) is int and n<=split[s]<=3000 for s,n in [('train',600),('val',100),('test',100)]),'Split floors invalid')
    for key,low,high in [('min_valid_fraction',.8,1),('min_province_inside_fraction',.95,1),('min_required_class_ratio',.005,.999999999),('max_reference_class_dominance',0,.9),('max_prediction_dominance',0,.995)]:_need(_number(effective[key]) and low<=effective[key]<=high and effective[key]>0,'Ratio gate threshold invalid: '+key)
    return effective


def _stage(stage,candidate,candidate_path,data,pins,size):
    stage=profile_receipt(stage)
    _need(type(stage) is dict and set(stage)==STAGE_FIELDS,'Exact staging receipt schema required')
    for key,value in {'schema_version':1,'kind':'DATA_CANDIDATE_STAGING_RECEIPT','status':'METADATA_STAGED_FOR_QA','next_step':'NEXT_QA_NOT_PERFORMED','qa_status':'NOT_PERFORMED','metadata_integrity_verified':True,'original_candidate_bytes_preserved':True,'proposed_refund_bytes':0,'exactly_once_applied':'UNKNOWN'}.items():_need(_same(stage[key],value),'Staging receipt state invalid')
    for key in STAGE_FALSE:_need(stage[key] is False,'Staging receipt false claim invalid: '+key)
    _need(type(stage['completion_contract']) is str and 0<len(stage['completion_contract'])<=4096,'Staging contract text invalid')
    oldpins=stage['input_pins'];_need(type(oldpins) is dict and set(oldpins)=={'source','readiness','saved_plan'} and all(_sha(x) for x in oldpins.values()) and oldpins['readiness']==pins['old_readiness'],'Old readiness pin differs from staging provenance')
    ref=stage['package_reference'];_need(type(ref) is dict and set(ref)=={'path','receipt_sha256'} and type(ref['path']) is str and 0<len(ref['path'])<=4096 and _sha(ref['receipt_sha256']),'Package reference invalid');_local(ref['path'])
    outputs=stage['verified_package_outputs'];_need(type(outputs) is dict and set(outputs)=={'plan','candidate'},'Package output references invalid')
    for role,item in outputs.items():_need(type(item) is dict and set(item)=={'name','sha256','bytes'} and item['name']==role+'.json' and _sha(item['sha256']) and _uint(item['bytes']) and 0<item['bytes']<=resource_policy(POLICY)['output_caps'][role],'Package output pin invalid')
    ref=stage['staged_candidate'];_need(type(ref) is dict and set(ref)=={'path','sha256','bytes'} and type(ref['path']) is str and 0<len(ref['path'])<=4096 and ref['sha256']==pins['candidate'] and _same(ref['bytes'],size),'Staged candidate pin/size invalid')
    _local(ref['path']);_need(_confined(data,ref['path'])==candidate_path,'Staged candidate path mismatch')
    _need(_same(outputs['candidate']['sha256'],pins['candidate']) and _same(outputs['candidate']['bytes'],size),'Package/staged candidate pin mismatch')
    _need(type(candidate) is dict and _same(candidate.get('schema_version'),1) and candidate.get('status')=='PLANNED_DERIVED_CANDIDATE' and candidate.get('executed') is False and candidate.get('learning_ready') is False,'Candidate metadata state invalid')
    _need(type(stage['derived_manifest_version']) is str and re.fullmatch('split-repair-v1-[0-9a-f]{16}',stage['derived_manifest_version']) is not None and candidate.get('version')==stage['derived_manifest_version'],'Candidate version mismatch')
    rows=candidate.get('scenes');_need(type(rows) is list and len(rows)<=(3000 if active() is not None else 100000) and _same(stage['candidate_row_count'],len(rows)) and _uint(stage['source_row_count']) and len(rows)<=stage['source_row_count']<=(3000 if active() is not None else 100000),'Candidate physical row counts invalid')
    lineage=candidate.get('lineage');_need(type(lineage) is dict and set(lineage)=={'source_manifest','selection_policy','source_row_indexes'},'Candidate lineage invalid')
    source=lineage['source_manifest'];_need(type(source) is dict and set(source)=={'path','sha256'} and type(source['path']) is str and 0<len(source['path'])<=4096 and source['sha256']==oldpins['source'],'Candidate source pin invalid');_local(source['path']);_confined(data,source['path'])
    selection=lineage['selection_policy'];_need(type(selection) is dict and _same(selection.get('province_splits'),FIXED_PROVINCE_SPLITS) and _same(selection.get('keep_split_priority'),['test','val','train']),'Candidate fixed selection policy invalid')
    indexes=lineage['source_row_indexes'];_need(type(indexes) is list and len(indexes)==len(rows) and all(_uint(i) and i<stage['source_row_count'] for i in indexes) and indexes==sorted(set(indexes)),'Candidate lineage row indexes invalid')
    projected=stage['projected_after'];_need(type(projected) is dict and set(projected)=={'eligible_patches_by_split','eligible_total','eligible_by_province_year'},'Projection schema invalid')
    counts=projected['eligible_patches_by_split'];_need(type(counts) is dict and set(counts)=={'train','val','test'} and all(_uint(v) and v<=len(rows) for v in counts.values()) and _same(projected['eligible_total'],sum(counts.values())),'Projection counts invalid')
    _need(type(projected['eligible_by_province_year']) is dict and all(type(k) is str and len(k)<=128 and _uint(v) for k,v in projected['eligible_by_province_year'].items()) and sum(projected['eligible_by_province_year'].values())==projected['eligible_total'],'Projection province/year counts invalid')


def _report(report,policy,candidate,data,pin,old):
    _need(type(report) is dict and _same(report.get('schema_version'),1) and type(report.get('ready_for_training')) is bool and report.get('scientific_accuracy_validated') is False,'QA report state invalid')
    blockers=report.get('blockers');_need(type(blockers) is list and len(blockers)<=10000 and all(type(x) is dict and type(x.get('code')) is str and 0<len(x['code'])<=128 for x in blockers),'QA blocker schema invalid')
    ready=report['ready_for_training'];_need(ready is (not blockers),'QA ready/blocker contradiction')
    expected_status='ready_for_weak_label_experiment' if ready else 'blocked'
    _need(report.get('status')==expected_status,'QA status/ready contradiction')
    _need(_same(report.get('policy'),policy),'QA report policy changed')
    refs=report.get('input_manifests');_need(type(refs) is list and len(refs)==1 and type(refs[0]) is dict and set(refs[0])=={'path','sha256'} and refs[0]['sha256']==pin,'QA candidate input pin invalid');_local(refs[0]['path']);_need(_confined(data,refs[0]['path'])==candidate,'QA input path differs')
    counts=report.get('patch_counts_by_split');_need(type(counts) is dict and set(counts)=={'train','val','test'} and all(_uint(v) and v<=3000 for v in counts.values()),'QA patch counts invalid')
    records=report.get('verified_files');_need(type(records) is list and len(records)<=10000 and all(type(r) is dict and set(r)=={'path','sha256','kind'} and type(r['path']) is str and 0<len(r['path'])<=4096 and _sha(r['sha256']) and type(r['kind']) is str and 0<len(r['kind'])<=128 for r in records),'QA verified-file metadata invalid')
    manifest_records=[r for r in records if r['kind']=='collection_manifest'];_need(len(manifest_records)==1 and manifest_records[0]['sha256']==pin and manifest_records[0]['path']==refs[0]['path'],'QA verified manifest pin invalid')
    _need(type(old.get('input_signature')) is dict and _same(report.get('input_signature'),old['input_signature']),'QA band/label signature changed')
    capture=report.get('connectivity_diagnostics');_need(type(capture) is dict and _same(capture.get('schema_version'),1) and capture.get('status')=='BLOCKED','QA diagnostic schema invalid')
    known={'CAPTURED_COMPONENTS_MATCH','CAPTURED_COMPONENT_MISMATCH','NOT_CAPTURED_UNSUPPORTED_POLICY','NOT_CAPTURED_BUDGET','NOT_CAPTURED_UNSUPPORTED_METADATA','FAILED_DIAGNOSTIC','FAILED_ADAPTER_BOUNDARY'}
    _need(type(capture.get('capture_status')) is str and capture['capture_status'] in known,'QA capture status invalid')
    for key in ['gate_result_modified','ready_for_training','scientific_accuracy_validated','settlement_authorized','execution_authorized','automatic_resume_allowed']:_need(capture.get(key) is False,'QA diagnostic authorization invalid')
    _need(_same(capture.get('proposed_refund_bytes'),0),'QA diagnostic refund invalid')
    for key in ['training_executed','eligibility_recomputed','eligible_patch_count_is_scene_count','historical_readiness_cause_reconstructed','provenance_verified','executing_code_verified']:
        if key in capture:_need(capture[key] is False,'QA diagnostic false claim invalid')
    for key in ['source_files_read','source_files_written','network_requests']:
        if key in capture:_need(_same(capture[key],0),'QA diagnostic IO claim invalid')
    if capture.get('supplied_eligible_patch_sum') is not None:_need(_same(capture['supplied_eligible_patch_sum'],sum(counts.values())),'QA diagnostic patch sum mismatch')
    if capture.get('scene_count') is not None:_need(_uint(capture['scene_count']) and capture['scene_count']<=100000,'QA diagnostic scene count invalid')
    if capture['capture_status'] in {'CAPTURED_COMPONENTS_MATCH','CAPTURED_COMPONENT_MISMATCH'}:_need(_same(capture.get('manifest_input_references'),refs),'QA captured candidate reference changed')
    return expected_status,counts,blockers,capture['capture_status']


@profile_entry
def assess_staged_candidate(data_root,paths,pins,output_dir):
    """출처·동일정책 guard. 기존 run의 QA는 호출하되 execute/resume는 항상 False."""
    _need(type(paths) is dict and set(paths)==set(ROLES) and type(pins) is dict and set(pins)==set(ROLES) and all(_sha(v) for v in pins.values()),'Four external input SHA pins required')
    root_logical=_local(data_root);data=root_logical.resolve();_local(data);_need(data.is_dir(),'Existing DATA root required')
    roles={'candidate':'candidate','staging_receipt':'saved_plan','policy':'source','old_readiness':'readiness'};contexts={r:_context(roles[r],profile_cap('candidate' if r=='candidate' else r,CAPS[r])) for r in ROLES};logical={};targets={};stamps={}
    for r in ROLES:
        value=Path(paths[r]);value=value if value.is_absolute() else data/value;logical[r]=_local(value);targets[r]=_confined(data,logical[r]);_local(targets[r]);stamps[r]=_stamp(targets[r].stat());_need(stamps[r][0]<=profile_cap('candidate' if r=='candidate' else r,CAPS[r]),'Input exceeds role byte cap')
    _need(len(set(targets.values()))==4 and len({s[3:] for s in stamps.values()})==4,'Four distinct input files required')
    out=_local(output_dir);target=_confined(data,out);_need(not out.exists() and not out.is_symlink(),'New DATA QA output directory required');parent=out.parent.resolve();parent_id=_dir_identity(parent)[:2]
    docs={r:contexts[r].read(logical[r],roles[r],pins[r])[0] for r in ROLES};_stage(docs['staging_receipt'],docs['candidate'],targets['candidate'],data,pins,stamps['candidate'][0]);effective=_policy(docs['policy'],docs['old_readiness'])
    old=docs['old_readiness'];_need(_same(old.get('schema_version'),1) and type(old.get('ready_for_training')) is bool and old.get('scientific_accuracy_validated') is False,'Old readiness schema invalid')
    _need(type(old.get('input_signature')) is dict,'Old label/band signature required')
    original_refs=old.get('input_manifests');_need(type(original_refs) is list and len(original_refs)==1 and type(original_refs[0]) is dict and set(original_refs[0])=={'path','sha256'} and original_refs[0]['sha256']==docs['staging_receipt']['input_pins']['source'],'Old readiness original source pin mismatch')
    _local(original_refs[0]['path']);_need(_confined(data,original_refs[0]['path'])==_confined(data,docs['candidate']['lineage']['source_manifest']['path']),'Old readiness original source path mismatch')
    def paths_ok(created=False):
        _need(root_logical.resolve()==data and out.resolve()==target and out.parent.resolve()==parent and _dir_identity(parent)[:2]==parent_id and not out.is_symlink(),'QA root/parent target changed')
        if created:_need(_dir_identity(out)[:2]==directory_id,'QA directory replaced')
        else:_need(not out.exists(),'QA directory appeared')
    def verify():
        for context in contexts.values():context.verify()
    verify();paths_ok();out.mkdir(exist_ok=False);directory_id=_dir_identity(out)[:2];report_path=target/'readiness.json'
    result=run([targets['candidate']],data,report_path,copy.deepcopy(docs['policy']),execute=False,resume=False,connectivity_diagnostics=True)
    state,counts,blockers,capture_status=_report(result,effective,targets['candidate'],data,pins['candidate'],docs['old_readiness'])
    verify();paths_ok(created=True)
    report_io=_context('saved_plan',16*1024**2);stored,report_sha=report_io.read(report_path,'saved_plan');_need(_same(stored,result),'Returned QA result differs from saved report')
    receipt={'schema_version':1,'kind':'STAGED_CANDIDATE_READINESS_QA_RECEIPT','status':'QA_COMPLETED','qa_scope':'EXISTING_READINESS_GATE_NO_EXECUTION',
      'inputs':{r:{'path':str(targets[r]),'sha256':pins[r],'bytes':stamps[r][0]} for r in ROLES},'readiness_report':{'name':'readiness.json','sha256':report_sha,'bytes':report_path.stat().st_size},
      'observed_readiness_status':state,'observed_gate_ready_for_training':result['ready_for_training'],'saved_blockers':copy.deepcopy(blockers),'patch_counts_by_split':copy.deepcopy(counts),'connectivity_capture_status':capture_status,
      'qa_performed':True,'full_plan_recomputation_performed':False,'package_revalidated':False,'prepared_dataset_registered':False,'training_executed':False,'execution_authorized':False,'ready_for_training':False,'scientific_accuracy_validated':False,'source_authenticity_verified':False,'exact_row_binding_verified':False,'training_split_leakage_resolved':False,'registry_called':False,'resume_requested':False,'settlement_authorized':False,'automatic_resume_allowed':False,'proposed_refund_bytes':0,'exactly_once_applied':'UNKNOWN',
      'completion_contract':'QA may complete with blockers. Receipt is not execution/scientific authorization. Absent/partial/invalid receipt is incomplete. Final stability check precedes exclusive receipt write; no atomic snapshot guarantee.'}
    receipt=profile_stamp(receipt)
    size=report_io.measure(receipt,'plan');verify();report_io.verify();paths_ok(created=True);receipt_out=target/'qa-receipt.json';_need(not receipt_out.exists() and not receipt_out.is_symlink(),'New QA receipt required');report_io.write(receipt_out,receipt,'plan',size)
    return receipt
