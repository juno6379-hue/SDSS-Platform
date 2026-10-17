"""Verify frozen documentation and refresh its evidence index, not operating data."""
from pathlib import Path
import datetime
import hashlib
import json
import re
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[2]
now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat()
errors = []
understanding = list((ROOT/'docs/understanding').rglob('*.md'))
new_docs = [ROOT/'docs/implementation'/name for name in (
    '111_data_pipeline_completion.md', '112_lcluc_ml_completion.md',
    '113_lcluc_integration_acceptance.md', '114_geollm_technical_review.md')]
links = references = 0
for path in understanding + new_docs:
    text = path.read_text('utf-8')
    if path in understanding and path.name != 'GATE_TEMPLATE.md':
        for field in ('updated_at', 'source_commit', 'evidence_paths', 'confidence', 'status'):
            if not re.search(r'^\|\s*'+field+r'\s*\|', text, re.M):
                errors.append(str(path.relative_to(ROOT))+': missing '+field)
        for line in text.splitlines():
            if re.match(r'^\|\s*evidence_paths\s*\|', line):
                for name in re.findall(r'`([^`]+)`', line):
                    references += 1
                    if not (ROOT/name).exists(): errors.append('missing evidence '+name)
    for value in re.findall(r'\]\(([^)]+)\)', text):
        name = unquote(value.strip('<>').split('#', 1)[0])
        if not name or re.match(r'^[a-zA-Z][\w+.-]*:', name): continue
        links += 1
        if not (path.parent/name).exists(): errors.append(str(path.relative_to(ROOT))+': missing link '+name)
faq_count = len(re.findall(r'^## \d+\.', (ROOT/'docs/understanding/presentations/FAQ.md').read_text('utf-8'), re.M))
assert faq_count == 10, faq_count
pairs = [('docs/agents/UNDERSTANDING_AGENT.md', 'UI/GreenBlue_Understanding_Agent/docs/agents/UNDERSTANDING_AGENT.md'),
         ('docs/understanding/GATE_TEMPLATE.md', 'UI/GreenBlue_Understanding_Agent/docs/understanding/GATE_TEMPLATE.md')]
assert all((ROOT/a).read_bytes() == (ROOT/b).read_bytes() for a, b in pairs)
assert not errors, errors
log_path = 'evidence/integration/lcluc-geollm-full-tests-20261018.log'
text = (ROOT/log_path).read_text('utf-8')
match = re.search(r'Ran (\d+) tests in ([\d.]+)s', text)
assert match and re.search(r'^OK \(skipped=1\)$', text, re.M)
regression = {'tests_run': int(match[1]), 'passed': int(match[1])-1, 'skipped': 1,
              'seconds': float(match[2]), 'exit_code': 0, 'log': log_path}
integrity = json.loads((ROOT/'evidence/integration/lcluc-geollm-live-integrity-final-20261018.json').read_text('utf-8'))
independent = json.loads((ROOT/'evidence/integration/geollm-independent-review-20261018.json').read_text('utf-8'))
assert independent['unittest']['tests'] == 17
audit = {'checked_at': now, 'understanding_markdown': len(understanding), 'new_implementation_markdown': len(new_docs),
         'local_links': links, 'metadata_evidence_references': references, 'numbered_faq': faq_count,
         'errors': errors, 'reference_templates_byte_identical': True}
closeout_path = ROOT/'evidence/integration/lcluc-geollm-closeout-20261018.json'
closeout = {'recorded_at': now, 'status': 'DATA_REGISTRATION_ML_ERROR_ANALYSIS_AND_GEO_LLM_REVIEW_COMPLETED_NOT_PROJECT_ACCEPTANCE',
            'documentation_validation': audit, 'current_regression': regression,
            'integrity': integrity, 'understanding_updated': True,
            'actual_geollm_in_app': 'NONE_PREDEFINED_PATTERN', 'actual_storage': 'SQLITE',
            'qwen3_8b': 'CANDIDATE_NOT_INSTALLED_NOT_BENCHMARKED',
            'BGE_embedding': 'REAL_LOCAL_1024_DIM_INTERNAL_CODE_RETRIEVAL_NOT_PRODUCTION_RAG',
            'actual_lcluc_workflow_executor': 'PLANNED_NOT_IMPLEMENTED_IN_THIS_UNIT',
            'operating_collection_training_registration_jobs_deployment': 0,
            'frontend_build_browser_rerun': False, 'frontend_change': False,
            'independent_validation_labels': 'USER_CONFIRMED_UNAVAILABLE',
            'other_five_model_runners': 'USER_CONFIRMED_NOT_PROVIDED_UNCONNECTED',
            'next_internal_work': 'LCLUC_ONLY_EXECUTOR_AND_GUARDED_OPTIONAL_GEOLLM_PROVIDER_AFTER_ACCEPTANCE_REVIEW'}
snapshot_path = ROOT/'docs/understanding/EVIDENCE_SNAPSHOT.json'
snapshot = json.loads(snapshot_path.read_text('utf-8'))
names = set(snapshot['files'])
patterns = ['backend/app/data/collection_registration.py', 'backend/app/ml/error_analysis.py',
            'backend/app/ml/service.py', 'scripts/register_collection.py', 'scripts/evaluate_geollm*.py',
            'tests/test_collection_version_registration.py', 'tests/test_ml_error_analysis.py',
            'tests/test_geollm*.py', 'docs/implementation/11[1-4]*.md', 'docs/understanding/**/*.md',
            'evidence/integration/data-pipeline-*20261018*', 'evidence/integration/data-review-ml-*20261018*',
            'evidence/integration/lcluc-ml-*20261018*', 'evidence/integration/geollm-*20261018*',
            'evidence/integration/lcluc-geollm-*20261018*']
for pattern in patterns:
    names.update(p.relative_to(ROOT).as_posix() for p in ROOT.glob(pattern) if p.is_file())
names.add(closeout_path.relative_to(ROOT).as_posix())
names.discard('docs/understanding/EVIDENCE_SNAPSHOT.json')
closeout['snapshot_files'] = len(names)
closeout_path.write_text(json.dumps(closeout, ensure_ascii=False, indent=2), 'utf-8')


def record(name):
    raw = (ROOT/name).read_bytes()
    return {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


snapshot['updated_at'] = now
snapshot['source_commit'] = 'be029c15b7966e8f64331349c54bb8508dabe3e8'
snapshot['source_commit_reason'] = 'Published baseline plus current verified working files identified by raw SHA; the baseline does not include units111-114. Subsequent Git commit preserves these exact files.'
snapshot['reported_status']['current_regression'] = regression
snapshot['reported_status']['full_regression_rerun_in_latest_unit'] = True
snapshot['reported_status']['latest_data_ml_geollm_review'] = closeout
snapshot['documentation_validation'] = audit
snapshot['files'] = {name: record(name) for name in sorted(names)}
snapshot_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), 'utf-8')
assert all(record(name) == expected for name, expected in snapshot['files'].items())
print(json.dumps({'audit': audit, 'snapshot_files': len(names), 'snapshot_mismatches': []}, ensure_ascii=False))
