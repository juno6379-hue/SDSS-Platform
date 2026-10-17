# 72. 후보 영수증 소비 검증과 동일 바이트 DATA staging

상태: **TESTED_SYNTHETIC**, **VERIFIED_REAL_METADATA_STAGING_ONLY**. evidence 후보 패키지의 영수증을 엄격히 검증한 뒤 `candidate.json` 원문만 새 DATA 경로에 복사한다. 실제 readiness QA/assess는 수행하지 않는다. 다음 단계는 명시적으로 **NEXT_QA_NOT_PERFORMED**다.

## 목적과 구현

기존 assess는 manifest도 DATA root 안에 있어야 한다. root를 repository 전체로 넓히면 영상/출처 읽기 경계의 의미가 달라진다. 이번 단위는 그 경계를 유지하기 위해 검증된 후보 metadata JSON만 DATA의 새 경로에 동일 SHA로 staging한다. 원본 raster·라벨·QA 파일을 복사하거나 변경하지 않으며 Dataset 등록/학습을 시작하지 않는다.

신규 파일:

- `backend/app/ml/candidate_staging.py`: `stage_split_candidate(data_root, package_dir, receipt_sha256, input_pins, output_dir, *, evidence_root)`.
- `scripts/stage_split_candidate.py`: 명시적 package·외부 pin·새 DATA 디렉터리를 요구하는 CLI.
- `tests/test_candidate_staging.py`: 작은 합성 package/복사 시험.

기존 materialization·planner·validator·BoundedJSONIO 및 readiness/CLI/API/UI는 수정하지 않는다. 71의 metadata receipt가 존재한다는 이유만으로 신뢰하지 않고, 별도 caller pin과 실제 JSON 바이트·전체 candidate validator를 결합한다.

## 입력 계약과 경계

필수 인자는 package 디렉터리, 외부에서 고정한 receipt SHA, 외부 source/readiness/saved_plan SHA 3개다. `input_pins`는 이 세 키만 허용하며 각 값과 receipt SHA는 exact string 소문자 64hex다. receipt 내부에서 pin을 꺼내 그대로 외부 신뢰 기준으로 사용하는 방식은 허용하지 않는다.

receipt의 세 input path는 문자열 타입·길이·local 경로·DATA/evidence confinement·외부 pin·실제 size/SHA를 확인한 후 사용한다. 따라서 CLI는 중복 input path를 받지 않는다. 그 경로는 저장 계획/원본 readiness 참조와 full validator에도 결합되어야 한다.

DATA와 evidence root는 **어느 방향으로도 겹치면 안 된다**. source/readiness는 DATA 안, saved_plan과 package는 evidence 안, 새 staging 디렉터리는 DATA 안이어야 한다. 기존 부모 디렉터리만 지원하고 기존 대상/깨진 symlink/원격·UNC·URL/drive-relative/ADS·Windows 장치명·끝점/공백·경계 이탈을 거부한다. 입력 세 파일, package plan/candidate/receipt는 canonical 대상 및 device/inode가 각각 다른 일반 파일이어야 한다.

package 파일 이름은 정확히 `plan.json`, `candidate.json`, `receipt.json`이다. 출력 이름은 `candidate.json`, `staging-receipt.json`으로 고정한다.

| 입력/출력 | 한도 |
|---|---|
| 원본 source / readiness / saved plan | 64 / 16 / 4MiB |
| package plan / candidate | 4 / 64MiB |
| package receipt | 64KiB |
| staged candidate | 64MiB, 원본 candidate와 동일 byte 수/SHA |
| staging receipt | 64KiB |
| JSON container 깊이 | 32 |

package receipt는 전용 `BoundedJSONIO` context의 saved_plan 역할 cap을 **64KiB**로 줄여 읽고 재검증한다. stat 크기만 제한한 뒤 일반 4MiB reader를 쓰는 형태가 아니다. 읽는 중 성장해도 최대 cap+1까지만 읽고 거부한다. 나머지 다섯 JSON은 기존 역할별 cap의 별도 context를 사용한다. 두 context 모두 마지막에 확인한다.

## receipt의 엄격한 소비 검증

