from .manifest_resource_profile import active as profile_active,cap as profile_cap,policy as resource_policy,charge as profile_charge,structure as profile_structure,entry as profile_entry,stamp as profile_stamp,receipt as profile_receipt,DESCRIPTOR,require_io_room
"""Opt-in bounded, strict JSON IO for split metadata; no approval semantics."""
import hashlib
import json
import math
import os
from pathlib import Path,PureWindowsPath
import re
import stat
from types import MappingProxyType

INPUT_ROLES={'source','readiness','saved_plan','candidate'}
OUTPUT_ROLES={'plan','candidate'}
MAX_BYTES=256*1024*1024
CHUNK=65536


def _need(value,message):
    if not value:raise ValueError(message)


def _local(path):
    text=str(path);windows=PureWindowsPath(text)
    _need(not text.startswith(('\\\\','//')),'Only local JSON paths supported')
    drive=bool(re.match(r'^[A-Za-z]:[\\/]',text))
    _need(':' not in (text[2:] if drive else text),'Remote, ADS or drive-relative JSON path prohibited')
    _need(not any(c in text for c in '<>"|?*') and not any(ord(c)<32 for c in text),'Invalid JSON path')
    devices={'CON','PRN','AUX','NUL','CONIN$','CONOUT$'}|{p+n for p in ('COM','LPT') for n in '123456789¹²³'}
    _need(all(p in (windows.anchor,'.','..') or p.rstrip(' .')==p and p.split('.')[0].strip(' .').upper() not in devices for p in windows.parts),'Reserved or ambiguous JSON path')
    logical=Path(path);return logical if logical.is_absolute() else Path.cwd()/logical


def _stamp(value):
    _need(stat.S_ISREG(value.st_mode),'JSON input must be regular file')
    return (value.st_size,value.st_mtime_ns,value.st_ctime_ns,value.st_dev,value.st_ino)


def _pairs(pairs):
    out={}
    for key,value in pairs:
        _need(key not in out,'Duplicate JSON key');out[key]=value
    return out


def _constant(value):raise ValueError('Non-finite JSON number')


def _depth(text,maximum):
    depth=0;quoted=False;escaped=False
    for c in text:
        if quoted:
            if escaped:escaped=False
            elif c=='\\':escaped=True
            elif c=='"':quoted=False
        elif c=='"':quoted=True
        elif c in '[{':
            depth+=1;_need(depth<=maximum,'JSON depth exceeds policy')
        elif c in ']}':depth-=1


def _tree(value,maximum,cap):
    visited=0
    # Bound serialization before encoder builds a possibly enormous string fragment.
    active=set();stack=[(value,1 if type(value) in (dict,list) else 0,False)]
    while stack:
        item,depth,leave=stack.pop();kind=type(item)
        visited+=1
        if profile_active() is not None:_need(visited<=DESCRIPTOR['max_nodes'],'MANIFEST_NODE_LIMIT')
        if leave:active.remove(id(item));continue
        if kind in (dict,list):
            _need(depth<=maximum,'JSON object depth exceeds policy')
            _need(id(item) not in active,'Cyclic JSON object');active.add(id(item));stack.append((item,depth,True))
            if kind is dict:
                _need(all(type(k) is str for k in item),'JSON keys must be strings')
                for key,val in item.items():stack.append((val,depth+1,False));stack.append((key,depth+1,False))
            else:
                for val in item:stack.append((val,depth+1,False))
        elif kind is str:
            _need(len(item)<=cap,'JSON string exceeds byte budget')
            for start in range(0,len(item),CHUNK):item[start:start+CHUNK].encode('utf-8')
        elif kind is float:_need(math.isfinite(item),'Non-finite JSON number')
        else:_need(kind in (int,bool,type(None)),'Unsupported JSON value type')


