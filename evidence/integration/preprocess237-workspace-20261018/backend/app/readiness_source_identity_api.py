"""Explicit read-only API projection of two pinned stored diagnostic JSON files."""
import hashlib
import threading
from fastapi import APIRouter,Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from .data.readiness_connectivity_lineage import inspect_readiness_connectivity_lineage
from .data.recovery_boundary import _read_bounded,_decode,_check_depth
from .data.recovery_raster_content import _file_stamp,_sha_valid
from .data.recovery_terminal import _confined

BODY_BYTES=8192
REPORT_BYTES=16*1024*1024
REPORT_RELATIVE='first-group/readiness-source-identity-20261017.json'
MANIFEST_RELATIVE='first-group-training-esri-v1/annual-window-report.json'
COUNT_FIELDS={'scene_count','complete_identity_scene_count','saved_blocker_count','query_member_count','query_active_token_member_count','query_zero_patch_scene_count','query_eligible_patch_count','broad_candidate_link_count','broad_unique_raw_row_count','refined_candidate_link_count','refined_unique_raw_row_count','refined_unique_member_count'}
FALSE_FIELDS={'ready_for_training','scientific_accuracy_validated','source_authenticity_verified','exact_row_binding_verified','execution_authorized','settlement_authorized','automatic_resume_allowed','training_split_leakage_resolved'}
REQUEST_SCHEMA={'type':'object','additionalProperties':False,'required':['report_sha256','manifest_sha256','token'],'properties':{'report_sha256':{'type':'string','pattern':'^[0-9a-f]{64}$'},'manifest_sha256':{'type':'string','pattern':'^[0-9a-f]{64}$'},'token':{'type':'string','maxLength':4096}}}


# This exact, path-free schema is also the frontend transport contract.
_NULLABLE_COUNTS={'complete_identity_scene_count','refined_candidate_link_count','refined_unique_raw_row_count','refined_unique_member_count'}
_COUNT_CAPS={k:(10000 if k=='saved_blocker_count' else 9007199254740991 if k=='query_eligible_patch_count' else 200000000 if 'link_count' in k else 100000 if 'raw_row_count' in k else 2000) for k in COUNT_FIELDS}
RESPONSE_SCHEMA={'type':'object','additionalProperties':False,
 'required':['schema_version','status','diagnostic_status','scope','report_sha256','manifest_sha256','query_token_sha256','counts','output_truncated',*sorted(FALSE_FIELDS)],
 'properties':{'schema_version':{'type':'integer','const':1},'status':{'const':'BLOCKED'},
  'diagnostic_status':{'enum':['OBSERVED_DECLARATIONS','SOURCE_IDENTITY_NOT_PROVIDED','SOURCE_IDENTITY_NOT_CAPTURED']},
  'scope':{'const':'PINNED_STORED_REPORT_DECLARATIONS_ONLY'},
  **{k:{'type':'string','pattern':'^[0-9a-f]{64}$'} for k in ['report_sha256','manifest_sha256','query_token_sha256']},
  'counts':{'type':'object','additionalProperties':False,'required':sorted(COUNT_FIELDS),'properties':{k:{'type':['integer','null'] if k in _NULLABLE_COUNTS else 'integer','minimum':0,'maximum':_COUNT_CAPS[k]} for k in COUNT_FIELDS}},
  'output_truncated':{'type':'boolean'},**{k:{'type':'boolean','const':False} for k in FALSE_FIELDS}}}
ERROR_SCHEMA={'type':'object','additionalProperties':False,'required':['error'],'properties':{'error':{'type':'object','additionalProperties':False,'required':['code','message','retryable'],'properties':{'code':{'enum':['INVALID_REQUEST','REQUEST_TOO_LARGE','PINNED_INPUT_CONFLICT','RESOURCE_UNAVAILABLE','DIAGNOSTIC_BUSY']},'message':{'type':'string'},'retryable':{'type':'boolean'}}}}}


def _require(value):
    if not value:raise ValueError('Diagnostic projection contract invalid')


def _uint(value):return type(value) is int and value>=0


def _request(raw):
    _check_depth(raw,8);value=_decode(raw)
    _require(type(value) is dict and set(value)=={'report_sha256','manifest_sha256','token'})
    _require(_sha_valid(value['report_sha256']) and _sha_valid(value['manifest_sha256']) and type(value['token']) is str and len(value['token'])<=4096)
    value['token'].encode('utf-8')
    return value


