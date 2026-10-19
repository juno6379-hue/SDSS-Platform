"""GMAIS 원문 Dataset Manifest의 불변 버전 등록 코어. 운영 승인을 부여하지 않는다."""
import hashlib
import json
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from .sdss_results import asset_sha256, local_asset
from .store import now


@lru_cache(maxsize=1)
def manifest_validator():
    path = Path(__file__).resolve().parents[2] / 'contracts/upstream/GMAIS-v0.2/schemas/dataset-manifest.schema.json'
    return Draft202012Validator(json.loads(path.read_text(encoding='utf-8')), format_checker=FormatChecker())


def version_key(dataset_id, version):
    if (not isinstance(dataset_id, str) or not dataset_id.strip() or not isinstance(version, str)
            or not version.strip() or version.strip().lower() in {'latest', 'current'}):
        raise ValueError('고정된 dataset_id와 version이 필요합니다.')
    return hashlib.sha256(json.dumps([dataset_id, version], ensure_ascii=False).encode()).hexdigest()


def canonical_manifest(manifest):
    """호출자가 원본 dict를 바꾸어 등록 내용을 바꿀 수 없도록 snapshot을 만든다."""
    encoded = json.dumps(manifest, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':'))
    snapshot = json.loads(encoded)
    errors = list(manifest_validator().iter_errors(snapshot))
    if errors:
        raise ValueError('GMAIS Dataset Manifest schema 위반: ' + errors[0].message)
    version_key(snapshot['dataset_id'], snapshot['version'])
    bbox = snapshot['spatial']['bbox']
    if not (bbox[0] < bbox[2] and bbox[1] < bbox[3]):
        raise ValueError('공간 범위의 최소값과 최대값 순서가 잘못됐습니다.')
    if snapshot['spatial']['crs'] in {'EPSG:4326', 'OGC:CRS84'} and not (-180 <= bbox[0] < bbox[2] <= 180 and -90 <= bbox[1] < bbox[3] <= 90):
        raise ValueError('경도·위도 공간 범위가 올바르지 않습니다.')
    start = datetime.fromisoformat(snapshot['temporal']['start'].replace('Z', '+00:00'))
    end = datetime.fromisoformat(snapshot['temporal']['end'].replace('Z', '+00:00'))
    if start > end:
        raise ValueError('자료 시작 시각이 종료 시각보다 늦습니다.')
    for ref in snapshot['lineage']:
        version_key(ref['id'], ref['version'])
    return snapshot, hashlib.sha256(encoded.encode()).hexdigest()


def verify_artifact(root, manifest):
    path = local_asset(root, manifest['artifact_uri'])
    if asset_sha256(path) != manifest['sha256']:
        raise ValueError('자료 자산 SHA-256이 manifest와 다릅니다.')
    # VALIDATED는 품질 기록이며 독립 과학검증·모델 배포 승인을 뜻하지 않는다.
    if manifest['quality_status'] == 'VALIDATED':
        if not manifest.get('quality_report_ref'):
            raise ValueError('VALIDATED 자료에는 실제 품질 보고서 참조가 필요합니다.')
        local_asset(root, manifest['quality_report_ref'])


def register_version(store, manifest):
    snapshot, digest = canonical_manifest(manifest)
    verify_artifact(store.root, snapshot)
    key = version_key(snapshot['dataset_id'], snapshot['version'])
    record = {'id': key, 'manifest': snapshot, 'manifest_sha256': digest, 'registered_at': now(),
              'scientific_accuracy_validated': False, 'deployment_approval': False}
    with store.connect() as connection:
        # 동일 버전의 동시 등록도 INSERT OR REPLACE로 덮어쓰지 않는다.
        connection.execute('BEGIN IMMEDIATE')
        old = connection.execute('SELECT body FROM records WHERE kind=? AND id=?', ('dataset_versions', key)).fetchone()
        if old:
            previous = json.loads(old[0])
            if previous['manifest_sha256'] != digest or previous['manifest'] != snapshot:
                raise ValueError('기존 dataset_id/version의 내용을 변경할 수 없습니다. 새 버전을 등록하세요.')
            return previous
        connection.execute('INSERT INTO records VALUES(?,?,?)', ('dataset_versions', key, json.dumps(record, ensure_ascii=False, allow_nan=False)))
    return record


def resolve_version(store, dataset_id, version, sha256):
    """고정 참조와 실제 자산을 다시 확인한다. 원격 fetch나 실행 승인으로 확대하지 않는다."""
    key = version_key(dataset_id, version)
    record = store.get('dataset_versions', key)
    snapshot, digest = canonical_manifest(record['manifest'])
    if (record['id'] != key or snapshot['dataset_id'] != dataset_id or snapshot['version'] != version
            or digest != record['manifest_sha256'] or snapshot['sha256'] != sha256):
        raise ValueError('자료 버전 또는 manifest/자산 해시가 요청과 다릅니다.')
    verify_artifact(store.root, snapshot)
    return record
