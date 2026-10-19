from pathlib import Path
import json,time
from collections import Counter
root=Path.cwd()/'data'; t=time.monotonic()
paths=sorted(root.glob('first-group*/**/annual-window-report.json'),key=lambda p:(p.stat().st_mtime_ns,str(p)))[-64:]
fields=Counter(); unique=set(); rows=0; totalbytes=0
for p in paths:
 totalbytes+=p.stat().st_size
 v=json.loads(p.read_text(encoding='utf-8'))
 for row in v.get('scenes',[]):
  rows+=1
  for key in ('image_path','label_path','quality_mask_path'):
   x=row.get(key)
   if isinstance(x,str) and x:
    fields[key]+=1;unique.add(x)
r={'scope':'report_json_only_no_path_resolve_no_file_hash_no_raster_qa','reports_last64':len(paths),'scene_rows':rows,'path_field_calls_potential':dict(fields),'unique_declared_paths':len(unique),'json_bytes':totalbytes,'elapsed_seconds':time.monotonic()-t}
(Path.cwd()/'evidence/integration/status185-report-shape-20261018.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
print(json.dumps(r))
