"""고정 지역 분할의 원본 누출을 제거할 파생 데이터 계획. 학습과 파일 재감사를 실행하지 않는다."""
import copy
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from .split_json_io import bounded_io,_local


def digest(path, *, io_policy=None, role='source'):
    io=bounded_io(io_policy)
    if io is not None:return io.read(path,role)[1]
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _load_bound(path, expected, *, io_policy=None, role='source'):
    io=bounded_io(io_policy)
    if io is not None:
        if type(expected) is not str or re.fullmatch(r'[0-9a-f]{64}',expected) is None:raise ValueError('Explicit lowercase SHA-256 is required')
        return io.read(path,role,expected)[0]
    if not isinstance(expected,str) or not re.fullmatch(r'[0-9a-f]{64}',expected):
        raise ValueError('명시적인 소문자 SHA-256이 필요합니다.')
    payload=Path(path).read_bytes()
    if hashlib.sha256(payload).hexdigest()!=expected:
        raise ValueError('입력 SHA-256 불일치 또는 stale 입력입니다.')
    return json.loads(payload)


def plan_split_repair(manifest_path, expected_sha256, *, province_splits,
                      readiness_path=None, readiness_sha256=None, data_root=None, io_policy=None):
    """test→val→train의 클래스/성능 비참조 우선순위로 한 split만 보존한다."""
    io=bounded_io(io_policy)
    logical_manifest=manifest_path
    if io is not None:source=_load_bound(logical_manifest,expected_sha256,io_policy=io)
    manifest_path=Path(manifest_path).resolve()
    if io is None:source=_load_bound(manifest_path,expected_sha256)
    rows=source.get('scenes')
    if not isinstance(rows,list) or not rows:
        raise ValueError('비어 있지 않은 scenes가 필요합니다.')
    if not province_splits or set(province_splits.values())!={'train','val','test'}:
        raise ValueError('train/val/test 고정 지역 분할이 필요합니다.')
    parents=list(range(len(rows)))
    def find(index):
        while parents[index]!=index:
            parents[index]=parents[parents[index]];index=parents[index]
        return index
    seen={}
    for index,row in enumerate(rows):
        if row.get('province') not in province_splits:
            raise ValueError('고정 split에 없는 province입니다.')
        split=province_splits[row['province']]
        if row.get('split') is not None and row['split']!=split:
            raise ValueError('원본 행 split과 고정 province split이 다릅니다.')
        if not row.get('scene_id') or not row.get('source_group'):
            raise ValueError('실제 scene_id와 source_group 식별자가 필요합니다.')
        if row.get('quality_status') not in ('quality_eligible','quality_insufficient'):
            raise ValueError('명시적인 수집 품질 상태가 필요합니다.')
        tokens=['source:'+str(row['scene_id']),'source:'+str(row['source_group'])]
        image_hash=(row.get('patch_sha256') or {}).get('image')
        if image_hash:
            if not re.fullmatch(r'[0-9a-f]{64}',str(image_hash)):
                raise ValueError('기록된 영상 SHA-256 형식이 잘못됐습니다.')
            tokens.append('image:'+image_hash)
        for token in tokens:
            if token in seen:
                parents[find(index)]=find(seen[token])
            seen[token]=index
    components=defaultdict(list)
    for index in range(len(rows)):
        components[find(index)].append(index)
    conflicts=[];excluded=set();priority={'test':0,'val':1,'train':2}
    for indexes in components.values():
        splits={province_splits[rows[i]['province']] for i in indexes}
        if len(splits)<2:
            continue
        owner=min(splits,key=priority.get)
        removed=[i for i in indexes if province_splits[rows[i]['province']]!=owner]
        excluded.update(removed)
        conflicts.append({'scene_ids':sorted({rows[i]['scene_id'] for i in indexes}),
                          'source_groups':sorted({rows[i]['source_group'] for i in indexes}),
                          'row_indexes':indexes,'keep_split':owner,'excluded_row_indexes':removed})
    retained=[i for i in range(len(rows)) if i not in excluded]
    def counts(indexes):
        split_counts={s:0 for s in priority};cells=Counter()
        for i in indexes:
            row=rows[i]
            if row['quality_status']=='quality_eligible':
                split_counts[province_splits[row['province']]]+=1
                cells[(row['province'],int(row['year']))]+=1
        return {'eligible_patches_by_split':split_counts,'eligible_total':sum(split_counts.values()),
                'eligible_by_province_year':{f'{p}/{y}':n for (p,y),n in sorted(cells.items())}}
    before=counts(range(len(rows)));after=counts(retained)
    cells=set(before['eligible_by_province_year'])|set(after['eligible_by_province_year'])
    degraded=[{'cell':cell,'before':before['eligible_by_province_year'].get(cell,0),
               'after':after['eligible_by_province_year'].get(cell,0)} for cell in sorted(cells)
              if after['eligible_by_province_year'].get(cell,0)<before['eligible_by_province_year'].get(cell,0)]
    class_impact={'status':'UNKNOWN_REQUIRES_DERIVED_READINESS','exact_after_counts_computed':False,
                  'bare_shortage_resolved':False,'independent_scientific_validation':False}
    readiness_ref=None;policy={}
    if readiness_path is not None:
        readiness=_load_bound(readiness_path,readiness_sha256,io_policy=io,role='readiness')
        if data_root is None:
            raise ValueError('readiness 출처 확인용 data_root가 필요합니다.')
        references=readiness.get('input_manifests',[])
        if len(references)!=1 or (Path(data_root)/references[0]['path']).resolve()!=manifest_path or references[0].get('sha256')!=expected_sha256:
            raise ValueError('readiness가 현재 단일 원본 manifest와 일치하지 않습니다(stale).')
        if readiness.get('patch_counts_by_split')!=before['eligible_patches_by_split']:
            raise ValueError('readiness와 manifest 적격 split 계수가 다릅니다(stale).')
        policy=readiness['policy']
        if policy['province_splits']!=province_splits:
            raise ValueError('readiness의 고정 split이 다릅니다.')
        readiness_ref={'path':str(Path(readiness_path).resolve()),'sha256':readiness_sha256}
        class_impact['status']='CONSERVATIVE_BOUNDS_ONLY'
        class_impact['by_split']={}
        for split in priority:
            prior=readiness['class_counts_by_split'][split]
            patches=readiness['class_patch_counts_by_split'][split]
            if len(prior)!=9 or len(patches)!=9 or any(type(x) is not int or x<0 for x in prior+patches):
                raise ValueError('readiness 클래스 계수가 유효하지 않습니다.')
            removed=before['eligible_patches_by_split'][split]-after['eligible_patches_by_split'][split]
            minimum_pixels=after['eligible_patches_by_split'][split]*policy['patch_size']**2*policy['min_valid_fraction']
            class_impact['by_split'][split]={'removed_eligible_patches':removed,
                'class_pixel_lower_bounds':[max(0,n-removed*policy['patch_size']**2) for n in prior],
                'class_pixel_upper_bounds':prior,
                'class_patch_upper_bounds':patches,
                'bare_ratio_upper_bound':min(1,prior[7]/minimum_pixels) if minimum_pixels else None,
                'bare_patch_upper_bound':patches[7],
                'class_representation_can_worsen':removed>0}
    version_material={'source_sha256':expected_sha256,'keep_priority':['test','val','train'],'province_splits':province_splits,
                      'retained_row_indexes':retained,'planner_version':'split-repair-v1'}
    version='split-repair-v1-'+hashlib.sha256(json.dumps(version_material,sort_keys=True).encode()).hexdigest()[:16]
    if io is not None:io.verify()
    return {'schema_version':1,'status':'PLAN_ONLY','evidence_state':'VERIFIED_REAL_METADATA_ONLY' if not source.get('synthetic') else 'TESTED_SYNTHETIC',
            'planner_version':'split-repair-v1','derived_manifest_version':version,
            'source_manifest':{'path':str(manifest_path),'sha256':expected_sha256},'readiness_reference':readiness_ref,
            'policy':{'province_splits':dict(province_splits),'keep_split_priority':['test','val','train'],
                      'selection_basis':'fixed priority; no labels, predictions or evaluation scores consulted',
                      'action':'exclude conflicting rows from a new candidate only; never reassign splits'},
            'conflicts':conflicts,'retained_row_indexes':retained,'excluded_row_indexes':sorted(excluded),
            'before':before,'projected_after':after,'degraded_province_year_cells':degraded,
            'projected_below_split_minimum':{s:after['eligible_patches_by_split'][s]<floor for s,floor in policy.get('min_patches_per_split',{'train':600,'val':100,'test':100}).items()},
            'projected_total_below_minimum':after['eligible_total']<policy.get('min_patches',1000),
            'class_impact':class_impact,'remaining_source_identity_conflicts':0,
            'spatial_overlap_rechecked':False,'ready_for_training':False,'training_executed':False,
            'scientific_accuracy_validated':False,
            'next_gate':'New candidate readiness must recheck all file hashes, spatial overlap, classes and source independence; independent labels and approval remain separate.'}


