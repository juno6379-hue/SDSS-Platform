"""Run this portable synthetic 64–128MiB + actual node-limit validation once."""
import ctypes
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from app.ml import manifest_resource_profile as profile
from app.data import targeted_bare_plan as plan_module
import test_target325_local_profile as local


def peak_working_set():
    if os.name!='nt':return None
    class Counters(ctypes.Structure):
        _fields_=[('cb',ctypes.c_ulong),('PageFaultCount',ctypes.c_ulong)]+[(n,ctypes.c_size_t) for n in ('PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage')]
    value=Counters();value.cb=ctypes.sizeof(value)
    handle=ctypes.windll.kernel32.GetCurrentProcess()
    ctypes.windll.psapi.GetProcessMemoryInfo.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_ulong]
    if not ctypes.windll.psapi.GetProcessMemoryInfo(handle,ctypes.byref(value),value.cb):return None
    return value.PeakWorkingSetSize


class PortableLargeOnce(unittest.TestCase):
    def test_64plus_json_full_explicit_local_preflight_once(self):
        f=local.LocalPreflightTests();f.setUp()
        try:
            source=f.root/'data/aggregate.json';original=source.read_bytes();size=(64<<20)+4096
            with source.open('wb') as stream:
                stream.write(original);left=size-len(original)
                while left:
                    amount=min(left,1<<20);stream.write(b' '*amount);left-=amount
            digest=hashlib.sha256()
            with source.open('rb') as stream:
                while chunk:=stream.read(65536):digest.update(chunk)
            f.request['plan']['current_manifest_ref']['sha256']=digest.hexdigest()
            start=time.monotonic()
            result=plan_module.prepare_explicit_targeted_bare_jobs(f.root,f.request,f.fixture.base)
            seconds=round(time.monotonic()-start,3)
            self.assertEqual(result['status'],'LOCAL_TARGETS_VERIFIED_EXECUTION_BLOCKED',result)
            self.assertFalse(result['execution_supported']);self.assertFalse(result['coordinator_connected'])
            self.assertGreaterEqual(result['metadata_usage']['read_bytes'],2*size)
            self.assertLess(result['metadata_usage']['json_io_bytes'],16<<30)
            print(json.dumps({'synthetic_source_bytes':size,'sha256':digest.hexdigest(),'explicit_full_local_preflight_seconds':seconds,'metadata_usage':result['metadata_usage'],'windows_process_peak_working_set_sample_bytes':peak_working_set(),'linux_rss_captured':False,'operating_data_read':False,'network':0}),flush=True)
        finally:f.tearDown()

    def test_actual_node4m_overflow_once(self):
        with tempfile.TemporaryDirectory(prefix='target325-nodes-') as directory:
            p=Path(directory)/'nodes.json'
            with p.open('wb') as stream:
                stream.write(b'{"scenes":[],"values":[')
                for _ in range(3999):stream.write(b'0,'*1000)
                stream.write(b'0,'*999+b'0]}')
            with profile.scope(profile.NAME),self.assertRaisesRegex(profile.ProfileResourceError,'MANIFEST_NODE_LIMIT'):
                profile.read_metadata(p,'source',maximum_bytes=128<<20)


if __name__=='__main__':unittest.main(verbosity=2)
