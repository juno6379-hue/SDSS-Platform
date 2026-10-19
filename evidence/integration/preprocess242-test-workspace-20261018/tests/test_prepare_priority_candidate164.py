"""Bounded local snapshot and exclusive-run safety; no raster/network/training."""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from scripts import prepare_priority_candidate164 as subject


class PriorityPreprocessing164Tests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = self.root / 'data'; self.data.mkdir()
        self.evidence = self.root / 'evidence'; self.evidence.mkdir()
        self.source = self.data / 'source.json'
        self.source.write_text(json.dumps({'scenes': [{'image_path': str(self.data / 'image.tif'), 'label_path': str(self.data / 'label.tif'), 'quality_mask_path': str(self.data / 'quality.tif')}]}), encoding='utf8')
        self.policy = self.data / 'policy.json'; self.policy.write_text('{}', encoding='utf8')
        self.pin = subject.digest(self.source); self.ppin = subject.digest(self.policy)

    def invoke(self, **overrides):
        args = {'data_root': self.data, 'source': self.source, 'source_pin': self.pin, 'policy': self.policy, 'policy_pin': self.ppin, 'run_id': 'test', 'evidence_root': self.evidence}
        args.update(overrides)
        return subject.prepare(**args)

    def test_copy_is_exact_and_exclusive(self):
        target = self.data / 'copy.json'
        size = subject.copy_pinned(self.source, target, self.pin)
        self.assertEqual(size, self.source.stat().st_size)
        self.assertEqual(target.read_bytes(), self.source.read_bytes())
        with self.assertRaises(FileExistsError):
            subject.copy_pinned(self.source, target, self.pin)

    def test_stale_pin_rejected_before_new_runs(self):
        with self.assertRaises(ValueError):
            self.invoke(source_pin='0' * 64)
        self.assertEqual(list(self.evidence.iterdir()), [])
        self.assertFalse((self.data / 'priority164-test').exists())

    def test_bad_run_id_rejected(self):
        for run_id in ('../escape', 'bad/name', '', 'a' * 49):
            with self.subTest(run_id=run_id), self.assertRaises(ValueError):
                self.invoke(run_id=run_id)

    def test_relative_source_and_external_source_rejected(self):
        with self.assertRaises(ValueError):
            self.invoke(source=Path('source.json'))
        external = self.root / 'external.json'; external.write_bytes(self.source.read_bytes())
        with self.assertRaises(ValueError):
            self.invoke(source=external)

    def test_existing_or_partial_runs_never_reused(self):
        partial = self.data / 'priority164-test'; partial.mkdir()
        marker = partial / 'partial'; marker.write_bytes(b'preserved')
        with patch.object(subject, 'assess') as assess, self.assertRaises(ValueError):
            self.invoke()
        assess.assert_not_called()
        self.assertEqual(marker.read_bytes(), b'preserved')

    def test_qa_failure_preserves_snapshot_and_blocks_rerun(self):
        original = self.source.read_bytes()
        with patch.object(subject, 'assess', side_effect=ValueError('synthetic QA refusal')):
            with self.assertRaises(ValueError):
                self.invoke()
        frozen = self.data / 'priority164-test/source.json'
        self.assertEqual(frozen.read_bytes(), original)
        self.assertTrue((self.evidence / 'priority164-test/preflight.json').is_file())
        self.assertFalse((self.evidence / 'priority164-test/summary.json').exists())
        with self.assertRaises(ValueError):
            self.invoke()
        self.assertEqual(self.source.read_bytes(), original)

    def test_copy_detects_concurrent_source_change(self):
        real_digest = subject.digest
        calls = 0
        def digest(path):
            nonlocal calls
            calls += 1
            if calls == 2:
                self.source.write_bytes(b'concurrent collector replaced source')
            return real_digest(path)
        target = self.data / 'copy.json'
        with patch.object(subject, 'digest', side_effect=digest), self.assertRaises(ValueError):
            subject.copy_pinned(self.source, target, self.pin)
        self.assertTrue(target.exists())
        self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(), self.pin)

    def test_copy_cap_refuses_before_destination(self):
        target = self.data / 'copy.json'
        with self.assertRaises(ValueError):
            subject.copy_pinned(self.source, target, self.pin, cap=1)
        self.assertFalse(target.exists())

    def test_relative_raster_paths_refused_before_assess(self):
        self.source.write_text(json.dumps({'scenes': [{'image_path': 'relative.tif', 'label_path': 'relative.tif', 'quality_mask_path': 'relative.tif'}]}), encoding='utf8')
        with patch.object(subject, 'assess') as assess, self.assertRaises(ValueError):
            self.invoke(source_pin=subject.digest(self.source))
        assess.assert_not_called()


if __name__ == '__main__':
    unittest.main()
