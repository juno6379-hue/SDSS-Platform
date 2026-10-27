"""권위 원장에 고정된 범주형 GeoTIFF와 fail-closed Swipe 비교 계약."""
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor
import hashlib
import itertools
import json
from pathlib import Path
import struct
from threading import RLock
import zlib

COLORS = ['#419bdf','#397d49','#88b053','#7a87c6','#e49635','#c2a867','#c4281b','#a59b8f','#e8f4fa']
NAMES = ['water','trees','grass','flooded_vegetation','crops','shrub_and_scrub','built','bare','snow_and_ice']
ESRI = {1:(0,'water'),2:(1,'trees'),4:(3,'flooded_vegetation'),5:(4,'crops'),7:(6,'built'),8:(7,'bare'),9:(8,'snow_and_ice'),11:(2,'grass_or_shrub_rangeland')}
WC = {10:(1,'trees'),20:(5,'shrub_and_scrub'),30:(2,'grass'),40:(4,'crops'),50:(6,'built'),60:(7,'bare'),70:(8,'snow_and_ice'),80:(0,'water'),90:(3,'wetland'),95:(1,'mangroves'),100:(2,'moss_lichen')}
AUTHORITY_REPORT = Path('first-group-training-esri-v1/annual-window-report.json')
CONTRACT_VERSION = 'landcover-comparison-contract-v1'
_CACHE = {}
_LOCK = RLock()


def inside_file(root, value):
    if not value:
        return None
    path = Path(str(value))
    path = path.resolve() if path.is_absolute() else (root / path).resolve()
    return path if path.is_relative_to(root) and path.is_file() else None


def palette_for(source, class_names=None):
    if source == 'esri_io':
        return [{'value': value, 'color': COLORS[index], 'label': label} for value,(index,label) in ESRI.items()]
    if source == 'worldcover':
        return [{'value': value, 'color': COLORS[index], 'label': label} for value,(index,label) in WC.items()]
    names = class_names or NAMES
    return [{'value': index, 'color': COLORS[index], 'label': name} for index,name in enumerate(names[:9]) if not name.startswith('unused')]


def read_json(path):
    try:
        result = json.loads(path.read_text(encoding='utf-8'))
        return result if isinstance(result, dict) else {}
    except (OSError, ValueError):
        return {}


def _sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def _json_id(prefix, value, length=24):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return prefix + hashlib.sha256(raw).hexdigest()[:length]


def _normal_number(value):
    if value is None:
        return None
    value = float(value)
    return int(value) if value.is_integer() else value


def _raster_contract(path, mask_path=None):
    import numpy as np
    import rasterio
    from rasterio.warp import transform_bounds
    with rasterio.open(path) as raster:
        if raster.count != 1 or raster.crs is None:
            raise ValueError('단일 밴드와 CRS가 있는 범주형 래스터만 등록할 수 있습니다.')
        contract = {
            'crs': raster.crs.to_string(),
            'affine': [_normal_number(value) for value in tuple(raster.transform)[:6]],
            'bounds': [_normal_number(value) for value in raster.bounds],
            'bbox': [_normal_number(value) for value in transform_bounds(raster.crs, 'EPSG:4326', *raster.bounds, densify_pts=21)],
            'resolution': [_normal_number(abs(value)) for value in raster.res],
            'shape': [raster.height, raster.width],
            'dtype': raster.dtypes[0],
            'nodata': _normal_number(raster.nodata),
        }
    if mask_path is None:
        contract['mask_grid'] = None
        return contract
    with rasterio.open(mask_path) as mask:
        if mask.count != 1 or mask.crs is None:
            raise ValueError('QUALITY_MASK_SINGLE_BAND_CRS_REQUIRED')
        contract['mask_grid'] = {
            'crs': mask.crs.to_string() if mask.crs else None,
            'affine': [_normal_number(value) for value in tuple(mask.transform)[:6]],
            'bounds': [_normal_number(value) for value in mask.bounds],
            'resolution': [_normal_number(abs(value)) for value in mask.res],
            'shape': [mask.height, mask.width],
            'nodata': _normal_number(mask.nodata),
            'dtype': mask.dtypes[0],
        }
        label_grid = {field: contract[field] for field in ('crs', 'affine', 'bounds', 'resolution', 'shape')}
        mask_grid = {field: contract['mask_grid'][field] for field in label_grid}
        if mask_grid != label_grid:
            raise ValueError('QUALITY_MASK_GRID_MISMATCH')
        values = set()
        for _, window in mask.block_windows(1):
            values.update(int(value) for value in np.unique(mask.read(1, window=window)))
            if not values.issubset({0, 1}):
                raise ValueError('QUALITY_MASK_NOT_BINARY_0_1')
        # 계약은 허용 domain을 고정한다. 실제 창에 0 또는 1이 우연히 없다는
        # 이유로 서로 다른 grid 계약으로 판정하면 안 된다.
        contract['mask_grid']['allowed_values'] = [0, 1]
    return contract


