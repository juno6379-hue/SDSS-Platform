"""추가1024 후보의 읽기 전용 검증과 별도 live guard. 집행 권한은 주지 않는다."""
import copy
from collections import Counter
import hashlib
import json
import math
import re
from pathlib import Path

from .quality_mask_bundle import _copy_json
from .readiness_connectivity_witness import FIXED_PROVINCE_SPLITS
from .targeted_bare_plan import _json, _keys, _need, _pinned
from .targeted_inventory import inspect_targeted_inventory
from .targeted_live_guards import TargetedLiveGuard, TargetedWindowClaims, _bounds, _metric_crs
from ..ml.per_scene_normalization_files import _root, _relative, _snapshot, _Blocked

REQUEST_KEYS = {'schema_version', 'kind', 'proposal_ref', 'current_manifest_ref',
                'ledger_ref', 'boundary_ref', 'config_ref', 'prior_plan_ref',
                'selected', 'maximum_batches'}
SIX_BANDS = ['blue', 'green', 'red', 'nir', 'swir16', 'swir22']
BATCH_BYTES = 65 * 1024**2


def _digest(value):
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                     separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def _config(root, ref):
    _need(_keys(ref, {'path', 'sha256'}) and type(ref['sha256']) is str and
          re.fullmatch('[a-f0-9]{64}', ref['sha256']) is not None, 'CENTER_CONFIG_REF_INVALID')
    path = _relative(root, ref['path'], 'config')
    _need(path.is_relative_to(root/'data') or path.is_relative_to(root/'configs'),
          'CENTER_CONFIG_PATH_INVALID')
    sha, raw = _snapshot(root, path, 2*1024**2, 'config', True)
    _need(sha == ref['sha256'], 'CENTER_CONFIG_PIN_MISMATCH')
    return path, _json(raw)


def _physical_inventory(root, aggregate, state):
    # 모듈을 읽는 것만으로 CLI를 import하지 않는다. main/원장 생성도 호출하지 않는다.
    from scripts.collect_targeted_bare import physical_patch_inventory
    return physical_patch_inventory(root, aggregate, state)


def _active_pins(root, request):
    for path, key, cap in [
        (root/'data/first-group-training-esri-v1/annual-window-report.json', 'current_manifest_ref', 128*1024**2),
        (root/'data/first-group-training-budget/global-ledger.json', 'ledger_ref', 8*1024**2),
    ]:
        _need(_snapshot(root, path, cap, 'active_input', True)[0] == request[key]['sha256'],
              'CENTER_ACTIVE_INPUT_CHANGED')


def _rectangle(native):
    from shapely.geometry import Polygon, box
    _need(_keys(native, {'crs', 'corners'}) and type(native['corners']) is list and
          len(native['corners']) == 4 and all(type(p) is list and len(p) == 2 and
          all(type(n) in (int, float) and math.isfinite(n) for n in p)
          for p in native['corners']), 'CENTER_NATIVE_INVALID')
    _metric_crs(native['crs'])
    polygon = Polygon(native['corners'])
    _need(polygon.is_valid and polygon.area > 0 and polygon.equals(box(*polygon.bounds)),
          'CENTER_NATIVE_INVALID')
    left, bottom, right, top = polygon.bounds
    _need(abs(right-left-10240) <= 1e-6 and abs(top-bottom-10240) <= 1e-6,
          'CENTER_NATIVE_SIZE_INVALID')
    return polygon


