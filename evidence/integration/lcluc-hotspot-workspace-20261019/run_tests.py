"""Test runner for spatial hotspot analysis engine.
Executes test_spatial_hotspot_engine.py and writes structured evidence.
"""
from __future__ import annotations

import io
import json
from pathlib import Path
import time
import unittest
import sys

# Ensure workspace is on sys.path
WORKSPACE = Path(__file__).resolve().parent
sys.path.insert(0, str(WORKSPACE))

import test_spatial_hotspot_engine


def main():
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(test_spatial_hotspot_engine)

    stream = io.StringIO()
    runner = unittest.TextTestRunner(stream=stream, verbosity=2)

    start_time = time.monotonic()
    result = runner.run(suite)
    duration = round(time.monotonic() - start_time, 4)

    output_log = stream.getvalue()
    print(output_log)

    log_path = WORKSPACE / "hotspot_test.log"
    log_path.write_text(output_log, encoding="utf-8")

    evidence = {
        "suite": "spatial_hotspot_analysis_engine",
        "total_tests": result.testsRun,
        "passed": result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped),
        "failed": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "was_successful": result.wasSuccessful(),
        "time_taken_seconds": duration,
        "failures_detail": [f"{test}: {err}" for test, err in result.failures],
        "errors_detail": [f"{test}: {err}" for test, err in result.errors]
    }

    results_path = WORKSPACE / "hotspot_test_results.json"
    results_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved evidence to {results_path}")
    print(f"Results: {evidence['passed']}/{evidence['total_tests']} passed (success={evidence['was_successful']})")

    if not result.wasSuccessful():
        sys.exit(1)


if __name__ == '__main__':
    main()
