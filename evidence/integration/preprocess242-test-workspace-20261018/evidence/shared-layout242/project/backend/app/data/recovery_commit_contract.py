"""Pure, unverified observations of caller-declared recovery commit phases.

This does not read artifacts, record a journal, settle a ledger, or authorize work.
"""

import re


_PHASES = ("PREPARED", "LEDGER_RECORDED", "AGGREGATE_RECORDED", "COMMITTED")
_TARGETS = ("ledger_sha256", "aggregate_sha256", "run_result_sha256")
_IDENTITY = ("operation_id", "batch_key", "config_sha256", "terminal_sha256",
             "reconciliation_sha256", "before", "expected_after")
_KEYS = frozenset(("schema_version", "phase", "phase_evidence_sha256", "observed", *_IDENTITY))
_PROOFS = ("terminal_sha256", "reconciliation_sha256", "phase_evidence_sha256")


def _sha(value):
    return type(value) is str and len(value) == 64 and re.fullmatch("[0-9a-f]{64}", value) is not None


def _issue(code, field, side):
    return {"code": code, "field": field, "side": side}


def _keys(value, expected):
    return (type(value) is dict and len(value) == len(expected)
            and all(type(key) is str for key in value) and value.keys() == set(expected))


def _validate(value, side):
    if not _keys(value, _KEYS):
        return _issue("OBSERVATION_SCHEMA_INVALID", "observation", side)
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        return _issue("OBSERVATION_SCHEMA_INVALID", "schema_version", side)
    for field in ("operation_id", "batch_key"):
        item = value[field]
        if (type(item) is not str or not 1 <= len(item) <= 128 or item in (".", "..")
                or re.fullmatch("[A-Za-z0-9._-]+", item) is None):
            return _issue("OBSERVATION_ID_INVALID", field, side)
    if type(value["phase"]) is not str or value["phase"] not in _PHASES:
        return _issue("PHASE_INVALID", "phase", side)
    for field in ("config_sha256", *_PROOFS):
        if field in _PROOFS and value[field] is None:
            continue
        if not _sha(value[field]):
            return _issue("SHA256_INVALID", field, side)
    for field in ("before", "expected_after", "observed"):
        mapping = value[field]
        if not _keys(mapping, _TARGETS):
            return _issue("OBSERVATION_SCHEMA_INVALID", field, side)
        for target in _TARGETS:
            if field == "observed" and mapping[target] is None:
                continue
            if not _sha(mapping[target]):
                return _issue("SHA256_INVALID", field + "." + target, side)
    for field in _PROOFS:
        if value[field] is None:
            return _issue("EVIDENCE_MISSING", field, side)
    for target in _TARGETS:
        if value["observed"][target] is None:
            return _issue("EVIDENCE_MISSING", "observed." + target, side)
    phase_index = _PHASES.index(value["phase"])
    for index, target in enumerate(_TARGETS):
        expected = value["expected_after" if index < phase_index else "before"][target]
        if value["observed"][target] != expected:
            return _issue("PHASE_OBSERVATION_MISMATCH", "observed." + target, side)
    return None


def validate_recovery_commit_transition(previous, current):
    """Check two bounded metadata claims; even consistent claims stay BLOCKED.

    A missing previous observation only permits PREPARED. Neither observation is
    authenticated, and identical digests cannot establish that a write occurred.
    """
    phase = None
    if _keys(current, _KEYS) and type(current["phase"]) is str and current["phase"] in _PHASES:
        phase = current["phase"]
    result = {
        "schema_version": 1, "scope": "RECOVERY_COMMIT_PHASE_CLAIMS_ONLY",
        "status": "BLOCKED", "metadata_transition": "REJECTED", "current_phase": phase,
        "issue": None, "claim_verification": "UNVERIFIED", "exactly_once_applied": "UNKNOWN",
        "settlement_authorized": False, "refund_authorized": False,
        "restart_authorized": False, "write_authorized": False,
        "execution_authorized": False, "commit_executed": False,
        "proposed_refund_bytes": 0, "source_files_read": 0,
        "source_files_written": 0, "network_requests": 0,
    }
    for observation, side in ((previous, "PREVIOUS"), (current, "CURRENT")):
        if observation is None and side == "PREVIOUS":
            continue
        problem = _validate(observation, side)
        if problem:
            result["issue"] = problem
            return result
    if previous is None:
        if phase == "PREPARED":
            result["metadata_transition"] = "INITIAL_PREPARED"
        else:
            result["issue"] = _issue("INITIAL_PHASE_INVALID", "phase", "CURRENT")
        return result
    for field in _IDENTITY:
        if previous[field] != current[field]:
            result["issue"] = _issue("OPERATION_IDENTITY_CONFLICT", field, "COMPARISON")
            return result
    distance = _PHASES.index(phase) - _PHASES.index(previous["phase"])
    if distance == 0:
        # Validation has already restricted every leaf to exact str/int types.
        if previous == current:
            result["metadata_transition"] = "IDENTICAL_REPLAY"
        else:
            result["issue"] = _issue("REPLAY_CONFLICT", "observation", "COMPARISON")
    elif distance == 1:
        result["metadata_transition"] = "NEXT_PHASE"
    else:
        result["issue"] = _issue("PHASE_REGRESSION" if distance < 0 else "PHASE_SKIP", "phase", "COMPARISON")
    return result
