"""고정 보고서 4JSON만 대조한다. 원본/후보 manifest·래스터·assess는 읽거나 실행하지 않는다."""
from collections import Counter
import copy
from pathlib import Path
import re
from .split_json_io import BoundedJSONIO,_local,_stamp
from .split_validation import _same
from ..data.readiness_connectivity_witness import FIXED_PROVINCE_SPLITS,PROVINCES
from ..data.readiness_connectivity_lineage import _lexical_identity_path
from ..data.recovery_terminal import _confined

PIN_NAMES=('original_report_sha256','candidate_report_sha256','qa_receipt_sha256','staging_receipt_sha256')
FIXED_PATHS={'original_report_sha256':'first-group/readiness-resume-20261017.json','candidate_report_sha256':'first-group-candidate-readiness-qa-20261017/readiness.json','qa_receipt_sha256':'first-group-candidate-readiness-qa-20261017/qa-receipt.json','staging_receipt_sha256':'first-group-candidate-qa-stage-20261017/staging-receipt.json'}
CAPS={k:(16*1024**2 if 'report' in k else 65536) for k in PIN_NAMES}
FALSE_FIELDS={'ready_for_training','scientific_accuracy_validated','source_authenticity_verified','exact_row_binding_verified','training_executed','execution_authorized','registry_called','training_split_leakage_resolved','automatic_resume_allowed','settlement_authorized'}
STAGE_FALSE={'qa_performed','readiness_assess_called','registered','registry_called','executed','learning_ready','ready_for_training','scientific_accuracy_validated','source_authenticity_verified','exact_row_binding_verified','spatial_overlap_rechecked','exact_class_counts_recomputed','training_split_leakage_resolved','source_rows_modified_or_reassigned','execution_authorized','settlement_authorized','automatic_resume_allowed'}
STAGE_FIELDS={'schema_version','kind','status','next_step','qa_status','package_reference','input_pins','verified_package_outputs','staged_candidate','derived_manifest_version','source_row_count','candidate_row_count','projected_after','metadata_integrity_verified','original_candidate_bytes_preserved','proposed_refund_bytes','exactly_once_applied','completion_contract'}|STAGE_FALSE
QA_FALSE={'full_plan_recomputation_performed','package_revalidated','prepared_dataset_registered','training_executed','execution_authorized','ready_for_training','scientific_accuracy_validated','source_authenticity_verified','exact_row_binding_verified','training_split_leakage_resolved','registry_called','resume_requested','settlement_authorized','automatic_resume_allowed'}
QA_FIELDS={'schema_version','kind','status','qa_scope','inputs','readiness_report','observed_readiness_status','observed_gate_ready_for_training','saved_blockers','patch_counts_by_split','connectivity_capture_status','qa_performed','proposed_refund_bytes','exactly_once_applied','completion_contract'}|QA_FALSE


def _need(value,message='저장 QA 비교 계약이 올바르지 않습니다.'):
    if not value:raise ValueError(message)


def _sha(value):return type(value) is str and re.fullmatch('[0-9a-f]{64}',value) is not None

def _uint(value,maximum):return type(value) is int and 0<=value<=maximum

def _path(value,root):
    _need(type(value) is str and 0<len(value)<=4096);key=_lexical_identity_path(value,root);_need(key is not None);return key


def _ref(value,root,*,path=None,pin=None,size=None):
    _need(type(value) is dict and set(value)=={'path','sha256','bytes'} and _sha(value['sha256']) and _uint(value['bytes'],64*1024**2) and value['bytes']>0)
    key=_path(value['path'],root)
    if path is not None:_need(key==_path(path,root))
    if pin is not None:_need(value['sha256']==pin)
    if size is not None:_need(_same(value['bytes'],size))


def _counts(report):
    counts=report.get('patch_counts_by_split');_need(type(counts) is dict and set(counts)=={'train','val','test'} and all(_uint(v,3000) for v in counts.values()))
    return {'eligible_patches_by_split':copy.deepcopy(counts),'eligible_patch_count':sum(counts.values()),'blocker_count':len(report['blockers'])}


