"""완료된227 산출물의 JSON/지문 인계 검산. native/HTTP/게시 쓰기 없음."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
E = ROOT / 'evidence/integration/priority164-guarded227-20261018'
D = ROOT / 'data/priority164-guarded227-20261018'


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


terminal = load(ROOT / 'evidence/integration/priority227-terminal-20261018.json')
assert terminal['exit_code'] == 0
summary = load(E / 'summary.json')
assert summary['status'] == 'PINNED_CANDIDATE_QA_COMPLETED'
assert summary['file_sha_mismatches'] == 0
mismatches = [name for name, value in summary['outputs'].items()
              if sha(Path(name)) != value['sha256'] or Path(name).stat().st_size != value['bytes']]
assert not mismatches
source = load(D / 'source.json')
candidate = load(D / 'stage/candidate.json')
plan = load(E / 'split-plan.json')
qa = load(D / 'qa/readiness.json')
raw = load(D / 'source-readiness.json')
kept = plan['retained_row_indexes']
excluded = plan['excluded_row_indexes']
assert not set(kept) & set(excluded)
assert sorted(kept + excluded) == list(range(len(source['scenes'])))
assert candidate['scenes'] == [source['scenes'][i] for i in kept]
assert candidate['lineage']['source_row_indexes'] == kept
launch = load(ROOT / 'evidence/integration/priority227-launch-20261018.json')
assert all(sha(ROOT / name) == pin for name, pin in launch['protected_before'].items())
assert sha(ROOT / 'data/first-group-training-esri-v1/annual-window-report.json') == summary['source_sha256']
assert summary['remaining_source_identity_conflicts'] == 0
statistics = {split: {'valid_label_pixels': sum(counts), 'bare_pixels': counts[7],
                     'bare_percent': counts[7] / sum(counts) * 100,
                     'bare_contributing_patches': qa['class_patch_counts_by_split'][split][7]}
              for split, counts in qa['class_counts_by_split'].items()}
proof = {'status': 'METADATA_HANDOFF_VERIFIED', 'at': datetime.now(timezone.utc).isoformat(),
         'summary_sha256': sha(E / 'summary.json'), 'summary_bytes': (E / 'summary.json').stat().st_size,
         'output_pins_verified': len(summary['outputs']), 'output_pin_mismatches': mismatches,
         'exact_retained_rows': True, 'partition_complete': True,
         'source_current_matches_snapshot': True,
         'previous_207_artifacts_unchanged': launch['protected_before'],
         'source_verified_file_records': len(raw['verified_files']),
         'candidate_verified_file_records': len(qa['verified_files']),
         'excluded_rows': excluded, 'conflicts': plan['conflicts'], 'class_statistics': statistics,
         'source_rows_modified': False, 'pointer_written': False,
         'additional_native_scans': 0, 'training_executed': False, 'network_requests': 0}
path = E / 'handoff-verification.json'
with path.open('x', encoding='utf-8') as stream:
    json.dump(proof, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps(proof, ensure_ascii=False, indent=2))
print('HANDOFF_SHA ' + sha(path))
