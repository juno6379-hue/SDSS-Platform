"""Bounded local STAC adapter. No HTTP, ledger, raster or execution authority."""
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import stat

from .bare_label_survey_contract import validate_survey_request, SurveyContractError
from .bare_survey_stac_binding import validate_survey_stac_binding, SurveyStacBindingError

MAX_BYTES = 1024**2
CHUNK_BYTES = 65536


class SurveyStacFileError(ValueError):
    """Fixed code and actual bytes observed before failure; no path or raw cause."""
    def __init__(self, code, actual_read_bytes=0):
        super().__init__(code)
        self.actual_read_bytes = actual_read_bytes


def _need(ok, code):
    if not ok:
        raise SurveyStacFileError(code)


def _identity(value):
    return (value.st_dev, value.st_ino, value.st_mode, value.st_size,
            value.st_mtime_ns, value.st_ctime_ns, value.st_nlink)


def _unlinked(value):
    return not stat.S_ISLNK(value.st_mode) and not (getattr(value, 'st_file_attributes', 0) & 0x400)


def _parents(path):
    values = []
    for parent in reversed(path.parent.parents):
        value = parent.lstat()
        _need(_unlinked(value) and stat.S_ISDIR(value.st_mode), 'SURVEY_FILE_PARENT_UNSAFE')
        values.append((parent, _identity(value)))
    value = path.parent.lstat()
    _need(_unlinked(value) and stat.S_ISDIR(value.st_mode), 'SURVEY_FILE_PARENT_UNSAFE')
    values.append((path.parent, _identity(value)))
    return values


@dataclass(frozen=True)
class SurveyStacFileBinding:
    request_sha256: str
    raw_stac_sha256: str
    actual_read_bytes: int
    canonical_json: str
    status: str = 'LOCAL_PINNED_STAC_FILE_AND_METADATA_BOUND'
    execution_supported: bool = False
    source_authenticity_verified: bool = False

    def to_dict(self):
        return json.loads(self.canonical_json)


def read_pinned_survey_stac(root, request, selected_asset, *, maximum_read_bytes=MAX_BYTES):
    """Read one declared DATA file once, then call unchanged246 pure binding.

    maximum_read_bytes is per invocation local IO, not remote metadata credit.
    Other request refs are never opened. No shared budget/transaction is created.
    """
    observed = 0
    try:
        _need(type(maximum_read_bytes) is int and 0 <= maximum_read_bytes <= MAX_BYTES,
              'SURVEY_FILE_BUDGET_INVALID')
        try:
            plan = validate_survey_request(request).to_dict()
        except SurveyContractError:
            raise SurveyStacFileError('SURVEY_FILE_REQUEST_INVALID') from None
        _need(type(selected_asset) is dict and set(selected_asset) == {'key', 'source_url', 'product_uri'},
              'SURVEY_FILE_ASSET_INVALID')
        selected = {key: selected_asset[key] for key in ('key', 'source_url', 'product_uri')}
        _need(all(type(v) is str and 1 <= len(v) <= 4096 for v in selected.values()),
              'SURVEY_FILE_ASSET_INVALID')
        _need(type(root) is type(Path()) and root.is_absolute(), 'SURVEY_FILE_ROOT_INVALID')
        ref = plan['selected_scene']['stac_ref']
        _need(ref['path'].startswith('data/'), 'SURVEY_FILE_PATH_INVALID')
        others = [plan[k]['path'] for k in ('current_manifest_ref', 'boundary_ref', 'ledger_ref', 'base_config_ref')]
        others.append(plan['seed']['justification_ref']['path'])
        _need(ref['path'].casefold() not in {p.casefold() for p in others}, 'SURVEY_FILE_REFERENCE_ALIAS')
        path = root.joinpath(*ref['path'].split('/'))
        parents = _parents(path)
        _need(root.resolve(strict=True) == root and path.resolve(strict=True) == path,
              'SURVEY_FILE_PATH_UNSAFE')
        before = path.lstat()
        _need(_unlinked(before) and stat.S_ISREG(before.st_mode) and before.st_nlink == 1,
              'SURVEY_FILE_NOT_SINGLE_REGULAR')
        _need(2 <= before.st_size <= MAX_BYTES, 'SURVEY_FILE_BYTE_LIMIT')
        _need(before.st_size <= maximum_read_bytes, 'SURVEY_FILE_BUDGET_EXCEEDED')
        flags = os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0)
        descriptor = os.open(path, flags)
        try:
            _need(_identity(os.fstat(descriptor)) == _identity(before), 'SURVEY_FILE_CHANGED_BEFORE_READ')
            parts = []
            while observed < before.st_size:
                raw = os.read(descriptor, min(CHUNK_BYTES, before.st_size - observed))
                _need(bool(raw), 'SURVEY_FILE_SHORT_READ')
                observed += len(raw)
                _need(observed <= maximum_read_bytes, 'SURVEY_FILE_BUDGET_EXCEEDED')
                parts.append(raw)
            _need(_identity(os.fstat(descriptor)) == _identity(before), 'SURVEY_FILE_CHANGED_DURING_READ')
        finally:
            os.close(descriptor)
        _need(_identity(path.lstat()) == _identity(before), 'SURVEY_FILE_REPLACED')
        _need(_parents(path) == parents and path.resolve(strict=True) == path, 'SURVEY_FILE_PARENT_CHANGED')
        raw_stac = b''.join(parts)
        _need(hashlib.sha256(raw_stac).hexdigest() == ref['sha256'], 'SURVEY_FILE_PIN_MISMATCH')
        try:
            bound = validate_survey_stac_binding(plan, raw_stac, selected)
        except SurveyStacBindingError:
            raise SurveyStacFileError('SURVEY_FILE_METADATA_BINDING_INVALID') from None
        # The pure validator may take time. Recheck logical path/parents after it.
        _need(_identity(path.lstat()) == _identity(before) and _parents(path) == parents,
              'SURVEY_FILE_CHANGED_AFTER_BINDING')
        result = {'schema_version': 1, 'kind': 'LOCAL_SURVEY_STAC_FILE_BINDING',
                  'request_sha256': bound.request_sha256, 'raw_stac_sha256': bound.raw_stac_sha256,
                  'stac_ref': ref, 'actual_read_bytes': observed, 'maximum_read_bytes': maximum_read_bytes,
                  'local_file_pin_and_identity_verified': True, 'metadata_binding': bound.to_dict(),
                  **dict.fromkeys(('source_authenticity_verified', 'remote_asset_verified',
                                  'raster_header_verified', 'ledger_verified', 'quality_eligible',
                                  'training_ready', 'execution_supported', 'collection_executed',
                                  'registry_connected', 'target_consumer_connected'), False)}
        return SurveyStacFileBinding(bound.request_sha256, bound.raw_stac_sha256, observed,
            json.dumps(result, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False))
    except SurveyStacFileError as error:
        raise SurveyStacFileError(str(error), observed) from None
    except (OSError, ValueError, TypeError, KeyError, RuntimeError):
        raise SurveyStacFileError('SURVEY_FILE_INPUT_OR_IO_INVALID', observed) from None