schema_version1, kind `EVIDENCE_SPLIT_CANDIDATE_RECEIPT`, status `METADATA_ROUNDTRIP_VERIFIED`, candidate_status `PLANNED_DERIVED_CANDIDATE`, readiness_status `BLOCKED`, scope `PINNED_JSON_METADATA_ONLY_NOT_RASTER_READINESS`를 exact typed 값으로 검사한다. metadata_integrity_verified는 정확히 true, refund는 exact int0, exactly_once는UNKNOWN이어야 한다.

15개 false 필드를 모두 exact false로 확인한다: raster_readiness_rechecked, source_rows_modified_or_reassigned, executed, learning_ready, ready_for_training, scientific_accuracy_validated, source_authenticity_verified, exact_row_binding_verified, spatial_overlap_rechecked, exact_class_counts_recomputed, training_split_leakage_resolved, execution_authorized, registry_called, settlement_authorized, automatic_resume_allowed. 숫자0을 false로 인정하지 않는다.

최상위/inputs/outputs/reference의 키 집합도 정확히 검사한다. input 3개의 path/SHA/bytes, output 2개의 고정 basename/SHA/bytes, 고정 6주 map·version 형식·물리 행 partition·projected 계수를 확인한다. bool/float는 정수 size/count가 아니다. `completion_contract`는 제한된 문자열로 검사하며 특정 영어 문구 전체를 동일성 기준으로 삼지는 않는다. 여기서 exact schema는 키/타입/주요 상태 계약이 정확하다는 뜻으로, receipt JSON 자체가 producer와 바이트 동일하다는 주장과 다르다.

## 처리와 원문 복사

1. package receipt를 caller SHA로 strict bounded 읽기·검증한다. source/readiness/saved plan과 package plan/candidate의 경계·크기·실제 SHA를 확인한다.
2. caller-pinned saved plan과 package plan의 **전체 typed JSON equality**를 확인한다. receipt version/projected·source/candidate/excluded 물리 행 수를 실제 객체와 대조한다.
3. 기존 `validate_split_repair_plan`을 package plan/source/readiness/candidate SHA·고정 split map·같은 bounded context로 **한 번** 호출한다. 내부 planner 재계산·exact retained rows/lineage·비실행 상태까지 확인한다. 검증 결과의 raster/class/spatial 재검사 false도 확인한다.
4. 두 context와 roots/package/output parent identity를 재확인하고, 새 DATA 디렉터리를 exclusive로 예약한다. 경합으로 생긴 기존 디렉터리/파일은 보존하고 거부한다.
5. candidate 원문을 65,536바이트 이하 요청으로 읽어 `xb` 출력에 복사한다. 재직렬화·newline 변환을 하지 않는다. 예정 byte 수/cap·원본 descriptor/stat·실시간 SHA를 확인하고, 조기 EOF·성장·변경/다른 SHA를 거부한다. 새 staged 파일도 기존 bounded reader로 SHA·JSON equality를 확인한다.
6. 작은 staging receipt를 측정한 뒤, 원본/package와 staged 파일 전체·두 context·roots/parents/새 디렉터리 identity를 다시 확인한다. 마지막에 staging receipt만 exclusive로 기록한다.

staging receipt는 status `METADATA_STAGED_FOR_QA`, next_step `NEXT_QA_NOT_PERFORMED`, qa_status `NOT_PERFORMED`다. 원본 package receipt pin·외부 input 3pin·package output 2pin·DATA-relative staged path/SHA/size·version·행 수/projected 계수를 담는다. metadata_integrity_verified/original_candidate_bytes_preserved는 true지만 qa/assess/등록/실행/학습준비/과학/원본인증/exact binding/공간·클래스/누출해소/원본행변경/정산·재개 승인은 false, refund0, exactly_onceUNKNOWN이다.

물리 candidate 행 수는 적격 패치 합계와 다르다. 이 복사는 원본 1384행/적격1111이나 후보 projection을 다시 평가하거나 변경하지 않는다. 원본 영상/라벨/QA 픽셀·다른 source manifest·모델·Registry·Job·네트워크는 접근하지 않는다. source/readiness/candidate JSON 읽기·SHA와 raster/픽셀 QA를 구분한다.

## 실패·증거 해석

