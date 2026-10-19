# 333. 원장 metadata_io 어댑터 — 공유 코드 적용 및 회귀 검증

상태: **APPLIED_TO_MAIN_VERIFIED**. 332 동결 결과물(`freeze332.json`)을 메인 코드베이스에 반영하고, 신규 단위 시험 45건 및 기존 의존 시험 9개 모듈 147건을 모두 통과했습니다.

## 1. 개요 및 반영 내역

332 격리 작업공간(`target332-workspace-20261019`)에서 독립 정적 검토를 거쳐 동결된 4개 파일을 메인 브랜치에 안전하게 반영했습니다.
- 원본 `backend/app/data/budget.py`는 바이트 검증 후 `archive/budget.py.pre333`로 영구 보존했습니다.
- 신규 적용 파일:
  - `backend/app/data/ledger_metadata_io.py`
  - `backend/app/data/budget.py` (수정 반영)
  - `tests/test_ledger_metadata332.py`
  - `tests/fixtures/budget332_legacy.py`

## 2. 시험 및 검증 결과

1. **신규 단위 시험**: `test_ledger_metadata332.py` (45건 전부 PASS, 8.918초)
2. **기존 의존 모듈 회귀 시험**: 9개 모듈 147건 전부 PASS (44.906초)
   - `test_collect_deficit_guarded`
   - `test_collect_targeted_bare`
   - `test_collection_continue_pending`
   - `test_data_parallel`
   - `test_data_training_grid`
   - `test_deficit_candidate_guard`
   - `test_deficit_metadata_selection260`
   - `test_targeted_inventory_profile232`
   - `test_training_priority`
3. 합계 **192건 전부 통과 (FAIL=0, SKIP=0, ERROR=0)**

## 3. 한계 및 안전 경계 유지

- 실제 운영 원장(`data/first-group-training-budget/global-ledger.json`) 직접 수정 0
- 외부 네트워크 HTTP 요청 0
- 170 실제 수집기 worker 연결 0
- 기존 2023년 반텐·서자바 2개 중단 배치 예약분(136,314,880B) 보존 상태 불변
- 본 적용으로 원장 I/O의 8MiB 사전 캡 및 원자적 쓰기 어댑터가 메인에 준비되었으며, 후속 수집기 파이프라인(328 연결)에서 호출할 수 있게 되었습니다.
