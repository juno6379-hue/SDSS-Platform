"""Fail-closed local GeoServer primary-layer candidate manager.

Builds local raster candidates and registry rows across the First Group six
provinces. It does not itself verify external GeoServer publication or a
GetCapabilities named-layer listing:
1. sentinel2_composite: Multi-spectral Sentinel-2 Level-2A surface reflectance composite
2. scl_mask: Copernicus Scene Classification Layer (values 0..11)
3. annual_valid_mask: Binary valid observation mask (1=Valid land observation, 0=Missing/Cloud)
4. observation_count: Number of cloud-free observations within annual dry season window (1..N)
5. coverage_comparison: 3-color comparison (1=Baseline Valid, 2=Newly Recovered, 3=Still Missing Gap)
6. worldcover_reference: ESA WorldCover 10m v200 reference land cover (9 discrete classes)
7. esri_reference: blocked compatibility slot; actual Esri annual weak labels
   are registered from the authority report and never derived from WorldCover
"""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.transform import Affine

PROVINCE_SPECS: Dict[str, Dict[str, Any]] = {
    "banten": {
        "name": "Banten",
        "island": "Java",
        "crs": "EPSG:32748",
        "utm_zone": "48S",
        "bounds": [624160.0, 9287010.0, 626720.0, 9289570.0],
        "lat_lon": [-6.447, 106.123, -6.424, 106.146],
        "default_year": 2021,
    },
    "west_java": {
        "name": "West Java",
        "island": "Java",
        "crs": "EPSG:32748",
        "utm_zone": "48S",
        "bounds": [792000.0, 9238820.0, 794560.0, 9241380.0],
        "lat_lon": [-6.883, 107.641, -6.860, 107.664],
        "default_year": 2021,
    },
    "east_java": {
        "name": "East Java",
        "island": "Java",
        "crs": "EPSG:32749",
        "utm_zone": "49S",
        "bounds": [639510.0, 9140510.0, 642070.0, 9143070.0],
        "lat_lon": [-7.771, 112.265, -7.748, 112.288],
        "default_year": 2021,
    },
    "south_sulawesi": {
        "name": "South Sulawesi",
        "island": "Sulawesi",
        "crs": "EPSG:32750",
        "utm_zone": "50S",
        "bounds": [826250.0, 9579220.0, 828810.0, 9581780.0],
        "lat_lon": [-3.801, 119.937, -3.778, 119.960],
        "default_year": 2021,
    },
    "gorontalo": {
        "name": "Gorontalo",
        "island": "Sulawesi",
        "crs": "EPSG:32651",
        "utm_zone": "51N",
        "bounds": [415900.0, 73040.0, 418460.0, 75600.0],
        "lat_lon": [0.660, 122.245, 0.683, 122.268],
        "default_year": 2021,
    },
    "southeast_sulawesi": {
        "name": "Southeast Sulawesi",
        "island": "Sulawesi",
        "crs": "EPSG:32751",
        "utm_zone": "51S",
        "bounds": [366840.0, 9578410.0, 369400.0, 9580970.0],
        "lat_lon": [-3.812, 121.799, -3.789, 121.822],
        "default_year": 2021,
    },
}

PRIMARY_LAYER_KINDS = [
    "sentinel2_composite",
    "scl_mask",
    "annual_valid_mask",
    "newly_recovered_mask",
    "still_missing_mask",
    "observation_count",
    "coverage_comparison",
    "worldcover_reference",
    "esri_reference",
]

G5_LINEAGE_LAYER_KINDS = {
    "newly_recovered_mask",
    "still_missing_mask",
    "observation_count",
    "coverage_comparison",
}

ESRI_AUTHORITY_REPORT = "first-group-training-esri-v1/annual-window-report.json"
ESRI_PRIMARY_BLOCK_REASON = "LEGACY_WORLDCOVER_CROSSWALK_MUST_NOT_BE_PUBLISHED_AS_ESRI"

REGISTRY_FIELDNAMES = [
    "layer_id",
    "stage",
    "kind",
    "province_id",
    "province_name",
    "year",
    "crs",
    "file_rel_path",
    "width",
    "height",
    "nodata_value",
    "resampling",
    "colormap_style",
    "source_product",
    "license",
    "published_status",
    "wms_getmap_url",
]

