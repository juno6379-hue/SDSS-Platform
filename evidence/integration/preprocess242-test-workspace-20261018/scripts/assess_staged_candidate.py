"""고정 staging 후보와 기존 동일 정책으로 QA만 실행한다. execute/resume 옵션 없음."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.app.ml.candidate_readiness_qa import assess_staged_candidate,ROLES


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--data-root',type=Path,default=ROOT/'data')
    for role in ROLES:
        flag=role.replace('_','-');parser.add_argument('--'+flag,type=Path,required=True);parser.add_argument('--'+flag+'-sha256',required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    try:
        paths={r:getattr(args,r).absolute() for r in ROLES};pins={r:getattr(args,r+'_sha256') for r in ROLES}
        receipt=assess_staged_candidate(args.data_root,paths,pins,args.output_dir.absolute())
        print(json.dumps({'status':receipt['status'],'observed_readiness_status':receipt['observed_readiness_status'],'observed_gate_ready_for_training':receipt['observed_gate_ready_for_training'],'blocker_count':len(receipt['saved_blockers']),'patch_counts_by_split':receipt['patch_counts_by_split'],'connectivity_capture_status':receipt['connectivity_capture_status'],'execution_authorized':False,'training_executed':False},ensure_ascii=True,allow_nan=False));return 0
    except (ValueError,OSError,TypeError,KeyError,IndexError,AttributeError,RecursionError,OverflowError) as exc:
        print(('Candidate readiness QA failed: '+str(exc)).encode('ascii',errors='backslashreplace').decode('ascii'),file=sys.stderr);return 1

if __name__=='__main__':raise SystemExit(main())
