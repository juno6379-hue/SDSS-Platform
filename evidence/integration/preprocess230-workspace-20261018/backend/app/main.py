"""실제 수집·학습 어댑터와 연결하는 로컬 실증 서버."""
import importlib
import importlib.util
import hashlib
import json
import os
import secrets
from threading import RLock
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from fastapi import Body, Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse, Response, JSONResponse

from .lifecycle import deploy, transition
from .gmais_api import create_router
from .dataset_lineage_api import create_dataset_lineage_router
from .job_lineage_api import create_job_lineage_router
from .workflow_lineage_api import create_workflow_lineage_router
from .readiness_source_identity_api import create_readiness_source_identity_router
from .candidate_qa_comparison_api import create_candidate_qa_comparison_router
from .job_execution_binding_capture_api import create_job_execution_binding_capture_router
from .stored_current_binding_preflight_api import create_stored_current_binding_preflight_router
from .workflow_node_input_handoff_api import create_workflow_node_input_handoff_router
from .workflow_job_request_handoff_api import create_workflow_job_request_handoff_router
from .workflow_job_model_record_handoff_api import create_workflow_job_model_record_handoff_router
from .lcluc_workflow_api import create_lcluc_workflow_router
from .annual_diagnostics_api import create_annual_diagnostics_router
from .model_error_analysis_api import create_model_error_analysis_router
from .store import Store, now

ROOT = Path(os.getenv('GEOAI_DATA_ROOT', str(Path(__file__).resolve().parents[2] / 'data')))
store = Store(ROOT, recover_jobs=True)
pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='geoai')
registry_lock = RLock()


def authorized(request: Request, authorization: str | None = Header(default=None)):
    # liveness/readiness는 GMAIS 제안 OpenAPI와 같이 인증 없이 확인할 수 있다.
    if request.url.path in {'/healthz', '/readyz'}:
        return
    token = os.getenv('GEOAI_API_TOKEN')
    if token and not secrets.compare_digest((authorization or '').encode('utf-8'), f'Bearer {token}'.encode('utf-8')):
        raise HTTPException(401, '인증 토큰이 필요합니다.')


