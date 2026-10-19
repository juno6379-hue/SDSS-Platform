"""저장 class7 통계의 부족 조건만 산출. 수집량/새장면 수/학습 승인을 추정하지 않는다."""
import copy
import math
from pathlib import Path
import re
from .readiness import balance_diagnostics
from .split_validation import _same
from .split_json_io import BoundedJSONIO,_local,_stamp
from ..data.recovery_terminal import _confined
from ..data.readiness_connectivity_witness import FIXED_PROVINCE_SPLITS
from ..data.readiness_connectivity_lineage import _lexical_identity_path

REPORT_RELATIVE='first-group-candidate-readiness-qa-20261017/readiness.json'
REPORT_CAP=16*1024**2
OUTPUT_CAP=65536
FALSE_FIELDS={'spatial_overlap_rechecked','source_independence_verified','pixels_rechecked','requirements_are_full_gate','new_scene_count_estimated','download_volume_estimated','adding_pixel_shortfall_alone_guarantees_ready','policy_thresholds_changed','exact_label_requirement_verified','ready_for_training','scientific_accuracy_validated','source_authenticity_verified','exact_row_binding_verified','execution_authorized','training_executed','collection_authorized','registry_called','training_split_leakage_resolved','settlement_authorized','automatic_resume_allowed'}


def _need(value,message='저장된 나지 부족 계약이 올바르지 않습니다.'):
    if not value:raise ValueError(message)


def _sha(value):return type(value) is str and re.fullmatch('[0-9a-f]{64}',value) is not None

def _uint(value,maximum):return type(value) is int and 0<=value<=maximum

def _ratio(value):
    if type(value) not in (int,float):return False
    try:return math.isfinite(value)
    except OverflowError:return False