def _comparison(left, right, kind):
    required_equal = ('aoi_id', 'crs', 'affine', 'bounds', 'resolution', 'shape',
                      'class_schema_id', 'class_schema_version', 'nodata',
                      'mask_policy_version', 'mask_grid')
    mismatches = [field for field in required_equal if left.get(field) != right.get(field)]
    blockers = []
    for field in ('aoi_id', 'class_schema_id', 'class_schema_version', 'mask_policy_version'):
        if not left.get(field) or not right.get(field):
            blockers.append(f'CONTRACT_FIELD_MISSING:{field}')
    if left['year'] == right['year']:
        blockers.append('SAME_YEAR_NOT_A_TEMPORAL_COMPARISON')
    if not left.get('asset_sha256') or not right.get('asset_sha256'):
        blockers.append('ASSET_SHA256_MISSING')
    elif left['asset_sha256'] == right['asset_sha256']:
        blockers.append('ASSET_SHA256_REUSED_ACROSS_YEARS')
    if not left.get('mask_asset_sha256') or not right.get('mask_asset_sha256'):
        blockers.append('QUALITY_MASK_SHA256_MISSING')
    blockers.extend(f'GRID_CONTRACT_MISMATCH:{field}' for field in mismatches)
    visual_allowed = not blockers
    model_pair = kind == 'model_prediction' and left.get('reference_kind') == right.get('reference_kind') == 'model_prediction'
    statistics_allowed = visual_allowed and model_pair and not left.get('synthetic') and not right.get('synthetic')
    fields = {
        'contract_version': CONTRACT_VERSION,
        'left_layer_id': left['layer_id'], 'right_layer_id': right['layer_id'],
        'left_asset_sha256': left.get('asset_sha256'), 'right_asset_sha256': right.get('asset_sha256'),
        'aoi_id': left.get('aoi_id'), 'class_schema_id': left.get('class_schema_id'),
        'class_schema_version': left.get('class_schema_version'),
        'mask_policy_version': left.get('mask_policy_version'),
    }
    return {
        'comparison_id': _json_id('cmp-', fields, 32), **fields,
        'left_year': left['year'], 'right_year': right['year'],
        'preflight_status': 'READY_VISUAL_REFERENCE_ONLY' if visual_allowed and not model_pair else ('READY' if visual_allowed else 'BLOCKED'),
        'visual_comparison_allowed': visual_allowed,
        'change_statistics_allowed': statistics_allowed,
        'change_statistics_status': ('AVAILABLE_MODEL_PREDICTION_PAIR' if statistics_allowed else
            ('BLOCKED_REFERENCE_LAYERS_NOT_MODEL_PREDICTIONS' if not model_pair else
             ('BLOCKED_SYNTHETIC_MODEL_PREDICTION' if visual_allowed else 'BLOCKED_PREFLIGHT'))),
        'pixel_query_status': 'BLOCKED_NO_PIXEL_QUERY_API',
        'blockers': blockers,
        'matched_contract_fields': [field for field in required_equal if field not in mismatches],
        'mismatched_contract_fields': mismatches,
        'evidence_state': 'IMPLEMENTED_UNVERIFIED',
    }


