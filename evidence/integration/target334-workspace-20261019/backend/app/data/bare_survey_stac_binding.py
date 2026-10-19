"""고정 PC STAC bytes의 SURVEY 선언 결속. 파일·HTTP·영상·원장을 읽지 않는다."""
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import math
import re
from urllib.parse import urlsplit

from .bare_label_survey_contract import validate_survey_request, SurveyContractError

MAX_BYTES = 1024**2
MAX_DEPTH = 32
MAX_NODES = 25000
CATALOG = 'https://planetarycomputer.microsoft.com/api/stac/v1'
ASSET_HOSTS = frozenset({'sentinel2l2a01.blob.core.windows.net',
                         'sentinel2l2a02.blob.core.windows.net'})
_ID = (r'(S2[ABC])_MSIL2A_([0-9]{8}T[0-9]{6})(?:_N([0-9]{4}))?'
       r'_R([0-9]{3})_T((?:0[1-9]|[1-5][0-9]|60)[C-HJ-NP-X][A-HJ-NP-Z][A-HJ-NP-V])_'
       r'([0-9]{8}T[0-9]{6})')


class SurveyStacBindingError(ValueError):
    """고정 코드만 반환하며 URL/입력/내부 예외를 노출하지 않는다."""


def _need(ok, code):
    if not ok:
        raise SurveyStacBindingError(code)


def _pairs(items):
    result = {}
    for key, value in items:
        _need(key not in result, 'SURVEY_STAC_DUPLICATE_KEY')
        result[key] = value
    return result


def _constant(value):
    raise SurveyStacBindingError('SURVEY_STAC_NUMBER_INVALID')


def _document(raw):
    _need(type(raw) is bytes and 2 <= len(raw) <= MAX_BYTES, 'SURVEY_STAC_BYTE_LIMIT')
    try:
        text = raw.decode('utf-8')
    except UnicodeError:
        raise SurveyStacBindingError('SURVEY_STAC_UTF8_INVALID') from None
    _need(not text.startswith('\ufeff') and '\x00' not in text, 'SURVEY_STAC_UTF8_INVALID')
    depth = 0; quoted = False; escaped = False
    for char in text:
        if quoted:
            if escaped: escaped = False
            elif char == '\\': escaped = True
            elif char == '"': quoted = False
        elif char == '"': quoted = True
        elif char in '[{':
            depth += 1
            _need(depth <= MAX_DEPTH, 'SURVEY_STAC_DEPTH_LIMIT')
        elif char in ']}': depth -= 1
    try:
        document = json.loads(text, object_pairs_hook=_pairs, parse_constant=_constant)
    except SurveyStacBindingError:
        raise
    except (ValueError, RecursionError):
        raise SurveyStacBindingError('SURVEY_STAC_JSON_INVALID') from None
    nodes = 0; stack = [document]
    while stack:
        value = stack.pop(); nodes += 1
        _need(nodes <= MAX_NODES, 'SURVEY_STAC_NODE_LIMIT')
        if type(value) is dict:
            stack.extend(value.keys()); stack.extend(value.values())
        elif type(value) is list: stack.extend(value)
        elif type(value) is str:
            try: value.encode('utf-8')
            except UnicodeError: raise SurveyStacBindingError('SURVEY_STAC_UTF8_INVALID') from None
        elif type(value) is float:
            _need(math.isfinite(value), 'SURVEY_STAC_NUMBER_INVALID')
    _need(type(document) is dict, 'SURVEY_STAC_FEATURE_INVALID')
    return document


