# 171 — 병렬 예약 실패 뒤 이미 시작한 작업의 중앙 finalize 보존

상태: `TESTED_SYNTHETIC`. 기존 `backend/app/data/parallel.py`의 `run_two_workers`를 수정했다. 이 단위는 collector·CLI170·물리 상한·운영 원장·실제 수집을 변경하거나 재시작하지 않는다.

## 문제와 재현

기존 실행기는 최대2개 작업을 제출한다. 첫 worker를 이미 제출한 뒤 두 번째 `reserve`가 FileExistsError 등 ValueError 이외 예외를 내면, ThreadPoolExecutor는 첫 worker의 종료까지 기다리지만 그 결과를 중앙 `finalize`에 전달하지 않고 예외를 반환했다. worker가 원격 처리를 끝냈어도 중앙 정산·manifest 등록이 누락될 수 있었다.

Root 요청에 따른 독립 재현은 실제 기존 `run_two_workers`와 메모리 가짜 작업2개로 확인했다. 순서는 `reserve:first → work_enter:first → reserve:second/FileExistsError → work_finished:first`였고 **finalize_count=0**, 소요0.078초였다. 증거는 `evidence/integration/targeted170-reserve-repro-20261018.py/.json/.log`다. 원장·collector·네트워크를 호출하지 않았다. 당시 실제 표적 실행은 최대1개 작업이므로 이 재현을 그 운영 실행에 실제 발생한 사고로 표현하지 않는다.

## 바뀐 동작

최초 coordinator 예외와 traceback을 보관하고 새 제출을 중단한다. 이미 Future가 반환된 작업은 완료 결과를 읽어 각각의 finalize를 정확히 한 번 **시도**한다. work 예외는 기존대로 `unmeasured_worker_failure`에 담아 caller가 보수적인 전액 예약 정산을 선택할 수 있도록 전달한다. 모두 처리한 뒤 최초 coordinator 예외 객체와 원래 traceback을 재전파한다.

포함한 오류 경계는 다음과 같다.

- iterator의 `next()` 실패: 기존 작업을 처리하고 최초 예외를 재전파한다.
- `reserve`의 ValueError 이외 실패: 새 제출을 멈추고 기존 작업을 처리한다. reserve가 성공을 반환하지 않은 실패 작업 자체는 실행기가 임의로 finalize하지 않는다. 부분 예약 가능성은 reserve caller가 보존·복구해야 한다.
- reserve 성공 후 `executor.submit` 실패: 반환된 Future가 없으므로 해당 작업을 `unmeasured_worker_failure`로 정확히 한 번 finalize 시도하고 기존 Future도 처리한다. submitted_batches는 Future 반환에 성공한 작업만 센다.
- finalize 실패: 해당 작업은 재시도하지 않고 나머지 Future의 finalize를 계속 시도한다. 정산을 끝낸 후 manifest 쓰기에서 실패했을 수 있으므로 자동 재시도는 이중 정산 위험이 있다.

ValueError 예산 부족은 기존 `global_budget_remaining_insufficient` 중단 사유와 정상 반환 계약을 유지한다. 이미 제출된 작업은 그대로 finalize한다. 최초429 공유 Event는 그대로 유지하고 새 제출을 막으며 시작한 작업의 결과를 처리한다. 다른 coordinator 오류가 있으면 429가 같이 발생했어도 최초 오류를 숨기지 않는다. 정상 종료·bounded batch 상한·호출 스레드에서 reserve/finalize를 수행하는 기존 계약도 유지한다.

## 보장과 한계

**finalize 한 번 시도는 정산 성공 보장이 아니다.** finalize 자체가 실패하면 원래 오류를 반환하며 운영 결과를 미확정으로 취급해야 한다. 성공한 finalize는 다시 호출하지 않는다. 최초 오류 뒤의 finalize 오류가 있어도 최초 예외를 대체하지 않는다. caller는 남은 pending·worker receipt·manifest·정산 상태를 read-only 대조해야 하며 원인 없이 환불·삭제·자동 재실행해서는 안 된다.

