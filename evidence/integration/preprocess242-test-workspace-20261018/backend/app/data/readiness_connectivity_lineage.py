"""Two pinned JSON membership/candidate traces; never exact row or source truth."""
from collections import Counter,defaultdict
import hashlib
import math
from pathlib import Path,PureWindowsPath,PurePosixPath
import re
from .recovery_boundary import _read_bounded,_decode
from .recovery_raster_content import _file_stamp,_sha_valid
from .recovery_terminal import _confined
from .readiness_connectivity_witness import PROVINCES,FIXED_PROVINCE_SPLITS,CAPS
from ..ml.readiness_connectivity_adapter import _token

PROJECT_ROOT=Path(__file__).resolve().parents[3]
MANIFEST_BYTES=64*1024*1024
REPORT_BYTES=16*1024*1024
ROW_CAP=100000
SCENE_CAP=2000
STRING_CAP=4096


def _same(a,b):
    if type(a) is not type(b):return False
    if type(a) is dict:return a.keys()==b.keys() and all(_same(a[k],b[k]) for k in a)
    if type(a) is list:return len(a)==len(b) and all(_same(x,y) for x,y in zip(a,b))
    return a==b


def _uint(value):return type(value) is int and value>=0


def _number(value):
    if type(value) not in (int,float):return False
    try:return math.isfinite(value)
    except (OverflowError,ValueError):return False


def _string(value):return type(value) is str and len(value)<=STRING_CAP


def _require(condition,message):
    if not condition:raise ValueError(message)


def _roles(group,identifier,token):
    literal=[role for role,value in [('source_group',group),('scene_id',identifier)] if value==token]
    return literal,literal if group else []


def _declared_candidate(index,row):
    path=row.get('image_path');hashes=row.get('patch_sha256');digest=hashes.get('image') if type(hashes) is dict else None
    return {'manifest_row_index':index,'image_path_declared':path if _string(path) else None,
      'image_path_status':'DECLARED_NOT_FILE_VERIFIED' if _string(path) and path else 'MISSING_OR_INVALID',
      'declared_patch_image_sha256':digest if _sha_valid(digest) else None,
      'declared_patch_image_sha256_status':'DECLARED_NOT_FILE_VERIFIED' if _sha_valid(digest) else 'MISSING_OR_INVALID',
      'source_file_read_or_hashed':False,'exact_current_scene_row_binding_verified':False}


def _lexical_identity_path(value,root):
    """No filesystem calls: lexical component key only, or None when unsupported."""
    if not _string(value) or not value or any(ord(c)<32 or ord(c)==127 for c in value):return None
    try:value.encode('utf-8')
    except UnicodeError:return None
    if value.startswith(('\\\\','//')) or value.endswith(('\\','/')) or any(c in '<>\"|?*' for c in value):return None
    windows_root=bool(re.match(r'^[A-Za-z]:[\\/]',str(root)))
    drive=re.match(r'^[A-Za-z]:[\\/]',value)
    if re.match(r'^[A-Za-z][A-Za-z0-9+.-]*:',value) and not drive:return None
    if ':' in (value[2:] if drive else value):return None
    pieces=re.split(r'[\\/]',value)
    if any(piece in ('.','..') for piece in pieces):return None
    devices={'CON','PRN','AUX','NUL','CONIN$','CONOUT$'}|{prefix+n for prefix in ('COM','LPT') for n in '123456789¹²³'}
    if any(piece and not re.fullmatch('[A-Za-z]:',piece) and (piece.rstrip(' .')!=piece or piece.split('.')[0].strip(' .').upper() in devices) for piece in pieces):return None
    if windows_root:
        base=PureWindowsPath(str(root));path=PureWindowsPath(value)
        if path.root and not path.drive:return None
        if path.drive and not path.is_absolute():return None
        if path.is_absolute():
            try:relative=path.relative_to(base)
            except ValueError:return None
        else:relative=path
        return tuple(part.casefold() for part in relative.parts) if relative.parts else None
    if drive or '\\' in value:return None
    base=PurePosixPath(str(root));path=PurePosixPath(value)
    if not base.is_absolute():return None
    if path.is_absolute():
        try:relative=path.relative_to(base)
        except ValueError:return None
    else:relative=path
    return tuple(relative.parts) if relative.parts else None


