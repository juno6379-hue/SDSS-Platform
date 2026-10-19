"""Pure existing manifest membership check, separate from readiness/approval.

The caller owns manifest selection and public error messages/status codes.
No normalization, duplicate selection, registry access, or policy is added.
"""


def agent_capability_issue(agent, capability_id):
    """Return the existing missing-agent/membership issue, or None on match.

    Preserve Python list membership and existing malformed-manifest exceptions.
    A match establishes registration only, never execution/scientific readiness.
    """
    if agent is None:
        return 'AGENT_NOT_IMPLEMENTED'
    if capability_id not in [capability['capability_id'] for capability in agent['capabilities']]:
        return 'INVALID_REQUEST'
    return None
