"""읽기 전용 영상·WorldCover 정합 감사. 네트워크 요청과 재학습은 수행하지 않는다."""
from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling
from rasterio.warp import transform_geom
from rasterio.features import geometry_mask

ROOT = Path(__file__).resolve().parents[1]
# 학습 구현을 호출하지 않는 독립 검산표다. 의미상 동등성은 전문가가 따로 검토한다.
WORLD_COVER_MAPPING = {10: 1, 20: 5, 30: 2, 40: 4, 50: 6, 60: 7, 70: 8, 80: 0, 90: 3, 95: 1, 100: 2}
ESRI_MAPPING = {1: 0, 2: 1, 4: 3, 5: 4, 7: 6, 8: 7, 9: 8, 11: 2}
_HASH_CACHE = {}
CLASS_NAMES = ['water', 'trees', 'grass', 'flooded_vegetation', 'crops', 'shrub_and_scrub', 'built', 'bare', 'snow_and_ice']


def digest(path):
    # 같은 원본 창을 여러 패치가 공유하면 재읽기를 줄인다. 변경된 파일은 다시 계산한다.
    path = Path(path).resolve()
    stat = path.stat()
    key = (str(path), stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
    if key in _HASH_CACHE:
        return _HASH_CACHE[key]
    checksum = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            checksum.update(chunk)
    after = path.stat()
    if (after.st_size, after.st_mtime_ns, after.st_ctime_ns) != (stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns):
        raise RuntimeError('해시 계산 중 파일 변경 감지')
    _HASH_CACHE[key] = checksum.hexdigest()
    return _HASH_CACHE[key]


def counts(values):
    classes, frequencies = np.unique(values, return_counts=True)
    return {str(int(key)) if float(key).is_integer() else str(float(key)): int(value)
            for key, value in zip(classes, frequencies)}


def independent_map(raw, label_source='worldcover'):
    mapped = np.full(raw.shape, 255, dtype='uint8')
    for source, target in (ESRI_MAPPING if label_source == 'esri_io' else WORLD_COVER_MAPPING).items():
        mapped[raw == source] = target
    return mapped


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def resolve_path(path, root):
    value = Path(path)
    return value.resolve() if value.is_absolute() else (root / value).resolve()


def backend_mapping(source):
    # 소스의 상수 사전만 AST로 읽는다. 학습 함수를 실행하거나 결과를 재사용하지 않는다.
    for node in ast.walk(ast.parse(Path(source).read_text(encoding='utf-8-sig'))):
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'mapping' for target in node.targets):
            for value in ast.walk(node.value):
                if isinstance(value, ast.Dict):
                    candidate = ast.literal_eval(value)
                    if 10 in candidate:
                        return candidate
    return None


def backend_esri_mapping(source):
    for node in ast.walk(ast.parse(Path(source).read_text(encoding='utf-8-sig'))):
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'ESRI_IO_MAPPING' for target in node.targets):
            return ast.literal_eval(node.value)
    return None


def resampling_evidence(source):
    matches = []
    tree = ast.parse(Path(source).read_text(encoding='utf-8-sig'))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'reproject' and node.args:
            # RGB의 bilinear와 레이블의 nearest를 혼동하지 않도록 labels 입력 호출만 고른다.
            if ast.unparse(node.args[0]) == 'labels[0]':
                method = next((ast.unparse(k.value) for k in node.keywords if k.arg == 'resampling'), None)
                matches.append({'line': node.lineno, 'method': method})
    return {'source_sha256': digest(source), 'label_reproject_calls': matches,
            'nearest_in_current_source': bool(matches) and all(item['method'] == 'Resampling.nearest' for item in matches),
            'historical_execution_proven': False,
            'limitation': '현재 코드의 최근린 설정 증거이며 과거 실행시점 원본 crop 재현 증거는 아님'}


def grid_metadata(src):
    positions = [(0, 0), (src.width, 0), (0, src.height), (src.width, src.height)]
    return {'crs': str(src.crs), 'shape': [src.height, src.width], 'bands': src.count,
            'dtype': list(src.dtypes), 'resolution': list(src.res), 'affine': list(src.transform)[:6],
            'pixel_corners': [list(src.transform * position) for position in positions],
            'first_pixel_center': list(src.transform * (0.5, 0.5)), 'nodata': src.nodata}


