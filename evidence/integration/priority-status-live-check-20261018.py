from pathlib import Path
import urllib.request,json,time,datetime
r=Path(__file__).resolve().parents[2]
start=time.perf_counter()
with urllib.request.urlopen('http://127.0.0.1:8002/api/data/collection-status',timeout=90) as response:
 assert response.status==200
 data=json.load(response)
elapsed=time.perf_counter()-start
assert data['collection_targets']['available'] and data['candidate_quality']['available']
assert data['candidate_quality']['eligible_total']==1106 and data['candidate_quality']['blocker_count']==4
assert data['candidate_quality']['source_matches_current_manifest'] is False
assert data['candidate_quality']['ready_for_training'] is False and data['summary']['learning_ready'] is False
record={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'http_status':200,'elapsed_seconds':elapsed,
 'collection_targets':data['collection_targets'],'candidate_quality':data['candidate_quality'],
 'global_readiness':data['training_readiness']['freshness'],'learning_ready':False,
 'limit':'One local request, no SLA claim. Declaration inventory and frozen candidate cohort remain distinct.'}
(r/'evidence/integration/priority-status-live-final-20261018.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'seconds':elapsed,'raw_eligible':record['collection_targets']['eligible_total'],'candidate_eligible':1106,'blockers':4}))
