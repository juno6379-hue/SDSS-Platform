from pathlib import Path
import cProfile,faulthandler,json,sys,time,traceback
root=Path.cwd()
sys.path.insert(0,str(root/'backend'))
base=root/'evidence/integration'
with (base/'status185-timedump-20261018.log').open('w',encoding='utf-8') as trace:
 faulthandler.enable(file=trace)
 faulthandler.dump_traceback_later(15,repeat=True,file=trace)
 started=time.monotonic()
 from app.collection_status import collection_status
 print('IMPORT_OK',flush=True)
 profile=cProfile.Profile()
 profile.enable()
 try:
  value=collection_status(root/'data')
  profile.disable()
  profile.dump_stats(str(base/'status185-cprofile-20261018.prof'))
  result={'completed':True,'elapsed_seconds':time.monotonic()-started,'physical':value.get('patch_inventory',{}).get('physical_total'),'eligible':value.get('patch_inventory',{}).get('total'),'candidate_available':value.get('candidate_quality',{}).get('available'),'bare_review_status':value.get('collection_targets',{}).get('bare_target_review',{}).get('status')}
  (base/'status185-child-result-20261018.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
  print(json.dumps(result),flush=True)
 finally:
  faulthandler.cancel_dump_traceback_later()
