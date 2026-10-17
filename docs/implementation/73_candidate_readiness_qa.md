# 73. 고정 후보·staging 영수증·동일 정책의 QA-only guard

상태: **TESTED_SYNTHETIC**, **VERIFIED_REAL_CANDIDATE_QA**. 4개 외부 SHA로 고정한 JSON을 검증한 뒤 기존 `scripts.run_experiment.run`을 QA-only로 호출한다. 담당 시험은 작은 합성 JSON과 모의 assess/run만 사용했다. 실제 후보 QA는 Root의 별도 실행 1회이며 이 문서의 합성 시험과 구분한다.

## 새 구현과 실행 경계

- `backend/app/ml/candidate_readiness_qa.py`: `assess_staged_candidate(data_root, paths, pins, output_dir)`.
- `scripts/assess_staged_candidate.py`: 명시 입력·SHA·새 DATA 디렉터리를 요구하는 CLI.
- `tests/test_candidate_readiness_qa.py`: 모의 QA/기존 run 격리·보존 시험.

기존 readiness, run_experiment, policy/분할, staging 및 31개 기존 코어는 수정하지 않는다. 실제 호출은 다음 literal 값으로 고정하며 사용자 인자로 받지 않는다.

```python
run(
    [candidate_path], data_root, new_report_path,
    deepcopy(caller_policy),
    execute=False, resume=False, connectivity_diagnostics=True,
)
```

기존 run은 `not execute`에서 준비/학습/infer 이전에 반환한다. QA gate가 ready=True라도 이번 guard는 Dataset 준비/등록·학습·재개·추론을 시작하지 않는다. caller 정책 객체도 deepcopy하여 모의 runner의 변경/예외가 입력 JSON 객체에 전파되지 않게 한다.

## 4입력과 한도

`paths`와 `pins`는 정확히 `candidate`, `staging_receipt`, `policy`, `old_readiness` 네 키다. 모든 경로는 DATA root 안 일반 로컬 JSON이어야 하며, 외부에서 고정한 SHA는 exact string 소문자64hex다. receipt 자체의 값을 외부 pin으로 다시 꺼내 사용하는 방식은 신뢰 근거가 아니다.

| 역할 | 파일/읽기 cap |
|---|---|
| staged candidate | 64MiB |
| staging receipt | 64KiB |
| 기존 정책 JSON | 1MiB |
| old readiness JSON | 16MiB |
| 생성 readiness 보고서의 신뢰/읽기 한도 | 16MiB |
| 마지막 QA receipt | 64KiB |

각 역할을 별도 bounded IO context로 처리하여 낮은 cap이 초기 read와 종료 재읽기에도 적용된다. 깊이32·strict UTF8/no BOM/NUL·중복 키·NaN/Infinity·Unicode·exact 타입·descriptor/stat/논리 경로 target·고정 SHA를 확인한다. 모든 입력의 크기·regular file·경계·서로 다른 canonical/device/inode를 먼저 확인한다.

새 output 디렉터리는 DATA 안이며 부모는 이미 존재해야 한다. 기존 대상/깨진 symlink/입력 별칭·root 이탈·원격/UNC/URL·drive-relative·ADS·Windows 장치명·끝점/공백은 거부한다. exclusive 새 디렉터리 안에 고정 `readiness.json`, `qa-receipt.json`만 생성한다. 기존 후보/staging/정책/과거 QA를 덮어쓰지 않는다.

## staging·과거 참조 검증

staging receipt는 v1의 정확한 키 집합과 `METADATA_STAGED_FOR_QA`, `NEXT_QA_NOT_PERFORMED`, `qa_status=NOT_PERFORMED`, metadata/원문보존 true, refund int0, exactly_onceUNKNOWN 및 모든 false 필드를 확인한다. package reference·과거 input 3pin·output 2pin은 제한된 선언 형식으로 확인하고, 현재 candidate path/SHA/size·version·물리 행 수·projected 계수·고정6주 분할·source row index lineage와 결합한다. 후보는 `PLANNED_DERIVED_CANDIDATE`, executed=false/learning_ready=false여야 한다.

old readiness 외부 SHA는 staging의 `input_pins.readiness`와 같아야 한다. old의 단일 input manifest는 **원본 source**로서 staging의 source pin 및 candidate.lineage.source_manifest의 pin/path와 일치해야 한다. 반면 새 QA 보고서의 단일 manifest는 **현재 staged candidate**여야 한다. 두 역할을 바꾸거나 원본 report 출처를 candidate 출처로 표시하지 않는다.

