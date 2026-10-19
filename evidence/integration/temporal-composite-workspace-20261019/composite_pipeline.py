"""
Temporal Composite & Cloud-Masking Verification Pipeline.
Isolated workspace module: evidence/integration/temporal-composite-workspace-20261019/composite_pipeline.py

Addresses: 6-year (2020-2025) time-series cloud-gap filling annual composite batch application
across 36 province-year cells (6 Indonesia provinces x 6 years).
Strictly follows annual mask diagnostics and policy contracts from backend/app/ml/.
"""

import copy
import hashlib
import json
import math
from typing import Dict, List, Optional, Tuple, Any
import warnings
import numpy as np

# Sentinel-2 Scene Classification Layer (SCL) Class Definitions
SCL_CLASSES = {
    0: "NO_DATA",
    1: "SATURATED_OR_DEFECTIVE",
    2: "DARK_AREA_PIXELS",
    3: "CLOUD_SHADOWS",
    4: "VEGETATION",
    5: "NOT_VEGETATED",
    6: "WATER",
    7: "UNCLASSIFIED",
    8: "CLOUD_MEDIUM_PROBABILITY",
    9: "CLOUD_HIGH_PROBABILITY",
    10: "THIN_CIRRUS",
    11: "SNOW",
}

# Contract: Aligned with scripts/audit_raster_alignment.py and Sentinel-2 L2A spec
INVALID_SCL_CODES = frozenset([0, 1, 3, 8, 9, 10, 11])
VALID_SCL_CODES = frozenset([2, 4, 5, 6, 7])

# Indonesian 6 Priority Target Provinces (First Group)
PROVINCES = [
    "banten",
    "east_java",
    "gorontalo",
    "south_sulawesi",
    "southeast_sulawesi",
    "west_java",
]

# 6-Year Target Time Horizon
YEARS = [2020, 2021, 2022, 2023, 2024, 2025]

# Standard 6-Band LCLUC Input Structure
BANDS = ["blue", "green", "red", "nir", "swir16", "swir22"]


def compute_sha256(data: bytes) -> str:
    """Compute hex SHA-256 digest of bytes."""
    return hashlib.sha256(data).hexdigest()


class SCLMaskEvaluator:
    """Evaluates Sentinel-2 SCL pixels, computes binary quality masks and statistics."""

    @staticmethod
    def compute_binary_mask(
        scl: np.ndarray,
        band_nodata_mask: Optional[np.ndarray] = None,
        custom_invalid_codes: Optional[frozenset] = None
    ) -> np.ndarray:
        """
        Produce a binary mask where 1 = valid observation, 0 = invalid (cloud/shadow/nodata).
        
        Args:
            scl: 2D uint8 numpy array with SCL class values (0..11).
            band_nodata_mask: Optional 2D boolean array where True indicates valid spectral data.
            custom_invalid_codes: Optional set of invalid SCL codes (defaults to INVALID_SCL_CODES).
        
        Returns:
            2D uint8 numpy array with values in {0, 1}.
        """
        if not isinstance(scl, np.ndarray) or scl.ndim != 2:
            raise ValueError("SCL must be a 2D numpy array.")
        
        invalid_codes = custom_invalid_codes if custom_invalid_codes is not None else INVALID_SCL_CODES
        # Valid where SCL is not in invalid codes
        valid_mask = ~np.isin(scl, list(invalid_codes))
        
        if band_nodata_mask is not None:
            if band_nodata_mask.shape != scl.shape:
                raise ValueError("band_nodata_mask shape must match SCL shape.")
            valid_mask = valid_mask & band_nodata_mask
            
        return valid_mask.astype(np.uint8)

    @staticmethod
    def evaluate_mask_counts(mask: np.ndarray) -> Dict[str, Any]:
        """
        Count valid, invalid, and total pixels matching backend/app/ml/annual_mask_policy.py schema.
        
        Returns:
            dict with 'valid_pixels', 'invalid_pixels', 'total_pixels', 'valid_ratio'
        """
        if not isinstance(mask, np.ndarray) or mask.ndim != 2:
            raise ValueError("Mask must be a 2D numpy array.")
        
        total = int(mask.size)
        valid = int(np.count_nonzero(mask == 1))
        invalid = total - valid
        
        return {
            "valid_pixels": valid,
            "invalid_pixels": invalid,
            "total_pixels": total,
            "valid_ratio": round(valid / total, 6) if total > 0 else 0.0,
        }

    @staticmethod
    def evaluate_scl_distribution(scl: np.ndarray) -> Dict[str, Any]:
        """Compute pixel count and percentage for each SCL class."""
        total = scl.size
        distribution = {}
        for code, label in SCL_CLASSES.items():
            cnt = int(np.count_nonzero(scl == code))
            pct = round(cnt / total * 100.0, 4) if total > 0 else 0.0
            distribution[label] = {"code": code, "count": cnt, "percentage": pct}
        return distribution


