"""Publish a derived scope annotation; original native report remains intact."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,os,sys
R=Path(__file__).resolve().parents[2];D=R/'data';E=R/'evidence/integration';sys.path.insert(0,str(R/'backend'))
from app.collection_priority_status import bare_target_review
def read(p):return json.loads(p.read_text('utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
report_path=E/'bare192-review-20261018/report.json';report=read(report_path)
proposal_path=E/'bare190-gap-20261018/proposal.json';proposal=read(proposal_path)
assert sha(proposal_path)==report['request']['proposal_ref']['sha256']
assert report['status']=='LOCAL_NATIVE_REVIEW_COMPLETE_EXECUTION_UNAPPROVED'
assert report['inventory_scan_count']==1 and report['inventory']['inventory_verified'] is True and report['inventory']['pending_footprints_verified'] is True and report['inventory']['source_pins_verified'] is True
assert all(report[k] is False for k in ['execution_supported','actual_quality_eligible','scientifically_verified_bare'])
scope=proposal['province_filter'];assert set(scope)=={'gorontalo','west_java'} and len(scope)==2
summary=report['ui_summary'];assert summary['candidate_total']==37 and report['historical_clear_count']==4
assert all(row['candidates']==0 for row in summary['summary_by_province'] if row['province'] not in scope)
current=D/'first-group-training-esri-v1/annual-window-report.json';current_pin=sha(current)
assert summary['current_manifest_sha256']==current_pin
original_pin=sha(report_path)
summary['searched_provinces']=scope
report['publication_scope_provenance']={'original_native_report_sha256':original_pin,'pinned_proposal_sha256':sha(proposal_path),'only_added_ui_scope_annotation':True}
payload=(json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode()
folder=D/'first-group-training-priority';target=folder/'bare-review192-20261018.json';pointer=folder/'latest-bare-review.json';prior=pointer.read_bytes()
assert read(pointer)['report']['sha256']=='36aaf1107292eee74b0f6a2ce462d90e40a22de498ca31aaff1c1ded636775f0'
with target.open('xb') as f:f.write(payload)
receipt={'schema_version':1,'report':{'path':target.relative_to(D).as_posix(),'sha256':sha(target)}}
raw=(json.dumps(receipt,indent=2)+'\n').encode()
for path,value in [(folder/'bare-review-pointer-before192-20261018.json',prior),(folder/'bare-review-receipt192-20261018.json',raw)]:
    with path.open('xb') as f:f.write(value)
temp=folder/'latest-bare-review192.tmp'
with temp.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
assert pointer.read_bytes()==prior and sha(current)==current_pin and sha(report_path)==original_pin
os.replace(temp,pointer)
view=bare_target_review(D,current_pin)
assert view['available'] and view['candidate_total']==37 and view['searched_provinces']==scope and view['source_matches_current_manifest']
result={'status':'SCOPED_NATIVE_REVIEW_PUBLISHED_READER_VERIFIED','recorded_at':datetime.now(timezone.utc).isoformat(),'original_native_report_sha256':original_pin,'published_report_sha256':sha(target),'scope_annotation_only':True,'previous_pointer_preserved':True,'reader':view,'source_or_ledger_written':False,'training_started':False}
with (E/'bare192-publication-root-20261018.json').open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
print(json.dumps(result,ensure_ascii=True),flush=True)
