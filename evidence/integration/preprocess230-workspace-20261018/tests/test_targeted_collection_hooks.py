"""Guard consumer tests: mocked transport/header only, no remote requests."""
from contextlib import ExitStack
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, Mock, patch
from urllib.error import HTTPError

import numpy as np
from rasterio.crs import CRS
from rasterio.transform import from_origin

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import collect_samples
from app.data import service


class TargetedCollectionHookTests(unittest.TestCase):
    def setUp(self):
        self.url = 'https://sentinel-cogs.s3.us-west-2.amazonaws.com/mock.tif'
        config = collect_samples.load_config(ROOT/'configs/collection.example.json')
        self.config = {**config, 'aois': config['aois'][:1], 'candidate_limit': 1,
                       'transient_asset_retries': 0, 'verify_product_metadata': False,
                       'periods': {'2021': {'start_date': '2021-06-01', 'end_date': '2021-09-30'}}}
        self.item = {'id': 'mock-scene', 'datetime': '2021-01-01', 'cloud_cover': 0,
                     'license': 'mock', 'assets': {'B02': {'href': self.url}}}

    def raster_context(self, reader=None):
        stack = ExitStack()
        src = MagicMock()
        src.crs = CRS.from_epsg(4326); src.bounds = (105, -6.064, 105.064, -6)
        src.transform = from_origin(105, -6, .001, .001)
        src.width = src.height = 64; src.index.return_value = (32, 32)
        src.window_transform.return_value = from_origin(105.028, -6.028, .001, .001)
        src.profile = {'crs': src.crs, 'transform': src.transform, 'dtype': 'uint8', 'count': 1,
                       'width': 64, 'height': 64, 'blockxsize': 16, 'blockysize': 16, 'tiled': True}
        src.read.return_value = np.ones((1, 8, 8), dtype='uint8')
        src.__enter__.return_value = src
        stack.enter_context(patch('rasterio.open', return_value=src))
        stack.enter_context(patch.object(service, 'resolve_asset_url', return_value=self.url+'?sig=PRIVATE'))
        stack.enter_context(patch.object(service, 'HTTPRangeReader', return_value=reader or SimpleNamespace(
            transferred=97, limit=100000, measurement_known=True, last_error=None)))
        return stack, src

    def test_legacy_wrapper_retains_five_positional_impl_arguments(self):
        with patch.object(service, '_read_cog_window_impl', return_value=('legacy',)) as impl:
            self.assertEqual(service.read_cog_window(self.url, [1, 2, 3, 4], 8, 90000), ('legacy',))
        self.assertEqual(len(impl.call_args.args), 5); self.assertEqual(impl.call_args.kwargs, {})

    def test_opt_in_wrapper_passes_callback_only_as_keyword(self):
        guard = Mock()
        with patch.object(service, '_read_cog_window_impl', return_value=('guarded',)) as impl:
            service.read_cog_window(self.url, [1, 2, 3, 4], 8, 90000, window_guard=guard)
        self.assertEqual(len(impl.call_args.args), 5)
        self.assertEqual(impl.call_args.kwargs, {'window_guard': guard})

    def test_header_guard_rejection_precedes_pixel_read_and_keeps_measured_accounting(self):
        stack, src = self.raster_context()
        with stack:
            with self.assertRaises(service.AssetTransferError) as caught:
                service.read_cog_window(self.url, [105.01, -6.05, 105.05, -6.01], 8, 100000,
                                        window_guard=Mock(side_effect=ValueError('GUARD_VETO')))
        src.read.assert_not_called()
        self.assertEqual(caught.exception.stage, 'window_geometry_guard')
        self.assertEqual(caught.exception.http_body_bytes, 97)
        self.assertTrue(caught.exception.transfer_measurement_known)
        self.assertIsInstance(caught.exception.__cause__, ValueError)

    def test_allowed_guard_observes_actual_header_window_without_signed_url(self):
        stack, src = self.raster_context(); guard = Mock()
        with stack:
            values, profile, stats = service.read_cog_window(
                self.url, [105.01, -6.05, 105.05, -6.01], 8, 100000, window_guard=guard)
        geometry = guard.call_args.args[0]
        self.assertEqual(geometry['crs'], 'EPSG:4326')
        self.assertEqual(geometry['source_width'], 64)
        self.assertEqual(geometry['source_transform'], list(src.transform)[:6])
        self.assertEqual(geometry['window'], {'col_off': 28, 'row_off': 28, 'width': 8, 'height': 8})
        self.assertEqual(geometry['window_transform'], list(src.window_transform.return_value)[:6])
        self.assertNotIn('PRIVATE', json.dumps(geometry)); self.assertNotIn('sig', json.dumps(geometry))
        src.read.assert_called_once(); self.assertEqual(values.shape, (1, 8, 8))
        self.assertEqual(profile['width'], 8); self.assertNotIn('tiled', profile)
        self.assertEqual(stats['http_body_bytes'], 97)

    def test_header_429_preserves_original_cause_and_does_not_call_guard(self):
        guard = Mock(); original = HTTPError(self.url, 429, 'Too Many Requests', {}, None)
        with patch.object(service, 'resolve_asset_url', return_value=self.url), \
                patch.object(service, 'HTTPRangeReader', side_effect=original):
            with self.assertRaises(service.AssetTransferError) as caught:
                service.read_cog_window(self.url, [1, 2, 3, 4], window_guard=guard)
        guard.assert_not_called(); self.assertIs(caught.exception.__cause__, original)
        self.assertEqual(caught.exception.http_body_bytes, 0)

    def test_scene_veto_precedes_metadata_and_pixel_fetch(self):
        guard = Mock(); guard.on_scene.side_effect = ValueError('SCENE_SPLIT_VETO')
        with tempfile.TemporaryDirectory() as temp, \
                patch.object(service, 'search_stac', return_value={'items': [self.item]}), \
                patch.object(service, 'read_cog_window') as read:
            root = Path(temp)
            report = collect_samples.collect_windows(self.config, root, True, collection_guard=guard)
            self.assertEqual(list(root.rglob('stac-item.json')), [])
            self.assertEqual(list(root.rglob('product-metadata.xml')), [])
        read.assert_not_called(); guard.on_scene.assert_called_once_with(
            self.item, self.config['aois'][0], '2021')
        self.assertFalse(report['learning_ready']); self.assertEqual(report['verified_patch_count'], 0)

    def collect_failed_window(self, known):
        guard = Mock(); guard.on_window.side_effect = ValueError('WINDOW_VETO')
        calls = []
        def read(*args, **kwargs):
            calls.append((args, kwargs))
            try:
                kwargs['window_guard']({'mock_geometry': True})
            except ValueError as exc:
                raise service.AssetTransferError('window_geometry_guard', 97, known) from exc
        with tempfile.TemporaryDirectory() as temp, \
                patch.object(service, 'search_stac', return_value={'items': [self.item]}), \
                patch.object(service, 'read_cog_window', side_effect=read):
            report = collect_samples.collect_windows(self.config, Path(temp), True, collection_guard=guard)
        return report, calls, guard

    def test_collector_window_hook_forwards_url_and_refunds_only_known_measurement(self):
        report, calls, guard = self.collect_failed_window(True)
        self.assertEqual(len(calls), 1); self.assertEqual(len(calls[0][0]), 4)
        guard.on_window.assert_called_once_with(self.url, {'mock_geometry': True})
        self.assertEqual(report['http_body_bytes_measured'], 97)
        self.assertEqual(report['http_body_bytes_upper_bound'], 97)

    def test_unknown_measurement_keeps_full_reservation_charged(self):
        report, calls, _ = self.collect_failed_window(False)
        self.assertEqual(report['http_body_bytes_measured'], 0)
        self.assertEqual(report['http_body_bytes_upper_bound'], calls[0][0][3])

    def test_candidate_scl_can_precede_scene_veto_and_is_also_window_guarded(self):
        guard = Mock(); order = []
        guard.on_scene.side_effect = lambda *args: (order.append('scene'), (_ for _ in ()).throw(ValueError('VETO')))[1]
        def read(url, bbox, pixels, cap, *, window_guard):
            window_guard({'candidate': True}); order.append('SCL')
            return np.ones((1, 1, 1)), {}, {'http_body_bytes': 10}
        def select(items, fetch, aoi, side, directory, root, minimum):
            fetch(self.url, aoi['bbox'], 1)
            return self.item, None, []
        with tempfile.TemporaryDirectory() as temp, \
                patch.object(service, 'search_stac', return_value={'items': [self.item]}), \
                patch.object(service, 'read_cog_window', side_effect=read), \
                patch.object(collect_samples, 'select_quality_candidate', side_effect=select):
            report = collect_samples.collect_windows({**self.config, 'candidate_limit': 2},
                Path(temp), True, collection_guard=guard)
            self.assertEqual(list(Path(temp).rglob('stac-item.json')), [])
        self.assertEqual(order, ['SCL', 'scene']); guard.on_window.assert_called_once()
        self.assertEqual(report['http_body_bytes_measured'], 10)

    def test_dry_run_invokes_neither_guard_nor_network(self):
        guard = Mock()
        with tempfile.TemporaryDirectory() as temp, patch.object(service, 'search_stac') as search:
            report = collect_samples.collect_windows(self.config, Path(temp), collection_guard=guard)
        search.assert_not_called(); self.assertEqual(guard.mock_calls, [])
        self.assertFalse(report['executed']); self.assertFalse(report['learning_ready'])


if __name__ == '__main__':
    unittest.main()
