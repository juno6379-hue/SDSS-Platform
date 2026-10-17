# 중단 수집 terminal·예산 메타데이터 읽기 대조 — 2026-10-17

## 상태와 범위

**TESTED_SYNTHETIC:** 격리 임시 파일로 18개 기능시험을 통과했다. **VERIFIED_REAL:** 실제 pending 조사 결과는 root의 별도 실행 근거로 기록한다. **BLOCKED:** terminal 복구·완전 전송 계측·프로세스 종료/lock 소유권·원장 정산·aggregate 정확히 한 번 반영은 미확인이다.

새 inspector는 pending batch의 terminal 파일이 단순히 JSON 객체라는 이유로 완료 처리하지 않는다. 원장·config·window-state·worker-result·source annual report의 실제 구현 필드를 읽어 부족/잘못된 형식/불일치/메타데이터 일치를 구분한다. 모든 결과는 `BLOCKED`이고 정산·재시작 권한은 부여하지 않는다. 기존 recovery inspect/build/validate와 plan ID·snapshot은 변경하지 않은 별도 companion이다.

## 코드와 기존 계약의 연결

- [recovery_terminal.py](../../backend/app/data/recovery_terminal.py)의 `inspect_recovery_terminal(data_root)`가 구현이다. [collect_training_parallel.py](../../scripts/collect_training_parallel.py)의 reserve/work/finalize와 [budget.py](../../backend/app/data/budget.py)의 pending 예약 보존 계약을 읽기만 한다. CollectionLedger를 생성하거나 `snapshot()`을 호출하지 않으며 lock을 획득하지 않는다.
- 원장 config SHA는 raw job config의 `json.dumps(sort_keys=True)` 해시다. window-state config SHA는 [collect_samples.py](../../scripts/collect_samples.py)의 `load_config`가 `years`를 `periods`로 변환한 뒤의 해시다. inspector는 그 명시적 변환만 복사해 별도로 대조한다. 각 year는 정수 2015~2026이어야 하고 기본 계절은 06-01~09-30이다. raw SHA와 정규화 SHA를 같다고 가정하지 않는다. 전체 collector config 검증이나 STAC 접근을 실행하지 않는다.
- worker `key`가 ledger batch key와 일치해야 한다. `cog_charged_bytes=window.http_body_bytes`, `charged_bytes=cog+metadata_budget.charged_bytes`를 검사한다. metadata는 `0<=read_body_bytes<=charged_bytes<=maximum_bytes`, worker 합계는 예약 이하여야 한다. pending 원장 자체의 charged와 reserved가 같아야 한다.
- byte 계수는 정확한 정수이며 boolean/float/음수를 거부한다. window 측정값과 legacy 보존량 및 두 값의 합은 upper를 초과하지 않아야 한다. window upper와 config prior의 합은 config max_total_bytes를 넘을 수 없다. global new_charged는 외부 metadata charge+모든 batch charge 합과 일치하고 global 예산 이하여야 한다.
- worker report_path는 로컬 data root 안에 있어야 하고 해당 batch의 annual-window-report.json과 같아야 한다. source report는 실제 collector의 executed/status 계약을 검사한다. report의 upper/measured/legacy와 window 계수, prior와 config, combined=prior+upper, years/common_bands를 부분 대조한다. report `http_body_bytes`는 legacy0·upper==measured일 때만 정수 실측이며 그 외 null인 기존 계약을 보존한다.

## 결과 분류와 해석

batch `classification`은 우선순위 `INVALID` → `MISMATCH` → `MISSING` → `UNKNOWN` → `CONSISTENT_METADATA`다. 상세 `issues`와 `artifact_states`가 함께 있어 파일 누락과 잘못된 JSON을 구별한다. 빈 dict도 필요한 필드가 없어 INVALID다. worker error가 있으면 UNKNOWN이다. missing worker/report 두 파일의 실제 pending은 MISSING/BLOCKED로 남는 것이 정상이다.

`CONSISTENT_METADATA`는 검사한 필드에 모순이 없다는 뜻이다. source annual report에는 config digest나 worker key가 없으므로 부분 문맥 일치와 암호학적 신원 연결은 다르다. `source_report_identity_binding=UNKNOWN_NO_CONFIG_DIGEST_IN_REPORT`, `complete_transfer_accounting=UNKNOWN`, `aggregate_applied_exactly_once=UNKNOWN`, `process_exit_verified=false`를 유지한다. upper−measured와 metadatacharged−read는 미계측/예약 차이를 보여줄 뿐 환불 근거가 아니다. 차이가 0이어도 독립적인 완전 전송 검증을 확정하지 않는다.

모든 batch와 전체 보고서의 `settlement_authorized=false`, `execution_authorized=false`, `automatic_resume_allowed=false`, `proposed_refund_bytes=0`이다. 예약·charged 원형 값을 결과에 보존하며 `PRESERVE_FULL_RESERVATION`으로 표시한다. 네트워크 요청·원본 쓰기는 0이다. 파일 lock 존재로 프로세스 건강 상태를 추정하지 않는다.

## 입력 안전성과 CLI

strict JSON은 duplicate key, NaN/Infinity, overflow 비유한 수를 INVALID artifact로 분류한다. 잘못된 전역 원장은 검사 자체를 거부한다. 경로 이탈·원격/UNC·위험 batch key·일반 파일이 아닌 근거는 거부한다. 입력 파일의 SHA/크기와 누락 상태를 검사 전후 대조하고, 원래 논리 경로를 다시 resolve해 symlink/디렉터리 alias의 target 변경도 거부한다. 여러 파일의 원자적 snapshot이나 운영체제 lock 제공은 아니므로 조사 이후의 변경까지 방지하지 않는다.