def inventory(root, analyses=(), authority_report=None):
    """한 권위 원장만 읽으며 중복 logical year와 불일치 비교를 차단한다."""
    root = Path(root).resolve()
    authority = (root / (authority_report or AUTHORITY_REPORT)).resolve()
    issues, series, layers = [], {}, {}
    counters = {'authority_rows': 0, 'authority_source_windows': 0, 'quality_eligible_rows': 0, 'registered_layers': 0,
                'skipped_noneligible_rows': 0, 'invalid_rows': 0, 'model_prediction_layers': 0}
    if not authority.is_relative_to(root) or not authority.is_file():
        return ({'schema_version': '2.0', 'contract_version': CONTRACT_VERSION, 'registry_status': 'BLOCKED',
                 'authority': {'report': str(AUTHORITY_REPORT), 'sha256': None}, 'series': [], 'comparisons': [],
                 'counts': counters, 'issues': [{'code': 'AUTHORITY_REPORT_MISSING', 'path': str(AUTHORITY_REPORT)}],
                 'change_statistics_status': 'BLOCKED_NO_MODEL_PREDICTION',
                 'limitations': ['권위 annual-window-report.json이 없어 파일 검색으로 대체하지 않았습니다.']}, layers)
    report = read_json(authority)
    manifest_sha = _sha256(authority)

    def add(key, title, kind, year, path, source, *, province=None, class_names=None,
            synthetic=False, origin=None, aoi_id=None, schema_id=None, schema_version=None,
            asset_sha=None, mask_path=None, mask_sha=None, mask_policy=None, dataset_version=None,
            contract=None):
        try:
            year = int(year)
            contract = contract or _raster_contract(path, mask_path)
            stat = path.stat()
        except (OSError, ValueError, TypeError) as exc:
            counters['invalid_rows'] += 1
            issues.append({'code': 'RASTER_CONTRACT_INVALID', 'origin': origin, 'detail': str(exc)})
            return
        palette = palette_for(source, class_names)
        schema_id = schema_id or _json_id('schema-', {'source': source, 'palette': palette}, 20)
        schema_version = schema_version or schema_id
        layer_key = {'origin': origin, 'year': year, 'asset_sha256': asset_sha, 'path': str(path.relative_to(root))}
        layer_id = _json_id('lc-', layer_key)
        layer = {
            'year': year, 'layer_id': layer_id, 'bbox': contract['bbox'], 'size': [contract['shape'][1], contract['shape'][0]],
            'palette': palette, 'source': {'name': source, 'report': origin, 'dataset_version': dataset_version},
            'reference_kind': 'weak_label_agreement' if kind == 'annual_reference' else 'model_prediction',
            'independent_ground_truth': False,
            'model_prediction': kind == 'model_prediction',
            'tile_url': f'/api/data/landcover-layers/{layer_id}/tiles/{{z}}/{{x}}/{{y}}.png',
            'synthetic': synthetic, 'asset_sha256': asset_sha, 'asset_bytes': stat.st_size,
            'asset_verification': 'VERIFIED_LOCAL_SHA256' if asset_sha else 'MISSING',
            'aoi_id': aoi_id, 'class_schema_id': schema_id, 'class_schema_version': schema_version,
            'mask_asset_sha256': mask_sha, 'mask_policy_version': mask_policy, **contract,
            'evidence_state': 'TESTED_SYNTHETIC' if synthetic else 'IMPLEMENTED_UNVERIFIED',
        }
        group = series.setdefault(key, {'id': _json_id('series-', key, 20), 'title': title, 'province': province,
            'aoi_id': aoi_id, 'kind': kind, 'class_names': class_names, 'label_source': source,
            'independent_ground_truth': False, 'model_prediction': kind == 'model_prediction',
            'synthetic': synthetic, 'years': {}, 'blocked_years': []})
        old = group['years'].get(year)
        if old is not None:
            issues.append({'code': 'DUPLICATE_GROUP_YEAR', 'series_id': group['id'], 'year': year,
                           'asset_sha256': sorted({str(old.get('asset_sha256')), str(asset_sha)}),
                           'origins': sorted({str(old.get('source', {}).get('report')), str(origin)})})
            group['years'].pop(year, None)
            group['blocked_years'].append({'year': year, 'reason': 'DUPLICATE_GROUP_YEAR'})
            layers.pop(old['layer_id'], None)
            counters['registered_layers'] -= 1
            counters['model_prediction_layers'] -= kind == 'model_prediction'
            return
        if any(entry['year'] == year for entry in group['blocked_years']):
            return
        group['years'][year] = layer
        mask_stat = mask_path.stat() if mask_path is not None else None
        layers[layer_id] = {
            'path': path, 'palette': palette, 'mtime': stat.st_mtime_ns, 'size': stat.st_size,
            'asset_sha256': asset_sha, 'mask_path': mask_path,
            'mask_mtime': mask_stat.st_mtime_ns if mask_stat else None,
            'mask_size': mask_stat.st_size if mask_stat else None,
            'mask_asset_sha256': mask_sha,
        }
        counters['registered_layers'] += 1
        counters['model_prediction_layers'] += kind == 'model_prediction'

    rows = report.get('scenes')
    if not isinstance(rows, list):
        issues.append({'code': 'AUTHORITY_SCENES_INVALID'})
        rows = []
    counters['authority_rows'] = len(rows)
    origin = authority.relative_to(root).as_posix()
    allowed_windows = {}
    source_path_cache = {}
    for index, scene in enumerate(rows):
        if not isinstance(scene, dict):
            counters['invalid_rows'] += 1
            issues.append({'code': 'AUTHORITY_ROW_INVALID', 'row_index': index})
            continue
        if scene.get('quality_status') != 'quality_eligible':
            counters['skipped_noneligible_rows'] += 1
            continue
        counters['quality_eligible_rows'] += 1
        source = scene.get('label_source')
        if source not in ('worldcover', 'esri_io'):
            counters['invalid_rows'] += 1
            issues.append({'code': 'LABEL_SOURCE_UNSUPPORTED', 'row_index': index})
            continue
        source_window = scene.get('source_window') or {}
        source_value = source_window.get('path') if isinstance(source_window, dict) else None
        source_token = str(source_value)
        if source_token not in source_path_cache:
            source_path_cache[source_token] = inside_file(root, source_value)
        source_path = source_path_cache[source_token]
        schema = scene.get('taxonomy_signature')
        if source_path is None or not scene.get('source_group') or not schema:
            counters['invalid_rows'] += 1
            issues.append({'code': 'AUTHORITY_ROW_REQUIRED_EVIDENCE_MISSING', 'row_index': index,
                           'patch_id': scene.get('patch_id')})
            continue
        source_parent = source_path.parent.resolve()
        identity = (str(scene.get('year')), scene.get('province', scene.get('aoi')), source,
                    scene.get('source_group'), schema)
        allowed_windows.setdefault(source_parent, set()).add(identity)
    counters['authority_source_windows'] = len(allowed_windows)

    # 파일 검색 대신 권위 원장이 직접 참조한 source window 디렉터리만 연다.
    def inspect_source(item):
        source_parent, identities = item
        report_path = source_parent.parent / 'annual-window-report.json'
        source_report = read_json(report_path)
        if not source_report:
            return [], [{'code': 'AUTHORITY_SOURCE_REPORT_MISSING', 'path': str(report_path.relative_to(root))}]
        candidates = source_report.get('scenes') or []
        matched, entries, local_issues = False, [], []
        for scene in candidates:
            if not isinstance(scene, dict):
                continue
            source = scene.get('label_source')
            schema = scene.get('taxonomy_signature')
            province = scene.get('province', scene.get('aoi'))
            identity = (str(scene.get('year')), province, source, scene.get('source_group'), schema)
            path = inside_file(root, scene.get('label_path'))
            mask_path = inside_file(root, scene.get('quality_mask_path'))
            if identity not in identities or path is None or mask_path is None or path.parent.resolve() != source_parent:
                continue
            matched = True
            aoi_id = scene.get('aoi')
            mask_policy = scene.get('quality_mask')
            if not aoi_id or not mask_policy:
                local_issues.append({'code': 'SOURCE_LAYER_CONTRACT_MISSING', 'path': str(report_path.relative_to(root)),
                                     'missing': [name for name, value in (('aoi_id', aoi_id), ('mask_policy_version', mask_policy)) if not value]})
                continue
            try:
                asset_sha, mask_sha = _sha256(path), _sha256(mask_path)
                contract = _raster_contract(path, mask_path)
                key = json.dumps(['annual_reference', province, source, aoi_id, schema], ensure_ascii=False, sort_keys=True)
                entries.append(dict(key=key, title=f'{province} · {source} · {aoi_id}', kind='annual_reference',
                    year=scene.get('year'), path=path, source=source,
                    province=province, synthetic=bool(report.get('synthetic')), origin=str(report_path.relative_to(root).as_posix()),
                    aoi_id=aoi_id, schema_id=schema, schema_version=schema, asset_sha=asset_sha, mask_path=mask_path,
                    mask_sha=mask_sha, mask_policy=mask_policy, dataset_version=scene.get('label_dataset_version'),
                    contract=contract))
            except (OSError, ValueError, TypeError) as exc:
                local_issues.append({'code': 'RASTER_CONTRACT_INVALID', 'path': str(report_path.relative_to(root)), 'detail': str(exc)})
        if not matched:
            local_issues.append({'code': 'AUTHORITY_SOURCE_IDENTITY_NOT_FOUND', 'path': str(report_path.relative_to(root))})
        return entries, local_issues

    source_items = sorted(allowed_windows.items(), key=lambda item: str(item[0]))
    with ThreadPoolExecutor(max_workers=min(12, max(1, len(source_items)))) as pool:
        for entries, local_issues in pool.map(inspect_source, source_items):
            issues.extend(local_issues)
            counters['invalid_rows'] += len(local_issues)
            for entry in entries:
                add(**entry)

    for analysis in analyses:
        if not isinstance(analysis, dict) or not analysis.get('id'):
            continue
        for year, item in (analysis.get('classifications') or {}).items():
            if not isinstance(item, dict):
                continue
            path = inside_file(root, item.get('classification_path'))
            mask_path = inside_file(root, item.get('quality_mask_path') or item.get('valid_mask_path'))
            if path and mask_path:
                actual_asset_sha, actual_mask_sha = _sha256(path), _sha256(mask_path)
                declared_asset_sha = item.get('sha256')
                declared_mask_sha = item.get('quality_mask_sha256') or item.get('valid_mask_sha256')
                if not declared_asset_sha or not declared_mask_sha:
                    counters['invalid_rows'] += 1
                    issues.append({'code': 'MODEL_ASSET_SHA_REQUIRED', 'analysis_id': str(analysis['id']), 'year': str(year)})
                    continue
                if ((declared_asset_sha and declared_asset_sha != actual_asset_sha) or
                        (declared_mask_sha and declared_mask_sha != actual_mask_sha)):
                    counters['invalid_rows'] += 1
                    issues.append({'code': 'MODEL_ASSET_SHA_MISMATCH', 'analysis_id': str(analysis['id']), 'year': str(year)})
                    continue
                asset_sha, mask_sha = actual_asset_sha, actual_mask_sha
                aoi_id = item.get('aoi_id') or analysis.get('aoi_id')
                class_names = item.get('class_names', analysis.get('class_names'))
                schema = item.get('class_schema_id') or analysis.get('class_schema_id')
                schema_version = item.get('class_schema_version') or analysis.get('class_schema_version')
                key = 'prediction:' + str(analysis['id'])
                add(key, f'모델 시계열 · {analysis["id"]}', 'model_prediction', year, path, 'model_prediction',
                    province=item.get('province') or analysis.get('province'), class_names=class_names,
                    synthetic=bool(analysis.get('synthetic')), origin=str(analysis['id']), aoi_id=aoi_id,
                    schema_id=schema, schema_version=schema_version, asset_sha=asset_sha, mask_path=mask_path,
                    mask_sha=mask_sha, mask_policy=item.get('mask_policy_version') or analysis.get('mask_policy_version'),
                    dataset_version=item.get('result_version') or analysis.get('version'))

    result, comparisons = [], []
    for group in series.values():
        group['years'] = [group['years'][year] for year in sorted(group['years'])]
        available = {row['year'] for row in group['years']}
        group['missing_years'] = sorted(set(range(2020, 2026)) - available)
        group['evaluation_kind'] = 'reference_map_not_ground_truth' if group['kind']=='annual_reference' else 'model_prediction_not_change_ground_truth'
        group['registry_status'] = 'BLOCKED_DUPLICATE_GROUP_YEAR' if group['blocked_years'] else 'REGISTERED'
        group_comparisons = [_comparison(left, right, group['kind']) for left, right in itertools.combinations(group['years'], 2)]
        group['comparison_ids'] = [entry['comparison_id'] for entry in group_comparisons]
        comparisons.extend(group_comparisons)
        if group['years'] or group['blocked_years']:
            result.append(group)
    result.sort(key=lambda row: (str(row.get('province')), str(row.get('aoi_id')), str(row.get('label_source'))))
    registry_status = 'BLOCKED' if issues else 'REGISTERED'
    change_status = ('BLOCKED_NO_MODEL_PREDICTION' if counters['model_prediction_layers'] == 0 else
                     'BLOCKED_UNTIL_EXACT_MODEL_PAIR_SELECTED_AND_VALIDATED')
    public = {
        'schema_version': '2.0', 'contract_version': CONTRACT_VERSION, 'registry_status': registry_status,
        'authority': {'report': origin, 'sha256': manifest_sha, 'rows': len(rows),
                      'learning_ready': report.get('learning_ready'), 'status': report.get('status')},
        'series': result, 'comparisons': comparisons, 'counts': counters, 'issues': issues,
        'change_statistics_status': change_status,
        'limitations': [
            '권위 annual-window-report.json의 quality_eligible 행이 직접 참조한 source window만 등록하며 누락 연도를 생성하지 않음',
            '연차 참조지도는 독립 지상정답과 모델 예측이 아님',
            '현재 타일은 패치 범위 표시이며 6개 주 전체 피복 커버리지를 뜻하지 않음',
            '모델 예측 쌍이 없으면 변화·면적·전이행렬 통계를 제공하지 않음',
        ],
    }
    return public, layers