old readiness는 고정 정책/source/signature 참조의 필요한 schema/ready/science 필드만 확인한다. 전체 과거 QA의 blockers·witness·모든 파일/클래스 검증을 다시 수행하는 기능은 아니다. package/source manifest를 따라가거나 72의 full plan 재계산을 반복하지 않는다. staging receipt와 candidate의 외부 pin이 이전에 검증한 동일 metadata 바이트를 고정한다는 범위이며, 과거 실행 신원이나 원본 제품 authenticity를 인증하지 않는다.

## 동일 정책·바닥·라벨

`effective_policy={**default_policy(), **caller_policy}` 전체가 old readiness.policy와 typed 동일해야 한다. bool==int·float==int 같은 Python 동치를 허용하지 않는다. required provinces/2020~2025 years·6 bands·required classes·고정4/1/1 map·patch256·scope/클래스 가중 기준을 현재 기본 계약과 같게 유지한다.

non-test 기준의 min patch1000, split600/100/100, train province50, unique location32, 품질.8, inside.95, max patch3000을 exact 타입/범위로 확인하여 기존 assess의 강제 바닥 적용 후 정책이 달라지는 입력을 거부한다. 클래스 최소 픽셀/패치와 ratio·dominance 기준도 기본보다 완화하지 않는다. seed 정수·band/class/scope/type 변경이나 알 수 없는 test_mode 키를 허용하지 않는다.

실제 기존 정책에는 `label_source='esri_io'`가 있으며 default_policy에는 이 키가 없다. 초기 초안의 base-key-only 검사는 이를 거부할 수 있어 허용 키를 default+label_source로 보완했다. label_source는 지원 enum의 exact string이며 old input_signature.label_source와 같아야 한다. old signature가 필수이고 새 보고서 signature 전체도 typed 동일해야 한다. 실제 정책 파일이나 데이터를 수정하여 호환 문제를 우회하지 않았다.

## 결과·차단·영수증

반환 QA 보고서에는 기존 status `blocked` 또는 `ready_for_weak_label_experiment`, exact ready bool과 blocker list가 필요하며 서로 모순되면 거부한다. 정책 전체·단일 candidate input pin/path·verified collection_manifest pin·band/label signature·typed split 패치 계수·과학 false를 대조한다. 진단 capture의 상태와 gate 변경/학습·실행·정산·재개·refund/IO 주장을 확인한다. CAPTURED 상태의 manifest 참조는 현재 candidate와 같아야 한다. 실패한 capture도 기존 gate를 바꾸지 않는 상태라면 QA 완료로 기록하되 capture 성공으로 승격하지 않는다. 전체 witness를 재생하거나 픽셀을 guard가 다시 읽지는 않는다.

**blocked는 정상 QA 완료 결과다.** QA receipt에는 `status=QA_COMPLETED`, 실제 관측 readiness 상태·관측 gate ready·차단 list·split 계수·capture 상태를 담는다. `observed_gate_ready_for_training`은 기존 QA의 관측값이며 receipt 자체의 `ready_for_training`·execution/training/science/auth/registry/resume/settlement/automatic_resume 권한은 모두 false다. 독립 정확도·누출 완전 해소를 선언하지 않는다.

run 반환 후 입력 네 JSON을 다시 고정 pin/target/stat로 확인한다. 생성 report를 16MiB·strict depth32 한도로 읽고 반환 객체와 전체 typed 동일해야 한다. report SHA/size와 입력4pin을 작은 QA receipt에 묶은 뒤 입력/보고서·root/parent/새 디렉터리를 마지막으로 재검증하고 receipt를 exclusive로 기록한다. receipt 뒤 입력 검사를 추가해 실패했는데 성공처럼 보이는 marker를 남기는 순서는 사용하지 않는다.

## IO·실패 한계

guard의 bounded IO는 입력 사전/사후 읽기와 report 검증에 적용한다. **기존 run 내부 assess의 read_text·원본 영상/라벨 읽기·hash와 report write를 이 helper가 bounded로 바꾸지는 않는다.** report16MiB는 run 이후 신뢰/완료 처리의 cap이며, run이 그보다 큰 보고서를 쓰는 순간을 막는 hard 출력 cap이 아니다. 초과·읽기/검증 실패 시 새 report는 보존하고 완료 receipt를 만들지 않는다. 전체 RAM·누적 IO·CPU/time hard cap도 아니다. 실제 Root 실행은 별도의 timeout/RSS 관측·GDAL 부수파일/네트워크 off 설정으로 관리하며 그 관측과 보장을 구분한다.

run 예외·입력 변경·경로 retarget·보고서 불일치/상한·receipt 쓰기 오류는 예외를 발생시킨다. 새 디렉터리·부분/완성 보고서·부분 receipt는 자동 삭제하지 않는다. 완료 receipt가 없거나 JSON/schema/pin이 무효이면 미완료다. 파일 존재만으로 완료를 믿지 않으며 다음 소비자가 receipt와 report SHA를 다시 확인해야 한다. OS 원자적 다중 파일 snapshot/commit을 보장하지 않는다. 원본·원장·lock·예약·분할·모델·Registry를 변경하지 않는다.

