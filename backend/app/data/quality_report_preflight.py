"""Read two caller-selected report files before registration; never registers or writes."""
import hashlib
import os
import stat

from ..dataset_registry import canonical_manifest
from .quality_mask_bundle import FALSE_FIELDS, _Invalid, _need, _copy_json, _canonical
from .quality_report_completion import complete_quality_report, _expected, _metadata, _same
from .quality_report_storage import _safe_uri, _key, _root, _parent_snapshot, _check_parents

MAX_FILE_BYTES = 2 * 1024**2


def _empty():
    result = {'schema_version':1,'scope':'READONLY_STORED_QUALITY_REPORT_PREFLIGHT_ONLY',
        'status':'BLOCKED','issue':None,'report_output_uri':None,'manifest_output_uri':None,
        'report_sha256':None,'manifest_sha256':None,'fixed_refs':None,'report_manifest_draft':None,
        'files':[{'role':role,'verified':False,'bytes':None} for role in ('report','manifest')],
        'stored_report_files_verified':False,'manifest_schema_verified':False}
    result.update({field:False for field in FALSE_FIELDS})
    return result


def _signature(info):
    return info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_ctime_ns


def _regular(info, field):
    _need(stat.S_ISREG(info.st_mode) and not stat.S_ISLNK(info.st_mode)
        and not (getattr(info,'st_file_attributes',0) & 0x400)
        and not getattr(info,'st_reparse_tag',0),'FILE_INVALID',field)


def _snapshot(path, parents, field):
    try:
        _check_parents(parents)
        before = path.lstat(); _regular(before,field)
        _need(0 <= before.st_size <= MAX_FILE_BYTES,'FILE_LIMIT',field)
        descriptor = os.open(path,os.O_RDONLY | getattr(os,'O_BINARY',0) | getattr(os,'O_NOFOLLOW',0))
        try:
            opened = os.fstat(descriptor); _regular(opened,field)
            _need(_signature(before) == _signature(opened),'FILE_CHANGED',field)
            chunks = []; size = 0; checksum = hashlib.sha256()
            while True:
                chunk = os.read(descriptor,min(65536,MAX_FILE_BYTES+1-size))
                if not chunk: break
                size += len(chunk)
                _need(size <= MAX_FILE_BYTES,'FILE_LIMIT',field)
                chunks.append(chunk); checksum.update(chunk)
            final = os.fstat(descriptor)
        finally: os.close(descriptor)
        after = path.lstat(); _regular(after,field); _check_parents(parents)
        _need(size == before.st_size and _signature(before) == _signature(final) == _signature(after),
            'FILE_CHANGED',field)
        return b''.join(chunks),checksum.hexdigest(),_signature(after)
    except _Invalid: raise
    except Exception: raise _Invalid('FILE_UNAVAILABLE',field) from None


def _unchanged(path, signature, parents, field):
    try:
        _check_parents(parents)
        current = path.lstat(); _regular(current,field)
        _need(_signature(current) == signature,'FILE_CHANGED',field)
    except _Invalid: raise
    except Exception: raise _Invalid('FILE_UNAVAILABLE',field) from None