def _validate_source_identity(capture,count):
    identity=capture['source_identity']
    _require(type(identity) is dict and _same(identity.get('identity_schema_version'),1),'Unsupported source identity version')
    common_false={'source_files_read_or_hashed','source_authenticity_verified','exact_original_row_binding_verified','ready_for_training','scientific_accuracy_validated'}
    for key in common_false:_require(identity.get(key) is False,'Invalid identity false flag: '+key)
    _require(_same(identity.get('scene_count'),count),'Identity scene count mismatch')
    if identity.get('identity_capture_status')=='NOT_CAPTURED_ERROR':
        _require(set(identity)=={'identity_schema_version','identity_capture_status','error_type','scene_count','scene_identities'}|common_false and identity['scene_identities'] is None and type(identity.get('error_type')) is str and 0<len(identity['error_type'])<=128,'Malformed uncaptured identity')
        return None
    keys={'identity_schema_version','identity_capture_status','identity_claim','coverage_status','scene_count','complete_declared_scene_count','unknown_not_provided_scene_count','partial_or_invalid_scene_count','scene_identities','path_normalized_or_resolved'}|common_false
    _require(set(identity)==keys and identity.get('identity_capture_status')=='DECLARED_METADATA_CAPTURED' and identity.get('identity_claim')=='ALREADY_COMPUTED_ASSESS_METADATA_NOT_FILE_AUTHENTICATION' and identity.get('path_normalized_or_resolved') is False,'Malformed identity capture contract')
    records=identity.get('scene_identities');_require(type(records) is list and len(records)==count,'Identity records count mismatch')
    complete=legacy=0
    path_states={'ABSENT','NULL_DECLARATION','INVALID_TYPE','TOO_LONG','EMPTY_DECLARATION','INVALID_CONTROL_CHARACTER','INVALID_UNICODE'}
    hash_states={'ABSENT','NULL_DECLARATION','INVALID_TYPE','INVALID_LENGTH','INVALID_SHA256_FORMAT'}
    for index,record in enumerate(records):
        _require(type(record) is dict and set(record)=={'scene_index','eligible_position','identity_status','image_path_declared','image_path_status','image_sha256_declared','image_sha256_status'} and _same(record.get('scene_index'),index) and _same(record.get('eligible_position'),index),'Identity index/order/schema invalid')
        ps=record['image_path_status'];hs=record['image_sha256_status'];path=record['image_path_declared'];digest=record['image_sha256_declared']
        _require(type(ps) is str and type(hs) is str,'Identity field states require strings')
        if ps=='DECLARED_NOT_FILE_VERIFIED':
            _require(_string(path) and bool(path.strip()) and not any(ord(c)<32 or ord(c)==127 for c in path),'Invalid declared identity path scalar')
            try:path.encode('utf-8')
            except UnicodeError as exc:raise ValueError('Invalid identity path Unicode') from exc
        else:_require(ps in path_states and path is None,'Malformed unknown/invalid identity path')
        if hs=='DECLARED_NOT_FILE_VERIFIED':_require(_sha_valid(digest),'Invalid declared identity SHA')
        else:_require(hs in hash_states and digest is None,'Malformed unknown/invalid identity SHA')
        if ps==hs=='ABSENT':expected='UNKNOWN_NOT_PROVIDED';legacy+=1
        elif ps==hs=='DECLARED_NOT_FILE_VERIFIED':expected='DECLARED_PATH_AND_SHA256';complete+=1
        elif 'ABSENT' in (ps,hs):expected='PARTIAL_DECLARATION'
        else:expected='INVALID_DECLARATION'
        _require(record['identity_status']==expected,'Identity state/value combination mismatch')
    coverage='NO_SCENES' if not count else 'COMPLETE_DECLARED_METADATA' if complete==count else 'UNKNOWN_NOT_PROVIDED' if legacy==count else 'PARTIAL_OR_INVALID_DECLARED_METADATA'
    _require(_same(identity.get('complete_declared_scene_count'),complete) and _same(identity.get('unknown_not_provided_scene_count'),legacy) and _same(identity.get('partial_or_invalid_scene_count'),count-complete-legacy) and identity.get('coverage_status')==coverage,'Identity coverage/count mismatch')
    return records


