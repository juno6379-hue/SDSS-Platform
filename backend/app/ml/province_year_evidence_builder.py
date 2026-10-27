"""Build auditable province boundaries and province-year SCL coverage mosaics.

The builder is intentionally separate from collection execution.  It may read
already-downloaded Sentinel-2 SCL windows and public metadata services, but it
never starts a collector, writes the collection ledger, or acquires an
execution lock.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import socket
import time
from typing import Any, Callable, Iterable, Mapping, Sequence
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import numpy as np
import rasterio
from rasterio.errors import RasterioIOError
from rasterio.features import geometry_mask
from rasterio.transform import from_origin
from rasterio.warp import Resampling, reproject, transform_geom
from shapely.geometry import mapping, shape
from shapely.ops import unary_union

from .province_year_gap_acquisition_planner import PROVINCES, YEARS
from .province_year_coverage import sha256_file


BIG_LAYER_URL = (
    "https://geoservices.big.go.id/rbi/rest/services/"
    "BATASWILAYAH/BATAS_WILAYAH/MapServer/12"
)
BIG_QUERY_URL = f"{BIG_LAYER_URL}/query"
BIG_LAYER_NAME = "Area Batas Wilayah Administrasi Provinsi"
BIG_LAYER_ID = 12
EQUAL_AREA_CRS = "EPSG:6933"
BOUNDARY_CANDIDATE_SCHEMA = "province-boundary-candidate/1.0"
GISTARU_DISCOVERY_SCHEMA = "gistaru-service-discovery/1.0"
MOSAIC_MANIFEST_SCHEMA = "province-year-scl-mosaic-manifest/1.0"

PROVINCE_LOCAL_NAMES = {
    "banten": "Banten",
    "west_java": "Jawa Barat",
    "east_java": "Jawa Timur",
    "south_sulawesi": "Sulawesi Selatan",
    "gorontalo": "Gorontalo",
    "southeast_sulawesi": "Sulawesi Tenggara",
}

GISTARU_SERVICE_CANDIDATES = (
    {
        "scope": "JAVA_PROVINCE_SPATIAL_PLAN",
        "service_url": (
            "https://gistaru.atrbpn.go.id/arcgis/rest/services/"
            "004_RTR_PROVINSI_PULAU_JAWA/_3000_PROVINSI_JAWA_PR_PERDA/MapServer"
        ),
        "province_ids": ["banten", "west_java", "east_java"],
    },
    {
        "scope": "SULAWESI_PROVINCE_SPATIAL_PLAN",
        "service_url": (
            "https://gistaru.atrbpn.go.id/arcgis/rest/services/"
            "006_RTR_PROVINSI_PULAU_SULAWESI/_7000_PROVINSI_SULAWESI_PR_PERDA/MapServer"
        ),
        "province_ids": ["south_sulawesi", "gorontalo", "southeast_sulawesi"],
    },
)

# Sentinel-2 L2A Scene Classification Layer values.
SCL_CLEAR = frozenset({4, 5, 6, 7, 11})
SCL_CLOUD = frozenset({8, 9, 10})
SCL_SHADOW = frozenset({2, 3})
SCL_NODATA = frozenset({0, 1})


class ProvinceEvidenceError(RuntimeError):
    """Raised when an evidence artifact cannot be built safely."""


@dataclass(frozen=True)
class SclAsset:
    province_id: str
    year: int
    path: Path
    sha256: str
    stac_item_id: str | None
    stac_item_path: str | None


@dataclass(frozen=True)
class MosaicCellResult:
    province_id: str
    year: int
    resolution_m: float
    width: int
    height: int
    boundary_pixels: int
    observed_pixels: int
    gap_pixels: int
    cause_pixels: dict[str, int]
    source_asset_count: int
    observed_path: str
    observed_sha256: str
    cause_path: str
    cause_sha256: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )


def _write_bytes(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise ProvinceEvidenceError(f"OUTPUT_EXISTS:{path}")
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_bytes(value)
    temporary.replace(path)


def _write_json(path: Path, value: Any) -> None:
    _write_bytes(path, _canonical_json_bytes(value))


def _request_bytes(url: str, *, timeout: float = 60.0) -> bytes:
    request = Request(url, headers={"User-Agent": "GeoAI-MLOps-SDSS-evidence-builder/1.0"})
    with urlopen(request, timeout=timeout) as response:
        if response.status != 200:
            raise ProvinceEvidenceError(f"HTTP_STATUS:{response.status}:{url}")
        return response.read()


def _query_url(base: str, values: Mapping[str, Any]) -> str:
    return f"{base}?{urlencode({key: str(value) for key, value in values.items()})}"


def _safe_union(features: Sequence[Mapping[str, Any]], province_id: str):
    geometries = []
    for feature in features:
        try:
            geometry = shape(feature["geometry"])
        except Exception as exc:  # pragma: no cover - defensive remote input guard
            raise ProvinceEvidenceError(f"BOUNDARY_GEOMETRY_INVALID:{province_id}") from exc
        if geometry.is_empty:
            continue
        if not geometry.is_valid:
            geometry = geometry.buffer(0)
        if not geometry.is_empty:
            geometries.append(geometry)
    if not geometries:
        raise ProvinceEvidenceError(f"BOUNDARY_GEOMETRY_EMPTY:{province_id}")
    merged = unary_union(geometries)
    if not merged.is_valid:
        merged = merged.buffer(0)
    if merged.is_empty or merged.geom_type not in {"Polygon", "MultiPolygon"}:
        raise ProvinceEvidenceError(f"BOUNDARY_UNION_INVALID:{province_id}:{merged.geom_type}")
    return merged


def fetch_big_boundary_candidate(
    output_dir: Path,
    *,
    timeout: float = 120.0,
    max_allowable_offset_degrees: float = 0.0001,
    fetcher: Callable[..., bytes] = _request_bytes,
) -> Path:
    """Fetch and dissolve the six current public BIG province polygons.

    The result deliberately remains a candidate: the public service does not
    expose a current legal/statistical approval record in its layer metadata.
    """
    output_dir = Path(output_dir)
    raw_dir = output_dir / "raw-boundary"
    metadata_url = _query_url(BIG_LAYER_URL, {"f": "pjson"})
    metadata_bytes = fetcher(metadata_url, timeout=timeout)
    metadata = json.loads(metadata_bytes.decode("utf-8"))
    if metadata.get("name") != BIG_LAYER_NAME or metadata.get("type") != "Feature Layer":
        raise ProvinceEvidenceError("BIG_LAYER_METADATA_MISMATCH")
    if metadata.get("geometryType") != "esriGeometryPolygon":
        raise ProvinceEvidenceError("BIG_LAYER_POLYGON_REQUIRED")
    metadata_path = raw_dir / "big-layer-12-metadata.json"
    _write_bytes(metadata_path, metadata_bytes)

    output_features = []
    query_evidence = []
    for province_id in PROVINCES:
        local_name = PROVINCE_LOCAL_NAMES[province_id]
        parameters = {
            "where": f"wadmpr='{local_name}'",
            "outFields": "objectid,namobj,kdpbps,kdppum,luaswh,wadmpr,metadata,remark",
            "returnGeometry": "true",
            "outSR": "4326",
            "geometryPrecision": "7",
            "maxAllowableOffset": max_allowable_offset_degrees,
            "f": "geojson",
        }
        url = _query_url(BIG_QUERY_URL, parameters)
        raw = fetcher(url, timeout=timeout)
        raw_path = raw_dir / f"big-{province_id}.geojson"
        _write_bytes(raw_path, raw)
        document = json.loads(raw.decode("utf-8"))
        features = document.get("features")
        if not isinstance(features, list) or not features:
            raise ProvinceEvidenceError(f"BIG_BOUNDARY_FEATURES_MISSING:{province_id}")
        names = {str((feature.get("properties") or {}).get("wadmpr")) for feature in features}
        if names != {local_name}:
            raise ProvinceEvidenceError(f"BIG_BOUNDARY_NAME_MISMATCH:{province_id}:{sorted(names)}")
        merged = _safe_union(features, province_id)
        output_features.append(
            {
                "type": "Feature",
                "properties": {
                    "province_id": province_id,
                    "local_name": local_name,
                    "source_feature_count": len(features),
                    "source_object_ids": sorted(
                        int(feature["properties"]["objectid"])
                        for feature in features
                        if feature.get("properties", {}).get("objectid") is not None
                    ),
                    "source_layer_id": BIG_LAYER_ID,
                    "source_layer_name": BIG_LAYER_NAME,
                    "derived_operation": "DISSOLVE_BY_WADMPR",
                },
                "geometry": mapping(merged),
            }
        )
        query_evidence.append(
            {
                "province_id": province_id,
                "query_url": url,
                "response_path": raw_path.relative_to(output_dir).as_posix(),
                "response_sha256": sha256_file(raw_path),
                "feature_count": len(features),
            }
        )

    candidate = {
        "type": "FeatureCollection",
        "schema_version": BOUNDARY_CANDIDATE_SCHEMA,
        "evidence_status": "IMPLEMENTED_UNVERIFIED",
        "status": "CANDIDATE_PENDING_COMPETENT_AUTHORITY_AND_STATISTICAL_APPROVAL",
        "crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
        "retrieved_at": _utc_now(),
        "authority": {
            "organization": "Badan Informasi Geospasial (BIG)",
            "source_url": BIG_LAYER_URL,
            "service_item_id": metadata.get("serviceItemId"),
            "layer_id": BIG_LAYER_ID,
            "layer_name": BIG_LAYER_NAME,
            "official_public_service": True,
            "legal_status": "OFFICIAL_PUBLICATION_CANDIDATE",
            "approved_for_project_statistics": False,
            "approval_blocker": "NO_CURRENT_EFFECTIVE_DATE_OR_STATISTICAL_APPROVAL_RECORD_IN_PUBLIC_LAYER_METADATA",
            "metadata_path": metadata_path.relative_to(output_dir).as_posix(),
            "metadata_sha256": sha256_file(metadata_path),
        },
        "derivation": {
            "max_allowable_offset_degrees": max_allowable_offset_degrees,
            "geometry_precision_decimal_places": 7,
            "query_evidence": query_evidence,
        },
        "features": output_features,
    }
    target = output_dir / "six-province-boundary-candidate.geojson"
    _write_json(target, candidate)
    return target


def probe_gistaru_services(
    output_dir: Path,
    *,
    timeout: float = 20.0,
    fetcher: Callable[..., bytes] = _request_bytes,
) -> Path:
    """Probe the exact public GISTARU MapServer candidates without guessing layers."""
    output_dir = Path(output_dir)
    results = []
    for candidate in GISTARU_SERVICE_CANDIDATES:
        service_url = str(candidate["service_url"])
        hostname = "gistaru.atrbpn.go.id"
        dns_addresses: list[str] = []
        dns_error = None
        try:
            dns_addresses = sorted({row[4][0] for row in socket.getaddrinfo(hostname, 443)})
        except OSError as exc:
            dns_error = f"{type(exc).__name__}:{exc}"
        record = dict(candidate)
        record.update(
            {
                "metadata_url": _query_url(service_url, {"f": "pjson"}),
                "dns_addresses": dns_addresses,
                "dns_error": dns_error,
                "http_status": None,
                "metadata_sha256": None,
                "layer_id": None,
                "layer_name": None,
                "query_where": None,
                "out_sr": 4326,
                "status": "BLOCKED_DNS_OR_SERVICE_UNAVAILABLE",
            }
        )
        try:
            raw = fetcher(record["metadata_url"], timeout=timeout)
            metadata = json.loads(raw.decode("utf-8"))
            metadata_path = output_dir / "raw-gistaru" / f"{candidate['scope'].lower()}.json"
            _write_bytes(metadata_path, raw)
            layers = metadata.get("layers")
            record["http_status"] = 200
            record["metadata_path"] = metadata_path.relative_to(output_dir).as_posix()
            record["metadata_sha256"] = sha256_file(metadata_path)
            record["status"] = "METADATA_RETRIEVED_LAYER_SELECTION_PENDING"
            record["advertised_layers"] = layers if isinstance(layers, list) else []
        except Exception as exc:
            record["probe_error"] = f"{type(exc).__name__}:{exc}"
        results.append(record)
    status = (
        "METADATA_RETRIEVED_LAYER_SELECTION_PENDING"
        if all(row["http_status"] == 200 for row in results)
        else "BLOCKED_GISTARU_LIVE_METADATA_UNAVAILABLE"
    )
    document = {
        "schema_version": GISTARU_DISCOVERY_SCHEMA,
        "evidence_status": "IMPLEMENTED_UNVERIFIED",
        "checked_at": _utc_now(),
        "portal_url": "https://gistaru.atrbpn.go.id/rtronline/",
        "status": status,
        "role": "BOUNDARY_CROSS_CHECK_ONLY",
        "source_catalog_reference": "https://simrenas-webgis.bappenas.go.id/list_services",
        "services": results,
        "operational_rule": (
            "Do not populate layer_id, layer_name, query_where, comparison_status, or VERIFIED_REAL "
            "until the official service metadata and query response are pinned and compared."
        ),
    }
    target = output_dir / "gistaru-service-discovery.json"
    _write_json(target, document)
    return target


def discover_local_scl_assets(source_root: Path) -> dict[tuple[str, int], list[SclAsset]]:
    """Inventory the preserved raw SCL windows for the exact 36 cells."""
    source_root = Path(source_root).resolve()
    result: dict[tuple[str, int], list[SclAsset]] = defaultdict(list)
    for path in sorted(source_root.rglob("raw-SCL.tif")):
        lowered = path.as_posix().lower()
        provinces = [province for province in PROVINCES if province in lowered]
        years = [year for year in YEARS if str(year) in lowered]
        if len(provinces) != 1 or len(years) != 1:
            raise ProvinceEvidenceError(f"SCL_CELL_ID_AMBIGUOUS:{path}")
        stac_path = path.with_name("stac-item.json")
        stac_id = None
        stac_ref = None
        if stac_path.is_file():
            try:
                stac_id = json.loads(stac_path.read_text(encoding="utf-8")).get("id")
                stac_ref = stac_path.as_posix()
            except (OSError, json.JSONDecodeError) as exc:
                raise ProvinceEvidenceError(f"SCL_STAC_ITEM_INVALID:{stac_path}") from exc
        result[(provinces[0], years[0])].append(
            SclAsset(provinces[0], years[0], path, sha256_file(path), stac_id, stac_ref)
        )
    expected = {(province, year) for province in PROVINCES for year in YEARS}
    if set(result) != expected:
        missing = sorted(expected - set(result))
        raise ProvinceEvidenceError(f"SCL_EXACT_36_CELL_SCOPE_REQUIRED:{missing}")
    return dict(result)


def _boundary_index(boundary_path: Path) -> dict[str, Mapping[str, Any]]:
    document = json.loads(Path(boundary_path).read_text(encoding="utf-8"))
    features = document.get("features")
    if not isinstance(features, list):
        raise ProvinceEvidenceError("BOUNDARY_FEATURES_REQUIRED")
    result = {}
    for feature in features:
        province_id = str((feature.get("properties") or {}).get("province_id"))
        if province_id in result:
            raise ProvinceEvidenceError(f"BOUNDARY_DUPLICATE_PROVINCE:{province_id}")
        result[province_id] = feature
    if set(result) != set(PROVINCES):
        raise ProvinceEvidenceError("BOUNDARY_EXACT_SIX_PROVINCE_SCOPE_REQUIRED")
    return result


def _aligned_grid(boundary_wgs84: Mapping[str, Any], resolution_m: float):
    equal_area = shape(transform_geom("EPSG:4326", EQUAL_AREA_CRS, boundary_wgs84, precision=9))
    if equal_area.is_empty:
        raise ProvinceEvidenceError("BOUNDARY_EQUAL_AREA_GEOMETRY_INVALID")
    repair = {
        "required": not equal_area.is_valid,
        "method": None,
        "relative_area_change": 0.0,
    }
    if not equal_area.is_valid:
        original_area = float(equal_area.area)
        repaired = equal_area.buffer(0)
        if repaired.is_empty or not repaired.is_valid or repaired.geom_type not in {"Polygon", "MultiPolygon"}:
            raise ProvinceEvidenceError("BOUNDARY_EQUAL_AREA_TOPOLOGY_REPAIR_FAILED")
        relative_change = abs(float(repaired.area) - original_area) / original_area if original_area else 1.0
        if relative_change > 0.0001:
            raise ProvinceEvidenceError(
                f"BOUNDARY_EQUAL_AREA_TOPOLOGY_REPAIR_EXCESSIVE:{relative_change:.12f}"
            )
        equal_area = repaired
        repair = {
            "required": True,
            "method": "SHAPELY_BUFFER_ZERO_AFTER_CRS_TRANSFORM",
            "relative_area_change": relative_change,
        }
    left, bottom, right, top = equal_area.bounds
    left = math.floor(left / resolution_m) * resolution_m
    bottom = math.floor(bottom / resolution_m) * resolution_m
    right = math.ceil(right / resolution_m) * resolution_m
    top = math.ceil(top / resolution_m) * resolution_m
    width = int(round((right - left) / resolution_m))
    height = int(round((top - bottom) / resolution_m))
    if width <= 0 or height <= 0 or width * height > 50_000_000:
        raise ProvinceEvidenceError(f"MOSAIC_GRID_SIZE_UNSAFE:{width}x{height}")
    transform = from_origin(left, top, resolution_m, resolution_m)
    inside = geometry_mask(
        [mapping(equal_area)], out_shape=(height, width), transform=transform,
        invert=True, all_touched=False,
    )
    if not np.any(inside):
        raise ProvinceEvidenceError("BOUNDARY_HAS_NO_GRID_PIXELS")
    return transform, inside, repair


def _reproject_scl(path: Path, shape_: tuple[int, int], transform) -> np.ndarray:
    destination = np.full(shape_, 255, dtype="uint8")
    last_error: RasterioIOError | None = None
    for attempt in range(3):
        try:
            with rasterio.open(path) as source:
                if source.count != 1 or source.crs is None:
                    raise ProvinceEvidenceError(f"SCL_SINGLE_BAND_GEOREFERENCED_REQUIRED:{path}")
                array = source.read(1)
                values = set(int(value) for value in np.unique(array))
                if not values.issubset(set(range(12))):
                    raise ProvinceEvidenceError(f"SCL_VALUE_DOMAIN_INVALID:{path}:{sorted(values)}")
                reproject(
                    source=array,
                    destination=destination,
                    src_transform=source.transform,
                    src_crs=source.crs,
                    src_nodata=255,
                    dst_transform=transform,
                    dst_crs=EQUAL_AREA_CRS,
                    dst_nodata=255,
                    resampling=Resampling.nearest,
                )
            return destination
        except RasterioIOError as exc:
            last_error = exc
            if not path.is_file():
                break
            if attempt < 2:
                time.sleep(0.1 * (attempt + 1))
    raise ProvinceEvidenceError(f"SCL_RASTER_OPEN_FAILED:{path}:{last_error}")


def _write_mask(path: Path, array: np.ndarray, transform) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        with rasterio.open(path) as existing:
            matches = (
                existing.count == 1
                and existing.crs is not None
                and existing.crs.to_string() == EQUAL_AREA_CRS
                and existing.transform == transform
                and existing.shape == array.shape
                and existing.nodata is None
                and np.array_equal(existing.read(1), array.astype("uint8"))
            )
        if not matches:
            raise ProvinceEvidenceError(f"OUTPUT_EXISTS_WITH_DIFFERENT_CONTENT:{path}")
        return
    temporary = path.with_name(f".{path.name}.tmp.tif")
    profile = {
        "driver": "GTiff",
        "height": array.shape[0],
        "width": array.shape[1],
        "count": 1,
        "dtype": "uint8",
        "crs": EQUAL_AREA_CRS,
        "transform": transform,
        "compress": "DEFLATE",
        "predictor": 2,
        "tiled": True,
        "blockxsize": 256,
        "blockysize": 256,
    }
    with rasterio.open(temporary, "w", **profile) as dataset:
        dataset.write(array.astype("uint8"), 1)
    temporary.replace(path)


def build_local_scl_mosaics(
    boundary_path: Path,
    source_root: Path,
    output_dir: Path,
    *,
    resolution_m: float = 1000.0,
    execution_metadata: Mapping[str, Any] | None = None,
) -> Path:
    """Build 36 whole-province grids from the preserved local SCL windows."""
    if not math.isfinite(resolution_m) or resolution_m <= 0:
        raise ProvinceEvidenceError("RESOLUTION_M_POSITIVE_REQUIRED")
    boundary_path = Path(boundary_path).resolve()
    output_dir = Path(output_dir).resolve()
    boundaries = _boundary_index(boundary_path)
    assets = discover_local_scl_assets(source_root)
    cells: list[MosaicCellResult] = []
    asset_records = []
    boundary_repairs = []

    for province_id in PROVINCES:
        transform, inside, repair = _aligned_grid(boundaries[province_id]["geometry"], resolution_m)
        boundary_repairs.append({"province_id": province_id, **repair})
        for year in YEARS:
            counts = {
                "clear": np.zeros(inside.shape, dtype="uint16"),
                "cloud": np.zeros(inside.shape, dtype="uint16"),
                "shadow": np.zeros(inside.shape, dtype="uint16"),
                "nodata": np.zeros(inside.shape, dtype="uint16"),
            }
            cell_assets = assets[(province_id, year)]
            for asset in cell_assets:
                scl = _reproject_scl(asset.path, inside.shape, transform)
                counts["clear"] += np.isin(scl, tuple(SCL_CLEAR))
                counts["cloud"] += np.isin(scl, tuple(SCL_CLOUD))
                counts["shadow"] += np.isin(scl, tuple(SCL_SHADOW))
                counts["nodata"] += np.isin(scl, tuple(SCL_NODATA))
                asset_records.append(
                    {
                        "province_id": province_id,
                        "year": year,
                        "path": asset.path.as_posix(),
                        "sha256": asset.sha256,
                        "stac_item_id": asset.stac_item_id,
                        "stac_item_path": asset.stac_item_path,
                    }
                )

            observed = (inside & (counts["clear"] > 0)).astype("uint8")
            cause = np.zeros(inside.shape, dtype="uint8")
            gap = inside & (observed == 0)
            covered = (counts["clear"] + counts["cloud"] + counts["shadow"] + counts["nodata"]) > 0
            cause[gap & ~covered] = 4
            classified = gap & covered
            # Deterministic dominant-cause rule; ties choose cloud, then shadow, then nodata.
            stacked = np.stack((counts["cloud"], counts["shadow"], counts["nodata"]), axis=0)
            dominant = np.argmax(stacked, axis=0).astype("uint8") + 1
            cause[classified] = dominant[classified]
            observed[~inside] = 0
            cause[~inside] = 0

            cell_dir = output_dir / "mosaics" / province_id / str(year)
            observed_path = cell_dir / "observed.tif"
            cause_path = cell_dir / "cause.tif"
            _write_mask(observed_path, observed, transform)
            _write_mask(cause_path, cause, transform)
            cause_counts = {
                "CLOUD": int(np.count_nonzero(cause == 1)),
                "SHADOW": int(np.count_nonzero(cause == 2)),
                "NODATA": int(np.count_nonzero(cause == 3)),
                "OUTSIDE_FOOTPRINT": int(np.count_nonzero(cause == 4)),
            }
            boundary_pixels = int(np.count_nonzero(inside))
            observed_pixels = int(np.count_nonzero(observed))
            cells.append(
                MosaicCellResult(
                    province_id=province_id,
                    year=year,
                    resolution_m=float(resolution_m),
                    width=int(inside.shape[1]),
                    height=int(inside.shape[0]),
                    boundary_pixels=boundary_pixels,
                    observed_pixels=observed_pixels,
                    gap_pixels=boundary_pixels - observed_pixels,
                    cause_pixels=cause_counts,
                    source_asset_count=len(cell_assets),
                    observed_path=observed_path.relative_to(output_dir).as_posix(),
                    observed_sha256=sha256_file(observed_path),
                    cause_path=cause_path.relative_to(output_dir).as_posix(),
                    cause_sha256=sha256_file(cause_path),
                )
            )

    if len(cells) != 36:
        raise ProvinceEvidenceError(f"MOSAIC_EXACT_36_CELL_SCOPE_REQUIRED:{len(cells)}")
    execution = {
        "collector_invoked": False,
        "remote_sentinel_downloads": 0,
        "ledger_written": False,
        "execution_lock_acquired": False,
    }
    if execution_metadata is not None:
        allowed = set(execution)
        if set(execution_metadata) != allowed:
            raise ProvinceEvidenceError("MOSAIC_EXECUTION_METADATA_FIELDS_MISMATCH")
        execution = {
            "collector_invoked": bool(execution_metadata["collector_invoked"]),
            "remote_sentinel_downloads": int(execution_metadata["remote_sentinel_downloads"]),
            "ledger_written": bool(execution_metadata["ledger_written"]),
            "execution_lock_acquired": bool(execution_metadata["execution_lock_acquired"]),
        }
        if execution["remote_sentinel_downloads"] < 0:
            raise ProvinceEvidenceError("MOSAIC_REMOTE_DOWNLOAD_COUNT_INVALID")
    manifest = {
        "schema_version": MOSAIC_MANIFEST_SCHEMA,
        "evidence_status": "IMPLEMENTED_UNVERIFIED",
        "status": "LOCAL_SCL_WINDOWS_MOSAICKED_BOUNDARY_APPROVAL_PENDING",
        "generated_at": _utc_now(),
        "boundary": {
            "path": boundary_path.as_posix(),
            "sha256": sha256_file(boundary_path),
        },
        "grid": {
            "crs": EQUAL_AREA_CRS,
            "resolution_m": float(resolution_m),
            "alignment": "PROVINCE_BOUNDS_FLOOR_CEIL_TO_RESOLUTION",
            "nodata": None,
        },
        "semantics": {
            "observed": "0_GAP_OR_OUTSIDE_1_ANY_CLEAR_SCL_OBSERVATION",
            "cause": "0_NONE_1_CLOUD_2_SHADOW_3_NODATA_4_OUTSIDE_FOOTPRINT",
            "clear_scl_classes": sorted(SCL_CLEAR),
            "cloud_scl_classes": sorted(SCL_CLOUD),
            "shadow_scl_classes": sorted(SCL_SHADOW),
            "nodata_scl_classes": sorted(SCL_NODATA),
            "multi_observation_rule": "ANY_CLEAR_WINS_ELSE_DOMINANT_CAUSE",
            "dominant_cause_tie_break": ["CLOUD", "SHADOW", "NODATA"],
        },
        "boundary_transform_repairs": boundary_repairs,
        "execution": execution,
        "limitations": [
            f"Mosaics represent only the {len(asset_records)} preserved local raw-SCL windows.",
            "OUTSIDE_FOOTPRINT means no preserved local SCL window, not cloud.",
            "The default 1000 m grid is an inventory grid, not a final 10/20 m science product.",
            "Boundary candidate requires competent-authority and statistical-use approval.",
        ],
        "cells": [asdict(cell) for cell in cells],
        "source_assets": asset_records,
    }
    target = output_dir / "province-year-scl-mosaic-manifest.json"
    _write_json(target, manifest)
    return target


def validate_local_scl_mosaic_manifest(
    manifest_path: Path,
    *,
    output_path: Path | None = None,
    allow_execution: bool = False,
) -> dict[str, Any]:
    """Independently re-open every manifest file and verify the 36-cell contract."""
    manifest_path = Path(manifest_path).resolve()
    root = manifest_path.parent
    document = json.loads(manifest_path.read_text(encoding="utf-8"))
    if document.get("schema_version") != MOSAIC_MANIFEST_SCHEMA:
        raise ProvinceEvidenceError("MOSAIC_MANIFEST_SCHEMA_MISMATCH")
    cells = document.get("cells")
    assets = document.get("source_assets")
    if not isinstance(cells, list) or len(cells) != 36:
        raise ProvinceEvidenceError("MOSAIC_MANIFEST_EXACT_36_CELLS_REQUIRED")
    if not isinstance(assets, list) or not assets:
        raise ProvinceEvidenceError("MOSAIC_MANIFEST_SOURCE_ASSETS_REQUIRED")
    expected = {(province, year) for province in PROVINCES for year in YEARS}
    actual = {(str(row.get("province_id")), int(row.get("year"))) for row in cells}
    if actual != expected:
        raise ProvinceEvidenceError("MOSAIC_MANIFEST_CELL_SCOPE_MISMATCH")

    boundary_ref = document.get("boundary") or {}
    boundary_path = Path(str(boundary_ref.get("path", ""))).resolve()
    if not boundary_path.is_file() or sha256_file(boundary_path) != boundary_ref.get("sha256"):
        raise ProvinceEvidenceError("MOSAIC_BOUNDARY_PIN_MISMATCH")
    boundaries = _boundary_index(boundary_path)

    unique_asset_paths = set()
    for asset in assets:
        path = Path(str(asset.get("path", ""))).resolve()
        if not path.is_file() or sha256_file(path) != asset.get("sha256"):
            raise ProvinceEvidenceError(f"MOSAIC_SOURCE_ASSET_PIN_MISMATCH:{path}")
        unique_asset_paths.add(path)
    if len(unique_asset_paths) != len(assets):
        raise ProvinceEvidenceError("MOSAIC_SOURCE_ASSET_DUPLICATE")

    total_boundary = 0
    total_observed = 0
    total_gap = 0
    total_causes = {"CLOUD": 0, "SHADOW": 0, "NODATA": 0, "OUTSIDE_FOOTPRINT": 0}
    for row in cells:
        province_id = str(row["province_id"])
        observed_path = (root / str(row["observed_path"])).resolve()
        cause_path = (root / str(row["cause_path"])).resolve()
        if sha256_file(observed_path) != row.get("observed_sha256"):
            raise ProvinceEvidenceError(f"OBSERVED_MOSAIC_PIN_MISMATCH:{province_id}:{row['year']}")
        if sha256_file(cause_path) != row.get("cause_sha256"):
            raise ProvinceEvidenceError(f"CAUSE_MOSAIC_PIN_MISMATCH:{province_id}:{row['year']}")
        with rasterio.open(observed_path) as observed_ds, rasterio.open(cause_path) as cause_ds:
            if (
                observed_ds.count != 1
                or cause_ds.count != 1
                or observed_ds.crs is None
                or observed_ds.crs.to_string() != EQUAL_AREA_CRS
                or cause_ds.crs != observed_ds.crs
                or cause_ds.transform != observed_ds.transform
                or cause_ds.shape != observed_ds.shape
                or observed_ds.nodata is not None
                or cause_ds.nodata is not None
            ):
                raise ProvinceEvidenceError(f"MOSAIC_GRID_CONTRACT_MISMATCH:{province_id}:{row['year']}")
            observed = observed_ds.read(1)
            cause = cause_ds.read(1)
            if not set(int(value) for value in np.unique(observed)).issubset({0, 1}):
                raise ProvinceEvidenceError(f"OBSERVED_MOSAIC_DOMAIN_INVALID:{province_id}:{row['year']}")
            if not set(int(value) for value in np.unique(cause)).issubset(set(range(5))):
                raise ProvinceEvidenceError(f"CAUSE_MOSAIC_DOMAIN_INVALID:{province_id}:{row['year']}")
            equal_area = shape(
                transform_geom("EPSG:4326", EQUAL_AREA_CRS, boundaries[province_id]["geometry"], precision=9)
            )
            if not equal_area.is_valid:
                equal_area = equal_area.buffer(0)
            inside = geometry_mask(
                [mapping(equal_area)], out_shape=observed_ds.shape, transform=observed_ds.transform,
                invert=True, all_touched=False,
            )
            if np.any(observed[~inside] != 0) or np.any(cause[~inside] != 0):
                raise ProvinceEvidenceError(f"MOSAIC_NONZERO_OUTSIDE_BOUNDARY:{province_id}:{row['year']}")
            if np.any(inside & (observed == 1) & (cause != 0)):
                raise ProvinceEvidenceError(f"MOSAIC_CAUSE_ON_OBSERVED:{province_id}:{row['year']}")
            gap = inside & (observed == 0)
            if np.any(gap & (cause == 0)):
                raise ProvinceEvidenceError(f"MOSAIC_UNCLASSIFIED_GAP:{province_id}:{row['year']}")
            boundary_count = int(np.count_nonzero(inside))
            observed_count = int(np.count_nonzero(inside & (observed == 1)))
            gap_count = int(np.count_nonzero(gap))
            measured_causes = {
                "CLOUD": int(np.count_nonzero(gap & (cause == 1))),
                "SHADOW": int(np.count_nonzero(gap & (cause == 2))),
                "NODATA": int(np.count_nonzero(gap & (cause == 3))),
                "OUTSIDE_FOOTPRINT": int(np.count_nonzero(gap & (cause == 4))),
            }
            if (
                boundary_count != int(row["boundary_pixels"])
                or observed_count != int(row["observed_pixels"])
                or gap_count != int(row["gap_pixels"])
                or measured_causes != row["cause_pixels"]
            ):
                raise ProvinceEvidenceError(f"MOSAIC_MANIFEST_COUNT_MISMATCH:{province_id}:{row['year']}")
            total_boundary += boundary_count
            total_observed += observed_count
            total_gap += gap_count
            for name, value in measured_causes.items():
                total_causes[name] += value

    result = {
        "schema_version": "province-year-scl-mosaic-validation/1.0",
        "status": "VERIFIED_REAL_LOCAL_ARTIFACTS_BOUNDARY_APPROVAL_PENDING",
        "validated_at": _utc_now(),
        "manifest_path": manifest_path.as_posix(),
        "manifest_sha256": sha256_file(manifest_path),
        "cell_count": len(cells),
        "source_asset_count": len(assets),
        "unique_source_asset_count": len(unique_asset_paths),
        "total_boundary_pixels": total_boundary,
        "total_observed_pixels": total_observed,
        "total_gap_pixels": total_gap,
        "observed_pct": round(total_observed * 100.0 / total_boundary, 6),
        "cause_pixels": total_causes,
        "checks": {
            "all_pins_match": True,
            "all_same_grid_per_cell": True,
            "all_epsg_6933": True,
            "all_nodata_unset": True,
            "all_value_domains_valid": True,
            "all_outside_boundary_zero": True,
            "all_gap_pixels_classified": True,
            "collector_invoked": bool((document.get("execution") or {}).get("collector_invoked")),
            "ledger_written": bool((document.get("execution") or {}).get("ledger_written")),
        },
    }
    if not allow_execution and (
        result["checks"]["collector_invoked"] or result["checks"]["ledger_written"]
    ):
        raise ProvinceEvidenceError("MOSAIC_MANIFEST_EXECUTION_SIDE_EFFECT_REPORTED")
    if output_path is not None:
        _write_json(Path(output_path), result)
    return result


def build_evidence_bundle(
    *,
    source_root: Path,
    output_dir: Path,
    resolution_m: float = 1000.0,
    boundary_timeout: float = 120.0,
    gistaru_timeout: float = 20.0,
    resume: bool = False,
) -> dict[str, Any]:
    """Run the bounded evidence preparation workflow and write its summary."""
    output_dir = Path(output_dir).resolve()
    if output_dir.exists() and any(output_dir.iterdir()) and not resume:
        raise ProvinceEvidenceError(f"OUTPUT_DIRECTORY_NOT_EMPTY:{output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    boundary = output_dir / "six-province-boundary-candidate.geojson"
    if not boundary.is_file():
        boundary = fetch_big_boundary_candidate(output_dir, timeout=boundary_timeout)
    gistaru = output_dir / "gistaru-service-discovery.json"
    if not gistaru.is_file():
        gistaru = probe_gistaru_services(output_dir, timeout=gistaru_timeout)
    mosaics = output_dir / "province-year-scl-mosaic-manifest.json"
    if not mosaics.is_file():
        mosaics = build_local_scl_mosaics(boundary, source_root, output_dir, resolution_m=resolution_m)
    summary = {
        "schema_version": "province-year-evidence-bundle/1.0",
        "status": "PARTIAL_BLOCKED_GISTARU_AND_BOUNDARY_APPROVAL",
        "generated_at": _utc_now(),
        "boundary_candidate": {
            "path": boundary.relative_to(output_dir).as_posix(),
            "sha256": sha256_file(boundary),
        },
        "gistaru_discovery": {
            "path": gistaru.relative_to(output_dir).as_posix(),
            "sha256": sha256_file(gistaru),
        },
        "scl_mosaics": {
            "path": mosaics.relative_to(output_dir).as_posix(),
            "sha256": sha256_file(mosaics),
            "cell_count": 36,
        },
        "execution": {
            "new_sentinel_downloads": 0,
            "collector_invoked": False,
            "ledger_written": False,
        },
    }
    summary_path = output_dir / "completion.json"
    _write_json(summary_path, summary)
    summary["completion_path"] = summary_path.as_posix()
    return summary
