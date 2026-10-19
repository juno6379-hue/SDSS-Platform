from .collection_source_profile import configured
from .ml.manifest_resource_profile import active,cap as profile_cap,charge as profile_charge,require_io_room,serialized_io
"""Bounded read-only ledger observation. Never instantiate CollectionLedger (it locks)."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat

LEDGER = 'first-group-training-budget/global-ledger.json'
SOURCE = 'first-group-training-esri-v1/annual-window-report.json'
LIMIT = 8 * 1024 ** 2
SOURCE_LIMIT = 64 * 1024 ** 2
SAFE = 2 ** 53 - 1
OLD_PENDING = {
    'parallel-v2-extra-banten-2023-v2-laneB-banten-boundary-01': 'efa62f34c493d430bce433a10da097f3600bea00a0af7364b3fd80abdf1229b8',
    'parallel-v2-extra-west_java-2023-v2-laneB-west_java-boundary-01': 'beb3767e75f5152fc174ea1314d04729bea27dd5112646c0a1c9d41e097b5593',
}


def _sha(value):
    return type(value) is str and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def _number(value):
    if type(value) is not int or not 0 <= value <= SAFE:
        raise ValueError('invalid integer')
    return value


def _identity(path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
        raise ValueError('non regular input')
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


@serialized_io
def _read(root, name, limit, keep, *, json_role=None):
    root_info = root.lstat()
    if not stat.S_ISDIR(root_info.st_mode) or stat.S_ISLNK(root_info.st_mode) or getattr(root_info, 'st_file_attributes', 0) & 0x400:
        raise ValueError('linked or non-directory data root')
    path = root
    for part in Path(name).parts:
        path = path / part
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ValueError('linked input')
    before = _identity(path)
    if before[2] > limit:
        raise ValueError('oversize input')
    if json_role is not None:require_io_room(limit+1)
    digest, chunks, size = hashlib.sha256(), [], 0
    with path.open('rb') as stream:
        opened = os.fstat(stream.fileno())
        if (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns, opened.st_ctime_ns) != before:
            raise ValueError('opened input changed')
        while block := stream.read(min(1024 * 1024, limit + 1 - size)):
            if json_role is not None:profile_charge(len(block))
            size += len(block)
            if size > limit:
                raise ValueError('oversize input')
            digest.update(block)
            if keep:
                chunks.append(block)
    if _identity(path) != before or size != before[2]:
        raise ValueError('input changed')
    return before, digest.hexdigest(), b''.join(chunks) if keep else None


def _decode(raw):
    text = raw.decode('utf-8')
    if text.startswith('\ufeff') or '\x00' in text:
        raise ValueError('JSON encoding')
    depth, quoted, escaped = 0, False, False
    for char in text:
        if quoted:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in '[{':
            depth += 1
            if depth > 16:
                raise ValueError('JSON depth')
        elif char in ']}':
            depth -= 1
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate key')
            result[key] = value
        return result
    def invalid(value):
        raise ValueError('nonfinite JSON')
    return json.loads(text, object_pairs_hook=pairs, parse_constant=invalid)


def _validate(value):
    keys = {'version', 'historical_ledgers', 'historical_charged_bytes', 'additional_maximum_bytes',
            'new_charged_bytes', 'external_research_metadata_body_bytes', 'combined_maximum_bytes',
            'batches', 'rate_limit_active', 'updated_at'}
    if type(value) is not dict or set(value) - {'last_rate_limit'} != keys or type(value['version']) is not int or value['version'] != 1:
        raise ValueError('ledger schema')
    if type(value['rate_limit_active']) is not bool:
        raise ValueError('rate limit flag')
    stamp = value['updated_at']
    if type(stamp) is not str or len(stamp) > 64 or datetime.fromisoformat(stamp.replace('Z', '+00:00')).tzinfo is None:
        raise ValueError('timestamp')
    for key in ['historical_charged_bytes', 'additional_maximum_bytes', 'new_charged_bytes', 'external_research_metadata_body_bytes', 'combined_maximum_bytes']:
        _number(value[key])
    cap, charged = value['additional_maximum_bytes'], value['new_charged_bytes']
    if not 1 <= cap <= 4 * 1024 ** 3 or charged > cap or value['combined_maximum_bytes'] != value['historical_charged_bytes'] + cap:
        raise ValueError('budget arithmetic')
    history = value['historical_ledgers']
    if type(history) is not list or not 1 <= len(history) <= 100:
        raise ValueError('historical references')
    for ref in history:
        if type(ref) is not dict or set(ref) != {'path', 'sha256'} or type(ref['path']) is not str or not 1 <= len(ref['path']) <= 2048 or not _sha(ref['sha256']):
            raise ValueError('historical reference')
    if 'last_rate_limit' in value and type(value['last_rate_limit']) is not dict:
        raise ValueError('rate limit declaration')
    batches = value['batches']
    if type(batches) is not dict or len(batches) > 10000:
        raise ValueError('batch map')
    settled = pending = pending_count = old = old_count = 0
    for key, batch in batches.items():
        if not 1 <= len(key) <= 512 or type(batch) is not dict or set(batch) - {'report_path'} != {'status', 'reserved_bytes', 'charged_bytes', 'config_sha256'} or not _sha(batch['config_sha256']):
            raise ValueError('batch schema')
        reserve, charge = _number(batch['reserved_bytes']), _number(batch['charged_bytes'])
        if not 0 < reserve <= 2 * 1024 ** 3 or charge > reserve or batch['status'] not in ('pending', 'settled'):
            raise ValueError('batch values')
        if 'report_path' in batch and batch['report_path'] is not None and (type(batch['report_path']) is not str or len(batch['report_path']) > 2048):
            raise ValueError('report declaration')
        if key in OLD_PENDING and batch['config_sha256'] != OLD_PENDING[key]:
            raise ValueError('historical pending identity')
        if batch['status'] == 'pending':
            if charge != reserve:
                raise ValueError('pending reservation not fully charged')
            pending += charge
            pending_count += 1
            if key in OLD_PENDING:
                old += charge
                old_count += 1
        else:
            settled += charge
    if not set(OLD_PENDING).issubset(batches) or settled + pending + value['external_research_metadata_body_bytes'] != charged:
        raise ValueError('ledger charge sum')
    return dict(additional_maximum_bytes=cap, charged_including_pending_bytes=charged,
                remaining_bytes=cap - charged, settled_batch_bytes=settled,
                metadata_body_bytes=value['external_research_metadata_body_bytes'],
                pending_bytes=pending, pending_count=pending_count,
                old_pending_bytes=old, old_pending_count=old_count,
                ledger_updated_at=stamp, rate_limit_active=value['rate_limit_active'])


@configured('budget')
def collection_budget_status(root,*,_source_selection=None):
    unavailable = {'schema_version': 1, 'available': False, 'status': 'UNCONFIRMED', 'process_verification': 'UNKNOWN'}
    try:
        root = Path(root)
        ledger_kwargs={'json_role':'ledger'} if active() is not None else {}
        ledger = _read(root, LEDGER, LIMIT, True,**ledger_kwargs)
        source_limit=profile_cap('source',SOURCE_LIMIT)
        source_kwargs={'json_role':'source'} if active() is not None else {}
        source = _read(root, SOURCE, source_limit, False,**source_kwargs)
        if _source_selection.source_sha256 is not None and source[1]!=_source_selection.source_sha256:return unavailable
        counts = _validate(_decode(ledger[2]))
        # Both identities and complete byte hashes must still match at the end of the observation.
        if source[:2] != _read(root, SOURCE, source_limit, False,**source_kwargs)[:2] or ledger[:2] != _read(root, LEDGER, LIMIT, False,**ledger_kwargs)[:2]:
            return unavailable
        return {'schema_version': 1, 'available': True, 'status': 'OBSERVED_LEDGER_SNAPSHOT',
                'scope': 'ADDITIONAL_BUDGET_INCLUDES_PENDING_NOT_PROCESS_LIVENESS',
                **counts, 'source_manifest_sha256': source[1], 'ledger_sha256': ledger[1],
                'observed_at': datetime.now(timezone.utc).isoformat(), 'process_verification': 'UNKNOWN',
                'execution_approved': False}
    except (OSError, ValueError, TypeError, KeyError, OverflowError, RecursionError):
        return unavailable
