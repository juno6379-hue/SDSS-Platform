"""고정 행렬·임시 모델 디렉터리 시험. 운영 데이터/모델/학습은 사용하지 않는다."""
import ast
import copy
import csv
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from backend.app.ml.error_analysis import confusion_error_analysis, write_training_error_analysis


NAMES = ['water', 'trees', 'grass', 'flooded_vegetation', 'crops', 'shrub', 'built', 'bare', 'snow']


def matrix():
    values = [[0]*9 for _ in range(9)]
    values[0][:2] = [3, 1]
    values[1][:2] = [2, 4]
    return values


def report():
    val = {'confusion_matrix': matrix(), 'loss': .1}
    return {'model_id': 'fixture', 'training_state': 'completed', 'selected_epoch': 1,
            'class_names': NAMES.copy(), 'checkpoint_sha256': 'a'*64,
            'reference_kind': 'worldcover_weak_label',
            'history': [{'epoch': 1, 'val': copy.deepcopy(val)}, {'epoch': 2, 'val': {'loss': .2}}],
            'selected_validation_metrics': val, 'test_metrics': {'confusion_matrix': matrix()}}


class ErrorAnalysisTests(unittest.TestCase):
    def test_reference_rows_predicted_columns_fp_fn_and_missing_denominators(self):
        result = confusion_error_analysis(matrix(), NAMES)
        self.assertEqual(result['reference_pixel_count'], 10)
        self.assertEqual(result['misclassified_pixel_count'], 3)
        item = result['classes'][0]
        self.assertEqual([item[k] for k in ('reference_pixels', 'predicted_pixels', 'true_positive_pixels', 'false_negative_pixels', 'false_positive_pixels')], [4, 5, 3, 1, 2])
        self.assertEqual(item['recall'], .75)
        self.assertEqual(item['precision'], .6)
        self.assertIsNone(result['classes'][7]['recall'])
        self.assertIsNone(result['classes'][7]['precision'])
        self.assertEqual(result['classes'][7]['status'], 'REFERENCE_AND_PREDICTION_ABSENT')

    def test_reference_present_never_predicted_and_false_positive_only_are_distinct(self):
        values = [[0]*9 for _ in range(9)]; values[7][1] = 20
        result = confusion_error_analysis(values, NAMES)
        bare, trees = result['classes'][7], result['classes'][1]
        self.assertEqual(bare['status'], 'REFERENCE_PRESENT_NOT_PREDICTED')
        self.assertEqual(bare['recall'], 0)
        self.assertIsNone(bare['precision'])
        self.assertEqual(bare['false_negative_pixels'], 20)
        self.assertEqual(trees['status'], 'NO_REFERENCE_SUPPORT')
        self.assertIsNone(trees['recall'])
        self.assertEqual(trees['false_positive_pixels'], 20)
        self.assertEqual(result['unpredicted_reference_present_classes'], [7])

    def test_pairs_exclude_diagonal_sort_deterministically_and_sum_to_errors(self):
        values = matrix(); values[8][7] = 2
        result = confusion_error_analysis(values, NAMES)
        self.assertEqual([(p['reference_class_index'], p['predicted_class_index']) for p in result['confusion_pairs']], [(1, 0), (8, 7), (0, 1)])
        self.assertEqual(sum(p['pixel_count'] for p in result['confusion_pairs']), result['misclassified_pixel_count'])

    def test_empty_and_perfect_predictions_are_not_independent_accuracy_certificates(self):
        for values in ([[0]*9 for _ in range(9)], [[int(i == j) for j in range(9)] for i in range(9)]):
            result = confusion_error_analysis(values, NAMES)
            self.assertEqual(result['misclassified_pixel_count'], 0)
            self.assertEqual(result['confusion_pairs'], [])
            self.assertIs(result['independent_accuracy_certified'], False)
            self.assertIs(result['spatial_error_map_generated'], False)

    def test_bad_shapes_bool_negative_fraction_and_huge_counts_rejected(self):
        for invalid in (None, [], [[0]*8 for _ in range(9)]):
            with self.assertRaises(ValueError): confusion_error_analysis(invalid, NAMES)
        for value in (True, -1, 1.5, float('nan'), 2**53):
            values = matrix(); values[0][0] = value
            with self.assertRaises(ValueError): confusion_error_analysis(values, NAMES)
        for names in (NAMES[:-1], [None]*9, ['\ud800']*9, ['a\n']*9):
            with self.assertRaises(ValueError): confusion_error_analysis(matrix(), names)

    def test_pure_calculation_preserves_input_without_io(self):
        values = matrix(); before = copy.deepcopy(values)
        with patch('builtins.open', side_effect=AssertionError('pure calculation IO')):
            confusion_error_analysis(values, NAMES)
        self.assertEqual(values, before)

    def test_temp_report_exports_selected_validation_and_final_test_only_with_sha(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); dest = root/'models'/'fixture'; dest.mkdir(parents=True)
            data = report(); original = copy.deepcopy(data)
            result = write_training_error_analysis(data, dest, root)
            self.assertEqual(data, original)
            self.assertEqual(result['selected_epoch'], 1)
            self.assertEqual(set(result['by_split']), {'val', 'test'})
            self.assertFalse(result['test_used_for_epoch_selection'])
            self.assertFalse(result['scientific_accuracy_validated'])
            self.assertEqual(result['reference_kind'], 'worldcover_weak_label')
            self.assertEqual(len(result['artifacts']), 3)
            for artifact in result['artifacts']:
                raw = (root/artifact['path']).read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), artifact['sha256'])
                self.assertEqual(len(raw), artifact['bytes'])
            stored = json.loads((dest/'error-analysis.json').read_text(encoding='utf-8'))
            self.assertEqual(stored['by_split'], result['by_split'])
            rows = list(csv.DictReader(io.StringIO((dest/'error-analysis-classes.csv').read_text(encoding='utf-8-sig'))))
            self.assertEqual(len(rows), 18)
            self.assertEqual({r['split'] for r in rows}, {'val', 'test'})

    def test_paused_or_selected_epoch_mismatch_does_not_write(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); dest = root/'model'; dest.mkdir()
            for change in ({'training_state': 'paused'}, {'selected_epoch': True}, {'selected_epoch': 2}, {'test_metrics': None}):
                with self.assertRaises(ValueError): write_training_error_analysis({**report(), **change}, dest, root)
                self.assertEqual(list(dest.iterdir()), [])

    def test_csv_formula_escape_preserves_original_json_names(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); dest = root/'model'; dest.mkdir(); data = report()
            data['class_names'] = ['=1+1', '+cmd', '-cmd', '@cmd', ' =formula', 'normal', '한글', 'bare', 'snow']
            result = write_training_error_analysis(data, dest, root)
            rows = list(csv.DictReader(io.StringIO((dest/'error-analysis-classes.csv').read_text(encoding='utf-8-sig'))))
            self.assertEqual([row['class_name'] for row in rows[:6]], ["'=1+1", "'+cmd", "'-cmd", "'@cmd", "' =formula", 'normal'])
            self.assertEqual(result['by_split']['val']['classes'][0]['class_name'], '=1+1')

    def test_identical_artifacts_reuse_and_different_bytes_never_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); dest = root/'model'; dest.mkdir(); first = write_training_error_analysis(report(), dest, root)
            self.assertEqual(first, write_training_error_analysis(report(), dest, root))
            (dest/'error-analysis-classes.csv').write_bytes(b'preserve')
            snapshot = {p.name: p.read_bytes() for p in dest.iterdir()}
            with self.assertRaises(ValueError): write_training_error_analysis(report(), dest, root)
            self.assertEqual(snapshot, {p.name: p.read_bytes() for p in dest.iterdir()})

    def test_root_escape_and_existing_directory_artifact_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            top = Path(temp); root = top/'data'; root.mkdir(); outside = top/'outside'; outside.mkdir()
            with self.assertRaises(ValueError): write_training_error_analysis(report(), outside, root)
            dest = root/'model'; dest.mkdir(); (dest/'error-analysis.json').mkdir()
            with self.assertRaises(ValueError): write_training_error_analysis(report(), dest, root)
            self.assertEqual(list((dest/'error-analysis.json').iterdir()), [])

    def test_completion_call_precedes_report_persist_without_changing_other_service_functions(self):
        root = Path(__file__).resolve().parents[1]
        old = ast.parse((root/'evidence/integration/lcluc-ml-original-service-20261018.py').read_text(encoding='utf-8'))
        new = ast.parse((root/'backend/app/ml/service.py').read_text(encoding='utf-8'))
        originals = {n.name: ast.dump(n) for n in old.body if isinstance(n, ast.FunctionDef)}
        for n in new.body:
            if isinstance(n, ast.FunctionDef) and n.name != 'train_model': self.assertEqual(ast.dump(n), originals[n.name], n.name)
        source = (root/'backend/app/ml/service.py').read_text(encoding='utf-8')
        self.assertEqual(source.count('report[\'error_analysis\']=write_training_error_analysis(report,destination,root)'), 1)
        self.assertLess(source.index('report[\'error_analysis\']=write_training_error_analysis'), source.index("(destination/'report.json').write_text", source.index('report[\'error_analysis\']=write_training_error_analysis')))


if __name__ == '__main__': unittest.main()
