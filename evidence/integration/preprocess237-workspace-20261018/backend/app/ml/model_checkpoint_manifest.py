"""Bind a local model reference to a manifest decoded from its checkpoint bytes.

Internal read only. weights_only + archive limits do NOT promise CPU/RSS/time
sandboxing or safety against every malicious tensor metadata denial of service.
"""
import hashlib
import io
import json
import math
import re
import zipfile

from ..model_reference_contract import model_reference_issue
from ..model_registration_provenance import inspect_model_registration_provenance
from .per_scene_normalization_files import _root, _relative, _snapshot, _evidence_json, _Blocked

MAX_CHECKPOINT = 8 * 1024**2
MAX_REPORT = 2 * 1024**2
MAX_MEMBERS = 512
MAX_UNCOMPRESSED = 32 * 1024**2
MAX_MEMBER = 8 * 1024**2
MAX_PICKLE = 2 * 1024**2
MAX_MANIFEST = 2 * 1024**2


class _Invalid(Exception):
    def __init__(self, code, field):self.code,self.field=code,field


def _need(value, code, field):
    if not value:raise _Invalid(code,field)


def _keys(value, fields):
    return type(value) is dict and len(value)==len(fields) and all(type(k) is str for k in value) and set(value)==set(fields)


def _sha(value):
    return type(value) is str and re.fullmatch('[0-9a-f]{64}',value) is not None


def _archive(raw):
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            entries=archive.infolist()
            _need(1<=len(entries)<=MAX_MEMBERS,'CHECKPOINT_ARCHIVE_INVALID','checkpoint')
            seen=set();prefix=None;total=0;pickle_found=False
            for entry in entries:
                name=entry.filename;parts=name.split('/')
                _need(name==entry.orig_filename and '\\' not in name and ':' not in name
                      and not entry.is_dir() and len(parts)>=2 and all(p and p not in ('.','..') for p in parts)
                      and name not in seen and not (entry.flag_bits & 1)
                      and entry.compress_type==zipfile.ZIP_STORED
                      and 0<=entry.file_size<=MAX_MEMBER and entry.file_size==entry.compress_size,
                      'CHECKPOINT_ARCHIVE_INVALID','checkpoint')
                if prefix is None:prefix=parts[0]
                _need(parts[0]==prefix,'CHECKPOINT_ARCHIVE_INVALID','checkpoint')
                seen.add(name);total+=entry.file_size
                _need(total<=MAX_UNCOMPRESSED,'CHECKPOINT_ARCHIVE_INVALID','checkpoint')
                if parts[1:]==['data.pkl']:
                    _need(entry.file_size<=MAX_PICKLE,'CHECKPOINT_ARCHIVE_INVALID','checkpoint')
                    pickle_found=True
            _need(pickle_found,'CHECKPOINT_ARCHIVE_INVALID','checkpoint')
    except _Invalid:raise
    except Exception:raise _Invalid('CHECKPOINT_ARCHIVE_INVALID','checkpoint') from None


