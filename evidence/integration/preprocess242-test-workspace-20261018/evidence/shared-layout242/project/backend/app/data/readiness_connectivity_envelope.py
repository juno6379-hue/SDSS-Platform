"""Bounded canonical-byte envelopes for prospective connectivity witnesses.

Pure in-memory protocol: SHA declarations do not authenticate files, eligibility,
executing code, or historical readiness. External pins remain caller trust inputs.
"""
import copy
import hashlib
import json
import math
import re
from .readiness_connectivity_witness import diagnose_readiness_connectivity, CAPS as WITNESS_CAPS

MAX_BYTES=16*1024*1024
MAX_DEPTH=32
MAX_STRING=4096
MAX_NUMBER_CHARS=64
MAX_NODES=300000
PROVENANCE_KEYS={'source_report_sha256','source_manifest_sha256','eligible_scene_reference_sha256'}
SCENE_KEYS={'scene_index','province','source_group','scene_id','bounds_wgs84'}
LIMIT_KEYS={'max_scenes','max_bbox_pairs','max_witness_edges'}
DEFAULT_LIMITS={'max_scenes':2000,'max_bbox_pairs':1000000,'max_witness_edges':10000}
CONSTANTS={'schema_version':1,'kind':'READINESS_CONNECTIVITY_WITNESS_ENVELOPE','status':'BLOCKED',
  'canonical_protocol':'PYTHON_JSON_UTF8_SORT_KEYS_COMPACT_V1',
  'provenance_claim':'CALLER_ASSERTED_HASHES_NOT_FILE_VERIFIED','helper_binding_claim':'CALLER_DECLARED_PIN_NOT_EXECUTING_CODE_VERIFIED',
  'provenance_verified':False,'executing_helper_code_verified':False,'eligibility_verified':False,
  'historical_readiness_cause_reconstructed':False,'ready_for_training':False,'scientific_accuracy_validated':False,
  'training_executed':False,'training_split_leakage_resolved':False,'settlement_authorized':False,
  'execution_authorized':False,'automatic_resume_allowed':False,'proposed_refund_bytes':0,
  'source_files_read':0,'source_files_written':0,'network_requests':0,'exactly_once_applied':'UNKNOWN'}
BODY_KEYS=set(CONSTANTS)|{'helper_sha256','provenance','provenance_sha256','input','input_sha256','witness','witness_sha256'}
ALL_KEYS=BODY_KEYS|{'envelope_sha256'}


def _sha(value):return type(value) is str and len(value)==64 and re.fullmatch('[0-9a-f]{64}',value) is not None


def _guard(value):
    """Exact serialized-size prewalk before dumps; bounded traversal rejects cycles."""
    nodes=0
    def walk(item,depth):
        nonlocal nodes
        nodes+=1
        if nodes>MAX_NODES or depth>MAX_DEPTH:raise ValueError('Envelope node/depth budget exceeded')
        kind=type(item)
        if item is None:size=4
        elif kind is bool:size=4 if item else 5
        elif kind is str:
            if len(item)>MAX_STRING:raise ValueError('Envelope string limit exceeded')
            try:size=len(json.dumps(item,ensure_ascii=False).encode('utf-8'))
            except UnicodeError as exc:raise ValueError('Invalid Unicode string') from exc
        elif kind in (int,float):
            if kind is float and not math.isfinite(item):raise ValueError('Non-finite number')
            try:token=str(item) if kind is int else json.dumps(item,allow_nan=False)
            except (ValueError,OverflowError) as exc:raise ValueError('Unsupported number') from exc
            if len(token)>MAX_NUMBER_CHARS:raise ValueError('Numeric lexeme too long')
            size=len(token)
        elif kind is list:
            size=2+max(0,len(item)-1)
            for child in item:
                size+=walk(child,depth+1)
                if size>MAX_BYTES:raise ValueError('Envelope byte budget exceeded')
        elif kind is dict:
            size=2+max(0,len(item)-1)
            for key,child in item.items():
                if type(key) is not str:raise ValueError('JSON object keys require strings')
                size+=walk(key,depth+1)+1+walk(child,depth+1)
                if size>MAX_BYTES:raise ValueError('Envelope byte budget exceeded')
        else:raise ValueError('Only exact JSON types are supported')
        if size>MAX_BYTES:raise ValueError('Envelope byte budget exceeded')
        return size
    return walk(value,1)


def _canonical(value):
    _guard(value)
    raw=json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
    if len(raw)>MAX_BYTES:raise ValueError('Envelope byte budget exceeded')
    return raw


def _digest(value):return hashlib.sha256(_canonical(value)).hexdigest()


def _provenance(value):
    if type(value) is not dict or len(value)!=len(PROVENANCE_KEYS) or set(value)!=PROVENANCE_KEYS or any(v is not None and not _sha(v) for v in value.values()):raise ValueError('Exact caller provenance SHA/null fields required')
    return dict(value)


def _input(scenes,policy,limits):
    if type(limits) is not dict or len(limits)!=len(LIMIT_KEYS) or set(limits)!=LIMIT_KEYS:raise ValueError('Exact three helper limits required')
    for key,value in limits.items():
        minimum=0 if key=='max_witness_edges' else 1
        if type(value) is not int or not minimum<=value<=WITNESS_CAPS[key]:raise ValueError('Invalid typed helper limit: '+key)
    if scenes is not None:
        if type(scenes) is not list or len(scenes)>limits['max_scenes']:raise ValueError('Scene list within declared limit or None required')
        if len(scenes)*(len(scenes)-1)//2>limits['max_bbox_pairs']:raise ValueError('Full pair plan exceeds declared limit')
        if any(type(row) is not dict or len(row)!=len(SCENE_KEYS) or set(row)!=SCENE_KEYS for row in scenes):raise ValueError('Exact scene metadata keys required')
    value={'eligible_scenes':scenes,'province_splits':policy,'limits':limits}
    _guard(value)
    return copy.deepcopy(value)