## CLI와 합성 증거

```powershell
python scripts/assess_staged_candidate.py `
  --data-root data `
  --candidate data/<stage>/candidate.json --candidate-sha256 <external-pin> `
  --staging-receipt data/<stage>/staging-receipt.json --staging-receipt-sha256 <external-pin> `
  --policy data/first-group/experiment-esri-v003-2020-2025.json --policy-sha256 <external-pin> `
  --old-readiness data/first-group/readiness-resume-20261017.json --old-readiness-sha256 <external-pin> `
  --output-dir data/<new-candidate-qa-directory>
```

CLI에는 execute/resume 옵션이 없고 명시 새 디렉터리가 필수다. 상대 경로는 cwd 기준 absolute로 만들되 logical alias를 먼저 resolve하지 않는다. stdout은 QA 완료/관측 상태/차단 수·계수/진단 상태와 실행 false의 ASCII JSON이고 stderr도 ASCII escape하여 CP949를 지원한다.

최종 관련 합성 시험: **19 PASS / 12.065초 / 종료0**, `evidence/integration/candidate-readiness-qa-related-20261017.log`.

```powershell
$env:PYTHONPATH="$PWD\.runtime;$PWD\backend;$PWD\tests"
python -m unittest test_candidate_readiness_qa -v
```

외부4pin·strict input/cap·stage schema/false/path/count·old source/정책/label/signature·바닥과 bool coercion·정책 객체 분리·반환/저장 report·status/ready/차단/참조/capture 모순·report/receipt 완료상한·중간 입력 변경·부분 report/receipt·경합/new-only/Windows·CLI 금지 옵션·CP949 subprocess를 검증했다. 실제 기존 run을 쓰되 assess를 모의한 ready=True 사례에서도 prepare_dataset/train_model/infer_raster trap이 호출되지 않았다. CLI subprocess도 모의 run만 사용했다. 실제 영상·QA·훈련은 담당이 실행하지 않았다. 초기15건 실행과 최종19건을 중복 합산하지 않는다.

Root가 실제 후보 QA1회·전체 회귀·139보호/31기존 코어·catalog 및 기존 자료 보존·운영 인계/이해자료 갱신을 맡는다. 새 공개 API/UI나 자동 Dataset 등록을 추가하지 않는 내부 QA-only CLI이므로 이번 화면 변경은 없다. 후보의 QA 완료/차단 결과는 전체 프로젝트 완료나 학습·과학·운영 승인과 구분한다.

## Root 실제 후보 QA — 검사 완료·학습 차단

실제 CP949 CLI를 한 번 실행했다. `candidate-readiness-qa-live-runner-20261017.py`가 PROJ_NETWORK=OFF/GDAL_PAM_ENABLED=NO/GDAL_DISABLE_READDIR_ON_OPEN=EMPTY_DIR/GDAL_VRT_ENABLE_PYTHON=NO 환경으로 실행하고600초/표본 RSS2GiB 초과 시 중단하도록 감시했다. 전체 호출202.344초·종료0·중단이유null,1초 간격197표본의 관측 최대 RSS532074496바이트다. 이는 OS 하드 메모리 제한이나 모든 순간의 실제 peak 보장이 아니다. 실제 QA는 영상·라벨·품질 자료를 읽고 해시/내용을 검사한다. 순수 추가 연결진단의 추가 IO0을 전체 QA의 영상 IO0으로 표현하면 안 된다.

새 출력은 `data/first-group-candidate-readiness-qa-20261017/` 아래다.

| 파일 | 바이트 | SHA256 |
|---|---:|---|
| readiness.json | 11,842,410 | 847343e1aa4ab9b67fd3bba36a2a9f91d716c2fd411af244e55bbfe1a8414019 |
| qa-receipt.json | 3,030 | 7b5ea8bba57bfc359076a0db27adce554b28c7d1796ae352b82ef9d94d79e38d |

결과는 `QA_COMPLETED`, 관측 준비성 `blocked/false`다. 원본과 후보의 정책·밴드/라벨 서명이 타입까지 동일하고, 실제 적격패치는 train628/val217/test250=1095다. 물리 장면1368개/캡처적격1095, `CAPTURED_COMPONENTS_MATCH`, verified_files4285개를 기록했다. 원본보고서와 공통인4284개 기록의 저장SHA/kind가 같고, 추가기록은 stagedcandidate manifest1개이며 기존기록51개는 새inventory에 없다. Root의 이 대조는 저장JSON 비교이며 영상을 중복 재검사하지 않았다.

새 차단4건은 원본보고서의 클래스 관련4건과 전체typed동일하다.

