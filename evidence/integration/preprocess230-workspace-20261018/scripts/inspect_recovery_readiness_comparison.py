"""Compare pinned saved readiness and physical corner JSON snapshots without reassessment."""
import argparse
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.app.data.recovery_readiness_comparison import inspect_recovery_readiness_comparison


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root',type=Path,default=ROOT/'data')
    parser.add_argument('--readiness',type=Path)
    parser.add_argument('--expected-manifest-sha256',required=True)
    parser.add_argument('--expected-readiness-sha256',required=True)
    parser.add_argument('--corner-report',type=Path,required=True)
    parser.add_argument('--expected-corner-sha256',required=True)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    try:
        if args.output:
            output=args.output.resolve()
            inputs=[args.data_root/'first-group-training-esri-v1/annual-window-report.json',args.readiness or args.data_root/'first-group/readiness-resume-20261017.json',args.corner_report]
            if not output.is_relative_to((ROOT/'evidence').resolve()) or output.exists() or output.is_relative_to(args.data_root.resolve()) or output in [p.resolve() for p in inputs]:
                raise ValueError('Output must be a new file under project evidence, outside inspected data and distinct from all inputs')
        result=inspect_recovery_readiness_comparison(args.data_root,args.expected_manifest_sha256,args.expected_readiness_sha256,args.corner_report.resolve(),args.expected_corner_sha256,readiness_path=args.readiness.resolve() if args.readiness else None)
        if args.output:
            output.parent.mkdir(parents=True,exist_ok=True)
            with output.open('x',encoding='utf-8') as stream:
                json.dump(result,stream,ensure_ascii=False,indent=2,allow_nan=False);stream.write('\n')
        print(json.dumps(result,ensure_ascii=True,indent=2,allow_nan=False));return 0
    except (ValueError,OSError,TypeError,KeyError,RecursionError,OverflowError) as exc:
        print(('Readiness comparison failed: '+str(exc)).encode('ascii',errors='backslashreplace').decode('ascii'),file=sys.stderr);return 1


if __name__=='__main__':raise SystemExit(main())
