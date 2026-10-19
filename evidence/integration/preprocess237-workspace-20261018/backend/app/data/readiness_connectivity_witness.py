"""Prospective caller-asserted eligible metadata connectivity; never a readiness decision.

No file IO, raster/geometry engine access, eligibility assessment, or historical
reconstruction. Token and strict-positive bounding-box unions mirror the bounded
metadata portion of the current readiness algorithm only.
"""
from collections import Counter
import math

PROVINCES = ('south_sulawesi','gorontalo','southeast_sulawesi','banten','west_java','east_java')
FIXED_PROVINCE_SPLITS = {'south_sulawesi':'train','gorontalo':'train','southeast_sulawesi':'train','east_java':'train','banten':'val','west_java':'test'}
CAPS = {'max_scenes':2000,'max_bbox_pairs':2000000,'max_witness_edges':10000}
MAX_STRING_LENGTH = 4096


def _number(value):
    if type(value) not in (int,float):return False
    try:return math.isfinite(value)
    except (ValueError,OverflowError):return False


def _policy(mapping):
    if type(mapping) is not dict or set(mapping)!=set(PROVINCES) or any(type(k) is not str or type(v) is not str for k,v in mapping.items()) or mapping!=FIXED_PROVINCE_SPLITS:
        raise ValueError('Explicit current six-province fixed 4/1/1 split mapping required')
    return dict(mapping)


