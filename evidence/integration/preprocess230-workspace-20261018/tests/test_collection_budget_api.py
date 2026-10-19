"""Read-only budget routes use temporary roots; no production catalog or HTTP."""
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from fastapi.testclient import TestClient

_bootstrap = tempfile.TemporaryDirectory()
with patch.dict(os.environ, {'GEOAI_DATA_ROOT': _bootstrap.name}):
    from app import main


class BudgetApiTests(unittest.TestCase):
    def test_unknown_is_safe_no_store_and_authenticated(self):
        with tempfile.TemporaryDirectory() as root, patch.object(main, 'store', SimpleNamespace(root=Path(root))), patch.dict(os.environ, {'GEOAI_API_TOKEN': 'synthetic-token'}):
            client = TestClient(main.app)
            self.assertEqual(client.get('/api/data/collection-budget-status').status_code, 401)
            response = client.get('/api/data/collection-budget-status', headers={'Authorization': 'Bearer synthetic-token'})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers['cache-control'], 'no-store')
            self.assertFalse(response.json()['available'])
            self.assertEqual(list(Path(root).iterdir()), [])

    def test_collection_route_attaches_independent_snapshot_without_replacing_counts(self):
        observed = {'schema_version': 1, 'available': False, 'status': 'UNCONFIRMED', 'process_verification': 'UNKNOWN'}
        with tempfile.TemporaryDirectory() as root, patch.object(main, 'store', SimpleNamespace(root=Path(root))), patch.dict(os.environ, {'GEOAI_API_TOKEN': ''}), patch('app.collection_status.collection_status', return_value={'collection_targets': {'eligible_total': 17}}), patch('app.collection_budget_status.collection_budget_status', return_value=observed):
            result = TestClient(main.app).get('/api/data/collection-status')
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.json()['collection_targets']['eligible_total'], 17)
            self.assertEqual(result.json()['collection_targets']['budget_status'], observed)
            self.assertEqual(list(Path(root).iterdir()), [])


if __name__ == '__main__':
    unittest.main()
