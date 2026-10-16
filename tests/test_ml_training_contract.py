"""학습 계약 감사의 클래스 불균형·ignore·단일 예측과 기본설정 판독 검증."""
import unittest
from pathlib import Path
import numpy as np
from scripts.audit_training_contract import distribution, numeric_summary, source_defaults, WORLD_COVER


class TrainingContractAuditTests(unittest.TestCase):
    def test_imbalance_ratios_exclude_ignore_and_invalid_labels(self):
        values=np.asarray([1,1,1,4,255,-1,np.nan])
        actual=distribution(values)
        self.assertEqual(actual['valid_pixels'],4)
        self.assertEqual(actual['ignore_255_pixels'],1)
        self.assertEqual(actual['other_invalid_pixels'],2)
        self.assertEqual(actual['class_ratios'][1],.75)
        self.assertEqual(actual['class_ratios'][4],.25)
        self.assertFalse(actual['single_class_prediction'])

    def test_grass_collapse_is_detected_without_calling_it_accuracy(self):
        actual=distribution(np.full((10,10),2,dtype='uint8'))
        self.assertEqual(actual['unique_classes'],[2])
        self.assertTrue(actual['single_class_prediction'])
        self.assertEqual(actual['dominant_ratio'],1)
        self.assertNotIn('accuracy',actual)

    def test_ignore_only_raster_has_no_valid_class_ratio(self):
        actual=distribution(np.full((2,2),255,dtype='uint8'))
        self.assertEqual(actual['valid_pixels'],0)
        self.assertEqual(actual['class_ratios'],[None]*9)
        self.assertFalse(actual['single_class_prediction'])

    def test_exact_worldcover_mapping_and_zero_is_not_water(self):
        self.assertEqual(WORLD_COVER,{10:1,20:5,30:2,40:4,50:6,60:7,70:8,80:0,90:3,95:1,100:2})
        self.assertNotIn(0,WORLD_COVER)

    def test_numeric_percentiles_and_training_defaults_are_explicit(self):
        actual=numeric_summary(np.asarray([0,10,20,np.nan],dtype='float32'))
        self.assertEqual(actual['min'],0)
        self.assertEqual(actual['max'],20)
        self.assertEqual(actual['percentiles']['50'],10)
        self.assertEqual(actual['nonfinite_count'],1)
        path=Path(__file__).resolve().parents[1]/'backend/app/ml/service.py'
        defaults=source_defaults(path)
        self.assertEqual(defaults['optimizer'],'adam')
        self.assertEqual(defaults['lr'],.001)
        self.assertEqual(defaults['loss'],'cross_entropy')
        self.assertIsNone(defaults['class_weights'])


if __name__=='__main__':
    unittest.main()
