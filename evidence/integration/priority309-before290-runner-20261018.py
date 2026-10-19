"""290 준비 runner. Root exact GO 없이는 CLI/QA를 실행하지 않는다."""
import argparse
import contextlib
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
PREPARATION_SHA = 'e9260f8ee5c81a63a9a8221e24b439f5e7c0b2b5e5955129be6b0cf169ace4ef'
PREPARATION = ROOT/'evidence/integration/priority290-preparation-20261018.json'


def need(value):
    if not value:
        raise ValueError('QA290_EXPLICIT_CONTRACT_INVALID')


def file_pin(path, maximum):
    before = path.stat()
    need(path.is_file() and not path.is_symlink() and before.st_size <= maximum)
    h = hashlib.sha256(); count = 0
    with path.open('rb') as stream:
        while True:
            block = stream.read(65536)
            if not block: break
            count += len(block); need(count <= maximum and count <= before.st_size); h.update(block)
    after = path.stat()
    need((before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns) ==
         (after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns) and count == before.st_size)
    return h.hexdigest()


def main():
    wrapper_start = time.monotonic()
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('--approval', type=Path, required=True)
    args = parser.parse_args()
    # 고정 준비 JSON만 초기 bootstrap한다. 실제 읽은 bytes는 아래 동일 budget에 반영한다.
    need(file_pin(PREPARATION,2*1024**2) == PREPARATION_SHA)
    with PREPARATION.open('rb') as stream:
        raw = stream.read(2*1024**2+1)
    need(len(raw)<=2*1024**2)
    need(hashlib.sha256(raw).hexdigest() == PREPARATION_SHA)
    plan = json.loads(raw)
    for rel, pin in plan['code_pins'].items():
        path = ROOT/rel
        need(path.stat().st_size == pin['bytes'] and file_pin(path,2*1024**2) == pin['sha256'])
    sys.path[:0] = [str(ROOT),str(ROOT/'.runtime'),str(ROOT/'backend')]
    from backend.app.ml import manifest_resource_profile as profile
    need(dict(profile.DESCRIPTOR) == plan['manifest_profile'] and profile.DIGEST == plan['manifest_profile_sha256'])
    need(profile.active() is None)
    with profile.scope(plan['manifest_profile']['name']) as budget:
        # file_pin + read_bytes의 준비 JSON 2회 실제 읽기를 모두 계산한다.
        profile.charge(2*len(raw))
        approval = args.approval
        need(approval.is_absolute() and approval.resolve().is_relative_to(ROOT/'evidence/integration'))
        go, go_sha, _ = profile.read_metadata(approval,'local_plan')
        expected = {'kind':'PINNED_CANDIDATE_QA_290_GO','approved':True,'run_id':plan['run_id'],
            'preparation_sha256':PREPARATION_SHA,'native_audit_sha256':plan['native_audit']['sha256'],
            'source_sha256':plan['source']['sha256'],'source_bytes':plan['source']['bytes'],
            'manifest_profile':dict(profile.MARKER),'no_active_collector':True,'execution_lock_absent':True}
        need(type(go) is dict and set(go) == set(expected) and go == expected and
             all(go[k] is True for k in ('approved','no_active_collector','execution_lock_absent')))
        need(not (ROOT/plan['lock_path']).exists() and not (ROOT/plan['lock_path']).is_symlink())
        need(profile.bounded_json_digest(ROOT/plan['native_audit']['path'],'readiness') == plan['native_audit']['sha256'])
        source = ROOT/plan['source']['path']
        need(source.is_file() and not source.is_symlink() and source.stat().st_size == plan['source']['bytes'] and
             source.stat().st_size <= profile.DESCRIPTOR['manifest_bytes'])
        paths = {k:ROOT/v for k,v in plan['paths'].items()}
        need(all(not p.exists() and not p.is_symlink() for p in paths.values()))
        protected = {p:profile.bounded_json_digest(ROOT/p,'pointer') for p in plan['protected_paths']}
        need(protected == plan['protected_expected'])
        def write_json(path, value):
            payload = (json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf-8')
            profile.write_new_json_bytes(path,payload,'local_plan')
        argv = ['--data-root',str(ROOT/'data'),'--source',str(source),
                '--source-sha256',plan['source']['sha256'],'--policy',str(ROOT/plan['policy']['path']),
                '--policy-sha256',plan['policy']['sha256'],'--run-id',plan['run_id'],
                '--manifest-profile',plan['manifest_profile']['name']]
        write_json(paths['launch'],{'status':'QA290_LAUNCHED','at':datetime.now(timezone.utc).isoformat(),
            'pid':os.getpid(),'argv':['scripts/prepare_priority_candidate164.py',*argv],
            'approval_sha256':go_sha,'preparation_sha256':PREPARATION_SHA,'native_audit_sha256':plan['native_audit']['sha256'],
            'source_pin_expected':plan['source'],'source_pin_direct_check':'164_BEFORE_OUTPUT_AND_AFTER_EACH_QA',
            'protected_before':protected,'manifest_profile':dict(profile.MARKER),'code_pins':plan['code_pins']})
        print(json.dumps({'status':'QA290_STARTED','pid':os.getpid(),'run_id':plan['run_id']}),flush=True)
        from scripts.prepare_priority_candidate164 import main as cli_main
        start = time.monotonic(); exit_code = 2; status = 'CLI_INCOMPLETE'; summary = None
        class MeteredLog:
            def __init__(self, stream): self.stream=stream; self.count=0
            def write(self, value):
                block=value.encode('utf-8'); need(self.count+len(block)<=4*1024**2)
                profile.write_measured(self.stream,block); self.count+=len(block); return len(value)
            def flush(self): self.stream.flush()
        try:
            with paths['log'].open('xb',buffering=0) as stream:
                logger=MeteredLog(stream)
                with contextlib.redirect_stdout(logger),contextlib.redirect_stderr(logger):
                    # 같은 ContextVar/budget에서 기존 CLI main을 정확히 한 번 호출한다.
                    exit_code=cli_main(argv)
            need(profile.active() is budget)
            if exit_code == 0:
                summary,_,_ = profile.read_metadata(paths['evidence']/'summary.json','saved_plan')
                need(summary['status']=='PINNED_CANDIDATE_QA_COMPLETED' and
                     summary['manifest_profile']==dict(profile.MARKER) and summary['file_sha_mismatches']==0 and
                     summary['source_sha256']==plan['source']['sha256'] and summary['training_executed'] is False)
                for rel in ('candidate-package/receipt.json',):
                    receipt,_,_=profile.read_metadata(paths['evidence']/rel,'receipt')
                    need(receipt['schema_version']==2 and receipt['manifest_profile']==dict(profile.MARKER))
                for rel in ('stage/staging-receipt.json','qa/qa-receipt.json'):
                    receipt,_,_=profile.read_metadata(paths['work']/rel,'receipt')
                    need(receipt['schema_version']==2 and receipt['manifest_profile']==dict(profile.MARKER))
                status='PINNED_CANDIDATE_QA_COMPLETED'
        except Exception:
            exit_code=2;status='QA290_INCOMPLETE_PARTIAL_PRESERVED'
        protected_after={p:profile.bounded_json_digest(ROOT/p,'pointer') for p in protected}
        need(protected_after==protected)
        for rel,pin in plan['code_pins'].items():need(file_pin(ROOT/rel,2*1024**2)==pin['sha256'])
        terminal={'status':status,'at':datetime.now(timezone.utc).isoformat(),'pid':os.getpid(),'exit_code':exit_code,
            'actual_wall_seconds':round(time.monotonic()-wrapper_start,3),
            'cli_and_postcheck_wall_seconds':round(time.monotonic()-start,3),
            'source_pin_expected':plan['source']['sha256'],
            'protected_before':protected,'protected_after':protected_after,'manifest_profile':dict(profile.MARKER),
            'resource_usage_before_terminal_write':{'read_bytes':budget.reads,'write_bytes':budget.writes,
                'json_io_bytes':budget.bytes,'maximum_bytes':budget.maximum},'rss_observed':False,
            'automatic_retry_allowed':False,'partial_outputs_preserved':True,'published':False,'training_executed':False}
        if summary is not None:
            terminal['candidate_eligible']=summary['candidate_eligible']
            terminal['candidate_blockers']=summary['candidate_blockers']
        write_json(paths['terminal'],terminal)
        print(json.dumps({'status':status,'exit_code':exit_code,'actual_wall_seconds':terminal['actual_wall_seconds']}),flush=True)
        return exit_code


if __name__=='__main__':
    try:
        raise SystemExit(main())
    except Exception:
        print(json.dumps({'status':'QA290_WRAPPER_INCOMPLETE','partial_outputs_preserved':True,
                          'automatic_retry_allowed':False}),file=sys.stderr)
        raise SystemExit(2)
