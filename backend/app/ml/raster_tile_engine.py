"""Standalone High-Performance Raster Tile Engine for LCLUC Change and Classification Maps.

Supports:
1. Transitions rasters (uint16 codes 0..80, 65535 NoData)
2. Real source classification rasters (WorldCover, ESRI, or standard 9-class discrete)
3. Standard Web Mercator XYZ tiles (render_tile)
4. WMS-compliant bounding box rendering (render_bbox with Nearest-Neighbor)
5. Direct pixel query (query_pixel) returning exact integer class ID, class name,
   coordinates, and NoData flag from actual GeoTIFF rasters without screen RGB guessing.
"""
from __future__ import annotations

import io
import math
import threading
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

import numpy as np
from PIL import Image
import pyproj
import rasterio
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT
from rasterio.warp import transform_bounds
from rasterio.windows import Window, from_bounds

# Web Mercator constants (WGS 84 / Pseudo-Mercator, EPSG:3857)
EARTH_RADIUS = 6378137.0
ORIGIN_SHIFT = math.pi * EARTH_RADIUS  # 20037508.342789244
MAX_ZOOM = 24
MIN_ZOOM = 0
NODATA_VALUE = 65535

# Project standard 9 land cover class names (matching UI/GreenBlue_CODEX Section 3.2)
CLASS_NAMES = [
    'Water',
    'Trees',
    'Grass',
    'Flooded vegetation',
    'Crops',
    'Shrub & scrub',
    'Built area',
    'Bare ground',
    'Snow & ice',
]

# Project standard land cover color palette (matching frontend WORKFLOW_CLASS_COLORS)
# Index 0..8 corresponding to 9 land cover classes
WORKFLOW_CLASS_COLORS = [
    '#2563eb',  # 0: Water (Blue)
    '#15803d',  # 1: Trees / Forest (Deep green)
    '#84cc16',  # 2: Grassland (Light green)
    '#14b8a6',  # 3: Flooded vegetation / Wetland (Teal)
    '#eab308',  # 4: Crops (Yellow)
    '#a16207',  # 5: Shrub & scrub (Brown)
    '#dc2626',  # 6: Built area / Urban (Red)
    '#a8a29e',  # 7: Bare ground / Rock (Gray)
    '#a5d8f3',  # 8: Snow & ice (Light blue)
]

# Standard cross-walk mappings for external source products
WORLDCOVER_TO_CLASS: Dict[int, int] = {
    10: 1,   # Tree cover -> Trees
    20: 5,   # Shrubland -> Shrub & scrub
    30: 2,   # Grassland -> Grass
    40: 4,   # Cropland -> Crops
    50: 6,   # Built-up -> Built area
    60: 7,   # Bare / sparse vegetation -> Bare ground
    70: 8,   # Snow and ice -> Snow & ice
    80: 0,   # Permanent water bodies -> Water
    90: 3,   # Herbaceous wetland -> Flooded vegetation
    95: 1,   # Mangroves -> Trees
    100: 2,  # Moss and lichen -> Grass
    0: 255,  # NoData
}

ESRI_TO_CLASS: Dict[int, int] = {
    1: 0,   # Water
    2: 1,   # Trees
    4: 3,   # Flooded vegetation
    5: 4,   # Crops
    7: 6,   # Built area
    8: 7,   # Bare ground
    9: 8,   # Snow & ice
    11: 2,  # Grass
    0: 255, # NoData
}


def hex_to_rgb(hex_str: str) -> Tuple[int, int, int]:
    """Convert hex color string like '#2563eb' to (R, G, B) tuple."""
    hex_clean = hex_str.lstrip('#')
    return (
        int(hex_clean[0:2], 16),
        int(hex_clean[2:4], 16),
        int(hex_clean[4:6], 16),
    )


RGB_PALETTE: Tuple[Tuple[int, int, int], ...] = tuple(
    hex_to_rgb(c) for c in WORKFLOW_CLASS_COLORS
)


def tile_bounds_3857(z: int, x: int, y: int) -> Tuple[float, float, float, float]:
    """Calculate EPSG:3857 bounding box (min_x, min_y, max_x, max_y) for tile (z, x, y).

    Tile coordinates follow the standard Slippy map / OSM / MapLibre scheme:
    x in [0, 2^z - 1], y in [0, 2^z - 1].
    y=0 is northernmost, y=2^z-1 is southernmost.
    """
    validate_tile_coords(z, x, y)
    num_tiles = 1 << z
    tile_span = (2.0 * ORIGIN_SHIFT) / num_tiles
    min_x = -ORIGIN_SHIFT + x * tile_span
    max_x = -ORIGIN_SHIFT + (x + 1) * tile_span
    max_y = ORIGIN_SHIFT - y * tile_span
    min_y = ORIGIN_SHIFT - (y + 1) * tile_span
    return (min_x, min_y, max_x, max_y)