def audit_pair(image_path, label_path, quality_path=None, expected_bands=3, label_source='worldcover'):
    with rasterio.open(image_path) as image, rasterio.open(label_path) as label:
        im, lm = grid_metadata(image), grid_metadata(label)
        checks = {'crs_equal': image.crs is not None and image.crs == label.crs,
                  'shape_equal': image.shape == label.shape, 'resolution_equal': image.res == label.res,
                  'exact_affine_equal': image.transform == label.transform,
                  'pixel_corners_equal': im['pixel_corners'] == lm['pixel_corners'],
                  'pixel_centers_equal': im['first_pixel_center'] == lm['first_pixel_center'],
                  'image_band_count_expected': image.count == expected_bands, 'label_single_band': label.count == 1,
                  'image_nodata_declared': image.nodata is not None, 'label_nodata_zero': label.nodata == 0}
        raw = label.read(1)
        known = np.isin(raw, [0, *(ESRI_MAPPING if label_source == 'esri_io' else WORLD_COVER_MAPPING)])
        checks['raw_class_codes_legal'] = bool(known.all())
        mapped = independent_map(raw, label_source)
        image_valid = (image.read_masks() > 0).all(axis=0) & np.isfinite(image.read()).all(axis=0)
        label_valid = label.read_masks(1) > 0
        checks['nodata_zero_matches_label_mask'] = bool(np.array_equal(raw != 0, label_valid))
        checks['image_invalid_excluded_from_label'] = image.shape == label.shape and bool((raw[~image_valid] == 0).all())
        result = {'status': 'pass' if all(checks.values()) else 'fail', 'checks': checks, 'image': im, 'label': lm,
                  'image_sha256': digest(image_path), 'label_sha256': digest(label_path),
                  'raw_class_counts': counts(raw), 'mapped_class_counts': counts(mapped),
                  'label_zero_count': int((raw == 0).sum()), 'training_ignore_255_count': int((mapped == 255).sum()),
                  'water_raw80_mapped0_count': int((raw == 80).sum()) if label_source == 'worldcover' else None,
                  'water_raw1_mapped0_count': int((raw == 1).sum()) if label_source == 'esri_io' else None,
                  'label_source': label_source,
                  'image_nodata_or_nonfinite_count': int((~image_valid).sum()),
                  'quality_mask_available': bool(quality_path and Path(quality_path).is_file()),
                  'limitations': ['WorldCover는 약한 참조 라벨이며 지상 독립 정답이 아님',
                                  '합법 클래스 정수값만으로 최근린의 과거 실행이나 의미상 라벨 정확성을 증명할 수 없음']}
        if result['quality_mask_available']:
            with rasterio.open(quality_path) as quality:
                same = quality.crs == image.crs and quality.transform == image.transform and quality.shape == image.shape
                checks['quality_grid_equal'] = same
                result['quality_mask_sha256'] = digest(quality_path)
                if same:
                    excluded = quality.read(1) == 0
                    result['quality_zero_count'] = int(excluded.sum())
                    checks['quality_excluded_label_zero'] = bool((raw[excluded] == 0).all())
                    result['label_zero_outside_quality_exclusion'] = int(((raw == 0) & ~excluded).sum())
        else:
            result['limitations'].append('별도 품질 마스크가 없어 label0의 구름/그림자/WorldCover NoData 원인 분리는 불가')
        result['status'] = 'pass' if all(checks.values()) else 'fail'
        return result


