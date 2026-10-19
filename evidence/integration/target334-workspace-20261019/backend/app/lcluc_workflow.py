"""Bounded local LCLUC execution, separate from GMAIS Jobs and scientific approval."""
import hashlib
import json
from pathlib import Path
import re

from .dataset_registry import resolve_version, version_key
from .model_reference_contract import model_reference_issue
from .model_registration_provenance import inspect_model_registration_provenance
from .sdss_results import local_asset
from .store import now

KIND = 'lcluc_workflows'
CAPABILITY = 'landcover.change_detection'
MAX_INPUT_BYTES = 64 * 1024**2
MAX_CHECKPOINT_BYTES = 8 * 1024**2
MAX_READ_ESTIMATE = 128 * 1024**2
MAX_OUTPUT_BYTES = 256 * 1024**2


class WorkflowError(ValueError):
    """Only fixed codes, never native exceptions/paths, cross this boundary."""


def _need(condition, code):
    if not condition:
        raise WorkflowError(code)


def _keys(value, fields):
    return type(value) is dict and len(value) == len(fields) and all(type(k) is str for k in value) and set(value) == set(fields)


def _sha(value):
    return type(value) is str and re.fullmatch('[a-f0-9]{64}', value) is not None


def _canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False, separators=(',', ':'))


def strict_request_json(raw):
    _need(type(raw) is bytes and len(raw) <= 16384, 'INVALID_REQUEST')
    def pairs(items):
        result = {}
        for key, value in items:
            _need(key not in result, 'INVALID_REQUEST')
            result[key] = value
        return result
    def invalid(_):
        raise WorkflowError('INVALID_REQUEST')
    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid, parse_float=invalid)
    except (ValueError, UnicodeError, RecursionError):
        raise WorkflowError('INVALID_REQUEST') from None


def _request(value):
    _need(_keys(value, ('schema_version', 'capability', 'trace_id', 'idempotency_key', 'model_ref', 'images')), 'INVALID_REQUEST')
    _need(type(value['schema_version']) is int and value['schema_version'] == 1
          and type(value['capability']) is str and value['capability'] == CAPABILITY, 'INVALID_REQUEST')
    for field in ('trace_id', 'idempotency_key'):
        _need(type(value[field]) is str and 1 <= len(value[field]) <= 128 and re.fullmatch('[A-Za-z0-9_-]+', value[field]) is not None, 'INVALID_REQUEST')
    def reference(ref):
        _need(_keys(ref, ('id', 'version', 'sha256')), 'INVALID_REQUEST')
        _need(model_reference_issue(ref) is None and _sha(ref['sha256']), 'INVALID_REQUEST')
        _need(all(re.fullmatch('[A-Za-z0-9_.-]{1,128}', ref[field]) is not None for field in ('id', 'version')), 'INVALID_REQUEST')
    reference(value['model_ref'])
    images = value['images']
    _need(type(images) is list and 2 <= len(images) <= 6, 'INVALID_REQUEST')
    for item in images:
        _need(_keys(item, ('year', 'input_ref', 'quality_report_sha256')), 'INVALID_REQUEST')
        _need(type(item['year']) is int and 1900 <= item['year'] <= 2200 and _sha(item['quality_report_sha256']), 'INVALID_REQUEST')
        reference(item['input_ref'])
    years = [item['year'] for item in images]
    _need(years == sorted(set(years)), 'INVALID_REQUEST')
    raw = _canonical(value).encode()
    _need(len(raw) <= 16384, 'INVALID_REQUEST')
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def _file(path, maximum):
    before = path.stat()
    _need(path.is_file() and before.st_size <= maximum, 'FILE_LIMIT_OR_INTEGRITY')
    digest = hashlib.sha256()
    count = 0
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(min(1024**2, maximum-count+1)), b''):
            count += len(block)
            _need(count <= maximum, 'FILE_LIMIT_OR_INTEGRITY')
            digest.update(block)
    after = path.stat()
    _need((before.st_size, before.st_mtime_ns, before.st_ctime_ns) == (after.st_size, after.st_mtime_ns, after.st_ctime_ns), 'FILE_LIMIT_OR_INTEGRITY')
    return digest.hexdigest()


