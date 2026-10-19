"""실제 연차 범주형 GeoTIFF를 조회하고 최근린 XYZ 타일로 표시한다."""
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
import struct
from threading import RLock
import time
import zlib

COLORS = ['#419bdf','#397d49','#88b053','#7a87c6','#e49635','#c2a867','#c4281b','#a59b8f','#e8f4fa']
NAMES = ['water','trees','grass','flooded_vegetation','crops','shrub_and_scrub','built','bare','snow_and_ice']
ESRI = {1:(0,'water'),2:(1,'trees'),4:(3,'flooded_vegetation'),5:(4,'crops'),7:(6,'built'),8:(7,'bare'),9:(8,'snow_and_ice'),11:(2,'grass_or_shrub_rangeland')}
WC = {10:(1,'trees'),20:(5,'shrub_and_scrub'),30:(2,'grass'),40:(4,'crops'),50:(6,'built'),60:(7,'bare'),70:(8,'snow_and_ice'),80:(0,'water'),90:(3,'wetland'),95:(1,'mangroves'),100:(2,'moss_lichen')}
_CACHE = {}
_LOCK = RLock()


def inside_file(root, value):
    if not value:
        return None
    path = (root / str(value)).resolve()
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


def inventory(root, analyses=()):
    """집계 패치를 다시 합성하지 않고 보관한 원본 참조 창의 시계열을 사용한다."""
    import rasterio
    from rasterio.warp import transform_bounds
    root = Path(root).resolve()
    series, layers = {}, {}
    def add(key, title, kind, year, path, source, province=None, class_names=None, synthetic=False, origin=None):
        try:
            year = int(year)
            with rasterio.open(path) as raster:
                if raster.count != 1 or raster.crs is None:
                    return
                bbox = list(transform_bounds(raster.crs, 'EPSG:4326', *raster.bounds, densify_pts=21))
                size = [raster.width, raster.height]
            stat = path.stat()
        except (OSError, ValueError, TypeError):
            return
        palette = palette_for(source, class_names)
        fingerprint = (str(path.relative_to(root)), stat.st_size, stat.st_mtime_ns, source, palette)
        layer_id = hashlib.sha256(json.dumps(fingerprint, sort_keys=True).encode()).hexdigest()[:24]
        layer = {'year': year, 'layer_id': layer_id, 'bbox': bbox, 'size': size, 'palette': palette,
                 'source': {'name': source, 'report': origin}, 'reference_kind': 'weak_label_agreement' if kind == 'annual_reference' else 'model_prediction',
                 'tile_url': f'/api/data/landcover-layers/{layer_id}/tiles/{{z}}/{{x}}/{{y}}.png', 'synthetic': synthetic}
        group = series.setdefault(key, {'id': hashlib.sha256(key.encode()).hexdigest()[:20], 'title': title, 'province': province,
            'kind': kind, 'class_names': class_names, 'label_source': source, 'synthetic': synthetic, 'years': {}})
        group['years'][year] = layer
        layers[layer_id] = {'path': path, 'palette': palette, 'mtime': stat.st_mtime_ns, 'size': stat.st_size}
    paths = sorted(root.glob('first-group*/**/annual-window-report.json'), key=lambda p:(p.stat().st_mtime_ns, str(p)))
    for report_path in paths[-512:]:
        if (report_path.parent / 'sources').is_dir():
            continue
        report = read_json(report_path)
        for scene in report.get('scenes', []):
            source = scene.get('label_source')
            if source not in ('worldcover', 'esri_io'):
                continue
            path = inside_file(root, scene.get('label_path'))
            if path is None:
                continue
            # 계획 중심·창 크기·출처가 같은 실제 관측만 같은 재생 시리즈에 묶는다.
            province = scene.get('province', scene.get('aoi'))
            bbox = scene.get('bbox') or []
            center = tuple(round((bbox[i]+bbox[i+2])/2, 6) for i in range(2)) if len(bbox)==4 else str(path.parent)
            with rasterio.open(path) as raster:
                shape = (raster.width, raster.height)
            key = json.dumps([province, source, scene.get('aoi'), center, shape])
            add(key, f'{province} · {source} · {scene.get("aoi", "원본 창")}', 'annual_reference',
                scene.get('year'), path, source, province, synthetic=bool(report.get('synthetic')),
                origin=str(report_path.relative_to(root)))
    for analysis in analyses:
        for year, item in (analysis.get('classifications') or {}).items():
            path = inside_file(root, item.get('classification_path'))
            if path:
                add('prediction:'+str(analysis['id']), f'모델 시계열 · {analysis["id"]}', 'model_prediction', year,
                    path, 'model_prediction', class_names=item.get('class_names', analysis.get('class_names')),
                    synthetic=bool(analysis.get('synthetic')), origin=str(analysis['id']))
    result = []
    for group in series.values():
        group['years'] = [group['years'][year] for year in sorted(group['years'])]
        available = {row['year'] for row in group['years']}
        group['missing_years'] = sorted(set(range(2020,2026))-available)
        group['evaluation_kind'] = 'reference_map_not_ground_truth' if group['kind']=='annual_reference' else 'model_prediction_not_change_ground_truth'
        result.append(group)
    return {'series': result, 'limitations': ['확보된 관측만 재생하며 누락 연도를 생성하지 않음',
            '연차 참조지도는 독립 지상정답이 아니며 모델 예측과 구분', '최근린 재투영 표시이며 원본 분석 해상도는 달라질 수 있음']}, layers


def series_index(root, analyses=(), refresh=False):
    key = str(Path(root).resolve())
    with _LOCK:
        cached = _CACHE.get(key)
        if refresh or not cached or time.monotonic()-cached[0] > 5:
            public, layers = inventory(Path(root), analyses)
            _CACHE[key] = (time.monotonic(), public, layers)
        return _CACHE[key][1], _CACHE[key][2]


def png(rgba):
    """추가 이미지 라이브러리 없이 RGBA PNG를 인코딩한다."""
    height, width, _ = rgba.shape
    def chunk(kind, data):
        return struct.pack('!I',len(data))+kind+data+struct.pack('!I',zlib.crc32(kind+data)&0xffffffff)
    raw = b''.join(b'\x00'+row.tobytes() for row in rgba)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!IIBBBBB',width,height,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b'')


@lru_cache(maxsize=256)
def render_tile(path, mtime, size, palette_json, z, x, y):
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
    rgba = np.zeros((256,256,4),dtype='uint8')
    for entry in json.loads(palette_json):
        color = entry['color'].lstrip('#')
        rgba[data==entry['value']] = [int(color[i:i+2],16) for i in (0,2,4)]+[255]
    return png(rgba)


def tile(root, layer_id, z, x, y, analyses=()):
    if not 0 <= z <= 22 or not 0 <= x < 2**z or not 0 <= y < 2**z:
        raise ValueError('XYZ 타일 좌표 범위가 잘못됐습니다.')
    _, layers = series_index(root, analyses)
    layer = layers.get(layer_id)
    if not layer:
        raise KeyError('보관한 실제 연차 레이어가 없습니다.')
    stat = layer['path'].stat()
    if (stat.st_mtime_ns, stat.st_size) != (layer['mtime'], layer['size']):
        raise KeyError('레이어 원본이 변경됐습니다. 연차 목록을 다시 조회하세요.')
    return render_tile(str(layer['path']),layer['mtime'],layer['size'],json.dumps(layer['palette'],sort_keys=True),z,x,y)
