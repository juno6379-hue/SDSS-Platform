"""명시 targeted256 로컬 지원 profile. 원격 예산이나 승인을 바꾸지 않는다."""
import hashlib
import json
from types import MappingProxyType

NAME = 'TARGETED_LOCAL_SUPPORT_3G_V1'
DESCRIPTOR = MappingProxyType({'name': NAME, 'max_files': 10000,
                               'max_support_bytes': 3 * 1024**3,
                               'max_file_bytes': 64 * 1024**2})
SHA256 = hashlib.sha256(json.dumps(dict(DESCRIPTOR), sort_keys=True,
                                   separators=(',', ':')).encode()).hexdigest()
MARKER = MappingProxyType({'name': NAME, 'sha256': SHA256})


def inventory_kwargs(request, legacy_fields, error):
    """v1은 기존 호출, 정확한 v2 marker만 고정3GiB를 선택한다."""
    def need(condition):
        if not condition:
            raise ValueError(error)
    need(type(request) is dict)
    version = request.get('schema_version')
    need(type(version) is int and version in (1, 2))
    fields = set(legacy_fields)
    if version == 1:
        need(set(request) == fields)
        return {}
    need(set(request) == fields | {'local_support_profile'})
    marker = request['local_support_profile']
    need(type(marker) is dict and set(marker) == {'name', 'sha256'})
    need(type(marker['name']) is str and marker['name'] == NAME and
         type(marker['sha256']) is str and marker['sha256'] == SHA256)
    return {'max_files': DESCRIPTOR['max_files'],
            'max_bytes': DESCRIPTOR['max_support_bytes']}


def metadata(request):
    """검증한 v2 요청의 관측 marker. 승인 flag를 만들지 않는다."""
    return {'local_support_profile': dict(MARKER)} if request['schema_version'] == 2 else {}


def request_sha256(request):
    return hashlib.sha256(json.dumps(request, sort_keys=True, ensure_ascii=False,
                                    allow_nan=False, separators=(',', ':')).encode()).hexdigest()
