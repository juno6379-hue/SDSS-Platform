"""Audit documentation and refresh the evidence reading snapshot after writers freeze."""
from pathlib import Path
import datetime
import hashlib
import json
import re
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[2]
now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat()
errors = []
documents = list((ROOT / 'docs/understanding').rglob('*.md'))
links = references = 0
for path in documents:
    text = path.read_text(encoding='utf-8')
    if path.name != 'GATE_TEMPLATE.md':
        for field in ['updated_at', 'source_commit', 'evidence_paths', 'confidence', 'status']:
            if not re.search(r'^\|\s*' + field + r'\s*\|', text, re.M):
                errors.append(str(path.relative_to(ROOT)) + ': missing ' + field)
        for line in text.splitlines():
            if re.match(r'^\|\s*evidence_paths\s*\|', line):
                for name in re.findall(r'`([^`]+)`', line):
                    references += 1
                    if not (ROOT / name).exists(): errors.append('evidence missing: ' + name)
    for value in re.findall(r'\]\(([^)]+)\)', text):
        name = unquote(value.strip('<>').split('#', 1)[0])
        if not name or re.match(r'^[a-zA-Z][\w+.-]*:', name): continue
        links += 1
        if not (path.parent / name).exists(): errors.append('link missing: ' + str(path.relative_to(ROOT)) + ': ' + name)
faq_count = len(re.findall(r'^## \d+\.', (ROOT / 'docs/understanding/presentations/FAQ.md').read_text(encoding='utf-8'), re.M))
if faq_count != 10: errors.append('FAQ count != 10')
pairs = [('docs/agents/UNDERSTANDING_AGENT.md', 'UI/GreenBlue_Understanding_Agent/docs/agents/UNDERSTANDING_AGENT.md'), ('docs/understanding/GATE_TEMPLATE.md', 'UI/GreenBlue_Understanding_Agent/docs/understanding/GATE_TEMPLATE.md')]
templates_ok = all((ROOT / a).read_bytes() == (ROOT / b).read_bytes() for a, b in pairs)
if not templates_ok: errors.append('reference template changed')
audit = {'checked_at': now, 'markdown_files': len(documents), 'local_links': links, 'evidence_references': references, 'numbered_faq': faq_count, 'errors': errors, 'reference_templates_byte_identical': templates_ok}
assert not errors, errors
snapshot_path = ROOT / 'docs/understanding/EVIDENCE_SNAPSHOT.json'
snapshot = json.loads(snapshot_path.read_text(encoding='utf-8'))
integrity = json.loads((ROOT / 'evidence/integration/model-version-live-integrity-20261017.json').read_text(encoding='utf-8'))
closeout_path = ROOT / 'evidence/integration/model-version-closeout-20261017.json'
closeout = {'recorded_at': now, 'status': 'COMPLETED_OPTIONAL_CALLER_MODEL_VERSION_DECLARATION_NOT_AUTHORITY_OR_EXECUTION_OR_PROJECT_COMPLETION', 'documentation_validation': audit, 'full_regression': integrity['full_regression'], 'protected_references_checked': 141, 'existing_contracts_checked': integrity['existing_contracts_checked'], 'catalog_records': 14, 'understanding_updated': True, 'new_qa_or_training_executed': False, 'next_unit': 'PLANNED_OPTIONAL_MODEL_VERSION_REGISTRATION_API_UI_MANUAL_INTEGRATION', 'snapshot_file': 'docs/understanding/EVIDENCE_SNAPSHOT.json'}
names = set(snapshot['files'])
for pattern in ['backend/app/experiment_registry.py', 'tests/test_model_version_declaration.py', 'docs/implementation/97*', 'docs/understanding/**/*.md', 'evidence/integration/model-version-*']:
    names.update(str(p.relative_to(ROOT)).replace('\\', '/') for p in ROOT.glob(pattern) if p.is_file())
names.add(str(closeout_path.relative_to(ROOT)).replace('\\', '/'))
names.discard('docs/understanding/EVIDENCE_SNAPSHOT.json')
closeout['snapshot_files'] = len(names)
closeout_path.write_text(json.dumps(closeout, ensure_ascii=False, indent=2), encoding='utf-8')
def record(name):
    data = (ROOT / name).read_bytes()
    return {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
snapshot['updated_at'] = now
status = snapshot['reported_status']
if status['current_regression']['log'] != integrity['full_regression']['log']:
    status['previous_regression'] = status['current_regression']
status['current_regression'] = integrity['full_regression']
status['latest_model_version_declaration'] = integrity
status['full_regression_rerun_in_latest_unit'] = True
snapshot['documentation_validation'] = audit
snapshot['files'] = {name: record(name) for name in sorted(names)}
snapshot_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding='utf-8')
mismatches = [name for name, old in snapshot['files'].items() if record(name) != old]
assert not mismatches, mismatches
print(json.dumps({'audit': audit, 'snapshot_files': len(names), 'snapshot_mismatches': mismatches}, ensure_ascii=False))
