# 중단 수집 복구계획 생성·검증

확인: 2026-10-17 09:31 KST. 담당: data_pipeline. 범위는 P0의 **읽기 전용 복구계획과 현재 근거 일치 검사**다. 전체 수집 복구·실자료 학습·플랫폼 개발 완료를 뜻하지 않는다.

## 구현과 상태

- **VERIFIED_REAL:** 기존 자료로 계획을 두 번 생성해 같은 ID와 기존 증거 재사용을 확인했다. 검증 결과는 `VALID_BLOCKED`, `execution_authorized=false`다. 원장·합산 manifest·run-result·lock·과거 원장·pending 근거의 전후 snapshot이 같다.
- **TESTED_SYNTHETIC:** 원장/manifest/config/window-state/terminal/lock/같은 크기 partial 내용 변경의 stale 거부, 계획 변조 후 재해시 거부, 중복 계획 재사용, 원본 바이트 불변, 경로 이탈 차단을 검증했다.
- **BLOCKED:** 두 pending에 terminal worker 결과와 source 보고서가 없다. 계획의 프로세스 상태는 `NOT_VERIFIED`이며 별도 OS 확인·완전 전송 계측·정산/aggregate 중복 방지 coordinator가 필요하다.
- **PLANNED:** 실제 적용 coordinator. 이번 CLI와 라이브러리는 예약 환불/해제, lock 삭제, 네트워크 요청, collector 재시작 기능을 제공하지 않는다.

## 코드와 동작

`backend/app/data/recovery.py`의 `inspect_recovery()`를 확장하고 `build_recovery_plan()`·`validate_recovery_plan()`을 추가했다. 표준 라이브러리만 사용한다.

snapshot은 전역 원장, 합산 manifest, run-result, execution/ledger lock, 과거 원장, pending별 config/window-state/worker-result/source report/partial 파일의 존재·바이트 SHA를 고정한다. 누락 파일의 존재 상태도 기록하므로 이후 terminal 파일이 나타나면 이전 계획이 stale이 된다. partial은 크기뿐 아니라 내용을 해시한다. 한 파일을 읽는 도중 메타데이터가 바뀌면 거부하고, 전체 조사를 연속 두 번 비교해 서로 다른 파일을 읽는 사이의 변경도 거부한다. 이는 검토 시점의 snapshot 검사이며 원장을 잠그는 원자적 적용이나 OS 프로세스 종료 증명은 아니다.

같은 내용 snapshot과 계획 본문은 같은 `collection-recovery-<SHA256>` ID를 만든다. 생성 시각을 ID 입력에 넣지 않는다. 검증은 계획의 자체 ID와 현재 snapshot을 확인한 뒤 현재 코드가 산출하는 전체 계획과 비교한다. 금지 action이나 `execution_authorized`를 바꾸고 ID를 다시 계산해도 거부한다. 오래된 snapshot, 읽을 수 없어진 근거, 추가/삭제/변경된 terminal·lock·partial 파일도 거부한다. 검증 성공은 `valid_for_review=true`만 의미하고 실행 허가는 항상 false다.

계획에는 pending 전액 보존, 환불 제안 0B, terminal/config 누락, 필수 검토 순서, 승인 전제, 금지 action을 기록한다. `worker-result.json`이나 source report가 JSON 객체라는 사실만으로 그 내용의 과학·전송·정산 적합성을 승인하지 않는다. 모든 terminal 파일이 있어도 실제 적용 coordinator가 없고 프로세스 상태를 검증하지 않았으므로 실행은 계속 차단한다.

기존 진단의 경로 경계도 보완했다. batch 키의 UNC/절대경로 문법을 resolve 이전에 거부하고, 개별 artifact의 resolved 경로가 데이터 루트 밖이면 읽지 않는다. 기존에는 directory만 확인하므로 그 안의 artifact symlink가 외부를 가리키는 경우를 막지 못했다.

## 명령

프로젝트 루트에서 실행한다. 기본 data-root는 `data`이며 출력은 `evidence/integration/collection-recovery-plans/`로 제한한다. 임의 output 경로와 `--execute` 옵션은 없다.

