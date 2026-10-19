"""DNS → HTTPS 카탈로그 → STAC 검색 → 선택적 COG 부분읽기를 분리 진단한다."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import re
from pathlib import Path
import socket
import ssl
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))
from app.data import service

QUERY = {"bbox": [106.75, -6.75, 106.80, -6.70], "start_date": "2023-06-01",
         "end_date": "2023-09-30", "cloud_cover": 10, "limit": 1,
         "collection": "sentinel-2-l2a"}


def classify_error(exc):
    """최종 RuntimeError 뒤에 감춰진 DNS/HTTP 원인을 복원한다."""
    def safe_message(error):
        message = re.sub(r"https?://[^\s\"'<>]+", "[REDACTED_URL]", str(error), flags=re.IGNORECASE)
        message = re.sub(r"https?%3a%2f%2f[^\s\"'<>]+", "[REDACTED_URL]", message, flags=re.IGNORECASE)
        message = re.sub(r"\b(sig|token|access_token|api_key)=[^\s&\"'<>]+", r"\1=[REDACTED]", message, flags=re.IGNORECASE)
        return message[:500]
    chain, seen = [], set()
    while id(exc) not in seen:
        seen.add(id(exc))
        chain.append({"error_type": type(exc).__name__, "sanitized_message": safe_message(exc)})
        if exc.__cause__ is None or len(chain) >= 5:
            break
        exc = exc.__cause__
    detail = {"sanitized_message": safe_message(exc), "exception_chain": chain}
    if getattr(exc, "shared_collection_stop", False):
        return {"category": "shared_collection_stop", "new_http_request_sent": False,
                "shared_reason": getattr(exc, "shared_reason", None), **detail}
    if isinstance(exc, UnicodeError):
        return {"category": "local_native_encoding", "error_type": type(exc).__name__, **detail}
    if isinstance(exc, HTTPError):
        request_url = urlsplit(exc.url or "")
        headers = exc.headers or {}
        return {"category": "http_response", "http_status": exc.code,
                "retry_after": str(headers.get("Retry-After"))[:120] if headers.get("Retry-After") is not None else None,
                "request_host": request_url.hostname, "request_path": request_url.path,
                "server_reached": True, "error_type": type(exc).__name__, **detail}
    if isinstance(exc, URLError):
        exc = exc.reason
    if isinstance(exc, socket.gaierror):
        category = "dns_resolution"
    elif isinstance(exc, (ssl.SSLError, ssl.CertificateError)):
        category = "tls_certificate"
    elif isinstance(exc, (TimeoutError, socket.timeout)):
        category = "network_timeout"
    elif isinstance(exc, (ConnectionError, OSError)):
        category = "network_connection"
    elif isinstance(exc, (ValueError, KeyError, TypeError)):
        category = "payload_or_response_contract"
    else:
        category = "unexpected_runtime"
    # 예외 문자열에는 서명 URL 등이 포함될 수 있어 원본 전체를 보고서에 쓰지 않는다.
    return {"category": category, "error_type": type(exc).__name__,
            "error_code": getattr(exc, "errno", None), **detail}


def sample_window(search, output, side):
    """COG 한 밴드의 작은 실제 픽셀 창을 저장한다. 장면 전체를 받지 않는다."""
    import rasterio
    from rasterio.windows import Window
    from rasterio.warp import transform

    if not search["items"]:
        return {"status": "skipped", "reason": "검색 결과 없음"}
    item = search["items"][0]
    assets = item["assets"]
    key = "red" if "red" in assets else "B04" if "B04" in assets else next(iter(assets), None)
    if key is None:
        return {"status": "skipped", "reason": "GeoTIFF 자산 없음"}
    original_url = service._safe_url(assets[key]["href"])
    url = service.resolve_asset_url(original_url)
    bbox = QUERY["bbox"]
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", GDAL_HTTP_TIMEOUT="20",
                      GDAL_HTTP_MAX_RETRY="1", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif,.tiff"):
        range_reader = service.HTTPRangeReader(url)
        # Windows GDAL/libcurl의 로컬 인증서 경로 인코딩 오류를 피하면서 urllib의
        # 동일 HTTPS 검증/허용목록과 엄격한 누적 본문 제한으로 COG를 읽는다.
        def range_opener(path, mode="r"):
            if path != url:
                raise FileNotFoundError("요청하지 않은 COG 보조파일")
            return range_reader
        with rasterio.open(url, opener=range_opener) as src:
            if src.crs is None:
                raise ValueError("샘플 COG 좌표계가 없습니다")
            x, y = transform("EPSG:4326", src.crs, [(bbox[0] + bbox[2]) / 2], [(bbox[1] + bbox[3]) / 2])
            row, col = src.index(x[0], y[0])
            if not 0 <= row < src.height or not 0 <= col < src.width:
                raise ValueError("검색 중심점이 반환된 COG 범위 밖입니다")
            window = Window(max(0, col - side // 2), max(0, row - side // 2),
                            min(side, src.width - max(0, col - side // 2)),
                            min(side, src.height - max(0, row - side // 2)))
            pixels = src.read(1, window=window)
            profile = src.profile.copy()
            profile.update(width=pixels.shape[1], height=pixels.shape[0], count=1,
                           transform=src.window_transform(window), driver="GTiff")
            # 원본의 타일 블록 옵션은 작은 창의 쓰기에 불필요하다.
            for field in ("blockxsize", "blockysize", "tiled"):
                profile.pop(field, None)
            destination = output / "sentinel2-red-window.tif"
            with rasterio.open(destination, "w", **profile) as dst:
                dst.write(pixels, 1)
    registered = service.register_local({"path": destination.name,
        "source": original_url.split("?", 1)[0], "license": item["license"]}, output)
    return {"status": "downloaded_window", "source_scene": item["id"], "asset": key,
            "shape": list(pixels.shape), "path": str(destination), "sha256": registered["sha256"],
            "bytes": destination.stat().st_size, "full_scene_downloaded": False,
            "http_body_bytes": range_reader.transferred, "max_http_body_bytes": range_reader.limit,
            "note": "픽셀 창 및 urllib Range 본문의 누적 전송량 32MiB를 제한합니다"}


def diagnose(output: Path, offline=False, sample=False, window_size=64, endpoint="earth-search"):
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    endpoint_url = service.stac_endpoint(endpoint)
    query = {**QUERY, "endpoint": endpoint}
    report = {"checked_at": datetime.now(timezone.utc).isoformat(), "endpoint": endpoint_url,
              "query": query, "offline": offline, "stages": [],
              "real_search_verified": False, "real_download_verified": False}
    if offline:
        report["stages"].append({"stage": "network", "status": "not_attempted", "reason": "offline 플래그"})
    else:
        host = urlsplit(endpoint_url).hostname
        try:
            addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
            report["stages"].append({"stage": "dns", "status": "passed", "address_count": len(addresses)})
            dns_ok = True
        except Exception as exc:
            report["stages"].append({"stage": "dns", "status": "failed", **classify_error(exc)})
            dns_ok = False
        if dns_ok:
            try:
                catalogue = service._json_response(Request(endpoint_url.removesuffix("/search")))
                report["stages"].append({"stage": "https_catalogue", "status": "passed",
                                          "stac_version": catalogue.get("stac_version")})
            except Exception as exc:
                report["stages"].append({"stage": "https_catalogue", "status": "failed", **classify_error(exc)})
            try:
                result = service.search_stac(query)
                (output / "stac-search.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
                report["real_search_verified"] = True
                report["stages"].append({"stage": "stac_post_search", "status": "passed", "count": result["count"],
                    "items": [{"id": item["id"], "datetime": item["datetime"], "cloud_cover": item["cloud_cover"],
                               "downloadable_asset_keys": list(item["assets"])} for item in result["items"]]})
            except Exception as exc:
                result = None
                report["stages"].append({"stage": "stac_post_search", "status": "failed", **classify_error(exc)})
            if sample and result is not None:
                try:
                    window = sample_window(result, output, window_size)
                    report["stages"].append({"stage": "cog_window", **window})
                    report["real_download_verified"] = window["status"] == "downloaded_window"
                except Exception as exc:
                    report["stages"].append({"stage": "cog_window", "status": "failed", **classify_error(exc)})
        else:
            report["stages"].append({"stage": "https_and_search", "status": "blocked_by_dns",
                                    "api_code_conclusion": "DNS 실패로 STAC API 구현의 성공/실패는 미검증"})
    (output / "diagnosis.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "data" / "validation")
    parser.add_argument("--offline", action="store_true", help="네트워크를 호출하지 않고 실행 환경만 기록")
    parser.add_argument("--sample", action="store_true", help="성공 시 Sentinel-2 실제 COG 한 밴드 픽셀 창 읽기")
    parser.add_argument("--window-size", type=int, default=64)
    parser.add_argument("--endpoint", default="earth-search", help="earth-search / planetary-computer 또는 고정 카탈로그 URL")
    args = parser.parse_args()
    if not 1 <= args.window_size <= 512:
        parser.error("--window-size는 1~512입니다")
    report = diagnose(args.output, args.offline, args.sample, args.window_size, args.endpoint)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if args.offline or report["real_search_verified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
