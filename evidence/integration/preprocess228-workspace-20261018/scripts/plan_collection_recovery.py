"""중단 수집 복구계획을 생성·검증한다. 출력은 evidence 아래 새 파일로만 제한한다."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.data.recovery import build_recovery_plan, validate_recovery_plan


def write_new_evidence(path, value):
    """같은 계획은 재사용하고 내용이 다른 기존 증거를 덮어쓰지 않는다."""
    evidence_root = (ROOT / "evidence/integration/collection-recovery-plans").resolve()
    path = path.resolve()
    path.relative_to(evidence_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if json.loads(path.read_text(encoding="utf-8")) != value:
            raise ValueError("동일 경로에 다른 증거가 있어 덮어쓰지 않습니다")
        return False
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
    return True


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=ROOT / "data")
    parser.add_argument("--validate", type=Path, help="기존 evidence 복구계획을 현재 snapshot과 대조")
    args = parser.parse_args(argv)
    evidence_root = ROOT / "evidence/integration/collection-recovery-plans"
    if args.validate:
        source = args.validate.resolve()
        source.relative_to(evidence_root.resolve())
        plan = json.loads(source.read_text(encoding="utf-8"))
        result = validate_recovery_plan(args.data_root, plan)
        result["assessed_at"] = datetime.now(timezone.utc).isoformat()
        output = evidence_root / ("validation-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json")
        write_new_evidence(output, result)
        print(json.dumps(dict(result, evidence=str(output)), ensure_ascii=True))
        return 0 if result["valid_for_review"] else 2
    plan = build_recovery_plan(args.data_root)
    output = evidence_root / (plan["plan_id"] + ".json")
    created = write_new_evidence(output, plan)
    print(json.dumps({"plan_id": plan["plan_id"], "evidence": str(output), "created": created,
        "status": plan["status"], "execution_authorized": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
