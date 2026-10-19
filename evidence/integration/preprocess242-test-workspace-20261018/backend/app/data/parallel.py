"""실제 수집 2worker와 중앙 예산 정산을 분리하는 작은 실행기.

이 모듈 자체는 네트워크를 호출하지 않는다. worker는 서로 다른 공간/연도
디렉터리만 사용하며 전역 원장과 합산 manifest 갱신은 메인 스레드가 한다.
"""
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
import threading


def run_two_workers(jobs, reserve, work, finalize, stop_event=None, max_new_batches=0):
    """처음부터 전부 큐에 넣지 않고 최대 두 batch만 실행한다.

    reserve/finalize는 호출 스레드에서만 실행된다. work의 예외도 finalize에
    전달해 실패 예약을 유실하지 않는다. 429 Event가 설정되면 새 작업을
    제출하지 않고 이미 시작한 worker의 측정/보수적 예약 정산을 기다린다.
    예약/iterator/submit/finalize의 오류도 새 제출을 중단하지만 기존 작업의
    finalize를 각각 한 번 시도한 후 최초 오류를 재전파한다. finalize 실패는
    재시도하지 않는다(이미 정산된 결과를 다시 정산할 수 있으므로).
    """
    event = stop_event or threading.Event()
    iterator = iter(jobs)
    active = {}
    submitted, finalized = 0, 0
    exhausted = False
    stop_reason = None
    failure = None

    def stop_with_error(exc):
        nonlocal failure, exhausted
        if failure is None:
            failure = (exc, exc.__traceback__)
        exhausted = True

    def finalize_once(job, result):
        nonlocal finalized
        try:
            finalize(job, result)
            finalized += 1
        except Exception as exc:
            stop_with_error(exc)

    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="geoai-collector") as executor:
        while active or not exhausted:
            while not exhausted and not event.is_set() and len(active) < 2:
                if max_new_batches and submitted >= max_new_batches:
                    exhausted = True
                    stop_reason = "bounded_batch_count"
                    break
                try:
                    job = next(iterator)
                except StopIteration:
                    exhausted = True
                    break
                except Exception as exc:
                    stop_with_error(exc)
                    break
                try:
                    should_run = reserve(job)
                except ValueError:
                    # 신규 예산 잔여가 예약보다 작은 경우 요청을 시작하지 않는다.
                    exhausted = True
                    stop_reason = "global_budget_remaining_insufficient"
                    break
                except Exception as exc:
                    stop_with_error(exc)
                    break
                if not should_run:
                    continue
                try:
                    future = executor.submit(work, job)
                except Exception as exc:
                    # reserve succeeded but no Future was returned. Keep its
                    # measurement conservative and attempt central finalize once.
                    stop_with_error(exc)
                    finalize_once(job, {"unmeasured_worker_failure": exc})
                    break
                active[future] = job
                submitted += 1
            if event.is_set():
                exhausted = True
                stop_reason = "shared_circuit_open"
            if not active:
                break
            done, _ = wait(active, return_when=FIRST_COMPLETED)
            for future in done:
                job = active.pop(future)
                try:
                    result = future.result()
                except Exception as exc:
                    # work의 finally조차 실패했으면 예약을 전액 유지할 수 있도록
                    # 예외를 감추지 않고 중앙 정산 콜백에 전달한다.
                    result = {"unmeasured_worker_failure": exc}
                finalize_once(job, result)
    if failure is not None:
        exc, traceback = failure
        raise exc.with_traceback(traceback)
    return {"workers": 2, "submitted_batches": submitted, "finalized_batches": finalized,
            "stop_reason": stop_reason or "all_planned_batches_finished", "circuit_open": event.is_set()}