| 차단 | 실제 관측 |
|---|---|
| REFERENCE_CLASS_IMBALANCE | train class7 픽셀 비율·기여패치 부족 |
| REFERENCE_CLASS_IMBALANCE | val class7 픽셀 비율·기여패치 부족 |
| CLASS_COVERAGE | val/class7 209픽셀 |
| REFERENCE_CLASS_IMBALANCE | test class7 픽셀 비율·기여패치 부족 |

나지(bare/class7) 픽셀은 원본/후보 모두 train1418·val209·test1025이며 기준을 충족하는 기여패치는 각0이다. 기존 원본보고서의5차단은 그대로 보존했다. 후보보고서에 `SHARED_SOURCE_CROSSES_FIXED_SPLIT` 항목은 없고, 제공된 메타데이터 연결 witness의 고정split 충돌0·bbox비교935028·완전선언identity1368을 관측했다. 이 제한된 관측은 완전한 누출 해소·원본 인증·과학적 독립성 승인이 아니다. 모든 실행·정식훈련·Registry·재개·정산·과학승인 플래그는 false다.

## 최종 회귀·보존과 문서 인계

전체744개/743 PASS/기존1 SKIP/356.067초/종료0이다. 관련19 PASS/12.065초·독립19 PASS/12.236초는 반복검증으로 전체에 중복 합산하지 않는다. 보호139참조·기존코어31개 SHA와 입력4핀·catalog14행 canonical SHA 불변, 기존추적 backend/scripts/tests/data/frontend 변경0이다. 전체 workspace/raster inventory 불변이나 원자적 snapshot 보장은 하지 않는다. 새 출력2개와 신규구현4개·Root 실행 증거를 별도 추가했다.

근거는 `candidate-readiness-qa-live-execution-20261017.json`, `candidate-readiness-qa-live-validation-20261017.json`, `candidate-readiness-qa-live-integrity-20261017.json`, 같은 접두사의 CLI/stderr/전체시험 로그다. stderr는 비어 있다. 72 staging 확인서의 QA NOT_PERFORMED는 당시 사실로 보존하고 이후73의 별도 QA완료확인서로 최신 검사를 연결한다. 원본·후보·이전확인서를 수정하지 않았다. 공개API/UI없는 내부CLI라 이번화면 변경·브라우저시험은 없으며 관련72/운영원장/인계/이해자료를 함께 갱신한다.

## 다음 원본·후보 비교 표시 — PLANNED

고정된 원본준비성/후보준비성/QA확인서/staging확인서4JSON과 호출자4SHA만 읽는 비교 코어·내부API를 검토한다. 정책/출처/라벨서명·확인서와입력pin·계수·차단코드빈도·false승인을 대조하고 거대source/candidate JSON·영상·assess·Registry는 읽거나 실행하지 않는다. 계약을 검증한 뒤 UI담당에게 수동비교카드로 인계하고 실제브라우저 반영을 확인한다. API/카드/브라우저검증은 아직 수행하지 않았다.

원본보고서는 물리장면수를 저장하지 않아 null/NOT_PERSISTED로 표현하고, 적격1111에서1384를 추정하면 안 된다. source1384/candidate1368은 staging의 선언행계수, 새QA1368은 관측 장면수로 출처를 구분한다. 원본1111→후보1095·차단5→4·bare미해결을 보여주되 공유소스차단항목 미관측을 완전한 누출 해소로 표시하지 않는다. 화면 조회는 명시적 수동 동작이며 자동 POST/QA/학습을 추가하지 않는다.


## 저장 결과의 후속 비교 UI

73에서 생성한 원본/후보 보고서·QA/복사확인서 4JSON을 고정해 비교하는 읽기 전용 API와 LCLUC 근거 탭 카드가 [문서74](74_candidate_qa_comparison_api.md)·[문서75](75_candidate_qa_comparison_ui.md)에 추가됐다. 저장 결과 비교를 위해 새 QA를 실행하지 않으며 73의 QA 수행 범위와 구분한다. 원본1111/차단5·후보1095/차단4·나지 부족·학습/과학 승인false는 유지한다.


## 저장 QA에서 나지 부족 조건 읽기

[문서76](76_bare_class_requirements.md)은 이 QA 보고서의 고정 SHA를 다시 확인하고 저장 통계·정책만으로 나지 부족 조건을 구분한다. 분할별 픽셀 바닥 부족은0/47/0, 기여 patch 부족은각5, 비율 기준은세분할 모두미달이다. 미래 자료가 비율의 분모를 바꾸므로47픽셀 또는새장면/패치15개만으로준비완료를보장하지않는다. 기존 순수 balance_diagnostics를 메모리 통계에 재적용한 동일성 확인이며 새로운 QA·래스터·라벨·기하 검사는 아니다. 입력 report/source/정책·원본분할·학습차단4건은 유지한다.
