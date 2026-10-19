"""First Group 6개 주·2020~2025 자료의 실제 파일/품질/공통 holdout을 감사한다."""
import argparse
import json
import math
import random
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np

PROJECT_ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT_ROOT))
from backend.app.ml.dataset import file_digest
from backend.app.ml.raster import read, safe_path, assert_aligned, CLASS_NAMES, ESRI_IO_MAPPING, ESRI_IO_CLASS_NAMES

PROVINCES = {
    'south_sulawesi':('South Sulawesi','Sulawesi Selatan'),
    'gorontalo':('Gorontalo',),
    'southeast_sulawesi':('Southeast Sulawesi','Sulawesi Tenggara'),
    'banten':('Banten',),
    'west_java':('West Java','Jawa Barat'),
    'east_java':('East Java','Jawa Timur'),
}
YEARS=list(range(2020,2026))
WORLD_COVER={10:1,20:5,30:2,40:4,50:6,60:7,70:8,80:0,90:3,95:1,100:2}


def normalized(value):
    return '_'.join(str(value).strip().lower().replace('-',' ').replace('_',' ').split())


def province_id(value):
    value=normalized(value)
    if value.endswith('_candidate'):
        value=value[:-10]
    for identifier,names in PROVINCES.items():
        if value==identifier or value in {normalized(name) for name in names}:
            return identifier
    return None


def holdout_plan(records, seed=42):
    """같은 주 또는 원본 장면을 연결요소로 묶어 모든 연차에 같은 분할을 적용한다."""
    parents={province:province for province in PROVINCES}
    def find(value):
        while parents[value]!=value:
            parents[value]=parents[parents[value]]
            value=parents[value]
        return value
    def union(first,second):
        a,b=find(first),find(second)
        if a!=b:
            parents[max(a,b)]=min(a,b)
    sources={}
    for record in records:
        province=record['province']
        for token in (record.get('source_group'), record.get('image_sha256')):
            if token:
                if token in sources:
                    union(province,sources[token])
                sources[token]=province
    components={}
    for province in parents:
        components.setdefault(find(province),[]).append(province)
    groups=sorted(components)
    if len(groups)<3:
        return {'status':'blocked_insufficient_independent_source_groups','components':components,'province_splits':{},'seed':seed}
    random.Random(seed).shuffle(groups)
    n_train=min(len(groups)-2,max(1,round(len(groups)*.7)))
    n_val=min(len(groups)-n_train-1,max(1,round(len(groups)*.15)))
    splits={province:('train' if index<n_train else 'val' if index<n_train+n_val else 'test')
            for index,group in enumerate(groups) for province in components[group]}
    return {'status':'planned_not_independently_validated','seed':seed,'components':components,
            'province_splits':splits,'province_counts':{split:list(splits.values()).count(split) for split in ('train','val','test')},
            'target_province_counts':{'train':4,'val':1,'test':1},
            'policy':'all years and tiles of each province and shared source group stay together; shared-source constraints override target counts',
            'independent_expert_reference_required':True}


