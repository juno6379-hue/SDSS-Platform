# 71. Evidence 전용 split 후보 생성과 metadata roundtrip 영수증

상태: **TESTED_SYNTHETIC**, **VERIFIED_REAL_METADATA_ONLY**. 신규 조정 코어는 고정 출처 세 JSON을 검증하고 기존 writer/validator만 연결하여 새 evidence 후보 패키지를 만든다. 실제 실행·보존·전체 회귀는 아래 Root 최종 근거로 연결한다. 이 완료는 원본 데이터 변경, Dataset 등록 또는 학습 준비 승인이 아니다.

## 구현과 책임

- `backend/app/ml/candidate_materialization.py`: `materialize_split_candidate(data_root, paths, pins, output_dir, *, evidence_root)`.
- `scripts/materialize_split_candidate.py`: 명시적 새 출력 디렉터리가 필수인 CLI.
- `tests/test_candidate_materialization.py`: 작은 합성 입력/후보만 사용하는 시험.

기존 `split_planning.py`, `split_validation.py`, `split_json_io.py`는 수정하지 않는다. 기존 planner를 내장한 full validator와 `write_plan`을 재사용하며 후보 문서를 만드는 별도 writer를 구현하지 않는다. 69의 큰 다섯 JSON 재검사는 강제하지 않는다. 이번 생성에 필요한 source/readiness/saved plan의 세 pin과 전체 계획 재계산이 근거다. 69의 현재 선언 계보 참조는 별도 설명 자료이며 이번 후보의 raster readiness 승인을 대체하지 않는다.

## 입력과 출력 경계

`paths`와 `pins`는 정확히 `source`, `readiness`, `saved_plan` 세 키다. SHA는 exact string 소문자 64hex로, 저장 plan에서 값을 꺼내 신뢰하는 대신 호출자가 별도 고정해야 한다.

| 역할 | 경계 | 읽기 cap |
|---|---|---|
| source | DATA root 안 일반 JSON 파일 | 64MiB |
| readiness | DATA root 안 일반 JSON 파일 | 16MiB |
| saved_plan | evidence root 안 일반 JSON 파일 | 4MiB |
| 생성 candidate | 새 evidence 디렉터리 | 64MiB |

코드의 고정 6주 split map은 기존 `FIXED_PROVINCE_SPLITS`를 그대로 사용한다. caller가 다른 분할 정책이나 새 실험 정책 파일을 전달하지 않는다. output dir은 DATA 밖·evidence 안의 아직 없는 명시 경로이며 **부모 디렉터리는 이미 존재해야 한다**. 부모를 재귀 생성하는 범위는 지원하지 않는다. 원격/UNC/URL·drive-relative·ADS·Windows 예약 장치명·끝점/공백·기존 경로/깨진 symlink·root 이탈을 거부한다. 세 입력은 canonical 경로와 inode/device도 서로 달라야 한다. 생성 plan/candidate 역시 입력 및 서로 다른 일반 파일이어야 한다.

출력 이름은 고정이다.

| 파일 | 한도 | 뜻 |
|---|---|---|
| plan.json | 4MiB | 기존 저장 계획의 재검증된 복사 |
| candidate.json | 64MiB | `PLANNED_DERIVED_CANDIDATE`, executed=false, learning_ready=false |
| receipt.json | 64KiB | 마지막에 쓰는 metadata roundtrip 완료 근거 |

모든 JSON 깊이 한도는 32다. 기존 bounded IO의 strict UTF8·중복 키·비유한 수·논리 경로/descriptor/stat·SHA 안정성 및 입력별 cap을 사용한다. 역할별 한도는 각 read/write에 적용하며 전체 누적 IO·메모리·실행 시간 hard cap을 뜻하지 않는다. 여러 번의 재검증으로 같은 JSON을 다시 읽는다.

## 처리 순서

1. 모든 입력의 위치·일반 파일·크기와 새 output/기존 부모를 전수 사전 확인한다. 세 입력을 동일 `BoundedJSONIO` context에서 caller SHA로 읽는다. saved plan pin도 여기서 고정한다.
2. 기존 `validate_split_repair_plan`을 fixed map과 source/readiness pin·같은 IO context로 실행한다. planner 전체 재계산과 저장 plan의 typed equality가 성공해야 한다.
3. 입력/roots/output parent를 다시 확인한 뒤 `mkdir(exist_ok=False)`로 새 디렉터리를 예약한다. 경합으로 생긴 기존 디렉터리와 파일은 보존하고 거부한다.
4. 기존 `write_plan`에 검증한 저장 plan과 두 새 파일 경로·동일 IO context를 전달한다. 기존 writer가 양 출력 크기를 사전 측정하고 exclusive 생성한다.
5. 생성 plan/candidate를 bounded read하여 SHA를 계산하고 candidate의 false 승인 상태를 확인한다. 기존 validator를 생성 plan·source/readiness·candidate SHA로 다시 실행하여 정확한 원본 retained 행·lineage·비실행 계약을 roundtrip 대조한다.
6. 작은 receipt를 64KiB 안으로 사전 측정한다. context에 등록한 원본과 생성 두 파일 전체를 다시 검증하고 root/출력 parent·새 디렉터리 identity를 확인한다. 디렉터리 ctime은 자식 생성으로 정상 변경되므로 마지막에는 device/inode와 논리 대상 일치를 확인한다.
7. **최종 입력/출력 확인 직후**, `receipt.json`을 exclusive로 기록한다. 영수증 뒤에 입력 검사를 추가해 그 검사 실패에도 성공처럼 보이는 receipt가 남는 구조를 만들지 않는다.

