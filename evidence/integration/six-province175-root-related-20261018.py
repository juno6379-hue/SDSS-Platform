"""175 local-plan regression against current targeted consumers; synthetic only."""
from pathlib import Path
import sys,unittest,json,time,hashlib
from datetime import datetime,timezone
R=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(R/'.runtime'),str(R/'tests'),str(R/'backend'),str(R/'scripts')]
modules=['test_targeted_bare_plan','test_collect_targeted_bare','test_targeted_live_guards',
         'test_targeted_collection_hooks','test_data_parallel','test_data_annual_budget']
start=time.perf_counter()
with (R/'evidence/integration/six-province175-root-related-20261018.log').open('x',encoding='utf-8') as stream:
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(modules))
proof={'at':datetime.now(timezone.utc).isoformat(),'modules':modules,'tests':result.testsRun,
       'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),
       'seconds':time.perf_counter()-start,'success':result.wasSuccessful(),
       'source_sha256':hashlib.sha256((R/'backend/app/data/targeted_bare_plan.py').read_bytes()).hexdigest(),
       'test_sha256':hashlib.sha256((R/'tests/test_targeted_bare_plan.py').read_bytes()).hexdigest(),
       'scope':'TESTED_SYNTHETIC_TEMP_LOCAL_GEOTIFF_TEMP_LEDGER_MOCK_HTTP','operating_collection_started':False}
with (R/'evidence/integration/six-province175-root-related-20261018.json').open('x',encoding='utf-8') as stream:json.dump(proof,stream,indent=2)
print(json.dumps(proof));sys.exit(0 if result.wasSuccessful() else 1)
