"""Isolated source-collection → common DatasetVersion registry integration."""
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.data import collection_registration as module
from app.dataset_registry import register_version, resolve_version
from app.store import Store

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("collection_version_cli", ROOT / "scripts/register_collection.py")
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)


class CollectionVersionRegistrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = Store(self.root, recover_jobs=False)
        self.paths, self.hashes = {}, {}
        for key in ("image", "label", "quality"):
            path = self.root / (key + ".tif")
            path.write_bytes(("tiny-synthetic-" + key).encode())
            self.paths[key] = path
            self.hashes[key] = hashlib.sha256(path.read_bytes()).hexdigest()
        self.report = self.root / "annual-window-report.json"
        self.row = {"status": "rgb_window_downloaded", "aoi": "banten", "year": "2024",
                    "image_path": str(self.paths["image"]), "label_path": str(self.paths["label"]),
                    "quality_mask_path": str(self.paths["quality"]), "patch_sha256": self.hashes}
        self.save_report({"scenes": [self.row]})
        self.manifest = {"schema_version": "0.2.0", "dataset_id": "collection-fixture", "version": "v1",
                         "source": {"institution": "synthetic-test", "product": "source-report", "license": "test-only"},
                         "data_type": "document", "spatial": {"bbox": [105, -7, 107, -5], "crs": "OGC:CRS84"},
                         "temporal": {"start": "2024-01-01T00:00:00Z", "end": "2024-12-31T00:00:00Z", "calendar": "gregorian"},
                         "quality_status": "RAW", "access_class": "RESTRICTED", "lineage": [],
                         "artifact_uri": self.report.name, "sha256": self.sha(self.report)}

    def tearDown(self):
        self.temp.cleanup()

    def sha(self, path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def save_report(self, document):
        self.report.write_text(json.dumps(document), encoding="utf-8")

    def register(self, manifest=None):
        return module.register_collection_version(self.store, self.report, manifest or self.manifest,
                                                  expected_dataset_id="collection-fixture")

    def test_real_registry_registration_resolve_and_idempotence_single_namespace(self):
        before = {p: p.read_bytes() for p in [self.report, *self.paths.values()]}
        first = self.register()
        self.assertEqual(first, self.register())
        self.assertEqual(resolve_version(self.store, "collection-fixture", "v1", self.manifest["sha256"]), first["dataset_version"])
        self.assertEqual(len(self.store.list("dataset_versions")), 1)
        self.assertEqual(self.store.list("datasets"), [])
        self.assertEqual(first["verified_file_count"], 3)
        self.assertEqual(first["quality_gate"], "SOURCE_FILE_HASHES_ONLY")
        for field in ("training_ready", "scientific_accuracy_validated", "deployment_approval"):
            self.assertIs(first[field], False)
        self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_explicit_parent_lineage_resolves_and_preserves_version(self):
        parent = dict(self.manifest, dataset_id="source-parent", version="pinned-v2")
        register_version(self.store, parent)
        self.manifest["lineage"] = [{"id": "source-parent", "version": "pinned-v2", "sha256": parent["sha256"], "role": "source"}]
        self.assertEqual(self.register()["dataset_version"]["manifest"]["lineage"], self.manifest["lineage"])
        self.assertEqual(len(self.store.list("dataset_versions")), 2)

    def test_missing_wrong_or_duplicate_parent_and_self_are_blocked_before_write(self):
        variants = [[{"id": "missing", "version": "v1", "sha256": "f" * 64}],
                    [{"id": "collection-fixture", "version": "v1", "sha256": self.manifest["sha256"]}]]
        parent = {"id": "missing", "version": "v1", "sha256": "f" * 64}
        variants.append([parent, copy.deepcopy(parent)])
        for lineage in variants:
            with self.subTest(lineage=lineage), self.assertRaises((ValueError, KeyError)):
                self.register(dict(self.manifest, lineage=lineage))
        self.assertEqual(self.store.list("dataset_versions"), [])

    def test_conflicting_existing_version_is_never_overwritten(self):
        first = self.register()["dataset_version"]
        changed = copy.deepcopy(self.manifest)
        changed["source"]["product"] = "different"
        with self.assertRaisesRegex(ValueError, "새 버전"):
            self.register(changed)
        self.assertEqual(self.store.get("dataset_versions", first["id"]), first)

    def test_new_mode_does_not_claim_quality_gate_or_infer_metadata(self):
        for quality in ("VALIDATED", "STANDARDIZED", "REJECTED"):
            with self.assertRaises(ValueError):
                self.register(dict(self.manifest, quality_status=quality))
        with self.assertRaises(ValueError):
            self.register(dict(self.manifest, data_type="raster"))
        for field in ("source", "spatial", "temporal", "version", "lineage"):
            manifest = copy.deepcopy(self.manifest)
            del manifest[field]
            with self.assertRaises(ValueError):
                self.register(manifest)
        staged = self.register(dict(self.manifest, quality_status="STAGED"))
        self.assertFalse(staged["training_ready"])

    def test_changed_each_file_missing_quality_wrong_report_or_id_has_no_write(self):
        for key in self.paths:
            original = self.paths[key].read_bytes()
            self.paths[key].write_bytes(b"changed")
            with patch.object(self.store, "connect", side_effect=AssertionError("registry write")) as connect:
                with self.assertRaises(ValueError):
                    self.register()
                connect.assert_not_called()
            self.paths[key].write_bytes(original)
        for manifest in (dict(self.manifest, sha256="a" * 64), dict(self.manifest, dataset_id="wrong"),
                         dict(self.manifest, artifact_uri="image.tif")):
            with patch.object(self.store, "connect", side_effect=AssertionError("registry write")) as connect:
                with self.assertRaises(ValueError):
                    self.register(manifest)
                connect.assert_not_called()
        del self.row["patch_sha256"]["quality"]
        self.save_report({"scenes": [self.row]})
        self.manifest["sha256"] = self.sha(self.report)
        with self.assertRaises(ValueError):
            self.register()
        self.assertEqual(self.store.list("dataset_versions"), [])

    def test_legacy_window_state_requires_exact_row_artifact_binding(self):
        del self.row["patch_sha256"]
        self.save_report({"scenes": [self.row]})
        self.manifest["sha256"] = self.sha(self.report)
        state = {"cells": {"banten-2024": {k: {"path": str(v), "sha256": self.hashes[k]} for k, v in self.paths.items()}}}
        state_path = self.root / "window-state.json"
        state_path.write_text(json.dumps(state), encoding="utf-8")
        self.assertEqual(self.register()["verified_file_count"], 3)
        state["cells"]["banten-2024"]["label"] = state["cells"]["banten-2024"]["image"]
        state_path.write_text(json.dumps(state), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "different files"):
            self.register()

    def test_invalid_province_year_empty_scenes_and_remote_paths_block(self):
        for field, value in (("aoi", "outside"), ("year", True), ("year", "2026"), ("province", "west_java"),
                             ("image_path", "https://example.invalid/source"), ("image_path", "../outside.tif")):
            row = {**self.row, field: value}
            self.save_report({"scenes": [row]})
            self.manifest["sha256"] = self.sha(self.report)
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                self.register()
        for scenes in ([], [None], [{"status": "no_scene"}], {}):
            self.save_report({"scenes": scenes})
            self.manifest["sha256"] = self.sha(self.report)
            with self.assertRaises(ValueError):
                self.register()
        self.assertEqual(self.store.list("dataset_versions"), [])

    def test_strict_json_size_duplicate_nonfinite_and_changed_report(self):
        path = self.root / "bad.json"
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'[]', b'\xff'):
            path.write_bytes(raw)
            with self.assertRaises(ValueError):
                module.read_registration_json(path)
        path.write_bytes(b'{}')
        with self.assertRaises(ValueError):
            module.read_registration_json(path, maximum=1)
        original = module._verified_file
        count = 0

        def tamper(*args):
            nonlocal count
            result = original(*args)
            count += 1
            if count == 3:
                self.save_report({"scenes": [self.row], "tampered": True})
            return result

        with patch.object(module, "_verified_file", side_effect=tamper), self.assertRaisesRegex(ValueError, "report changed"):
            self.register()
        self.assertEqual(self.store.list("dataset_versions"), [])

    def test_cli_explicit_mode_writes_common_version_only_and_multiple_reports_rejected(self):
        manifest_path = self.root / "dataset-manifest.json"
        manifest_path.write_text(json.dumps(self.manifest), encoding="utf-8")
        argv = ["register_collection", "--manifest", str(self.report), "--id", "collection-fixture", "--data-root", str(self.root),
                "--registry-manifest", str(manifest_path)]
        output = io.StringIO()
        with patch("sys.argv", argv), contextlib.redirect_stdout(output):
            cli.main()
        self.assertEqual(json.loads(output.getvalue())["dataset_version"]["manifest"], self.manifest)
        self.assertEqual(self.store.list("datasets"), [])
        self.assertEqual(len(self.store.list("dataset_versions")), 1)
        with patch("sys.argv", argv[:3] + [str(self.report)] + argv[3:]), self.assertRaises(ValueError):
            cli.main()

    def test_cli_legacy_omission_matches_original_source(self):
        original_path = ROOT / "evidence/integration/data-pipeline-original-register-collection-20261018.py"
        self.assertEqual(self.sha(original_path), "2d99a02d6227060c47b22e8d1b99c41db0b171a3fe030e1853551053fe23e26b")
        original_spec = importlib.util.spec_from_file_location("original_collection_cli", original_path)
        original = importlib.util.module_from_spec(original_spec)
        original_spec.loader.exec_module(original)
        results = []
        # Use two isolated roots with equivalent fixture bytes, then compare relative metadata.
        for entry in (original, cli):
            identifier = "legacy-original" if entry is original else "legacy-current"
            with patch("sys.argv", ["register_collection", "--manifest", str(self.report), "--id", identifier, "--data-root", str(self.root)]), patch("app.store.now", return_value="fixed-clock"), contextlib.redirect_stdout(io.StringIO()):
                entry.main()
            record = self.store.get("datasets", identifier)
            record.pop("id")
            results.append(record)
        self.assertEqual(results[0], results[1])
        self.assertEqual(self.store.list("dataset_versions"), [])

    def test_logical_path_retarget_is_rejected_before_registry_write(self):
        original = module._confined
        original_verify = module._verified_file
        completed = 0

        def verify(*args):
            nonlocal completed
            result = original_verify(*args)
            completed += 1
            return result

        def retarget(root, value):
            resolved = original(root, value)
            if completed == 3 and str(value) == str(self.paths["image"]):
                return self.paths["label"]
            return resolved

        with patch.object(module, "_verified_file", side_effect=verify), patch.object(module, "_confined", side_effect=retarget):
            with self.assertRaisesRegex(ValueError, "path changed"):
                self.register()
        self.assertEqual(self.store.list("dataset_versions"), [])


if __name__ == "__main__":
    unittest.main()
