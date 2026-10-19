"""Conservative read-only terminal metadata reconciliation; never settles a ledger."""
import copy
import hashlib
import json
import math
import re
from pathlib import Path
from urllib.parse import urlsplit


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key')
        result[key] = value
    return result


def _constant(value):
    raise ValueError('Non-finite JSON number')


def _finite(value):
    if type(value) is float and not math.isfinite(value):
        raise ValueError('Non-finite JSON number')
    if type(value) is dict:
        for item in value.values():
            _finite(item)
    if type(value) is list:
        for item in value:
            _finite(item)


def _confined(root, value):
    text = str(value)
    if text.startswith(('\\\\', '//')) or urlsplit(text).netloc or urlsplit(text).scheme not in ('',) and not re.match(r'^[A-Za-z]:[\\/]', text):
        raise ValueError('Remote paths are prohibited')
    path = Path(value)
    path = path if path.is_absolute() else root / path
    path.absolute().relative_to(root)
    resolved = path.resolve()
    resolved.relative_to(root)
    return resolved


def _fingerprint(path):
    if not path.exists():
        return {'path': str(path), 'exists': False}
    if not path.is_file():
        raise ValueError('Evidence must be a regular file')
    before = path.stat()
    payload = path.read_bytes()
    after = path.stat()
    if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
        raise ValueError('Evidence changed while reading')
    return {'path': str(path), 'exists': True, 'sha256': hashlib.sha256(payload).hexdigest(), 'bytes': len(payload)}


def _digest(document):
    return hashlib.sha256(json.dumps(document, sort_keys=True, allow_nan=False).encode()).hexdigest()


def _uint(value):
    return type(value) is int and value >= 0


