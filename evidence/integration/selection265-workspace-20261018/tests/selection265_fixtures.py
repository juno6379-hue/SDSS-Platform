"""시험 전용 원바이트 비교 코드. 외부 workspace/baseline fallback은 없다."""
import hashlib
import json
from pathlib import Path
import types

MANIFEST_SHA256 = 'b0398658098475f9788a11d9a8f7fa9cbc6c077847e8f896b513bf0aa39d0163'
FIXTURES = Path(__file__).resolve().parent/'fixtures/selection265'


def _read(path, maximum, expected_size=None):
    try:
        before = path.stat()
        if path.is_symlink() or not path.is_file() or before.st_size > maximum:
            raise ValueError()
        with path.open('rb') as stream:
            raw = stream.read(maximum+1)
        after = path.stat()
        if (len(raw) > maximum or len(raw) != before.st_size or
            (expected_size is not None and len(raw) != expected_size) or
            (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns) !=
            (after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns)):
            raise ValueError()
        return raw
    except (OSError, ValueError):
        raise ValueError('SELECTION265_FIXTURE_INVALID') from None


def load_legacy(role, *, fixture_root=None):
    if role not in ('guard','collector'):
        raise ValueError('SELECTION265_FIXTURE_ROLE_INVALID')
    root = FIXTURES if fixture_root is None else Path(fixture_root)
    raw = _read(root/'manifest.json', 65536, 299)
    if hashlib.sha256(raw).hexdigest() != MANIFEST_SHA256:
        raise ValueError('SELECTION265_FIXTURE_MANIFEST_MISMATCH')
    metadata = json.loads(raw)['roles'][role]
    code = _read(root/metadata['filename'], 65536, metadata['bytes'])
    if hashlib.sha256(code).hexdigest() != metadata['sha256']:
        raise ValueError('SELECTION265_FIXTURE_SHA_MISMATCH')
    name = 'app.data._selection265_legacy_guard' if role == 'guard' else '_selection265_legacy_collector'
    module = types.ModuleType(name)
    module.__file__ = str(root/metadata['filename'])
    module.__package__ = name.rpartition('.')[0]
    # SHA 검증한 동일 bytes를 실행한다. loader가 파일을 다시 여는 경로는 없다.
    exec(compile(code, module.__file__, 'exec'), module.__dict__)
    return module
