"""Standalone High-Performance Multi-Layer Raster Tile Engine for LCLUC Maps.

Supports 5 distinct layer types (UI/GreenBlue_CODEX Section 4 & 5):
1. 'classification': Annual 9-class discrete land cover (0..8) & WorldCover (10..90)
2. 'quality_mask': Binary validity mask (0: Cloud/Invalid, 1: Valid)
3. 'observation_count': Pixel-wise valid observation count (0..N)
4. 'common_valid': T1/T2 Common Valid Mask (1: Valid in both T1 and T2, 0: Cloud gap/Invalid)
5. 'transitions': Multi-temporal change transitions (uint16 codes 0..80, 65536 LUT mapping)

Features:
- O(1) bounded memory windowed reads via rasterio and WarpedVRT
- Precomputed 65536x4 uint8 vectorized LUTs for sub-millisecond color mapping
- Strict Nearest-Neighbor resampling preserving categorical integer integrity
- Complete NoData (255, 65535) and customizable transparency handling
- Standard Web Mercator (EPSG:3857) Slippy tiles and WMS 1.3.0 GetMap BBOX rendering
- Native 1x1 pixel direct inspection without screen RGB guessing
"""
from __future__ import annotations

import io
import math
import threading
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

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

# Supported Layer Types
LAYER_CLASSIFICATION = 'classification'
LAYER_QUALITY_MASK = 'quality_mask'
LAYER_OBSERVATION_COUNT = 'observation_count'
LAYER_COMMON_VALID = 'common_valid'
LAYER_TRANSITIONS = 'transitions'

SUPPORTED_LAYER_TYPES = [
    LAYER_CLASSIFICATION,
    LAYER_QUALITY_MASK,
    LAYER_OBSERVATION_COUNT,
    LAYER_COMMON_VALID,
    LAYER_TRANSITIONS,
]

# Standard 9 land cover class names (UI/GreenBlue CODEX Section 3.2)
CLASS_NAMES = [
    'Water',
    'Trees',
    'Grassland',
    'Flooded vegetation',
    'Crops',
    'Shrub & scrub',
    'Built area',
    'Bare ground',
    'Snow & ice',
]

# Standard 9 land cover colors (#hex)
WORKFLOW_CLASS_COLORS = [
    '#2563eb',  # 0: Water (Blue)
    '#15803d',  # 1: Trees / Forest (Deep green)
    '#84cc16',  # 2: Grassland (Light green)
    '#14b8a6',  # 3: Flooded vegetation / Wetland (Teal)
    '#eab308',  # 4: Crops (Yellow)
    '#a16207',  # 5: Shrub & scrub (Brown)
    '#dc2626',  # 6: Built-up / Urban (Red)
    '#a8a29e',  # 7: Bare ground / Rock (Gray)
    '#a5d8f3',  # 8: Snow & ice (Light blue)
]


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

# WorldCover 10m raw codes to standard 9-class mapping
WORLDCOVER_TO_CLASS = {
    10: 1,  # Tree cover -> Trees
    20: 5,  # Shrubland -> Shrub & scrub
    30: 2,  # Grassland -> Grassland
    40: 4,  # Cropland -> Crops
    50: 6,  # Built-up -> Built area
    60: 7,  # Bare / sparse vegetation -> Bare ground
    70: 8,  # Snow and ice -> Snow / Ice
    80: 0,  # Permanent water bodies -> Water
    90: 3,  # Herbaceous wetland -> Flooded vegetation
}

# ESRI 10m Land Cover codes mapping
ESRI_TO_CLASS = {
    1: 0,   # Water -> Water
    2: 1,   # Trees -> Trees
    4: 3,   # Flooded vegetation -> Flooded vegetation
    5: 4,   # Crops -> Crops
    7: 6,   # Built area -> Built area
    8: 7,   # Bare ground -> Bare ground
    9: 8,   # Snow/Ice -> Snow / Ice
    10: 7,  # Clouds -> Bare ground / neutral
    11: 2,  # Rangeland -> Grassland
}