def _output(root, identifier, *, absent):
    path = root / 'results' / 'lcluc-workflows' / identifier
    _need(path.resolve() == path and (not absent or not path.exists()), 'OUTPUT_NAMESPACE_UNAVAILABLE')
    return path


def _gate(store, request, identifier):
    import numpy as np
    import rasterio
    import torch
    from .ml.network import TinyUNet
    from .ml.normalization import channel_values
    root = Path(store.root).resolve()
    _output(root, identifier, absent=True)
    ref = request['model_ref']
    model = store.get('models', ref['id'])
    _need(model.get('id') == ref['id'], 'MODEL_IDENTITY_MISMATCH')
    _need(model.get('status') == 'Deployed' and model.get('independent_evaluation') is True, 'MODEL_NOT_DEPLOYED_OR_EVALUATED')
    evaluation = model.get('evaluation')
    _need(type(evaluation) is dict and evaluation.get('reference_kind') == 'expert_independent'
          and evaluation.get('checkpoint_sha256') == ref['sha256'], 'MODEL_EVALUATION_MISMATCH')
    _need(inspect_model_registration_provenance(model)['status'] == 'CONSISTENT_UNVERIFIED'
          and model['model_version_declaration']['version'] == ref['version']
          and model['checkpoint_sha256'] == ref['sha256'], 'MODEL_VERSION_NOT_BOUND')
    checkpoint = local_asset(root, model.get('checkpoint_path'))
    _need(_file(checkpoint, MAX_CHECKPOINT_BYTES) == ref['sha256'], 'CHECKPOINT_MISMATCH')
    training_report = local_asset(root, str((checkpoint.parent / 'report.json').relative_to(root)))
    _need(_file(training_report, 2 * 1024**2) == model['training_report_sha256'], 'TRAINING_REPORT_MISMATCH')
    saved = torch.load(checkpoint, map_location='cpu', weights_only=True)
    _need(type(saved) is dict and saved.get('architecture') == 'tiny_unet', 'MODEL_ARCHITECTURE_UNSUPPORTED')
    manifest = saved.get('manifest')
    _need(type(manifest) is dict and model.get('synthetic') is False and manifest.get('synthetic') is False,
          'SYNTHETIC_MODEL_BLOCKED')
    for kind in (model.get('reference_kind'), manifest.get('reference_kind')):
        _need(type(kind) is str and 1 <= len(kind) <= 128 and not kind.strip().lower().startswith('synthetic'), 'SYNTHETIC_MODEL_BLOCKED')
    _need(manifest.get('normalization_mode', 'global') == 'global', 'NORMALIZATION_MODE_UNSUPPORTED')
    bands, names = manifest.get('bands'), manifest.get('band_names')
    _need(type(bands) is list and 1 <= len(bands) <= 16 and all(type(b) is int and 1 <= b <= 16 for b in bands)
          and len(set(bands)) == len(bands) and type(names) is list and len(names) == len(bands)
          and all(type(n) is str and 1 <= len(n) <= 64 for n in names), 'MODEL_BAND_SIGNATURE_INVALID')
    _need(type(manifest.get('class_names')) is list and len(manifest['class_names']) == 9
          and all(type(n) is str and 1 <= len(n) <= 128 for n in manifest['class_names']), 'MODEL_CLASSES_INVALID')
    patch_size = manifest.get('patch_size')
    _need(type(patch_size) is int and 4 <= patch_size <= 256, 'MODEL_PATCH_LIMIT')
    channel_values(manifest.get('scale'), len(bands), 'scale')
    channel_values(manifest.get('offset'), len(bands), 'offset')
    TinyUNet(len(bands)).load_state_dict(saved['state_dict'])
    model_metadata = _canonical(model).encode()
    _need(len(model_metadata) <= 2 * 1024**2, 'MODEL_METADATA_LIMIT')
    pins = {'model': hashlib.sha256(model_metadata).hexdigest()}
    images, estimated = [], 0
    for item in request['images']:
        source = item['input_ref']
        preliminary = store.get('dataset_versions', version_key(source['id'], source['version']))
        preliminary_path = local_asset(root, preliminary['manifest']['artifact_uri'])
        _need(preliminary_path.stat().st_size <= MAX_INPUT_BYTES, 'FILE_LIMIT_OR_INTEGRITY')
        record = resolve_version(store, source['id'], source['version'], source['sha256'])
        data = record['manifest']
        _need(data['quality_status'] == 'VALIDATED' and data['access_class'] == 'PUBLIC'
              and data['data_type'] == 'raster', 'DATASET_QUALITY_OR_ACCESS_BLOCKED')
        _need(int(data['temporal']['start'][:4]) == item['year'] == int(data['temporal']['end'][:4]), 'DATASET_YEAR_MISMATCH')
        image = local_asset(root, data['artifact_uri'])
        _need(_file(image, MAX_INPUT_BYTES) == source['sha256'], 'INPUT_INTEGRITY_MISMATCH')
        quality = local_asset(root, data['quality_report_ref'])
        _need(_file(quality, 2 * 1024**2) == item['quality_report_sha256'], 'QUALITY_REPORT_MISMATCH')
        with rasterio.open(image) as raster:
            _need(raster.crs is not None and 4 <= raster.width <= 1024 and 4 <= raster.height <= 1024
                  and 1 <= raster.count <= 16 and max(bands) <= raster.count, 'RASTER_LIMIT_OR_BANDS')
            _need([raster.descriptions[b-1] for b in bands] == names, 'RASTER_BAND_SIGNATURE_MISMATCH')
            estimated += raster.width * raster.height * (sum(np.dtype(d).itemsize for d in raster.dtypes) + 4 * len(bands) + 2)
        _need(estimated <= MAX_READ_ESTIMATE, 'RASTER_READ_BUDGET_EXCEEDED')
        pins[str(item['year'])] = record['manifest_sha256']
        images.append({'year': item['year'], 'image_path': str(image.relative_to(root)),
                       'source': data['source']['product'], 'license': data['source']['license']})
    payload = {'checkpoint_path': str(checkpoint.relative_to(root)), 'images': images,
               'output_id': 'lcluc-workflows/' + identifier}
    return payload, pins


