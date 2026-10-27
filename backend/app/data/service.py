"""공개 카탈로그 검색, 검증된 다운로드, 수동 래스터 등록.

네트워크 성공과 계획 생성을 구분한다. 인증 토큰은 manifest에 기록하지 않는다.
"""
from __future__ import annotations

import hashlib
import io
import importlib
import json
import math
import os
from pathlib import Path
import re
import time
import threading
from http.client import IncompleteRead
from datetime import date, datetime, timezone
from urllib.parse import urlsplit, urlunsplit, parse_qs
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError, URLError

STAC_URL = "https://earth-search.aws.element84.com/v1/search"
PC_STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
STAC_ENDPOINTS = {"earth-search": STAC_URL, "planetary-computer": PC_STAC_URL}
PC_ASSET_HOSTS = {"sentinel2l2a01.blob.core.windows.net", "sentinel2l2a02.blob.core.windows.net",
                  "landsateuwest.blob.core.windows.net"}
COLLECTIONS = {"sentinel-2-l2a", "landsat-c2-l2"}
DOWNLOAD_HOSTS = {
    "earth-search.aws.element84.com", "sentinel-cogs.s3.us-west-2.amazonaws.com",
    "sentinel-cogs.s3.amazonaws.com", "earthsearch-data.s3.amazonaws.com",
    "earthsearch-data.s3.us-west-2.amazonaws.com", "landsatlook.usgs.gov",
    "esa-worldcover.s3.eu-central-1.amazonaws.com",
    "planetarycomputer.microsoft.com",
    # Esri 공식 Explorer의 공개 v003 COG. SAS/계정이 필요 없는 제품 전용 호스트.
    "lulctimeseries.blob.core.windows.net",
}
DOWNLOAD_HOSTS.update(PC_ASSET_HOSTS)
DEFAULT_MAX_BYTES = 512 * 1024 * 1024
HARD_MAX_BYTES = 2 * 1024 * 1024 * 1024
_PC_TOKEN_CACHE = {}
_PC_TOKEN_LOCK = threading.Lock()
_REQUEST_LOCK = threading.Lock()
_REQUEST_INTERVAL = 0.0
_LAST_REQUEST_AT = 0.0
_METADATA_CONTEXT = threading.local()
_REQUEST_CIRCUIT = None
_REQUEST_CIRCUIT_REASON = None
_CIRCUIT_LOCK = threading.Lock()
RANGE_MEASUREMENT_SCOPE = "Python이 실제 읽은 COG Range 응답 본문; SAS JSON/HEAD/오류본문/TLS overhead 제외"


class AssetTransferError(RuntimeError):
    """측정 가능한 실패와 측정 불가능한 중단의 전송 예산을 구분한다."""
    def __init__(self, stage, http_body_bytes, measurement_known):
        super().__init__(f"원격 자산 처리 실패(stage={stage}); 원인은 exception chain을 확인하세요")
        self.stage = stage
        self.http_body_bytes = http_body_bytes if measurement_known else None
        self.transfer_measurement_known = measurement_known
        self.measurement_scope = RANGE_MEASUREMENT_SCOPE


class SharedCollectionStop(RuntimeError):
    """다른worker가연공유회로.새HTTP429응답을받았다고표시하지않는다."""
    def __init__(self, reason):
        super().__init__("수집 공유 중단 회로가 열려 새 HTTP 요청을 보내지 않았습니다")
        self.shared_collection_stop = True
        self.shared_reason = reason


def _number(value, name, lower, upper):
    if isinstance(value, bool):
        raise ValueError(f"{name}: 숫자가 필요합니다")
    try:
        result = float(value)
    except (ValueError, TypeError):
        raise ValueError(f"{name}: 숫자가 필요합니다") from None
    if not math.isfinite(result) or not lower <= result <= upper:
        raise ValueError(f"{name}: {lower}~{upper} 범위여야 합니다")
    return result


def _integer(value, name, lower, upper):
    result = _number(value, name, lower, upper)
    if result != int(result):
        raise ValueError(f"{name}: 정수가 필요합니다")
    return int(result)


def _bbox(payload):
    raw = payload.get("bbox")
    if not isinstance(raw, (list, tuple)) or len(raw) != 4:
        raise ValueError("bbox는 WGS84 [west, south, east, north] 4개 좌표입니다")
    w, s, e, n = [_number(v, "bbox", -180 if i % 2 == 0 else -90,
                         180 if i % 2 == 0 else 90) for i, v in enumerate(raw)]
    if w >= e or s >= n:
        raise ValueError("bbox의 최소값은 최대값보다 작아야 합니다; 날짜변경선 AOI는 분할하세요")
    return [w, s, e, n]


