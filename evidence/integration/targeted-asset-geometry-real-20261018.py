"""Observe a stored aligned image/label pair; no pixel QA, network or collector."""
from pathlib import Path
import sys
import hashlib
import json
from datetime import datetime, timezone

root = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(root / '.runtime'), str(root / 'backend')]
import rasterio
from rasterio.warp import transform_bounds
from app.data.targeted_asset_geometry import inspect_targeted_asset_geometry

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

manifest_path = root / 'data/first-group-training-esri-v1/annual-window-report.json'
manifest_bytes = manifest_path.read_bytes()
manifest = json.loads(manifest_bytes)
row = next(row for row in manifest['scenes'] if row.get('quality_status') == 'quality_eligible'
           and row.get('image_path') and row.get('label_path'))
paths = {}
for role in ('image', 'label'):
    path = Path(row[role + '_path'])
    path = (path if path.is_absolute() else root / 'data' / path).resolve()
    assert path.is_relative_to((root / 'data').resolve()) and path.is_file()
    paths[role] = path
before = {role: digest(path) for role, path in paths.items()}
with rasterio.Env(GDAL_PAM_ENABLED='NO', GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR', PROJ_NETWORK='OFF'):
    with rasterio.open(paths['image']) as dataset:
        bounds = dataset.bounds
        margin_x, margin_y = (bounds.right-bounds.left)/4, (bounds.top-bounds.bottom)/4
        bbox = list(transform_bounds(dataset.crs, 'EPSG:4326', bounds.left+margin_x,
                    bounds.bottom+margin_y, bounds.right-margin_x, bounds.top-margin_y,
                    densify_pts=1024))
assert type(row['year']) is str and row['year'] in {str(year) for year in range(2020,2026)}
declared_year = int(row['year'])
request = {'schema_version':1, 'kind':'TARGETED_ASSET_GEOMETRY_REQUEST',
           'target_year':declared_year, 'image_year':declared_year, 'label_year':declared_year,
           'target_bbox_wgs84':bbox,
           **{role+'_ref':{'path':path.relative_to(root).as_posix(), 'sha256':before[role]}
              for role,path in paths.items()}}
outcome = inspect_targeted_asset_geometry(root, request)
assert outcome['status'] == 'LOCAL_COVERAGE_OBSERVED_EXECUTION_BLOCKED', outcome
assert outcome['execution_supported'] is False and outcome['quality_verified'] is False
assert before == {role: digest(path) for role,path in paths.items()}
protected = json.loads((root/'evidence/integration/targeted-asset-geometry-preflight-20261018.json').read_text(encoding='utf-8-sig'))
protected_matches = {entry['path']:digest(root/entry['path']) == entry['sha256'] for entry in protected}
report = {'observed_at_utc':datetime.now(timezone.utc).isoformat(),
          'classification':'VERIFIED_REAL_LOCAL_HEADERS_AND_PINNED_BYTES_ONLY',
          'manifest_sha256_at_read':hashlib.sha256(manifest_bytes).hexdigest(),
          'request':request, 'result':outcome, 'original_pair_sha_unchanged':True,
          'protected_source_matches_preflight':protected_matches,
          'module_sha256':digest(root/'backend/app/data/targeted_asset_geometry.py'),
          'limits':'Interior bbox of one stored aligned pair, not a new256-pixel crop or remote COG preflight. Declared year equality is not temporal truth. No pixel reads/QA or bare count validation.',
          'initial_probe':'Caller copied legacy manifest string year and was correctly blocked REQUEST_INVALID. Caller now explicitly declares validated integer year; no source/year data altered.',
          'network_requests':0, 'operating_writes':0, 'collectors_started':0}
with (root/'evidence/integration/targeted-asset-geometry-real-20261018.json').open('x',encoding='utf-8') as stream:
    json.dump(report,stream,ensure_ascii=False,indent=2)
    stream.write('\n')
print(json.dumps({'status':outcome['status'],'pair_preserved':True,'protected_source_unchanged':all(protected_matches.values())}, ensure_ascii=True))
