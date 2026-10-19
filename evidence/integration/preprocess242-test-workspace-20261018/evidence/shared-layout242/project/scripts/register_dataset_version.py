"""Explicit RAW/STAGED raster version registration in an existing local catalog."""
import hashlib
import json
from pathlib import Path
import sys

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
for _module_root in (_PROJECT_ROOT,_PROJECT_ROOT/'backend',_PROJECT_ROOT/'.runtime'):
    sys.path.insert(0,str(_module_root))

from app.store import Store
from app.dataset_registry import canonical_manifest, verify_artifact, register_version, version_key
from app.data.quality_mask_bundle import FALSE_FIELDS, _manifest, _copy_json, _canonical
from app.data.quality_report_completion import _same
from app.data.quality_report_registration import _record
from scripts.quality_report_cli import _Parser, _CLIError, _require, _input_file, _existing_catalog
from app.data.quality_report_storage import _root, _safe_uri, _check_parents, _key
from app.data.quality_report_preflight import _regular

_STORE_TYPE = Store
_PATH_TYPE = type(Path())
_CODES = frozenset('ARGUMENTS_INVALID CLI_ARGUMENT_INVALID INPUT_FILE_INVALID INPUT_FILE_LIMIT INPUT_FILE_CHANGED INPUT_JSON_INVALID MANIFEST_INPUT_INVALID MANIFEST_SCHEMA_INVALID MANIFEST_SCHEMA_OUTPUT_INVALID SOURCE_ARTIFACT_INVALID CATALOG_INVALID CATALOG_SCHEMA_INVALID CATALOG_CHANGED CATALOG_ARTIFACT_ALIAS RESOURCE_UNAVAILABLE REGISTRATION_OUTCOME_UNCONFIRMED'.split())


def _empty():
    result = {'schema_version':1,'scope':'EXPLICIT_SOURCE_RASTER_REGISTRATION_CLI_ONLY','status':'BLOCKED',
        'issue':None,'dataset_ref':None,'manifest_sha256':None,'registration_record':None,
        'store_initialization_started':False,'registration_attempted':False,'registry_outcome_verified':False}
    result.update({field:False for field in FALSE_FIELDS})
    return result


def _catalog_binding(root,db,identity,parents,store=None):
    _check_parents(parents)
    current = db.lstat(); _regular(current,'catalog')
    _require((current.st_dev,current.st_ino) == identity and db.resolve(strict=True) == db,'CATALOG_CHANGED')
    if store is not None:
        _require(type(store) is _STORE_TYPE and type(store.root) is _PATH_TYPE and type(store.db) is _PATH_TYPE
            and store.root == root and store.db == db,'CATALOG_CHANGED')


def _artifact_catalog_guard(root,manifest):
    """Do not register this mutable catalog family as its own source artifact."""
    relative = _safe_uri(manifest['artifact_uri'],'artifact_uri')
    family = tuple(root/('catalog.sqlite3'+suffix) for suffix in ('','-wal','-shm','-journal'))
    names = {_key(path.name) for path in family}
    _require(_key(relative) not in names,'CATALOG_ARTIFACT_ALIAS')
    try:
        resolved = root.joinpath(*relative.split('/')).resolve(strict=True)
        _require(resolved.is_relative_to(root),'SOURCE_ARTIFACT_INVALID')
        _require(_key(resolved.relative_to(root).as_posix()) not in names,'CATALOG_ARTIFACT_ALIAS')
        source = resolved.stat()
        for protected in family:
            try: current = protected.stat()
            except FileNotFoundError: continue
            _require((source.st_dev,source.st_ino) != (current.st_dev,current.st_ino),'CATALOG_ARTIFACT_ALIAS')
    except _CLIError: raise
    except Exception: raise _CLIError('SOURCE_ARTIFACT_INVALID') from None


def run(argv):
    """Return (exit code, exact20 result). --help prints static help, result None."""
    result = _empty()
    try:
        _require(type(argv) is list and len(argv) <= 8 and all(type(v) is str and len(v) <= 4096 for v in argv),'ARGUMENTS_INVALID')
        seen = set()
        for argument in argv:
            if argument.startswith('--'):
                option = argument.split('=',1)[0]
                _require(option not in seen,'CLI_ARGUMENT_INVALID'); seen.add(option)
        parser = _Parser(prog='register_dataset_version',description='Explicit existing-catalog raster registration; no automatic metadata or approval.')
        parser.add_argument('--data-root',required=True)
        parser.add_argument('--manifest',required=True)
        try: args = parser.parse_args(argv)
        except SystemExit as error:
            if error.code == 0: return 0,None
            raise _CLIError('ARGUMENTS_INVALID') from None
        try:
            manifest,ref = _manifest(_input_file(args.manifest),'manifest')
            _safe_uri(manifest['artifact_uri'],'artifact_uri')
            root = _root(args.data_root)
        except _CLIError: raise
        except Exception: raise _CLIError('MANIFEST_INPUT_INVALID') from None
        expected_digest = hashlib.sha256(_canonical(manifest)).hexdigest()
        try: validated = canonical_manifest(_copy_json(manifest,'manifest'))
        except Exception: raise _CLIError('MANIFEST_SCHEMA_INVALID') from None
        _require(type(validated) is tuple and len(validated) == 2 and _same(validated[0],manifest)
            and type(validated[1]) is str and validated[1] == expected_digest,'MANIFEST_SCHEMA_OUTPUT_INVALID')
        # Keep only the independent expected manifest/ref, never mutable validator output.
        result.update(dataset_ref=_copy_json(ref,'dataset_ref'),manifest_sha256=expected_digest)
        _artifact_catalog_guard(root,manifest)
        db,identity,parents = _existing_catalog(root)
        try: verify_artifact(root,_copy_json(manifest,'manifest'))
        except Exception: raise _CLIError('SOURCE_ARTIFACT_INVALID') from None
        _catalog_binding(root,db,identity,parents)
        _artifact_catalog_guard(root,manifest)
        result['store_initialization_started'] = True
        store = Store(root,recover_jobs=False)
        _catalog_binding(root,db,identity,parents,store)
        _artifact_catalog_guard(root,manifest)
        result['registration_attempted'] = True
        returned = register_version(store,_copy_json(manifest,'manifest'))
        fixed_record = _record(returned,manifest,expected_digest)
        _catalog_binding(root,db,identity,parents,store)
        _artifact_catalog_guard(root,manifest)
        readback = _record(store.get('dataset_versions',version_key(ref['id'],ref['version'])),manifest,expected_digest)
        _require(_same(readback,fixed_record),'RESOURCE_UNAVAILABLE')
        _catalog_binding(root,db,identity,parents,store)
        result.update(status='SOURCE_RASTER_REGISTERED_UNAPPROVED',registration_record=fixed_record,
            registry_outcome_verified=True,registry_registered=True)
        return 0,result
    except Exception as error:
        uncertain = result['store_initialization_started']
        code = error.code if type(error) is _CLIError and type(error.code) is str and error.code in _CODES else 'RESOURCE_UNAVAILABLE'
        if uncertain:
            result['status'] = code = 'REGISTRATION_OUTCOME_UNCONFIRMED'
            result['registration_record'] = None
        result['issue'] = {'code':code}
        return (3 if uncertain else 2),result


def main(argv=None):
    code,result = run(sys.argv[1:] if argv is None else argv)
    if result is not None:
        if hasattr(sys.stdout,'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
        print(json.dumps(result,ensure_ascii=False,allow_nan=False,separators=(',',':')))
    return code


if __name__ == '__main__': raise SystemExit(main())
