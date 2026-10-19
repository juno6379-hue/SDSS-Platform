"""Pinned saved-readiness versus physical corner snapshot comparison; no gate rerun."""
from collections import defaultdict
import copy
import hashlib
import math
from pathlib import Path
from .recovery_boundary import _read_bounded, _decode, MAX_MANIFEST_BYTES
from .recovery_raster_content import _file_stamp, _sha_valid
from .recovery_source_split_overlap import _fixed_policy, _cross_split_plan
from .recovery_terminal import _confined

PROJECT_ROOT = Path(__file__).resolve().parents[3]
REPORT_BYTES = 32 * 1024 * 1024
MAX_ROWS = 100000
MAX_SOURCES = 10000
MAX_PAIRS = 10000


def _same(left, right):
    if type(left) is not type(right): return False
    if type(left) is dict: return left.keys() == right.keys() and all(_same(left[k], right[k]) for k in left)
    if type(left) is list: return len(left) == len(right) and all(_same(a,b) for a,b in zip(left,right))
    return left == right


def _uint(value): return type(value) is int and value >= 0


def _number(value):
    if type(value) not in (int,float): return False
    try:return math.isfinite(value)
    except (OverflowError,ValueError):return False


def _points(value):
    return type(value) is list and len(value)==4 and all(type(p) is list and len(p)==2 and all(_number(v) for v in p) for p in value)


def _stored_header_and_footprint(header, footprint):
    if type(header) is not dict or type(footprint) is not dict:return False
    if header.get('status')!='VALID_HEADER' or header.get('driver')!='GTiff' or any(type(header.get(k)) is not int or header[k]<=0 for k in ['width','height','count']):return False
    if type(header.get('crs_wkt')) is not str or not header['crs_wkt'].strip():return False
    affine=header.get('transform');dtypes=header.get('dtypes')
    if type(affine) is not list or len(affine)!=6 or not all(_number(v) for v in affine):return False
    try:determinant=affine[0]*affine[4]-affine[1]*affine[3]
    except (OverflowError,TypeError):return False
    if not _number(determinant) or determinant==0:return False
    if type(dtypes) is not list or len(dtypes)!=header['count'] or any(type(v) is not str or not v.strip() for v in dtypes):return False
    if footprint.get('status')!='CORNER_ONLY_FOOTPRINT_VALID' or footprint.get('always_xy') is not True or footprint.get('transform_errcheck') is not True or footprint.get('projection_network_enabled_during_transform') is not False:return False
    corners=footprint.get('longitude_latitude_corners');native=footprint.get('native_crs_corners')
    expected_pixels=[[0,0],[header['width'],0],[header['width'],header['height']],[0,header['height']]]
    if not _same(footprint.get('pixel_edge_corners'),expected_pixels) or not _points(corners) or not _points(native):return False
    if any(not -180<=x<=180 or not -90<=y<=90 for x,y in corners) or max(p[0] for p in corners)-min(p[0] for p in corners)>180:return False
    geometry=footprint.get('geometry');topology=footprint.get('topology')
    if not _same(geometry,{'type':'Polygon','coordinates':[corners+[corners[0]]]}):return False
    return type(topology) is dict and topology.get('status')=='VALID_TOPOLOGY' and topology.get('is_empty') is False and topology.get('is_valid') is True and topology.get('finite_positive_area') is True and _number(topology.get('area_square_degrees_planar')) and topology['area_square_degrees_planar']>0