[inspect_recovery_terminal.py](../../scripts/inspect_recovery_terminal.py)는 기본 stdout만 사용한다. stdout/stderr는 ASCII escape로 Windows CP949에서도 안전하게 출력한다. `--output`은 프로젝트 evidence 아래의 새 파일만 허용하며 UTF-8로 저장한다. inspected data root 아래 출력·기존 파일 덮어쓰기를 거부하고 exclusive create를 사용한다.

```powershell
python scripts/inspect_recovery_terminal.py --data-root data
# 새 증거가 필요할 때만, 아직 없는 출력 경로 지정
python scripts/inspect_recovery_terminal.py --data-root data `
  --output evidence/integration/recovery-terminal-live-20261017.json
```

exit 0은 읽기 조사 성공을 의미하며 결과 status는 여전히 BLOCKED다. 안전 경계/입력 오류는 exit 1, stderr 오류이며 성공 보고서를 쓰지 않는다. 개별 artifact의 INVALID/MISSING은 진단 보고서로 반환하므로 조사 exit0일 수 있다.

## 시험과 보완 이력

[시험](../../tests/test_recovery_terminal.py), [최종 단위 로그](../../evidence/integration/recovery-terminal-tests-20261017.log): **18 PASS (최종 시간은 로그 기준)**.

```powershell
$env:PYTHONPATH="$PWD\.runtime;$PWD\backend"
python -m unittest discover -s tests -p test_recovery_terminal.py -v
```

메타데이터 일치·모든 승인 false·원본 bytes 보존, terminal 누락/빈 dict, 중복 키·비유한 JSON, boolean/float/음수 계수, worker key/합계/예약/metadata 범위, raw↔정규화 config, source 문맥·null 실측 계약, 측정값이 같아도 UNKNOWN 유지, report 경로·루트 이탈, 위험 key·global 합계, config 예산, 조사 중 내용 변경·누락 파일 출현, 논리 경로 retarget, CP949 CLI/new evidence/덮어쓰기·외부 출력 거부를 검사했다.

초기 독립검토에서 state legacy boolean이 report0과 Python equality로 같아지는 공백과 legacy>upper 미검출을 재현했다. state legacy의 엄격한 계수 검증과 상한 검사를 추가했다. 후속 독립검토의 legacy+measured>upper도 MISMATCH로 거부하도록 추가 보완했다. root 검토의 논리 경로 재해석 경계도 보완하고, 실제 symlink 권한 없이 deterministic mock retarget 시험을 추가했다. 과거 실패 재현과 최종 PASS를 구별하며 독립시험 수를 전체 회귀에 중복 합산하지 않는다.

## UI 영향 및 인계

새 기능은 내부 CLI이며 공개 API·화면 상태·실행 중 frontend 계약을 바꾸지 않아 UI 수정/브라우저 재검증이 필요하지 않다. UI에 노출할 경우 별도 API·상태·오류·보안 계약을 확정해 web_ui에 전달해야 한다. root는 실제 pending 2건의 읽기 결과·보호 SHA·전체 회귀·인계서를 기록하고 이해 에이전트에 완료 코드/시험/한계를 전달한다. 관련 기존 설계는 [문서24](24_collection_recovery_plan.md)를 참조한다. 정산 coordinator·환불·lock 삭제·재시작·다운로드·학습은 이번 범위에 없다.

## Root 최종 실자료·회귀 확인

**VERIFIED_REAL(로컬 메타데이터만):** CP949 환경의 최종 CLI는 exit0이며 [최종 JSON](../../evidence/integration/recovery-terminal-live-final-20261017.json)은 두 pending 모두 `MISSING/BLOCKED`로 분류한다. 각 worker-result/source-report가 없고 rawconfig→ledger 및 정규화 config→window-state SHA는 각각 일치한다. 두 batch 모두 상한−실측33,554,432B를 미계측/예약 차이로 표시한다. 예약 총136,314,880B 보존, 환불0, 정산·자동재개 승인false다. [기존 계획 재검증](../../evidence/integration/collection-recovery-plans/validation-20261017T024014042395Z.json)은 기존 ID 그대로 `VALID_BLOCKED`다. 중간 `recovery-terminal-live-20261017.json`은 합상한 추가 전 실행 기록으로 보존하며 최종 근거는 `live-final`을 사용한다.

[보호 대조](../../evidence/integration/recovery-terminal-live-integrity-20261017.json)는 시험 후 존재/누락 포함19참조 불변과 기존 recovery·budget·collector2개·저장복구계획5SHA 불변을 확인한다. 관련18 PASS·7.150초, 독립18 PASS·7.545초이며 [전체 회귀](../../evidence/integration/recovery-terminal-full-tests-20261017.log)는 **356건/355 PASS/1 SKIP/110.069초/종료0**이다. 독립 실행을 전체356건에 중복 합산하지 않는다. SKIP은 기존 Windows symlink 생성 권한 제한이며 deterministic 경로 이탈 시험은 PASS다. UI 변경이 없어 기존 UI49건/build를 반복하지 않았다. 완전한 전송 계측·프로세스 종료·aggregate exactly-once·독립 과학 검증·정산/재개 승인으로 확대 해석하지 않는다.

## 후속 aggregate 참조 대조

[문서46](46_recovery_aggregate_reconciliation.md)의 별도 읽기 검사기는 aggregate 출처 참조와 원장 보고서의 양방향 연결, patch ID/이미지 경로 중복, source_window.path와 scene_id의 JSON 연결을 대조한다. terminal 계수 검증과 구분되는 부분 검사이며, 두 검사 결과를 합쳐도 완전 전송 계측·출처 파일 무결성·정확히 한 번 반영·정산/재개 승인을 부여하지 않는다. 새 검사기의 실자료와 최신 전체 회귀는 문서46 및 인계서를 참조한다.
