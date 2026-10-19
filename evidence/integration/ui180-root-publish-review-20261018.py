from pathlib import Path
import sys,json,hashlib,os,datetime
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'backend'))
from app.collection_priority_status import bare_target_review
E=R/'evidence/integration';D=R/'data';source=E/'bare179-report-20261018.json';raw=source.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='36aaf1107292eee74b0f6a2ce462d90e40a22de498ca31aaff1c1ded636775f0'
report=json.loads(raw);target=D/'first-group-training-priority/bare-review179-20261018.json'
with target.open('xb') as stream:stream.write(raw)
receipt={'schema_version':1,'report':{'path':target.relative_to(D).as_posix(),'sha256':hashlib.sha256(raw).hexdigest()}}
path=D/'first-group-training-priority/latest-bare-review.json';assert not path.exists()
payload=(json.dumps(receipt,indent=2)+'\n').encode();tmp=path.with_suffix('.tmp')
with tmp.open('xb') as stream:stream.write(payload);stream.flush();os.fsync(stream.fileno())
os.replace(tmp,path)
current=hashlib.sha256((D/'first-group-training-esri-v1/annual-window-report.json').read_bytes()).hexdigest()
view=bare_target_review(D,current);assert view['available'] is True
out={'recorded_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PINNED_REVIEW_PUBLISHED_READER_VERIFIED','receipt':receipt,'reader':view,'receipt_sha256':hashlib.sha256(payload).hexdigest(),'training_started':False,'source_or_ledger_written':False}
(E/'ui180-root-publish-review-20261018.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':out['status'],'review':view},ensure_ascii=True))
