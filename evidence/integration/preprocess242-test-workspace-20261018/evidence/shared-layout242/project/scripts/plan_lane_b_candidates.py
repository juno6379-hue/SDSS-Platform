"""lane B 공간 보완 후보를 로컬 공개 경계로만 계산한다. 수집을 실행하지 않는다."""
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import Point, box, shape
from shapely.ops import transform

ROOT = Path(__file__).resolve().parents[1]


def main():
    boundary_path = ROOT / 'data/first-group-boundaries/selected-six.geojson'
    plan_path = ROOT / 'data/first-group-training-esri-v1/grid-plan.json'
    boundary_bytes = boundary_path.read_bytes()
    boundaries = json.loads(boundary_bytes)
    plan = json.loads(plan_path.read_text(encoding='utf-8'))
    candidates = []
    for province in ('east_java', 'banten', 'west_java'):
        feature = next(row for row in boundaries['features'] if row['properties']['province_id'] == province)
        geographic = shape(feature['geometry'])
        center = geographic.representative_point()
        epsg = 32700 + int((center.x + 180) // 6) + 1
        forward = Transformer.from_crs(4326, epsg, always_xy=True)
        inverse = Transformer.from_crs(epsg, 4326, always_xy=True)
        polygon = transform(forward.transform, geographic)
        # 1024창 전체 내부 조건을 완화하되, 후보 중심은 주 안쪽에 둔다.
        band = polygon.buffer(-1800).difference(polygon.buffer(-7400))
        existing = {}
        for batch in plan['batches']:
            if batch['province'] == province:
                lon, lat = batch['center']['lon'], batch['center']['lat']
                x, y = forward.transform(lon, lat)
                existing[(lon, lat)] = box(x - 5120, y - 5120, x + 5120, y + 5120)
        xmin, ymin, xmax, ymax = polygon.bounds
        pool = []
        for ix in range(math.floor(xmin / 10400), math.ceil(xmax / 10400) + 1):
            for iy in range(math.floor(ymin / 10400), math.ceil(ymax / 10400) + 1):
                x, y = ix * 10400, iy * 10400
                point = Point(x, y)
                if not band.covers(point):
                    continue
                footprint = box(x - 5120, y - 5120, x + 5120, y + 5120)
                if any(footprint.intersection(old).area > 0 for old in existing.values()):
                    continue
                # 기하 면적비 사전 검사다. 수집 후 실제 픽셀 중심 마스크를 다시 검사해야 한다.
                patch_count = sum(polygon.intersection(box(x - 5120 + c * 2560, y - 5120 + r * 2560,
                    x - 5120 + (c + 1) * 2560, y - 5120 + (r + 1) * 2560)).area / 2560**2 >= .95
                    for r in range(4) for c in range(4))
                if patch_count:
                    pool.append((patch_count, x, y, footprint))
        selected = []
        while pool and len(selected) < 8:
            pick = max(pool, key=lambda row: (min((row[1]-old[1])**2 + (row[2]-old[2])**2 for old in selected)
                if selected else row[0] * 1e8, row[0], row[1], row[2]))
            pool.remove(pick); selected.append(pick)
        for index, (patch_count, x, y, footprint) in enumerate(selected):
            lon, lat = inverse.transform(x, y)
            bbox = list(transform(inverse.transform, footprint).bounds)
            candidates.append({'province': province, 'spatial_window_id': f'v2-laneB-{province}-boundary-{index:02d}',
                'lon': lon, 'lat': lat, 'bbox': bbox, 'window_size': 1024, 'grid_crs': f'EPSG:{epsg}',
                'minimum_spacing_m': 10400, 'overlap_with_v1': False,
                'boundary_source_path': str(boundary_path.relative_to(ROOT)),
                'boundary_sha256': hashlib.sha256(boundary_bytes).hexdigest(),
                'expected_class_intent': ['built', 'crops', 'water_inside_province', 'bare'],
                'class_presence_verified': False, 'label_evidence': None,
                'geometric_patches_at_least_95_percent_inside': patch_count,
                'quality_eligible_patch_count': None, 'years': list(range(2020, 2026)),
                'reference': 'esri_io', 'selection_stratum': 'inside_boundary_band_1800_to_7400m'})
    result = {'schema_version': 1, 'lane': 'B', 'recorded_at': datetime.now(timezone.utc).isoformat(),
        'executed_network': False, 'collector_consumption_approved': False, 'candidates': candidates,
        'constraints': {'shared_coordinator_required': True, 'global_spacing_seconds': 2,
            'first_429_stops_all': True, 'patch_quality_minimum': .8, 'patch_province_inside_minimum': .95},
        'limitations': ['기하 후보이며 실제 도시·농경·수역·나지 클래스 존재는 미검증',
            '경계 인근 후보는 해안뿐 아니라 주 사이 경계도 포함',
            '1024창은 주 밖을 포함할 수 있으나 실제 패치는 주경계 마스크와 품질 기준 필수',
            '2020~2025 동년 ESRI는 약한 참조이며 독립 정답이 아님; WC와 혼합 매핑 금지']}
    target = ROOT / 'data/first-group-training-esri-v2/lane-b-candidates.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'path': str(target), 'candidate_windows': len(candidates), 'network_requests': 0}))


if __name__ == '__main__':
    main()
