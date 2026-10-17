"""Root HTTP checks against isolated, non-executable constructed report fixture."""
import copy
import hashlib
import json
from pathlib import Path
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
fixture = json.loads((ROOT/'evidence/integration/model-error-read-browser-fixture-20261018.json').read_text('utf-8'))
request = fixture['request']
checks = []


def post(body, suffix='', raw=None, port=8003):
    data = json.dumps(body).encode() if raw is None else raw
    req = urllib.request.Request(f'http://127.0.0.1:{port}/v1/models/error-analysis'+suffix,
                                 data=data, headers={'Content-Type': 'application/json'}, method='POST')
    try:
        response = urllib.request.urlopen(req, timeout=15)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        return response.status, dict(response.headers), response.read()


status, headers, raw = post(request)
view = json.loads(raw)
assert status == 200 and view == fixture['response'] and headers['cache-control'] == 'no-store'
checks.append('main_app_live_pinned_response_matches_actual_writer_fixture')
val, test = (view['analysis']['by_split'][s] for s in ('val', 'test'))
assert val['reference_pixel_count'] == 12 and val['misclassified_pixel_count'] == 5
assert test['reference_pixel_count'] == 10 and test['misclassified_pixel_count'] == 3
for split in (val, test):
    water = split['classes'][0]
    assert (water['true_positive_pixels'], water['false_negative_pixels'], water['false_positive_pixels']) == (3, 1, 2)
    assert water['precision'] == 3/5 and water['recall'] == 3/4
assert val['classes'][7]['precision'] is None and val['classes'][7]['recall'] == 0
assert test['classes'][7]['precision'] is None and test['classes'][7]['recall'] is None
checks.append('independent_hand_computed_denominators_and_null_not_zero')
downloads = []
for artifact in view['artifacts']:
    code, asset_headers, content = post(request, '/assets/'+str(artifact['index']))
    assert code == 200 and len(content) == artifact['bytes']
    assert hashlib.sha256(content).hexdigest() == artifact['sha256']
    assert asset_headers['cache-control'] == 'no-store'
    downloads.append({'filename': artifact['filename'], 'bytes': len(content), 'sha256': artifact['sha256']})
checks.append('all_three_live_downloads_match_pinned_bytes_and_sha')
bad = copy.deepcopy(request)
bad['training_report_sha256'] = '0'*64
assert post(bad)[0] == 409
checks.append('live_conflicting_training_report_pin_rejected')
bad = copy.deepcopy(request)
bad['model_ref']['id'] = 'missing-fixture'
assert post(bad)[0] == 404
assert post(request, '/assets/3')[0] == 404
checks.append('live_unknown_model_and_out_of_range_asset_rejected')
assert post(None, raw=b'{"schema_version":1,"schema_version":1}')[0] == 400
assert post(None, raw=b' '*16385)[0] == 413
checks.append('live_duplicate_json_and_body_limit_rejected')
result = {'scope': fixture['scope'], 'checks_passed': checks, 'downloads': downloads,
          'scientific_accuracy_validated': False, 'standard_gmais_result': False,
          'training_inference_checkpoint_load': 0, 'operating_api_requests': 0}
(ROOT/'evidence/integration/model-error-read-independent-20261018.json').write_text(
    json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(f'PASS {len(checks)} independent live HTTP scenarios; fixture only; no model execution.')