def inspect_recovery_readiness_comparison(data_root, expected_manifest_sha256, expected_readiness_sha256, corner_report_path, expected_corner_sha256, *, readiness_path=None):
    """Read three pinned JSON snapshots; verify bounded stored evidence, never reassess readiness."""
    pins = [expected_manifest_sha256, expected_readiness_sha256, expected_corner_sha256]
    if any(not _sha_valid(pin) for pin in pins): raise ValueError('Three explicit lowercase SHA256 pins required')
    requested = Path(data_root)
    if str(requested).startswith(('\\\\','//')): raise ValueError('Data root must be local')
    root = requested.resolve(); evidence_root = (PROJECT_ROOT/'evidence').resolve()
    mapping, policy = _fixed_policy()
    targets = {}; inputs = []
    def resolve(base, logical):
        target = _confined(base, logical)
        logical = Path(logical); logical = logical if logical.is_absolute() else base/logical
        key = (base,logical)
        if key in targets and targets[key] != target: raise ValueError('Logical JSON target changed')
        targets[key] = target
        return target
    def load(base, logical, pin, maximum):
        target = resolve(base,logical); stamp = _file_stamp(target)
        if not stamp['exists']: raise ValueError('Pinned JSON input missing: '+str(target))
        raw = _read_bounded(target,stamp,maximum,32)
        if hashlib.sha256(raw).hexdigest() != pin: raise ValueError('Pinned JSON SHA mismatch: '+str(target))
        value = _decode(raw)
        if type(value) is not dict: raise ValueError('Pinned JSON requires object')
        inputs.append((target,stamp,pin,maximum))
        return target,value
    manifest_path, manifest = load(root,root/'first-group-training-esri-v1/annual-window-report.json',pins[0],MAX_MANIFEST_BYTES)
    saved_path, saved = load(root,readiness_path or root/'first-group/readiness-resume-20261017.json',pins[1],REPORT_BYTES)
    corner_path, corner = load(evidence_root,corner_report_path,pins[2],REPORT_BYTES)
    if corner_path.is_relative_to(root):raise ValueError('Corner evidence must be outside inspected data')
    if len({manifest_path,saved_path,corner_path}) != 3: raise ValueError('Three distinct JSON inputs required')
    rows = manifest.get('scenes')
    if type(rows) is not list or not 1 <= len(rows) <= MAX_ROWS: raise ValueError('Bounded nonempty manifest scenes required')
    sources = {}; physical = {'train':0,'val':0,'test':0}
    for index,row in enumerate(rows):
        if type(row) is not dict or type(row.get('province')) is not str or row['province'] not in mapping: raise ValueError('Manifest province invalid')
        split = mapping[row['province']]; physical[split] += 1
        if 'split' in row and not _same(row['split'],split): raise ValueError('Manifest split disagrees with fixed policy')
        ref = row.get('source_window')
        if type(ref) is not dict or type(ref.get('path')) is not str or not ref['path'] or not _sha_valid(ref.get('sha256')): raise ValueError('Manifest source reference invalid')
        # Resolution only: this unit neither stats nor opens any raster.
        path = resolve(root,ref['path'])
        entry = sources.setdefault(path,{'expected_sha256':ref['sha256'],'splits':set(),'provinces':set(),'scene_indexes':[],'rows_by_split':defaultdict(list)})
        if entry['expected_sha256'] != ref['sha256']: raise ValueError('Conflicting canonical source SHA')
        entry['splits'].add(split);entry['provinces'].add(row['province']);entry['scene_indexes'].append(index);entry['rows_by_split'][split].append(index)
    if len(sources)>MAX_SOURCES: raise ValueError('Source metadata count exceeds cap')
    pairs,within = _cross_split_plan(sources,MAX_PAIRS)
    issues=[]
    def check(condition,code):
        if not condition: issues.append({'code':code})
    def field(document,key,expected,prefix): check(_same(document.get(key),expected),prefix+key.upper())
    field(saved,'schema_version',1,'READINESS_')
    check(type(saved.get('policy')) is dict and _same(saved['policy'].get('province_splits'),mapping),'READINESS_FIXED_POLICY_MISMATCH')
    refs=saved.get('input_manifests')
    ref_ok=type(refs) is list and len(refs)==1 and type(refs[0]) is dict and refs[0].get('sha256')==pins[0] and type(refs[0].get('path')) is str
    if ref_ok:
        try:ref_ok=resolve(root,refs[0]['path'])==manifest_path
        except (ValueError,OSError):ref_ok=False
    check(ref_ok,'READINESS_SINGLE_MANIFEST_BINDING_MISMATCH')
    eligible=saved.get('patch_counts_by_split')
    count_ok=type(eligible) is dict and set(eligible)==set(physical) and all(_uint(v) for v in eligible.values())
    check(count_ok,'READINESS_ELIGIBLE_COUNTS_INVALID')
    if count_ok:check(all(eligible[s]<=physical[s] for s in physical),'READINESS_ELIGIBLE_EXCEEDS_PHYSICAL')
    blockers=saved.get('blockers')
    check(type(blockers) is list and all(type(b) is dict and type(b.get('code')) is str and bool(b['code']) for b in blockers),'READINESS_BLOCKERS_INVALID')
    check('prepared_payload' in saved,'READINESS_PREPARED_PAYLOAD_FIELD_MISSING')
    field(saved,'group_splits',mapping,'READINESS_')
    field(saved,'status','blocked','READINESS_');field(saved,'ready_for_training',False,'READINESS_');field(saved,'scientific_accuracy_validated',False,'READINESS_')
    check(bool(blockers),'READINESS_BLOCKED_WITHOUT_RECORDED_BLOCKER')
    metadata_expected={'schema_version':1,'kind':'RECOVERY_PHYSICAL_SOURCE_FIXED_SPLIT_CORNER_DIAGNOSTIC','mode':'READ_ONLY','status':'BLOCKED',
      'scope_rows':'ALL_PHYSICAL_MANIFEST_SCENES','aggregate_physical_row_count':len(rows),'physical_row_counts_by_fixed_split':physical,
      'boundary_status':'BOUNDARY_NOT_USED','planned_source_header_count':len(sources),'source_header_attempt_count':len(sources),
      'pair_plan_evaluated':True,'planned_cross_split_pair_count':len(pairs),'pair_diagnostic_record_count':len(pairs),
      'intersection_attempt_count':len(pairs),'within_split_pair_count_out_of_scope':within,'within_split_pair_status':'OUT_OF_SCOPE',
      'footprint_method':'FOUR_PIXEL_EDGE_CORNERS_STRAIGHT_SEGMENTS','area_units':'square_degrees_planar_diagnostic','exactly_once_applied':'UNKNOWN',
      'proposed_refund_bytes':0,'network_requests':0,'source_files_written':0,'issues':[]}
    for key,value in metadata_expected.items():field(corner,key,value,'CORNER_')
    false_fields=['eligibility_recomputed','quality_status_used_as_filter','readiness_gate_revalidated','curved_edges_densified','exact_raster_footprint_verified','source_content_sha_revalidated','pixel_arrays_read','eligible_subset_leakage_assessed','training_split_leakage_resolved','geometric_independence_verified','original_geometry_reprojected_or_written','automatic_geometry_repair_performed','ready_for_training','training_executed','scientific_accuracy_validated','settlement_authorized','execution_authorized','automatic_resume_allowed']
    for key in false_fields:field(corner,key,False,'CORNER_')
    check(_same(corner.get('fixed_split_policy'),policy),'CORNER_POLICY_CODE_PROVENANCE_MISMATCH')
    binding=corner.get('manifest');bound=type(binding) is dict and binding.get('sha256')==pins[0] and type(binding.get('path')) is str
    if bound:
        try:bound=resolve(root,binding['path'])==manifest_path
        except (ValueError,OSError):bound=False
    check(bound,'CORNER_MANIFEST_BINDING_MISMATCH')
    geometry_runtime=corner.get('geometry_runtime')
    check(type(geometry_runtime) is dict and geometry_runtime.get('available') is True and all(type(geometry_runtime.get(k)) is str and bool(geometry_runtime[k].strip()) and geometry_runtime[k]!='UNKNOWN' for k in ['shapely_version','geos_version']),'CORNER_GEOMETRY_RUNTIME_INCOMPLETE')
    projection=corner.get('projection_runtime')
    check(type(projection) is dict and projection.get('available') is True and all(type(projection.get(k)) is str and bool(projection[k].strip()) and projection[k]!='UNKNOWN' for k in ['pyproj_version','proj_version']) and projection.get('network_state_restored') is True and type(projection.get('network_enabled_at_entry')) is bool and _same(projection.get('network_enabled_at_exit'),projection.get('network_enabled_at_entry')),'CORNER_NETWORK_RESTORATION_UNPROVEN')
    for key,minimum in [('max_source_headers',len(sources)),('max_pairs',max(1,len(pairs)))]:check(type(corner.get(key)) is int and minimum<=corner[key]<=10000,'CORNER_BUDGET_INVALID_'+key.upper())
    source_rows=corner.get('source_footprints');seen=set()
    if type(source_rows) is not list or len(source_rows)!=len(sources):check(False,'CORNER_SOURCE_RECORD_COUNT_MISMATCH');source_rows=[]
    for item in source_rows:
        if type(item) is not dict or type(item.get('path')) is not str:check(False,'CORNER_SOURCE_RECORD_INVALID');continue
        try:path=resolve(root,item['path'])
        except (ValueError,OSError):check(False,'CORNER_SOURCE_PATH_INVALID');continue
        if path not in sources or path in seen:check(False,'CORNER_SOURCE_CANONICAL_SET_MISMATCH');continue
        seen.add(path);entry=sources[path]
        for key,value in {'recorded_sha256':entry['expected_sha256'],'recorded_sha_revalidated':False,'provinces':sorted(entry['provinces']),'fixed_splits':sorted(entry['splits']),'scene_indexes':entry['scene_indexes'],'rows_by_split':dict(entry['rows_by_split']),'footprint_status':'CORNER_ONLY_FOOTPRINT_VALID'}.items():field(item,key,value,'CORNER_SOURCE_')
        header=item.get('header');footprint=item.get('footprint')
        check(_stored_header_and_footprint(header,footprint),'CORNER_STORED_HEADER_OR_FOOTPRINT_INCOMPLETE')
    check(seen==set(sources),'CORNER_SOURCE_CANONICAL_SET_INCOMPLETE')
    expected_pairs=set(pairs);seen_pairs=set();pair_rows=corner.get('pair_results');positive=[];statuses=[]
    if type(pair_rows) is not list or len(pair_rows)!=len(pairs):check(False,'CORNER_PAIR_RECORD_COUNT_MISMATCH');pair_rows=[]
    for item in pair_rows:
        if type(item) is not dict:check(False,'CORNER_PAIR_INVALID');continue
        try:
            if type(item.get('left_source_path')) is not str or type(item.get('right_source_path')) is not str:raise ValueError('Path invalid')
            pair=(resolve(root,item['left_source_path']),resolve(root,item['right_source_path']))
        except (ValueError,OSError):check(False,'CORNER_PAIR_PATH_INVALID');continue
        if pair not in expected_pairs or pair in seen_pairs:check(False,'CORNER_PAIR_CANONICAL_SET_MISMATCH');continue
        seen_pairs.add(pair);left,right=(sources[p] for p in pair)
        for key,value in {'left_fixed_splits':sorted(left['splits']),'right_fixed_splits':sorted(right['splits']),'cross_split_combinations':[{'left':a,'right':b} for a in sorted(left['splits']) for b in sorted(right['splits']) if a!=b]}.items():field(item,key,value,'CORNER_PAIR_')
        status=item.get('status');area=item.get('intersection_area_square_degrees');statuses.append(status)
        valid_area=_number(area) and area>=0
        check(valid_area,'CORNER_PAIR_AREA_INVALID')
        flags=['intersection_empty','intersects','disjoint','touches','equal','left_contains_right','right_contains_left']
        check(all(type(item.get(k)) is bool for k in flags),'CORNER_PAIR_BOOLEAN_FLAGS_INVALID')
        consistent=False
        if valid_area:
            if status=='DISJOINT':consistent=area==0 and item.get('intersection_empty') is True and item.get('disjoint') is True and all(item.get(k) is False for k in ['intersects','touches','equal','left_contains_right','right_contains_left'])
            elif status=='BOUNDARY_CONTACT':consistent=area==0 and item.get('intersection_empty') is False and item.get('intersects') is True and item.get('disjoint') is False and item.get('touches') is True and all(item.get(k) is False for k in ['equal','left_contains_right','right_contains_left'])
            elif status=='POSITIVE_AREA_OVERLAP':
                consistent=area>0 and item.get('intersection_empty') is False and item.get('intersects') is True and item.get('disjoint') is False and item.get('touches') is False and _same(item.get('equal'),item.get('left_contains_right') is True and item.get('right_contains_left') is True);positive.append(item)
        check(consistent,'CORNER_PAIR_INCOMPLETE_OR_CONTRADICTORY')
    check(seen_pairs==expected_pairs,'CORNER_PAIR_CANONICAL_SET_INCOMPLETE')
    shared=[{'code':'SHARED_CANONICAL_SOURCE_CROSSES_FIXED_SPLITS','source_path':str(path),'provinces':sorted(e['provinces']),'fixed_splits':sorted(e['splits']),'scene_indexes':e['scene_indexes'],'rows_by_split':dict(e['rows_by_split'])} for path,e in sources.items() if len(e['splits'])>1]
    field(corner,'shared_source_cross_split_findings',shared,'CORNER_')
    field(corner,'positive_area_overlap_candidate_count',len(positive),'CORNER_');field(corner,'positive_area_overlap_candidates',positive,'CORNER_')
    expected_validation='CROSS_SPLIT_CORNER_CANDIDATES_DIAGNOSED' if pairs else 'SHARED_SOURCE_FINDINGS_NO_DISTINCT_PAIRS' if shared else 'NO_CROSS_SPLIT_PAIR_CANDIDATES'
    field(corner,'candidate_validation',expected_validation,'CORNER_')
    # Re-read only the three JSON inputs; no raster headers, pixels, or boundary file.
    for path,stamp,pin,maximum in inputs:
        if _file_stamp(path)!=stamp:raise ValueError('JSON input changed during comparison')
        if hashlib.sha256(_read_bounded(path,stamp,maximum,32)).hexdigest()!=pin:raise ValueError('JSON input bytes changed during comparison')
    for (base,logical),target in targets.items():
        if _confined(base,logical)!=target:raise ValueError('Logical input target changed during comparison')
    if hashlib.sha256(Path(policy['implementation_path']).read_bytes()).hexdigest()!=policy['implementation_sha256']:raise ValueError('Policy implementation changed during comparison')
    complete=not issues
    witness_status='UNKNOWN_NOT_PERSISTED' if saved.get('prepared_payload') is None else 'PRESENT_NOT_ANALYZED'
    return {'schema_version':1,'kind':'RECOVERY_SAVED_READINESS_PHYSICAL_CORNER_SCOPE_COMPARISON','mode':'READ_ONLY','status':'BLOCKED',
      'comparison_status':'CONSISTENT_SAVED_SCOPE_METADATA' if complete else 'ISSUES_FOUND',
      'inputs':{'manifest':{'path':str(manifest_path),'sha256':pins[0]},'readiness':{'path':str(saved_path),'sha256':pins[1]},'corner_report':{'path':str(corner_path),'sha256':pins[2]}},
      'fixed_split_policy':policy,'physical_row_count':len(rows),'physical_row_counts_by_fixed_split':physical,
      'saved_eligible_patch_counts_by_split':copy.deepcopy(eligible),'physical_minus_saved_eligible_by_split':{s:physical[s]-eligible[s] for s in physical} if count_ok else None,
      'saved_readiness_blockers':copy.deepcopy(blockers),'saved_readiness_blocker_count':len(blockers) if type(blockers) is list else None,
      'saved_group_splits':copy.deepcopy(saved.get('group_splits')),'saved_province_groups':copy.deepcopy(saved.get('province_groups')),'saved_component_mapping_is_branch_witness':False,
      'saved_prepared_payload_is_null':'prepared_payload' in saved and saved['prepared_payload'] is None,'eligible_scene_witness_status':witness_status,
      'shared_source_token_or_bbox_branch_cause':'UNKNOWN_NOT_PERSISTED','readiness_blocker_root_cause_recomputed':False,
      'corner_snapshot_complete_and_consistent':complete,'stored_corner_all_cross_pairs_disjoint':bool(complete and pairs and all(s=='DISJOINT' for s in statuses)),
      'stored_corner_no_cross_split_candidates':bool(complete and not positive and not shared),
      'planned_source_count':len(sources),'planned_cross_split_pair_count':len(pairs),'within_split_pairs_out_of_scope':within,
      'snapshot_evidence_only':True,'current_headers_or_geometry_revalidated':False,'current_source_content_sha_revalidated':False,
      'eligibility_recomputed':False,'readiness_assess_called':False,'boundary_status':'BOUNDARY_NOT_USED','issues':issues,
      'exactly_once_applied':'UNKNOWN','ready_for_training':False,'training_executed':False,'scientific_accuracy_validated':False,
      'training_split_leakage_resolved':False,'settlement_authorized':False,'execution_authorized':False,'automatic_resume_allowed':False,
      'proposed_refund_bytes':0,'network_requests':0,'source_files_written':0,
      'limitation':'Pinned JSON snapshot consistency only. Physical corner proxies and saved eligible weak-label readiness have different scopes; absent eligible-scene/token/bbox witnesses leave the blocker branch UNKNOWN. No current raster, geometry, eligible leakage, official accuracy, or operational approval is verified.'}