class DeficitCandidateLiveGuard(TargetedLiveGuard):
    """256 부모를 수정하지 않고 선택 B02의1024 규격만 별도로 확인한다."""
    def _binding(self):
        aoi = super()._binding()
        _need(type(self.job.get('key')) is str and
              re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,79}', self.job['key']) is not None,
              'CENTER_OWNER_INVALID')
        _need(type(self.job['config'].get('window_size')) is int and
              self.job['config']['window_size'] == 1024 and
              type(self.job.get('nominal_patches')) is int and self.job['nominal_patches'] == 16 and
              type(self.target.get('window_size')) is int and self.target['window_size'] == 1024,
              'CENTER_WINDOW_SIZE_INVALID')
        _rectangle(self.target['target_footprint_native'])
        from pyproj import Transformer
        inverse = Transformer.from_crs(self.target['target_footprint_native']['crs'], 4326, always_xy=True)
        points = [inverse.transform(*p) for p in self.target['target_footprint_native']['corners']]
        bbox = [min(p[0] for p in points), min(p[1] for p in points),
                max(p[0] for p in points), max(p[1] for p in points)]
        _need(all(abs(a-b) <= 1e-8 for a, b in zip(aoi['bbox'], bbox)), 'CENTER_BBOX_MISMATCH')
        return aoi

    def on_window(self, url, geometry):
        _need(type(url) is str and bool(url), 'CENTER_ASSET_URL_INVALID')
        if self.selected is None or url != self.blue:
            # 후보 SCL·동년 확대라벨·다른 선택asset은 기존 부모의 검사를 유지한다.
            return super().on_window(url, geometry)
        aoi = self._binding()
        _need(geometry['requested_bbox_wgs84'] == aoi['bbox'], 'TARGET_WINDOW_AOI_CHANGED')
        crs = _metric_crs(geometry['crs'])
        bounds = _bounds(geometry)
        _need(crs == _metric_crs(self.target['target_footprint_native']['crs']) and
              type(geometry['requested_side']) is int and geometry['requested_side'] == 1024 and
              geometry['window_width'] == geometry['window_height'] == 1024 and
              geometry['window']['width'] == geometry['window']['height'] == 1024 and
              geometry['window_transform'][0] == 10 and geometry['window_transform'][4] == -10,
              'CENTER_B02_GRID_INVALID')
        planned = _rectangle(self.target['target_footprint_native']).bounds
        _need(all(abs(a-b) <= 10.000001 for a, b in zip(bounds, planned)),
              'CENTER_B02_ALIGNMENT_SHORTFALL')
        self.windows.claim(self.job['key'], geometry['crs'], bounds)
        self.b02_checked = True