def _stored_metadata(root,pin):
    logical=root/REPORT_RELATIVE;target=_confined(root,logical);stamp=_file_stamp(target)
    _require(stamp['exists'] and stamp['bytes']<=REPORT_BYTES)
    raw=_read_bounded(target,stamp,REPORT_BYTES,32)
    if hashlib.sha256(raw).hexdigest()!=pin:raise ValueError('Pinned JSON SHA mismatch')
    report=_decode(raw);_require(type(report) is dict)
    blockers=report.get('blockers');_require(type(blockers) is list and len(blockers)<=10000 and all(type(b) is dict and type(b.get('code')) is str and 0<len(b['code'])<=128 for b in blockers))
    capture=report.get('connectivity_diagnostics');_require(type(capture) is dict)
    if 'source_identity' not in capture:state='SOURCE_IDENTITY_NOT_PROVIDED';complete=None
    else:
        identity=capture['source_identity'];_require(type(identity) is dict and type(identity.get('identity_schema_version')) is int and identity['identity_schema_version']==1)
        if identity.get('identity_capture_status')=='NOT_CAPTURED_ERROR':state='SOURCE_IDENTITY_NOT_CAPTURED';complete=None
        else:
            _require(identity.get('identity_capture_status')=='DECLARED_METADATA_CAPTURED' and _uint(identity.get('complete_declared_scene_count')))
            state='OBSERVED_DECLARATIONS';complete=identity['complete_declared_scene_count']
    _require(_file_stamp(target)==stamp and _confined(root,logical)==target)
    return {'state':state,'complete':complete,'saved_blocker_count':len(blockers),'report_path':str(target)}