def _dates(payload):
    try:
        start = date.fromisoformat(payload["start_date"])
        end = date.fromisoformat(payload["end_date"])
    except (KeyError, ValueError, TypeError):
        raise ValueError("start_date/end_date에 YYYY-MM-DD 날짜가 필요합니다") from None
    if start > end:
        raise ValueError("start_date는 end_date 이후일 수 없습니다")
    return start.isoformat(), end.isoformat()


def _safe_url(url):
    if not isinstance(url, str):
        raise ValueError("HTTPS URL이 필요합니다")
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or parsed.hostname not in DOWNLOAD_HOSTS
            or parsed.username or parsed.password or parsed.port not in (None, 443)
            or parsed.fragment):
        raise ValueError("허용된 공개 데이터 호스트의 HTTPS URL만 사용할 수 있습니다")
    return url


class _SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # 리다이렉트도 동일 허용목록을 적용하여 내부망 접근을 차단한다.
        _safe_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _open(request):
    global _LAST_REQUEST_AT
    with _REQUEST_LOCK:
        if _REQUEST_CIRCUIT is not None and _REQUEST_CIRCUIT.is_set():
            raise SharedCollectionStop(request_circuit_status())
        delay = _REQUEST_INTERVAL - (time.monotonic() - _LAST_REQUEST_AT)
        if delay > 0:
            if _REQUEST_CIRCUIT is None:
                time.sleep(delay)
            else:
                _REQUEST_CIRCUIT.wait(delay)
        # 대기중 다른worker가429를관찰했으면대기열요청도차단한다.
        if _REQUEST_CIRCUIT is not None and _REQUEST_CIRCUIT.is_set():
            raise SharedCollectionStop(request_circuit_status())
        _LAST_REQUEST_AT = time.monotonic()
    try:
        return build_opener(_SafeRedirect()).open(request, timeout=45)
    except HTTPError as exc:
        if exc.code == 429 and _REQUEST_CIRCUIT is not None:
            global _REQUEST_CIRCUIT_REASON
            with _CIRCUIT_LOCK:
                if _REQUEST_CIRCUIT_REASON is None:
                    parsed = urlsplit(exc.url or request.full_url)
                    _REQUEST_CIRCUIT_REASON = {"reason": "provider_http_429", "http_status": 429,
                        "request_host": parsed.hostname, "request_path": parsed.path,
                        "retry_after": str((exc.headers or {}).get("Retry-After", ""))[:120]}
                _REQUEST_CIRCUIT.set()
        raise


def configure_request_circuit(event=None):
    global _REQUEST_CIRCUIT, _REQUEST_CIRCUIT_REASON
    with _CIRCUIT_LOCK:
        _REQUEST_CIRCUIT, _REQUEST_CIRCUIT_REASON = event, None


def request_circuit_status():
    with _CIRCUIT_LOCK:
        return dict(_REQUEST_CIRCUIT_REASON) if _REQUEST_CIRCUIT_REASON else None


def configure_request_spacing(seconds=0):
    global _REQUEST_INTERVAL
    _REQUEST_INTERVAL = _number(seconds, "request_interval_seconds", 0, 10)


def configure_metadata_budget(max_bytes=None):
    maximum = None if max_bytes is None else _integer(max_bytes, "metadata_budget_bytes", 1, 8 * 1024 ** 2)
    _METADATA_CONTEXT.value = {"maximum_bytes": maximum, "charged_bytes": 0, "read_body_bytes": 0}


def metadata_budget_status():
    if not hasattr(_METADATA_CONTEXT, "value"):
        configure_metadata_budget(None)
    return _METADATA_CONTEXT.value.copy()


def _metadata_response(request):
    metadata_budget_status()
    budget = _METADATA_CONTEXT.value
    maximum = 8 * 1024 * 1024
    if budget["maximum_bytes"] is not None:
        maximum = min(maximum, budget["maximum_bytes"] - budget["charged_bytes"])
        if maximum <= 0:
            raise RuntimeError("메타데이터 응답 본문 예산 소진")
    reservation = maximum if budget["maximum_bytes"] is not None else 0
    budget["charged_bytes"] += reservation
    measured = 0
    try:
        with _open(request) as response:
            length = response.headers.get("Content-Length")
            if length is not None and int(length) > maximum:
                raise RuntimeError("메타데이터 응답 본문 크기 제한 초과")
            try:
                raw = response.read(maximum)
                measured = len(raw)
            except IncompleteRead as exc:
                measured = len(exc.partial)
                raise
            except Exception:
                measured = None
                raise
    finally:
        if measured is not None:
            budget["charged_bytes"] += measured - reservation
            budget["read_body_bytes"] += measured
    return raw


