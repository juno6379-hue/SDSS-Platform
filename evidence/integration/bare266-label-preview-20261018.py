"""One saved failed-batch label; no aggregate, ledger, HTTP or consumer access."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / '.runtime'))
HERE = ROOT / 'evidence/integration'
PREPARED = HERE / 'bare266-prepared-metadata-20261018.json'
PREPARED_SHA = '3e0343f730a2e475eb43b4f89547f91730686a3f6e029f7a5eb7e5fb610714fb'
BOUNDARY = ROOT / 'data/first-group-boundaries/selected-six.geojson'
BOUNDARY_SHA = 'de7722bfa88ddff3e12137d271c28717c23b3077a87b7dc36c66d1d8c522c909'
SOURCE_SHA = '9473861797b729b6b6eb60607a7edfb67921fa2b259bc2b0ffa8b2af08fc1353'
LEDGER_SHA = 'a92506b7b5b2ca5f668a21f9b111b32b3d2080a707ba9646bbf063c53dfe5aea'
LABEL_SHA = '10180e532308d221ac26e9c6db24e288b0b9ac79db404c6f3dfccd2f10e23097'
RESULT = HERE / 'bare266-label-preview-result-20261018.json'
STARTED = HERE / 'bare266-label-preview-started-20261018.json'
OFFICIAL_CLASSES = {0, 1, 2, 4, 5, 7, 8, 9, 10, 11}


def need(value, code):
    if not value:
        raise ValueError(code)


def identity(stat):
    return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)


def pinned(path, sha, cap):
    path = Path(path)
    need(path.resolve().is_relative_to(ROOT), 'INPUT_PATH_OUTSIDE_ROOT')
    before = path.stat()
    need(0 < before.st_size <= cap, 'INPUT_BYTE_BOUND')
    with path.open('rb') as stream:
        need(identity(os.fstat(stream.fileno())) == identity(before), 'INPUT_REPLACED_BEFORE_READ')
        raw = stream.read(cap + 1)
        after_handle = os.fstat(stream.fileno())
    need(len(raw) == before.st_size and len(raw) <= cap, 'INPUT_SIZE_CHANGED')
    need(identity(before) == identity(after_handle) == identity(path.stat()), 'INPUT_CHANGED_DURING_READ')
    need(hashlib.sha256(raw).hexdigest() == sha, 'INPUT_SHA_MISMATCH')
    return raw, identity(before)


def write_new(path, value):
    raw = (json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + '\n').encode('utf-8')
    with path.open('xb') as stream:
        stream.write(raw)


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('--approval', type=Path, required=True)
    parser.add_argument('--approval-sha256', required=True)
    args = parser.parse_args()
    approval = json.loads(pinned(args.approval, args.approval_sha256, 16384)[0])
    expected = {'schema_version': 1, 'kind': 'BARE266_ONE_SAVED_LABEL_ARRAY_GO',
                'approved': True, 'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'prepared_metadata_sha256': PREPARED_SHA, 'boundary_sha256': BOUNDARY_SHA,
                'operating_source_sha256': SOURCE_SHA, 'operating_ledger_sha256': LEDGER_SHA}
    need(type(approval) is dict and approval == expected and
         type(approval.get('schema_version')) is int and type(approval.get('approved')) is bool,
         'APPROVAL_CONTRACT_INVALID')
    prepared = json.loads(pinned(PREPARED, PREPARED_SHA, 65536)[0])
    refs = prepared['refs']
    for ref in refs:
        pinned(ROOT / ref['path'], ref['sha256'], 2 * 1024**2)
    pinned(BOUNDARY, BOUNDARY_SHA, 2 * 1024**2)
    need(not RESULT.exists(), 'RESULT_ALREADY_EXISTS')
    write_new(STARTED, {'at_utc': datetime.now(timezone.utc).isoformat(),
                        'approval_sha256': args.approval_sha256, 'runner_sha256': expected['runner_sha256']})
    start = time.monotonic()
    result = {'status': 'STARTED', 'raster_array_reads': 0, 'windows_scanned': 0,
              'ranked_windows': [], 'qualified_dense_inside_windows': 0,
              'scope': 'ONE_FAILED_BATCH_RAW_LABEL_ONLY_NOT_REGISTERED_PATCH',
              'province': 'southeast_sulawesi', 'year': 2024, 'fixed_split': 'train',
              'label_sha256': LABEL_SHA, 'label_file_bytes_read': 0,
              'boundary_sha256': BOUNDARY_SHA, 'operating_source_sha256_declared_by_root': SOURCE_SHA,
              'operating_ledger_sha256_declared_by_root': LEDGER_SHA,
              'operating_source_or_ledger_read_by_runner': False,
              'execution_supported': False, 'actual_quality_eligible': False,
              'scientifically_verified_bare': False, 'spatial_independence_verified': False,
              'existing_image_overlap_checked': False, 'pending_inventory_checked': False,
              'consumer_connected': False, 'ready_for_training': False,
              'http_calls': 0, 'collection_executed': False, 'training_executed': False,
              'aggregate_rows_created': 0}
    try:
        import numpy as np
        import rasterio
        from rasterio.io import MemoryFile
        label = Path(prepared['raw_label']['path'])
        need(label.name == 'raw-esri_io.tif' and prepared['raw_label']['sha256'] == LABEL_SHA,
             'LABEL_IDENTITY_INVALID')
        raw, label_identity = pinned(label, LABEL_SHA, 8 * 1024**2)
        result['label_file_bytes_read'] = len(raw)
        os.environ['PROJ_NETWORK'] = 'OFF'
        with rasterio.Env(GDAL_PAM_ENABLED='NO', GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR',
                          GDAL_GEOREF_SOURCES='INTERNAL'):
            with MemoryFile(raw) as memory:
                with memory.open(driver='GTiff') as ds:
                    need(ds.width == 2048 and ds.height == 2048 and ds.count == 1 and
                         ds.dtypes == ('uint8',) and ds.crs.to_epsg() == 32751 and
                         list(ds.transform)[:6] == [10.0, 0.0, 353750.0, 0.0, -10.0, 9609450.0] and
                         list(ds.bounds) == [353750.0, 9588970.0, 374230.0, 9609450.0] and ds.nodata == 0,
                         'LABEL_GRID_CONTRACT_INVALID')
                    result['raster_array_reads'] += 1
                    values = ds.read(1)
                    need(values.shape == (2048, 2048) and values.dtype == np.uint8,
                         'LABEL_ARRAY_CONTRACT_INVALID')
                    counts = np.bincount(values.ravel(), minlength=256)
                    histogram = {str(i): int(v) for i, v in enumerate(counts) if v}
                    result['actual_whole_label_class_counts'] = histogram
                    result['actual_whole_label_bare_pixels'] = int(counts[8])
                    need(set(np.flatnonzero(counts)).issubset(OFFICIAL_CLASSES), 'UNEXPECTED_ESRI_CLASS')
                    result['stored_histogram_exact_match'] = histogram == prepared['stored_label_preview_counts']
                    need(result['stored_histogram_exact_match'], 'STORED_HISTOGRAM_MISMATCH')
                    need(int(counts[8]) == 0, 'BARE_POSITIVE_REQUIRES_ROOT_REASSESSMENT')
        need(identity(label.stat()) == label_identity, 'LABEL_CHANGED_AFTER_ARRAY_READ')
        for ref in refs:
            pinned(ROOT / ref['path'], ref['sha256'], 2 * 1024**2)
        pinned(BOUNDARY, BOUNDARY_SHA, 2 * 1024**2)
        result.update(status='LOCAL_SAVED_LABEL_ACTUAL_ZERO_BARE_NO_TARGET_UNAPPROVED',
                      reason='WHOLE_LABEL_CLASS8_ZERO_IMPLIES_NO_256_WINDOW_WITH_256_BARE_PIXELS',
                      individual_256_windows_read=0, maximum_possible_bare_pixels_in_any_subwindow=0,
                      province_fraction_computed=False,
                      province_filter_reason='NO_WINDOW_CAN_MEET_PRIOR_BARE_PIXEL_MINIMUM',
                      logical_zero_candidates=True, label_identity_after_unchanged=True)
    except Exception as error:
        result['status'] = 'BLOCKED_PARTIAL_PRESERVED_NO_RETRY'
        result['issue'] = str(error) if type(error) is ValueError and str(error).replace('_', '').isalnum() else 'LOCAL_PREVIEW_ERROR'
    result['seconds'] = time.monotonic() - start
    write_new(RESULT, result)
    print(json.dumps({'status': result['status'], 'array_reads': result['raster_array_reads'],
                      'windows_scanned': result['windows_scanned'], 'result_path': str(RESULT),
                      'result_sha256': hashlib.sha256(RESULT.read_bytes()).hexdigest()}), flush=True)
    return 0 if result['status'].startswith('LOCAL_SAVED_LABEL_ACTUAL_ZERO') else 2


if __name__ == '__main__':
    raise SystemExit(main())
