"""Explicit source-profile rebind only after audited publication312; read-only API check."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,os,sys,time,urllib.request
R=Path(__file__).resolve().parents[2];D=R/'data';E=R/'evidence/integration'
sys.path[:0]=[str(R),str(R/'backend')]
from backend.app.ml.manifest_resource_profile import scope,NAME,read_metadata,bounded_json_digest,write_new_json_bytes,write_measured,MARKER

def need(v):
    if not v:raise ValueError('PROFILE313_CONTRACT_FAILED')
def write(p,v):write_new_json_bytes(p,(json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode(),'local_plan')

def main():
    ap=argparse.ArgumentParser(allow_abbrev=False);ap.add_argument('--publication-sha256',required=True);args=ap.parse_args()
    with scope(NAME):
        publication,_,_=read_metadata(E/'priority312-publication-root-20261018.json','local_plan',args.publication_sha256)
        need(publication['status']=='COMPLETED_QA_PUBLISHED_AND_PROFILE_READER_VERIFIED')
        need(publication.get('manifest_profile')==dict(MARKER) and publication.get('exact_retained_rows') is True and publication.get('partition_complete') is True and publication.get('file_sha_mismatches')==0)
        view=publication['candidate_view'];need(type(view.get('eligible_total')) is int and view['eligible_total']>=0 and view.get('source_matches_current_manifest') is True and view.get('ready_for_training') is False and type(view.get('blocker_count')) is int and view['blocker_count']==3)
        source=D/'first-group-training-esri-v1/annual-window-report.json';ledger=D/'first-group-training-budget/global-ledger.json';config=D/'first-group-training-priority/source-profile237-root-20261018.json'
        names={source:'source',ledger:'status_report',D/'first-group-training-priority/latest-candidate.json':'pointer',D/'first-group-training-priority/latest-bare-review.json':'pointer'}
        pins={p:bounded_json_digest(p,role) for p,role in names.items()}
        need(pins[source]==publication['source_snapshot_sha256']=='0c149628ccfa916ee976e561c5da05f9ccc810cbeab7d233a05b9bc7eff54658')
        need(pins[ledger]=='d5ee31ff7970adaaa6b166805c240616efa8e9af713bb8394c7a166346f21c91' and pins[D/'first-group-training-priority/latest-candidate.json']==publication['pointer_sha256'])
        need(not (ledger.parent/'global-ledger.execution.lock').exists())
        value,oldpin,old=read_metadata(config,'local_config','b9a2cd5cfe20bb570281882adcd1f47b4b81b0be4e69c0f0b91d606f0cd17f9e')
        need(value['source_manifest_sha256']=='9e63564c87647a144665bbb6bbe49b4a95d09bbd2c3bc0f3725861c54d5e7109')
        outputs=[E/f'profile313-{name}-root-20261018.json' for name in ('before-config','selection','api-response','api-checks')]
        need(all(not p.exists() and not p.is_symlink() for p in outputs))
        write_new_json_bytes(E/'profile313-before-config-root-20261018.json',old,'local_config')
        value['source_manifest_sha256']=pins[source]
        payload=(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode()
        tmp=config.with_name(config.name+'.root313-new')
        with tmp.open('xb',buffering=0) as stream:write_measured(stream,payload);stream.flush();os.fsync(stream.fileno())
        need(bounded_json_digest(config,'local_config')==oldpin and all(bounded_json_digest(p,role)==pins[p] for p,role in names.items()))
        os.replace(tmp,config)
        configpin=bounded_json_digest(config,'local_config')
        write(E/'profile313-selection-root-20261018.json',{'status':'EXPLICIT_SOURCE_PROFILE_REBOUND_AFTER_POST309_PUBLICATION','at_utc':datetime.now(timezone.utc).isoformat(),'old_config_sha256':oldpin,'new_config_sha256':configpin,'source_sha256':pins[source],'publication_sha256':args.publication_sha256,'candidate_qa_repeated':False,'server_restarted':False,'native_executed':False})
        request=urllib.request.Request('http://127.0.0.1:8002/api/data/collection-status',headers={'Origin':'http://127.0.0.1:5174'})
        start=time.monotonic()
        with urllib.request.urlopen(request,timeout=150) as response:
            raw=response.read(2*1024**2+1);code=response.status
        need(len(raw)<=2*1024**2)
        write_new_json_bytes(E/'profile313-api-response-root-20261018.json',raw,'local_plan')
        v=json.loads(raw);t=v.get('collection_targets',{});c=v.get('candidate_quality',{});b=t.get('budget_status',{});bare=t.get('bare_target_review',{})
        checks={'http200':code==200,'raw1407':t.get('eligible_total')==1407,'gap0':t.get('cell_gap_total')==0,'candidate_actual':c.get('eligible_total')==publication['candidate_view']['eligible_total'],'candidate_current_source':c.get('source_matches_current_manifest') is True,'bare50_stale':bare.get('candidate_total')==50 and bare.get('source_matches_current_manifest') is False,'not_ready':c.get('ready_for_training') is False and c.get('blocker_count')==publication['candidate_view']['blocker_count']==3,'budget_remaining':b.get('remaining_bytes')==1799757940,'oldpending':b.get('old_pending_bytes')==136314880,'operating_pins_preserved':all(bounded_json_digest(p,role)==pins[p] for p,role in names.items()),'config_preserved':bounded_json_digest(config,'local_config')==configpin}
        result={'status':'REAL_API_POST309_CURRENT_CANDIDATE_VERIFIED' if all(checks.values()) else 'REAL_API_CHECK_INCOMPLETE','at_utc':datetime.now(timezone.utc).isoformat(),'seconds':round(time.monotonic()-start,3),'checks':checks,'recorded_at':v.get('recorded_at'),'budget_observed_at':b.get('observed_at'),'source_sha256':pins[source],'config_sha256':configpin,'training_started':False,'browser_verified':False,'candidate_qa_repeated':False}
        write(E/'profile313-api-checks-root-20261018.json',result);print(json.dumps(result),flush=True)
        need(all(checks.values()))
if __name__=='__main__':main()