def _report(report,root):
    _need(type(report) is dict and _same(report.get('schema_version'),1) and report.get('status')=='blocked' and report.get('ready_for_training') is False and report.get('scientific_accuracy_validated') is False)
    blockers=report.get('blockers');_need(type(blockers) is list and 0<len(blockers)<=10000)
    for item in blockers:_need(type(item) is dict and type(item.get('code')) is str and re.fullmatch('[A-Z][A-Z0-9_]{0,63}',item['code']) is not None)
    policy=report.get('policy');_need(type(policy) is dict and _same(policy.get('province_splits'),FIXED_PROVINCE_SPLITS) and _same(policy.get('patch_size'),256) and type(policy.get('required_classes')) is list and all(type(x) is int and 0<=x<9 for x in policy['required_classes']) and len(policy['required_classes'])==len(set(policy['required_classes'])) and 7 in policy['required_classes'])
    _need(type(policy.get('min_class_pixels_per_split')) is int and 256<=policy['min_class_pixels_per_split']<=65536 and type(policy.get('min_class_patches_per_split')) is int and 5<=policy['min_class_patches_per_split']<=3000)
    _need(_same(policy.get('required_provinces'),list(PROVINCES)) and _same(policy.get('required_years'),list(range(2020,2026))) and _same(policy.get('band_names'),['B02','B03','B04','B08','B11','B12']))
    refs=report.get('input_manifests');_need(type(refs) is list and len(refs)==1 and type(refs[0]) is dict and set(refs[0])=={'path','sha256'} and _sha(refs[0]['sha256']));_path(refs[0]['path'],root)
    signature=report.get('input_signature');_need(type(signature) is dict and set(signature)=={'band_names','band_indices','patch_size','normalization_mode','label_source','class_names'} and type(signature['label_source']) is str and signature['label_source'] in {'esri_io','worldcover','dynamic_world','classes'} and signature['label_source']==policy.get('label_source') and _same(signature['band_names'],policy['band_names']) and _same(signature['band_indices'],list(range(1,7))) and _same(signature['patch_size'],256) and signature['normalization_mode']=='per_scene_product_metadata' and type(signature['class_names']) is list and len(signature['class_names'])==9 and all(type(v) is str and 0<len(v)<=256 for v in signature['class_names']) and signature['class_names'][7]=='bare')
    counts=_counts(report)
    for key in ['class_counts_by_split','class_patch_counts_by_split']:
        values=report.get(key);_need(type(values) is dict and set(values)=={'train','val','test'})
        for split,items in values.items():
            _need(type(items) is list and len(items)==9 and all(_uint(n,9007199254740991 if key=='class_counts_by_split' else 3000) for n in items))
            _need(all(n<=counts['eligible_patches_by_split'][split]*(65536 if key=='class_counts_by_split' else 1) for n in items))
            if key=='class_counts_by_split':_need(sum(items)<=counts['eligible_patches_by_split'][split]*65536)
    return counts,Counter(item['code'] for item in blockers)