def prepare_deficit_candidate_jobs(project_root, request):
    """로컬 proof와 job 사본만 반환한다. 성공해도 항상 EXECUTION_BLOCKED다."""
    result = {'schema_version': 1, 'status': 'EXECUTION_BLOCKED', 'issue': None,
              'local_checks_passed': False, 'request_sha256': None, 'job_proposals': [],
              'targets': [], 'inventory': None, 'physical_inventory': None,
              'inventory_scan_count': 0, 'source_pins_verified': False,
              'execution_supported': False, 'collection_executed': False,
              'actual_quality_eligible': False, 'scientifically_verified_bare': False,
              'ready_for_training': False, 'network_requests': 0, 'source_or_ledger_writes': 0}
    try:
        request = _copy_json(request, 'request')
        _need(_keys(request, REQUEST_KEYS) and type(request['schema_version']) is int and
              request['schema_version'] == 1 and
              request['kind'] == 'GUARDED_DEFICIT_1024_REQUEST', 'CENTER_REQUEST_INVALID')
        maximum = request['maximum_batches']
        selected = request['selected']
        _need(type(maximum) is int and 1 <= maximum <= 2 and type(selected) is list and
              1 <= len(selected) <= maximum and all(_keys(s, {'spatial_window_id', 'year'})
              for s in selected), 'CENTER_BATCH_LIMIT_INVALID')
        _need(all(type(s['spatial_window_id']) is str and
              re.fullmatch('[A-Za-z0-9_-]{1,52}', s['spatial_window_id']) is not None and
              type(s['year']) is int and 2020 <= s['year'] <= 2025 for s in selected) and
              len({s['spatial_window_id'] for s in selected}) == len(selected),
              'CENTER_SELECTION_INVALID')
        root = _root(project_root)
        request_sha = _digest(request)
        paths, documents = {}, {}
        roles = [('proposal', 'proposal_ref', 2*1024**2),
                 ('source', 'current_manifest_ref', 128*1024**2),
                 ('ledger', 'ledger_ref', 8*1024**2),
                 ('boundary', 'boundary_ref', 2*1024**2),
                 ('prior', 'prior_plan_ref', 2*1024**2)]
        for role, key, cap in roles:
            paths[role], raw = _pinned(root, request[key], cap)
            documents[role] = _json(raw)
        paths['config'], documents['config'] = _config(root, request['config_ref'])
        _active_pins(root, request)
        _need(len(set(paths.values())) == 6, 'CENTER_INPUT_ALIAS')
        proposal, source, ledger, boundary, prior, config = (
            documents[k] for k in ('proposal', 'source', 'ledger', 'boundary', 'prior', 'config'))
        _need(type(proposal.get('schema_version')) is int and proposal['schema_version'] == 1 and
              proposal.get('executed_network') is False and
              proposal.get('collector_consumption_approved') is False and
              proposal.get('full_pending_support_inventory_verified') is False,
              'CENTER_PROPOSAL_INVALID')
        _need(proposal.get('source_sha256') == request['current_manifest_ref']['sha256'],
              'CENTER_SOURCE_SNAPSHOT_STALE')
        for declared, ref in [('boundary_sha256', 'boundary_ref'),
                              ('config_sha256', 'config_ref'), ('prior_plan_sha256', 'prior_plan_ref')]:
            _need(proposal.get(declared) == request[ref]['sha256'], 'CENTER_PROPOSAL_PIN_MISMATCH')
        rows = source.get('scenes'); history = source.get('historical_noneligible_patches', [])
        _need(type(rows) is list and type(history) is list and len(rows)+len(history) <= 3000 and
              all(type(r) is dict for r in rows+history) and type(ledger.get('batches')) is dict,
              'CENTER_SOURCE_OR_LEDGER_INVALID')
        _need(ledger.get('rate_limit_active') is False and
              type(ledger.get('additional_maximum_bytes')) is int and
              ledger['additional_maximum_bytes'] == 4*1024**3 and
              type(ledger.get('new_charged_bytes')) is int and
              0 <= ledger['new_charged_bytes'] <= ledger['additional_maximum_bytes'] and
              ledger['additional_maximum_bytes']-ledger['new_charged_bytes'] >= len(selected)*BATCH_BYTES,
              'CENTER_BUDGET_OR_CIRCUIT_INVALID')
        charged = ledger.get('external_research_metadata_body_bytes')
        _need(type(charged) is int and 0 <= charged <= ledger['new_charged_bytes'], 'CENTER_LEDGER_ACCOUNTING_INVALID')
        for batch in ledger['batches'].values():
            _need(type(batch) is dict and batch.get('status') in ('pending', 'settled') and
                  type(batch.get('reserved_bytes')) is int and type(batch.get('charged_bytes')) is int and
                  0 <= batch['charged_bytes'] <= batch['reserved_bytes'] <= 2*1024**3 and
                  (batch['status'] != 'pending' or batch['charged_bytes'] == batch['reserved_bytes']),
                  'CENTER_LEDGER_ACCOUNTING_INVALID')
            charged += batch['charged_bytes']
        _need(charged == ledger['new_charged_bytes'], 'CENTER_LEDGER_ACCOUNTING_INVALID')
        from shapely.geometry import shape
        from shapely.ops import transform
        from pyproj import Transformer
        features = {}; aois = {}
        for f in boundary['features']:
            p = f['properties']['province_id']
            _need(p in FIXED_PROVINCE_SPLITS and p not in features, 'CENTER_BOUNDARY_INVALID')
            features[p] = shape(f['geometry'])
            _need(features[p].is_valid and not features[p].is_empty, 'CENTER_BOUNDARY_INVALID')
        for aoi in config['aois']:
            p = aoi['id']
            _need(p in FIXED_PROVINCE_SPLITS and p not in aois, 'CENTER_CONFIG_AOI_INVALID')
            aois[p] = aoi
        _need(set(features) == set(aois) == set(FIXED_PROVINCE_SPLITS), 'CENTER_SIX_PROVINCES_REQUIRED')
        _need(type(prior.get('schema_version')) is int and prior['schema_version'] == 1 and prior.get('executed_network') is False,
              'CENTER_PRIOR_INVALID')
        from .candidates import validate_candidate_plan
        prior_checked = validate_candidate_plan(paths['prior'], paths['boundary'])
        # 미집행 prior 후보도 새 이름으로 다시 사용하지 않는다.
        existing_centers = [{k: c[k] for k in ('province', 'lon', 'lat', 'grid_crs')}
                            for c in prior_checked['candidates']]
        validate_candidate_plan(paths['proposal'], paths['boundary'], existing_centers)
        candidates = proposal.get('candidates')
        _need(type(candidates) is list and 1 <= len(candidates) <= 4 and
              all(type(c) is dict for c in candidates), 'CENTER_CANDIDATE_LIMIT')
        identifiers = [c['spatial_window_id'] for c in candidates]
        _need(len(set(identifiers)) == len(identifiers), 'CENTER_DUPLICATE_ID')
        counts = Counter()
        for row in rows:
            p, y = row['province'], row['year']
            if type(y) is str and re.fullmatch('202[0-5]', y): y = int(y)
            _need(p in FIXED_PROVINCE_SPLITS and type(y) is int and 2020 <= y <= 2025,
                  'CENTER_SOURCE_CELL_INVALID')
            if row.get('quality_status') == 'quality_eligible': counts[p, y] += 1
        jobs, targets = [], []
        for selection in selected:
            _need(selection['spatial_window_id'] in identifiers, 'CENTER_NOT_IN_PROPOSAL')
            candidate = candidates[identifiers.index(selection['spatial_window_id'])]
            p, y = candidate['province'], selection['year']
            _need(p in FIXED_PROVINCE_SPLITS and candidate.get('fixed_split') == FIXED_PROVINCE_SPLITS[p] and
                  candidate.get('reference') == 'esri_io' and type(candidate.get('window_size')) is int and
                  candidate['window_size'] == 1024 and type(candidate.get('years')) is list and
                  candidate['years'] and all(type(n) is int and 2020 <= n <= 2025 for n in candidate['years']) and
                  y in candidate['years'], 'CENTER_YEAR_OR_SPLIT_INVALID')
            _need(candidate.get('source_snapshot_sha256') == request['current_manifest_ref']['sha256'] and
                  candidate.get('boundary_sha256') == request['boundary_ref']['sha256'],
                  'CENTER_CANDIDATE_PIN_MISMATCH')
            _need(candidate.get('class_presence_verified') is False and
                  candidate.get('actual_quality_eligible') is False and
                  candidate.get('execution_supported') is False, 'CENTER_UNAPPROVED_FLAGS_REQUIRED')
            _need(counts[p, y] < 28, 'CENTER_CELL_ALREADY_MET')
            lon, lat = candidate['lon'], candidate['lat']
            _need(all(type(n) in (int, float) and math.isfinite(n) for n in (lon, lat)) and
                  -180 < lon < 180 and -90 < lat < 90, 'CENTER_COORDINATE_INVALID')
            crs = _metric_crs(candidate['grid_crs'])
            x, yy = Transformer.from_crs(4326, crs, always_xy=True).transform(lon, lat)
            native = {'crs': crs.to_string(), 'corners': [[x-5120, yy+5120], [x+5120, yy+5120],
                      [x+5120, yy-5120], [x-5120, yy-5120]]}
            polygon = _rectangle(native)
            boundary_native = transform(Transformer.from_crs(4326, crs, always_xy=True).transform, features[p])
            _need(boundary_native.intersection(polygon).area/polygon.area >= .95, 'CENTER_BOUNDARY_SHORTFALL')
            inverse = Transformer.from_crs(crs, 4326, always_xy=True)
            xy = [inverse.transform(*point) for point in native['corners']]
            bbox = [min(t[0] for t in xy), min(t[1] for t in xy), max(t[0] for t in xy), max(t[1] for t in xy)]
            given = candidate['bbox']
            _need(type(given) is list and len(given) == 4 and all(type(a) in (int, float) and
                  math.isfinite(a) and abs(a-b) <= 1e-8 for a, b in zip(given, bbox)), 'CENTER_BBOX_MISMATCH')
            identifier = selection['spatial_window_id']
            prefix = f'{p}/{identifier}/'
            _need(not any(r.get('province') == p and str(r.get('year')) == str(y) and
                  r.get('spatial_location_id', '').startswith(prefix) and
                  r.get('quality_status') == 'quality_eligible' for r in rows), 'CENTER_ALREADY_ELIGIBLE')
            key = f'center1024-{p}-{y}-{request_sha[:12]}-{_digest(identifier)[:8]}'
            legacy_key = f'parallel-v2-extra-{p}-{y}-{identifier}'
            _need(key not in ledger['batches'] and legacy_key not in ledger['batches'], 'CENTER_BATCH_ALREADY_RESERVED')
            job_config = copy.deepcopy(config); aoi = copy.deepcopy(aois[p])
            aoi.update(id=identifier, province_id=p, bbox=copy.deepcopy(given))
            job_config.update(aois=[aoi], years=[y], bands=SIX_BANDS.copy(), annual_reference='esri_io',
                window_size=1024, max_total_bytes=64*1024**2, prior_download_budget_bytes=0,
                candidate_limit=5, search_limit=20, sort_by_cloud=True, min_valid_fraction=.8,
                candidate_valid_fraction=.65, cloud_cover=60, label_first=True,
                verify_product_metadata=True, preserve_source_crops=True, transient_asset_retries=0,
                collection_policy_version='deficit-center-1024-PLAN-ONLY')
            target = {'target_id': identifier, 'province': p, 'fixed_split': FIXED_PROVINCE_SPLITS[p],
                      'year': y, 'window_size': 1024, 'target_bbox_wgs84': copy.deepcopy(given),
                      'target_footprint_native': native}
            targets.append(target)
            jobs.append({'key': key, 'target_id': identifier, 'province': p, 'year': y,
                         'split': FIXED_PROVINCE_SPLITS[p], 'spatial_window_id': identifier,
                         'nominal_patches': 16, 'geometry': copy.deepcopy(features[p].__geo_interface__),
                         'config': job_config, 'config_sha256': hashlib.sha256(json.dumps(job_config, sort_keys=True).encode()).hexdigest()})
        _need(len({job['key'] for job in jobs}) == len(jobs), 'CENTER_JOB_ID_COLLISION')
        proof = inspect_targeted_inventory(root, {'manifest_ref': request['current_manifest_ref'],
                    'ledger_ref': request['ledger_ref'], 'target': targets[0]['target_footprint_native']})
        result['inventory_scan_count'] = 1
        _need(all(proof.get(k) is True for k in ('inventory_verified', 'pending_footprints_verified', 'source_pins_verified')),
              'CENTER_FULL_INVENTORY_NOT_VERIFIED')
        windows = TargetedWindowClaims(proof['assets'])
        for target in targets:
            windows.claim(target['target_id'], target['target_footprint_native']['crs'],
                          _rectangle(target['target_footprint_native']).bounds)
        physical = _physical_inventory(root, source, ledger)
        _need(type(physical.get('physical_patch_count')) is int and
              0 <= physical['physical_patch_count'] and physical.get('limit') == 3000 and
              physical['physical_patch_count']+16*len(jobs) <= 3000, 'CENTER_PHYSICAL_CAP')
        for role, key, cap in roles: _pinned(root, request[key], cap)
        _config(root, request['config_ref'])
        _active_pins(root, request)
        _need(_physical_inventory(root, source, ledger) == physical, 'CENTER_PHYSICAL_CHANGED')
        result.update(local_checks_passed=True, issue='COORDINATOR_NOT_CONNECTED', request_sha256=request_sha,
                      job_proposals=jobs, targets=targets, inventory=proof, physical_inventory=physical,
                      source_pins_verified=True)
    except _Blocked as exc: result['issue'] = exc.code
    except Exception as exc:
        code = str(exc)
        result['issue'] = code if re.fullmatch('[A-Z_]{1,80}', code) else 'CENTER_INPUT_UNAVAILABLE'
    return result
