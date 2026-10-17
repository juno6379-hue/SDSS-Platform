# 110 — 수집 복구 commit 단계 선언 관측 계약

상태: **TESTED_SYNTHETIC / 운영 연결 BLOCKED**. `backend/app/data/recovery_commit_contract.py`의 `validate_recovery_commit_transition(previous, current)`는 호출자가 제공한 두 메타데이터 선언의 형식과 순서를 관측한다. 파일·DB·원장·네트워크를 읽거나 쓰지 않고 journal도 생성하지 않는다. 수집기/정산기/API/UI에 연결하지 않았다. 실제 pending 복구나 ledger/run-result 차이를 수정한 기능이 아니다.

## 배경과 범위

읽기 확인한 `scripts/collect_training_parallel.py`의 finalize는 `ledger.settle` → aggregate JSON 저장 → run-result JSON 저장 순서다. worker terminal은 이와 별도로 먼저 저장된다. `backend/app/data/budget.py`의 settle은 pending 상태·측정 상한을 검사하고 원장 하나를 저장하며 이미 정산한 batch는 거부한다. 기존 동작과 문서24/45/46/109를 변경하지 않았다. 이 순서는 여러 파일의 원자 commit이나 복구 가능한 journal을 입증하지 않는다.

새 함수는 세 저장 대상의 **선언된** before/expected-after/observed SHA를 비교한다. 실제 바이트 hash 계산·출처 인증·terminal 검증·reconciliation 수행·pending 해제·정산·환불·재개·재다운로드는 없다. 이미 있는 실제 missing terminal 2건을 합성 증거로 대체하지 않는다.

## 입력: observation exact11

`previous`는 `None` 또는 아래 관측이고 `current`는 반드시 관측이다. 둘 다 정확한 builtin dict, 정확한 builtin str 키만 허용한다. extra/missing 키·dict subclass를 거부한다.

| 키 | 계약 |
| --- | --- |
| schema_version | 정확한 int 1. bool/float 거부 |
| operation_id, batch_key | 정확한 str, 1..128 ASCII 문자 `[A-Za-z0-9._-]+`. `.`/`..` 금지. 공백·control·surrogate·경로 구분자·colon 거부 |
| config_sha256 | 정확한 str, lowercase hex64 |
| terminal_sha256, reconciliation_sha256 | lowercase hex64 또는 명시적 None(누락 증거로 거부) |
| phase | PREPARED / LEDGER_RECORDED / AGGREGATE_RECORDED / COMMITTED |
| phase_evidence_sha256 | lowercase hex64 또는 None. 단계 근거의 불투명한 호출자 선언이며 실제 journal/run-result 검증이 아님 |
| before, expected_after | exact3 dict: ledger_sha256 / aggregate_sha256 / run_result_sha256. 값은 lowercase hex64 |
| observed | 같은 exact3 dict. 값은 lowercase hex64 또는 None(누락 증거로 거부) |

정규화·trim·기본 SHA 생성·현재 파일 추정·ID 경로 해석·누락값 보정은 없다. 문자열과 dict 크기부터 제한하며 알 수 없는 extra 값·순환 값 전체를 순회·복제·serialize하지 않는다. batch 문법은 이 순수 계약의 제한이며 실제 파일의 존재나 업무 식별자를 인증하지 않는다.

## 단계별 observed 기대값

아래 B는 같은 target의 before, A는 expected_after다.

| phase | ledger | aggregate | run-result |
| --- | --- | --- | --- |
| PREPARED | B | B | B |
| LEDGER_RECORDED | A | B | B |
| AGGREGATE_RECORDED | A | A | B |
| COMMITTED | A | A | A |

따라서 aggregate까지 일치해도 run-result가 before이거나 누락이면 COMMITTED 선언을 수용하지 않는다. before와 expected_after가 같아도 허용하지만 이때 digest로 단계를 식별할 수 없다. 서로 다른 SHA도 실제 write를 입증하지 않으며 실제 write 여부는 미확인이다. phase 근거 SHA가 인접 전이에서 같아도 거부하지 않는다. 이것은 근거 인증을 수행하지 않는 관측 계약의 한계다.

## 검증·오류 우선순위

1. previous가 있으면 previous 전체를 먼저 검사하고, 다음 current를 검사한다. invalid previous를 전이 근거로 사용하지 않는다.
2. 각 관측: exact11 shape → schema_version → operation_id/batch_key → phase → config/terminal/reconciliation/phase-evidence SHA 형식 → before/expected_after/observed의 exact3 및 각 target 형식을 검사한다.
3. 형식이 모두 유효한 뒤 terminal → reconciliation → phase-evidence → observed ledger/aggregate/run 순서로 None 누락을 거부한다. 형식 오류는 누락보다 앞선다.
4. 관측 자체의 phase별 observed를 ledger → aggregate → run 순서로 검사한다. 누락·관측 불일치는 전이 판단보다 앞선다.
5. previous가 None이면 PREPARED만 `INITIAL_PREPARED`다. 호출자가 이전 이력을 생략할 수 있으므로 이것은 새 operation임을 인증하지 않는다.
6. 두 관측의 operation_id → batch_key → config_sha256 → terminal_sha256 → reconciliation_sha256 → before → expected_after를 원형 그대로 비교한다. 하나라도 다르면 identity 충돌이다.
7. 같은 단계는 모든 exact11 값이 동일할 때만 `IDENTICAL_REPLAY`다. 각 leaf의 정확한 타입은 앞 단계에서 이미 제한하므로 bool/int 동등성 우회가 없다. 같은 단계의 phase-evidence 변경은 충돌이다.
8. 바로 다음 단계만 `NEXT_PHASE`, 건너뛰기·역행은 거부한다. 인접 전이에서 phase-evidence는 바뀔 수 있다.

