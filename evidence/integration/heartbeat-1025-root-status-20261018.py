"""Independent read-only observation; never runs collection, training or API writes."""
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
from urllib.request import urlopen

root = Path(__file__).resolve().parents[2]
read = lambda path: json.loads((root / path).read_text(encoding='utf-8-sig'))
summary = read('evidence/integration/priority-ml-20261018-summary.json')
pins = {}
for relative, expected in summary['outputs'].items():
    data = (root / relative).read_bytes()
    pins[relative] = len(data) == expected['bytes'] and hashlib.sha256(data).hexdigest() == expected['sha256']
assert all(pins.values()), pins
with urlopen('http://127.0.0.1:5174/api/data/collection-status', timeout=45) as response:
    status = json.load(response)
targets = status['collection_targets']
round2 = read('evidence/integration/priority-collection-round2-final-20261018.json')
result = {
    'observed_at_utc': datetime.now(timezone.utc).isoformat(),
    'status_api_path': '/api/data/collection-status',
    'initial_probe_error': '/api/collection-status returned 404; corrected using actual main.py route; no server defect inferred',
    'current_inventory': {key: targets[key] for key in ['source_manifest_sha256','physical_total','eligible_total','ineligible_total','eligible_target_gap','cell_gap_total']},
    'current_bare_declarations': targets['class_quality']['bare_by_split'],
    'candidate_api_available_at_observation': status['candidate_quality']['available'],
    'fixed_candidate': {key: summary[key] for key in ['status','scope','raw_source_snapshot_sha256','source_row_count','candidate_row_count','excluded_source_rows','candidate_eligible','candidate_blockers','remaining_source_identity_conflicts','verified_file_records']},
    'all_summary_output_pins_independently_match': all(pins.values()),
    'output_pin_checks': pins,
    'candidate_source_matches_current': summary['raw_source_snapshot_sha256'] == targets['source_manifest_sha256'],
    'round2': {key: round2[key] for key in ['status','new_physical','new_eligible','charged_delta_from_launch','remaining_budget','old_pending_rows_unchanged','old_pending_reserved_bytes','rate_limit_active','execution_lock_present']},
    'round2_caveat': 'SETTLED denotes accounting finalization. Both scene reports failed: AOI center outside COG. The recorded stdout-empty limitation is stale: actual stdout contains two starts and two finishes.',
    'native_raster_qa_rerun_by_this_observer': False,
    'training_executed_by_this_observer': False,
    'api_writes_by_this_observer': 0,
    'limitations': 'Sequential reads, not atomic OS snapshot; latest current inventory is manifest quality status, not new native QA. Fixed candidate does not include later collector additions.',
}
target = root / 'evidence/integration/heartbeat-1025-root-status-20261018.json'
with target.open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps({'all_output_pins_match': all(pins.values()), 'candidate_source_matches_current': result['candidate_source_matches_current'], 'current_eligible': targets['eligible_total'], 'candidate_api_available': status['candidate_quality']['available']}, ensure_ascii=True))
