"""Explicit source-profile rebind after audited zero-patch279; no candidate QA or publication."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,os,sys,time,urllib.request
R=Path(__file__).resolve().parents[2];D=R/'data';E=R/'evidence/integration'
sys.path[:0]=[str(R),str(R/'backend')]
from backend.app.ml.manifest_resource_profile import scope,NAME,read_metadata,bounded_json_digest,write_new_json_bytes,write_measured

def need(v):
    if not v:raise ValueError('PROFILE282_CONTRACT_FAILED')
def write(p,v):write_new_json_bytes(p,(json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode(),'local_plan')

def main():
    ap=argparse.ArgumentParser(allow_abbrev=False);ap.add_argument('--audit-sha256',required=True);args=ap.parse_args()
    with scope(NAME):
        audit,_,_=read_metadata(E/'deficit279-native-root-20261018.json','local_plan',args.audit_sha256)
        need(audit['status']=='COMPLETED_ZERO_PATCH_NARROW_AUDIT' and audit['new_patch_files']==audit['new_eligible_patches']==0 and audit['old_rows_exact'] and audit['old_pending_exact'] and audit['source_ledger_two_reads_stable'])
        source=D/'first-group-training-esri-v1/annual-window-report.json';ledger=D/'first-group-training-budget/global-ledger.json';config=D/'first-group-training-priority/source-profile237-root-20261018.json'
        names={source:'source',ledger:'status_report',D/'first-group-training-priority/latest-candidate.json':'pointer',D/'first-group-training-priority/latest-bare-review.json':'pointer'}
        pins={p:bounded_json_digest(p,role) for p,role in names.items()}
        need(pins[source]==audit['source_sha256']=='9b580b338c8a2bca9b1a65ae5184b05622c457480acfec7ff9ddf169260bf89c')
        need(pins[ledger]=='3e8d7a98cbec1ac8b3a4a00ce546a7eb76014ec61e94e048c0b6ac5fd4f86225' and pins[D/'first-group-training-priority/latest-candidate.json']=='1aee2e01583a024c508d6fdac0d3c4fac2260bbd449ea12269d5e033c1dcc7b4')
        need(not (ledger.parent/'global-ledger.execution.lock').exists())
        value,oldpin,old=read_metadata(config,'local_config','a6113a2563f69c44de9b1834f74a0e06c79b1631d226d816ef12e3adb42beba8')
        need(value['source_manifest_sha256']=='0f436db2c320ca6a3b54ae265470d7c26e1e9d64fc657d35aa12619c3bb73b2b')
        write_new_json_bytes(E/'profile282-before-config-root-20261018.json',old,'local_config')
        value['source_manifest_sha256']=pins[source]
        payload=(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode()
        tmp=config.with_name(config.name+'.root282-new')
        with tmp.open('xb',buffering=0) as stream:write_measured(stream,payload);stream.flush();os.fsync(stream.fileno())
        need(bounded_json_digest(config,'local_config')==oldpin and all(bounded_json_digest(p,role)==pins[p] for p,role in names.items()))
        os.replace(tmp,config)
        configpin=bounded_json_digest(config,'local_config')
        write(E/'profile282-selection-root-20261018.json',{'status':'EXPLICIT_SOURCE_PROFILE_REBOUND_AFTER_AUDITED_ZERO_PATCH279','at_utc':datetime.now(timezone.utc).isoformat(),'old_config_sha256':oldpin,'new_config_sha256':configpin,'source_sha256':pins[source],'narrow_audit_sha256':args.audit_sha256,'candidate_qa_repeated':False,'candidate_promoted':False,'server_restarted':False,'native_executed':False})
        request=urllib.request.Request('http://127.0.0.1:8002/api/data/collection-status',headers={'Origin':'http://127.0.0.1:5174'})
        start=time.monotonic()
        with urllib.request.urlopen(request,timeout=150) as response:
            raw=response.read(2*1024**2+1);code=response.status
        need(len(raw)<=2*1024**2)
        write_new_json_bytes(E/'profile282-api-response-root-20261018.json',raw,'local_plan')
        v=json.loads(raw);t=v.get('collection_targets',{});c=v.get('candidate_quality',{});b=t.get('budget_status',{});bare=t.get('bare_target_review',{})
        checks={'http200':code==200,'raw1364':t.get('eligible_total')==1364,'gap15':t.get('cell_gap_total')==15,'candidate_actual':c.get('eligible_total')==1348,'candidate_stale':c.get('source_matches_current_manifest') is False,'bare50_stale':bare.get('candidate_total')==50 and bare.get('source_matches_current_manifest') is False,'not_ready':c.get('ready_for_training') is False and c.get('blocker_count')==3,'budget_remaining':b.get('remaining_bytes')==1869043250,'oldpending':b.get('old_pending_bytes')==136314880,'operating_pins_preserved':all(bounded_json_digest(p,role)==pins[p] for p,role in names.items()),'config_preserved':bounded_json_digest(config,'local_config')==configpin}
        result={'status':'REAL_API_ZERO_PATCH279_STALE_CANDIDATE_VERIFIED' if all(checks.values()) else 'REAL_API_CHECK_INCOMPLETE','at_utc':datetime.now(timezone.utc).isoformat(),'seconds':round(time.monotonic()-start,3),'checks':checks,'recorded_at':v.get('recorded_at'),'budget_observed_at':b.get('observed_at'),'source_sha256':pins[source],'config_sha256':configpin,'training_started':False,'browser_verified':False,'candidate_qa_repeated':False}
        write(E/'profile282-api-checks-root-20261018.json',result);print(json.dumps(result),flush=True)
        need(all(checks.values()))
if __name__=='__main__':main()