입력 객체를 바꾸지 않고 반환에 입력 dict를 alias하지 않는다. issue는 exact3 `{code, field, side}`이며 고정된 문자열만 사용한다. side는 PREVIOUS/CURRENT/COMPARISON이다. 호출자 ID·SHA·예외 문자열·경로를 반환하지 않는다.

| code | 의미 |
| --- | --- |
| OBSERVATION_SCHEMA_INVALID | 관측/맵 키 또는 schema_version 부적합 |
| OBSERVATION_ID_INVALID | bounded ID 문법 위반 |
| PHASE_INVALID | 허용 단계 아님 |
| SHA256_INVALID | SHA 형식 위반 |
| EVIDENCE_MISSING | 명시적 None 증거 |
| PHASE_OBSERVATION_MISMATCH | 해당 단계와 observed SHA가 불일치 |
| INITIAL_PHASE_INVALID | previous 없이 PREPARED 이외 단계 |
| OPERATION_IDENTITY_CONFLICT | operation/batch/config/proof/before/after 혼합 |
| REPLAY_CONFLICT | 같은 단계에서 다른 선언 |
| PHASE_SKIP / PHASE_REGRESSION | 단계 건너뛰기 / 역행 |

## 반환 exact18과 승인 경계

schema_version=1, scope=`RECOVERY_COMMIT_PHASE_CLAIMS_ONLY`, status=`BLOCKED`, metadata_transition=`INITIAL_PREPARED`/`NEXT_PHASE`/`IDENTICAL_REPLAY`/`REJECTED`, current_phase=허용 단계 또는 null, issue=고정 오류 또는 null이다. claim_verification=`UNVERIFIED`, exactly_once_applied=`UNKNOWN`이다.

settlement_authorized / refund_authorized / restart_authorized / write_authorized / execution_authorized / commit_executed는 항상 정확한 false다. proposed_refund_bytes / source_files_read / source_files_written / network_requests는 항상 정확한 int 0이다. issue null이나 metadata 전이 일치는 운영 승인이 아니다. 입력은 위조될 수 있고 함수는 과거 operation을 전역 조회하지 않는다. `IDENTICAL_REPLAY`는 선언 재관측 분류이며 실제 정산의 멱등성·exactly-once 적용 증명이 아니다.

## 사용과 시험

```python
from backend.app.data.recovery_commit_contract import validate_recovery_commit_transition

# previous/current는 위 exact11 계약의 호출자 선언. 운영 상태를 생성하지 않는다.
observation = validate_recovery_commit_transition(previous, current)
assert observation["status"] == "BLOCKED"
assert observation["write_authorized"] is False
```

PowerShell 시험은 `$env:PYTHONPATH = '.runtime;backend;tests;.'` 후 `python -m unittest test_recovery_commit_contract -v`다. 관련 묶음은 `test_recovery_commit_contract test_collection_recovery test_recovery_terminal test_recovery_aggregate test_data_annual_budget`이다. 합성 crash 경계·세 대상 전이·replay·identity 충돌·skip/regress·strict key/type/SHA·누락 우선순위·입력 불변·file/network 호출 금지를 검사한다. 실제 원장·예약·데이터 파일을 입력하지 않는다.

최초 focused는 12 PASS/0.007초였고 독립 읽기에서 exactstr key guard를 보강했다. 이어 shape 검사 전 phase 조회가 악성 key의 equality callback을 호출할 수 있음을 합성 재현해 shape 선행 검사와 poison key 시험을 추가했다. 기존 제품/운영 데이터 오류 수정은 아니다. 최초 및 중간 로그는 보존한다. 최종 focused는 **14 PASS/0.022초/exit0**, `evidence/integration/recovery-commit-contract-focused-final2-20261017.log`다. 최종 관련/독립 시험 결과는 아래 완료 근거에 기록한다. 새 순수 미연결 코드이므로 전체 backend/front/build/browser는 재실행하지 않는다. 이전107 전체1069건/1068PASS/1SKIP는 이전 근거다.

## 완료 근거·인계

최종 관련 시험은 **67건/66 PASS/기존 Windows symlink 1 SKIP/41.983초/exit0**이며 `evidence/integration/recovery-commit-contract-related-final2-20261017.log`에 보존했다. focused와 관련 묶음의 중복 시험을 합산하지 않는다. 중간 related 65건/64PASS/1SKIP 및 key-guard 이후 66건/65PASS/1SKIP 로그는 보존하고 최종 소스 근거로 대체하지 않는다.

