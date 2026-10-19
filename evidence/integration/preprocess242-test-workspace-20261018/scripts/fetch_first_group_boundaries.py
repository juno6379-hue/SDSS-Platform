"""geoBoundaries 공식 gbOpen IDN ADM1에서 사용자 지정 6개 주 경계를 선택한다."""
from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler

ROOT = Path(__file__).resolve().parents[1]
HOSTS = {"www.geoboundaries.org", "geoboundaries.org", "github.com", "raw.githubusercontent.com", "media.githubusercontent.com"}


def validate_url(url):
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in HOSTS or parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ValueError("허용된 geoBoundaries 공식 HTTPS 경로가 아닙니다")
    if parsed.hostname in {"github.com", "raw.githubusercontent.com", "media.githubusercontent.com"} and "wmgeolab/geoBoundaries" not in parsed.path:
        raise ValueError("공식 geoBoundaries 저장소 경로가 아닙니다")
    return url


class SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(url, max_bytes):
    validate_url(url)
    with build_opener(SafeRedirect()).open(Request(url), timeout=45) as response:
        body = response.read(max_bytes + 1)
    if len(body) > max_bytes:
        raise ValueError("경계 데이터 다운로드 용량 제한 초과")
    return body


def normalized(name):
    return re.sub(r"[^a-z]", "", name.lower())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/first-group.collection.json")
    parser.add_argument("--output", type=Path, default=ROOT / "data/first-group-boundaries")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    if not args.execute:
        print(json.dumps({"status": "planned", "province_ids": [p["id"] for p in config["provinces"]], "expected_cells": 36}))
        return 0
    from shapely.geometry import shape, mapping, box
    args.output.mkdir(parents=True, exist_ok=True)
    metadata_raw = fetch(config["boundary_api"], 1024 ** 2)
    metadata = json.loads(metadata_raw)
    url = metadata.get("simplifiedGeometryGeoJSON") or metadata["gjDownloadURL"]
    raw = fetch(url, 32 * 1024 ** 2)
    country = json.loads(raw)
    (args.output / "geoBoundaries-IDN-ADM1.geojson").write_bytes(raw)
    (args.output / "source-metadata.json").write_bytes(metadata_raw)
    aliases = {
        "south_sulawesi": ["Sulawesi Selatan", "South Sulawesi"],
        "gorontalo": ["Gorontalo"],
        "southeast_sulawesi": ["Sulawesi Tenggara", "Southeast Sulawesi", "South East Sulawesi"],
        "banten": ["Banten"], "west_java": ["Jawa Barat", "West Java"],
        "east_java": ["Jawa Timur", "East Java"],
    }
    selected, aois = [], []
    for province in config["provinces"]:
        matches = [feature for feature in country["features"] if normalized(feature["properties"].get("shapeName", "")) in {normalized(x) for x in aliases[province["id"]]}]
        if len(matches) != 1:
            raise ValueError(f"{province['id']} 경계 일치 {len(matches)}개; 원본 이름 {[f['properties'].get('shapeName') for f in country['features']]}")
        feature = matches[0]
        geometry = shape(feature["geometry"])
        if geometry.is_empty or not geometry.is_valid:
            raise ValueError(f"{province['id']} 경계가 유효하지 않습니다")
        interior = geometry.representative_point()
        x, y = interior.x, interior.y
        sample_bbox = [x - .03, y - .03, x + .03, y + .03]
        feature["properties"].update(province_id=province["id"], province_name=province["name"],
            representative_interior_point=[x, y], boundary_bbox=list(geometry.bounds))
        selected.append(feature)
        aois.append({"id": province["id"], "province_name": province["name"], "local_name": province["local_name"],
            "bbox": sample_bbox, "province_bbox": list(geometry.bounds), "representative_interior_point": [x, y],
            "sample_bbox_inside_province": geometry.covers(box(*sample_bbox)),
            "boundary_status": "public_geoboundaries_ADM1_reference_not_legal_certification",
            "boundary_feature_id": feature["properties"].get("shapeID"),
            "boundary_geojson": str(args.output.resolve() / "selected-six.geojson"),
            "scope_note": "province_bbox는 전체 주 범위; bbox는 내부 대표점 주변 STAC 검색용 작은 범위; 실제256창은 주 전체가 아님"})
    selected_path = args.output / "selected-six.geojson"
    selected_path.write_text(json.dumps({"type": "FeatureCollection", "features": selected}, ensure_ascii=False), encoding="utf-8")
    manifest = {"status": "downloaded_selected", "recorded_at": datetime.now(timezone.utc).isoformat(),
        "api": config["boundary_api"], "geometry_url": url, "source_metadata": metadata,
        "release_family": "geoBoundaries gbOpen",
        "boundary_license": metadata.get("boundaryLicense"), "license_source": metadata.get("licenseSource"),
        "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw), "country_feature_count": len(country["features"]),
        "selected_province_count": len(selected), "selected_sha256": hashlib.sha256(selected_path.read_bytes()).hexdigest(),
        "boundary_is_current_legal_authority": False,
        "note": "공개 참조 행정경계이며 사업/발주처의 법적 확정 경계라는 주장을 하지 않습니다"}
    (args.output / "boundary-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    config.update(aois=aois, boundary_status="public_ADM1_reference_fetched", boundary_manifest=str((args.output / "boundary-manifest.json").resolve()))
    config["prior_download_budget_bytes"] += len(raw) + len(metadata_raw)
    args.config.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": manifest["status"], "country_features": len(country["features"]),
                      "selected_provinces": len(selected), "bytes": len(raw), "license": metadata.get("boundaryLicense")}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
