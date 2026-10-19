"""지역 단위 데이터 분할 및 반사도 패치 구성."""
import hashlib
import json
import random
from pathlib import Path
import numpy as np
from .raster import CLASS_NAMES, ESRI_IO_MAPPING, ESRI_IO_CLASS_NAMES, IGNORE, assert_aligned, read, safe_path
from .normalization import apply_normalization


def file_digest(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


def split_groups(groups, seed=42):
    groups = sorted(set(groups))
    if len(groups) < 3:
        raise ValueError('누출 없는 train/val/test 분할에는 독립적인 지역 그룹이 최소 3개 필요합니다.')
    random.Random(seed).shuffle(groups)
    # 작은 자료에서도 독립 검증/시험을 남기되 충분한 그룹에서는 70/15/15를 근사한다.
    n_train = min(len(groups)-2, max(1, round(len(groups)*.7)))
    n_val = min(len(groups)-n_train-1, max(1, round(len(groups)*.15)))
    return {group: ('train' if i < n_train else 'val' if i < n_train+n_val else 'test') for i, group in enumerate(groups)}


def prepare(payload, root):
    scenes = payload.get('scenes', [])
    if not scenes:
        raise ValueError('scenes에 영상·라벨·독립 지역 group을 지정하세요.')
    label_sources={s.get('label_source','classes') for s in scenes}
    if 'esri_io' in label_sources and label_sources!={'esri_io'}:
        raise ValueError('ESRI rangeland 실험에는 WC/DW 라벨을 혼합하지 않습니다.')
    class_names=payload.get('class_names',ESRI_IO_CLASS_NAMES if label_sources=={'esri_io'} else CLASS_NAMES)
    if not isinstance(class_names,list) or len(class_names)!=9 or not all(isinstance(name,str) and name for name in class_names) or ('esri_io' in label_sources and class_names!=ESRI_IO_CLASS_NAMES):
        raise ValueError('클래스 이름이 실제 라벨 분류체계와 다릅니다.')
    class_names=list(class_names)
    taxonomy={'label_sources':sorted(label_sources),'class_names':class_names,'esri_io_mapping':{str(k):v for k,v in ESRI_IO_MAPPING.items()} if label_sources=={'esri_io'} else None}
    taxonomy_signature=hashlib.sha256(json.dumps(taxonomy,sort_keys=True).encode()).hexdigest()
    group_ids={str(s['group']) for s in scenes}
    groups = payload.get('group_splits') or split_groups(group_ids, int(payload.get('seed', 42)))
    if set(groups)!=group_ids or set(groups.values())!={'train','val','test'}:
        raise ValueError('group_splits는 모든 독립 그룹을 train/val/test에 정확히 한 번 배정해야 합니다.')
    dataset_id = payload.get('dataset_id', 'dataset')
    destination = safe_path(root, f'datasets/{dataset_id}')
    if destination.exists():
        raise ValueError('기존 데이터셋을 덮어쓸 수 없습니다. 새 dataset_id를 사용하세요.')
    size = int(payload.get('patch_size', 256))
    if size < 16 or size > 1024 or size % 4:
        raise ValueError('patch_size는 16~1024의 4배수여야 합니다.')
    threshold = float(payload.get('confidence_threshold', .8))
    if not 0 <= threshold <= 1:
        raise ValueError('confidence_threshold는 0~1이어야 합니다.')
    scale, offset = payload.get('scale', .0001), payload.get('offset', 0)
    min_valid_fraction=float(payload.get('min_valid_fraction',0))
    if not 0<=min_valid_fraction<=1:
        raise ValueError('min_valid_fraction은 0~1이어야 합니다.')
    destination.mkdir(parents=True)
    entries, provenance, bands = [], [], payload.get('bands')
    expected_bands = None
    spatial_scenes = []
    for scene_index, scene in enumerate(scenes):
        image_path, label_path = safe_path(root, scene['image_path']), safe_path(root, scene['label_path'])
        image, image_valid, profile = read(image_path)
        from rasterio.transform import array_bounds
        from rasterio.warp import transform_bounds
        bounds = transform_bounds(profile['crs'], 'EPSG:4326', *array_bounds(profile['height'],profile['width'],profile['transform']), densify_pts=21)
        image_hash = file_digest(image_path)
        group = str(scene['group'])
        scene_id = str(scene.get('scene_id', scene['image_path']))
        for prior in spatial_scenes:
            if prior['group'] != group:
                overlap = min(bounds[2],prior['bounds'][2]) > max(bounds[0],prior['bounds'][0]) and min(bounds[3],prior['bounds'][3]) > max(bounds[1],prior['bounds'][1])
                if prior['hash'] == image_hash or prior['scene_id'] == scene_id or overlap:
                    raise ValueError('서로 다른 분할 그룹에 중복 영상·동일 scene_id·중첩 공간이 있습니다. 같은 장면의 인접 타일도 같은 group으로 지정하세요.')
        spatial_scenes.append({'group':group,'hash':image_hash,'scene_id':scene_id,'bounds':bounds})
        labels, label_valid, lp = read(label_path)
        assert_aligned(profile, lp)
        selected = bands or list(range(1, image.shape[0]+1))
        if expected_bands is None:
            expected_bands = selected
        elif selected != expected_bands:
            raise ValueError('모든 장면의 입력 밴드 순서와 개수가 같아야 합니다.')
        if not selected or min(selected) < 1 or max(selected) > image.shape[0]:
            raise ValueError('선택 밴드가 영상 범위를 벗어납니다.')
        normalization=scene.get('normalization') or {'scale':scale,'offset':offset}
        image = apply_normalization(image[np.asarray(selected)-1],normalization['scale'],normalization['offset'])
        valid = image_valid & label_valid & np.isfinite(image).all(axis=0)
        if scene.get('label_source', 'classes') == 'dynamic_world':
            if labels.shape[0] != 9:
                raise ValueError('Dynamic World는 공식 순서의 9개 확률 밴드가 필요합니다.')
            valid &= np.isfinite(labels).all(axis=0) & (labels >= 0).all(axis=0) & (labels <= 1).all(axis=0)
            valid &= np.isclose(labels.sum(axis=0), 1.0, atol=.03)
            valid &= labels.max(axis=0) >= threshold
            label = labels.argmax(axis=0).astype('uint8')
        elif scene.get('label_source') in ('worldcover','esri_io'):
            # 서로 다른 정의를 통합하는 초기 제안 매핑이며 전문가 확정 분류체계가 아니다.
            mapping = ESRI_IO_MAPPING if scene.get('label_source')=='esri_io' else {10:1,20:5,30:2,40:4,50:6,60:7,70:8,80:0,90:3,95:1,100:2}
            label = np.full(labels.shape[1:], IGNORE, dtype='uint8')
            for source, target in mapping.items():
                label[labels[0] == source] = target
            valid &= label != IGNORE
        else:
            label = labels[0]
            valid &= (label >= 0) & (label < 9) & (label == np.floor(label))
        # 별도 품질 마스크에서 0은 구름·그림자 등 학습 제외 픽셀이다.
        if scene.get('quality_mask_path'):
            mask, mask_valid, mp = read(safe_path(root, scene['quality_mask_path']))
            assert_aligned(profile, mp)
            valid &= mask_valid & (mask[0] > 0)
        label = np.where(valid, label, IGNORE).astype('uint8')
        image[:, ~valid] = 0
        for y in range(0, profile['height'], size):
            for x in range(0, profile['width'], size):
                xx = np.zeros((len(selected), size, size), dtype='float32')
                yy = np.full((size, size), IGNORE, dtype='uint8')
                h, w = min(size, profile['height']-y), min(size, profile['width']-x)
                if payload.get('require_full_patches',False) and (h<size or w<size):
                    continue
                xx[:, :h, :w] = image[:, y:y+h, x:x+w]
                yy[:h, :w] = label[y:y+h, x:x+w]
                if np.all(yy == IGNORE) or np.mean(yy!=IGNORE)<min_valid_fraction:
                    continue
                name = f'{scene_index}_{y}_{x}.npz'
                np.savez_compressed(destination/name, image=xx, label=yy)
                entries.append({'path': name, 'sha256':file_digest(destination/name),'split': groups[str(scene['group'])], 'group': str(scene['group'])})
        provenance.append({'image_path': str(image_path.relative_to(root)), 'label_path': str(label_path.relative_to(root)),
                           'image_sha256':image_hash,'label_sha256':file_digest(label_path),'bounds_wgs84':bounds,'scene_id':scene_id,
                           'quality_mask_path':scene.get('quality_mask_path'),
                           'quality_mask_sha256':file_digest(safe_path(root,scene['quality_mask_path'])) if scene.get('quality_mask_path') else None,
                           'normalization':normalization,'source_group':scene.get('source_group',scene_id),'province':scene.get('province'),'year':scene.get('year'),
                           'spatial_locations':scene.get('spatial_locations'),'spatial_location_id':scene.get('spatial_location_id'),
                           'label_year':scene.get('label_year'),'label_dataset_version':scene.get('label_dataset_version'),'label_source_url':scene.get('label_source_url'),
                           'source_window':scene.get('source_window'),
                           'license':scene.get('license','unverified'),'acquisition_date':scene.get('acquisition_date'),
                           'group': str(scene['group']), 'label_source': scene.get('label_source','classes'), 'source': scene.get('source','user supplied; license unverified')})
    counts = {s: sum(e['split']==s for e in entries) for s in ('train','val','test')}
    if not all(counts.values()):
        raise ValueError('유효한 학습·검증·시험 패치가 각각 하나 이상 필요합니다. 입력 품질과 그룹을 확인하세요.')
    band_names=payload.get('band_names')
    if band_names is not None and (not isinstance(band_names,list) or len(band_names)!=len(selected) or not all(isinstance(name,str) and name for name in band_names)):
        raise ValueError('band_names는 선택 밴드와 같은 길이의 비어 있지 않은 이름 목록이어야 합니다.')
    manifest = {'dataset_id': dataset_id, 'patches': entries, 'counts': counts, 'groups': groups,'seed':int(payload.get('seed',42)),
                'bands': selected, 'band_names':band_names, 'scale': scale, 'offset': offset, 'patch_size': size,
                'normalization_mode':'per_scene_product_metadata' if any(scene.get('normalization') for scene in scenes) else 'global',
                'readiness_contract':payload.get('readiness_contract'),
                'min_valid_fraction':min_valid_fraction,'require_full_patches':bool(payload.get('require_full_patches',False)),
                'class_names': class_names,'label_taxonomy':taxonomy,'label_taxonomy_signature':taxonomy_signature,
                'ignore_index': IGNORE, 'confidence_threshold': threshold,
                'synthetic': bool(payload.get('synthetic', False)), 'reference_kind': payload.get('reference_kind','unverified_or_pseudo_label'), 'provenance': provenance,
                'mapping_warning':'ESRI rangeland는 grass+shrub 의미이며 기존 WC grass와 동일하지 않습니다. 코드5는 미사용입니다.' if label_sources=={'esri_io'} else 'WorldCover 맹그로브→trees, moss/lichen→grass 등 의미 손실이 있는 초기 통합매핑입니다. 불일치는 라벨 오류를 의미하지 않습니다.'}
    manifest['version'] = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()[:16]
    (destination/'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    return {**manifest, 'manifest_path': str((destination/'manifest.json').relative_to(root))}