def tile_bounds_lnglat(z: int, x: int, y: int) -> Tuple[float, float, float, float]:
    """Calculate WGS84 EPSG:4326 bounding box (min_lon, min_lat, max_lon, max_lat)."""
    min_x, min_y, max_x, max_y = tile_bounds_3857(z, x, y)
    return transform_bounds('EPSG:3857', 'EPSG:4326', min_x, min_y, max_x, max_y)


def validate_tile_coords(z: int, x: int, y: int) -> None:
    """Validate tile coordinates z, x, y."""
    if not isinstance(z, int) or not isinstance(x, int) or not isinstance(y, int):
        raise TypeError('Tile coordinates z, x, y must be integers.')
    if not (MIN_ZOOM <= z <= MAX_ZOOM):
        raise ValueError(f'Zoom level {z} out of bounds [{MIN_ZOOM}, {MAX_ZOOM}].')
    max_coord = (1 << z) - 1
    if not (0 <= x <= max_coord):
        raise ValueError(f'Tile x={x} out of bounds [0, {max_coord}] for zoom {z}.')
    if not (0 <= y <= max_coord):
        raise ValueError(f'Tile y={y} out of bounds [0, {max_coord}] for zoom {z}.')


def _create_empty_png(width: int = 256, height: int = 256) -> bytes:
    """Precompute a fully transparent RGBA PNG."""
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format='PNG', compress_level=1)
    return buf.getvalue()


EMPTY_TILE_PNG = _create_empty_png(256, 256)


@lru_cache(maxsize=32)
def get_transition_lut(
    mode: str = 'changes_only',
    to_class: Optional[int] = None,
    from_class: Optional[int] = None,
    alpha: int = 255,
    num_classes: int = 9,
) -> np.ndarray:
    """Build a precomputed 65536x4 uint8 lookup table (LUT) for transition codes.

    Transition code encoding (from analyze_change):
    code = from_class * num_classes + to_class (0 <= code < num_classes^2)
    nodata = 65535
    """
    lut = np.zeros((65536, 4), dtype=np.uint8)

    for code in range(num_classes * num_classes):
        fc = code // num_classes
        tc = code % num_classes

        # Filter check
        if to_class is not None and tc != to_class:
            continue
        if from_class is not None and fc != from_class:
            continue

        if mode == 'changes_only':
            if fc == tc:
                # Unchanged pixel -> transparent
                continue
            color = RGB_PALETTE[tc % len(RGB_PALETTE)]
            lut[code, 0] = color[0]
            lut[code, 1] = color[1]
            lut[code, 2] = color[2]
            lut[code, 3] = alpha
        elif mode == 'all':
            color = RGB_PALETTE[tc % len(RGB_PALETTE)]
            lut[code, 0] = color[0]
            lut[code, 1] = color[1]
            lut[code, 2] = color[2]
            lut[code, 3] = alpha
        elif mode == 'from_class':
            # Color by origin class
            color = RGB_PALETTE[fc % len(RGB_PALETTE)]
            lut[code, 0] = color[0]
            lut[code, 1] = color[1]
            lut[code, 2] = color[2]
            lut[code, 3] = alpha

    # 65535 (NODATA) and 255 remain [0, 0, 0, 0]
    return lut


@lru_cache(maxsize=32)
def get_discrete_lut(
    scheme: str = 'project_9class',
    alpha: int = 255,
) -> np.ndarray:
    """Build a precomputed 65536x4 uint8 lookup table for discrete land cover classification.

    Supported schemes:
    - 'project_9class': raw values 0..8 mapped to RGB_PALETTE[0..8]
    - 'worldcover': raw values (10, 20, ..., 80, 90) mapped via WORLDCOVER_TO_CLASS
    - 'esri': raw values (1, 2, 4, 5, ...) mapped via ESRI_TO_CLASS
    - 255 and 65535 are transparent NoData (alpha=0).
    """
    lut = np.zeros((65536, 4), dtype=np.uint8)

    if scheme == 'project_9class':
        for c in range(min(9, len(RGB_PALETTE))):
            color = RGB_PALETTE[c]
            lut[c, 0] = color[0]
            lut[c, 1] = color[1]
            lut[c, 2] = color[2]
            lut[c, 3] = alpha
    elif scheme == 'worldcover':
        for raw_val, target_c in WORLDCOVER_TO_CLASS.items():
            if target_c != 255:
                color = RGB_PALETTE[target_c % len(RGB_PALETTE)]
                lut[raw_val, 0] = color[0]
                lut[raw_val, 1] = color[1]
                lut[raw_val, 2] = color[2]
                lut[raw_val, 3] = alpha
    elif scheme == 'esri':
        for raw_val, target_c in ESRI_TO_CLASS.items():
            if target_c != 255:
                color = RGB_PALETTE[target_c % len(RGB_PALETTE)]
                lut[raw_val, 0] = color[0]
                lut[raw_val, 1] = color[1]
                lut[raw_val, 2] = color[2]
                lut[raw_val, 3] = alpha

    return lut