def series_index(root, analyses=(), refresh=False):
    resolved = Path(root).resolve()
    key = str(resolved)
    authority = resolved / AUTHORITY_REPORT
    try:
        stat = authority.stat()
        authority_stamp = (stat.st_mtime_ns, stat.st_size)
    except OSError:
        authority_stamp = None
    analyses_stamp = hashlib.sha256(json.dumps(analyses, ensure_ascii=False, sort_keys=True, default=str).encode('utf-8')).hexdigest()
    input_stamp = (authority_stamp, analyses_stamp)
    with _LOCK:
        cached = _CACHE.get(key)
        # refresh=True도 입력 stamp를 다시 확인한다. 불변 원장을 1,407회 재개방하지 않는다.
        if not cached or cached[3] != input_stamp:
            public, layers = inventory(resolved, analyses)
            _CACHE[key] = (None, public, layers, input_stamp)
        return _CACHE[key][1], _CACHE[key][2]


def png(rgba):
    """추가 이미지 라이브러리 없이 RGBA PNG를 인코딩한다."""
    height, width, _ = rgba.shape
    def chunk(kind, data):
        return struct.pack('!I',len(data))+kind+data+struct.pack('!I',zlib.crc32(kind+data)&0xffffffff)
    raw = b''.join(b'\x00'+row.tobytes() for row in rgba)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!IIBBBBB',width,height,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b'')