def _json_response(request):
    return json.loads(_metadata_response(request))


def stac_endpoint(value="earth-search"):
    if value in STAC_ENDPOINTS:
        return STAC_ENDPOINTS[value]
    if isinstance(value, str):
        normalized = value.rstrip("/")
        for endpoint in STAC_ENDPOINTS.values():
            if normalized in (endpoint, endpoint.removesuffix("/search")):
                return endpoint
    raise ValueError("endpoint는 earth-search 또는 planetary-computer 고정 카탈로그여야 합니다")


def resolve_asset_url(url):
    """공식 container-token을 만료 전까지 메모리에 캐시한다. 토큰은 기록하지 않는다."""
    _safe_url(url)
    parsed = urlsplit(url)
    if parsed.hostname not in PC_ASSET_HOSTS or parsed.query:
        return url
    container = parsed.path.lstrip("/").split("/", 1)[0]
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,61}[a-z0-9]", container):
        raise ValueError("PC 자산 컨테이너 이름이 올바르지 않습니다")
    key = (parsed.hostname, container)
    with _PC_TOKEN_LOCK:
        now = datetime.now(timezone.utc).timestamp()
        cached = _PC_TOKEN_CACHE.get(key)
        if cached is None or cached["expires_at"] <= now + 120:
            account = parsed.hostname.split(".", 1)[0]
            endpoint = f"https://planetarycomputer.microsoft.com/api/sas/v1/token/{account}/{container}"
            result = _json_response(Request(endpoint))
            if not isinstance(result.get("token"), str) or not isinstance(result.get("msft:expiry"), str):
                raise RuntimeError("PC container-token 응답 형식이 올바르지 않습니다")
            token = result["token"].lstrip("?")
            try:
                expiry = datetime.fromisoformat(result["msft:expiry"].replace("Z", "+00:00"))
                if expiry.tzinfo is None or expiry.timestamp() <= now + 120 or "sig" not in parse_qs(token):
                    raise ValueError("만료되거나 서명이 없는 SAS 토큰")
            except (KeyError, ValueError, TypeError):
                raise RuntimeError("PC container-token 응답의 만료/서명을 확인할 수 없습니다") from None
            cached = {"token": token, "expires_at": expiry.timestamp()}
            _PC_TOKEN_CACHE[key] = cached
        return _safe_url(urlunsplit((parsed.scheme, parsed.netloc, parsed.path, cached["token"], "")))


