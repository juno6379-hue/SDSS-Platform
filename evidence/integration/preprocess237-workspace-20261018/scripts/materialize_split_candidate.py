"""Create a new evidence-only planned split candidate and metadata roundtrip receipt."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.app.ml.candidate_materialization import materialize_split_candidate,INPUT_ROLES


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root',type=Path,default=ROOT/'data')
    for role in INPUT_ROLES:
        flag=role.replace('_','-');parser.add_argument('--'+flag,type=Path,required=True);parser.add_argument('--'+flag+'-sha256',required=True)
    parser.add_argument('--output-dir',type=Path,required=True,help='New directory under project evidence; existing parent required')
    args=parser.parse_args()
    try:
        paths={k:getattr(args,k).absolute() for k in INPUT_ROLES};pins={k:getattr(args,k+'_sha256') for k in INPUT_ROLES}
        receipt=materialize_split_candidate(args.data_root,paths,pins,args.output_dir.absolute(),evidence_root=ROOT/'evidence')
        print(json.dumps({k:receipt[k] for k in ['status','candidate_status','readiness_status','source_row_count','candidate_row_count','excluded_source_row_count','projected_after','ready_for_training','registry_called']},ensure_ascii=True,allow_nan=False));return 0
    except (ValueError,OSError,TypeError,KeyError,IndexError,AttributeError,RecursionError,OverflowError) as exc:
        print(('Candidate materialization failed: '+str(exc)).encode('ascii',errors='backslashreplace').decode('ascii'),file=sys.stderr);return 1

if __name__=='__main__':raise SystemExit(main())