def build_readiness_connectivity_envelope(eligible_scenes,province_splits=None,*,provenance,helper_sha256,expected_helper_sha256,limits=None):
    if not _sha(helper_sha256) or not _sha(expected_helper_sha256) or helper_sha256!=expected_helper_sha256:raise ValueError('Declared helper SHA must match explicit external helper pin')
    lineage=_provenance(provenance)
    supplied=_input(eligible_scenes,province_splits,dict(DEFAULT_LIMITS) if limits is None else limits)
    input_sha=_digest(supplied)  # Reject byte limits before helper computation.
    witness=diagnose_readiness_connectivity(supplied['eligible_scenes'],supplied['province_splits'],**supplied['limits'])
    body={**CONSTANTS,'helper_sha256':helper_sha256,'provenance':lineage,'provenance_sha256':_digest(lineage),
      'input':supplied,'input_sha256':input_sha,'witness':witness,'witness_sha256':_digest(witness)}
    envelope={**body,'envelope_sha256':_digest(body)}
    _guard(envelope)
    return envelope


def validate_readiness_connectivity_envelope(envelope,*,expected_helper_sha256,expected_provenance,expected_input_sha256):
    _guard(envelope)  # No serialization or helper work until bounded JSON-tree check.
    if type(envelope) is not dict or set(envelope)!=ALL_KEYS:raise ValueError('Unsupported envelope schema/unknown or missing keys')
    lineage=_provenance(expected_provenance)
    if not _sha(expected_helper_sha256) or not _sha(expected_input_sha256):raise ValueError('External helper and input SHA pins required')
    for key,value in CONSTANTS.items():
        if _canonical(envelope[key])!=_canonical(value):raise ValueError('Envelope contract mismatch: '+key)
    if envelope['helper_sha256']!=expected_helper_sha256 or not _sha(envelope['helper_sha256']):raise ValueError('Helper pin mismatch')
    if _canonical(_provenance(envelope['provenance']))!=_canonical(lineage):raise ValueError('External provenance pin mismatch')
    if envelope['provenance_sha256']!=_digest(lineage):raise ValueError('Provenance digest mismatch')
    supplied=envelope['input']
    if type(supplied) is not dict or set(supplied)!={'eligible_scenes','province_splits','limits'}:raise ValueError('Unknown or missing input keys')
    supplied=_input(supplied['eligible_scenes'],supplied['province_splits'],supplied['limits'])
    if envelope['input_sha256']!=expected_input_sha256 or _digest(supplied)!=expected_input_sha256:raise ValueError('External eligible-input digest mismatch')
    if envelope['witness_sha256']!=_digest(envelope['witness']):raise ValueError('Witness digest mismatch')
    body={key:envelope[key] for key in BODY_KEYS}
    if envelope['envelope_sha256']!=_digest(body):raise ValueError('Envelope digest mismatch')
    expected=diagnose_readiness_connectivity(supplied['eligible_scenes'],supplied['province_splits'],**supplied['limits'])
    if _canonical(envelope['witness'])!=_canonical(expected):raise ValueError('Witness differs from exact typed helper recomputation')
    return copy.deepcopy(envelope)


def encode_readiness_connectivity_envelope(envelope,**external_pins):
    return _canonical(validate_readiness_connectivity_envelope(envelope,**external_pins))


def _preparse(raw):
    if type(raw) is not bytes or len(raw)>MAX_BYTES:raise ValueError('Bounded exact bytes required')
    try:text=raw.decode('utf-8')
    except UnicodeError as exc:raise ValueError('Strict UTF-8 required') from exc
    if text.startswith('\ufeff') or '\x00' in text:raise ValueError('BOM/NUL or unsupported encoding')
    depth=0;quoted=False;escaped=False;string_chars=0;tokens=0;index=0
    while index<len(text):
        char=text[index]
        if quoted:
            if escaped:escaped=False
            elif char=='\\':escaped=True
            elif char=='"':quoted=False
            if quoted:
                string_chars+=1
                if string_chars>MAX_STRING*6:raise ValueError('Encoded string limit exceeded')
        elif char=='"':quoted=True;string_chars=0;tokens+=1
        elif char in '[{':
            depth+=1;tokens+=1
            if depth>MAX_DEPTH:raise ValueError('JSON depth limit exceeded')
        elif char in ']}':
            depth-=1
            if depth<0:raise ValueError('JSON depth invalid')
        elif char in ',:':tokens+=1
        elif char=='-' or char.isdigit():
            end=index+1
            while end<len(text) and text[end] in '0123456789.eE+-':end+=1
            if end-index>MAX_NUMBER_CHARS:raise ValueError('Numeric lexeme limit exceeded')
            tokens+=1;index=end-1
        if tokens>MAX_NODES:raise ValueError('JSON token budget exceeded')
        index+=1
    if depth or quoted:raise ValueError('JSON structure incomplete')
    return text


def _pairs(items):
    result={}
    for key,value in items:
        if key in result:raise ValueError('Duplicate JSON key')
        result[key]=value
    return result


def _constant(unused):raise ValueError('Non-finite JSON number')


def decode_readiness_connectivity_envelope(raw,**external_pins):
    text=_preparse(raw)
    try:value=json.loads(text,object_pairs_hook=_pairs,parse_constant=_constant)
    except (ValueError,RecursionError,OverflowError) as exc:raise ValueError('Invalid strict JSON envelope') from exc
    if _canonical(value)!=raw:raise ValueError('Noncanonical envelope bytes')
    return validate_readiness_connectivity_envelope(value,**external_pins)
