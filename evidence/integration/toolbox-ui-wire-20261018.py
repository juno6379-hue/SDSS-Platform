"""Narrow Toolbox-only wiring, preserving all existing workspace implementations."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
mode = sys.argv[1]
shell = ROOT / 'frontend/src/PlatformShell.tsx'
before = json.loads((ROOT / 'evidence/integration/toolbox-ui-preflight-20261018.json').read_text('utf-8'))
blob = subprocess.check_output(['git', 'show', 'HEAD:frontend/src/PlatformShell.tsx'], cwd=ROOT)
variants = [blob, blob.replace(b'\r\n', b'\n'), blob.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')]
original = next(value for value in variants if hashlib.sha256(value).hexdigest() == before['frontend/src/PlatformShell.tsx']['sha256'])
original_lf = original.replace(b'\r\n', b'\n')
line = next(line for line in original_lf.splitlines(keepends=True) if line.startswith(b'export function ToolboxHub('))
wired = original_lf.replace(b"import type { EvidenceRecord } from './integrationAdapter';", b"export { default as ToolboxHub } from './GeoAIToolbox';").replace(line, b'')
current = shell.read_bytes().replace(b'\r\n', b'\n')
assert current in (original_lf, wired), 'Another owner changed PlatformShell; inspect before wiring.'
if mode == 'defer':
    shell.write_bytes(original)
else:
    assert mode == 'wire' and (ROOT / 'frontend/src/GeoAIToolbox.tsx').exists()
    shell.write_bytes(wired.replace(b'\n', b'\r\n') if b'\r\n' in original else wired)
    app = ROOT / 'frontend/src/App.tsx'
    raw = app.read_bytes()
    old = b'return <div className={step===24?"app reference-workspace":"app"}>'
    new = b'return <div className={step===24?"app reference-workspace":step===12||step===13?"app toolbox-page":"app"}>'
    assert raw.count(old) == 1
    raw = raw.replace(old, new)
    old_props = b'<ToolboxHub tools={rows(resources.tools)} onOpen='
    new_props = b'<ToolboxHub tools={resources.tools===undefined?undefined:rows(resources.tools)} datasets={resources.datasets===undefined?undefined:datasets} models={resources.models===undefined?undefined:models} jobs={resources.jobs===undefined?undefined:rows(resources.jobs)} errors={errors} loading={loading} connected={connected} onNavigate={navigate} onRefresh={()=>void refresh()} onOpen='
    assert raw.count(old_props) == 1
    app.write_bytes(raw.replace(old_props, new_props))
print(mode)
