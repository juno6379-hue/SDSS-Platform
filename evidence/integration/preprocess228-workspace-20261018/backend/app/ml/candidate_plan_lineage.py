"""Reference-only linkage of a saved split plan and pinned declared identity trace.

Pure build has no IO. It does not rerun the planner, assess, or publish a candidate.
"""
from collections import Counter,defaultdict
import copy
import hashlib
import math
from pathlib import Path,PureWindowsPath,PurePosixPath
import re
from ..data.readiness_connectivity_lineage import (_same,_uint,_number,_string,_roles,
    _lexical_identity_path,_validate_source_identity,_refine_identity_members,_declared_candidate)
from ..data.readiness_connectivity_witness import FIXED_PROVINCE_SPLITS,PROVINCES
from ..ml.readiness_connectivity_adapter import _token
from ..data.recovery_boundary import _read_bounded,_decode
from ..data.recovery_raster_content import _file_stamp,_sha_valid
from ..data.recovery_terminal import _confined

NAMES=('plan','source','old_readiness','new_report','lineage')
BYTE_CAPS={'plan':4*1024**2,'source':64*1024**2,'old_readiness':16*1024**2,'new_report':16*1024**2,'lineage':4*1024**2}
ROW_CAP=100000
SCENE_CAP=2000
LINK_CAP=2000


def _need(value,message='Candidate reference contract invalid'):
    if not value:raise ValueError(message)


def _path(value,root):
    # Reference paths may be in evidence; only raster declaration refinement is DATA-bound.
    _need(_string(value),'Invalid reference path scalar')
    windows=bool(re.match(r'^[A-Za-z]:[\\/]',str(root)))
    cls=PureWindowsPath if windows else PurePosixPath
    p=cls(value);base=cls(str(root))
    full=p if p.is_absolute() else base/p
    anchor=full.anchor
    key=_lexical_identity_path(str(full),anchor)
    _need(key is not None,'Unsupported declared reference path')
    return (anchor.casefold() if windows else anchor,key)


def _ref(value,expected,root):
    _need(type(value) is dict and set(value)=={'path','sha256'} and value['sha256']==expected['sha256'] and _path(value['path'],root)==_path(expected['path'],root),'Pinned reference linkage mismatch')


def _counts(rows,indexes):
    result={s:0 for s in ('train','val','test')};cells=Counter()
    for i in indexes:
        r=rows[i]
        if r['quality_status']=='quality_eligible':
            result[FIXED_PROVINCE_SPLITS[r['province']]]+=1
            cells[(r['province'],int(r['year']))]+=1
    return {'eligible_patches_by_split':result,'eligible_total':sum(result.values()),'eligible_by_province_year':{f'{p}/{y}':n for (p,y),n in sorted(cells.items())}}


