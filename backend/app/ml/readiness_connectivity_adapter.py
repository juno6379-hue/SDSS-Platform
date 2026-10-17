"""Optional bounded connectivity observation of all appended assess scenes.

No extra IO and no gate mutation. The strict witness interface is reused for all
appended scenes, including zero eligible-patch scenes, rather than a filtered set.
"""
import math
from ..data.readiness_connectivity_witness import diagnose_readiness_connectivity, FIXED_PROVINCE_SPLITS, PROVINCES, CAPS

DEFAULT_LIMITS={'max_scenes':2000,'max_bbox_pairs':1000000,'max_witness_edges':10000}


def failure_capture(code='FAILED_DIAGNOSTIC',error_type=None):
    result={'schema_version':1,'status':'BLOCKED','capture_status':code,'scope':'ALL_APPENDED_ASSESS_SCENES_INCLUDING_ZERO_PATCH',
      'eligibility_recomputed':False,'eligible_patch_count_is_scene_count':False,'historical_readiness_cause_reconstructed':False,
      'ready_for_training':False,'scientific_accuracy_validated':False,'training_executed':False,'gate_result_modified':False,
      'settlement_authorized':False,'execution_authorized':False,'automatic_resume_allowed':False,'proposed_refund_bytes':0,
      'source_files_read':0,'source_files_written':0,'network_requests':0,'provenance_verified':False,'executing_code_verified':False,
      'scene_count':None,'scene_mapping':None,'manifest_input_references':None,'manifest_reference_claim':'ALREADY_COMPUTED_ASSESS_INPUTS_NO_ADDITIONAL_VERIFICATION',
      'gate_components_match':None,'witness':None,'limits':dict(DEFAULT_LIMITS)}
    if error_type is not None:result['error_type']=error_type
    return result


def _token(value,*,group=False):
    if type(value) not in (str,int,float,bool,type(None)):raise ValueError('Unsupported token type')
    if type(value) is float and not math.isfinite(value):raise ValueError('Non-finite token')
    # Readiness checks group truthiness BEFORE str, but always str(scene_id).
    text='' if group and not value else str(value)
    if len(text)>4096:raise ValueError('Token length unsupported')
    return text


def _identity_field(scene,key):
    if key not in scene:return None,'ABSENT'
    value=scene[key]
    if value is None:return None,'NULL_DECLARATION'
    if type(value) is not str:return None,'INVALID_TYPE'
    if key=='image_sha256':
        if len(value)!=64:return None,'INVALID_LENGTH'
        if any(char not in '0123456789abcdef' for char in value):return None,'INVALID_SHA256_FORMAT'
    else:
        if len(value)>4096:return None,'TOO_LONG'
        if not value or not value.strip():return None,'EMPTY_DECLARATION'
        if any(ord(char)<32 or ord(char)==127 for char in value):return None,'INVALID_CONTROL_CHARACTER'
        try:value.encode('utf-8')
        except UnicodeError:return None,'INVALID_UNICODE'
    return value,'DECLARED_NOT_FILE_VERIFIED'


def _source_identity_metadata(scenes):
    # Already-bounded assess metadata only. No path parsing/resolution or hash IO.
    identities=[];complete=0;legacy=0
    for index,scene in enumerate(scenes):
        path,path_status=_identity_field(scene,'image_path');digest,hash_status=_identity_field(scene,'image_sha256')
        if path_status==hash_status=='ABSENT':status='UNKNOWN_NOT_PROVIDED';legacy+=1
        elif path_status==hash_status=='DECLARED_NOT_FILE_VERIFIED':status='DECLARED_PATH_AND_SHA256';complete+=1
        elif 'ABSENT' in (path_status,hash_status):status='PARTIAL_DECLARATION'
        else:status='INVALID_DECLARATION'
        identities.append({'scene_index':index,'eligible_position':index,'identity_status':status,
          'image_path_declared':path,'image_path_status':path_status,'image_sha256_declared':digest,'image_sha256_status':hash_status})
    return {'identity_schema_version':1,'identity_capture_status':'DECLARED_METADATA_CAPTURED',
      'identity_claim':'ALREADY_COMPUTED_ASSESS_METADATA_NOT_FILE_AUTHENTICATION',
      'coverage_status':'NO_SCENES' if not scenes else 'COMPLETE_DECLARED_METADATA' if complete==len(scenes) else 'UNKNOWN_NOT_PROVIDED' if legacy==len(scenes) else 'PARTIAL_OR_INVALID_DECLARED_METADATA',
      'scene_count':len(scenes),'complete_declared_scene_count':complete,'unknown_not_provided_scene_count':legacy,
      'partial_or_invalid_scene_count':len(scenes)-complete-legacy,'scene_identities':identities,
      'path_normalized_or_resolved':False,'source_files_read_or_hashed':False,'source_authenticity_verified':False,
      'exact_original_row_binding_verified':False,'ready_for_training':False,'scientific_accuracy_validated':False}


