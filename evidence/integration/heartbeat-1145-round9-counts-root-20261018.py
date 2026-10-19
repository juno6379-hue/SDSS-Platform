"""Single stable metadata count after round9; native quality owned by178."""
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone
import json,hashlib
R=Path(__file__).resolve().parents[2];E=R/'evidence/integration'
p=R/'data/first-group-training-esri-v1/annual-window-report.json';raw=p.read_bytes();m=json.loads(raw)
rows=[x for x in m['scenes'] if x.get('quality_status')=='quality_eligible']
cells=Counter((x['province'],int(x['year'])) for x in rows)
assert len(cells)==36 and p.read_bytes()==raw
proof={'at':datetime.now(timezone.utc).isoformat(),'source_sha256':hashlib.sha256(raw).hexdigest(),
 'physical_total':len(m['scenes']),'eligible_total':len(rows),'eligible_by_split':dict(Counter(x['split'] for x in rows)),
 'cell_deficit':sum(max(0,28-n) for n in cells.values()),
 'remaining_cells':[{'province':province,'year':year,'eligible':n,'deficit':28-n} for (province,year),n in sorted(cells.items()) if n<28],
 'scope':'STORED_METADATA_ONLY_NATIVE_ROUND9_SEPARATE','stable_second_read':True,'operating_writes':0}
with (E/'heartbeat-1145-round9-counts-root-20261018.json').open('x',encoding='utf-8') as out:json.dump(proof,out,indent=2)
print(json.dumps(proof))
