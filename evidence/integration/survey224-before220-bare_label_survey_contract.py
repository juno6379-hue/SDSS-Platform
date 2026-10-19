"""SURVEY_LABEL_ONLY의 순수 선언 계약. 파일/원장/HTTP/영상은 읽지 않는다."""
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import math
from pathlib import PurePosixPath
import re
from .references import esri_annual_plan


SPLITS = {'south_sulawesi': 'train', 'gorontalo': 'train',
          'southeast_sulawesi': 'train', 'east_java': 'train',
          'banten': 'val', 'west_java': 'test'}
COG_BYTES = 64 * 1024**2
METADATA_BYTES = 1024**2
BATCH_BYTES = COG_BYTES + METADATA_BYTES
GLOBAL_BYTES = 4 * 1024**3
FALSE_FLAGS = {'execution_supported', 'collection_executed', 'quality_eligible',
               'training_ready', 'independent_ground_truth', 'rgb_collected',
               'source_authenticity_verified', 'raster_header_verified',
               'ledger_verified', 'registry_connected', 'target_consumer_connected'}
POLICY = {'maximum_batches': 1, 'maximum_cog_bytes': COG_BYTES,
          'maximum_metadata_bytes': METADATA_BYTES, 'maximum_label_side': 2048,
          'request_spacing_seconds': 2, 'transient_asset_retries': 0,
          'stop_on_first_429': True}


class SurveyContractError(ValueError):
    """고정 오류코드만 노출한다. 입력값/경로/예외문을 포함하지 않는다."""


def _need(ok, code):
    if not ok:
        raise SurveyContractError(code)


def _keys(value, keys, code):
    _need(type(value) is dict and set(value) == set(keys), code)


def _uint(value, maximum):
    return type(value) is int and 0 <= value <= maximum


def _number(value):
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _copy(value):
    # Pure bounded input walk, before serializing. No arbitrary object methods.
    stack = [(value, 0)]; nodes = 0
    while stack:
        item, depth = stack.pop(); nodes += 1
        _need(nodes <= 10000 and depth <= 24, 'SURVEY_STRUCTURE_LIMIT')
        if type(item) is dict:
            _need(len(item) <= 128 and all(type(k) is str and len(k) <= 128 for k in item),
                  'SURVEY_STRUCTURE_LIMIT')
            stack.extend((v, depth+1) for v in item.values())
        elif type(item) is list:
            _need(len(item) <= 128, 'SURVEY_STRUCTURE_LIMIT')
            stack.extend((v, depth+1) for v in item)
        elif type(item) is str:
            _need(len(item) <= 4096, 'SURVEY_STRUCTURE_LIMIT')
        elif type(item) in (int, float):
            _need(_number(item) and abs(item) <= 2**63-1, 'SURVEY_NUMBER_INVALID')
        else:
            _need(type(item) in (bool, type(None)), 'SURVEY_TYPE_INVALID')
    text = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)
    _need(len(text.encode('utf-8')) <= 65536, 'SURVEY_STRUCTURE_LIMIT')
    return json.loads(text)


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def _digest(value):
    return hashlib.sha256(_canonical(value).encode('utf-8')).hexdigest()


def _ref(value, *, survey=False):
    _keys(value, {'path', 'sha256'}, 'SURVEY_REFERENCE_INVALID')
    path = value['path']; pin = value['sha256']
    _need(type(path) is str and 1 <= len(path) <= 1024 and
          type(pin) is str and re.fullmatch('[a-f0-9]{64}', pin) is not None,
          'SURVEY_REFERENCE_INVALID')
    parts = path.split('/')
    _need(not any(c in path for c in '\\:*?"<>|') and
          not any(ord(c) < 32 for c in path) and
          all(p not in ('', '.', '..') and p == p.rstrip(' .') for p in parts) and
          not any(re.fullmatch(r'(?i)(CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³])(?:\..*)?', p) for p in parts) and
          parts[0] in ('data', 'evidence', 'configs') and
          (parts[0] != 'evidence' or parts[1:2] == ['integration']), 'SURVEY_PATH_INVALID')
    if survey:
        _need(parts[:2] == ['data', 'bare-label-surveys'], 'SURVEY_PATH_INVALID')
    return PurePosixPath(path)


