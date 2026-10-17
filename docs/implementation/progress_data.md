# 데이터 수집 읽기전용 진행 기록

<!-- physical=1384;eligible=1111;coverage=36;rate_limit=False;errors=11 -->

## 6. 주기 상태 갱신 — 2026-10-16 17:01:34 KST

1384물리/1111적격/273비적격,36/36셀. split train/val/test=628/233/250. 신규예약/계측1,933,512,405B중pending136,314,880B,신규4GiB/기존원장불변,429회로=False. 이숫자는전체실수신량이아니다. 원본session89858/collector/원장변경0.

동년Esri참조만사용하며WC2021연도대체금지,year불일치=0. 적격0셀=. 누적실패시도11건은docs20§8에원인별기록한다. 셀당28개바닥까지추가151개/총1262개이며개수만으로학습승인하지않는다.

고정증거: `evidence/integration/data-g0-g1-20261016T080135327079Z.json`. 상세행렬/오류/진행중pending은docs20§8-9.

## 7. 중단 복구 조사 — 2026-10-17 08:40 KST

재개 인계서 P0에 따라 OS 프로세스 목록을 다시 조회했으며 수집 coordinator와 monitor Python 프로세스는 발견되지 않았다. 빈 `global-ledger.execution.lock`은 남아 있다. 원본 수신파일·원장·합산 manifest·잠금파일을 변경하거나 수집을 시작하지 않았다.

읽기 전용 감사 `evidence/integration/data-g0-g1-20261016T234059384068Z.json`은 1,384 물리 / 1,111 적격 / 273 비적격, 36/36 셀, train/val/test 628/233/250으로 기존 수치와 일치한다. 원장 SHA `154004a2527c7ef6e93bec0c8a3ebf00a2af8e0683a1d4ed5252d59769da74a8`, manifest SHA `cdc374b2779dee749b57689fd90ef27e3525a48e59062343537327d0f4859a8f`도 그대로다.

별도 복구 조사 `evidence/integration/collection-recovery-20261016T234057781783Z.json`에서 Banten 2023·West Java 2023 두 pending의 `config.json`이 원장 설정 해시와 일치함을 확인했다. 두 작업 모두 `worker-result.json`과 source `annual-window-report.json`이 없다. 각 window-state의 상한과 실측 차이는 33,554,432B이며, 이를 실제 수신량 또는 환불 가능액으로 간주하지 않는다. pending 136,314,880B를 전액 보존한다.

`run-result.json` 신규 계상은 1,865,354,965B로 실제 전역 원장 1,933,512,405B보다 68,157,440B 뒤처져 있다. 재개 예산의 근거는 전역 원장이며 신규 4GiB 잔여는 2,361,454,891B다. 원장 내부합계는 일치하고 429 회로는 비활성이다.

새 `backend/app/data/recovery.py`와 `scripts/collect_recovery_inspect.py`는 원장/worker 근거를 읽고 별도 증거만 작성하며 자동 정산·lock 해제·재시작 기능을 제공하지 않는다. 예약 보존·원본 바이트 불변·보고서 지연·손상 JSON·경로 이탈·완료파일만으로 정산 불허를 5개 회귀시험으로 검증했다. 실행: `PYTHONPATH=backend python -m unittest discover -s tests -p test_collection_recovery.py -v`, 5 PASS.

재개는 여전히 보류한다. 먼저 기존 프로세스 종료를 재확인하고, 누락된 worker 완료/메타데이터 계측 및 aggregate 반영 근거를 대조해 coordinator 복구 절차를 마련해야 한다. 현재 `CollectionLedger.reserve()`는 같은 키의 pending 재실행을 거부하므로 실행 lock만 삭제해도 안전한 복구가 되지 않는다. 학습 승인 여부는 ML 담당의 최신 별도 readiness에 따른다.

## 8. 대시보드 재고와 readiness 출처 분리 — 2026-10-17

`collection_status()`는 현재 합산 manifest에서 1,384 물리 / 1,111 품질 적격 및 고정 분할 628/233/250을 직접 계산한다. 이 재고는 `patch_inventory.count_basis=manifest_quality_status`로 명시하며 과거 77패치 readiness 숫자로 대체하지 않는다. 클래스 통계는 최신 readiness의 입력·파일 해시가 현재 자료와 일치하고 검사 분할 개수도 재고와 같은 경우에만 함께 표시한다.

학습 검사는 `first-group/readiness-*.json`과 기존 `training-readiness.json` 중 가장 최근 보고서를 선택하며 기존 파일을 덮어쓰지 않는다. `training_readiness.source_report`, `freshness`, `manifest_matches_current`, `evidence_matched`, `current_manifest_sha256`로 출처와 최신성을 반환한다. 현재 합산 manifest의 경로와 SHA가 입력 근거에 없거나 verified_files가 변하면 `ready_for_training=false`로 표시한다. 과거 입력이 디스크에 그대로 남아 있어도 최신 합산 자료를 검증한 것으로 간주하지 않는다. 최신 파일이 손상되거나 불완전한 경우 과거 ready 결과로 되돌아가지 않는다.

기존 7시험과 재고/readiness 분리 및 최신 보고서 선택·입력 변경 회귀 2시험을 포함한 `test_collection_status.py` 9시험을 통과했다. 실제 데이터 읽기에서도 최신 명시적 readiness 선택과 manifest SHA 일치를 확인했으며 ML 담당의 최종 QA 결과를 기준으로 학습 gate를 표시한다. API 요청 첫 회의 전체 입력 파일 해시 검증은 시간이 걸릴 수 있고 이후에는 파일 메타데이터가 같은 해시를 캐시한다.

