"""Portable pinned test fixture loader; code-only synthetic checks."""
import hashlib,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import manifest_profile_baseline_fixtures as baseline
class BaselinePackaging242Tests(unittest.TestCase):
    def test_all_explicit_fixture_pins_and_provenance_match(self):
        document=json.loads((baseline.BASELINE_ROOT/'manifest.json').read_text('utf-8'))
        self.assertTrue(document['no_mutable_current_source_fallback'])
        self.assertEqual(set(baseline.BASELINES),{entry['name'] for entry in document['files']})
        for entry in document['files']:
            self.assertEqual(baseline.BASELINES[entry['name']]['sha256'],entry['sha256'])
            raw=baseline.baseline_bytes(entry['name'])
            self.assertEqual((len(raw),hashlib.sha256(raw).hexdigest()),(entry['bytes'],entry['sha256']))
    def test_missing_fixture_does_not_fall_back_or_skip(self):
        manifest=(baseline.BASELINE_ROOT/'manifest.json').read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'manifest.json').write_bytes(manifest)
            with patch.object(baseline,'BASELINE_ROOT',root):
                with self.assertRaises(FileNotFoundError):baseline.load_baseline('status230','app._missing_baseline242','app')
    def test_tampered_code_or_manifest_cannot_rebase_expected_sha(self):
        manifest=(baseline.BASELINE_ROOT/'manifest.json').read_bytes();code=baseline.baseline_bytes('status230')
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'manifest.json').write_bytes(manifest);path=root/baseline.BASELINES['status230']['file'];path.write_bytes(code+b'\n# altered')
            with patch.object(baseline,'BASELINE_ROOT',root):
                with self.assertRaisesRegex(AssertionError,'SHA mismatch'):baseline.load_baseline('status230','app._changed_baseline242','app')
                path.write_bytes(code);(root/'manifest.json').write_bytes(manifest+b' ')
                with self.assertRaisesRegex(AssertionError,'SHA mismatch'):baseline.load_baseline('status230','app._changed_manifest242','app')
    def test_baseline_script_loader_restores_sys_path(self):
        before=sys.path[:]
        module=baseline.load_baseline('centers230','scripts._pinned_baseline242','scripts')
        self.assertEqual(sys.path,before)
        self.assertEqual(Path(module.__file__).parent,baseline.BASELINE_ROOT)
        self.assertFalse(any(parent.name.startswith('preprocess230-workspace') for parent in Path(__file__).resolve().parents))
if __name__=='__main__':unittest.main()
