"""Read-only independent pins/counts audit, without rerunning native raster QA."""
from pathlib import Path
import hashlib
import json
from datetime import datetime, timezone

root = Path(__file__).resolve().parents[2]
source = root / 'evidence/integration/priority-ml-next-20261018-summary.json'
summary = json.loads(source.read_text(encoding='utf-8'))
assert summary['status'] == 'FROZEN_SNAPSHOT_CANDIDATE_QA_COMPLETED'
pins = {}
for name, expected in summary['outputs'].items():
    raw = (root / name).read_bytes()
    pins[name] = len(raw) == expected['bytes'] and hashlib.sha256(raw).hexdigest() == expected['sha256']
assert all(pins.values())
raw = (root / 'data/first-group-training-esri-v1/annual-window-report.json').read_bytes()
current = json.loads(raw)
result = {key: summary[key] for key in ['status','scope','raw_source_snapshot_sha256','source_row_count','candidate_row_count','excluded_source_rows','candidate_eligible','candidate_blockers','candidate_bare_pixels','candidate_bare_contributing_patches','ready_for_training','training_executed','verified_file_records','source_qa_seconds','candidate_qa_seconds']}
result.update(observed_at_utc=datetime.now(timezone.utc).isoformat(),
              output_pin_checks=pins, all_output_pins_match=True,
              current_manifest_sha256=hashlib.sha256(raw).hexdigest(),
              current_physical=len(current['scenes']),
              candidate_source_matches_current=hashlib.sha256(raw).hexdigest() == summary['raw_source_snapshot_sha256'],
              native_raster_qa_rerun=False, operating_writes=0,
              limitation='Sequential reads, not an atomic OS snapshot. Current inventory may change under the authorized collector. Native QA evidence belongs to fixed cohort.')
with (root / 'evidence/integration/heartbeat-1045-candidate-audit-20261018.json').open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps({'pins_match':True,'eligible':sum(summary['candidate_eligible'].values()),'blockers':len(summary['candidate_blockers']),'source_matches_current':result['candidate_source_matches_current']}, ensure_ascii=True))
