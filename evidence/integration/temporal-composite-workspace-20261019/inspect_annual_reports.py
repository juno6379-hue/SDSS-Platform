import json
from pathlib import Path
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

root = Path(__file__).resolve().parents[3]
annual_dir = root / 'data' / 'first-group-annual'

print(f"Annual dir exists: {annual_dir.exists()}")
plan_file = annual_dir / 'run-plan.json'
if plan_file.exists():
    plan = json.loads(plan_file.read_text(encoding='utf-8'))
    print(f"Plan schema: {plan.get('schema_version')}, expected cells: {plan.get('expected_province_year_cells')}")
    print(f"Tasks: {len(plan.get('tasks', []))}")
    for t in plan.get('tasks', []):
        aois = [a['id'] for a in t['config']['aois']]
        print(f"  Task {t['id']}: aois={aois}, allowance={t['reserved_transfer_allowance']}")

cells_summary = []
for chunk_id in ['chunk-01', 'chunk-02', 'chunk-03']:
    report_file = annual_dir / chunk_id / 'annual-window-report.json'
    if report_file.exists():
        data = json.loads(report_file.read_text(encoding='utf-8'))
        scenes = data.get('scenes', [])
        print(f"\nReport {chunk_id}: status={data.get('status')} scenes={len(scenes)}")
        for s in scenes:
            cells_summary.append({
                'chunk': chunk_id,
                'aoi': s.get('aoi'),
                'year': s.get('year'),
                'status': s.get('status'),
                'cloud_cover': s.get('cloud_cover'),
                'valid_pixel_ratio': s.get('valid_pixel_ratio'),
                'scene_id': s.get('scene_id'),
                'datetime': s.get('datetime'),
                'error': s.get('error'),
            })

print(f"\nTotal scenes/cells found in reports: {len(cells_summary)}")
status_counts = {}
for c in cells_summary:
    st = c['status']
    status_counts[st] = status_counts.get(st, 0) + 1
print("Status counts:", status_counts)

print("\nCell details:")
for c in cells_summary:
    err = c['error']
    err_msg = ""
    if isinstance(err, dict):
        err_msg = f"code={err.get('code') or err.get('http_status')} msg={err.get('message', '')}"
    print(f"  [{c['chunk']}] {c['aoi']} - {c['year']}: status={c['status']} cloud={c['cloud_cover']} valid_ratio={c['valid_pixel_ratio']} err={err_msg}")