class TemporalCompositeEngine:
    """
    Multi-temporal compositing and cloud-gap filling engine.
    Supports median blending, medoid selection, and hierarchical adjacent-year gap-filling.
    """

    def __init__(self, default_method: str = "median"):
        if default_method not in ("median", "medoid", "max_ndvi"):
            raise ValueError(f"Unsupported compositing method: {default_method}")
        self.default_method = default_method

    @staticmethod
    def _calculate_ndvi(nir: np.ndarray, red: np.ndarray) -> np.ndarray:
        """Compute Normalized Difference Vegetation Index with zero-division safeguard."""
        denom = (nir.astype(np.float32) + red.astype(np.float32))
        numer = (nir.astype(np.float32) - red.astype(np.float32))
        ndvi = np.zeros_like(denom)
        valid_denom = denom > 1e-6
        ndvi[valid_denom] = numer[valid_denom] / denom[valid_denom]
        return np.clip(ndvi, -1.0, 1.0)

    def composite_slice_stack(
        self,
        slices: List[Dict[str, Any]],
        method: Optional[str] = None,
        fallback_slices: Optional[List[Dict[str, Any]]] = None,
        nodata_value: float = 0.0
    ) -> Dict[str, Any]:
        """
        Blend a temporal stack of multi-spectral observations into an annual composite.
        
        Each slice dictionary in slices must have:
            'bands': Dict[str, np.ndarray] of 2D arrays (e.g. 'blue', 'green', 'red', 'nir', ...)
            'scl': 2D np.ndarray uint8
            'datetime': str (ISO-8601 acquisition time)
            'scene_id': str
            
        Args:
            slices: List of temporal acquisition slices within the target annual window.
            method: 'median', 'medoid', or 'max_ndvi'.
            fallback_slices: Optional list of fallback slices from adjacent years for residual gap filling.
            nodata_value: Fill value for unfillable pixels (default 0.0).
            
        Returns:
            Dict containing:
                'composite_bands': Dict[str, np.ndarray]
                'quality_mask': np.ndarray (1 = valid blended pixel, 0 = nodata / unfillable gap)
                'observation_count': np.ndarray (number of valid observations per pixel)
                'provenance_mask': np.ndarray (0 = intra-year blend, 1 = gap-filled from adjacent year, 2 = persistent nodata)
                'metrics': Dict of summary statistics
        """
        blend_method = method or self.default_method
        if not slices and not fallback_slices:
            raise ValueError("At least one slice or fallback slice is required.")
        
        # Determine geometry from first available slice
        reference_slice = slices[0] if slices else fallback_slices[0]
        first_band = next(iter(reference_slice["bands"].values()))
        height, width = first_band.shape
        band_names = list(reference_slice["bands"].keys())

        # Validate all slices have consistent shapes and band sets
        for s in (slices + (fallback_slices or [])):
            if s["scl"].shape != (height, width):
                raise ValueError("All slices must have identical raster dimensions.")
            for bname in band_names:
                if bname not in s["bands"] or s["bands"][bname].shape != (height, width):
                    raise ValueError(f"Slice missing band {bname} or shape mismatch.")

        # Step 1: Compute per-slice validity masks
        slice_masks = []
        for s in slices:
            band_nodata = np.ones((height, width), dtype=bool)
            for b in s["bands"].values():
                band_nodata &= (b != nodata_value) & (~np.isnan(b))
            vmask = SCLMaskEvaluator.compute_binary_mask(s["scl"], band_nodata_mask=band_nodata)
            slice_masks.append(vmask)

        # Observation count stack (intra-year)
        if slices:
            stacked_masks = np.stack(slice_masks, axis=0)  # Shape (T, H, W)
            obs_count = np.sum(stacked_masks, axis=0)  # Shape (H, W)
        else:
            obs_count = np.zeros((height, width), dtype=np.int32)
            stacked_masks = np.zeros((0, height, width), dtype=np.uint8)

        # Step 2: Initialize output arrays
        composite_bands = {bname: np.full((height, width), nodata_value, dtype=np.float32) for bname in band_names}
        # Provenance: 0 = intra-year, 1 = fallback gap filled, 2 = persistent gap / nodata
        provenance = np.full((height, width), 2, dtype=np.uint8)
        
        has_intra_valid = obs_count >= 1
        provenance[has_intra_valid] = 0

        # Step 3: Perform Intra-year Blending for pixels with >= 1 valid observation
        if np.any(has_intra_valid):
            if blend_method == "median":
                for bname in band_names:
                    # Stack bands across time
                    band_stack = np.stack([s["bands"][bname].astype(np.float32) for s in slices], axis=0)  # (T, H, W)
                    # Mask invalid values with NaN
                    band_stack[stacked_masks == 0] = np.nan
                    
                    # Compute nanmedian with warning suppression for all-NaN pixels
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore", category=RuntimeWarning)
                        med_val = np.nanmedian(band_stack, axis=0)
                    valid_idx = has_intra_valid & (~np.isnan(med_val))
                    composite_bands[bname][valid_idx] = med_val[valid_idx]

            elif blend_method == "max_ndvi" and "nir" in band_names and "red" in band_names:
                # Compute NDVI stack
                ndvi_stack = np.full((len(slices), height, width), -999.0, dtype=np.float32)
                for t, s in enumerate(slices):
                    ndvi_t = self._calculate_ndvi(s["bands"]["nir"], s["bands"]["red"])
                    ndvi_t[stacked_masks[t] == 0] = -999.0
                    ndvi_stack[t] = ndvi_t

                best_t = np.argmax(ndvi_stack, axis=0)  # (H, W)
                for bname in band_names:
                    band_stack = np.stack([s["bands"][bname].astype(np.float32) for s in slices], axis=0)
                    # Select best slice per pixel
                    selected = np.take_along_axis(band_stack, best_t[np.newaxis, :, :], axis=0).squeeze(axis=0)
                    composite_bands[bname][has_intra_valid] = selected[has_intra_valid]

            elif blend_method == "medoid":
                # Medoid: observation closest to median vector
                # Compute medians per band
                medians = {}
                for bname in band_names:
                    band_stack = np.stack([s["bands"][bname].astype(np.float32) for s in slices], axis=0)
                    band_stack[stacked_masks == 0] = np.nan
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore", category=RuntimeWarning)
                        medians[bname] = np.nanmedian(band_stack, axis=0)

                # Distance stack
                dist_stack = np.full((len(slices), height, width), 1e12, dtype=np.float32)
                for t, s in enumerate(slices):
                    d_sq = np.zeros((height, width), dtype=np.float32)
                    for bname in band_names:
                        diff = s["bands"][bname].astype(np.float32) - medians[bname]
                        d_sq += diff * diff
                    # Only valid pixels qualify
                    d_sq[stacked_masks[t] == 0] = 1e12
                    dist_stack[t] = d_sq

                best_t = np.argmin(dist_stack, axis=0)
                for bname in band_names:
                    band_stack = np.stack([s["bands"][bname].astype(np.float32) for s in slices], axis=0)
                    selected = np.take_along_axis(band_stack, best_t[np.newaxis, :, :], axis=0).squeeze(axis=0)
                    composite_bands[bname][has_intra_valid] = selected[has_intra_valid]

        # Step 4: Hierarchical Gap-filling with Fallback Slices (Residual gaps where obs_count == 0)
        gap_mask = (obs_count == 0)
        gap_filled_count = 0
        
        if np.any(gap_mask) and fallback_slices:
            # Process fallback slices in order
            for fs in fallback_slices:
                if not np.any(gap_mask):
                    break
                fb_band_nodata = np.ones((height, width), dtype=bool)
                for b in fs["bands"].values():
                    fb_band_nodata &= (b != nodata_value) & (~np.isnan(b))
                fb_vmask = SCLMaskEvaluator.compute_binary_mask(fs["scl"], band_nodata_mask=fb_band_nodata)
                
                # Pixels that are gaps in target composite AND valid in this fallback slice
                fillable = gap_mask & (fb_vmask == 1)
                if np.any(fillable):
                    for bname in band_names:
                        composite_bands[bname][fillable] = fs["bands"][bname][fillable]
                    provenance[fillable] = 1  # 1 = gap-filled from adjacent year
                    gap_mask[fillable] = False
                    gap_filled_count += int(np.count_nonzero(fillable))

        # Step 5: Final Quality Mask
        # 1 = valid composite (intra-year or successfully gap-filled), 0 = persistent nodata
        final_quality_mask = ((provenance == 0) | (provenance == 1)).astype(np.uint8)
        
        # Summary counts
        total_pixels = height * width
        valid_final_pixels = int(np.count_nonzero(final_quality_mask == 1))
        intra_valid_pixels = int(np.count_nonzero(provenance == 0))
        persistent_gap_pixels = total_pixels - valid_final_pixels
        
        # Pre-composite vs Post-composite comparison
        # Pre-composite average valid pixel count across individual slices
        pre_valid_counts = [int(np.count_nonzero(m == 1)) for m in slice_masks]
        pre_mean_valid = float(np.mean(pre_valid_counts)) if pre_valid_counts else 0.0
        pre_mean_ratio = round(pre_mean_valid / total_pixels, 6) if total_pixels > 0 else 0.0
        post_ratio = round(valid_final_pixels / total_pixels, 6) if total_pixels > 0 else 0.0
        
        # Gap reduction calculation
        initial_mean_gap = total_pixels - pre_mean_valid
        gap_reduction_ratio = (
            round((initial_mean_gap - persistent_gap_pixels) / initial_mean_gap, 6)
            if initial_mean_gap > 0 else 1.0
        )

        metrics = {
            "total_pixels": total_pixels,
            "intra_year_valid_pixels": intra_valid_pixels,
            "gap_filled_pixels": gap_filled_count,
            "final_valid_pixels": valid_final_pixels,
            "persistent_gap_pixels": persistent_gap_pixels,
            "pre_composite_mean_valid_ratio": pre_mean_ratio,
            "post_composite_valid_ratio": post_ratio,
            "gap_reduction_ratio": max(0.0, gap_reduction_ratio),
            "slice_count": len(slices),
            "fallback_slice_count": len(fallback_slices) if fallback_slices else 0,
            "blending_method": blend_method,
        }

        return {
            "composite_bands": composite_bands,
            "quality_mask": final_quality_mask,
            "observation_count": obs_count,
            "provenance_mask": provenance,
            "metrics": metrics,
        }


