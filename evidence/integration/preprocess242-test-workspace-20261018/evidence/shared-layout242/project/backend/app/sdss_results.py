"""표준 Result를 검증된 로컬 SDSS 자산으로 투영하는 읽기 전용 RFC 어댑터."""
from functools import lru_cache
import hashlib
import json
from pathlib import Path, PureWindowsPath
from tempfile import SpooledTemporaryFile
from urllib.parse import quote, urlsplit

from jsonschema import Draft202012Validator, FormatChecker


@lru_cache(maxsize=1)
def result_validator():
    # backend 디렉터리 밖에 보존된 원문 계약을 사용한다.
    schema_path = Path(__file__).resolve().parents[2] / 'contracts/upstream/GMAIS-v0.2/schemas/result-manifest.schema.json'
    return Draft202012Validator(json.loads(schema_path.read_text(encoding='utf-8')), format_checker=FormatChecker())


def local_asset(root, uri):
    """원격 URL·경로 탈출을 차단하며 로컬 파일만 검증한다."""
    if (not isinstance(uri, str) or urlsplit(uri).scheme or urlsplit(uri).netloc
            or PureWindowsPath(uri).anchor or Path(uri).is_absolute() or '?' in uri or '#' in uri):
        raise ValueError('로컬 데이터 경로만 지원합니다.')
    path = (Path(root) / uri).resolve()
    if not path.is_relative_to(Path(root).resolve()) or not path.is_file():
        raise ValueError('데이터 루트 안의 자산 파일을 찾을 수 없습니다.')
    return path


def asset_sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def project_result(store, result_id, result=None):
    result = store.get('gmais_results', result_id) if result is None else result
    # Store의 저장용 필드는 원문 Result schema에 포함하지 않는다.
    manifest = {key: value for key, value in result.items() if key not in ('id', 'created_at')}
    response = {
        'extension': {'id': 'greenblue.sdss-result.rfc1', 'approval_status': 'INTERNAL_REVIEW',
                      'present_in_upstream_openapi': False},
        'result_id': result_id, 'job_id': manifest.get('job_id'),
        'trace_id': manifest.get('provenance', {}).get('trace_id') if isinstance(manifest.get('provenance'), dict) else None,
        'status': manifest.get('status'), 'publishable': False,
        'blockers': [], 'layers': [], 'reports': [], 'assets': [],
    }

    def block(code, message):
        response['blockers'].append({'code': code, 'message': message})

    if list(result_validator().iter_errors(manifest)):
        block('SCHEMA_MISMATCH', 'Result manifest가 GMAIS v0.2 계약과 일치하지 않습니다.')
        return response
    if manifest['result_id'] != result_id:
        block('IDENTITY_MISMATCH', '저장 식별자와 Result 식별자가 다릅니다.')
    try:
        job = store.get('gmais_jobs', manifest['job_id'])
    except KeyError:
        block('JOB_NOT_FOUND', 'Result의 원본 Job이 없습니다.')
        return response
    status, request = job.get('status', {}), job.get('request', {})
    if (job.get('result_id') != result_id or status.get('job_id') != manifest['job_id']
            or status.get('agent_id') != manifest['agent_id']
            or status.get('trace_id') != response['trace_id']
            or (request.get('execution_context') or {}).get('trace_id') != response['trace_id']):
        block('IDENTITY_MISMATCH', 'Job·Agent·Result·Trace 연결이 일치하지 않습니다.')
    if status.get('status') != 'SUCCEEDED':
        block('JOB_NOT_SUCCEEDED', '성공한 Job만 결과를 게시할 수 있습니다.')
    def identities(refs):
        return sorted((ref.get('id'), ref.get('version'), ref.get('sha256')) for ref in refs)
    if (not manifest['input_refs'] or identities(manifest['input_refs']) != identities(request.get('input_refs', []))
            or not manifest.get('model_ref') or manifest.get('model_ref') != request.get('model_ref')):
        block('LINEAGE_MISMATCH', '고정 데이터·모델 버전과 해시가 원본 요청에 일치해야 합니다.')
    if manifest['status'] != 'SCIENTIFIC_VALIDATED' or manifest['validation']['validation_level'] != 'INDEPENDENT_SCIENTIFIC':
        block('SCIENCE_NOT_VALIDATED', '독립 과학 검증이 확인되지 않은 결과는 게시하지 않습니다.')
    bbox = manifest['spatial']['bbox']
    if not (bbox[0] < bbox[2] and bbox[1] < bbox[3]):
        block('INVALID_SPATIAL', 'Result 공간 범위가 올바르지 않습니다.')
    if not manifest['output_assets']:
        block('ASSET_MISSING', '게시할 자산이 없습니다.')
    assets = []
    for index, asset in enumerate(manifest['output_assets']):
        try:
            path = local_asset(store.root, asset['uri'])
            if asset_sha256(path) != asset['sha256']:
                block('HASH_MISMATCH', f'자산 {index}의 SHA-256이 다릅니다.')
                continue
        except (ValueError, OSError):
            block('ASSET_UNAVAILABLE', f'자산 {index}의 로컬 파일을 검증할 수 없습니다.')
            continue
        assets.append({'index': index, 'type': asset['type'], 'sha256': asset['sha256'],
                       'href': f'/v1/results/{quote(result_id, safe="")}/assets/{index}',
                       'units': asset.get('units'), 'verified': True})
    if response['blockers']:
        return response
    response['publishable'] = True
    response['assets'] = assets
    response['layers'] = [dict(asset, spatial=manifest['spatial']) for asset in assets if asset['type'] in ('GeoJSON', 'COG')]
    response['reports'] = [asset for asset in assets if asset['type'] in ('JSON', 'PDF', 'CSV')]
    return response


def download_snapshot(store, result_id, asset_index):
    """한 manifest snapshot에서 고른 바이트를 복사·검증하고 그 복사본만 제공한다."""
    result = store.get('gmais_results', result_id)
    projection = project_result(store, result_id, result=result)
    if not projection['publishable']:
        return projection, None, None
    assets = result['output_assets']
    if asset_index < 0 or asset_index >= len(assets):
        raise IndexError('자산 번호가 없습니다.')
    asset = assets[asset_index]
    path = local_asset(store.root, asset['uri'])
    snapshot = SpooledTemporaryFile(max_size=8 * 1024 * 1024)
    try:
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                snapshot.write(chunk)
                digest.update(chunk)
        if digest.hexdigest() != asset['sha256']:
            raise ValueError('자산 내용이 검증 도중 변경되었습니다.')
        snapshot.seek(0)
        return projection, snapshot, path.name
    except Exception:
        snapshot.close()
        raise
