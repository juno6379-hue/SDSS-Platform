"""원본을 보존하는 실험용 split 복구 계획. 기본 출력은 evidence JSON 하나다."""
import argparse
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.app.ml.split_planning import plan_split_repair,write_plan


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--expected-sha256',required=True)
    parser.add_argument('--plan',type=Path,required=True,help='고정 province_splits가 있는 실험 계획')
    parser.add_argument('--readiness',type=Path)
    parser.add_argument('--readiness-sha256')
    parser.add_argument('--data-root',type=Path,default=ROOT/'data')
    parser.add_argument('--output',type=Path,default=ROOT/'evidence/integration/ml-split-repair-plan-20261017.json')
    parser.add_argument('--derived-manifest',type=Path,help='지정할 때만 별도 실험용 후보 manifest도 생성; readiness/학습 실행 없음')
    args=parser.parse_args()
    policy=json.loads(args.plan.read_text(encoding='utf-8'))
    report=plan_split_repair(args.manifest,args.expected_sha256,province_splits=policy['province_splits'],
                             readiness_path=args.readiness,readiness_sha256=args.readiness_sha256,data_root=args.data_root)
    write_plan(report,args.output,derived_manifest=args.derived_manifest)
    print(json.dumps({'status':report['status'],'conflict_groups':len(report['conflicts']),
                      'excluded_rows':len(report['excluded_row_indexes']),'projected_after':report['projected_after']['eligible_patches_by_split'],
                      'ready_for_training':False,'training_executed':False}))


if __name__=='__main__':
    main()
