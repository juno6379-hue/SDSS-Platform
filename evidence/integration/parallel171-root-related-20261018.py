"""171 변경 뒤 기존 수집/예산/표적 계약 회귀. 운영 수집을 호출하지 않는다."""
from pathlib import Path
import sys, unittest, json, time, hashlib
from datetime import datetime, timezone
root=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(root/'.runtime'),str(root/'tests'),str(root/'backend'),str(root/'scripts')]
modules=['test_data_parallel','test_data_annual_budget','test_collect_targeted_bare',
         'test_targeted_live_guards','test_targeted_collection_hooks']
start=time.perf_counter()
with (root/'evidence/integration/parallel171-root-related-20261018.log').open('x',encoding='utf-8') as log:
    suite=unittest.defaultTestLoader.loadTestsFromNames(modules)
    result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
report={'observed_at':datetime.now(timezone.utc).isoformat(),'modules':modules,
        'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
        'skipped':len(result.skipped),'seconds':time.perf_counter()-start,
        'success':result.wasSuccessful(),'scope':'TESTED_SYNTHETIC_TEMP_LEDGER_MOCK_HTTP',
        'source_sha256':hashlib.sha256((root/'backend/app/data/parallel.py').read_bytes()).hexdigest(),
        'test_sha256':hashlib.sha256((root/'tests/test_data_parallel.py').read_bytes()).hexdigest(),
        'actual_collection_started':False}
with (root/'evidence/integration/parallel171-root-related-20261018.json').open('x',encoding='utf-8') as output:
    json.dump(report,output,ensure_ascii=False,indent=2)
print(json.dumps(report,ensure_ascii=True))
sys.exit(0 if result.wasSuccessful() else 1)
