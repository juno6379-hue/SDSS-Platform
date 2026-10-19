"""Physical source corner-proxy cross-split candidates; no eligible leakage approval."""
from collections import Counter, defaultdict
from itertools import combinations, product
import hashlib
import json
from pathlib import Path
from ..ml import readiness
from .recovery_boundary import MAX_MANIFEST_BYTES, LIMITS, _read_bounded, _decode
from .recovery_boundary_topology import _geometry_runtime
from .recovery_boundary_relations import _pair_relation
from .recovery_source_footprints import _source_footprint, _projection_runtime
from .recovery_raster_headers import _read_header, SAFE_GDAL_OPTIONS
from .recovery_raster_content import _sha_valid, _file_stamp
from .recovery_terminal import _confined


def _fixed_policy():
    path = Path(readiness.__file__).resolve()
    raw = path.read_bytes()
    mapping = readiness.default_policy().get('province_splits')
    if type(mapping) is not dict or set(mapping) != set(readiness.FIRST_GROUP) or any(type(k) is not str or type(v) is not str for k,v in mapping.items()) or Counter(mapping.values()) != {'train':4,'val':1,'test':1}:
        raise ValueError('Default fixed six-province 4/1/1 policy is invalid')
    mapping = dict(mapping)
    evidence = {'function': 'readiness.default_policy.province_splits', 'implementation_path': str(path),
        'implementation_sha256': hashlib.sha256(raw).hexdigest(), 'province_splits': mapping,
        'policy_map_sha256': hashlib.sha256(json.dumps(mapping,sort_keys=True,separators=(',',':')).encode()).hexdigest()}
    return mapping,evidence