class AnnualPolicyValidator:
    """
    Validates composite pixel counts against exact rational threshold policy.
    Directly mirrors backend/app/ml/annual_mask_policy.py logic.
    """

    @staticmethod
    def evaluate_policy(
        valid_pixels: int,
        total_pixels: int,
        numerator: int,
        denominator: int
    ) -> Dict[str, Any]:
        """
        Exact integer rational comparison:
        valid_pixels * denominator >= total_pixels * numerator
        """
        if denominator <= 0 or numerator < 0 or numerator > denominator:
            raise ValueError("Invalid rational policy bounds.")
        if valid_pixels < 0 or total_pixels < 0 or valid_pixels > total_pixels:
            raise ValueError("Invalid pixel counts.")
            
        met = (valid_pixels * denominator) >= (total_pixels * numerator)
        return {
            "caller_policy_met": met,
            "required_ratio": f"{numerator}/{denominator} ({round(numerator/denominator, 4)})",
            "observed_ratio": f"{valid_pixels}/{total_pixels} ({round(valid_pixels/total_pixels, 4)})" if total_pixels > 0 else "0/0",
            "valid_pixels": valid_pixels,
            "total_pixels": total_pixels,
            "deficit_pixels": max(0, math.ceil((total_pixels * numerator) / denominator) - valid_pixels) if not met else 0,
        }


