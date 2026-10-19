import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
before = json.loads((root / 'evidence/integration/toolbox-ui-preflight-20261018.json').read_text(encoding='utf-8-sig'))
details = ['ModelAnalysisWorkspace.tsx', 'model-workspace.css', 'LclucWorkflowPanel.tsx', 'SDSSChrome.tsx', 'sdss-chrome.css']
files = ['App.tsx', 'PlatformShell.tsx', 'GeoAIToolbox.tsx', 'geoai-toolbox.css', 'toolboxAdapter.ts', 'toolboxAdapter.test.mjs'] + details
hashes = {'frontend/src/' + name: hashlib.sha256((root / 'frontend/src' / name).read_bytes()).hexdigest() for name in files}
unchanged = {name: hashes['frontend/src/' + name] == before['frontend/src/' + name]['sha256'] for name in details}
assert all(unchanged.values()), unchanged
report = {
    'observed_at_utc': datetime.now(timezone.utc).isoformat(),
    'source_sha256': hashes, 'detail_files_unchanged': unchanged,
    'frontend_all': {'command': 'node --test src/*.test.mjs', 'pass': 293, 'fail': 0, 'skip': 0, 'duration_ms': 43750.147, 'exit': 0},
    'focused_adapter': {'pass': 5, 'overlaps_full_suite': True},
    'independent_checks': {'pass': 11, 'evidence': 'toolbox-ui-independent-20261018.json'},
    'build': {'command': 'npm run build', 'exit': 0, 'modules': 123, 'vite_seconds': 44.32, 'warning': 'JavaScript chunk exceeds 500 kB; output 1739.26 kB'},
    'browser': {'url': 'http://127.0.0.1:5174/#/view/12', 'cards_verified': ['lcluc','climate','carbon','biodiversity','coastal','flood'], 'return_to_hub': True, 'banten_map_and_overview': True, 'catalog_quick_action': '#/catalog', 'mobile': {'width':390, 'height':844, 'document_scroll_width':375, 'card_columns':1}, 'default': {'width':1280, 'document_scroll_width':1265}, 'viewport_reset':True, 'new_console_errors_after_final_reload':0, 'historical_hmr_error':'2026-10-18T01:17:10.289Z intermediate wiring; corrected before final verification'},
    'screenshots': ['toolbox-ui-desktop-top-20261018.jpg','toolbox-ui-desktop-20261018.jpg','toolbox-ui-mobile-20261018.jpg'],
    'scope': {'api_writes':0, 'service_restarts':0, 'collection_changes':0, 'scientific_approval':False},
    'coordination': {'other_thread':'01a1470d-b3a0-7a50-95ac-0e050d4cef86', 'other_thread_observed_active':True, 'automation':'geoai-2', 'duplicate_collection_started':False},
}
(root / 'evidence/integration/toolbox-ui-final-20261018.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('Final evidence saved; 5 detail source hashes unchanged.')