class HTTPRangeReader(io.RawIOBase):
    """urllib 기반 COG 읽기. 실제 전송된 본문 합계를 제한하고 Range 미지원은 거부한다."""
    def __init__(self, url, max_transfer_bytes=32 * 1024 * 1024, block_size=65536):
        self.url = _safe_url(url)
        self.limit = max_transfer_bytes
        self.transferred = 0
        self.measurement_known = True
        self.last_error = None
        self.position = 0
        self.block_size = block_size
        self.cache = {}
        with _open(Request(url, method="HEAD", headers={"Cache-Control": "no-cache", "Pragma": "no-cache"})) as response:
            self.size = int(response.headers["Content-Length"])
            self.etag = response.headers.get("ETag")

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset, whence=0):
        target = offset if whence == 0 else self.position + offset if whence == 1 else self.size + offset
        if target < 0:
            raise ValueError("음수 파일 위치")
        self.position = target
        return target

    def read(self, size=-1):
        available = max(0, self.size - self.position)
        size = available if size < 0 else min(size, available)
        if size == 0:
            return b""
        start_position = self.position
        blocks = list(range(start_position // self.block_size, (start_position + size - 1) // self.block_size + 1))
        missing = [block for block in blocks if block not in self.cache]
        if missing:
            start = missing[0] * self.block_size
            end = min(self.size, (missing[-1] + 1) * self.block_size) - 1
            try:
                content = self._fetch(start, end)
            except Exception as exc:
                # GDAL이 Python 콜백 예외를 CPL오류로 감싸도 원래HTTP429를 보존한다.
                self.last_error = exc
                raise
            for block in range(missing[0], missing[-1] + 1):
                local = block * self.block_size - start
                self.cache[block] = content[local:local + self.block_size]
        content = b"".join(self.cache[block] for block in blocks)
        offset = start_position % self.block_size
        self.position += size
        return content[offset:offset + size]

    def _fetch(self, start, end):
        size = end - start + 1
        if self.transferred + size > self.limit:
            raise ValueError("COG 부분읽기 누적 전송량 제한 초과")
        headers = {"Range": f"bytes={start}-{end}", "Accept-Encoding": "identity",
                   "Cache-Control": "no-cache", "Pragma": "no-cache"}
        if self.etag:
            headers["If-Match"] = self.etag
        with _open(Request(self.url, headers=headers)) as response:
            if response.status != 206:
                raise RuntimeError("원격 자산이 HTTP Range 요청을 지원하지 않습니다")
            expected = f"bytes {start}-{end}/{self.size}"
            actual = response.headers.get("Content-Range")
            if actual != expected:
                raise RuntimeError(f"COG Range 응답 범위 불일치: expected={expected!r}; actual={str(actual)[:160]!r}; status={response.status}")
            try:
                content = response.read(size)
            except IncompleteRead as exc:
                self.transferred += len(exc.partial)
                raise
            except Exception:
                # 내부 버퍼에서 읽고 반환하지 못한 바이트를 정확히 모르면 예약을 유지한다.
                self.measurement_known = False
                raise
        self.transferred += len(content)
        if len(content) != size:
            raise RuntimeError("COG Range 응답 길이 불일치")
        return content


def read_cog_window(url, bbox, side=256, max_transfer_bytes=32 * 1024 * 1024, window_guard=None):
    """WGS84 중심점 주변 실제 원본 해상도 창. GDAL 네트워크 대신 검증된 urllib 사용."""
    holder = {"stage": "validation_and_dependencies"}
    try:
        if window_guard is None:
            return _read_cog_window_impl(url, bbox, side, max_transfer_bytes, holder)
        return _read_cog_window_impl(url, bbox, side, max_transfer_bytes, holder, window_guard=window_guard)
    except Exception as exc:
        reader = holder.get("reader")
        known = reader.measurement_known if reader is not None else True
        count = reader.transferred if reader is not None else 0
        cause = getattr(reader, "last_error", None) or exc
        raise AssetTransferError(holder["stage"], count, known) from cause


def read_cog_full_tile(url, max_transfer_bytes=64 * 1024 * 1024, max_side=8192):
    """Read one complete, bounded single-band COG for a guarded full-tile pilot."""
    holder = {"stage": "validation_and_dependencies"}
    try:
        return _read_cog_full_tile_impl(url, max_transfer_bytes, max_side, holder)
    except Exception as exc:
        reader = holder.get("reader")
        known = reader.measurement_known if reader is not None else True
        count = reader.transferred if reader is not None else 0
        cause = getattr(reader, "last_error", None) or exc
        raise AssetTransferError(holder["stage"], count, known) from cause


def _read_cog_full_tile_impl(url, max_transfer_bytes, max_side, holder):
    import rasterio
    max_transfer_bytes = _integer(max_transfer_bytes, "max_transfer_bytes", 1, HARD_MAX_BYTES)
    max_side = _integer(max_side, "max_side", 1, 8192)
    holder["stage"] = "sas_token"
    signed = resolve_asset_url(url)
    holder["stage"] = "head_metadata"
    reader = HTTPRangeReader(signed, max_transfer_bytes)
    holder["reader"] = reader
    holder["stage"] = "range_raster_read"

    def opener(path, mode="r"):
        if path != signed:
            raise FileNotFoundError("요청하지 않은 COG 보조파일")
        return reader

    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"):
        with rasterio.open(signed, opener=opener) as src:
            if src.count != 1 or src.crs is None:
                raise ValueError("전체 타일은 CRS가 있는 단일 band COG여야 합니다")
            if src.width > max_side or src.height > max_side:
                raise ValueError("전체 타일 크기 상한 초과")
            pixels = src.read()
            if pixels.shape != (1, src.height, src.width):
                raise ValueError("전체 타일 읽기 크기 불일치")
            profile = src.profile.copy()
            profile.update(width=src.width, height=src.height, driver="GTiff")
    return pixels, profile, {
        "http_body_bytes": reader.transferred,
        "source_content_length_bytes": reader.size,
        "max_http_body_bytes": reader.limit,
        "measurement_scope": RANGE_MEASUREMENT_SCOPE,
        "transfer_measurement_known": True,
        "full_tile": True,
    }


def _read_cog_window_impl(url, bbox, side, max_transfer_bytes, holder, window_guard=None):
    import rasterio
    from rasterio.warp import transform
    from rasterio.windows import Window
    # 대량 패치는 1024 기준창을 한 번 읽고 로컬에서 나눈다. 라벨은 CRS 차이를
    # 감안하여 최대 2048 원본 픽셀까지만 읽도록 별도의 상한을 유지한다.
    side = _integer(side, "window_size", 1, 2048)
    bbox = _bbox({"bbox": bbox})
    holder["stage"] = "sas_token"
    signed = resolve_asset_url(url)
    holder["stage"] = "head_metadata"
    reader = HTTPRangeReader(signed, max_transfer_bytes)
    holder["reader"] = reader
    holder["stage"] = "range_raster_read"
    def opener(path, mode="r"):
        if path != signed:
            raise FileNotFoundError("요청하지 않은 COG 보조파일")
        return reader
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"):
        with rasterio.open(signed, opener=opener) as src:
            x, y = transform("EPSG:4326", src.crs, [(bbox[0] + bbox[2]) / 2], [(bbox[1] + bbox[3]) / 2])
            row, col = src.index(x[0], y[0])
            if not 0 <= row < src.height or not 0 <= col < src.width:
                raise ValueError("AOI 중심점이 COG 범위 밖입니다")
            left, top = max(0, col - side // 2), max(0, row - side // 2)
            window = Window(left, top, min(side, src.width - left), min(side, src.height - top))
            if window_guard is not None:
                # Header ranges may have transferred; pixel data have not been
                # requested by src.read. Do not attach signed URL to this record.
                holder["stage"] = "window_geometry_guard"
                window_guard({"schema_version": 1, "crs": src.crs.to_string() if src.crs else None,
                    "source_bounds": list(src.bounds), "source_transform": list(src.transform)[:6],
                    "source_width": src.width, "source_height": src.height,
                    "requested_bbox_wgs84": list(bbox), "requested_side": side,
                    "window": {"col_off": window.col_off, "row_off": window.row_off,
                               "width": window.width, "height": window.height},
                    "window_transform": list(src.window_transform(window))[:6],
                    "window_width": int(window.width), "window_height": int(window.height)})
                holder["stage"] = "range_raster_read"
            pixels = src.read(window=window)
            profile = src.profile.copy()
            profile.update(width=pixels.shape[2], height=pixels.shape[1], transform=src.window_transform(window), driver="GTiff")
            for field in ("blockxsize", "blockysize", "tiled"):
                profile.pop(field, None)
    return pixels, profile, {"http_body_bytes": reader.transferred, "max_http_body_bytes": reader.limit,
                            "measurement_scope": RANGE_MEASUREMENT_SCOPE, "transfer_measurement_known": True}


def search_stac(payload: dict) -> dict:
    endpoint = stac_endpoint(payload.get("endpoint", "earth-search"))
    bbox = _bbox(payload)
    start, end = _dates(payload)
    collection = payload.get("collection", "sentinel-2-l2a")
    if collection not in COLLECTIONS:
        raise ValueError("지원 collection: sentinel-2-l2a, landsat-c2-l2")
    cloud = _number(payload.get("cloud_cover", 30), "cloud_cover", 0, 100)
    limit = _integer(payload.get("limit", 10), "limit", 1, 100)
    query = {"collections": [collection], "bbox": bbox, "limit": limit,
             "datetime": f"{start}T00:00:00Z/{end}T23:59:59Z",
             "query": {"eo:cloud_cover": {"lte": cloud}}}
    if payload.get("sort_by_cloud", False):
        query["sortby"] = [{"field": "properties.eo:cloud_cover", "direction": "asc"}]
    try:
        result = _json_response(Request(endpoint, data=json.dumps(query).encode(),
                                       headers={"Content-Type": "application/json", "Cache-Control": "no-cache", "Pragma": "no-cache"}))
    except (OSError, ValueError) as exc:
        raise RuntimeError(f"STAC 검색 실패: {type(exc).__name__}") from exc
    items, rejected = [], []
    for feature in result.get("features", [])[:limit]:
        props = feature.get("properties", {})
        # 원격 query 지원 여부를 가정하지 않고 실제 응답값도 요청 조건과 대조한다.
        try:
            if not isinstance(props.get("eo:cloud_cover"), (int, float)):
                raise ValueError("STAC cloud cover는 JSON 숫자여야 합니다")
            actual_cloud = _number(props.get("eo:cloud_cover"), "eo:cloud_cover", 0, 100)
        except ValueError:
            rejected.append({"id": str(feature.get("id", ""))[:120], "reason": "missing_or_invalid_cloud_cover"})
            continue
        if actual_cloud > cloud:
            rejected.append({"id": str(feature.get("id", ""))[:120], "reason": "cloud_cover_above_requested_maximum", "cloud_cover": actual_cloud})
            continue
        assets = {}
        for key, asset in feature.get("assets", {}).items():
            href = asset.get("href", "")
            # 카탈로그에 있는 모든 보조파일 대신 실제 래스터 자산을 노출한다.
            if "tiff" in asset.get("type", "").lower() or urlsplit(href).path.lower().endswith((".tif", ".tiff")):
                assets[key] = {"href": href, "type": asset.get("type"),
                               "roles": asset.get("roles", []), "title": asset.get("title", key),
                               "raster:bands": asset.get("raster:bands"), "eo:bands": asset.get("eo:bands")}
        items.append({"id": feature.get("id"), "collection": collection,
                      "bbox": feature.get("bbox"), "datetime": props.get("datetime"),
                      "cloud_cover": actual_cloud,
                      "properties": props,
                      "license": feature.get("license", props.get("license", "SEE_COLLECTION_TERMS")),
                      "assets": assets, "geometry": feature.get("geometry")})
        if payload.get("include_raw") is True:
            items[-1]["stac_feature"] = feature
    return {"status": "searched", "source": endpoint, "query": query,
            "items": items, "count": len(items), "filtered_count": len(rejected), "filtered_items": rejected,
            "cloud_cover_response_verified": True, "truncated": bool(result.get("links") and
                     any(link.get("rel") == "next" for link in result["links"]))}


def _inside(root: Path, path: Path) -> Path:
    root = root.resolve()
    target = path.resolve()
    if not target.is_relative_to(root):
        raise ValueError("파일 경로는 데이터 루트 내부여야 합니다")
    return target


def _sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _record(root, record):
    # 항목별 manifest이므로 병렬 작업 간 JSON 배열 덮어쓰기가 발생하지 않는다.
    directory = _inside(root, root / "manifests")
    directory.mkdir(parents=True, exist_ok=True)
    record["recorded_at"] = datetime.now(timezone.utc).isoformat()
    fingerprint = hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest()[:16]
    path = _inside(root, directory / f"{record['sha256']}-{fingerprint}.json")
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    record["manifest"] = str(path)
    return record


def download_asset(payload: dict, data_root: Path) -> dict:
    url = _safe_url(payload.get("url"))
    original_url = url
    max_bytes = _integer(payload.get("max_bytes", DEFAULT_MAX_BYTES), "max_bytes", 1, HARD_MAX_BYTES)
    retries = _integer(payload.get("retries", 2), "retries", 0, 5)
    expected = payload.get("sha256")
    if expected is not None and not re.fullmatch(r"[a-fA-F0-9]{64}", str(expected)):
        raise ValueError("sha256은 64자리 16진수여야 합니다")
    name = payload.get("filename") or Path(urlsplit(url).path).name or "asset.tif"
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,180}", name):
        raise ValueError("filename은 경로를 포함하지 않는 영문/숫자 파일명이어야 합니다")
    root = Path(data_root).resolve()
    directory = _inside(root, root / "downloads")
    directory.mkdir(parents=True, exist_ok=True)
    # URL 단위 부분파일은 다른 자산의 재개 데이터가 섞이는 일을 방지한다.
    parsed_original = urlsplit(original_url)
    identity_url = urlunsplit((parsed_original.scheme, parsed_original.netloc, parsed_original.path, "", "")) if parsed_original.hostname in PC_ASSET_HOSTS else original_url
    key = hashlib.sha256(identity_url.encode()).hexdigest()
    partial = _inside(root, directory / f"{key}.part")
    validator_path = _inside(root, directory / f"{key}.validator")
    url = resolve_asset_url(url)
    for attempt in range(retries + 1):
        offset = partial.stat().st_size if partial.exists() else 0
        if offset > max_bytes:
            partial.unlink()
            raise ValueError("부분파일이 다운로드 용량제한을 초과했습니다")
        headers = {"Accept-Encoding": "identity"}
        validator = validator_path.read_text() if validator_path.exists() else ""
        # ETag/Last-Modified가 없으면 안전한 재개를 보장할 수 없어 처음부터 받는다.
        if offset and validator:
            headers.update({"Range": f"bytes={offset}-", "If-Range": validator})
        else:
            offset = 0
        try:
            with _open(Request(url, headers=headers)) as response:
                resumed = response.status == 206 and offset > 0
                if response.status not in (200, 206):
                    raise RuntimeError("다운로드 응답 상태가 올바르지 않습니다")
                if response.status == 206:
                    content_range = response.headers.get("Content-Range", "")
                    match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", content_range)
                    if not resumed or not match or int(match[1]) != offset:
                        raise RuntimeError("재개 응답의 Content-Range가 일치하지 않습니다")
                    if int(match[3]) > max_bytes:
                        raise ValueError("다운로드 용량제한을 초과했습니다")
                    if int(match[2]) + 1 != int(match[3]):
                        raise RuntimeError("서버가 요청한 끝까지의 바이트 범위를 반환하지 않았습니다")
                    current_validator = response.headers.get("ETag") or response.headers.get("Last-Modified")
                    if current_validator and current_validator != validator:
                        raise RuntimeError("재개 응답 중 원격 자산 버전이 변경되었습니다")
                if not resumed:
                    offset = 0
                length = response.headers.get("Content-Length")
                if length and int(length) + offset > max_bytes:
                    raise ValueError("다운로드 용량제한을 초과했습니다")
                validator_path.write_text(response.headers.get("ETag") or response.headers.get("Last-Modified") or "")
                total = offset
                with partial.open("ab" if resumed else "wb") as stream:
                    while chunk := response.read(min(1024 * 1024, max_bytes - total + 1)):
                        total += len(chunk)
                        if total > max_bytes:
                            raise ValueError("다운로드 용량제한을 초과했습니다")
                        stream.write(chunk)
                if length and total - offset != int(length):
                    raise OSError("다운로드 본문이 조기에 종료되었습니다")
            break
        except (OSError, HTTPError, URLError, IncompleteRead) as exc:
            if isinstance(exc, HTTPError) and exc.code == 429:
                raise RuntimeError("공급자가 HTTP429를 반환하여 추가 재시도를 중단했습니다") from exc
            if attempt == retries:
                raise RuntimeError(f"다운로드 실패: {type(exc).__name__}; 부분파일은 재시도용으로 보존했습니다") from exc
            time.sleep(min(2 ** attempt, 4))
    digest = _sha(partial)
    if expected and digest.lower() != expected.lower():
        partial.unlink(missing_ok=True)
        validator_path.unlink(missing_ok=True)
        raise ValueError("SHA256 검증 실패")
    # 내용 해시를 파일명에 포함하여 같은 이름의 다른 장면을 덮어쓰지 않는다.
    target = _inside(root, directory / f"{digest}-{name}")
    duplicates = []
    for candidate in directory.glob(f"{digest}-*"):
        candidate = _inside(root, candidate)
        if candidate.is_file() and _sha(candidate) == digest:
            duplicates.append(candidate)
    duplicate = bool(duplicates)
    if duplicate:
        target = _inside(root, duplicates[0])
        partial.unlink()
    else:
        partial.replace(target)
    validator_path.unlink(missing_ok=True)
    parsed = urlsplit(url)
    # 서명 URL의 query는 보관하지 않지만 출처 호스트/경로는 남긴다.
    public_url = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
    return _record(root, {"status": "downloaded", "path": str(target), "sha256": digest,
                         "bytes": target.stat().st_size, "duplicate": duplicate,
                         "source": public_url, "license": payload.get("license", "UNVERIFIED"),
                         "license_verified": False})


def register_local(payload: dict, data_root: Path) -> dict:
    root = Path(data_root).resolve()
    raw = payload.get("path")
    if not isinstance(raw, str) or not raw:
        raise ValueError("데이터 루트 내부 GeoTIFF path가 필요합니다")
    path = _inside(root, root / raw)
    if not path.is_file() or path.suffix.lower() not in (".tif", ".tiff"):
        raise ValueError("존재하는 .tif/.tiff 파일이 필요합니다")
    try:
        rasterio = importlib.import_module("rasterio")
    except ImportError as exc:
        raise RuntimeError("GeoTIFF 검증에 rasterio 설치가 필요합니다") from exc
    with rasterio.open(path) as src:
        if src.driver != "GTiff" or src.crs is None:
            raise ValueError("좌표계가 명시된 유효한 GeoTIFF가 필요합니다")
        metadata = {"crs": str(src.crs), "bounds": list(src.bounds),
                    "width": src.width, "height": src.height, "count": src.count,
                    "dtype": list(src.dtypes), "resolution": list(src.res),
                    "nodata": str(src.nodata) if src.nodata is not None and not math.isfinite(src.nodata) else src.nodata}
    return _record(root, {"status": "registered", "path": str(path), "sha256": _sha(path),
                         "bytes": path.stat().st_size, "metadata": metadata,
                         "source": payload.get("source", "manual-local-registration"),
                         "license": payload.get("license", "UNVERIFIED"), "license_verified": False})


def worldcover_plan(payload: dict) -> dict:
    w, s, e, n = _bbox(payload)
    year = _integer(payload.get("year", 2021), "year", 2020, 2021)
    version = "v100" if year == 2020 else "v200"
    tiles = []
    for lat in range(math.floor(s / 3) * 3, math.ceil(n / 3) * 3, 3):
        for lon in range(math.floor(w / 3) * 3, math.ceil(e / 3) * 3, 3):
            code = f"{'N' if lat >= 0 else 'S'}{abs(lat):02d}{'E' if lon >= 0 else 'W'}{abs(lon):03d}"
            filename = f"ESA_WorldCover_10m_{year}_{version}_{code}_Map.tif"
            tiles.append({"tile": code, "filename": filename,
                          "url": f"https://esa-worldcover.s3.eu-central-1.amazonaws.com/{version}/{year}/map/{filename}",
                          "license": "CC-BY-4.0"})
            if len(tiles) > 100:
                raise ValueError("AOI가 너무 큽니다: 한 번에 최대 100개 타일만 계획합니다")
    return {"status": "planned", "executed": False, "year": year, "bbox": [w, s, e, n],
            "tiles": tiles, "license": "CC-BY-4.0", "availability_checked": False,
            "note": "3도 격자 후보입니다. 해양 타일은 없을 수 있습니다. 각 URL을 download_asset에 전달하세요."}


def dynamic_world_export(payload: dict) -> dict:
    bbox = _bbox(payload)
    start, end = _dates(payload)
    probability_bands = ["water", "trees", "grass", "flooded_vegetation", "crops",
                         "shrub_and_scrub", "built", "bare", "snow_and_ice"]
    plan = {"status": "planned", "executed": False, "collection": "GOOGLE/DYNAMICWORLD/V1",
            "bbox": bbox, "start_date": start, "end_date": end, "bands": probability_bands,
            "reducer": "mean_probabilities", "scale": 10, "license": "CC-BY-4.0",
            "note": "9개 기간평균 확률의 argmax는 기간별 label 최빈값과 다른 결과일 수 있습니다"}
    if payload.get("execute", False) is not True:
        return plan
    project = payload.get("project") or os.environ.get("GOOGLE_CLOUD_PROJECT")
    if not project:
        raise RuntimeError("Earth Engine 실행에는 인증된 Google Cloud project가 필요합니다; 실행되지 않았습니다")
    try:
        ee = importlib.import_module("ee")
    except ImportError as exc:
        raise RuntimeError("earthengine-api가 설치되지 않아 실행되지 않았습니다") from exc
    try:
        ee.Initialize(project=project)
        region = ee.Geometry.Rectangle(bbox)
        # filterDate 종료는 배타적이므로 사용자 종료 날짜의 다음 날까지 포함한다.
        exclusive_end = ee.Date(end).advance(1, "day")
        collection = ee.ImageCollection(plan["collection"]).filterBounds(region).filterDate(start, exclusive_end)
        if collection.size().getInfo() == 0:
            raise ValueError("AOI/기간에 Dynamic World 영상이 없습니다")
        image = collection.select(probability_bands).mean().toFloat().clip(region)
        task = ee.batch.Export.image.toDrive(image=image, description="dynamic_world_labels",
            folder="GeoAI_DynamicWorld", region=region, scale=10, maxPixels=1e9, fileFormat="GeoTIFF")
        task.start()
    except ValueError:
        raise
    except Exception as exc:
        raise RuntimeError("Earth Engine 인증/내보내기 요청 실패; 완료되지 않았습니다") from exc
    return {**plan, "status": "submitted", "executed": True, "completed": False,
            "task_id": task.id, "destination": "Google Drive/GeoAI_DynamicWorld"}


def align_labels(source: Path, reference: Path, destination: Path) -> dict:
    """참조 격자에 최근린 보간을 적용하여 이산 클래스 값을 보존한다."""
    try:
        import rasterio
        from rasterio.warp import reproject, Resampling
    except ImportError as exc:
        raise RuntimeError("레이블 정렬에 rasterio가 필요합니다") from exc
    if destination.resolve() in (source.resolve(), reference.resolve()):
        raise ValueError("정렬 결과는 입력과 다른 파일에 저장해야 합니다")
    with rasterio.open(source) as src, rasterio.open(reference) as ref:
        if src.crs is None or ref.crs is None:
            raise ValueError("입력/참조 래스터의 좌표계가 필요합니다")
        # NoData가 없는 클래스 래스터는 겹치지 않는 영역을 0(실제 클래스)으로 채우지 않는다.
        if src.nodata is None:
            raise ValueError("레이블 정렬 전 명시적 NoData 값을 설정하세요")
        profile = src.profile.copy()
        profile.update(driver="GTiff", width=ref.width, height=ref.height, crs=ref.crs,
                       transform=ref.transform, compress="deflate")
        with rasterio.open(destination, "w", **profile) as dst:
            for band in range(1, src.count + 1):
                reproject(source=rasterio.band(src, band), destination=rasterio.band(dst, band),
                          src_transform=src.transform, src_crs=src.crs, src_nodata=src.nodata,
                          dst_transform=ref.transform, dst_crs=ref.crs, dst_nodata=src.nodata,
                          resampling=Resampling.nearest)
    return {"status": "aligned", "path": str(destination), "resampling": "nearest"}
