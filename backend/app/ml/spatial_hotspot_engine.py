"""Spatial Hotspot Analysis Engine for LCLUC Change Detection.

Calculates Getis-Ord Gi* local spatial autocorrelation statistics across multi-scale
spatial kernels on deforestation, urbanization, and general change transition rasters.
Extracts statistically significant hotspot clusters, computes physical intervention metrics
(area in hectares, mean change intensity, composite priority scores), and produces standardized
GeoJSON vector boundaries and GeoTIFF evidence rasters.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np

# Optional fast-path imports
try:
    import cv2  # OpenCV for hardware-accelerated 2D convolution and CC labeling
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

try:
    import rasterio
    import rasterio.features
    import rasterio.warp
    from pyproj import CRS
    HAS_RASTERIO = True
except ImportError:
    HAS_RASTERIO = False

try:
    import shapely.geometry
    import shapely.ops
    HAS_SHAPELY = True
except ImportError:
    HAS_SHAPELY = False


# Critical Z-score thresholds for two-tailed alpha levels (0.01, 0.05, 0.10)
# corresponding to 99%, 95%, 90% statistical confidence
Z_99: float = 2.5758293035489004  # p < 0.01
Z_95: float = 1.959963984540054   # p < 0.05
Z_90: float = 1.6448536269514722  # p < 0.10

# Classification integer codes
CLASS_HOTSPOT_99: int = 3
CLASS_HOTSPOT_95: int = 2
CLASS_HOTSPOT_90: int = 1
CLASS_NOT_SIGNIFICANT: int = 0
CLASS_COLDSPOT_90: int = -1
CLASS_COLDSPOT_95: int = -2
CLASS_COLDSPOT_99: int = -3
CLASS_NODATA: int = -99

FLOAT_NODATA: float = -9999.0

# 9-class LCLUC default class definitions
DEFAULT_CLASS_NAMES = [
    'water', 'trees', 'grass', 'flooded_vegetation',
    'crops', 'shrub_and_scrub', 'built', 'bare', 'snow_and_ice'
]
INDEX_TREES = 1
INDEX_BUILT = 6


def create_spatial_kernel(
    size: int = 3,
    kind: str = 'uniform',
    sigma: Optional[float] = None
) -> np.ndarray:
    """Generate normalized or raw spatial weight kernel.

    Args:
        size: Odd integer kernel dimension (e.g., 3, 5, 7).
        kind: 'uniform' (box/queen), 'gaussian', or 'inverse_distance'.
        sigma: Standard deviation for Gaussian kernel. Defaults to (radius / 2.0).

    Returns:
        2D numpy array of shape (size, size) with dtype float64.
    """
    if size % 2 == 0 or size < 1:
        raise ValueError(f"Kernel size must be an odd positive integer, got {size}")
    
    rad = size // 2
    if size == 1:
        return np.ones((1, 1), dtype=np.float64)

    y, x = np.ogrid[-rad:rad + 1, -rad:rad + 1]
    dist = np.sqrt(x * x + y * y)

    kind_lower = kind.lower().strip()
    if kind_lower == 'uniform':
        kernel = np.ones((size, size), dtype=np.float64)
    elif kind_lower == 'gaussian':
        s = float(sigma) if sigma is not None and sigma > 0 else max(1.0, rad / 2.0)
        kernel = np.exp(-(dist ** 2) / (2.0 * s ** 2)).astype(np.float64)
    elif kind_lower in ('inverse_distance', 'inv_dist', 'idw'):
        # At center cell (dist=0), weight is 1.0; decays monotonically with distance
        kernel = (1.0 / (1.0 + dist)).astype(np.float64)
    else:
        raise ValueError(f"Unsupported kernel kind '{kind}'. Expected 'uniform', 'gaussian', or 'inverse_distance'.")

    return kernel


def apply_2d_convolution(
    image: np.ndarray,
    kernel: np.ndarray
) -> np.ndarray:
    """Perform 2D spatial convolution with zero-padding on image boundaries.

    Uses OpenCV's cv2.filter2D for hardware acceleration if available,
    falling back to NumPy sliding window convolution.
    """
    image_f64 = np.asarray(image, dtype=np.float64)
    kernel_f64 = np.asarray(kernel, dtype=np.float64)

    if image_f64.ndim != 2:
        raise ValueError(f"Input image must be 2D, got shape {image_f64.shape}")
    if kernel_f64.ndim != 2 or kernel_f64.shape[0] != kernel_f64.shape[1] or kernel_f64.shape[0] % 2 == 0:
        raise ValueError(f"Kernel must be square with odd dimensions, got {kernel_f64.shape}")

    k_size = kernel_f64.shape[0]
    if k_size == 1:
        return image_f64 * kernel_f64[0, 0]

    # Fast path via OpenCV
    if HAS_CV2:
        # Note: cv2.filter2D applies correlation; since our spatial kernels are symmetric,
        # correlation and convolution are mathematically identical.
        return cv2.filter2D(image_f64, cv2.CV_64F, kernel_f64, borderType=cv2.BORDER_CONSTANT)

    # Pure NumPy fallback via stride tricks
    pad_width = k_size // 2
    padded = np.pad(image_f64, pad_width, mode='constant', constant_values=0.0)
    windows = np.lib.stride_tricks.sliding_window_view(padded, (k_size, k_size))
    # Flip kernel for standard mathematical convolution
    k_flipped = np.flip(kernel_f64)
    return np.einsum('ijkl,kl->ij', windows, k_flipped, optimize=True)


def calculate_p_value_two_sided(z_scores: np.ndarray) -> np.ndarray:
    """Calculate two-sided asymptotic p-values from standard normal z-scores.

    p = erfc(|z| / sqrt(2))
    """
    z_abs = np.abs(z_scores)
    p_values = np.full_like(z_scores, np.nan, dtype=np.float64)
    valid = np.isfinite(z_abs)
    
    # Vectorized erfc evaluation using Python's standard math.erfc
    erfc_vec = np.frompyfunc(lambda v: math.erfc(v / math.sqrt(2.0)), 1, 1)
    p_values[valid] = erfc_vec(z_abs[valid]).astype(np.float64)
    return p_values


def extract_transition_mask(
    t1_array: np.ndarray,
    t2_array: np.ndarray,
    transition_type: str = 'deforestation',
    valid_mask: Optional[np.ndarray] = None,
    from_classes: Optional[List[int]] = None,
    to_classes: Optional[List[int]] = None
) -> Tuple[np.ndarray, np.ndarray]:
    """Extract binary transition mask and combined valid mask from multitemporal LCLUC maps.

    Supported transition types:
        - 'deforestation': trees (class 1) in T1 converted to non-trees in T2.
        - 'urbanization': non-built in T1 converted to built (class 6) in T2.
        - 'general_change': any transition where t1 != t2.
        - 'custom': explicitly defined via from_classes and to_classes.

    Returns:
        (change_mask, combined_valid_mask): Both as boolean or float arrays.
    """
    t1 = np.asarray(t1_array)
    t2 = np.asarray(t2_array)
    if t1.shape != t2.shape:
        raise ValueError(f"Shape mismatch between T1 {t1.shape} and T2 {t2.shape}")

    # Determine valid cells (finite and non-negative)
    base_valid = np.isfinite(t1) & np.isfinite(t2) & (t1 >= 0) & (t2 >= 0)
    if valid_mask is not None:
        base_valid &= np.asarray(valid_mask, dtype=bool)

    tt_lower = transition_type.lower().strip()
    change_mask = np.zeros(t1.shape, dtype=np.float64)

    if tt_lower in ('deforestation', 'forest_loss'):
        # Trees -> Non-trees
        tree_idx = from_classes[0] if (from_classes and len(from_classes) == 1) else INDEX_TREES
        target = (t1 == tree_idx) & (t2 != tree_idx) & base_valid
        change_mask[target] = 1.0

    elif tt_lower in ('urbanization', 'urban_expansion', 'built_growth'):
        # Non-built -> Built
        built_idx = to_classes[0] if (to_classes and len(to_classes) == 1) else INDEX_BUILT
        target = (t1 != built_idx) & (t2 == built_idx) & base_valid
        change_mask[target] = 1.0

    elif tt_lower in ('general_change', 'any_change', 'change'):
        target = (t1 != t2) & base_valid
        change_mask[target] = 1.0

    elif tt_lower == 'custom':
        if not from_classes or not to_classes:
            raise ValueError("Custom transition type requires non-empty from_classes and to_classes")
        from_set = set(from_classes)
        to_set = set(to_classes)
        t1_in = np.isin(t1, list(from_set))
        t2_in = np.isin(t2, list(to_set))
        target = t1_in & t2_in & base_valid
        change_mask[target] = 1.0

    else:
        raise ValueError(f"Unknown transition_type '{transition_type}'. "
                         f"Choose from 'deforestation', 'urbanization', 'general_change', or 'custom'.")

    return change_mask, base_valid


def calculate_getis_ord_gi(
    data: np.ndarray,
    valid_mask: Optional[np.ndarray] = None,
    kernel_size: int = 3,
    kernel_type: str = 'uniform',
    sigma: Optional[float] = None
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute Getis-Ord Gi* statistic, asymptotic p-value, and classification raster.

    Formulation (Ord & Getis, 1995):
        Gi* = (sum_j(w_ij * x_j) - X_bar * sum_j(w_ij)) /
              (S * sqrt((n * sum_j(w_ij^2) - (sum_j(w_ij))^2) / (n - 1)))

    Boundary & NoData handling:
        - Image boundaries are padded with zeros, and valid mask is simultaneously convolved.
        - sum_j(w_ij) and sum_j(w_ij^2) strictly sum weights over valid non-masked neighbors.
        - Denominator automatically adapts to local neighborhood sample size.

    Args:
        data: 2D numpy array representing change intensity (binary or continuous).
        valid_mask: Optional 2D boolean array of valid observations.
        kernel_size: Spatial window width (odd integer >= 1).
        kernel_type: 'uniform', 'gaussian', or 'inverse_distance'.
        sigma: Optional standard deviation for Gaussian kernel.

    Returns:
        z_scores: 2D float64 array (NaN for invalid/NoData cells).
        p_values: 2D float64 array (two-sided asymptotic p-values).
        classification: 2D int8 array (-3, -2, -1, 0, 1, 2, 3, or -99 for NoData).
    """
    arr = np.asarray(data, dtype=np.float64)
    if arr.ndim != 2:
        raise ValueError(f"Data array must be 2-dimensional, got {arr.shape}")

    if valid_mask is None:
        mask = np.isfinite(arr)
    else:
        mask = np.asarray(valid_mask, dtype=bool) & np.isfinite(arr)

    n_valid = int(np.sum(mask))
    h, w = arr.shape

    # Pre-allocate output arrays
    z_scores = np.full((h, w), np.nan, dtype=np.float64)
    p_values = np.full((h, w), np.nan, dtype=np.float64)
    classification = np.full((h, w), CLASS_NODATA, dtype=np.int8)

    # Edge cases: 0 or 1 valid cell, or all valid cells identical
    if n_valid <= 1:
        z_scores[mask] = 0.0
        p_values[mask] = 1.0
        classification[mask] = CLASS_NOT_SIGNIFICANT
        return z_scores, p_values, classification

    # Mask invalid values to 0 for linear convolution
    arr_masked = np.zeros((h, w), dtype=np.float64)
    arr_masked[mask] = arr[mask]

    # Global population statistics across all valid cells
    sum_x = float(np.sum(arr_masked))
    x_bar = sum_x / float(n_valid)
    sum_x2 = float(np.sum(arr_masked ** 2))
    variance_x = (sum_x2 / float(n_valid)) - (x_bar ** 2)

    # Zero global variance (e.g. perfectly uniform grid)
    if variance_x <= 1e-12:
        z_scores[mask] = 0.0
        p_values[mask] = 1.0
        classification[mask] = CLASS_NOT_SIGNIFICANT
        return z_scores, p_values, classification

    s = math.sqrt(variance_x)

    # Create spatial kernel
    kernel = create_spatial_kernel(size=kernel_size, kind=kernel_type, sigma=sigma)
    kernel_sq = kernel ** 2

    # Convolve to obtain local neighborhood sums
    # L_i = sum_j (w_ij * x_j)
    l_sum = apply_2d_convolution(arr_masked, kernel)

    # W_i = sum_j (w_ij) for valid neighbors
    mask_f64 = mask.astype(np.float64)
    w_sum = apply_2d_convolution(mask_f64, kernel)

    # W2_i = sum_j (w_ij^2) for valid neighbors
    w2_sum = apply_2d_convolution(mask_f64, kernel_sq)

    # Numerator: L_i - X_bar * W_i
    numerator = l_sum - (x_bar * w_sum)

    # Denominator variance term:
    # var_w = (n * sum(w^2) - (sum(w))^2) / (n - 1)
    # Cauchy-Schwarz ensures (n * W2 - W^2) >= 0; apply max(0.0) against floating precision error
    var_w = (float(n_valid) * w2_sum - (w_sum ** 2)) / float(n_valid - 1)
    var_w = np.maximum(0.0, var_w)
    denominator = s * np.sqrt(var_w)

    # Evaluate Gi* z-scores for valid cells
    eval_mask = mask & (denominator > 1e-12)
    zero_denom_mask = mask & (denominator <= 1e-12)

    z_scores[eval_mask] = numerator[eval_mask] / denominator[eval_mask]
    z_scores[zero_denom_mask] = 0.0

    # Calculate asymptotic p-values
    p_values[mask] = calculate_p_value_two_sided(z_scores)[mask]

    # Assign classification tiers
    # Hotspots
    classification[mask & (z_scores > Z_99)] = CLASS_HOTSPOT_99
    classification[mask & (z_scores > Z_95) & (z_scores <= Z_99)] = CLASS_HOTSPOT_95
    classification[mask & (z_scores > Z_90) & (z_scores <= Z_95)] = CLASS_HOTSPOT_90

    # Coldspots
    classification[mask & (z_scores < -Z_99)] = CLASS_COLDSPOT_99
    classification[mask & (z_scores < -Z_95) & (z_scores >= -Z_99)] = CLASS_COLDSPOT_95
    classification[mask & (z_scores < -Z_90) & (z_scores >= -Z_95)] = CLASS_COLDSPOT_90

    # Not Significant
    classification[mask & (z_scores >= -Z_90) & (z_scores <= Z_90)] = CLASS_NOT_SIGNIFICANT

    return z_scores, p_values, classification