이 변경은 같은 coordinator 수명 안에서의 ordinary Python Exception 경계다. 강제 프로세스 종료·전원 차단·OS 장애·KeyboardInterrupt/SystemExit 등 BaseException에 대한 영속 복구나 crash-safe transaction을 구현하지 않는다. submit이 Future를 반환하지 않으면 Python executor의 실패 계약에 따라 미측정 처리하며 worker 실행 여부를 임의로 성공이라고 추정하지 않는다. 이미 실행 중인 worker를 강제로 취소하지 않으며 worker 완료 대기의 기존 수명/timeout 계약도 바꾸지 않는다.

CLI의 `executed:false` 예외 보고(F2), 물리3000 상한의 미등록 실제 패치 집계(F3)는 다른 개발 채팅의 소유다. 이 단위에서 수정하지 않았다. 170의 실제 집행 승인이나 기존 사고의 운영 정산 완료로 확대하지 않는다.

## 시험 근거

```powershell
$env:PYTHONPATH='.runtime;.;backend;tests'
python -m unittest test_data_parallel -v
```

`evidence/integration/parallel-finalization-recovery-agent-20261018.log`: **12 PASS / 1.165초**. 기존5개와 신규7개 시험이며, 성공/실패 worker 변형은 한 시험의 subtest로 분리했다. 실제 ThreadPoolExecutor와 Event/Barrier를 사용한다.

신규 검증은 두 번째 reserve FileExistsError 뒤 첫 worker의 성공·실패 각각을 실제 Temp CollectionLedger에서 정산하고 pending 유실·0환불 추정을 막는지, iterator 오류 뒤 drain, reserve 성공/submit 실패의 정확한 finalize1회, finalize가 실제 임시 정산 뒤 실패했을 때 재시도 없이 나머지 작업 정산, drain 오류가 최초 오류를 덮지 않는지, 기존 ValueError 중단 사유, 429 공유 중단과 reserve 오류의 병행을 포함한다. 모든 Event/Barrier 대기는5초 한도다. 실제 네트워크·운영 원장·수집기는 사용하지 않았다.

수정 전 SHA256은 parallel.py `87c32c3a7b90b3b0d2fc1067b3e2adba9c0aff81dc44720675a513382a637280`, test_data_parallel.py `e1d33c1b4bc75520c37d8d917010ffc8efe9810cd677a8c8917aafaf33d817cf`다. 최종 소스/시험 SHA는 Root 인계와 집중 로그의 핀을 따른다.

내부 실행기 예외 처리 변경이고 HTTP/UI 계약을 추가하지 않아 화면 수정은 필요하지 않다. 기존 호출자는 정상 결과 계약을 유지하지만, 예외 전에 기존 worker finalize가 끝나므로 오류 반환 시점이 worker 완료 뒤가 될 수 있다. 실제 새 프로세스 적용·관련 collector 회귀·독립 검토·이해자료와 공통 인계 갱신은 Root의 후속 마감 범위다.

## Root 관련 회귀·후속 검증

Root는 최종 구현을 읽고 기존 수집/예산/표적 호출자와의 회귀를 실행했다. `parallel171-root-related-20261018.py/.json/.log`의5모듈(test_data_parallel/test_data_annual_budget/test_collect_targeted_bare/test_targeted_live_guards/test_targeted_collection_hooks) **50 PASS/0 SKIP/7.5502362초**다. 실제 ThreadPoolExecutor와 임시 원장/모의 HTTP 경계이며 실제 수집 시작0이다. 소스SHA `ff25bf4d83a43bb9b04ffcdadc31d6a02a6609e2c417d02c192c532cbd5b6ae3`, 시험SHA `5ca6b310f24b9c1db5c9942d32d5109632d571b5a2bdb3dc053cf3cdd8abb4c7`와 일치한다. 집중12개를 관련50개에 다시 더해62개의 서로 다른 시험으로 표시하지 않는다.

실행 중이던170 단일 batch는 이 변경 이전11:31:36에 종료됐으므로 새 F1 복구를 실제 원격 사고에서 검증한 것은 아니다. 다음 Python collector process는 현재 파일을 새로 import한다. UI 후보1219 승계는 별도 게시 담당과 Root 실제 브라우저 응답02:35:00UTC에서 확인했고, 내부 정산 수정 때문에 새 UI나 endpoint는 추가하지 않았다. 이 단위의 이해자료는 `docs/understanding/171_PARALLEL_FINALIZATION_RECOVERY.md`다.