def build_candidate_plan_lineage(documents,references,*,data_root_literal,token):
    """Caller-declared references, not byte pins; CLI separately verifies actual bytes.

    Restricted to a complete, nontruncated unique declared-metadata member trace.
    Only selected plan fields are checked: no full planner recomputation claim.
    """
    _need(type(documents) is dict and set(documents)==set(NAMES) and all(type(v) is dict for v in documents.values()))
    _need(type(references) is dict and set(references)==set(NAMES))
    _need(_string(token) and bool(token),'Explicit bounded nonempty token required')
    token.encode('utf-8')
    for r in references.values():_need(type(r) is dict and set(r)=={'path','sha256'} and _string(r['path']) and _sha_valid(r['sha256']))
    _need(len({_path(r['path'],data_root_literal) for r in references.values()})==5,'Five distinct declared references required')
    plan,source,old,fresh,lineage=(documents[k] for k in NAMES)
    rows=source.get('scenes');_need(type(rows) is list and 0<len(rows)<=ROW_CAP)
    for row in rows:
        _need(type(row) is dict and type(row.get('province')) is str and row['province'] in FIXED_PROVINCE_SPLITS and row.get('quality_status') in ('quality_eligible','quality_insufficient'))
        year=row.get('year');_need((type(year) is int and 2015<=year<=2026) or (type(year) is str and len(year)==4 and year.isascii() and year.isdigit() and 2015<=int(year)<=2026))
        _need(row.get('split') is None or type(row['split']) is str and row['split']==FIXED_PROVINCE_SPLITS[row['province']])
    _need(type(plan.get('derived_manifest_version')) is str and re.fullmatch(r'split-repair-v1-[0-9a-f]{16}',plan['derived_manifest_version']) is not None,'Unsupported saved derived version')
    _need(_same(plan.get('schema_version'),1) and plan.get('status')=='PLAN_ONLY' and plan.get('planner_version')=='split-repair-v1')
    for key in ['ready_for_training','training_executed','scientific_accuracy_validated','spatial_overlap_rechecked']:_need(plan.get(key) is False)
    _ref(plan.get('source_manifest'),references['source'],data_root_literal);_ref(plan.get('readiness_reference'),references['old_readiness'],data_root_literal)
    policy=plan.get('policy');_need(type(policy) is dict and _same(policy.get('province_splits'),FIXED_PROVINCE_SPLITS) and _same(policy.get('keep_split_priority'),['test','val','train']))
    kept=plan.get('retained_row_indexes');excluded=plan.get('excluded_row_indexes')
    for indexes in (kept,excluded):_need(type(indexes) is list and all(_uint(i) and i<len(rows) for i in indexes) and indexes==sorted(set(indexes)))
    keptset=set(kept);excludedset=set(excluded);_need(not keptset&excludedset and keptset|excludedset==set(range(len(rows))),'Plan indexes must partition source rows')
    before=_counts(rows,range(len(rows)));after=_counts(rows,kept)
    _need(_same(plan.get('before'),before) and _same(plan.get('projected_after'),after),'Plan selected counts mismatch')
    for report in (old,fresh):
        _need(_same(report.get('schema_version'),1) and report.get('status')=='blocked' and report.get('ready_for_training') is False and report.get('scientific_accuracy_validated') is False)
        _need(type(report.get('policy')) is dict and _same(report['policy'].get('province_splits'),FIXED_PROVINCE_SPLITS))
        refs=report.get('input_manifests');_need(type(refs) is list and len(refs)==1);_ref(refs[0],references['source'],data_root_literal)
        _need(_same(report.get('patch_counts_by_split'),before['eligible_patches_by_split']))
    for key in ['policy','blockers','patch_counts_by_split','class_counts_by_split','class_patch_counts_by_split']:_need(_same(old.get(key),fresh.get(key)),'Old/current stored gate metadata mismatch: '+key)
    blockers=old.get('blockers');_need(type(blockers) is list and len(blockers)<=10000 and all(type(b) is dict and _string(b.get('code')) and b['code'] for b in blockers))
    impact=plan.get('class_impact');_need(type(impact) is dict and impact.get('status')=='CONSERVATIVE_BOUNDS_ONLY')
    for key in ['exact_after_counts_computed','bare_shortage_resolved','independent_scientific_validation']:_need(impact.get(key) is False)
    bysplit=impact.get('by_split');_need(type(bysplit) is dict and set(bysplit)=={'train','val','test'})
    size=old['policy'].get('patch_size');fraction=old['policy'].get('min_valid_fraction')
    _need(type(size) is int and 1<=size<=4096 and _number(fraction) and 0<fraction<=1)
    for split,bound in bysplit.items():
        prior=old.get('class_counts_by_split',{}).get(split);patchprior=old.get('class_patch_counts_by_split',{}).get(split)
        _need(type(prior) is list and type(patchprior) is list and len(prior)==len(patchprior)==9 and all(_uint(n) and n<=9007199254740991 for n in prior+patchprior))
        removed=before['eligible_patches_by_split'][split]-after['eligible_patches_by_split'][split]
        lower=[max(0,n-removed*size**2) for n in prior]
        _need(type(bound) is dict and _same(bound.get('removed_eligible_patches'),removed) and _same(bound.get('class_pixel_lower_bounds'),lower) and _same(bound.get('class_pixel_upper_bounds'),prior) and _same(bound.get('class_patch_upper_bounds'),patchprior) and _same(bound.get('bare_patch_upper_bound'),patchprior[7]) and bound.get('class_representation_can_worsen') is (removed>0),'Stored conservative class bound mismatch')
        minimum=after['eligible_patches_by_split'][split]*size**2*fraction
        ratio=min(1,prior[7]/minimum) if minimum else None
        _need(_same(bound.get('bare_ratio_upper_bound'),ratio))
    capture=fresh.get('connectivity_diagnostics');_need(type(capture) is dict and _same(capture.get('schema_version'),1) and capture.get('capture_status')=='CAPTURED_COMPONENTS_MATCH' and capture.get('gate_components_match') is True and capture.get('scope')=='ALL_APPENDED_ASSESS_SCENES_INCLUDING_ZERO_PATCH')
    _need(capture.get('status')=='BLOCKED')
    for key in ['eligibility_recomputed','eligible_patch_count_is_scene_count','historical_readiness_cause_reconstructed','ready_for_training','scientific_accuracy_validated','training_executed','gate_result_modified','settlement_authorized','execution_authorized','automatic_resume_allowed','provenance_verified','executing_code_verified']:_need(capture.get(key) is False,'Capture false-claim mismatch: '+key)
    for key in ['proposed_refund_bytes','source_files_read','source_files_written','network_requests']:_need(_same(capture.get(key),0),'Capture non-execution count mismatch')
    count=capture.get('scene_count');projected=capture.get('projected_scene_metadata');mapping=capture.get('scene_mapping')
    _need(_uint(count) and count<=SCENE_CAP and type(projected) is list and type(mapping) is list and len(projected)==len(mapping)==count)
    _need(_same(capture.get('manifest_input_references'),fresh['input_manifests']))
    identities=_validate_source_identity(capture,count);_need(identities is not None and all(r['identity_status']=='DECLARED_PATH_AND_SHA256' for r in identities),'Complete declared identities required')
    raw_index=defaultdict(list)
    for i,row in enumerate(rows):
        group=_token(row.get('source_group',row.get('scene_id')),group=True);identifier=_token(row.get('scene_id'))
        raw_index[(row['province'],group,identifier)].append(i)
    members=[];patches={s:0 for s in ('train','val','test')}
    for i,(r,m) in enumerate(zip(projected,mapping)):
        _need(type(r) is dict and set(r)=={'scene_index','province','source_group','scene_id','bounds_wgs84'} and _same(r.get('scene_index'),i) and r.get('province') in FIXED_PROVINCE_SPLITS and _string(r.get('source_group')) and _string(r.get('scene_id')))
        _need(type(m) is dict and _same(m.get('scene_index'),i) and _same(m.get('eligible_position'),i) and m.get('province')==r['province'] and _uint(m.get('eligible_patches')) and m['eligible_patches']<=9007199254740991 and m.get('included_despite_zero_eligible_patches') is (m['eligible_patches']==0))
        patches[FIXED_PROVINCE_SPLITS[r['province']]]+=m['eligible_patches']
        literal,active=_roles(r['source_group'],r['scene_id'],token)
        if literal:members.append({'scene_index':i,'eligible_position':i,'province':r['province'],'fixed_split':FIXED_PROVINCE_SPLITS[r['province']],'eligible_patches':m['eligible_patches'],'normalized_source_group':r['source_group'],'normalized_scene_id':r['scene_id'],'literal_roles':literal,'active_token_roles':active,'token_participation':'ACTIVE' if active else 'SKIPPED_FALSY_SOURCE_GROUP'})
    _need(_same(patches,before['eligible_patches_by_split']) and _same(capture.get('supplied_eligible_patch_sum'),sum(patches.values())))
    _need(_same(lineage.get('schema_version'),1) and lineage.get('kind')=='PINNED_CURRENT_CONNECTIVITY_TOKEN_LINEAGE' and lineage.get('mode')=='READ_ONLY' and lineage.get('status')=='BLOCKED' and lineage.get('lineage_status')=='OBSERVED_METADATA_MEMBERSHIP' and lineage.get('token')==token and lineage.get('query_inferred') is False and lineage.get('output_truncated') is False and lineage.get('raw_metadata_membership_complete') is True and _same(lineage.get('raw_unknown_row_count'),0))
    _ref(lineage.get('inputs',{}).get('report'),references['new_report'],data_root_literal);_ref(lineage['inputs'].get('manifest'),references['source'],data_root_literal)
    for key in ['ready_for_training','scientific_accuracy_validated','exact_row_binding_verified','original_file_or_product_authenticity_verified','raw_row_order_used_as_identity','eligibility_recomputed','historical_readiness_cause_reconstructed','zero_patch_removal_or_blocker_resolution_assessed','assess_called','connectivity_helper_called','source_headers_or_pixels_read','source_content_hashes_revalidated','source_manifests_followed','execution_authorized','settlement_authorized','automatic_resume_allowed','training_split_leakage_resolved']:_need(lineage.get(key) is False)
    for key in ['source_files_written','network_requests','proposed_refund_bytes']:_need(_same(lineage.get(key),0))
    _need(_same(lineage.get('report_scene_count'),count) and _same(lineage.get('manifest_row_count'),len(rows)) and _same(lineage.get('patch_counts_by_split'),patches))
    _need(_same(lineage.get('report_literal_member_count'),len(members)) and _same(lineage.get('report_active_token_member_count'),sum(bool(m['active_token_roles']) for m in members)) and _same(lineage.get('report_skipped_literal_member_count'),sum(not m['active_token_roles'] for m in members)))
    total=sum(len(raw_index[(m['province'],m['normalized_source_group'],m['normalized_scene_id'])]) for m in members)
    _need(total<=LINK_CAP,'Complete candidate linkage budget exceeded')
    expected=[];uniqueraw=set()
    for m in members:
        candidates=raw_index[(m['province'],m['normalized_source_group'],m['normalized_scene_id'])];uniqueraw.update(candidates)
        expected.append({**m,'candidate_status':'NO_MATCH' if not candidates else 'UNIQUE_METADATA_CANDIDATE' if len(candidates)==1 else 'AMBIGUOUS_MATCH_SET','candidate_count':len(candidates),'candidate_row_indices':candidates,'candidate_links_truncated':False,'exact_row_binding_verified':False})
    _need(_same(lineage.get('report_members'),expected) and _same(lineage.get('candidate_link_count_total'),total) and _same(lineage.get('candidate_link_count_stored'),total) and _same(lineage.get('unique_candidate_raw_row_count'),len(uniqueraw)),'Saved lineage broad candidate metadata mismatch')
    maximum=lineage.get('max_candidates');maxmembers=lineage.get('max_members');_need(_uint(maximum) and total<=maximum<=10000 and type(maxmembers) is int and len(members)<=maxmembers<=2000)
    refinement=_refine_identity_members(members,identities,raw_index,rows,data_root_literal,maxmembers,maximum,True)
    _need(_same(lineage.get('source_identity_refinement'),refinement) and refinement['output_truncated'] is False and all(m['refined_match_status']=='UNIQUE_DECLARED_METADATA_CANDIDATE' for m in refinement['members']),'Unique complete declared metadata linkage required')
    links=[];linked=set()
    for member,refined in zip(members,refinement['members']):
        raw=refined['candidate_row_indices'][0];linked.add(raw)
        links.append({'internal_scene_index':member['scene_index'],'raw_manifest_candidate_row_index':raw,'eligible_patches':member['eligible_patches'],'province':member['province'],'fixed_split':member['fixed_split'],'planned_membership':'EXCLUDED_FROM_NEW_CANDIDATE_ONLY' if raw in excludedset else 'RETAINED_IN_NEW_CANDIDATE_ONLY','binding':'UNIQUE_DECLARED_METADATA_CANDIDATE','exact_row_binding_verified':False})
    _need(members,'Token has no current report members')
    return {'schema_version':1,'kind':'CANDIDATE_PLAN_DECLARED_LINEAGE_REFERENCE','status':'PLAN_ONLY','readiness_status':'BLOCKED','references':copy.deepcopy(references),'token':token,'scope':'SAVED_PLAN_SELECTED_METADATA_AND_CURRENT_DECLARED_LINEAGE_ONLY',
      'pin_validation':'CALLER_DECLARED_REFERENCES_ONLY','full_planner_recomputation':'NOT_PERFORMED','full_witness_replay':'NOT_PERFORMED',
      'derived_manifest_version':plan.get('derived_manifest_version'),'fixed_province_splits':dict(FIXED_PROVINCE_SPLITS),'keep_split_priority':['test','val','train'],'priority_scope':'SAVED_POLICY_DECLARATION_NOT_RECOMPUTED',
      'source_row_count':len(rows),'retained_source_row_count':len(kept),'excluded_source_row_count':len(excluded),'before':copy.deepcopy(before),'projected_after':copy.deepcopy(after),
      'saved_blocker_count':len(blockers),'saved_blockers':copy.deepcopy(blockers),'class_impact':copy.deepcopy(impact),
      'current_query':{'report_member_count':len(members),'zero_patch_member_count':sum(m['eligible_patches']==0 for m in members),'eligible_patch_sum':sum(m['eligible_patches'] for m in members),'broad_candidate_link_count':total,'unique_declared_raw_candidate_count':len(linked),'excluded_declared_raw_candidate_count':len(linked&excludedset),'retained_declared_raw_candidate_count':len(linked&keptset),'member_plan_links':links},
      'candidate_manifest_created':False,'source_rows_excluded_or_reassigned':False,'registry_called':False,'source_files_read_or_hashed':False,'assess_called':False,'connectivity_helper_called':False,'spatial_overlap_rechecked':False,'exact_class_counts_recomputed':False,'class_shortage_resolved':False,'training_split_leakage_resolved':False,'exact_row_binding_verified':False,'source_authenticity_verified':False,'ready_for_training':False,'scientific_accuracy_validated':False,'execution_authorized':False,'settlement_authorized':False,'automatic_resume_allowed':False,'proposed_refund_bytes':0,'exactly_once_applied':'UNKNOWN','source_files_written':0,'network_requests':0}


