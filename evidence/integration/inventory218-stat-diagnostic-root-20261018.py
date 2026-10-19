from pathlib import Path
import sys,json,hashlib
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'backend'))
from app.data.targeted_inventory import _files,LABELS,SOURCE
mp=R/'data/first-group-training-esri-v1/annual-window-report.json';lp=R/'data/first-group-training-budget/global-ledger.json'
pins={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [mp,lp]}
manifest=json.loads(mp.read_text('utf-8'));ledger=json.loads(lp.read_text('utf-8'))
roots={R/SOURCE}
for row in ledger['batches'].values():
 if row.get('report_path') is not None:
  p=Path(row['report_path']);roots.add((p if p.is_absolute() else R/p).parent)
roots={p for p in roots if not any(p!=other and p.is_relative_to(other) for other in roots)}
files=sorted({p for base in roots for p in _files(R,base,10000)})
assets={p for p in files if p.name not in LABELS}
for row in manifest['scenes']+manifest.get('historical_noneligible_patches',[]):
 p=Path(row['source_window']['path']);assets.add(p if p.is_absolute() else R/p)
total=sum(p.stat().st_size for p in assets)
record={'scope':'STAT_ONLY_NO_RASTER_NO_HASH_INVENTORY_REEXECUTION','all_files':len(files),'assets':len(assets),'total_support_bytes':total,'default_support_cap':2*1024**3,'over_cap':total>2*1024**3,'source_and_ledger_pins':pins,'max_single_asset_bytes':max(p.stat().st_size for p in assets)}
assert all(hashlib.sha256((R/p).read_bytes()).hexdigest()==h for p,h in pins.items())
with (R/'evidence/integration/inventory218-stat-diagnostic-root-20261018.json').open('x',encoding='utf-8') as f:json.dump(record,f,indent=2)
print(json.dumps(record))
