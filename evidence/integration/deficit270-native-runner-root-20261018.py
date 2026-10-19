"""Root GO 뒤 새270분만 1회 검사. 제품/운영자료/원장 쓰기와 HTTP 없음."""
from pathlib import Path
import argparse
import copy
import json
import sys
import tempfile
from contextlib import ExitStack, redirect_stdout, redirect_stderr

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'backend'), str(ROOT)]
from audit_priority_increment165 import audit_increment, canonical, local, read_json, sha, snapshot


def run(result):
    import numpy as np
    import rasterio
    from rasterio.io import MemoryFile
    from rasterio.windows import Window, transform
    from rasterio.warp import reproject, Resampling
    from app.data.readiness_connectivity_witness import FIXED_PROVINCE_SPLITS

    data = ROOT / 'data'
    evidence = ROOT / 'evidence/integration'
    read = lambda p, cap=16 << 20: read_json(p, cap)[1]
    launch_path = evidence / 'deficit270-launch-root-20261018.json'
    launch_raw = snapshot(launch_path, 1 << 20)
    launch = json.loads(launch_raw)
    terminal = read(evidence / 'deficit270-terminal-root-20261018.json')
    request = read(evidence / 'deficit270-request-root-20261018.json')
    assert sha(json.dumps(request, sort_keys=True, ensure_ascii=False, allow_nan=False,
                          separators=(',', ':')).encode()) == launch['request_sha256']
    assert terminal['exit_code'] == 0
    assert len(launch['selected_jobs']) == 1 and launch['maximum_new_physical_patches'] == 16
    job = launch['selected_jobs'][0]
    key = job['key']
    mp = data / 'first-group-training-esri-v1/annual-window-report.json'
    lp = data / 'first-group-training-budget/global-ledger.json'
    assert not (lp.parent / 'global-ledger.execution.lock').exists()
    manifest_raw, manifest = read_json(mp, 128 << 20)
    ledger_raw, ledger = read_json(lp, 16 << 20)
    prior_raw, prior = read_json(local(ROOT, request['current_manifest_ref']['path']), 128 << 20)
    assert sha(prior_raw) == request['current_manifest_ref']['sha256'] == launch['manifest_before_sha256']
    old_count = launch['source_rows_before']
    assert old_count == len(prior['scenes']) == 1715
    assert manifest['scenes'][:old_count] == prior['scenes']
    assert manifest.get('historical_noneligible_patches', []) == prior.get('historical_noneligible_patches', [])
    rows = manifest['scenes'][old_count:]
    assert 0 < len(rows) <= 16 and all(row['patch_id'].startswith(key + '-') for row in rows)
    assert all(row['split'] == job['split'] == FIXED_PROVINCE_SPLITS[job['province']] for row in rows)
    config = read(mp.parent / 'sources' / key / 'config.json')
    assert canonical(config) == job['config_sha256'] == ledger['batches'][key]['config_sha256']
    assert request['schema_version'] == 2
    marker = 'DEFICIT_AOI_BBOX_CONTAINS_V1'
    assert config['candidate_metadata_policy'] == request['candidate_metadata_policy'] == marker
    assert all(ledger['batches'].get(k) == v for k, v in launch['pending_before'].items())
    adapter = copy.deepcopy(launch)
    adapter.update(manifest_before_rows=old_count, old_rows_canonical_sha256=canonical(prior['scenes']))
    result['native_helper_invocations'] = 1
    print('NATIVE_HELPER_ONCE_BEGIN', flush=True)
    with tempfile.TemporaryDirectory(prefix='geoai270-native-') as temp:
        adapted_path = Path(temp) / 'launch165-adapter.json'
        adapted_path.write_text(json.dumps(adapter, ensure_ascii=False), encoding='utf-8')
        product = audit_increment(data, adapted_path, (data / 'first-group-boundaries/selected-six.geojson').absolute())
    result['product165'] = product
    assert product['native_validation_complete'] and product['native_patches_checked'] == len(rows)
    assert not any(product['external_metadata_changed_during_audit'].values())
    assert not product['execution_lock_present_at_read']
    report = read(mp.parent / 'sources' / key / 'annual-window-report.json')
    downloaded = [s for s in report['scenes'] if s.get('status') == 'rgb_window_downloaded']
    assert len(downloaded) == 1
    scene = downloaded[0]
    summary = scene['candidate_metadata_filter']
    assert summary['policy'] == marker
    assert summary['request_sha256'] == launch['request_sha256']
    assert summary['source_sha256'] == launch['manifest_before_sha256']
    n = summary['input_count']
    assert type(n) is int and 0 <= n <= 20
    assert len(summary['items']) == n
    assert sorted(x['input_index'] for x in summary['items']) == list(range(n))
    assert sorted(x['cloud_rank'] for x in summary['items']) == list(range(n))
    assert summary['retained_count'] + summary['excluded_count'] == n
    assert sum(x['reason'] == 'METADATA_CONTAINS_AOI' for x in summary['items']) == summary['retained_count']
    assert summary['selected_pool_count'] == min(config['candidate_limit'], summary['retained_count']) <= 5
    assert not any(s in json.dumps(summary) for s in ('http:', 'https:', '?sig='))
    checked = {}

    def load(path, pin, cap):
        confined = local(data, path)
        raw = snapshot(confined, cap)
        assert sha(raw) == pin
        checked[str(confined)] = pin
        return raw

    row = rows[0]
    ref = row['source_window']
    sref = ref['stac_item']
    stac = json.loads(load(sref['path'], sref['sha256'], 16 << 20))
    assert stac['id'] == scene['scene_id'] == row['scene_id']
    assert stac['properties']['datetime'] == scene['datetime'] == row['datetime']
    assert stac['collection'] == 'sentinel-2-l2a'
    aoi_box = config['aois'][0]['bbox']
    box = stac['bbox']
    assert len(box) == 4 and box[0] <= aoi_box[0] and box[1] <= aoi_box[1]
    assert box[2] >= aoi_box[2] and box[3] >= aoi_box[3]
    bref = ref['raw_source_crops']['raw-B02.tif']
    lref = ref['raw_source_crops']['raw-esri_io.tif']
    assert stac['assets']['B02']['href'].split('?')[0] == bref['source'].split('?')[0]
    bare = []
    with rasterio.Env(GDAL_PAM_ENABLED='NO', GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR', PROJ_NETWORK='OFF'):
        with ExitStack() as stack:
            def open_tiff(raw):
                assert raw[:4] in (b'II*\x00', b'MM\x00*', b'II+\x00', b'MM\x00+')
                return stack.enter_context(stack.enter_context(MemoryFile(raw)).open(driver='GTiff'))

            b02 = open_tiff(load(bref['path'], bref['sha256'], 64 << 20))
            image = open_tiff(load(ref['path'], ref['sha256'], 64 << 20))
            label = open_tiff(load(lref['path'], lref['sha256'], 64 << 20))
            quality = open_tiff(load(ref['quality_mask_path'], ref['quality_mask_sha256'], 2 << 20))
            signature = lambda ds: (ds.crs, ds.transform, ds.width, ds.height)
            assert signature(b02) == signature(image) == signature(quality)
            assert (image.width, image.height, image.count) == (1024, 1024, 6) and b02.count == 1
            assert label.width <= 2048 and label.height <= 2048 and label.count == 1
            assert quality.count == 1 and quality.dtypes == ('uint8',)
            assert image.transform.a == 10 and image.transform.e == -10 and image.transform.b == image.transform.d == 0
            blue = b02.read(1)
            assert np.array_equal(blue, image.read(1))
            q = quality.read(1)
            aligned = np.zeros((1024, 1024), dtype='uint8')
            reproject(label.read(1), aligned, src_transform=label.transform, src_crs=label.crs,
                      src_nodata=0, dst_transform=image.transform, dst_crs=image.crs,
                      dst_nodata=0, resampling=Resampling.nearest)
            for row in rows:
                assert row['source_window'] == ref and row['scene_id'] == stac['id']
                assert row['label_year'] == int(row['year']) == job['year']
                patch = open_tiff(load(row['image_path'], row['patch_sha256']['image'], 64 << 20))
                w = Window(*row['window_in_source'])
                assert w.width == w.height == 256 and 0 <= w.col_off <= 768 and 0 <= w.row_off <= 768
                assert patch.crs == image.crs and patch.transform == transform(w, image.transform)
                rr, cc = int(w.row_off), int(w.col_off)
                s = (slice(rr, rr + 256), slice(cc, cc + 256))
                assert np.array_equal(patch.read(1), blue[s])
                final_bare = row['sample_class_coverage'].get('8', 0)
                eligible = row['quality_status'] == 'quality_eligible'
                bare.append({'patch_id': row['patch_id'], 'raw_aligned_bare_pixels': int(np.sum(aligned[s] == 8)),
                             'after_source_quality_bare_pixels': int(np.sum((aligned[s] == 8) & (q[s] == 1))),
                             'final_supported_bare_pixels': final_bare, 'quality_status': row['quality_status'],
                             'eligible_bare_pixels': final_bare if eligible else 0,
                             'eligible_bare_contribution': bool(eligible and final_bare >= 256)})
            native_grid = {'crs': str(image.crs), 'transform': list(image.transform)[:6], 'shape': [1024, 1024], 'bands': 6}
    expected_files = {str(local(data, row[field])) for row in rows for field in ('image_path', 'label_path', 'quality_mask_path')}
    actual_files = {str(p.absolute()) for p in (mp.parent / 'patches' / key).rglob('*.tif')}
    assert actual_files == expected_files and len(actual_files) == 3 * len(rows) <= 48
    for path, pin in checked.items():
        assert sha(snapshot(Path(path), 64 << 20)) == pin
    assert snapshot(mp, 128 << 20) == manifest_raw and snapshot(lp, 16 << 20) == ledger_raw
    assert snapshot(launch_path, 1 << 20) == launch_raw
    worker = read(mp.parent / 'sources' / key / 'worker-result.json')
    final = [json.loads(x) for x in (evidence / 'deficit270-live-root-20261018-stdout.log').read_text('utf-8-sig').splitlines() if x.strip()][-1]
    assert all(final['execution_progress'][name] == [key] for name in ('finalization_attempted_batches', 'settled_batches', 'published_batches'))
    result.update(status='COMPLETED_BOUNDED_NATIVE_AND_TRACE_CHECKED', native_validation_complete=True,
                  original_launch_sha256=sha(launch_raw), source_sha256=sha(manifest_raw), ledger_sha256=sha(ledger_raw),
                  source_bytes=len(manifest_raw), old_rows_exact=True, old_history_exact=True,
                  old_pending_exact=True, old_pending_reserved_bytes=sum(v['reserved_bytes'] for v in launch['pending_before'].values()),
                  metadata_filter_summary=summary, metadata_filter_trace_scope='Stored bounded summary + selectedSTACbbox verified; all20 originalfeatures not independently replayed',
                  selected_scene=stac['id'], selected_datetime=stac['properties']['datetime'], actual_source_grid=native_grid,
                  raw_b02_source_firstband_equal=True, patch_firstband_and_grid_matches=len(rows),
                  actual_new_patch_rasters=len(actual_files), new_unreferenced_patch_rasters=0,
                  source_trace_file_sha_rechecks=len(checked), trace_counts_overlap_product_image_files=len(rows),
                  bare_per_patch=bare, raw_aligned_bare_pixels=sum(x['raw_aligned_bare_pixels'] for x in bare),
                  after_source_quality_bare_pixels=sum(x['after_source_quality_bare_pixels'] for x in bare),
                  final_supported_bare_pixels=sum(x['final_supported_bare_pixels'] for x in bare),
                  eligible_bare_pixels=sum(x['eligible_bare_pixels'] for x in bare),
                  eligible_bare_contribution_patches=sum(x['eligible_bare_contribution'] for x in bare),
                  cog_charged_bytes=worker['cog_charged_bytes'], metadata_charged_bytes=worker['metadata_budget']['charged_bytes'],
                  total_settled_bytes=worker['charged_bytes'], remaining_budget=ledger['additional_maximum_bytes']-ledger['new_charged_bytes'],
                  physical_before=final['physical_inventory_before'], physical_after_inferred=final['physical_inventory_before']['physical_patch_count']+len(rows),
                  metadata_two_reads_stable=True, terminal_seconds=terminal['seconds'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root-go', action='store_true')
    args = parser.parse_args()
    if not args.root_go:
        parser.error('ROOT_FIXED_SOURCE_GO_REQUIRED')
    prefix = ROOT / 'evidence/integration/deficit270-native-root-20261018'
    result = {'status': 'INCOMPLETE', 'native_helper_invocations': 0, 'native_validation_complete': False,
              'reviewer_http_calls': 0, 'reviewer_collection_starts': 0, 'operating_writes': 0,
              'learning_ready': False, 'scientific_accuracy_validated': False}
    with Path(str(prefix) + '.json').open('x', encoding='utf-8') as output, Path(str(prefix) + '.log').open('x', encoding='utf-8') as log, Path(str(prefix) + '-stderr.log').open('x', encoding='utf-8') as error:
        try:
            with redirect_stdout(log), redirect_stderr(error):
                run(result)
        except Exception as exc:
            result['issue_type'] = type(exc).__name__
            result['status'] = 'INCOMPLETE_PRESERVED_NO_RETRY'
            error.write(type(exc).__name__ + '\n')
        finally:
            json.dump(result, output, ensure_ascii=False, indent=2)
    print(json.dumps({'status': result['status'], 'native_helper_invocations': result['native_helper_invocations']}))
    return 0 if result['native_validation_complete'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
