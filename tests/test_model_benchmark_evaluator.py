"""Fail-closed tests for the G8-G9 deterministic scenario fixture."""
from pathlib import Path
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(PROJECT_ROOT / "backend")]

from app.ml.model_benchmark_evaluator import ModelBenchmarkEvaluator, CLASS_NAMES


@pytest.fixture(scope="module")
def evaluator() -> ModelBenchmarkEvaluator:
    return ModelBenchmarkEvaluator(PROJECT_ROOT / "data")


def test_evaluator_2x2_matrix(evaluator: ModelBenchmarkEvaluator):
    summary = evaluator.evaluate_all()
    assert len(summary.experiments) == 4
    assert summary.test_holdout_province == "west_java"
    assert summary.total_test_patches == 0
    assert summary.total_test_pixels == 0
    assert summary.scenario_test_patches == 264
    assert summary.evidence_status == "TESTED_SYNTHETIC"
    assert summary.metrics_origin == "DETERMINISTIC_SCENARIO_FIXTURE"

    exp_ids = [e.experiment_id for e in summary.experiments]
    assert exp_ids == ["EXP-A", "EXP-B", "EXP-C", "EXP-D"]


def test_scenario_cannot_select_or_promote_a_model(evaluator: ModelBenchmarkEvaluator):
    summary = evaluator.evaluate_all()
    assert summary.best_experiment_id is None
    assert summary.scenario_reference_experiment_id == "EXP-D"
    assert summary.promotion_target is None
    assert summary.rollback_target is None
    assert summary.promotion_authorized is False
    assert summary.scientific_accuracy_validated is False
    assert summary.training_executed is False
    assert summary.prediction_artifacts_verified is False
    assert summary.holdout_independence_verified is False
    assert summary.gate_promotion_decision.startswith("BLOCKED_")
    assert "SOURCE_SCENE_SPLIT_CONFLICT_PRESENT" in summary.blocking_reasons
    assert "DATASET_LEARNING_READY_FALSE" in summary.blocking_reasons
    assert not any(e.is_best_model for e in summary.experiments)
    assert all(e.status == "SYNTHETIC_SCENARIO_ONLY" for e in summary.experiments)
    assert all(e.promotion_eligible is False for e in summary.experiments)


def test_scenario_values_are_explicitly_provenanced(evaluator: ModelBenchmarkEvaluator):
    summary = evaluator.evaluate_all()
    scenario = summary.experiments[3]
    assert len(scenario.per_class_metrics) == len(CLASS_NAMES) == 9
    assert scenario.is_scenario_reference is True
    assert scenario.evidence_status == "TESTED_SYNTHETIC"
    assert scenario.metrics_origin == "DETERMINISTIC_SCENARIO_FIXTURE"
    assert scenario.training_executed is False
    assert scenario.prediction_artifacts_verified is False
    assert scenario.scientific_accuracy_validated is False


def test_deliverables_export(evaluator: ModelBenchmarkEvaluator, tmp_path: Path):
    manifest_f, csv_f, conf_f, card_f, gov_f = evaluator.export_deliverables(tmp_path)
    assert manifest_f.is_file() and manifest_f.stat().st_size > 1000
    assert csv_f.is_file() and csv_f.stat().st_size > 200
    assert conf_f.is_file() and conf_f.stat().st_size > 500
    assert card_f.is_file() and card_f.stat().st_size > 500
    assert gov_f.is_file() and gov_f.stat().st_size > 500

    manifest = manifest_f.read_text(encoding="utf-8")
    csv_text = csv_f.read_text(encoding="utf-8")
    conf_text = conf_f.read_text(encoding="utf-8")
    card_text = card_f.read_text(encoding="utf-8")
    gov_text = gov_f.read_text(encoding="utf-8")
    combined = "\n".join([manifest, csv_text, conf_text, card_text, gov_text])

    assert "TESTED_SYNTHETIC" in combined
    assert "DETERMINISTIC_SCENARIO_FIXTURE" in combined
    assert "BLOCKED_NO_EXECUTED_TRAINING_OR_MEASURED_PREDICTIONS" in combined
    assert "Scenario assumption: 1,179 training patches" in manifest
    assert "scenario; independence unverified" in manifest
    assert "시나리오 모델 / 가정 학습량" in conf_text
    assert "1,779행 중 품질 적격 1,407행" in card_text
    assert "source class 8" in card_text
    assert "`learning_ready` | `false`" in gov_text
    assert "PROMOTED_TO_PRODUCTION" not in combined
    assert "PRODUCTION_APPROVED" not in combined
    assert "KLHK 국가 토지피복 심의관" not in combined
