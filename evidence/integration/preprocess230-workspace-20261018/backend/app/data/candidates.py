"""공개경계 근처의 추가 공간후보를 로컬에서만 검증한다. HTTP 호출 없음."""
import hashlib
import json
import re
from pathlib import Path


def footprint(lon, lat, crs, side=1024):
    from pyproj import Transformer
    from shapely.geometry import box
    from shapely.ops import transform
    if not re.fullmatch(r"EPSG:32[67](4[6-9]|5[0-4])", crs):
        raise ValueError("인도네시아 UTM 미터계 CRS가 필요합니다")
    forward = Transformer.from_crs(4326, crs, always_xy=True)
    inverse = Transformer.from_crs(crs, 4326, always_xy=True)
    x, y = forward.transform(lon, lat)
    half = side * 10 / 2
    return transform(inverse.transform, box(x-half,y-half,x+half,y+half))


def validate_candidate_plan(path, boundary_path, existing_centers=()):
    """후보의 실제 클래스 존재를 검증했다고 주장하지 않고 공간중복만 거부한다.

    existing_centers는[{province,lon,lat,grid_crs},...]이다. 같은주내같은공간을
    새 ID로 다시 넣어도 거부한다. source파일의 proposal 플래그는 보존한다.
    """
    import math
    from shapely.geometry import Point, shape
    boundary_path, path = Path(boundary_path), Path(path)
    digest = hashlib.sha256(boundary_path.read_bytes()).hexdigest()
    boundaries = json.loads(boundary_path.read_text(encoding="utf-8"))["features"]
    polygons = {feature["properties"]["province_id"]: shape(feature["geometry"]) for feature in boundaries}
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("schema_version") != 1 or document.get("executed_network") is not False:
        raise ValueError("스키마1/로컬제안기록이필요합니다")
    previous = [(item["province"], footprint(item["lon"],item["lat"],item["grid_crs"])) for item in existing_centers]
    accepted, ids = [], set()
    for candidate in document.get("candidates", []):
        province = candidate.get("province")
        identifier = candidate.get("spatial_window_id", "")
        if province not in polygons or not re.fullmatch(r"[A-Za-z0-9_-]{1,52}", identifier) or identifier in ids:
            raise ValueError("등록된주/고유공간ID가필요합니다")
        if candidate.get("boundary_sha256") != digest or candidate.get("window_size") != 1024:
            raise ValueError("경계SHA또는원본창크기가기존계획과다릅니다")
        lon, lat = candidate["lon"], candidate["lat"]
        if isinstance(lon,bool) or isinstance(lat,bool) or not all(isinstance(v,(int,float)) and math.isfinite(v) for v in (lon,lat)):
            raise ValueError("유한한수치좌표가필요합니다")
        if not polygons[province].covers(Point(lon,lat)):
            raise ValueError("후보중심이해당주공개polygon밖입니다")
        polygon = footprint(lon,lat,candidate["grid_crs"])
        if any(p == province and polygon.intersection(other).area > 1e-12 for p,other in previous):
            raise ValueError("기존/추가원본창과공간이겹칩니다.새ID로중복허용하지않습니다")
        if candidate.get("reference") != "esri_io" or not candidate.get("years") or any(y not in range(2020,2026) for y in candidate["years"]):
            raise ValueError("검토한Esri동년참조2020~2025범위만허용합니다")
        previous.append((province,polygon))
        ids.add(identifier)
        accepted.append(candidate.copy())
    return {"source_path": str(path.resolve()), "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "boundary_sha256": digest, "candidates": accepted, "validated_spatial_only": True,
        "class_presence_verified": False, "source_proposal_consumption_flag": document.get("collector_consumption_approved")}
