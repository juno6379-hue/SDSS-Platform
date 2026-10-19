"""Read-only actual API verification after explicit bare320 publication; no profile change."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,sys,time,urllib.request
R=Path(__file__).resolve().parents[2];D=R/'data';E=R/'evidence/integration'
sys.path[:0]=[str(R),str(R/'backend')]
from backend.app.ml.manifest_resource_profile import scope,NAME,MARKER,read_metadata,bounded_json_digest,write_new_json_bytes,write_measured

def need(v):
    if not v:raise ValueError('BARE322_API_CONTRACT_FAILED')

def main():
    p=argparse.ArgumentParser(allow_abbrev=False);p.add_argument('--publication-sha256',required=True);a=p.parse_args()
    with scope(NAME):
        pub,_,_=read_metadata(E/'bare320-publication-root-20261018.json','local_plan',a.publication_sha256)
        need(pub['status']=='LOCAL_ONLY_REVIEW_PUBLISHED_READER_VERIFIED' and pub['manifest_profile']==dict(MARKER))
        need(pub['source_sha256']=='0c149628ccfa916ee976e561c5da05f9ccc810cbeab7d233a05b9bc7eff54658' and pub['ledger_sha256']=='d5ee31ff7970adaaa6b166805c240616efa8e9af713bb8394c7a166346f21c91')
        need(pub['candidate_pointer_sha256']=='25d7bf6d37a7c96ab6a9eaa2a74e78b94f52e8186b22a8ac705184ff96b5832e' and pub['remote_requests']==0 and pub['collection_started'] is False)
        names={D/'first-group-training-esri-v1/annual-window-report.json':('source',pub['source_sha256']),D/'first-group-training-budget/global-ledger.json':('status_report',pub['ledger_sha256']),D/'first-group-training-priority/latest-candidate.json':('pointer',pub['candidate_pointer_sha256']),D/'first-group-training-priority/latest-bare-review.json':('pointer',pub['pointer_sha256']),D/'first-group-training-priority/source-profile237-root-20261018.json':('local_config','e63f89cae95c33bad9f5195e9750b684232ee89a895309d591668e7519767a68')}
        need(all(bounded_json_digest(q,role)==pin for q,(role,pin) in names.items()))
        need(not (D/'first-group-training-budget/global-ledger.execution.lock').exists())
        response_path=E/'bare322-api-response-root-20261018.json';checks_path=E/'bare322-api-checks-root-20261018.json'
        need(all(not q.exists() and not q.is_symlink() for q in (response_path,checks_path)))
        req=urllib.request.Request('http://127.0.0.1:8002/api/data/collection-status',headers={'Origin':'http://127.0.0.1:5174'})
        start=time.monotonic()
        with urllib.request.urlopen(req,timeout=150) as resp:raw=resp.read(2*1024**2+1);code=resp.status
        need(len(raw)<=2*1024**2);write_new_json_bytes(response_path,raw,'local_plan')
        value=json.loads(raw);targets=value.get('collection_targets',{});candidate=value.get('candidate_quality',{});bare=targets.get('bare_target_review',{});budget=targets.get('budget_status',{})
        rows=bare.get('rows',[])
        checks={'http200':code==200,'raw1407_gap0':targets.get('eligible_total')==1407 and targets.get('cell_gap_total')==0,'candidate1391_current':candidate.get('eligible_total')==1391 and candidate.get('source_matches_current_manifest') is True,'not_ready3':candidate.get('ready_for_training') is False and candidate.get('blocker_count')==3,'bare50_current':bare.get('candidate_total')==50 and bare.get('source_matches_current_manifest') is True,'bare_report_sha':bare.get('report_sha256')==pub['report_sha256'],'bare_35_15':len(rows)==6 and sum(x.get('overlap',-10000) for x in rows)==35 and sum(x.get('support_clear',-10000) for x in rows)==15,'bare_unapproved':all(bare.get(k) is False for k in ('execution_supported','actual_quality_verified','scientific_accuracy_validated')),'budget_remaining':budget.get('remaining_bytes')==1799757940,'oldpending':budget.get('old_pending_bytes')==136314880,'operating_pins_preserved':all(bounded_json_digest(q,role)==pin for q,(role,pin) in names.items())}
        result={'status':'REAL_API_POST320_LOCAL_REVIEW_VERIFIED' if all(checks.values()) else 'REAL_API_POST320_INCOMPLETE','at_utc':datetime.now(timezone.utc).isoformat(),'seconds':round(time.monotonic()-start,3),'checks':checks,'recorded_at':value.get('recorded_at'),'budget_observed_at':budget.get('observed_at'),'bare_review_recorded_at':bare.get('recorded_at'),'publication_sha256':a.publication_sha256,'source_sha256':pub['source_sha256'],'report_sha256':pub['report_sha256'],'profile_changed':False,'server_restarted':False,'native_repeated':False,'collection_started':False,'browser_verified':False}
        data=(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode();write_new_json_bytes(checks_path,data,'local_plan');write_measured(sys.stdout.buffer,data);sys.stdout.buffer.flush();need(all(checks.values()))
if __name__=='__main__':main()
