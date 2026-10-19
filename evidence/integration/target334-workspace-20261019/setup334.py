"""Setup script for target334 isolated workspace."""
import hashlib
import json
from pathlib import Path
import shutil
import sys

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parents[3]
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

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def pin(path, rel_to):
    data = path.read_bytes()
    return {
        'path': str(path.relative_to(rel_to)).replace('\\', '/'),
        'bytes': len(data),
        'sha256': hashlib.sha256(data).hexdigest()
    }

# 1. Baseline copy of scripts/collect_targeted_bare.py
target_script = 'scripts/collect_targeted_bare.py'
baseline_target = WORKSPACE / 'baseline' / target_script
baseline_target.parent.mkdir(parents=True, exist_ok=True)
shutil.copyfile(ROOT / target_script, baseline_target)

# Workspace working copy of collect_targeted_bare.py
work_target = WORKSPACE / target_script
work_target.parent.mkdir(parents=True, exist_ok=True)
shutil.copyfile(ROOT / target_script, work_target)

# 2. Copy backend files
for rel_path in BACKEND_FILES:
    src = ROOT / rel_path
    dst = WORKSPACE / rel_path
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)

# 3. Copy other scripts
for rel_path in SCRIPT_FILES:
    if rel_path == target_script:
        continue
    src = ROOT / rel_path
    dst = WORKSPACE / rel_path
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)

# 4. Copy legacy test for regression verification
legacy_test_src = ROOT / 'tests/test_collect_targeted_bare.py'
legacy_test_dst = WORKSPACE / 'tests/test_collect_targeted_bare_legacy.py'
legacy_test_dst.parent.mkdir(parents=True, exist_ok=True)
shutil.copyfile(legacy_test_src, legacy_test_dst)

# 5. Generate baseline-manifest334.json
manifest = {
    'unit': 334,
    'target_file': pin(ROOT / target_script, ROOT),
    'dependencies': [pin(ROOT / p, ROOT) for p in BACKEND_FILES + [f for f in SCRIPT_FILES if f != target_script]]
}
(WORKSPACE / 'baseline-manifest334.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('Setup complete. Baseline pinned:', manifest['target_file']['sha256'])
