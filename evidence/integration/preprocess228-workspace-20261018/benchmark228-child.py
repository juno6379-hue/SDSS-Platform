import sys,time,json,tempfile,gc,os
from pathlib import Path
from backend.app.ml import manifest_resource_profile as profile
from backend.app.ml.candidate_materialization import POLICY
from backend.app.ml.split_json_io import BoundedJSONIO
import psutil
root=Path.cwd();assert Path(sys.modules['backend.app.ml.manifest_resource_profile'].__file__).resolve().is_relative_to(root)
started=time.perf_counter();cpu=time.process_time();records=[]
def emit(value):print(json.dumps(value),flush=True)
def make(path,size):
    prefix=b'{"scenes":[{}]}'
    with path.open('wb') as f:
        f.write(prefix);remaining=size-len(prefix)
        block=b' '*1048576
        while remaining:
            chunk=block[:min(remaining,len(block))];f.write(chunk);remaining-=len(chunk)
def read_case(path,size,selected,valid):
    make(path,size);at=time.perf_counter()
    try:
        with profile.scope(profile.NAME if selected else None) as budget:
            value=BoundedJSONIO(POLICY).read(path,'source')[0]
            assert value=={'scenes':[{}]};status='ACCEPTED';io=budget.bytes if budget else None
    except ValueError as exc:
        status='REJECTED';io=None
    assert (status=='ACCEPTED')==valid
    record={'size':size,'profile_selected':selected,'status':status,'wall_seconds':round(time.perf_counter()-at,3),'profile_json_io_bytes':io}
    records.append(record);emit(record);gc.collect()
with tempfile.TemporaryDirectory(dir=root/'evidence') as directory:
    p=Path(directory)/'boundary.json'
    read_case(p,64*1024**2,False,True)
    read_case(p,64*1024**2+1,False,False)
    read_case(p,64*1024**2+1,True,True)
    read_case(p,128*1024**2,True,True)
    read_case(p,128*1024**2+1,True,False)
    with profile.scope(profile.NAME):
        oversized={'padding':'x'*(128*1024**2+1)}
        try:BoundedJSONIO(POLICY).measure(oversized,'candidate')
        except ValueError:records.append({'candidate_output128_plus1':'REJECTED_BEFORE_WRITE'})
        else:raise AssertionError('output must reject')
        del oversized
    result={'status':'SYNTHETIC_BOUNDARY_BENCHMARK_COMPLETE','cases':records,'wall_seconds':round(time.perf_counter()-started,3),'cpu_seconds':round(time.process_time()-cpu,3),'peak_working_set_bytes':psutil.Process().memory_info().peak_wset,'network_requests':0,'real_qa_runs':0}
    (root/'benchmark228-result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');emit(result)
