"""Authoritative AI dataset split audit and fail-closed training gate.

The annual window report is the source of truth.  A row is counted as an
eligible training patch only when its ledger status, geographic split, files,
raster contract, and recorded SHA-256 digests all agree.  Readiness also
requires the report's coverage gate, the class contribution policy, and
independent scene-id plus raster-footprint leakage checks to pass.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import csv
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Set, Tuple

import numpy as np
import rasterio
from rasterio.features import geometry_mask
from rasterio.warp import transform_geom

try:
    from shapely.geometry import shape as shape_geometry
except ImportError:  # pragma: no cover - exercised through the fail-closed runtime branch
    shape_geometry = None

PROVINCE_SPLIT_MAP: Dict[str, str] = {
    "east_java": "train",
    "south_sulawesi": "train",
    "gorontalo": "train",
    "southeast_sulawesi": "train",
    "banten": "val",
    "west_java": "test",
}

ALLOWED_QUALITY_STATUSES = {"quality_eligible", "quality_insufficient"}
MIN_SPLIT_COUNTS = {"train": 100, "val": 10, "test": 10}
MIN_REQUIRED_CLASS_FRACTION = 0.005
MIN_REQUIRED_CLASS_CONTRIBUTING_PATCHES = 5
MIN_PIXELS_PER_CONTRIBUTING_PATCH = 256
MAX_DOMINANT_CLASS_FRACTION = 0.90
MIN_VALID_PIXEL_RATIO = 0.80
MIN_PROVINCE_INSIDE_FRACTION = 0.95
EXPECTED_IMAGE_BANDS = 6
EXPECTED_PATCH_SIZE = (256, 256)
FOOTPRINT_INTERSECTION_RATIO_TOLERANCE = 1e-9
# `readiness.default_policy().required_classes == [0, 1, 2, 4, 6, 7]`.
# Under `raster.ESRI_IO_MAPPING`, those fixed model classes are these source
# codes.  The annual report stores source-code keys, not model-class keys.
REQUIRED_SOURCE_CLASS_CODES = frozenset({"1", "2", "5", "7", "8", "11"})
ALL_SOURCE_CLASS_CODES = frozenset({"1", "2", "4", "5", "7", "8", "9", "11"})
REQUIRED_SPLITS = frozenset({"train", "val", "test"})


@dataclass
class PatchRecord:
    patch_id: str
    parent_group: str
    province_id: str
    split: str
    rel_path: str
    band_count: int
    has_image: bool
    has_label: bool
    has_quality: bool
    is_eligible: bool
    scene_id: str
    quality_status: str
    policy_split: str
    split_policy_valid: bool
    raster_contract_valid: bool
    hashes_match: Optional[bool]
    validation_errors: List[str] = field(default_factory=list)


@dataclass
class SplitStats:
    split_name: str
    provinces: List[str]
    total_patches: int
    eligible_patches: int
    total_pixels: int
    spatial_leakage_detected: Optional[bool]
    leaked_scene_ids: List[str] = field(default_factory=list)


@dataclass
class RasterContentEvidence:
    label_histogram: Optional[Dict[str, int]]
    valid_ratio: Optional[float]
    province_inside_ratio: Optional[float]
    footprint_geometry: Any
    normalized_payload_sha256: Optional[str]
    errors: Tuple[str, ...]
    read_error: Optional[str]


# Raster evidence is a pure function of the three file payloads and the
# reference province geometry.  Synthetic regression tests intentionally copy
# the same pinned payloads to isolated directories; this digest-keyed cache
# avoids decoding the same 256x256x6 content dozens of times without trusting
# paths or bypassing SHA verification.
_RASTER_CONTENT_EVIDENCE_CACHE: Dict[
    Tuple[str, str, str, str], RasterContentEvidence
] = {}


@dataclass
class DatasetSplitsSummary:
    schema_version: str
    generated_at: str
    ready_for_training: bool
    gate_decision: str
    total_scanned: int
    total_eligible: int
    train_count: int
    val_count: int
    test_count: int
    baseline_eligible_count: Optional[int]
    expansion_pct: Optional[float]
    splits: Dict[str, SplitStats]
    patches: List[PatchRecord]
    authority_report: str
    province_reference_boundary: str
    province_reference_boundary_verified: bool
    authority_report_execution_confirmed: Optional[bool]
    training_executed: bool
    quality_eligible_count: int
    ledger_learning_ready: bool
    coverage_learning_ready: bool
    class_coverage_ready: bool
    class_coverage_failures: List[str]
    scene_split_conflicts: List[str]
    footprint_split_conflicts: List[str]
    blockers: List[str]
    integrity_errors: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "ready_for_training": self.ready_for_training,
            "gate_decision": self.gate_decision,
            "total_scanned": self.total_scanned,
            "total_eligible": self.total_eligible,
            "train_count": self.train_count,
            "val_count": self.val_count,
            "test_count": self.test_count,
            "baseline_eligible_count": self.baseline_eligible_count,
            "expansion_pct": (
                round(self.expansion_pct, 1)
                if self.expansion_pct is not None
                else None
            ),
            "authority_report": self.authority_report,
            "province_reference_boundary": self.province_reference_boundary,
            "province_reference_boundary_verified": (
                self.province_reference_boundary_verified
            ),
            "authority_report_execution_confirmed": (
                self.authority_report_execution_confirmed
            ),
            "training_executed": self.training_executed,
            "quality_eligible_count": self.quality_eligible_count,
            "ledger_learning_ready": self.ledger_learning_ready,
            "coverage_learning_ready": self.coverage_learning_ready,
            "class_coverage_ready": self.class_coverage_ready,
            "class_coverage_failures": self.class_coverage_failures,
            "scene_split_conflicts": self.scene_split_conflicts,
            "footprint_split_conflicts": self.footprint_split_conflicts,
            "blockers": self.blockers,
            "integrity_errors": self.integrity_errors,
            "splits": {k: asdict(v) for k, v in self.splits.items()},
            "patches_sample": [asdict(p) for p in self.patches[:50]],
        }


class AIDatasetSplitsManager:
    """Validate the annual ledger and evaluate the G7 readiness contract."""

    def __init__(self, data_root: Path):
        self.data_root = Path(data_root).resolve()
        self.report_path = (
            self.data_root / "first-group-training-esri-v1" / "annual-window-report.json"
        )
        self.boundary_path = (
            self.data_root.parent
            / "frontend"
            / "public"
            / "first-group-provinces.geojson"
        )
        self.boundary_source_path = self.boundary_path.with_name(
            "first-group-provinces.source.json"
        )

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _load_province_boundaries(
        self,
    ) -> Tuple[Optional[Dict[str, Mapping[str, Any]]], Optional[str]]:
        if shape_geometry is None:
            return None, "province_boundaries:geometry_runtime_unavailable"
        if not self.boundary_path.is_file() or not self.boundary_source_path.is_file():
            return None, "province_reference_boundaries:files_missing"
        try:
            boundary_bytes = self.boundary_path.read_bytes()
            boundary_sha256 = hashlib.sha256(boundary_bytes).hexdigest()
            source = json.loads(self.boundary_source_path.read_text(encoding="utf-8"))
            collection = json.loads(boundary_bytes.decode("utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            return None, f"province_reference_boundaries:unreadable:{type(exc).__name__}"
        if not isinstance(source, Mapping):
            return None, "province_reference_boundaries:source_metadata_invalid"
        if source.get("legal_boundary_certification") is not False:
            return None, "province_reference_boundaries:legal_status_unexpected"
        expected_sha256 = source.get("selected_sha256")
        if (
            not isinstance(expected_sha256, str)
            or len(expected_sha256) != 64
            or expected_sha256.lower() != boundary_sha256
        ):
            return None, "province_reference_boundaries:sha256_mismatch"
        if not isinstance(collection, Mapping) or collection.get("type") != "FeatureCollection":
            return None, "province_reference_boundaries:feature_collection_invalid"
        features = collection.get("features")
        if not isinstance(features, list):
            return None, "province_reference_boundaries:features_invalid"
        if (
            type(source.get("selected_feature_count")) is not int
            or source.get("selected_feature_count") != len(features)
        ):
            return None, "province_reference_boundaries:feature_count_mismatch"

        boundaries: Dict[str, Mapping[str, Any]] = {}
        try:
            for feature in features:
                if not isinstance(feature, Mapping) or feature.get("type") != "Feature":
                    return None, "province_reference_boundaries:feature_invalid"
                properties = feature.get("properties")
                geometry = feature.get("geometry")
                if not isinstance(properties, Mapping) or not isinstance(geometry, Mapping):
                    return None, "province_reference_boundaries:feature_invalid"
                province_id = properties.get("province_id")
                if (
                    not isinstance(province_id, str)
                    or province_id in boundaries
                    or province_id not in PROVINCE_SPLIT_MAP
                ):
                    return None, "province_reference_boundaries:province_id_invalid"
                shaped = shape_geometry(geometry)
                if shaped.is_empty or not shaped.is_valid or shaped.area <= 0:
                    return None, (
                        f"province_reference_boundaries:{province_id}:geometry_invalid"
                    )
                boundaries[province_id] = geometry
        except (TypeError, ValueError):
            return None, "province_reference_boundaries:geometry_invalid"
        if set(boundaries) != set(PROVINCE_SPLIT_MAP):
            return None, "province_reference_boundaries:province_set_mismatch"
        return boundaries, None

    def _resolve_ledger_path(self, raw_path: Any) -> Tuple[Optional[Path], Optional[str]]:
        if not isinstance(raw_path, str) or not raw_path.strip():
            return None, "missing_path"
        candidate = Path(raw_path)
        if not candidate.is_absolute():
            candidate = self.data_root / candidate
        try:
            resolved = candidate.resolve(strict=False)
        except (OSError, RuntimeError):
            return None, "unresolvable_path"
        try:
            resolved.relative_to(self.data_root)
        except ValueError:
            return None, "path_outside_data_root"
        return resolved, None

    @staticmethod
    def _inspect_raster(path: Path) -> Tuple[int, int, int, Tuple[str, ...]]:
        with rasterio.open(path) as dataset:
            return (
                int(dataset.count),
                int(dataset.width),
                int(dataset.height),
                tuple(str(dtype) for dtype in dataset.dtypes),
            )

    @staticmethod
    def _empty_splits() -> Dict[str, SplitStats]:
        return {
            split_name: SplitStats(
                split_name=split_name,
                provinces=[],
                total_patches=0,
                eligible_patches=0,
                total_pixels=0,
                spatial_leakage_detected=None,
            )
            for split_name in ("train", "val", "test")
        }

    def _failed_summary(self, errors: List[str]) -> DatasetSplitsSummary:
        return DatasetSplitsSummary(
            schema_version="3.1",
            generated_at=datetime.now(timezone.utc).isoformat(),
            ready_for_training=False,
            gate_decision="BLOCKED_FAIL_CLOSED",
            total_scanned=0,
            total_eligible=0,
            train_count=0,
            val_count=0,
            test_count=0,
            baseline_eligible_count=None,
            expansion_pct=None,
            splits=self._empty_splits(),
            patches=[],
            authority_report=str(self.report_path),
            province_reference_boundary=str(self.boundary_path),
            province_reference_boundary_verified=False,
            authority_report_execution_confirmed=None,
            training_executed=False,
            quality_eligible_count=0,
            ledger_learning_ready=False,
            coverage_learning_ready=False,
            class_coverage_ready=False,
            class_coverage_failures=["coverage_metrics:unavailable"],
            scene_split_conflicts=[],
            footprint_split_conflicts=[],
            blockers=["LEDGER_INTEGRITY_ERROR"],
            integrity_errors=errors,
        )

    @staticmethod
    def _class_coverage_gate(
        coverage: Mapping[str, Any],
        split_counts: Mapping[str, int],
    ) -> Tuple[bool, List[str]]:
        def finite_number(value: Any) -> bool:
            if type(value) not in (int, float):
                return False
            try:
                return math.isfinite(value)
            except (OverflowError, TypeError, ValueError):
                return False

        pixel_counts = coverage.get("required_class_pixel_counts")
        fractions = coverage.get("required_class_pixel_fractions")
        contributors = coverage.get("required_class_contributing_patches")
        dominant = coverage.get("dominant_class_fraction")
        failures: List[str] = []

        if not all(isinstance(value, Mapping) for value in (pixel_counts, fractions, contributors)):
            return False, ["coverage_metrics:missing_required_class_maps"]
        if not isinstance(dominant, Mapping):
            return False, ["coverage_metrics:missing_dominant_class_fraction"]

        metric_maps = {
            "required_class_pixel_counts": pixel_counts,
            "required_class_pixel_fractions": fractions,
            "required_class_contributing_patches": contributors,
            "dominant_class_fraction": dominant,
        }
        for metric_name, metric_map in metric_maps.items():
            if set(metric_map) != REQUIRED_SPLITS:
                failures.append(f"coverage_metrics:{metric_name}:split_key_mismatch")

        for split_name in sorted(REQUIRED_SPLITS):
            split_pixels = pixel_counts.get(split_name)
            split_fractions = fractions.get(split_name)
            split_contributors = contributors.get(split_name)
            split_patch_count = split_counts.get(split_name)
            if not all(
                isinstance(value, Mapping)
                for value in (split_pixels, split_fractions, split_contributors)
            ):
                failures.append(f"{split_name}:missing_required_class_metrics")
                continue
            if type(split_patch_count) is not int or split_patch_count < 0:
                failures.append(f"{split_name}:eligible_patch_count_invalid")
                continue

            for metric_name, split_map in (
                ("required_class_pixel_counts", split_pixels),
                ("required_class_pixel_fractions", split_fractions),
                ("required_class_contributing_patches", split_contributors),
            ):
                if set(split_map) != REQUIRED_SOURCE_CLASS_CODES:
                    failures.append(f"{split_name}:{metric_name}:required_class_key_mismatch")

            valid_fractions: List[float] = []
            valid_pixels: List[int] = []
            inferred_denominators: List[float] = []
            for class_id in sorted(REQUIRED_SOURCE_CLASS_CODES, key=int):
                pixel_value = split_pixels.get(class_id)
                fraction_value = split_fractions.get(class_id)
                contributor_value = split_contributors.get(class_id)
                pixel_valid = type(pixel_value) is int and finite_number(pixel_value)
                fraction_valid = (
                    finite_number(fraction_value) and 0.0 <= fraction_value <= 1.0
                )
                contributor_valid = (
                    type(contributor_value) is int and finite_number(contributor_value)
                )

                if not pixel_valid:
                    failures.append(f"{split_name}:{class_id}:pixel_count_invalid")
                elif pixel_value <= 0:
                    failures.append(f"{split_name}:{class_id}:no_pixels")
                else:
                    valid_pixels.append(pixel_value)

                if not fraction_valid:
                    failures.append(f"{split_name}:{class_id}:fraction_invalid")
                elif fraction_value < MIN_REQUIRED_CLASS_FRACTION:
                    failures.append(f"{split_name}:{class_id}:fraction_below_0.5pct")
                    valid_fractions.append(float(fraction_value))
                else:
                    valid_fractions.append(float(fraction_value))

                if not contributor_valid:
                    failures.append(f"{split_name}:{class_id}:contributors_invalid")
                elif contributor_value < MIN_REQUIRED_CLASS_CONTRIBUTING_PATCHES:
                    failures.append(f"{split_name}:{class_id}:contributors_below_5")

                if pixel_valid and pixel_value > 0 and contributor_valid and contributor_value >= 0:
                    if contributor_value > split_patch_count:
                        failures.append(
                            f"{split_name}:{class_id}:contributors_exceed_split_patches"
                        )
                    else:
                        minimum_pixels = (
                            contributor_value * MIN_PIXELS_PER_CONTRIBUTING_PATCH
                        )
                        maximum_pixels = (
                            contributor_value * EXPECTED_PATCH_SIZE[0] * EXPECTED_PATCH_SIZE[1]
                            + (split_patch_count - contributor_value)
                            * (MIN_PIXELS_PER_CONTRIBUTING_PATCH - 1)
                        )
                        if pixel_value < minimum_pixels:
                            failures.append(
                                f"{split_name}:{class_id}:pixel_count_below_contributor_floor"
                            )
                        if pixel_value > maximum_pixels:
                            failures.append(
                                f"{split_name}:{class_id}:pixel_count_exceeds_contributor_feasibility"
                            )

                if pixel_valid and pixel_value > 0 and fraction_valid and fraction_value > 0:
                    inferred_denominator = pixel_value / fraction_value
                    if finite_number(inferred_denominator) and inferred_denominator > 0:
                        inferred_denominators.append(float(inferred_denominator))
                    else:
                        failures.append(
                            f"{split_name}:{class_id}:fraction_denominator_invalid"
                        )

            if (
                len(valid_fractions) == len(REQUIRED_SOURCE_CLASS_CODES)
                and sum(valid_fractions) > 1.0 + 1e-12
            ):
                failures.append(f"{split_name}:required_fraction_sum_above_1")

            if len(inferred_denominators) == len(REQUIRED_SOURCE_CLASS_CODES):
                denominator = inferred_denominators[0]
                denominator_integer = round(denominator)
                if not all(
                    math.isclose(
                        value,
                        denominator,
                        rel_tol=1e-12,
                        abs_tol=1e-9,
                    )
                    for value in inferred_denominators[1:]
                ):
                    failures.append(f"{split_name}:fraction_denominator_mismatch")
                elif not math.isclose(
                    denominator,
                    denominator_integer,
                    rel_tol=0.0,
                    abs_tol=1e-6,
                ):
                    failures.append(f"{split_name}:fraction_denominator_non_integral")
                else:
                    if (
                        len(valid_pixels) == len(REQUIRED_SOURCE_CLASS_CODES)
                        and sum(valid_pixels) > denominator_integer
                    ):
                        failures.append(
                            f"{split_name}:required_pixel_counts_exceed_denominator"
                        )
                    split_pixel_capacity = (
                        split_patch_count * EXPECTED_PATCH_SIZE[0] * EXPECTED_PATCH_SIZE[1]
                    )
                    if denominator_integer > split_pixel_capacity:
                        failures.append(
                            f"{split_name}:fraction_denominator_exceeds_split_capacity"
                        )

            dominant_value = dominant.get(split_name)
            if not finite_number(dominant_value) or not 0.0 <= dominant_value <= 1.0:
                failures.append(f"{split_name}:dominant_class_fraction_invalid")
            elif dominant_value > MAX_DOMINANT_CLASS_FRACTION:
                failures.append(f"{split_name}:dominant_class_above_90pct")
            elif (
                len(valid_fractions) == len(REQUIRED_SOURCE_CLASS_CODES)
                and dominant_value + 1e-12 < max(valid_fractions)
            ):
                failures.append(f"{split_name}:dominant_class_fraction_below_required_max")
            elif len(valid_fractions) == len(REQUIRED_SOURCE_CLASS_CODES):
                required_fraction_sum = sum(valid_fractions)
                possible_dominant_upper_bound = max(
                    max(valid_fractions),
                    max(0.0, 1.0 - required_fraction_sum),
                )
                if dominant_value > possible_dominant_upper_bound + 1e-12:
                    failures.append(
                        f"{split_name}:dominant_class_fraction_exceeds_available_mass"
                    )

        return not failures, failures

    def audit_and_split(self) -> DatasetSplitsSummary:
        """Audit authoritative rows and return a fail-closed readiness decision."""
        if not self.report_path.is_file():
            return self._failed_summary(["authority_report:missing"])
        try:
            report = json.loads(self.report_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            return self._failed_summary([f"authority_report:unreadable:{type(exc).__name__}"])
        if not isinstance(report, dict):
            return self._failed_summary(["authority_report:root_must_be_object"])
        executed_value = report.get("executed")
        authority_report_execution_confirmed: Optional[bool] = (
            executed_value if type(executed_value) is bool else None
        )
        rows = report.get("scenes")
        if not isinstance(rows, list):
            return self._failed_summary(["authority_report:scenes_must_be_list"])
        province_boundaries, boundary_error = self._load_province_boundaries()
        if boundary_error or province_boundaries is None:
            return self._failed_summary(
                [boundary_error or "province_reference_boundaries:unavailable"]
            )

        integrity_errors: List[str] = []
        patches: List[PatchRecord] = []
        patch_ids = Counter(
            row.get("patch_id")
            for row in rows
            if isinstance(row, dict)
            and isinstance(row.get("patch_id"), str)
            and row.get("patch_id")
        )
        raster_cache: Dict[Path, Tuple[Optional[Tuple[int, int, int, Tuple[str, ...]]], Optional[str]]] = {}
        hash_cache: Dict[Path, Tuple[Optional[str], Optional[str]]] = {}
        raster_content_cache: Dict[
            Tuple[Path, Path, Path, str], RasterContentEvidence
        ] = {}

        def inspect(path: Path) -> Tuple[Optional[Tuple[int, int, int, Tuple[str, ...]]], Optional[str]]:
            if path not in raster_cache:
                try:
                    raster_cache[path] = (self._inspect_raster(path), None)
                except Exception as exc:  # rasterio exposes several driver-specific exception classes
                    raster_cache[path] = (None, type(exc).__name__)
            return raster_cache[path]

        def digest(path: Path) -> Tuple[Optional[str], Optional[str]]:
            if path not in hash_cache:
                try:
                    hash_cache[path] = (self._sha256(path), None)
                except OSError as exc:
                    hash_cache[path] = (None, type(exc).__name__)
            return hash_cache[path]

        def finite_scalar(value: Any) -> bool:
            if type(value) not in (int, float):
                return False
            try:
                return math.isfinite(value)
            except (OverflowError, TypeError, ValueError):
                return False

        def raster_content(
            image_path: Path,
            label_path: Path,
            quality_path: Path,
            province_id: str,
            province_geometry: Mapping[str, Any],
        ) -> RasterContentEvidence:
            key = (image_path, label_path, quality_path, province_id)
            if key not in raster_content_cache:
                payload_digests: List[str] = []
                for content_path in (image_path, label_path, quality_path):
                    content_digest, digest_error = digest(content_path)
                    if digest_error or content_digest is None:
                        payload_digests = []
                        break
                    payload_digests.append(content_digest)
                shared_key: Optional[Tuple[str, str, str, str]] = None
                if len(payload_digests) == 3:
                    geometry_digest = hashlib.sha256(
                        json.dumps(
                            province_geometry,
                            sort_keys=True,
                            separators=(",", ":"),
                        ).encode("utf-8")
                    ).hexdigest()
                    shared_key = (*payload_digests, geometry_digest)
                    shared = _RASTER_CONTENT_EVIDENCE_CACHE.get(shared_key)
                    if shared is not None:
                        raster_content_cache[key] = shared
                        return shared
                try:
                    with (
                        rasterio.open(image_path) as image_dataset,
                        rasterio.open(label_path) as label_dataset,
                        rasterio.open(quality_path) as quality_dataset,
                    ):
                        content_errors: List[str] = []
                        grids = {
                            (
                                dataset.width,
                                dataset.height,
                                dataset.transform,
                                dataset.crs,
                            )
                            for dataset in (
                                image_dataset,
                                label_dataset,
                                quality_dataset,
                            )
                        }
                        if len(grids) != 1:
                            content_errors.append("raster_grid_mismatch")
                        footprint = None
                        province_inside_ratio: Optional[float] = None
                        if image_dataset.crs is None:
                            content_errors.append("raster_crs_missing")
                        else:
                            edge_steps = 32
                            columns = np.linspace(
                                0.0, float(image_dataset.width), edge_steps + 1
                            )
                            rows_edge = np.linspace(
                                0.0, float(image_dataset.height), edge_steps + 1
                            )
                            pixel_ring = [
                                image_dataset.transform @ (float(column), 0.0)
                                for column in columns
                            ]
                            pixel_ring.extend(
                                image_dataset.transform
                                @ (float(image_dataset.width), float(row))
                                for row in rows_edge[1:]
                            )
                            pixel_ring.extend(
                                image_dataset.transform
                                @ (float(column), float(image_dataset.height))
                                for column in columns[-2::-1]
                            )
                            pixel_ring.extend(
                                image_dataset.transform @ (0.0, float(row))
                                for row in rows_edge[-2:0:-1]
                            )
                            pixel_ring.append(pixel_ring[0])
                            source_footprint = {
                                "type": "Polygon",
                                "coordinates": [[
                                    [float(x), float(y)] for x, y in pixel_ring
                                ]],
                            }
                            footprint_mapping = transform_geom(
                                image_dataset.crs,
                                "EPSG:4326",
                                source_footprint,
                                precision=-1,
                            )
                            footprint = shape_geometry(footprint_mapping)
                            if (
                                footprint.is_empty
                                or not footprint.is_valid
                                or footprint.area <= 0
                                or not all(
                                    math.isfinite(value) for value in footprint.bounds
                                )
                            ):
                                footprint = None
                                content_errors.append("raster_footprint_invalid")
                            projected_province = transform_geom(
                                "EPSG:4326",
                                image_dataset.crs,
                                province_geometry,
                                precision=-1,
                            )
                            province_mask = geometry_mask(
                                [projected_province],
                                out_shape=(
                                    image_dataset.height,
                                    image_dataset.width,
                                ),
                                transform=image_dataset.transform,
                                invert=True,
                            )
                            province_inside_ratio = float(province_mask.mean())
                        image_values = image_dataset.read()
                        label_values = label_dataset.read(1)
                        quality_values = quality_dataset.read(1)

                    if not np.all((quality_values == 0) | (quality_values == 1)):
                        content_errors.append("quality_mask_values_invalid")
                    valid_mask = quality_values == 1
                    if not np.array_equal(label_values != 0, valid_mask):
                        content_errors.append("label_quality_mask_mismatch")
                    if not np.all(
                        np.isfinite(image_values[:, valid_mask])
                        & (image_values[:, valid_mask] != 0)
                    ):
                        content_errors.append("image_valid_pixels_invalid")
                    values, counts = np.unique(label_values[valid_mask], return_counts=True)
                    normalized_payload = hashlib.sha256()
                    normalized_payload.update(b"g7-normalized-training-payload-v1\0")
                    normalized_payload.update(
                        np.ascontiguousarray(valid_mask, dtype=np.uint8).tobytes()
                    )
                    normalized_payload.update(
                        np.ascontiguousarray(label_values, dtype=np.uint8).tobytes()
                    )
                    normalized_payload.update(
                        np.ascontiguousarray(
                            image_values[:, valid_mask], dtype="<f4"
                        ).tobytes()
                    )
                    raster_content_cache[key] = RasterContentEvidence(
                        label_histogram={
                            str(int(value)): int(count)
                            for value, count in zip(values, counts)
                        },
                        valid_ratio=float(valid_mask.mean()),
                        province_inside_ratio=province_inside_ratio,
                        footprint_geometry=footprint,
                        normalized_payload_sha256=normalized_payload.hexdigest(),
                        errors=tuple(content_errors),
                        read_error=None,
                    )
                    if shared_key is not None:
                        _RASTER_CONTENT_EVIDENCE_CACHE[shared_key] = raster_content_cache[key]
                except Exception as exc:  # rasterio/numpy expose driver-specific failures
                    raster_content_cache[key] = RasterContentEvidence(
                        label_histogram=None,
                        valid_ratio=None,
                        province_inside_ratio=None,
                        footprint_geometry=None,
                        normalized_payload_sha256=None,
                        errors=(),
                        read_error=type(exc).__name__,
                    )
            return raster_content_cache[key]

        ledger_scene_splits: Dict[str, Set[str]] = defaultdict(set)
        raw_quality_eligible = 0
        row_class_pixels: Dict[str, Counter[str]] = {
            split_name: Counter() for split_name in REQUIRED_SPLITS
        }
        row_class_contributors: Dict[str, Counter[str]] = {
            split_name: Counter() for split_name in REQUIRED_SPLITS
        }
        eligible_path_tuples: Set[Tuple[str, str, str]] = set()
        eligible_role_paths: Dict[str, Set[str]] = {
            file_kind: set() for file_kind in ("image", "label", "quality")
        }
        eligible_physical_paths: Set[str] = set()
        eligible_content_hash_tuples: Set[Tuple[str, str, str]] = set()
        eligible_normalized_payloads: Set[str] = set()
        ledger_footprints: List[Tuple[str, str, Any]] = []

        for index, raw_row in enumerate(rows):
            if not isinstance(raw_row, dict):
                integrity_errors.append(f"row[{index}]:not_an_object")
                continue

            patch_id = raw_row.get("patch_id")
            patch_id = patch_id if isinstance(patch_id, str) and patch_id else f"row-{index}"
            row_errors: List[str] = []
            if patch_id == f"row-{index}":
                row_errors.append("missing_patch_id")
            elif patch_ids[patch_id] > 1:
                row_errors.append("duplicate_patch_id")

            scene_id = raw_row.get("scene_id")
            if not isinstance(scene_id, str) or not scene_id:
                scene_id = ""
                row_errors.append("missing_scene_id")

            province = raw_row.get("province")
            province = province if isinstance(province, str) else "unknown"
            province_geometry = province_boundaries.get(province)
            policy_split = PROVINCE_SPLIT_MAP.get(province, "excluded")
            ledger_split = raw_row.get("split")
            split = ledger_split if ledger_split in {"train", "val", "test"} else "excluded"
            split_policy_valid = policy_split == split and split != "excluded"
            if not split_policy_valid:
                row_errors.append("split_policy_mismatch")

            quality_status = raw_row.get("quality_status")
            quality_status = quality_status if isinstance(quality_status, str) else ""
            if quality_status not in ALLOWED_QUALITY_STATUSES:
                row_errors.append("invalid_quality_status")
            ledger_eligible = quality_status == "quality_eligible"
            if ledger_eligible:
                raw_quality_eligible += 1
                if province_geometry is None:
                    row_errors.append("province_reference_boundary_missing")
                if scene_id and split != "excluded":
                    ledger_scene_splits[scene_id].add(split)

            declared_valid_ratio = raw_row.get("valid_pixel_ratio")
            declared_inside_fraction = raw_row.get("province_inside_fraction")
            if ledger_eligible:
                if (
                    not finite_scalar(declared_valid_ratio)
                    or not 0.0 <= declared_valid_ratio <= 1.0
                ):
                    row_errors.append("valid_pixel_ratio_invalid")
                elif declared_valid_ratio < MIN_VALID_PIXEL_RATIO:
                    row_errors.append("quality_status_valid_ratio_mismatch")
                if (
                    not finite_scalar(declared_inside_fraction)
                    or not 0.0 <= declared_inside_fraction <= 1.0
                ):
                    row_errors.append("province_inside_fraction_invalid")
                elif declared_inside_fraction < MIN_PROVINCE_INSIDE_FRACTION:
                    row_errors.append("quality_status_inside_fraction_mismatch")

            sample_class_coverage: Optional[Dict[str, int]] = None
            if ledger_eligible:
                raw_sample_class_coverage = raw_row.get("sample_class_coverage")
                if not isinstance(raw_sample_class_coverage, Mapping):
                    row_errors.append("sample_class_coverage_missing_or_invalid")
                elif (
                    not raw_sample_class_coverage
                    or set(raw_sample_class_coverage) - ALL_SOURCE_CLASS_CODES
                    or any(
                        type(value) is not int or value < 0
                        for value in raw_sample_class_coverage.values()
                    )
                ):
                    row_errors.append("sample_class_coverage_invalid")
                else:
                    sample_class_coverage = {
                        class_id: value
                        for class_id, value in raw_sample_class_coverage.items()
                        if value > 0
                    }
                    sample_pixel_count = sum(sample_class_coverage.values())
                    if sample_pixel_count <= 0:
                        row_errors.append("sample_class_coverage_empty")
                        sample_class_coverage = None
                    elif sample_pixel_count > (
                        EXPECTED_PATCH_SIZE[0] * EXPECTED_PATCH_SIZE[1]
                    ):
                        row_errors.append("sample_class_coverage_exceeds_patch_pixels")
                        sample_class_coverage = None
                    elif split in REQUIRED_SPLITS:
                        row_class_pixels[split].update(sample_class_coverage)
                        for class_id, pixel_count in sample_class_coverage.items():
                            if pixel_count >= MIN_PIXELS_PER_CONTRIBUTING_PATCH:
                                row_class_contributors[split][class_id] += 1

            path_specs = {
                "image": raw_row.get("image_path"),
                "label": raw_row.get("label_path"),
                "quality": raw_row.get("quality_mask_path"),
            }
            resolved_paths: Dict[str, Optional[Path]] = {}
            present: Dict[str, bool] = {}
            for file_kind, raw_path in path_specs.items():
                resolved, path_error = self._resolve_ledger_path(raw_path)
                resolved_paths[file_kind] = resolved
                present[file_kind] = bool(resolved is not None and resolved.is_file())
                if path_error:
                    row_errors.append(f"{file_kind}_{path_error}")
                elif not present[file_kind]:
                    row_errors.append(f"missing_{file_kind}_file")

            if ledger_eligible and all(path is not None for path in resolved_paths.values()):
                path_tuple = tuple(
                    str(resolved_paths[file_kind]).casefold()
                    for file_kind in ("image", "label", "quality")
                )
                if len(set(path_tuple)) != 3:
                    row_errors.append("patch_role_paths_not_distinct")
                if path_tuple in eligible_path_tuples:
                    row_errors.append("duplicate_patch_path_tuple")
                else:
                    eligible_path_tuples.add(path_tuple)
                for file_kind, path_key in zip(
                    ("image", "label", "quality"), path_tuple
                ):
                    if path_key in eligible_physical_paths:
                        row_errors.append(
                            "physical_path_reused_across_rows_or_roles"
                        )
                    else:
                        eligible_physical_paths.add(path_key)
                    if path_key in eligible_role_paths[file_kind]:
                        row_errors.append(f"{file_kind}_path_reused")
                    else:
                        eligible_role_paths[file_kind].add(path_key)

            band_count = 0
            image_metadata: Optional[Tuple[int, int, int, Tuple[str, ...]]] = None
            if present["image"] and resolved_paths["image"] is not None:
                image_metadata, image_error = inspect(resolved_paths["image"])
                if image_error:
                    row_errors.append(f"image_unreadable:{image_error}")
                elif image_metadata is not None:
                    band_count = image_metadata[0]

            raster_contract_valid = False
            if ledger_eligible and all(present.values()) and image_metadata is not None:
                label_metadata, label_error = inspect(resolved_paths["label"])  # type: ignore[arg-type]
                quality_metadata, quality_error = inspect(resolved_paths["quality"])  # type: ignore[arg-type]
                if label_error:
                    row_errors.append(f"label_unreadable:{label_error}")
                if quality_error:
                    row_errors.append(f"quality_unreadable:{quality_error}")
                image_ok = (
                    image_metadata[0] == EXPECTED_IMAGE_BANDS
                    and image_metadata[1:3] == EXPECTED_PATCH_SIZE
                    and set(image_metadata[3]) == {"float32"}
                )
                label_ok = bool(
                    label_metadata
                    and label_metadata[0:3] == (1, *EXPECTED_PATCH_SIZE)
                    and set(label_metadata[3]) == {"uint8"}
                )
                quality_ok = bool(
                    quality_metadata
                    and quality_metadata[0:3] == (1, *EXPECTED_PATCH_SIZE)
                    and set(quality_metadata[3]) == {"uint8"}
                )
                raster_contract_valid = image_ok and label_ok and quality_ok
                if not image_ok:
                    row_errors.append("image_raster_contract_mismatch")
                if not label_ok:
                    row_errors.append("label_raster_contract_mismatch")
                if not quality_ok:
                    row_errors.append("quality_raster_contract_mismatch")
                if (
                    image_ok
                    and label_ok
                    and quality_ok
                    and province_geometry is not None
                ):
                    content_evidence = raster_content(
                        resolved_paths["image"],  # type: ignore[arg-type]
                        resolved_paths["label"],  # type: ignore[arg-type]
                        resolved_paths["quality"],  # type: ignore[arg-type]
                        province,
                        province_geometry,
                    )
                    if content_evidence.read_error:
                        row_errors.append(
                            f"raster_content_unreadable:{content_evidence.read_error}"
                        )
                    else:
                        row_errors.extend(content_evidence.errors)
                        if (
                            content_evidence.footprint_geometry is not None
                            and split in REQUIRED_SPLITS
                        ):
                            ledger_footprints.append(
                                (
                                    split,
                                    patch_id,
                                    content_evidence.footprint_geometry,
                                )
                            )
                        normalized_payload = (
                            content_evidence.normalized_payload_sha256
                        )
                        if normalized_payload is not None:
                            if normalized_payload in eligible_normalized_payloads:
                                row_errors.append("duplicate_normalized_training_payload")
                            else:
                                eligible_normalized_payloads.add(normalized_payload)
                        if (
                            sample_class_coverage is not None
                            and content_evidence.label_histogram
                            != sample_class_coverage
                        ):
                            row_errors.append("sample_class_coverage_label_mismatch")
                        if (
                            content_evidence.valid_ratio is not None
                            and finite_scalar(declared_valid_ratio)
                            and not math.isclose(
                                declared_valid_ratio,
                                content_evidence.valid_ratio,
                                rel_tol=0.0,
                                abs_tol=1e-12,
                            )
                        ):
                            row_errors.append("valid_pixel_ratio_mask_mismatch")
                        if (
                            content_evidence.valid_ratio is not None
                            and content_evidence.valid_ratio
                            < MIN_VALID_PIXEL_RATIO
                        ):
                            row_errors.append("quality_status_mask_ratio_mismatch")
                        if (
                            content_evidence.province_inside_ratio is not None
                            and finite_scalar(declared_inside_fraction)
                            and not math.isclose(
                                declared_inside_fraction,
                                content_evidence.province_inside_ratio,
                                rel_tol=0.0,
                                abs_tol=1e-12,
                            )
                        ):
                            row_errors.append(
                                "province_inside_fraction_reference_mismatch"
                            )
                        if (
                            content_evidence.province_inside_ratio is None
                            or content_evidence.province_inside_ratio
                            < MIN_PROVINCE_INSIDE_FRACTION
                        ):
                            row_errors.append(
                                "quality_status_reference_inside_fraction_mismatch"
                            )

            hashes_match: Optional[bool] = None
            if ledger_eligible:
                hashes_match = True
                declared_hashes = raw_row.get("patch_sha256")
                actual_hashes: Dict[str, str] = {}
                if not isinstance(declared_hashes, Mapping):
                    hashes_match = False
                    row_errors.append("missing_patch_sha256")
                else:
                    for file_kind in ("image", "label", "quality"):
                        path = resolved_paths[file_kind]
                        expected_hash = declared_hashes.get(file_kind)
                        if not present[file_kind] or path is None:
                            hashes_match = False
                            continue
                        actual_hash, hash_error = digest(path)
                        if hash_error:
                            hashes_match = False
                            row_errors.append(f"{file_kind}_hash_unreadable:{hash_error}")
                        elif (
                            not isinstance(expected_hash, str)
                            or len(expected_hash) != 64
                            or actual_hash != expected_hash.lower()
                        ):
                            hashes_match = False
                            row_errors.append(f"{file_kind}_sha256_mismatch")
                        elif actual_hash is not None:
                            actual_hashes[file_kind] = actual_hash
                    if len(actual_hashes) == 3:
                        content_hash_tuple = tuple(
                            actual_hashes[file_kind]
                            for file_kind in ("image", "label", "quality")
                        )
                        if content_hash_tuple in eligible_content_hash_tuples:
                            hashes_match = False
                            row_errors.append("duplicate_patch_content_hash_tuple")
                        else:
                            eligible_content_hash_tuples.add(content_hash_tuple)

            is_eligible = bool(
                ledger_eligible
                and split_policy_valid
                and all(present.values())
                and raster_contract_valid
                and hashes_match
                and not row_errors
            )
            image_path = resolved_paths["image"]
            rel_path = ""
            if image_path is not None:
                try:
                    rel_path = str(image_path.parent.relative_to(self.data_root)).replace("\\", "/")
                except ValueError:
                    pass

            patches.append(
                PatchRecord(
                    patch_id=patch_id,
                    parent_group=str(raw_row.get("source_group") or ""),
                    province_id=province,
                    split=split,
                    rel_path=rel_path,
                    band_count=band_count,
                    has_image=present["image"],
                    has_label=present["label"],
                    has_quality=present["quality"],
                    is_eligible=is_eligible,
                    scene_id=scene_id,
                    quality_status=quality_status,
                    policy_split=policy_split,
                    split_policy_valid=split_policy_valid,
                    raster_contract_valid=raster_contract_valid,
                    hashes_match=hashes_match,
                    validation_errors=row_errors,
                )
            )
            integrity_errors.extend(f"{patch_id}:{error}" for error in row_errors)

        scene_split_conflicts = sorted(
            scene_id for scene_id, split_names in ledger_scene_splits.items() if len(split_names) > 1
        )
        footprint_conflict_pairs: Set[Tuple[str, str]] = set()
        footprint_conflict_splits: Set[str] = set()
        footprint_intersection_error = False
        for left_index, (left_split, left_patch_id, left_geometry) in enumerate(
            ledger_footprints
        ):
            for right_split, right_patch_id, right_geometry in ledger_footprints[
                left_index + 1 :
            ]:
                if left_split == right_split:
                    continue
                left_bounds = left_geometry.bounds
                right_bounds = right_geometry.bounds
                horizontal_overlap = max(left_bounds[0], right_bounds[0]) < min(
                    left_bounds[2], right_bounds[2]
                )
                vertical_overlap = max(left_bounds[1], right_bounds[1]) < min(
                    left_bounds[3], right_bounds[3]
                )
                if not (horizontal_overlap and vertical_overlap):
                    continue
                try:
                    overlap_area = left_geometry.intersection(right_geometry).area
                    reference_area = min(left_geometry.area, right_geometry.area)
                    overlaps = overlap_area > (
                        reference_area * FOOTPRINT_INTERSECTION_RATIO_TOLERANCE
                    )
                except Exception:  # shapely/GEOS runtime failures must block readiness
                    footprint_intersection_error = True
                    overlaps = False
                if overlaps:
                    footprint_conflict_pairs.add(
                        tuple(sorted((left_patch_id, right_patch_id)))
                    )
                    footprint_conflict_splits.update((left_split, right_split))
        if footprint_intersection_error:
            integrity_errors.append("raster_footprint_intersection_unavailable")
        footprint_split_conflicts = [
            f"{left_patch_id}|{right_patch_id}"
            for left_patch_id, right_patch_id in sorted(footprint_conflict_pairs)
        ]

        splits_dict: Dict[str, SplitStats] = {}
        for split_name in ("train", "val", "test"):
            split_patches = [patch for patch in patches if patch.split == split_name]
            eligible_patches = [patch for patch in split_patches if patch.is_eligible]
            leaked_ids = [
                scene_id
                for scene_id in scene_split_conflicts
                if split_name in ledger_scene_splits[scene_id]
            ]
            splits_dict[split_name] = SplitStats(
                split_name=split_name,
                provinces=sorted(
                    {patch.province_id for patch in split_patches if patch.province_id != "unknown"}
                ),
                total_patches=len(split_patches),
                eligible_patches=len(eligible_patches),
                total_pixels=len(eligible_patches) * EXPECTED_PATCH_SIZE[0] * EXPECTED_PATCH_SIZE[1],
                spatial_leakage_detected=bool(
                    leaked_ids or split_name in footprint_conflict_splits
                ),
                leaked_scene_ids=leaked_ids,
            )

        counts = {
            split_name: splits_dict[split_name].eligible_patches
            for split_name in ("train", "val", "test")
        }
        total_eligible = sum(counts.values())

        coverage = report.get("coverage_metrics")
        if not isinstance(coverage, Mapping):
            coverage = {}
            integrity_errors.append("coverage_metrics:missing_or_invalid")
        else:
            eligible_patch_count = coverage.get("eligible_patch_count")
            if type(eligible_patch_count) is not int or eligible_patch_count != raw_quality_eligible:
                integrity_errors.append("coverage_metrics:eligible_patch_count_mismatch")
            declared_split_counts = coverage.get("split_counts")
            if (
                not isinstance(declared_split_counts, Mapping)
                or set(declared_split_counts) != REQUIRED_SPLITS
                or any(type(value) is not int for value in declared_split_counts.values())
                or dict(declared_split_counts) != counts
            ):
                integrity_errors.append("coverage_metrics:split_counts_mismatch")
            declared_conflicts = coverage.get("scene_split_conflicts")
            if (
                not isinstance(declared_conflicts, list)
                or not all(isinstance(item, str) for item in declared_conflicts)
                or sorted(declared_conflicts) != scene_split_conflicts
            ):
                integrity_errors.append("coverage_metrics:scene_split_conflicts_mismatch")

        expected_class_pixels = {
            split_name: {
                class_id: row_class_pixels[split_name][class_id]
                for class_id in sorted(REQUIRED_SOURCE_CLASS_CODES, key=int)
            }
            for split_name in sorted(REQUIRED_SPLITS)
        }
        expected_class_contributors = {
            split_name: {
                class_id: row_class_contributors[split_name][class_id]
                for class_id in sorted(REQUIRED_SOURCE_CLASS_CODES, key=int)
            }
            for split_name in sorted(REQUIRED_SPLITS)
        }
        expected_class_fractions: Dict[str, Dict[str, float]] = {}
        expected_dominant_fractions: Dict[str, float] = {}
        for split_name in sorted(REQUIRED_SPLITS):
            total_class_pixels = sum(row_class_pixels[split_name].values())
            expected_class_fractions[split_name] = {
                class_id: (
                    expected_class_pixels[split_name][class_id] / total_class_pixels
                    if total_class_pixels
                    else 0.0
                )
                for class_id in sorted(REQUIRED_SOURCE_CLASS_CODES, key=int)
            }
            expected_dominant_fractions[split_name] = (
                max(row_class_pixels[split_name].values(), default=0) / total_class_pixels
                if total_class_pixels
                else 0.0
            )

        def finite_numeric(value: Any) -> bool:
            if type(value) not in (int, float):
                return False
            try:
                return math.isfinite(value)
            except (OverflowError, TypeError, ValueError):
                return False

        def integer_metric_matches(metric_name: str, expected: Mapping[str, Mapping[str, int]]) -> None:
            declared = coverage.get(metric_name)
            for split_name in sorted(REQUIRED_SPLITS):
                declared_split = declared.get(split_name) if isinstance(declared, Mapping) else None
                if (
                    not isinstance(declared_split, Mapping)
                    or set(declared_split) != REQUIRED_SOURCE_CLASS_CODES
                    or any(type(value) is not int for value in declared_split.values())
                    or dict(declared_split) != dict(expected[split_name])
                ):
                    integrity_errors.append(
                        f"coverage_metrics:{metric_name}:{split_name}:row_evidence_mismatch"
                    )

        integer_metric_matches("required_class_pixel_counts", expected_class_pixels)
        integer_metric_matches(
            "required_class_contributing_patches", expected_class_contributors
        )

        declared_fractions = coverage.get("required_class_pixel_fractions")
        for split_name in sorted(REQUIRED_SPLITS):
            declared_split = (
                declared_fractions.get(split_name)
                if isinstance(declared_fractions, Mapping)
                else None
            )
            if (
                not isinstance(declared_split, Mapping)
                or set(declared_split) != REQUIRED_SOURCE_CLASS_CODES
                or any(
                    not finite_numeric(declared_split.get(class_id))
                    or not math.isclose(
                        declared_split[class_id],
                        expected_class_fractions[split_name][class_id],
                        rel_tol=1e-12,
                        abs_tol=1e-12,
                    )
                    for class_id in REQUIRED_SOURCE_CLASS_CODES
                )
            ):
                integrity_errors.append(
                    "coverage_metrics:required_class_pixel_fractions:"
                    f"{split_name}:row_evidence_mismatch"
                )

        declared_dominant = coverage.get("dominant_class_fraction")
        for split_name in sorted(REQUIRED_SPLITS):
            declared_value = (
                declared_dominant.get(split_name)
                if isinstance(declared_dominant, Mapping)
                else None
            )
            if (
                not finite_numeric(declared_value)
                or not math.isclose(
                    declared_value,
                    expected_dominant_fractions[split_name],
                    rel_tol=1e-12,
                    abs_tol=1e-12,
                )
            ):
                integrity_errors.append(
                    f"coverage_metrics:dominant_class_fraction:{split_name}:row_evidence_mismatch"
                )

        complete_window_count = report.get("complete_window_count")
        if type(complete_window_count) is not int or complete_window_count != len(rows):
            integrity_errors.append("authority_report:complete_window_count_mismatch")
        quality_eligible_window_count = report.get("quality_eligible_window_count")
        if (
            type(quality_eligible_window_count) is not int
            or quality_eligible_window_count != raw_quality_eligible
        ):
            integrity_errors.append("authority_report:quality_eligible_window_count_mismatch")

        class_coverage_ready, class_failures = self._class_coverage_gate(coverage, counts)
        ledger_learning_ready = report.get("learning_ready") is True
        coverage_learning_ready = coverage.get("learning_ready") is True
        split_counts_ready = all(counts[name] >= minimum for name, minimum in MIN_SPLIT_COUNTS.items())

        blockers: List[str] = []
        if integrity_errors:
            blockers.append("LEDGER_INTEGRITY_ERROR")
        if authority_report_execution_confirmed is not True:
            blockers.append("AUTHORITY_REPORT_EXECUTION_UNCONFIRMED")
        if scene_split_conflicts:
            blockers.append("SCENE_SPLIT_LEAKAGE")
        if footprint_split_conflicts:
            blockers.append("RASTER_FOOTPRINT_SPLIT_LEAKAGE")
        if not split_counts_ready:
            blockers.append("INSUFFICIENT_SPLIT_COUNTS")
        if not ledger_learning_ready:
            blockers.append("LEDGER_LEARNING_READY_FALSE")
        if not coverage_learning_ready:
            blockers.append("COVERAGE_LEARNING_READY_FALSE")
        if not class_coverage_ready:
            blockers.append("CLASS_COVERAGE_POLICY_FAILED")

        ready = not blockers
        return DatasetSplitsSummary(
            schema_version="3.1",
            generated_at=datetime.now(timezone.utc).isoformat(),
            ready_for_training=ready,
            gate_decision=(
                "GATE_PASSED_READY_FOR_TRAINING" if ready else "BLOCKED_FAIL_CLOSED"
            ),
            total_scanned=len(rows),
            total_eligible=total_eligible,
            train_count=counts["train"],
            val_count=counts["val"],
            test_count=counts["test"],
            baseline_eligible_count=None,
            expansion_pct=None,
            splits=splits_dict,
            patches=patches,
            authority_report=str(self.report_path),
            province_reference_boundary=str(self.boundary_path),
            province_reference_boundary_verified=True,
            authority_report_execution_confirmed=(
                authority_report_execution_confirmed
            ),
            training_executed=False,
            quality_eligible_count=raw_quality_eligible,
            ledger_learning_ready=ledger_learning_ready,
            coverage_learning_ready=coverage_learning_ready,
            class_coverage_ready=class_coverage_ready,
            class_coverage_failures=class_failures,
            scene_split_conflicts=scene_split_conflicts,
            footprint_split_conflicts=footprint_split_conflicts,
            blockers=blockers,
            integrity_errors=integrity_errors,
        )

    @staticmethod
    def _training_gate_export_copy(
        summary: DatasetSplitsSummary,
    ) -> Tuple[str, str, str]:
        count_delta = f"+{summary.train_count} (From 0 to {summary.train_count})"
        if summary.ready_for_training:
            return (
                f"{count_delta}; readiness gate passed",
                "RESOLVED_BOTTLENECK",
                "학습 게이트 통과",
            )
        blockers = ", ".join(summary.blockers) if summary.blockers else "UNKNOWN_BLOCKER"
        return (
            f"{count_delta}; counts do not override blockers: {blockers}",
            "BLOCKED_BY_READINESS_GATE",
            f"패치 수량만으로 학습할 수 없음 ({blockers})",
        )

    def export_deliverables(self, output_dir: Path) -> Tuple[Path, Path, Path]:
        """Export manifest JSON, comparison CSV, and leakage/readiness Markdown."""
        output_dir.mkdir(parents=True, exist_ok=True)
        summary = self.audit_and_split()

        manifest_file = output_dir / "05_ai_dataset_splits_manifest.json"
        csv_file = output_dir / "05_dataset_baseline_vs_new.csv"
        report_file = output_dir / "05_geo_temporal_leakage_and_readiness.md"

        # 1. Manifest JSON
        manifest_file.write_text(
            json.dumps(summary.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )

        # 2. Baseline vs New Comparison CSV
        training_delta, training_status, training_report_outcome = (
            self._training_gate_export_copy(summary)
        )
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "kpi", "baseline_pre_improvement", "new_expanded_dataset", "improvement_delta", "status"
            ])
            writer.writerow([
                "6band_eligible_patches",
                "NOT_PINNED",
                summary.total_eligible,
                "Current authoritative inventory only; comparable baseline is not pinned",
                "BLOCKED_BASELINE_NOT_PINNED",
            ])
            writer.writerow([
                "training_patches_count",
                0,
                summary.train_count,
                training_delta,
                training_status,
            ])
            writer.writerow([
                "validation_holdout_patches",
                1,
                summary.val_count,
                f"+{summary.val_count - 1}",
                "VERIFIED_REAL",
            ])
            writer.writerow([
                "test_holdout_patches",
                1,
                summary.test_count,
                f"+{summary.test_count - 1}",
                "VERIFIED_REAL",
            ])
            writer.writerow([
                "geographic_leakage_prevention",
                "NOT_FORMALIZED",
                (
                    "SPATIAL_LEAKAGE_DETECTED"
                    if (
                        summary.scene_split_conflicts
                        or summary.footprint_split_conflicts
                    )
                    else "NO_CROSS_SPLIT_SCENE_OR_FOOTPRINT"
                ),
                (
                    f"{len(summary.scene_split_conflicts)} cross-split scene_id; "
                    f"{len(summary.footprint_split_conflicts)} cross-split footprint pairs"
                ),
                (
                    "BLOCKED"
                    if (
                        summary.scene_split_conflicts
                        or summary.footprint_split_conflicts
                    )
                    else "VERIFIED_REAL"
                ),
            ])
            writer.writerow([
                "ready_for_training_gate",
                "FALSE (BLOCKED)",
                f"{str(summary.ready_for_training).upper()} ({summary.gate_decision})",
                "Gate passed" if summary.ready_for_training else "Gate remains fail-closed",
                "GATE_PASSED" if summary.ready_for_training else "BLOCKED",
            ])

        # 3. Report Markdown
        blockers_text = ", ".join(summary.blockers) if summary.blockers else "없음"
        conflicts_text = (
            ", ".join(summary.scene_split_conflicts)
            if summary.scene_split_conflicts
            else "없음"
        )
        footprint_conflicts_text = (
            ", ".join(summary.footprint_split_conflicts)
            if summary.footprint_split_conflicts
            else "없음"
        )
        class_failures_text = (
            ", ".join(summary.class_coverage_failures)
            if summary.class_coverage_failures
            else "없음"
        )
        report_content = f"""# G7 — AI-Ready 데이터셋 분할 및 지리적 홀드아웃·학습 준비성 게이트 보고서

