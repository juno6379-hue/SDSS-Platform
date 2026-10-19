"""Explicit report-only registration using an already initialized trusted local Store."""
import hashlib
from datetime import datetime
from pathlib import Path

from ..store import Store
from ..dataset_registry import resolve_version, register_version, version_key
from .quality_mask_bundle import FALSE_FIELDS, _Invalid, _need, _copy_json, _canonical, _text
from .quality_report_completion import _expected, _metadata, _same
from .quality_report_preflight import inspect_stored_quality_report, _empty as _preflight_empty, _regular
from .quality_report_storage import _root, _check_parents, _parent_snapshot, _safe_uri

_PATH_TYPE = type(Path())
_RECORD_KEYS = {'id','manifest','manifest_sha256','registered_at','scientific_accuracy_validated','deployment_approval'}


def _empty():
    result = {'schema_version':1,'scope':'EXPLICIT_STORED_QUALITY_REPORT_REGISTRATION_ONLY','status':'BLOCKED',
        'issue':None,'fixed_refs':None,'report_manifest_sha256':None,'registration_record':None,
        'source_dataset_refs_verified':False,'stored_report_files_verified':False,'manifest_schema_verified':False,
        'registration_attempted':False,'registry_outcome_verified':False}
    result.update({field:False for field in FALSE_FIELDS})
    return result


def _store_boundary(store, root, identity=None):
    try:
        _need(type(store) is Store and type(store.root) is _PATH_TYPE and type(store.db) is _PATH_TYPE,
            'STORE_INVALID','store')
        _need(store.root == root and store.db == root/'catalog.sqlite3','STORE_ROOT_MISMATCH','store')
        parents = _parent_snapshot(root) if identity is None else identity[1]
        _check_parents(parents)
        info = store.db.lstat(); _regular(info,'catalog')
        _need(store.db.resolve(strict=True) == store.db,'STORE_DB_INVALID','catalog')
        current = info.st_dev,info.st_ino
        _need(identity is None or current == identity[0],'STORE_DB_CHANGED','catalog')
        return current,parents
    except _Invalid: raise
    except Exception: raise _Invalid('STORE_DB_UNAVAILABLE','catalog') from None


def _record(value, manifest, digest):
    value = _copy_json(value,'registry_record')
    _need(value.keys() == _RECORD_KEYS and type(value['id']) is str
        and value['id'] == version_key(manifest['dataset_id'],manifest['version'])
        and type(value['manifest_sha256']) is str and value['manifest_sha256'] == digest
        and _same(value['manifest'],manifest) and value['scientific_accuracy_validated'] is False
        and value['deployment_approval'] is False,'REGISTRY_RECORD_INVALID','registry_record')
    stamp = value['registered_at']
    _need(type(stamp) is str and 1 <= len(stamp) <= 128 and _text(stamp),'REGISTRY_RECORD_INVALID','registry_record')
    try: timestamp = datetime.fromisoformat(stamp.replace('Z','+00:00'))
    except Exception: raise _Invalid('REGISTRY_RECORD_INVALID','registry_record') from None
    _need(timestamp.tzinfo is not None and timestamp.utcoffset().total_seconds() == 0
        and timestamp.isoformat() == stamp,'REGISTRY_RECORD_INVALID','registry_record')
    return value


def register_stored_quality_report(store,data_root,image_manifest,mask_manifest,report_identity,report_metadata,manifest_output_uri):
    """Registers only the explicit report; uncertain post-call outcomes are preserved."""
    result = _empty()
    try:
        image = _copy_json(image_manifest,'image_manifest'); mask = _copy_json(mask_manifest,'mask_manifest')
        identity = _copy_json(report_identity,'report_identity'); metadata = _metadata(report_metadata)
        bundle = _expected(image,mask,identity)
        report = {**metadata,**bundle['report_manifest_patch']}
        report_raw = bundle['report_bytes']; manifest_raw = _canonical(report)
        _safe_uri(manifest_output_uri,'manifest_output_uri')
        expected = _preflight_empty()
        expected.update(status='STORED_REPORT_FILES_VERIFIED_UNREGISTERED',report_output_uri=identity['artifact_uri'],
            manifest_output_uri=manifest_output_uri,report_sha256=bundle['report_sha256'],
            manifest_sha256=hashlib.sha256(manifest_raw).hexdigest(),fixed_refs=bundle['fixed_refs'],report_manifest_draft=report,
            files=[{'role':'report','verified':True,'bytes':len(report_raw)},
                {'role':'manifest','verified':True,'bytes':len(manifest_raw)}],
            stored_report_files_verified=True,manifest_schema_verified=True)
        _need(type(store) is Store,'STORE_INVALID','store')
        root = _root(data_root); db_identity = _store_boundary(store,root)
        preflight = inspect_stored_quality_report(root,_copy_json(image,'image_manifest'),_copy_json(mask,'mask_manifest'),
            _copy_json(identity,'report_identity'),_copy_json(metadata,'report_metadata'),manifest_output_uri)
        _need(_same(preflight,expected),'STORED_REPORT_PREFLIGHT_FAILED','preflight')
        result.update(fixed_refs=_copy_json(bundle['fixed_refs'],'fixed_refs'),report_manifest_sha256=expected['manifest_sha256'],
            stored_report_files_verified=True,manifest_schema_verified=True)
        for raw,ref_key in ((image,'image_ref'),(mask,'mask_ref')):
            _store_boundary(store,root,db_identity)
            ref = bundle['fixed_refs'][ref_key]
            try:
                resolved = resolve_version(store,ref['id'],ref['version'],ref['sha256'])
                _record(resolved,raw,hashlib.sha256(_canonical(raw)).hexdigest())
            except Exception: raise _Invalid('SOURCE_DATASET_BINDING_FAILED',ref_key) from None
        result['source_dataset_refs_verified'] = True
        _store_boundary(store,root,db_identity)
        result['registration_attempted'] = True
        # From here exceptions can follow a commit. Never claim rollback/absence.
        returned = register_version(store,_copy_json(report,'report_manifest_draft'))
        fixed_record = _record(returned,report,expected['manifest_sha256'])
        _store_boundary(store,root,db_identity)
        readback = _record(store.get('dataset_versions',version_key(identity['id'],identity['version'])),
            report,expected['manifest_sha256'])
        _need(_same(readback,fixed_record),'REGISTRY_READBACK_MISMATCH','registry_record')
        _store_boundary(store,root,db_identity)
        result.update(status='REPORT_REGISTERED_UNAPPROVED',registration_record=fixed_record,
            registry_registered=True,registry_outcome_verified=True)
    except _Invalid as error:
        result['issue'] = {'code':error.code,'field':error.field}
    except Exception:
        result['issue'] = {'code':'REGISTRATION_UNCONFIRMED' if result['registration_attempted'] else 'REGISTRATION_INPUT_UNAVAILABLE',
            'field':'registration' if result['registration_attempted'] else 'inputs'}
    if result['issue'] is not None and result['registration_attempted']:
        result['status'] = 'REGISTRATION_OUTCOME_UNCONFIRMED'
        result['registration_record'] = None
    return result
