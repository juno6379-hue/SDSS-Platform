"""Pure optional model declaration checks; never resolve or normalize a model.

Callers retain their own JSON Schema, shape, SHA-256 and URI policies. None
means no declaration to inspect here, not a schema-valid explicit null.
"""
from .execution_input_binding import _text


def model_reference_issue(ref):
    """Return the first supported declaration issue, or None; perform no I/O."""
    if ref is None:
        return None
    if (type(ref) is not dict
            or any(not _text(ref.get(key)) for key in ('id', 'version'))
            or ('role' in ref and not _text(ref['role']))):
        return 'MODEL_REFERENCE_INVALID'
    if ref['version'].strip().lower() in {'latest', 'current'}:
        return 'MODEL_VERSION_NOT_PINNED'
    return None
