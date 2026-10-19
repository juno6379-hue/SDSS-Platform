"""완료309의 metadata/SHA 인계 검산만. assess/native/training/publish 호출0."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'.runtime'),str(ROOT/'backend')]
from backend.app.ml import manifest_resource_profile as profile

D=ROOT/'data/priority164-guarded309-20261018'
E=ROOT/'evidence/integration/priority164-guarded309-20261018'
with profile.scope(profile.NAME) as budget:
    terminal,t_sha,t_raw=profile.read_metadata(ROOT/'evidence/integration/priority309-terminal-20261018.json','local_plan')
    assert terminal['exit_code']==0 and terminal['status']=='PINNED_CANDIDATE_QA_COMPLETED'
    prior=terminal['resource_usage_before_terminal_write']
    # 기존 operation 사용량을 debit하여 인계 검사도 남은16GiB 안에 둔다.
    profile.charge(prior['read_bytes'])
    profile.charge(prior['write_bytes']+len(t_raw),'write')
    summary,s_sha,_=profile.read_metadata(E/'summary.json','saved_plan')
    preparation,_,_=profile.read_metadata(ROOT/'evidence/integration/priority309-preparation-20261018.json','local_plan')
    ledger_ref=preparation['ledger_preparation_provenance']
    ledger=ROOT/ledger_ref['path']
    assert ledger.stat().st_size==ledger_ref['bytes']
    assert profile.bounded_json_digest(ledger,'status_report')==ledger_ref['sha256']
    assert summary['manifest_profile']==dict(profile.MARKER)==terminal['manifest_profile']
    assert summary['remaining_source_identity_conflicts']==0 and summary['file_sha_mismatches']==0
    assert summary['training_executed'] is False and summary['ready_for_training'] is False
    roles={D/'source.json':'source',D/'source-readiness.json':'readiness',E/'split-plan.json':'saved_plan',
           E/'candidate-package/plan.json':'saved_plan',E/'candidate-package/candidate.json':'candidate',
           E/'candidate-package/receipt.json':'receipt',D/'stage/candidate.json':'candidate',
           D/'stage/staging-receipt.json':'receipt',ROOT/'data/first-group/experiment-esri-v003-2020-2025.json':'policy',
           D/'qa/readiness.json':'readiness',D/'qa/qa-receipt.json':'receipt'}
    assert {Path(p) for p in summary['outputs']}==set(roles)
    output_pins={}
    for value,pin in summary['outputs'].items():
        path=Path(value);actual=profile.bounded_json_digest(path,roles[path])
        assert actual==pin['sha256'] and path.stat().st_size==pin['bytes']
        output_pins[str(path.relative_to(ROOT))]={'sha256':actual,'bytes':pin['bytes']}
    current=ROOT/'data/first-group-training-esri-v1/annual-window-report.json'
    assert profile.bounded_json_digest(current,'source')==summary['source_sha256']
    source,_,_=profile.read_metadata(D/'source.json','source',summary['source_sha256'])
    candidate,_,_=profile.read_metadata(D/'stage/candidate.json','candidate',summary['outputs'][str(D/'stage/candidate.json')]['sha256'])
    plan,_,_=profile.read_metadata(E/'split-plan.json','saved_plan',summary['outputs'][str(E/'split-plan.json')]['sha256'])
    qa,_,_=profile.read_metadata(D/'qa/readiness.json','readiness',summary['outputs'][str(D/'qa/readiness.json')]['sha256'])
    kept=plan['retained_row_indexes'];excluded=plan['excluded_row_indexes']
    assert type(kept) is list and type(excluded) is list
    assert all(type(i) is int and 0<=i<len(source['scenes']) for i in kept+excluded)
    assert len(set(kept+excluded))==len(kept+excluded)
    assert not set(kept)&set(excluded)
    assert sorted(kept+excluded)==list(range(len(source['scenes'])))
    assert candidate['scenes']==[source['scenes'][i] for i in kept]
    assert candidate['lineage']['source_row_indexes']==kept
    assert candidate.get('historical_noneligible_patches',[])==source.get('historical_noneligible_patches',[])
    assert len(candidate['scenes'])==summary['candidate_row_count']
    assert len(source['scenes'])+len(source.get('historical_noneligible_patches',[]))<=3000
    assert len(candidate['scenes'])+len(candidate.get('historical_noneligible_patches',[]))<=3000
    receipts={}
    for p in (E/'candidate-package/receipt.json',D/'stage/staging-receipt.json',D/'qa/qa-receipt.json'):
        receipt,sha,_=profile.read_metadata(p,'receipt')
        assert receipt['schema_version']==2 and receipt['manifest_profile']==dict(profile.MARKER)
        receipts[str(p.relative_to(ROOT))]=sha
    for p,pin in terminal['protected_before'].items():
        assert profile.bounded_json_digest(ROOT/p,'pointer')==pin==terminal['protected_after'][p]
    stats={split:{'valid_label_pixels':sum(counts),'bare_pixels':counts[7],
                  'bare_percent':counts[7]/sum(counts)*100,
                  'bare_contributing_patches':qa['class_patch_counts_by_split'][split][7]}
           for split,counts in qa['class_counts_by_split'].items()}
    proof={'status':'METADATA_HANDOFF_VERIFIED','at':datetime.now(timezone.utc).isoformat(),
           'summary_sha256':s_sha,'terminal_sha256':t_sha,'output_pins':output_pins,
           'output_pin_mismatches':0,'v2_receipts':receipts,'manifest_profile':dict(profile.MARKER),
           'exact_retained_rows':True,'partition_complete':True,'exact_lineage':True,'history_exact':True,'source_current_matches_snapshot':True,
           'source_rows':len(source['scenes']),'candidate_rows':len(candidate['scenes']),
           'source_history_rows':len(source.get('historical_noneligible_patches',[])),
           'candidate_history_rows':len(candidate.get('historical_noneligible_patches',[])),
           'ledger_current_matches_preparation':True,'ledger_preparation_sha256':ledger_ref['sha256'],
           'candidate_eligible':summary['candidate_eligible'],'excluded_rows':excluded,
           'conflicts':plan['conflicts'],'remaining_source_identity_conflicts':0,
           'candidate_verified_file_records':len(qa['verified_files']),
           'verified_file_sha_recheck':f"EXISTING_164_CLI_RECHECKED_ALL_{len(qa['verified_files'])}_ZERO_MISMATCH_NOT_REPEATED_HERE",
           'class_statistics':stats,'candidate_blockers':summary['candidate_blockers'],
           'connectivity_capture_status':summary['connectivity_capture_status'],
           'protected_before_and_now':terminal['protected_before'],
           'carried_forward_qa_usage_before_terminal':prior,
           'cumulative_qa_plus_handoff_budget_before_proof_write':budget.bytes,
           'maximum_json_io_bytes':budget.maximum,'additional_native_scans':0,'network_requests':0,
           'source_or_pointer_written':False,'training_executed':False,'registry_called':False}
    payload=(json.dumps(proof,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf-8')
    path=E/'handoff-verification.json';profile.write_new_json_bytes(path,payload,'local_plan')
    print(json.dumps({'status':proof['status'],'candidate_eligible':summary['candidate_eligible'],
                     'excluded_rows':excluded,'class_statistics':stats,'output_pin_mismatches':0,
                     'v2_receipts_verified':len(receipts),'candidate_verified_files':len(qa['verified_files']),
                     'proof_sha256':hashlib.sha256(payload).hexdigest(),'proof_bytes':len(payload),
                     'cumulative_json_io_bytes_after_proof':budget.bytes},ensure_ascii=False))