def audit_source_reprojection(image_path, label_path, quality_path, source_crops, root, label_source='worldcover', province_geometry=None, patch_quality=False):
    """보간 전 보관 crop에서 재투영을 새로 계산하며 원격 자료는 열지 않는다."""
    record = source_crops.get(f'raw-{label_source}.tif', {})
    if not record.get('path'):
        return {'status': 'unverified', 'raw_source_crop_archived': False,
                'raw_source_pixel_reprojection_reproduced': False,
                'reason': '보간 전 WorldCover crop 보관 기록이 없음; 기존 정렬본만으로 원본을 역추정하지 않음'}
    raw_path = resolve_path(record['path'], root)
    if not raw_path.is_file() or not quality_path or not Path(quality_path).is_file():
        return {'status': 'unverified', 'raw_source_crop_archived': raw_path.is_file(),
                'raw_source_pixel_reprojection_reproduced': False,
                'reason': '원본 crop 또는 저장 quality-mask가 없어 완전 재현 불가'}
    with rasterio.open(raw_path) as raw, rasterio.open(image_path) as image, rasterio.open(label_path) as label, rasterio.open(quality_path) as quality:
        source = raw.read(1)
        checks = {'source_hash_matches_archive': digest(raw_path) == record.get('sha256'),
                  'source_crs_available': raw.crs is not None,
                  'source_codes_legal': bool(np.isin(source, [0, 10, *ESRI_MAPPING] if label_source == 'esri_io' else [0, *WORLD_COVER_MAPPING]).all()),
                  'source_saved_before_resampling': record.get('resampling_applied') is False,
                  'quality_grid_equal': quality.crs == image.crs and quality.transform == image.transform and quality.shape == image.shape,
                  'label_grid_equal': label.crs == image.crs and label.transform == image.transform and label.shape == image.shape,
                  'quality_binary': bool(np.isin(quality.read(1), [0, 1]).all())}
        if record.get('transform'):
            checks['source_affine_matches_archive'] = list(raw.transform)[:6] == record['transform'][:6]
        expected = np.zeros(image.shape, dtype='uint8')
        reproject(source, expected, src_transform=raw.transform, src_crs=raw.crs, src_nodata=0,
                  dst_transform=image.transform, dst_crs=image.crs, dst_nodata=0, resampling=Resampling.nearest)
        quality_reconstruction = {'status': 'unverified', 'reason': '보간 전 SCL crop이 없어 저장 품질 마스크의 의미적 재현은 미검증'}
        scl_record = source_crops.get('raw-SCL.tif', {})
        if scl_record.get('path') and resolve_path(scl_record['path'], root).is_file():
            scl_path = resolve_path(scl_record['path'], root)
            with rasterio.open(scl_path) as scl:
                scl_aligned = np.zeros(image.shape, dtype='uint8')
                reproject(scl.read(1), scl_aligned, src_transform=scl.transform, src_crs=scl.crs,
                          dst_transform=image.transform, dst_crs=image.crs, resampling=Resampling.nearest)
                image_data = image.read()
                independently_valid = (image_data != 0).all(axis=0) & ~np.isin(scl_aligned, [0, 1, 3, 8, 9, 10, 11])
                if patch_quality:
                    # 공간 패치는 주경계 내부·라벨 가용성까지 강화한 품질 규칙을 재현한다.
                    independently_valid &= np.isfinite(image_data).all(axis=0)
                    independently_valid &= ~np.isin(expected, [0, 10] if label_source == 'esri_io' else [0])
                    if province_geometry is None:
                        raise ValueError('공간 패치 품질 재현에 공개 주경계 geometry가 필요함')
                    projected = transform_geom('EPSG:4326', image.crs, province_geometry)
                    independently_valid &= geometry_mask([projected], image.shape, image.transform, invert=True)
                scl_checks = {'source_hash_matches_archive': digest(scl_path) == scl_record.get('sha256'),
                              'source_saved_before_resampling': scl_record.get('resampling_applied') is False}
                if scl_record.get('transform'):
                    scl_checks['source_affine_matches_archive'] = list(scl.transform)[:6] == scl_record['transform'][:6]
                mismatch = int((quality.read(1) != independently_valid.astype('uint8')).sum()) if checks['quality_grid_equal'] else None
                scl_checks['saved_quality_pixels_equal'] = mismatch == 0
                quality_reconstruction = {'status': 'pass' if all(scl_checks.values()) else 'fail', 'checks': scl_checks,
                    'source': grid_metadata(scl), 'pixel_mismatch': mismatch,
                    'excluded_scl_codes': [0, 1, 3, 8, 9, 10, 11]}
        if checks['quality_grid_equal']:
            expected[quality.read(1) == 0] = 0
        if label_source == 'esri_io':
            # ESRI 구름10은 SCL 품질과 별도로 라벨에서 제외한다. 물1은 유지한다.
            expected[expected == 10] = 0
        mismatch = int((label.read(1) != expected).sum()) if checks['label_grid_equal'] else None
        checks['final_label_pixels_equal'] = mismatch == 0
        if quality_reconstruction['status'] == 'fail':
            checks['quality_reconstruction_passes'] = False
        return {'status': 'pass' if all(checks.values()) else 'fail', 'checks': checks,
                'raw_source_crop_archived': True, 'raw_source_pixel_reprojection_reproduced': mismatch == 0 and all(checks.values()),
                'source': grid_metadata(raw), 'source_sha256': digest(raw_path), 'source_class_counts': counts(source),
                'expected_final_class_counts': counts(expected), 'actual_final_class_counts': counts(label.read(1)),
                'pixel_mismatch': mismatch, 'resampling': 'nearest', 'quality_reconstruction': quality_reconstruction,
                'limitation': '보관 crop→정렬본 재현 결과이며 제공처 원본 전체 파일의 진위·지상 정확도는 별도 검증'}