def _cross_split_plan(sources, maximum):
    paths = list(sources)
    cohorts = defaultdict(list)
    for path in paths: cohorts[tuple(sorted(sources[path]['splits']))].append(path)
    total = len(paths)*(len(paths)-1)//2
    within = sum(len(group)*(len(group)-1)//2 for split_set,group in cohorts.items() if len(split_set)==1)
    count = total-within
    if count>maximum: raise ValueError('Full cross-split source pair plan exceeds budget; no headers or pair work performed')
    order = {path:index for index,path in enumerate(paths)}
    pairs=[]
    groups=list(cohorts.items())
    for i,(split_set,left) in enumerate(groups):
        if len(split_set)>1: pairs.extend(combinations(left,2))
        for _,right in groups[i+1:]: pairs.extend(product(left,right))
    pairs=[(a,b) if order[a]<order[b] else (b,a) for a,b in pairs]
    pairs.sort(key=lambda pair:(order[pair[0]],order[pair[1]]))
    if len(pairs)!=count: raise ValueError('Cross-split pair plan accounting mismatch')
    return pairs,within


def inspect_recovery_source_split_overlap(data_root, expected_manifest_sha256, *, max_source_headers=128, max_pairs=10000):
    if type(max_source_headers) is not int or not 1<=max_source_headers<=10000: raise ValueError('Source-header budget must be an integer from 1 through 10000')
    if type(max_pairs) is not int or not 1<=max_pairs<=10000: raise ValueError('Pair budget must be an integer from 1 through 10000')
    if not _sha_valid(expected_manifest_sha256): raise ValueError('Explicit lowercase manifest SHA256 required')
    splits,policy = _fixed_policy()
    requested=Path(data_root)
    if str(requested).startswith(('\\\\','//')): raise ValueError('Data root must be local')
    root=requested.resolve();targets={};sources={}
    def resolve(value):
        logical=Path(value);target=_confined(root,logical)
        if logical in targets and targets[logical]!=target: raise ValueError('Logical input target changed')
        targets[logical]=target;return target
    manifest=resolve(root/'first-group-training-esri-v1/annual-window-report.json');manifest_stat=_file_stamp(manifest)
    if not manifest_stat['exists']: raise ValueError('Pinned manifest missing')
    raw=_read_bounded(manifest,manifest_stat,MAX_MANIFEST_BYTES,LIMITS['max_json_depth'])
    if hashlib.sha256(raw).hexdigest()!=expected_manifest_sha256: raise ValueError('Pinned manifest SHA mismatch')
    document=_decode(raw)
    if type(document) is not dict or type(document.get('scenes')) is not list or not document['scenes']: raise ValueError('Manifest requires nonempty scenes list')
    issues=[];row_counts={'train':0,'val':0,'test':0}
    for index,row in enumerate(document['scenes']):
        if type(row) is not dict:
            issues.append({'code':'SCENE_INVALID','scene_index':index});continue
        province=row.get('province')
        if type(province) is not str or province not in splits:
            issues.append({'code':'PROVINCE_UNKNOWN_OR_INVALID','scene_index':index});continue
        split=splits[province];row_counts[split]+=1
        if 'split' in row and (type(row['split']) is not str or row['split']!=split):
            issues.append({'code':'ROW_SPLIT_FIXED_POLICY_MISMATCH','scene_index':index});continue
        source=row.get('source_window')
        if type(source) is not dict or type(source.get('path')) is not str or not source['path'] or not _sha_valid(source.get('sha256')):
            issues.append({'code':'SOURCE_REFERENCE_INVALID','scene_index':index});continue
        path=resolve(source['path']);expected=source['sha256']
        if path not in sources:sources[path]={'expected_sha256':expected,'file_stat':_file_stamp(path),'provinces':set(),'splits':set(),'scene_indexes':[],'rows_by_split':defaultdict(list)}
        entry=sources[path]
        if entry['expected_sha256']!=expected:issues.append({'code':'CANONICAL_EXPECTED_SHA_CONFLICT','scene_index':index,'path':str(path)})
        entry['provinces'].add(province);entry['splits'].add(split);entry['scene_indexes'].append(index);entry['rows_by_split'][split].append(index)
    for path,entry in sources.items():
        if not entry['file_stat']['exists']:issues.append({'code':'SOURCE_FILE_MISSING','path':str(path)})
    if len(sources)>max_source_headers:raise ValueError('Full source-header plan exceeds budget; no headers opened')
    plan_valid=not issues
    pairs,within=_cross_split_plan(sources,max_pairs) if plan_valid else ([],None)
    shared=[{'code':'SHARED_CANONICAL_SOURCE_CROSSES_FIXED_SPLITS','source_path':str(path),'provinces':sorted(entry['provinces']),'fixed_splits':sorted(entry['splits']),'scene_indexes':entry['scene_indexes'],'rows_by_split':dict(entry['rows_by_split'])} for path,entry in sources.items() if len(entry['splits'])>1] if plan_valid else []
    geometry_runtime,shape_fn,explain_fn=_geometry_runtime();projection_runtime=_projection_runtime()
    source_results=[];geometries={}
    if plan_valid:
        for path,entry in sources.items():
            if _confined(root,path)!=path or _file_stamp(path)!=entry['file_stat']:raise ValueError('Source header target changed before open')
            header=_read_header(path)
            if _file_stamp(path)!=entry['file_stat']:raise ValueError('Source changed during header read')
            result={'path':str(path),'recorded_sha256':entry['expected_sha256'],'recorded_sha_revalidated':False,'file_stat':entry['file_stat'],'provinces':sorted(entry['provinces']),'fixed_splits':sorted(entry['splits']),'scene_indexes':entry['scene_indexes'],'rows_by_split':dict(entry['rows_by_split']),'header':header};source_results.append(result)
            if header['status']!='VALID_HEADER':
                result['footprint_status']='UNKNOWN_SOURCE_HEADER';issues.append({'code':result['footprint_status'],'path':str(path)});continue
            if not geometry_runtime['available'] or not projection_runtime['available']:
                result['footprint_status']='UNKNOWN_GEOMETRY_OR_PROJECTION_ENGINE_UNAVAILABLE';issues.append({'code':result['footprint_status'],'path':str(path)});continue
            footprint,geometry=_source_footprint(header,shape_fn,explain_fn);result['footprint']=footprint;result['footprint_status']=footprint['status']
            if geometry is None:issues.append({'code':footprint['status'],'path':str(path)})
            else:geometries[path]=geometry
    pair_results=[];intersection_attempts=0
    if plan_valid:
        for left,right in pairs:
            left_geometry,right_geometry=geometries.get(left),geometries.get(right)
            if left_geometry is None or right_geometry is None:
                relation={'status':'NOT_CHECKED_INVALID_CORNER_FOOTPRINT','intersection_area_square_degrees':None,'left_footprint_available':left_geometry is not None,'right_footprint_available':right_geometry is not None}
            else:
                relation=_pair_relation(left_geometry,right_geometry);intersection_attempts+=1
            relation.update(left_source_path=str(left),right_source_path=str(right),left_fixed_splits=sorted(sources[left]['splits']),right_fixed_splits=sorted(sources[right]['splits']),cross_split_combinations=[{'left':a,'right':b} for a in sorted(sources[left]['splits']) for b in sorted(sources[right]['splits']) if a!=b])
            pair_results.append(relation)
            if relation['status'].startswith(('UNKNOWN','NOT_CHECKED')):issues.append({'code':relation['status'],'left_source_path':str(left),'right_source_path':str(right)})
    for logical,target in targets.items():
        if _confined(root,logical)!=target:raise ValueError('Logical input target changed during inspection')
    if _file_stamp(manifest)!=manifest_stat:raise ValueError('Manifest changed during inspection')
    if hashlib.sha256(_read_bounded(manifest,manifest_stat,MAX_MANIFEST_BYTES,LIMITS['max_json_depth'])).hexdigest()!=expected_manifest_sha256:raise ValueError('Pinned manifest content changed during inspection')
    for path,entry in sources.items():
        if _file_stamp(path)!=entry['file_stat']:raise ValueError('Source changed during inspection')
    policy_path=Path(policy['implementation_path'])
    if hashlib.sha256(policy_path.read_bytes()).hexdigest()!=policy['implementation_sha256']:raise ValueError('Fixed split policy implementation changed during inspection')
    after=_projection_runtime();projection_runtime['network_enabled_at_exit']=after['network_enabled_at_entry'];projection_runtime['network_state_restored']=projection_runtime['network_enabled_at_entry']==projection_runtime['network_enabled_at_exit'] if type(projection_runtime['network_enabled_at_entry']) is bool else None
    if plan_valid and source_results and projection_runtime['network_state_restored'] is not True:issues.append({'code':'PROJECTION_NETWORK_RESTORATION_UNVERIFIED'})
    validation='NOT_STARTED_PLAN_REJECTED' if not plan_valid else 'ISSUES_FOUND' if issues else 'SHARED_SOURCE_FINDINGS_NO_DISTINCT_PAIRS' if not pairs and shared else 'NO_CROSS_SPLIT_PAIR_CANDIDATES' if not pairs else 'CROSS_SPLIT_CORNER_CANDIDATES_DIAGNOSED'
    return {'schema_version':1,'kind':'RECOVERY_PHYSICAL_SOURCE_FIXED_SPLIT_CORNER_DIAGNOSTIC','mode':'READ_ONLY','status':'BLOCKED','candidate_validation':validation,
        'manifest':{'path':str(manifest),'sha256':expected_manifest_sha256},'fixed_split_policy':policy,'scope_rows':'ALL_PHYSICAL_MANIFEST_SCENES','aggregate_physical_row_count':len(document['scenes']),'physical_row_counts_by_fixed_split':row_counts,
        'eligibility_recomputed':False,'quality_status_used_as_filter':False,'readiness_gate_revalidated':False,'boundary_status':'BOUNDARY_NOT_USED',
        'planned_source_header_count':len(sources),'source_header_attempt_count':len(source_results),'max_source_headers':max_source_headers,
        'pair_plan_evaluated':plan_valid,'planned_cross_split_pair_count':len(pairs) if plan_valid else None,'pair_diagnostic_record_count':len(pair_results),'intersection_attempt_count':intersection_attempts,'max_pairs':max_pairs,
        'within_split_pair_count_out_of_scope':within,'within_split_pair_status':'OUT_OF_SCOPE','shared_source_cross_split_findings':shared,
        'positive_area_overlap_candidate_count':sum(pair['status']=='POSITIVE_AREA_OVERLAP' for pair in pair_results),'positive_area_overlap_candidates':[pair for pair in pair_results if pair['status']=='POSITIVE_AREA_OVERLAP'],
        'source_footprints':source_results,'pair_results':pair_results,'issues':issues,'geometry_runtime':geometry_runtime,'projection_runtime':projection_runtime,'safe_gdal_options':SAFE_GDAL_OPTIONS.copy(),
        'footprint_method':'FOUR_PIXEL_EDGE_CORNERS_STRAIGHT_SEGMENTS','area_units':'square_degrees_planar_diagnostic','curved_edges_densified':False,'exact_raster_footprint_verified':False,
        'source_content_sha_revalidated':False,'pixel_arrays_read':False,'eligible_subset_leakage_assessed':False,'training_split_leakage_resolved':False,
        'geometric_independence_verified':False,'original_geometry_reprojected_or_written':False,'automatic_geometry_repair_performed':False,
        'exactly_once_applied':'UNKNOWN','ready_for_training':False,'training_executed':False,'scientific_accuracy_validated':False,
        'settlement_authorized':False,'execution_authorized':False,'automatic_resume_allowed':False,'proposed_refund_bytes':0,'network_requests':0,'source_files_written':0,
        'limitation':'All physical manifest rows and corner-proxy candidates only; not the eligible subset, exact footprint, pixel overlap, split leakage resolution, readiness/accuracy approval or recovery authorization.'}