```powershell
python scripts/plan_collection_recovery.py
python scripts/plan_collection_recovery.py --validate evidence/integration/collection-recovery-plans/collection-recovery-8c3a33bff71ffbaad911ca44bc1ff5a9e831c257a8c3b7eaef5299b1770ef5b5.json
$env:PYTHONPATH = 'backend'
python -m unittest discover -s tests -p test_collection_recovery.py -v
```

같은 계획 파일이 이미 있으면 동일 내용만 재사용한다. 다른 내용이 같은 경로에 있으면 덮어쓰지 않는다. 검증 결과는 시각이 붙은 새로운 `validation-*.json`으로 남긴다. stale/변조 검증의 CLI 종료 코드는 2이며 계획 생성·검토 일치 성공은 0이다. 형식이 잘못된 입력 파일이나 데이터 루트 밖 경로는 오류로 종료하고 원본을 변경하지 않는다.

## 실자료 증거

- 계획: [collection-recovery-8c3a33bf….json](../../evidence/integration/collection-recovery-plans/collection-recovery-8c3a33bff71ffbaad911ca44bc1ff5a9e831c257a8c3b7eaef5299b1770ef5b5.json)
- 실제 현재 snapshot 검증: [validation-20261017T003037618057Z.json](../../evidence/integration/collection-recovery-plans/validation-20261017T003037618057Z.json)
- 보호 근거 15개 참조의 전후 내용 일치: [integrity-20261017T003101447624Z.json](../../evidence/integration/collection-recovery-plans/integrity-20261017T003101447624Z.json)

합산 manifest SHA는 `cdc374b2779dee749b57689fd90ef27e3525a48e59062343537327d0f4859a8f`, 전역 원장은 `154004a2527c7ef6e93bec0c8a3ebf00a2af8e0683a1d4ed5252d59769da74a8`로 이전 감사와 같다. 이 비교를 전체 raster 파일 재해시 증거로 확대 해석하지 않는다.

실제 계획의 pending은 Banten 2023 `parallel-v2-extra-banten-2023-v2-laneB-banten-boundary-01`, West Java 2023 `parallel-v2-extra-west_java-2023-v2-laneB-west_java-boundary-01`이다. 각 예약 68,157,440B, 합계 136,314,880B를 전액 보존한다. 두 config의 canonical SHA는 원장과 일치하지만 terminal worker 결과와 source annual report가 없다. 각 window-state의 상한−실측은 32MiB이며 완전 계측이나 환불 가능액으로 보지 않는다. 신규 원장 계상은 1,933,512,405B, 잔여 2,361,454,891B다. run-result는 68,157,440B 뒤처져 있어 실제 원장이 예산 근거다.

09:31 KST OS 조회에서 collector/monitor Python 프로세스는 발견되지 않았다. 이 별도 조회는 영속 복구계획의 `process_evidence=NOT_VERIFIED`를 운영 승인으로 바꾸지 않는다. 적용 시각에 다시 확인할 근거와 책임이 필요하다.

## 시험과 남은 작업

`test_collection_recovery.py`는 **15개 중 14 PASS, 1 SKIP**다. SKIP은 Windows에서 실제 symlink 생성 권한이 없어서 실행하지 못한 OS symlink 시험이다. 같은 경로 이탈의 deterministic resolver 대체 시험은 PASS다. CLI 중복생성·stale 검증·evidence 밖 출력 거부 시험도 포함한다. root의 전체 `scripts/test.ps1` 결과는 **225개 중 224 PASS, 1 SKIP, 종료 코드 0**이며 로그는 `evidence/integration/continuous-tests-20261017.log`다. 이 시험을 수집 복구 실행이나 독립 과학 검증 성공으로 해석하지 않는다.

후속 적용 구현은 동일 batch의 전송/메타데이터 계측과 aggregate 반영 상태를 먼저 확인하고, 미계측 예약을 보존하면서 정확히 한 번만 정산·반영하는 journal/멱등 절차가 필요하다. 빈 lock 삭제 또는 계획 검증 성공만으로 재수집하지 않는다. 기존 자료·원장·분할·모델을 변경하는 작업은 이번 단위에 포함하지 않았다.

