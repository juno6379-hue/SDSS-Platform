"""검증된 evidence 후보 JSON을 같은 바이트로 새 DATA QA staging 경로에 복사한다."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.app.ml.candidate_staging import stage_split_candidate,INPUT_ROLES


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root',type=Path,default=ROOT/'data');parser.add_argument('--package-dir',type=Path,required=True);parser.add_argument('--receipt-sha256',required=True)
    for role in INPUT_ROLES:parser.add_argument('--'+role.replace('_','-')+'-sha256',required=True)
    parser.add_argument('--output-dir',type=Path,required=True,help='DATA 안의 새 디렉터리. 부모는 이미 존재해야 함')
    args=parser.parse_args()
    try:
        pins={r:getattr(args,r+'_sha256') for r in INPUT_ROLES}
        result=stage_split_candidate(args.data_root,args.package_dir.absolute(),args.receipt_sha256,pins,args.output_dir.absolute(),evidence_root=ROOT/'evidence')
        print(json.dumps({k:result[k] for k in ['status','next_step','qa_status','candidate_row_count','projected_after','ready_for_training','registered']},ensure_ascii=True,allow_nan=False));return 0
    except (ValueError,OSError,TypeError,KeyError,IndexError,AttributeError,RecursionError,OverflowError) as exc:
        print(('Candidate staging failed: '+str(exc)).encode('ascii',errors='backslashreplace').decode('ascii'),file=sys.stderr);return 1

if __name__=='__main__':raise SystemExit(main())