def audit_manifest(manifest_path, root):
    manifest = read_json(manifest_path)
    results = []
    for entry in manifest['patches']:
        item = {'path': entry['path'], 'group': entry.get('group'), 'split': entry.get('split')}
        try:
            scene_index, y, x = map(int, Path(entry['path']).stem.split('_'))
            source = manifest['provenance'][scene_index]
            image_path, label_path = [resolve_path(source[key], root) for key in ('image_path', 'label_path')]
            with rasterio.open(image_path) as image, rasterio.open(label_path) as label:
                raw = label.read(1)
                if source.get('label_source') not in ('worldcover', 'esri_io'):
                    results.append({**item, 'status': 'unverified', 'reason': 'WorldCover 외 라벨은 이 감사의 대상이 아님'})
                    continue
                mapped = independent_map(raw, source.get('label_source'))
                selected = [int(band) for band in manifest['bands']]
                # 제품별 벡터 계수는 밴드 축에 적용한다. 전역 계수와 혼합하지 않는다.
                normalization = source.get('normalization') or {'scale': manifest['scale'], 'offset': manifest['offset']}
                scale, offset = [np.asarray(normalization[key], dtype='float32') for key in ('scale', 'offset')]
                scale = scale[:, None, None] if scale.ndim else scale
                offset = offset[:, None, None] if offset.ndim else offset
                scaled = image.read(selected).astype('float32') * scale + offset
                valid = (image.read_masks() > 0).all(axis=0) & (label.read_masks(1) > 0) & np.isfinite(scaled).all(axis=0) & (mapped != 255)
                if source.get('quality_mask_path'):
                    with rasterio.open(resolve_path(source['quality_mask_path'], root)) as quality:
                        valid &= (quality.read_masks(1) > 0) & (quality.read(1) > 0)
                mapped[~valid] = 255
                scaled[:, ~valid] = 0
                size = int(manifest['patch_size'])
                expected = np.full((size, size), 255, dtype='uint8')
                expected_image = np.zeros((len(selected), size, size), dtype='float32')
                h, w = min(size, raw.shape[0] - y), min(size, raw.shape[1] - x)
                expected[:h, :w] = mapped[y:y+h, x:x+w]
                expected_image[:, :h, :w] = scaled[:, y:y+h, x:x+w]
            patch_path = Path(manifest_path).parent / entry['path']
            with np.load(patch_path, allow_pickle=False) as patch:
                actual, actual_image = patch['label'], patch['image']
                same_shape = actual.shape == expected.shape
                mismatch = int((actual != expected).sum()) if same_shape else None
                image_equal = actual_image.shape == expected_image.shape and bool(np.array_equal(actual_image, expected_image))
                hashes_match = digest(image_path) == source.get('image_sha256') and digest(label_path) == source.get('label_sha256')
                class_equal = counts(actual) == counts(expected)
                item.update(status='pass' if same_shape and mismatch == 0 and image_equal and hashes_match and class_equal else 'fail',
                            expected_class_counts=counts(expected), actual_class_counts=counts(actual),
                            class_counts_equal=class_equal, label_pixel_mismatch=mismatch,
                            image_values_exact_equal=image_equal, source_hashes_match=hashes_match,
                            npz_sha256=digest(patch_path), raw_label_zero_count=int((raw == 0).sum()),
                            ignore_count=int((actual == 255).sum()), water_class0_count=int((actual == 0).sum()))
        except Exception as exc:
            item.update(status='error', error=str(exc))
        results.append(item)
    return {'manifest': str(manifest_path), 'manifest_sha256': digest(manifest_path), 'patches': results,
            'status': 'pass' if results and all(row['status'] == 'pass' for row in results) else 'fail'}