def inspect_recovery_terminal(data_root):
    """Classify only available metadata; missing evidence is not a worker completion."""
    requested = Path(data_root)
    if str(requested).startswith(('\\\\', '//')) or urlsplit(str(requested)).netloc:
        raise ValueError('Data root must be local')
    root = requested.resolve()
    references = {}
    logical_targets = {}

    def read(path):
        logical_path = Path(path)
        path = _confined(root, logical_path)
        logical_targets[logical_path] = path
        reference = _fingerprint(path)
        references[path] = reference
        if not reference['exists']:
            return None, 'MISSING'
        try:
            payload = path.read_bytes()
            if hashlib.sha256(payload).hexdigest() != reference['sha256']:
                raise ValueError('Evidence changed while reading')
            document = json.loads(payload, object_pairs_hook=_pairs, parse_constant=_constant)
            _finite(document)
            if type(document) is not dict:
                return None, 'INVALID'
            return document, 'PRESENT'
        except (UnicodeError, json.JSONDecodeError):
            return None, 'INVALID'
        except ValueError as exc:
            if 'changed' in str(exc):
                raise
            return None, 'INVALID'

    ledger_path = root / 'first-group-training-budget/global-ledger.json'
    ledger, ledger_status = read(ledger_path)
    if ledger_status != 'PRESENT' or type(ledger.get('batches')) is not dict:
        raise ValueError('Global ledger is missing or invalid')
    batches = ledger['batches']
    if any(type(batch) is not dict for batch in batches.values()):
        raise ValueError('Invalid ledger batches')
    global_valid = all(_uint(ledger.get(k)) for k in ('new_charged_bytes', 'additional_maximum_bytes', 'external_research_metadata_body_bytes')) and all(_uint(b.get('charged_bytes')) for b in batches.values())
    global_sum_matches = (ledger['new_charged_bytes'] == ledger['external_research_metadata_body_bytes'] + sum(b['charged_bytes'] for b in batches.values())) if global_valid else False
    budget_in_bounds = global_valid and ledger['new_charged_bytes'] <= ledger['additional_maximum_bytes']
    pending = []
    for key, batch in sorted(batches.items()):
        if batch.get('status') != 'pending':
            continue
        if type(key) is not str or not key or key in ('.', '..') or any(c in key for c in '/\\:'):
            raise ValueError('Batch key must be a single local name')
        logical_directory = root / 'first-group-training-esri-v1/sources' / key
        directory = _confined(root, logical_directory)
        logical_targets[logical_directory] = directory
        directory.relative_to((root / 'first-group-training-esri-v1/sources').resolve())
        documents, states = {}, {}
        for name in ('config.json', 'window-state.json', 'worker-result.json', 'annual-window-report.json'):
            documents[name], states[name] = read(logical_directory / name)
        issues = [{'code': name.upper().replace('.', '_').replace('-', '_') + '_' + state, 'kind': state} for name, state in states.items() if state != 'PRESENT']

        def issue(code, kind='MISMATCH'):
            issues.append({'code': code, 'kind': kind})

        def counter(doc, field, prefix):
            value = doc.get(field)
            if not _uint(value):
                issue(prefix + '_' + field.upper() + '_INVALID', 'INVALID')
                return None
            return value

        reserved = batch.get('reserved_bytes')
        charged_preserved = batch.get('charged_bytes')
        if not _uint(reserved) or reserved == 0 or not _uint(charged_preserved):
            issue('PENDING_RESERVATION_INVALID', 'INVALID')
        elif reserved != charged_preserved:
            issue('PENDING_RESERVATION_MISMATCH')
        config = documents['config.json']
        state = documents['window-state.json']
        worker = documents['worker-result.json']
        report = documents['annual-window-report.json']
        normalized = None
        raw_config_matches = None
        normalized_config_matches = None
        if config is not None:
            raw_config_matches = _digest(config) == batch.get('config_sha256')
            if not raw_config_matches:
                issue('RAW_CONFIG_LEDGER_MISMATCH')
            normalized = copy.deepcopy(config)
            years = normalized.get('years')
            if years:
                if type(years) is not list or any(type(year) is not int or not 2015 <= year <= 2026 for year in years):
                    issue('CONFIG_YEARS_INVALID', 'INVALID')
                    normalized = None
                else:
                    normalized['periods'] = {str(year): {'start_date': f"{year}-{config.get('season_start', '06-01')}", 'end_date': f"{year}-{config.get('season_end', '09-30')}"} for year in years}
            if normalized is not None and type(normalized.get('periods')) is not dict:
                issue('CONFIG_PERIODS_INVALID', 'INVALID')
                normalized = None
        upper = measured = cog = total = metadata_charged = metadata_read = state_legacy = None
        if state is not None:
            upper = counter(state, 'http_body_bytes', 'STATE')
            measured = counter(state, 'http_body_bytes_measured', 'STATE')
            state_legacy = counter(state, 'legacy_charged_bytes_preserved', 'STATE')
            if None not in (state_legacy, measured, upper) and state_legacy + measured > upper:
                issue('STATE_LEGACY_PLUS_MEASURED_EXCEEDS_UPPER')
            if None not in (state_legacy, upper) and state_legacy > upper:
                issue('STATE_LEGACY_EXCEEDS_UPPER')
            if upper is not None and measured is not None and measured > upper:
                issue('STATE_MEASURED_EXCEEDS_UPPER')
            if normalized is not None:
                normalized_config_matches = _digest(normalized) == state.get('config_sha256')
                if not normalized_config_matches:
                    issue('NORMALIZED_CONFIG_STATE_MISMATCH')
        if worker is not None:
            if worker.get('key') != key:
                issue('WORKER_KEY_MISMATCH')
            cog = counter(worker, 'cog_charged_bytes', 'WORKER')
            total = counter(worker, 'charged_bytes', 'WORKER')
            metadata = worker.get('metadata_budget')
            if type(metadata) is not dict:
                issue('WORKER_METADATA_BUDGET_INVALID', 'INVALID')
            else:
                metadata_charged = counter(metadata, 'charged_bytes', 'METADATA')
                metadata_read = counter(metadata, 'read_body_bytes', 'METADATA')
                maximum = counter(metadata, 'maximum_bytes', 'METADATA')
                if None not in (metadata_read, metadata_charged, maximum) and not metadata_read <= metadata_charged <= maximum:
                    issue('METADATA_COUNTER_RANGE_MISMATCH')
            if None not in (cog, metadata_charged, total) and cog + metadata_charged != total:
                issue('WORKER_CHARGE_SUM_MISMATCH')
            if _uint(reserved) and total is not None and total > reserved:
                issue('WORKER_CHARGE_EXCEEDS_RESERVATION')
            if cog is not None and upper is not None and cog != upper:
                issue('WORKER_STATE_COG_MISMATCH')
            report_path = worker.get('report_path')
            if type(report_path) is not str or not report_path:
                issue('WORKER_REPORT_PATH_MISSING', 'MISSING')
            elif _confined(root, report_path) != (directory / 'annual-window-report.json').resolve():
                issue('WORKER_REPORT_PATH_MISMATCH')
            if worker.get('error') is not None:
                issue('WORKER_ERROR_RECORDED', 'UNKNOWN')
        if config is not None:
            config_max = counter(config, 'max_total_bytes', 'CONFIG')
            prior = config.get('prior_download_budget_bytes', 0)
            if not _uint(prior):
                issue('CONFIG_PRIOR_BYTES_INVALID', 'INVALID')
            elif config_max is not None and (prior > config_max or upper is not None and upper + prior > config_max):
                issue('STATE_CONFIG_BUDGET_EXCEEDED')
        if report is not None:
            if report.get('executed') is not True or report.get('status') != 'executed_windows_readiness_unverified':
                issue('SOURCE_REPORT_EXECUTION_CONTRACT_MISMATCH')
            report_upper = counter(report, 'http_body_bytes_upper_bound', 'REPORT')
            report_measured = counter(report, 'http_body_bytes_measured', 'REPORT')
            if report_upper is not None and upper is not None and report_upper != upper:
                issue('REPORT_STATE_UPPER_MISMATCH')
            if report_measured is not None and measured is not None and report_measured != measured:
                issue('REPORT_STATE_MEASURED_MISMATCH')
            if report_upper is not None and report_measured is not None and report_measured > report_upper:
                issue('REPORT_MEASURED_EXCEEDS_UPPER')
            legacy = counter(report, 'legacy_charged_bytes_preserved', 'REPORT')
            if None not in (legacy, report_measured, report_upper) and legacy + report_measured > report_upper:
                issue('REPORT_LEGACY_PLUS_MEASURED_EXCEEDS_UPPER')
            if legacy is not None and report_upper is not None and legacy > report_upper:
                issue('REPORT_LEGACY_EXCEEDS_UPPER')
            if state is not None and legacy != state_legacy:
                issue('REPORT_STATE_LEGACY_MISMATCH')
            prior = counter(report, 'prior_download_budget_bytes', 'REPORT')
            combined = counter(report, 'combined_budget_charged_bytes', 'REPORT')
            if None not in (prior, combined, report_upper) and combined != prior + report_upper:
                issue('REPORT_COMBINED_BUDGET_MISMATCH')
            if config is not None and prior != config.get('prior_download_budget_bytes', 0):
                issue('REPORT_CONFIG_PRIOR_MISMATCH')
            if None not in (legacy, report_upper, report_measured):
                expected_body = report_measured if legacy == 0 and report_upper == report_measured else None
                observed_body = report.get('http_body_bytes')
                if type(observed_body) is not type(expected_body) or observed_body != expected_body:
                    issue('REPORT_HTTP_BODY_MEASUREMENT_CONTRACT_MISMATCH')
            if config is not None and report.get('common_bands') != config.get('bands'):
                issue('REPORT_CONFIG_BANDS_MISMATCH')
            if normalized is not None and report.get('years') != list(normalized['periods']):
                issue('REPORT_CONFIG_YEARS_MISMATCH')
        if not global_valid or not global_sum_matches or not budget_in_bounds:
            issue('GLOBAL_LEDGER_COUNTERS_INVALID_OR_INCONSISTENT', 'INVALID' if not global_valid else 'MISMATCH')
        kinds = {item['kind'] for item in issues}
        classification = next((kind for kind in ('INVALID', 'MISMATCH', 'MISSING') if kind in kinds), 'CONSISTENT_METADATA' if not issues else 'UNKNOWN')
        pending.append({'key': key, 'classification': classification, 'status': 'BLOCKED', 'issues': issues,
            'artifact_states': states, 'reserved_bytes_preserved': reserved, 'charged_bytes_preserved': charged_preserved,
            'raw_config_matches_ledger': raw_config_matches, 'normalized_config_matches_window_state': normalized_config_matches,
            'observed_worker_charged_bytes': total,
            'complete_transfer_accounting': 'UNKNOWN',
            'cog_unmeasured_or_reserved_bytes': upper - measured if None not in (upper, measured) and upper >= measured else None,
            'metadata_unmeasured_or_reserved_bytes': metadata_charged - metadata_read if None not in (metadata_charged, metadata_read) and metadata_charged >= metadata_read else None,
            'source_report_identity_binding': 'UNKNOWN_NO_CONFIG_DIGEST_IN_REPORT',
            'aggregate_applied_exactly_once': 'UNKNOWN', 'process_exit_verified': False,
            'settlement_authorized': False, 'execution_authorized': False, 'automatic_resume_allowed': False,
            'proposed_refund_bytes': 0, 'action': 'PRESERVE_FULL_RESERVATION'})
    for logical_path, target in logical_targets.items():
        if _confined(root, logical_path) != target:
            raise ValueError('Evidence logical path target changed during inspection')
    for path, reference in references.items():
        if _confined(root, path) != path or _fingerprint(path) != reference:
            raise ValueError('Evidence changed during inspection')
    return {'schema_version': 1, 'kind': 'RECOVERY_TERMINAL_METADATA_RECONCILIATION', 'status': 'BLOCKED',
        'mode': 'READ_ONLY', 'artifacts': list(references.values()), 'pending_batches': pending,
        'ledger_internal_sum_matches': global_sum_matches, 'ledger_budget_in_bounds': budget_in_bounds,
        'pending_reserved_bytes_preserved': sum(b['reserved_bytes_preserved'] for b in pending) if all(_uint(b['reserved_bytes_preserved']) for b in pending) else None,
        'settlement_authorized': False, 'execution_authorized': False, 'automatic_resume_allowed': False,
        'process_health_verified': False, 'aggregate_applied_exactly_once': 'UNKNOWN',
        'proposed_refund_bytes': 0, 'network_requests': 0, 'source_files_written': 0,
        'limitation': 'Consistent metadata does not establish complete transfer measurement, process exit, source identity or exactly-once aggregate application.'}