def _manifest(value):
    """Strict detached JSON tree; never serialize tensor/custom objects."""
    count=0;budget=0;active=set()
    def spend(size):
        nonlocal budget
        budget+=size
        _need(budget<=MAX_MANIFEST,'MANIFEST_INVALID','checkpoint_manifest')
    def copy(item,depth):
        nonlocal count
        count+=1
        _need(depth<=16 and count<=65536,'MANIFEST_INVALID','checkpoint_manifest')
        kind=type(item)
        if kind in (dict,list):
            _need(id(item) not in active,'MANIFEST_INVALID','checkpoint_manifest')
            active.add(id(item))
            try:
                if kind is dict:
                    _need(len(item)<=128 and all(type(k) is str and 1<=len(k)<=128
                          and all(not 0xD800<=ord(c)<=0xDFFF and ord(c)>=32 and not 127<=ord(c)<=159 for c in k)
                          for k in item),'MANIFEST_INVALID','checkpoint_manifest')
                    spend(2+2*len(item))
                    for key in item:spend(len(json.dumps(key,ensure_ascii=False).encode('utf-8')))
                    return {k:copy(v,depth+1) for k,v in item.items()}
                _need(len(item)<=65536-count,'MANIFEST_INVALID','checkpoint_manifest')
                spend(2+len(item))
                return [copy(v,depth+1) for v in item]
            finally:active.remove(id(item))
        if kind is str:
            _need(len(item)<=4096 and all(not 0xD800<=ord(c)<=0xDFFF for c in item),'MANIFEST_INVALID','checkpoint_manifest')
        elif kind is int:
            _need(item.bit_length()<=53,'MANIFEST_INVALID','checkpoint_manifest')
        elif kind is float:
            _need(math.isfinite(item),'MANIFEST_INVALID','checkpoint_manifest')
        else:_need(item is None or kind is bool,'MANIFEST_INVALID','checkpoint_manifest')
        spend(len(json.dumps(item,ensure_ascii=False,allow_nan=False).encode('utf-8')))
        return item
    _need(type(value) is dict,'MANIFEST_INVALID','checkpoint_manifest')
    result=copy(value,0)
    raw=json.dumps(result,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode('utf-8')
    _need(len(raw)<=MAX_MANIFEST,'MANIFEST_INVALID','checkpoint_manifest')
    return result


def read_pinned_model_checkpoint_manifest(store, model_ref, training_report_sha256):
    """Return actual checkpoint manifest, not a report's copied input signature.

    No load_state_dict, tensor compatibility checking, inference, training,
    Registry dataset lookup, authority verification or execution is performed.
    """
    result={'schema_version':1,'scope':'PINNED_MODEL_CHECKPOINT_MANIFEST_READ_ONLY','status':'BLOCKED','issue':None,
        'registration_observation':None,'model_ref':None,'training_report_sha256':None,'checkpoint_manifest':None,
        'checkpoint_artifact_verified':False,'training_report_artifact_verified':False,
        'state_dict_verified':False,'source_authority_verified':False,'scientific_accuracy_validated':False,
        'execution_authorized':False,'workflow_supported':False}
    try:
        _need(_keys(model_ref,('id','version','sha256')) and model_reference_issue(model_ref) is None
              and re.fullmatch('[A-Za-z0-9_-]{1,100}',model_ref['id']) is not None
              and _sha(model_ref['sha256']) and _sha(training_report_sha256),'INVALID_INPUT','model_ref')
        result['model_ref']=dict(model_ref);result['training_report_sha256']=training_report_sha256
        try:record=store.get('models',model_ref['id'])
        except KeyError:raise _Invalid('MODEL_NOT_FOUND','model_ref') from None
        _need(type(record) is dict and len(record)<=256 and all(type(k) is str for k in record)
              and record.get('id')==model_ref['id'],'MODEL_RECORD_INVALID','model_record')
        observation=inspect_model_registration_provenance(record);result['registration_observation']=observation
        _need(observation['status']=='CONSISTENT_UNVERIFIED','REGISTRATION_NOT_BOUND','model_record')
        _need(record['model_version_declaration']['version']==model_ref['version']
              and record['checkpoint_sha256']==model_ref['sha256']
              and record['training_report_sha256']==training_report_sha256,'PIN_CONFLICT','model_ref')
        root=_root(store.root)
        expected=f"models/{model_ref['id']}/best.pt"
        _need(type(record.get('checkpoint_path')) is str and record['checkpoint_path'].replace('\\','/')==expected,
              'CHECKPOINT_PATH_INVALID','checkpoint')
        checkpoint=_relative(root,expected,'checkpoint')
        report_path=_relative(root,f"models/{model_ref['id']}/report.json",'training_report')
        checkpoint_sha,raw=_snapshot(root,checkpoint,MAX_CHECKPOINT,'checkpoint',True)
        _need(checkpoint_sha==model_ref['sha256'],'SHA256_MISMATCH','checkpoint')
        result['checkpoint_artifact_verified']=True
        report_sha,report_raw=_snapshot(root,report_path,MAX_REPORT,'training_report',True)
        _need(report_sha==training_report_sha256,'SHA256_MISMATCH','training_report')
        result['training_report_artifact_verified']=True
        try:report=_evidence_json(report_raw)
        except _Blocked:raise _Invalid('TRAINING_REPORT_INVALID','training_report') from None
        _need(report.get('model_id')==model_ref['id'] and report.get('checkpoint_sha256')==model_ref['sha256']
              and report.get('training_state')=='completed','TRAINING_REPORT_INVALID','training_report')
        if 'model_version' in report:
            _need(type(report['model_version']) is str and report['model_version']==model_ref['version'],
                  'TRAINING_REPORT_INVALID','training_report')
        _archive(raw)
        try:
            import torch
            # Inherit installed Torch/caller ambient allowlists without adding,
            # clearing or replacing them. This is not a clean-process sandbox.
            saved=torch.load(io.BytesIO(raw),map_location='cpu',weights_only=True)
        except _Invalid:raise
        except Exception:raise _Invalid('CHECKPOINT_LOAD_UNAVAILABLE','checkpoint') from None
        _need(type(saved) is dict and len(saved)<=128 and all(type(k) is str for k in saved)
              and saved.get('architecture')=='tiny_unet','CHECKPOINT_FORMAT_INVALID','checkpoint')
        result['checkpoint_manifest']=_manifest(saved.get('manifest'))
        result['status']='MANIFEST_BOUND_UNVERIFIED'
    except (_Invalid,_Blocked) as error:
        result['issue']={'code':error.code,'field':error.field}
    except Exception:
        result['issue']={'code':'READ_UNAVAILABLE','field':'inputs'}
    return result
