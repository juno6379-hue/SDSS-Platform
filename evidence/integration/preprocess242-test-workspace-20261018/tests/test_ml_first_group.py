"""First Group 감사의 누락·합성제외·품질·연차 누출 방지 회귀시험."""
import json
import tempfile
import unittest
from pathlib import Path
import numpy as np
import rasterio
from rasterio.transform import from_origin
from scripts.audit_first_group import audit, inspect_scene, holdout_plan, PROVINCES


class FirstGroupAuditTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory()
        self.root=Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def manifest(self,scenes,synthetic=True):
        path=self.root/'inputs.json'
        path.write_text(json.dumps({'scenes':scenes,'synthetic':synthetic}),encoding='utf-8')
        return path

    def rasters(self,height=256,invalid_rows=0):
        profile={'driver':'GTiff','crs':'EPSG:32748','width':256,'height':height,'transform':from_origin(500000,9000000,10,10),'nodata':0}
        with rasterio.open(self.root/'image.tif','w',**profile,count=3,dtype='uint16') as dst:
            dst.write(np.full((3,height,256),1000,dtype='uint16'))
        labels=np.full((height,256),10,dtype='uint8');labels[:invalid_rows]=0
        with rasterio.open(self.root/'label.tif','w',**profile,count=1,dtype='uint8') as dst:
            dst.write(labels,1)
        return {'aoi':'west_java','year':2021,'image_path':'image.tif','label_path':'label.tif','label_source':'worldcover','source':'explicit-generated-test-fixture','scene_id':'fixture_scene'}

    def test_empty_inventory_has_all_36_missing(self):
        report=audit([self.manifest([])],self.root)
        self.assertEqual(report['expected_combinations'],36)
        self.assertEqual(len(report['missing_images']),36)
        self.assertEqual(len(report['missing_labels']),36)
        self.assertFalse(report['learning_ready'])

    def test_padded_nominal_patch_is_not_full_or_quality_eligible(self):
        row=self.rasters(height=300,invalid_rows=64)
        item=inspect_scene(row,self.root,.8)
        self.assertEqual(item['nominal_patch_count'],2)
        self.assertEqual(item['actual_256_patch_count'],1)
        self.assertEqual(item['nonempty_patch_count'],2)
        self.assertEqual(item['eligible_patch_count'],0)
        self.assertEqual(item['class_counts'],{'1':236*256})

    def test_synthetic_fixture_cannot_satisfy_actual_data_goal(self):
        row=self.rasters()
        report=audit([self.manifest([row])],self.root)
        self.assertEqual(report['inventory'][0]['eligible_patch_count'],1)
        self.assertEqual(report['eligible_patch_count'],0)
        self.assertEqual(report['image_cells_available'],0)
        self.assertFalse(report['target_patch_count_met'])

    def test_central_java_excluded_and_missing_label_does_not_hide_image(self):
        row=self.rasters();row['label_path']='missing.tif'
        outside={**row,'aoi':'central_java_candidate'}
        report=audit([self.manifest([row,outside])],self.root)
        self.assertEqual(len(report['excluded']),1)
        self.assertEqual(report['inventory'][0]['image_status'],'local_file_verified')
        self.assertEqual(report['inventory'][0]['label_status'],'missing')
        self.assertIn('missing.tif',report['inventory'][0]['error'])

    def test_six_provinces_split_four_one_one_and_shared_source_stays_together(self):
        records=[{'province':province,'year':year,'source_group':province+'_'+str(year)} for province in PROVINCES for year in (2020,2021)]
        plan=holdout_plan(records)
        self.assertEqual(plan['province_counts'],{'train':4,'val':1,'test':1})
        self.assertTrue(plan['independent_expert_reference_required'])
        records[0]['source_group']='shared_scene';records[-1]['source_group']='shared_scene'
        joined=holdout_plan(records)
        self.assertEqual(joined['province_splits'][records[0]['province']],joined['province_splits'][records[-1]['province']])

    def test_duplicate_year_copy_does_not_increase_unique_eligible_patches(self):
        row=self.rasters()
        report=audit([self.manifest([row,{**row,'year':2022}])],self.root)
        self.assertTrue(report['inventory'][1]['duplicate_raster_pair'])
        self.assertEqual(report['inventory'][1]['eligible_patch_count'],0)
        self.assertEqual(report['inventory'][0]['split'],report['inventory'][1]['split'])

    def test_worldcover_2021_does_not_validate_a_2020_reference(self):
        row={**self.rasters(),'year':2020,'datetime':'2020-09-01T00:00:00Z','label_year':2021}
        inspected=inspect_scene(row,self.root,.8)
        self.assertTrue(inspected['acquisition_year_match'])
        self.assertFalse(inspected['label_year_match'])
        self.assertEqual(inspected['label_year'],2021)

    def test_province_geometry_excludes_outside_pixels_from_quality(self):
        from rasterio.warp import transform_geom
        row=self.rasters()
        half={'type':'Polygon','coordinates':[[[500000,9000000],[501280,9000000],[501280,8997440],[500000,8997440],[500000,9000000]]]}
        geometry=transform_geom('EPSG:32748','EPSG:4326',half)
        inspected=inspect_scene(row,self.root,.8,geometry)
        self.assertAlmostEqual(inspected['province_boundary_pixel_ratio'],.5)
        self.assertEqual(inspected['valid_pixels'],128*256)
        self.assertEqual(inspected['eligible_patch_count'],0)


if __name__=='__main__':
    unittest.main()
