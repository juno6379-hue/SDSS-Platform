"""Focused tests for the authoritative G7 dataset split and readiness gate."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Dict, Iterable, Tuple

import numpy as np
import pytest
import rasterio
from affine import Affine
from rasterio.windows import Window

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(PROJECT_ROOT / "backend")]

from app.ml.ai_dataset_splits_manager import (  # noqa: E402
    ALL_SOURCE_CLASS_CODES,
    AIDatasetSplitsManager,
    PROVINCE_SPLIT_MAP,
    REQUIRED_SOURCE_CLASS_CODES,
)


DEFAULT_CLASS_PIXELS_PER_PATCH = {
    class_id: 10_000 for class_id in sorted(REQUIRED_SOURCE_CLASS_CODES, key=int)
}
CONTRACT_IMAGE_CACHE: Dict[Tuple[float, Tuple[float, ...]], Tuple[bytes, str]] = {}
CONTRACT_AUX_CACHE: Dict[
    Tuple[str, Tuple[Tuple[str, int], ...], Tuple[float, ...]],
    Tuple[bytes, str],
] = {}


@pytest.fixture(scope="module")
def data_root() -> Path:
    return PROJECT_ROOT / "data"


@pytest.fixture(scope="module")
def real_summary(data_root: Path):
    return AIDatasetSplitsManager(data_root).audit_and_split()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_boundary_fixture(data_root: Path) -> None:
    """Write the exact boundary/SHA contract required by the production gate.

    Synthetic raster footprints span longitudes 100..106 and latitudes near
    -5.  Reusing one broad valid polygon for all six province ids keeps this
    fixture focused on split/raster invariants; it does not claim real
    administrative geometry.
    """
    public_dir = data_root.parent / "frontend" / "public"
    public_dir.mkdir(parents=True, exist_ok=True)
    boundary_path = public_dir / "first-group-provinces.geojson"
    source_path = public_dir / "first-group-provinces.source.json"
    geometry = {
        "type": "Polygon",
        "coordinates": [[[99.0, -6.0], [107.0, -6.0], [107.0, -4.0], [99.0, -4.0], [99.0, -6.0]]],
    }
    collection = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"province_id": province_id},
                "geometry": geometry,
            }
            for province_id in PROVINCE_SPLIT_MAP
        ],
    }
    boundary_path.write_text(
        json.dumps(collection, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    source_path.write_text(
        json.dumps(
            {
                "legal_boundary_certification": False,
                "selected_feature_count": len(collection["features"]),
                "selected_sha256": _sha256(boundary_path),
                "fixture_provenance": "TESTED_SYNTHETIC",
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )


def _write_contract_rasters(
    patch_dir: Path,
    class_pixels_per_patch: Dict[str, int],
    transform,
) -> Tuple[Dict[str, Path], Dict[str, str]]:
    patch_dir.mkdir(parents=True, exist_ok=True)
    label_path = patch_dir / "label.tif"
    quality_path = patch_dir / "quality.tif"

    label = np.zeros((1, 256, 256), dtype=np.uint8)
    offset = 0
    for class_id, pixel_count in sorted(class_pixels_per_patch.items(), key=lambda item: int(item[0])):
        assert class_id in ALL_SOURCE_CLASS_CODES
        label.flat[offset : offset + pixel_count] = int(class_id)
        offset += pixel_count
    assert offset <= label.size

    coverage_key = tuple(
        sorted(class_pixels_per_patch.items(), key=lambda item: int(item[0]))
    )
    transform_key = tuple(float(value) for value in transform)
    digests: Dict[str, str] = {}
    for file_kind, path, values in (
        ("label", label_path, label),
        ("quality", quality_path, (label != 0).astype(np.uint8)),
    ):
        cache_key = (file_kind, coverage_key, transform_key)
        cached = CONTRACT_AUX_CACHE.get(cache_key)
        if cached is not None:
            payload, sha256 = cached
            path.write_bytes(payload)
            digests[file_kind] = sha256
            continue
        with rasterio.open(
            path,
            "w",
            driver="GTiff",
            width=256,
            height=256,
            count=1,
            dtype="uint8",
            crs="EPSG:4326",
            transform=transform,
            compress="deflate",
        ) as dataset:
            dataset.write(values)
        sha256 = _sha256(path)
        CONTRACT_AUX_CACHE[cache_key] = (path.read_bytes(), sha256)
        digests[file_kind] = sha256

    paths = {"label": label_path, "quality": quality_path}
    return paths, digests


def _write_contract_image(path: Path, value: float, transform) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    cache_key = (value, tuple(float(item) for item in transform))
    cached = CONTRACT_IMAGE_CACHE.get(cache_key)
    if cached is not None:
        payload, sha256 = cached
        path.write_bytes(payload)
        return sha256
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=256,
        height=256,
        count=6,
        dtype="float32",
        crs="EPSG:4326",
        transform=transform,
        compress="deflate",
    ) as dataset:
        dataset.write(np.full((6, 256, 256), value, dtype=np.float32))
    sha256 = _sha256(path)
    CONTRACT_IMAGE_CACHE[cache_key] = (path.read_bytes(), sha256)
    return sha256


def _passing_class_metrics(
    split_counts: Dict[str, int],
    class_pixels_per_patch: Dict[str, int],
) -> Dict[str, Dict]:
    classes = tuple(sorted(REQUIRED_SOURCE_CLASS_CODES, key=int))
    total_pixels_per_patch = sum(class_pixels_per_patch.values())
    return {
        "required_class_pixel_counts": {
            split: {
                class_id: class_pixels_per_patch.get(class_id, 0) * split_count
                for class_id in classes
            }
            for split, split_count in split_counts.items()
        },
        "required_class_pixel_fractions": {
            split: {
                class_id: class_pixels_per_patch.get(class_id, 0) / total_pixels_per_patch
                for class_id in classes
            }
            for split in split_counts
        },
        "required_class_contributing_patches": {
            split: {
                class_id: (
                    split_count
                    if class_pixels_per_patch.get(class_id, 0) >= 256
                    else 0
                )
                for class_id in classes
            }
            for split, split_count in split_counts.items()
        },
        "dominant_class_fraction": {
            split: max(class_pixels_per_patch.values()) / total_pixels_per_patch
            for split in split_counts
        },
    }


def _write_authority_fixture(
    data_root: Path,
    *,
    train: int,
    val: int,
    test: int,
    leaked_scene: bool = False,
    overlapped_footprint: bool = False,
    class_pixels_per_patch: Dict[str, int] | None = None,
) -> Tuple[Path, Dict[str, Path]]:
    _write_boundary_fixture(data_root)
    class_pixels_per_patch = dict(
        class_pixels_per_patch or DEFAULT_CLASS_PIXELS_PER_PATCH
    )
    rows = []
    first_paths: Dict[str, Path] | None = None
    global_index = 0
    provinces = {"train": "east_java", "val": "banten", "test": "west_java"}
    counts = {"train": train, "val": val, "test": test}
    for split, count in counts.items():
        for index in range(count):
            patch_dir = (
                data_root
                / "first-group-training-esri-v1"
                / "patches"
                / "fixture"
                / split
                / f"r{index:03d}-c00"
            )
            footprint_index = global_index
            if overlapped_footprint and split == "val" and index == 0:
                footprint_index = 0
            transform = Affine.translation(
                100.0 + footprint_index * 0.05,
                -5.0,
            ) @ Affine.scale(0.0001, -0.0001)
            paths, digests = _write_contract_rasters(
                patch_dir,
                class_pixels_per_patch,
                transform,
            )
            image_path = patch_dir / "image.tif"
            image_sha256 = _write_contract_image(
                image_path,
                1.0 + global_index,
                transform,
            )
            global_index += 1
            if first_paths is None:
                first_paths = {"image": image_path, **paths}
            scene_id = f"scene-{split}-{index}"
            if leaked_scene and index == 0 and split in {"val", "test"}:
                scene_id = "scene-cross-split"
            rows.append(
                {
                    "province": provinces[split],
                    "split": split,
                    "scene_id": scene_id,
                    "source_group": f"fixture/{split}",
                    "patch_id": f"patch-{split}-{index}",
                    "quality_status": "quality_eligible",
                    "valid_pixel_ratio": sum(class_pixels_per_patch.values()) / (256 * 256),
                    "province_inside_fraction": 1.0,
                    "sample_class_coverage": dict(class_pixels_per_patch),
                    "image_path": str(image_path),
                    "label_path": str(paths["label"]),
                    "quality_mask_path": str(paths["quality"]),
                    "patch_sha256": {"image": image_sha256, **digests},
                }
            )

    conflict_ids = ["scene-cross-split"] if leaked_scene else []
    coverage = {
        "eligible_patch_count": len(rows),
        "split_counts": counts,
        "scene_split_conflicts": conflict_ids,
        "learning_ready": True,
        **_passing_class_metrics(counts, class_pixels_per_patch),
    }
    report = {
        "executed": True,
        "learning_ready": True,
        "complete_window_count": len(rows),
        "quality_eligible_window_count": len(rows),
        "scenes": rows,
        "coverage_metrics": coverage,
    }
    report_path = data_root / "first-group-training-esri-v1" / "annual-window-report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
    assert first_paths is not None
    return report_path, first_paths


def _read_report(report_path: Path) -> Dict:
    return json.loads(report_path.read_text(encoding="utf-8"))


def _write_report(report_path: Path, report: Dict) -> None:
    # allow_nan intentionally remains enabled so the gate is tested against
    # Python's permissive JSON decoder and must reject NaN/Infinity itself.
    report_path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")


def _eligible_records(summary) -> Iterable:
    return (patch for patch in summary.patches if patch.quality_status == "quality_eligible")


def test_geographic_holdout_policy():
    assert PROVINCE_SPLIT_MAP == {
        "east_java": "train",
        "south_sulawesi": "train",
        "gorontalo": "train",
        "southeast_sulawesi": "train",
        "banten": "val",
        "west_java": "test",
    }
    # Model IDs [0,1,2,4,6,7] mapped through the Esri source taxonomy.
    assert REQUIRED_SOURCE_CLASS_CODES == frozenset({"1", "2", "5", "7", "8", "11"})


def test_real_authoritative_counts_are_preserved_but_gate_is_fail_closed(real_summary):
    assert real_summary.total_scanned == 1779
    assert real_summary.quality_eligible_count == 1407
    assert real_summary.total_eligible == 1407
    assert (real_summary.train_count, real_summary.val_count, real_summary.test_count) == (
        865,
        292,
        250,
    )
    assert real_summary.integrity_errors == []
    assert real_summary.authority_report_execution_confirmed is True
    assert real_summary.training_executed is False
    assert real_summary.baseline_eligible_count is None
    assert real_summary.expansion_pct is None
    assert real_summary.ready_for_training is False
    assert real_summary.gate_decision == "BLOCKED_FAIL_CLOSED"
    assert "LEDGER_LEARNING_READY_FALSE" in real_summary.blockers
    assert "COVERAGE_LEARNING_READY_FALSE" in real_summary.blockers


def test_real_eligible_rows_validate_files_rasters_hashes_and_split_policy(real_summary):
    eligible = list(_eligible_records(real_summary))
    assert len(eligible) == 1407
    assert all(patch.is_eligible for patch in eligible)
    assert all(patch.has_image and patch.has_label and patch.has_quality for patch in eligible)
    assert all(patch.band_count == 6 for patch in eligible)
    assert all(patch.raster_contract_valid for patch in eligible)
    assert all(patch.hashes_match is True for patch in eligible)
    assert all(patch.split_policy_valid for patch in eligible)


def test_real_scene_id_cross_split_leakage_is_detected(real_summary):
    conflict = "S2A_MSIL2A_20210812T025551_R032_T48MXT_20210812T132431"
    assert real_summary.scene_split_conflicts == [conflict]
    assert real_summary.footprint_split_conflicts == []
    assert "SCENE_SPLIT_LEAKAGE" in real_summary.blockers
    assert real_summary.splits["train"].spatial_leakage_detected is False
    assert real_summary.splits["val"].spatial_leakage_detected is True
    assert real_summary.splits["test"].spatial_leakage_detected is True
    assert real_summary.splits["val"].leaked_scene_ids == [conflict]
    assert real_summary.splits["test"].leaked_scene_ids == [conflict]


def test_real_required_class_contribution_policy_blocks_training(real_summary):
    assert real_summary.class_coverage_ready is False
    assert "CLASS_COVERAGE_POLICY_FAILED" in real_summary.blockers
    assert "train:8:fraction_below_0.5pct" in real_summary.class_coverage_failures
    assert "train:8:contributors_below_5" in real_summary.class_coverage_failures
    assert "val:8:fraction_below_0.5pct" in real_summary.class_coverage_failures
    assert "val:8:contributors_below_5" in real_summary.class_coverage_failures
    assert "test:8:fraction_below_0.5pct" in real_summary.class_coverage_failures
    assert "test:8:contributors_below_5" in real_summary.class_coverage_failures


def test_synthetic_exact_count_boundary_is_ready_and_one_less_is_blocked(tmp_path: Path):
    ready_root = tmp_path / "ready" / "data"
    _write_authority_fixture(ready_root, train=100, val=10, test=10)
    ready = AIDatasetSplitsManager(ready_root).audit_and_split()
    assert ready.ready_for_training is True
    assert ready.gate_decision == "GATE_PASSED_READY_FOR_TRAINING"
    assert ready.blockers == []
    assert ready.footprint_split_conflicts == []
    ready_delta, ready_status, ready_report = AIDatasetSplitsManager._training_gate_export_copy(
        ready
    )
    assert "readiness gate passed" in ready_delta
    assert ready_status == "RESOLVED_BOTTLENECK"
    assert ready_report == "학습 게이트 통과"

    blocked_root = tmp_path / "blocked" / "data"
    _write_authority_fixture(blocked_root, train=99, val=10, test=10)
    blocked = AIDatasetSplitsManager(blocked_root).audit_and_split()
    assert blocked.ready_for_training is False
    assert blocked.blockers == ["INSUFFICIENT_SPLIT_COUNTS"]
    assert blocked.train_count == 99
    blocked_delta, blocked_status, blocked_report = (
        AIDatasetSplitsManager._training_gate_export_copy(blocked)
    )
    assert "INSUFFICIENT_SPLIT_COUNTS" in blocked_delta
    assert blocked_status == "BLOCKED_BY_READINESS_GATE"
    assert "학습 불능 공백 완전 해소" not in blocked_report
    assert "학습할 수 없음" in blocked_report


@pytest.mark.parametrize("executed_case", ["missing", False, None, 1, "true"])
def test_synthetic_executed_must_be_literal_true(tmp_path: Path, executed_case):
    data_root = tmp_path / "executed" / "data"
    report_path, _ = _write_authority_fixture(data_root, train=100, val=10, test=10)
    report = _read_report(report_path)
    if executed_case == "missing":
        report.pop("executed")
    else:
        report["executed"] = executed_case
    _write_report(report_path, report)

    summary = AIDatasetSplitsManager(data_root).audit_and_split()
    assert summary.ready_for_training is False
    assert summary.blockers == ["AUTHORITY_REPORT_EXECUTION_UNCONFIRMED"]
    assert summary.authority_report_execution_confirmed is (
        False if type(executed_case) is bool else None
    )
    assert summary.training_executed is False


@pytest.mark.parametrize(
    ("metric_name", "mutation"),
    [
        (metric_name, mutation)
        for metric_name in (
            "required_class_pixel_counts",
            "required_class_pixel_fractions",
            "required_class_contributing_patches",
        )
        for mutation in ("missing", "extra", "wrong_type")
    ],
)
def test_synthetic_required_class_maps_require_exact_authoritative_keys_and_shape(
    tmp_path: Path,
    metric_name: str,
    mutation: str,
):
    data_root = tmp_path / f"class-keys-{metric_name}-{mutation}" / "data"
    report_path, _ = _write_authority_fixture(data_root, train=100, val=10, test=10)
    report = _read_report(report_path)
    train_metrics = report["coverage_metrics"][metric_name]["train"]
    if mutation == "missing":
        train_metrics.pop("8")
    elif mutation == "extra":
        train_metrics["3"] = 5
    else:
        report["coverage_metrics"][metric_name]["train"] = []
    _write_report(report_path, report)

    summary = AIDatasetSplitsManager(data_root).audit_and_split()
    assert summary.ready_for_training is False
    assert "LEDGER_INTEGRITY_ERROR" in summary.blockers
    assert "CLASS_COVERAGE_POLICY_FAILED" in summary.blockers
    if mutation == "wrong_type":
        assert "train:missing_required_class_metrics" in summary.class_coverage_failures
    else:
        assert (
            f"train:{metric_name}:required_class_key_mismatch"
            in summary.class_coverage_failures
        )


@pytest.mark.parametrize(
    ("metric_name", "class_id", "bad_value", "expected_failure"),
    [
        ("required_class_pixel_fractions", "8", float("nan"), "train:8:fraction_invalid"),
        ("required_class_pixel_fractions", "8", float("inf"), "train:8:fraction_invalid"),
        ("required_class_pixel_fractions", "8", float("-inf"), "train:8:fraction_invalid"),
        ("required_class_pixel_fractions", "8", True, "train:8:fraction_invalid"),
        ("required_class_pixel_fractions", "8", "0.5", "train:8:fraction_invalid"),
        ("required_class_pixel_fractions", "8", 10**400, "train:8:fraction_invalid"),
        ("dominant_class_fraction", None, float("nan"), "train:dominant_class_fraction_invalid"),
        ("dominant_class_fraction", None, float("inf"), "train:dominant_class_fraction_invalid"),
        ("dominant_class_fraction", None, True, "train:dominant_class_fraction_invalid"),
        ("dominant_class_fraction", None, "0.5", "train:dominant_class_fraction_invalid"),
        (
            "dominant_class_fraction",
            None,
            0.1,
            "train:dominant_class_fraction_below_required_max",
        ),
        ("required_class_pixel_counts", "8", True, "train:8:pixel_count_invalid"),
        ("required_class_pixel_counts", "8", 1.0, "train:8:pixel_count_invalid"),
        ("required_class_pixel_counts", "8", 10**400, "train:8:pixel_count_invalid"),
        ("required_class_contributing_patches", "8", True, "train:8:contributors_invalid"),
        ("required_class_contributing_patches", "8", 5.0, "train:8:contributors_invalid"),
        ("required_class_contributing_patches", "8", float("nan"), "train:8:contributors_invalid"),
    ],
)
def test_synthetic_class_metrics_reject_non_finite_and_wrong_numeric_types(
    tmp_path: Path,
    metric_name: str,
    class_id,
    bad_value,
    expected_failure: str,
):
    data_root = tmp_path / f"numeric-{metric_name}" / "data"
    report_path, _ = _write_authority_fixture(data_root, train=100, val=10, test=10)
    report = _read_report(report_path)
    if class_id is None:
        report["coverage_metrics"][metric_name]["train"] = bad_value
    else:
        report["coverage_metrics"][metric_name]["train"][class_id] = bad_value
    _write_report(report_path, report)

    summary = AIDatasetSplitsManager(data_root).audit_and_split()
    assert summary.ready_for_training is False
    assert "LEDGER_INTEGRITY_ERROR" in summary.blockers
    assert "CLASS_COVERAGE_POLICY_FAILED" in summary.blockers
    assert expected_failure in summary.class_coverage_failures


@pytest.mark.parametrize(
    ("metric_name", "bad_value", "expected_failure"),
    [
        (
            "required_class_contributing_patches",
            101,
            "train:8:contributors_exceed_split_patches",
        ),
        (
            "required_class_pixel_counts",
            1_279,
            "train:8:pixel_count_below_contributor_floor",
        ),
        (
            "required_class_pixel_counts",
            7_000_000,
            "train:8:pixel_count_exceeds_contributor_feasibility",
        ),
        (
            "required_class_pixel_fractions",
            0.2,
            "train:fraction_denominator_mismatch",
        ),
    ],
)
def test_synthetic_class_metrics_reject_cross_field_contradictions(
    tmp_path: Path,
    metric_name: str,
    bad_value,
    expected_failure: str,
):
    data_root = tmp_path / f"cross-field-{metric_name}" / "data"
    report_path, _ = _write_authority_fixture(data_root, train=100, val=10, test=10)
    report = _read_report(report_path)
    report["coverage_metrics"][metric_name]["train"]["8"] = bad_value
    _write_report(report_path, report)

    summary = AIDatasetSplitsManager(data_root).audit_and_split()
    assert summary.ready_for_training is False
    assert "LEDGER_INTEGRITY_ERROR" in summary.blockers
    assert "CLASS_COVERAGE_POLICY_FAILED" in summary.blockers
    assert expected_failure in summary.class_coverage_failures


def test_synthetic_required_fraction_sum_cannot_exceed_one(tmp_path: Path):
    data_root = tmp_path / "fraction-sum" / "data"
    report_path, _ = _write_authority_fixture(data_root, train=100, val=10, test=10)
    report = _read_report(report_path)
    train_fractions = report["coverage_metrics"]["required_class_pixel_fractions"]["train"]
    for class_id in train_fractions:
        train_fractions[class_id] = 0.2
    report["coverage_metrics"]["dominant_class_fraction"]["train"] = 0.2
    _write_report(report_path, report)

    summary = AIDatasetSplitsManager(data_root).audit_and_split()
    assert summary.ready_for_training is False
    assert "LEDGER_INTEGRITY_ERROR" in summary.blockers
    assert "CLASS_COVERAGE_POLICY_FAILED" in summary.blockers
    assert "train:required_fraction_sum_above_1" in summary.class_coverage_failures
    assert "train:required_pixel_counts_exceed_denominator" in summary.class_coverage_failures


def test_synthetic_dominant_can_be_a_non_required_class(tmp_path: Path):
    data_root = tmp_path / "non-required-dominant" / "data"
    class_pixels_per_patch = {
        **{class_id: 6_000 for class_id in REQUIRED_SOURCE_CLASS_CODES},
        "4": 24_000,
    }
    _write_authority_fixture(
        data_root,
        train=100,
        val=10,
        test=10,
        class_pixels_per_patch=class_pixels_per_patch,
    )

    summary = AIDatasetSplitsManager(data_root).audit_and_split()
    assert summary.ready_for_training is True
    assert summary.blockers == []


def test_synthetic_row_class_evidence_must_match_label_and_aggregates(tmp_path: Path):
    data_root = tmp_path / "row-class-evidence" / "data"
    report_path, _ = _write_authority_fixture(data_root, train=100, val=10, test=10)
    report = _read_report(report_path)
    first_row = report["scenes"][0]
    first_row["sample_class_coverage"]["1"] -= 1
    first_row["sample_class_coverage"]["2"] += 1
    _write_report(report_path, report)

    summary = AIDatasetSplitsManager(data_root).audit_and_split()
    assert summary.ready_for_training is False
    assert "LEDGER_INTEGRITY_ERROR" in summary.blockers
    assert any(
        error.endswith(":sample_class_coverage_label_mismatch")
        for error in summary.integrity_errors
    )
    assert (
        "coverage_metrics:required_class_pixel_counts:train:row_evidence_mismatch"
        in summary.integrity_errors
    )


@pytest.mark.parametrize(
    ("mutation", "expected_suffix"),
    [
        ("missing", ":sample_class_coverage_missing_or_invalid"),
        ("unknown_class", ":sample_class_coverage_invalid"),
        ("bool_value", ":sample_class_coverage_invalid"),
        ("zero_only", ":sample_class_coverage_empty"),
    ],
)
def test_synthetic_row_class_evidence_is_strict_and_required(
    tmp_path: Path,
    mutation: str,
    expected_suffix: str,
):
    data_root = tmp_path / f"row-class-evidence-{mutation}" / "data"
    report_path, _ = _write_authority_fixture(data_root, train=101, val=11, test=11)
    report = _read_report(report_path)
    first_row = report["scenes"][0]
    if mutation == "missing":
        first_row.pop("sample_class_coverage")
    elif mutation == "unknown_class":
        first_row["sample_class_coverage"]["3"] = 1
    elif mutation == "bool_value":
        first_row["sample_class_coverage"]["1"] = True
    else:
        first_row["sample_class_coverage"] = {"1": 0}
    _write_report(report_path, report)

    summary = AIDatasetSplitsManager(data_root).audit_and_split()
    assert summary.ready_for_training is False
    assert "LEDGER_INTEGRITY_ERROR" in summary.blockers
    assert any(error.endswith(expected_suffix) for error in summary.integrity_errors)


def test_synthetic_duplicate_physical_patch_is_blocked(tmp_path: Path):
    data_root = tmp_path / "duplicate-physical-patch" / "data"
    report_path, _ = _write_authority_fixture(data_root, train=100, val=10, test=10)
    report = _read_report(report_path)
    first_row, duplicate_row = report["scenes"][:2]
    for field in ("image_path", "label_path", "quality_mask_path", "patch_sha256"):
        duplicate_row[field] = first_row[field]
    _write_report(report_path, report)

    summary = AIDatasetSplitsManager(data_root).audit_and_split()
    assert summary.ready_for_training is False
    assert "LEDGER_INTEGRITY_ERROR" in summary.blockers
    assert any(
        error.endswith(":duplicate_patch_path_tuple")
        for error in summary.integrity_errors
    )
    assert any(
        error.endswith(":duplicate_patch_content_hash_tuple")
        for error in summary.integrity_errors
    )


def test_synthetic_single_role_path_reuse_is_blocked(tmp_path: Path):
    data_root = tmp_path / "single-role-path-reuse" / "data"
    report_path, _ = _write_authority_fixture(data_root, train=100, val=10, test=10)
    report = _read_report(report_path)
    first_row, duplicate_row = report["scenes"][:2]
    duplicate_row["label_path"] = first_row["label_path"]
    duplicate_row["patch_sha256"]["label"] = first_row["patch_sha256"]["label"]
    _write_report(report_path, report)

    summary = AIDatasetSplitsManager(data_root).audit_and_split()
    assert summary.ready_for_training is False
    assert "LEDGER_INTEGRITY_ERROR" in summary.blockers
    assert any(
        error.endswith(":label_path_reused")
        for error in summary.integrity_errors
    )


def test_synthetic_cross_role_physical_path_reuse_is_blocked(tmp_path: Path):
    data_root = tmp_path / "cross-role-path-reuse" / "data"
    report_path, _ = _write_authority_fixture(data_root, train=100, val=10, test=10)
    report = _read_report(report_path)
    first_row, duplicate_row = report["scenes"][:2]
    duplicate_row["quality_mask_path"] = first_row["label_path"]
    duplicate_row["patch_sha256"]["quality"] = first_row["patch_sha256"]["label"]
    _write_report(report_path, report)

    summary = AIDatasetSplitsManager(data_root).audit_and_split()
    assert summary.ready_for_training is False
    assert "LEDGER_INTEGRITY_ERROR" in summary.blockers
    assert any(
        error.endswith(":physical_path_reused_across_rows_or_roles")
        for error in summary.integrity_errors
    )


def test_synthetic_cross_split_raster_footprint_overlap_is_blocked(tmp_path: Path):
    data_root = tmp_path / "cross-split-footprint" / "data"
    _write_authority_fixture(
        data_root,
        train=100,
        val=10,
        test=10,
        overlapped_footprint=True,
    )

    summary = AIDatasetSplitsManager(data_root).audit_and_split()
    assert summary.ready_for_training is False
    assert "RASTER_FOOTPRINT_SPLIT_LEAKAGE" in summary.blockers
    assert summary.footprint_split_conflicts == ["patch-train-0|patch-val-0"]
    assert summary.splits["train"].spatial_leakage_detected is True
    assert summary.splits["val"].spatial_leakage_detected is True
    assert summary.splits["test"].spatial_leakage_detected is False


def test_synthetic_reencoded_duplicate_normalized_payload_is_blocked(tmp_path: Path):
    data_root = tmp_path / "normalized-payload-duplicate" / "data"
    report_path, _ = _write_authority_fixture(data_root, train=100, val=10, test=10)
    report = _read_report(report_path)
    first_row, duplicate_row = report["scenes"][:2]
    with rasterio.open(first_row["image_path"]) as first_image:
        first_values = first_image.read()
    with rasterio.open(duplicate_row["quality_mask_path"]) as quality:
        duplicate_valid_mask = quality.read(1) == 1
    first_values[:, ~duplicate_valid_mask] = 777.0
    with rasterio.open(duplicate_row["image_path"], "r+") as duplicate_image:
        duplicate_image.write(first_values)
    duplicate_row["patch_sha256"]["image"] = _sha256(
        Path(duplicate_row["image_path"])
    )
    _write_report(report_path, report)

    summary = AIDatasetSplitsManager(data_root).audit_and_split()
    assert summary.ready_for_training is False
    assert "LEDGER_INTEGRITY_ERROR" in summary.blockers
    assert any(
        error.endswith(":duplicate_normalized_training_payload")
        for error in summary.integrity_errors
    )


def test_synthetic_quality_mask_content_is_verified(tmp_path: Path):
    data_root = tmp_path / "invalid-quality-content" / "data"
    report_path, paths = _write_authority_fixture(data_root, train=100, val=10, test=10)
    with rasterio.open(paths["quality"], "r+") as dataset:
        values = dataset.read(1)
        values[0, 0] = 255
        dataset.write(values, 1)
    report = _read_report(report_path)
    quality_sha256 = _sha256(paths["quality"])
    report["scenes"][0]["patch_sha256"]["quality"] = quality_sha256
    _write_report(report_path, report)

    summary = AIDatasetSplitsManager(data_root).audit_and_split()
    assert summary.ready_for_training is False
    assert "LEDGER_INTEGRITY_ERROR" in summary.blockers
    assert any(
        error.endswith(":quality_mask_values_invalid")
        for error in summary.integrity_errors
    )
    assert any(
        error.endswith(":label_quality_mask_mismatch")
        for error in summary.integrity_errors
    )


def test_synthetic_image_valid_pixels_must_be_finite_and_nonzero(tmp_path: Path):
    data_root = tmp_path / "invalid-image-content" / "data"
    report_path, paths = _write_authority_fixture(data_root, train=100, val=10, test=10)
    with rasterio.open(paths["image"], "r+") as dataset:
        values = dataset.read()
        values[:, 0, 0] = 0.0
        dataset.write(values)
    report = _read_report(report_path)
    report["scenes"][0]["patch_sha256"]["image"] = _sha256(paths["image"])
    _write_report(report_path, report)

    summary = AIDatasetSplitsManager(data_root).audit_and_split()
    assert summary.ready_for_training is False
    assert "LEDGER_INTEGRITY_ERROR" in summary.blockers
    assert any(
        error.endswith(":image_valid_pixels_invalid")
        for error in summary.integrity_errors
    )


def test_synthetic_valid_tiff_content_tampering_is_detected_by_sha256(tmp_path: Path):
    data_root = tmp_path / "tampered" / "data"
    _, paths = _write_authority_fixture(data_root, train=100, val=10, test=10)
    with rasterio.open(paths["image"], "r+") as dataset:
        one_pixel = dataset.read(1, window=Window(0, 0, 1, 1))
        one_pixel[0, 0] = 0.5
        dataset.write(one_pixel, 1, window=Window(0, 0, 1, 1))

    summary = AIDatasetSplitsManager(data_root).audit_and_split()
    assert summary.ready_for_training is False
    assert "LEDGER_INTEGRITY_ERROR" in summary.blockers
    assert any(error.endswith(":image_sha256_mismatch") for error in summary.integrity_errors)
    assert all(patch.band_count == 6 for patch in _eligible_records(summary))
    assert all(patch.raster_contract_valid for patch in _eligible_records(summary))
    records = {patch.patch_id: patch for patch in _eligible_records(summary)}
    assert records["patch-train-0"].hashes_match is False
    assert all(
        patch.hashes_match is True
        for patch_id, patch in records.items()
        if patch_id != "patch-train-0"
    )


def test_synthetic_scene_cross_split_is_computed_instead_of_assumed_false(tmp_path: Path):
    data_root = tmp_path / "leakage" / "data"
    _write_authority_fixture(data_root, train=100, val=10, test=10, leaked_scene=True)
    summary = AIDatasetSplitsManager(data_root).audit_and_split()
    assert summary.ready_for_training is False
    assert summary.scene_split_conflicts == ["scene-cross-split"]
    assert summary.blockers == ["SCENE_SPLIT_LEAKAGE"]


def test_synthetic_split_policy_tampering_is_fail_closed(tmp_path: Path):
    data_root = tmp_path / "split-policy" / "data"
    report_path, _ = _write_authority_fixture(data_root, train=100, val=10, test=10)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    val_row = next(row for row in report["scenes"] if row["province"] == "banten")
    val_row["split"] = "train"
    report_path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")

    summary = AIDatasetSplitsManager(data_root).audit_and_split()
    assert summary.ready_for_training is False
    assert "LEDGER_INTEGRITY_ERROR" in summary.blockers
    assert any(error.endswith(":split_policy_mismatch") for error in summary.integrity_errors)
    changed = next(patch for patch in summary.patches if patch.patch_id == val_row["patch_id"])
    assert changed.split_policy_valid is False
    assert changed.is_eligible is False
