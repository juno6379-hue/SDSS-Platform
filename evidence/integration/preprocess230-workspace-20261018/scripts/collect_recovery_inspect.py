"""네트워크·원장 변경 없이 중단 수집의 별도 복구 조사 증거를 생성한다."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.data.recovery import inspect_recovery


def main():
    result = inspect_recovery(ROOT / "data")
    result["snapshot_at"] = datetime.now(timezone.utc).isoformat()
    output = ROOT / "evidence/integration" / ("collection-recovery-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json")
    output.parent.mkdir(parents=True, exist_ok=True)
    # 이전 증거를 교체하지 않는다.
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    print(json.dumps({"evidence": str(output), "pending": len(result["pending_batches"]),
        "automatic_resume_allowed": result["automatic_resume_allowed"]}))


if __name__ == "__main__":
    main()