def compute_summary_statistics(
    classification: np.ndarray,
    z_scores: np.ndarray,
    change_mask: np.ndarray,
    pixel_area_ha: float = 0.01,
    transition_type: str = 'deforestation',
    kernel_size: int = 3,
    kernel_type: str = 'uniform',
    clusters: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """Compute comprehensive area, percentage, and severity metrics."""
    valid_mask = classification != CLASS_NODATA
    total_pixels = int(classification.size)
    valid_pixels = int(np.sum(valid_mask))
    nodata_pixels = total_pixels - valid_pixels

    total_valid_area_ha = round(valid_pixels * pixel_area_ha, 4)

    # Global change stats
    global_mean_change = float(np.mean(change_mask[valid_mask])) if valid_pixels > 0 else 0.0
    global_std_change = float(np.std(change_mask[valid_mask])) if valid_pixels > 0 else 0.0

    # Hotspot counts
    h99 = int(np.sum(classification == CLASS_HOTSPOT_99))
    h95 = int(np.sum(classification == CLASS_HOTSPOT_95))
    h90 = int(np.sum(classification == CLASS_HOTSPOT_90))
    hotspot_total = h99 + h95 + h90

    # Coldspot counts
    c99 = int(np.sum(classification == CLASS_COLDSPOT_99))
    c95 = int(np.sum(classification == CLASS_COLDSPOT_95))
    c90 = int(np.sum(classification == CLASS_COLDSPOT_90))
    coldspot_total = c99 + c95 + c90

    # Not significant
    ns = int(np.sum(classification == CLASS_NOT_SIGNIFICANT))

    def stat_dict(count: int) -> Dict[str, Any]:
        ha = round(count * pixel_area_ha, 4)
        pct = round((count / valid_pixels * 100.0), 2) if valid_pixels > 0 else 0.0
        return {"pixels": count, "area_ha": ha, "pct": pct}

    top_priority_zones = []
    if clusters:
        for idx, cl in enumerate(clusters[:5], start=1):
            top_priority_zones.append({
                "rank": idx,
                "cluster_id": cl["properties"]["cluster_id"],
                "severity": cl["properties"]["severity"],
                "priority_score": cl["properties"]["priority_score"],
                "area_ha": cl["properties"]["area_ha"],
                "mean_z_score": cl["properties"]["mean_z_score"],
                "max_z_score": cl["properties"]["max_z_score"],
                "mean_change_intensity": cl["properties"]["mean_change_intensity"],
                "centroid": cl["properties"].get("centroid")
            })

    return {
        "transition_type": transition_type,
        "kernel": {
            "size": kernel_size,
            "type": kernel_type
        },
        "total_pixels": total_pixels,
        "valid_pixels": valid_pixels,
        "nodata_pixels": nodata_pixels,
        "total_valid_area_ha": total_valid_area_ha,
        "global_mean_change": round(global_mean_change, 6),
        "global_std_change": round(global_std_change, 6),
        "hotspots_total": stat_dict(hotspot_total),
        "coldspots_total": stat_dict(coldspot_total),
        "not_significant": stat_dict(ns),
        "hotspot_breakdown": {
            "hotspot_99": stat_dict(h99),
            "hotspot_95": stat_dict(h95),
            "hotspot_90": stat_dict(h90)
        },
        "coldspot_breakdown": {
            "coldspot_99": stat_dict(c99),
            "coldspot_95": stat_dict(c95),
            "coldspot_90": stat_dict(c90)
        },
        "cluster_count": len(clusters) if clusters is not None else 0,
        "top_priority_intervention_zones": top_priority_zones
    }


def vectorize_hotspots(
    classification: np.ndarray,
    z_scores: np.ndarray,
    change_intensity: np.ndarray,
    transform: Any = None,
    crs: Any = None,
    pixel_area_m2: float = 100.0,
    min_cluster_pixels: int = 1,
    max_features: int = 5000,
    transition_type: str = 'deforestation'
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Vectorize contiguous hotspot clusters (z > 1.65) into standardized GeoJSON.

    Args:
        classification: 2D int8 classification array.
        z_scores: 2D float64 z-score array.
        change_intensity: 2D float64 change mask array.
        transform: Affine transform from raster coordinates to spatial reference.
        crs: Source CRS (e.g., EPSG:3857 or UTM). Reprojects to EPSG:4326 if needed.
        pixel_area_m2: Area of a single pixel in square meters.
        min_cluster_pixels: Filter out clusters smaller than this pixel count.
        max_features: Truncation threshold for map rendering limit.
        transition_type: Name of transition analyzed.

    Returns:
        (geojson_collection, features_list)
    """
    hotspot_mask = (classification >= CLASS_HOTSPOT_90).astype(np.uint8)

    features: List[Dict[str, Any]] = []
    if np.sum(hotspot_mask) == 0:
        collection = {"type": "FeatureCollection", "features": []}
        return collection, features

    # Extract 8-connected components
    if HAS_CV2:
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(hotspot_mask, connectivity=8)
    else:
        # Fallback labeling using simple DFS/BFS or rasterio shapes
        labels = np.zeros_like(hotspot_mask, dtype=np.int32)
        curr_label = 1
        h, w = hotspot_mask.shape
        visited = np.zeros_like(hotspot_mask, dtype=bool)
        for r in range(h):
            for c in range(w):
                if hotspot_mask[r, c] and not visited[r, c]:
                    # BFS
                    queue = [(r, c)]
                    visited[r, c] = True
                    labels[r, c] = curr_label
                    while queue:
                        qr, qc = queue.pop(0)
                        for dr in (-1, 0, 1):
                            for dc in (-1, 0, 1):
                                nr, nc = qr + dr, qc + dc
                                if 0 <= nr < h and 0 <= nc < w and hotspot_mask[nr, nc] and not visited[nr, nc]:
                                    visited[nr, nc] = True
                                    labels[nr, nc] = curr_label
                                    queue.append((nr, nc))
                    curr_label += 1
        num_labels = curr_label

    cluster_candidates = []
    for lbl in range(1, num_labels):
        comp_mask = (labels == lbl)
        n_pixels = int(np.sum(comp_mask))
        if n_pixels < min_cluster_pixels:
            continue

        z_vals = z_scores[comp_mask]
        mean_z = float(np.mean(z_vals))
        max_z = float(np.max(z_vals))
        mean_intensity = float(np.mean(change_intensity[comp_mask]))

        # Assign severity tier
        if max_z >= Z_99:
            severity = 'hotspot_99'
            conf = 99
        elif max_z >= Z_95:
            severity = 'hotspot_95'
            conf = 95
        else:
            severity = 'hotspot_90'
            conf = 90

        area_m2 = round(n_pixels * pixel_area_m2, 2)
        area_ha = round(area_m2 / 10000.0, 4)
        priority_score = round(area_ha * mean_z, 4)

        cluster_candidates.append({
            "lbl": lbl,
            "mask": comp_mask,
            "n_pixels": n_pixels,
            "mean_z": round(mean_z, 4),
            "max_z": round(max_z, 4),
            "mean_intensity": round(mean_intensity, 4),
            "severity": severity,
            "conf": conf,
            "area_m2": area_m2,
            "area_ha": area_ha,
            "priority_score": priority_score
        })

    # Sort descending by priority score
    cluster_candidates.sort(key=lambda x: x["priority_score"], reverse=True)

    # Determine whether CRS re-projection to WGS84 (EPSG:4326) is necessary
    need_reproject = False
    source_crs = None
    if crs is not None and HAS_RASTERIO:
        try:
            source_crs = CRS.from_user_input(crs)
            need_reproject = not source_crs.equals(CRS.from_epsg(4326))
        except Exception:
            need_reproject = False

    eff_transform = transform
    if eff_transform is None and HAS_RASTERIO:
        from rasterio.transform import Affine
        eff_transform = Affine.identity()

    for rank, cl in enumerate(cluster_candidates[:max_features], start=1):
        comp_mask = cl["mask"]
        geom_json = None
        centroid_coord = None

        if HAS_RASTERIO and HAS_SHAPELY:
            shapes_gen = rasterio.features.shapes(
                comp_mask.astype(np.uint8),
                mask=comp_mask,
                transform=eff_transform
            )
            geoms = [shapely.geometry.shape(s[0]) for s in shapes_gen]
            if geoms:
                merged = shapely.ops.unary_union(geoms)
                if not merged.is_empty:
                    if need_reproject:
                        raw_mapping = shapely.geometry.mapping(merged)
                        geom_json = rasterio.warp.transform_geom(source_crs, 'EPSG:4326', raw_mapping)
                    else:
                        geom_json = shapely.geometry.mapping(merged)

                    cent = merged.centroid
                    centroid_coord = [round(cent.x, 6), round(cent.y, 6)]

        # Fallback if rasterio/shapely not fully available or geometry extraction failed
        if geom_json is None:
            # Generate bounding box geometry
            rows, cols = np.where(comp_mask)
            min_r, max_r = int(np.min(rows)), int(np.max(rows))
            min_c, max_c = int(np.min(cols)), int(np.max(cols))
            if transform is not None:
                p1 = transform * (min_c, min_r)
                p2 = transform * (max_c + 1, min_r)
                p3 = transform * (max_c + 1, max_r + 1)
                p4 = transform * (min_c, max_r + 1)
                coords = [[list(p1), list(p2), list(p3), list(p4), list(p1)]]
                cent_x = (p1[0] + p3[0]) / 2.0
                cent_y = (p1[1] + p3[1]) / 2.0
                centroid_coord = [round(cent_x, 6), round(cent_y, 6)]
            else:
                coords = [[[min_c, min_r], [max_c + 1, min_r], [max_c + 1, max_r + 1], [min_c, max_r + 1], [min_c, min_r]]]
                centroid_coord = [round((min_c + max_c) / 2.0, 2), round((min_r + max_r) / 2.0, 2)]

            geom_json = {"type": "Polygon", "coordinates": coords}

        feat = {
            "type": "Feature",
            "geometry": geom_json,
            "properties": {
                "cluster_id": rank,
                "priority_rank": rank,
                "severity": cl["severity"],
                "confidence_level": cl["conf"],
                "priority_score": cl["priority_score"],
                "mean_z_score": cl["mean_z"],
                "max_z_score": cl["max_z"],
                "mean_change_intensity": cl["mean_intensity"],
                "pixel_count": cl["n_pixels"],
                "area_m2": cl["area_m2"],
                "area_ha": cl["area_ha"],
                "transition_type": transition_type,
                "centroid": centroid_coord
            }
        }
        features.append(feat)

    collection = {
        "type": "FeatureCollection",
        "features": features
    }
    return collection, features


def export_geotiff(
    path: Union[str, Path],
    data: np.ndarray,
    profile: Dict[str, Any],
    dtype: str = 'float32',
    nodata: Optional[Union[float, int]] = None
) -> Path:
    """Export single-band 2D raster to GeoTIFF file."""
    if not HAS_RASTERIO:
        raise RuntimeError("rasterio is required to export GeoTIFF rasters")

    out_path = Path(path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    out_profile = profile.copy()
    out_profile.update(
        driver='GTiff',
        count=1,
        dtype=dtype,
        nodata=nodata,
        compress='deflate'
    )
    for k in ('blockxsize', 'blockysize', 'tiled', 'photometric'):
        out_profile.pop(k, None)

    arr_write = data.astype(dtype)
    if nodata is not None:
        if np.issubdtype(np.dtype(dtype), np.floating):
            arr_write[np.isnan(data)] = nodata

    with rasterio.open(out_path, 'w', **out_profile) as dst:
        dst.write(arr_write, 1)

    return out_path


class SpatialHotspotEngine:
    """Production-grade spatial hotspot analysis engine for LCLUC change monitoring."""

    def __init__(
        self,
        kernel_size: int = 3,
        kernel_type: str = 'uniform',
        sigma: Optional[float] = None
    ):
        self.kernel_size = kernel_size
        self.kernel_type = kernel_type
        self.sigma = sigma

    def analyze_arrays(
        self,
        change_intensity: np.ndarray,
        valid_mask: Optional[np.ndarray] = None,
        transform: Any = None,
        crs: Any = None,
        pixel_area_m2: float = 100.0,
        transition_type: str = 'deforestation',
        min_cluster_pixels: int = 1
    ) -> Dict[str, Any]:
        """Execute full hotspot analysis pipeline on in-memory arrays.

        Returns structured result dictionary containing z_scores, p_values,
        classification, summary statistics, and GeoJSON cluster collection.
        """
        z_scores, p_values, classification = calculate_getis_ord_gi(
            data=change_intensity,
            valid_mask=valid_mask,
            kernel_size=self.kernel_size,
            kernel_type=self.kernel_type,
            sigma=self.sigma
        )

        geojson_coll, cluster_features = vectorize_hotspots(
            classification=classification,
            z_scores=z_scores,
            change_intensity=change_intensity,
            transform=transform,
            crs=crs,
            pixel_area_m2=pixel_area_m2,
            min_cluster_pixels=min_cluster_pixels,
            transition_type=transition_type
        )

        summary = compute_summary_statistics(
            classification=classification,
            z_scores=z_scores,
            change_mask=change_intensity,
            pixel_area_ha=pixel_area_m2 / 10000.0,
            transition_type=transition_type,
            kernel_size=self.kernel_size,
            kernel_type=self.kernel_type,
            clusters=cluster_features
        )

        return {
            "z_scores": z_scores,
            "p_values": p_values,
            "classification": classification,
            "summary": summary,
            "geojson": geojson_coll,
            "cluster_features": cluster_features
        }

    def analyze_rasters(
        self,
        t1_path: Union[str, Path],
        t2_path: Union[str, Path],
        transition_type: str = 'deforestation',
        output_dir: Optional[Union[str, Path]] = None,
        from_classes: Optional[List[int]] = None,
        to_classes: Optional[List[int]] = None,
        min_cluster_pixels: int = 1
    ) -> Dict[str, Any]:
        """Perform end-to-end hotspot analysis directly from two GeoTIFF input rasters."""
        if not HAS_RASTERIO:
            raise RuntimeError("rasterio is required to read GeoTIFF rasters")

        p1 = Path(t1_path).resolve()
        p2 = Path(t2_path).resolve()

        with rasterio.open(p1) as src1, rasterio.open(p2) as src2:
            if src1.shape != src2.shape:
                raise ValueError(f"Raster shape mismatch: {src1.shape} vs {src2.shape}")
            if src1.crs != src2.crs or src1.transform != src2.transform:
                raise ValueError("Raster alignment mismatch: CRS or transform differs")

            t1_data = src1.read(1)
            t2_data = src2.read(1)
            profile = src1.profile.copy()
            transform = src1.transform
            crs = src1.crs

            # Compute pixel area in m2
            if crs.is_projected:
                factor = crs.axis_info[0].unit_conversion_factor if hasattr(crs, 'axis_info') else 1.0
                pixel_area_m2 = abs(transform.a * transform.e - transform.b * transform.d) * (factor ** 2)
            else:
                # Approximation or 100m2 default for unprojected/synthetic
                pixel_area_m2 = 100.0

            valid1 = (src1.read_masks(1) > 0)
            valid2 = (src2.read_masks(1) > 0)
            combined_mask = valid1 & valid2

        change_mask, valid = extract_transition_mask(
            t1_array=t1_data,
            t2_array=t2_data,
            transition_type=transition_type,
            valid_mask=combined_mask,
            from_classes=from_classes,
            to_classes=to_classes
        )

        results = self.analyze_arrays(
            change_intensity=change_mask,
            valid_mask=valid,
            transform=transform,
            crs=crs,
            pixel_area_m2=pixel_area_m2,
            transition_type=transition_type,
            min_cluster_pixels=min_cluster_pixels
        )

        # Export artifacts if output_dir is specified
        if output_dir:
            out_dir = Path(output_dir).resolve()
            out_dir.mkdir(parents=True, exist_ok=True)

            z_path = out_dir / "hotspot_zscores.tif"
            export_geotiff(z_path, results["z_scores"], profile, dtype='float32', nodata=FLOAT_NODATA)

            c_path = out_dir / "hotspot_classes.tif"
            export_geotiff(c_path, results["classification"], profile, dtype='int16', nodata=CLASS_NODATA)

            geojson_path = out_dir / "hotspots.geojson"
            geojson_path.write_text(json.dumps(results["geojson"], ensure_ascii=False, indent=2), encoding='utf-8')

            summary_path = out_dir / "summary.json"
            summary_path.write_text(json.dumps(results["summary"], ensure_ascii=False, indent=2), encoding='utf-8')

            results["artifacts"] = {
                "zscores_geotiff": str(z_path),
                "classes_geotiff": str(c_path),
                "hotspots_geojson": str(geojson_path),
                "summary_json": str(summary_path)
            }

        return results