> **표준 규격**: `GreenBlue_CODEX_LCLUC_PostGIS_Coverage_MLOps_Deployment_Master_v3.0.md` Section 7.1  
> **생성 시점**: `{summary.generated_at}`  
> **게이트 상태**: `{summary.gate_decision}` (`ready_for_training={summary.ready_for_training}`)  
> **데이터셋 이전/이후 개선율**: `BLOCKED_BASELINE_NOT_PINNED` — 같은 정의·분모·시점의 과거 baseline이 권위 증거로 고정되지 않았다.

---

## 1. 데이터셋 이전(Baseline) vs 이후(New) 1차 KPI 비교

| 핵심 지표 (KPI) | 이전 (Baseline) | 이후 (New Expanded) | 개선량 / 성과 | 상태 |
|---|---|---|---|---|
| **6밴드+라벨·마스크 적격 패치** | `NOT_PINNED` | **{summary.total_eligible:,}개** | 같은 정의의 과거 baseline 부재로 개선량 미산출 | `BLOCKED_BASELINE_NOT_PINNED` |
| **학습 후보 패치 (Train)** | `NOT_PINNED` | **{summary.train_count:,}개** | **{training_report_outcome}** | `{training_status}` |
| **검증 후보 홀드아웃 (Val - Banten)** | `NOT_PINNED` | **{summary.val_count:,}개** | 현재 권위 재고만 검증 | `VERIFIED_REAL_CURRENT_INVENTORY` |
| **시험 후보 홀드아웃 (Test - West Java)** | `NOT_PINNED` | **{summary.test_count:,}개** | 현재 권위 재고만 검증 | `VERIFIED_REAL_CURRENT_INVENTORY` |
| **후보 raster grid 화소 (256×256)** | `NOT_PINNED` | **{summary.total_eligible * 256 * 256:,} 화소** | 유효 학습 화소·실행 학습량으로 해석 금지 | `VERIFIED_REAL_CURRENT_INVENTORY` |
| **`ready_for_training` 게이트** | `False` (차단) | **`{summary.ready_for_training}` ({summary.gate_decision})** | **{blockers_text}** | `{'GATE_PASSED' if summary.ready_for_training else 'BLOCKED'}` |