EVIDENCE_REGISTRY_FIELDNAMES = REGISTRY_FIELDNAMES + [
    "artifact_evidence_status",
    "file_sha256",
    "named_layer_evidence",
]


@dataclass
class GeoServerLayerRecord:
    layer_id: str
    stage: str               # '1st_primary' or '2nd_secondary'
    kind: str
    province_id: str
    province_name: str
    year: int
    crs: str
    file_rel_path: Optional[str]
    width: Optional[int]
    height: Optional[int]
    nodata_value: Optional[int]
    resampling: str
    colormap_style: str
    source_product: str
    license: str
    published_status: str
    wms_getmap_url: Optional[str]
    evidence_status: str = "IMPLEMENTED_UNVERIFIED"
    source_lineage_verified: bool = False
    synthetic_fixture: Optional[bool] = None
    local_artifact_materialized: bool = False
    external_publication_verified: bool = False
    getcapabilities_named_listing_verified: bool = False
    asset_role: str = "primary_layer_candidate"
    authority_report: Optional[str] = None
    authority_report_present: bool = False
    blocked_reason: Optional[str] = None
    legacy_artifact_quarantined: bool = False
    independent_ground_truth: bool = False
    model_prediction: bool = False


class GeoServerPrimaryLayersManager:
    """Create local candidates while keeping publication and G5 lineage fail-closed."""

    def __init__(self, data_root: Path, *, allow_synthetic_fixtures: bool = False):
        self.data_root = Path(data_root).resolve()
        # Synthetic G5 masks are useful only for deterministic code-path tests.  The
        # default is deliberately fail-closed so a production call cannot create a
        # recovery product without a separately verified G5 lineage contract.
        self.allow_synthetic_fixtures = bool(allow_synthetic_fixtures)
        self.layers_dir = self.data_root / "geoserver_layers" / "primary"
        self.layers_dir.mkdir(parents=True, exist_ok=True)

    def materialize_all(self) -> List[GeoServerLayerRecord]:
        """Materialize permitted local artifacts and return candidate registry rows."""
        registry: List[GeoServerLayerRecord] = []

        for prov_id, spec in PROVINCE_SPECS.items():
            prov_dir = self.layers_dir / f"{prov_id}_{spec['default_year']}"
            prov_dir.mkdir(parents=True, exist_ok=True)

            source_2021 = self.data_root / "first-group-2021" / f"{prov_id}-2021"
            recovery32 = self.data_root / "first-group-recovery32" / f"{prov_id}-2021"

            # 1. Base image (Sentinel-2 composite)
            img_src = None
            if recovery32.exists() and (recovery32 / "image.tif").is_file():
                img_src = recovery32 / "image.tif"
            elif source_2021.exists() and (source_2021 / "image.tif").is_file():
                img_src = source_2021 / "image.tif"

            # 2. Reference WorldCover
            wc_src = None
            if recovery32.exists() and (recovery32 / "label-worldcover.tif").is_file():
                wc_src = recovery32 / "label-worldcover.tif"
            elif source_2021.exists() and (source_2021 / "label-worldcover.tif").is_file():
                wc_src = source_2021 / "label-worldcover.tif"

            # 3. Quality mask
            qm_src = None
            if recovery32.exists() and (recovery32 / "quality-mask.tif").is_file():
                qm_src = recovery32 / "quality-mask.tif"
            elif source_2021.exists() and (source_2021 / "quality-mask.tif").is_file():
                qm_src = source_2021 / "quality-mask.tif"

            # Read affine transform and CRS from primary source
            ref_path = img_src or wc_src
            if ref_path and ref_path.is_file():
                with rasterio.open(ref_path) as ds:
                    transform = ds.transform
                    crs = ds.crs
                    width = ds.width
                    height = ds.height
            else:
                left, bottom, right, top = spec["bounds"]
                transform = rasterio.transform.from_bounds(left, bottom, right, top, 256, 256)
                crs = CRS.from_string(spec["crs"])
                width, height = 256, 256

            # Materialize individual rasters
            if img_src is not None or self.allow_synthetic_fixtures:
                self._ensure_sentinel2_composite(prov_dir, img_src, transform, crs, width, height)
            if qm_src is not None or self.allow_synthetic_fixtures:
                self._ensure_scl_mask(prov_dir, qm_src, transform, crs, width, height)
                self._ensure_annual_valid_mask(prov_dir, qm_src, transform, crs, width, height)
            if self.allow_synthetic_fixtures:
                self._ensure_coverage_comparison(prov_dir, transform, crs, width, height)
                self._ensure_newly_recovered_mask(prov_dir, transform, crs, width, height)
                self._ensure_still_missing_mask(prov_dir, transform, crs, width, height)
                self._ensure_observation_count(prov_dir, transform, crs, width, height)
            if wc_src is not None or self.allow_synthetic_fixtures:
                self._ensure_worldcover_reference(prov_dir, wc_src, transform, crs, width, height)
            # Deliberately do not create an ``esri_reference.tif`` here.  The
            # historical implementation remapped WorldCover class codes and then
            # mislabeled the result as Esri.  Actual Esri annual rasters are weak
            # training labels registered through ESRI_AUTHORITY_REPORT; they are
            # not interchangeable with this fixed 2021 primary-layer slot.

            # Build layer registry records
            for kind in PRIMARY_LAYER_KINDS:
                filename = f"{kind}.tif"
                rel_path = f"geoserver_layers/primary/{prov_id}_{spec['default_year']}/{filename}"
                layer_id = f"lcluc:primary_{kind}_{prov_id}_{spec['default_year']}"

                style_map = {
                    "sentinel2_composite": "raster_rgb_truecolor",
                    "scl_mask": "scl_discrete_12classes",
                    "annual_valid_mask": "valid_mask_binary",
                    "newly_recovered_mask": "valid_mask_binary",
                    "still_missing_mask": "valid_mask_binary",
                    "observation_count": "obs_count_ramp",
                    "coverage_comparison": "recovery_comparison_3colors",
                    "worldcover_reference": "lcluc_discrete_9classes",
                    "esri_reference": "lcluc_discrete_9classes",
                }

                prod_map = {
                    "sentinel2_composite": "Copernicus Sentinel-2 L2A (B04, B03, B02)",
                    "scl_mask": "Copernicus Sentinel-2 SCL (Scene Classification Layer)",
                    "annual_valid_mask": "SCL Multi-temporal Valid Mask Composite",
                    "newly_recovered_mask": "CODEX G5 Multi-temporal Newly Recovered Mask",
                    "still_missing_mask": "CODEX G5 Persistent Cloud Gap Still Missing Mask",
                    "observation_count": "Sentinel-2 L2A Dry Season Observation Count",
                    "coverage_comparison": "CODEX G5 Multi-temporal Recovery 3-Color Raster",
                    "worldcover_reference": "ESA WorldCover 10m v200 Reference",
                    "esri_reference": "Esri annual weak labels (authority-report registered; not a primary layer)",
                }

                getmap_url: Optional[str] = (
                    f"http://127.0.0.1:8088/geoserver/wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap"
                    f"&LAYERS={layer_id}&CRS=EPSG:3857&WIDTH=256&HEIGHT=256&FORMAT=image/png"
                )

                artifact_path = prov_dir / filename
                artifact_exists = artifact_path.is_file()
                tagged_synthetic = self._is_tagged_synthetic_fixture(artifact_path)
                is_g5_lineage_layer = kind in G5_LINEAGE_LAYER_KINDS
                authority_report_present = (self.data_root / ESRI_AUTHORITY_REPORT).is_file()
                asset_role = "primary_layer_candidate"
                authority_report: Optional[str] = None
                blocked_reason: Optional[str] = None
                legacy_artifact_quarantined = False
                record_file_rel_path: Optional[str] = rel_path
                record_width: Optional[int] = width
                record_height: Optional[int] = height
                record_nodata: Optional[int] = 255
                recognized_artifact = artifact_exists

                if kind == "esri_reference":
                    # Keep the row only as a compatibility/blocking marker.  Even
                    # when a legacy file exists, it is not an accepted Esri asset
                    # and must not receive a file path or WMS candidate URL.
                    evidence_status = "BLOCKED"
                    synthetic_fixture = None
                    published_status = "BLOCKED"
                    source_product = prod_map[kind]
                    asset_role = "weak_training_label_pointer_only"
                    authority_report = ESRI_AUTHORITY_REPORT
                    blocked_reason = ESRI_PRIMARY_BLOCK_REASON
                    legacy_artifact_quarantined = artifact_exists
                    recognized_artifact = False
                    record_file_rel_path = None
                    record_width = None
                    record_height = None
                    record_nodata = None
                    getmap_url = None
                elif is_g5_lineage_layer:
                    evidence_status = "TESTED_SYNTHETIC" if tagged_synthetic else "BLOCKED"
                    synthetic_fixture = True if tagged_synthetic else None
                    published_status = "BLOCKED"
                    if tagged_synthetic:
                        source_product = "TEST FIXTURE - NO VERIFIED G5 LINEAGE"
                    elif artifact_exists:
                        source_product = "UNVERIFIED LOCAL ARTIFACT - G5 LINEAGE NOT VERIFIED"
                    else:
                        source_product = "MISSING - VERIFIED G5 LINEAGE REQUIRED"
                else:
                    source_available = {
                        "sentinel2_composite": img_src is not None,
                        "scl_mask": qm_src is not None,
                        "annual_valid_mask": qm_src is not None,
                        "worldcover_reference": wc_src is not None,
                    }.get(kind, False)
                    if tagged_synthetic:
                        evidence_status = "TESTED_SYNTHETIC"
                        synthetic_fixture = True
                        published_status = "BLOCKED"
                        source_product = "TEST FIXTURE - NOT A SOURCE-BACKED PRODUCT"
                    elif source_available:
                        evidence_status = "IMPLEMENTED_UNVERIFIED"
                        synthetic_fixture = False
                        published_status = "IMPLEMENTED_UNVERIFIED"
                        source_product = prod_map.get(kind, "Derived")
                    else:
                        evidence_status = "BLOCKED"
                        synthetic_fixture = None
                        published_status = "BLOCKED"
                        source_product = (
                            "UNVERIFIED LOCAL ARTIFACT - SOURCE INPUT NOT AVAILABLE"
                            if artifact_exists
                            else "MISSING - SOURCE INPUT REQUIRED"
                        )

                registry.append(
                    GeoServerLayerRecord(
                        layer_id=layer_id,
                        stage="1st_primary",
                        kind=kind,
                        province_id=prov_id,
                        province_name=spec["name"],
                        year=spec["default_year"],
                        crs=spec["crs"],
                        file_rel_path=record_file_rel_path,
                        width=record_width,
                        height=record_height,
                        nodata_value=record_nodata,
                        resampling="nearest",
                        colormap_style=style_map.get(kind, "default"),
                        source_product=source_product,
                        license="NOT_ASSERTED" if kind == "esri_reference" else "CC-BY-4.0",
                        published_status=published_status,
                        wms_getmap_url=getmap_url,
                        evidence_status=evidence_status,
                        source_lineage_verified=False,
                        synthetic_fixture=synthetic_fixture,
                        local_artifact_materialized=recognized_artifact,
                        external_publication_verified=False,
                        getcapabilities_named_listing_verified=False,
                        asset_role=asset_role,
                        authority_report=authority_report,
                        authority_report_present=authority_report_present if kind == "esri_reference" else False,
                        blocked_reason=blocked_reason,
                        legacy_artifact_quarantined=legacy_artifact_quarantined,
                    )
                )

        return registry

    @staticmethod
    def _is_tagged_synthetic_fixture(path: Path) -> bool:
        """Return true only when the raster itself carries explicit fixture tags."""
        if not path.is_file():
            return False
        try:
            with rasterio.open(path) as dataset:
                tags = dataset.tags()
        except (OSError, rasterio.errors.RasterioError):
            return False
        return (
            tags.get("synthetic_fixture", "").strip().lower() == "true"
            or tags.get("evidence_status", "").strip().upper() == "TESTED_SYNTHETIC"
        )

    @staticmethod
    def _tag_local_candidate(dataset: Any, *, synthetic: bool) -> None:
        dataset.update_tags(
            evidence_status="TESTED_SYNTHETIC" if synthetic else "IMPLEMENTED_UNVERIFIED",
            synthetic_fixture="true" if synthetic else "false",
            source_lineage_verified="false",
        )

    def _ensure_sentinel2_composite(
        self, prov_dir: Path, src: Optional[Path], transform: Affine, crs: CRS, width: int, height: int
    ) -> None:
        dest = prov_dir / "sentinel2_composite.tif"
        if dest.is_file():
            return
        if src and src.is_file():
            with rasterio.open(src) as s, rasterio.open(
                dest, "w", driver="GTiff", width=width, height=height, count=s.count,
                dtype=s.dtypes[0], crs=crs, transform=transform, nodata=s.nodata or 0,
                compress="deflate"
            ) as d:
                for b in range(1, s.count + 1):
                    d.write(s.read(b), b)
                self._tag_local_candidate(d, synthetic=False)
        else:
            arr = np.full((3, height, width), 128, dtype=np.uint8)
            with rasterio.open(
                dest, "w", driver="GTiff", width=width, height=height, count=3,
                dtype="uint8", crs=crs, transform=transform, nodata=0, compress="deflate"
            ) as d:
                d.write(arr)
                self._tag_local_candidate(d, synthetic=True)

    def _ensure_scl_mask(
        self, prov_dir: Path, src: Optional[Path], transform: Affine, crs: CRS, width: int, height: int
    ) -> None:
        dest = prov_dir / "scl_mask.tif"
        if dest.is_file():
            return
        if src and src.is_file():
            with rasterio.open(src) as s:
                raw_data = s.read(1)
            # Map quality mask binary (0, 1) to representative SCL (4=Vegetation, 9=Cloud)
            scl_data = np.where(raw_data == 1, 4, 9).astype(np.uint8)
        else:
            scl_data = np.full((height, width), 4, dtype=np.uint8)
            scl_data[:4, :4] = 9

        with rasterio.open(
            dest, "w", driver="GTiff", width=width, height=height, count=1,
            dtype="uint8", crs=crs, transform=transform, nodata=255, compress="deflate"
        ) as d:
            d.write(scl_data, 1)
            self._tag_local_candidate(d, synthetic=not (src and src.is_file()))

    def _ensure_annual_valid_mask(
        self, prov_dir: Path, src: Optional[Path], transform: Affine, crs: CRS, width: int, height: int
    ) -> None:
        dest = prov_dir / "annual_valid_mask.tif"
        if dest.is_file():
            return
        if src and src.is_file():
            with rasterio.open(src) as s:
                val_data = s.read(1).astype(np.uint8)
        else:
            val_data = np.ones((height, width), dtype=np.uint8)
            val_data[:2, :2] = 0

        with rasterio.open(
            dest, "w", driver="GTiff", width=width, height=height, count=1,
            dtype="uint8", crs=crs, transform=transform, nodata=255, compress="deflate"
        ) as d:
            d.write(val_data, 1)
            self._tag_local_candidate(d, synthetic=not (src and src.is_file()))

    def _ensure_observation_count(
        self, prov_dir: Path, transform: Affine, crs: CRS, width: int, height: int
    ) -> None:
        dest = prov_dir / "observation_count.tif"
        if dest.is_file():
            return
        # Deterministic fixture only.  This is never a measured observation count
        # and materialization is reachable only with allow_synthetic_fixtures=True.
        obs_data = np.full((height, width), 3, dtype=np.uint8)
        with rasterio.open(
            dest, "w", driver="GTiff", width=width, height=height, count=1,
            dtype="uint8", crs=crs, transform=transform, nodata=0, compress="deflate"
        ) as d:
            d.write(obs_data, 1)
            d.update_tags(
                evidence_status="TESTED_SYNTHETIC",
                synthetic_fixture="true",
                source_lineage_verified="false",
            )

    def _ensure_coverage_comparison(
        self, prov_dir: Path, transform: Affine, crs: CRS, width: int, height: int
    ) -> None:
        dest = prov_dir / "coverage_comparison.tif"
        if dest.is_file():
            return
        # 1 = Baseline Valid (approx 49.5%), 2 = Newly Recovered (approx 49.5%), 3 = Still Missing (approx 1.0%)
        comp_data = np.zeros((height, width), dtype=np.uint8)
        half_y = height // 2
        comp_data[:half_y, :] = 1         # Baseline Valid
        comp_data[half_y:, :] = 2         # Newly Recovered
        comp_data[:2, :2] = 3             # Still Missing
        comp_data[-2:, -2:] = 3

        with rasterio.open(
            dest, "w", driver="GTiff", width=width, height=height, count=1,
            dtype="uint8", crs=crs, transform=transform, nodata=255, compress="deflate"
        ) as d:
            d.write(comp_data, 1)
            d.update_tags(
                evidence_status="TESTED_SYNTHETIC",
                synthetic_fixture="true",
                source_lineage_verified="false",
            )

    def _ensure_newly_recovered_mask(
        self, prov_dir: Path, transform: Affine, crs: CRS, width: int, height: int
    ) -> None:
        dest = prov_dir / "newly_recovered_mask.tif"
        if dest.is_file():
            return
        comp_file = prov_dir / "coverage_comparison.tif"
        if comp_file.is_file():
            with rasterio.open(comp_file) as s:
                comp = s.read(1)
                recov_data = np.where(comp == 2, 1, 0).astype(np.uint8)
        else:
            raise RuntimeError("coverage comparison fixture is required before deriving recovered mask")

        with rasterio.open(
            dest, "w", driver="GTiff", width=width, height=height, count=1,
            dtype="uint8", crs=crs, transform=transform, nodata=255, compress="deflate"
        ) as d:
            d.write(recov_data, 1)
            d.update_tags(
                evidence_status="TESTED_SYNTHETIC",
                synthetic_fixture="true",
                source_lineage_verified="false",
            )

    def _ensure_still_missing_mask(
        self, prov_dir: Path, transform: Affine, crs: CRS, width: int, height: int
    ) -> None:
        dest = prov_dir / "still_missing_mask.tif"
        if dest.is_file():
            return
        comp_file = prov_dir / "coverage_comparison.tif"
        if comp_file.is_file():
            with rasterio.open(comp_file) as s:
                comp = s.read(1)
                missing_data = np.where(comp == 3, 1, 0).astype(np.uint8)
        else:
            raise RuntimeError("coverage comparison fixture is required before deriving missing mask")

        with rasterio.open(
            dest, "w", driver="GTiff", width=width, height=height, count=1,
            dtype="uint8", crs=crs, transform=transform, nodata=255, compress="deflate"
        ) as d:
            d.write(missing_data, 1)
            d.update_tags(
                evidence_status="TESTED_SYNTHETIC",
                synthetic_fixture="true",
                source_lineage_verified="false",
            )

    def _ensure_worldcover_reference(
        self, prov_dir: Path, src: Optional[Path], transform: Affine, crs: CRS, width: int, height: int
    ) -> None:
        dest = prov_dir / "worldcover_reference.tif"
        if dest.is_file():
            return
        if src and src.is_file():
            with rasterio.open(src) as s:
                wc_data = s.read(1)
        else:
            wc_data = np.full((height, width), 10, dtype=np.uint8)  # Tree cover default

        with rasterio.open(
            dest, "w", driver="GTiff", width=width, height=height, count=1,
            dtype="uint8", crs=crs, transform=transform, nodata=255, compress="deflate"
        ) as d:
            d.write(wc_data, 1)
            self._tag_local_candidate(d, synthetic=not (src and src.is_file()))

    def _ensure_esri_reference(
        self, prov_dir: Path, src: Optional[Path], transform: Affine, crs: CRS, width: int, height: int
    ) -> None:
        """Reject the retired WorldCover-to-Esri masquerading path.

        This method remains as an explicit guard for callers that may still use
        the old private API.  An actual Esri weak label must retain its own source
        URL, dataset version, local SHA and quality mask in the authority report.
        """
        del prov_dir, src, transform, crs, width, height
        raise RuntimeError(ESRI_PRIMARY_BLOCK_REASON)

    def export_deliverables(self, output_dir: Path) -> Tuple[Path, Path, Path]:
        """Export fail-closed G6 evidence and merge the combined layer registry.

        Existing non-primary rows (including all 2nd-stage rows) are preserved.
        Primary rows are replaced deterministically. Publication and named-layer
        GetCapabilities verification remain false because this manager performs no
        external service request.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        registry = self.materialize_all()

        manifest_file = output_dir / "04_geoserver_primary_layers_manifest.json"
        report_file = output_dir / "04_geoserver_primary_layer_verification.md"
        csv_file = output_dir / "08_geoserver_1st_2nd_layer_registry.csv"

        preserved_registry_rows: List[Dict[str, str]] = []
        output_registry_fieldnames = EVIDENCE_REGISTRY_FIELDNAMES
        if csv_file.is_file():
            with open(csv_file, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                if reader.fieldnames not in (REGISTRY_FIELDNAMES, EVIDENCE_REGISTRY_FIELDNAMES):
                    raise ValueError("existing GeoServer registry schema does not match the required schema")
                output_registry_fieldnames = list(reader.fieldnames)
                seen_layer_ids = set()
                for row in reader:
                    layer_id = row.get("layer_id", "")
                    if not layer_id or layer_id in seen_layer_ids:
                        raise ValueError("existing GeoServer registry contains a missing or duplicate layer_id")
                    seen_layer_ids.add(layer_id)
                    if row.get("stage") != "1st_primary":
                        preserved_registry_rows.append(dict(row))

        primary_layer_ids = {record.layer_id for record in registry}
        preserved_layer_ids = {row["layer_id"] for row in preserved_registry_rows}
        cross_set_collisions = sorted(primary_layer_ids & preserved_layer_ids)
        if cross_set_collisions:
            raise ValueError(
                "preserved non-primary layer_id collides with primary replacement: "
                + ", ".join(cross_set_collisions)
            )

        # 1. Manifest JSON
        manifest_payload = {
            "schema_version": "3.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "evidence_status": "TESTED_SYNTHETIC" if self.allow_synthetic_fixtures else "BLOCKED",
            "g5_source_lineage_verified": False,
            "synthetic_fixture_mode": self.allow_synthetic_fixtures,
            "external_publication_verified": False,
            "getcapabilities_named_listing_verified": False,
            "publication_status": "BLOCKED_NO_EXTERNAL_PUBLICATION_VERIFICATION",
            "total_layers": len(registry),
            "combined_registry_total_layers": len(registry) + len(preserved_registry_rows),
            "preserved_non_primary_layers": len(preserved_registry_rows),
            "provinces": list(PROVINCE_SPECS.keys()),
            "layer_kinds": PRIMARY_LAYER_KINDS,
            "limitations": [
                "No verified G5 raster lineage contract was supplied.",
                "Synthetic recovery fixtures are test-only and are not scientific products.",
                "WorldCover crosswalks are quarantined and cannot be registered or served as Esri layers.",
                f"Actual Esri annual weak labels are registered only from {ESRI_AUTHORITY_REPORT}.",
                "No external GeoServer publication or named-layer GetCapabilities response was verified.",
            ],
            "layers": [asdict(r) for r in registry],
        }
        manifest_file.write_text(json.dumps(manifest_payload, ensure_ascii=False, indent=2), encoding="utf-8")

        # 2. Deterministic primary replacement plus preserved non-primary rows.
        # Repeated exports therefore do not duplicate secondary records.
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=output_registry_fieldnames)
            writer.writeheader()
            for r in registry:
                row = asdict(r)
                if output_registry_fieldnames == EVIDENCE_REGISTRY_FIELDNAMES:
                    row.update(
                        artifact_evidence_status=r.evidence_status,
                        file_sha256=self._accepted_artifact_sha256(r),
                        named_layer_evidence=None,
                    )
                writer.writerow({key: row.get(key) for key in output_registry_fieldnames})
            writer.writerows(preserved_registry_rows)

        # 3. Verification Report Markdown
        report_content = f"""# G6 — GeoServer 1차 공간 레이어 로컬 구현·검증 상태 보고서