def _refine_identity_members(members,identities,raw_index,raw_rows,root,max_members,max_candidates,raw_complete):
    caches={};result=[];total=0;status_counts=Counter();budget=max_candidates;details=[];detail_set=set();all_base=set();matched_pairs=set()
    for member in members:
        base=(member['province'],member['normalized_source_group'],member['normalized_scene_id']);original=raw_index.get(base,[]);record=identities[member['scene_index']] if identities is not None else None
        reason='NOT_REFINED_IDENTITY_NOT_CAPTURED' if record is None else 'NOT_REFINED_IDENTITY_INCOMPLETE'
        candidates=original;refined=False;pair=None
        if record is not None and record['identity_status']=='DECLARED_PATH_AND_SHA256':
            pathkey=_lexical_identity_path(record['image_path_declared'],root)
            if not raw_complete:reason='NOT_REFINED_RAW_METADATA_INCOMPLETE'
            elif pathkey is None:reason='NOT_REFINED_UNSUPPORTED_LEXICAL_PATH'
            else:
                if base not in caches:
                    index=defaultdict(list);comparable=True
                    for raw_index_value in original:
                        raw=raw_rows[raw_index_value];rawkey=_lexical_identity_path(raw.get('image_path'),root);hashes=raw.get('patch_sha256');digest=hashes.get('image') if type(hashes) is dict else None
                        if rawkey is None or not _sha_valid(digest):comparable=False;continue
                        index[(rawkey,digest)].append(raw_index_value)
                    caches[base]=(index,comparable)
                index,comparable=caches[base]
                if not comparable:reason='NOT_REFINED_RAW_DECLARATIONS_INCOMPLETE'
                else:
                    pair=(pathkey,record['image_sha256_declared']);candidates=index.get(pair,[]);refined=True;reason='REFINED_DECLARED_METADATA_ONLY'
        total+=len(candidates);status_counts[reason]+=1
        if refined:matched_pairs.add((base,pair))
        else:all_base.add(base)
        if len(result)<max_members:
            links=candidates[:budget];budget-=len(links)
            for i in links:
                if i not in detail_set:detail_set.add(i);details.append(i)
            result.append({'scene_index':member['scene_index'],'eligible_position':member['eligible_position'],'eligible_patches':member['eligible_patches'],'refinement_status':reason,'original_candidate_count':len(original),'refined_candidate_count':len(candidates),
              'refined_match_status':('NO_DECLARED_METADATA_MATCH' if not candidates else 'UNIQUE_DECLARED_METADATA_CANDIDATE' if len(candidates)==1 else 'AMBIGUOUS_DECLARED_METADATA_MATCH_SET') if refined else 'UNKNOWN_ORIGINAL_CANDIDATES_PRESERVED',
              'candidate_row_indices':links,'candidate_links_truncated':len(links)<len(candidates),'exact_row_binding_verified':False})
    unique=sum(len(raw_index.get(base,[])) for base in all_base)
    unique+=sum(len(caches[base][0].get(pair,[])) for base,pair in matched_pairs if base not in all_base)
    return {'identity_schema_version':1,'status':'DECLARED_METADATA_ONLY','method':'LEXICAL_DATA_ROOT_PATH_AND_DECLARED_SHA256','path_comparison_protocol':'WINDOWS_CASEFOLD_COMPONENTS' if re.match(r'^[A-Za-z]:[\\/]',str(root)) else 'POSIX_CASE_SENSITIVE_COMPONENTS',
      'status_counts_all_report_literal_members':dict(status_counts),'candidate_link_count_total':total,'unique_candidate_raw_row_count':unique,'candidate_link_count_stored':sum(len(m['candidate_row_indices']) for m in result),'members':result,
      'candidate_rows':[_declared_candidate(i,raw_rows[i]) for i in details],'output_truncated':len(result)<len(members) or any(m['candidate_links_truncated'] for m in result),
      'source_files_read_or_hashed':False,'filesystem_path_identity_verified':False,'exact_row_binding_verified':False,'original_file_or_product_authenticity_verified':False,'ready_for_training':False,'scientific_accuracy_validated':False}


