"""Opt-in targeted256 collector using existing global budget, circuit and QA."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import threading

ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT/'backend',ROOT/'scripts'):sys.path.insert(0,str(p))
from app.data import service
from app.data.budget import CollectionLedger
from app.data.parallel import run_two_workers
from app.data.targeted_bare_plan import prepare_targeted_bare_jobs,_pinned,_json,_need
from app.data.targeted_inventory import inspect_targeted_inventory
from app.data.targeted_inventory_profile import inventory_kwargs,metadata as profile_metadata
from app.data.targeted_live_guards import TargetedLiveGuard,TargetedWindowClaims,scene_registry
from app.data.targeted_execution import _directory_identity
from app.ml.per_scene_normalization_files import _root,_snapshot,_check_path
from collect_samples import collect_windows,load_config,now
from collect_training_grid import materialize_patches,write_json,COG_BATCH,METADATA_BATCH
from collect_training_parallel import balanced_coverage
from diagnose_stac import classify_error


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode()).hexdigest()


def physical_patch_inventory(root, aggregate, ledger_state):
    """Count local patch footprints, including rejected/unreported physical files.

    Read-only sequential observation, not native quality approval. Every explicit
    row needs three regular local files; duplicate image identities fail closed.
    Loose partial patch directories consume a slot even without a worker receipt.
    """
    root=_root(root);output=root/'data/first-group-training-esri-v1'
    patch_root=_root(output/'patches');source_root=_root(output/'sources')
    directories=set();references=set();identities=set();observations=[];receipts={}

    def local_file(value):
        _need(type(value) is str and bool(value),'TARGETED_PATCH_REFERENCE_INVALID')
        path=Path(value)
        if not path.is_absolute():path=root/path
        _need(path.is_relative_to(root/'data'),'TARGETED_PATCH_REFERENCE_INVALID')
        try:attributes=_check_path(root,path,'physical_patch')
        except Exception:raise ValueError('TARGETED_PATCH_REFERENCE_UNAVAILABLE') from None
        _need(not getattr(attributes,'st_file_attributes',0)&0x400,'TARGETED_PATCH_REFERENCE_INVALID')
        observations.append([path.relative_to(root).as_posix(),attributes.st_size,
                             attributes.st_mtime_ns,attributes.st_ctime_ns])
        return path,attributes

    def row_reference(row):
        _need(type(row) is dict,'TARGETED_PATCH_REFERENCE_INVALID')
        image,attributes=local_file(row.get('image_path'))
        _need(image.name=='image.tif','TARGETED_PATCH_REFERENCE_INVALID')
        identity=(attributes.st_dev,attributes.st_ino)
        _need(image not in references and identity not in identities,'TARGETED_PATCH_REFERENCE_DUPLICATE')
        references.add(image);identities.add(identity);directories.add(image.parent)
        _need(len(directories)<=3000,'TARGETED_PHYSICAL_PATCH_LIMIT')
        role_paths={image}
        for key,name in (('label_path','label.tif'),('quality_mask_path','quality.tif')):
            path,_=local_file(row.get(key))
            _need(path.parent==image.parent and path.name==name and path not in role_paths,
                  'TARGETED_PATCH_REFERENCE_INVALID')
            role_paths.add(path)

    for row in aggregate['scenes']+aggregate.get('historical_noneligible_patches',[]):row_reference(row)
    for directory in source_root.iterdir():
        _need(not directory.is_symlink() and not getattr(directory.lstat(),'st_file_attributes',0)&0x400,
              'TARGETED_PHYSICAL_PATH_INVALID')
        if not directory.is_dir():continue
        _root(directory)
        receipt=directory/'worker-result.json'
        _need(not receipt.is_symlink(),'TARGETED_PHYSICAL_PATH_INVALID')
        if receipt.exists():
            pin,raw=_snapshot(root,receipt,8*1024**2,'worker_receipt',True)
            value=_json(raw);receipts[directory.name]=pin
            rows=value.get('targeted_unenrolled_patches',[])
            _need(type(rows) is list,'TARGETED_PATCH_REFERENCE_INVALID')
            for row in rows:row_reference(row)
    for key in ledger_state['batches']:
        if key.startswith('target256-'):
            _need(key in receipts,'TARGETED_WORKER_RECEIPT_UNAVAILABLE')
    pending=[(patch_root,0)];files=0;visited=0
    while pending:
        directory,depth=pending.pop();visited+=1
        _need(depth<=12 and visited<=20000,'TARGETED_PHYSICAL_SCAN_LIMIT')
        _root(directory)
        for path in directory.iterdir():
            attributes=path.lstat()
            _need(not path.is_symlink() and not getattr(attributes,'st_file_attributes',0)&0x400,
                  'TARGETED_PHYSICAL_PATH_INVALID')
            if stat.S_ISDIR(attributes.st_mode):pending.append((path,depth+1))
            else:
                files+=1;_need(files<=30000,'TARGETED_PHYSICAL_SCAN_LIMIT')
                _need(stat.S_ISREG(attributes.st_mode),'TARGETED_PHYSICAL_PATH_INVALID')
                if path.name in {'image.tif','label.tif','quality.tif'}:
                    directories.add(path.parent)
                    _need(len(directories)<=3000,'TARGETED_PHYSICAL_PATCH_LIMIT')
                    observations.append([path.relative_to(root).as_posix(),attributes.st_size,
                                         attributes.st_mtime_ns,attributes.st_ctime_ns])
    _need(len(directories)<=3000,'TARGETED_PHYSICAL_PATCH_LIMIT')
    return {'physical_patch_count':len(directories),'referenced_patch_count':len(references),
            'unreferenced_physical_directories':len(directories-{p.parent for p in references}),
            'worker_receipt_count':len(receipts),'limit':3000,
            'observation_sha256':digest({'files':sorted(observations),'receipts':receipts,
                                        'directories':sorted(str(p.relative_to(root)) for p in directories)})}


class TargetedExecutionFailure(RuntimeError):
    """A failure after a reservation; transfer cannot be inferred from a CLI error."""
    def __init__(self, progress):
        super().__init__('TARGETED_EXECUTION_OR_FINALIZATION_FAILED')
        self.progress=progress


def _execution_progress(progress):
    details={key:list(value) for key,value in progress.items()}
    attempted=set(progress['reservation_attempted_batches']);reserved=set(progress['reserved_batches'])
    details.update(execution_started=bool(attempted),transfer_status='NOT_INDEPENDENTLY_VERIFIED',
        reservation_status='ALL_ATTEMPTS_CONFIRMED_RESERVED' if attempted==reserved else 'INCOMPLETE_OR_UNVERIFIED',
        settlement_status='ALL_RESERVED_SETTLED' if attempted==reserved==set(progress['settled_batches']) else 'INCOMPLETE_OR_UNVERIFIED',
        publication_status='ALL_RESERVED_PUBLISHED' if attempted==reserved==set(progress['published_batches']) else 'INCOMPLETE_OR_UNVERIFIED')
    return details


def validate_request(root, request, expected_sha256):
    """Read-only full plan/inventory validation; never converts157 into approval."""
    root=_root(root)
    inventory_options=inventory_kwargs(request,{'schema_version','plan','ledger_ref','maximum_batches'},'TARGETED_REQUEST_INVALID')
    _need(type(request['maximum_batches']) is int and 1<=request['maximum_batches']<=2,'TARGETED_REQUEST_INVALID')
    _need(digest(request)==expected_sha256,'TARGETED_REQUEST_PIN_MISMATCH')
    aggregate_path=root/'data/first-group-training-esri-v1/annual-window-report.json'
    ledger_path=root/'data/first-group-training-budget/global-ledger.json'
    source_pin,raw=_snapshot(root,aggregate_path,128*1024**2,'aggregate',True)
    aggregate=_json(raw)
    _need(source_pin==request['plan']['current_manifest_ref']['sha256'],'TARGETED_SOURCE_CHANGED')
    _,ledger_raw=_pinned(root,request['ledger_ref'],8*1024**2)
    _need(_snapshot(root,ledger_path,8*1024**2,'ledger')[0]==request['ledger_ref']['sha256'],'TARGETED_LEDGER_CHANGED')
    state=_json(ledger_raw)
    _need(state['rate_limit_active'] is False and state['additional_maximum_bytes']==4*1024**3,
          'TARGETED_CIRCUIT_OR_BUDGET_INVALID')
    _need(state['additional_maximum_bytes']-state['new_charged_bytes']>=
          request['maximum_batches']*(COG_BATCH+METADATA_BATCH),'TARGETED_BUDGET_SHORTFALL')
    base=_json((root/'configs/first-group.collection.json').read_bytes())
    local=prepare_targeted_bare_jobs(root,request['plan'],base)
    _need(local['status']=='LOCAL_TARGETS_VERIFIED_EXECUTION_BLOCKED','TARGETED_LOCAL_PLAN_'+str(local['issue']))
    jobs=local['job_proposals']
    _need(1<=len(jobs)<=request['maximum_batches'],
          'TARGETED_PATCH_OR_BATCH_LIMIT')
    for job in jobs:
        _need(job['nominal_patches']==1 and job['config']['window_size']==256 and
              len(job['config']['aois'])==1 and job['config']['years']==[job['year']],
              'TARGETED_MAXIMUM_NEW_PATCHES_INVALID')
    physical=physical_patch_inventory(root,aggregate,state)
    _need(physical['physical_patch_count']+len(jobs)<=3000,'TARGETED_PHYSICAL_PATCH_LIMIT')
    proofs=[]
    for target in request['plan']['targets']:
        proof=inspect_targeted_inventory(root,{'manifest_ref':request['plan']['current_manifest_ref'],
                  'ledger_ref':request['ledger_ref'],'target':target['target_footprint_native']},**inventory_options)
        _need(proof['status']=='LOCAL_INVENTORY_VERIFIED_EXECUTION_BLOCKED','TARGETED_INVENTORY_'+str(proof['issue']))
        proofs.append(proof)
    _need(_snapshot(root,aggregate_path,128*1024**2,'aggregate')[0]==source_pin and
          _snapshot(root,ledger_path,8*1024**2,'ledger')[0]==request['ledger_ref']['sha256'],'TARGETED_INPUT_CHANGED')
    _need(physical_patch_inventory(root,aggregate,state)==physical,'TARGETED_PHYSICAL_INVENTORY_CHANGED')
    for job in jobs:
        _need(job['key'] not in state['batches'],'TARGETED_BATCH_ALREADY_RESERVED')
        job['spatial_window_id']='bare256-'+job['target_id']
    return {'root':root,'jobs':jobs,'aggregate':aggregate,'aggregate_path':aggregate_path,
            'ledger_path':ledger_path,'source_sha256':source_pin,'inventory':proofs,
            'physical_inventory':physical,'maximum_new_physical_patches':len(jobs),
            'targets':{t['target_id']:t for t in request['plan']['targets']},'request_sha256':expected_sha256,
            **profile_metadata(request)}


def run_targeted(root,request,expected_sha256,*,execute=False):
    root=_root(root)
    lock=root/'data/first-group-training-budget/global-ledger.execution.lock'
    fd=None;identity=None;event=threading.Event()
    progress={'reservation_attempted_batches':[],'reserved_batches':[],'collector_entered_batches':[],
              'settled_batches':[],'published_batches':[],'finalization_attempted_batches':[]}
    try:
        if execute:
            fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
            os.write(fd,str(os.getpid()).encode());st=os.fstat(fd);identity=(st.st_dev,st.st_ino)
        checked=validate_request(root,request,expected_sha256)
        if not execute:
            return {'status':'LOCAL_DISPATCH_INPUTS_VERIFIED','executed':False,
                    'request_sha256':expected_sha256,**profile_metadata(request),'jobs':[j['key'] for j in checked['jobs']],
                    'inventory_assets':len(checked['inventory'][0]['assets']),
                    'physical_inventory':checked['physical_inventory'],
                    'maximum_new_physical_patches':checked['maximum_new_physical_patches'],
                    'live_scene_and_window_verified':False,'learning_ready':False}
        ledger=CollectionLedger(checked['ledger_path'],[root/'data/first-group-annual/run-result.json',
                   root/'data/first-group-recovery32/run-result.json'],initial_metadata_charge=3675728)
        service.configure_request_spacing(2);service.configure_request_circuit(event)
        output=checked['aggregate_path'].parent;aggregate=checked['aggregate']
        claims=scene_registry(aggregate,checked['source_sha256'])
        windows=TargetedWindowClaims(checked['inventory'][0]['assets'])
        reservations={};summaries=[]
        _need(checked['maximum_new_physical_patches']==len(checked['jobs']) and
              checked['physical_inventory']['physical_patch_count']+len(checked['jobs'])<=3000,
              'TARGETED_PHYSICAL_PATCH_LIMIT')

        def reserve(job):
            parent_source=_root(output/'sources');parent_patch=_root(output/'patches')
            created=[]
            try:
                for parent in (parent_source,parent_patch):
                    leaf=parent/job['key'];os.mkdir(leaf);created.append((leaf,_directory_identity(leaf)))
                progress['reservation_attempted_batches'].append(job['key'])
                accepted=ledger.reserve(job['key'],COG_BATCH+METADATA_BATCH,job['config_sha256'])
                _need(accepted,'TARGETED_BATCH_NOT_NEW')
                reservations[job['key']]=created
                progress['reserved_batches'].append(job['key'])
                return True
            except Exception:
                for leaf,stamp in reversed(created):
                    try:
                        if _directory_identity(leaf)==stamp:os.rmdir(leaf)
                    except (OSError,ValueError):pass
                raise

        def work(job):
            directory=output/'sources'/job['key'];result={'key':job['key'],'patches':[]}
            service.configure_metadata_budget(METADATA_BATCH)
            guard=TargetedLiveGuard(job,checked['targets'][job['target_id']],claims,windows)
            print(json.dumps({'status':'targeted_worker_started','key':job['key']}),flush=True)
            try:
                for leaf,stamp in reservations[job['key']]:
                    _need(_directory_identity(leaf)==stamp,'TARGETED_OUTPUT_RESERVATION_CHANGED')
                path=directory/'config.json';write_json(path,job['config'])
                progress['collector_entered_batches'].append(job['key'])
                report=collect_windows(load_config(path),directory,execute=True,
                                       selection_context=job['selection_context'],collection_guard=guard)
                result.update(report_path=str(directory/'annual-window-report.json'),circuit=report.get('batch_circuit_breaker'))
                if guard.b02_checked:
                    # Actual selected B02 is256 and each job is one AOI/year.
                    # Check report cardinality and local image dimensions BEFORE
                    # materialization can create any additional physical patch.
                    import rasterio
                    maximum=0
                    for source in report.get('scenes',[]):
                        if source.get('status')=='rgb_window_downloaded':
                            image=Path(source['image_path']);_check_path(root,image,'targeted_source_image')
                            with rasterio.open(image) as dataset:
                                maximum+=(dataset.width//256)*(dataset.height//256)
                    _need(maximum<=1,'TARGETED_MAXIMUM_NEW_PATCHES_EXCEEDED')
                    patches=materialize_patches(report,job,output)
                    _need(len(patches)<=1,'TARGETED_MAXIMUM_NEW_PATCHES_EXCEEDED')
                    result['targeted_unenrolled_patches']=[]
                    for row in patches:
                        row['targeted_bare_minimum_pixels']=256
                        row['targeted_bare_pixels']=row['sample_class_coverage'].get('8',0)
                        row['targeted_bare_class_status']='met' if row['targeted_bare_pixels']>=256 else 'insufficient'
                        if row['targeted_bare_pixels']<256:
                            # Keep actual files and full lineage in the worker
                            # receipt without changing the80/95 quality meaning.
                            result['targeted_unenrolled_patches'].append(row)
                        else:
                            result['patches'].append(row)
                result['live_b02_checked']=guard.b02_checked
            except Exception as exc:
                result['error']=classify_error(exc)
            finally:
                path=directory/'window-state.json'
                state=_json(path.read_bytes()) if path.exists() else {}
                metadata=service.metadata_budget_status()
                result.update(charged_bytes=state.get('http_body_bytes',0)+metadata['charged_bytes'],
                              metadata_budget=metadata,cog_charged_bytes=state.get('http_body_bytes',0))
                write_json(directory/'worker-result.json',{k:v for k,v in result.items() if k!='patches'})
            return result

        def finalize(job,result):
            progress['finalization_attempted_batches'].append(job['key'])
            if 'unmeasured_worker_failure' in result:
                result={'charged_bytes':COG_BATCH+METADATA_BATCH,'patches':[],
                        'error':classify_error(result['unmeasured_worker_failure']),'measurement_known':False}
            circuit=result.get('circuit') or service.request_circuit_status()
            ledger.settle(job['key'],result['charged_bytes'],result.get('report_path'),circuit)
            progress['settled_batches'].append(job['key'])
            if circuit:event.set()
            rows=result.get('patches',[]);aggregate['scenes'].extend(rows)
            if result.get('report_path'):aggregate.setdefault('source_manifests',[]).append(result['report_path'])
            if result.get('error'):aggregate.setdefault('batch_errors',[]).append({'key':job['key'],'error':result['error']})
            metrics=balanced_coverage(aggregate['scenes'])
            aggregate.update(status='targeted_bare_bounded_stage',policy_version='parallel-v2-targeted256',
                complete_window_count=len(aggregate['scenes']),quality_eligible_window_count=metrics['eligible_patch_count'],
                coverage_metrics=metrics,learning_ready=False,full_2020_2025_goal_met=False)
            write_json(checked['aggregate_path'],aggregate)
            progress['published_batches'].append(job['key'])
            item={'key':job['key'],'patches':len(rows),'eligible':sum(r['quality_status']=='quality_eligible' for r in rows),
                  'charged_bytes':result['charged_bytes'],'live_b02_checked':result.get('live_b02_checked',False),
                  'rate_limited':bool(circuit)}
            summaries.append(item);print(json.dumps({'status':'targeted_worker_finished',**item}),flush=True)

        execution=run_two_workers(checked['jobs'],reserve,work,finalize,event,request['maximum_batches'])
        return {'status':'BOUNDED_TARGETED_STAGE_FINISHED','executed':True,'recorded_at':now(),
                'request_sha256':expected_sha256,**profile_metadata(request),'execution':execution,'batches':summaries,
                'execution_progress':_execution_progress(progress),
                'physical_inventory_before':checked['physical_inventory'],
                'maximum_new_physical_patches':checked['maximum_new_physical_patches'],
                'quality_eligible_total':balanced_coverage(aggregate['scenes'])['eligible_patch_count'],
                'learning_ready':False,'scientific_accuracy_validated':False}
    except Exception as exc:
        if progress['reservation_attempted_batches']:
            raise TargetedExecutionFailure(_execution_progress(progress)) from exc
        raise
    finally:
        if fd is not None:
            try:
                service.configure_request_circuit(None)
                os.close(fd)
                try:
                    st=lock.lstat()
                    if (st.st_dev,st.st_ino)==identity:lock.unlink()
                except FileNotFoundError:
                    pass  # Never replace or erase someone else's missing/replaced lock.
            except Exception as exc:
                if progress['reservation_attempted_batches']:
                    details=_execution_progress(progress);details['cleanup_status']='INCOMPLETE_OR_UNVERIFIED'
                    raise TargetedExecutionFailure(details) from exc
                raise


def main():
    p=argparse.ArgumentParser(description=__doc__,allow_abbrev=False)
    p.add_argument('--request',type=Path,required=True);p.add_argument('--expected-request-sha256',required=True)
    p.add_argument('--execute',action='store_true');args=p.parse_args()
    try:
        path=args.request.resolve();_need(path.is_relative_to(ROOT/'evidence/integration'),'REQUEST_PATH_INVALID')
        _,raw=_snapshot(ROOT,path,2*1024**2,'request',True)
        print(json.dumps(run_targeted(ROOT,_json(raw),args.expected_request_sha256,execute=args.execute),ensure_ascii=True))
        return 0
    except Exception as exc:
        code=str(exc)
        progress=getattr(exc,'progress',None)
        print(json.dumps({'status':'TARGETED_EXECUTION_FAILED' if progress else 'BLOCKED',
            'executed':None if progress else False,'execute_requested':args.execute,
            'execution_started':bool(progress),'execution_progress':progress,
            'issue':code if code.replace('_','').isalnum() and code.upper()==code else 'TARGETED_LOCAL_OR_EXECUTION_FAILURE'}))
        return 2


if __name__=='__main__':raise SystemExit(main())
