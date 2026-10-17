"""Trace an explicit literal token in two pinned JSON snapshots; no assess or pixels."""
import argparse
import json
import re
import sys
from pathlib import Path,PureWindowsPath
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.app.data.readiness_connectivity_lineage import inspect_readiness_connectivity_lineage
from backend.app.data.recovery_terminal import _confined


def _output_path(value,data_root,inputs):
    text=str(value);windows=PureWindowsPath(text)
    if text.startswith(('\\\\','//')) or ':' in (text[2:] if re.match(r'^[A-Za-z]:[\\/]',text) else text):raise ValueError('Remote/ADS diagnostic output prohibited')
    devices={'CON','PRN','AUX','NUL','CONIN$','CONOUT$'}|{prefix+n for prefix in ('COM','LPT') for n in '123456789¹²³'}
    if any(part not in (windows.anchor,'.','..') and (part.rstrip(' .')!=part or part.split('.')[0].strip(' .').upper() in devices) for part in windows.parts):raise ValueError('Reserved or ambiguous diagnostic output path')
    logical=Path(value);logical=logical if logical.is_absolute() else Path.cwd()/logical
    if logical.is_symlink() or logical.exists():raise ValueError('New evidence file required')
    target=_confined((ROOT/'evidence').resolve(),logical)
    if target.is_relative_to(data_root.resolve()) or target in {Path(p).resolve() for p in inputs}:raise ValueError('Evidence must be outside DATA and distinct from inputs')
    return logical,target,logical.parent.resolve()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root',type=Path,default=ROOT/'data')
    parser.add_argument('--report',type=Path)
    parser.add_argument('--expected-report-sha256',required=True)
    parser.add_argument('--expected-manifest-sha256',required=True)
    parser.add_argument('--token',required=True)
    parser.add_argument('--max-candidates',type=int,default=1000)
    parser.add_argument('--max-members',type=int,default=2000)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    try:
        report=args.report.absolute() if args.report else args.data_root.absolute()/'first-group/readiness-connectivity-20261017.json'
        if args.output:logical,target,parent=_output_path(args.output,args.data_root,[report,args.data_root/'first-group-training-esri-v1/annual-window-report.json'])
        result=inspect_readiness_connectivity_lineage(args.data_root,args.expected_report_sha256,args.expected_manifest_sha256,args.token,report_path=report,max_candidates=args.max_candidates,max_members=args.max_members)
        if args.output:
            if logical.resolve()!=target or logical.parent.resolve()!=parent or logical.is_symlink() or logical.exists():raise ValueError('Evidence target changed during inspection')
            target.parent.mkdir(parents=True,exist_ok=True)
            if logical.resolve()!=target or logical.parent.resolve()!=parent:raise ValueError('Evidence parent changed during inspection')
            with target.open('x',encoding='utf-8') as stream:json.dump(result,stream,ensure_ascii=False,indent=2,allow_nan=False);stream.write('\n')
        print(json.dumps({key:result[key] for key in ['status','lineage_status','report_active_token_member_count','raw_active_token_member_count','candidate_link_count_total','unique_candidate_raw_row_count','output_truncated','exact_row_binding_verified']},ensure_ascii=True,allow_nan=False));return 0
    except (ValueError,OSError,TypeError,KeyError,OverflowError,RecursionError) as exc:
        print(('Connectivity lineage inspection failed: '+str(exc)).encode('ascii',errors='backslashreplace').decode('ascii'),file=sys.stderr);return 1


if __name__=='__main__':raise SystemExit(main())