# Quality Mask Colors (Section 4 & 133):
# 0: Cloud / Invalid -> Red (#ef4444)
# 1: Valid / Clear -> Green (#22c55e)
QUALITY_MASK_COLORS = {
    0: (239, 68, 68),   # Cloud / Invalid
    1: (34, 197, 94),   # Valid / Clear
}

# Common Valid Colors:
# 0: Cloud gap / Invalid in either T1 or T2 -> Red (#ef4444)
# 1: Common Valid in both T1 and T2 -> Blue (#3b82f6)
COMMON_VALID_COLORS = {
    0: (239, 68, 68),   # Invalid in T1 or T2
    1: (59, 130, 246),  # Common Valid
}

# Observation Count Ramp Colors (0..6+ observations):
OBSERVATION_COUNT_COLORS = {
    0: (153, 27, 27),   # 0 obs (Dark red)
    1: (239, 68, 68),   # 1 obs (Red)
    2: (249, 115, 22),  # 2 obs (Orange)
    3: (234, 179, 8),   # 3 obs (Yellow)
    4: (132, 204, 22),  # 4 obs (Light green)
    5: (34, 197, 94),   # 5 obs (Green)
    6: (21, 128, 61),   # 6+ obs (Deep forest green)
}


def tile_bounds_3857(z: int, x: int, y: int) -> Tuple[float, float, float, float]:
    """Calculate EPSG:3857 bounding box (min_x, min_y, max_x, max_y) for tile (z, x, y)."""
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


