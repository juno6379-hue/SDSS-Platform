"""Explicit bounded metadata profile; isolated228 prototype, never remote budget."""
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
import copy,hashlib,json
from types import MappingProxyType,ModuleType
import sys
import threading

NAME='bounded128m-3000-v1'
DESCRIPTOR=MappingProxyType({'name':NAME,'manifest_bytes':128*1024**2,'max_rows':3000,'max_depth':32,'max_nodes':4000000,'max_json_io_bytes':16*1024**3})
DIGEST=hashlib.sha256(json.dumps(dict(DESCRIPTOR),sort_keys=True,separators=(',',':')).encode()).hexdigest()
MARKER=MappingProxyType({'name':NAME,'sha256':DIGEST})
_state_candidate=ModuleType('_geoai_manifest_profile228_state')
_state_candidate.context=ContextVar('manifest_profile228',default=None)
_state_candidate.ResourceError=type('ProfileResourceError',(ValueError,),{})
_STATE=sys.modules.setdefault('_geoai_manifest_profile228_state',_state_candidate)
_CONTEXT=_STATE.context
ProfileResourceError=_STATE.ResourceError
# app.ml and backend.app.ml are both used by existing entry points.
# Share only the operation-local ContextVar, never a globally enabled profile.
class Budget:
    def __init__(self,maximum):
        self._maximum=maximum;self._bytes=0;self._reads=0;self._writes=0;self.lock=threading.RLock()
    @property
    def maximum(self):return self._maximum
    @property
    def bytes(self):return self._bytes
    @property
    def reads(self):return self._reads
    @property
    def writes(self):return self._writes
    def charge(self,size,kind='read'):
        with self.lock:
            if type(size) is not int or size<0 or self._bytes+size>self._maximum:raise ProfileResourceError('MANIFEST_JSON_IO_LIMIT')
            self._bytes+=size
            if kind=='read':self._reads+=size
            else:self._writes+=size

@contextmanager
def io_transaction():
    budget=active()
    if budget is None:yield;return
    with budget.lock:yield

def serialized_io(function):
    @wraps(function)
    def wrapped(*args,**kwargs):
        with io_transaction():return function(*args,**kwargs)
    return wrapped


def active():return _CONTEXT.get()
def validate_name(name):
    if name is not None and (type(name) is not str or name!=NAME):raise ValueError('MANIFEST_PROFILE_INVALID')
    return name
@contextmanager
def scope(name=None):
    validate_name(name);old=active()
    if old is not None or name is None:yield old;return
    budget=Budget(DESCRIPTOR['max_json_io_bytes']);token=_CONTEXT.set(budget)
    try:yield budget
    finally:_CONTEXT.reset(token)
def entry(function):
    @wraps(function)
    def wrapped(*args,manifest_profile=None,**kwargs):
        with scope(manifest_profile):return function(*args,**kwargs)
    return wrapped
def cap(role,maximum):
    if active() is not None and role in ('source','candidate'):
        if type(maximum) is not int or not 1<=maximum<=DESCRIPTOR['manifest_bytes']:raise ProfileResourceError('MANIFEST_POLICY_LIMIT')
        return DESCRIPTOR['manifest_bytes'] if maximum==64*1024**2 else maximum
    return maximum
def policy(value):
    result=copy.deepcopy(value)
    if active() is not None:
        if type(result.get('max_depth')) is not int or not 1<=result['max_depth']<=DESCRIPTOR['max_depth']:raise ProfileResourceError('MANIFEST_DEPTH_LIMIT')
        for key in ('input_caps','output_caps'):
            for role,maximum in result[key].items():result[key][role]=cap(role,maximum)
    return result
def charge(size,kind='read'):
    if active() is not None:active().charge(size,kind)
def structure(document,role):
    if active() is None:return
    if role in ('source','candidate') and type(document) is dict and 'scenes' in document:
        rows=document['scenes'];history=document.get('historical_noneligible_patches',[])
        if type(rows) is not list or type(history) is not list or len(rows)+len(history)>DESCRIPTOR['max_rows']:raise ProfileResourceError('MANIFEST_ROW_LIMIT')
def stamp(receipt,version=True):
    if active() is None:return receipt
    result=dict(receipt);result['manifest_profile']=dict(MARKER)
    if version:result['schema_version']=2
    return result
