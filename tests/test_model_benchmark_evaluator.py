"""Unit & Integration Tests for G8-G9 Model Retraining & Same-Holdout Benchmark Evaluator."""
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
    assert summary.total_test_patches == 264

    exp_ids = [e.experiment_id for e in summary.experiments]
    assert exp_ids == ["EXP-A", "EXP-B", "EXP-C", "EXP-D"]


def test_best_challenger_improvement(evaluator: ModelBenchmarkEvaluator):
    summary = evaluator.evaluate_all()
    best = next(e for e in summary.experiments if e.is_best_model)
    assert best.experiment_id == "EXP-D"
    assert best.overall_accuracy > 0.85
    assert best.macro_f1 > 0.80
    assert best.miou > 0.80

    # Verify gains over baseline
    baseline = summary.experiments[0]
    assert best.overall_accuracy > baseline.overall_accuracy
    assert best.f1_improvement_pct_point > 30.0  # +30%p or more
    assert best.f1_relative_gain_pct > 50.0      # +50% or more


def test_per_class_metrics_coverage(evaluator: ModelBenchmarkEvaluator):
    summary = evaluator.evaluate_all()
    best = summary.experiments[3]
    assert len(best.per_class_metrics) == 9

    # Verify Trees and Built Area have strong performance
    trees_metric = next(m for m in best.per_class_metrics if m.class_id == 1)
    assert trees_metric.f1_score >= 0.85
    built_metric = next(m for m in best.per_class_metrics if m.class_id == 6)
    assert built_metric.f1_score >= 0.80


def test_deliverables_export(evaluator: ModelBenchmarkEvaluator, tmp_path: Path):
    manifest_f, csv_f, conf_f, card_f, gov_f = evaluator.export_deliverables(tmp_path)
    assert manifest_f.is_file() and manifest_f.stat().st_size > 1000
    assert csv_f.is_file() and csv_f.stat().st_size > 200
    assert conf_f.is_file() and conf_f.stat().st_size > 500
    assert card_f.is_file() and card_f.stat().st_size > 500
    assert gov_f.is_file() and gov_f.stat().st_size > 500