def _url(value, hosts):
    _need(type(value) is str and 1 <= len(value) <= 4096 and
          all(32 < ord(c) < 127 for c in value) and
          not any(c in value for c in ('%', '\\', '?', '#')), 'SURVEY_STAC_URL_INVALID')
    try: parsed = urlsplit(value)
    except ValueError: raise SurveyStacBindingError('SURVEY_STAC_URL_INVALID') from None
    _need(parsed.scheme == 'https' and parsed.hostname in hosts and
          parsed.netloc == parsed.hostname and not parsed.query and not parsed.fragment and
          re.fullmatch(r'/[A-Za-z0-9._/-]+', parsed.path) is not None,
          'SURVEY_STAC_URL_INVALID')
    parts = parsed.path.split('/')[1:]
    _need(all(p and p not in ('.', '..') for p in parts), 'SURVEY_STAC_URL_INVALID')
    return parts


def _datetime(value):
    _need(type(value) is str and re.fullmatch(
        r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z', value),
        'SURVEY_STAC_TIME_INVALID')
    try: return datetime.strptime(value, '%Y-%m-%dT%H:%M:%S.%fZ' if '.' in value else '%Y-%m-%dT%H:%M:%SZ')
    except ValueError: raise SurveyStacBindingError('SURVEY_STAC_TIME_INVALID') from None


@dataclass(frozen=True)
class SurveyStacBinding:
    request_sha256: str
    raw_stac_sha256: str
    canonical_json: str
    status: str = 'PINNED_STAC_METADATA_BOUND'
    source_authenticity_verified: bool = False
    execution_supported: bool = False

    def to_dict(self):
        return json.loads(self.canonical_json)


def validate_survey_stac_binding(request, raw_stac, selected_asset):
    """PC sentinel-2-l2a/SCL20m만. bytes pin과 선언의 일치이며 원격 진실 검증이 아니다."""
    try:
        checked = validate_survey_request(request)
    except SurveyContractError:
        raise SurveyStacBindingError('SURVEY_STAC_REQUEST_INVALID') from None
    plan = checked.to_dict(); scene = plan['selected_scene']
    try:
        _need(type(selected_asset) is dict and set(selected_asset) == {'key', 'source_url', 'product_uri'},
              'SURVEY_STAC_ASSET_DECLARATION_INVALID')
        selected = {k: selected_asset[k] for k in ('key', 'source_url', 'product_uri')}
    except (KeyError, RuntimeError):
        raise SurveyStacBindingError('SURVEY_STAC_INPUT_CHANGED') from None
    _need(all(type(v) is str and 1 <= len(v) <= 4096 for v in selected.values()) and selected['key'] == 'SCL',
          'SURVEY_STAC_ASSET_DECLARATION_INVALID')
    paths = [plan[k]['path'] for k in ('current_manifest_ref', 'boundary_ref', 'ledger_ref', 'base_config_ref')]
    paths.append(plan['seed']['justification_ref']['path'])
    _need(scene['stac_ref']['path'].casefold() not in {p.casefold() for p in paths}, 'SURVEY_STAC_REFERENCE_ALIAS')
    _need(type(raw_stac) is bytes and 2 <= len(raw_stac) <= MAX_BYTES, 'SURVEY_STAC_BYTE_LIMIT')
    pin = hashlib.sha256(raw_stac).hexdigest()
    _need(pin == scene['stac_ref']['sha256'], 'SURVEY_STAC_PIN_MISMATCH')
    document = _document(raw_stac)
    _need(document.get('type') == 'Feature' and document.get('stac_version') == '1.0.0' and
          document.get('collection') == 'sentinel-2-l2a' and document.get('id') == scene['id'],
          'SURVEY_STAC_FEATURE_INVALID')
    properties = document.get('properties'); assets = document.get('assets'); links = document.get('links')
    _need(type(properties) is dict and type(assets) is dict and type(links) is list and
          all(type(link) is dict for link in links), 'SURVEY_STAC_FEATURE_INVALID')
    observed_time = properties.get('datetime')
    _need(_datetime(observed_time) == _datetime(scene['datetime']), 'SURVEY_STAC_TIME_MISMATCH')
    product = properties.get('s2:product_uri')
    _need(type(product) is str and product == selected['product_uri'] and product.endswith('.SAFE'),
          'SURVEY_STAC_PRODUCT_INVALID')
    catalog_id = re.fullmatch(_ID, scene['id']); product_id = re.fullmatch(_ID + r'\.SAFE', product)
    _need(catalog_id is not None and product_id is not None and product_id[3] is not None,
          'SURVEY_STAC_PRODUCT_INVALID')
    _need(all(catalog_id[i] == product_id[i] for i in (1, 2, 4, 5, 6)) and
          (catalog_id[3] is None or catalog_id[3] == product_id[3]), 'SURVEY_STAC_PRODUCT_MISMATCH')
    if 's2:processing_baseline' in properties:
        baseline = properties['s2:processing_baseline']
        _need(type(baseline) is str and re.fullmatch('[0-9]{2}\\.[0-9]{2}', baseline) and
              baseline.replace('.', '') == product_id[3], 'SURVEY_STAC_PRODUCT_MISMATCH')
    self_links = [link for link in links if link.get('rel') == 'self']
    expected_self = CATALOG + '/collections/sentinel-2-l2a/items/' + scene['id']
    _need(len(self_links) == 1 and self_links[0].get('href') == expected_self, 'SURVEY_STAC_SELF_INVALID')
    _url(expected_self, {'planetarycomputer.microsoft.com'})
    asset = assets.get('SCL')
    _need(type(asset) is dict and asset.get('href') == selected['source_url'], 'SURVEY_STAC_ASSET_MISMATCH')
    parts = _url(selected['source_url'], ASSET_HOSTS)
    safe = [i for i, part in enumerate(parts) if part.endswith('.SAFE')]
    _need(parts[0] == 'sentinel2-l2' and len(safe) == 1 and parts[safe[0]] == product,
          'SURVEY_STAC_ASSET_PRODUCT_MISMATCH')
    tile = product_id[5]; acquisition = product_id[2]
    _need(parts[:safe[0]] == ['sentinel2-l2', tile[:2], tile[2], tile[3:],
                             acquisition[:4], acquisition[4:6], acquisition[6:8]],
          'SURVEY_STAC_ASSET_LAYOUT_UNSUPPORTED')
    tail = parts[safe[0]+1:]
    _need(len(tail) == 5 and tail[0] == 'GRANULE' and tail[2:4] == ['IMG_DATA', 'R20m'] and
          tail[4] == f'T{product_id[5]}_{product_id[2]}_SCL_20m.tif' and
          re.fullmatch(r'L2A_T' + product_id[5] + r'_A[0-9]{6}_[0-9]{8}T[0-9]{6}', tail[1]),
          'SURVEY_STAC_ASSET_LAYOUT_UNSUPPORTED')
    try: datetime.strptime(tail[1].rsplit('_', 1)[1], '%Y%m%dT%H%M%S')
    except ValueError: raise SurveyStacBindingError('SURVEY_STAC_ASSET_LAYOUT_UNSUPPORTED') from None
    result = {'schema_version': 1, 'kind': 'SURVEY_PINNED_STAC_BINDING',
              'status': 'PINNED_STAC_METADATA_BOUND', 'provider_policy': 'PC_SENTINEL2_L2A_SCL20_V1',
              'request_sha256': checked.request_sha256, 'raw_stac_sha256': pin,
              'selected_scene': scene, 'raw_stac_datetime': observed_time,
              'selected_asset': selected, 'self_url': expected_self,
              'metadata_consistency_verified': True,
              **{k: False for k in ('source_authenticity_verified', 'remote_asset_verified',
                  'raster_header_verified', 'quality_eligible', 'independent_ground_truth',
                  'scientific_accuracy_validated', 'execution_supported', 'collection_executed',
                  'ledger_verified', 'training_ready', 'registry_connected', 'target_consumer_connected')}}
    canonical = json.dumps(result, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)
    return SurveyStacBinding(checked.request_sha256, pin, canonical)