독립 final3은 **63건/62 PASS/기존 Windows 1 SKIP/41.636초/exit0**, `evidence/integration/recovery-commit-contract-independent-final3-20261017.log`다. 별도 poison counter 5케이스(CURRENT/PREVIOUS/세 맵)에서 validator의 equality callback 0회도 확인했으며 unittest 건수에 합산하지 않는다. Root는 00:02:35 KST 보존 검사에서 보호141·이전 증거809·catalog14와 기존 코드 byte 불변, 최종 source/test SHA 일치를 확인했다. 독립 묶음도 구현 담당 시험과 중복되므로 합산하지 않는다. 신규 코드와 합성 관측의 계약 검증이며 운영 수집/정산 인증이 아니다.

사전 보존 근거는 `evidence/integration/recovery-commit-contract-preflight-20261017.json`이다. 현재 작업은 신규 module/시험/이 문서만 소유한다. 기존 source·24/45/46·collector/budget·recovery plan ID·API/UI를 변경하지 않는다. UI에 표시할 새 경로/응답이 없어 화면 변경은 필요 없다. Root는 최종 보존과 관련 문서/인계 및 이해 에이전트의 쉬운 설명·대본·FAQ·INDEX·변경 이력 갱신을 별도로 통합한다. 실제 durable journal과 coordinator 재개/정산 설계·검증은 후속 미완료다.

## 2026-10-18 — 복구 commit 단계 선언 검사 완료 (110)

새 순수 함수는 PREPARED→LEDGER_RECORDED→AGGREGATE_RECORDED→COMMITTED의 caller 선언과 ledger/aggregate/run-result 세 target의 before/expected_after/observed SHA를 검사한다. 최초 PREPARED·인접 전이·전체 동일 재관측만 구분하고 누락 근거·다른 작업 혼합·단계 건너뜀/역행·관측 불일치를 거부한다. source/evidence SHA는 caller 선언이며 실제 파일/권위/phase 증명이 아니다. 동일 before/after는 실제 쓰기나 단계 구별을 보장하지 않는다. 모든 결과 BLOCKED/UNVERIFIED·exactly_once UNKNOWN, 정산/환불/재개/쓰기/실행 false다.

입력 키의 exactstr 검사와 phase 표시용 사전 lookup 순서를 독립 검토로 보완했다. 최초·중간 통과 로그는 보존했고 최종 신규14 PASS/.022초·관련67건66PASS/기존1SKIP41.983초·독립63건62PASS/기존1SKIP41.636초를 완료 근거로 사용한다. 별도 poison-key5사례는 시험 건수에 합산하지 않는다. 새 독립 helper/시험/문서만 추가했으며 기존 제품과 API/UI 호출부는 바꾸지 않았다. 이번 전체/front/build/browser 재시험은 없고107 전체1069건은 이전 근거다.

Root 보존 검사는 보호141·이전증거809·catalog14·이전추적코드 불변을 확인했다. 수집기/예산코드는 현 raw snapshot 직접목록에 없어 별도 고정 Git 기준259b5f3의 원문 바이트와 대조해 둘 다 같음을 확인했다. 실제 pending2건에는 worker-result/annual-report가 여전히 없으며 새 helper를 적용할 operation/afterpin을 지어내지 않았다. 실제 journal·coordinator·원자적 정산·집계·재개는 미구현/미연결이다. 원장/run 차이·예약136314880B·원본/lock/분할/모델·QA차단4/학습BLOCKED를 보존한다.

사용자는 외부5개 모델의 API/SDK/code 실행자료와 독립 정확도 검증용 라벨이 별도 준비되지 않았다고 확인했다. 미연결·실행자료 미제공/미구현·독립 검증 라벨 미확보로 관리하고, 이미 있는 약한라벨 학습자료와 구분한다. 외부 의존은 BLOCKED이며 내부 개발은 계속한다. 관련 계약·문서24/45/46/109·gap/SOP·인계서와 이해자료14개(해설·이론·코드·시험·발표·FAQ·INDEX·변경이력)를 함께 갱신했다.

Git은 지정 origin SDSS-Platform/main259b5f3의 게시 확인 상태를 기준으로 이 단위를 별도 커밋/푸시한다. 다음 내부 후보는 실제 journal 지속화·실패 지점별 복구 coordinator 설계/구현이며110의 선언 검사만으로 완료되지 않는다. 전체 프로젝트는 미완료·담당별10분 보고와 지속 개발을 유지한다. 예약ACTIVE와 실제 수집/학습 프로세스는 구분한다.

근거: `evidence/integration/recovery-commit-contract-live-integrity-20261017.json`, `evidence/integration/recovery-commit-contract-independent-review-20261017.json`, `evidence/integration/recovery-commit-contract-external-dependencies-20261017.json`. 최종 문서 감사/파일 snapshot은 `evidence/integration/recovery-commit-contract-closeout-20261017.json`을 따른다.