def audit_reports(report_paths, root):
    results = []
    for path in report_paths:
        report = read_json(path)
        state_path = Path(path).parent / 'window-state.json'
        state = read_json(state_path) if state_path.is_file() else {}
        for scene in report.get('scenes', []):
            row = {'report': str(path), 'aoi': scene['aoi'], 'year': scene['year'], 'collection_status': scene.get('status'),
                   'image_path': scene.get('image_path'), 'label_path': scene.get('label_path'),
                   'label_source': scene.get('label_source'), 'source_window': scene.get('source_window'),
                   'window_in_source': scene.get('window_in_source')}
            try:
                if not scene.get('image_path') or not scene.get('label_path'):
                    results.append({**row, 'status': 'missing', 'reason': '실제 영상·라벨 쌍이 없음; 성공으로 간주하지 않음',
                                    'label_status': scene.get('label_status'),
                                    'reference_note': 'WorldCover 같은 연차 참조 없음; 향후 참조 계획은 실제 확보와 구분' if int(scene['year']) > 2021 else '2020/2021 실제 영상·라벨 쌍 미확보'})
                    continue
                # ESRI 코드는 WorldCover와 다르므로 기존 매핑으로 검증 성공을 만들지 않는다.
                if scene.get('label_source') not in (None, 'worldcover', 'esri_io'):
                    results.append({**row, 'status': 'unverified',
                                    'reason': '이 감사의 독립 원본 매핑은 WorldCover 전용; 다른 라벨 소스 검산은 별도 구현 필요'})
                    continue
                image_path, label_path = [resolve_path(scene[key], root) for key in ('image_path', 'label_path')]
                quality_path = scene.get('quality_mask_path')
                quality_path = resolve_path(quality_path, root) if quality_path else None
                label_source = scene.get('label_source') or 'worldcover'
                row.update(audit_pair(image_path, label_path, quality_path, expected_bands=len(scene.get('bands', [1, 2, 3])), label_source=label_source))
                cell = state.get('cells', {}).get(f"{scene['aoi']}-{scene['year']}", {})
                archived = cell.get('label', {})
                province_geometry = None
                if scene.get('window_in_source'):
                    source_window = scene.get('source_window') or {}
                    boundary_path = resolve_path(source_window['boundary_path'], root) if source_window.get('boundary_path') else root / 'first-group-boundaries/selected-six.geojson'
                    boundaries = read_json(boundary_path)
                    province = scene.get('province') or scene.get('aoi')
                    province_geometry = next((feature['geometry'] for feature in boundaries['features']
                        if feature['properties'].get('province_id') == province), None)
                    row['patch_boundary_evidence'] = {'path': str(boundary_path), 'sha256': digest(boundary_path),
                        'historical_hash_recorded_by_collector': bool(source_window.get('boundary_sha256')),
                        'recorded_hash_matches': digest(boundary_path) == source_window.get('boundary_sha256') if source_window.get('boundary_sha256') else None}
                reconstruction = audit_source_reprojection(image_path, label_path, quality_path, scene.get('source_crops', {}), root, label_source,
                    province_geometry, patch_quality=bool(scene.get('window_in_source')))
                row['source_reconstruction'] = reconstruction
                row['provenance'] = {'final_label_registration_found': bool(archived),
                    'final_label_hash_matches_registration': archived.get('sha256') == row['label_sha256'] if archived else None,
                    'source_url': scene.get('label_source_url') or archived.get('source'),
                    'raw_source_crop_archived': reconstruction.get('raw_source_crop_archived', False),
                    'raw_source_pixel_reprojection_reproduced': reconstruction.get('raw_source_pixel_reprojection_reproduced', False),
                    'limitation': reconstruction.get('reason') or reconstruction.get('limitation')}
                row['mapping_semantic_review_required'] = True
                if archived and archived.get('sha256') != row['label_sha256']:
                    row['status'] = 'fail'
                if reconstruction['status'] == 'fail':
                    row['status'] = 'fail'
                if row.get('patch_boundary_evidence', {}).get('recorded_hash_matches') is False:
                    row['status'] = 'fail'
            except Exception as exc:
                row.update(status='error', error=str(exc))
            results.append(row)
    return results


