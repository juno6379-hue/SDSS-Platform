"""TESTED_SYNTHETIC Temp-only137 actual-main HTTP/browser fixture, not training."""
import copy
import hashlib
import json
import os
from pathlib import Path
from threading import Thread
import time
import urllib.error
import urllib.request

import numpy as np
import rasterio
import uvicorn

from app.dataset_registry import version_key
from test_annual_quality_mask_diagnostics import AnnualQualityMaskDiagnosticsTests

PREFIX = Path(__file__).resolve().parent
TOKEN = 'LOCAL_DIAGNOSTIC_137_ONLY'
PORT = 18037


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def http(url, body=None, token=None):
    headers = {'Content-Type':'application/json'}
    if token is not None: headers['Authorization'] = 'Bearer '+token
    request = urllib.request.Request(url, data=body, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            raw = response.read(65536); status = response.status; response_headers = dict(response.headers)
    except urllib.error.HTTPError as error:
        raw = error.read(65536); status = error.code; response_headers = dict(error.headers)
    try: value = json.loads(raw)
    except (ValueError, UnicodeError): value = None
    return {'http_status':status,'body':value,'cache_control':response_headers.get('cache-control',response_headers.get('Cache-Control'))}


def main():
    fixture = AnnualQualityMaskDiagnosticsTests(); fixture.setUp()
    server = None; thread = None
    try:
        for index, row in enumerate(fixture.rows[:2]):
            path = fixture.mask_paths[index]
            values = np.zeros((16,16),dtype='uint8'); values[:8,:] = 1
            with rasterio.open(path,'r+') as dataset: dataset.write(values,1)
            row['mask_ref']['sha256'] = sha(path.read_bytes())
            record = fixture.store.get('dataset_versions',version_key(row['mask_ref']['id'],row['mask_ref']['version']))
            record['manifest']['sha256'] = row['mask_ref']['sha256']; fixture.raster.save(record)
            quality = fixture.store.get('dataset_versions',version_key(row['quality_report_ref']['id'],row['quality_report_ref']['version']))
            report_path = fixture.store.root / quality['manifest']['artifact_uri']
            report = json.loads(report_path.read_text(encoding='utf-8')); report['mask_ref'] = dict(row['mask_ref'])
            report_path.write_text(json.dumps(report,ensure_ascii=False),encoding='utf-8')
            row['quality_report_ref']['sha256'] = sha(report_path.read_bytes())
            quality['manifest']['sha256'] = row['quality_report_ref']['sha256']
            for parent in quality['manifest']['lineage']:
                if parent.get('role') == 'quality_input_mask': parent.update(row['mask_ref'])
            fixture.raster.save(quality)
        model = fixture.store.get('models',fixture.model.model_ref['id'])
        model['name'] = 'TESTED_SYNTHETIC137_TEMP_ONLY_NO_TRAINING'
        fixture.store.put('models',model)
        request = {'schema_version':1,'capability':'landcover.input_diagnostics',
            'model_ref':copy.deepcopy(fixture.model.model_ref),'training_report_sha256':fixture.model.report_sha,
            'requested_years':copy.deepcopy(fixture.rows[:2]),'policy':{'schema_version':1,'minimum_valid_numerator':1,
                'minimum_valid_denominator':2,'comparison':'greater_than_or_equal'}}
        (PREFIX/'diagnostic-api-live-request-20261018.json').write_text(json.dumps(request,ensure_ascii=False,indent=2),encoding='utf-8')
        os.environ['GEOAI_DATA_ROOT'] = str(fixture.store.root)
        os.environ['GEOAI_API_TOKEN'] = TOKEN
        from app.main import app
        server = uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=PORT,reload=False,log_level='warning'))
        thread = Thread(target=server.run,daemon=False); thread.start()
        for _ in range(1000):
            if server.started: break
            if not thread.is_alive(): raise RuntimeError('Fixture server exited')
            time.sleep(.01)
        if not server.started: raise RuntimeError('Fixture server did not start')
        url = f'http://127.0.0.1:{PORT}/v1/lcluc/input-diagnostics'
        raw = json.dumps(request).encode()
        checks = {'missing_token':http(url,raw),'wrong_token':http(url,raw,'wrong'),
            'policy_met':http(url,raw,TOKEN)}
        not_met = copy.deepcopy(request); not_met['policy'].update(minimum_valid_numerator=500001,minimum_valid_denominator=1000000)
        checks['policy_not_met'] = http(url,json.dumps(not_met).encode(),TOKEN)
        checks['invalid'] = http(url,b'{}',TOKEN)
        checks['oversize'] = http(url,b'x'*16385,TOKEN)
        assert [checks[key]['http_status'] for key in ('missing_token','wrong_token','policy_met','policy_not_met','invalid','oversize')] == [401,401,200,200,422,413]
        assert checks['policy_met']['body']['status'] == 'CALLER_POLICY_MET_UNVERIFIED'
        assert checks['policy_not_met']['body']['status'] == 'CALLER_POLICY_NOT_MET'
        assert [row['counts'] for row in checks['policy_met']['body']['per_year_observations']] == [
            {'valid_pixels':128,'invalid_pixels':128,'total_pixels':256}]*2
        operating = {}
        try:
            opened = http('http://127.0.0.1:8002/openapi.json')
            document = opened['body'] or {}
            operating['openapi_status'] = opened['http_status']
            operating['endpoint_present'] = '/v1/lcluc/input-diagnostics' in document.get('paths',{})
            operating['unauthenticated_empty_request'] = http('http://127.0.0.1:8002/v1/lcluc/input-diagnostics',b'{}')
        except Exception as error:
            operating = {'observation_unavailable':type(error).__name__}
        evidence = {'scope':'TESTED_SYNTHETIC_TEMP_ACTUAL_MAIN_HTTP_NO_TRAINING_NO_INFERENCE',
            'fixture_pid':os.getpid(),'port':PORT,'data_root':str(fixture.store.root),
            'model_ref':request['model_ref'],'model_status':model.get('status'),
            'model_name':model['name'],'checks':checks,'operating_8002_read_only_observation':operating,
            'operating_writes':0,'operating_token_read':False,'training_inference':0,
            'limitations':['Random untrained Temp checkpoint; weights-only manifest load, no model forward.',
                'Binary128/128 is a constructed fixture, not real QA/accuracy/authority or readiness.',
                'Actual main is imported only after GEOAI_DATA_ROOT points to TempStore.']}
        (PREFIX/'diagnostic-api-live-http-20261018.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'ready':True,'port':PORT,'pid':os.getpid(),'fixture_root':str(fixture.store.root)},ensure_ascii=True),flush=True)
        thread.join()
    except KeyboardInterrupt:
        pass
    finally:
        if server is not None: server.should_exit = True
        if thread is not None: thread.join(timeout=30)
        if thread is None or not thread.is_alive():
            fixture.doCleanups()
            print('TEMP_FIXTURE_CLEANED',flush=True)


if __name__ == '__main__':
    main()
