"""Read-only aggregate/source/ledger metadata reconciliation, never exactly-once proof."""
from collections import defaultdict
from pathlib import Path

from .recovery_terminal import _confined, _fingerprint, _finite, _pairs, _constant
import hashlib
import json


def inspect_recovery_aggregate(data_root):
    requested = Path(data_root)
    if str(requested).startswith(('\\\\', '//')):
        raise ValueError('Data root must be local')
    root = requested.resolve()
    references, logical_targets = {}, {}

    def resolve(path):
        logical = Path(path)
        target = _confined(root, logical)
        if logical in logical_targets and logical_targets[logical] != target:
            raise ValueError('Logical input target changed during inspection')
        logical_targets[logical] = target
        return target

    def read(path):
        target = resolve(path)
        ref = _fingerprint(target)
        if target in references and references[target] != ref:
            raise ValueError('Input changed between repeated reads')
        references[target] = ref
        if not ref['exists']:
            return None, 'MISSING'
        raw = target.read_bytes()
        if hashlib.sha256(raw).hexdigest() != ref['sha256']:
            raise ValueError('Input changed during read')
        try:
            doc = json.loads(raw, object_pairs_hook=_pairs, parse_constant=_constant)
            _finite(doc)
            return (doc, 'PRESENT') if type(doc) is dict else (None, 'INVALID')
        except (ValueError, UnicodeError):
            return None, 'INVALID'

    output = root / 'first-group-training-esri-v1'
    source_scope = resolve(output / 'sources')
    aggregate, aggregate_state = read(output / 'annual-window-report.json')
    ledger, ledger_state = read(root / 'first-group-training-budget/global-ledger.json')
    if aggregate_state != 'PRESENT' or ledger_state != 'PRESENT':
        raise ValueError('Aggregate and ledger must be valid JSON objects')
    if type(aggregate.get('source_manifests')) is not list or type(aggregate.get('scenes')) is not list or type(ledger.get('batches')) is not dict:
        raise ValueError('Invalid aggregate lists or ledger batches')
    issues = []

    def issue(code, **context):
        issues.append({'code': code, **context})

    source_refs = []
    canonical_indexes = defaultdict(list)
    source_index = defaultdict(list)
    for index, value in enumerate(aggregate['source_manifests']):
        if type(value) is not str or not value:
            issue('SOURCE_REFERENCE_INVALID', reference_index=index)
            source_refs.append({'index': index, 'status': 'INVALID'})
            continue
        target = resolve(value)
        canonical_indexes[target].append(index)
        report, state = read(value)
        source_refs.append({'index': index, 'path': str(target), 'status': state})
        if state != 'PRESENT':
            issue('SOURCE_REPORT_' + state, reference_index=index, path=str(target))
            continue
        if type(report.get('scenes')) is not list:
            issue('SOURCE_REPORT_SCENES_INVALID', reference_index=index)
            continue
        for source_row_index, row in enumerate(report['scenes']):
            if type(row) is not dict:
                issue('SOURCE_REPORT_ROW_INVALID', reference_index=index, source_row_index=source_row_index)
                continue
            # materialize_patches only emits rows for downloaded windows.
            if row.get('status') != 'rgb_window_downloaded':
                continue
            path, scene_id = row.get('image_path'), row.get('scene_id')
            if type(path) is not str or not path or type(scene_id) is not str or not scene_id:
                issue('SOURCE_REPORT_ROW_IDENTITY_MISSING', reference_index=index, source_row_index=source_row_index)
                continue
            image = resolve(path)
            source_index[(image, scene_id)].append((str(target), source_row_index))
    duplicates = [{'path': str(path), 'reference_indexes': indexes} for path, indexes in canonical_indexes.items() if len(indexes) > 1]
    for item in duplicates:
        issue('SOURCE_REFERENCE_CANONICAL_DUPLICATE', **item)
    reference_paths = set(canonical_indexes)
    ledger_entries = []
    ledger_reference_keys = defaultdict(list)
    for key, batch in sorted(ledger['batches'].items()):
        if type(batch) is not dict:
            issue('LEDGER_BATCH_INVALID', batch_key=key)
            continue
        path = batch.get('report_path')
        if path is None:
            # Pending worker may not yet have reached ledger settlement.
            if batch.get('status') == 'pending':
                if type(key) is not str or not key or key in ('.', '..') or any(c in key for c in '/\\:'):
                    raise ValueError('Unsafe pending batch key')
                expected = resolve(output / 'sources' / key / 'annual-window-report.json')
                in_refs = expected in reference_paths
                ledger_entries.append({'key': key, 'ledger_status': 'pending', 'scope': 'CURRENT_AGGREGATE', 'report_path': None, 'expected_report_path': str(expected), 'referenced': in_refs})
                if in_refs:
                    issue('PENDING_BATCH_REPORT_REFERENCED', batch_key=key, path=str(expected))
            else:
                ledger_entries.append({'key': key, 'ledger_status': batch.get('status'), 'scope': 'UNKNOWN_NO_REPORT_PATH', 'referenced': None})
                issue('LEDGER_REPORT_SCOPE_UNKNOWN', batch_key=key)
            continue
        if type(path) is not str or not path:
            issue('LEDGER_REPORT_PATH_INVALID', batch_key=key)
            continue
        target = resolve(path)
        in_scope = target.is_relative_to(source_scope) and target.name == 'annual-window-report.json' and target.parent.parent == source_scope
        if not in_scope:
            ledger_entries.append({'key': key, 'ledger_status': batch.get('status'), 'scope': 'OUT_OF_SCOPE', 'report_path': str(target), 'referenced': None})
            continue
        if type(batch.get('status')) is not str or batch['status'] not in ('pending', 'settled'):
            issue('LEDGER_BATCH_STATUS_INVALID', batch_key=key)
        ledger_reference_keys[target].append(key)
        _, state = read(path)
        referenced = target in reference_paths
        ledger_entries.append({'key': key, 'ledger_status': batch.get('status'), 'scope': 'CURRENT_AGGREGATE', 'report_path': str(target), 'artifact_state': state, 'referenced': referenced})
        if state != 'PRESENT':
            issue('LEDGER_SOURCE_REPORT_' + state, batch_key=key, path=str(target))
        if batch.get('status') == 'settled' and not referenced:
            issue('SETTLED_REPORT_NOT_REFERENCED', batch_key=key, path=str(target))
        if batch.get('status') == 'pending' and referenced:
            issue('PENDING_BATCH_REPORT_REFERENCED', batch_key=key, path=str(target))
        if target.parent.name != key:
            issue('LEDGER_KEY_REPORT_DIRECTORY_MISMATCH', batch_key=key, path=str(target))
    for target in reference_paths:
        in_scope = target.is_relative_to(source_scope) and target.name == 'annual-window-report.json' and target.parent.parent == source_scope
        if not in_scope:
            issue('SOURCE_REFERENCE_OUT_OF_SCOPE', path=str(target))
            continue
        keys = ledger_reference_keys.get(target, [])
        # A pending entry without report_path is not a cryptographic ledger link.
        if not keys:
            issue('SOURCE_REFERENCE_LEDGER_UNKNOWN', path=str(target))
        elif len(keys) > 1:
            issue('SOURCE_REFERENCE_LEDGER_AMBIGUOUS', path=str(target), batch_keys=keys)
    patch_ids, patch_images = defaultdict(list), defaultdict(list)
    scene_links = []
    for index, row in enumerate(aggregate['scenes']):
        if type(row) is not dict:
            issue('AGGREGATE_SCENE_INVALID', scene_index=index)
            continue
        patch_id, image = row.get('patch_id'), row.get('image_path')
        if type(patch_id) is str and patch_id:
            patch_ids[patch_id].append(index)
        else:
            issue('PATCH_ID_MISSING_OR_INVALID', scene_index=index)
        if type(image) is str and image:
            patch_images[resolve(image)].append(index)
        else:
            issue('PATCH_IMAGE_PATH_MISSING_OR_INVALID', scene_index=index)
        source = row.get('source_window')
        path = source.get('path') if type(source) is dict else None
        scene_id = row.get('scene_id')
        if type(path) is not str or not path or type(scene_id) is not str or not scene_id:
            issue('SCENE_SOURCE_IDENTITY_MISSING', scene_index=index)
            scene_links.append({'scene_index': index, 'status': 'UNKNOWN_IDENTITY_MISSING'})
            continue
        matches = source_index.get((resolve(path), scene_id), [])
        # Duplicate canonical report references do not invent multiple physical rows.
        matches = sorted(set(matches))
        status = 'UNIQUE_METADATA_MATCH' if len(matches) == 1 else 'MISSING_MATCH' if not matches else 'AMBIGUOUS_MATCH'
        scene_links.append({'scene_index': index, 'status': status, 'matching_source_rows': [{'report_path': p, 'row_index': i} for p, i in matches]})
        if len(matches) != 1:
            issue('SCENE_SOURCE_' + status, scene_index=index)
    duplicate_ids = [{'patch_id': key, 'scene_indexes': indexes} for key, indexes in patch_ids.items() if len(indexes) > 1]
    duplicate_images = [{'image_path': str(key), 'scene_indexes': indexes} for key, indexes in patch_images.items() if len(indexes) > 1]
    for item in duplicate_ids:
        issue('DUPLICATE_PATCH_ID', **item)
    for item in duplicate_images:
        issue('DUPLICATE_PATCH_IMAGE_PATH', **item)
    for logical, target in logical_targets.items():
        if _confined(root, logical) != target:
            raise ValueError('Logical input target changed during inspection')
    for path, reference in references.items():
        if _fingerprint(path) != reference:
            raise ValueError('Input changed during inspection')
    return {'schema_version': 1, 'kind': 'RECOVERY_AGGREGATE_METADATA_RECONCILIATION', 'mode': 'READ_ONLY',
        'status': 'BLOCKED', 'metadata_consistency': 'ISSUES_FOUND' if issues else 'CONSISTENT_METADATA',
        'source_reference_count': len(aggregate['source_manifests']), 'unique_source_reference_count': len(reference_paths),
        'aggregate_scene_count': len(aggregate['scenes']), 'source_references': source_refs,
        'duplicate_source_references': duplicates, 'ledger_report_reconciliation': ledger_entries,
        'duplicate_patch_ids': duplicate_ids, 'duplicate_patch_image_paths': duplicate_images,
        'scene_source_links': scene_links, 'issues': issues, 'artifacts': list(references.values()),
        'exactly_once_applied': 'UNKNOWN', 'raster_files_read': 0, 'source_file_hashes_verified': False, 'scene_link_fields_checked': ['source_window.path', 'scene_id'],
        'scene_year_province_binding': 'NOT_CHECKED', 'scene_year_province_checked': False,
        'crop_window_identity_checked': False,
        'settlement_authorized': False, 'execution_authorized': False, 'automatic_resume_allowed': False,
        'proposed_refund_bytes': 0, 'network_requests': 0, 'source_files_written': 0,
        'limitation': 'JSON metadata and reference consistency only; no raster bytes, transfer proof, process exit, approval or atomic journal verification.'}
