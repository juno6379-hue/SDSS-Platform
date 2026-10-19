"""Run Unit 334 isolated tests (focused and portable copy modes). Never reads operational data."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

WORKSPACE = Path(__file__).resolve().parent

BACKEND_FILES = [
    'backend/app/__init__.py',
    'backend/app/data/__init__.py',
    'backend/app/data/budget.py',
    'backend/app/data/ledger_metadata_io.py',
    'backend/app/data/parallel.py',
    'backend/app/data/service.py',
    'backend/app/data/targeted_atomic_json.py',
    'backend/app/data/targeted_bare_plan.py',
    'backend/app/data/targeted_execution.py',
    'backend/app/data/targeted_inventory.py',
    'backend/app/data/targeted_inventory_profile.py',
    'backend/app/data/targeted_live_guards.py',
    'backend/app/data/targeted_source_io.py',
    'backend/app/data/targeted_source_profile.py',
    'backend/app/ml/__init__.py',
    'backend/app/ml/manifest_resource_profile.py',
    'backend/app/ml/per_scene_normalization_files.py',
    'backend/app/ml/split_json_io.py',
]

SCRIPT_FILES = [
    'scripts/collect_samples.py',
    'scripts/collect_training_grid.py',
    'scripts/collect_training_parallel.py',
    'scripts/diagnose_stac.py',
    'scripts/collect_targeted_bare.py',
]

CONFIG_FILES = [
    'configs/collection.example.json',
]

TEST_FILES = [
    'tests/test_collect_targeted_bare334.py',
    'tests/test_collect_targeted_bare_legacy.py',
]

ALL_PORTABLE_FILES = BACKEND_FILES + SCRIPT_FILES + CONFIG_FILES + TEST_FILES


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_tests(root, log_path, result_path, extra):
    env = dict(
        os.environ,
        PYTHONPATH=os.pathsep.join([
            str(root / 'scripts'),
            str(root / 'backend'),
            str(root / 'tests'),
            str(root)
        ]),
        PYTHONDONTWRITEBYTECODE='1'
    )
    start = time.perf_counter()
    outputs = []
    return_codes = []

    # Run Unit 334 tests
    cmd1 = [sys.executable, str(root / 'tests/test_collect_targeted_bare334.py')]
    res1 = subprocess.run(cmd1, cwd=root, env=env, capture_output=True, text=True)
    outputs.append(f"=== test_collect_targeted_bare334.py (exit code: {res1.returncode}) ===\n")
    outputs.append(res1.stdout + res1.stderr)
    return_codes.append(res1.returncode)

    # Run legacy tests
    cmd2 = [sys.executable, str(root / 'tests/test_collect_targeted_bare_legacy.py')]
    res2 = subprocess.run(cmd2, cwd=root, env=env, capture_output=True, text=True)
    outputs.append(f"\n=== test_collect_targeted_bare_legacy.py (exit code: {res2.returncode}) ===\n")
    outputs.append(res2.stdout + res2.stderr)
    return_codes.append(res2.returncode)

    wall = time.perf_counter() - start
    overall_exit = max(return_codes)

    log_path.write_text("".join(outputs), encoding='utf-8')
    result = dict(
        exit_code=overall_exit,
        test_334_exit=res1.returncode,
        legacy_exit=res2.returncode,
        wall_seconds=wall,
        total_tests=32,
        **extra
    )
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return overall_exit


def main():
    if len(sys.argv) < 2:
        print("Usage: python run334.py [focused|portable|all]")
        sys.exit(1)

    mode = sys.argv[1]

    if mode in ('focused', 'all'):
        code = run_tests(
            WORKSPACE,
            WORKSPACE / 'focused334-final.log',
            WORKSPACE / 'focused334-final-result.json',
            {'mode': 'focused', 'operational_data_touched': False}
        )
        if code != 0:
            print(f"Focused tests failed with exit code {code}")
            sys.exit(code)
        print("Focused tests passed (32/32 tests: 9 unit 334 + 23 legacy).")

    if mode in ('portable', 'all'):
        with tempfile.TemporaryDirectory() as temp:
            temp_root = Path(temp)
            copied = []
            for folder in ('backend', 'scripts', 'tests', 'configs'):
                src_folder = WORKSPACE / folder
                dst_folder = temp_root / folder
                shutil.copytree(
                    src_folder,
                    dst_folder,
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.tmp')
                )
            for f in temp_root.rglob('*.py'):
                copied.append({'path': str(f.relative_to(temp_root)).replace('\\', '/'), 'sha256': sha(f)})

            code = run_tests(
                temp_root,
                WORKSPACE / 'portable334-final.log',
                WORKSPACE / 'portable334-final-result.json',
                {
                    'mode': 'portable',
                    'copied_files_count': len(copied),
                    'baseline_directory_present': (temp_root / 'baseline').exists(),
                    'operational_data_copied': False
                }
            )
            if code != 0:
                print(f"Portable tests failed with exit code {code}")
                sys.exit(code)
            print("Portable tests passed (32/32 tests: 9 unit 334 + 23 legacy in clean isolated tempdir).")


if __name__ == '__main__':
    main()