def capture_readiness_connectivity(scenes,policy,province_groups,manifest_inputs,*,limits=None):
    """Observe a completed gate's metadata without modifying the gate or its data."""
    result=failure_capture()
    try:
        selected=dict(DEFAULT_LIMITS) if limits is None else limits
        if type(selected) is not dict or set(selected)!=set(DEFAULT_LIMITS):raise ValueError('Unsupported diagnostic limits')
        for key,value in selected.items():
            if type(value) is not int or not (0 if key=='max_witness_edges' else 1)<=value<=CAPS[key]:raise ValueError('Unsupported diagnostic limits')
        result['limits']=dict(selected)
        if type(policy) is not dict or type(policy.get('required_provinces')) is not list or policy['required_provinces']!=list(PROVINCES) or policy.get('province_splits')!=FIXED_PROVINCE_SPLITS:
            result['capture_status']='NOT_CAPTURED_UNSUPPORTED_POLICY';return result
        if type(scenes) is not list:raise ValueError('Unsupported scene collection')
        result['scene_count']=len(scenes)
        if len(scenes)>selected['max_scenes'] or len(scenes)*(len(scenes)-1)//2>selected['max_bbox_pairs']:
            result['capture_status']='NOT_CAPTURED_BUDGET';return result
        projected=[];mapping=[]
        for index,scene in enumerate(scenes):
            if type(scene) is not dict or type(scene.get('province')) is not str or scene['province'] not in FIXED_PROVINCE_SPLITS:raise ValueError('Unsupported scene province')
            count=scene.get('eligible_patches')
            if type(count) is not int or not 0<=count<=2**63-1:raise ValueError('Unsupported patch count')
            bbox=scene.get('bounds_wgs84')
            if type(bbox) not in (list,tuple) or len(bbox)!=4:raise ValueError('Unsupported bounds')
            group=scene['source_group'];identifier=scene['scene_id']
            projected.append({'scene_index':index,'province':scene['province'],'source_group':_token(group,group=True),'scene_id':_token(identifier),'bounds_wgs84':list(bbox)})
            mapping.append({'scene_index':index,'eligible_position':index,'province':scene['province'],'eligible_patches':count,
              'included_despite_zero_eligible_patches':count==0,'source_group_original_type':type(group).__name__,
              'scene_id_original_type':type(identifier).__name__,'token_coercion':'READINESS_TRUTHINESS_AND_STR_SCALARS'})
        refs=[]
        if type(manifest_inputs) is not list or len(manifest_inputs)>128:raise ValueError('Unsupported input references')
        for ref in manifest_inputs:
            if type(ref) is not dict or set(ref)!={'path','sha256'} or type(ref['path']) is not str or not ref['path'] or len(ref['path'])>4096 or type(ref['sha256']) is not str or len(ref['sha256'])!=64 or any(c not in '0123456789abcdef' for c in ref['sha256']):raise ValueError('Unsupported manifest reference')
            refs.append({'path':ref['path'],'sha256':ref['sha256']})
        result['scene_mapping']=mapping;result['manifest_input_references']=refs
        try:witness=diagnose_readiness_connectivity(projected,dict(policy['province_splits']),**selected)
        except ValueError:
            result['capture_status']='NOT_CAPTURED_UNSUPPORTED_METADATA';return result
        result['witness']=witness
        result['helper_input_role']='STRICT_METADATA_INTERFACE_USED_FOR_ALL_APPENDED_SCENES_NOT_ELIGIBLE_PATCH_SUBSET'
        result['projected_scene_metadata']=projected
        result['supplied_eligible_patch_sum']=sum(row['eligible_patches'] for row in mapping)
        matched=type(province_groups) is dict and len(province_groups)==6 and all(type(k) is str and type(v) is str for k,v in province_groups.items()) and province_groups==witness['province_components']
        result['gate_components_match']=matched
        result['capture_status']='CAPTURED_COMPONENTS_MATCH' if matched else 'CAPTURED_COMPONENT_MISMATCH'
        try:
            result['source_identity']=_source_identity_metadata(scenes)
        except Exception as exc:
            result['source_identity']={'identity_schema_version':1,'identity_capture_status':'NOT_CAPTURED_ERROR',
                'error_type':type(exc).__name__,'scene_count':len(scenes),'scene_identities':None,
                'source_files_read_or_hashed':False,'source_authenticity_verified':False,'exact_original_row_binding_verified':False,
                'ready_for_training':False,'scientific_accuracy_validated':False}
        return result
    except (ValueError,TypeError,KeyError,OverflowError) as exc:
        result['capture_status']='NOT_CAPTURED_UNSUPPORTED_METADATA';result['error_type']=type(exc).__name__;return result
    except Exception as exc:
        result['capture_status']='FAILED_DIAGNOSTIC';result['error_type']=type(exc).__name__;return result