> **표준 규격**: `GreenBlue_CODEX_LCLUC_PostGIS_Coverage_MLOps_Deployment_Master_v3.0.md` Section 6  
> **생성 시점**: `{datetime.now(timezone.utc).isoformat()}`  
> **근거 상태**: `{'TESTED_SYNTHETIC' if self.allow_synthetic_fixtures else 'BLOCKED'}`
> **배포 상태**: `BLOCKED_NO_EXTERNAL_PUBLICATION_VERIFICATION`
> **로컬 1차 레지스트리 행**: **{len(registry)}개** (6개 주 × 9종)
> **보존한 비-1차 행**: **{len(preserved_registry_rows)}개**
> **제한**: 검증된 G5 래스터 계보, 외부 GeoServer 게시, GetCapabilities 명명 레이어 열거를 확인하지 않음.

---

## 1. 1차 공간 레이어 9종 규격 및 리샘플링 정책

| 레이어 유형 | 설명 | 리샘플링 정책 | NoData 정책 | 스타일 규격 |
|---|---|---|---|---|
| **sentinel2_composite** | Sentinel-2 L2A BOA 반사도 합성 (B04/B03/B02) | Bilinear (연속 반사도) | 0 (투명) | `raster_rgb_truecolor` |
| **scl_mask** | Scene Classification Layer (0..11) | **Nearest-Neighbor** | 255 (투명) | `scl_discrete_12classes` |
| **annual_valid_mask** | 연간 유효 관측 이진 마스크 (1=유효, 0=결측) | **Nearest-Neighbor** | 255 (투명) | `valid_mask_binary` |
| **newly_recovered_mask** | 다중시기 복원 신규 확보 이진 마스크 (1=신규확보, 0=기타) | **Nearest-Neighbor** | 255 (투명) | `valid_mask_binary` |
| **still_missing_mask** | 잔여 결측 클라우드 갭 이진 마스크 (1=잔여결측, 0=관측완료) | **Nearest-Neighbor** | 255 (투명) | `valid_mask_binary` |
| **observation_count** | 건기 창(6~9월) 유효 관측 누적 횟수 | **Nearest-Neighbor** | 0 (투명) | `obs_count_ramp` |
| **coverage_comparison** | CODEX 3색 비교지도 (1:기존유효, 2:신규확보, 3:잔여결측) | **Nearest-Neighbor** | 255 (투명) | `recovery_comparison_3colors` |
| **worldcover_reference** | ESA WorldCover 10m v200 공인 참조 레이어 | **Nearest-Neighbor** | 255 / 0 (투명) | `lcluc_discrete_9classes` |
| **esri_reference** | 호환용 차단 슬롯. WorldCover 교차표는 Esri로 인정하지 않고, 실제 Esri 연차 weak label은 권위 report 경로로만 등록 | N/A | N/A | `BLOCKED` |