def project_candidate_qa(documents,pins,references,*,data_root_literal):
    """메모리 안의 선택 보고서 계약 대조. pin의 실제 바이트 검증은 reader 담당."""
    _need(type(documents) is dict and set(documents)==set(PIN_NAMES) and type(pins) is dict and set(pins)==set(PIN_NAMES) and all(_sha(p) for p in pins.values()) and type(references) is dict and set(references)==set(PIN_NAMES))
    old,new,qa,stage=(documents[k] for k in PIN_NAMES);root=data_root_literal
    for k,ref in references.items():_need(type(ref) is dict and set(ref)=={'path','bytes'} and _uint(ref['bytes'],CAPS[k]) and ref['bytes']>0);_path(ref['path'],root)
    old_summary,old_codes=_report(old,root);new_summary,new_codes=_report(new,root)
    _need(old.get('prepared_payload') is None and 'connectivity_diagnostics' not in old and old.get('scene_count') is None,'Original physical scene count is outside supported stored scope')
    _need(_same(old['policy'],new['policy']) and _same(old['input_signature'],new['input_signature']))
    _need(type(stage) is dict and set(stage)==STAGE_FIELDS and type(qa) is dict and set(qa)==QA_FIELDS)
    for item,states,false_fields in [(stage,{'schema_version':1,'kind':'DATA_CANDIDATE_STAGING_RECEIPT','status':'METADATA_STAGED_FOR_QA','next_step':'NEXT_QA_NOT_PERFORMED','qa_status':'NOT_PERFORMED','metadata_integrity_verified':True,'original_candidate_bytes_preserved':True,'proposed_refund_bytes':0,'exactly_once_applied':'UNKNOWN'},STAGE_FALSE),(qa,{'schema_version':1,'kind':'STAGED_CANDIDATE_READINESS_QA_RECEIPT','status':'QA_COMPLETED','qa_scope':'EXISTING_READINESS_GATE_NO_EXECUTION','observed_readiness_status':'blocked','observed_gate_ready_for_training':False,'qa_performed':True,'proposed_refund_bytes':0,'exactly_once_applied':'UNKNOWN'},QA_FALSE)]:
        for k,v in states.items():_need(_same(item[k],v))
        for k in false_fields:_need(item[k] is False)
        _need(type(item['completion_contract']) is str and 0<len(item['completion_contract'])<=4096)
    _need(type(stage['derived_manifest_version']) is str and re.fullmatch('split-repair-v1-[0-9a-f]{16}',stage['derived_manifest_version']) is not None)
    package=stage['package_reference'];_need(type(package) is dict and set(package)=={'path','receipt_sha256'} and type(package['path']) is str and 0<len(package['path'])<=4096 and _sha(package['receipt_sha256']));_local(package['path'])
    source_pins=stage['input_pins'];_need(type(source_pins) is dict and set(source_pins)=={'source','readiness','saved_plan'} and all(_sha(v) for v in source_pins.values()) and source_pins['readiness']==pins['original_report_sha256'] and old['input_manifests'][0]['sha256']==source_pins['source'])
    staged=stage['staged_candidate'];_ref(staged,root);_need(staged['sha256']==new['input_manifests'][0]['sha256'] and _path(staged['path'],root)==_path(new['input_manifests'][0]['path'],root))
    outputs=stage['verified_package_outputs'];_need(type(outputs) is dict and set(outputs)=={'plan','candidate'})
    for k,item in outputs.items():_need(type(item) is dict and set(item)=={'name','sha256','bytes'} and item['name']==k+'.json' and _sha(item['sha256']) and _uint(item['bytes'],4*1024**2 if k=='plan' else 64*1024**2) and item['bytes']>0)
    _need(outputs['candidate']['sha256']==staged['sha256'] and _same(outputs['candidate']['bytes'],staged['bytes']))
    inputs=qa['inputs'];_need(type(inputs) is dict and set(inputs)=={'candidate','staging_receipt','policy','old_readiness'})
    _ref(inputs['candidate'],root,path=staged['path'],pin=staged['sha256'],size=staged['bytes'])
    _ref(inputs['old_readiness'],root,path=references['original_report_sha256']['path'],pin=pins['original_report_sha256'],size=references['original_report_sha256']['bytes'])
    _ref(inputs['staging_receipt'],root,path=references['staging_receipt_sha256']['path'],pin=pins['staging_receipt_sha256'],size=references['staging_receipt_sha256']['bytes'])
    _ref(inputs['policy'],root);_need(inputs['policy']['bytes']<=1024**2)
    report_ref=qa['readiness_report'];_need(type(report_ref) is dict and set(report_ref)=={'name','sha256','bytes'} and report_ref['name']=='readiness.json' and report_ref['sha256']==pins['candidate_report_sha256'] and _same(report_ref['bytes'],references['candidate_report_sha256']['bytes']))
    _need(_same(qa['saved_blockers'],new['blockers']) and _same(qa['patch_counts_by_split'],new['patch_counts_by_split']))
    capture=new.get('connectivity_diagnostics');_need(type(capture) is dict and _same(capture.get('schema_version'),1) and capture.get('status')=='BLOCKED' and type(capture.get('capture_status')) is str and qa['connectivity_capture_status']==capture['capture_status'])
    for k in ['gate_result_modified','ready_for_training','scientific_accuracy_validated','settlement_authorized','execution_authorized','automatic_resume_allowed']:_need(capture.get(k) is False)
    _need(_same(capture.get('proposed_refund_bytes'),0))
    for k in ['source_files_read','source_files_written','network_requests']:
        if k in capture:_need(_same(capture[k],0))
    for k in ['training_executed','eligibility_recomputed','eligible_patch_count_is_scene_count','historical_readiness_cause_reconstructed','provenance_verified','executing_code_verified']:
        if k in capture:_need(capture[k] is False)
    captured=capture['capture_status'] in {'CAPTURED_COMPONENTS_MATCH','CAPTURED_COMPONENT_MISMATCH'}
    if captured:
        _need(capture.get('scope')=='ALL_APPENDED_ASSESS_SCENES_INCLUDING_ZERO_PATCH' and capture.get('gate_components_match') is (capture['capture_status']=='CAPTURED_COMPONENTS_MATCH'))
        _need(_same(capture.get('manifest_input_references'),new['input_manifests']) and _uint(capture.get('scene_count'),2000) and _same(capture.get('supplied_eligible_patch_sum'),new_summary['eligible_patch_count']))
        scene_count=capture['scene_count']
    else:
        _need(capture['capture_status'] in {'NOT_CAPTURED_UNSUPPORTED_POLICY','NOT_CAPTURED_BUDGET','NOT_CAPTURED_UNSUPPORTED_METADATA','FAILED_DIAGNOSTIC','FAILED_ADAPTER_BOUNDARY'});scene_count=None
    _need(_uint(stage['source_row_count'],100000) and _uint(stage['candidate_row_count'],100000) and stage['candidate_row_count']<=stage['source_row_count'])
    if captured:_need(scene_count==stage['candidate_row_count'])
    projected=stage['projected_after'];_need(type(projected) is dict and set(projected)=={'eligible_patches_by_split','eligible_total','eligible_by_province_year'} and type(projected['eligible_patches_by_split']) is dict and set(projected['eligible_patches_by_split'])=={'train','val','test'} and all(_uint(n,stage['candidate_row_count']) for n in projected['eligible_patches_by_split'].values()) and _same(projected['eligible_total'],sum(projected['eligible_patches_by_split'].values())) and type(projected['eligible_by_province_year']) is dict and all(type(k) is str and len(k)<=128 and _uint(v,stage['candidate_row_count']) for k,v in projected['eligible_by_province_year'].items()) and sum(projected['eligible_by_province_year'].values())==projected['eligible_total'])
    codes=sorted(set(old_codes)|set(new_codes));_need(len(codes)<=32)
    bare={'class_index':7,'class_name':'bare','original_pixels_by_split':{s:old['class_counts_by_split'][s][7] for s in ('train','val','test')},'candidate_pixels_by_split':{s:new['class_counts_by_split'][s][7] for s in ('train','val','test')},'original_patch_counts_by_split':{s:old['class_patch_counts_by_split'][s][7] for s in ('train','val','test')},'candidate_patch_counts_by_split':{s:new['class_patch_counts_by_split'][s][7] for s in ('train','val','test')},'required_min_pixels_per_split':new['policy']['min_class_pixels_per_split'],'required_min_class_patches_per_split':new['policy']['min_class_patches_per_split'],'shortage_resolved':False}
    bare['candidate_shortage_observed']=any(bare['candidate_pixels_by_split'][s]<bare['required_min_pixels_per_split'] or bare['candidate_patch_counts_by_split'][s]<bare['required_min_class_patches_per_split'] for s in ('train','val','test'))
    code='SHARED_SOURCE_CROSSES_FIXED_SPLIT'
    return {'schema_version':1,'status':'BLOCKED','scope':'PINNED_REPORT_COMPARISON_ONLY','pins':dict(pins),'original':old_summary,'candidate':new_summary,'blocker_frequencies':[{'code':k,'original_count':old_codes[k],'candidate_count':new_codes[k]} for k in codes],
      'shared_source_blocker':{'code':code,'original_observed':bool(old_codes[code]),'candidate_observed':bool(new_codes[code]),'absence_proves_independence':False},
      'row_counts':{'original_report_physical_scene_count':None,'original_report_scope':'NOT_PERSISTED','source_rows_declared':stage['source_row_count'],'candidate_rows_declared':stage['candidate_row_count'],'declared_scope':'PINNED_STAGING_RECEIPT_DECLARATION','candidate_appended_scene_count':scene_count,'candidate_capture_scope':'STORED_QA_CAPTURE' if captured else 'NOT_CAPTURED'},'bare_class':bare,**{k:False for k in sorted(FALSE_FIELDS)}}


def compare_candidate_qa(data_root,pins):
    _need(type(pins) is dict and set(pins)==set(PIN_NAMES) and all(_sha(v) for v in pins.values()))
    logical_root=_local(data_root);root=logical_root.resolve();_local(root);targets={};contexts={};references={}
    for k in PIN_NAMES:
        logical=logical_root/FIXED_PATHS[k];target=_confined(root,logical);_local(target);stamp=_stamp(target.stat());_need(stamp[0]<=CAPS[k],'Pinned comparison input exceeds byte cap')
        targets[k]=logical;references[k]={'path':str(target),'bytes':stamp[0]};contexts[k]=BoundedJSONIO({'input_caps':{'source':CAPS[k],'readiness':CAPS[k],'saved_plan':CAPS[k],'candidate':CAPS[k]},'output_caps':{'plan':65536,'candidate':65536},'max_depth':32})
    _need(len({references[k]['path'] for k in PIN_NAMES})==4)
    documents={k:contexts[k].read(targets[k],'source',pins[k])[0] for k in PIN_NAMES}
    result=project_candidate_qa(documents,pins,references,data_root_literal=str(root))
    for context in contexts.values():context.verify()
    _need(logical_root.resolve()==root,'Pinned comparison root changed')
    return result