## 영수증 계약과 실패 처리

receipt는 schema_version1, kind `EVIDENCE_SPLIT_CANDIDATE_RECEIPT`, status `METADATA_ROUNDTRIP_VERIFIED`, candidate_status `PLANNED_DERIVED_CANDIDATE`, readiness_status `BLOCKED`, scope `PINNED_JSON_METADATA_ONLY_NOT_RASTER_READINESS`다.

`inputs`에는 세 파일 각각 canonical path·caller SHA·byte 크기, `outputs`에는 plan/candidate의 고정 basename·실제 SHA·byte 크기가 있다. derived manifest version·fixed map·source/candidate/excluded 물리 행 수·projected eligible patch 계수를 담는다. **후보 물리 행 수와 적격 패치 합계는 다르다.** 실제 원본 1384행/적격1111이라는 맥락이 있어도 입력을 변경하거나 숫자를 하드코딩하지 않는다.

`metadata_integrity_verified=true`는 JSON roundtrip에 한한다. executed/learning_ready/ready/scientific/source_authenticity/exact_row_binding/spatial_recheck/exact_class/leakage_resolved/execution/registry/settlement/automatic_resume는 모두 false, refund는0, exactly_once는UNKNOWN이다. 원본 raster·라벨/QA 픽셀·정확 클래스·공간 독립성·독립 라벨·운영 승인을 새로 검사하지 않는다. 학습 gate의 차단을 해제하지 않으며 Registry/Job/API/UI·학습·다운로드/네트워크를 호출하지 않는다.

**파일 존재만으로 완료를 믿으면 안 된다.** receipt가 없거나 잘린 JSON·잘못된 schema/status/falseflags·입출력 SHA/크기 불일치이면 미완료/무효다. 다음 소비자는 receipt 구조와 출력 pin을 검증해야 한다. 이번 단위는 후보 자동 소비/등록 기능이 없다.

writer/roundtrip/마지막 안정성 검사/receipt 쓰기 실패는 예외를 발생시킨다. 새 디렉터리·완성된 sibling·부분 plan/candidate/receipt를 자동 삭제하지 않는다. 기존 입력·원장·lock도 정리하지 않는다. 부분 receipt 자체가 남을 수 있으며 유효한 영수증으로 취급하지 않는다. 최종 확인 직후에도 OS 수준 동시 교체가 가능하므로 원자적 다중 파일 snapshot/commit·불변 저장소/정확히 한 번 반영을 보장하지 않는다.

## CLI

```powershell
python scripts/materialize_split_candidate.py `
  --data-root data `
  --source data/first-group-training-esri-v1/annual-window-report.json `
  --source-sha256 <caller-pin> `
  --readiness data/first-group/readiness-resume-20261017.json `
  --readiness-sha256 <caller-pin> `
  --saved-plan evidence/integration/ml-split-repair-plan-20261017.json `
  --saved-plan-sha256 <caller-pin> `
  --output-dir evidence/integration/<new-package-directory>
```

CLI 상대 입력/출력은 cwd 기준 absolute로 바꾸되 미리 resolve하여 logical alias를 제거하지 않는다. evidence root는 repository evidence로 고정한다. 성공 stdout은 상태/행 수/projected 계수/ready·registry false의 ASCII JSON 요약이며 원문 거대 후보는 출력하지 않는다. stderr도 ASCII escape하여 Windows CP949에서 경로를 안전하게 표시한다. 기존 디렉터리로 재실행하면 덮어쓰지 않고 실패한다.

## 합성 검증과 인계

최종 관련 시험: **60 PASS / 26.246초 / 종료0**. 신규15 + 기존 bounded IO20/planning8/validation17이며, 이전 12건 실행을 중복 합산하지 않는다.

```powershell
$env:PYTHONPATH="$PWD\.runtime;$PWD\backend;$PWD\tests"
python -m unittest test_candidate_materialization test_split_bounded_io test_ml_split_planning test_ml_split_validation -v
```

