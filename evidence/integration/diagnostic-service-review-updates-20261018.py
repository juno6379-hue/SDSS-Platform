"""Attribute separately updated status prose without claiming collection progress."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
records = []
for name in ('docs/16_충분학습자료_단계별수집계획.md', 'docs/20_대량수집_학습_통합실행.md'):
    before = subprocess.check_output(['git', 'show', 'HEAD:' + name], cwd=ROOT)
    after = (ROOT / name).read_bytes()
    expected = before.replace(b'03:54', b'04:54').replace('34시간 53분'.encode(), '35시간 53분'.encode())
    assert after == expected, name
    records.append({'path': name, 'before_sha256': hashlib.sha256(before).hexdigest(),
                    'after_sha256': hashlib.sha256(after).hexdigest(),
                    'only_observation_time_and_stagnation_duration_changed': True,
                    'collection_counters_and_manifest_ledger_hashes_unchanged': True})
proof = {'recorded_at': datetime.now().astimezone().isoformat(),
         'attribution': 'Separately updated status documents reviewed and integrated; not authored as this service implementation.',
         'not_evidence_of_collection_or_training_resumption': True, 'files': records}
(ROOT / 'evidence/integration/diagnostic-service-separate-status-docs-20261018.json').write_text(
    json.dumps(proof, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'separate_status_documents_reviewed': len(records), 'unexpected_changes': []}))
