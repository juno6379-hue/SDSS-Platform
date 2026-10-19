from pathlib import Path
import json, subprocess, sys, time
root=Path.cwd()
base=root/'evidence/integration'
script=base/'status185-fixed-child-20261018.py'
start=time.monotonic()
with (base/'status185-fixed-stdout-20261018.log').open('w',encoding='utf-8') as out,(base/'status185-fixed-stderr-20261018.log').open('w',encoding='utf-8') as err:
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
 (base/'status185-fixed-performance-20261018.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