@lru_cache(maxsize=256)
def render_tile(path, mtime, size, palette_json, z, x, y,
                mask_path=None, mask_mtime=None, mask_size=None):
    import numpy as np
    import rasterio
    from rasterio.transform import from_bounds
    from rasterio.warp import reproject, Resampling
    half = 20037508.342789244
    span = 2*half/(2**z)
    west, north = -half+x*span, half-y*span
    data = np.full((256,256),65535,dtype='uint16')
    with rasterio.open(path) as source:
        reproject(rasterio.band(source,1), data, src_transform=source.transform, src_crs=source.crs,
            src_nodata=source.nodata, dst_crs='EPSG:3857', dst_transform=from_bounds(west,north-span,west+span,north,256,256),
            dst_nodata=65535, resampling=Resampling.nearest)
    valid = np.ones((256, 256), dtype='uint8')
    if mask_path:
        valid.fill(0)
        with rasterio.open(mask_path) as source:
            reproject(rasterio.band(source, 1), valid, src_transform=source.transform, src_crs=source.crs,
                src_nodata=source.nodata, dst_crs='EPSG:3857',
                dst_transform=from_bounds(west,north-span,west+span,north,256,256),
                dst_nodata=0, resampling=Resampling.nearest)
    rgba = np.zeros((256,256,4),dtype='uint8')
    for entry in json.loads(palette_json):
        color = entry['color'].lstrip('#')
        rgba[data==entry['value']] = [int(color[i:i+2],16) for i in (0,2,4)]+[255]
    rgba[valid != 1, 3] = 0
    return png(rgba)


