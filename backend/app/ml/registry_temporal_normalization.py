"""Same-get image Registry temporal binding around the unchanged127 batch."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
import re

from ..dataset_registry import canonical_manifest, version_key
from .model_checkpoint_manifest import _manifest
from .pinned_annual_normalization import _request, inspect_pinned_annual_normalization

_TIME = re.compile(r'([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})(?:\.([0-9]{1,9}))?(Z|[+-][0-9]{2}:[0-9]{2})')
_EPOCH = datetime(1970,1,1,tzinfo=timezone.utc)


class _TemporalBlocked(Exception):
    def __init__(self,code,field):self.code,self.field=code,field


def _need(value,code,field):
    if not value:raise _TemporalBlocked(code,field)


def _stamp(value,field):
    _need(type(value) is str and len(value)<=64,'TEMPORAL_FIELD_INVALID',field)
    match=_TIME.fullmatch(value)
    _need(match is not None,'TEMPORAL_FIELD_INVALID',field)
    y,m,d,h,minute,second,fraction,zone=match.groups()
    _need(zone!='-00:00','TEMPORAL_OFFSET_UNKNOWN',field)
    try:
        if zone=='Z':offset=timezone.utc
        else:
            zh,zm=int(zone[1:3]),int(zone[4:6])
            _need(zh<=23 and zm<=59,'TEMPORAL_FIELD_INVALID',field)
            offset=timezone(timedelta(minutes=(1 if zone[0]=='+' else -1)*(zh*60+zm)))
        stamp=datetime(int(y),int(m),int(d),int(h),int(minute),int(second),tzinfo=offset).astimezone(timezone.utc)
        delta=stamp-_EPOCH
        return (delta.days*86400+delta.seconds)*10**9+int((fraction or '').ljust(9,'0'))
    except _TemporalBlocked:raise
    except (ValueError,OverflowError):raise _TemporalBlocked('TEMPORAL_FIELD_INVALID',field) from None


def _window(temporal,year):
    _need(type(temporal) is dict,'TEMPORAL_FIELD_INVALID','temporal')
    calendar=temporal.get('calendar')
    _need(type(calendar) is str and bool(calendar),'TEMPORAL_FIELD_INVALID','calendar')
    _need(calendar=='gregorian','TEMPORAL_CALENDAR_UNSUPPORTED','calendar')
    start,end=_stamp(temporal.get('start'),'start'),_stamp(temporal.get('end'),'end')
    _need(start<=end,'TEMPORAL_WINDOW_REVERSED','window')
    lower=_stamp(f'{year:04d}-01-01T00:00:00Z','start')
    upper=_stamp(f'{year+1:04d}-01-01T00:00:00Z','end')
    _need(lower<=start<=end<upper,'TEMPORAL_YEAR_MISMATCH','window')


class _TemporalStore:
    """Only get/root; actual125 image reads are first in each three-get row.

    Track row role position, not just a key lookup, so a later row image key
    reused as an earlier metadata key cannot create a false future observation.
    """
    def __init__(self,store,rows):
        self.store,self.rows,self.dataset_calls=store,rows,0
        self.observations=[];self.first_issue=None

    @property
    def root(self):return self.store.root

    def get(self,kind,identifier):
        record=self.store.get(kind,identifier)
        if kind!='dataset_versions':return record
        position=self.dataset_calls;self.dataset_calls+=1
        if position%3:return record
        row=self.rows[position//3];ref=row['image_ref'];digest=None
        try:
            key=version_key(ref['id'],ref['version'])
            _need(identifier==key and type(record) is dict and len(record)<=128 and all(type(k) is str for k in record)
                  and type(record.get('id')) is str and record['id']==key
                  and type(record.get('manifest_sha256')) is str,'REGISTRY_RECORD_INVALID','image')
            try:manifest=_manifest(record.get('manifest'))
            except Exception:raise _TemporalBlocked('REGISTRY_RECORD_INVALID','image') from None
            digest=hashlib.sha256(json.dumps(manifest,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode()).hexdigest()
            _need(record.get('manifest_sha256')==digest and manifest.get('dataset_id')==ref['id']
                  and manifest.get('version')==ref['version'] and manifest.get('sha256')==ref['sha256'],
                  'REGISTRY_REFERENCE_CONFLICT','image')
            # Classify temporal errors precisely before upstream canonical's
            # more general datetime/order exception, without bypassing schema.
            _window(manifest.get('temporal'),row['year'])
            try:
                canonical,canonical_digest=canonical_manifest(manifest)
            except Exception:raise _TemporalBlocked('REGISTRY_RECORD_INVALID','image') from None
            _need(canonical_digest==digest,'REGISTRY_REFERENCE_CONFLICT','image')
            copied={**record,'manifest':canonical}
            self.observations.append({'year':row['year'],'status':'MATCHED_UNVERIFIED','manifest_sha256':digest,'issue':None})
            return copied
        except _TemporalBlocked as error:
            issue={'code':error.code,'field':error.field}
            self.observations.append({'year':row['year'],'status':'BLOCKED','manifest_sha256':digest,'issue':issue})
            self.first_issue={'code':error.code,'field':error.field,'year':row['year']}
            raise


def inspect_registry_temporal_normalization(store,model_ref,training_report_sha256,requested_years):
    """Verify declared Gregorian UTC-year windows, never physical acquisition."""
    result={'schema_version':1,'scope':'PINNED_YEARS_REGISTRY_TEMPORAL_READ_ONLY','status':'INVALID_INPUT','issue':None,
        'batch_observation':None,'temporal_observations':[],'registry_temporal_year_verified':False,
        'physical_acquisition_year_verified':False,'artifact_bytes_verified':False,'source_authority_verified':False,
        'scientific_accuracy_validated':False,'execution_authorized':False,'workflow_supported':False}
    try:ref,rows=_request(model_ref,training_report_sha256,requested_years)
    except Exception:
        # Preserve127's exact invalid-input response; its validation performs no I/O.
        result['batch_observation']=inspect_pinned_annual_normalization(store,None,None,None)
        result['issue']={'code':'INVALID_INPUT','field':'request','year':None};return result
    proxy=_TemporalStore(store,rows)
    batch=inspect_pinned_annual_normalization(proxy,ref,training_report_sha256,rows)
    result['batch_observation']=batch;result['temporal_observations']=proxy.observations
    if proxy.first_issue is not None:
        result['status']='TEMPORAL_BLOCKED';result['issue']=proxy.first_issue
    elif batch['status']=='PINNED_YEARS_MATCHED_UNVERIFIED':
        result['status']='REGISTRY_YEARS_MATCHED_UNVERIFIED'
        result['registry_temporal_year_verified']=(len(proxy.observations)==len(rows)
            and all(row['status']=='MATCHED_UNVERIFIED' for row in proxy.observations))
        result['artifact_bytes_verified']=result['registry_temporal_year_verified'] and batch['artifact_bytes_verified'] is True
    else:
        result['status']=batch['status'];result['issue']=batch['issue']
    return result
