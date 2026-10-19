"""Explicit bounded metadata profile; isolated228 prototype, never remote budget."""
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
import copy,hashlib,json
from types import MappingProxyType,ModuleType
import sys

NAME='bounded128m-3000-v1'
DESCRIPTOR=MappingProxyType({'name':NAME,'manifest_bytes':128*1024**2,'max_rows':3000,'max_depth':32,'max_nodes':4000000,'max_json_io_bytes':16*1024**3})
DIGEST=hashlib.sha256(json.dumps(dict(DESCRIPTOR),sort_keys=True,separators=(',',':')).encode()).hexdigest()
MARKER=MappingProxyType({'name':NAME,'sha256':DIGEST})
_state_candidate=ModuleType('_geoai_manifest_profile228_state')
_state_candidate.context=ContextVar('manifest_profile228',default=None)
_CONTEXT=sys.modules.setdefault('_geoai_manifest_profile228_state',_state_candidate).context
# app.ml and backend.app.ml are both used by existing entry points.
# Share only the operation-local ContextVar, never a globally enabled profile.
class Budget:
    def __init__(self,maximum):self.maximum=maximum;self.bytes=0;self.reads=0;self.writes=0
    def charge(self,size,kind='read'):
        if type(size) is not int or size<0 or self.bytes+size>self.maximum:raise ValueError('MANIFEST_JSON_IO_LIMIT')
        self.bytes+=size
        if kind=='read':self.reads+=size
        else:self.writes+=size

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
    return DESCRIPTOR['manifest_bytes'] if active() is not None and role in ('source','candidate') and maximum==64*1024**2 else maximum
def policy(value):
    result=copy.deepcopy(value)
    if active() is not None:
        for key in ('input_caps','output_caps'):
            for role,maximum in result[key].items():result[key][role]=cap(role,maximum)
    return result
def charge(size,kind='read'):
    if active() is not None:active().charge(size,kind)
def structure(document,role):
    if active() is None:return
    if role in ('source','candidate') and type(document) is dict and 'scenes' in document:
        rows=document['scenes'];history=document.get('historical_noneligible_patches',[])
        if type(rows) is not list or type(history) is not list or len(rows)+len(history)>DESCRIPTOR['max_rows']:raise ValueError('MANIFEST_ROW_LIMIT')
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
    if active() is not None and active().bytes+maximum>active().maximum:raise ValueError('MANIFEST_JSON_IO_LIMIT')
