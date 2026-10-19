"""명시 고정 요청의 부족 셀1024창만 단일 공유 coordinator로 수집한다."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import threading

ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'backend',ROOT/'scripts'):sys.path.insert(0,str(p))
from app.data import service
from app.data.budget import CollectionLedger
from app.data.parallel import run_two_workers
from app.data.deficit_candidate_guard import (prepare_deficit_candidate_jobs,DeficitCandidateLiveGuard,
    _inventory_diagnostic,LOCAL_SUPPORT_PROFILE,LOCAL_SUPPORT_BYTES)
from app.data.targeted_live_guards import scene_registry,TargetedWindowClaims
from app.data.targeted_execution import _directory_identity
from app.data.targeted_bare_plan import _json,_need
from app.data.quality_mask_bundle import _copy_json
from app.data.readiness_connectivity_witness import FIXED_PROVINCE_SPLITS
from app.ml.per_scene_normalization_files import _root,_snapshot,_relative,_check_path
from collect_samples import collect_windows,load_config,now
from collect_training_grid import materialize_patches,write_json,COG_BATCH,METADATA_BATCH
from collect_training_parallel import balanced_coverage
from collect_targeted_bare import digest,_execution_progress
from diagnose_stac import classify_error


class DeficitExecutionFailure(RuntimeError):
    def __init__(self,progress):
        super().__init__('DEFICIT_EXECUTION_OR_FINALIZATION_FAILED')
        self.progress=progress


class DeficitLocalProofFailure(ValueError):
    def __init__(self,code,diagnostic=None):
        super().__init__(code)
        self.inventory_diagnostic=None
        if (type(diagnostic) is dict and diagnostic.get('resource_profile')==LOCAL_SUPPORT_PROFILE and
            type(diagnostic.get('max_files')) is int and diagnostic['max_files']==10000 and
            type(diagnostic.get('max_support_bytes')) is int and diagnostic['max_support_bytes']==LOCAL_SUPPORT_BYTES):
            self.inventory_diagnostic=_inventory_diagnostic(diagnostic)


def validate_request(root,request,expected_sha256):
    """199의 fresh proof를 소비한다. EXECUTION_BLOCKED를 승인으로 바꾸지 않는다."""
    root=_root(root)
    _need(type(expected_sha256) is str and re.fullmatch('[a-f0-9]{64}',expected_sha256) is not None and
          digest(request)==expected_sha256,'DEFICIT_REQUEST_PIN_MISMATCH')
    proof=prepare_deficit_candidate_jobs(root,request)
    failure='DEFICIT_LOCAL_PROOF_INVALID'
    proof_issue=proof.get('issue')
    if proof.get('local_checks_passed') is False and type(proof_issue) is str and re.fullmatch('[A-Z_]{1,48}',proof_issue):
        failure+='_'+proof_issue
    valid=(proof.get('status')=='EXECUTION_BLOCKED' and proof.get('issue')=='COORDINATOR_NOT_CONNECTED' and
          proof.get('local_checks_passed') is True and proof.get('source_pins_verified') is True and
          proof.get('request_sha256')==expected_sha256 and proof.get('execution_supported') is False and
          proof.get('collection_executed') is False and proof.get('network_requests')==0 and
          proof.get('source_or_ledger_writes')==0)
    if not valid:
        raise DeficitLocalProofFailure(failure,proof.get('inventory_diagnostic')
                                      if proof.get('local_checks_passed') is False else None)
    inventory=proof.get('inventory');physical=proof.get('physical_inventory')
    _need(type(inventory) is dict and all(inventory.get(k) is True for k in
          ('inventory_verified','pending_footprints_verified','source_pins_verified')) and
          type(inventory.get('assets')) is list,'DEFICIT_INVENTORY_PROOF_INVALID')
    jobs=proof.get('job_proposals');targets=proof.get('targets')
    _need(type(jobs) is list and type(targets) is list and len(jobs)==len(targets) and
          type(request.get('maximum_batches')) is int and 1<=len(jobs)<=request['maximum_batches']<=2,
          'DEFICIT_BATCH_LIMIT')
    _need(type(physical) is dict and type(physical.get('physical_patch_count')) is int and
          0<=physical['physical_patch_count'] and physical.get('limit')==3000 and
          physical['physical_patch_count']+16*len(jobs)<=3000,'DEFICIT_PHYSICAL_CAP')
    aggregate_path=root/'data/first-group-training-esri-v1/annual-window-report.json'
    ledger_path=root/'data/first-group-training-budget/global-ledger.json'
    for key,path in [('current_manifest_ref',aggregate_path),('ledger_ref',ledger_path)]:
        # A pinned DATA snapshot is valid evidence when the active operational
        # file has the same SHA. CollectionLedger always receives the active path.
        _need(_relative(root,request[key]['path'],'active_input').is_relative_to(root/'data'),
              'DEFICIT_ACTIVE_PATH_INVALID')
    source_pin,raw=_snapshot(root,aggregate_path,128*1024**2,'aggregate',True);aggregate=_json(raw)
    ledger_pin,raw=_snapshot(root,ledger_path,8*1024**2,'ledger',True);state=_json(raw)
    _need(source_pin==request['current_manifest_ref']['sha256'] and ledger_pin==request['ledger_ref']['sha256'],
          'DEFICIT_ACTIVE_INPUT_CHANGED')
    _need(state['rate_limit_active'] is False and state['additional_maximum_bytes']==4*1024**3 and
          state['additional_maximum_bytes']-state['new_charged_bytes']>=len(jobs)*(COG_BATCH+METADATA_BATCH),
          'DEFICIT_BUDGET_OR_CIRCUIT_INVALID')
    target_map={}
    selected={(s['spatial_window_id'],s['year']) for s in request['selected']}
    _need(len(selected)==len(jobs),'DEFICIT_SELECTION_MISMATCH')
    for job,target in zip(jobs,targets):
        p=job.get('province');year=job.get('year');identifier=job.get('target_id');config=job.get('config',{})
        _need(type(job.get('key')) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.:-]{0,79}',job['key']) is not None and
              p in FIXED_PROVINCE_SPLITS and job.get('split')==FIXED_PROVINCE_SPLITS[p] and
              type(year) is int and (identifier,year) in selected and job.get('spatial_window_id')==identifier and
              type(job.get('nominal_patches')) is int and job['nominal_patches']==16 and
              type(config.get('window_size')) is int and config['window_size']==1024 and
              config.get('years')==[year] and len(config.get('aois',[]))==1 and
              config.get('max_total_bytes')==COG_BATCH and config.get('prior_download_budget_bytes')==0 and
              config.get('transient_asset_retries')==0 and config.get('min_valid_fraction')==.8 and
              config.get('annual_reference')=='esri_io' and
              job.get('config_sha256')==hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest(),
              'DEFICIT_JOB_PROOF_INVALID')
        _need(job['key']==f"center1024-{p}-{year}-{expected_sha256[:12]}-{digest(identifier)[:8]}",
              'DEFICIT_JOB_KEY_INVALID')
        _need(job['key'] not in state['batches'] and identifier not in target_map and
              target.get('target_id')==identifier and target.get('province')==p and target.get('year')==year and
              target.get('fixed_split')==job['split'] and target.get('window_size')==1024,
              'DEFICIT_TARGET_PROOF_INVALID')
        # Binding also verifies declared1024 footprint, target bbox, and AOI.
        DeficitCandidateLiveGuard(job,target,None,None)._binding()
        target_map[identifier]=copy.deepcopy(target)
    _need(len({j['key'] for j in jobs})==len(jobs),'DEFICIT_JOB_DUPLICATE')
    return {'root':root,'jobs':copy.deepcopy(jobs),'targets':target_map,'aggregate':aggregate,
            'aggregate_path':aggregate_path,'ledger_path':ledger_path,'ledger_state':state,
            'source_sha256':source_pin,'inventory':inventory,'physical_inventory':physical}


def run_deficit_guarded(root,request,expected_sha256,*,execute=False):
    request=_copy_json(request,'request');root=_root(root)
    lock=root/'data/first-group-training-budget/global-ledger.execution.lock'
    fd=None;identity=None;event=threading.Event()
    progress={k:[] for k in ('reservation_attempted_batches','reserved_batches','collector_entered_batches',
              'settled_batches','published_batches','finalization_attempted_batches')}
    try:
        if execute:
            fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
            st=os.fstat(fd);identity=(st.st_dev,st.st_ino);os.write(fd,str(os.getpid()).encode())
        checked=validate_request(root,request,expected_sha256)
        if not execute:
            return {'status':'DEFICIT_DISPATCH_INPUTS_VERIFIED','executed':False,'request_sha256':expected_sha256,
                    'jobs':[j['key'] for j in checked['jobs']],'physical_inventory':checked['physical_inventory'],
                    'maximum_new_physical_patches':16*len(checked['jobs']),
                    'live_scene_and_window_verified':False,'learning_ready':False}
        ledger=CollectionLedger(checked['ledger_path'],[root/'data/first-group-annual/run-result.json',
                  root/'data/first-group-recovery32/run-result.json'],initial_metadata_charge=3675728)
        service.configure_request_spacing(2);service.configure_request_circuit(event)
        aggregate=checked['aggregate'];output=checked['aggregate_path'].parent
        original_rows=copy.deepcopy(aggregate['scenes']);original_history=copy.deepcopy(aggregate.get('historical_noneligible_patches',[]))
        old_batches=copy.deepcopy(checked['ledger_state']['batches'])
        claims=scene_registry(aggregate,checked['source_sha256'])
        windows=TargetedWindowClaims(checked['inventory']['assets'])
        reservations={};summaries=[];inflight=0;completed_sources=0
        published_pin=checked['source_sha256']

        def reserve(job):
            nonlocal inflight
            _need(checked['physical_inventory']['physical_patch_count']+16*(completed_sources+inflight+1)<=3000,
                  'DEFICIT_PHYSICAL_CAP')
            _need(_snapshot(root,checked['aggregate_path'],128*1024**2,'aggregate')[0]==published_pin,
                  'DEFICIT_AGGREGATE_CHANGED')
            created=[]
            try:
                for parent in (_root(output/'sources'),_root(output/'patches')):
                    leaf=parent/job['key'];os.mkdir(leaf);created.append((leaf,_directory_identity(leaf)))
                progress['reservation_attempted_batches'].append(job['key'])
                accepted=ledger.reserve(job['key'],COG_BATCH+METADATA_BATCH,job['config_sha256'])
                _need(accepted,'DEFICIT_BATCH_NOT_NEW')
                reservations[job['key']]=created;inflight+=1;progress['reserved_batches'].append(job['key'])
                metrics=balanced_coverage(aggregate['scenes']);split=job['split']
                fractions=metrics['required_class_pixel_fractions'][split]
                counts=metrics['required_class_contributing_patches'][split]
                rows=[r for r in aggregate['scenes'] if r.get('province')==job['province'] and r.get('quality_status')=='quality_eligible']
                job['selection_context']={'priority_source_classes':[int(c) for c in fractions if fractions[c]<.005 or counts[c]<5],
                    'allow_dominant_class_deferral':len(rows)>=50 and len({r.get('spatial_location_id') for r in rows})>=32 and
                         any(int(r['year'])==job['year'] for r in rows),'snapshot_eligible_patches':len(rows)}
                return True
            except Exception:
                if job['key'] in progress['reservation_attempted_batches']:
                    # reserve may have written before raising; never interpret
                    # a post-reserve ValueError as an ordinary budget stop.
                    raise RuntimeError('DEFICIT_RESERVATION_OR_JOB_PREPARATION_UNCONFIRMED') from None
                for leaf,stamp in reversed(created):
                    try:
                        if _directory_identity(leaf)==stamp:os.rmdir(leaf)
                    except (OSError,ValueError):pass
                raise

        def work(job):
            directory=output/'sources'/job['key'];result={'key':job['key'],'patches':[]}
            service.configure_metadata_budget(METADATA_BATCH)
            guard=DeficitCandidateLiveGuard(job,checked['targets'][job['target_id']],claims,windows)
            print(json.dumps({'status':'deficit_worker_started','key':job['key']}),flush=True)
            try:
                for leaf,stamp in reservations[job['key']]:
                    _need(_directory_identity(leaf)==stamp,'DEFICIT_OUTPUT_RESERVATION_CHANGED')
                path=directory/'config.json';write_json(path,job['config'])
                write_json(directory/'selection-context.json',job['selection_context'])
                progress['collector_entered_batches'].append(job['key'])
                report=collect_windows(load_config(path),directory,execute=True,
                         selection_context=job['selection_context'],collection_guard=guard)
                result.update(report_path=str(directory/'annual-window-report.json'),circuit=report.get('batch_circuit_breaker'))
                if guard.b02_checked:
                    import rasterio
                    sources=[s for s in report.get('scenes',[]) if s.get('status')=='rgb_window_downloaded']
                    _need(len(sources)<=1,'DEFICIT_SOURCE_CARDINALITY_INVALID')
                    for source in sources:
                        image=Path(source['image_path']);_check_path(root,image,'deficit_image')
                        _need(image.is_relative_to(directory),'DEFICIT_SOURCE_PATH_INVALID')
                        with rasterio.open(image) as dataset:
                            _need(dataset.width==dataset.height==1024 and dataset.count==6,'DEFICIT_SOURCE_GRID_INVALID')
                    rows=materialize_patches(report,job,output)
                    _need(len(rows)<=16,'DEFICIT_MAXIMUM_PATCHES_EXCEEDED')
                    for row in rows:
                        _need(row.get('province')==job['province'] and row.get('split')==job['split'] and
                              str(row.get('year'))==str(job['year']) and
                              row.get('spatial_location_id','').startswith(f"{job['province']}/{job['spatial_window_id']}/"),
                              'DEFICIT_PATCH_BINDING_INVALID')
                    result['patches']=rows
                result['live_b02_checked']=guard.b02_checked
            except Exception as exc:
                result['error']=classify_error(exc)
            finally:
                result['live_b02_checked']=guard.b02_checked
                diagnostic=guard.alignment_diagnostic()
                if diagnostic is not None:
                    result['b02_alignment_diagnostic']=diagnostic
                path=directory/'window-state.json';state=_json(path.read_bytes()) if path.exists() else {}
                metadata=service.metadata_budget_status()
                result.update(charged_bytes=state.get('http_body_bytes',0)+metadata['charged_bytes'],
                    metadata_budget=metadata,cog_charged_bytes=state.get('http_body_bytes',0))
                write_json(directory/'worker-result.json',{k:v for k,v in result.items() if k!='patches'})
            return result

        def finalize(job,result):
            nonlocal inflight,completed_sources,published_pin
            progress['finalization_attempted_batches'].append(job['key'])
            if 'unmeasured_worker_failure' in result:
                # Terminal/finally failure: no invented measured completion or refund.
                raise RuntimeError('DEFICIT_WORKER_MEASUREMENT_UNCONFIRMED')
            _need(_snapshot(root,checked['aggregate_path'],128*1024**2,'aggregate')[0]==published_pin,
                  'DEFICIT_AGGREGATE_CHANGED')
            current=ledger.snapshot()
            _need(all(current['batches'].get(k)==v for k,v in old_batches.items()),'DEFICIT_OLD_BATCH_CHANGED')
            circuit=result.get('circuit') or service.request_circuit_status()
            current=ledger.settle(job['key'],result['charged_bytes'],result.get('report_path'),circuit)
            progress['settled_batches'].append(job['key']);inflight-=1;completed_sources+=1
            if circuit:event.set()
            _need(aggregate['scenes'][:len(original_rows)]==original_rows and
                  aggregate.get('historical_noneligible_patches',[])==original_history,'DEFICIT_SOURCE_PREFIX_CHANGED')
            rows=result.get('patches',[]);aggregate['scenes'].extend(rows)
            if result.get('report_path'):aggregate.setdefault('source_manifests',[]).append(result['report_path'])
            if result.get('error'):aggregate.setdefault('batch_errors',[]).append({'key':job['key'],'error':result['error']})
            metrics=balanced_coverage(aggregate['scenes'])
            aggregate.update(status='deficit_guarded_bounded_stage',policy_version='guarded-deficit-1024',
                complete_window_count=len(aggregate['scenes']),quality_eligible_window_count=metrics['eligible_patch_count'],
                coverage_metrics=metrics,learning_ready=False,full_2020_2025_goal_met=False)
            write_json(checked['aggregate_path'],aggregate)
            published_pin=_snapshot(root,checked['aggregate_path'],128*1024**2,'published_aggregate')[0]
            write_json(output/'run-result.json',{'status':aggregate['status'],'manifests':[str(checked['aggregate_path'])],
                'new_charged_upper_bound_bytes':current['new_charged_bytes'],
                'reserved_or_transferred_bytes_including_prior':current['historical_charged_bytes']+current['new_charged_bytes'],
                'new_supplementary_budget_bytes':current['additional_maximum_bytes'],
                'maximum_total_bytes':current['combined_maximum_bytes'],'learning_ready':False,
                'request_sha256':expected_sha256,'circuit_breaker':circuit})
            progress['published_batches'].append(job['key'])
            item={'key':job['key'],'patches':len(rows),'eligible':sum(r.get('quality_status')=='quality_eligible' for r in rows),
                  'charged_bytes':result['charged_bytes'],'live_b02_checked':result.get('live_b02_checked',False),
                  'rate_limited':bool(circuit)}
            summaries.append(item);print(json.dumps({'status':'deficit_worker_finished',**item}),flush=True)

        execution=run_two_workers(checked['jobs'],reserve,work,finalize,event,request['maximum_batches'])
        return {'status':'BOUNDED_DEFICIT_STAGE_FINISHED','executed':True,'recorded_at':now(),
                'request_sha256':expected_sha256,'execution':execution,'batches':summaries,
                'execution_progress':_execution_progress(progress),'physical_inventory_before':checked['physical_inventory'],
                'maximum_new_physical_patches':16*len(checked['jobs']),
                'quality_eligible_total':balanced_coverage(aggregate['scenes'])['eligible_patch_count'],
                'learning_ready':False,'scientific_accuracy_validated':False}
    except Exception as exc:
        if progress['reservation_attempted_batches']:raise DeficitExecutionFailure(_execution_progress(progress)) from exc
        raise
    finally:
        if fd is not None:
            try:
                service.configure_request_circuit(None);os.close(fd)
                try:
                    st=lock.lstat()
                    if (st.st_dev,st.st_ino)==identity:lock.unlink()
                except FileNotFoundError:pass
            except Exception as exc:
                if progress['reservation_attempted_batches']:
                    details=_execution_progress(progress);details['cleanup_status']='INCOMPLETE_OR_UNVERIFIED'
                    raise DeficitExecutionFailure(details) from exc
                raise


def main():
    parser=argparse.ArgumentParser(description=__doc__,allow_abbrev=False)
    parser.add_argument('--request',type=Path,required=True);parser.add_argument('--expected-request-sha256',required=True)
    parser.add_argument('--execute',action='store_true');args=parser.parse_args()
    try:
        path=_relative(ROOT,args.request.as_posix(),'request')
        _need(path.is_relative_to(ROOT/'evidence/integration'),'DEFICIT_REQUEST_PATH_INVALID')
        _,raw=_snapshot(ROOT,path,2*1024**2,'request',True)
        print(json.dumps(run_deficit_guarded(ROOT,_json(raw),args.expected_request_sha256,execute=args.execute),ensure_ascii=True))
        return 0
    except Exception as exc:
        progress=getattr(exc,'progress',None);code=str(exc)
        result={'status':'DEFICIT_EXECUTION_FAILED' if progress else 'BLOCKED',
            'executed':None if progress else False,'execute_requested':args.execute,
            'execution_started':bool(progress),'execution_progress':progress,
            'issue':code if re.fullmatch('[A-Z_]{1,80}',code) else 'DEFICIT_LOCAL_OR_EXECUTION_FAILURE'}
        if isinstance(exc,DeficitLocalProofFailure) and exc.inventory_diagnostic is not None:
            result['inventory_diagnostic']=exc.inventory_diagnostic
        print(json.dumps(result))
        return 2


if __name__=='__main__':raise SystemExit(main())