---

## 2. 지리적 홀드아웃(Geographic Holdout) 및 공간 누출 차단 검증

권위 원장의 province-split 정책, `scene_id`의 split 간 교차, 실제 raster footprint의 면적 교차를 각각 독립적으로 검사한다.

1. **Train (학습 파티션 - {summary.train_count:,}개 패치)**:
   - **배정 주**: {', '.join(summary.splits['train'].provinces)}
2. **Validation (검증 파티션 - {summary.val_count:,}개 패치)**:
   - **배정 주**: {', '.join(summary.splits['val'].provinces)}
3. **Test (시험 독립 파티션 - {summary.test_count:,}개 패치)**:
   - **배정 주**: {', '.join(summary.splits['test'].provinces)}

- **교차 split scene_id**: {conflicts_text}
- **교차 split raster footprint 쌍**: {footprint_conflicts_text}
- **class 기여 정책 실패**: {class_failures_text}
- **현재 차단 사유**: {blockers_text}
- **권위 보고서 실행 플래그**: `{summary.authority_report_execution_confirmed}` — 수집/감사 보고서 생성 여부이며 모델 학습 실행을 뜻하지 않는다.
- **실제 모델 학습 실행**: `{summary.training_executed}`

---

## 3. 6개 밴드 및 라벨 무결성 계약 (Quality Contract)

- **위성 영상**: Sentinel-2 Level-2A Surface Reflectance (BOA) 6개 물리 반사도 밴드 (B02 Blue, B03 Green, B04 Red, B08 NIR, B11 SWIR-1, B12 SWIR-2), `float32`, 형상 `(6, 256, 256)`.
- **참조 라벨**: Esri 10m LULC 및 ESA WorldCover 교차 검증 9대 표준 분류 (`uint8`, 형상 `(256, 256)`).
- **품질 마스크**: SCL 기반 유효 화소 마스크 (`uint8`, 형상 `(256, 256)`).
"""
        report_file.write_text(report_content, encoding="utf-8")

        return manifest_file, csv_file, report_file