def inspect_scene(row, root, min_fraction, boundary_geometry=None):
    image_path=safe_path(root,row['image_path'])
    image,imask,profile=read(image_path)
    h,w=profile['height'],profile['width']
    result={'image_path':str(image_path.relative_to(root)),'image_sha256':file_digest(image_path),
            'shape':list(image.shape),'crs':str(profile['crs']),'resolution':[abs(profile['transform'].a),abs(profile['transform'].e)],
            'input_band_count_sufficient':image.shape[0]>=3,'input_band_order':row.get('bands','unknown'),
            'nominal_patch_count':math.ceil(h/256)*math.ceil(w/256),
            'actual_256_patch_count':(h//256)*(w//256),'nonempty_patch_count':0,'eligible_patch_count':0,
            'source_group':row.get('source_group',row.get('scene_id')),
            'source':row.get('source',row.get('scene_id','unverified')),'license':row.get('license','unverified'),
            'acquisition_date':row.get('acquisition_date',row.get('datetime')),
            'full_original_scene':bool(row.get('full_original_scene',False)),
            'province_boundary_pixel_ratio':None,
            'label_status':'missing','valid_pixel_ratio':None,'class_counts':{},'quality_mask':row.get('quality_mask','unverified')}
    if not row.get('label_path'):
        return result
    label_path=safe_path(root,row['label_path'])
    label,lmask,lp=read(label_path)
    assert_aligned(profile,lp)
    valid=imask & lmask & np.isfinite(image).all(0)
    if boundary_geometry is not None:
        from rasterio.features import geometry_mask
        from rasterio.warp import transform_geom
        geometry=transform_geom('EPSG:4326',profile['crs'],boundary_geometry)
        inside=geometry_mask([geometry],out_shape=(h,w),transform=profile['transform'],invert=True)
        result['province_boundary_pixel_ratio']=float(inside.mean())
        valid &= inside
    if row.get('quality_mask_path'):
        quality,qvalid,qp=read(safe_path(root,row['quality_mask_path']))
        assert_aligned(profile,qp);valid &= qvalid & (quality[0]>0)
    source=row.get('label_source','classes')
    if source in ('worldcover','esri_io'):
        mapped=np.full((h,w),255,dtype='uint8')
        for original,target in (ESRI_IO_MAPPING if source=='esri_io' else WORLD_COVER).items():
            mapped[label[0]==original]=target
        valid &= mapped!=255
    elif source=='dynamic_world':
        if label.shape[0]!=9:
            raise ValueError('Dynamic World에는 공식 순서 9개 확률 밴드가 필요합니다.')
        valid &= np.isfinite(label).all(0) & (label>=0).all(0) & (label<=1).all(0)
        valid &= np.isclose(label.sum(0),1,atol=.03) & (label.max(0)>=.8)
        mapped=label.argmax(0)
    elif source=='classes':
        mapped=label[0];valid &= (mapped>=0) & (mapped<9) & (mapped==np.floor(mapped))
    else:
        raise ValueError('지원하지 않는 라벨 출처입니다.')
    for y in range(0,h,256):
        for x in range(0,w,256):
            patch=valid[y:y+256,x:x+256]
            result['nonempty_patch_count']+=int(patch.any())
            if image.shape[0]>=3 and patch.shape==(256,256) and patch.mean()>=min_fraction:
                result['eligible_patch_count']+=1
    values,counts=np.unique(mapped[valid],return_counts=True)
    observed=str(result['acquisition_date'] or '')[:4]
    requested=str(row.get('year',''))
    result.update(label_status='aligned_local_file_verified',label_path=str(label_path.relative_to(root)),label_sha256=file_digest(label_path),
                  label_source=source,valid_pixel_ratio=float(valid.mean()),valid_pixels=int(valid.sum()),
                  class_counts={str(int(value)):int(count) for value,count in zip(values,counts)},
                  acquisition_year_match=(observed==requested) if observed.isdigit() else None)
    result['class_count']=len(values)
    result['class_names']=ESRI_IO_CLASS_NAMES if source=='esri_io' else CLASS_NAMES
    if source!='dynamic_world':
        raw_values,raw_counts=np.unique(label[0][valid],return_counts=True)
        result['raw_class_counts']={str(int(value)):int(count) for value,count in zip(raw_values,raw_counts)}
    else:
        result['raw_class_counts']=None
    label_year=row.get('label_year')
    try:
        label_year=int(label_year) if label_year is not None else None
    except (TypeError,ValueError):
        label_year=None
    result.update(label_year=label_year,label_year_match=(label_year==int(requested)) if label_year is not None else None,
                  label_year_basis=row.get('label_year_basis','declared_row_metadata' if label_year is not None else 'unknown'))
    return result


def audit(manifests, data_root, min_fraction=.8, seed=42):
    if not 0<min_fraction<=1:
        raise ValueError('min-valid-fraction은 0 초과 1 이하여야 합니다.')
    root=Path(data_root).resolve()
    boundary_path=root/'first-group-boundaries/selected-six.geojson'
    boundaries={}
    if boundary_path.exists():
        boundary_document=json.loads(boundary_path.read_text(encoding='utf-8'))
        for feature in boundary_document['features']:
            identifier=province_id(feature['properties'].get('province_id',feature['properties'].get('shapeName')))
            if identifier:
                boundaries[identifier]=feature['geometry']
    inventory=[]; excluded=[]; inputs=[]
    seen=set(); seen_pairs={}
    for manifest_path in manifests:
        manifest_path=Path(manifest_path).resolve()
        document=json.loads(manifest_path.read_text(encoding='utf-8'))
        label_registry={}
        # 수집기가 보존한 원본 URL과 해시가 일치하는 경우에만 WC 제품 연도를 보완한다.
        registry_directory=manifest_path.parent/'manifests'
        if registry_directory.is_dir():
            for registry_path in registry_directory.glob('*.json'):
                metadata=json.loads(registry_path.read_text(encoding='utf-8'))
                match=re.search(r'/v(?:100|200)/(2020|2021)/',str(metadata.get('source','')))
                if match and metadata.get('sha256'):
                    label_registry[metadata['sha256']]=int(match.group(1))
        inputs.append({'path':str(manifest_path),'sha256':file_digest(manifest_path),'declared_synthetic':document.get('synthetic',None)})
        for row in document.get('scenes',[]):
            province=province_id(row.get('province_id',row.get('province',row.get('aoi',row.get('group','')))))
            try:
                year=int(row.get('year'))
            except (TypeError,ValueError):
                year=None
            if province is None or year not in YEARS:
                excluded.append({'province_input':row.get('aoi',row.get('province')),'year':row.get('year'),'reason':'outside_First_Group_or_2020_2025'})
                continue
            identity=(province,year,str(row.get('image_path','')))
            if identity in seen:
                continue
            seen.add(identity)
            entry={'province':province,'year':year,'manifest_path':str(manifest_path),'declared_status':row.get('status'),
                   'synthetic':bool(document.get('synthetic',False)),'image_status':'missing','error':None}
            if row.get('image_path'):
                try:
                    entry.update(inspect_scene({**row,'label_path':None},root,min_fraction),image_status='local_file_verified')
                    if row.get('label_path'):
                        entry.update(inspect_scene(row,root,min_fraction,boundaries.get(province)))
                        if entry.get('label_year') is None and entry.get('label_sha256') in label_registry:
                            label_year=label_registry[entry['label_sha256']]
                            entry.update(label_year=label_year,label_year_match=label_year==year,label_year_basis='registered_source_url_sha256_matched')
                except Exception as exc:
                    entry.update(error=f'{type(exc).__name__}: {exc}')
            pair=(entry.get('image_sha256'),entry.get('label_sha256'))
            if all(pair):
                if pair in seen_pairs:
                    entry.update(duplicate_raster_pair=True,duplicate_of=seen_pairs[pair],eligible_patch_count=0)
                else:
                    seen_pairs[pair]={'province':province,'year':year,'image_path':entry.get('image_path')}
            inventory.append(entry)
    cells=[]
    for province in PROVINCES:
        for year in YEARS:
            rows=[row for row in inventory if row['province']==province and row['year']==year]
            actual=[row for row in rows if row.get('image_status')=='local_file_verified' and not row['synthetic']]
            labels=[row for row in actual if row.get('label_status')=='aligned_local_file_verified' and row.get('valid_pixels',0)>0 and row.get('acquisition_year_match') is not False]
            temporal=[row for row in labels if row.get('label_year_match') is True and row.get('acquisition_year_match') is True]
            cells.append({'province':province,'year':year,'image_available':bool(actual),'label_available':bool(labels),
                          'temporally_matched_label_available':bool(temporal),'full_original_available':any(row.get('full_original_scene') for row in actual),
                          'nominal_patch_count':sum(row.get('nominal_patch_count',0) for row in actual),
                          'actual_256_patch_count':sum(row.get('actual_256_patch_count',0) for row in actual),
                          'eligible_patch_count':sum(row.get('eligible_patch_count',0) for row in labels),
                          'temporally_eligible_patch_count':sum(row.get('eligible_patch_count',0) for row in temporal)})
    verified=[row for row in inventory if row.get('image_status')=='local_file_verified' and not row['synthetic']]
    plan=holdout_plan(verified,seed)
    component_by_province={province:component for component,provinces in plan.get('components',{}).items() for province in provinces}
    for row in inventory:
        row['split']=plan.get('province_splits',{}).get(row['province'])
        row['dataset_group']=component_by_province.get(row['province'])
    total_eligible=sum(cell['eligible_patch_count'] for cell in cells)
    temporal_eligible=sum(cell['temporally_eligible_patch_count'] for cell in cells)
    missing_images=[{'province':cell['province'],'year':cell['year']} for cell in cells if not cell['image_available']]
    missing_labels=[{'province':cell['province'],'year':cell['year']} for cell in cells if not cell['label_available']]
    missing_temporal=[{'province':cell['province'],'year':cell['year']} for cell in cells if not cell['temporally_matched_label_available']]
    complete=not missing_images and not missing_labels and not missing_temporal
    eligible_by_split={split:sum(cell['temporally_eligible_patch_count'] for cell in cells if plan.get('province_splits',{}).get(cell['province'])==split) for split in ('train','val','test')}
    return {'audit_at':datetime.now(timezone.utc).isoformat(),'expected_provinces':[{'id':key,'names':names} for key,names in PROVINCES.items()],
            'boundary_reference':{'path':str(boundary_path),'sha256':file_digest(boundary_path) if boundary_path.exists() else None,
                                  'status':'public_2017_ADM1_reference_not_official_current_approval' if boundaries else 'missing'},
            'expected_years':YEARS,'expected_combinations':36,'inputs':inputs,'inventory':inventory,'excluded':excluded,'cells':cells,
            'missing_images':missing_images,'missing_labels':missing_labels,'image_cells_available':36-len(missing_images),
            'label_cells_available':36-len(missing_labels),'actual_256_patch_count':sum(cell['actual_256_patch_count'] for cell in cells),
            'temporally_matched_label_cells':36-len(missing_temporal),'missing_label_year_matches':missing_temporal,
            'full_original_cells_available':sum(cell['full_original_available'] for cell in cells),
            'all_36_full_original_scenes_available':all(cell['full_original_available'] for cell in cells),
            'nominal_patch_count':sum(cell['nominal_patch_count'] for cell in cells),'eligible_patch_count':total_eligible,
            'temporally_eligible_patch_count':temporal_eligible,
            'temporally_eligible_patches_by_split':eligible_by_split,
            'all_splits_have_eligible_patches':all(eligible_by_split.values()),
            'eligibility_rule':{'patch_size':256,'full_size_required':True,'min_valid_fraction':min_fraction},
            'target_patch_range':[1000,3000],'target_patch_count_met':temporal_eligible>=1000,
            'all_36_image_label_combinations_available':complete,'holdout':plan,
            'learning_ready':False,'independent_expert_evaluation_available':False,
            'readiness_statement':'재고 검사는 원본/라벨36조합·1000개이상유효패치·출처/시기·전문가독립검증을 대체하지 않습니다. 경계승인·물리반사도·라벨품질의 별도 검토가 필요합니다.',
            'previous_baseline_scope':'기존3지역 baseline에는 First Group 외 Central Java가 포함됩니다. First Group 모델 성능이 아닙니다.'}


def main():
    if hasattr(sys.stdout,'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,nargs='+',required=True)
    parser.add_argument('--data-root',type=Path,default=PROJECT_ROOT/'data')
    parser.add_argument('--config',type=Path,default=PROJECT_ROOT/'configs/first-group.collection.json')
    parser.add_argument('--output',type=Path,default=PROJECT_ROOT/'data/first-group/quality-audit.json')
    parser.add_argument('--min-valid-fraction',type=float,default=.8)
    parser.add_argument('--seed',type=int,default=42)
    args=parser.parse_args()
    if args.config.exists():
        config=json.loads(args.config.read_text(encoding='utf-8'))
        configured={province_id(row.get('province_id',row.get('id',row.get('name')))) for row in config.get('aois',[])}
        if configured!=set(PROVINCES):
            raise ValueError('First Group config의 주 목록은 사용자 지정 6개 주와 같아야 합니다.')
    result=audit(args.manifest,args.data_root,args.min_valid_fraction,args.seed)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({key:result[key] for key in ['expected_combinations','image_cells_available','label_cells_available','eligible_patch_count','learning_ready']},ensure_ascii=False))
    # 부족한 자료는 정상 감사결과이며, learning_ready를 성공으로 바꾸지 않는다.
    return 0


if __name__=='__main__':
    raise SystemExit(main())
