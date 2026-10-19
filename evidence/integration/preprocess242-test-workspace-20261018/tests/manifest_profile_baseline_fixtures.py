"""Self-contained SHA-pinned historical test code; never fall back to current code."""
import hashlib
import sys
import types
from pathlib import Path
from types import MappingProxyType
BASELINE_ROOT=Path(__file__).resolve().parent/'fixtures/manifest_profile_baselines'
MANIFEST_SHA256='7e4babd8f30ff31ca70e677c1eb1cabae0e715bd7a386136c4cb6be84abde637'
BASELINES=MappingProxyType({'candidate_materialization_pre228': {'file': 'candidate_materialization_pre228.py', 'sha256': '6caec21389aa68472a50097f6f5d70d1554f17a8cda67b85e9d1e21f8a32f37b', 'bytes': 8716}, 'candidate_qa_comparison_pre228': {'file': 'candidate_qa_comparison_pre228.py', 'sha256': '7c472e37a5df7a56a6935adeff991a966d90ce9fd4337c3326777b00be57f18e', 'bytes': 17204}, 'centers230': {'file': 'centers230.py', 'sha256': 'c67e868ac693d62f5384c84c173d6e9fea7a221f56df8bade9140eca4be09f8d', 'bytes': 14002}, 'status230': {'file': 'status230.py', 'sha256': 'bacd9f17a1b256b51752e639a02458f623286506aba2bc59664f3153513ddce4', 'bytes': 17192}})

def _pinned(path,expected):
    if path.is_symlink() or path.resolve().parent!=BASELINE_ROOT.resolve():raise AssertionError('Baseline fixture path mismatch')
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=expected:raise AssertionError('Baseline fixture SHA mismatch: '+path.name)
    return raw

def baseline_bytes(name):
    _pinned(BASELINE_ROOT/'manifest.json',MANIFEST_SHA256)
    record=BASELINES[name]
    return _pinned(BASELINE_ROOT/record['file'],record['sha256'])

def load_baseline(name,module_name,package):
    raw=baseline_bytes(name);path=BASELINE_ROOT/BASELINES[name]['file']
    module=types.ModuleType(module_name);module.__package__=package;module.__file__=str(path)
    original_path=sys.path[:]
    try:exec(compile(raw,str(path),'exec'),module.__dict__)
    finally:sys.path[:]=original_path
    return module
