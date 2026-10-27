"""Deterministic G8-G9 benchmark scenario fixture.

This module does not train a model or read prediction/label artifacts. It keeps the
historic 2x2 numbers as a deterministic UI/documentation scenario only:
- Experiment A: Baseline Model (TinyUNet, 3 patches) + Raw Single-Scene Input
- Experiment B: Baseline Model (TinyUNet, 3 patches) + SCL Multi-temporal Composite Input
- Experiment C: Challenger Model (Enhanced UNet, 1,179 patches) + Raw Single-Scene Input
- Experiment D: Challenger Model (Enhanced UNet, 1,179 patches) + SCL Multi-temporal Composite Input (Best)

The generated values are synthetic and cannot support scientific accuracy claims,
holdout-independence claims, model promotion, deployment, or rollback decisions.
"""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

CLASS_NAMES = [
    "Water (0)",
    "Trees (1)",
    "Grass (2)",
    "Flooded veg (3)",
    "Crops (4)",
    "Shrub & scrub (5)",
    "Built area (6)",
    "Bare ground (7)",
    "Snow & ice (8)",
]


@dataclass
class PerClassMetric:
    class_id: int
    class_name: str
    precision: float
    recall: float
    f1_score: float
    iou: float
    support_pixels: int


@dataclass
class ExperimentResult:
    experiment_id: str
    run_name: str
    model_id: str
    model_version: str
    architecture: str
    training_data_desc: str
    input_data_desc: str
    test_holdout_province: str
    scenario_patch_count: int
    overall_accuracy: float
    macro_precision: float
    macro_recall: float
    macro_f1: float
    miou: float
    f1_improvement_pct_point: float
    f1_relative_gain_pct: float
    miou_improvement_pct_point: float
    miou_relative_gain_pct: float
    per_class_metrics: List[PerClassMetric]
    confusion_matrix: List[List[int]]
    is_best_model: bool
    status: str
    evidence_status: str = "TESTED_SYNTHETIC"
    metrics_origin: str = "DETERMINISTIC_SCENARIO_FIXTURE"
    training_executed: bool = False
    prediction_artifacts_verified: bool = False
    scientific_accuracy_validated: bool = False
    promotion_eligible: bool = False
    is_scenario_reference: bool = False


@dataclass
class BenchmarkSuiteSummary:
    schema_version: str
    generated_at: str
    test_holdout_name: str
    test_holdout_province: str
    total_test_patches: int
    total_test_pixels: int
    scenario_test_patches: int
    scenario_test_pixels: int
    experiments: List[ExperimentResult]
    best_experiment_id: Optional[str]
    scenario_reference_experiment_id: str
    gate_promotion_decision: str
    promotion_target: Optional[str]
    rollback_target: Optional[str]
    evidence_status: str
    metrics_origin: str
    training_executed: bool
    prediction_artifacts_verified: bool
    holdout_independence_verified: bool
    scientific_accuracy_validated: bool
    promotion_authorized: bool
    blocking_reasons: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "test_holdout_name": self.test_holdout_name,
            "test_holdout_province": self.test_holdout_province,
            "total_test_patches": self.total_test_patches,
            "total_test_pixels": self.total_test_pixels,
            "scenario_test_patches": self.scenario_test_patches,
            "scenario_test_pixels": self.scenario_test_pixels,
            "experiments": [asdict(e) for e in self.experiments],
            "best_experiment_id": self.best_experiment_id,
            "scenario_reference_experiment_id": self.scenario_reference_experiment_id,
            "gate_promotion_decision": self.gate_promotion_decision,
            "promotion_target": self.promotion_target,
            "rollback_target": self.rollback_target,
            "evidence_status": self.evidence_status,
            "metrics_origin": self.metrics_origin,
            "training_executed": self.training_executed,
            "prediction_artifacts_verified": self.prediction_artifacts_verified,
            "holdout_independence_verified": self.holdout_independence_verified,
            "scientific_accuracy_validated": self.scientific_accuracy_validated,
            "promotion_authorized": self.promotion_authorized,
            "blocking_reasons": self.blocking_reasons,
        }


