"""엄격한 evidence 영수증 검증과 동일 바이트 DATA metadata staging. QA는 실행하지 않는다."""
import copy
import hashlib
import os
from pathlib import Path
import re
from .candidate_materialization import POLICY,INPUT_ROLES,_dir_identity
from .split_json_io import BoundedJSONIO,_local,_stamp
from .split_validation import validate_split_repair_plan,_same
from ..data.recovery_terminal import _confined
from ..data.readiness_connectivity_witness import FIXED_PROVINCE_SPLITS

RECEIPT_CAP=65536
FALSE_FIELDS={'raster_readiness_rechecked','source_rows_modified_or_reassigned','executed','learning_ready','ready_for_training','scientific_accuracy_validated','source_authenticity_verified','exact_row_binding_verified','spatial_overlap_rechecked','exact_class_counts_recomputed','training_split_leakage_resolved','execution_authorized','registry_called','settlement_authorized','automatic_resume_allowed'}
RECEIPT_FIELDS={'schema_version','kind','status','candidate_status','readiness_status','scope','inputs','outputs','derived_manifest_version','fixed_province_splits','source_row_count','candidate_row_count','excluded_source_row_count','projected_after','metadata_integrity_verified','proposed_refund_bytes','exactly_once_applied','completion_contract'}|FALSE_FIELDS


def _need(value,message):
    if not value:raise ValueError(message)


def _sha(value):return type(value) is str and re.fullmatch('[0-9a-f]{64}',value) is not None

def _uint(value):return type(value) is int and value>=0


def _receipt_contract(receipt,input_pins):
    _need(type(receipt) is dict and set(receipt)==RECEIPT_FIELDS,'Exact materialization receipt schema required')
    for key,value in {'schema_version':1,'kind':'EVIDENCE_SPLIT_CANDIDATE_RECEIPT','status':'METADATA_ROUNDTRIP_VERIFIED','candidate_status':'PLANNED_DERIVED_CANDIDATE','readiness_status':'BLOCKED','scope':'PINNED_JSON_METADATA_ONLY_NOT_RASTER_READINESS','metadata_integrity_verified':True,'proposed_refund_bytes':0,'exactly_once_applied':'UNKNOWN'}.items():_need(_same(receipt[key],value),'Receipt status/type claim invalid: '+key)
    for key in FALSE_FIELDS:_need(receipt[key] is False,'Receipt false claim invalid: '+key)
    _need(type(receipt['completion_contract']) is str and 0<len(receipt['completion_contract'])<=4096,'Receipt completion text invalid')
    _need(type(receipt['derived_manifest_version']) is str and re.fullmatch('split-repair-v1-[0-9a-f]{16}',receipt['derived_manifest_version']) is not None and _same(receipt['fixed_province_splits'],FIXED_PROVINCE_SPLITS),'Receipt version/fixed split invalid')
    for key in ['source_row_count','candidate_row_count','excluded_source_row_count']:_need(_uint(receipt[key]) and receipt[key]<=100000,'Receipt row count invalid')
    _need(receipt['source_row_count']==receipt['candidate_row_count']+receipt['excluded_source_row_count'],'Receipt row partition invalid')
    inputs=receipt['inputs'];outputs=receipt['outputs'];_need(type(inputs) is dict and set(inputs)==set(INPUT_ROLES) and type(outputs) is dict and set(outputs)=={'plan','candidate'},'Receipt reference keys invalid')
    for role,value in inputs.items():
        _need(type(value) is dict and set(value)=={'path','sha256','bytes'} and type(value['path']) is str and 0<len(value['path'])<=4096 and _sha(value['sha256']) and value['sha256']==input_pins[role] and _uint(value['bytes']) and 0<value['bytes']<=POLICY['input_caps'][role],'Receipt input reference invalid')
    for role,value in outputs.items():
        _need(type(value) is dict and set(value)=={'name','sha256','bytes'} and value['name']==role+'.json' and _sha(value['sha256']) and _uint(value['bytes']) and 0<value['bytes']<=POLICY['output_caps'][role],'Receipt output reference invalid')


