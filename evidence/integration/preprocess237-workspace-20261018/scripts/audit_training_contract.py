"""기존 baseline 파일을 읽어 입력·라벨·학습설정·예측 분포를 감사한다. 재학습하지 않는다."""
import argparse
import ast
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np

PROJECT_ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT_ROOT))
from backend.app.ml.dataset import file_digest
from backend.app.ml.raster import read, safe_path, CLASS_NAMES, IGNORE
from scripts.audit_first_group import WORLD_COVER


def distribution(labels):
    labels=np.asarray(labels)
    valid=np.isfinite(labels) & (labels>=0) & (labels<9) & (labels==np.floor(labels))
    counts=np.bincount(labels[valid].astype('int64'),minlength=9)
    total=int(counts.sum())
    present=np.flatnonzero(counts).tolist()
    return {'total_pixels':int(labels.size),'valid_pixels':total,'ignore_255_pixels':int((labels==IGNORE).sum()),
            'other_invalid_pixels':int(labels.size-total-(labels==IGNORE).sum()),
            'class_counts':counts.tolist(),'class_ratios':(counts/total).tolist() if total else [None]*9,
            'unique_classes':present,'single_class_prediction':len(present)==1,
            'dominant_class':int(counts.argmax()) if total else None,
            'dominant_ratio':float(counts.max()/total) if total else None}


def numeric_summary(values):
    array=np.asarray(values)
    valid=array[np.isfinite(array)]
    percentiles=[0,1,5,25,50,75,95,99,100]
    return {'dtype':str(array.dtype),'count':int(valid.size),'nonfinite_count':int(array.size-valid.size),
            'min':float(valid.min()) if valid.size else None,'max':float(valid.max()) if valid.size else None,
            'percentiles':{str(p):float(v) for p,v in zip(percentiles,np.percentile(valid,percentiles))} if valid.size else {}}


def source_defaults(path):
    """과거 checkpoint에 없는 설정은 현행 소스의 기본값임을 구분해 읽는다."""
    tree=ast.parse(Path(path).read_text(encoding='utf-8'))
    function=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='train_model')
    result={}
    for node in ast.walk(function):
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and isinstance(node.func.value,ast.Name) and node.func.value.id=='payload' and node.func.attr=='get' and node.args and isinstance(node.args[0],ast.Constant):
            try:
                result[node.args[0].value]=ast.literal_eval(node.args[1]) if len(node.args)>1 else None
            except (ValueError,TypeError):
                pass
    return result