def diagnose_readiness_connectivity(eligible_scenes, province_splits=None, *, max_scenes=2000, max_bbox_pairs=1000000, max_witness_edges=10000):
    """Return bounded witnesses for supplied metadata, not retroactive gate evidence.

    Each scene requires unique nonnegative int ``scene_index``, a known province,
    string ``source_group`` and ``scene_id`` (at most 4096 code points), and finite
    positive-area geographic ``bounds_wgs84=[xmin,ymin,xmax,ymax]``. Empty group
    skips *both* token roles, preserving readiness semantics; bbox still applies.
    The ordered list determines last-seen token ownership. Scene indexes are
    caller-supplied identifiers, never recovered original-manifest indexes.
    """
    limits={'max_scenes':max_scenes,'max_bbox_pairs':max_bbox_pairs,'max_witness_edges':max_witness_edges}
    for key,value in limits.items():
        minimum=0 if key=='max_witness_edges' else 1
        if type(value) is not int or not minimum<=value<=CAPS[key]:raise ValueError('Invalid bounded integer limit: '+key)
    mapping=_policy(province_splits) if province_splits is not None else None
    base={'schema_version':1,'kind':'PROSPECTIVE_ELIGIBLE_METADATA_CONNECTIVITY_WITNESS','mode':'PURE_DIAGNOSTIC','status':'BLOCKED',
      'input_eligibility':'CALLER_ASSERTED_NOT_VERIFIED','eligibility_verified':False,'historical_readiness_cause_reconstructed':False,
      'fixed_province_splits':mapping,'scope':'SUPPLIED_ELIGIBLE_METADATA_ONLY','source_files_read':0,'pixel_arrays_read':False,
      'geometry_engine_called':False,'readiness_assess_called':False,'source_files_written':0,'network_requests':0,
      'ready_for_training':False,'scientific_accuracy_validated':False,'training_executed':False,'training_split_leakage_resolved':False,
      'settlement_authorized':False,'execution_authorized':False,'automatic_resume_allowed':False,'proposed_refund_bytes':0,
      'exactly_once_applied':'UNKNOWN','complete_spatial_separation_claimed':False,'limits':limits,
      'limitation':'Prospective caller-asserted eligible metadata only; not recovered historical eligible scenes, token/bbox causes, exact geometry independence, split leakage resolution, scientific or operational approval.'}
    if eligible_scenes is None:
        return {**base,'input_eligibility':'UNKNOWN_NOT_PERSISTED','diagnostic_status':'UNKNOWN_NOT_PERSISTED','scene_count':None,
          'bbox_pair_plan_count':None,'bbox_pairs_evaluated':0,'token_occurrences_processed':0,'union_complete':False,'union_change_count':None,
          'witness_edges':[],'witness_edge_count_total':0,'witness_edge_count_stored':0,'witness_edge_counts_by_kind':{'TOKEN_SHARED_NAMESPACE':None,'BBOX_STRICT_POSITIVE_OVERLAP':None},'witness_edges_truncated':False,
          'witness_edge_coverage':'NOT_STARTED','input_token_metadata_complete':None,'province_components':None,'components':None,'fixed_split_conflicts':None,
          'fixed_split_conflict_events':None,'fixed_split_assignments_changed':False,'no_cross_split_connectivity_found_in_supplied_metadata':None,'issues':[]}
    if mapping is None:raise ValueError('Explicit province split mapping required for supplied scenes')
    if type(eligible_scenes) is not list or len(eligible_scenes)>max_scenes:raise ValueError('Scene metadata must be a list within the scene limit')
    pair_count=len(eligible_scenes)*(len(eligible_scenes)-1)//2
    if pair_count>max_bbox_pairs:raise ValueError('Full bbox pair plan exceeds budget; no union or witness work performed')
    # Complete validation and detached copy precede every union/token/bbox operation.
    scenes=[];indexes=set()
    for position,scene in enumerate(eligible_scenes):
        if type(scene) is not dict:raise ValueError('Scene metadata requires object')
        index=scene.get('scene_index');province=scene.get('province')
        if type(index) is not int or index<0 or index>2**63-1 or index in indexes:raise ValueError('Scene index requires unique nonnegative signed-64-bit integer')
        indexes.add(index)
        if type(province) is not str or province not in mapping:raise ValueError('Scene province invalid')
        for role in ['source_group','scene_id']:
            if type(scene.get(role)) is not str or len(scene[role])>MAX_STRING_LENGTH:raise ValueError('Bounded literal string required: '+role)
        bbox=scene.get('bounds_wgs84')
        if type(bbox) is not list or len(bbox)!=4 or not all(_number(v) for v in bbox):raise ValueError('Finite numeric four-coordinate bounds required')
        xmin,ymin,xmax,ymax=bbox
        if not -180<=xmin<xmax<=180 or not -90<=ymin<ymax<=90:raise ValueError('Bounds must have positive area inside geographic coordinate ranges; wrapped boxes unsupported')
        scenes.append({'scene_index':index,'eligible_position':position,'province':province,'source_group':scene['source_group'],'scene_id':scene['scene_id'],'bounds_wgs84':list(bbox)})
    parents={p:p for p in PROVINCES};last_owner={};edges=[];issues=[]
    counts={'TOKEN_SHARED_NAMESPACE':0,'BBOX_STRICT_POSITIVE_OVERLAP':0};token_occurrences=0;union_changes=0
    def find(province):
        while parents[province]!=province:province=parents[province]
        return province
    def union(left,right):
        nonlocal union_changes
        a,b=find(left),find(right);changed=a!=b
        parents[max(a,b)]=min(a,b)
        if changed:union_changes+=1
        return changed
    def endpoint(scene,role=None):
        result={key:scene[key] for key in ['scene_index','eligible_position','province']}
        if role is not None:result['token_role']=role
        return result
    def witness(event):
        counts[event['kind']]+=1
        if len(edges)<max_witness_edges:edges.append(event)
    for scene in scenes:
        if not scene['source_group']:
            issues.append({'code':'SOURCE_GROUP_MISSING','scene_index':scene['scene_index'],'eligible_position':scene['eligible_position'],'token_roles_skipped':['source_group','scene_id'],'bbox_participation_preserved':True})
            continue
        for role in ['source_group','scene_id']:
            token=scene[role];token_occurrences+=1
            if token in last_owner:
                previous,previous_role=last_owner[token]
                changed=union(scene['province'],previous['province'])
                witness({'kind':'TOKEN_SHARED_NAMESPACE','token':token,'left':endpoint(scene,role),'right':endpoint(previous,previous_role),'component_union_changed':changed})
            last_owner[token]=(scene,role)
    evaluated=0
    for index,scene in enumerate(scenes):
        a=scene['bounds_wgs84']
        for other in scenes[:index]:
            evaluated+=1;b=other['bounds_wgs84']
            if min(a[2],b[2])>max(a[0],b[0]) and min(a[3],b[3])>max(a[1],b[1]):
                changed=union(scene['province'],other['province'])
                witness({'kind':'BBOX_STRICT_POSITIVE_OVERLAP','left':endpoint(scene),'right':endpoint(other),
                  'left_bounds_wgs84':list(a),'right_bounds_wgs84':list(b),
                  'overlap_bounds_wgs84':[max(a[0],b[0]),max(a[1],b[1]),min(a[2],b[2]),min(a[3],b[3])],
                  'comparison':'STRICT_POSITIVE_BOTH_AXES','component_union_changed':changed})
    province_components={p:find(p) for p in PROVINCES};components=[];conflicts=[]
    observed=Counter(s['province'] for s in scenes)
    for root in sorted(set(province_components.values())):
        provinces=[p for p in PROVINCES if province_components[p]==root];splits=sorted({mapping[p] for p in provinces})
        item={'component':root,'provinces':provinces,'fixed_splits':splits,'supplied_scene_count':sum(observed[p] for p in provinces)}
        components.append(item)
        if len(splits)>1:conflicts.append({'code':'SHARED_SOURCE_CROSSES_FIXED_SPLIT_IN_SUPPLIED_METADATA',**item})
    # Preserve current gate's last-assigned component-split traversal, including
    # transitive and within-split unions, without changing any split assignment.
    component_splits={};conflict_events=[]
    for province in PROVINCES:
        component=province_components[province];split=mapping[province]
        if component in component_splits and component_splits[component]!=split:
            conflict_events.append({'code':'SHARED_SOURCE_CROSSES_FIXED_SPLIT','province':province,'component':component,'previous_fixed_split':component_splits[component],'current_fixed_split':split})
        component_splits[component]=split
    total=sum(counts.values());truncated=total>len(edges)
    return {**base,'diagnostic_status':'SUPPLIED_METADATA_DIAGNOSED' if scenes else 'NO_SUPPLIED_ELIGIBLE_SCENES','scene_count':len(scenes),
      'bbox_pair_plan_count':pair_count,'bbox_pairs_evaluated':evaluated,'token_occurrences_processed':token_occurrences,'union_complete':True,
      'union_change_count':union_changes,'witness_edges':edges,'witness_edge_count_total':total,'witness_edge_count_stored':len(edges),
      'witness_edge_counts_by_kind':counts,'witness_edges_truncated':truncated,
      'witness_edge_coverage':'TRUNCATED_UNION_COMPLETE' if truncated else 'COMPLETE' if scenes else 'NO_SCENES',
      'province_components':province_components,'components':components,'fixed_split_conflicts':conflicts,
      'fixed_split_conflict_events':conflict_events,'fixed_split_assignments_changed':False,
      'input_token_metadata_complete':not bool(issues),
      'no_cross_split_connectivity_found_in_supplied_metadata':False if conflicts else True if scenes and not issues else None,'issues':issues}
