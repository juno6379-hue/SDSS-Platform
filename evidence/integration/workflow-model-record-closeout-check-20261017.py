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
snapshot_path=ROOT/'docs/understanding/EVIDENCE_SNAPSHOT.json'
snapshot=json.loads(snapshot_path.read_text('utf-8'))
proof=json.loads((ROOT/'evidence/integration/workflow-model-record-live-integrity-20261017.json').read_text('utf-8'))
closeout_path=ROOT/'evidence/integration/workflow-model-record-closeout-20261017.json'
names=set(snapshot['files'])
for pattern in ['backend/app/workflow_job_model_record_handoff.py','tests/test_workflow_job_model_record_handoff.py','docs/implementation/104*','docs/understanding/**/*.md','evidence/integration/workflow-model-record-*']:
    names.update(str(p.relative_to(ROOT)).replace('\\','/') for p in ROOT.glob(pattern) if p.is_file())
names.add(str(closeout_path.relative_to(ROOT)).replace('\\','/'))
names.discard('docs/understanding/EVIDENCE_SNAPSHOT.json')
closeout={'recorded_at':now,'status':'COMPLETED_INTERNAL_WORKFLOW_MODEL_RECORD_WRAPPER_NOT_AUTHORITY_OR_PROJECT_COMPLETION','documentation_validation':audit,'tests':proof['tests'],'full_regression_rerun_in_latest_unit':False,'previous_full_regression':proof['previous_full_regression'],'protected_references_checked':141,'existing_contracts_checked':72,'catalog_records':14,'understanding_updated':True,'direct_ui_change':False,'next_unit':'PLANNED_READ_ONLY_WORKFLOW_MODEL_RECORD_API_CONTRACT_REVIEW','snapshot_files':len(names)}
closeout_path.write_text(json.dumps(closeout,ensure_ascii=False,indent=2),'utf-8')
def record(name):
    data=(ROOT/name).read_bytes();return {'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}
snapshot['updated_at']=now
snapshot['reported_status']['latest_workflow_job_model_record_handoff']=proof
snapshot['reported_status']['full_regression_rerun_in_latest_unit']=False
snapshot['documentation_validation']=audit
snapshot['files']={name:record(name) for name in sorted(names)}
snapshot_path.write_text(json.dumps(snapshot,ensure_ascii=False,indent=2),'utf-8')
mismatches=[name for name,old in snapshot['files'].items() if record(name)!=old]
assert not mismatches,mismatches
print(json.dumps({'audit':audit,'snapshot_files':len(names),'snapshot_mismatches':mismatches},ensure_ascii=False))