def inspect_stored_quality_report(data_root,image_manifest,mask_manifest,report_identity,report_metadata,manifest_output_uri):
    """Compare copied stored bytes and full report schema; success remains unregistered."""
    result = _empty()
    try:
        image = _copy_json(image_manifest,'image_manifest'); mask = _copy_json(mask_manifest,'mask_manifest')
        identity = _copy_json(report_identity,'report_identity'); metadata = _metadata(report_metadata)
        bundle = _expected(image,mask,identity)
        expected = {'schema_version':1,'scope':'UNREGISTERED_EXPLICIT_QUALITY_REPORT_COMPLETION_ONLY',
            'status':'UNREGISTERED_REPORT_MANIFEST_PREPARED','issue':None,'image_manifest_draft':bundle['image_manifest_draft'],
            'mask_manifest_draft':bundle['mask_manifest_draft'],'report_manifest_draft':{**metadata,**bundle['report_manifest_patch']},
            'report_envelope':bundle['report_envelope'],'report_bytes':bundle['report_bytes'],
            'report_sha256':bundle['report_sha256'],'fixed_refs':bundle['fixed_refs']}
        expected.update({field:False for field in FALSE_FIELDS})
        producer = complete_quality_report(_copy_json(image,'image_manifest'),_copy_json(mask,'mask_manifest'),
            _copy_json(identity,'report_identity'),_copy_json(metadata,'report_metadata'))
        _need(_same(producer,expected),'COMPLETION_OUTPUT_INVALID','completion')
        report_uri = _safe_uri(identity['artifact_uri'],'report_output_uri')
        manifest_uri = _safe_uri(manifest_output_uri,'manifest_output_uri')
        inputs = [_safe_uri(value['artifact_uri'],'input_artifact') for value in (image,mask)]
        quality_refs = [_safe_uri(value['quality_report_ref'],'quality_report_ref') for value in (image,mask) if 'quality_report_ref' in value]
        _need(_key(report_uri) != _key(manifest_uri) and all(_key(uri) not in {_key(p) for p in inputs}
            for uri in (report_uri,manifest_uri)) and _key(manifest_uri) not in {_key(p) for p in quality_refs},
            'OUTPUT_PATH_CONFLICT','outputs')
        _need(report_uri.rpartition('/')[0] == manifest_uri.rpartition('/')[0],'OUTPUT_PARENT_MISMATCH','outputs')
        report_raw = expected['report_bytes']; manifest = expected['report_manifest_draft']; manifest_raw = _canonical(manifest)
        _need(len(report_raw) <= MAX_FILE_BYTES and len(manifest_raw) <= MAX_FILE_BYTES,'FILE_LIMIT','files')
        root = _root(data_root)
        report_path = root.joinpath(*report_uri.split('/')); manifest_path = root.joinpath(*manifest_uri.split('/'))
        _need(report_path.is_relative_to(root) and manifest_path.is_relative_to(root),'PATH_INVALID','outputs')
        parents = _parent_snapshot(report_path.parent)
        report_copy,report_sha,report_stat = _snapshot(report_path,parents,'report')
        _need(report_copy == report_raw and report_sha == expected['report_sha256'],'FILE_BYTES_MISMATCH','report')
        manifest_copy,manifest_sha,manifest_stat = _snapshot(manifest_path,parents,'manifest')
        _need(manifest_copy == manifest_raw and manifest_sha == hashlib.sha256(manifest_raw).hexdigest(),
            'FILE_BYTES_MISMATCH','manifest')
        # Parse only the trusted expected draft; stored JSON is accepted by exact bytes.
        try: schema_result = canonical_manifest(_copy_json(manifest,'report_manifest_draft'))
        except Exception: raise _Invalid('MANIFEST_SCHEMA_INVALID','report_manifest') from None
        _need(type(schema_result) is tuple and len(schema_result) == 2
            and _same(schema_result[0],manifest) and type(schema_result[1]) is str
            and schema_result[1] == manifest_sha,'MANIFEST_SCHEMA_OUTPUT_INVALID','report_manifest')
        # Recheck the first file after the second read and schema work as well.
        _unchanged(report_path,report_stat,parents,'report')
        _unchanged(manifest_path,manifest_stat,parents,'manifest')
        result.update(status='STORED_REPORT_FILES_VERIFIED_UNREGISTERED',report_output_uri=identity['artifact_uri'],
            manifest_output_uri=manifest_output_uri,report_sha256=report_sha,manifest_sha256=manifest_sha,
            fixed_refs=_copy_json(expected['fixed_refs'],'fixed_refs'),report_manifest_draft=_copy_json(manifest,'report_manifest_draft'),
            files=[{'role':'report','verified':True,'bytes':len(report_copy)},
                {'role':'manifest','verified':True,'bytes':len(manifest_copy)}],
            stored_report_files_verified=True,manifest_schema_verified=True)
    except _Invalid as error:
        result = _empty(); result['issue'] = {'code':error.code,'field':error.field}
    except Exception:
        result = _empty(); result['issue'] = {'code':'PREFLIGHT_UNAVAILABLE','field':'files'}
    return result
