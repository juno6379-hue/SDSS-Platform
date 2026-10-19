"""격자 집계의 패치별 해시를 검증하고 출처 자료로만 등록한다."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from app.store import Store

spec = importlib.util.spec_from_file_location('register_grid_collection', Path(__file__).resolve().parents[1] / 'scripts/register_collection.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class CollectionRegistryTests(unittest.TestCase):
    def fixture(self, root):
        paths = {}
        hashes = {}
        for name in ('image', 'label', 'quality'):
            path = root / (name + '.tif')
            path.write_bytes(('explicit-file-fixture-' + name).encode())
            paths[name] = str(path)
            hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest = root / 'annual-window-report.json'
        manifest.write_text(json.dumps({'scenes': [{'status':'rgb_window_downloaded', 'aoi':'east_java', 'year':'2020',
            'image_path':paths['image'], 'label_path':paths['label'], 'quality_mask_path':paths['quality'], 'patch_sha256':hashes}]}), encoding='utf-8')
        return manifest, paths

    def test_grid_manifest_without_shared_state_registers_verified_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, _ = self.fixture(root)
            with patch('sys.argv', ['register_collection', '--manifest',str(manifest),'--id','fixture','--data-root',str(root)]), contextlib.redirect_stdout(io.StringIO()):
                module.main()
            record = Store(root).get('datasets', 'fixture')
            self.assertEqual(record['verified_file_count'], 3)
            self.assertFalse(record['training_ready'])

    def test_changed_grid_label_does_not_register(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, paths = self.fixture(root)
            Path(paths['label']).write_bytes(b'changed')
            with patch('sys.argv', ['register_collection', '--manifest',str(manifest),'--id','fixture','--data-root',str(root)]):
                with self.assertRaises(ValueError):
                    module.main()
            self.assertEqual(Store(root).list('datasets'), [])
