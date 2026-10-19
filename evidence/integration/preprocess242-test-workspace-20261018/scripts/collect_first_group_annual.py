"""First Group 연차 수집을 세 작업으로 나누고 총 전송 예산을 보수적으로 분배한다."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
PROVINCES = {'south_sulawesi', 'gorontalo', 'southeast_sulawesi', 'banten', 'west_java', 'east_java'}
BANDS = ['blue', 'green', 'red', 'nir', 'swir16', 'swir22']


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def build_plan(config, output, additional_prior=0, workers=3):
    if {item['id'] for item in config['aois']} != PROVINCES or len(config['aois']) != 6:
        raise ValueError('사용자 지정 First Group 6개 주가 모두 필요합니다.')
    if not 1 <= workers <= 3:
        raise ValueError('동시 작업은 1~3개로 제한합니다.')
    if sorted(config['years']) != list(range(2020,2026)):
        raise ValueError('연차 범위는2020~2025년이어야 합니다.')
    maximum = int(config['max_total_bytes'])
    prior = int(config.get('prior_download_budget_bytes',0)) + int(additional_prior)
    if prior < 0 or maximum > 2*1024**3 or maximum <= prior:
        raise ValueError('기존 자료를 차감한2GiB이하의 잔여 예산이 필요합니다.')
    allowance = (maximum-prior)//workers
    if allowance < 65536:
        raise ValueError('작업별 잔여 예산이 부족합니다.')
    tasks = []
    for i in range(workers):
        chunk = copy.deepcopy(config)
        chunk.update(aois=config['aois'][i::workers], bands=BANDS,
                     prior_download_budget_bytes=prior, max_total_bytes=prior+allowance,
                     description='First Group 연차6밴드 수집:10m기준 SWIR bilinear, 라벨/SCL nearest')
        tasks.append({'id':f'chunk-{i+1:02d}', 'config':chunk,
                      'config_path':str(output/f'chunk-{i+1:02d}.json'),
                      'output':str(output/f'chunk-{i+1:02d}'),
                      'reserved_transfer_allowance':allowance})
    return {'schema_version':1, 'executed':False, 'prior_budget_bytes':prior,
            'maximum_total_bytes':maximum, 'workers':workers,'years':list(range(2020,2026)),
            'expected_province_year_cells':36,'bands':BANDS,'tasks':tasks,
            'budget_proof':'prior + sum(worker allowances) <= maximum; 실패/중단 예약도 사용량으로 보존',
            'learning_ready':False, 'target_verified_patches':[1000,3000],
            'coverage_note':'주별 대표점256창36개로 주전체나1000패치를 확보했다고 판단하지 않는다.'}


def usage(output):
    path = output/'window-state.json'
    return int(read_json(path).get('http_body_bytes',0)) if path.exists() else 0


def rate_limit_evidence(report, state=None):
    # 작업 종료 전에도 원장의 첫429를 읽어 다른 병렬 요청을 멈춘다.
    breaker=(state or {}).get('last_rate_limit') or (report or {}).get('batch_circuit_breaker')
    if breaker:
        return {**breaker,'http_status':429}
    for row in (report or {}).get('scenes',[]):
        error=row.get('error',{})
        if error.get('http_status')==429:
            return {'aoi':row.get('aoi'),'year':row.get('year'),'retry_after':error.get('retry_after'),
                    'request_host':error.get('request_host') or error.get('server_host'),'http_status':429}
    return None


def validate_plan(plan, output):
    """재개할 때 저장 계획과 작업 설정이 서로 같은 예산을 가리키는지 확인한다."""
    tasks=plan.get('tasks',[])
    prior=plan.get('prior_budget_bytes',-1)
    maximum=plan.get('maximum_total_bytes',0)
    if not 1<=len(tasks)<=3 or not 0<=prior<maximum<=2*1024**3:
        raise ValueError('저장 계획의 총 예산/작업 수가 올바르지 않습니다.')
    allowance_sum=0; ids=[]
    for i,task in enumerate(tasks,1):
        config=task['config']; allowance=task['reserved_transfer_allowance']
        if allowance<=0 or config['prior_download_budget_bytes']!=prior or config['max_total_bytes']!=prior+allowance:
            raise ValueError('작업별 예산 예약이 일치하지 않습니다.')
        if Path(task['config_path']).resolve()!=output/f'chunk-{i:02d}.json' or Path(task['output']).resolve()!=output/f'chunk-{i:02d}':
            raise ValueError('저장 계획의 작업 경로가 올바르지 않습니다.')
        if read_json(task['config_path'])!=config or config['bands']!=BANDS or sorted(config['years'])!=list(range(2020,2026)):
            raise ValueError('작업 설정이 고정된 연차/밴드 계획과 다릅니다.')
        allowance_sum+=allowance
        ids.extend(a['id'] for a in config['aois'])
    if prior+allowance_sum>maximum or len(ids)!=6 or set(ids)!=PROVINCES:
        raise ValueError('대상 주 또는 병렬 작업의 총 예산이 맞지 않습니다.')


def main():
    if hasattr(sys.stdout,'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,default=ROOT/'configs/first-group.collection.json')
    parser.add_argument('--output',type=Path,default=ROOT/'data/first-group-annual')
    parser.add_argument('--previous-window-state',type=Path,default=ROOT/'data/first-group-2021/window-state.json')
    parser.add_argument('--workers',type=int,default=3)
    parser.add_argument('--execute',action='store_true')
    args=parser.parse_args()
    out=args.output.resolve()
    out.mkdir(parents=True,exist_ok=True)
    plan_path=out/'run-plan.json'
    # 재실행은 처음 정한 예산/설정을 유지하며 worker별 SHA 재개 검증을 사용한다.
    if plan_path.exists():
        plan=read_json(plan_path)
        if not plan.get('tasks') or plan.get('expected_province_year_cells')!=36:
            raise ValueError('수집 계획 형식을 확인하십시오.')
        current_prior=int(read_json(args.config).get('prior_download_budget_bytes',0))+(usage(args.previous_window_state.parent) if args.previous_window_state.exists() else 0)
        if current_prior!=plan['prior_budget_bytes']:
            if any((Path(t['output'])/'window-state.json').exists() for t in plan['tasks']):
                raise ValueError('기존 작업 이후 외부 수집 예산이 바뀌었습니다. 사용량을 합산한 새 계획이 필요합니다.')
            plan=build_plan(read_json(args.config),out,current_prior-int(read_json(args.config).get('prior_download_budget_bytes',0)),args.workers)
            plan['source_config_sha256']=hashlib.sha256(args.config.read_bytes()).hexdigest()
            for task in plan['tasks']:
                Path(task['config_path']).write_text(json.dumps(task['config'],ensure_ascii=False,indent=2),encoding='utf-8')
            plan_path.write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
    else:
        prior=usage(args.previous_window_state.parent) if args.previous_window_state.exists() else 0
        plan=build_plan(read_json(args.config),out,prior,args.workers)
        plan['source_config_sha256']=hashlib.sha256(args.config.read_bytes()).hexdigest()
        for task in plan['tasks']:
            Path(task['config_path']).write_text(json.dumps(task['config'],ensure_ascii=False,indent=2),encoding='utf-8')
        plan_path.write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
    if not args.execute:
        print(json.dumps({'status':'planned','cells':36,'workers':plan['workers'],'bands':plan['bands'],
                          'maximum_total_bytes':plan['maximum_total_bytes'],'prior_budget_bytes':plan['prior_budget_bytes']},ensure_ascii=False))
        return 0
    validate_plan(plan,out)
    processes=[]; handles=[]; stopped_for_rate_limit=None
    try:
        for task in plan['tasks']:
            log=(out/f"{task['id']}.log").open('ab')
            handles.append(log)
            command=[sys.executable,str(ROOT/'scripts/collect_samples.py'),'--config',task['config_path'],'--execute','--output',task['output']]
            proc=subprocess.Popen(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,
                                  creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            processes.append((task,proc))
        print(json.dumps({'status':'running','workers':len(processes),'maximum_total_bytes':plan['maximum_total_bytes']},ensure_ascii=False),flush=True)
        previous=None
        while any(proc.poll() is None for _,proc in processes):
            progress=[]
            for task,proc in processes:
                report_path=Path(task['output'])/'annual-window-report.json'
                # 작업자가 JSON을 저장 중이면 다음 관찰까지 미확인으로 두고 실행을 중단하지 않는다.
                try:
                    report=read_json(report_path) if report_path.exists() else None
                    state_path=Path(task['output'])/'window-state.json'
                    state=read_json(state_path) if state_path.exists() else None
                    used=usage(Path(task['output']))
                except (json.JSONDecodeError,OSError):
                    report=None; state=None; used=None
                stopped_for_rate_limit=stopped_for_rate_limit or rate_limit_evidence(report,state)
                progress.append({'id':task['id'],'downloaded_windows':sum(row.get('status')=='rgb_window_downloaded' for row in report.get('scenes',[])) if report else None,
                                 'reserved_or_transferred_bytes':used,'exit_code':proc.poll()})
            serialized=json.dumps(progress,ensure_ascii=False)
            if serialized!=previous:
                print(serialized,flush=True); previous=serialized
            if stopped_for_rate_limit:
                # 한 작업에서429가 확인되면 다른 작업도 중단하여 제공자 제한을 존중한다.
                for _,proc in processes:
                    if proc.poll() is None:
                        proc.terminate()
                for _,proc in processes:
                    proc.wait(timeout=15)
                break
            time.sleep(3)
        total=plan['prior_budget_bytes']
        for task,_ in processes:
            try:
                total+=usage(Path(task['output']))
            except (json.JSONDecodeError,OSError):
                # 중단 시 원장이 읽히지 않으면 사용량을0으로 낮추지 않고 전체 예약으로 잡는다.
                total+=task['reserved_transfer_allowance']
        manifests=[str(Path(task['output'])/'annual-window-report.json') for task,_ in processes]
        result={'status':'finished','executed':True,'exit_codes':{task['id']:proc.returncode for task,proc in processes},
                'reserved_or_transferred_bytes_including_prior':total,'maximum_total_bytes':plan['maximum_total_bytes'],
                'budget_within_limit':total<=plan['maximum_total_bytes'],'manifests':manifests,'learning_ready':False}
        result['stopped_for_rate_limit']=stopped_for_rate_limit
        (out/'run-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(result,ensure_ascii=False),flush=True)
        return 0 if result['budget_within_limit'] and all(proc.returncode==0 for _,proc in processes) else 2
    except BaseException:
        # 총괄 처리가 중단되면 자식 수집 프로세스도 종료해 계속 다운로드하지 않게 한다.
        for _,proc in processes:
            if proc.poll() is None:
                proc.terminate()
        raise
    finally:
        for handle in handles:
            handle.close()


if __name__=='__main__':
    raise SystemExit(main())
