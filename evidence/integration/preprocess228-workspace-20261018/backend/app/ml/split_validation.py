"""Read-only integrity checks for saved split-repair plans; never authorizes training."""
import copy
import hashlib
import json
import math
import re
from pathlib import Path

from .split_planning import plan_split_repair
from .split_json_io import bounded_io


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key: ' + key)
        result[key] = value
    return result


def _constant(value):
    raise ValueError('Non-finite JSON number: ' + value)


def load_json_document(path, *, io_policy=None, role='saved_plan'):
    """Strict JSON including duplicate-key and non-finite-number rejection."""
    io=bounded_io(io_policy)
    if io is not None:return io.read(path,role)[0]
    payload = Path(path).read_bytes()
    document = json.loads(payload, object_pairs_hook=_pairs, parse_constant=_constant)
    _check_json(document)
    return document


def _check_json(value):
    if type(value) is float and not math.isfinite(value):
        raise ValueError('Non-finite JSON number')
    if type(value) is dict:
        for item in value.values():
            _check_json(item)
    elif type(value) is list:
        for item in value:
            _check_json(item)


def _same(left, right):
    # Python equality otherwise accepts True == 1 and 1 == 1.0.
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return left.keys() == right.keys() and all(_same(left[k], right[k]) for k in left)
    if type(left) is list:
        return len(left) == len(right) and all(_same(a, b) for a, b in zip(left, right))
    return left == right


def _sha(path, *, io_policy=None, role='source'):
    io=bounded_io(io_policy)
    if io is not None:return io.read(path,role)[1]
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_split_repair_plan(saved_plan_path, manifest_path, expected_sha256, *,
                               province_splits, readiness_path=None,
                               readiness_sha256=None, data_root=None,
                               candidate_path=None, candidate_sha256=None, io_policy=None):
    """Recompute from caller-pinned inputs, compare full typed JSON, read only.

    An optional candidate is compared with the exact expected generated document.
    Raster content, geometric overlap, classes, permissions and approval are not checked.
    """
    if (readiness_path is None) != (readiness_sha256 is None):
        raise ValueError('readiness path and SHA-256 must be supplied together')
    if (candidate_path is None) != (candidate_sha256 is None):
        raise ValueError('candidate path and SHA-256 must be supplied together')
    if type(province_splits) is not dict or any(type(k) is not str or type(v) is not str for k, v in province_splits.items()):
        raise ValueError('Explicit province_splits object with string values is required')
    io=bounded_io(io_policy)
    logical_paths=[saved_plan_path,manifest_path]+([readiness_path] if readiness_path is not None else [])+([candidate_path] if candidate_path is not None else [])
    roles=['saved_plan','source']+(['readiness'] if readiness_path is not None else [])+(['candidate'] if candidate_path is not None else [])
    if io is not None:
        bounded_documents=[io.read(path,role) for path,role in zip(logical_paths,roles)]
    paths = [Path(saved_plan_path).resolve(), Path(manifest_path).resolve()]
    if readiness_path is not None:
        paths.append(Path(readiness_path).resolve())
    if candidate_path is not None:
        paths.append(Path(candidate_path).resolve())
    if len(set(paths)) != len(paths):
        raise ValueError('Plan, source, readiness and candidate paths must be distinct')
    if io is None:
        initial = {path: _sha(path) for path in paths}
        documents = {path: load_json_document(path) for path in paths}
    else:
        initial={path:record[1] for path,record in zip(paths,bounded_documents)}
        documents={path:record[0] for path,record in zip(paths,bounded_documents)}
    source = documents[paths[1]]
    if type(source) is not dict:
        raise ValueError('Source must be a JSON object')
    if 'synthetic' in source and type(source['synthetic']) is not bool:
        raise ValueError('Source synthetic flag must be boolean')
    if type(source.get('scenes')) is not list or any(type(row) is not dict or not (type(row.get('year')) is int or (type(row.get('year')) is str and re.fullmatch(r'[0-9]{4}', row['year']))) for row in source.get('scenes', [])):
        raise ValueError('Source scenes require objects with integer or four-digit string year')
    recomputed = plan_split_repair(manifest_path, expected_sha256,
        province_splits=province_splits, readiness_path=readiness_path,
        readiness_sha256=readiness_sha256, data_root=data_root, **({'io_policy':io} if io is not None else {}))
    if not _same(documents[paths[0]], recomputed):
        raise ValueError('Saved split repair plan differs from recomputed caller-pinned plan')
    candidate_checked = candidate_path is not None
    if candidate_checked:
        if type(candidate_sha256) is not str or not re.fullmatch(r'[0-9a-f]{64}', candidate_sha256) or initial[Path(candidate_path).resolve()] != candidate_sha256:
            raise ValueError('Candidate SHA-256 mismatch or invalid explicit SHA-256')
        expected_candidate = {
            'schema_version': 1, 'version': recomputed['derived_manifest_version'],
            'status': 'PLANNED_DERIVED_CANDIDATE', 'executed': False,
            'learning_ready': False, 'synthetic': bool(source.get('synthetic')),
            'lineage': {'source_manifest': recomputed['source_manifest'],
                        'selection_policy': recomputed['policy'],
                        'source_row_indexes': recomputed['retained_row_indexes']},
            'scenes': [copy.deepcopy(source['scenes'][i]) for i in recomputed['retained_row_indexes']]}
        if not _same(documents[Path(candidate_path).resolve()], expected_candidate):
            raise ValueError('Candidate differs from exact retained source rows, lineage or non-execution contract')
    # Planner reopens inputs. Reject changes across both reads and recomputation.
    if io is not None:io.verify()
    if io is None and any(_sha(path) != sha for path, sha in initial.items()):
        raise ValueError('Input changed during validation (stale)')
    return {
        'schema_version': 1, 'status': 'METADATA_INTEGRITY_VERIFIED',
        'evidence_state': recomputed['evidence_state'],
        'plan_integrity_valid': True,
        'saved_plan': {'path': str(paths[0]), 'sha256': initial[paths[0]]},
        'source_manifest': recomputed['source_manifest'],
        'readiness_reference': recomputed['readiness_reference'],
        'derived_manifest_version': recomputed['derived_manifest_version'],
        'candidate_validation': {
            'status': 'EXACT_METADATA_MATCH' if candidate_checked else 'NOT_REQUESTED',
            'candidate_integrity_valid': True if candidate_checked else None,
            'reference': {'path': str(Path(candidate_path).resolve()), 'sha256': candidate_sha256} if candidate_checked else None},
        'projected_after': recomputed['projected_after'],
        'excluded_rows': len(recomputed['excluded_row_indexes']),
        'source_identity_plan_recomputed': True,
        'raster_files_rehashed': False, 'spatial_overlap_rechecked': False,
        'exact_class_counts_recomputed': False, 'ready_for_training': False,
        'training_executed': False, 'scientific_accuracy_validated': False,
        'source_files_written': 0,
        'limitation': 'Metadata integrity only; no candidate publication, raster readiness, spatial/class validation, execution or approval.'}
