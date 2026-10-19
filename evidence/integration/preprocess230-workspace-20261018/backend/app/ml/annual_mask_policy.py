"""Caller-explicit rational threshold over already observed annual mask counts."""
from .annual_quality_mask_diagnostics import _snapshot_request, inspect_annual_quality_mask_diagnostics

FALSE_FIELDS = ('quality_report_verified', 'quality_mask_verified', 'mask_semantics_verified',
    'registry_aoi_verified', 'source_authority_verified', 'scientific_accuracy_validated',
    'execution_authorized', 'state_dict_verified', 'workflow_supported')


def _keys(value, names):
    return (type(value) is dict and len(value) == len(names) and all(type(k) is str for k in value)
        and value.keys() == set(names))


def _policy(value):
    if not (_keys(value, ('schema_version', 'minimum_valid_numerator', 'minimum_valid_denominator', 'comparison'))
        and type(value['schema_version']) is int and value['schema_version'] == 1
        and type(value['minimum_valid_numerator']) is int and type(value['minimum_valid_denominator']) is int
        and 1 <= value['minimum_valid_denominator'] <= 1000000
        and 0 <= value['minimum_valid_numerator'] <= value['minimum_valid_denominator']
        and type(value['comparison']) is str and value['comparison'] == 'greater_than_or_equal'):
        raise ValueError('invalid policy')
    return dict(value)


def _counts(value):
    if not (_keys(value, ('valid_pixels', 'invalid_pixels', 'total_pixels'))
        and all(type(v) is int for v in value.values()) and 1 <= value['total_pixels'] <= 1024**2
        and 0 <= value['valid_pixels'] <= value['total_pixels']
        and 0 <= value['invalid_pixels'] <= value['total_pixels']
        and value['valid_pixels'] + value['invalid_pixels'] == value['total_pixels']):
        raise ValueError('invalid counts')
    return dict(value)


def inspect_annual_mask_policy(store, model_ref, training_report_sha256, requested_years, policy):
    """Evaluate caller policy, not QA/agency/scientific or execution approval."""
    result = {'schema_version': 1, 'scope': 'CALLER_EXPLICIT_ANNUAL_MASK_POLICY_READ_ONLY', 'status': 'INVALID_INPUT',
        'issue': None, 'parent_annual_observation': None, 'policy': None, 'per_year_observations': [],
        'annual_observation_calls': 0, 'caller_policy_evaluated': False, 'caller_policy_met': False,
        'artifact_bytes_verified': False}
    result.update({field: False for field in FALSE_FIELDS})
    try:
        fixed_policy = _policy(policy)
        ref, rows, _ = _snapshot_request(model_ref, training_report_sha256, requested_years)
    except Exception:
        result['issue'] = {'code': 'INVALID_INPUT', 'field': 'request_or_policy', 'year': None}
        return result
    result['policy'] = fixed_policy
    result['per_year_observations'] = [{'year': row['year'], 'status': 'NOT_CHECKED', 'counts': None, 'policy_met': None} for row in rows]
    result['status'] = 'ANNUAL_DIAGNOSTICS_BLOCKED'
    try:
        result['annual_observation_calls'] = 1
        parent = inspect_annual_quality_mask_diagnostics(store, ref, training_report_sha256, rows)
        result['parent_annual_observation'] = parent
        if not (type(parent) is dict and len(parent) <= 128 and all(type(k) is str for k in parent)):
            raise ValueError('invalid parent')
        if parent['status'] != 'ANNUAL_QUALITY_MASK_MATCHED_UNVERIFIED':
            result['issue'] = parent['issue'] or {'code': 'ANNUAL_DIAGNOSTICS_BLOCKED', 'field': 'annual', 'year': None}
            return result
    except Exception:
        result['issue'] = {'code': 'ANNUAL_DIAGNOSTICS_BLOCKED', 'field': 'annual', 'year': None}
        return result
    result['status'] = 'POLICY_INPUT_BLOCKED'
    current_year = None
    try:
        if not all(parent.get(key) is True for key in ('artifact_bytes_verified', 'mask_values_verified', 'registry_manifest_join_verified')):
            raise ValueError('missing full flags')
        observations = parent['mask_observations']
        if type(observations) is not list or len(observations) != len(rows):
            raise ValueError('invalid rows')
        counts = []
        for row, observation in zip(rows, observations):
            current_year = row['year']
            if not (_keys(observation, ('year', 'status', 'mask_observation', 'registry_manifest_join_verified', 'issue'))
                and type(observation['year']) is int and observation['year'] == current_year
                and observation['status'] == 'MATCHED_UNVERIFIED' and observation['issue'] is None
                and observation['registry_manifest_join_verified'] is True):
                raise ValueError('invalid row')
            mask = observation['mask_observation']
            if not (type(mask) is dict and len(mask) <= 128 and all(type(k) is str for k in mask)
                and mask.get('status') == 'REGISTERED_BINARY_MASK_VALUES_MATCHED_UNVERIFIED'
                and all(mask.get(key) is True for key in ('mask_declaration_verified', 'mask_values_verified', 'artifact_bytes_verified'))):
                raise ValueError('invalid mask result')
            counts.append(_counts(mask.get('counts')))
    except Exception:
        result['issue'] = {'code': 'POLICY_COUNTS_INVALID', 'field': 'counts', 'year': current_year}
        return result
    numerator = fixed_policy['minimum_valid_numerator']
    denominator = fixed_policy['minimum_valid_denominator']
    for output, count in zip(result['per_year_observations'], counts):
        met = count['valid_pixels'] * denominator >= count['total_pixels'] * numerator
        output.update(status='MET' if met else 'NOT_MET', counts=count, policy_met=met)
        if not met and result['issue'] is None:
            result['issue'] = {'code': 'CALLER_POLICY_NOT_MET', 'field': 'minimum_valid_ratio', 'year': output['year']}
    met = all(output['policy_met'] is True for output in result['per_year_observations'])
    result.update(status='CALLER_POLICY_MET_UNVERIFIED' if met else 'CALLER_POLICY_NOT_MET',
        caller_policy_evaluated=True, caller_policy_met=met, artifact_bytes_verified=met)
    return result
