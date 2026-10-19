"""Explicit bounded existing-ledger adapter. No collection/network integration."""
from contextlib import contextmanager
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from types import MappingProxyType
from ..ml import manifest_resource_profile as profile
from ..ml.split_json_io import _local
from . import targeted_atomic_json as writer

LEDGER_CAP = 8388608


def _need(value, code):
    if not value:
        raise ValueError(code)


def _same(left, right):
    # JSON equality must distinguish bool/int and preserve list ordering.
    return json.dumps(left, sort_keys=True, allow_nan=False, ensure_ascii=False, separators=(',', ':')) == json.dumps(
        right, sort_keys=True, allow_nan=False, ensure_ascii=False, separators=(',', ':'))


class LedgerMetadataIO:
    def __init__(self, *, root, ledger_ref, historical_refs, allowed_batches, manifest_profile):
        _need(type(manifest_profile) is dict and set(manifest_profile) == {'name','sha256'} and
              all(type(manifest_profile[k]) is str and manifest_profile[k] == writer.EXPECTED_MARKER[k]
                  for k in writer.EXPECTED_MARKER), 'LEDGER_PROFILE_INVALID')
        _need(dict(profile.MARKER) == dict(writer.EXPECTED_MARKER) and profile.active() is not None,
              'LEDGER_EXPLICIT_SCOPE_REQUIRED')
        self._budget = profile.active()
        self._root = _local(root)
        _need(self._root.is_absolute() and self._root.resolve() == self._root, 'LEDGER_ROOT_INVALID')
        _need(type(historical_refs) is list and 1 <= len(historical_refs) <= 100,
              'LEDGER_HISTORY_REFS_INVALID')
        def reference(ref):
            _need(type(ref) is dict and set(ref) == {'path','sha256'} and type(ref['path']) is str,
                  'LEDGER_REF_INVALID')
            _need(type(ref['sha256']) is str and re.fullmatch('[a-f0-9]{64}',ref['sha256']) is not None,
                  'LEDGER_REF_INVALID')
            path = _local(ref['path'])
            _need(path.resolve() == path and path.is_relative_to(self._root) and path != self._root,
                  'LEDGER_REF_OUTSIDE_ROOT')
            return (path, ref['sha256'])
        self._path, self._pin = reference(ledger_ref)
        self._history = tuple(reference(ref) for ref in historical_refs)
        all_paths = [self._path] + [path for path, _ in self._history]
        _need(len(set(all_paths)) == len(all_paths), 'LEDGER_REF_ALIAS')
        _need(type(allowed_batches) is dict and 1 <= len(allowed_batches) <= 2,
              'LEDGER_ALLOWLIST_INVALID')
        for key, sha in allowed_batches.items():
            _need(type(key) is str and 0 < len(key.encode('utf-8')) <= 256 and
                  not any(ord(c) < 32 for c in key) and type(sha) is str and
                  re.fullmatch('[a-f0-9]{64}',sha) is not None, 'LEDGER_ALLOWLIST_INVALID')
        self._allowed = MappingProxyType(dict(allowed_batches))
        self._owner = None
        self._stopped = False
        self._owned = set()
        self._before = None

    def _check(self, ledger):
        _need(not self._stopped, 'LEDGER_ADAPTER_STOPPED')
        _need(self._owner is ledger and profile.active() is self._budget, 'LEDGER_SCOPE_OR_OWNER_CHANGED')

    def _references(self):
        return [{'path':str(p), 'sha256':sha} for p, sha in self._history]

    def _physical(self, path, sha):
        # Parent identity/nlink rules match the writer. Read+hash uses one bounded fd.
        parents = writer._parents(self._root, path)
        stamp = writer._identity(path, file=True)
        value, _, _ = profile.read_metadata(path, 'status_report', sha, maximum_bytes=LEDGER_CAP)
        writer._check_parents(parents)
        _need(writer._identity(path, file=True) == stamp, 'LEDGER_INPUT_CHANGED')
        _need(type(value) is dict, 'LEDGER_OBJECT_REQUIRED')
        return value

    def _histories(self):
        for path, sha in self._history:
            self._physical(path, sha)

    def _structure(self, state, ledger):
        _need(type(state) is dict and type(state.get('version')) is int and state['version'] == 1,
              'LEDGER_STATE_INVALID')
        _need(_same(state.get('historical_ledgers'), self._references()), 'LEDGER_HISTORY_BINDING_INVALID')
        _need(type(state.get('batches')) is dict and type(state.get('rate_limit_active')) is bool,
              'LEDGER_STATE_INVALID')
        for field in ('additional_maximum_bytes','historical_charged_bytes','new_charged_bytes',
                      'combined_maximum_bytes','external_research_metadata_body_bytes'):
            _need(type(state.get(field)) is int and state[field] >= 0, 'LEDGER_STATE_INVALID')
        _need(state['additional_maximum_bytes'] == ledger.additional_budget and
              state['combined_maximum_bytes'] == state['historical_charged_bytes'] + ledger.additional_budget and
              state['new_charged_bytes'] <= ledger.additional_budget, 'LEDGER_BUDGET_BINDING_INVALID')

    def bind(self, ledger):
        _need(not self._stopped, 'LEDGER_ADAPTER_STOPPED')
        try:
            # Review F2: every bind failure (including a second bind) stops the adapter.
            _need(self._owner is None, 'LEDGER_ADAPTER_ALREADY_BOUND')
            _need(_local(ledger.path) == self._path and ledger.historical_paths == [p for p, _ in self._history],
                  'LEDGER_CONSTRUCTOR_BINDING_INVALID')
            _need(type(ledger.additional_budget) is int and type(ledger.initial_metadata_charge) is int,
                  'LEDGER_BUDGET_BINDING_INVALID')
            # Existing destination/parents must be valid before locked() can create a lock.
            writer._parents(self._root, self._path)
            writer._identity(self._path, file=True)
            self._owner = ledger
            with ledger.locked():
                state = self.read(ledger)
                _need(not any(k in state['batches'] for k in self._allowed), 'LEDGER_ALLOWED_KEY_NOT_NEW')
        except BaseException:
            self._stopped = True
            raise

    @contextmanager
    def stop_on_failure(self, ledger):
        """Review F1: failures raised by legacy checks between read and save also stop."""
        _need(not self._stopped, 'LEDGER_ADAPTER_STOPPED')
        try:
            yield
        except BaseException:
            self._stopped = True
            raise

    def read(self, ledger):
        try:
            self._check(ledger)
            with profile.io_transaction():
                state = self._physical(self._path, self._pin)
                self._structure(state, ledger)
                self._histories()
                self._before = copy.deepcopy(state)
                return state
        except BaseException:
            self._stopped = True
            raise

    def reserve_arguments(self, ledger, key, maximum, config_sha256):
        try:
            self._check(ledger)
            _need(type(key) is str and key in self._allowed and type(config_sha256) is str and
                  config_sha256 == self._allowed[key] and type(maximum) is int and
                  0 < maximum <= 2*1024**3, 'LEDGER_RESERVE_NOT_ALLOWED')
        except BaseException:
            self._stopped = True
            raise

    def settle_arguments(self, ledger, key, measured, report_path):
        try:
            self._check(ledger)
            _need(type(key) is str and key in self._owned and type(measured) is int and measured >= 0 and
                  (report_path is None or type(report_path) is str), 'LEDGER_SETTLE_NOT_OWNED')
        except BaseException:
            self._stopped = True
            raise

    def _transition(self, state, ledger):
        before = self._before
        _need(before is not None, 'LEDGER_READ_REQUIRED')
        self._structure(state, ledger)
        old, new = before['batches'], state['batches']
        added = set(new) - set(old)
        changed = [k for k in old if k in new and not _same(old[k],new[k])]
        _need(not (set(old)-set(new)), 'LEDGER_TRANSITION_INVALID')
        expected = copy.deepcopy(before)
        reserved_key = None
        if len(added) == 1 and not changed:
            key = next(iter(added)); batch = new[key]
            _need(key in self._allowed and type(batch) is dict and
                  set(batch) == {'status','reserved_bytes','charged_bytes','config_sha256'} and
                  batch['status'] == 'pending' and type(batch['reserved_bytes']) is int and
                  0 < batch['reserved_bytes'] <= 2*1024**3 and
                  type(batch['charged_bytes']) is int and batch['charged_bytes'] == batch['reserved_bytes'] and
                  batch['config_sha256'] == self._allowed[key] and not before['rate_limit_active'],
                  'LEDGER_TRANSITION_INVALID')
            expected['batches'][key] = copy.deepcopy(batch)
            expected['new_charged_bytes'] += batch['reserved_bytes']
            reserved_key = key
        elif not added and len(changed) == 1:
            key = changed[0]; batch = new[key]; prior = old[key]
            _need(key in self._owned and type(prior) is dict and prior.get('status') == 'pending' and
                  type(batch) is dict and type(batch.get('charged_bytes')) is int and
                  0 <= batch['charged_bytes'] <= prior['reserved_bytes'] and batch.get('status') == 'settled' and
                  (batch.get('report_path') is None or type(batch.get('report_path')) is str),
                  'LEDGER_TRANSITION_INVALID')
            expected['batches'][key].update(status='settled', charged_bytes=batch['charged_bytes'],
                                            report_path=batch.get('report_path'))
            expected['new_charged_bytes'] -= prior['reserved_bytes'] - batch['charged_bytes']
            if state.get('last_rate_limit') != before.get('last_rate_limit') or state['rate_limit_active'] != before['rate_limit_active']:
                _need(state['rate_limit_active'] is True and bool(state.get('last_rate_limit')),
                      'LEDGER_TRANSITION_INVALID')
                expected['rate_limit_active'] = True
                expected['last_rate_limit'] = copy.deepcopy(state['last_rate_limit'])
        else:
            raise ValueError('LEDGER_TRANSITION_INVALID')
        expected.pop('updated_at', None)
        actual = copy.deepcopy(state); actual.pop('updated_at', None)
        _need(_same(expected, actual), 'LEDGER_TRANSITION_INVALID')
        return reserved_key

    def save(self, ledger, state):
        result = None
        try:
            self._check(ledger)
            with profile.io_transaction():
                # Review F3: the validated copy is exactly what is written and recorded.
                candidate = copy.deepcopy(state)
                reserved_key = self._transition(candidate, ledger)
                self._histories()
                candidate['updated_at'] = datetime.now(timezone.utc).isoformat()
                result = writer.replace_json_value(self._root, self._path, candidate, role='ledger',
                    expected_sha256=self._pin, manifest_profile=dict(profile.MARKER))
                self._histories()  # Failure here is after apply: stop, never refund/rollback.
                self._pin = result.sha256
                self._before = copy.deepcopy(candidate)
                if reserved_key is not None:
                    self._owned.add(reserved_key)
                if type(state) is dict:
                    state['updated_at'] = candidate['updated_at']
                return None
        except BaseException as exc:
            self._stopped = True
            exc.ledger_metadata_commit_outcome = ('APPLIED' if result is not None else
                getattr(exc, 'atomic_json_commit_outcome', 'NOT_ATTEMPTED'))
            raise
