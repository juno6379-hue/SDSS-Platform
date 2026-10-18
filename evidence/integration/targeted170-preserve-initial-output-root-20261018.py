"""기존 실패 증거 원바이트 보존 이동. 실행 중 감사의 exclusive 최종 출력을 확보한다."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib,json,os
root=Path(__file__).resolve().parents[2]
folder=root/'evidence/integration'
source=folder/'targeted170-independent-20261018.json'
initial=folder/'targeted170-independent-initial-20261018.json'
destination=folder/'targeted170-independent-initial-output-conflict-preserved-20261018.json'
assert source.resolve().parent==folder.resolve() and destination.resolve().parent==folder.resolve()
raw=source.read_bytes();document=json.loads(raw)
assert document['status']=='INDEPENDENT_CHECK_FAILED'
assert document['recorded_at']=='2026-10-18T02:34:06.617298+00:00'
assert raw==initial.read_bytes() and not destination.exists()
digest=hashlib.sha256(raw).hexdigest()
assert source.read_bytes()==raw
os.rename(source,destination)
assert destination.read_bytes()==raw and initial.read_bytes()==raw
proof={'at':datetime.now(timezone.utc).isoformat(),'action':'PRESERVE_FAILED_INITIAL_OUTPUT_BY_RENAME',
       'source':str(source),'preserved':str(destination),'sha256':digest,
       'existing_initial_backup_sha256':hashlib.sha256(initial.read_bytes()).hexdigest(),
       'old_bytes_preserved':True,'operating_data_or_ledger_writes':0,
       'audit_restarted':False,'audit_success_claimed':False,
       'reason':'Running existing audit uses exclusive create at final output; leave old failed receipt immutable at preserved path.'}
with (folder/'targeted170-output-collision-repair-root-20261018.json').open('x',encoding='utf-8') as output:
    json.dump(proof,output,ensure_ascii=False,indent=2)
print(json.dumps(proof,ensure_ascii=True))
