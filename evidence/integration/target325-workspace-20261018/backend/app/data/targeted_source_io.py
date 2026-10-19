"""Opt-in local preflight only; no coordinator, worker, reservation or network."""
from .targeted_source_profile import validate_request_v3, ROLE_LIMITS, MARKER, DESCRIPTOR
from ..ml import manifest_resource_profile as profile
from ..ml.per_scene_normalization_files import _root, _relative
from types import MappingProxyType


ROLES = MappingProxyType({'source': 'source', 'proposal': 'proposal', 'boundary': 'boundary',
                          'ledger': 'status_report', 'lineage': 'readiness'})


class _Reader:
    def __init__(self, root):
        self.root = root
        self.cache = {}
        self.pins = {}

    def read(self, ref, role):
        if role not in ROLES:
            raise profile.ProfileResourceError('TARGET_SOURCE_JSON_ROLE_INVALID')
        path = _relative(self.root, ref['path'], 'profile_json')
        json_role, maximum = ROLES[role], ROLE_LIMITS[role]
        key = (path, role)
        logical, identity = profile.metadata_identity(path, json_role)
        if identity[0] > maximum:
            raise profile.ProfileResourceError('MANIFEST_JSON_FILE_LIMIT')
        if key in self.cache:
            old_identity, old_pin, value = self.cache[key]
            if old_identity != identity or old_pin != ref['sha256']:
                raise profile.ProfileResourceError('MANIFEST_JSON_CHANGED')
            return logical, value
        value, digest, _ = profile.read_metadata(path, json_role, ref['sha256'], maximum_bytes=maximum)
        after_logical, after = profile.metadata_identity(path, json_role)
        if after_logical != logical or identity != after:
            raise profile.ProfileResourceError('MANIFEST_JSON_CHANGED')
        if role == 'source' and (type(value) is not dict or type(value.get('scenes')) is not list):
            raise profile.ProfileResourceError('TARGET_SOURCE_MANIFEST_INVALID')
        self.cache[key] = (after, digest, value)
        self.pins[key] = (json_role, maximum, digest)
        return logical, value

    def recheck(self):
        for (path, role), (json_role, maximum, digest) in self.pins.items():
            before = profile.metadata_identity(path, json_role)
            if before[1] != self.cache[(path, role)][0]:
                raise profile.ProfileResourceError('MANIFEST_JSON_CHANGED')
            if profile.bounded_json_digest(path, json_role, maximum_bytes=maximum) != digest:
                raise profile.ProfileResourceError('MANIFEST_JSON_PIN_MISMATCH')
            if profile.metadata_identity(path, json_role) != before:
                raise profile.ProfileResourceError('MANIFEST_JSON_CHANGED')


def run_explicit_local_preflight(project_root, request, base_config):
    # No path/root/stat/open precedes the pure exact-marker contract validation.
    checked = validate_request_v3(request)
    value = checked.to_dict()
    if dict(profile.MARKER) != dict(MARKER) or dict(profile.DESCRIPTOR) != dict(DESCRIPTOR):
        raise profile.ProfileResourceError('TARGET_SOURCE_PROFILE_IMPLEMENTATION_MISMATCH')
    with profile.scope(MARKER['name']) as budget:
        root = _root(project_root)
        reader = _Reader(root)
        reader.read(value['plan']['current_manifest_ref'], 'source')
        reader.read(value['ledger_ref'], 'ledger')
        from .targeted_bare_plan import _prepare_targeted_bare_jobs
        result = _prepare_targeted_bare_jobs(root, value['plan'], base_config, _metadata_reader=reader.read)
        reader.recheck()
        result.update(manifest_profile=dict(MARKER), request_schema_version=3,
                      request_sha256=checked.request_sha256, metadata_scope='LOCAL_PREFLIGHT_JSON_ONLY',
                      metadata_usage={'read_bytes': budget.reads, 'write_bytes': budget.writes,
                                      'json_io_bytes': budget.bytes, 'maximum_bytes': budget.maximum},
                      execution_supported=False, coordinator_connected=False, training_ready=False)
        return result
