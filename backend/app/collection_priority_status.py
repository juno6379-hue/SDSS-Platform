"""Read-only counts from the collector manifest; no raster QA or execution."""
from collections import Counter, defaultdict
import json
from pathlib import Path

PROVINCES = ('south_sulawesi', 'gorontalo', 'southeast_sulawesi', 'east_java', 'banten', 'west_java')
YEARS = tuple(range(2020, 2026))
SPLITS = {p: 'train' for p in PROVINCES} | {'banten': 'val', 'west_java': 'test'}


def candidate_quality(root, current_sha256, same_hash):
    """Read an explicitly published candidate receipt, never choose a newest glob."""
    unavailable = {'available': False, 'ready_for_training': False}
    path = Path(root) / 'first-group-training-priority/latest-candidate.json'
    try:
        if path.stat().st_size > 65536:
            return unavailable
        receipt = json.loads(path.read_text('utf-8'))
        files = receipt['files']
        if not isinstance(files, list) or len(files) != 3:
            return unavailable
        for entry in files:
            target = (Path(root) / entry['path']).resolve()
            if not target.is_relative_to(Path(root).resolve()) or not same_hash(target, entry['sha256']):
                return unavailable
        counts = receipt['by_split']
        if set(counts) != {'train', 'val', 'test'} or any(type(n) is not int or n < 0 for n in counts.values()):
            return unavailable
        if type(receipt['blocker_count']) is not int or receipt['blocker_count'] < 0:
            return unavailable
        qa_path = (Path(root) / files[2]['path']).resolve()
        if qa_path.stat().st_size > 16 * 1024 * 1024:
            return unavailable
        qa = json.loads(qa_path.read_text('utf-8'))
        if qa.get('patch_counts_by_split') != counts or len(qa.get('blockers', [])) != receipt['blocker_count']:
            return unavailable
        if files[0]['sha256'] != receipt['source_manifest_sha256'] or receipt['scene_split_conflicts'] != []:
            return unavailable
        return {'available': True, 'source_manifest_sha256': receipt['source_manifest_sha256'],
            'eligible_total': sum(counts.values()), 'by_split': counts,
            'ready_for_training': False, 'blocker_count': receipt['blocker_count'],
            'source_pins_match': True, 'source_matches_current_manifest': receipt['source_manifest_sha256'] == current_sha256,
            'source_report': files[2]['path'], 'recorded_at': receipt['recorded_at'],
            'scene_split_conflicts': receipt['scene_split_conflicts'],
            'scientific_accuracy_validated': False,
            'scope': 'PINNED_CANDIDATE_COHORT_NOT_AUTOMATIC_CURRENT_COLLECTION'}
    except (OSError, KeyError, TypeError, ValueError):
        return unavailable


def collection_targets(manifest, source_sha256):
    unavailable = {'available': False, 'learning_ready': False, 'scientific_accuracy_validated': False}
    scenes = manifest.get('scenes') if isinstance(manifest, dict) else None
    if not isinstance(scenes, list) or not scenes or not source_sha256:
        return unavailable
    physical, eligible = Counter(), Counter()
    pixels = {s: Counter() for s in ('train', 'val', 'test')}
    contributing = Counter()
    scene_splits = defaultdict(set)
    try:
        for row in scenes:
            province, year = row['province'], int(row['year'])
            if province not in PROVINCES or year not in YEARS or row.get('split') != SPLITS[province]:
                return unavailable
            physical[province] += 1
            if row.get('quality_status') != 'quality_eligible':
                continue
            eligible[province, year] += 1
            split = SPLITS[province]
            histogram = row.get('sample_class_coverage', {})
            if not isinstance(histogram, dict) or any(type(n) is not int or n < 0 for n in histogram.values()):
                return unavailable
            pixels[split].update(histogram)
            contributing[split] += histogram.get('8', 0) >= 256
            if isinstance(row.get('scene_id'), str) and row['scene_id']:
                scene_splits[row['scene_id']].add(split)
    except (KeyError, TypeError, ValueError, OverflowError):
        return unavailable
    rows = []
    for province in PROVINCES:
        counts = {str(y): eligible[province, y] for y in YEARS}
        rows.append({'province': province, 'split': SPLITS[province], 'physical': physical[province],
                     'eligible': sum(counts.values()), 'year_counts': counts,
                     'cell_gap': sum(max(0, 28 - n) for n in counts.values())})
    total = sum(eligible.values())
    return {'available': True, 'source_manifest_sha256': source_sha256,
            'count_basis': 'manifest_quality_status', 'physical_total': len(scenes),
            'eligible_total': total, 'ineligible_total': len(scenes) - total,
            'eligible_target': 1200, 'eligible_target_gap': max(0, 1200 - total),
            'cell_floor': 28, 'cell_gap_total': sum(r['cell_gap'] for r in rows), 'rows': rows,
            'minimum_valid_fraction': .8, 'minimum_province_fraction': .95,
            'class_quality': {'required_fraction': .005, 'minimum_contributing_patches': 5,
                'minimum_pixels_per_contributing_patch': 256, 'minimum_pixels_per_split': 256,
                'max_dominance': .9,
                'bare_by_split': {s: {'pixels': pixels[s]['8'],
                    'ratio': pixels[s]['8'] / sum(pixels[s].values()) if sum(pixels[s].values()) else None,
                    'contributing_patches': contributing[s]} for s in pixels},
                'scene_split_conflicts': sorted(k for k, splits in scene_splits.items() if len(splits) > 1)},
            'native_raster_reverified': False, 'learning_ready': False, 'scientific_accuracy_validated': False}