class BoundedJSONIO:
    """Shared operation context; all subsequent reads retain first logical/stat/SHA binding."""
    def __init__(self,policy):
        policy=resource_policy(policy)
        _need(type(policy) is dict and set(policy)=={'input_caps','output_caps','max_depth'},'Exact bounded JSON policy required')
        for key,roles in [('input_caps',INPUT_ROLES),('output_caps',OUTPUT_ROLES)]:
            caps=policy[key];_need(type(caps) is dict and set(caps)==roles and all(type(n) is int and 1<=n<=MAX_BYTES for n in caps.values()),'Exact integer role byte caps required')
        _need(type(policy['max_depth']) is int and 1<=policy['max_depth']<=64,'Exact integer JSON depth 1..64 required')
        self._input_caps=MappingProxyType(dict(policy['input_caps']));self._output_caps=MappingProxyType(dict(policy['output_caps']));self._max_depth=policy['max_depth'];self._records={}

    @property
    def input_caps(self):return self._input_caps

    @property
    def output_caps(self):return self._output_caps

    @property
    def max_depth(self):return self._max_depth

    def read(self,path,role,expected=None):
        _need(role in self.input_caps,'Unknown input role')
        if expected is not None:_need(type(expected) is str and re.fullmatch('[0-9a-f]{64}',expected) is not None,'Explicit lowercase SHA required')
        logical=_local(path);target=logical.resolve();_local(target);before=_stamp(target.stat());cap=self.input_caps[role]
        _need(before[0]<=cap,'JSON input exceeds role byte cap')
        old=self._records.get(logical)
        if old is not None:_need(old['target']==target and old['stamp']==before,'JSON logical target or input state changed')
        require_io_room(cap+1)
        parts=[];count=0
        with target.open('rb',buffering=0) as stream:
            _need(_stamp(os.fstat(stream.fileno()))==before,'JSON descriptor differs from input')
            while count<=cap:
                block=stream.read(min(CHUNK,cap+1-count))
                if not block:break
                profile_charge(len(block));count+=len(block);parts.append(block)
            _need(count<=cap,'JSON input grew beyond byte cap')
            _need(_stamp(os.fstat(stream.fileno()))==before,'JSON input changed during read')
        _need(_stamp(target.stat())==before and logical.resolve()==target,'JSON input target changed after read')
        payload=b''.join(parts);_need(len(payload)==before[0],'JSON input size changed')
        digest=hashlib.sha256(payload).hexdigest()
        if expected is not None:_need(digest==expected,'JSON SHA mismatch or stale input')
        if old is not None:_need(digest==old['sha256'],'JSON input content changed')
        text=payload.decode('utf-8');_need(not text.startswith('\ufeff') and '\x00' not in text,'Only strict UTF8 JSON without BOM/NUL supported');_depth(text,self.max_depth)
        document=json.loads(text,object_pairs_hook=_pairs,parse_constant=_constant);_tree(document,self.max_depth,cap);profile_structure(document,role)
        self._records[logical]={'target':target,'stamp':before,'sha256':digest,'role':role}
        return document,digest

    def verify(self):
        for logical,record in list(self._records.items()):self.read(logical,record['role'],record['sha256'])

    def measure(self,document,role):
        _need(role in self.output_caps,'Unknown output role');cap=self.output_caps[role];_tree(document,self.max_depth,cap);profile_structure(document,role)
        count=0
        for part in self.chunks(document):count+=len(part);_need(count<=cap,'JSON output exceeds role byte cap')
        return count

    @staticmethod
    def chunks(document):
        for text in json.JSONEncoder(ensure_ascii=False,indent=2,allow_nan=False).iterencode(document):
            text=text.replace('\n',os.linesep)
            for i in range(0,len(text),CHUNK):yield text[i:i+CHUNK].encode('utf-8')

    def write(self,path,document,role,expected_size):
        cap=self.output_caps[role];count=0
        with Path(path).open('xb') as stream:
            for part in self.chunks(document):
                _need(count+len(part)<=cap and count+len(part)<=expected_size,'JSON output changed or exceeded budget')
                profile_charge(len(part),'write');written=stream.write(part);_need(written==len(part),'Incomplete JSON output write');count+=written
        _need(count==expected_size,'JSON output changed after measurement')


def bounded_io(policy):
    if policy is None:return None
    return policy if type(policy) is BoundedJSONIO else BoundedJSONIO(policy)