로그: `evidence/integration/candidate-materialization-related-20261017.log`. 작은 임시 JSON만 사용했다. 원본 바이트 보존·세 pin/정책/typed false·scope와 새 경로·디렉터리 경합·root/output retarget·writer 부분 실패·candidate 변조/roundtrip 승인 모순·최종 원본 변경·출력/receipt cap·부분 receipt 무효·no assess/무제한 read trap·기존 package 재실행·CP949를 검증했다. 기존 IO/planner/validator도 함께 통과했다.

Root가 실제 후보 생성 CLI1회, 원본/원장/lock/분할/모델 및 기존29계약·catalog 보존·전체 회귀·운영 인계와 이해자료 갱신을 맡는다. 새 공개 API/화면/자동실행 계약이 없으며 evidence 후보를 UI Dataset으로 등록하지 않으므로 이번 단위의 UI 변경은 없다. 이 문서의 합성 결과와 Root의 실제 결과를 구분하며, 단일 후보 패키지 완료를 전체 프로젝트 완료로 보지 않는다.

## Root 실제 생성·행 대조·최종 회귀

**VERIFIED_REAL_METADATA_ONLY**: CP949 환경에서 CLI를 1회 실행하여 종료0으로 새 `evidence/integration/candidate-materialization-live-20261017/` 패키지를 생성했다. 후보는 이제 실제 파일로 존재하지만 Dataset 등록·학습 준비 승인은 없다.

| 산출물 | 바이트 | SHA256 |
|---|---:|---|
| plan.json | 22,298 | ccdc704ead412d7aee069fb4f61f30a2baf9c9944458b858efcc28ba4197dfbf |
| candidate.json | 53,247,999 | 2ff7be093db3930d99f10cdc7687809222ef7f525ec6e9cf6248ec144725d158 |
| receipt.json | 3,936 | 889c549d8c8620a33fb90503313157313c520088809f2e16304c1d7fdcc3be51 |

Root는 생성 코어·validator를 다시 호출하지 않고 strict JSON, 입력3핀, 출력2핀/크기, 행 partition 및 후보1368행 전체를 원본1384행의 retained 목록과 타입까지 독립 대조했다. 새 plan은 기존 저장 계획과 바이트도 같다. 제외16은 후보에만 적용되며 원본1384행/기존 적격1111(628/233/250)은 불변이다. 후보의 계획 적격1095(628/217/250)는 raster 재검사 결과가 아니다. 15개 false 상태·환급0·exactly-once UNKNOWN을 확인했다. 근거는 `candidate-materialization-live-cli-20261017.log`, `candidate-materialization-live-validation-20261017.json`이다.

전체 회귀는 **706개/705 PASS/기존1 SKIP/329.107초/종료0**이며, 관련60(신규15+기존45)/26.246초 및 독립신규15/13.445초는 중복 합산하지 않는다. 보호참조134개/기존코어29개 SHA와 catalog14행 canonical SHA 불변, 기존 추적 backend/scripts/tests/data/frontend 변경0이다. 전체 workspace 불변·원본 raster 인증·OS 원자성 보장을 뜻하지 않는다. `candidate-materialization-live-integrity-20261017.json`과 `candidate-materialization-full-tests-20261017.log`에 기록했다.

기존 저장 readiness의 차단5건은 그대로다. 새 후보 readiness는 **NOT_ASSESSED**이며 차단 수나 누출 해소를 추정하지 않는다. 영상·기하·정확 클래스 재검사, Registry·학습·배포·정산·재개는 실행하지 않았다. 실제 실행 시간은 별도 정밀 계측하지 않아 초수를 제시하지 않는다.

## 다음 준비성 QA 연결 — PLANNED

기존 assess는 manifest도 DATA 경계 안에 한정하므로 evidence 후보를 직접 입력하면 거부된다. DATA root를 repository 전체로 넓히지 않는다. 다음 최소 구현은 strict receipt 소비 검증(입력3/출력2 SHA·크기·typed false 상태·lineage/fullcandidate 대조) 후 동일 SHA 후보 JSON만 DATA의 새 경로에 exclusive 복사하는 QA staging이다. 기존 `run_experiment.py`에 execute/resume 없이 진단 옵션과 새 readiness 출력 경로를 전달해 QA만 재사용한다. `--readiness-only`라는 플래그는 현재 존재하지 않는다. 아직 receipt 소비 검증기·staging·후보 QA는 구현/실행하지 않았으며, 원본 영상 복제·자동 등록·학습을 포함하지 않는다.

## 후속 실제 QA용 복사 — 구현72

[72 확인서 검증·복사](72_candidate_staging.md)에서 71패키지 확인서와 외부3핀을 엄격하게 대조한 뒤 후보 JSON만 DATA의 새 경로로 복사했다. SHA와53,247,999바이트가 원래 evidence 후보와 동일하다. 3,675바이트 staging확인서는 QA NOT_PERFORMED를 명시한다. 이 문서의72 PLANNED 내용은 당시의 역사이며 최신 복사 완료 근거는72를 참조한다. 후보 raster QA·등록·학습은 여전히 미실행이다.
