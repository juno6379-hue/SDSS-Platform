"""Final independent report/operational metadata pin checks, no inventory rerun."""
import hashlib,json
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[2]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def load(relative):return json.loads((ROOT/relative).read_text(encoding='utf8'))
pin=load('evidence/integration/bare179-request-pin-20261018.json')
report_path=ROOT/'evidence/integration/bare179-report-20261018.json'
report=load('evidence/integration/bare179-report-20261018.json')
assert report['status']=='LOCAL_NATIVE_REVIEW_COMPLETE_EXECUTION_UNAPPROVED'
assert report['inventory_scan_count']==1 and report['inventory']['inventory_verified'] is True
assert report['inventory']['pending_footprints_verified'] is True
assert len(report['targets'])==len(report['observations'])==50
assert all(sha(ROOT/path)==expected for path,expected in pin['original_pins'].items())
ui=report['ui_summary'];assert ui['candidate_total']==50
assert sum(r['candidates'] for r in ui['summary_by_province'])==50
assert all(r['candidates']==r['support_clear']+r['overlap']+r['local_invalid'] for r in ui['summary_by_province'])
assert all(ui[k] is False for k in ('execution_supported','actual_quality_verified','scientific_accuracy_validated'))
code=['scripts/review_bare_targets179.py','tests/test_review_bare_targets179.py']
out={'status':'VERIFIED_REAL_LOCAL_50_NATIVE_AND_SUPPORT_REVIEW','recorded_at':datetime.now(timezone.utc).isoformat(),
 'report':{'path':report_path.relative_to(ROOT).as_posix(),'sha256':sha(report_path),'bytes':report_path.stat().st_size},
 'operational_original_pins_preserved':pin['original_pins'],'source_pins':{p:sha(ROOT/p) for p in code},
 'ui_summary':ui,'candidate_mutual_overlap_pairs':len(report['candidate_mutual_overlap_pairs']),
 'support_assets_verified':report['inventory']['support_files_verified'],'native_label_files_read':report['native_label_files_read'],
 'native_label_bytes_read':report['native_label_bytes_read'],'inventory_scan_count':1,'http_calls':0,
 'execution_supported':False,'actual_quality_verified':False,'scientific_accuracy_validated':False,
 'scope':'Local weak-label native verification and numerical support overlaps; no optical collection or final approval.'}
with Path(__file__).with_suffix('.json').open('x',encoding='utf8') as f:json.dump(out,f,ensure_ascii=False,indent=2)
print(json.dumps(out,ensure_ascii=True))
