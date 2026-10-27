from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
import rasterio
from rasterio.transform import from_origin
from rasterio.warp import transform_geom

from backend.app.ml.province_year_evidence_builder import (
    BIG_LAYER_NAME,
    GISTARU_SERVICE_CANDIDATES,
    PROVINCES,
    YEARS,
    ProvinceEvidenceError,
    build_local_scl_mosaics,
    discover_local_scl_assets,
    fetch_big_boundary_candidate,
    probe_gistaru_services,
    validate_local_scl_mosaic_manifest,
)


class ProvinceYearEvidenceBuilderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _fake_big_fetcher(self, url: str, **_: object) -> bytes:
        if "MapServer/12?" in url:
            return json.dumps(
                {
                    "name": BIG_LAYER_NAME,
                    "type": "Feature Layer",
                    "geometryType": "esriGeometryPolygon",
                    "serviceItemId": "fixture-item",
                }
            ).encode()
        local_name = next(name for name in (
            "Banten", "Jawa Barat", "Jawa Timur", "Sulawesi Selatan", "Gorontalo", "Sulawesi Tenggara"
        ) if name.replace(" ", "+") in url or name.replace(" ", "%20") in url or name in url)
        province_index = list((
            "Banten", "Jawa Barat", "Jawa Timur", "Sulawesi Selatan", "Gorontalo", "Sulawesi Tenggara"
        )).index(local_name)
        left = 100.0 + province_index * 0.1
        polygon = {
            "type": "Polygon",
            "coordinates": [[[left, 0.0], [left + 0.05, 0.0], [left + 0.05, 0.05], [left, 0.05], [left, 0.0]]],
        }
        return json.dumps(
            {
                "type": "FeatureCollection",
                "features": [{
                    "type": "Feature",
                    "properties": {"objectid": province_index + 1, "wadmpr": local_name},
                    "geometry": polygon,
                }],
            }
        ).encode()

    def test_big_candidate_stays_unapproved(self):
        target = fetch_big_boundary_candidate(self.root / "boundary", fetcher=self._fake_big_fetcher)
        document = json.loads(target.read_text(encoding="utf-8"))
        self.assertEqual(len(document["features"]), 6)
        self.assertEqual(document["evidence_status"], "IMPLEMENTED_UNVERIFIED")
        self.assertFalse(document["authority"]["approved_for_project_statistics"])
        self.assertEqual(
            {row["properties"]["province_id"] for row in document["features"]}, set(PROVINCES)
        )

    def test_gistaru_probe_records_exact_urls_but_does_not_guess_layers(self):
        def unavailable(_: str, **__: object) -> bytes:
            raise OSError("fixture unavailable")

        target = probe_gistaru_services(self.root / "gistaru", fetcher=unavailable)
        document = json.loads(target.read_text(encoding="utf-8"))
        self.assertEqual(document["status"], "BLOCKED_GISTARU_LIVE_METADATA_UNAVAILABLE")
        self.assertEqual([row["service_url"] for row in document["services"]], [
            row["service_url"] for row in GISTARU_SERVICE_CANDIDATES
        ])
        self.assertTrue(all(row["layer_id"] is None for row in document["services"]))

    def _write_fixture_boundary(self) -> Path:
        features = []
        for index, province in enumerate(PROVINCES):
            x0 = index * 4000.0
            geometry = {
                "type": "Polygon",
                "coordinates": [[[x0, 0.0], [x0 + 2000.0, 0.0], [x0 + 2000.0, 2000.0], [x0, 2000.0], [x0, 0.0]]],
            }
            features.append({
                "type": "Feature",
                "properties": {"province_id": province},
                "geometry": transform_geom("EPSG:6933", "EPSG:4326", geometry),
            })
        target = self.root / "boundaries.geojson"
        target.write_text(json.dumps({"type": "FeatureCollection", "features": features}), encoding="utf-8")
        return target

    def _write_fixture_scl(self) -> Path:
        source_root = self.root / "sources"
        for province_index, province in enumerate(PROVINCES):
            for year in YEARS:
                cell = source_root / f"fixture-{province}-{year}" / f"cell-{province}-{year}"
                cell.mkdir(parents=True)
                transform = from_origin(province_index * 4000.0, 2000.0, 1000.0, 1000.0)
                with rasterio.open(
                    cell / "raw-SCL.tif", "w", driver="GTiff", height=2, width=2, count=1,
                    dtype="uint8", crs="EPSG:6933", transform=transform, nodata=0,
                ) as dataset:
                    dataset.write(np.array([[4, 8], [3, 0]], dtype="uint8"), 1)
                (cell / "stac-item.json").write_text(
                    json.dumps({"id": f"fixture-{province}-{year}"}), encoding="utf-8"
                )
        return source_root

    def test_local_scl_builder_writes_exact_36_same_grid_cells(self):
        boundary = self._write_fixture_boundary()
        source_root = self._write_fixture_scl()
        discovered = discover_local_scl_assets(source_root)
        self.assertEqual(len(discovered), 36)
        manifest_path = build_local_scl_mosaics(
            boundary, source_root, self.root / "output", resolution_m=1000.0
        )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(len(manifest["cells"]), 36)
        self.assertFalse(manifest["execution"]["collector_invoked"])
        first = manifest["cells"][0]
        with rasterio.open(manifest_path.parent / first["observed_path"]) as observed, rasterio.open(
            manifest_path.parent / first["cause_path"]
        ) as cause:
            self.assertEqual(observed.crs.to_string(), "EPSG:6933")
            self.assertEqual(observed.transform, cause.transform)
            self.assertEqual(observed.shape, cause.shape)
            self.assertEqual(set(np.unique(observed.read(1))), {0, 1})
            self.assertTrue(set(np.unique(cause.read(1))).issubset(set(range(5))))
        validation = validate_local_scl_mosaic_manifest(manifest_path)
        self.assertEqual(validation["cell_count"], 36)
        self.assertEqual(validation["source_asset_count"], 36)
        self.assertTrue(validation["checks"]["all_gap_pixels_classified"])

    def test_missing_cell_is_rejected(self):
        source_root = self._write_fixture_scl()
        next(source_root.rglob("raw-SCL.tif")).unlink()
        with self.assertRaisesRegex(ProvinceEvidenceError, "SCL_EXACT_36_CELL_SCOPE_REQUIRED"):
            discover_local_scl_assets(source_root)


if __name__ == "__main__":
    unittest.main()
