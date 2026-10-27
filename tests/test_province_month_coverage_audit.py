"""Fail-closed inventory audit tests against the pinned operating report."""
from pathlib import Path
import json, sys, tempfile, unittest
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"backend"))
sys.path.insert(0,str(ROOT/"scripts"))
from app.ml.province_month_coverage_audit import DRY_SEASON_MONTHS,FIRST_GROUP_IDS,MONTHS,YEARS,build_province_month_audit
from app.ml.province_year_coverage import CoverageEvidenceError, sha256_file
from g2_province_month_audit import _metric as format_audit_metric

class TestProvinceMonthCoverageAudit(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.result=build_province_month_audit(ROOT/"data")
 def test_matrix_and_inventory_truth(self):
  self.assertEqual(self.result.total_cells,432); self.assertEqual(self.result.dry_season_cells,144); self.assertEqual(self.result.wet_season_cells,288)
  self.assertEqual(self.result.total_patches_inventory,1779); self.assertEqual(self.result.total_unique_scenes,107)
  self.assertEqual(self.result.total_eligible_patches,1407); self.assertEqual(self.result.total_insufficient_patches,372)
  self.assertEqual(self.result.active_observation_cells,77)
 def test_unique_scene_is_not_patch_count(self):
  active=[c for c in self.result.cells if c.patch_rows_count]
  self.assertTrue(any(c.patch_rows_count>c.discovered_scenes_count for c in active))
  self.assertTrue(all(c.verified_download_scenes_count==0 for c in active))
 def test_patch_ratio_is_never_province_coverage(self):
  for cell in self.result.cells:
   self.assertIsNone(cell.valid_coverage_pct); self.assertIsNone(cell.outside_footprint_pct)
   self.assertEqual(cell.measurement_status,"BLOCKED_NOT_MEASURED")
   self.assertEqual(cell.inventory_status,"VERIFIED_REAL_INVENTORY_ONLY")
  self.assertEqual(self.result.nominal_cells_count,0); self.assertEqual(self.result.degraded_cells_count,0)
  self.assertEqual(self.result.unclassified_cells_count,432)
  self.assertTrue(all(r.unclassified_cell_count==r.total_cells and r.degraded_cell_count==0 for r in self.result.province_rollups))
  self.assertTrue(all(r.unclassified_cell_count==r.total_cells and r.degraded_cell_count==0 for r in self.result.year_rollups))
 def test_scope_and_season(self):
  self.assertEqual({c.province_id for c in self.result.cells},FIRST_GROUP_IDS)
  for pid in FIRST_GROUP_IDS:
   self.assertEqual(len([c for c in self.result.cells if c.province_id==pid]),72)
  for c in self.result.cells:
   self.assertEqual(c.season_policy,"DRY_SEASON_WINDOW" if c.month in DRY_SEASON_MONTHS else "WET_SEASON_MONSOON")
 def test_source_pin_is_fail_closed(self):
  with self.assertRaisesRegex(CoverageEvidenceError,"SOURCE_SHA256_MISMATCH"):
   build_province_month_audit(ROOT/"data",expected_source_sha256="0"*64)
 def test_serialization_preserves_nulls(self):
  value=self.result.to_dict(); self.assertEqual(value["coverage_measurement_status"],"BLOCKED_NOT_MEASURED")
  self.assertIsNone(value["cells"][0]["valid_coverage_pct"])
  self.assertEqual(value["schema_version"],"4.1")
 def test_cli_formats_unmeasured_null_safely(self):
  self.assertEqual(format_audit_metric(None,"%"),"null")
  self.assertEqual(format_audit_metric(2.5,"%",1),"2.5%")
 def test_unknown_quality_status_is_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td); folder=root/"first-group-training-esri-v1"; folder.mkdir()
   doc={"policy_version":"guarded-deficit-1024","status":"deficit_guarded_bounded_stage","executed":True,"scenes":[{
    "province":"banten","aoi":"banten","year":"2020","datetime":"2020-06-01T00:00:00Z","scene_id":"s1","patch_id":"p1",
    "split":"val","quality_status":"unknown","quality_mask_path":"q.tif","patch_sha256":{"quality":"a"*64}}]}
   path=folder/"annual-window-report.json"; path.write_text(json.dumps(doc),encoding="utf-8")
   with self.assertRaisesRegex(CoverageEvidenceError,"QUALITY_STATUS_UNKNOWN"):
    build_province_month_audit(root,expected_source_sha256=sha256_file(path))

if __name__=="__main__": unittest.main()