def project_readiness_source_identity(core,metadata,request):
    """Strict allowlist only; paths, token text, scene/member rows never leave API."""
    _require(type(core) is dict and type(core.get('schema_version')) is int and core['schema_version']==1 and core.get('kind')=='PINNED_CURRENT_CONNECTIVITY_TOKEN_LINEAGE' and core.get('mode')=='READ_ONLY' and core.get('status')=='BLOCKED')
    _require(core.get('token')==request['token'] and core.get('query_inferred') is False)
    inputs=core.get('inputs');_require(type(inputs) is dict and set(inputs)=={'report','manifest'} and inputs['report']['sha256']==request['report_sha256'] and inputs['manifest']['sha256']==request['manifest_sha256'] and inputs['report']['path']==metadata['report_path'])
    for key in ['exact_row_binding_verified','raw_row_order_used_as_identity','original_file_or_product_authenticity_verified','executing_code_identity_verified','eligibility_recomputed','historical_readiness_cause_reconstructed','zero_patch_removal_or_blocker_resolution_assessed','assess_called','connectivity_helper_called','source_headers_or_pixels_read','source_content_hashes_revalidated','source_manifests_followed',*FALSE_FIELDS]:
        # source_authenticity_verified is a projection name; core has its longer original-file claim.
        if key=='source_authenticity_verified':continue
        _require(core.get(key) is False)
    _require(type(core.get('source_files_written')) is int and core['source_files_written']==0 and type(core.get('network_requests')) is int and core['network_requests']==0 and type(core.get('proposed_refund_bytes')) is int and core['proposed_refund_bytes']==0)
    scene=core.get('report_scene_count');members=core.get('report_members');query=core.get('report_literal_member_count');active=core.get('report_active_token_member_count');skipped=core.get('report_skipped_literal_member_count')
    _require(_uint(scene) and scene<=2000 and _uint(query) and query<=scene and _uint(active) and _uint(skipped) and active+skipped==query and type(members) is list and len(members)==query)
    seen=set();patches=zero=active_count=0;broad_links=0
    for member in members:
        _require(type(member) is dict and _uint(member.get('scene_index')) and member['scene_index']<scene and member['scene_index'] not in seen and _uint(member.get('eligible_position')) and member['eligible_position']==member['scene_index'] and _uint(member.get('eligible_patches')))
        seen.add(member['scene_index']);patches+=member['eligible_patches'];zero+=member['eligible_patches']==0
        roles=member.get('active_token_roles');_require(type(roles) is list and len(roles)<=2 and len(set(roles))==len(roles) and all(r in ('source_group','scene_id') for r in roles));active_count+=bool(roles)
        _require(_uint(member.get('candidate_count')) and type(member.get('exact_row_binding_verified')) is bool and member['exact_row_binding_verified'] is False)
        broad_links+=member['candidate_count']
    broad=core.get('candidate_link_count_total');raw=core.get('unique_candidate_raw_row_count')
    _require(_uint(broad) and broad==broad_links and _uint(raw) and raw<=broad and active_count==active and type(core.get('output_truncated')) is bool)
    state=metadata.get('state');_require(state in {'OBSERVED_DECLARATIONS','SOURCE_IDENTITY_NOT_PROVIDED','SOURCE_IDENTITY_NOT_CAPTURED'} and _uint(metadata.get('saved_blocker_count')) and metadata['saved_blocker_count']<=10000)
    complete=metadata.get('complete');refined_links=refined_raw=unique_members=None;truncated=core['output_truncated']
    if state=='SOURCE_IDENTITY_NOT_PROVIDED':_require(complete is None and 'source_identity_refinement' not in core)
    else:
        refinement=core.get('source_identity_refinement');_require(type(refinement) is dict and type(refinement.get('identity_schema_version')) is int and refinement['identity_schema_version']==1 and refinement.get('path_comparison_protocol') in {'WINDOWS_CASEFOLD_COMPONENTS','POSIX_CASE_SENSITIVE_COMPONENTS'} and refinement.get('status')=='DECLARED_METADATA_ONLY' and refinement.get('method')=='LEXICAL_DATA_ROOT_PATH_AND_DECLARED_SHA256')
        for key in ['source_files_read_or_hashed','filesystem_path_identity_verified','exact_row_binding_verified','original_file_or_product_authenticity_verified','ready_for_training','scientific_accuracy_validated']:_require(refinement.get(key) is False)
        rows=refinement.get('members');_require(type(rows) is list and len(rows)==query and type(refinement.get('output_truncated')) is bool)
        _require(_uint(refinement.get('candidate_link_count_total')) and refinement['candidate_link_count_total']<=broad and _uint(refinement.get('unique_candidate_raw_row_count')) and refinement['unique_candidate_raw_row_count']<=raw)
        refined_sum=0;unique_count=0
        for source,row in zip(members,rows):
            _require(type(row) is dict and type(row.get('scene_index')) is int and row['scene_index']==source['scene_index'] and type(row.get('eligible_position')) is int and row['eligible_position']==source['eligible_position'] and type(row.get('eligible_patches')) is int and row['eligible_patches']==source['eligible_patches'] and _uint(row.get('refined_candidate_count')) and row['refined_candidate_count']<=source['candidate_count'] and row.get('exact_row_binding_verified') is False)
            refined_sum+=row['refined_candidate_count'];match=row.get('refined_match_status');reason=row.get('refinement_status')
            _require(reason in {'REFINED_DECLARED_METADATA_ONLY','NOT_REFINED_IDENTITY_NOT_CAPTURED','NOT_REFINED_IDENTITY_INCOMPLETE','NOT_REFINED_UNSUPPORTED_LEXICAL_PATH','NOT_REFINED_RAW_METADATA_INCOMPLETE','NOT_REFINED_RAW_DECLARATIONS_INCOMPLETE'})
            _require((reason=='REFINED_DECLARED_METADATA_ONLY')==(match!='UNKNOWN_ORIGINAL_CANDIDATES_PRESERVED'))
            if match=='UNKNOWN_ORIGINAL_CANDIDATES_PRESERVED':_require(row['refined_candidate_count']==source['candidate_count'])
            _require(match in {'NO_DECLARED_METADATA_MATCH','UNIQUE_DECLARED_METADATA_CANDIDATE','AMBIGUOUS_DECLARED_METADATA_MATCH_SET','UNKNOWN_ORIGINAL_CANDIDATES_PRESERVED'})
            if match=='UNIQUE_DECLARED_METADATA_CANDIDATE':_require(row['refined_candidate_count']==1);unique_count+=1
            if match=='NO_DECLARED_METADATA_MATCH':_require(row['refined_candidate_count']==0)
            if match=='AMBIGUOUS_DECLARED_METADATA_MATCH_SET':_require(row['refined_candidate_count']>1)
        _require(refined_sum==refinement['candidate_link_count_total'] and refinement['unique_candidate_raw_row_count']<=refined_sum and unique_count<=refined_sum)
        truncated=truncated or refinement['output_truncated']
        if state=='OBSERVED_DECLARATIONS':
            _require(_uint(complete) and complete<=scene and unique_count<=complete)
            refined_links=refinement['candidate_link_count_total'];refined_raw=refinement['unique_candidate_raw_row_count'];unique_members=unique_count
        else:_require(complete is None and all(r['refined_match_status']=='UNKNOWN_ORIGINAL_CANDIDATES_PRESERVED' for r in rows))
    counts={'scene_count':scene,'complete_identity_scene_count':complete,'saved_blocker_count':metadata['saved_blocker_count'],'query_member_count':query,'query_active_token_member_count':active,'query_zero_patch_scene_count':zero,'query_eligible_patch_count':patches,'broad_candidate_link_count':broad,'broad_unique_raw_row_count':raw,'refined_candidate_link_count':refined_links,'refined_unique_raw_row_count':refined_raw,'refined_unique_member_count':unique_members}
    _require(set(counts)==COUNT_FIELDS and patches<=9007199254740991 and broad<=200000000 and raw<=100000)
    _require(refined_links is None or refined_links<=200000000)
    _require(refined_raw is None or refined_raw<=100000)
    return {'schema_version':1,'status':'BLOCKED','diagnostic_status':state,'scope':'PINNED_STORED_REPORT_DECLARATIONS_ONLY','report_sha256':request['report_sha256'],'manifest_sha256':request['manifest_sha256'],'query_token_sha256':hashlib.sha256(request['token'].encode('utf-8')).hexdigest(),'counts':counts,'output_truncated':truncated,**{key:False for key in sorted(FALSE_FIELDS)}}


