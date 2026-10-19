"""이미 생성한 변화 GeoJSON을 지도에 전달한다. 전체 래스터 통계와 구분한다."""
import json
import math
from pathlib import Path


def coordinates(value):
    if isinstance(value, (list, tuple)):
        if len(value) >= 2 and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in value[:2]):
            yield value[:2]
        else:
            for child in value:
                yield from coordinates(child)


def map_data(analysis, root):
    root = Path(root).resolve()
    collection = analysis.get('geometry')
    if not collection:
        path = (root / str(analysis.get('geojson_path', ''))).resolve()
        if not path.is_relative_to(root) or not path.is_file() or path.suffix.lower() != '.geojson':
            raise ValueError('변화 지도용 GeoJSON 산출물이 없습니다.')
        if path.stat().st_size > 8 * 1024 * 1024:
            raise ValueError('지도용 GeoJSON이 8MiB를 초과합니다. 더 작은 AOI 또는 피처 제한으로 분석하세요.')
        collection = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(collection, dict) or collection.get('type') != 'FeatureCollection' or not isinstance(collection.get('features'), list):
        raise ValueError('지도 산출물이 GeoJSON FeatureCollection 형식이 아닙니다.')
    features = collection['features']
    if len(features) > 5000:
        raise ValueError('지도 산출물이 5000피처 제한을 초과합니다.')
    west, south, east, north = math.inf, math.inf, -math.inf, -math.inf
    for feature in features:
        geometry = feature.get('geometry') or {}
        if geometry.get('type') not in ('Polygon', 'MultiPolygon'):
            raise ValueError('변화지도는 Polygon/MultiPolygon 지오메트리만 지원합니다.')
        point_count = 0
        for x, y in coordinates(geometry.get('coordinates')):
            if not math.isfinite(x) or not math.isfinite(y) or not -180 <= x <= 180 or not -90 <= y <= 90:
                raise ValueError('지도 산출물의 좌표가 WGS84 경위도 범위를 벗어납니다.')
            west, south, east, north = min(west, x), min(south, y), max(east, x), max(north, y)
            point_count += 1
        if point_count < 4:
            raise ValueError('변화지도 폴리곤의 유효 좌표가 부족합니다.')
    bbox = [west, south, east, north] if math.isfinite(west) else None
    # 변화량은 원본 래스터 통계다. 표시 피처의 잘림으로 면적을 다시 계산하지 않는다.
    return {'geojson': collection, 'bbox': bbox, 'feature_count': len(features),
        'truncated': bool(analysis.get('vector_truncated')), 'statistics_basis': analysis.get('statistics_basis'),
        'changed_area_m2': analysis.get('changed_area_m2'),
        'validation': {'kind': 'comparison_of_classifications', 'independent_accuracy_validated': False,
                       'warning': analysis.get('warning', '분류 오차·계절·센서 차이가 변화에 포함될 수 있습니다.')},
        'source': {'geojson_path': analysis.get('geojson_path'), 'geotiff_path': analysis.get('geotiff_path'),
                   'checkpoint_sha256': analysis.get('checkpoint_sha256')}}
