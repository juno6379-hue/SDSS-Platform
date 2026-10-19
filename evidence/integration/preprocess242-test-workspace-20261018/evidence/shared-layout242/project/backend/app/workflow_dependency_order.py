"""Deterministic sorted ready layers for an already validated dependency map.

Callers own identifier, unknown-edge, duplicate and self-edge validation. This
helper copies dependency sets, performs no I/O, and never starts execution.
"""


def topological_order(validated_dependency_map):
    """Return the original sorted-layer Kahn order, or None if stuck."""
    remaining = {identifier: set(dependencies)
                 for identifier, dependencies in validated_dependency_map.items()}
    ordered = []
    while remaining:
        ready = sorted(identifier for identifier, dependencies in remaining.items() if not dependencies)
        if not ready:
            return None
        ordered.extend(ready)
        for identifier in ready:
            remaining.pop(identifier)
        for dependencies in remaining.values():
            dependencies.difference_update(ready)
    return ordered
