from pathlib import Path
import json,subprocess,sys
r=Path.cwd();e=r/'evidence/integration';pin=json.loads((e/'targeted170-live-request-pin-20261018.json').read_text('utf-8'))['request_sha256']
with (e/'targeted170-dryrun-20261018.log').open('xb') as f:
 result=subprocess.run([sys.executable,str(r/'scripts/collect_targeted_bare.py'),'--request',str(e/'targeted170-live-request-20261018.json'),'--expected-request-sha256',pin],stdout=f,stderr=subprocess.STDOUT)
print(json.dumps({'returncode':result.returncode}));sys.exit(result.returncode)