def _error(code,status):
    messages={'INVALID_REQUEST':'Invalid diagnostic request.','REQUEST_TOO_LARGE':'Diagnostic request exceeds body limit.','PINNED_INPUT_CONFLICT':'Pinned diagnostic inputs changed or do not match.','RESOURCE_UNAVAILABLE':'Stored diagnostic is unavailable.','DIAGNOSTIC_BUSY':'A diagnostic inspection is already running.'}
    headers={'Cache-Control':'no-store'}
    if status==429:headers['Retry-After']='1'
    return JSONResponse({'error':{'code':code,'message':messages[code],'retryable':status==429}},status_code=status,headers=headers)


def create_readiness_source_identity_router(get_store):
    router=APIRouter();gate=threading.BoundedSemaphore(1)
    @router.post('/v1/diagnostics/readiness-source-identity',responses={200:{'content':{'application/json':{'schema':RESPONSE_SCHEMA}}},**{code:{'description':'Safe diagnostic error','content':{'application/json':{'schema':ERROR_SCHEMA}}} for code in [400,409,413,429,503]}},openapi_extra={'requestBody':{'required':True,'content':{'application/json':{'schema':REQUEST_SCHEMA}}}})
    async def inspect(request:Request):
        body=bytearray()
        try:
            async for chunk in request.stream():
                if len(body)+len(chunk)>BODY_BYTES:return _error('REQUEST_TOO_LARGE',413)
                body.extend(chunk)
            payload=_request(bytes(body))
        except Exception:return _error('INVALID_REQUEST',400)
        def worker():
            if not gate.acquire(blocking=False):return None
            try:
                root=get_store().root
                core=inspect_readiness_connectivity_lineage(root,payload['report_sha256'],payload['manifest_sha256'],payload['token'],max_candidates=1000,max_members=2000,report_path=root/REPORT_RELATIVE)
                metadata=_stored_metadata(root,payload['report_sha256'])
                return project_readiness_source_identity(core,metadata,payload)
            finally:gate.release()
        try:result=await run_in_threadpool(worker)
        except ValueError as exc:
            # Classification only; never return exception text, paths, or raw JSON.
            if any(marker in str(exc) for marker in ['SHA mismatch','changed','retargeted']):return _error('PINNED_INPUT_CONFLICT',409)
            return _error('RESOURCE_UNAVAILABLE',503)
        except Exception:return _error('RESOURCE_UNAVAILABLE',503)
        if result is None:return _error('DIAGNOSTIC_BUSY',429)
        return JSONResponse(result,headers={'Cache-Control':'no-store'})
    return router
