"""Observe private registry behavior using stored declared scene history."""
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import sys

root = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(root/'.runtime'),str(root/'backend')]
from app.data.targeted_scene_claims import SceneClaimRegistry

path = root/'data/first-group-training-esri-v1/annual-window-report.json'
raw = path.read_bytes()
manifest = json.loads(raw)
history = defaultdict(set)
missing = 0
for row in manifest['scenes']:
    if not row.get('scene_id'):
        missing += 1
        continue
    history[row['scene_id']].add(row['split'])
records = [{'scene_id':scene,'split':split} for scene,splits in sorted(history.items()) for split in sorted(splits)]
assert len(records) <= 1024
source_sha = hashlib.sha256(raw).hexdigest()
seed = {'schema_version':1,'kind':'DECLARED_SCENE_SPLIT_HISTORY',
        'source_manifest_sha256':source_sha,'scenes':records}
registry = SceneClaimRegistry(seed)
assert registry.snapshot()['status'] == 'LOCAL_REGISTRY_INITIALIZED_EXECUTION_BLOCKED'
conflicts = [scene for scene,splits in history.items() if len(splits)>1]
assert conflicts, 'Expected stored cross-split scene must be independently observed.'
quarantine = []
for scene in sorted(conflicts):
    for split in ('train','val','test'):
        outcome = registry.claim({'schema_version':1,'scene_id':scene,'split':split,'owner_id':'root-private-observer'})
        assert outcome['issue'] == 'SEEDED_SCENE_QUARANTINED' and outcome['claim'] is None
        quarantine.append({'scene_id':scene,'split':split,'issue':outcome['issue']})
scene,splits = next((scene,splits) for scene,splits in sorted(history.items()) if len(splits)==1)
declared_split = next(iter(splits))
other_split = next(value for value in ('train','val','test') if value != declared_split)
rejected = registry.claim({'schema_version':1,'scene_id':scene,'split':other_split,'owner_id':'root-private-observer'})
assert rejected['issue'] == 'DECLARED_SPLIT_CONFLICT'
accepted = registry.claim({'schema_version':1,'scene_id':scene,'split':declared_split,'owner_id':'root-private-observer'})
assert accepted['claim'] is not None and accepted['execution_supported'] is False
assert path.read_bytes() == raw
report = {'at_utc':datetime.now(timezone.utc).isoformat(),
    'classification':'VERIFIED_REAL_STORED_SCENE_DECLARATIONS_PRIVATE_MEMORY_OBSERVATION',
    'source_manifest_sha256_observed_by_caller':source_sha,'manifest_rows':len(manifest['scenes']),
    'rows_without_scene_id':missing,'deduplicated_scene_split_records':len(records),
    'distinct_declared_scenes':len(history),'quarantine_checks':quarantine,
    'single_split_veto_issue':rejected['issue'],'private_registry_snapshot':registry.snapshot(),
    'original_manifest_sha_unchanged':True,
    'source_sha_verification_scope':'This audit pins its one manifest read; the registry itself never verifies files or inventory completeness.',
    'limitations':'No unaggregated source reports, pending footprints, image aliases, live worker registry, network or cross-process protection checked.',
    'operating_writes':0,'network_requests':0,'collectors_started':0}
with (root/'evidence/integration/targeted-scene-claims-real-history-20261018.json').open('x',encoding='utf-8') as stream:
    json.dump(report,stream,ensure_ascii=False,indent=2)
    stream.write('\n')
print(json.dumps({'distinct_scenes':len(history),'quarantined_scenes':len(conflicts),'claim_count':registry.snapshot()['claim_count'],'execution_supported':False},ensure_ascii=True))