def _time(text, year):
    _need(type(text) is str and re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ', text) is not None,
          'SURVEY_TIME_INVALID')
    try:
        parsed = datetime.strptime(text, '%Y-%m-%dT%H:%M:%SZ')
    except ValueError:
        raise SurveyContractError('SURVEY_TIME_INVALID') from None
    _need(parsed.year == year, 'SURVEY_YEAR_MISMATCH')
    return parsed


def _scene(value, province, year):
    _keys(value, {'id', 'datetime', 'source_group', 'stac_ref'}, 'SURVEY_SCENE_INVALID')
    _need(type(value['id']) is str and re.fullmatch('[A-Za-z0-9_.:-]{1,160}', value['id']) is not None and
          re.match(r'S2[ABC]_MSIL2A_'+str(year)+r'\d{4}T\d{6}_', value['id']) is not None and
          value['source_group'] == province+'/'+value['id'], 'SURVEY_SCENE_INVALID')
    _time(value['datetime'], year); _ref(value['stac_ref'])
    try:
        esri_annual_plan(year, value['id'])
    except ValueError:
        raise SurveyContractError('SURVEY_SCENE_INVALID') from None


def _grid(value, *, label):
    _keys(value, {'crs', 'transform', 'width', 'height'}, 'SURVEY_GRID_INVALID')
    _need(type(value['crs']) is str and re.fullmatch(r'EPSG:(326|327)(0[1-9]|[1-5][0-9]|60)', value['crs']) is not None,
          'SURVEY_GRID_INVALID')
    _need(all(type(value[k]) is int and 1 <= value[k] <= (2048 if label else 1024)
              for k in ('width', 'height')), 'SURVEY_GRID_INVALID')
    t = value['transform']
    _need(type(t) is list and len(t) == 6 and all(_number(n) for n in t) and
          t[1] == t[3] == 0 and t[0] in ((10,) if label else (10, 20)) and
          t[4] == -t[0], 'SURVEY_GRID_INVALID')


def _false(value):
    _need(all(value[k] is False for k in FALSE_FLAGS) and
          type(value['patches_materialized']) is int and value['patches_materialized'] == 0,
          'SURVEY_APPROVAL_PROHIBITED')


@dataclass(frozen=True)
class ValidatedSurveyContract:
    """검증한 선언의 불변 canonical JSON. 파일진실/집행승인 토큰이 아니다."""
    kind: str
    request_sha256: str
    canonical_json: str
    status: str = 'DECLARED_CONTRACT_VALID_EXECUTION_PLANNED'
    execution_supported: bool = False
    provenance_verified: bool = False

    def to_dict(self):
        """새 사본만 반환해 호출자의 변경이 검증객체를 바꾸지 않게 한다."""
        return json.loads(self.canonical_json)