def receipt(value):
    if type(value) is not dict:raise ValueError('MANIFEST_PROFILE_RECEIPT_INVALID')
    if active() is None:
        if 'manifest_profile' in value or value.get('schema_version')!=1:raise ValueError('MANIFEST_PROFILE_NOT_SELECTED')
        return value
    if type(value.get('schema_version')) is not int or value['schema_version']!=2 or value.get('manifest_profile')!=MARKER:raise ValueError('MANIFEST_PROFILE_MISMATCH')
    result=dict(value);result.pop('manifest_profile');result['schema_version']=1
    return result
def read_json(path,role,maximum=None):
    from .split_json_io import BoundedJSONIO
    base={'input_caps':{'source':64*1024**2,'readiness':16*1024**2,'saved_plan':4*1024**2,'candidate':64*1024**2},'output_caps':{'plan':4*1024**2,'candidate':64*1024**2},'max_depth':32}
    if maximum is not None:base['input_caps'][role]=maximum
    return BoundedJSONIO(base).read(path,role)[0]

def require_io_room(maximum):
    if active() is not None and active().bytes+maximum>active().maximum:raise ProfileResourceError('MANIFEST_JSON_IO_LIMIT')

_RESOURCE_MESSAGES={**{key:'MANIFEST_JSON_CHANGED' for key in ('JSON logical target or input state changed','JSON descriptor differs from input','JSON input changed during read','JSON input target changed after read','JSON input size changed','JSON input content changed')},'JSON input exceeds role byte cap':'MANIFEST_JSON_FILE_LIMIT','JSON input grew beyond byte cap':'MANIFEST_JSON_FILE_LIMIT','JSON depth exceeds policy':'MANIFEST_DEPTH_LIMIT','JSON object depth exceeds policy':'MANIFEST_DEPTH_LIMIT','JSON string exceeds byte budget':'MANIFEST_JSON_FILE_LIMIT','JSON output exceeds role byte cap':'MANIFEST_JSON_FILE_LIMIT','JSON output changed or exceeded budget':'MANIFEST_JSON_FILE_LIMIT','MANIFEST_NODE_LIMIT':'MANIFEST_NODE_LIMIT'}
def resource_boundary(function):
    @wraps(function)
    def wrapped(*args,**kwargs):
        try:
            with io_transaction():return function(*args,**kwargs)
        except ProfileResourceError:raise
        except ValueError as exc:
            code=_RESOURCE_MESSAGES.get(str(exc))
            if active() is not None and code:raise ProfileResourceError(code) from None
            raise
    return wrapped
JSON_ROLE_CAPS=MappingProxyType({'source':128*1024**2,'candidate':128*1024**2,'evidence':2*1024**2,'readiness':16*1024**2,'saved_plan':4*1024**2,'receipt':65536,'policy':1024**2,'boundary':2*1024**2,'local_config':2*1024**2,'local_plan':2*1024**2,'proposal':2*1024**2,'status_report':16*1024**2,'pointer':65536})
def _effective_metadata_cap(role,maximum_bytes):
    if role not in JSON_ROLE_CAPS:raise ValueError('MANIFEST_JSON_ROLE_INVALID')
    maximum=JSON_ROLE_CAPS[role]
    if maximum_bytes is not None:
        if type(maximum_bytes) is not int or not 0<maximum_bytes<=maximum:
            raise ProfileResourceError('MANIFEST_JSON_NARROW_CAP_INVALID')
        maximum=maximum_bytes
    return maximum

@serialized_io
def bounded_json_digest(path,role,*,_capture=False,maximum_bytes=None):
    # Role is explicit; filenames/extensions never choose whether to charge.
    import os,stat
    from pathlib import Path
    from .split_json_io import _local,_stamp
    if role not in JSON_ROLE_CAPS:raise ValueError('MANIFEST_JSON_ROLE_INVALID')
    maximum=_effective_metadata_cap(role,maximum_bytes)
    path=_local(path)
    if path.resolve()!=path or path.is_symlink():raise ValueError('MANIFEST_JSON_PATH_INVALID')
    before=_stamp(path.stat())
    if getattr(path.lstat(),'st_file_attributes',0)&0x400:raise ValueError('MANIFEST_JSON_PATH_INVALID')
    if before[0]>maximum:raise ProfileResourceError('MANIFEST_JSON_FILE_LIMIT')
    require_io_room(before[0]);h=hashlib.sha256();count=0;parts=[]
    with path.open('rb',buffering=0) as stream:
        if _stamp(os.fstat(stream.fileno()))!=before:raise ProfileResourceError('MANIFEST_JSON_CHANGED')
        while count<before[0]:
            amount=min(65536,before[0]-count);require_io_room(amount)
            block=stream.read(amount);charge(len(block));count+=len(block)
            if not block:raise ProfileResourceError('MANIFEST_JSON_CHANGED')
            h.update(block)
            if _capture:parts.append(block)
        if _stamp(os.fstat(stream.fileno()))!=before:raise ProfileResourceError('MANIFEST_JSON_CHANGED')
    if _stamp(path.stat())!=before or path.resolve()!=path or count!=before[0]:raise ProfileResourceError('MANIFEST_JSON_CHANGED')
    return (h.hexdigest(),b''.join(parts)) if _capture else h.hexdigest()

