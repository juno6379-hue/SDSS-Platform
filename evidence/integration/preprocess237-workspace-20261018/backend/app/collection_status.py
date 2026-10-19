from .collection_source_profile import configured,read_source,verify_source,SourceProfileError
"""수집 보고서를 읽어 성공 재고와 최근 실패를 분리하는 읽기 전용 현황."""
from datetime import datetime, timezone
import hashlib
import json
import os
import stat
from pathlib import Path
from .ml.manifest_resource_profile import active,read_metadata,bounded_json_digest,metadata_identity,ProfileResourceError,serialized_io
from .collection_priority_status import collection_targets, candidate_quality, bare_target_review

_HASH_CACHE = {}


@serialized_io
def same_hash(path, expected, *, json_role=None):
    """큰 입력의 재해시는 내용 변경을 시사하는 파일 메타데이터가 바뀔 때 수행한다."""
    if active() is not None and json_role!='binary':
        if json_role is None:raise ProfileResourceError('MANIFEST_JSON_ROLE_REQUIRED')
        logical,before_identity=metadata_identity(path,json_role)
        key=('PROFILE237',str(logical),json_role,before_identity)
        if key not in _HASH_CACHE:
            value=bounded_json_digest(logical,json_role)
            if metadata_identity(path,json_role)!=(logical,before_identity):raise ProfileResourceError('MANIFEST_JSON_CHANGED')
            if len(_HASH_CACHE)>20000:_HASH_CACHE.clear()
            _HASH_CACHE[key]=value
        if metadata_identity(path,json_role)!=(logical,before_identity):raise ProfileResourceError('MANIFEST_JSON_CHANGED')
        return isinstance(expected,str) and _HASH_CACHE[key]==expected
    before = path.stat()
    key = (str(path), before.st_mtime_ns, before.st_ctime_ns, before.st_size)
    if key not in _HASH_CACHE:
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(chunk)
        after = path.stat()
        if (before.st_mtime_ns, before.st_ctime_ns, before.st_size) != (after.st_mtime_ns, after.st_ctime_ns, after.st_size):
            return False
        if len(_HASH_CACHE) > 20000:
            _HASH_CACHE.clear()
        _HASH_CACHE[key] = digest.hexdigest()
    return isinstance(expected, str) and _HASH_CACHE[key] == expected

PROVINCES = [('south_sulawesi', 'South Sulawesi'), ('gorontalo', 'Gorontalo'),
             ('southeast_sulawesi', 'Southeast Sulawesi'), ('banten', 'Banten'),
             ('west_java', 'West Java'), ('east_java', 'East Java')]
YEARS = list(range(2020, 2026))


def read_report(path, errors, *, json_role='status_report'):
    try:
        value = read_metadata(path,json_role)[0] if active() is not None else json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(value, dict):
            raise ValueError('보고서 객체가 아님')
        return value
    except (ProfileResourceError,SourceProfileError):
        raise
    except (OSError, ValueError):
        # 작성 중인 파일은 미확인으로 표시하며 과거 성공을 실패로 바꾸지 않는다.
        errors.append(path.name)
        return {}


def local_file(value, root):
    if not isinstance(value, str) or not value:
        return None
    # Resolve the trusted data root once in collection_status, not thousands of
    # historical raster paths through Windows realpath. Reject outside paths
    # lexically before touching them, then inspect every local component without
    # following links (including Windows junctions/reparse points).
    try:
        if any(part not in ('.', '..') and part.endswith((' ', '.'))
               for part in Path(value).parts):
            return None
        root = Path(os.path.abspath(root))
        path = Path(os.path.abspath(os.path.join(root, value)))
        relative = path.relative_to(root)
        if not relative.parts:
            return None
        if any(':' in part or part.endswith((' ', '.')) for part in relative.parts):
            return None
        current = root
        for index, part in enumerate((None, *relative.parts)):
            if part is not None:
                current = current / part
            info = current.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
                return None
            last = index == len(relative.parts)
            if not (stat.S_ISREG(info.st_mode) if last else stat.S_ISDIR(info.st_mode)):
                return None
        return path
    except (ProfileResourceError,SourceProfileError):
        raise
    except (OSError, ValueError):
        return None


