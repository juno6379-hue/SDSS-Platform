"""격리된 합성 변화 지도·보고서 브라우저 검증 서버. 운영 자료나 모델 승인을 변경하지 않는다."""
import os
import json
from pathlib import Path
import sys
import tempfile

import numpy as np
import rasterio
from rasterio.transform import from_origin

ROOT = Path(__file__).resolve().parents[1]


def main():
    temporary = tempfile.TemporaryDirectory(prefix='geoai-sdss-fixture-')
    fixture_root = Path(temporary.name).resolve()
    if fixture_root.parent != Path(tempfile.gettempdir()).resolve():
        raise RuntimeError('합성 시험 임시 디렉터리가 예상 경로 밖에 있습니다.')
    os.environ['GEOAI_DATA_ROOT'] = str(fixture_root)
    os.environ['GEOAI_CORS_ORIGINS'] = 'http://localhost:5174,http://127.0.0.1:5174'
    # 독립 프로세스에서 최초 import하며 운영 카탈로그 위치로 초기화하지 않는다.
    sys.path.insert(0, str(ROOT / 'backend'))
    from app import main as server
    from app.ml.service import analyze_change
    import uvicorn
    profile = {'driver': 'GTiff', 'width': 16, 'height': 16, 'count': 1, 'dtype': 'uint8',
               'crs': 'EPSG:32748', 'transform': from_origin(500000, 9300000, 10, 10), 'nodata': 255}
    before = np.ones((16, 16), dtype='uint8')
    after = before.copy()
    after[4:12, 4:12] = 4
    for filename, values in [('synthetic-t1.tif', before), ('synthetic-t2.tif', after)]:
        with rasterio.open(fixture_root / filename, 'w', **profile) as output:
            output.write(values, 1)
    result = analyze_change({'t1_path': 'synthetic-t1.tif', 't2_path': 'synthetic-t2.tif',
                             'output_id': 'synthetic-change-fixture'}, fixture_root)
    result.update(id='synthetic-map-fixture', name='합성 fixture · 실제 정확도 아님', synthetic=True,
                  source='synthetic_fixture_only_not_production',
                  warning='합성 fixture · 실제 정확도 아님. 지정된 64픽셀 변화의 지도·산출물·보고서 연결 시험입니다.',
                  execution={'operation': 'analyze_change', 'fixture_only': True,
                             'inputs': {'t1_path': 'synthetic-t1.tif', 't2_path': 'synthetic-t2.tif'}})
    server.store.put('analyses', result)
    # 독립 임시 루트의 3연도 ESRI 코드 합성 지도다. 누락 연도는 일부러 비워 둔다.
    annual = fixture_root / 'first-group-synthetic-annual'
    annual.mkdir()
    scenes = []
    for year, code in [(2020, 2), (2021, 5), (2023, 7)]:
        values = np.full((16, 16), 1, dtype='uint8')
        values[3:13, 3:13] = code
        values[:2] = 0
        target = annual / f'synthetic-esri-{year}.tif'
        with rasterio.open(target, 'w', **{**profile, 'nodata': 0}) as output:
            output.write(values, 1)
        scenes.append({'aoi': 'synthetic_same_aoi', 'province': 'synthetic_fixture', 'year': year,
            'label_source': 'esri_io', 'label_path': str(target), 'bbox': [104.9, -6.4, 105.1, -6.2]})
    (annual / 'annual-window-report.json').write_text(json.dumps({'synthetic': True,
        'warning': '합성 fixture · 실제 관측·모델 정확도 아님', 'scenes': scenes}, ensure_ascii=False), encoding='utf-8')
    print(f'FIXTURE ONLY root={fixture_root} API=http://127.0.0.1:8001/api analysis=synthetic-map-fixture', flush=True)
    print('합성 fixture · 실제 정확도 아님 · 운영 모델/자료/승인 기록 변경 없음', flush=True)
    try:
        uvicorn.run(server.app, host='127.0.0.1', port=8001)
    finally:
        server.pool.shutdown(wait=True, cancel_futures=True)
        temporary.cleanup()


if __name__ == '__main__':
    main()
