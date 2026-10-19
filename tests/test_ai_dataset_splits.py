"""Unit & Integration Tests for G7 AI Dataset Splits & Training Readiness Gate."""
from pathlib import Path
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(PROJECT_ROOT / "backend")]

from app.ml.ai_dataset_splits_manager import (
    AIDatasetSplitsManager,
    PROVINCE_SPLIT_MAP,
)


@pytest.fixture(scope="module")
def data_root() -> Path:
    return PROJECT_ROOT / "data"


@pytest.fixture(scope="module")
def splits_manager(data_root: Path) -> AIDatasetSplitsManager:
    return AIDatasetSplitsManager(data_root)


def test_geographic_holdout_policy():
    assert PROVINCE_SPLIT_MAP["banten"] == "val"
    assert PROVINCE_SPLIT_MAP["west_java"] == "test"
    assert PROVINCE_SPLIT_MAP["east_java"] == "train"
    assert PROVINCE_SPLIT_MAP["south_sulawesi"] == "train"
    assert PROVINCE_SPLIT_MAP["gorontalo"] == "train"
    assert PROVINCE_SPLIT_MAP["southeast_sulawesi"] == "train"


def test_splits_audit_readiness(splits_manager: AIDatasetSplitsManager):
    summary = splits_manager.audit_and_split()
    assert summary.ready_for_training is True
    assert summary.gate_decision == "GATE_PASSED_READY_FOR_TRAINING"
    assert summary.train_count >= 100
    assert summary.val_count >= 10
    assert summary.test_count >= 10
    assert summary.baseline_eligible_count == 2
    assert summary.expansion_pct > 1000.0  # Over 10x expansion


def test_zero_spatial_leakage(splits_manager: AIDatasetSplitsManager):
    summary = splits_manager.audit_and_split()
    train_provs = set(summary.splits["train"].provinces)
    val_provs = set(summary.splits["val"].provinces)
    test_provs = set(summary.splits["test"].provinces)

    # Disjoint province assignment
    assert train_provs.isdisjoint(val_provs)
    assert train_provs.isdisjoint(test_provs)
    assert val_provs.isdisjoint(test_provs)


def test_deliverables_export(splits_manager: AIDatasetSplitsManager, tmp_path: Path):
    manifest_f, csv_f, report_f = splits_manager.export_deliverables(tmp_path)
    assert manifest_f.is_file() and manifest_f.stat().st_size > 500
    assert csv_f.is_file() and csv_f.stat().st_size > 100
    assert report_f.is_file() and report_f.stat().st_size > 500
