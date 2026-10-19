"""Unit Tests for Spectral Audit & Batch Validation Tool.

Validates:
- 6-band full BOA spectrum vs 4-band RGB-NIR and 3-band RGB.
- 10m spatial resolution verification.
- Radiometric scaling (0-10000 DN to 0.0-1.0 physical surface reflectance).
- PB < 04.00 (offset=0.0) vs PB >= 04.00 (offset=-0.1) calibration logic.
- Pixel-level saturation and negative anomaly flagging to prevent LCLUC contamination.
- Nodata consistency and quality mask alignment.
- Strict non-mutation guarantee on raw data files.
"""

import hashlib
import json
from pathlib import Path
import tempfile
from typing import Optional
import unittest
import numpy as np
import rasterio
from rasterio.transform import from_origin

import sys
WORKSPACE_DIR = Path(__file__).resolve().parent
if str(WORKSPACE_DIR) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_DIR))

from spectral_validator import (
    audit_single_patch,
    compute_file_sha256,
    BAND_NAMES_6,
    ESA_SCALE,
    PB_PRE04_OFFSET,
    PB_POST04_OFFSET,
    SPATIAL_RESOLUTION_10M
)
from spectral_batch_contract import (
    SpectralBatchContract,
    S2_6BANDS,
    PB_PRE04_REFLECTANCE_OFFSET,
    PB_POST04_REFLECTANCE_OFFSET
)


def create_synthetic_geotiff(
    path: Path,
    bands: int,
    data: Optional[np.ndarray] = None,
    nodata: float = 0.0,
    dtype: str = 'float32',
    height: int = 16,
    width: int = 16,
    res: float = 10.0
) -> Path:
    """Helper to generate a clean synthetic GeoTIFF for unit testing."""
    transform = from_origin(500000.0, 100000.0, res, res)
    crs = 'EPSG:32651'
    
    if data is None:
        base_dn = [200.0, 400.0, 300.0, 3000.0, 1800.0, 900.0]
        data = np.zeros((bands, height, width), dtype=dtype)
        for b in range(bands):
            dn = base_dn[b] if b < len(base_dn) else 500.0
            data[b, :, :] = dn
        data[:, 0, 0] = nodata
        
    with rasterio.open(
        path,
        'w',
        driver='GTiff',
        height=height,
        width=width,
        count=bands,
        dtype=dtype,
        crs=crs,
        transform=transform,
        nodata=nodata
    ) as dst:
        dst.write(data.astype(dtype))
        
    return path


class SpectralValidatorTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_6band_raw_dn_patch_audit(self):
        """A 6-band raster with DN values around 1000-5000 is verified as 6_BAND_BOA_READY in RAW_DN scale."""
        tif_path = self.root / 'patch_6band_dn.tif'
        create_synthetic_geotiff(tif_path, bands=6)
        
        cal_data = {
            'scale': [0.0001] * 6,
            'offset': [0.0] * 6,
            'baseline': '02.12'
        }
        
        audit = audit_single_patch(
            image_path=tif_path,
            patch_id='test_6b_01',
            calibration_data=cal_data,
            check_sha_immutability=True
        )
        
        self.assertTrue(audit.file_exists)
        self.assertFalse(audit.mutation_detected)
        self.assertEqual(audit.band_count, 6)
        self.assertTrue(audit.resolution_10m_verified)
        self.assertEqual(audit.spectral_readiness, '6_BAND_BOA_READY')
        self.assertEqual(audit.scale_status, 'RAW_DN_0_10000')
        self.assertEqual(audit.offset_rule, 'PB_PRE04_ZERO_OFFSET')
        self.assertTrue(audit.reflectance_physically_plausible)
        self.assertTrue(audit.is_valid)
        self.assertEqual(audit.nodata_pixel_count, 1)

    def test_10m_spatial_resolution_verification(self):
        """Verify 10m spatial resolution verification and detection of mismatched resolution."""
        # 10m valid patch
        p10 = self.root / 'p10.tif'
        create_synthetic_geotiff(p10, bands=6, res=10.0)
        a10 = audit_single_patch(p10)
        self.assertTrue(a10.resolution_10m_verified)
        
        # 20m invalid patch
        p20 = self.root / 'p20.tif'
        create_synthetic_geotiff(p20, bands=6, res=20.0)
        a20 = audit_single_patch(p20)
        self.assertFalse(a20.resolution_10m_verified)
        self.assertTrue(any("SPATIAL_RESOLUTION_MISMATCH" in i for i in a20.issues))

    def test_4band_rgb_nir_detection(self):
        """A 4-band raster is correctly classified as RGB_NIR_4_BAND_ONLY and not 6-band ready."""
        tif_path = self.root / 'patch_4band.tif'
        create_synthetic_geotiff(tif_path, bands=4)
        
        audit = audit_single_patch(
            image_path=tif_path,
            patch_id='test_4b_01',
            check_sha_immutability=True
        )
        
        self.assertTrue(audit.file_exists)
        self.assertEqual(audit.band_count, 4)
        self.assertEqual(audit.spectral_readiness, 'RGB_NIR_4_BAND_ONLY')
        self.assertFalse(audit.is_valid)

    def test_3band_rgb_detection(self):
        """A 3-band raster is correctly classified as RGB_3_BAND_ONLY."""
        tif_path = self.root / 'patch_3band.tif'
        create_synthetic_geotiff(tif_path, bands=3)
        
        audit = audit_single_patch(
            image_path=tif_path,
            patch_id='test_3b_01'
        )
        
        self.assertEqual(audit.band_count, 3)
        self.assertEqual(audit.spectral_readiness, 'RGB_3_BAND_ONLY')
        self.assertFalse(audit.is_valid)

    def test_already_normalized_reflectance_patch(self):
        """A patch already in 0.0-1.0 reflectance range is correctly identified."""
        tif_path = self.root / 'patch_norm.tif'
        norm_data = np.full((6, 16, 16), 0.35, dtype='float32')
        norm_data[:, 0, 0] = 0.0
        create_synthetic_geotiff(tif_path, bands=6, data=norm_data)
        
        audit = audit_single_patch(
            image_path=tif_path,
            patch_id='test_norm_01'
        )
        
        self.assertEqual(audit.scale_status, 'NORMALIZED_REFLECTANCE_0_1')
        self.assertTrue(audit.reflectance_physically_plausible)
        self.assertTrue(audit.is_valid)

    def test_strict_zero_mutation_guarantee(self):
        """Verify that audit_single_patch does not alter file content bytes or hashes."""
        tif_path = self.root / 'patch_immutable.tif'
        create_synthetic_geotiff(tif_path, bands=6)
        
        initial_hash = compute_file_sha256(tif_path)
        
        for _ in range(3):
            audit = audit_single_patch(tif_path, patch_id='immut_test')
            self.assertFalse(audit.mutation_detected)
            self.assertEqual(audit.sha256_before, initial_hash)
            self.assertEqual(audit.sha256_after, initial_hash)
            
        final_hash = compute_file_sha256(tif_path)
        self.assertEqual(initial_hash, final_hash)

    def test_pb_post04_negative_offset_calibration(self):
        """Verify PB 04.00+ negative offset (-0.1) calibration logic: DN=5000 becomes 0.40 reflectance."""
        tif_path = self.root / 'patch_pb04.tif'
        data = np.full((6, 16, 16), 5000.0, dtype='float32')
        create_synthetic_geotiff(tif_path, bands=6, data=data)
        
        cal_data = {
            'scale': [0.0001] * 6,
            'offset': [-0.1] * 6,
            'baseline': '04.00'
        }
        
        audit = audit_single_patch(
            image_path=tif_path,
            patch_id='test_pb04_01',
            calibration_data=cal_data
        )
        
        self.assertEqual(audit.offset_rule, 'PB_POST04_NEGATIVE_OFFSET')
        for b_min, b_max in zip(audit.normalized_band_min, audit.normalized_band_max):
            self.assertAlmostEqual(b_min, 0.40, places=4)
            self.assertAlmostEqual(b_max, 0.40, places=4)
            
        self.assertTrue(audit.reflectance_physically_plausible)

    def test_saturation_and_distortion_flagging(self):
        """Verify that saturated pixels (> 1.0 BOA) and negative anomalies (< 0.0) are accurately flagged."""
        tif_path = self.root / 'patch_sat.tif'
        # 16x16 raster with standard DN = 3000 (reflectance = 0.30)
        data = np.full((6, 16, 16), 3000.0, dtype='float32')
        # Inject saturated pixel at (1, 1): DN = 15000 -> Reflectance = 1.50
        data[:, 1, 1] = 15000.0
        # Inject negative anomaly under PB 04.00 offset (-0.1) at (2, 2): DN = 200 -> Reflectance = 0.02 - 0.1 = -0.08
        data[:, 2, 2] = 200.0
        
        create_synthetic_geotiff(tif_path, bands=6, data=data)
        
        cal_data = {
            'scale': [0.0001] * 6,
            'offset': [-0.1] * 6,
            'baseline': '04.00'
        }
        
        audit = audit_single_patch(
            image_path=tif_path,
            patch_id='test_sat_flag',
            calibration_data=cal_data
        )
        
        self.assertTrue(audit.distortion_flagged)
        self.assertEqual(audit.saturated_pixel_count, 1)
        self.assertEqual(audit.negative_pixel_count, 1)
        # Total pixels = 256. 0 nodata, 1 sat at (1,1), 1 neg at (2,2) -> 254 clean pixels
        self.assertEqual(audit.clean_lcluc_pixel_count, 254)

    def test_quality_mask_alignment_and_mismatch(self):
        """Verify quality mask geometry alignment check."""
        img_path = self.root / 'img.tif'
        create_synthetic_geotiff(img_path, bands=6, height=16, width=16)
        
        qm_aligned = self.root / 'qm_aligned.tif'
        create_synthetic_geotiff(qm_aligned, bands=1, dtype='uint8', height=16, width=16)
        
        audit_ok = audit_single_patch(img_path, quality_mask_path=qm_aligned)
        self.assertTrue(audit_ok.quality_mask_aligned)
        
        qm_mismatched = self.root / 'qm_mismatched.tif'
        create_synthetic_geotiff(qm_mismatched, bands=1, dtype='uint8', height=32, width=32)
        
        audit_mismatch = audit_single_patch(img_path, quality_mask_path=qm_mismatched)
        self.assertFalse(audit_mismatch.quality_mask_aligned)
        self.assertIn("QUALITY_MASK_GEOMETRY_MISMATCH", audit_mismatch.issues)


