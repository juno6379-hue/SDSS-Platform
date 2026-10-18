"""Only one newly collected target patch and raw B02; not a full inventory audit."""
from pathlib import Path
import datetime
import hashlib
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
for folder in ('.runtime', 'backend', 'scripts'):
    sys.path.insert(0, str(ROOT/folder))
from audit_priority_increment165 import native_patch, local, snapshot, require, sha
import numpy as np
import rasterio
from rasterio.io import MemoryFile

started = time.perf_counter()
E = ROOT/'evidence/integration'
read = lambda p: json.loads(p.read_text('utf-8'))
launch = read(E/'targeted170-execute-launch-20261018.json')
manifest = read(ROOT/'data/first-group-training-esri-v1/annual-window-report.json')
key = 'target256-bare-banten-2020-local-rank0-2020-4e7f2a1411cc'
rows = [row for row in manifest['scenes'] if row.get('patch_id', '').startswith(key+'-')]
require(len(rows) == 1, 'EXPECTED_EXACTLY_ONE_TARGET_PATCH')
row = rows[0]
require(row['province'] == 'banten' and row['split'] == 'val' and int(row['year']) == 2020, 'TARGET_IDENTITY')
boundary_path = local(ROOT, row['source_window']['boundary_path'])
boundary_raw = snapshot(boundary_path, 2 << 20)
require(sha(boundary_raw) == row['source_window']['boundary_sha256'], 'BOUNDARY_SHA')
features = [f for f in json.loads(boundary_raw)['features'] if f['properties']['province_id'] == 'banten']
require(len(features) == 1, 'BOUNDARY_IDENTITY')
checked = {}
native = native_patch(ROOT, row, features[0]['geometry'], checked)
require(native['quality_status'] == 'quality_eligible' and native['eligible_bare_pixels'] >= 256, 'TARGET_FINAL_QUALITY')
raw_ref = row['source_window']['raw_source_crops']['raw-B02.tif']
b02_path = local(ROOT, raw_ref['path'])
b02_raw = snapshot(b02_path, 2 << 20)
require(sha(b02_raw) == raw_ref['sha256'], 'RAW_B02_SHA')
checked[str(b02_path)] = sha(b02_raw)
image_raw = snapshot(local(ROOT, row['image_path']), 64 << 20)
require(sha(image_raw) == row['patch_sha256']['image'], 'IMAGE_SHA_SECOND_READ')
with rasterio.Env(GDAL_PAM_ENABLED='NO', GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR', GDAL_GEOREF_SOURCES='INTERNAL', PROJ_NETWORK='OFF'):
    with MemoryFile(image_raw) as im, MemoryFile(b02_raw) as bm:
        with im.open(driver='GTiff') as image, bm.open(driver='GTiff') as blue:
            require((blue.width, blue.height, blue.count) == (256, 256, 1), 'B02_SHAPE')
            require(image.crs == blue.crs and image.transform == blue.transform, 'B02_GRID_ALIGNMENT')
            require(image.crs.to_epsg() == 32748 and image.transform.a == 10 and image.transform.e == -10 and image.transform.b == image.transform.d == 0, 'B02_NATIVE_10M')
            require(np.array_equal(image.read(1), blue.read(1)), 'FINAL_BLUE_BAND_MISMATCH')
            actual_grid = {'crs': image.crs.to_string(), 'transform': list(image.transform)[:6],
                           'width': image.width, 'height': image.height, 'image_bands': image.count}
ledger = read(ROOT/'data/first-group-training-budget/global-ledger.json')
batch = ledger['batches'][key]
receipt = read(ROOT/'data/first-group-training-esri-v1/sources'/key/'worker-result.json')
require(batch['status'] == 'settled' and batch['charged_bytes'] == receipt['charged_bytes'] == 3827633, 'SETTLEMENT_MISMATCH')
require(receipt['live_b02_checked'] is True, 'B02_WITNESS')
require(all(ledger['batches'][k] == value for k, value in launch['pending_before'].items()), 'OLD_PENDING_CHANGED')
for value, digest in checked.items():
    require(sha(snapshot(Path(value), 64 << 20)) == digest, 'FOUR_FILE_POST_PIN')
result = {'at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'status': 'VERIFIED_REAL_BOUNDED_NEW_TARGET_PATCH',
          'elapsed_seconds': round(time.perf_counter()-started, 6),
          'patch_id': row['patch_id'], 'province': 'banten', 'year': 2020, 'split': 'val',
          'native': native, 'actual_grid': actual_grid, 'valid_fraction': native['valid_pixels']/65536,
          'inside_fraction': native['province_inside_pixels']/65536,
          'bare_contribution_patch_ge256': True, 'actual_final_blue_equals_raw_b02': True,
          'four_unique_raster_files_sha_verified': checked, 'boundary_sha_verified': sha(boundary_raw),
          'worker_ledger_settled_bytes': batch['charged_bytes'], 'old_pending_two_rows_unchanged': True,
          'old_pending_reserved_bytes': sum(v['reserved_bytes'] for v in launch['pending_before'].values()),
          'stored_manifest_physical_count': len(manifest['scenes']),
          'stored_manifest_eligible_count': sum(r.get('quality_status') == 'quality_eligible' for r in manifest['scenes']),
          'scope_limits': 'Only this new image/label/quality/rawB02 and local boundary were natively read. Does not replace ownerPID9664 full4704 prior-file pins/1152support inventory preservation audit. Weak Esri reference, not independent truth; no global bare gate or training clearance.',
          'scientific_accuracy_validated': False, 'training_ready': False,
          'network_calls': 0, 'collection_starts': 0, 'operating_data_writes': 0}
Path(__file__).with_suffix('.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps(result, ensure_ascii=True))
