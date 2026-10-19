"""과거 원장을 보존하면서 여러 순차 수집 실행의 신규 예산을 공유한다."""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class CollectionLedger:
    """먼저 예약하고, 측정 가능한 정상 종료에 한해서만 현재 예약을 정산한다.

    비정상 중단의 pending 예약은 자동 환불하지 않는다. 원장 lock은 다른
    수집 프로세스와 경합하면 즉시 실패하며 잠긴 채 재시도하지 않는다.
    """
    def __init__(self, path, historical_paths, additional_budget=4 * 1024 ** 3, initial_metadata_charge=0, *, metadata_io=None):
        self.path = Path(path)
        self.historical_paths = [Path(p).resolve() for p in historical_paths]
        if not 1 <= additional_budget <= 4 * 1024 ** 3:
            raise ValueError("이번 신규 전역 예산은 최대 4GiB입니다")
        self.additional_budget = additional_budget
        if not 0 <= initial_metadata_charge <= additional_budget:
            raise ValueError("외부 조사 HTTP 본문 계측은 신규 예산 범위 안이어야 합니다")
        self.initial_metadata_charge = initial_metadata_charge
        self.metadata_io = metadata_io
        if metadata_io is not None:
            from .ledger_metadata_io import LedgerMetadataIO
            if type(metadata_io) is not LedgerMetadataIO:
                raise ValueError('LEDGER_METADATA_ADAPTER_INVALID')
            metadata_io.bind(self)

    @contextmanager
    def locked(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lock = self.path.with_suffix(".lock")
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        try:
            os.write(descriptor, str(os.getpid()).encode())
            yield
        finally:
            os.close(descriptor)
            lock.unlink()

    def _read(self):
        if self.metadata_io is not None:
            return self.metadata_io.read(self)
        if self.path.exists():
            state = json.loads(self.path.read_text(encoding="utf-8"))
            if state["additional_maximum_bytes"] != self.additional_budget:
                raise ValueError("기존 신규예산을 설정 변경으로 초기화할 수 없습니다")
            for item in state["historical_ledgers"]:
                if sha256(item["path"]) != item["sha256"]:
                    raise RuntimeError("과거 원장이 변경되어 수집을 중단합니다")
            return state
        historical = [{"path": str(p), "sha256": sha256(p)} for p in self.historical_paths]
        # 마지막 recovery 원장의 수치는 이전 원장을 이미 포함한다. 합산 중복 금지.
        latest = json.loads(self.historical_paths[-1].read_text(encoding="utf-8"))
        prior = latest["reserved_or_transferred_bytes_including_prior"]
        return {"version": 1, "historical_ledgers": historical, "historical_charged_bytes": prior,
                "additional_maximum_bytes": self.additional_budget, "new_charged_bytes": self.initial_metadata_charge,
                "external_research_metadata_body_bytes": self.initial_metadata_charge,
                "combined_maximum_bytes": prior + self.additional_budget, "batches": {},
                "rate_limit_active": False}

    def _save(self, state):
        if self.metadata_io is not None:
            return self.metadata_io.save(self, state)
        state["updated_at"] = datetime.now(timezone.utc).isoformat()
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(self.path)

    def snapshot(self):
        with self.locked():
            return self._read()

    def reserve(self, key, maximum, config_sha256):
        with self.locked():
            if self.metadata_io is not None:
                self.metadata_io.reserve_arguments(self, key, maximum, config_sha256)
            state = self._read()
            if state["rate_limit_active"]:
                raise RuntimeError("전역 HTTP429 회로가 열려 추가 요청을 중단합니다")
            if key in state["batches"]:
                old = state["batches"][key]
                if old["config_sha256"] != config_sha256:
                    raise RuntimeError("동일 batch 설정 변경으로 원장을 재사용할 수 없습니다")
                if old["status"] == "settled":
                    return False
                raise RuntimeError("미측정 중단 예약이 남아 있어 자동 재실행/환불하지 않습니다")
            if not 0 < maximum <= 2 * 1024 ** 3:
                raise ValueError("개별 batch 상한은 2GiB 이내입니다")
            if state["new_charged_bytes"] + maximum > self.additional_budget:
                raise ValueError("신규 전역 예산의 잔여량이 batch 예약보다 적습니다")
            state["new_charged_bytes"] += maximum
            state["batches"][key] = {"status": "pending", "reserved_bytes": maximum,
                "charged_bytes": maximum, "config_sha256": config_sha256}
            self._save(state)
            return True

    def settle(self, key, measured_or_reserved, report_path=None, rate_limit=None):
        with self.locked():
            if self.metadata_io is not None:
                self.metadata_io.settle_arguments(self, key, measured_or_reserved, report_path)
            state = self._read()
            batch = state["batches"][key]
            if batch["status"] != "pending":
                raise RuntimeError("이미 정산한 batch입니다")
            if not 0 <= measured_or_reserved <= batch["reserved_bytes"]:
                raise ValueError("정산값이 batch 예약 범위 밖입니다")
            state["new_charged_bytes"] -= batch["reserved_bytes"] - measured_or_reserved
            batch.update(status="settled", charged_bytes=measured_or_reserved, report_path=report_path)
            if rate_limit:
                state.update(rate_limit_active=True, last_rate_limit=rate_limit)
            self._save(state)
            return state