---

## 2. 6개 주별 등록 현황 (First Group 6 Provinces)

"""
        for prov_id, spec in PROVINCE_SPECS.items():
            report_content += f"### {spec['name']} (`{prov_id}`) — {spec['crs']} (UTM Zone {spec['utm_zone']})\n\n"
            report_content += f"- **BBOX (Native)**: `{spec['bounds']}`\n"
            report_content += f"- **BBOX (WGS84)**: `{spec['lat_lon']}`\n"
            report_content += "- **로컬 레지스트리 레이어 (9종)**:\n"
            for r in [x for x in registry if x.province_id == prov_id]:
                report_content += (
                    f"  - `{r.layer_id}` ({r.kind}): `{r.colormap_style}` | "
                    f"근거 `{r.evidence_status}` | 게시 `{r.published_status}` | "
                    f"후보 URI `{r.wms_getmap_url}`"
                    + (f" | 차단 `{r.blocked_reason}`" if r.blocked_reason else "")
                    + "\n"
                )
            report_content += "\n"

        report_content += """---

## 3. 현재 검증 범위

1. **외부 WMS GetCapabilities 명명 레이어 검증**: `NOT_CHECKED`.
2. **외부 GeoServer 게시 검증**: `NOT_CHECKED`.
3. **G5 계보 검증**: `BLOCKED`; 시험 픽스처는 실측 복구 성과로 해석하지 않음.
4. **Esri 참조 역할**: WorldCover 파생물은 일괄 차단하고, 실제 Esri 연차 자료는 `{ESRI_AUTHORITY_REPORT}`의 weak-label provenance로만 조회함.
5. **로컬 코드 경로**: 임시 디렉터리에서 래스터 쓰기·직접 픽셀 읽기·Nearest-Neighbor 렌더링을 시험할 수 있음. 이 시험은 외부 게시 근거가 아님.
"""
        report_file.write_text(report_content, encoding="utf-8")

        return manifest_file, report_file, csv_file

    def _accepted_artifact_sha256(self, record: GeoServerLayerRecord) -> Optional[str]:
        """Hash only accepted registry artifacts; quarantined rows stay blank."""
        if not record.local_artifact_materialized or not record.file_rel_path:
            return None
        path = (self.data_root / record.file_rel_path).resolve()
        if not path.is_relative_to(self.data_root) or not path.is_file():
            return None
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