def _existing(record, digest, root):
    _need(type(record) is dict and record.get('request_sha256') == digest, 'IDEMPOTENCY_CONFLICT')
    _need(record.get('status') in ('RUNNING', 'BLOCKED', 'FAILED', 'SUCCEEDED'), 'STORED_STATE_INVALID')
    if record['status'] == 'SUCCEEDED':
        try:
            for artifact in record['artifacts']:
                _need(_file(local_asset(root, artifact['path']), MAX_OUTPUT_BYTES) == artifact['sha256'], 'STORED_OUTPUT_CHANGED')
        except Exception:
            raise WorkflowError('STORED_OUTPUT_CHANGED') from None
    return {**record, 'replayed': True}


def _execute(store, request, *, _runner=None):
    """Explicit local call; _runner is only a test seam, never a CLI option.

    RUNNING after interruption is not automatically resumed. Scientific approval,
    issuer authentication and filesystem/SQLite atomicity are not claimed.
    """
    request, digest = _request(request)
    identifier = hashlib.sha256(request['idempotency_key'].encode()).hexdigest()
    root = Path(store.root).resolve()
    try:
        return _existing(store.get(KIND, identifier), digest, root)
    except KeyError:
        pass
    except WorkflowError:
        raise
    except Exception:
        raise WorkflowError('LOCAL_WORKFLOW_UNAVAILABLE') from None
    # No output or claim is created if the first admission gate fails.
    try:
        _, first_pins = _gate(store, request, identifier)
    except Exception as error:
        # Another dispatcher may have claimed and created its output after our
        # initial miss. Read its state instead of inventing a new BLOCKED state.
        try:
            concurrent = store.get(KIND, identifier)
        except KeyError:
            concurrent = None
        if concurrent is not None:
            return _existing(concurrent, digest, root)
        code = str(error) if type(error) is WorkflowError else 'ADMISSION_GATE_BLOCKED'
        return {'schema_version': 1, 'scope': 'LOCAL_LCLUC_WORKFLOW_ONLY', 'status': 'BLOCKED',
                'trace_id': request['trace_id'], 'id': identifier, 'issue': code, 'replayed': False,
                'scientific_accuracy_validated': False, 'standard_gmais_result': False}
    record = {'schema_version': 1, 'scope': 'LOCAL_LCLUC_WORKFLOW_ONLY', 'id': identifier,
              'trace_id': request['trace_id'], 'request_sha256': digest, 'status': 'RUNNING',
              'request_snapshot': {key: request[key] for key in ('schema_version', 'capability', 'trace_id', 'model_ref', 'images')},
              'created_at': now(), 'issue': None, 'artifacts': [],
              'scientific_accuracy_validated': False, 'standard_gmais_result': False}
    claimed_body = _canonical(record)
    with store.connect() as connection:
        connection.execute('BEGIN IMMEDIATE')
        previous = connection.execute('SELECT body FROM records WHERE kind=? AND id=?', (KIND, identifier)).fetchone()
        if not previous:
            connection.execute('INSERT INTO records VALUES(?,?,?)', (KIND, identifier, claimed_body))
    if previous:
        return _existing(json.loads(previous[0]), digest, root)
    try:
        payload, pins = _gate(store, request, identifier)
        _need(pins == first_pins, 'ADMISSION_CHANGED_AFTER_CLAIM')
        if _runner is None:
            from .ml.service import analyze_timeseries
            _runner = analyze_timeseries
        _output(root, identifier, absent=True)
        report = _runner(payload, root)
        _canonical(report)  # Non-finite output values must not be recorded as success.
        _output(root, identifier, absent=False)
        report_path = local_asset(root, 'results/' + payload['output_id'] + '/timeseries.json')
        _need(report.get('report_path') == str(report_path.relative_to(root))
              and report.get('checkpoint_sha256') == request['model_ref']['sha256'], 'RUNNER_REPORT_MISMATCH')
        # Rasterio geometry may contain tuple coordinates; JSON represents these
        # as arrays. Compare their finite canonical JSON, preserving value/type
        # differences while accepting that serialization representation change.
        _need(report_path.stat().st_size <= 8 * 1024**2
              and _canonical(json.loads(report_path.read_text(encoding='utf-8'))) == _canonical(report), 'RUNNER_REPORT_MISMATCH')
        output = report_path.parent
        total, artifacts = 0, []
        for path in sorted(output.rglob('*')):
            _need(not path.is_symlink() and path.resolve().is_relative_to(output), 'OUTPUT_PATH_CHANGED')
            if path.is_file():
                total += path.stat().st_size
                _need(total <= MAX_OUTPUT_BYTES and len(artifacts) < 128, 'OUTPUT_LIMIT')
                artifacts.append({'path': str(path.relative_to(root)), 'sha256': _file(path, MAX_OUTPUT_BYTES)})
        record.update(status='SUCCEEDED', report_path=str(report_path.relative_to(root)), artifacts=artifacts,
                      admission_pins=pins)
    except Exception as error:
        record.update(status='FAILED', issue=str(error) if type(error) is WorkflowError else 'LOCAL_EXECUTION_FAILED')
    record['finished_at'] = now()
    # Update only our own claimed record, not INSERT OR REPLACE of shared state.
    with store.connect() as connection:
        cursor = connection.execute('UPDATE records SET body=? WHERE kind=? AND id=? AND body=?',
                                    (_canonical(record), KIND, identifier, claimed_body))
        _need(cursor.rowcount == 1, 'CLAIM_STATE_CHANGED')
    return {**record, 'replayed': False}


def execute_lcluc_workflow(store, request, *, _runner=None):
    """Execute one explicit local workflow; sanitize native infrastructure errors."""
    try:
        return _execute(store, request, _runner=_runner)
    except WorkflowError:
        raise
    except Exception:
        raise WorkflowError('LOCAL_WORKFLOW_UNAVAILABLE') from None