## 2026-10-17 11:27 KST 재개 시 읽기 대조

[새 로컬 조사](../../evidence/integration/collection-recovery-20261017T022648851066Z.json)와 [기존 계획의 현재 재검증](../../evidence/integration/collection-recovery-plans/validation-20261017T022720783320Z.json)을 수행했다. 기존 계획은 `VALID_BLOCKED`, `valid_for_review=true`, `execution_authorized=false`다. pending 2건의 terminal worker/source 보고서는 여전히 없고 config SHA는 일치한다. 예약 총136,314,880B, 신규 계상1,933,512,405B, 잔여2,361,454,891B, run-result와의 차이68,157,440B 및 내부 합계 일치는 직전과 같다.

[별도 OS 프로세스 조회](../../evidence/integration/ml-split-validation-processes-20261017.json)는 UI/API 서버만 확인했다. 이 조회는 종료 책임자 확인이나 lock 해제 승인으로 사용하지 않는다. 원본/원장/lock 수정, 네트워크 수집과 학습은 실행하지 않았다. terminal 내용·완전 전송 계측·coordinator exactly-once 정산은 여전히 후속 구현과 검증 대상이다. 기존 225건 회귀 수치는 당시 이력이며 이번 새 전체 시험 결과는 최신 인계서에 별도 기록한다.

## 2026-10-17 terminal 내용 대조 companion

[문서45](45_recovery_terminal_reconciliation.md)의 별도 read-only inspector가 terminal 파일의 내용과 원장·config·window-state 계수를 대조한다. 기존 이 문서의 `worker_terminal_evidence_present`는 여전히 JSON객체 존재를 뜻하며 새 inspector의 내용 일치 판정과 구분한다. 기존 recovery 코어/영속 계획 본문·ID는 바꾸지 않는다. [새 기존 계획 검증](../../evidence/integration/collection-recovery-plans/validation-20261017T024014042395Z.json)은 같은 ID의 `VALID_BLOCKED`, `execution_authorized=false`를 확인했다.

[최종 실제 내용 검사](../../evidence/integration/recovery-terminal-live-final-20261017.json)는 두 pending 모두 `MISSING/BLOCKED`다. worker-result/source-report가 각각 없고 raw config→ledger SHA 및 정규화 config→window-state SHA는 모두 일치한다. 각 COG 상한−실측33,554,432B는 미계측 또는 예약 잔액이며 환불 가능액이 아니다. 총136,314,880B 예약을 보존하고 환불 제안은0이다. source report에 config digest가 없으므로 완전한 출처 바인딩, 전체 전송 계측과 aggregate exactly-once 적용은 `UNKNOWN`이다. 이 검사나 전체 메타데이터 일치만으로 정산·lock해제·재개를 승인하지 않는다.

코드와 CLI의 관련18 PASS/7.150초·독립18 PASS/7.545초를 보존했다. 최신 전체 회귀/보호19개 참조 및 기존 계약5개 SHA 검사는 문서45와 최신 인계서에 확정한다. 이번은 내부 CLI 추가이며 공개API/화면 계약 변화가 없어 UI시험49건/build를 반복하지 않았다.

### 110 후속: commit 단계 선언 검사

[110 구현 문서](110_recovery_commit_contract.md)의 독립 순수 함수가 caller의 단계·세 target SHA·재관측·충돌을 검사한다. 기존 이 문서의 실자료 검사/형식·수집기·예산코드는 바뀌지 않았고 실제 journal/정산·집계/재개 coordinator는 미연결이다. 기존 pending2/예약·원장-run 차이를 해결하거나 exactly-once를 인증한 것이 아니다. 최종 신규14·관련66PASS/1SKIP·독립62PASS/1SKIP·보존 범위는 `evidence/integration/recovery-commit-contract-live-integrity-20261017.json`을 따른다. 해당 내부 선언 검사만 완료이며109의 실제 지속화/복구 수락 조건은 남는다.