class RasterTileEngine:
    """High-performance windowed raster tile & WMS engine for transitions and classification rasters.

    Maintains thread-safe dataset metadata and serves 256x256 Web Mercator PNG tiles and WMS GetMap bboxes.
    Uses rasterio windowed reads with WarpedVRT to guarantee bounded memory usage.
    """

    def __init__(
        self,
        tif_path: Union[str, Path],
        num_classes: int = 9,
        scheme: Optional[str] = None,
    ):
        self.tif_path = Path(tif_path).resolve()
        if not self.tif_path.is_file():
            raise FileNotFoundError(f'Raster file not found: {self.tif_path}')
        self.num_classes = num_classes
        self._lock = threading.Lock()

        # Cache dataset metadata
        with rasterio.open(self.tif_path) as src:
            self.crs = src.crs
            self.nodata = src.nodata if src.nodata is not None else NODATA_VALUE
            self.src_bounds = src.bounds
            self.src_transform = src.transform
            self.src_width = src.width
            self.src_height = src.height

            # Transform raster bounds to EPSG:3857 for fast tile intersection testing
            if src.crs is not None and str(src.crs).upper() not in ('EPSG:3857', 'PROJCS["WGS 84 / PSEUDO-MERCATOR"'):
                self.bounds_3857 = transform_bounds(
                    src.crs, 'EPSG:3857',
                    src.bounds.left, src.bounds.bottom,
                    src.bounds.right, src.bounds.top
                )
            else:
                self.bounds_3857 = (
                    src.bounds.left, src.bounds.bottom,
                    src.bounds.right, src.bounds.top
                )

        # Coordinate transformers
        if self.crs is not None:
            self.transformer_from_wgs84 = pyproj.Transformer.from_crs('EPSG:4326', self.crs, always_xy=True)
            self.transformer_to_wgs84 = pyproj.Transformer.from_crs(self.crs, 'EPSG:4326', always_xy=True)
        else:
            self.transformer_from_wgs84 = None
            self.transformer_to_wgs84 = None

        # Determine classification scheme
        if scheme:
            self.scheme = scheme
        else:
            name_lower = self.tif_path.name.lower()
            if 'transition' in name_lower:
                self.scheme = 'transitions'
            elif 'worldcover' in name_lower:
                self.scheme = 'worldcover'
            elif 'esri' in name_lower:
                self.scheme = 'esri'
            else:
                self.scheme = 'project_9class'

    def intersects(self, tile_min_x: float, tile_min_y: float, tile_max_x: float, tile_max_y: float) -> bool:
        """Check whether tile EPSG:3857 bounds intersect the raster's EPSG:3857 bounds."""
        r_min_x, r_min_y, r_max_x, r_max_y = self.bounds_3857
        if tile_max_x <= r_min_x or tile_min_x >= r_max_x:
            return False
        if tile_max_y <= r_min_y or tile_min_y >= r_max_y:
            return False
        return True

    def get_raster_info(self) -> Dict[str, Any]:
        """Return spatial metadata for frontend map alignment."""
        min_lon, min_lat, max_lon, max_lat = transform_bounds(
            'EPSG:3857', 'EPSG:4326', *self.bounds_3857
        )
        return {
            'crs': str(self.crs),
            'width': self.src_width,
            'height': self.src_height,
            'nodata': self.nodata,
            'bounds_3857': list(self.bounds_3857),
            'bounds_wgs84': [min_lon, min_lat, max_lon, max_lat],
            'num_classes': self.num_classes,
            'scheme': self.scheme,
            'class_names': CLASS_NAMES,
            'colors': WORKFLOW_CLASS_COLORS,
        }

    def render_bbox(
        self,
        min_x: float,
        min_y: float,
        max_x: float,
        max_y: float,
        srs: str = 'EPSG:3857',
        width: int = 256,
        height: int = 256,
        mode: str = 'changes_only',
        to_class: Optional[int] = None,
        from_class: Optional[int] = None,
        opacity: float = 1.0,
    ) -> bytes:
        """Render an arbitrary spatial bounding box to a PNG image using Nearest-Neighbor sampling.

        Supports standard WMS GetMap rendering in EPSG:3857 or EPSG:4326.
        """
        # Transform bounds if srs is EPSG:4326 to EPSG:3857 for bounds check
        if srs.upper() in ('EPSG:4326', 'CRS:84'):
            b3857 = transform_bounds('EPSG:4326', 'EPSG:3857', min_x, min_y, max_x, max_y)
        else:
            b3857 = (min_x, min_y, max_x, max_y)

        if not self.intersects(*b3857):
            return _create_empty_png(width, height)

        alpha_byte = int(round(max(0.0, min(1.0, opacity)) * 255))
        if self.scheme == 'transitions':
            lut = get_transition_lut(
                mode=mode,
                to_class=to_class,
                from_class=from_class,
                alpha=alpha_byte,
                num_classes=self.num_classes,
            )
        else:
            lut = get_discrete_lut(scheme=self.scheme, alpha=alpha_byte)

        with rasterio.open(self.tif_path) as src:
            with WarpedVRT(
                src,
                crs=srs,
                resampling=Resampling.nearest,
                nodata=self.nodata,
            ) as vrt:
                # Compute intersection with VRT bounds in target srs
                v_min_x, v_min_y, v_max_x, v_max_y = vrt.bounds
                i_min_x = max(min_x, v_min_x)
                i_max_x = min(max_x, v_max_x)
                i_min_y = max(min_y, v_min_y)
                i_max_y = min(max_y, v_max_y)

                if i_min_x >= i_max_x or i_min_y >= i_max_y:
                    return _create_empty_png(width, height)

                span_w = max_x - min_x
                span_h = max_y - min_y

                px_min_x = int(round((i_min_x - min_x) / span_w * width))
                px_max_x = int(round((i_max_x - min_x) / span_w * width))
                px_min_y = int(round((max_y - i_max_y) / span_h * height))
                px_max_y = int(round((max_y - i_min_y) / span_h * height))

                px_min_x = max(0, min(width, px_min_x))
                px_max_x = max(px_min_x, min(width, px_max_x))
                px_min_y = max(0, min(height, px_min_y))
                px_max_y = max(px_min_y, min(height, px_max_y))

                sub_w = px_max_x - px_min_x
                sub_h = px_max_y - px_min_y
                if sub_w <= 0 or sub_h <= 0:
                    return _create_empty_png(width, height)

                data = np.full((height, width), NODATA_VALUE, dtype=np.uint16)

                window = from_bounds(i_min_x, i_min_y, i_max_x, i_max_y, transform=vrt.transform)
                window = window.intersection(Window(0, 0, vrt.width, vrt.height))

                sub_data = vrt.read(
                    1,
                    window=window,
                    out_shape=(sub_h, sub_w),
                    resampling=Resampling.nearest,
                )
                data[px_min_y:px_min_y + sub_h, px_min_x:px_min_x + sub_w] = sub_data

        rgba = lut[data]
        if not np.any(rgba[:, :, 3]):
            return _create_empty_png(width, height)

        img = Image.fromarray(rgba, mode='RGBA')
        buf = io.BytesIO()
        img.save(buf, format='PNG', compress_level=1)
        return buf.getvalue()

    def render_tile(
        self,
        z: int,
        x: int,
        y: int,
        mode: str = 'changes_only',
        to_class: Optional[int] = None,
        from_class: Optional[int] = None,
        opacity: float = 1.0,
        tile_size: int = 256,
    ) -> bytes:
        """Render a single Web Mercator PNG tile (z, x, y)."""
        validate_tile_coords(z, x, y)
        t_min_x, t_min_y, t_max_x, t_max_y = tile_bounds_3857(z, x, y)
        return self.render_bbox(
            min_x=t_min_x,
            min_y=t_min_y,
            max_x=t_max_x,
            max_y=t_max_y,
            srs='EPSG:3857',
            width=tile_size,
            height=tile_size,
            mode=mode,
            to_class=to_class,
            from_class=from_class,
            opacity=opacity,
        )

    def query_pixel(self, lng: float, lat: float) -> Dict[str, Any]:
        """Perform authoritative point query on the actual GeoTIFF raster.

        Extracts exact integer pixel value and returns metadata without screen RGB guessing.
        """
        if not (-180.0 <= lng <= 180.0) or not (-90.0 <= lat <= 90.0):
            raise ValueError(f'Invalid coordinates lng={lng}, lat={lat}')

        if self.transformer_from_wgs84 is None:
            raise RuntimeError('Raster CRS not defined for coordinate transformation.')

        native_x, native_y = self.transformer_from_wgs84.transform(lng, lat)

        # Check bounds
        r_left, r_bottom, r_right, r_top = (
            self.src_bounds.left,
            self.src_bounds.bottom,
            self.src_bounds.right,
            self.src_bounds.top,
        )
        if not (r_left <= native_x <= r_right and r_bottom <= native_y <= r_top):
            return {
                'lat': lat,
                'lng': lng,
                'valid': False,
                'nodata': True,
                'reason': 'outside_raster_bounds',
                'native_coords': [round(native_x, 3), round(native_y, 3)],
                'native_crs': str(self.crs),
                'source_file': str(self.tif_path),
            }

        # Convert to pixel col, row
        col, row = ~self.src_transform @ (native_x, native_y)
        c_int = int(math.floor(col))
        r_int = int(math.floor(row))

        if not (0 <= c_int < self.src_width and 0 <= r_int < self.src_height):
            return {
                'lat': lat,
                'lng': lng,
                'valid': False,
                'nodata': True,
                'reason': 'outside_raster_dimensions',
                'native_coords': [round(native_x, 3), round(native_y, 3)],
                'native_crs': str(self.crs),
                'source_file': str(self.tif_path),
            }

        with rasterio.open(self.tif_path) as src:
            raw_val = int(src.read(1, window=Window(c_int, r_int, 1, 1))[0, 0])

        is_nodata = (
            (raw_val == self.nodata)
            or (raw_val in (255, 65535))
            or (self.scheme == 'worldcover' and raw_val == 0)
        )

        res_x = round(abs(self.src_transform.a), 3)
        res_y = round(abs(self.src_transform.e), 3)

        if is_nodata:
            return {
                'lat': lat,
                'lng': lng,
                'valid': False,
                'nodata': True,
                'raw_value': raw_val,
                'class_id': None,
                'class_name': 'NoData',
                'color': None,
                'pixel_row': r_int,
                'pixel_col': c_int,
                'native_coords': [round(native_x, 3), round(native_y, 3)],
                'native_crs': str(self.crs),
                'pixel_resolution_m': [res_x, res_y],
                'source_file': str(self.tif_path),
                'scheme': self.scheme,
            }

        from_class_name = None
        if self.scheme == 'transitions':
            fc = raw_val // self.num_classes
            tc = raw_val % self.num_classes
            class_id = tc
            class_name = CLASS_NAMES[tc % len(CLASS_NAMES)]
            from_class_name = CLASS_NAMES[fc % len(CLASS_NAMES)]
            color = WORKFLOW_CLASS_COLORS[tc % len(WORKFLOW_CLASS_COLORS)]
        elif self.scheme == 'worldcover':
            class_id = WORLDCOVER_TO_CLASS.get(raw_val, 7)
            class_name = CLASS_NAMES[class_id]
            color = WORKFLOW_CLASS_COLORS[class_id]
        elif self.scheme == 'esri':
            class_id = ESRI_TO_CLASS.get(raw_val, 7)
            class_name = CLASS_NAMES[class_id]
            color = WORKFLOW_CLASS_COLORS[class_id]
        else:
            class_id = raw_val % len(CLASS_NAMES)
            class_name = CLASS_NAMES[class_id]
            color = WORKFLOW_CLASS_COLORS[class_id]

        result = {
            'lat': lat,
            'lng': lng,
            'valid': True,
            'nodata': False,
            'raw_value': raw_val,
            'class_id': class_id,
            'class_name': class_name,
            'color': color,
            'pixel_row': r_int,
            'pixel_col': c_int,
            'native_coords': [round(native_x, 3), round(native_y, 3)],
            'native_crs': str(self.crs),
            'pixel_resolution_m': [res_x, res_y],
            'source_file': str(self.tif_path),
            'scheme': self.scheme,
        }
        if from_class_name is not None:
            result['from_class_name'] = from_class_name
            result['transition_name'] = f'{from_class_name} -> {class_name}'

        return result