class SpectralBatchContractTests(unittest.TestCase):
    def test_calibration_parameter_resolution(self):
        """Verify year and baseline mapping to authoritative calibration parameters."""
        s_2020, o_2020 = SpectralBatchContract.get_calibration_parameters(year=2020)
        self.assertEqual(s_2020, [0.0001] * 6)
        self.assertEqual(o_2020, [0.0] * 6)
        
        s_2021, o_2021 = SpectralBatchContract.get_calibration_parameters(year=2021)
        self.assertEqual(o_2021, [0.0] * 6)
        
        s_2022, o_2022 = SpectralBatchContract.get_calibration_parameters(year=2022)
        self.assertEqual(s_2022, [0.0001] * 6)
        self.assertEqual(o_2022, [-0.1] * 6)
        
        _, o_pb4 = SpectralBatchContract.get_calibration_parameters(year=2021, baseline='04.00')
        self.assertEqual(o_pb4, [-0.1] * 6)

    def test_apply_physical_reflectance_preserves_nodata(self):
        """Ensure apply_physical_reflectance correctly preserves nodata values and applies scaling."""
        raw = np.array([
            [[0.0, 1000.0], [2000.0, 3000.0]]
        ] * 6, dtype='float32')
        
        scale = [0.0001] * 6
        offset = [0.0] * 6
        
        refl = SpectralBatchContract.apply_physical_reflectance(raw, scale, offset, nodata_val=0.0)
        
        self.assertEqual(refl.shape, (6, 2, 2))
        self.assertEqual(refl[0, 0, 0], 0.0)
        self.assertAlmostEqual(refl[0, 0, 1], 0.10)
        self.assertAlmostEqual(refl[0, 1, 0], 0.20)
        self.assertAlmostEqual(refl[0, 1, 1], 0.30)

    def test_spectral_quality_mask_and_distortion_prevention(self):
        """Verify generate_spectral_quality_mask flags saturated, negative, and nodata pixels accurately."""
        # shape (6, 2, 2)
        raw = np.array([
            [[0.0, 15000.0], [200.0, 4000.0]]
        ] * 6, dtype='float32')
        
        scale = [0.0001] * 6
        offset = [-0.1] * 6  # PB 04.00
        
        # (0, 0): DN = 0 -> Nodata
        # (0, 1): DN = 15000 -> 15000 * 0.0001 - 0.1 = 1.40 (Saturated)
        # (1, 0): DN = 200 -> 200 * 0.0001 - 0.1 = -0.08 (Negative anomaly)
        # (1, 1): DN = 4000 -> 4000 * 0.0001 - 0.1 = 0.30 (Clean LCLUC)
        
        q_mask = SpectralBatchContract.generate_spectral_quality_mask(raw, scale, offset, nodata_val=0.0)
        
        self.assertTrue(q_mask['nodata_pixel_mask'][0, 0])
        self.assertTrue(q_mask['saturated_pixel_mask'][0, 1])
        self.assertTrue(q_mask['negative_pixel_mask'][1, 0])
        self.assertTrue(q_mask['clean_pixel_mask'][1, 1])
        
        self.assertEqual(q_mask['clean_pixel_count'], 1)
        self.assertEqual(q_mask['saturated_pixel_count'], 1)
        self.assertEqual(q_mask['negative_pixel_count'], 1)
        self.assertFalse(q_mask['is_contamination_free'])

    def test_apply_physical_reflectance_for_lcluc_masks_distortion(self):
        """Verify that apply_physical_reflectance_for_lcluc masks out saturated and negative pixels to prevent LCLUC distortion."""
        raw = np.array([
            [[0.0, 15000.0], [200.0, 4000.0]]
        ] * 6, dtype='float32')
        
        scale = [0.0001] * 6
        offset = [-0.1] * 6
        
        refl, clean_mask = SpectralBatchContract.apply_physical_reflectance_for_lcluc(
            raw, scale, offset, nodata_val=0.0, mask_saturated=True, clip_negative=True
        )
        
        # Saturated pixel at (0, 1) should be masked to 0.0 nodata
        self.assertEqual(refl[0, 0, 1], 0.0)
        # Clean pixel at (1, 1) preserved as 0.30
        self.assertAlmostEqual(refl[0, 1, 1], 0.30)
        # Clean mask
        self.assertTrue(clean_mask[1, 1])
        self.assertFalse(clean_mask[0, 1])
        self.assertFalse(clean_mask[0, 0])

    def test_spectral_contract_validation_including_10m_resolution(self):
        """Check contract rules pass for valid Sentinel-2 6-band at 10m and fail for wrong configurations."""
        valid, issues = SpectralBatchContract.validate_spectral_contract(
            band_count=6,
            band_names=list(S2_6BANDS),
            dtypes=['float32'] * 6,
            scale=[0.0001] * 6,
            offset=[0.0] * 6,
            spatial_resolution=(10.0, -10.0)
        )
        self.assertTrue(valid)
        self.assertEqual(len(issues), 0)
        
        # Wrong spatial resolution (20m)
        invalid_res, issues_res = SpectralBatchContract.validate_spectral_contract(
            band_count=6,
            band_names=list(S2_6BANDS),
            dtypes=['float32'] * 6,
            scale=[0.0001] * 6,
            offset=[0.0] * 6,
            spatial_resolution=(20.0, -20.0)
        )
        self.assertFalse(invalid_res)
        self.assertTrue(any("SPATIAL_RESOLUTION_MISMATCH" in i for i in issues_res))


if __name__ == '__main__':
    unittest.main()