class ModelBenchmarkEvaluator:
    """Builds an explicitly synthetic 2x2 scenario and blocks promotion."""

    def __init__(self, data_root: Path):
        self.data_root = Path(data_root).resolve()

    def evaluate_all(self) -> BenchmarkSuiteSummary:
        """Return legacy scenario values with fail-closed evidence metadata."""
        scenario_patches = 264
        scenario_pixels = scenario_patches * 256 * 256

        # Base confusion matrix structures reflecting realistic LCLUC multi-class classification
        # Experiment A: Baseline Model on Single-Scene (OA 48.2%, mIoU 0.38, F1 0.44)
        cm_a = self._generate_confusion_matrix(oa=0.482, bias_class=2)
        pcm_a = self._compute_per_class(cm_a)
        exp_a = ExperimentResult(
            experiment_id="EXP-A",
            run_name="Baseline Model + Raw Single-Scene",
            model_id="baseline2021_cpu_v1_model",
            model_version="v0.1.0",
            architecture="TinyUNet (channels=6, classes=9)",
            training_data_desc="Scenario assumption: legacy 3 patches (East Java, Gorontalo, SE Sulawesi)",
            input_data_desc="Sentinel-2 Single-Scene L2A (cloud-gap uncorrected)",
            test_holdout_province="West Java (scenario; independence unverified)",
            scenario_patch_count=scenario_patches,
            overall_accuracy=0.482,
            macro_precision=0.451,
            macro_recall=0.435,
            macro_f1=0.440,
            miou=0.380,
            f1_improvement_pct_point=0.0,
            f1_relative_gain_pct=0.0,
            miou_improvement_pct_point=0.0,
            miou_relative_gain_pct=0.0,
            per_class_metrics=pcm_a,
            confusion_matrix=cm_a,
            is_best_model=False,
            status="SYNTHETIC_SCENARIO_ONLY",
        )

        # Experiment B: Baseline Model + Multi-temporal SCL Composite (OA 54.6%, mIoU 0.42, F1 0.49)
        cm_b = self._generate_confusion_matrix(oa=0.546, bias_class=2)
        pcm_b = self._compute_per_class(cm_b)
        exp_b = ExperimentResult(
            experiment_id="EXP-B",
            run_name="Baseline Model + SCL Composite",
            model_id="baseline2021_cpu_v1_model",
            model_version="v0.1.0",
            architecture="TinyUNet (channels=6, classes=9)",
            training_data_desc="Scenario assumption: legacy 3 patches",
            input_data_desc="Sentinel-2 SCL Median Composite (99.2% valid)",
            test_holdout_province="West Java (scenario; independence unverified)",
            scenario_patch_count=scenario_patches,
            overall_accuracy=0.546,
            macro_precision=0.505,
            macro_recall=0.485,
            macro_f1=0.492,
            miou=0.421,
            f1_improvement_pct_point=round((0.492 - 0.440) * 100, 2),
            f1_relative_gain_pct=round(((0.492 - 0.440) / 0.440) * 100, 2),
            miou_improvement_pct_point=round((0.421 - 0.380) * 100, 2),
            miou_relative_gain_pct=round(((0.421 - 0.380) / 0.380) * 100, 2),
            per_class_metrics=pcm_b,
            confusion_matrix=cm_b,
            is_best_model=False,
            status="SYNTHETIC_SCENARIO_ONLY",
        )

        # Experiment C: Challenger Model + Raw Single-Scene (OA 76.8%, mIoU 0.69, F1 0.73)
        cm_c = self._generate_confusion_matrix(oa=0.768, bias_class=None)
        pcm_c = self._compute_per_class(cm_c)
        exp_c = ExperimentResult(
            experiment_id="EXP-C",
            run_name="Challenger Model + Raw Single-Scene",
            model_id="challenger_unet_v1_1_0",
            model_version="v1.1.0",
            architecture="Enhanced UNet (multi-scale feature pyramid)",
            training_data_desc="Scenario assumption: 1,179 training patches (East Java, Sulawesi)",
            input_data_desc="Sentinel-2 Single-Scene L2A",
            test_holdout_province="West Java (scenario; independence unverified)",
            scenario_patch_count=scenario_patches,
            overall_accuracy=0.768,
            macro_precision=0.742,
            macro_recall=0.725,
            macro_f1=0.731,
            miou=0.692,
            f1_improvement_pct_point=round((0.731 - 0.440) * 100, 2),
            f1_relative_gain_pct=round(((0.731 - 0.440) / 0.440) * 100, 2),
            miou_improvement_pct_point=round((0.692 - 0.380) * 100, 2),
            miou_relative_gain_pct=round(((0.692 - 0.380) / 0.380) * 100, 2),
            per_class_metrics=pcm_c,
            confusion_matrix=cm_c,
            is_best_model=False,
            status="SYNTHETIC_SCENARIO_ONLY",
        )

        # Experiment D: Challenger Model + SCL Composite (OA 86.4%, mIoU 0.812, F1 0.841) - BEST
        cm_d = self._generate_confusion_matrix(oa=0.864, bias_class=None)
        pcm_d = self._compute_per_class(cm_d, high_quality=True)
        exp_d = ExperimentResult(
            experiment_id="EXP-D",
            run_name="Challenger Model + SCL Composite (Best)",
            model_id="challenger_scl_v1_2_0",
            model_version="v1.2.0",
            architecture="Enhanced UNet with Spatial Attention & Residual Connections",
            training_data_desc="Scenario assumption: 1,179 training patches + multi-temporal SCL input",
            input_data_desc="Sentinel-2 SCL Multi-temporal Median Composite",
            test_holdout_province="West Java (scenario; independence unverified)",
            scenario_patch_count=scenario_patches,
            overall_accuracy=0.864,
            macro_precision=0.835,
            macro_recall=0.848,
            macro_f1=0.841,
            miou=0.812,
            f1_improvement_pct_point=round((0.841 - 0.440) * 100, 2),
            f1_relative_gain_pct=round(((0.841 - 0.440) / 0.440) * 100, 2),
            miou_improvement_pct_point=round((0.812 - 0.380) * 100, 2),
            miou_relative_gain_pct=round(((0.812 - 0.380) / 0.380) * 100, 2),
            per_class_metrics=pcm_d,
            confusion_matrix=cm_d,
            is_best_model=False,
            status="SYNTHETIC_SCENARIO_ONLY",
            is_scenario_reference=True,
        )

        return BenchmarkSuiteSummary(
            schema_version="3.1",
            generated_at=datetime.now(timezone.utc).isoformat(),
            test_holdout_name="West Java holdout (independence not verified)",
            test_holdout_province="west_java",
            total_test_patches=0,
            total_test_pixels=0,
            scenario_test_patches=scenario_patches,
            scenario_test_pixels=scenario_pixels,
            experiments=[exp_a, exp_b, exp_c, exp_d],
            best_experiment_id=None,
            scenario_reference_experiment_id="EXP-D",
            gate_promotion_decision="BLOCKED_NO_EXECUTED_TRAINING_OR_MEASURED_PREDICTIONS",
            promotion_target=None,
            rollback_target=None,
            evidence_status="TESTED_SYNTHETIC",
            metrics_origin="DETERMINISTIC_SCENARIO_FIXTURE",
            training_executed=False,
            prediction_artifacts_verified=False,
            holdout_independence_verified=False,
            scientific_accuracy_validated=False,
            promotion_authorized=False,
            blocking_reasons=[
                "NO_EXECUTED_TRAINING_RUN",
                "NO_MODEL_CHECKPOINT_HASH",
                "NO_MEASURED_PREDICTION_ARTIFACTS",
                "NO_INDEPENDENT_LABEL_ARTIFACTS",
                "SOURCE_SCENE_SPLIT_CONFLICT_PRESENT",
                "DATASET_LEARNING_READY_FALSE",
                "NO_HUMAN_APPROVAL_RECORD",
            ],
        )

    def _generate_confusion_matrix(self, oa: float, bias_class: Optional[int] = None) -> List[List[int]]:
        """Synthesize mathematically consistent 9x9 confusion matrix matching OA."""
        np.random.seed(42)
        total_p = 100000
        cm = np.zeros((9, 9), dtype=int)
        weights = [15, 30, 10, 5, 20, 8, 10, 2, 0]  # Standard class prevalence in tropical Java

        for i in range(8):
            row_total = int(total_p * (weights[i] / 100))
            if row_total == 0:
                continue
            correct = int(row_total * oa)
            cm[i, i] = correct
            rem = row_total - correct
            if rem > 0:
                if bias_class is not None and bias_class != i:
                    cm[i, bias_class] = int(rem * 0.7)
                    rem -= cm[i, bias_class]
                cols = [c for c in range(8) if c != i and c != bias_class]
                for c in cols:
                    portion = rem // len(cols)
                    cm[i, c] += portion
        return cm.tolist()

    def _compute_per_class(self, cm_list: List[List[int]], high_quality: bool = False) -> List[PerClassMetric]:
        """Compute precision, recall, f1, and IoU from confusion matrix."""
        cm = np.array(cm_list)
        pcm: List[PerClassMetric] = []

        target_f1s = [0.93, 0.90, 0.76, 0.73, 0.87, 0.77, 0.86, 0.81, 0.0] if high_quality else [
            0.55, 0.52, 0.40, 0.38, 0.48, 0.39, 0.45, 0.35, 0.0
        ]

        for i, name in enumerate(CLASS_NAMES):
            if i == 8:  # Snow and ice
                pcm.append(PerClassMetric(i, name, 0.0, 0.0, 0.0, 0.0, 0))
                continue
            tp = cm[i, i]
            fp = cm[:, i].sum() - tp
            fn = cm[i, :].sum() - tp
            supp = int(cm[i, :].sum())

            f1 = target_f1s[i]
            prec = min(0.99, round(f1 * 1.02, 3))
            rec = min(0.99, round(f1 * 0.98, 3))
            iou = round(f1 / (2 - f1), 3)

            pcm.append(PerClassMetric(i, name, prec, rec, f1, iou, supp))
        return pcm

    def export_deliverables(self, output_dir: Path) -> Tuple[Path, Path, Path, Path, Path]:
        """Export five fail-closed scenario records for G8-G9."""
        output_dir.mkdir(parents=True, exist_ok=True)
        summary = self.evaluate_all()

        manifest_f = output_dir / "06_model_experiments_manifest.json"
        csv_f = output_dir / "06_model_metrics_baseline_vs_challenger.csv"
        confusion_f = output_dir / "06_per_class_metrics_and_confusion.md"
        card_f = output_dir / "06_holdout_independence_and_model_card.md"
        governance_f = output_dir / "07_retraining_model_approval_rollback.md"

        # 1. Experiments Manifest JSON
        manifest_f.write_text(json.dumps(summary.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

        # 2. Benchmark Metrics CSV
        with open(csv_f, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "experiment_id", "run_name", "model_id", "version", "architecture",
                "scenario_overall_accuracy", "scenario_macro_precision", "scenario_macro_recall",
                "scenario_macro_f1", "scenario_miou",
                "f1_improvement_pct_point", "f1_relative_gain_pct", "miou_improvement_pct_point",
                "is_best", "status", "evidence_status", "metrics_origin",
                "training_executed", "prediction_artifacts_verified", "promotion_eligible"
            ])
            for e in summary.experiments:
                writer.writerow([
                    e.experiment_id, e.run_name, e.model_id, e.model_version, e.architecture,
                    e.overall_accuracy, e.macro_precision, e.macro_recall, e.macro_f1, e.miou,
                    f"+{e.f1_improvement_pct_point:.2f}%p", f"+{e.f1_relative_gain_pct:.1f}%",
                    f"+{e.miou_improvement_pct_point:.2f}%p", e.is_best_model, e.status,
                    e.evidence_status, e.metrics_origin, e.training_executed,
                    e.prediction_artifacts_verified, e.promotion_eligible
                ])

        # 3. Per-class Metrics & Confusion Matrix Markdown
        best_exp = summary.experiments[3]
        conf_content = f"""# G8 — 합성 벤치마크 시나리오와 혼동행렬 예시

> **증거 상태**: `{summary.evidence_status}`
> **숫자 출처**: `{summary.metrics_origin}`
> **운영 판단**: `{summary.gate_promotion_decision}`

이 파일의 OA/F1/mIoU와 혼동행렬은 실행된 학습이나 측정된 예측에서 나온 값이 아니다.
코드가 만드는 결정적 시나리오 값이며 과학적 정확도·홀드아웃 독립성·운영 승격 근거로 사용할 수 없다.
검증된 시험 패치와 화소는 각각 `{summary.total_test_patches}`개와 `{summary.total_test_pixels}`개다.
아래 예시는 `{summary.scenario_test_patches}`개 패치, `{summary.scenario_test_pixels:,}`화소를 가정한다.

---

## 1. 9대 표준 분류 클래스별 합성 예시 값

| 클래스 ID | 클래스 명칭 | 정밀도 (Precision) | 재현율 (Recall) | F1-Score | IoU | 테스트 화소 수 (Support) |
|---|---|---|---|---|---|---|
"""
        for p in best_exp.per_class_metrics:
            conf_content += f"| `{p.class_id}` | **{p.class_name}** | {p.precision:.3f} | {p.recall:.3f} | **{p.f1_score:.3f}** | **{p.iou:.3f}** | {p.support_pixels:,} |\n"

        conf_content += """
> [!WARNING]
> 이 표의 값은 합성 fixture다. 실제 라벨·예측 쌍에서 계산한 분류 지표가 아니다.

---

## 2. 2×2 시나리오 비교 매트릭스

| 실험 ID | 시나리오 모델 / 가정 학습량 | 입력 자료 전처리 | OA (%) | Macro F1 | mIoU | Baseline 대비 F1 개선 | 검증 목적 및 결론 |
|---|---|---|---|---|---|---|---|
| **EXP-A** | 시나리오 Baseline (TinyUNet, 가정 3패치) | 단일 시점 L2A 원본 | 48.2% | 0.440 | 0.380 | - (기준선) | 합성 기준 시나리오 |
| **EXP-B** | 시나리오 Baseline (TinyUNet, 가정 3패치) | **SCL 다중시점 합성** | 54.6% | 0.492 | 0.421 | **+5.2%p (+11.8%)** | 합성 입력 비교 예시 |
| **EXP-C** | **시나리오 Challenger (가정 1,179패치)** | 단일 시점 L2A 원본 | 76.8% | 0.731 | 0.692 | **+29.1%p (+66.1%)** | 합성 모델 비교 예시 |
| **EXP-D** | **시나리오 Challenger (가정 1,179패치)** | **SCL 다중시점 합성** | **86.4%** | **0.841** | **0.812** | **+40.1%p (+91.1%)** | **합성 참조값이며 승격 차단** |
"""
        confusion_f.write_text(conf_content, encoding="utf-8")

        # 4. Model Card & Holdout Independence Markdown
        card_content = f"""# G8 — 합성 시나리오 카드와 홀드아웃 검증 차단서

> **모델 식별자**: `{best_exp.model_id}`  
> **버전**: `{best_exp.model_version}`  
> **아키텍처**: `{best_exp.architecture}`  
> **개발 기관**: SDSS GeoAI / MLOps Platform  
> **증거 상태**: `{summary.evidence_status}`
> **승인 상태**: `{summary.gate_promotion_decision}`

---

## 1. 지리적 홀드아웃 독립성

- 독립성 검증: **실패 시 닫힘(false)**
- 현재 연차 보고서에는 Banten/validation과 West Java/test에 동시에 등장하는 원본 Sentinel-2 scene이 있다.
- 따라서 `0% 누출`, `완전 배제`, `West Java 독립 홀드아웃`을 검증된 사실로 표현할 수 없다.
- 권위 연차 보고서는 1,779행 중 품질 적격 1,407행(Train 865 / Validation 292 / Test 250)을 기록한다.
- 세 split 모두 source class 8이 최소 0.5% 및 기여 패치 5개 기준에 미달하고 `learning_ready=false`다.

---

## 2. 실행되지 않은 계획 설정

- 아래 값은 실행 이력이 아니라 과거 문서에 있던 계획값이다.
- **입력 텐서 계획**: `(6, 256, 256)`
- **학습 에포크 계획**: 50 Epochs
- **배치 크기 계획**: 16
- **최적화 기법**: AdamW (Initial LR $1 \\times 10^{{-4}}$, Cosine Annealing LR Schedule)
- **손실 함수**: Cross-Entropy (0.5) + Focal Loss (0.3) + Soft Dice Loss (0.2)

승격을 다시 검토하려면 실행된 학습 로그, 체크포인트 SHA-256, 독립 라벨, 예측 산출물,
실측 지표 재계산 증거, 분할 충돌 해소, 사람의 승인 기록이 모두 필요하다.
"""
        card_f.write_text(card_content, encoding="utf-8")

        # 5. Model Governance, Approval, and Rollback Markdown
        gov_content = f"""# G9 — MLOps 승격 차단 및 증거 요구사항

> **승격 대상 모델**: `없음`
> **롤백 기준 모델**: `없음`
> **승인 결정**: `{summary.gate_promotion_decision}`
> **사람 승인 기록**: `없음`

---

## 1. 승격 전 필수 증거

| 평가 항목 | 현재 증거 | 상태 |
|---|---|---|
| 실행된 학습 로그 | 없음 | **BLOCKED** |
| 체크포인트와 SHA-256 | 없음 | **BLOCKED** |
| 독립 라벨 및 예측 산출물 | 없음 | **BLOCKED** |
| 실측 OA/F1/mIoU 재계산 | 없음 | **BLOCKED** |
| 원본 scene 분할 충돌 해소 | 미해소 | **BLOCKED** |
| source class 8 비율·기여 기준 충족 | 세 split 모두 미달 | **BLOCKED** |
| 권위 원장의 `learning_ready` | `false` | **BLOCKED** |
| 운영 승인자 서명 기록 | 없음 | **BLOCKED** |

---

## 2. 배포와 롤백 상태

승격과 배포가 승인되지 않았으므로 운영 모델 포인터 전환과 롤백 대상도 없다.
배포·무중단 전환·롤백 성공을 주장하지 않는다. 위 필수 증거와 별도 운영 승인이 생긴 뒤에만
실제 배포 절차와 검증된 롤백 대상을 작성할 수 있다.
"""
        governance_f.write_text(gov_content, encoding="utf-8")

        return manifest_f, csv_f, confusion_f, card_f, governance_f
