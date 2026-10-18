"""Join completed observations without promoting collection into training approval."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tomllib

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / 'evidence/integration'


def read(name):
    return json.loads((EVIDENCE / name).read_text('utf-8-sig'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


log = EVIDENCE / 'collection-resume-root-full-20261018.log'
raw_log = log.read_text('utf-8', errors='replace')
count_matches = list(re.finditer(r'^Ran (\d+) tests in ([\d.]+)s[\r\n]*$', raw_log, re.M))
success_matches = list(re.finditer(r'^OK(?: \(skipped=(\d+)\))?[\r\n]*$', raw_log, re.M))
counts = count_matches[-1] if count_matches else None
success = success_matches[-1] if success_matches else None
assert counts and success, 'Full backend regression has not completed successfully.'
assert raw_log.rstrip().splitlines()[-1].startswith('OK'), 'Regression is still running or failed.'
assert not re.search(r'^FAILED\b', raw_log, re.M)
total, seconds = int(counts[1]), float(counts[2])
skipped = int(success[1] or 0)
collection = read('collection-resume-audit-20261018-final-outcome.json')
observation = read('collection-resume-audit-20261018-observation-005717992597.json')
qa = read('ml-resume-audit-20261018-candidate-only-summary.json')
qa_files = read('ml-resume-audit-20261018-final-verification.json')
service = read('147-local-service-restore-20261018-final.json')
assert collection['physical_count'] == 1400 and collection['eligible_count'] == 1122
assert collection['new_physical'] == 16 and collection['new_eligible'] == 11
assert collection['new_patch_bare8_pixels_all'] == 0
assert collection['pending_count'] == 2 and not collection['execution_lock_exists']
assert collection['run_result']['parallel_execution']['finalized_batches'] == 2
assert observation['old_pending_records_unchanged'] and not observation['old_partial_changes']
assert not observation['fixed_input_changes'] and not observation['original_existing_ledger_record_changes']
assert observation['within_same_4gib_budget'] and observation['new_keys_within_expected_two']
assert qa['fixed_pins_stable'] and not qa['ready_for_training']
assert all(qa['same_as_stored_candidate_QA'].values())
assert qa_files['actual_final_file_rehash_count'] == 4285 and not qa_files['mismatch_paths']
assert service['catalog_rows'] == 14 and service['api_access_log_POST_count'] == 0
assert service['catalog_canonical_sha256'] == '72cf29dae2c6790907559d38d92ebf43eaf6ede795607637b0a46ccdaa5b754b'
automation_path = Path.home() / '.codex/automations/geoai-2/automation.toml'
automation = tomllib.loads(automation_path.read_text('utf-8-sig'))
assert automation['status'] == 'ACTIVE'
assert automation['rrule'] == 'FREQ=MINUTELY;INTERVAL=10'
assert automation['target_thread_id'] == '01a14c70-71a9-7e80-b326-dfbba5a958d6'
result = {
    'observed_at': datetime.now().astimezone().isoformat(),
    'source_parent_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
    'source_change': 'scripts/collect_training_parallel.py explicit unrelated-pending queue filter only',
    'full_backend': {'total': total, 'passed': total - skipped, 'skipped': skipped, 'seconds': seconds,
                     'log': str(log.relative_to(ROOT)), 'log_sha256': digest(log)},
    'root_focused': {'passed': 7, 'seconds': 1.962, 'scope': 'SYNTHETIC_TEMP_LEDGER_NO_NETWORK'},
    'live_collection': {'physical': 1400, 'eligible': 1122, 'new_physical': 16, 'new_eligible': 11,
                        'new_bare_pixels': 0, 'new_charged_bytes': collection['new_total_charged'],
                        'remaining_new_budget_bytes': collection['new_budget_remaining'],
                        'old_pending_count': 2, 'old_pending_reserved_bytes_preserved': 136314880,
                        'old_pending_retry_or_settlement': False, 'old_pending_refund_bytes': 0,
                        'bounded_submitted_and_finalized': 2, 'execution_lock_exists_after': False},
    'frozen_candidate': {'eligible': qa['eligible'], 'blocker_count': 4, 'seconds': qa['seconds'],
                         'actual_post_QA_file_rehashes': 4285, 'mismatches': 0,
                         'new_collection_included': False, 'first_mutable_parent_stability_failure_preserved': True},
    'service': {'api': 'http://127.0.0.1:8002', 'frontend': 'http://127.0.0.1:5174',
                'mode': 'EXISTING_LOCALHOST_DEVELOPMENT_TOKEN_UNSET', 'catalog_unchanged': True,
                'new_POST_requests': 0, 'new_operating_workflow_report_GET': 0},
    'reporting': {'automation_id': 'geoai-2', 'active': True, 'interval_minutes': 10,
                  'target_thread_id': automation['target_thread_id']},
    'documents': ['148_collection_resume_audit.md', '149_training_data_remediation_audit.md',
                  '150_service_recovery_audit.md', '151_development_resume_runbook.md'],
    'understanding_documents_updated': 11,
    'not_achieved': ['old_pending_terminal_recovery', 'bare_class_remediation', 'new_1122_candidate_QA',
                     'independent_ground_truth', 'operating_training_or_model_approval', 'whole_project_completion'],
    'next_internal_work': 'Explicit 256 target planning/collection with geometry, overlap/scene separation and shared budget gates.'
}
target = EVIDENCE / 'collection-resume-closeout-20261018.json'
with target.open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
print(json.dumps(result, ensure_ascii=True))