def build_bare_class_requirements(report,reference):
    """메모리 객체만 사용. reference SHA는 호출자 선언이며 실제 파일 검증이 아니다."""
    _need(type(reference) is dict and set(reference)=={'path','sha256'} and type(reference['path']) is str and 0<len(reference['path'])<=4096 and _sha(reference['sha256']))
    _need(type(report) is dict and _same(report.get('schema_version'),1) and report.get('status')=='blocked' and report.get('ready_for_training') is False and report.get('scientific_accuracy_validated') is False)
    policy=report.get('policy');_need(type(policy) is dict and _same(policy.get('province_splits'),FIXED_PROVINCE_SPLITS) and _same(policy.get('patch_size'),256))
    required=policy.get('required_classes');_need(type(required) is list and all(_uint(x,8) for x in required) and len(required)>=2 and len(required)==len(set(required)) and 7 in required)
    for key,minimum,maximum in [('min_class_pixels_per_split',256,65536),('min_class_patches_per_split',5,3000),('min_class_pixels_per_patch',256,65536)]:_need(type(policy.get(key)) is int and minimum<=policy[key]<=maximum)
    minimum_ratio=policy.get('min_required_class_ratio');maximum_dominance=policy.get('max_reference_class_dominance')
    _need(_ratio(minimum_ratio) and .005<=minimum_ratio<1 and _ratio(maximum_dominance) and 0<maximum_dominance<=.90)
    signature=report.get('input_signature');_need(type(signature) is dict and type(signature.get('class_names')) is list and len(signature['class_names'])==9 and all(type(s) is str and 0<len(s)<=256 for s in signature['class_names']) and signature['class_names'][7]=='bare' and signature.get('label_source')==policy.get('label_source') and type(signature.get('label_source')) is str and signature['label_source'] in {'esri_io','worldcover','dynamic_world','classes'})
    manifests=report.get('input_manifests');_need(type(manifests) is list and len(manifests)==1 and type(manifests[0]) is dict and set(manifests[0])=={'path','sha256'} and type(manifests[0]['path']) is str and 0<len(manifests[0]['path'])<=4096 and _sha(manifests[0]['sha256']))
    blockers=report.get('blockers');_need(type(blockers) is list and 0<len(blockers)<=10000 and all(type(x) is dict and type(x.get('code')) is str and re.fullmatch('[A-Z][A-Z0-9_]{0,63}',x['code']) is not None for x in blockers))
    eligible=report.get('patch_counts_by_split');counts=report.get('class_counts_by_split');patches=report.get('class_patch_counts_by_split');stored=report.get('reference_balance_by_split')
    for value in (eligible,counts,patches,stored):_need(type(value) is dict and set(value)=={'train','val','test'})
    by_split={}
    for split in ('train','val','test'):
        n=eligible[split];pixels=counts[split];class_patches=patches[split]
        _need(_uint(n,3000) and type(pixels) is list and type(class_patches) is list and len(pixels)==len(class_patches)==9 and all(_uint(v,n*65536) for v in pixels) and sum(pixels)<=n*65536 and all(_uint(v,n) for v in class_patches))
        _need(all(class_patches[i]*policy['min_class_pixels_per_patch']<=pixels[i] for i in range(9)),'기여 패치 수와 클래스 최소 픽셀 조건이 모순됩니다.')
        # Existing function is pure array/policy arithmetic: no assess or pixel IO.
        recomputed=balance_diagnostics(pixels,class_patches,policy)
        _need(_same(stored[split],recomputed),'저장 reference balance가 class 통계/정책과 다릅니다.')
        total=sum(pixels);bare=pixels[7];contributing=class_patches[7]
        ratio=bare/total if total else None;dominance=max(pixels)/total if total else None
        pixel_shortfall=max(0,policy['min_class_pixels_per_split']-bare);patch_shortfall=max(0,policy['min_class_patches_per_split']-contributing)
        ratio_met=bool(total and ratio>=minimum_ratio)
        by_split[split]={'eligible_patches':n,'bare_pixels':bare,'minimum_split_bare_pixels':policy['min_class_pixels_per_split'],'split_pixel_shortfall':pixel_shortfall,
          'contributing_class_patches':contributing,'minimum_contributing_class_patches':policy['min_class_patches_per_split'],'contributing_patch_shortfall':patch_shortfall,'minimum_bare_pixels_per_contributing_patch':policy['min_class_pixels_per_patch'],
          'reference_class_pixel_total':total,'bare_ratio':ratio,'minimum_bare_ratio':minimum_ratio,'bare_ratio_shortfall':max(0.0,minimum_ratio-ratio) if total else None,'bare_ratio_threshold_met':ratio_met,
          'dominant_class_ratio':dominance,'maximum_dominant_class_ratio':maximum_dominance,'dominance_threshold_met':bool(total and dominance<=maximum_dominance),
          'all_bare_conditions_met':pixel_shortfall==0 and patch_shortfall==0 and ratio_met,'stored_reference_balance_passed':recomputed['passed'],'stored_reference_balance_failures':copy.deepcopy(recomputed['failures'])}
    return {'schema_version':1,'kind':'BARE_CLASS_STORED_REQUIREMENTS','status':'BLOCKED','scope':'READONLY_REQUIREMENTS_ONLY','report_reference':copy.deepcopy(reference),'pin_validation':'CALLER_DECLARED_REFERENCE_ONLY','class_index':7,'class_name':'bare','fixed_province_splits':dict(FIXED_PROVINCE_SPLITS),'eligible_patch_count':sum(eligible.values()),'by_split':by_split,
      'ratio_denominator_definition':'SUM_OF_NINE_STORED_REFERENCE_CLASS_PIXEL_COUNTS_IN_THE_SAME_SPLIT','zero_denominator_contract':'Stored balance uses zero class ratios; this projection reports unavailable ratio and shortfall as null and threshold false.',
      'stored_balance_metadata_recomputed':True,'stored_balance_exact_match':True,'source_manifest_reference':copy.deepcopy(manifests[0]),'source_manifest_currently_verified':False,
      **{k:False for k in sorted(FALSE_FIELDS)},'proposed_refund_bytes':0,'exactly_once_applied':'UNKNOWN','network_requests':0,'source_files_written':0,
      'limitation':'Stored metadata conditions only. Pixel floor, contributing-patch representation, ratio and overall balance are separate. No future scene/pixel/download volume, exact labels, collection or training approval is inferred. Future data must retain fixed province splits and pass period, quality, boundary, label and source/overlap checks; none are performed here.'}


def inspect_bare_class_requirements(data_root,expected_report_sha256):
    _need(_sha(expected_report_sha256),'명시 외부 report SHA가 필요합니다.')
    logical_root=_local(data_root);root=logical_root.resolve();_local(root)
    logical=logical_root/REPORT_RELATIVE;target=_confined(root,logical);_local(target);stamp=_stamp(target.stat());_need(stamp[0]<=REPORT_CAP,'보고서 크기 한도 초과')
    io=BoundedJSONIO({'input_caps':{r:REPORT_CAP for r in ['source','readiness','saved_plan','candidate']},'output_caps':{'plan':OUTPUT_CAP,'candidate':OUTPUT_CAP},'max_depth':32})
    report,pin=io.read(logical,'source',expected_report_sha256)
    manifests=report.get('input_manifests') if type(report) is dict else None
    _need(type(manifests) is list and len(manifests)==1 and type(manifests[0]) is dict and _lexical_identity_path(manifests[0].get('path'),str(root)) is not None,'보고서 manifest 참조 형식이 잘못됐습니다.')
    result=build_bare_class_requirements(report,{'path':str(target),'sha256':pin});io.verify();_need(logical_root.resolve()==root,'DATA root changed')
    result['pin_validation']='PINNED_REPORT_BYTES_AND_STABILITY_VERIFIED'
    return result
