"""API용 동기 서비스. 무거운 실행은 호출측 작업 큐에서 처리한다."""
import csv
import json
import random
import threading
import time
import os
from functools import wraps
from pathlib import Path
import numpy as np
from .dataset import prepare, file_digest
from .raster import IGNORE, CLASS_NAMES, assert_aligned, pixel_areas, read, safe_path, write_classes
from .normalization import apply_normalization


_model_lock = threading.RLock()


def _serialized(function):
    """스레드 작업 큐에서 PyTorch 전역 seed 설정의 동시 변경을 방지한다."""
    @wraps(function)
    def wrapped(*args, **kwargs):
        with _model_lock:
            return function(*args, **kwargs)
    return wrapped


def prepare_dataset(payload: dict, data_root: Path) -> dict:
    return prepare(payload, Path(data_root).resolve())


def runtime_status():
    try:
        import torch
        return {'torch_available':True,'torch_version':torch.__version__,'cuda_available':torch.cuda.is_available(), 'device':'cuda' if torch.cuda.is_available() else 'cpu'}
    except ImportError:
        return {'torch_available':False,'cuda_available':False,'device':None,'reason':'선택 의존성 torch 설치가 필요합니다.'}


def metrics(confusion):
    matrix = confusion.astype('float64')
    diagonal = np.diag(matrix)
    def divide(a,b):
        return np.divide(a,b,out=np.zeros_like(a),where=b>0)
    precision, recall = divide(diagonal,matrix.sum(0)), divide(diagonal,matrix.sum(1))
    union = matrix.sum(0)+matrix.sum(1)-diagonal
    iou = divide(diagonal,union)
    return {'confusion_matrix':confusion.tolist(), 'overall_accuracy':float(diagonal.sum()/matrix.sum()) if matrix.sum() else None,
            'precision':precision.tolist(),'recall':recall.tolist(),'f1':divide(2*precision*recall,precision+recall).tolist(),
            'class_support':matrix.sum(1).astype('int64').tolist(),'predicted_class_counts':matrix.sum(0).astype('int64').tolist(),
            'predicted_class_ratio':(matrix.sum(0)/matrix.sum()).tolist() if matrix.sum() else [None]*len(matrix),
            'recall_evaluable':(matrix.sum(1)>0).tolist(),
            'class_iou':[float(v) if u else None for v,u in zip(iou,union)], 'mean_iou':float(iou[union>0].mean()) if np.any(union>0) else None}