def main():
    # Windows 기본 cp949에서도 한글·유니코드 경로를 손실 없이 보고한다.
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root', type=Path, default=ROOT / 'data')
    parser.add_argument('--reports', type=Path, nargs='+')
    parser.add_argument('--manifests', type=Path, nargs='*')
    parser.add_argument('--output', type=Path, default=ROOT / 'data/audits/alignment.json')
    args = parser.parse_args()
    root = args.data_root.resolve()
    report_paths = args.reports or [root / name / 'annual-window-report.json' for name in ('baseline2021', 'first-group-2021')]
    manifests = args.manifests if args.manifests is not None else sorted((root / 'datasets').glob('*/manifest.json'))
    mapping = backend_mapping(ROOT / 'backend/app/ml/dataset.py')
    esri_mapping = backend_esri_mapping(ROOT / 'backend/app/ml/raster.py')
    rows = audit_reports(report_paths, root)
    training = [audit_manifest(path, root) for path in manifests]
    result = {'recorded_at': datetime.now(timezone.utc).isoformat(), 'read_only': True,
        'network_requests': 0, 'retraining_executed': False, 'mapping_expected': WORLD_COVER_MAPPING,
        'backend_mapping_matches_independent_expected': mapping == WORLD_COVER_MAPPING,
        'esri_mapping_expected': ESRI_MAPPING, 'backend_esri_mapping_matches_independent_expected': esri_mapping == ESRI_MAPPING,
        'class_names': CLASS_NAMES, 'class_names_scope': 'worldcover_merged_taxonomy_only',
        'esri_class_names': ['water','trees','grass_or_shrub_rangeland','flooded_vegetation','crops','unused_separate_shrub_class','built','bare','snow_and_ice'],
        'resampling_evidence': resampling_evidence(ROOT / 'scripts/collect_samples.py'),
        'raster_rows': rows, 'training_manifests': training,
        'audit_scope': {'selection': 'all_rows_in_explicit_reports', 'report_count': len(report_paths),
                        'row_count': len(rows), 'pixel_comparison': 'all_pixels_per_available_supported_label_pair',
                        'sampling_applied': False, 'province_wide_coverage_claimed': False},
        'summary': {name: sum(row['status'] == name for row in rows) for name in ('pass', 'fail', 'missing', 'error', 'unverified')},
        'source_reconstruction_summary': {name: sum(row.get('source_reconstruction', {}).get('status') == name for row in rows) for name in ('pass', 'fail', 'unverified')},
        'limitations': ['격자·코드·NPZ 일치가 원본 WorldCover의 의미상 정확도나 독립평가를 보장하지 않음',
                        '95 mangrove→trees 및100 moss/lichen→grass는 의미 손실이 있는 초기 통합매핑으로 전문가 검토 필요']}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'output': str(args.output), 'summary': result['summary'],
                      'source_reconstruction_summary': result['source_reconstruction_summary'], 'mapping_match': mapping == WORLD_COVER_MAPPING,
                      'training': [{'manifest': row['manifest'], 'status': row['status']} for row in training]}, ensure_ascii=False))
    return 1 if any(row['status'] in ('fail', 'error') for row in rows) or any(row['status'] == 'fail' for row in training) or mapping != WORLD_COVER_MAPPING or esri_mapping != ESRI_MAPPING else 0


if __name__ == '__main__':
    raise SystemExit(main())