app = FastAPI(title='Indonesia GeoAI LCLUC', version='0.1.0', dependencies=[Depends(authorized)])
app.add_middleware(CORSMiddleware, allow_origins=os.getenv('GEOAI_CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(','), allow_methods=['GET', 'POST'], allow_headers=['Authorization', 'Content-Type', 'Idempotency-Key'])


def record(kind, identifier):
    try:
        return store.get(kind, identifier)
    except KeyError:
        raise HTTPException(404, '항목이 없습니다.')


def call(module, function, payload, with_root=True):
    try:
        fn = getattr(importlib.import_module(module), function)
        return fn(payload, store.root) if with_root else fn(payload)
    except (ValueError, TypeError, KeyError) as exc:
        raise HTTPException(422, str(exc)) from exc
    except (RuntimeError, OSError, ImportError) as exc:
        raise HTTPException(503, str(exc)) from exc


def public_input(value):
    """실행 근거는 남기되 서명 URL과 비밀 필드는 이력에서 제거한다."""
    if isinstance(value, dict):
        return {k: public_input(v) for k, v in value.items() if not any(part in k.lower() for part in ('token', 'password', 'secret', 'authorization', 'api_key'))}
    if isinstance(value, list):
        return [public_input(item) for item in value]
    if isinstance(value, str) and value.startswith(('https://', 'http://')):
        parsed = urlsplit(value)
        return urlunsplit((parsed.scheme, parsed.hostname or '', parsed.path, '', ''))
    return value


def verified_checkpoint(model):
    path = (store.root / str(model.get('checkpoint_path', ''))).resolve()
    if not path.is_relative_to(store.root) or not path.is_file():
        raise ValueError('체크포인트 파일을 확인할 수 없습니다.')
    expected = model.get('checkpoint_sha256')
    if not expected:
        raise ValueError('체크포인트 해시가 등록되지 않았습니다. 학습 결과를 검증하여 다시 등록하십시오.')
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    if not secrets.compare_digest(digest.hexdigest(), expected):
        raise ValueError('체크포인트 내용이 등록된 모델 해시와 다릅니다.')
    return path


def verified_evaluation(model):
    """독립평가가 현재 등록된 가중치에 대한 것인지 승인 직전에 확인한다."""
    evaluation = model.get('evaluation') or {}
    if (not model.get('independent_evaluation') or evaluation.get('reference_kind') != 'expert_independent'
            or not model.get('checkpoint_sha256') or evaluation.get('checkpoint_sha256') != model.get('checkpoint_sha256')):
        raise ValueError('현재 체크포인트 해시에 연결된 독립 참조평가가 필요합니다.')
    verified_checkpoint(model)


def submit(module, function, payload, kind=None, model_to_evaluate=None, runtime_model_id=None):
    if sum(j['status'] in ('queued', 'running') for j in store.list('jobs')) >= 20:
        raise HTTPException(429, '대기 작업이 20개입니다. 완료 후 다시 요청하십시오.')
    job = store.put('jobs', {'id': uuid.uuid4().hex, 'operation': function, 'status': 'queued', 'input': public_input(payload), 'evaluation_model_id': model_to_evaluate, 'result': None, 'error': None})

    def execute():
        current = dict(job, status='running', started_at=now())
        store.put('jobs', current)
        try:
            if model_to_evaluate:
                with registry_lock:
                    candidate = store.get('models', model_to_evaluate)
                    if candidate['status'] != 'Draft' or candidate.get('checkpoint_sha256') != payload.get('expected_checkpoint_sha256'):
                        raise HTTPException(409, '대기 중 독립 평가 대상 모델의 상태 또는 해시가 바뀌었습니다.')
                    verified_checkpoint(candidate)
            if runtime_model_id:
                with registry_lock:
                    active = store.get('models', runtime_model_id)
                    if active['status'] != 'Deployed' or active.get('checkpoint_path') != payload.get('checkpoint_path'):
                        raise HTTPException(409, '대기 중 모델 배포 상태가 바뀌었습니다. 배포 모델을 다시 선택하십시오.')
                    verified_checkpoint(active)
            result = call(module, function, payload)
            result = dict(result, execution={'job_id': job['id'], 'operation': function, 'inputs': public_input(payload), 'started_at': current['started_at'], 'completed_at': now()})
            if kind:
                # 학습결과는 검토 전 Draft이며 API 입력만으로 독립평가 증거를 만들 수 없다.
                if kind == 'models':
                    result = dict(result, status='Draft', independent_evaluation=False, checkpoint_path=result.get('checkpoint_path', result.get('checkpoint')), training_history=result.get('history', []), history=[])
                result = store.put(kind, result)
            if model_to_evaluate:
                with registry_lock:
                    model = store.get('models', model_to_evaluate)
                    if (model['status'] != 'Draft' or model.get('checkpoint_path') != payload.get('checkpoint_path')
                            or model.get('checkpoint_sha256') != payload.get('expected_checkpoint_sha256')):
                        raise HTTPException(409, '평가 도중 모델 상태/체크포인트가 변경되어 근거를 반영하지 않았습니다.')
                    verified_checkpoint(model)
                    if result.get('reference_kind') != 'expert_independent':
                        raise HTTPException(409, '독립 참조평가 결과가 아니므로 승인 근거에 반영하지 않았습니다.')
                    result = dict(result, checkpoint_sha256=model['checkpoint_sha256'])
                    model.update(independent_evaluation=True, evaluation=result)
                    store.put('models', model)
            current.update(status='succeeded', result=result)
        except Exception as exc:
            current.update(status='failed', error=str(exc.detail) if isinstance(exc, HTTPException) else str(exc))
        current['finished_at'] = now()
        store.put('jobs', current)

    pool.submit(execute)
    return job


@app.get('/api/health')
def health():
    return {'status': 'ok', 'mode': 'local-development', 'storage': 'sqlite', 'dependencies': {name: bool(importlib.util.find_spec(name)) for name in ['torch', 'rasterio', 'pyproj', 'ee', 'mlflow']}, 'authentication': 'token' if os.getenv('GEOAI_API_TOKEN') else 'localhost-only; configure GEOAI_API_TOKEN for shared access'}


@app.get('/api/dashboard')
def dashboard():
    return {'datasets': len(store.list('datasets')), 'models': len(store.list('models')), 'jobs': len(store.list('jobs')), 'analyses': len(store.list('analyses')), 'recent_jobs': store.list('jobs')[:10], 'limitations': ['실데이터 독립평가 전 운영 승인 불가', 'PostGIS·MLflow·RDTR·드리프트는 후속 통합 대상']}


@app.get('/api/datasets')
def datasets():
    return store.list('datasets')


@app.get('/api/data/collection-status')
def data_collection_status():
    from .collection_status import collection_status
    from .collection_budget_status import collection_budget_status
    config_path=getattr(app.state,'collection_source_profile_path',None)
    result = collection_status(store.root,source_profile_config_path=config_path)
    if isinstance(result.get('collection_targets'), dict):
        result['collection_targets']['budget_status'] = collection_budget_status(store.root,source_profile_config_path=config_path)
        budget=result['collection_targets']['budget_status']
        current=(result.get('training_readiness') or {}).get('current_manifest_sha256')
        if budget.get('available') and current and budget.get('source_manifest_sha256')!=current:
            result['collection_targets']['available']=False
            result['collection_targets']['budget_status']={'available':False,'status':'UNCONFIRMED'}
    return result


@app.get('/api/data/collection-budget-status')
def data_collection_budget_status():
    from .collection_budget_status import collection_budget_status
    return JSONResponse(collection_budget_status(store.root,source_profile_config_path=getattr(app.state,'collection_source_profile_path',None)), headers={'Cache-Control': 'no-store'})


@app.get('/api/data/landcover-series')
def landcover_series():
    from .landcover_tiles import series_index
    return series_index(store.root, store.list('analyses'), refresh=True)[0]


@app.get('/api/data/landcover-layers/{layer_id}/tiles/{z}/{x}/{y}.png')
def landcover_tile(layer_id: str, z: int, x: int, y: int):
    from .landcover_tiles import tile
    try:
        return Response(tile(store.root, layer_id, z, x, y, store.list('analyses')), media_type='image/png',
                        headers={'Cache-Control':'private, max-age=30'})
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    except (ValueError, OSError) as exc:
        raise HTTPException(422, str(exc)) from exc


@app.get('/api/models')
def models():
    return store.list('models')


@app.get('/api/models/{identifier}/registration-provenance')
def model_registration_provenance(identifier: str):
    try:
        from .model_registration_provenance import inspect_model_registration_provenance
        return inspect_model_registration_provenance(record('models', identifier))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(503, '등록 선언 관측을 완료할 수 없습니다.') from exc


@app.get('/api/models/{identifier}/readiness')
def model_readiness(identifier: str):
    model = record('models', identifier)
    blockers = []
    matched = False
    try:
        verified_checkpoint(model)
        matched = True
    except ValueError as exc:
        blockers.append(str(exc))
    evaluated = False
    try:
        verified_evaluation(model)
        evaluated = True
    except ValueError as exc:
        blockers.append(str(exc))
    pending = evaluation_pending(identifier)
    if pending:
        blockers.append('독립 평가 작업이 진행 중입니다.')
    allowed = []
    if not pending:
        if evaluated and model['status'] == 'Draft':
            allowed.append('Validated')
        if evaluated and model['status'] == 'Validated':
            allowed.append('Approved')
        if model['status'] == 'Validated':
            allowed.append('Draft')
        if model['status'] in ('Approved', 'Deployed'):
            allowed.append('Retired')
    return {'model_id': identifier, 'status': model['status'],
        'evaluation_kind': (model.get('evaluation') or {}).get('reference_kind', 'unverified'),
        'independent_evaluation': bool(model.get('independent_evaluation')),
        'checkpoint_integrity': {'matched': matched, 'expected_sha256': model.get('checkpoint_sha256')},
        'allowed_transitions': allowed, 'can_deploy': evaluated and not pending and model['status'] == 'Approved',
        'blockers': list(dict.fromkeys(blockers)), 'evaluation_pending': pending}


@app.post('/api/models/register-experiment', status_code=201)
def register_completed_experiment(payload: dict = Body(...)):
    from .experiment_registry import register_experiment
    try:
        with registry_lock:
            if 'model_version' in payload:
                return register_experiment(store, payload.get('report_path'), model_version=payload['model_version'])
            return register_experiment(store, payload.get('report_path'))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        raise HTTPException(422, str(exc)) from exc


@app.get('/api/jobs')
def jobs():
    return store.list('jobs')


@app.get('/api/jobs/{identifier}')
def get_job(identifier: str):
    return record('jobs', identifier)


@app.get('/api/analyses')
def analyses():
    return store.list('analyses')


@app.get('/api/tools')
def tools():
    return [{'id': name, 'implemented': name == 'lcluc', 'status': 'baseline-development' if name == 'lcluc' else 'interface-only', 'input_schema': {'aoi': 'bbox', 'period': ['start_date', 'end_date'], 'dataset_id': 'string'}, 'output_schema': {'artifacts': 'list', 'quality': 'object', 'provenance': 'object'}} for name in ['climate-downscaling', 'lcluc', 'net-carbon-footprint', 'biodiversity', 'sea-level-subsidence', 'flood-drought']]


@app.post('/api/data/search')
def search(payload: dict = Body(...)):
    return call('app.data.service', 'search_stac', payload, False)


@app.post('/api/data/download', status_code=202)
def download(payload: dict = Body(...)):
    return submit('app.data.service', 'download_asset', payload, 'datasets')


@app.post('/api/data/register')
def register(payload: dict = Body(...)):
    return store.put('datasets', call('app.data.service', 'register_local', payload))


@app.post('/api/data/worldcover/plan')
def worldcover(payload: dict = Body(...)):
    return call('app.data.service', 'worldcover_plan', payload, False)


@app.post('/api/data/dynamic-world/export')
def dynamic_world(payload: dict = Body(...)):
    return call('app.data.service', 'dynamic_world_export', payload, False)


@app.post('/api/datasets/prepare', status_code=202)
def prepare(payload: dict = Body(...)):
    return submit('app.ml.service', 'prepare_dataset', payload, 'datasets')


@app.post('/api/training', status_code=202)
def training(payload: dict = Body(...)):
    return submit('app.ml.service', 'train_model', payload, 'models')


@app.post('/api/inference', status_code=202)
def inference(payload: dict = Body(...)):
    # 운영 추론은 배포 레지스트리의 경로만 사용한다. 실험 추론은 직접 ML 모듈로 실행한다.
    model = record('models', str(payload.get('model_id', '')))
    if model['status'] != 'Deployed':
        raise HTTPException(409, '배포된 모델이 필요합니다. 실험은 로컬 ML 모듈을 사용하십시오.')
    return submit('app.ml.service', 'infer_raster', dict(payload, checkpoint_path=model['checkpoint_path']), 'analyses', runtime_model_id=model['id'])


@app.post('/api/change', status_code=202)
def change(payload: dict = Body(...)):
    return submit('app.ml.service', 'analyze_change', payload, 'analyses')


@app.post('/api/timeseries', status_code=202)
def timeseries(payload: dict = Body(...)):
    model = record('models', str(payload.get('model_id', '')))
    if model['status'] != 'Deployed':
        raise HTTPException(409, '연차별 운영 분석에는 배포된 모델이 필요합니다.')
    return submit('app.ml.service', 'analyze_timeseries', dict(payload, checkpoint_path=model['checkpoint_path']), 'analyses', runtime_model_id=model['id'])


@app.post('/api/models/{identifier}/transition')
def model_transition(identifier: str, payload: dict = Body(...)):
    try:
        with registry_lock:
            if evaluation_pending(identifier):
                raise HTTPException(409, '독립 평가 작업이 끝난 뒤 검토 상태를 변경하십시오.')
            model = record('models', identifier)
            if payload.get('status') in ('Validated', 'Approved'):
                verified_evaluation(model)
            return store.put('models', transition(model, payload.get('status'), payload.get('reason', '')))
    except ValueError as exc:
        raise HTTPException(409, str(exc))


@app.post('/api/models/{identifier}/evaluate', status_code=202)
def model_evaluate(identifier: str, payload: dict = Body(...)):
    with registry_lock:
        model = record('models', identifier)
        if model['status'] != 'Draft' or evaluation_pending(identifier):
            raise HTTPException(409, 'Draft 모델에서 한 번에 한 평가만 진행할 수 있습니다.')
        try:
            verified_checkpoint(model)
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
        return submit('app.ml.service', 'evaluate_model', dict(payload, checkpoint_path=model['checkpoint_path'],
                      expected_checkpoint_sha256=model['checkpoint_sha256']), model_to_evaluate=identifier)


def evaluation_pending(identifier):
    return any(j.get('evaluation_model_id') == identifier and j['status'] in ('queued', 'running') for j in store.list('jobs'))


@app.post('/api/models/{identifier}/deploy')
def model_deploy(identifier: str):
    try:
        with registry_lock:
            model = deploy(record('models', identifier))
            verified_evaluation(model)
            # 단일 운영 모델 포인터를 전환하되 이전 버전 및 배포 이력을 보존한다.
            previous = [m for m in store.list('models') if m['status'] == 'Deployed']
            for item in previous:
                history = [*item.get('history', []), {'status': 'Approved', 'at': now(), 'reason': f"운영 버전을 {identifier}로 전환"}]
                store.put('models', dict(item, status='Approved', history=history))
            return store.put('models', model)
    except ValueError as exc:
        raise HTTPException(409, str(exc))


@app.post('/api/query')
def query(payload: dict = Body(...)):
    question = str(payload.get('question', '')).strip()
    if not question or len(question) > 2000:
        raise HTTPException(422, '질문은 1~2000자로 입력하십시오.')
    # 자연어를 코드나 SQL로 실행하지 않고 승인된 읽기 패턴에만 연결한다.
    if '모델' in question and ('정확도' in question or '버전' in question):
        return {'mode': 'predefined-pattern', 'answer': '등록된 모델의 실제 기록입니다. 독립평가 여부를 함께 확인하십시오.', 'evidence': store.list('models')}
    if any(word in question for word in ['변화', '산림', '농경지', '도시', '면적']):
        if not payload.get('analysis_id'):
            return {'mode': 'predefined-pattern', 'answer': '먼저 변화분석을 실행한 뒤 analysis_id를 지정하십시오.', 'evidence': []}
        result = record('analyses', payload['analysis_id'])
        return {'mode': 'predefined-pattern', 'answer': '선택한 분석의 기록된 결과입니다. 질문의 기간·분류체계가 결과와 일치하는지 확인하십시오.', 'evidence': [result]}
    return {'mode': 'predefined-pattern', 'answer': '지원 질의: 모델 정확도/버전, 완료된 변화분석의 면적·통계 조회. 새 분석은 Toolbox에서 실행하십시오.', 'evidence': []}


@app.get('/api/analyses/{identifier}/report', response_class=PlainTextResponse)
def report(identifier: str):
    analysis = record('analyses', identifier)
    return PlainTextResponse('# LCLUC 분석 기록\n\n정책 검토 지원자료입니다. 데이터 품질 및 독립평가 범위를 확인하십시오.\n\n```json\n' + json.dumps(analysis, ensure_ascii=False, indent=2) + '\n```\n', headers={'Content-Disposition': f'attachment; filename="analysis-{identifier}.md"'})


@app.get('/api/analyses/{identifier}/map-data')
def analysis_map_data(identifier: str):
    from .map_data import map_data
    try:
        return map_data(record('analyses', identifier), store.root)
    except (ValueError, OSError) as exc:
        raise HTTPException(422, str(exc)) from exc


@app.get('/api/artifacts/{relative_path:path}')
def artifact(relative_path: str):
    target = (store.root / relative_path).resolve()
    if not target.is_relative_to(store.root) or target.suffix.lower() not in {'.tif', '.tiff', '.csv', '.geojson', '.json', '.md'} or not target.is_file() or target.name == 'catalog.sqlite3':
        raise HTTPException(404, '공개 가능한 산출물이 없습니다.')
    return FileResponse(target, filename=target.name)


# GMAIS v0.2 내부 검토 계약 Adapter. 제안 규격의 공식 승인 또는 LCLUC 검증을 뜻하지 않는다.
app.include_router(create_router(lambda: store))
app.include_router(create_dataset_lineage_router(lambda: store))
app.include_router(create_job_lineage_router(lambda: store))
app.include_router(create_workflow_lineage_router(lambda: store))
app.include_router(create_readiness_source_identity_router(lambda: store))
app.include_router(create_candidate_qa_comparison_router(lambda: store))
app.include_router(create_job_execution_binding_capture_router(lambda: store))
app.include_router(create_stored_current_binding_preflight_router(lambda: store))
app.include_router(create_workflow_node_input_handoff_router())
app.include_router(create_workflow_job_request_handoff_router())
app.include_router(create_workflow_job_model_record_handoff_router())
app.include_router(create_lcluc_workflow_router(lambda: store))
app.include_router(create_annual_diagnostics_router(lambda: store))
app.include_router(create_model_error_analysis_router(lambda: store))
