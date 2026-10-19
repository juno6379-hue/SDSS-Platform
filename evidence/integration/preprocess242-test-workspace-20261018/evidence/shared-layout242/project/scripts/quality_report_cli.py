"""Explicit inspect/register CLI; no environment defaults or automatic registration."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
import sys

from app.store import Store
from app.data.quality_mask_bundle import FALSE_FIELDS, _copy_json, _canonical
from app.data.quality_report_completion import _expected, _metadata, _same
from app.data.quality_report_storage import _root, _parent_snapshot, _check_parents, _safe_uri
from app.data.quality_report_preflight import inspect_stored_quality_report, _empty as _inspect_empty, _regular, _signature
from app.data.quality_report_registration import register_stored_quality_report, _empty as _register_empty, _record

MAX_INPUT_BYTES = 256 * 1024
_CODES = frozenset('INVALID_MANIFEST PATH_INVALID QUALITY_STATUS_UNSUPPORTED REPORT_IDENTITY_INVALID REFERENCE_CONFLICT MASK_SEMANTICS_INVALID QUALITY_REPORT_REF_CONFLICT REPORT_METADATA_INVALID REPORT_INPUT_INVALID PREPARATION_OUTPUT_INVALID COMPLETION_OUTPUT_INVALID ROOT_INVALID DIRECTORY_UNAVAILABLE DIRECTORY_CHANGED OUTPUT_PATH_CONFLICT OUTPUT_PARENT_MISMATCH FILE_INVALID FILE_LIMIT FILE_CHANGED FILE_BYTES_MISMATCH FILE_UNAVAILABLE MANIFEST_SCHEMA_INVALID MANIFEST_SCHEMA_OUTPUT_INVALID PREFLIGHT_UNAVAILABLE STORE_INVALID STORE_ROOT_MISMATCH STORE_DB_INVALID STORE_DB_CHANGED STORE_DB_UNAVAILABLE REGISTRY_RECORD_INVALID STORED_REPORT_PREFLIGHT_FAILED SOURCE_DATASET_BINDING_FAILED REGISTRY_READBACK_MISMATCH REGISTRATION_UNCONFIRMED REGISTRATION_INPUT_UNAVAILABLE'.split())
_FIELDS = frozenset('image_manifest mask_manifest report_identity report_metadata references quality_report_ref fixed_refs bundle completion report_output_uri manifest_output_uri input_artifact outputs data_root output_parent report manifest files report_manifest store catalog registry_record preflight image_ref mask_ref registration inputs'.split())
_CLI_CODES = frozenset('ARGUMENTS_INVALID CLI_ARGUMENT_INVALID INPUT_JSON_INVALID INPUT_FILE_INVALID INPUT_FILE_LIMIT INPUT_FILE_CHANGED CATALOG_INVALID CATALOG_SCHEMA_INVALID CATALOG_CHANGED INPUT_DECLARATION_INVALID CHILD_OUTPUT_INVALID RESOURCE_UNAVAILABLE REGISTRATION_OUTCOME_UNCONFIRMED'.split())


class _CLIError(Exception):
    def __init__(self, code): self.code = code


class _Parser(argparse.ArgumentParser):
    def __init__(self,*args,**kwargs):
        kwargs['allow_abbrev'] = False
        super().__init__(*args,**kwargs)
    def error(self, message): raise _CLIError('ARGUMENTS_INVALID')


def _require(condition, code):
    if not condition: raise _CLIError(code)


def _parser():
    parser = _Parser(prog='quality_report_cli',description='Explicit local quality report inspect/register; no automatic action.')
    commands = parser.add_subparsers(dest='command',required=True,parser_class=_Parser)
    for name in ('inspect','register'):
        command = commands.add_parser(name)
        for option in ('data-root','image-manifest','mask-manifest','report-identity','report-metadata','manifest-output-uri'):
            command.add_argument('--'+option,required=True)
    return parser


def _strict_json(raw):
    text = raw.decode('utf-8',errors='strict'); depth = 0; quoted = False; escaped = False
    for char in text:
        if quoted:
            if escaped: escaped = False
            elif char == '\\': escaped = True
            elif char == '"': quoted = False
        elif char == '"': quoted = True
        elif char in '[{':
            depth += 1; _require(depth <= 16,'INPUT_JSON_INVALID')
        elif char in ']}': depth -= 1
    def pairs(items):
        _require(len(items) <= 128,'INPUT_JSON_INVALID'); result = {}
        for key,value in items:
            _require(key not in result,'INPUT_JSON_INVALID'); result[key] = value
        return result
    def integer(value):
        _require(len(value.lstrip('-')) <= 16,'INPUT_JSON_INVALID')
        result = int(value); _require(abs(result) <= 2**53-1,'INPUT_JSON_INVALID'); return result
    def decimal(value):
        result = float(value); _require(math.isfinite(result),'INPUT_JSON_INVALID'); return result
    def constant(value): raise _CLIError('INPUT_JSON_INVALID')
    return _copy_json(json.loads(text,object_pairs_hook=pairs,parse_int=integer,parse_float=decimal,parse_constant=constant),'input_json')


def _input_file(value):
    try:
        _require(type(value) is str and 1 <= len(value) <= 4096 and not any(ord(c) < 32 for c in value),'INPUT_FILE_INVALID')
        path = Path(value).absolute(); _root(path.parent); parents = _parent_snapshot(path.parent)
        before = path.lstat(); _regular(before,'input_json')
        _require(before.st_size <= MAX_INPUT_BYTES,'INPUT_FILE_LIMIT')
        descriptor = os.open(path,os.O_RDONLY|getattr(os,'O_BINARY',0)|getattr(os,'O_NOFOLLOW',0))
        try:
            opened = os.fstat(descriptor); _regular(opened,'input_json')
            _require(_signature(opened) == _signature(before),'INPUT_FILE_CHANGED')
            chunks = []; size = 0
            while True:
                chunk = os.read(descriptor,min(65536,MAX_INPUT_BYTES+1-size))
                if not chunk: break
                size += len(chunk); _require(size <= MAX_INPUT_BYTES,'INPUT_FILE_LIMIT'); chunks.append(chunk)
            final = os.fstat(descriptor)
        finally: os.close(descriptor)
        after = path.lstat(); _regular(after,'input_json'); _check_parents(parents)
        _require(size == before.st_size and _signature(before) == _signature(final) == _signature(after),'INPUT_FILE_CHANGED')
        try: return _strict_json(b''.join(chunks))
        except Exception: raise _CLIError('INPUT_JSON_INVALID') from None
    except _CLIError: raise
    except Exception: raise _CLIError('INPUT_FILE_INVALID') from None


def _existing_catalog(root):
    """Read-only precheck, not a replacement Store or SQL sandbox."""
    try:
        parents = _parent_snapshot(root); db = root/'catalog.sqlite3'; before = db.lstat(); _regular(before,'catalog')
        _require(db.resolve(strict=True) == db,'CATALOG_INVALID')
        connection = sqlite3.connect(db.as_uri()+'?mode=ro',uri=True)
        try:
            tables = connection.execute("SELECT type FROM sqlite_master WHERE name='records'").fetchall()
            columns = connection.execute('PRAGMA table_info(records)').fetchall()
        finally: connection.close()
        _require(tables == [('table',)] and len(columns) == 3 and [column[1] for column in columns] == ['kind','id','body']
            and [column[2].upper() for column in columns] == ['TEXT','TEXT','TEXT']
            and [column[5] for column in columns] == [1,2,0],'CATALOG_SCHEMA_INVALID')
        _check_parents(parents); after = db.lstat(); _regular(after,'catalog')
        _require((before.st_dev,before.st_ino) == (after.st_dev,after.st_ino),'CATALOG_CHANGED')
        return db,(after.st_dev,after.st_ino),parents
    except _CLIError: raise
    except Exception: raise _CLIError('CATALOG_INVALID') from None


def _plan(image,mask,identity,metadata,uri):
    bundle = _expected(image,mask,identity); metadata = _metadata(metadata); _safe_uri(uri,'manifest_output_uri')
    report = {**metadata,**bundle['report_manifest_patch']}; manifest_raw = _canonical(report)
    expected = _inspect_empty()
    expected.update(status='STORED_REPORT_FILES_VERIFIED_UNREGISTERED',report_output_uri=identity['artifact_uri'],manifest_output_uri=uri,
        report_sha256=bundle['report_sha256'],manifest_sha256=hashlib.sha256(manifest_raw).hexdigest(),fixed_refs=bundle['fixed_refs'],
        report_manifest_draft=report,files=[{'role':'report','verified':True,'bytes':len(bundle['report_bytes'])},
            {'role':'manifest','verified':True,'bytes':len(manifest_raw)}],stored_report_files_verified=True,manifest_schema_verified=True)
    return expected


def _issue(value):
    return (type(value) is dict and value.keys() == {'code','field'} and type(value['code']) is str
        and value['code'] in _CODES and type(value['field']) is str and value['field'] in _FIELDS)


def _child(value,command,plan):
    value = _copy_json(value,'child_result')
    if command == 'inspect':
        if _same(value,plan): return value
        empty = _inspect_empty()
        _require(type(value.get('issue')) is dict and _issue(value['issue']),'CHILD_OUTPUT_INVALID')
        empty['issue'] = value['issue']; _require(_same(value,empty),'CHILD_OUTPUT_INVALID'); return value
    expected = _register_empty()
    _require(value.keys() == expected.keys() and type(value['schema_version']) is int and value['schema_version'] == 1
        and value['scope'] == expected['scope'],'CHILD_OUTPUT_INVALID')
    for field in FALSE_FIELDS:
        if field != 'registry_registered': _require(value[field] is False,'CHILD_OUTPUT_INVALID')
    fields = ('source_dataset_refs_verified','stored_report_files_verified','manifest_schema_verified','registration_attempted','registry_outcome_verified','registry_registered')
    _require(all(type(value[k]) is bool for k in fields),'CHILD_OUTPUT_INVALID')
    _require(value['stored_report_files_verified'] == value['manifest_schema_verified'],'CHILD_OUTPUT_INVALID')
    planned = value['stored_report_files_verified']
    _require(_same(value['fixed_refs'],plan['fixed_refs'] if planned else None)
        and _same(value['report_manifest_sha256'],plan['manifest_sha256'] if planned else None),'CHILD_OUTPUT_INVALID')
    _require(not value['source_dataset_refs_verified'] or planned,'CHILD_OUTPUT_INVALID')
    if value['status'] == 'REPORT_REGISTERED_UNAPPROVED':
        _require(all(value[k] is True for k in fields) and value['issue'] is None,'CHILD_OUTPUT_INVALID')
        value['registration_record'] = _record(value['registration_record'],plan['report_manifest_draft'],plan['manifest_sha256'])
    else:
        _require(value['status'] in ('BLOCKED','REGISTRATION_OUTCOME_UNCONFIRMED') and _issue(value['issue'])
            and value['registration_record'] is None and value['registry_registered'] is False
            and value['registry_outcome_verified'] is False,'CHILD_OUTPUT_INVALID')
        attempted = value['status'] == 'REGISTRATION_OUTCOME_UNCONFIRMED'
        _require(value['registration_attempted'] is attempted and (not attempted or (planned and value['source_dataset_refs_verified'])),
            'CHILD_OUTPUT_INVALID')
    return value


def run(argv):
    """Return (exit code, safe exact6 wrapper); --help prints static help and returns None."""
    command = None; initialized = False
    def wrapper(status,code=None,result=None):
        return {'schema_version':1,'scope':'EXPLICIT_QUALITY_REPORT_CLI_ONLY','command':command,
            'status':status,'issue':None if code is None else {'code':code},'result':result}
    try:
        _require(type(argv) is list and len(argv) <= 32 and all(type(v) is str and len(v) <= 4096 for v in argv),'ARGUMENTS_INVALID')
        seen = set()
        for value in argv:
            if value.startswith('--'):
                option = value.split('=',1)[0]
                _require(option not in seen,'CLI_ARGUMENT_INVALID'); seen.add(option)
        try: args = _parser().parse_args(argv)
        except SystemExit as error:
            if error.code == 0: return 0,None
            raise _CLIError('ARGUMENTS_INVALID') from None
        command = args.command
        image,mask,identity,metadata = [_input_file(getattr(args,key)) for key in ('image_manifest','mask_manifest','report_identity','report_metadata')]
        try: plan = _plan(image,mask,identity,metadata,args.manifest_output_uri); root = _root(args.data_root)
        except Exception: raise _CLIError('INPUT_DECLARATION_INVALID') from None
        # Child inputs cannot mutate the independent output verification plan.
        children = [_copy_json(value,'child_input') for value in (image,mask,identity,metadata)]
        if command == 'inspect':
            child = inspect_stored_quality_report(root,*children,args.manifest_output_uri)
        else:
            db,identity_db,parents = _existing_catalog(root)
            _check_parents(parents); info = db.lstat(); _regular(info,'catalog')
            _require((info.st_dev,info.st_ino) == identity_db,'CATALOG_CHANGED')
            initialized = True  # Constructor can touch SQLite before an exception.
            store = Store(root,recover_jobs=False)
            _check_parents(parents); info = db.lstat(); _regular(info,'catalog')
            _require((info.st_dev,info.st_ino) == identity_db,'CATALOG_CHANGED')
            child = register_stored_quality_report(store,root,*children,args.manifest_output_uri)
            _check_parents(parents); info = db.lstat(); _regular(info,'catalog')
            _require((info.st_dev,info.st_ino) == identity_db,'CATALOG_CHANGED')
        safe = _child(child,command,plan)
        status = safe['status']; exit_code = 0 if status in ('STORED_REPORT_FILES_VERIFIED_UNREGISTERED','REPORT_REGISTERED_UNAPPROVED') else 3 if status == 'REGISTRATION_OUTCOME_UNCONFIRMED' else 2
        return exit_code,wrapper(status,result=safe)
    except Exception as error:
        uncertain = command == 'register' and initialized
        code = error.code if type(error) is _CLIError and type(error.code) is str and error.code in _CLI_CODES else 'RESOURCE_UNAVAILABLE'
        if uncertain: code = 'REGISTRATION_OUTCOME_UNCONFIRMED'
        return (3 if uncertain else 2),wrapper('REGISTRATION_OUTCOME_UNCONFIRMED' if uncertain else 'BLOCKED',code)


def main(argv=None):
    code,result = run(sys.argv[1:] if argv is None else argv)
    if result is not None:
        if hasattr(sys.stdout,'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
        print(json.dumps(result,ensure_ascii=False,allow_nan=False,separators=(',',':')))
    return code


if __name__ == '__main__': raise SystemExit(main())
