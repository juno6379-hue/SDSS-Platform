"""Local preparation controller only. No HTTP, collector or execution authority."""
import os
import re
import stat

from .quality_mask_bundle import _copy_json
from .targeted_asset_geometry import inspect_targeted_asset_geometry
from .targeted_scene_claims import SceneClaimRegistry, SPLITS
from ..ml.per_scene_normalization_files import _root


def _directory_identity(path):
    attributes = path.lstat()
    if (not stat.S_ISDIR(attributes.st_mode) or path.is_symlink() or
            getattr(attributes, 'st_file_attributes', 0) & 0x400):
        raise ValueError('OUTPUT_PATH_INVALID')
    return attributes.st_dev, attributes.st_ino


def _leaf(value):
    if type(value) is not str or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}', value):
        return False
    return value.upper() not in {'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(1, 10)),
                                *(f'LPT{i}' for i in range(1, 10))}


class TargetedPreparationController:
    """One process, shared SceneClaimRegistry, existing private output parent.

    The caller must share the *same* registry across all workers. This controller
    neither validates seed completeness nor makes claims persistent. Failed scene
    claims stay consumed (fail closed); only our still-identical empty output
    directory may be removed. Parent directories are never created or removed.
    """
    def __init__(self, project_root, output_root, fixed_split, scene_claims):
        self._issue = 'CONTROLLER_INVALID'
        try:
            if fixed_split not in SPLITS or not isinstance(scene_claims, SceneClaimRegistry):
                return
            root = _root(project_root)
            parent = _root(output_root)
            if not parent.is_relative_to(root/'data') or parent == root/'data':
                return
            self._root, self._parent = root, parent
            self._parent_identity = _directory_identity(parent)
            self._split, self._claims = fixed_split, scene_claims
            self._issue = None
        except Exception:
            pass

    def _check_parent(self):
        if _root(self._root) != self._root or _root(self._parent) != self._parent:
            raise ValueError('OUTPUT_PATH_INVALID')
        if _directory_identity(self._parent) != self._parent_identity:
            raise ValueError('OUTPUT_PARENT_CHANGED')

    def prepare(self, request):
        """Reserve an empty leaf, claim scene and inspect pinned local assets.

        Exact request keys: schema_version=1, scene_id, split, owner_id,
        output_name (portable single component), geometry_request (160 contract).
        Output may describe local observations; execution_supported is ALWAYS false.
        """
        result = {'schema_version': 1, 'scope': 'LOCAL_TARGETED_PREPARATION_ONLY',
                  'status': 'BLOCKED', 'issue': self._issue, 'output_reserved': False,
                  'output_relative_path': None, 'cleanup': 'NOT_NEEDED',
                  'scene_claim': None, 'asset_geometry': None,
                  'execution_supported': False, 'inventory_verified': False,
                  'budget_verified': False, 'rate_limit_verified': False,
                  'quality_verified': False, 'preprocessing_complete': False,
                  'settlement_complete': False, 'training_ready': False}
        if self._issue:
            return result
        output, identity = None, None
        try:
            value = _copy_json(request, 'request')
            if not (type(value) is dict and value.keys() == {
                    'schema_version', 'scene_id', 'split', 'owner_id', 'output_name', 'geometry_request'}
                    and type(value['schema_version']) is int and value['schema_version'] == 1
                    and _leaf(value['output_name'])):
                raise ValueError('REQUEST_INVALID')
            if value['split'] != self._split:
                raise ValueError('FIXED_SPLIT_CONFLICT')
            self._check_parent()
            output = self._parent/value['output_name']
            # Atomic existence veto; no exist_ok, overwriting, recursive cleanup.
            os.mkdir(output)
            identity = _directory_identity(output)
            result['output_reserved'] = True
            result['output_relative_path'] = output.relative_to(self._root).as_posix()
            claim = self._claims.claim({key: value[key] for key in (
                'schema_version', 'scene_id', 'split', 'owner_id')})
            result['scene_claim'] = claim
            if claim['claim'] is None:
                raise ValueError(claim['issue'])
            # Registry replay is diagnostic idempotence, not permission to create
            # a second output for the same scene under the same owner.
            if claim['replayed']:
                raise ValueError('SCENE_CLAIM_REPLAY_REQUIRES_EXISTING_OUTPUT')
            geometry = inspect_targeted_asset_geometry(self._root, value['geometry_request'])
            result['asset_geometry'] = geometry
            if not geometry['local_bytes_verified']:
                raise ValueError(geometry['issue'])
            self._check_parent()
            if _directory_identity(output) != identity:
                raise ValueError('OUTPUT_RESERVATION_CHANGED')
            if any(output.iterdir()):
                raise ValueError('OUTPUT_RESERVATION_NOT_EMPTY')
            result.update(status='LOCAL_PREPARED_EXECUTION_BLOCKED',
                          issue='EXECUTION_GUARDS_NOT_CONNECTED')
            return result
        except FileExistsError:
            result['issue'] = 'OUTPUT_ALREADY_EXISTS'
        except ValueError as exc:
            # Issues originate from fixed local guard codes, never request text.
            result['issue'] = str(exc) if re.fullmatch('[A-Z_]+', str(exc)) else 'REQUEST_INVALID'
        except Exception:
            result['issue'] = 'LOCAL_PREPARATION_FAILED'
        if identity is not None:
            result['cleanup'] = 'PRESERVED'
            try:
                self._check_parent()
                if _directory_identity(output) == identity:
                    # rmdir refuses any content, including another worker's file.
                    os.rmdir(output)
                    result['cleanup'] = 'OWN_EMPTY_RESERVATION_RELEASED'
                    result['output_reserved'] = False
            except Exception:
                pass
        return result