def write_plan(report, output, *, derived_manifest=None, io_policy=None):
    """새 경로만 생성하며, 출력 직전 원본 해시를 재확인한다."""
    io=bounded_io(io_policy)
    source=report['source_manifest'];document=_load_bound(source['path'],source['sha256'],io_policy=io)
    if io is not None:
        _local(output)
        if derived_manifest is not None:_local(derived_manifest)
    outputs=[Path(output).resolve()]+([Path(derived_manifest).resolve()] if derived_manifest else [])
    protected={Path(source['path']).resolve()}
    if report.get('readiness_reference'):
        protected.add(Path(report['readiness_reference']['path']).resolve())
        _load_bound(report['readiness_reference']['path'],report['readiness_reference']['sha256'],io_policy=io,role='readiness')
    if len(set(outputs))!=len(outputs) or any(p in protected or p.exists() for p in outputs):
        raise ValueError('원본/기존 파일을 덮어쓰지 않습니다. 서로 다른 새 출력 경로가 필요합니다.')
    if io is not None:
        logical_outputs=[_local(output)]+([_local(derived_manifest)] if derived_manifest else [])
        if any(p.is_symlink() or p.exists() for p in logical_outputs):raise ValueError('Only new output paths supported')
        parents=[p.parent.resolve() for p in logical_outputs]
        candidate=None
        if derived_manifest:
            candidate={'schema_version':1,'version':report['derived_manifest_version'],'status':'PLANNED_DERIVED_CANDIDATE',
                'executed':False,'learning_ready':False,'synthetic':bool(document.get('synthetic')),
                'lineage':{'source_manifest':source,'selection_policy':report['policy'],'source_row_indexes':report['retained_row_indexes']},
                'scenes':[copy.deepcopy(document['scenes'][i]) for i in report['retained_row_indexes']]}
        plan_size=io.measure(report,'plan')
        candidate_size=io.measure(candidate,'candidate') if candidate is not None else None
        io.verify()
        for logical,target,parent in zip(logical_outputs,outputs,parents):
            if logical.resolve()!=target or logical.parent.resolve()!=parent or logical.is_symlink() or logical.exists():raise ValueError('Output target changed or exists')
        for p in outputs:p.parent.mkdir(parents=True,exist_ok=True)
        for logical,target,parent in zip(logical_outputs,outputs,parents):
            if logical.resolve()!=target or logical.parent.resolve()!=parent:raise ValueError('Output parent changed')
        if candidate is not None:io.write(outputs[1],candidate,'candidate',candidate_size)
        io.write(outputs[0],report,'plan',plan_size)
        io.verify()
        return
    for p in outputs:
        p.parent.mkdir(parents=True,exist_ok=True)
    if derived_manifest:
        candidate={'schema_version':1,'version':report['derived_manifest_version'],'status':'PLANNED_DERIVED_CANDIDATE',
                   'executed':False,'learning_ready':False,'synthetic':bool(document.get('synthetic')),
                   'lineage':{'source_manifest':source,'selection_policy':report['policy'],
                              'source_row_indexes':report['retained_row_indexes']},
                   'scenes':[copy.deepcopy(document['scenes'][i]) for i in report['retained_row_indexes']]}
        with Path(derived_manifest).open('x',encoding='utf-8') as stream:
            json.dump(candidate,stream,ensure_ascii=False,indent=2)
    with Path(output).open('x',encoding='utf-8') as stream:
        json.dump(report,stream,ensure_ascii=False,indent=2)
