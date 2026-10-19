"""Explicit exclusive creation of two new unregistered report files; no rollback."""
import hashlib
import os
from pathlib import Path
import stat
import unicodedata

from .quality_mask_bundle import FALSE_FIELDS, _Invalid, _need, _copy_json, _canonical, _path
from .quality_report_completion import complete_quality_report, _expected, _metadata, _same

_PATH_TYPE = type(Path())
_RESERVED = {'CON','PRN','AUX','NUL','CLOCK$','CONIN$','CONOUT$'} | {
    prefix+number for prefix in ('COM','LPT') for number in '123456789¹²³'}


def _safe_uri(value, field):
    normalized = _path(value,field)
    _need(not any(char in '<>"|?*' for char in normalized), 'PATH_INVALID',field)
    _need(all(not unicodedata.category(char).startswith('C') for char in normalized), 'PATH_INVALID',field)
    _need(all(part.split('.',1)[0].upper() not in _RESERVED for part in normalized.split('/')), 'PATH_INVALID',field)
    return normalized


def _key(uri):
    return unicodedata.normalize('NFC',uri).casefold()


def _directory(path):
    try:
        info = path.lstat()
        _need(stat.S_ISDIR(info.st_mode) and not stat.S_ISLNK(info.st_mode)
            and not (getattr(info,'st_file_attributes',0) & 0x400)
            and not getattr(info,'st_reparse_tag',0) and path.resolve(strict=True) == path,
            'DIRECTORY_UNAVAILABLE','output_parent')
        return info.st_dev,info.st_ino
    except _Invalid: raise
    except Exception: raise _Invalid('DIRECTORY_UNAVAILABLE','output_parent') from None


def _root(value):
    _need(type(value) in (str,_PATH_TYPE),'ROOT_INVALID','data_root')
    text = str(value)
    _need(1 <= len(text) <= 4096 and not text.startswith(('\\\\','//'))
        and all(not unicodedata.category(c).startswith('C') for c in text),'ROOT_INVALID','data_root')
    path = Path(value)
    _need(path.is_absolute() and not str(path).startswith(('\\\\','//')),'ROOT_INVALID','data_root')
    for component in (path,*path.parents): _directory(component)
    return path


def _parent_snapshot(path):
    return [(component,_directory(component)) for component in (path,*path.parents)]


def _check_parents(snapshot):
    _need(all(_directory(path) == identity for path,identity in snapshot),'DIRECTORY_CHANGED','output_parent')


def _absent(path):
    try: path.lstat()
    except FileNotFoundError: return
    except Exception: raise _Invalid('OUTPUT_UNAVAILABLE','outputs') from None
    raise _Invalid('OUTPUT_ALREADY_EXISTS','outputs')


def _write_new(path, raw, parents, output):
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os,'O_BINARY',0) | getattr(os,'O_NOFOLLOW',0)
    _check_parents(parents)
    descriptor = os.open(path,flags,0o600)
    output['created'] = True
    try:
        _check_parents(parents)
        first = os.fstat(descriptor)
        _need(stat.S_ISREG(first.st_mode) and first.st_size == 0,'OUTPUT_CHANGED','outputs')
        position = 0
        while position < len(raw):
            written = os.write(descriptor,memoryview(raw)[position:])
            _need(type(written) is int and written > 0,'OUTPUT_WRITE_FAILED','outputs')
            position += written
        os.fsync(descriptor)
        final = os.fstat(descriptor)
        _need((first.st_dev,first.st_ino) == (final.st_dev,final.st_ino) and final.st_size == len(raw),
            'OUTPUT_CHANGED','outputs')
        identity = final.st_dev,final.st_ino
    finally: os.close(descriptor)
    _check_parents(parents)
    before = path.lstat()
    _need(stat.S_ISREG(before.st_mode) and not (getattr(before,'st_file_attributes',0) & 0x400)
        and not getattr(before,'st_reparse_tag',0) and (before.st_dev,before.st_ino) == identity
        and before.st_size == len(raw),'OUTPUT_CHANGED','outputs')
    reader = os.open(path,os.O_RDONLY | getattr(os,'O_BINARY',0) | getattr(os,'O_NOFOLLOW',0))
    try:
        opened = os.fstat(reader)
        _need((opened.st_dev,opened.st_ino,opened.st_size) == (*identity,len(raw)),'OUTPUT_CHANGED','outputs')
        checksum = hashlib.sha256(); size = 0
        while True:
            chunk = os.read(reader,min(65536,len(raw)+1-size))
            if not chunk: break
            size += len(chunk)
            _need(size <= len(raw),'OUTPUT_CHANGED','outputs')
            checksum.update(chunk)
        final_read = os.fstat(reader)
    finally: os.close(reader)
    after = path.lstat()
    _check_parents(parents)
    signature = lambda info:(info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_ctime_ns)
    _need(size == len(raw) and checksum.hexdigest() == hashlib.sha256(raw).hexdigest()
        and signature(before) == signature(opened) == signature(final_read) == signature(after), 'OUTPUT_CHANGED','outputs')
    output.update(verified=True,bytes=size)


def write_quality_report_files(data_root,image_manifest,mask_manifest,report_identity,report_metadata,manifest_output_uri):
    """Writes two new files only; partial files remain and no registration occurs."""
    result = {'schema_version':1,'scope':'EXCLUSIVE_NEW_QUALITY_REPORT_FILES_ONLY','status':'BLOCKED','issue':None,
        'report_output_uri':None,'manifest_output_uri':None,'report_sha256':None,'manifest_sha256':None,'fixed_refs':None,
        'outputs':[{'role':role,'created':False,'verified':False,'bytes':None} for role in ('report','manifest')],
        'stored_outputs_verified':False}
    result.update({field:False for field in FALSE_FIELDS})
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
        root = _root(data_root); report_path = root.joinpath(*report_uri.split('/')); manifest_path = root.joinpath(*manifest_uri.split('/'))
        parents = _parent_snapshot(report_path.parent)
        _need(report_path.is_relative_to(root) and manifest_path.is_relative_to(root),'PATH_INVALID','outputs')
        _absent(report_path); _absent(manifest_path)
        report_raw = expected['report_bytes']; manifest_raw = _canonical(expected['report_manifest_draft'])
        _need(len(report_raw) <= 2*1024**2 and len(manifest_raw) <= 2*1024**2,'OUTPUT_LIMIT','outputs')
        result.update(report_output_uri=identity['artifact_uri'],manifest_output_uri=manifest_output_uri,
            report_sha256=expected['report_sha256'],manifest_sha256=hashlib.sha256(manifest_raw).hexdigest(),
            fixed_refs=_copy_json(expected['fixed_refs'],'fixed_refs'))
        _write_new(report_path,report_raw,parents,result['outputs'][0])
        _write_new(manifest_path,manifest_raw,parents,result['outputs'][1])
        result.update(status='FILES_WRITTEN_UNREGISTERED',stored_outputs_verified=True)
    except _Invalid as error: result['issue'] = {'code':error.code,'field':error.field}
    except Exception: result['issue'] = {'code':'OUTPUT_WRITE_FAILED','field':'outputs'}
    if result['issue'] is not None and any(output['created'] for output in result['outputs']):
        result['status'] = 'PARTIAL_FILES_PRESERVED'
    return result