def inspect_readiness_connectivity_lineage(data_root,expected_report_sha256,expected_manifest_sha256,token,*,report_path=None,max_candidates=1000,max_members=2000):
    _require(_string(token),'Explicit literal token string of at most 4096 characters required')
    _require(_sha_valid(expected_report_sha256) and _sha_valid(expected_manifest_sha256),'Explicit lowercase report/manifest SHA pins required')
    _require(type(max_candidates) is int and 1<=max_candidates<=10000,'Candidate output cap must be integer 1..10000')
    _require(type(max_members) is int and 1<=max_members<=SCENE_CAP,'Member output cap must be integer 1..2000')
    requested=Path(data_root)
    _require(not str(requested).startswith(('\\\\','//')),'Local DATA root required')
    root=requested.resolve();targets={};inputs=[]
    def resolve(value):
        target=_confined(root,value);logical=Path(value);logical=logical if logical.is_absolute() else root/logical
        if logical in targets and targets[logical]!=target:raise ValueError('Logical JSON target changed')
        targets[logical]=target;return target
    manifest_path=resolve(root/'first-group-training-esri-v1/annual-window-report.json')
    fresh_path=resolve(report_path or root/'first-group/readiness-connectivity-20261017.json')
    _require(fresh_path!=manifest_path,'Two distinct JSON inputs required')
    plans=[(manifest_path,expected_manifest_sha256,MANIFEST_BYTES),(fresh_path,expected_report_sha256,REPORT_BYTES)]
    for path,pin,maximum in plans:
        stamp=_file_stamp(path)
        _require(stamp['exists'] and stamp['bytes']<=maximum,'Pinned JSON missing or exceeds byte cap')
        inputs.append((path,stamp,pin,maximum))
    documents=[]
    for path,stamp,pin,maximum in inputs:
        raw=_read_bounded(path,stamp,maximum,32)
        _require(hashlib.sha256(raw).hexdigest()==pin,'Pinned JSON SHA mismatch')
        value=_decode(raw);_require(type(value) is dict,'JSON document requires object');documents.append(value)
    manifest,fresh=documents
    raw_rows=manifest.get('scenes');_require(type(raw_rows) is list and len(raw_rows)<=ROW_CAP,'Bounded manifest scenes required')
    _require(_same(fresh.get('schema_version'),1) and fresh.get('status')=='blocked' and fresh.get('ready_for_training') is False and fresh.get('scientific_accuracy_validated') is False,'Unsupported report schema or gate state')
    policy=fresh.get('policy');_require(type(policy) is dict and _same(policy.get('required_provinces'),list(PROVINCES)) and _same(policy.get('province_splits'),FIXED_PROVINCE_SPLITS),'Unsupported fixed policy')
    _require(_same(fresh.get('group_splits'),FIXED_PROVINCE_SPLITS),'Report split mapping mismatch')
    refs=fresh.get('input_manifests');_require(type(refs) is list and len(refs)==1 and type(refs[0]) is dict and set(refs[0])=={'path','sha256'} and _string(refs[0]['path']) and refs[0]['sha256']==expected_manifest_sha256,'Report single-manifest binding invalid')
    _require(resolve(refs[0]['path'])==manifest_path,'Report manifest path retargeted')
    capture=fresh.get('connectivity_diagnostics');_require(type(capture) is dict and _same(capture.get('schema_version'),1) and capture.get('status')=='BLOCKED' and capture.get('capture_status')=='CAPTURED_COMPONENTS_MATCH' and capture.get('scope')=='ALL_APPENDED_ASSESS_SCENES_INCLUDING_ZERO_PATCH' and capture.get('gate_components_match') is True,'Report connectivity not captured/complete/matching')
    _require(_same(capture.get('manifest_input_references'),refs),'Capture input references mismatch')
    for field in ['eligibility_recomputed','eligible_patch_count_is_scene_count','historical_readiness_cause_reconstructed','ready_for_training','scientific_accuracy_validated','training_executed','gate_result_modified','settlement_authorized','execution_authorized','automatic_resume_allowed','provenance_verified','executing_code_verified']:
        _require(capture.get(field) is False,'Unsupported capture flag: '+field)
    rows=capture.get('projected_scene_metadata');mapping=capture.get('scene_mapping');count=capture.get('scene_count')
    _require(_uint(count) and count<=SCENE_CAP and type(rows) is list and type(mapping) is list and len(rows)==len(mapping)==count,'Projected scene/mapping count invalid')
    witness=capture.get('witness');_require(type(witness) is dict and _same(witness.get('schema_version'),1) and witness.get('kind')=='PROSPECTIVE_ELIGIBLE_METADATA_CONNECTIVITY_WITNESS' and witness.get('status')=='BLOCKED' and witness.get('union_complete') is True and _same(witness.get('scene_count'),count),'Witness schema/scope/count invalid')
    groups=fresh.get('province_groups');_require(type(groups) is dict and set(groups)==set(PROVINCES) and all(type(v) is str and v in PROVINCES for v in groups.values()) and _same(witness.get('province_components'),groups) and _same(witness.get('fixed_province_splits'),FIXED_PROVINCE_SPLITS),'Component/policy metadata mismatch')
    limits=capture.get('limits')
    _require(type(limits) is dict and set(limits)==set(CAPS) and all(type(v) is int and (0 if k=='max_witness_edges' else 1)<=v<=CAPS[k] for k,v in limits.items()) and _same(witness.get('limits'),limits),'Capture/witness typed limits mismatch')
    _require(count<=limits['max_scenes'] and count*(count-1)//2<=limits['max_bbox_pairs'],'Scene/pair count exceeds declared capture budget')
    for doc in (capture,witness):
        for key in ['ready_for_training','scientific_accuracy_validated','training_executed','historical_readiness_cause_reconstructed','settlement_authorized','execution_authorized','automatic_resume_allowed']:
            _require(doc.get(key) is False,'Unsupported diagnostic authorization flag: '+key)
        for key in ['proposed_refund_bytes','source_files_read','source_files_written','network_requests']:
            _require(_same(doc.get(key),0),'Unsupported diagnostic IO/refund count: '+key)
    for key in ['eligibility_verified','pixel_arrays_read','geometry_engine_called','readiness_assess_called','training_split_leakage_resolved','complete_spatial_separation_claimed','fixed_split_assignments_changed']:
        _require(witness.get(key) is False,'Unsupported witness claim: '+key)
    _require(witness.get('mode')=='PURE_DIAGNOSTIC' and witness.get('exactly_once_applied')=='UNKNOWN' and _uint(witness.get('union_change_count')) and witness['union_change_count']<=5,'Witness mode/union count invalid')
    _require(_same(witness.get('bbox_pair_plan_count'),count*(count-1)//2) and _same(witness.get('bbox_pairs_evaluated'),count*(count-1)//2),'Pair accounting invalid')
    stored=witness.get('witness_edges');total=witness.get('witness_edge_count_total');stored_count=witness.get('witness_edge_count_stored');kinds=witness.get('witness_edge_counts_by_kind')
    _require(type(stored) is list and _uint(stored_count) and stored_count==len(stored)<=10000 and _uint(total) and total>=stored_count and type(kinds) is dict and set(kinds)=={'TOKEN_SHARED_NAMESPACE','BBOX_STRICT_POSITIVE_OVERLAP'} and all(_uint(v) for v in kinds.values()) and sum(kinds.values())==total,'Witness counters invalid')
    _require(stored_count==min(total,limits['max_witness_edges']) and kinds['TOKEN_SHARED_NAMESPACE']<=2*count and kinds['BBOX_STRICT_POSITIVE_OVERLAP']<=count*(count-1)//2,'Witness event/storage count exceeds budget')
    truncated=total>stored_count
    _require(witness.get('witness_edges_truncated') is truncated and witness.get('witness_edge_coverage')==('TRUNCATED_UNION_COMPLETE' if truncated else 'COMPLETE' if count else 'NO_SCENES'),'Witness truncation metadata mismatch')
    patch_counts={'train':0,'val':0,'test':0};report_matches=[]
    for index,(row,entry) in enumerate(zip(rows,mapping)):
        _require(type(row) is dict and set(row)=={'scene_index','province','source_group','scene_id','bounds_wgs84'} and _same(row.get('scene_index'),index) and _string(row.get('province')) and row['province'] in FIXED_PROVINCE_SPLITS and _string(row.get('source_group')) and _string(row.get('scene_id')),'Projected scene identity/order invalid')
        bbox=row['bounds_wgs84'];_require(type(bbox) is list and len(bbox)==4 and all(_number(v) for v in bbox) and -180<=bbox[0]<bbox[2]<=180 and -90<=bbox[1]<bbox[3]<=90,'Projected scene bounds invalid')
        _require(type(entry) is dict and _same(entry.get('scene_index'),index) and _same(entry.get('eligible_position'),index) and _same(entry.get('province'),row['province']) and _uint(entry.get('eligible_patches')) and entry.get('included_despite_zero_eligible_patches') is (entry['eligible_patches']==0),'Scene mapping identity/count invalid')
        patch_counts[FIXED_PROVINCE_SPLITS[row['province']]]+=entry['eligible_patches']
        literal,active=_roles(row['source_group'],row['scene_id'],token)
        if literal:report_matches.append({'scene_index':index,'eligible_position':index,'province':row['province'],'fixed_split':FIXED_PROVINCE_SPLITS[row['province']],'eligible_patches':entry['eligible_patches'],'normalized_source_group':row['source_group'],'normalized_scene_id':row['scene_id'],'literal_roles':literal,'active_token_roles':active,'token_participation':'ACTIVE' if active else 'SKIPPED_FALSY_SOURCE_GROUP'})
    _require(_same(witness.get('token_occurrences_processed'),sum(2 for row in rows if row['source_group'])),'Token occurrence count invalid')
    _require(_same(fresh.get('patch_counts_by_split'),patch_counts) and _same(capture.get('supplied_eligible_patch_sum'),sum(patch_counts.values())),'Patch accounting mismatch; patch count is not scene count')
    identities=_validate_source_identity(capture,count) if 'source_identity' in capture else None
    raw_index=defaultdict(list);raw_matches=[];unknown=[]
    for index,row in enumerate(raw_rows):
        try:
            _require(type(row) is dict,'Raw scene requires object')
            province=row.get('province',row.get('province_id',row.get('aoi')))
            _require(_string(province),'Raw province unsupported')
            group=_token(row.get('source_group',row.get('scene_id')),group=True);identifier=_token(row.get('scene_id'))
            key=(province,group,identifier);raw_index[key].append(index)
            literal,active=_roles(group,identifier,token)
            if literal:raw_matches.append({'manifest_row_index':index,'province_declared_by_readiness_fallback':province,'normalized_source_group':group,'normalized_scene_id':identifier,'literal_roles':literal,'active_token_roles':active,'token_participation':'ACTIVE' if active else 'SKIPPED_FALSY_SOURCE_GROUP'})
        except (ValueError,TypeError,KeyError,OverflowError) as exc:
            unknown.append({'manifest_row_index':index,'status':'UNKNOWN_UNSUPPORTED_RAW_METADATA','error_type':type(exc).__name__})
    bindings=[];selected=[];selected_set=set();link_budget=max_candidates;binding_counts=Counter();matched_keys=set();total_links=0
    for member in report_matches:
        key=(member['province'],member['normalized_source_group'],member['normalized_scene_id']);candidates=raw_index.get(key,[])
        status='NO_MATCH' if not candidates else 'UNIQUE_METADATA_CANDIDATE' if len(candidates)==1 else 'AMBIGUOUS_MATCH_SET'
        binding_counts[status]+=1;matched_keys.add(key);total_links+=len(candidates)
        if len(bindings)<max_members:
            links=candidates[:link_budget];link_budget-=len(links)
            for i in links:
                if i not in selected_set and len(selected)<max_candidates:selected_set.add(i);selected.append(i)
            bindings.append({**member,'candidate_status':status,'candidate_count':len(candidates),'candidate_row_indices':links,'candidate_links_truncated':len(links)<len(candidates),'exact_row_binding_verified':False})
    for member in raw_matches[:max_candidates]:
        i=member['manifest_row_index']
        if i not in selected_set and len(selected)<max_candidates:selected_set.add(i);selected.append(i)
    incomplete=bool(unknown);output_truncated=len(bindings)<len(report_matches) or any(x['candidate_links_truncated'] for x in bindings) or len(raw_matches)>max_candidates
    if incomplete:status='RAW_METADATA_INCOMPLETE'
    elif not report_matches and not raw_matches:status='TOKEN_NOT_FOUND'
    elif not report_matches:status='RAW_ONLY_MEMBERSHIP'
    elif binding_counts['NO_MATCH']:status='REPORT_MEMBER_NO_RAW_MATCH'
    elif output_truncated:status='OBSERVED_MEMBERSHIP_OUTPUT_TRUNCATED'
    else:status='OBSERVED_METADATA_MEMBERSHIP'
    refinement=_refine_identity_members(report_matches,identities,raw_index,raw_rows,root,max_members,max_candidates,not incomplete) if 'source_identity' in capture else None
    for path,stamp,pin,maximum in inputs:
        if _file_stamp(path)!=stamp or hashlib.sha256(_read_bounded(path,stamp,maximum,32)).hexdigest()!=pin:raise ValueError('JSON input changed during lineage inspection')
    for logical,target in targets.items():
        if _confined(root,logical)!=target:raise ValueError('Logical JSON target changed during lineage inspection')
    result={'schema_version':1,'kind':'PINNED_CURRENT_CONNECTIVITY_TOKEN_LINEAGE','mode':'READ_ONLY','status':'BLOCKED','lineage_status':status,
      'inputs':{'report':{'path':str(fresh_path),'sha256':expected_report_sha256},'manifest':{'path':str(manifest_path),'sha256':expected_manifest_sha256}},
      'token':token,'token_namespace':'SHARED_SOURCE_GROUP_AND_SCENE_ID_LITERAL_STR','query_inferred':False,'report_scene_count':count,'manifest_row_count':len(raw_rows),'patch_counts_by_split':patch_counts,
      'report_literal_member_count':len(report_matches),'report_active_token_member_count':sum(bool(m['active_token_roles']) for m in report_matches),'report_skipped_literal_member_count':sum(not m['active_token_roles'] for m in report_matches),
      'raw_literal_member_count':len(raw_matches),'raw_active_token_member_count':sum(bool(m['active_token_roles']) for m in raw_matches),'raw_skipped_literal_member_count':sum(not m['active_token_roles'] for m in raw_matches),
      'raw_metadata_membership_complete':not incomplete,'raw_unknown_row_count':len(unknown),'raw_unknown_examples':unknown[:32],
      'binding_status_counts_all_report_literal_members':dict(binding_counts),'has_ambiguous_match_sets':bool(binding_counts['AMBIGUOUS_MATCH_SET']),
      'candidate_link_count_total':total_links,'candidate_link_count_stored':sum(len(b['candidate_row_indices']) for b in bindings),'unique_candidate_raw_row_count':sum(len(raw_index.get(key,[])) for key in matched_keys),
      'report_members':bindings,'raw_members':raw_matches[:max_candidates],
      'candidate_rows':[_declared_candidate(i,raw_rows[i]) for i in selected],'output_truncated':output_truncated,'max_candidates':max_candidates,'max_members':max_members,
      'stored_witness_truncated':truncated,'membership_queried_from_full_projected_and_raw_rows':True,'stored_witness_prefix_used_for_membership':False,
      'exact_row_binding_verified':False,'raw_row_order_used_as_identity':False,'original_file_or_product_authenticity_verified':False,'executing_code_identity_verified':False,
      'eligibility_recomputed':False,'historical_readiness_cause_reconstructed':False,'zero_patch_removal_or_blocker_resolution_assessed':False,
      'assess_called':False,'connectivity_helper_called':False,'source_headers_or_pixels_read':False,'source_content_hashes_revalidated':False,'source_manifests_followed':False,
      'ready_for_training':False,'scientific_accuracy_validated':False,'training_split_leakage_resolved':False,'settlement_authorized':False,'execution_authorized':False,'automatic_resume_allowed':False,'proposed_refund_bytes':0,'exactly_once_applied':'UNKNOWN','source_files_written':0,'network_requests':0,
      'limitation':'Current pinned JSON literal membership and candidate match sets only. Internal scene indexes are not raw row identities; even one candidate is not authenticated binding. Falsy group skips both token roles. No raw eligibility, historical cause, source truth, geometry independence, removal counterfactual or approval is verified.'}
    if 'source_identity' in capture:
        result['source_identity_refinement']=refinement
    return result