def _copy_bytes(source,destination,stamp,pin,maximum):
    """原本JSON 바이트만 복사. 픽셀/직렬화/권한·상태 변경 없음."""
    _need(_stamp(source.stat())==stamp,'Candidate changed before copy');digest=hashlib.sha256();count=0
    with source.open('rb',buffering=0) as src:
        _need(_stamp(os.fstat(src.fileno()))==stamp,'Candidate descriptor changed')
        with destination.open('xb') as dst:
            while count<stamp[0]:
                block=src.read(min(65536,stamp[0]-count));_need(bool(block),'Candidate ended before expected size')
                _need(count+len(block)<=maximum and count+len(block)<=stamp[0],'Candidate copy exceeds byte cap')
                _need(dst.write(block)==len(block),'Incomplete metadata copy');count+=len(block);digest.update(block)
        _need(_stamp(os.fstat(src.fileno()))==stamp,'Candidate changed during copy')
    _need(_stamp(source.stat())==stamp and count==stamp[0] and digest.hexdigest()==pin,'Copied candidate SHA/size mismatch')
    return count


def stage_split_candidate(data_root,package_dir,receipt_sha256,input_pins,output_dir,*,evidence_root):
    """3 외부 pin + pinned receipt를 검증한 뒤 DATA 새 metadata 파일만 staging."""
    _need(_sha(receipt_sha256) and type(input_pins) is dict and set(input_pins)==set(INPUT_ROLES) and all(_sha(p) for p in input_pins.values()),'Explicit receipt SHA and three external lowercase SHA pins required')
    roots=[_local(data_root),_local(evidence_root)];resolved=[p.resolve() for p in roots]
    for p in resolved:_local(p);_need(p.is_dir(),'Existing local roots required')
    data,evidence=resolved;_need(not evidence.is_relative_to(data) and not data.is_relative_to(evidence),'DATA and evidence roots must be disjoint')
    package=_local(package_dir);package_target=_confined(evidence,package);package_id=_dir_identity(package_target)[:2]
    out=_local(output_dir);target=_confined(data,out);_need(not out.exists() and not out.is_symlink(),'New DATA staging directory required')
    parent=out.parent.resolve();parent_id=_dir_identity(parent)[:2];_need(target.parent==parent,'Staging parent mismatch')
    receipt_path=package/'receipt.json';receipt_target=_confined(evidence,receipt_path)
    receipt_policy=copy.deepcopy(POLICY);receipt_policy['input_caps']['saved_plan']=RECEIPT_CAP;receipt_policy['output_caps']={'plan':RECEIPT_CAP,'candidate':RECEIPT_CAP}
    receipt_io=BoundedJSONIO(receipt_policy);receipt=receipt_io.read(receipt_path,'saved_plan',receipt_sha256)[0];_receipt_contract(receipt,input_pins)
    paths={};stamps={};targets={}
    for role,reference in receipt['inputs'].items():
        scope=data if role!='saved_plan' else evidence
        paths[role]=_local(reference['path']);targets[role]=_confined(scope,paths[role]);_local(targets[role]);stamps[role]=_stamp(targets[role].stat())
        _need(stamps[role][0]==reference['bytes'],'Receipt input size mismatch')
    package_paths={'new_plan':package/'plan.json','candidate':package/'candidate.json'}
    for role,logical in package_paths.items():
        targets[role]=_confined(evidence,logical);_local(targets[role]);stamps[role]=_stamp(targets[role].stat())
        info=receipt['outputs']['plan' if role=='new_plan' else 'candidate'];_need(stamps[role][0]==info['bytes'],'Receipt output size mismatch')
    targets['receipt']=receipt_target;stamps['receipt']=_stamp(receipt_target.stat())
    _need(len(set(targets.values()))==6 and len({s[3:] for s in stamps.values()})==6,'Receipt/package/inputs must be distinct regular files')
    io=BoundedJSONIO(copy.deepcopy(POLICY));docs={r:io.read(paths[r],r,input_pins[r])[0] for r in INPUT_ROLES}
    plan,plan_sha=io.read(package_paths['new_plan'],'saved_plan',receipt['outputs']['plan']['sha256']);candidate,candidate_sha=io.read(package_paths['candidate'],'candidate',receipt['outputs']['candidate']['sha256'])
    _need(all(type(d) is dict for d in [*docs.values(),plan,candidate]),'Pinned JSON documents must be objects')
    _need(_same(plan,docs['saved_plan']),'Package plan differs from caller-pinned original plan')
    _need(_same(receipt['derived_manifest_version'],plan.get('derived_manifest_version')) and _same(receipt['projected_after'],plan.get('projected_after')),'Receipt plan/version projection mismatch')
    _need(type(docs['source'].get('scenes')) is list and type(candidate.get('scenes')) is list and _same(receipt['source_row_count'],len(docs['source']['scenes'])) and _same(receipt['candidate_row_count'],len(candidate['scenes'])) and _same(receipt['excluded_source_row_count'],len(plan.get('excluded_row_indexes',[]))),'Receipt physical row count mismatch')
    checked=validate_split_repair_plan(package_paths['new_plan'],paths['source'],input_pins['source'],province_splits=dict(FIXED_PROVINCE_SPLITS),readiness_path=paths['readiness'],readiness_sha256=input_pins['readiness'],data_root=data,candidate_path=package_paths['candidate'],candidate_sha256=candidate_sha,io_policy=io)
    _need(checked.get('status')=='METADATA_INTEGRITY_VERIFIED' and checked.get('plan_integrity_valid') is True and checked.get('candidate_validation',{}).get('status')=='EXACT_METADATA_MATCH' and checked['candidate_validation'].get('candidate_integrity_valid') is True and checked.get('ready_for_training') is False and checked.get('training_executed') is False and checked.get('scientific_accuracy_validated') is False,'Full candidate metadata verification failed')
    for key in ['raster_files_rehashed','spatial_overlap_rechecked','exact_class_counts_recomputed']:_need(checked.get(key) is False,'Unexpected raster/class QA claim')
    def check_paths(created=False):
        _need(all(p.resolve()==r for p,r in zip(roots,resolved)) and _confined(evidence,package)==package_target and _dir_identity(package_target)[:2]==package_id,'Input root/package changed')
        _need(out.resolve()==target and out.parent.resolve()==parent and _dir_identity(parent)[:2]==parent_id and not out.is_symlink(),'Staging path or parent changed')
        if created:_need(_dir_identity(out)[:2]==created_id,'Staging directory replaced')
        else:_need(not out.exists(),'Staging directory appeared')
    io.verify();receipt_io.verify();check_paths();out.mkdir(exist_ok=False);created_id=_dir_identity(out)[:2]
    staged=target/'candidate.json';_copy_bytes(targets['candidate'],staged,stamps['candidate'],candidate_sha,POLICY['input_caps']['candidate'])
    staged_doc,staged_sha=io.read(staged,'candidate',candidate_sha);_need(_same(staged_doc,candidate) and staged.stat().st_size==receipt['outputs']['candidate']['bytes'],'Staged metadata differs')
    staging={'schema_version':1,'kind':'DATA_CANDIDATE_STAGING_RECEIPT','status':'METADATA_STAGED_FOR_QA','next_step':'NEXT_QA_NOT_PERFORMED','qa_status':'NOT_PERFORMED',
      'package_reference':{'path':str(package_target),'receipt_sha256':receipt_sha256},'input_pins':dict(input_pins),'verified_package_outputs':copy.deepcopy(receipt['outputs']),
      'staged_candidate':{'path':str(staged.relative_to(data)),'sha256':staged_sha,'bytes':staged.stat().st_size},'derived_manifest_version':receipt['derived_manifest_version'],'source_row_count':receipt['source_row_count'],'candidate_row_count':receipt['candidate_row_count'],'projected_after':copy.deepcopy(receipt['projected_after']),
      'metadata_integrity_verified':True,'original_candidate_bytes_preserved':True,'qa_performed':False,'readiness_assess_called':False,'registered':False,'registry_called':False,'executed':False,'learning_ready':False,'ready_for_training':False,'scientific_accuracy_validated':False,'source_authenticity_verified':False,'exact_row_binding_verified':False,'spatial_overlap_rechecked':False,'exact_class_counts_recomputed':False,'training_split_leakage_resolved':False,'source_rows_modified_or_reassigned':False,'execution_authorized':False,'settlement_authorized':False,'automatic_resume_allowed':False,'proposed_refund_bytes':0,'exactly_once_applied':'UNKNOWN',
      'completion_contract':'Absent, partial or invalid staging receipt is incomplete. Validate receipt schema and staged SHA before QA. Receipt follows final stability check; no atomic snapshot guarantee.'}
    size=receipt_io.measure(staging,'plan');io.verify();receipt_io.verify();check_paths(created=True)
    receipt_out=target/'staging-receipt.json';_need(not receipt_out.exists() and not receipt_out.is_symlink(),'New staging receipt required')
    receipt_io.write(receipt_out,staging,'plan',size)
    return staging
