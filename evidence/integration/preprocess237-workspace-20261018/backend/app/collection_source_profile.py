"""Root-owned strict local profile selection, no writing/admin/automatic promotion."""
from dataclasses import dataclass
from functools import wraps
from pathlib import Path
import hashlib,json
from .ml.manifest_resource_profile import NAME,MARKER,scope,active,cap,charge,require_io_room,structure,resource_boundary,independent_operation
CONFIG_BYTES=4096
SOURCE='first-group-training-esri-v1/annual-window-report.json'
class SourceProfileError(ValueError):pass
@dataclass(frozen=True)
class Selection:
    name:str|None=None
    source_sha256:str|None=None
    config_path:str|None=None
    token:tuple|None=None

def _config(root,path):
    from .collection_budget_status import _read
    root=Path(root).resolve();path=Path(path)
    if not path.is_absolute():path=root/path
    try:relative=path.relative_to(root).as_posix()
    except ValueError:raise SourceProfileError('SOURCE_PROFILE_CONFIG_PATH') from None
    if path.resolve()!=path:raise SourceProfileError('SOURCE_PROFILE_CONFIG_PATH')
    if not path.exists():return None
    identity,pin,raw=_read(root,relative,CONFIG_BYTES,True,json_role='config')
    from .ml.split_json_io import _pairs,_constant,_depth
    text=raw.decode('utf-8');_depth(text,8)
    value=json.loads(text,object_pairs_hook=_pairs,parse_constant=_constant)
    if type(value) is not dict or set(value)!={'schema_version','kind','manifest_profile','source_manifest_sha256'} or type(value['schema_version']) is not int or value['schema_version']!=1 or value['kind']!='ROOT_SELECTED_SOURCE_MANIFEST_PROFILE' or value['manifest_profile']!=MARKER:raise SourceProfileError('SOURCE_PROFILE_CONFIG_INVALID')
    source=value['source_manifest_sha256']
    if type(source) is not str or len(source)!=64 or any(c not in '0123456789abcdef' for c in source):raise SourceProfileError('SOURCE_PROFILE_CONFIG_INVALID')
    return Selection(NAME,source,str(path),(identity,pin))
def selection(root,path=None):
    if path is None:return Selection()
    return _config(root,path) or Selection(config_path=str(Path(path) if Path(path).is_absolute() else Path(root)/path))
def verify_selection(root,selected):
    if selected.config_path is None:return
    current=_config(root,selected.config_path)
    if selected.token is None:
        if current is not None:raise SourceProfileError('SOURCE_PROFILE_CONFIG_CHANGED')
    elif current!=selected:raise SourceProfileError('SOURCE_PROFILE_CONFIG_CHANGED')
def unavailable(kind):
    value={'schema_version':1,'available':False,'status':'UNCONFIRMED','process_verification':'UNKNOWN'}
    if kind=='status':value.update(summary={'learning_ready':False},training_readiness={'ready_for_training':False,'current_manifest_sha256':None},collection_targets={'available':False},candidate_quality={'available':False,'ready_for_training':False},patch_inventory={'available':False})
    return value
def configured(kind):
    def decorate(function):
        @wraps(function)
        def wrapped(root,*args,source_profile_config_path=None,**kwargs):
            try:
                with independent_operation():
                    selected=selection(root,source_profile_config_path)
                    with scope(selected.name):
                        if selected.token is not None:charge(selected.token[0][2])
                        value=function(root,*args,_source_selection=selected,**kwargs)
                        verify_selection(root,selected)
                        return value
            except (ValueError,OSError,TypeError,KeyError,UnicodeError):return unavailable(kind)
        return wrapped
    return decorate
@resource_boundary
def read_source(root,selected):
    from .collection_budget_status import _read
    from .ml.split_json_io import _depth,_pairs,_constant,_tree
    maximum=cap('source',64*1024**2)
    observation=_read(Path(root),SOURCE,maximum,True,**({'json_role':'source'} if active() is not None else {}))
    if selected.source_sha256 is not None and observation[1]!=selected.source_sha256:raise SourceProfileError('SOURCE_PROFILE_PIN_MISMATCH')
    text=observation[2].decode('utf-8')
    if active() is not None:
        _depth(text,32);document=json.loads(text,object_pairs_hook=_pairs,parse_constant=_constant);_tree(document,32,maximum);structure(document,'source')
    else:document=json.loads(text)
    if type(document) is not dict:raise SourceProfileError('SOURCE_PROFILE_SOURCE_INVALID')
    return document,observation[:2]
def verify_source(root,selected,before):
    from .collection_budget_status import _read
    after=_read(Path(root),SOURCE,cap('source',64*1024**2),False,**({'json_role':'source'} if active() is not None else {}))[:2]
    if before!=after or (selected.source_sha256 is not None and after[1]!=selected.source_sha256):raise SourceProfileError('SOURCE_PROFILE_SOURCE_CHANGED')
