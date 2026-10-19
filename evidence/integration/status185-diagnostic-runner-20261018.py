from pathlib import Path
import json, subprocess, sys, time
root=Path.cwd()
base=root/'evidence/integration'
script=base/'status185-diagnostic-child-20261018.py'
script.write_text('''from pathlib import Path\nimport cProfile,faulthandler,json,sys,time,traceback\nroot=Path.cwd()\nsys.path.insert(0,str(root/'backend'))\nbase=root/'evidence/integration'\nwith (base/'status185-timedump-20261018.log').open('w',encoding='utf-8') as trace:\n faulthandler.enable(file=trace)\n faulthandler.dump_traceback_later(15,repeat=True,file=trace)\n started=time.monotonic()\n from app.collection_status import collection_status\n print('IMPORT_OK',flush=True)\n profile=cProfile.Profile()\n profile.enable()\n try:\n  value=collection_status(root/'data')\n  profile.disable()\n  profile.dump_stats(str(base/'status185-cprofile-20261018.prof'))\n  result={'completed':True,'elapsed_seconds':time.monotonic()-started,'physical':value.get('patch_inventory',{}).get('physical_total'),'eligible':value.get('patch_inventory',{}).get('total'),'candidate_available':value.get('candidate_quality',{}).get('available'),'bare_review_status':value.get('collection_targets',{}).get('bare_target_review',{}).get('status')}\n  (base/'status185-child-result-20261018.json').write_text(json.dumps(result,indent=2),encoding='utf-8')\n  print(json.dumps(result),flush=True)\n finally:\n  faulthandler.cancel_dump_traceback_later()\n''',encoding='utf-8')
start=time.monotonic()
with (base/'status185-stdout-20261018.log').open('w',encoding='utf-8') as out,(base/'status185-stderr-20261018.log').open('w',encoding='utf-8') as err:
 proc=subprocess.Popen([sys.executable,str(script)],stdout=out,stderr=err,cwd=root)
 result={'diagnostic_pid':proc.pid,'server_mutations':0,'http_requests':0,'native_raster_qa':False}
 try:
  result['exit_code']=proc.wait(timeout=60)
  result['timed_out']=False
 except subprocess.TimeoutExpired:
  result['timed_out']=True
  proc.kill();proc.wait()
  result['exit_code']=proc.returncode
 result['elapsed_seconds']=time.monotonic()-start
 (base/'status185-performance-20261018.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