class SyntheticSliceGenerator:
    """
    Generates realistic synthetic multi-temporal Sentinel-2 slices for Indonesian provinces.
    Models tropical monsoon cloud cycles (rainy vs dry seasons), cloud shadows, cirrus,
    and typical surface reflectance values for vegetation, soil, water, and urban classes.
    """

    @staticmethod
    def generate_annual_stack(
        province: str,
        year: int,
        num_slices: int = 6,
        grid_size: Tuple[int, int] = (64, 64),
        seed: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Create a temporal stack of synthetic slices for a given province and year.
        
        Tropical climate profile:
        - West Java / Banten / East Java: Dry season roughly June-September, rainy season Nov-March.
        - Sulawesi (South, Southeast, Gorontalo): Complex equatorial bimodal or monsoon cycles.
        """
        height, width = grid_size
        # Base landscape: synthetic land cover truth for this province (stable over multi-year horizon)
        prov_seed = abs(hash(province)) % (2**31)
        prov_rng = np.random.RandomState(prov_seed)
        r_grid = prov_rng.rand(height, width)
        base_landcover = np.zeros((height, width), dtype=np.uint8)
        base_landcover[r_grid < 0.40] = 4   # Vegetation
        base_landcover[(r_grid >= 0.40) & (r_grid < 0.65)] = 5  # Bare / soil
        base_landcover[(r_grid >= 0.65) & (r_grid < 0.85)] = 6  # Water
        base_landcover[r_grid >= 0.85] = 7  # Unclassified / urban

        # Weather and temporal acquisition variations use the annual seed
        rng = np.random.RandomState(seed if seed is not None else (abs(hash(f"{province}_{year}")) % (2**31)))

        # Base spectral reflectance per land cover class (scaled 0..10000)
        # B02 (blue), B03 (green), B04 (red), B08 (nir), B11 (swir16), B12 (swir22)
        class_spectra = {
            4: {"blue": 350, "green": 650, "red": 450, "nir": 3800, "swir16": 1600, "swir22": 800},   # Veg
            5: {"blue": 900, "green": 1200, "red": 1500, "nir": 2200, "swir16": 2800, "swir22": 2400}, # Bare
            6: {"blue": 500, "green": 550, "red": 400, "nir": 150, "swir16": 80, "swir22": 40},        # Water
            7: {"blue": 1100, "green": 1300, "red": 1400, "nir": 1800, "swir16": 2100, "swir22": 1900},# Urban
            2: {"blue": 250, "green": 300, "red": 250, "nir": 400, "swir16": 300, "swir22": 200},      # Dark
        }

        slices = []
        # Multi-temporal acquisitions spanning the calendar year (DOY 30, 90, 150, 210, 270, 330)
        day_of_years = np.linspace(25, 345, num_slices).astype(int)

        for t_idx, doy in enumerate(day_of_years):
            # Cloud probability modeled with seasonal sinusoidal curve
            # Indonesia: dry season around DOY 180-240 (July-August) -> lowest cloud
            # Rainy season around DOY 300-60 (Dec-Feb) -> highest cloud
            season_phase = 2 * math.pi * (doy - 210) / 365.0
            # Mean cloud prob oscillates between ~25% (dry) and ~75% (wet)
            cloud_prob = 0.50 + 0.25 * math.cos(season_phase) + rng.uniform(-0.10, 0.10)
            cloud_prob = np.clip(cloud_prob, 0.15, 0.85)

            # Generate spatial cloud patterns (using simple localized cloud blobs)
            scl = base_landcover.copy()
            cloud_mask = rng.rand(height, width) < cloud_prob

            # Assign cloud types:
            # High prob cloud (9), medium prob cloud (8), thin cirrus (10), shadow (3)
            cloud_type_rand = rng.rand(height, width)
            is_cloud = cloud_mask & (cloud_type_rand < 0.65)
            is_cirrus = cloud_mask & (cloud_type_rand >= 0.65) & (cloud_type_rand < 0.82)
            is_shadow = cloud_mask & (cloud_type_rand >= 0.82)

            scl[is_cloud] = 9   # Cloud high prob
            scl[is_cirrus] = 10 # Thin cirrus
            scl[is_shadow] = 3  # Cloud shadow

            # Add occasional boundary nodata (0)
            if t_idx == 0:
                scl[:2, :] = 0  # Edge nodata
            elif t_idx == num_slices - 1:
                scl[:, -2:] = 0

            # Generate spectral bands
            bands = {}
            for bname in BANDS:
                arr = np.zeros((height, width), dtype=np.float32)
                for code, spec in class_spectra.items():
                    c_mask = (base_landcover == code)
                    # Add base reflectance + small Gaussian noise
                    arr[c_mask] = spec[bname] + rng.normal(0, 30, size=int(np.count_nonzero(c_mask)))
                
                # Cloud pixels reflect brightly across all optical bands
                arr[is_cloud] = rng.uniform(4500, 8500, size=int(np.count_nonzero(is_cloud)))
                # Cirrus has moderate diffuse reflectance
                arr[is_cirrus] = arr[is_cirrus] * 1.3 + rng.uniform(800, 1500, size=int(np.count_nonzero(is_cirrus)))
                # Shadows have reduced reflectance
                arr[is_shadow] = arr[is_shadow] * 0.35
                # Nodata pixels are 0.0
                arr[scl == 0] = 0.0

                bands[bname] = np.clip(arr, 0.0, 10000.0)

            iso_date = f"{year}-{(doy//30)+1:02d}-{(doy%28)+1:02d}T03:15:00Z"
            scene_id = f"S2A_MSIL2A_{year}_{(doy//30)+1:02d}_{(doy%28)+1:02d}_{province}_T{t_idx:02d}"
            slices.append({
                "scene_id": scene_id,
                "datetime": iso_date,
                "bands": bands,
                "scl": scl,
                "cloud_prob_param": float(cloud_prob),
            })

        return slices


class AnnualCellBatchRunner:
    """
    Executes and verifies annual compositing and cloud-gap filling across all 36 province-year cells.
    """

    def __init__(
        self,
        provinces: List[str] = PROVINCES,
        years: List[int] = YEARS,
        grid_size: Tuple[int, int] = (64, 64),
        slices_per_year: int = 6,
        policy_threshold: Tuple[int, int] = (65, 100)  # 65% minimum valid ratio
    ):
        self.provinces = provinces
        self.years = years
        self.grid_size = grid_size
        self.slices_per_year = slices_per_year
        self.policy_num, self.policy_den = policy_threshold
        self.engine = TemporalCompositeEngine(default_method="median")

    def run_all_cells(self) -> Dict[str, Any]:
        """
        Execute full batch run across the 36 cells:
        1) Generates multi-temporal slices per cell.
        2) Generates cross-year pool for hierarchical fallback gap-filling.
        3) Executes composite and cloud-gap filling.
        4) Evaluates exact rational mask policy.
        5) Compiles exhaustive verification report.
        """
        total_cells = len(self.provinces) * len(self.years)
        results = []
        
        # Pre-generate stacks for all 36 cells to enable adjacent-year fallback
        all_stacks: Dict[Tuple[str, int], List[Dict[str, Any]]] = {}
        for prov in self.provinces:
            for yr in self.years:
                stack = SyntheticSliceGenerator.generate_annual_stack(
                    province=prov,
                    year=yr,
                    num_slices=self.slices_per_year,
                    grid_size=self.grid_size,
                    seed=abs(hash(f"{prov}_{yr}")) % (2**31)
                )
                all_stacks[(prov, yr)] = stack

        # Execute compositing for each cell
        for prov in self.provinces:
            for yr in self.years:
                slices = all_stacks[(prov, yr)]
                
                # Assemble fallback slices from adjacent years (yr-1, yr+1) if available
                fallbacks = []
                for adj_yr in [yr - 1, yr + 1]:
                    if (prov, adj_yr) in all_stacks:
                        # Take dry-season slice (DOY ~ 210, middle slice) as prime fallback
                        adj_stack = all_stacks[(prov, adj_yr)]
                        mid_idx = len(adj_stack) // 2
                        fallbacks.append(adj_stack[mid_idx])

                # Run composite blending
                comp_result = self.engine.composite_slice_stack(
                    slices=slices,
                    method="median",
                    fallback_slices=fallbacks
                )

                metrics = comp_result["metrics"]
                policy_eval = AnnualPolicyValidator.evaluate_policy(
                    valid_pixels=metrics["final_valid_pixels"],
                    total_pixels=metrics["total_pixels"],
                    numerator=self.policy_num,
                    denominator=self.policy_den
                )

                # Evaluate single-scene pass rate under same policy
                single_scene_ratios = [
                    round(int(np.count_nonzero(~np.isin(s["scl"], list(INVALID_SCL_CODES)))) / metrics["total_pixels"], 4)
                    for s in slices
                ]
                single_scene_passes = sum(1 for r in single_scene_ratios if r >= (self.policy_num / self.policy_den))

                cell_summary = {
                    "province": prov,
                    "year": yr,
                    "status": "COMPOSITE_VERIFIED" if policy_eval["caller_policy_met"] else "POLICY_DEFICIT",
                    "pre_composite": {
                        "slice_count": len(slices),
                        "single_scene_valid_ratios": single_scene_ratios,
                        "mean_valid_ratio": metrics["pre_composite_mean_valid_ratio"],
                        "single_scene_passed_count": single_scene_passes,
                    },
                    "post_composite": {
                        "total_pixels": metrics["total_pixels"],
                        "intra_year_valid_pixels": metrics["intra_year_valid_pixels"],
                        "gap_filled_pixels": metrics["gap_filled_pixels"],
                        "final_valid_pixels": metrics["final_valid_pixels"],
                        "persistent_gap_pixels": metrics["persistent_gap_pixels"],
                        "final_valid_ratio": metrics["post_composite_valid_ratio"],
                        "gap_reduction_ratio": metrics["gap_reduction_ratio"],
                    },
                    "policy_conformance": policy_eval,
                }
                results.append(cell_summary)

        # Aggregate statistics across all 36 cells
        passed_cells = sum(1 for r in results if r["policy_conformance"]["caller_policy_met"])
        mean_pre_ratio = float(np.mean([r["pre_composite"]["mean_valid_ratio"] for r in results]))
        mean_post_ratio = float(np.mean([r["post_composite"]["final_valid_ratio"] for r in results]))
        mean_gap_red = float(np.mean([r["post_composite"]["gap_reduction_ratio"] for r in results]))
        total_single_scenes = sum(r["pre_composite"]["slice_count"] for r in results)
        total_single_passes = sum(r["pre_composite"]["single_scene_passed_count"] for r in results)

        batch_report = {
            "schema_version": 1,
            "scope": "ANNUAL_TEMPORAL_COMPOSITE_36_CELLS_VERIFICATION",
            "status": "BATCH_VERIFICATION_COMPLETE",
            "cell_matrix": {
                "provinces": self.provinces,
                "province_count": len(self.provinces),
                "years": self.years,
                "year_count": len(self.years),
                "total_expected_cells": total_cells,
                "evaluated_cells": len(results),
            },
            "policy": {
                "minimum_valid_numerator": self.policy_num,
                "minimum_valid_denominator": self.policy_den,
                "minimum_valid_ratio": round(self.policy_num / self.policy_den, 4),
            },
            "summary_metrics": {
                "total_cells": total_cells,
                "cells_meeting_policy": passed_cells,
                "cell_policy_pass_rate": round(passed_cells / total_cells, 4),
                "mean_pre_composite_valid_ratio": round(mean_pre_ratio, 4),
                "mean_post_composite_valid_ratio": round(mean_post_ratio, 4),
                "mean_gap_reduction_ratio": round(mean_gap_red, 4),
                "total_single_scenes_evaluated": total_single_scenes,
                "single_scenes_meeting_policy": total_single_passes,
                "single_scene_pass_rate": round(total_single_passes / total_single_scenes, 4),
            },
            "cell_results": results,
        }

        return batch_report


class MultiTemporalConsistencyChecker:
    """
    Checks spectral, radiometric, and temporal consistency of annual composites.
    """

    @staticmethod
    def check_radiometric_bounds(
        composite_bands: Dict[str, np.ndarray],
        valid_range: Tuple[float, float] = (0.0, 10000.0)
    ) -> Dict[str, Any]:
        """Verify reflectance values are finite and within physical bounds."""
        issues = []
        low_bound, high_bound = valid_range
        for bname, arr in composite_bands.items():
            if np.isnan(arr).any():
                issues.append(f"Band {bname} contains NaN values.")
            if np.isinf(arr).any():
                issues.append(f"Band {bname} contains Inf values.")
            out_of_bounds = np.count_nonzero((arr < low_bound) | (arr > high_bound))
            if out_of_bounds > 0:
                issues.append(f"Band {bname} has {out_of_bounds} pixels outside [{low_bound}, {high_bound}].")
        return {"passed": len(issues) == 0, "issues": issues}

    @staticmethod
    def check_temporal_smoothness(
        year_composites: List[Dict[str, np.ndarray]],
        years: List[int],
        max_ndvi_delta: float = 0.40
    ) -> Dict[str, Any]:
        """
        Verify inter-annual NDVI stability.
        Tropical perennial forests / stable land covers should not experience violent
        artificial NDVI jumps unless severe disturbance occurred. Wild jumps typically indicate
        unmasked cloud or cloud shadow contamination.
        """
        if len(year_composites) != len(years) or len(years) < 2:
            raise ValueError("Need at least 2 consecutive annual composites.")

        ndvis = []
        for comp in year_composites:
            ndvi = TemporalCompositeEngine._calculate_ndvi(comp["nir"], comp["red"])
            ndvis.append(ndvi)

        deltas = []
        excessive_jump_pixels = 0
        total_eval_pixels = ndvis[0].size * (len(years) - 1)

        for i in range(len(years) - 1):
            delta = np.abs(ndvis[i + 1] - ndvis[i])
            jumps = np.count_nonzero(delta > max_ndvi_delta)
            excessive_jump_pixels += jumps
            deltas.append({
                "from_year": years[i],
                "to_year": years[i + 1],
                "mean_abs_delta": round(float(np.mean(delta)), 4),
                "max_delta": round(float(np.max(delta)), 4),
                "excessive_jump_pixels": jumps,
                "excessive_jump_rate": round(jumps / ndvis[0].size, 4),
            })

        excess_rate = round(excessive_jump_pixels / total_eval_pixels, 4) if total_eval_pixels > 0 else 0.0
        return {
            "passed": excess_rate < 0.05,  # Less than 5% anomalous inter-annual jumps
            "max_allowed_delta": max_ndvi_delta,
            "overall_excessive_jump_rate": excess_rate,
            "year_pair_deltas": deltas,
        }