def inspect_candidate_plan_lineage(data_root,paths,pins,*,token,evidence_root):
    """Five bounded pinned JSONs only; no raster/source files or planner execution."""
    _need(type(paths) is dict and set(paths)==set(NAMES) and type(pins) is dict and set(pins)==set(NAMES) and all(_sha_valid(x) for x in pins.values()))
    _path(str(data_root),str(Path.cwd()));_path(str(evidence_root),str(Path.cwd()))
    root=Path(data_root).resolve();evidence=Path(evidence_root).resolve();targets=[];refs={}
    for name in NAMES:
        scope=root if name in ('source','old_readiness','new_report') else evidence
        _path(str(paths[name]),str(scope))
        logical=Path(paths[name]);logical=logical if logical.is_absolute() else scope/logical
        target=_confined(scope,logical);stamp=_file_stamp(target)
        _need(stamp['exists'] and stamp['bytes']<=BYTE_CAPS[name],'Input missing or exceeds byte cap')
        targets.append((name,scope,logical,target,stamp));refs[name]={'path':str(target),'sha256':pins[name]}
    _need(len({x[3] for x in targets})==5,'Five distinct input files required')
    docs={}
    for name,scope,logical,target,stamp in targets:
        raw=_read_bounded(target,stamp,BYTE_CAPS[name],32);_need(hashlib.sha256(raw).hexdigest()==pins[name],'Pinned input SHA mismatch');docs[name]=_decode(raw)
    result=build_candidate_plan_lineage(docs,refs,data_root_literal=str(root),token=token)
    for name,scope,logical,target,stamp in targets:
        _need(_confined(scope,logical)==target and _file_stamp(target)==stamp,'Input target or state changed')
        raw=_read_bounded(target,stamp,BYTE_CAPS[name],32);_need(hashlib.sha256(raw).hexdigest()==pins[name],'Input SHA changed')
    result['pin_validation']='FIVE_INPUT_BYTE_SHA256_VERIFIED_WITH_STABILITY_RECHECK'
    return result
