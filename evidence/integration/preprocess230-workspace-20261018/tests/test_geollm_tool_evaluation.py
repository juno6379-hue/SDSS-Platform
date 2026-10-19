import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
spec = importlib.util.spec_from_file_location('geollm_tool_evaluation', ROOT/'scripts/evaluate_geollm_tools.py')
evaluation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluation)


class ToolEvaluationTests(unittest.TestCase):
    def call(self):
        return [{'function': {'name': 'propose_lcluc_plan', 'arguments': {
            'province': 'Gorontalo', 'start_year': 2021, 'end_year': 2025}}}]

    def test_only_exact_single_planning_call_passes(self):
        self.assertTrue(evaluation.score_calls(self.call(), evaluation.CASES[0]['expected']))
        self.assertFalse(evaluation.score_calls(self.call()*2, evaluation.CASES[0]['expected']))

    def test_malformed_tool_data_is_failure_not_exception(self):
        for calls in (None, {}, [], [None], [5], [{}], [{'function': None}], [{'function': {'arguments': 'wrong'}}]):
            self.assertFalse(evaluation.score_calls(calls, evaluation.CASES[0]['expected']))

    def test_generated_path_and_wrong_period_rejected(self):
        calls = self.call(); calls[0]['function']['arguments']['path'] = '/api/execute'
        self.assertFalse(evaluation.score_calls(calls, evaluation.CASES[0]['expected']))
        calls = self.call(); calls[0]['function']['arguments']['end_year'] = 2024
        self.assertFalse(evaluation.score_calls(calls, evaluation.CASES[0]['expected']))

    def test_execution_tool_is_never_a_planning_success(self):
        calls = self.call(); calls[0]['function']['name'] = 'execute_lcluc'
        self.assertFalse(evaluation.score_calls(calls, evaluation.CASES[0]['expected']))


if __name__ == '__main__':
    unittest.main()
