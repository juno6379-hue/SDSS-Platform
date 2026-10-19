"""Test runner and evidence generator for ModelDeploymentPromotionManager."""
from __future__ import annotations

import io
import json
from pathlib import Path
import sys
import time
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
WORKSPACE_DIR = Path(__file__).resolve().parent
if str(WORKSPACE_DIR) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_DIR))

from test_model_deployment_promotion import TestModelDeploymentPromotion


def main():
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestModelDeploymentPromotion)

    test_names = loader.getTestCaseNames(TestModelDeploymentPromotion)

    stream = io.StringIO()
    runner = unittest.TextTestRunner(stream=stream, verbosity=2)

    started_at = time.time()
    result = runner.run(suite)
    elapsed = time.time() - started_at

    output_text = stream.getvalue()
    print(output_text)

    log_path = WORKSPACE_DIR / "promotion_test.log"
    log_path.write_text(output_text, encoding="utf-8")

    evidence = {
        "suite": "TestModelDeploymentPromotion",
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "was_successful": result.wasSuccessful(),
        "elapsed_seconds": round(elapsed, 3),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "test_names": test_names,
    }

    json_path = WORKSPACE_DIR / "promotion_test_results.json"
    json_path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(f"Results written to {json_path}")

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