# -----------------------------------------------------------------------------
# Precomputed Lookup Tables (LUTs) for Multi-Layer Rendering
# -----------------------------------------------------------------------------

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

    Rendering modes:
    - 'changes_only': Unchanged pixels (from_class == to_class) are transparent (alpha=0).
                      Changed pixels are colored with the target class color.
    - 'all': Both changed and unchanged pixels are colored with to_class color.
    - 'from_class': Color by origin class.
    """
    lut = np.zeros((65536, 4), dtype=np.uint8)

    for code in range(num_classes * num_classes):
        fc = code // num_classes
        tc = code % num_classes

        if to_class is not None and tc != to_class:
            continue
        if from_class is not None and fc != from_class:
            continue

        if mode == 'changes_only':
            if fc == tc:
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
            color = RGB_PALETTE[fc % len(RGB_PALETTE)]
            lut[code, 0] = color[0]
            lut[code, 1] = color[1]
            lut[code, 2] = color[2]
            lut[code, 3] = alpha

    # 255 and 65535 (NODATA) remain [0, 0, 0, 0]
    return lut


@lru_cache(maxsize=32)
def get_classification_lut(
    alpha: int = 255,
    num_classes: int = 9,
) -> np.ndarray:
    """Build a precomputed 65536x4 uint8 LUT for discrete land cover classification.

    Maps 0..8 standard classes and 10..90 ESA WorldCover codes to standard colors.
    Explicitly ensures 255 and 65535 NoData are completely transparent.
    """
    lut = np.zeros((65536, 4), dtype=np.uint8)

    # 1. Standard 0..8 classes
    for c in range(min(num_classes, len(RGB_PALETTE))):
        color = RGB_PALETTE[c]
        lut[c, 0] = color[0]
        lut[c, 1] = color[1]
        lut[c, 2] = color[2]
        lut[c, 3] = alpha

    # 2. ESA WorldCover codes remap
    for wc_code, c in WORLDCOVER_TO_CLASS.items():
        color = RGB_PALETTE[c % len(RGB_PALETTE)]
        lut[wc_code, 0] = color[0]
        lut[wc_code, 1] = color[1]
        lut[wc_code, 2] = color[2]
        lut[wc_code, 3] = alpha

    # 3. Explicit NoData (255, 65535) remain [0, 0, 0, 0]
    lut[255] = [0, 0, 0, 0]
    lut[65535] = [0, 0, 0, 0]
    return lut


@lru_cache(maxsize=32)
def get_quality_mask_lut(
    mode: str = 'all',
    alpha: int = 255,
) -> np.ndarray:
    """Build a precomputed 65536x4 uint8 LUT for binary quality mask.

    Semantics (Section 4 & 133):
    - 0: Cloud / Invalid pixel (Red: #ef4444)
    - 1: Valid / Clear pixel (Green: #22c55e)

    Modes:
    - 'all': Both 0 (Red) and 1 (Green) colored.
    - 'invalid_only' / 'cloud_only': 0 is colored Red, 1 is transparent (useful for map overlays).
    - 'valid_only': 0 is transparent, 1 is colored Green.
    - NoData (255, 65535): completely transparent.
    """
    lut = np.zeros((65536, 4), dtype=np.uint8)

    # Value 0: Cloud / Invalid
    if mode in ('all', 'invalid_only', 'cloud_only'):
        c0 = QUALITY_MASK_COLORS[0]
        lut[0, 0] = c0[0]
        lut[0, 1] = c0[1]
        lut[0, 2] = c0[2]
        lut[0, 3] = alpha

    # Value 1: Valid
    if mode in ('all', 'valid_only'):
        c1 = QUALITY_MASK_COLORS[1]
        lut[1, 0] = c1[0]
        lut[1, 1] = c1[1]
        lut[1, 2] = c1[2]
        lut[1, 3] = alpha

    # Explicit NoData
    lut[255] = [0, 0, 0, 0]
    lut[65535] = [0, 0, 0, 0]
    return lut


@lru_cache(maxsize=32)
def get_observation_count_lut(
    mode: str = 'all',
    alpha: int = 255,
) -> np.ndarray:
    """Build a precomputed 65536x4 uint8 LUT for observation count raster.

    Ramp from 0 observations (dark red) through 6+ observations (deep green).
    NoData (255, 65535): completely transparent.
    """
    lut = np.zeros((65536, 4), dtype=np.uint8)

    for cnt in range(256):
        if cnt == 0:
            if mode != 'valid_only':
                c = OBSERVATION_COUNT_COLORS[0]
                lut[0, 0] = c[0]
                lut[0, 1] = c[1]
                lut[0, 2] = c[2]
                lut[0, 3] = alpha
        elif cnt in OBSERVATION_COUNT_COLORS:
            c = OBSERVATION_COUNT_COLORS[cnt]
            lut[cnt, 0] = c[0]
            lut[cnt, 1] = c[1]
            lut[cnt, 2] = c[2]
            lut[cnt, 3] = alpha
        elif cnt < 255:
            # 6+ observations saturate at deep forest green
            c = OBSERVATION_COUNT_COLORS[6]
            lut[cnt, 0] = c[0]
            lut[cnt, 1] = c[1]
            lut[cnt, 2] = c[2]
            lut[cnt, 3] = alpha

    # Explicit NoData
    lut[255] = [0, 0, 0, 0]
    lut[65535] = [0, 0, 0, 0]
    return lut


@lru_cache(maxsize=32)
def get_common_valid_lut(
    mode: str = 'all',
    alpha: int = 255,
) -> np.ndarray:
    """Build a precomputed 65536x4 uint8 LUT for T1/T2 Common Valid Mask.

    Semantics:
    - 0: Cloud gap in either T1 or T2 (Red: #ef4444)
    - 1: Common Valid in both T1 and T2 (Blue: #3b82f6)

    Modes:
    - 'all': Both 0 and 1 colored.
    - 'invalid_only': 0 is colored Red, 1 is transparent.
    - 'valid_only': 0 is transparent, 1 is colored Blue.
    - NoData (255, 65535): completely transparent.
    """
    lut = np.zeros((65536, 4), dtype=np.uint8)

    if mode in ('all', 'invalid_only', 'gap_only'):
        c0 = COMMON_VALID_COLORS[0]
        lut[0, 0] = c0[0]
        lut[0, 1] = c0[1]
        lut[0, 2] = c0[2]
        lut[0, 3] = alpha

    if mode in ('all', 'valid_only'):
        c1 = COMMON_VALID_COLORS[1]
        lut[1, 0] = c1[0]
        lut[1, 1] = c1[1]
        lut[1, 2] = c1[2]
        lut[1, 3] = alpha

    # Explicit NoData
    lut[255] = [0, 0, 0, 0]
    lut[65535] = [0, 0, 0, 0]
    return lut


def get_layer_lut(
    layer_type: str,
    mode: Optional[str] = None,
    to_class: Optional[int] = None,
    from_class: Optional[int] = None,
    alpha: int = 255,
    num_classes: int = 9,
) -> np.ndarray:
    """Unified LUT dispatcher for all supported layer types."""
    if layer_type == LAYER_CLASSIFICATION:
        return get_classification_lut(alpha=alpha, num_classes=num_classes)
    elif layer_type == LAYER_QUALITY_MASK:
        return get_quality_mask_lut(mode=mode or 'all', alpha=alpha)
    elif layer_type == LAYER_OBSERVATION_COUNT:
        return get_observation_count_lut(mode=mode or 'all', alpha=alpha)
    elif layer_type == LAYER_COMMON_VALID:
        return get_common_valid_lut(mode=mode or 'all', alpha=alpha)
    else:  # LAYER_TRANSITIONS
        return get_transition_lut(
            mode=mode or 'changes_only',
            to_class=to_class,
            from_class=from_class,
            alpha=alpha,
            num_classes=num_classes,
        )


# -----------------------------------------------------------------------------
# Multi-Layer RasterTileEngine
# -----------------------------------------------------------------------------

class RasterTileEngine:
    """High-performance windowed raster tile engine for multi-layer LCLUC rasters.

    Maintains thread-safe dataset metadata and serves 256x256 Web Mercator PNG tiles.
    Uses rasterio windowed reads with WarpedVRT to guarantee bounded memory usage.
    Supports single rasters and dual rasters (for on-the-fly T1/T2 common valid computation).
    """

    def __init__(
        self,
        tif_path: Union[str, Path],
        tif_path_t2: Optional[Union[str, Path]] = None,
        layer_type: str = LAYER_TRANSITIONS,
        num_classes: int = 9,
    ):
        self.tif_path = Path(tif_path).resolve()
        if not self.tif_path.is_file():
            raise FileNotFoundError(f'Raster file not found: {self.tif_path}')

        self.tif_path_t2: Optional[Path] = None
        if tif_path_t2 is not None:
            p2 = Path(tif_path_t2).resolve()
            if not p2.is_file():
                raise FileNotFoundError(f'Second raster file not found: {p2}')
            self.tif_path_t2 = p2

        self.layer_type = layer_type
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
            if src.crs is not None and str(src.crs).upper() not in (
                'EPSG:3857', 'PROJCS["WGS 84 / PSEUDO-MERCATOR"'
            ):
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
            'layer_type': self.layer_type,
            'width': self.src_width,
            'height': self.src_height,
            'nodata': self.nodata,
            'bounds_3857': list(self.bounds_3857),
            'bounds_wgs84': [min_lon, min_lat, max_lon, max_lat],
            'num_classes': self.num_classes,
        }

    def render_tile(
        self,
        z: int,
        x: int,
        y: int,
        layer_type: Optional[str] = None,
        mode: Optional[str] = None,
        to_class: Optional[int] = None,
        from_class: Optional[int] = None,
        opacity: float = 1.0,
        tile_size: int = 256,
    ) -> bytes:
        """Render a single Web Mercator PNG tile (z, x, y) for the requested layer type.

        Parameters:
            z, x, y: Standard Web Mercator tile coordinates.
            layer_type: 'classification', 'quality_mask', 'observation_count', 'common_valid', 'transitions'.
            mode: Layer-specific mode filter (e.g. 'changes_only', 'all', 'invalid_only', 'valid_only').
            to_class: Optional filter for target class (0..8) in transitions.
            from_class: Optional filter for origin class (0..8) in transitions.
            opacity: Opacity float between 0.0 and 1.0.
            tile_size: Pixel dimension of the tile (default 256).

        Returns:
            PNG byte stream.
        """
        validate_tile_coords(z, x, y)
        t_min_x, t_min_y, t_max_x, t_max_y = tile_bounds_3857(z, x, y)

        # 1. Out-of-bounds fast rejection
        if not self.intersects(t_min_x, t_min_y, t_max_x, t_max_y):
            return EMPTY_TILE_PNG if tile_size == 256 else _create_empty_png(tile_size, tile_size)

        # 2. Compute intersection in EPSG:3857
        r_min_x, r_min_y, r_max_x, r_max_y = self.bounds_3857
        i_min_x = max(t_min_x, r_min_x)
        i_max_x = min(t_max_x, r_max_x)
        i_min_y = max(t_min_y, r_min_y)
        i_max_y = min(t_max_y, r_max_y)

        if i_min_x >= i_max_x or i_min_y >= i_max_y:
            return EMPTY_TILE_PNG if tile_size == 256 else _create_empty_png(tile_size, tile_size)

        # Sub-tile pixel coordinates
        tile_w = t_max_x - t_min_x
        tile_h = t_max_y - t_min_y

        px_min_x = int(round((i_min_x - t_min_x) / tile_w * tile_size))
        px_max_x = int(round((i_max_x - t_min_x) / tile_w * tile_size))
        px_min_y = int(round((t_max_y - i_max_y) / tile_h * tile_size))
        px_max_y = int(round((t_max_y - i_min_y) / tile_h * tile_size))

        # Clamp to tile boundary
        px_min_x = max(0, min(tile_size, px_min_x))
        px_max_x = max(px_min_x, min(tile_size, px_max_x))
        px_min_y = max(0, min(tile_size, px_min_y))
        px_max_y = max(px_min_y, min(tile_size, px_max_y))

        sub_w = px_max_x - px_min_x
        sub_h = px_max_y - px_min_y
        if sub_w <= 0 or sub_h <= 0:
            return EMPTY_TILE_PNG if tile_size == 256 else _create_empty_png(tile_size, tile_size)

        # Effective layer & mode
        eff_layer = layer_type or self.layer_type
        eff_mode = mode or ('changes_only' if eff_layer == LAYER_TRANSITIONS else 'all')

        # Initialize full tile buffer with NODATA
        data = np.full((tile_size, tile_size), NODATA_VALUE, dtype=np.uint16)

        alpha_byte = int(round(max(0.0, min(1.0, opacity)) * 255))
        lut = get_layer_lut(
            eff_layer,
            mode=eff_mode,
            to_class=to_class,
            from_class=from_class,
            alpha=alpha_byte,
            num_classes=self.num_classes,
        )

        # 3. Read raster data
        if eff_layer == LAYER_COMMON_VALID and self.tif_path_t2 is not None:
            # Dual raster on-the-fly common valid computation
            with rasterio.open(self.tif_path) as src1, rasterio.open(self.tif_path_t2) as src2:
                with WarpedVRT(src1, crs='EPSG:3857', resampling=Resampling.nearest, nodata=self.nodata) as vrt1, \
                     WarpedVRT(src2, crs='EPSG:3857', resampling=Resampling.nearest, nodata=src2.nodata) as vrt2:
                    win1 = from_bounds(i_min_x, i_min_y, i_max_x, i_max_y, transform=vrt1.transform)
                    win1 = win1.intersection(Window(0, 0, vrt1.width, vrt1.height))
                    sub1 = vrt1.read(1, window=win1, out_shape=(sub_h, sub_w), resampling=Resampling.nearest)

                    win2 = from_bounds(i_min_x, i_min_y, i_max_x, i_max_y, transform=vrt2.transform)
                    win2 = win2.intersection(Window(0, 0, vrt2.width, vrt2.height))
                    sub2 = vrt2.read(1, window=win2, out_shape=(sub_h, sub_w), resampling=Resampling.nearest)

                    # Common valid = 1 if both valid (1), else 0. Preserving NoData.
                    is_nodata = (sub1 == self.nodata) | (sub2 == src2.nodata) | (sub1 == 255) | (sub2 == 255)
                    common = np.where((sub1 == 1) & (sub2 == 1), 1, 0).astype(np.uint16)
                    common[is_nodata] = NODATA_VALUE
                    data[px_min_y:px_min_y + sub_h, px_min_x:px_min_x + sub_w] = common
        else:
            with rasterio.open(self.tif_path) as src:
                with WarpedVRT(
                    src,
                    crs='EPSG:3857',
                    resampling=Resampling.nearest,
                    nodata=self.nodata,
                ) as vrt:
                    window = from_bounds(i_min_x, i_min_y, i_max_x, i_max_y, transform=vrt.transform)
                    window = window.intersection(Window(0, 0, vrt.width, vrt.height))

                    sub_data = vrt.read(
                        1,
                        window=window,
                        out_shape=(sub_h, sub_w),
                        resampling=Resampling.nearest,
                    )
                    data[px_min_y:px_min_y + sub_h, px_min_x:px_min_x + sub_w] = sub_data

        # 4. Fast vectorized color mapping
        rgba = lut[data]

        # 5. Check if completely transparent
        if not np.any(rgba[:, :, 3]):
            return EMPTY_TILE_PNG if tile_size == 256 else _create_empty_png(tile_size, tile_size)

        # 6. Fast PNG serialization via Pillow
        img = Image.fromarray(rgba, mode='RGBA')
        buf = io.BytesIO()
        img.save(buf, format='PNG', compress_level=1)
        return buf.getvalue()

    def render_bbox(
        self,
        min_x: float,
        min_y: float,
        max_x: float,
        max_y: float,
        srs: str = 'EPSG:3857',
        layer_type: Optional[str] = None,
        mode: Optional[str] = None,
        to_class: Optional[int] = None,
        from_class: Optional[int] = None,
        opacity: float = 1.0,
        width: int = 256,
        height: int = 256,
        format: str = 'image/png',
        transparent: bool = True,
    ) -> bytes:
        """Render arbitrary bounding box in specified CRS (WMS 1.3.0 GetMap support)."""
        eff_layer = layer_type or self.layer_type
        eff_mode = mode or ('changes_only' if eff_layer == LAYER_TRANSITIONS else 'all')
        alpha_byte = int(round(max(0.0, min(1.0, opacity)) * 255))

        lut = get_layer_lut(
            eff_layer,
            mode=eff_mode,
            to_class=to_class,
            from_class=from_class,
            alpha=alpha_byte,
            num_classes=self.num_classes,
        )

        with rasterio.open(self.tif_path) as src:
            with WarpedVRT(
                src,
                crs=srs,
                resampling=Resampling.nearest,
                nodata=self.nodata,
            ) as vrt:
                window = from_bounds(min_x, min_y, max_x, max_y, transform=vrt.transform)
                window = window.intersection(Window(0, 0, vrt.width, vrt.height))

                if window.width <= 0 or window.height <= 0:
                    return _create_empty_png(width, height)

                data = vrt.read(
                    1,
                    window=window,
                    out_shape=(height, width),
                    resampling=Resampling.nearest,
                )

        rgba = lut[data]
        if not transparent:
            # Replace transparent pixels with white
            mask = rgba[:, :, 3] == 0
            rgba[mask] = [255, 255, 255, 255]

        img = Image.fromarray(rgba, mode='RGBA')
        buf = io.BytesIO()
        img.save(buf, format='PNG', compress_level=1)
        return buf.getvalue()

    def query_pixel(
        self,
        lng: float,
        lat: float,
        layer_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Authoritative pixel query reading exact 1x1 window directly from GeoTIFF."""
        eff_layer = layer_type or self.layer_type

        with rasterio.open(self.tif_path) as src:
            # Transform WGS84 (lng, lat) to native raster CRS
            if src.crs and str(src.crs).upper() not in ('EPSG:4326', 'WGS 84'):
                transformer = pyproj.Transformer.from_crs('EPSG:4326', src.crs, always_xy=True)
                native_x, native_y = transformer.transform(lng, lat)
            else:
                native_x, native_y = lng, lat

            # Inverse Affine Transform to pixel coordinates (col, row)
            inv_transform = ~src.transform
            col_f, row_f = inv_transform @ (native_x, native_y)
            col_int, row_int = int(math.floor(col_f)), int(math.floor(row_f))

            # Out of bounds check
            if not (0 <= col_int < src.width and 0 <= row_int < src.height):
                return {
                    'status': 'nodata',
                    'layer_type': eff_layer,
                    'coordinates': {'lng': lng, 'lat': lat},
                    'raw_value': None,
                    'is_nodata': True,
                    'source_file': str(self.tif_path.name),
                    'source_crs': str(src.crs),
                }

            # Read exact 1x1 window
            window = Window(col_int, row_int, 1, 1)
            raw_pixel_data = src.read(1, window=window)
            raw_val = int(raw_pixel_data[0, 0])

            # Check NoData
            is_nodata = (
                (src.nodata is not None and raw_val == src.nodata)
                or raw_val == 255
                or raw_val == 65535
            )

            res: Dict[str, Any] = {
                'status': 'nodata' if is_nodata else 'success',
                'layer_type': eff_layer,
                'coordinates': {'lng': lng, 'lat': lat},
                'raw_value': raw_val if not is_nodata else None,
                'is_nodata': is_nodata,
                'source_file': str(self.tif_path.name),
                'source_crs': str(src.crs),
            }

            if not is_nodata:
                if eff_layer == LAYER_CLASSIFICATION:
                    class_id = WORLDCOVER_TO_CLASS.get(raw_val, raw_val)
                    if 0 <= class_id < len(CLASS_NAMES):
                        res['class_id'] = class_id
                        res['class_name'] = CLASS_NAMES[class_id]
                        res['color'] = WORKFLOW_CLASS_COLORS[class_id]
                elif eff_layer == LAYER_QUALITY_MASK:
                    res['is_valid'] = (raw_val == 1)
                    res['quality_label'] = 'Valid' if raw_val == 1 else 'Cloud / Invalid'
                    res['color'] = '#22c55e' if raw_val == 1 else '#ef4444'
                elif eff_layer == LAYER_OBSERVATION_COUNT:
                    res['observation_count'] = raw_val
                elif eff_layer == LAYER_COMMON_VALID:
                    res['is_common_valid'] = (raw_val == 1)
                    res['common_valid_label'] = 'Common Valid' if raw_val == 1 else 'Cloud Gap / Invalid'
                    res['color'] = '#3b82f6' if raw_val == 1 else '#ef4444'
                elif eff_layer == LAYER_TRANSITIONS:
                    fc = raw_val // self.num_classes
                    tc = raw_val % self.num_classes
                    res['from_class'] = fc
                    res['to_class'] = tc
                    res['is_changed'] = (fc != tc)
                    if 0 <= tc < len(CLASS_NAMES):
                        res['target_class_name'] = CLASS_NAMES[tc]
                        res['color'] = WORKFLOW_CLASS_COLORS[tc]

            return res
