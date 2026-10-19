"""Root-only post309 publication. Requires an exact separately pinned approval."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, json, os, sys
R=Path(__file__).resolve().parents[2];D=R/'data';E=R/'evidence/integration'
sys.path[:0]=[str(R),str(R/'backend')]
from backend.app.ml.manifest_resource_profile import scope,NAME,MARKER,read_metadata,bounded_json_digest,write_new_json_bytes,active,write_measured
from backend.app.collection_priority_status import candidate_quality

def need(v):
    if not v:raise ValueError('PUBLICATION312_CONTRACT_FAILED')
def read(p,role,pin=None):return read_metadata(p,role,pin)
def write(p,v,role='local_plan'):
    raw=(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode()
    write_new_json_bytes(p,raw,role);return raw

def main():
    parser=argparse.ArgumentParser(allow_abbrev=False);parser.add_argument('--approval',type=Path,required=True);args=parser.parse_args()
    with scope(NAME) as budget:
        need(args.approval.is_absolute() and args.approval.resolve().is_relative_to(E))
        a,_,_=read(args.approval,'local_plan')
        need(set(a)=={'kind','approved','summary_sha256','handoff_sha256','terminal_sha256','source_sha256','ledger_sha256','previous_pointer_sha256'} and a['kind']=='ROOT_POST309_PUBLICATION' and a['approved'] is True)
        need((a['source_sha256'],a['ledger_sha256'],a['previous_pointer_sha256'])==('0c149628ccfa916ee976e561c5da05f9ccc810cbeab7d233a05b9bc7eff54658','d5ee31ff7970adaaa6b166805c240616efa8e9af713bb8394c7a166346f21c91','996a88de2034e9803381d7ae4e906a0d1f418075675d13ef796fb5648bb472c0'))
        need(not (D/'first-group-training-budget/global-ledger.execution.lock').exists())
        base=D/'priority164-guarded309-20261018';eb=E/'priority164-guarded309-20261018'
        terminal,_,_=read(E/'priority309-terminal-20261018.json','local_plan',a['terminal_sha256'])
        need(terminal['exit_code']==0 and terminal['status']=='PINNED_CANDIDATE_QA_COMPLETED')
        summary,_,_=read(eb/'summary.json','saved_plan',a['summary_sha256'])
        read(eb/'handoff-verification.json','local_plan',a['handoff_sha256'])
        need(summary['status']=='PINNED_CANDIDATE_QA_COMPLETED' and summary['manifest_profile']==dict(MARKER))
        need(summary['file_sha_mismatches']==summary['remaining_source_identity_conflicts']==0)
        need(summary['training_executed'] is False and summary['registry_called'] is False and summary['network_requests']==0)
        need(summary['ready_for_training'] is False and summary['observed_gate_ready_for_training'] is False)
        current=D/'first-group-training-esri-v1/annual-window-report.json';ledger=D/'first-group-training-budget/global-ledger.json'
        need(bounded_json_digest(current,'source')==a['source_sha256']==summary['source_sha256'])
        need(bounded_json_digest(ledger,'status_report')==a['ledger_sha256'])
        roles={base/'source.json':'source',base/'source-readiness.json':'readiness',eb/'split-plan.json':'saved_plan',eb/'candidate-package/plan.json':'saved_plan',eb/'candidate-package/candidate.json':'candidate',eb/'candidate-package/receipt.json':'receipt',base/'stage/candidate.json':'candidate',base/'stage/staging-receipt.json':'receipt',D/'first-group/experiment-esri-v003-2020-2025.json':'policy',base/'qa/readiness.json':'readiness',base/'qa/qa-receipt.json':'receipt'}
        need({Path(x) for x in summary['outputs']}==set(roles))
        for name,pin in summary['outputs'].items():
            target=Path(name);need(target.stat().st_size==pin['bytes'] and bounded_json_digest(target,roles[target])==pin['sha256'])
        def output_pin(p):return summary['outputs'][str(p)]['sha256']
        for p in (eb/'candidate-package/receipt.json',base/'stage/staging-receipt.json',base/'qa/qa-receipt.json'):
            v,_,_=read(p,'receipt',output_pin(p));need(v['schema_version']==2 and v['manifest_profile']==dict(MARKER))
        source,sourcepin,_=read(base/'source.json','source',a['source_sha256'])
        candidate,_,_=read(base/'stage/candidate.json','candidate',output_pin(base/'stage/candidate.json'))
        plan,_,_=read(eb/'split-plan.json','saved_plan',output_pin(eb/'split-plan.json'));qa,_,_=read(base/'qa/readiness.json','readiness',output_pin(base/'qa/readiness.json'))
        retained=plan['retained_row_indexes'];excluded=plan['excluded_row_indexes'];n=len(source['scenes'])
        need(type(retained) is list and type(excluded) is list)
        need(all(type(x) is int and 0<=x<n for x in retained+excluded))
        need(len(set(retained+excluded))==len(retained+excluded)==n and sorted(retained+excluded)==list(range(n)))
        need(candidate['scenes']==[source['scenes'][i] for i in retained])
        need(n==summary['source_row_count'] and len(candidate['scenes'])==summary['candidate_row_count'] and len(excluded)==summary['excluded_source_rows'])
        need(qa['patch_counts_by_split']==summary['candidate_eligible'] and qa['blockers']==summary['candidate_blockers'] and qa['ready_for_training'] is False)
        folder=D/'first-group-training-priority';pointer=folder/'latest-candidate.json'
        old,oldpin,prior=read(pointer,'pointer',a['previous_pointer_sha256'])
        need(old['by_split']=={'train':834,'val':276,'test':250})
        paths=[base/'source.json',base/'stage/candidate.json',base/'qa/readiness.json']
        receipt={'schema_version':1,'recorded_at':datetime.now(timezone.utc).isoformat(),'files':[{'path':p.relative_to(D).as_posix(),'sha256':output_pin(p)} for p in paths],'source_manifest_sha256':a['source_sha256'],'by_split':qa['patch_counts_by_split'],'blocker_count':len(qa['blockers']),'scene_split_conflicts':[],'ready_for_training':False,'scientific_accuracy_validated':False,'scope':'FROZEN_POST304_1779_ROW_SOURCE_NOT_LATER_COLLECTION','limitations':['Connectivity witness '+summary['connectivity_capture_status']+'; no gate bypass','Weak labels are not independent ground truth; no training or registry approval'],'previous_pointer_sha256':oldpin}
        archive=folder/'candidate-pointer-before312-20261018.json';write_new_json_bytes(archive,prior,'pointer')
        need(bounded_json_digest(archive,'pointer')==oldpin)
        payload=write(folder/'candidate-receipt312-20261018.json',receipt,'pointer')
        tmp=folder/'latest-candidate312.tmp'
        with tmp.open('xb',buffering=0) as stream:write_measured(stream,payload);stream.flush();os.fsync(stream.fileno())
        need(bounded_json_digest(pointer,'pointer')==oldpin and bounded_json_digest(current,'source')==a['source_sha256'] and bounded_json_digest(ledger,'status_report')==a['ledger_sha256'])
        need(not (ledger.parent/'global-ledger.execution.lock').exists())
        need(all(bounded_json_digest(p,roles[p])==output_pin(p) for p in paths))
        os.replace(tmp,pointer)
        def same_hash(path,pin,*,json_role):return bounded_json_digest(path,json_role)==pin
        view=candidate_quality(D,a['source_sha256'],same_hash)
        need(view['available'] and view['source_matches_current_manifest'] and view['eligible_total']==sum(summary['candidate_eligible'].values()) and view['by_split']==summary['candidate_eligible'] and view['blocker_count']==len(qa['blockers']) and view['ready_for_training'] is False)
        need(bounded_json_digest(current,'source')==a['source_sha256'] and bounded_json_digest(ledger,'status_report')==a['ledger_sha256'])
        result={'status':'COMPLETED_QA_PUBLISHED_AND_PROFILE_READER_VERIFIED','recorded_at':datetime.now(timezone.utc).isoformat(),'pointer_sha256':bounded_json_digest(pointer,'pointer'),'previous_pointer_sha256':oldpin,'previous_pointer_preserved':True,'exact_retained_rows':True,'partition_complete':True,'file_sha_mismatches':0,'source_snapshot_sha256':a['source_sha256'],'candidate_view':view,'manifest_profile':dict(MARKER),'json_io_before_result_write':{'read_bytes':budget.reads,'write_bytes':budget.writes,'json_io_bytes':budget.bytes,'maximum_bytes':budget.maximum},'training_started':False,'registry_written':False,'source_or_ledger_written':False,'profile_config_changed':False,'api_or_browser_verified':False}
        write(E/'priority312-publication-root-20261018.json',result)
        print(json.dumps(result,ensure_ascii=True),flush=True)
if __name__=='__main__':main()
