import os,sys,time,json,subprocess
from pathlib import Path
import psutil
root=Path.cwd();start=time.monotonic();cap=850*1024**2;timeout=75;peak=0;stopped=None
with (root/'benchmark228-child.log').open('wb') as log:
    child=subprocess.Popen([sys.executable,str(root/'benchmark228-child.py')],cwd=root,env=os.environ.copy(),stdout=log,stderr=subprocess.STDOUT)
    process=psutil.Process(child.pid)
    while child.poll() is None:
        try:peak=max(peak,process.memory_info().rss)
        except psutil.NoSuchProcess:break
        if peak>cap:stopped='RSS_LIMIT';child.terminate();break
        if time.monotonic()-start>timeout:stopped='WALL_LIMIT';child.terminate();break
        time.sleep(.25)
    code=child.wait(timeout=5)
record={'child_count':1,'child_exit_code':code,'stop_reason':stopped,'parent_observed_peak_rss':peak,'rss_cap_bytes':cap,'timeout_seconds':timeout,'elapsed_seconds':round(time.monotonic()-start,3),'automatic_retry':False}
(root/'benchmark228-supervision.json').write_text(json.dumps(record,indent=2),encoding='utf-8');print(json.dumps(record))
