"""Read-only API/source review; no server restart, POST, catalog or collection writes."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import subprocess
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).with_suffix('.json')
results = []
api_summary = {}
for endpoint in ('tools', 'datasets', 'models', 'jobs'):
    with urllib.request.urlopen('http://127.0.0.1:8002/api/' + endpoint, timeout=15) as response:
        value = json.load(response)
    assert isinstance(value, list), endpoint
    assert all(isinstance(row, dict) for row in value), endpoint
    api_summary[endpoint] = {'shape': 'list[object]', 'count': len(value), 'row_keys': sorted(value[0]) if value else []}
    if endpoint == 'tools':
        api_summary[endpoint]['implementation'] = [{'id': row.get('id'), 'implemented': row.get('implemented')} for row in value]
    results.append({'name': endpoint + '_live_get_shape', 'pass': True})

node = r'''
import assert from 'node:assert/strict';
import { toolboxCounts, toolboxImplementation, toolboxModels, recentToolboxJobs, toolboxJobState } from './frontend/src/toolboxAdapter.ts';
for (const value of ['true',1,{},null,undefined]) assert.equal(toolboxImplementation([{id:'lcluc',implemented:value}],'lcluc'),'unknown');
assert.equal(toolboxImplementation([{id:'unrelated',implemented:true}],'lcluc'),'unknown');
assert.deepEqual(toolboxCounts(toolboxModels.map(m=>({id:m.apiId,implemented:true})),true),{implemented:0,pending:0,unknown:6});
assert.deepEqual(recentToolboxJobs([]),[]);
assert.equal(toolboxJobState('unexpected').label,'상태 미확인');
console.log('strict_implementation,error_overrides_stale,empty_jobs,unknown_job_state');
'''
completed = subprocess.run(['node', '--experimental-strip-types', '--input-type=module', '-e', node], cwd=ROOT, capture_output=True, text=True, check=True)
for name in completed.stdout.strip().split(','):
    results.append({'name': name, 'pass': True})

css = (ROOT / 'frontend/src/geoai-toolbox.css').read_text(encoding='utf-8')
assert '.geoai-toolbox button:focus-visible' in css
assert 'url(\'/reference/model-' in css
results.append({'name': 'scoped_css_and_keyboard_focus_source_review', 'pass': True})
ui = (ROOT / 'frontend/src/GeoAIToolbox.tsx').read_text(encoding='utf-8')
assert 'Object.keys(errors).length>0' not in ui, 'Resolved-error keys must not show failure banner'
assert '실행과 승인은 각 Workspace에서 확인' in ui
assert '과학 검증·운영 승인과 별도' in ui
results.append({'name': 'resolved_errors_and_approval_separation_source_review', 'pass': True})

source_hashes = {}
for name in ('GeoAIToolbox.tsx', 'geoai-toolbox.css', 'toolboxAdapter.ts', 'App.tsx', 'PlatformShell.tsx'):
    source_hashes[name] = hashlib.sha256((ROOT / 'frontend/src' / name).read_bytes()).hexdigest()
workspace = 'frontend/src/ModelAnalysisWorkspace.tsx'
before = subprocess.run(['git', 'show', 'HEAD:' + workspace], cwd=ROOT, capture_output=True, check=True).stdout
assert before.replace(b'\r\n', b'\n') == (ROOT / workspace).read_bytes().replace(b'\r\n', b'\n')
results.append({'name': 'existing_detail_workspace_matches_head', 'pass': True})
OUT.write_text(json.dumps({'observed_at_utc': datetime.now(timezone.utc).isoformat(), 'classification': 'VERIFIED_REAL read-only GET plus TESTED_SYNTHETIC adapter assertions and source review; browser and full build are Root-owned', 'results': results, 'api_summary': api_summary, 'source_sha256': source_hashes, 'post_calls': 0, 'server_restarts': 0, 'collection_or_registry_writes': 0}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'pass': len(results), 'evidence': str(OUT)}, ensure_ascii=True))
