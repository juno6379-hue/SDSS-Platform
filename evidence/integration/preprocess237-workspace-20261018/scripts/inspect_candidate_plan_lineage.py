"""Read-only pinned plan/current identity reference package; never creates a candidate."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.app.ml.candidate_plan_lineage import inspect_candidate_plan_lineage,NAMES
from scripts.inspect_readiness_connectivity_lineage import _output_path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root',type=Path,default=ROOT/'data')
    for name in NAMES:
        parser.add_argument('--'+name.replace('_','-'),type=Path,required=True)
        parser.add_argument('--'+name.replace('_','-')+'-sha256',required=True)
    parser.add_argument('--token',required=True)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    try:
        paths={k:getattr(args,k).absolute() for k in NAMES};pins={k:getattr(args,k+'_sha256') for k in NAMES}
        if args.output:logical,target,parent=_output_path(args.output,args.data_root,paths.values())
        result=inspect_candidate_plan_lineage(args.data_root,paths,pins,token=args.token,evidence_root=ROOT/'evidence')
        if args.output:
            if logical.resolve()!=target or logical.parent.resolve()!=parent or logical.is_symlink() or logical.exists():raise ValueError('New evidence path changed or exists')
            target.parent.mkdir(parents=True,exist_ok=True)
            if logical.resolve()!=target or logical.parent.resolve()!=parent:raise ValueError('Evidence parent changed')
            with target.open('x',encoding='utf-8') as stream:json.dump(result,stream,ensure_ascii=False,indent=2,allow_nan=False);stream.write('\n')
        print(json.dumps(result if not args.output else {k:result[k] for k in ['status','readiness_status','pin_validation','source_row_count','excluded_source_row_count','projected_after','current_query','ready_for_training']},ensure_ascii=True,allow_nan=False));return 0
    except (ValueError,OSError,TypeError,KeyError,OverflowError,RecursionError) as exc:
        print(('Candidate plan reference failed: '+str(exc)).encode('ascii',errors='backslashreplace').decode('ascii'),file=sys.stderr);return 1

if __name__=='__main__':raise SystemExit(main())