입력/상태/크기/roundtrip/복사/최종 안정성/영수증 쓰기 실패는 예외를 낸다. 부분 candidate/부분 staging receipt·이미 생성한 디렉터리는 자동 삭제하지 않는다. **receipt가 없거나 잘린 JSON·schema/status/falseflags·staged SHA/size가 잘못되면 미완료**다. 파일 존재만으로 다음 QA를 허용하면 안 된다.

마지막 검증 직후 영수증을 쓰고, 성공처럼 보이는 영수증을 만든 뒤 입력 재검사 실패를 반환하는 순서는 사용하지 않는다. 그 사이 OS 수준 동시 변경은 가능하므로 다중 파일 원자 snapshot/commit을 보장하지 않는다. 역할별 cap은 각 read/write에 한하며 누적 IO·메모리·CPU/time hard cap도 아니다. 다음 소비자가 다시 pin/영수증을 검증해야 하며 staging 완료 자체는 학습·운영 승인과 무관하다.

## CLI와 합성 시험

```powershell
python scripts/stage_split_candidate.py `
  --data-root data `
  --package-dir evidence/integration/<verified-package> `
  --receipt-sha256 <external-receipt-pin> `
  --source-sha256 <external-source-pin> `
  --readiness-sha256 <external-readiness-pin> `
  --saved-plan-sha256 <external-saved-plan-pin> `
  --output-dir data/<new-qa-staging-directory>