@configured('status')
def collection_status(data_root,*,_source_selection=None):
    root = Path(data_root).resolve()
    errors = []
    current_path=root/'first-group-training-esri-v1/annual-window-report.json'
    current_cache=[]
    def current():
        if not current_cache:current_cache.append(read_source(root,_source_selection))
        return current_cache[0][0]
    def report_at(path,json_role='status_report'):
        if path==current_path:
            try:return current()
            except (ProfileResourceError,SourceProfileError):raise
            except (OSError,ValueError):errors.append(path.name);return {}
        return read_report(path,errors,json_role=json_role)

    reports = sorted(root.glob('first-group*/**/annual-window-report.json'), key=lambda p: (p.stat().st_mtime_ns, str(p)))[-64:]
    known_source_paths={current_path,*reports}
    cells = {(province, year): {'province': province, 'year': year, 'image_available': False,
        'label_available': False, 'bands': [], 'collection_status': 'unknown', 'latest_attempt_status': 'unknown',
        'valid_pixel_ratio': None, 'quality_eligible': None, 'quality_mask_available': None,
        'label_status': 'unknown', 'label_source': None, 'label_year': None, 'mode': None,
        'source_report': None, 'latest_error': None} for province, _ in PROVINCES for year in YEARS}
    for path in reports:
        report = report_at(path,'source')
        for scene in report.get('scenes', []):
            try:
                key = (scene['aoi'], int(scene['year']))
            except (KeyError, ValueError, TypeError):
                continue
            if key not in cells:
                continue
            cell = cells[key]
            error = scene.get('error') or {}
            # 외부 오류 원문/서명 URL은 화면에 노출하지 않는다.
            cell.update(latest_attempt_status=scene.get('status', 'unknown'),
                        latest_error={'code': error.get('category'), 'http_status': error.get('http_status')} if error else None)
            image = local_file(scene.get('image_path'), root)
            label = local_file(scene.get('label_path'), root)
            if image:
                cell.update(image_available=True, label_available=bool(label), bands=scene.get('bands', []),
                    collection_status=scene.get('status', 'unknown'), valid_pixel_ratio=scene.get('label_valid_pixel_ratio', scene.get('valid_pixel_ratio')),
                    quality_eligible=None, quality_mask_available=bool(local_file(scene.get('quality_mask_path'), root)),
                    label_status=scene.get('label_status', 'unknown'), label_source=scene.get('label_source'),
                    label_year=scene.get('label_year'), mode='bounded_window', source_report=str(path.relative_to(root)))
            elif not cell['image_available']:
                cell.update(collection_status=scene.get('status', 'unknown'), label_status=scene.get('label_status', 'unknown'))
    # 품질 적격은 별도 감사가 해당 수집 보고서의 해시를 확인한 경우만 표시한다.
    for audit_name in ('quality-audit-2021.json', 'quality-audit-current.json'):
        audit_path = root / 'first-group' / audit_name
        audit = report_at(audit_path,'readiness') if audit_path.exists() else {}
        verified_reports = set()
        for entry in audit.get('inputs', []):
            path = local_file(entry.get('path'), root)
            if path and same_hash(path, entry.get('sha256'),**({'json_role':'source'} if active() is not None else {})):
                verified_reports.add(str(path.relative_to(root)))
        for row in audit.get('inventory', []):
            key = (row.get('province'), row.get('year'))
            cell = cells.get(key)
            source = local_file(row.get('manifest_path'), root)
            if cell and source and cell['source_report'] == str(source.relative_to(root)) and cell['source_report'] in verified_reports and cell['image_available']:
                cell['quality_eligible'] = row.get('eligible_patch_count', 0) > 0
                cell['label_year'] = row.get('label_year')
    attempts = sorted(root.glob('first-group*/run-result.json'), key=lambda p: (p.stat().st_mtime_ns, str(p)))
    latest_run = None
    if attempts:
        result_path = attempts[-1]
        run = report_at(result_path)
        rows = []
        for value in run.get('manifests', []):
            path = local_file(value, root)
            if path:
                known_source_paths.add(path)
                rows.extend(report_at(path,'source').get('scenes', []))
        latest_run = {key: run.get(key) for key in ('status', 'learning_ready', 'maximum_total_bytes', 'reserved_or_transferred_bytes_including_prior')}
        latest_run.update({key: run.get(key) for key in ('new_supplementary_budget_bytes',
            'new_charged_upper_bound_bytes', 'historical_charged_upper_bound_bytes',
            'combined_historical_and_new_charged_upper_bound_bytes', 'combined_maximum_charged_upper_bound_bytes')})
        latest_run.update(source_report=str(result_path.relative_to(root)),
            rate_limited_cells=sum((row.get('error') or {}).get('http_status') == 429 for row in rows),
            budget_exhausted_cells=sum('예산 소진' in str((row.get('error') or {}).get('sanitized_message', '')) for row in rows),
            no_scene_cells=sum(row.get('status') in ('no_scene', 'no_scene_found', 'no_scenes') or
                               '장면 없음' in str((row.get('error') or {}).get('sanitized_message', '')) for row in rows),
            complete_windows=sum(bool(local_file(row.get('image_path'), root)) for row in rows))
        run_error = run.get('error') or {}
        latest_run['rate_limit_active'] = bool(run.get('circuit_breaker') or run.get('stopped_for_rate_limit') or
                                              run_error.get('http_status') == 429 or latest_run['rate_limited_cells'])
        latest_run['server_http_status'] = run_error.get('http_status')
        latest_run['error_category'] = run_error.get('category')
    reference_path = root / 'raw-reference/reference-report.json'
    reference = report_at(reference_path) if reference_path.exists() else {}
    record, raster = reference.get('record', {}), reference.get('raster_metadata', {})
    file = local_file(record.get('path'), root)
    full_reference = {'band': 'B04', 'status': reference.get('status', 'unknown'),
        'file_available': bool(file), 'mode': 'full_single_band', 'bytes': file.stat().st_size if file else None,
        'width': raster.get('width'), 'height': raster.get('height'), 'crs': raster.get('crs'),
        'sha256': record.get('sha256'), 'hash_verified_now': False}
    rows = list(cells.values())
    blockers = ['충분한 패치 및 지역별 검증·시험 자료 부족', '물리 반사도 보정 검증 필요',
                '독립 참조가 없으면 WorldCover 일치도만 평가 가능']
    readiness_candidates = list((root / 'first-group').glob('readiness-*.json'))
    readiness_candidates += list((root / 'first-group').glob('training-readiness.json'))
    readiness_path = max(readiness_candidates, key=lambda p: (p.stat().st_mtime_ns, p.name)) if readiness_candidates else root / 'first-group/training-readiness.json'
    readiness = report_at(readiness_path,'readiness') if readiness_path.exists() else {}
    readiness_source = readiness_path.relative_to(root).as_posix() if readiness else None
    current_path = root / 'first-group-training-esri-v1/annual-window-report.json'
    current_manifest, current_sha = {}, None
    if current_path.exists():
        try:
            current_manifest = current()
            current_sha = current_cache[0][1][1]
        except (ProfileResourceError,SourceProfileError):
            raise
        except (OSError, ValueError):
            errors.append(current_path.name)
            current_manifest = {}
    ready = False
    integrity_status = 'not_checked'
    evidence_matched = False
    evidence = readiness.get('input_manifests', []) + readiness.get('verified_files', [])
    manifest_matches_current = not current_path.exists()
    if current_sha:
        manifest_matches_current = any(local_file(entry.get('path'), root) == current_path and
            entry.get('sha256') == current_sha for entry in readiness.get('input_manifests', []))
    # A stale manifest already fails freshness; do not hash its entire raster set.
    if manifest_matches_current and readiness.get('input_manifests') and readiness.get('verified_files'):
        try:
            def verified(entry,role):
                path=local_file(entry.get('path'),root)
                return path is not None and same_hash(path,entry.get('sha256'),**({'json_role':role} if active() is not None else {}))
            def manifest_role(entry):
                path=local_file(entry.get('path'),root)
                return 'source' if path in known_source_paths else None
            kinds={'normalization_qa':'evidence','input_image':'binary','label':'binary','quality_mask':'binary','official_product_metadata':'binary'}
            evidence_matched=all(verified(entry,manifest_role(entry)) for entry in readiness.get('input_manifests',[])) and all(verified(entry,manifest_role(entry) if entry.get('kind')=='collection_manifest' else kinds.get(entry.get('kind'))) for entry in readiness.get('verified_files',[]))
        except OSError:
            evidence_matched = False
    # 과거 입력이 아직 남아 있더라도 현재 합산 manifest를 검사한 근거가 없으면 최신 검증으로 보지 않는다.
    evidence_matched = evidence_matched and manifest_matches_current
    freshness = 'current' if evidence_matched else ('stale_or_missing' if readiness else 'missing')
    if readiness:
        integrity_status = 'matched' if evidence_matched else 'stale_or_missing'
    if readiness.get('schema_version') == 1 and readiness.get('status') == 'ready_for_weak_label_experiment' and readiness.get('ready_for_training') is True:
        ready = evidence_matched
        integrity_status = 'matched' if ready else 'stale_or_missing'
    splits = readiness.get('patch_counts_by_split') or {}
    counts_by_split = (readiness.get('class_counts_by_split') or {}) if evidence_matched else {}
    class_counts = {str(index): sum(values[index] for values in counts_by_split.values()
                    if isinstance(values, list) and len(values) == 9) for index in range(9)}
    total_pixels = sum(class_counts.values())
    patch_inventory = {'verified': evidence_matched, 'total': sum(splits.values()) if splits else None,
        'by_split': splits, 'by_class': class_counts,
        'class_names': (readiness.get('input_signature') or {}).get('class_names'),
        'label_source': (readiness.get('input_signature') or {}).get('label_source'),
        'class_ratios': {key: value / total_pixels if total_pixels else None for key, value in class_counts.items()},
        'source_report': readiness_source, 'freshness': freshness,
        'scope_note': '실험에 선택한 원본 창에서 품질 조건을 통과한 완전 256픽셀 패치 수. 격자 후보 계획 수나 혼합 RGB 재고 수가 아님.'}
    if current_sha:
        manifest_rows = current_manifest.get('scenes', [])
        eligible = [row for row in manifest_rows if row.get('quality_status') == 'quality_eligible']
        manifest_splits = {split: sum(row.get('split') == split for row in eligible) for split in ('train', 'val', 'test')}
        # 재고 개수는 현재 manifest에서 계산하고 readiness의 과거 개수를 가져오지 않는다.
        counts_match_inventory = splits == manifest_splits
        if not counts_match_inventory:
            patch_inventory.update(by_class={}, class_ratios={})
        patch_inventory.update(total=len(eligible), physical_total=len(manifest_rows), by_split=manifest_splits,
            verified=evidence_matched and counts_match_inventory, manifest_sha256=current_sha,
            source_report=current_path.relative_to(root).as_posix(), freshness='current_manifest',
            count_basis='manifest_quality_status', readiness_source_report=readiness_source,
            scope_note='현재 합산 manifest의 품질 적격 패치 재고. 파일 무결성·학습 승인 여부는 별도 최신 readiness로 판정한다.')
    if current_cache:verify_source(root,_source_selection,current_cache[0][1])
    return {'schema_version': 1, 'recorded_at': datetime.now(timezone.utc).isoformat(),
        'provinces': [{'id': key, 'name': name} for key, name in PROVINCES], 'years': YEARS, 'cells': rows,
        'summary': {'expected_cells': 36, 'available_image_cells': sum(row['image_available'] for row in rows),
            'available_label_cells': sum(row['label_available'] for row in rows),
            'quality_eligible_cells': sum(row['quality_eligible'] is True for row in rows),
            'learning_ready': ready, 'readiness_basis': '학습 전 검사 및 입력 해시 일치' if ready else '정식 데이터셋 구축·학습 gate 통과 기록 없음 또는 입력 변경'},
        'training_readiness': {'status': readiness.get('status', 'unknown'), 'integrity_status': integrity_status,
            'source_report': readiness_source, 'freshness': freshness,
            'manifest_matches_current': manifest_matches_current, 'evidence_matched': evidence_matched,
            'current_manifest_sha256': current_sha,
            'ready_for_training': ready, 'blockers': readiness.get('blockers', []),
            'patch_counts_by_split': readiness.get('patch_counts_by_split'),
            'input_signature': readiness.get('input_signature'),
            'required_bands': (readiness.get('policy') or {}).get('band_names'),
            'minimum_patches': (readiness.get('policy') or {}).get('min_patches'),
            'evaluation_kind': readiness.get('evaluation_kind'), 'scientific_accuracy_validated': False},
        'latest_run': latest_run, 'full_reference': full_reference, 'blocked_reasons': blockers,
        'patch_inventory': patch_inventory,
        'collection_targets': collection_targets(current_manifest, current_sha, bare_target_review(root, current_sha)),
        'candidate_quality': candidate_quality(root, current_sha, same_hash),
        'limitations': ['실제 파일 존재와 독립 정확도 검증을 구분', '예약 예산은 실제 수신량이 아님',
                        '부분 창을 주 전체나 전체 장면 확보로 계산하지 않음'],
        'unreadable_reports': errors}
