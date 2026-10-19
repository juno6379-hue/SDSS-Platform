"""One read-only current JSON size/row/tree observation; no raster or readiness QA."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,time
R=Path(__file__).resolve().parents[2];p=R/'data/first-group-training-esri-v1/annual-window-report.json'
def state(path):
    s=path.stat();return (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
start=time.monotonic();before=state(p)
assert before[2]<=64*1024**2
current=p
while current!=R:
    assert not current.is_symlink() and not (getattr(current.lstat(),'st_file_attributes',0)&0x400)
    current=current.parent
with p.open('rb') as f:raw=f.read(64*1024**2+1)
assert len(raw)==before[2] and state(p)==before
digest=hashlib.sha256(raw).hexdigest()
assert digest=='9c24eec337a17f95855d190918c9999c25aeb1925a7642b1ade26afa4e20d987'
document=json.loads(raw)
rows=len(document['scenes']);history=len(document.get('historical_noneligible_patches',[]))
assert rows+history<=3000
# Match the profile's _tree visit semantics, including dict keys and container leave visits.
stack=[(document,1,False)];visited=0;maximum_container_depth=0
while stack:
    value,depth,leave=stack.pop();visited+=1
    assert visited<=4000000,'MANIFEST_NODE_LIMIT'
    if leave:continue
    if type(value) in (dict,list):
        maximum_container_depth=max(maximum_container_depth,depth)
        assert depth<=32,'MANIFEST_DEPTH_LIMIT'
        stack.append((None,depth,True))
        if type(value) is dict:
            for key,item in value.items():stack.append((item,depth+1,False));stack.append((key,depth+1,False))
        else:
            for item in value:stack.append((item,depth+1,False))
with p.open('rb') as f:after_raw=f.read(64*1024**2+1)
assert state(p)==before and hashlib.sha256(after_raw).hexdigest()==digest
out={'status':'CURRENT_MANIFEST_STRUCTURAL_LIMITS_VERIFIED_NOT_QA','at_utc':datetime.now(timezone.utc).isoformat(),
 'source_sha256':digest,'source_bytes':len(raw),'rows':rows,'history_rows':history,
 'profile_tree_visits':visited,'maximum_container_depth':maximum_container_depth,
 'limits':{'source_candidate_bytes':128*1024**2,'rows_plus_history':3000,'tree_visits':4000000,'depth':32},
 'actual_json_bytes_read':len(raw)+len(after_raw),'seconds':round(time.monotonic()-start,3),
 'current_source_within_legacy64m':True,'source_unchanged':True,'rss_observed':False,
 'real128m_performance_verified':False,'raster_reads':0,'readiness_qa_runs':0,
 'http_requests':0,'source_or_ledger_writes':False,'collection_started':False,'profile_activated':False}
with (R/'evidence/integration/current-manifest-structural-preflight-root-20261018.json').open('x',encoding='utf-8') as f:json.dump(out,f,ensure_ascii=False,indent=2)
print(json.dumps(out),flush=True)
