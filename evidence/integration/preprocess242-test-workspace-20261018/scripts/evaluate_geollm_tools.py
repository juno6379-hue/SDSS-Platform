"""Native Ollama planning-tool proposals only: no function is ever executed."""
import argparse
import json
from pathlib import Path
import time
from urllib.error import HTTPError, URLError

from jsonschema import Draft202012Validator
from evaluate_geollm_local import CASES, OLLAMA, request_json

PARAMETERS = {'type': 'object', 'additionalProperties': False,
              'required': ['province', 'start_year', 'end_year'],
              'properties': {'province': {'type': 'string'}, 'start_year': {'type': 'integer'},
                             'end_year': {'type': 'integer'}}}
TOOL = {'type': 'function', 'function': {
    'name': 'propose_lcluc_plan',
    'description': 'Propose a LCLUC plan for a province and period. Planning only; never grants approval or submits a Job.',
    'parameters': PARAMETERS}}


def score_calls(calls, expected):
    if type(calls) is not list or len(calls) != 1:
        return False
    if type(calls[0]) is not dict or type(calls[0].get('function')) is not dict:
        return False
    function = calls[0]['function']
    arguments = function.get('arguments')
    return (function.get('name') == 'propose_lcluc_plan'
            and Draft202012Validator(PARAMETERS).is_valid(arguments)
            and arguments == dict(province=expected[0], start_year=expected[1], end_year=expected[2]))


def run(models):
    tags, _ = request_json(OLLAMA, '/api/tags')
    installed = {item['name']: item for item in tags['models']}
    result = {'recorded_at': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
              'scope': 'NATIVE_PLANNING_TOOL_PROPOSAL_NOT_APPROVED_API_EXECUTION',
              'actual_api': '/v1/agents/lcluc-agent/jobs', 'api_called': False,
              'job_input_refs_available': False, 'execution_authorized': False,
              'tool': TOOL, 'models': [], 'tool_executions': 0, 'model_installations': 0}
    for model in models:
        rows = []
        if model not in installed:
            result['models'].append({'model': model, 'status': 'NOT_INSTALLED', 'cases': []})
            continue
        for case in CASES[:2]:
            try:
                response, seconds = request_json(OLLAMA, '/api/chat', {
                    'model': model, 'stream': False, 'think': False, 'keep_alive': '2m',
                    'options': {'temperature': 0, 'seed': 42, 'num_ctx': 4096, 'num_predict': 128},
                    'tools': [TOOL], 'messages': [
                        {'role': 'system', 'content': 'Use the offered planning tool for a land-cover change request. '
                         'Use English province names. It only proposes a BLOCKED plan because no approved model, '
                         'independent labels or pinned input refs are available. Do not claim API execution.'},
                        {'role': 'user', 'content': case['question']}]})
                message = response.get('message', {})
                calls = message.get('tool_calls')
                rows.append({'case': case['id'], 'seconds': seconds, 'returned_model': response.get('model'),
                             'content': message.get('content'), 'tool_calls': calls,
                             'correct_planning_call': score_calls(calls, case['expected']),
                             'done_reason': response.get('done_reason'), 'tool_executed': False})
            except (HTTPError, URLError, OSError, ValueError, TimeoutError) as error:
                rows.append({'case': case['id'], 'error_type': type(error).__name__,
                             'http_status': getattr(error, 'code', None)})
            print(model, case['id'], rows[-1].get('correct_planning_call', rows[-1].get('error_type')), flush=True)
        result['models'].append({'model': model, 'digest': installed[model]['digest'], 'cases': rows})
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-local', action='store_true')
    parser.add_argument('--model', action='append', default=[])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not args.run_local or args.output.exists():
        parser.error('Explicit --run-local and a new output path are required')
    output = run(args.model)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(output, ensure_ascii=False, indent=2))
