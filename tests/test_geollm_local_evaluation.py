"""Evaluation checks cannot authorize tools, infer results, or install models."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('geollm_local_evaluation', ROOT/'scripts/evaluate_geollm_local.py')
evaluation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluation)


class LocalEvaluationTests(unittest.TestCase):
    def answer(self):
        return {'province': 'Gorontalo', 'start_year': 2021, 'end_year': 2025,
                'analysis_type': 'lcluc_change', 'tool': 'lcluc-agent', 'may_execute': False,
                'result_available': False, 'forest_loss_ha': None, 'status': 'BLOCKED',
                'evidence_ids': ['model', 'result']}

    def score(self, value):
        return evaluation.score(json.dumps(value), evaluation.CASES[0])

    def test_valid_blocked_plan(self):
        self.assertTrue(self.score(self.answer())['all_pass'])

    def test_schema_valid_is_not_semantically_correct(self):
        value = self.answer()
        value.update(may_execute=True, result_available=True, forest_loss_ha=500, status='READY')
        result = self.score(value)
        self.assertTrue(result['json_schema_valid'])
        self.assertFalse(result['grounded_fields'])
        self.assertFalse(result['all_pass'])

    def test_correct_tool_with_wrong_period_fails_intent(self):
        value = self.answer(); value['end_year'] = 2024
        self.assertFalse(self.score(value)['intent_exact'])
        self.assertTrue(self.score(value)['tool_correct'])

    def test_invented_citation_and_empty_citation_fail(self):
        for ids in ([], ['BIG-official-approval'], ['model', 'made-up']):
            value = self.answer(); value['evidence_ids'] = ids
            self.assertFalse(self.score(value)['citation_ids_valid'])

    def test_unknown_property_and_wrong_type_fail_schema(self):
        for value in (dict(self.answer(), sql='DROP TABLE records'), dict(self.answer(), start_year='2021')):
            self.assertFalse(self.score(value)['json_schema_valid'])

    def test_json_wrapper_duplicate_and_nonfinite_fail(self):
        valid = json.dumps(self.answer())
        for raw in ('```json\n'+valid+'\n```', valid[:-1]+',"status":"READY"}',
                    valid.replace('null', 'NaN'), valid.replace('null', '1e999'), 'null', '{}'):
            self.assertFalse(evaluation.score(raw, evaluation.CASES[0])['all_pass'])

    def test_local_fixed_urls_only_no_network_on_invalid_url(self):
        with patch.object(evaluation.OPENER, 'open') as request:
            for base in ('https://example.com', 'http://127.0.0.1:8000', 'file:///etc'):
                with self.assertRaises(ValueError):
                    evaluation.request_json(base, '/api/chat')
            request.assert_not_called()

    def test_missing_model_never_pulls_or_calls_chat(self):
        calls = []
        def reply(base, path, payload=None, timeout=45):
            calls.append(path)
            if path == '/api/tags': return {'models': []}, 0
            if path == '/api/version': return {'version': 'fixture'}, 0
            if path == '/api/ps': return {'models': []}, 0
            return {'mode': 'predefined-pattern', 'evidence': []}, 0
        with patch.object(evaluation, 'request_json', side_effect=reply):
            result = evaluation.run(['qwen3:8b'])
        self.assertEqual(result['models'][0]['status'], 'NOT_INSTALLED')
        self.assertNotIn('/api/pull', calls)
        self.assertNotIn('/api/chat', calls)
        self.assertEqual(result['tool_executions'], 0)

    def test_cosine_dimension_zero_and_known_ranking(self):
        self.assertAlmostEqual(evaluation.cosine([1, 0], [1, 0]), 1)
        self.assertAlmostEqual(evaluation.cosine([1, 0], [0, 1]), 0)
        for left, right in (([], []), ([1], [1, 2]), ([0], [0])):
            with self.assertRaises(ValueError): evaluation.cosine(left, right)

    def test_embedding_nonfinite_strings_and_boolean_rejected(self):
        for value in (float('nan'), float('inf'), '0.5', True):
            with self.assertRaises(ValueError): evaluation.cosine([value], [1])

    def test_corpus_is_repository_source_and_no_policy_authenticity_claim(self):
        chunks = evaluation.corpus()
        self.assertEqual(len(chunks), 4)
        for chunk in chunks:
            self.assertEqual(chunk['source_kind'], 'INTERNAL_CODE_NOT_OFFICIAL_POLICY')
            self.assertTrue((ROOT/chunk['source']).is_file())
            self.assertEqual(len(chunk['source_sha256']), 64)

    def test_redirect_is_rejected_before_second_request(self):
        with self.assertRaises(ValueError):
            evaluation.NoRedirect().redirect_request(None, None, 302, 'redirect', {}, 'https://example.com')

    def test_transport_rejects_duplicate_and_nonfinite_before_native_tools(self):
        for raw in (b'{"model":"a","model":"b"}', b'{"number":NaN}', b'{"number":1e999}'):
            response = unittest.mock.MagicMock()
            response.__enter__.return_value.read.return_value = raw
            with patch.object(evaluation.OPENER, 'open', return_value=response):
                with self.assertRaises(ValueError):
                    evaluation.request_json(evaluation.OLLAMA, '/api/chat', {})


if __name__ == '__main__':
    unittest.main()