@resource_boundary
def pinned_source_bytes(path,expected):
    from .split_json_io import _depth,_tree,_pairs,_constant
    digest,raw=bounded_json_digest(path,'source',_capture=True)
    if digest!=expected:raise ProfileResourceError('MANIFEST_JSON_PIN_MISMATCH')
    text=raw.decode('utf-8')
    if text.startswith('\ufeff') or '\x00' in text:raise ValueError('MANIFEST_JSON_ENCODING')
    _depth(text,32);document=json.loads(text,object_pairs_hook=_pairs,parse_constant=_constant)
    _tree(document,32,DESCRIPTOR['manifest_bytes']);structure(document,'source')
    return raw

@contextmanager
def independent_operation():
    token=_CONTEXT.set(None)
    try:yield
    finally:_CONTEXT.reset(token)

@serialized_io
def write_measured(stream,block):
    """Known synchronous unbuffered JSON output; actual partial bytes or explicit unknown."""
    import os
    if active() is None:return stream.write(block)
    require_io_room(len(block));before=os.fstat(stream.fileno()).st_size
    try:written=stream.write(block)
    except OSError:
        try:
            actual=os.fstat(stream.fileno()).st_size-before
            if not 0<=actual<=len(block):raise ValueError('unknown')
        except Exception:
            charge(len(block),'write')
            raise ProfileResourceError('MANIFEST_JSON_WRITE_MEASUREMENT_UNKNOWN') from None
        charge(actual,'write');raise
    if type(written) is int and written>0:charge(written,'write')
    if written!=len(block):raise ProfileResourceError('MANIFEST_JSON_INCOMPLETE_WRITE')
    return written

@serialized_io
def write_new_json_bytes(path,payload,role):
    """Explicit JSON-role new snapshot/output, no filename-based selection."""
    if role not in JSON_ROLE_CAPS or type(payload) is not bytes:raise ValueError('MANIFEST_JSON_ROLE_INVALID')
    if len(payload)>JSON_ROLE_CAPS[role]:raise ProfileResourceError('MANIFEST_JSON_FILE_LIMIT')
    require_io_room(len(payload))
    with path.open('xb',buffering=0) as stream:
        for start in range(0,len(payload),65536):write_measured(stream,payload[start:start+65536])

def metadata_identity(path,role):
    """Stat-only exact logical identity for a role-bound cache; no size-based selection."""
    from .split_json_io import _local,_stamp
    if role not in JSON_ROLE_CAPS:raise ProfileResourceError('MANIFEST_JSON_ROLE_REQUIRED')
    logical=_local(path)
    if logical.resolve()!=logical or logical.is_symlink() or getattr(logical.lstat(),'st_file_attributes',0)&0x400:raise ProfileResourceError('MANIFEST_JSON_PATH_CHANGED')
    identity=_stamp(logical.stat())
    if identity[0]>JSON_ROLE_CAPS[role]:raise ProfileResourceError('MANIFEST_JSON_FILE_LIMIT')
    return logical,identity

@resource_boundary
def read_metadata(path,role,expected=None,*,maximum_bytes=None):
    """One bounded physical JSON read; preserve caller's semantic role and pin."""
    from .split_json_io import _depth,_tree,_pairs,_constant
    if role not in JSON_ROLE_CAPS:raise ProfileResourceError('MANIFEST_JSON_ROLE_REQUIRED')
    maximum=_effective_metadata_cap(role,maximum_bytes)
    digest,raw=bounded_json_digest(path,role,_capture=True,maximum_bytes=maximum)
    if expected is not None and digest!=expected:raise ProfileResourceError('MANIFEST_JSON_PIN_MISMATCH')
    text=raw.decode('utf-8')
    if text.startswith('\ufeff') or '\x00' in text:raise ValueError('MANIFEST_JSON_ENCODING')
    _depth(text,DESCRIPTOR['max_depth'])
    document=json.loads(text,object_pairs_hook=_pairs,parse_constant=_constant)
    _tree(document,DESCRIPTOR['max_depth'],maximum);structure(document,role)
    return document,digest,raw