```

CLI는 repository evidence를 고정하고 명시 새 DATA 출력 디렉터리가 필수다. 상대 package/output은 cwd 기준 absolute로 만들되 logical alias를 먼저 resolve하지 않는다. stdout은 stage/QA 미수행 상태·행 수/projected·ready/registered false의 ASCII JSON이며, stderr도 ASCII escape하여 CP949에서 안전하다. 기존 경로 재실행은 덮어쓰지 않는다.

최종 관련 시험: **19 PASS / 23.740초 / 종료0**, `evidence/integration/candidate-staging-related-20261017.log`.

```powershell
$env:PYTHONPATH="$PWD\.runtime;$PWD\backend;$PWD\tests"
python -m unittest test_candidate_staging -v
```

작은 합성 package만 사용했다. exact receipt/15false·외부 필수3pin·size bool·basename traversal·고정map/row/version/projected 변조, strict UTF8/중복/비유한/depth/cap·receipt64KiB 성장 실제65537바이트 차단, 별도context·full validator1회/QA claim 거부·old/newplan typed equality, 무assess/무제한read trap·identical byte/SHA·조기EOF/변경·package logical retarget·roots 겹침·scope/Windows·경합/부분복사/부분영수증·원본 변경 시완료차단·CP949/재실행 보존을 확인했다. 초기15/17건 실행은 최종19건과 중복 합산하지 않는다. CLI 합성 DATA는 고유 repository DATA 임시 디렉터리, evidence는 별도 임시 경로로 분리해 실제 운영 경계를 유지했다. 기존 호환 시험은 Root 전체 회귀에 포함되어 담당이 반복 실행하지 않았다.

Root가 실제 staging1회와 전체 회귀·137보호 참조/30기존 계약·catalog 보존·운영 인계/이해자료를 맡는다. 실제 후보 readiness QA는 다음73의 별도 명시 작업이며 이번에는 수행하지 않는다. 새 API/UI/자동 Dataset 등록이 없는 내부 단계이므로 화면 변경은 없다. 단일 staging 완료는 전체 프로젝트 완료나 학습 준비성 통과를 뜻하지 않는다.

## Root 실제 QA용 메타데이터 복사 확인

CP949 CLI 1회가 종료0으로 완료됐다. 새 `data/first-group-candidate-qa-stage-20261017/candidate.json`은 53,247,999바이트, SHA256 `2ff7be093db3930d99f10cdc7687809222ef7f525ec6e9cf6248ec144725d158`로71 evidence 후보와 동일하다. `staging-receipt.json`은 3,675바이트, SHA256 `b8224cb3eb5c5ef0accf0cab10359401d792719e6fd8cae0b610279e759404dd`다. Root가 생성 코어를 다시 호출하지 않고 두 후보의 스트림 SHA/크기·확인서의 외부pin/패키지참조·17개 false상태·행계수를 대조했다.

후보1368행/원본1384행/계획적격1095(628/217/250)가 연결된다. 원본의 기존 적격1111(628/233/250)은 그대로다. 단계는 `METADATA_STAGED_FOR_QA/NEXT_QA_NOT_PERFORMED`, 실제 후보 준비성은 **NOT_ASSESSED**다. 영상·라벨 파일 복사·assess·Registry·훈련·정산·자동재개는 없다. 메타데이터를 DATA 안에 놓았다는 사실이 학습 준비나 물리 파일 인증을 뜻하지 않는다.

근거는 `evidence/integration/candidate-staging-live-cli-20261017.log`와 `candidate-staging-live-validation-20261017.json`이다. Root의 첫 독립 대조에서는 경로 예상값을 slash로 작성하여 Windows의 backslash 상대 경로와 달라 실패했다. 예상값을 `str(Path(...))`로 고쳐 같은 산출물을 재대조해 통과했으며 생산 코드 변경·CLI 재실행은 없었다. 실제 실행 초수는 별도 정밀 계측하지 않았다. 전체 회귀와 보존 근거는 아래 최종 마감 절에 기록했다.

## 다음 후보 QA 경계 — PLANNED

다음73은 staged candidate·staging 확인서·정책의 외부SHA와 새 QA출력을 고정하고 기존 `run(..., execute=False, resume=False, connectivity_diagnostics=True)`만 호출하는 작은 QA 전용 guard다. 72의 전체 계획 재계산을 반복할 필요는 없지만, 확인서와 후보 바이트를 고정한 범위를 넘어 과학적 승인을 주장하지 않는다. 역사적 동일 정책까지 자동 검증하려면 네 번째 입력인 old readiness의 pin을 확인하고 `{**default_policy(), **policy}`와 저장된 정책을 타입까지 대조한다. 기존 CLI에는 `--readiness-only` 플래그가 없다.

차단된 QA 결과도 검사 자체의 정상 완료일 수 있다. 예외·입력 변경 시 새 보고서는 보존하되 마지막 QA완료확인서를 만들지 않는 방식으로 미검증 결과를 구별한다. 기존 DATA 경계·assess·원본분할·gate를 바꾸지 않으며 준비/훈련/추론으로 진입하지 않는다. 이 guard와 후보 QA는 아직 구현·실행하지 않았다.

## 최종 전체 회귀·보존·인계

전체725개 중724 PASS·기존1 SKIP,338.008초,종료0이다. 관련19 PASS/23.740초와 독립19 PASS/25.510초는 같은 시험의 반복 확인이며 전체에 중복 합산하지 않는다. SKIP은 기존 Windows symlink 생성 권한 제약이다. 보호참조137개(기존134+71패키지3)/기존코어30개 SHA, catalog14행 canonical SHA가 불변이며 기존 추적 backend/scripts/tests/data/frontend 변경0이다. 새 DATA 파일2개와 새 구현4파일을 추가했으므로 전체 workspace 불변을 뜻하지 않는다. 근거는 `candidate-staging-live-integrity-20261017.json`, `candidate-staging-full-tests-20261017.log`다.

기존 원본 준비성 보고서의 차단5건은 보존했다. 새 후보의 실제 QA 차단 수는 아직 알 수 없다. 관련71의 원본 계보·상태 설명, 운영원장·소유권·인계서와 이해자료를 같은 단위로 갱신한다. 새 공개 API/UI 계약이 없는 내부 복사 CLI이므로 UI 변경이나 브라우저 시험을 수행했다고 주장하지 않는다. 전체 개발과 10분 보고 예약을 유지한다.

## 후속 실제 후보 QA — 구현73

[73 QA 전용 호출](73_candidate_readiness_qa.md)이 같은 후보/확인서 SHA와 기존정책을 고정해 실제 영상·라벨 준비성을1회 검사했다. 후보QA는 완료됐으며 1095적격/차단4건으로 blocked다. 기존 staging확인서의 QA NOT_PERFORMED는 생성시점 기록으로 변경하지 않고 새73 QA완료확인서를 연결한다. 원본5차단/원본139보호 참조는 보존했고 등록·정식훈련은 없다. 최신상태와해시/한계는73 문서를 참조한다.