def validate_survey_request(request):
    """선택scene까지 고정한 단일SURVEY 계획의 선언만 검증한다. I/O0."""
    value = _copy(request)
    refs = {'current_manifest_ref', 'boundary_ref', 'ledger_ref', 'base_config_ref'}
    _keys(value, {'schema_version', 'kind', 'survey_id', 'seed', 'selected_scene',
                  'policy', 'budget_snapshot', 'output_relative_path', 'patches_materialized',
                  'config_sha256'} |
          refs | FALSE_FLAGS, 'SURVEY_REQUEST_INVALID')
    _need(type(value['schema_version']) is int and value['schema_version'] == 1 and
          value['kind'] == 'BARE_LABEL_SURVEY_REQUEST', 'SURVEY_REQUEST_INVALID')
    identifier = value['survey_id']
    _need(type(identifier) is str and re.fullmatch('[a-z0-9][a-z0-9-]{0,47}', identifier) is not None,
          'SURVEY_ID_INVALID')
    _need(type(value['config_sha256']) is str and re.fullmatch('[a-f0-9]{64}', value['config_sha256']) is not None,
          'SURVEY_CONFIG_INVALID')
    paths = [_ref(value[k]) for k in sorted(refs)]
    _need(len(set(str(p).casefold() for p in paths)) == len(paths), 'SURVEY_REFERENCE_ALIAS')
    _need(all(value[k]['path'].startswith('data/') for k in refs-{'base_config_ref'}) and
          value['base_config_ref']['path'].split('/')[0] in ('data', 'configs'), 'SURVEY_PATH_INVALID')
    _need(value['output_relative_path'] == 'data/bare-label-surveys/'+identifier,
          'SURVEY_OUTPUT_INVALID')
    seed = value['seed']
    _keys(seed, {'seed_id', 'province', 'fixed_split', 'year', 'bbox_wgs84',
                 'period_start', 'period_end', 'justification_ref'}, 'SURVEY_SEED_INVALID')
    province = seed['province']; year = seed['year']
    _need(type(province) is str and province in SPLITS and seed['fixed_split'] == SPLITS[province] and
          type(year) is int and 2020 <= year <= 2025 and type(seed['seed_id']) is str and
          re.fullmatch('[A-Za-z0-9_-]{1,52}', seed['seed_id']) is not None, 'SURVEY_SEED_INVALID')
    bbox = seed['bbox_wgs84']
    _need(type(bbox) is list and len(bbox) == 4 and all(_number(n) for n in bbox) and
          -180 < bbox[0] < bbox[2] < 180 and -90 < bbox[1] < bbox[3] < 90,
          'SURVEY_BBOX_INVALID')
    _need(_time(seed['period_start'], year) < _time(seed['period_end'], year), 'SURVEY_TIME_INVALID')
    _ref(seed['justification_ref']); _scene(value['selected_scene'], province, year)
    _need(seed['period_start'] <= value['selected_scene']['datetime'] <= seed['period_end'],
          'SURVEY_SCENE_INVALID')
    _keys(value['policy'], POLICY, 'SURVEY_POLICY_INVALID')
    _need(all(type(value['policy'][k]) is type(v) and value['policy'][k] == v for k, v in POLICY.items()),
          'SURVEY_POLICY_INVALID')
    budget = value['budget_snapshot']
    _keys(budget, {'additional_maximum_bytes', 'new_charged_bytes', 'preserved_pending_bytes',
                   'rate_limit_active'}, 'SURVEY_BUDGET_INVALID')
    _need(type(budget['additional_maximum_bytes']) is int and budget['additional_maximum_bytes'] == GLOBAL_BYTES and
          _uint(budget['new_charged_bytes'], GLOBAL_BYTES-BATCH_BYTES) and
          _uint(budget['preserved_pending_bytes'], budget['new_charged_bytes']) and
          budget['rate_limit_active'] is False, 'SURVEY_BUDGET_INVALID')
    _false(value)
    return ValidatedSurveyContract(value['kind'], _digest(value), _canonical(value))


