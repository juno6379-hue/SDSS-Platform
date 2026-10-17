"""Freeze documentation evidence after the local executor implementation writers stop."""
from pathlib import Path
import datetime
import hashlib
import json
import re
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[2]
now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat()
documents = list((ROOT/'docs/understanding').rglob('*.md'))
documents.append(ROOT/'docs/implementation/115_lcluc_workflow_executor.md')
errors = []
links = references = 0
for path in documents:
    text = path.read_text('utf-8')
    if 'understanding' in path.parts and path.name != 'GATE_TEMPLATE.md':
        for field in ('updated_at', 'source_commit', 'evidence_paths', 'confidence', 'status'):
            if not re.search(r'^\|\s*'+field+r'\s*\|', text, re.M): errors.append(str(path)+': '+field)
        for line in text.splitlines():
            if re.match(r'^\|\s*evidence_paths\s*\|', line):
                for name in re.findall(r'`([^`]+)`', line):
                    references += 1
                    if not (ROOT/name).exists(): errors.append('missing evidence '+name)
    for value in re.findall(r'\]\(([^)]+)\)', text):
        name = unquote(value.strip('<>').split('#', 1)[0])
        if not name or re.match(r'^[a-zA-Z][\w+.-]*:', name): continue
        links += 1
        if not (path.parent/name).exists(): errors.append(str(path)+': missing link '+name)
faq = len(re.findall(r'^## \d+\.', (ROOT/'docs/understanding/presentations/FAQ.md').read_text('utf-8'), re.M))
assert faq == 10
for left, right in (
    ('docs/agents/UNDERSTANDING_AGENT.md', 'UI/GreenBlue_Understanding_Agent/docs/agents/UNDERSTANDING_AGENT.md'),
    ('docs/understanding/GATE_TEMPLATE.md', 'UI/GreenBlue_Understanding_Agent/docs/understanding/GATE_TEMPLATE.md'),
):
    assert (ROOT/left).read_bytes() == (ROOT/right).read_bytes()
assert not errors, errors
integrity = json.loads((ROOT/'evidence/integration/lcluc-workflow-live-integrity-20261018.json').read_text('utf-8'))
review = json.loads((ROOT/'evidence/integration/lcluc-workflow-independent-review-20261018.json').read_text('utf-8'))
audit = {'checked_at': now, 'understanding_markdown': len(documents)-1, 'implementation_markdown': 1,
         'local_links': links, 'metadata_evidence_references': references, 'numbered_faq': faq,
         'errors': errors, 'reference_templates_byte_identical': True}
closeout = {'recorded_at': now, 'status': 'LOCAL_LCLUC_CORE_AND_EXPLICIT_CLI_COMPLETED_NOT_OPERATING_ACCEPTANCE',
            'scope': 'GLOBAL_NORMALIZATION_TINY_UNET_BOUNDED_TILE', 'documentation_validation': audit,
            'current_regression': integrity['full'], 'independent': review['independent'], 'related': review['related'],
            'protected_files_checked': integrity['protected_files_checked'], 'catalog_rows': integrity['catalog_rows'],
            'existing_source_changes': [], 'understanding_updated': True,
            'operating_collection_training_jobs_registry_deployment': 0,
            'API_UI_connected': False, 'six_band_per_scene_normalization_supported': False,
            'scientific_accuracy_validated': False, 'standard_gmais_result': False,
            'front_build_browser_rerun': False,
            'next_unit': '116_API_UI_BINDING_AND_PINNED_PER_SCENE_INPUT_CONTRACT_REVIEW'}
target = ROOT/'evidence/integration/lcluc-workflow-closeout-20261018.json'
snapshot_path = ROOT/'docs/understanding/EVIDENCE_SNAPSHOT.json'
snapshot = json.loads(snapshot_path.read_text('utf-8'))
names = set(snapshot['files'])
for pattern in ('backend/app/lcluc_workflow.py', 'scripts/run_lcluc_workflow.py', 'tests/test_lcluc_workflow.py',
                'docs/implementation/115*.md', 'docs/understanding/**/*.md', 'evidence/integration/lcluc-workflow-*20261018*'):
    names.update(path.relative_to(ROOT).as_posix() for path in ROOT.glob(pattern) if path.is_file())
names.add(target.relative_to(ROOT).as_posix())
names.discard('docs/understanding/EVIDENCE_SNAPSHOT.json')
closeout['snapshot_files'] = len(names)
target.write_text(json.dumps(closeout, ensure_ascii=False, indent=2), 'utf-8')


def record(name):
    raw = (ROOT/name).read_bytes()
    return {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


snapshot['updated_at'] = now
snapshot['source_commit'] = 'd264f81378f7fd3a2b07ab69b9193e8b3d651bc9'
snapshot['source_commit_reason'] = 'Published baseline plus the new115 files pinned by raw SHA; the baseline does not contain115. Subsequent Git publication preserves these bytes.'
snapshot['reported_status']['current_regression'] = integrity['full']
snapshot['reported_status']['full_regression_rerun_in_latest_unit'] = True
snapshot['reported_status']['latest_lcluc_workflow_executor'] = closeout
snapshot['documentation_validation'] = audit
snapshot['files'] = {name: record(name) for name in sorted(names)}
snapshot_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), 'utf-8')
assert all(record(name) == expected for name, expected in snapshot['files'].items())
print(json.dumps({'audit': audit, 'snapshot_files': len(names), 'snapshot_mismatches': []}, ensure_ascii=False))