def audit(report_path, data_root):
    root=Path(data_root).resolve();report_path=Path(report_path).resolve()
    run=json.loads(report_path.read_text(encoding='utf-8'))
    manifest_path=safe_path(root,run['dataset']['manifest_path'])
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    checkpoint_path=safe_path(root,run['training']['checkpoint_path'])
    import torch
    checkpoint=torch.load(checkpoint_path,map_location='cpu',weights_only=True)
    if checkpoint['manifest']['version']!=manifest['version']:
        raise ValueError('checkpoint와 데이터셋 버전이 다릅니다.')
    registration_path=report_path.parent/'registration.json'
    registration=json.loads(registration_path.read_text(encoding='utf-8')).get('registration',{}) if registration_path.exists() else {}
    checkpoint_hash=file_digest(checkpoint_path)
    expected_checkpoint_hash=run.get('checkpoint_sha256',registration.get('checkpoint_sha256'))
    if expected_checkpoint_hash and checkpoint_hash!=expected_checkpoint_hash:
        raise ValueError('현재 checkpoint 해시가 실행/등록 기록과 다릅니다.')
    service_path=PROJECT_ROOT/'backend/app/ml/service.py'
    defaults=source_defaults(service_path)
    recorded_config=checkpoint.get('training_config')
    settings=recorded_config or defaults
    source_report_path=root/'baseline2021/annual-window-report.json'
    source_report=json.loads(source_report_path.read_text(encoding='utf-8')) if source_report_path.exists() else {'scenes':[]}
    source_rows={str(safe_path(root,row['image_path'])):row for row in source_report.get('scenes',[]) if row.get('image_path')}
    scenes=[];patches=[]
    split_totals={split:{'class_counts':np.zeros(9,dtype='int64'),'ignore_255_pixels':0,'total_pixels':0,'patch_count':0} for split in ('train','val','test')}
    all_mapping_match=True;all_normalization_match=True
    for index,source in enumerate(manifest['provenance']):
        image_path=safe_path(root,source['image_path']);label_path=safe_path(root,source['label_path'])
        image,image_valid,profile=read(image_path);label,label_valid,_=read(label_path)
        if source['label_source']!='worldcover':
            raise ValueError('이 baseline 계약 감사는 WorldCover 라벨 실험을 대상으로 합니다.')
        source_row=source_rows.get(str(image_path),{})
        named_bands=source_row.get('bands',['unknown']*image.shape[0])
        mapped=np.full(label.shape[1:],IGNORE,dtype='uint8')
        for original,target in WORLD_COVER.items():
            mapped[label[0]==original]=target
        valid=image_valid & label_valid & np.isfinite(image).all(0) & (mapped!=IGNORE)
        if source.get('quality_mask_path'):
            quality,qvalid,_=read(safe_path(root,source['quality_mask_path']))
            valid &= qvalid & (quality[0]>0)
        mapped[~valid]=IGNORE
        selected=np.asarray(manifest['bands'])-1
        normalized=image[selected].astype('float32')*manifest['scale']+manifest['offset']
        normalized[:,~valid]=0
        scenes.append({'group':source['group'],'image_path':source['image_path'],'image_sha256':file_digest(image_path),
                       'label_path':source['label_path'],'label_sha256':file_digest(label_path),
                       'source_hash_matches_dataset':file_digest(image_path)==source['image_sha256'] and file_digest(label_path)==source['label_sha256'],
                       'raw_shape':list(image.shape),'raw_dtype':str(image.dtype),'source_band_order':named_bands,
                       'raw_dn_statistics':[{'source_band_index':int(band),'source_band_name':named_bands[int(band)-1],
                                             **numeric_summary(image[int(band)-1][image_valid])} for band in manifest['bands']],
                       'raw_worldcover_counts':{str(int(v)):int(n) for v,n in zip(*np.unique(label[0],return_counts=True))},
                       'mapped_reference_distribution':distribution(mapped)})
        for item in manifest['patches']:
            parts=Path(item['path']).stem.split('_')
            if len(parts)!=3 or int(parts[0])!=index:
                continue
            y,x=int(parts[1]),int(parts[2])
            patch_path=safe_path(root,manifest_path.parent/item['path'])
            with np.load(patch_path,allow_pickle=False) as npz:
                xx,yy=npz['image'],npz['label']
            size=manifest['patch_size'];h,w=min(size,mapped.shape[0]-y),min(size,mapped.shape[1]-x)
            expected_label=np.full((size,size),IGNORE,dtype='uint8');expected_label[:h,:w]=mapped[y:y+h,x:x+w]
            expected_image=np.zeros_like(xx);expected_image[:,:h,:w]=normalized[:,y:y+h,x:x+w]
            mapping_match=np.array_equal(yy,expected_label)
            normalization_match=np.allclose(xx,expected_image,atol=1e-7,rtol=1e-6)
            all_mapping_match &= mapping_match;all_normalization_match &= normalization_match
            hist=distribution(yy);summary=split_totals[item['split']]
            summary['class_counts']+=np.asarray(hist['class_counts']);summary['ignore_255_pixels']+=hist['ignore_255_pixels']
            summary['total_pixels']+=hist['total_pixels'];summary['patch_count']+=1
            patches.append({'path':str(patch_path.relative_to(root)),'sha256':file_digest(patch_path),'group':item['group'],'split':item['split'],
                            'image_shape':list(xx.shape),'image_dtype':str(xx.dtype),'label_shape':list(yy.shape),'label_dtype':str(yy.dtype),
                            'mapping_matches_original_worldcover':mapping_match,'normalization_matches_manifest':normalization_match,
                            'input_on_labeled_pixels':[numeric_summary(channel[yy!=IGNORE]) for channel in xx],
                            'labels':hist})
    for summary in split_totals.values():
        counts=summary['class_counts'];total=int(counts.sum())
        summary.update(valid_pixels=total,class_ratios=(counts/total).tolist() if total else [None]*9,
                       class_counts=counts.tolist(),present_classes=np.flatnonzero(counts).tolist(),
                       missing_classes=np.flatnonzero(counts==0).tolist(),
                       majority_class=int(counts.argmax()) if total else None,
                       majority_ratio=float(counts.max()/total) if total else None)
    predictions=[]
    for prediction in run['predictions']:
        path=safe_path(root,prediction['classification_path'])
        raster,mask,profile=read(path)
        hist=distribution(np.where(mask,raster[0],IGNORE))
        predictions.append({'path':str(path.relative_to(root)),'sha256':file_digest(path),'group':prediction['group'],
                            'shape':list(raster.shape),'dtype':str(raster.dtype),'nodata':profile.get('nodata'),**hist})
    reference_path=root/'raw-reference/reference-report.json'
    reference=json.loads(reference_path.read_text(encoding='utf-8')) if reference_path.exists() else {}
    return {'audit_at':datetime.now(timezone.utc).isoformat(),'run_id':run['run_id'],'synthetic':run['synthetic'],
            'evidence_files':{'run_report':{'path':str(report_path),'sha256':file_digest(report_path)},
                              'dataset_manifest':{'path':str(manifest_path),'sha256':file_digest(manifest_path)},
                              'checkpoint':{'path':str(checkpoint_path),'sha256':checkpoint_hash,
                                            'matches_recorded_hash':checkpoint_hash==expected_checkpoint_hash if expected_checkpoint_hash else None},
                              'registration_report_hash_matches_current_report':registration.get('report_sha256')==file_digest(report_path) if registration else None},
            'input_contract':{'channels':len(manifest['bands']),'source_band_indices':manifest['bands'],
                              'band_order_observed':[scene['source_band_order'] for scene in scenes],
                              'logical_band_order':['blue','green','red'],'bands_not_present':['NIR','SWIR','NDVI','NDWI'],
                              'source_band_order_verified':all(scene['source_band_order']==['B02','B03','B04'] for scene in scenes),
                              'patch_size':manifest['patch_size'],'batch_shape':[1,len(manifest['bands']),manifest['patch_size'],manifest['patch_size']],
                              'normalization':{'scale':manifest['scale'],'offset':manifest['offset'],'kind':'numeric_DN_scaling',
                                               'physical_reflectance_verified':False,'normalization_matches_all_npz':bool(all_normalization_match)}},
            'mapping':{'ignore_index':IGNORE,'source_nodata':0,'target_class_names':CLASS_NAMES,
                       'worldcover_to_internal':{str(key):value for key,value in WORLD_COVER.items()},
                       'mapping_matches_all_npz':bool(all_mapping_match),'semantic_caution':'mangrove95->trees1 and moss100->grass2 are lossy harmonization choices'},
            'scenes':scenes,'patches':patches,'splits':split_totals,
            'training_settings':{'architecture':checkpoint['architecture'],'device_recorded':run['training']['device'],
                                 'epochs_executed':len(run['training']['history']),'checkpoint_epoch':checkpoint['epoch'],'seed':checkpoint['seed'],
                                 'loss':settings.get('loss'),'optimizer':settings.get('optimizer'),'learning_rate':settings.get('lr'),
                                 'class_weights':settings.get('class_weights'),'ignore_index':IGNORE,
                                 'batch_size':settings.get('batch_size',1) if recorded_config else 1,
                                 'configuration_basis':'serialized_actual_applied_values' if recorded_config else 'reconstructed_source_defaults',
                                 'serialized_training_config':recorded_config,
                                 'nonserialized_settings_basis':None if recorded_config else 'reconstructed from current service defaults and baseline runner; optimizer state/lr/loss were not serialized in this original checkpoint',
                                 'service_source_sha256':file_digest(service_path),'runner_source_sha256':file_digest(PROJECT_ROOT/'scripts/run_baseline.py')},
            'predictions':predictions,'all_predictions_single_grass':bool(predictions) and all(item['unique_classes']==[2] for item in predictions),
            'test_metrics_recorded':run['training']['test_metrics'],
            'normalization_evidence':{'west_java_processing_baseline':reference.get('source_properties',{}).get('s2:processing_baseline'),
                                      'west_java_source_scene':reference.get('source_scene_id'),'other_two_processing_baselines':'not verified',
                                      'per_band_scale_offset_from_product_metadata':'not established; N0300 alone is insufficient'},
            'claim':'3 patches and 3 epochs verify data-to-training/inference execution only; WC agreement is not independently validated real-world accuracy',
            'independent_reference_available':False,'scientific_accuracy_validated':False,'first_group_performance_claim':False,
            'retraining_gate':{'minimum_temporally_valid_patches':1000,'province_and_class_coverage_review_required':True,
                               'physical_normalization_qa_required':True,'label_temporal_semantic_qa_required':True,
                               'independent_reference_required_for_weak_label_experiment':False,
                               'expert_independent_holdout_required_for_accuracy_claim':True,'current_gate_passed':False}}


def main():
    if hasattr(sys.stdout,'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',type=Path,default=PROJECT_ROOT/'data/results/baseline2021_cpu_v1/baseline-run.json')
    parser.add_argument('--data-root',type=Path,default=PROJECT_ROOT/'data')
    parser.add_argument('--output',type=Path,default=PROJECT_ROOT/'data/audits/training-contract.json')
    args=parser.parse_args();result=audit(args.report,args.data_root)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'run_id':result['run_id'],'mapping_matches':result['mapping']['mapping_matches_all_npz'],
                      'normalization_matches':result['input_contract']['normalization']['normalization_matches_all_npz'],
                      'single_grass_predictions':result['all_predictions_single_grass'],'scientific_accuracy_validated':False},ensure_ascii=False))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