def tile(root, layer_id, z, x, y, analyses=()):
    if not 0 <= z <= 22 or not 0 <= x < 2**z or not 0 <= y < 2**z:
        raise ValueError('XYZ 타일 좌표 범위가 잘못됐습니다.')
    _, layers = series_index(root, analyses)
    layer = layers.get(layer_id)
    if not layer:
        raise KeyError('권위 원장에 등록된 연차 레이어가 없습니다.')
    stat = layer['path'].stat()
    if (stat.st_mtime_ns, stat.st_size) != (layer['mtime'], layer['size']):
        raise KeyError('레이어 원본이 변경됐습니다. 연차 목록을 다시 조회하세요.')
    expected = layer.get('asset_sha256')
    if not expected or _sha256(layer['path']) != expected:
        raise KeyError('레이어 SHA256이 권위 원장과 다릅니다.')
    mask_path = layer.get('mask_path')
    if mask_path is None:
        raise KeyError('레이어 품질 마스크가 등록되지 않았습니다.')
    mask_stat = mask_path.stat()
    if (mask_stat.st_mtime_ns, mask_stat.st_size) != (layer.get('mask_mtime'), layer.get('mask_size')):
        raise KeyError('레이어 품질 마스크가 변경됐습니다. 연차 목록을 다시 조회하세요.')
    mask_expected = layer.get('mask_asset_sha256')
    if not mask_expected or _sha256(mask_path) != mask_expected:
        raise KeyError('레이어 품질 마스크 SHA256이 권위 원장과 다릅니다.')
    return render_tile(str(layer['path']), layer['mtime'], layer['size'],
                       json.dumps(layer['palette'], sort_keys=True), z, x, y,
                       str(mask_path), layer['mask_mtime'], layer['mask_size'])