def validate_survey_receipt(receipt, request):
    """실측정산 선언/미정산전액보존을 구분한다. 실제원장은 확인하지 않는다."""
    checked = validate_survey_request(request)
    plan = checked.to_dict(); value = _copy(receipt)
    _keys(value, {'schema_version', 'kind', 'collection_purpose', 'survey_id', 'request_sha256',
          'batch_key', 'config_sha256', 'selected_scene', 'label', 'candidate_scl_refs',
          'accounting', 'patches_materialized'} | FALSE_FLAGS, 'SURVEY_RECEIPT_INVALID')
    _need(type(value['schema_version']) is int and value['schema_version'] == 1 and
          value['kind'] == 'BARE_LABEL_SURVEY_RECEIPT' and
          value['collection_purpose'] == 'SURVEY_LABEL_ONLY' and
          value['survey_id'] == plan['survey_id'] and value['request_sha256'] == checked.request_sha256,
          'SURVEY_RECEIPT_BINDING_INVALID')
    _need(value['selected_scene'] == plan['selected_scene'], 'SURVEY_SCENE_MISMATCH')
    _need(value['batch_key'] == 'bare-survey-'+plan['survey_id']+'-'+checked.request_sha256[:12] and
          value['config_sha256'] == plan['config_sha256'],
          'SURVEY_RECEIPT_BINDING_INVALID')
    label = value['label']; seed = plan['seed']
    _keys(label, {'ref', 'label_source', 'label_year', 'source_url', 'license', 'dataset_version',
                  'grid'}, 'SURVEY_LABEL_INVALID')
    label_path = _ref(label['ref'], survey=True)
    expected_label = esri_annual_plan(seed['year'], plan['selected_scene']['id'])
    _need(str(label_path) == plan['output_relative_path']+'/raw-esri_io.tif' and
          label['label_source'] == 'esri_io' and type(label['label_year']) is int and
          label['label_year'] == seed['year'] and label['license'] == 'CC-BY-4.0' and
          label['dataset_version'] == expected_label['version'] and
          label['source_url'] == expected_label['url'],
          'SURVEY_LABEL_INVALID')
    _grid(label['grid'], label=True)
    scls = value['candidate_scl_refs']
    # v1 is intentionally only the fixed selected-scene SCL. Other candidate
    # scenes need their own pinned lineage contract before this can be widened.
    _need(type(scls) is list and len(scls) == 1, 'SURVEY_SCL_INVALID')
    seen = {str(label_path).casefold()}; selected = 0
    for scl in scls:
        _keys(scl, {'ref', 'scene_id', 'role', 'grid'}, 'SURVEY_SCL_INVALID')
        path = _ref(scl['ref'], survey=True)
        _need(path.parent == label_path.parent and re.fullmatch(r'qa-candidate-\d{2}-SCL\.tif', path.name) is not None and
              str(path).casefold() not in seen and scl['role'] == 'SCL_CANDIDATE_SUPPORT' and
              scl['scene_id'] == plan['selected_scene']['id'],
              'SURVEY_SCL_INVALID')
        seen.add(str(path).casefold()); selected += scl['scene_id'] == plan['selected_scene']['id']
        _grid(scl['grid'], label=False)
        _need(scl['grid']['crs'] == label['grid']['crs'], 'SURVEY_GRID_INVALID')
    _need(selected == 1, 'SURVEY_SELECTED_SCL_REQUIRED')
    accounting = value['accounting']
    _keys(accounting, {'state', 'measurement_known', 'reserved_bytes', 'charged_bytes',
          'metadata_body_bytes', 'cog_body_bytes'}, 'SURVEY_ACCOUNTING_INVALID')
    _need(type(accounting['reserved_bytes']) is int and accounting['reserved_bytes'] == BATCH_BYTES,
          'SURVEY_ACCOUNTING_INVALID')
    if accounting['state'] == 'DECLARED_MEASURED_SETTLED':
        _need(accounting['measurement_known'] is True and
              _uint(accounting['metadata_body_bytes'], METADATA_BYTES) and
              _uint(accounting['cog_body_bytes'], COG_BYTES) and
              type(accounting['charged_bytes']) is int and accounting['charged_bytes'] ==
              accounting['metadata_body_bytes']+accounting['cog_body_bytes'], 'SURVEY_ACCOUNTING_INVALID')
    else:
        _need(accounting['state'] == 'UNSETTLED_FULL_RESERVATION' and
              accounting['measurement_known'] is False and
              type(accounting['charged_bytes']) is int and accounting['charged_bytes'] == BATCH_BYTES and
              accounting['metadata_body_bytes'] is None and accounting['cog_body_bytes'] is None,
              'SURVEY_ACCOUNTING_INVALID')
    _false(value)
    return ValidatedSurveyContract(value['kind'], checked.request_sha256, _canonical(value))