@_serialized
def train_model(payload: dict, data_root: Path) -> dict:
    root = Path(data_root).resolve()
    manifest_path = safe_path(root,payload['dataset_path'])
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if not manifest.get('synthetic',False):
        from .readiness import validate_prepared_training, train_only_weights
        counts=validate_prepared_training(manifest,manifest_path,root)
        mode=manifest['readiness_contract']['policy']['class_weighting']
        if mode not in ('none','inverse_sqrt_train'):
            raise ValueError('실험 class_weighting은 none 또는 inverse_sqrt_train입니다.')
        derived=train_only_weights(counts['train']) if mode=='inverse_sqrt_train' else None
        if payload.get('class_weights') is not None and (derived is None or not np.allclose(payload['class_weights'],derived)):
            raise ValueError('정식 실험의 class weights는 학습 분할에서만 계산해야 합니다.')
        payload=dict(payload,class_weights=derived)
    # 존재하지 않는 입력은 무거운 torch 초기화 전에 즉시 실패시킨다.
    import torch
    from .network import TinyUNet
    seed = int(payload.get('seed',42))
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    torch.set_num_threads(max(1,min(8,int(payload.get('cpu_threads',2)))))
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True)
    device = payload.get('device','cuda' if torch.cuda.is_available() else 'cpu')
    if device not in ('cpu','cuda') or device == 'cuda' and not torch.cuda.is_available():
        raise ValueError('요청 장치를 사용할 수 없습니다.')
    if payload.get('architecture','tiny_unet') != 'tiny_unet':
        raise ValueError('현재 구현된 모델은 tiny_unet입니다. U-Net++는 미구현입니다.')
    epochs = int(payload.get('epochs',5)); batch_size = int(payload.get('batch_size',2))
    if not 1 <= epochs <= (1000 if manifest.get('synthetic',False) else 20) or not 1 <= batch_size <= 64:
        raise ValueError('실자료 epochs는 1~20(합성 시험은 1~1000), batch_size는 1~64 범위를 사용하세요.')
    model_id = payload.get('model_id','baseline')
    destination = safe_path(root,f'models/{model_id}')
    resume=bool(payload.get('resume',False))
    if destination.exists() and not resume:
        raise ValueError('기존 모델을 덮어쓸 수 없습니다. 새 model_id를 사용하세요.')
    if resume and not (destination/'last.pt').is_file():
        raise ValueError('재개할 last.pt가 없습니다.')
    if resume and (destination/'report.json').exists() and json.loads((destination/'report.json').read_text(encoding='utf-8')).get('training_state')=='completed':
        raise ValueError('완료된 실험은 재학습/재평가 재개로 덮어쓰지 않습니다.')
    destination.mkdir(parents=True,exist_ok=True)
    splits = {}
    for split in ('train','val','test'):
        splits[split] = [p for p in manifest['patches'] if p['split']==split]
        if not splits[split]:
            raise ValueError('세 분할 모두 유효 패치가 필요합니다.')
    group_sets = [{p['group'] for p in splits[s]} for s in ('train','val','test')]
    if any(group_sets[i] & group_sets[j] for i in range(3) for j in range(i)):
        raise ValueError('동일 지역이 여러 분할에 포함된 데이터 누출이 발견되었습니다.')
    model = TinyUNet(len(manifest['bands'])).to(device)
    optimizer_name = payload.get('optimizer','adam')
    if optimizer_name not in ('adam','sgd'):
        raise ValueError('optimizer는 adam 또는 sgd입니다.')
    optimizer = (torch.optim.Adam if optimizer_name=='adam' else torch.optim.SGD)(model.parameters(),lr=float(payload.get('lr',.001)))
    weight = payload.get('class_weights')
    if weight is not None and (len(weight)!=9 or min(weight)<0 or sum(weight)<=0):
        raise ValueError('class_weights는 음수가 아닌 9개 값이며 합이 양수여야 합니다.')
    if payload.get('loss','cross_entropy') != 'cross_entropy':
        raise ValueError('현재 loss는 cross_entropy만 지원합니다.')
    criterion = torch.nn.CrossEntropyLoss(ignore_index=IGNORE,weight=torch.tensor(weight,dtype=torch.float32,device=device) if weight else None)
    inactive_classes=[i for i,name in enumerate(manifest.get('class_names',CLASS_NAMES)) if name.startswith('unused_')]
    def active_logits(logits):
        if not inactive_classes:
            return logits
        mask=torch.zeros((1,9,1,1),device=logits.device,dtype=torch.bool);mask[:,inactive_classes]=True
        return logits.masked_fill(mask,torch.finfo(logits.dtype).min)
    mixed = bool(payload.get('mixed_precision',False))
    if mixed and device!='cuda':
        raise ValueError('mixed_precision은 CUDA 장치에서만 지원합니다.')
    scaler = torch.amp.GradScaler('cuda',enabled=mixed)
    patience=int(payload.get('patience',3));min_delta=float(payload.get('min_delta',0))
    if patience<1 or not np.isfinite(min_delta) or min_delta<0:
        raise ValueError('patience는 1 이상, min_delta는 유한한 0 이상이어야 합니다.')
    # 신규 실험은 실제 적용한 설정을 가중치와 함께 보존한다. 과거 파일은 수정하지 않는다.
    input_signature={'band_indices':list(manifest['bands']),'band_names':manifest.get('band_names'),
                     'scale':manifest['scale'],'offset':manifest['offset'],'normalization_mode':manifest.get('normalization_mode','global'),
                     'patch_size':int(manifest['patch_size']),'channels':len(manifest['bands'])}
    input_signature.update(class_names=manifest.get('class_names',CLASS_NAMES),label_taxonomy_signature=manifest.get('label_taxonomy_signature'))
    training_config={'optimizer':optimizer_name,'lr':float(optimizer.param_groups[0]['lr']),
                     'loss':'cross_entropy','class_weights':criterion.weight.detach().cpu().tolist() if criterion.weight is not None else None,
                     'epochs':epochs,'batch_size':batch_size,'patience':patience,'min_delta':min_delta,
                     'precision':str(torch.get_autocast_dtype(device)).removeprefix('torch.') if mixed else 'float32',
                     'mixed_precision':mixed,'device':device,'seed':seed,'ignore_index':criterion.ignore_index,
                     'class_weight_basis':'training_split_only' if not manifest.get('synthetic',False) else 'explicit_synthetic_test_configuration',
                     'input_signature':input_signature,'configuration_basis':'serialized_actual_applied_values'}
    max_seconds=float(payload.get('max_seconds',1800))
    epochs_per_call=int(payload.get('epochs_per_call',20))
    if not np.isfinite(max_seconds) or max_seconds<=0 or epochs_per_call<1:
        raise ValueError('max_seconds와 epochs_per_call은 양수여야 합니다.')
    # 시간 예산은 배치 경계에서 확인한다. 완료하지 못한 epoch는 last.pt에서 재실행한다.
    started=time.monotonic()
    class BudgetStop(Exception):
        pass
    def run(split, training=False):
        model.train(training)
        items = list(splits[split])
        if training:
            random.shuffle(items)
        losses=[]; confusion=np.zeros((9,9),dtype='int64')
        for start in range(0,len(items),batch_size):
            if time.monotonic()-started>=max_seconds:
                raise BudgetStop()
            arrays=[]
            for item in items[start:start+batch_size]:
                with np.load(safe_path(root,manifest_path.parent/item['path']),allow_pickle=False) as z:
                    arrays.append((z['image'],z['label']))
            xx=torch.tensor(np.stack([a[0] for a in arrays]),device=device)
            yy=torch.tensor(np.stack([a[1] for a in arrays]),device=device,dtype=torch.long)
            with torch.set_grad_enabled(training), torch.autocast(device_type=device,enabled=mixed):
                logits=active_logits(model(xx)); loss=criterion(logits,yy)
            if not torch.isfinite(loss):
                raise ValueError('유한하지 않은 손실: 입력 또는 class_weights를 확인하세요.')
            if training:
                optimizer.zero_grad(); scaler.scale(loss).backward(); scaler.step(optimizer); scaler.update()
            losses.append(float(loss.detach().cpu()))
            prediction=logits.detach().argmax(1).cpu().numpy(); truth=yy.cpu().numpy(); valid=truth!=IGNORE
            confusion += np.bincount((truth[valid]*9+prediction[valid]),minlength=81).reshape(9,9)
        return {'loss':float(np.mean(losses)),**metrics(confusion),'class_names':manifest.get('class_names',CLASS_NAMES),
                'label_taxonomy_signature':manifest.get('label_taxonomy_signature')}
    best=float('inf'); stale=0; history=[]; checkpoint=destination/'best.pt';last=destination/'last.pt'
    def atomic_save(value,path):
        temporary=path.with_suffix('.tmp')
        # Windows에서도 직렬화 스트림을 명시적으로 닫은 뒤 이름을 교체한다.
        with temporary.open('wb') as stream:
            torch.save(value,stream);stream.flush();os.fsync(stream.fileno())
        for attempt in range(3):
            try:
                temporary.replace(path);break
            except PermissionError:
                if attempt==2:
                    raise
                time.sleep(.05)
    def persist_progress():
        numpy_state=np.random.get_state()
        atomic_save({'state_dict':model.state_dict(),'optimizer_state_dict':optimizer.state_dict(),'scaler_state_dict':scaler.state_dict(),
                     'manifest':manifest,'architecture':'tiny_unet','seed':seed,'epoch':len(history),'history':history,
                     'training_config':training_config,'input_signature':input_signature,'best_loss':best,'stale_epochs':stale,
                     'early_stopped':stale>=patience,'python_rng_state':random.getstate(),'torch_rng_state':torch.get_rng_state(),
                     'cuda_rng_state':torch.cuda.get_rng_state_all() if device=='cuda' else [],
                     'numpy_rng_state':{'kind':numpy_state[0],'keys':numpy_state[1].tolist(),'pos':numpy_state[2],'has_gauss':numpy_state[3],'cached_gaussian':numpy_state[4]}},last)
        (destination/'progress.json').write_text(json.dumps({'training_state':'running','completed_epochs':len(history),
            'target_epochs':epochs,'best_validation_loss':best if np.isfinite(best) else None,'resume_path':str(last.relative_to(root))}),encoding='utf-8')
    if resume:
        previous=torch.load(last,map_location=device,weights_only=True)
        if previous['manifest']!=manifest or previous['training_config']!=training_config:
            raise ValueError('재개 시 데이터·분할·입력/학습 설정을 변경할 수 없습니다.')
        model.load_state_dict(previous['state_dict']);optimizer.load_state_dict(previous['optimizer_state_dict']);scaler.load_state_dict(previous['scaler_state_dict'])
        history=previous['history'];best=previous['best_loss'];stale=previous['stale_epochs']
        random.setstate(previous['python_rng_state']);torch.set_rng_state(previous['torch_rng_state'].cpu())
        if device=='cuda':
            torch.cuda.set_rng_state_all(previous['cuda_rng_state'])
        ns=previous['numpy_rng_state'];np.random.set_state((ns['kind'],np.asarray(ns['keys'],dtype='uint32'),ns['pos'],ns['has_gauss'],ns['cached_gaussian']))
    else:
        persist_progress()
    start_epoch=len(history);paused=False;partial_discarded=False
    try:
        for epoch in range(start_epoch,epochs):
            if stale>=patience:
                break
            train=run('train',True); val=run('val')
            history.append({'epoch':epoch+1,'train':train,'val':val})
            if val['loss'] < best-min_delta:
                best=val['loss']; stale=0
                atomic_save({'state_dict':model.state_dict(),'manifest':manifest,'architecture':'tiny_unet','seed':seed,'epoch':epoch+1,
                             'training_config':training_config,'input_signature':input_signature},checkpoint)
            else:
                stale+=1
            persist_progress()
            if len(history)-start_epoch>=epochs_per_call and epoch+1<epochs and stale<patience:
                paused=True;break
        if not paused:
            saved=torch.load(checkpoint,map_location=device,weights_only=True)
            model.load_state_dict(saved['state_dict'])
            test=run('test')
    except BudgetStop:
        paused=True;partial_discarded=len(history)<epochs and stale<patience
    if paused:
        report={'model_id':model_id,'status':'Draft','training_state':'paused','resume_path':str(last.relative_to(root)),
                'architecture':'tiny_unet','device':device,'seed':seed,'synthetic':manifest.get('synthetic',False),
                'class_names':manifest.get('class_names',CLASS_NAMES),'input_signature':input_signature,
                'checkpoint_path':str(checkpoint.relative_to(root)) if checkpoint.exists() else None,
                'training_config':training_config,'history':history,'epochs_executed':len(history),'dataset_version':manifest['version'],
                'test_metrics':None,'weak_label_experiment_output_accepted':False,'scientific_accuracy_validated':False,
                'discarded_incomplete_epoch':partial_discarded,'resume_semantics':'last completed train+validation epoch; incomplete epoch is rerun',
                'elapsed_seconds':time.monotonic()-started}
        (destination/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        (destination/'progress.json').write_text(json.dumps({'training_state':'paused','completed_epochs':len(history),'target_epochs':epochs,'resume_path':str(last.relative_to(root))}),encoding='utf-8')
        return report
    from .readiness import prediction_check
    dominance=manifest.get('readiness_contract',{}).get('policy',{}).get('max_prediction_dominance',.995) if manifest.get('readiness_contract') else .995
    prediction_quality={'val':prediction_check(history[saved['epoch']-1]['val']['confusion_matrix'],dominance),
                        'test':prediction_check(test['confusion_matrix'],dominance)}
    report={'model_id':model_id,'architecture':'tiny_unet','status':'Draft','device':device,'seed':seed,'history':history,
            'training_state':'completed','resume_path':str(last.relative_to(root)),'elapsed_seconds':time.monotonic()-started,
            'training_config':training_config,'input_signature':input_signature,'epochs_executed':len(history),
            'selected_epoch':saved['epoch'],'selected_validation_metrics':history[saved['epoch']-1]['val'],
            'prediction_quality':prediction_quality,'weak_label_experiment_output_accepted':all(value['passed'] for value in prediction_quality.values()),
            'test_metrics':test,'dataset_version':manifest['version'],'synthetic':manifest.get('synthetic',False),
            'reference_kind':manifest.get('reference_kind','unverified_or_pseudo_label'),
            'class_names':manifest.get('class_names',CLASS_NAMES),'label_taxonomy_signature':manifest.get('label_taxonomy_signature'),
            'accuracy_claim':'기능시험/의사라벨 일치도. 독립 참조자료 검증 없이는 최종 정확도가 아닙니다.',
            'checkpoint_path':str(checkpoint.relative_to(root)),'checkpoint_sha256':file_digest(checkpoint)}
    (destination/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    (destination/'progress.json').write_text(json.dumps({'training_state':'completed','completed_epochs':len(history),'selected_epoch':saved['epoch'],'target_epochs':epochs}),encoding='utf-8')
    return report


@_serialized
def infer_raster(payload: dict, data_root: Path) -> dict:
    import torch
    from .network import TinyUNet
    root=Path(data_root).resolve()
    checkpoint=torch.load(safe_path(root,payload['checkpoint_path']),map_location='cpu',weights_only=True)
    manifest=checkpoint['manifest']; image,valid,profile=read(safe_path(root,payload['image_path']))
    bands=np.asarray(manifest['bands'])-1
    if max(bands)>=image.shape[0]:
        raise ValueError('추론 영상 밴드가 모델 입력보다 적습니다.')
    normalization=payload.get('normalization')
    if manifest.get('normalization_mode')=='per_scene_product_metadata' and not normalization:
        raise ValueError('제품별 정규화 모델에는 추론 영상의 검증된 normalization 설정이 필요합니다.')
    normalization=normalization or {'scale':manifest['scale'],'offset':manifest['offset']}
    normalization_provenance={}
    if manifest.get('normalization_mode')=='per_scene_product_metadata' and not manifest.get('synthetic'):
        from .normalization import verify_inference_normalization
        normalization_provenance=verify_inference_normalization(normalization,payload.get('source_scene'),safe_path(root,payload['image_path']),manifest['band_names'],root)
    image=apply_normalization(image[bands],normalization['scale'],normalization['offset'])
    valid &= np.isfinite(image).all(0); image[:,~valid]=0
    if payload.get('quality_mask_path'):
        quality,quality_valid,quality_profile=read(safe_path(root,payload['quality_mask_path']))
        assert_aligned(profile,quality_profile)
        valid &= quality_valid & (quality[0]>0)
        image[:,~valid]=0
    model=TinyUNet(len(bands)); model.load_state_dict(checkpoint['state_dict']); model.eval()
    inactive_classes=[i for i,name in enumerate(manifest.get('class_names',CLASS_NAMES)) if name.startswith('unused_')]
    size=manifest['patch_size']; result=np.full(valid.shape,IGNORE,dtype='uint8')
    with torch.inference_mode():
        for y in range(0,image.shape[1],size):
            for x in range(0,image.shape[2],size):
                h,w=min(size,image.shape[1]-y),min(size,image.shape[2]-x)
                patch=np.zeros((1,len(bands),size,size),dtype='float32'); patch[0,:,:h,:w]=image[:,y:y+h,x:x+w]
                logits=model(torch.from_numpy(patch))
                if inactive_classes:
                    logits[:,inactive_classes]=torch.finfo(logits.dtype).min
                result[y:y+h,x:x+w]=logits.argmax(1)[0,:h,:w].numpy()
    result[~valid]=IGNORE
    output=safe_path(root,f"results/{payload.get('output_id','inference')}/classification.tif")
    if output.exists():
        raise ValueError('결과가 이미 존재합니다. 새 output_id를 사용하세요.')
    write_classes(output,result,profile)
    return {'classification_path':str(output.relative_to(root)),'valid_pixels':int(valid.sum()),'checkpoint_path':payload['checkpoint_path'],'class_names':manifest.get('class_names',CLASS_NAMES),
            'label_taxonomy_signature':manifest.get('label_taxonomy_signature'),'normalization_provenance':normalization_provenance,
            'quality_mask_path':payload.get('quality_mask_path'),'quality_mask_basis':payload.get('quality_mask_basis','caller_supplied_binary_mask') if payload.get('quality_mask_path') else 'input_nodata_only'}


def analyze_change(payload: dict, data_root: Path) -> dict:
    root=Path(data_root).resolve()
    feature_limit = int(payload.get('max_features', 5000))
    if not 1 <= feature_limit <= 5000:
        raise ValueError('max_features는 1~5000이어야 합니다.')
    a,av,ap=read(safe_path(root,payload['t1_path'])); b,bv,bp=read(safe_path(root,payload['t2_path']))
    assert_aligned(ap,bp)
    classes=int(payload.get('num_classes',9))
    if not 2<=classes<=255:
        raise ValueError('num_classes는 2~255 범위여야 합니다.')
    a,b=a[0],b[0]
    valid=av & bv & np.isfinite(a) & np.isfinite(b) & (a>=0) & (a<classes) & (b>=0) & (b<classes) & (a==np.floor(a)) & (b==np.floor(b))
    area,method=pixel_areas(ap)
    code=a[valid].astype('int64')*classes+b[valid].astype('int64')
    pixels=np.bincount(code,minlength=classes**2).reshape(classes,classes)
    matrix=np.bincount(code,weights=area[valid],minlength=classes**2).reshape(classes,classes)
    output=safe_path(root,f"results/{payload.get('output_id','change')}")
    if output.exists():
        raise ValueError('결과가 이미 존재합니다. 새 output_id를 사용하세요.')
    output.mkdir(parents=True)
    transitions=np.full(a.shape,65535,dtype='uint16'); transitions[valid]=code
    write_classes(output/'transitions.tif',transitions,ap,nodata=65535,dtype='uint16')
    from rasterio.features import shapes
    from rasterio.warp import transform_geom
    features = []; truncated = False
    # 지도용 벡터는 크기를 제한한다. 전체 면적은 아래의 원본 래스터 행렬만 사용한다.
    for geometry, value in shapes(transitions, mask=valid & (a != b), transform=ap['transform']):
        if len(features) >= feature_limit:
            truncated = True
            break
        transition_code = int(value)
        features.append({'type':'Feature','geometry':transform_geom(ap['crs'],'EPSG:4326',geometry),
                         'properties':{'from_class':transition_code//classes,'to_class':transition_code%classes,
                                       'transition_code':transition_code,'quality':'comparison_of_classifications; unverified_change'}})
    collection = {'type':'FeatureCollection','features':features}
    encoded = json.dumps(collection, ensure_ascii=False)
    (output/'changes.geojson').write_text(encoded, encoding='utf-8')
    with (output/'transitions.csv').open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.writer(stream); writer.writerow(['from_class','to_class','pixels','area_m2'])
        for i,j in np.ndindex(matrix.shape):
            writer.writerow([i,j,int(pixels[i,j]),float(matrix[i,j])])
    total=float(matrix.sum()); changed=float(total-np.trace(matrix))
    report={'transition_pixels':pixels.tolist(),'transition_area_m2':matrix.tolist(),'valid_pixels':int(valid.sum()),'excluded_pixels':int(valid.size-valid.sum()),
            'class_names':payload.get('class_names',CLASS_NAMES if classes==9 else [str(i) for i in range(classes)]),
            'total_area_m2':total,'changed_area_m2':changed,'change_rate':changed/total if total else None,'area_method':method,
            'class_net_area_m2':(matrix.sum(0)-matrix.sum(1)).tolist(),
            'warning':'계절·센서·구름 잔존 및 두 분류지도의 오차가 가짜 변화로 나타날 수 있습니다. 투영면적은 CRS 왜곡의 영향을 받습니다.',
            'geojson_path':str((output/'changes.geojson').relative_to(root)),
            'geometry':collection if len(encoded.encode('utf-8')) <= 1048576 else None,
            'vector_feature_count':len(features),'vector_truncated':truncated,
            'vector_inline_omitted':len(encoded.encode('utf-8')) > 1048576,
            'statistics_basis':'full_valid_raster; vector truncation does not affect statistics',
            'geotiff_path':str((output/'transitions.tif').relative_to(root)), 'csv_path':str((output/'transitions.csv').relative_to(root))}
    (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report


@_serialized
def analyze_timeseries(payload: dict, data_root: Path) -> dict:
    """연차별 입력을 실제 추론하고 인접·기준연도 전이를 한 번씩 계산한다."""
    root = Path(data_root).resolve()
    images = payload.get('images', [])
    if not isinstance(images, list) or not 2 <= len(images) <= 100:
        raise ValueError('연차 분석에는 images가 2~100개 필요합니다.')
    years = [item.get('year') for item in images]
    if any(type(year) is not int or not 1900 <= year <= 2200 for year in years):
        raise ValueError('year는 1900~2200 범위의 정수여야 합니다.')
    if len(set(years)) != len(years) or years != sorted(years):
        raise ValueError('year는 중복 없이 오름차순이어야 합니다.')
    output_id = payload.get('output_id', 'timeseries')
    output = safe_path(root, f'results/{output_id}')
    if output.exists():
        raise ValueError('결과가 이미 존재합니다. 새 output_id를 사용하세요.')
    checkpoint_path = safe_path(root, payload['checkpoint_path'])
    provenance = []
    reference = None
    # 모든 연차를 먼저 검증해 뒤늦은 grid 오류로 일부 추론만 생성되는 것을 막는다.
    for item in images:
        path = safe_path(root, item['image_path'])
        _, mask, profile = read(path)
        if reference is None:
            reference = profile
        else:
            assert_aligned(reference, profile)
        mask_provenance = {}
        if item.get('quality_mask_path'):
            mask_path=safe_path(root,item['quality_mask_path'])
            quality,quality_valid,quality_profile=read(mask_path)
            assert_aligned(profile,quality_profile)
            mask &= quality_valid & (quality[0]>0)
            mask_provenance={'quality_mask_path':str(mask_path.relative_to(root)),'quality_mask_sha256':file_digest(mask_path),
                             'quality_mask_basis':item.get('quality_mask_basis','caller_supplied_binary_mask')}
        provenance.append({'year': item['year'], 'image_path': str(path.relative_to(root)),
                           'sha256': file_digest(path), 'valid_input_pixels': int(mask.sum()),
                           'source': item.get('source', 'user supplied; source unverified'),
                           'license': item.get('license', 'unverified'),
                           'acquisition_date': item.get('acquisition_date'),**mask_provenance})
    import torch
    checkpoint = torch.load(checkpoint_path, map_location='cpu', weights_only=True)
    manifest = checkpoint['manifest']
    output.mkdir(parents=True)
    classifications = {}
    for item in images:
        result = infer_raster({'image_path': item['image_path'], 'checkpoint_path': payload['checkpoint_path'],
                               'normalization':item.get('normalization'),
                               'source_scene':item.get('source_scene'),
                               'quality_mask_path':item.get('quality_mask_path'),'quality_mask_basis':item.get('quality_mask_basis','caller_supplied_binary_mask'),
                               'output_id': f'{output_id}/years/{item["year"]}'}, root)
        classifications[str(item['year'])] = {'year': item['year'], **result}
    observations = [f'{a}-{b}' for a,b in zip(years, years[1:])]
    adjacent = [f'{a}-{b}' for a,b in zip(years, years[1:]) if b-a == 1]
    missing_years = sorted(set(range(years[0], years[-1]+1))-set(years))
    baseline = [f'{years[0]}-{year}' for year in years[1:]]
    changes = {}
    # 첫 인접연도와 기준연도 쌍은 동일하므로 공통 사전에서 결과를 재사용한다.
    for pair in dict.fromkeys(observations + baseline):
        a,b = pair.split('-')
        changes[pair] = {'from_year': int(a), 'to_year': int(b), **analyze_change({
            't1_path': classifications[a]['classification_path'],
            't2_path': classifications[b]['classification_path'],
            'output_id': f'{output_id}/changes/{pair}','class_names':manifest['class_names']}, root)}
    report = {'years': years, 'baseline_year': years[0], 'classifications': classifications,
              'class_names':manifest.get('class_names',CLASS_NAMES),'label_taxonomy_signature':manifest.get('label_taxonomy_signature'),
              'adjacent_pairs': adjacent, 'adjacent_observation_pairs': observations, 'baseline_pairs': baseline, 'changes': changes,
              'provenance': provenance, 'checkpoint_path': str(checkpoint_path.relative_to(root)),
              'checkpoint_sha256': file_digest(checkpoint_path), 'architecture': checkpoint['architecture'],
              'dataset_version': manifest['version'], 'synthetic': manifest.get('synthetic', False),
              'reference_kind': manifest.get('reference_kind', 'unverified_or_pseudo_label'),
              'quality': {'grid_alignment': 'verified', 'missing_years': missing_years,
                          'annual_coverage_complete': not missing_years,
                          'adjacent_pairs_definition':'calendar-year gap exactly 1; adjacent_observation_pairs may span missing years',
                          'cloud_shadow_mask': 'per-year external binary mask when provided; otherwise input_nodata_only',
                          'warning': '연차 차이는 계절·센서·구름·모델 오류를 포함할 수 있습니다. 실제 관측연도만 분석하며 누락 연도를 생성하지 않습니다.'},
              'report_path': str((output/'timeseries.json').relative_to(root))}
    (output/'timeseries.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report


@_serialized
def evaluate_model(payload: dict, data_root: Path) -> dict:
    """전문가 참조자료 평가. 독립성 자체는 사용자의 증빙 진술이며 자동 인증이 아니다."""
    root=Path(data_root).resolve()
    if payload.get('reference_kind') != 'expert_independent':
        raise ValueError('reference_kind=expert_independent 전문가 독립 참조자료만 제출할 수 있습니다.')
    for field in ('label_provenance','reviewer','group'):
        if not str(payload.get(field,'')).strip():
            raise ValueError(f'독립 평가 증빙 필드가 필요합니다: {field}')
    import torch
    checkpoint=torch.load(safe_path(root,payload['checkpoint_path']),map_location='cpu',weights_only=True)
    manifest=checkpoint['manifest']
    if manifest.get('synthetic') or manifest.get('reference_kind')=='synthetic':
        raise ValueError('합성 데이터 학습 모델은 운영 독립 검증 대상으로 승인할 수 없습니다.')
    if manifest.get('label_taxonomy_signature') and payload.get('label_taxonomy_signature')!=manifest['label_taxonomy_signature']:
        raise ValueError('독립 참조라벨의 분류체계 서명이 모델과 일치해야 합니다.')
    # 기존 자료의 파일 이름 변경을 통한 우발적 중복도 내용 해시로 검출한다.
    import hashlib
    def digest(path):
        h=hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda:stream.read(1024*1024),b''):
                h.update(block)
        return h.hexdigest()
    image_path=safe_path(root,payload['image_path']); label_path=safe_path(root,payload['label_path'])
    candidate_hashes={digest(image_path),digest(label_path)}
    _,_,candidate_profile=read(image_path)
    from rasterio.transform import array_bounds
    from rasterio.warp import transform_bounds
    candidate_bounds=transform_bounds(candidate_profile['crs'],'EPSG:4326',*array_bounds(candidate_profile['height'],candidate_profile['width'],candidate_profile['transform']),densify_pts=21)
    for scene in manifest.get('provenance',[]):
        if str(scene['group'])==str(payload['group']):
            raise ValueError('평가 그룹이 학습 데이터셋에 이미 포함되어 있습니다.')
        previous_bounds=scene.get('bounds_wgs84')
        if previous_bounds and min(candidate_bounds[2],previous_bounds[2])>max(candidate_bounds[0],previous_bounds[0]) and min(candidate_bounds[3],previous_bounds[3])>max(candidate_bounds[1],previous_bounds[1]):
            raise ValueError('독립 평가 영상의 공간 범위가 학습 데이터셋과 중첩됩니다.')
        for key in ('image_path','label_path'):
            if scene.get(key.replace('_path','_sha256')) in candidate_hashes:
                raise ValueError('평가 자료의 해시가 학습 데이터셋 원본과 중복됩니다.')
            previous=safe_path(root,scene[key])
            if previous.exists() and digest(previous) in candidate_hashes:
                raise ValueError('평가 영상 또는 라벨이 학습 데이터셋과 중복됩니다.')
    label,valid,profile=read(label_path)
    if label.shape[0]!=1:
        raise ValueError('평가 라벨은 0~8 단일 밴드 범주형 래스터여야 합니다.')
    _,_,image_profile=read(image_path); assert_aligned(profile,image_profile)
    result=infer_raster(payload,root)
    prediction,pred_valid,pred_profile=read(safe_path(root,result['classification_path']))
    truth=label[0]; pred=prediction[0]
    valid &= pred_valid & (truth>=0) & (truth<9) & (truth==np.floor(truth))
    if not valid.any():
        raise ValueError('평가 가능한 유효 참조 픽셀이 없습니다.')
    confusion=np.bincount(truth[valid].astype('int64')*9+pred[valid],minlength=81).reshape(9,9)
    report={**metrics(confusion),'reference_kind':'expert_independent','reviewer':payload['reviewer'],
            'label_provenance':payload['label_provenance'],'group':payload['group'],'independence_basis':'user_attestation_with_duplicate_hash_and_group_checks',
            'independence_warning':'공간 중첩·라벨 작성 독립성은 전문가의 증빙 검토가 추가로 필요합니다.',
            'evaluated_pixels':int(valid.sum()),'checkpoint_path':payload['checkpoint_path'],**result}
    out=safe_path(root,result['classification_path']).parent/'evaluation.json'
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report
