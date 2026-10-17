# 76. 저장된 나지(class7) 부족 조건의 읽기 계약

상태: **VERIFIED_REAL(저장 JSON 메타데이터) / TESTED_SYNTHETIC / BLOCKED / READONLY_REQUIREMENTS_ONLY**. 후보 QA 보고서에 저장된 class7 통계와 정책을 대조하여 현재 부족 조건을 구분한다. 새 장면 수·수집/다운로드량·정확 라벨 요구량·학습/수집 승인을 산출하지 않는다. 실제 CLI1회는 Root가 수행했으며 아래 근거에 기록했다. 전체 회귀·보존·운영/이해자료 갱신은 Root의 별도 근거이며, 저장 메타데이터 검증을 영상 정확도 검증으로 확대하지 않는다.

## 구현과 고정 입력

신규 `backend/app/ml/bare_class_requirements.py`에는 순수 `build_bare_class_requirements(report, reference)`와 `inspect_bare_class_requirements(data_root, expected_report_sha256)`가 있다. `scripts/inspect_bare_class_requirements.py`는 stdout 또는 새 evidence 출력만 제공하고, `tests/test_bare_class_requirements.py`는 작은 합성 저장 통계를 사용한다. 기존 코어/API/UI는 수정하지 않는다.

고정 DATA 입력은 `first-group-candidate-readiness-qa-20261017/readiness.json`이다. 외부 SHA는 caller가 명시하며 이번 실제 대상은 `847343e1aa4ab9b67fd3bba36a2a9f91d716c2fd411af244e55bbfe1a8414019`다. 파일은16MiB/depth32·strict UTF8/no BOM/NUL·중복 키/비유한 수 거부·일반 파일·DATA confinement·local/Winsafety·stat/fstat/논리target·SHA를 최초/최종 확인한다. root retarget나 중간 바이트 변경은 거부한다. 보고서 하나만 두 번 읽고 source/candidate manifest·영상/라벨/QA 파일을 열거나 hash하지 않는다.

순수 build의 reference는 caller 선언이다. 반환 `pin_validation=CALLER_DECLARED_REFERENCE_ONLY`는 파일 SHA를 실제 검증했다는 뜻이 아니다. reader만 바이트 pin과 finalverify가 끝난 뒤 `PINNED_REPORT_BYTES_AND_STABILITY_VERIFIED`로 표시한다. 두 경우 모두 독립 과학/현재 원본 검증이나 VERIFIED_REAL 정확도 주장이 아니다.

## 현재 후보에 한정한 입력 검증

현재 저장된 blocked/ready=false/science=false 보고서만 지원한다. fixed4/1/1 province split·patch256, class7 이름bare·기존 label source, required class exact int0..8/중복 없음/최소2개/7포함을 확인한다. 이 helper는 default_policy의 모든 일반 범위를 지원하는 기능이 아니라 기존 후보의 보수적 저장 계약에 한정한다.

| 정책 항목 | 지원 범위 | 현재 값 |
|---|---|---:|
| min_class_pixels_per_split | exact int256..65536 | 256 |
| min_class_patches_per_split | exact int5..3000 | 5 |
| min_class_pixels_per_patch | exact int256..65536 | 256 |
| min_required_class_ratio | 유한 number .005이상,1미만; bool 제외 | .005 |
| max_reference_class_dominance | 유한 number 0초과,.90이하; bool 제외 | .90 |

정책을 완화하거나 기존 보고서를 수정하지 않는다. eligible 각 split0..3000, class pixel/class patch 배열 각9개 exact unsigned int를 확인한다. NumPy로 계산하기 전에 다음 교차식으로 모순/overflow를 막는다.

- 각 class patch count ≤ 해당 split eligible patch count.
- 각 class patch count × min_class_pixels_per_patch ≤ 해당 class pixel count.
- 9개 class pixel 합 ≤ eligible patch count ×256².

여러 class가 같은 patch에 기여할 수 있으므로 **9개 class patch count의 합 ≤ eligible**라는 제약은 적용하지 않는다. eligible1에 class0/class7 각256픽셀·각1기여 patch인 합성 양성 사례를 통과시켰다. 이는 나지 기여 patch 부족5를 새 장면5개로 바꾸어도 된다는 뜻이 아니다.

## 서로 다른 부족 조건과 수식

각 split에서 B=저장 class7 픽셀, P=저장 class7 기여 patch 수, D=같은 split의 저장9클래스 픽셀 합이다.

| 출력 | 수식/뜻 |
|---|---|
| split_pixel_shortfall | max(0, min_class_pixels_per_split − B) |
| contributing_patch_shortfall | max(0, min_class_patches_per_split − P) |
| minimum_bare_pixels_per_contributing_patch | 이미 기여로 세는 patch 하나가 포함해야 하는 class7 최소 픽셀 |
| bare_ratio | D>0이면 B/D, 아니면 null |
| bare_ratio_shortfall | D>0이면 max(0, min_required_class_ratio − B/D), 아니면 null |
| bare_ratio_threshold_met | D>0이고 B/D ≥ min_required_class_ratio |
| dominant_class_ratio | D>0이면 max(9 class pixels)/D, 아니면 null |
| dominance_threshold_met | D>0이고 dominant ratio ≤ max_reference_class_dominance |
| all_bare_conditions_met | 절대 픽셀 부족0·기여 patch 부족0·나지 비율 조건 충족의 교집합 |

비율 분모는 전체 raster 크기, eligible×65536, mask 전체 또는 bare 픽셀만이 아니라 **저장된 해당 split의 9클래스 reference 픽셀 합**이다. 비율은 fraction 단위이며 .005는0.5%다. ratio shortfall도 픽셀 수가 아닌 비율 차이다.

기존 순수 `readiness.balance_diagnostics`를 class 배열/정책만으로 split별 다시 호출하여 저장 `reference_balance_by_split`의 passed·9개 ratio·class patch counts·dominant ratio·failures·interpretation 전체를 typed 동일성으로 대조한다. 전체 저장 balance 산술을 확인하지만 실제 픽셀/품질/적격성 gate를 재실행하지 않는다. 이때 다른 required class 부족도 저장 함수와 같은 순서/값으로 확인하며 bare 한 항목만 맞추어 전체 balance가 통과했다고 표시하지 않는다.

D=0이면 기존 함수는9개 ratio를0으로 저장하고 dominant ratio는null로 반환한다. 그 저장 계약 자체는 그대로 재대조한다. 별도 요구 출력에서는 분모가 없으므로 bare ratio/ratio shortfall/dominance를null로, 해당 threshold 충족은false로 명시한다.

## 고정 후보의 현재 저장 관측

아래는 Root의 별도 독립 산술과 연결할 현재 후보 통계다. 신규 합성 시험과 실제 CLI 출력은 구분한다.

| split | eligible | bare pixels | 절대 픽셀 부족 | 기여 patch/최소 | 기여 patch 부족 | D |
|---|---:|---:|---:|---|---:|---:|
| train | 628 | 1418 | 0 | 0 /5 | 5 | 40149113 |
| val | 217 | 209 | 47 | 0 /5 | 5 | 13989243 |
| test | 250 | 1025 | 0 | 0 /5 | 5 | 16252940 |

bare ratio는 각각 약 `3.531833941138376e-05`, `1.4940050723259293e-05`, `6.306551307025068e-05`이며 모두 .005 미만이다. dominant ratio 조건은 세 split 모두 충족하지만 각 저장 balance의 failures에는 `class7_pixel_ratio`, `class7_patch_representation`가 남는다.

**val에47픽셀을 보충하면 충분하다는 뜻이 아니다.** 절대 픽셀 바닥만 맞아도 기여 patch5개 조건과 비율 조건은 별도로 남는다. train/test의 bare 픽셀 총량이256 이상이어도 분포가 얇으면 기여 patch0일 수 있다. 또한 추가 유효 자료는 비율 분모 D 자체를 바꾸므로, 현재 비율 차이를 미래 추가 픽셀/patch/장면/다운로드량으로 환산하지 않는다. 이 구현은 고정분모 ceil 환산량도 출력하지 않는다.

## 출력 schema와 승인 한계

최상위는 schema_version1, kind `BARE_CLASS_STORED_REQUIREMENTS`, status `BLOCKED`, scope `READONLY_REQUIREMENTS_ONLY`, report_reference, pin_validation, class_index7/namebare, fixed_province_splits, eligible_patch_count, by_split3개다. split별 출력 키는 다음과 같다.

```text
eligible_patches, bare_pixels, minimum_split_bare_pixels, split_pixel_shortfall,
contributing_class_patches, minimum_contributing_class_patches,
contributing_patch_shortfall, minimum_bare_pixels_per_contributing_patch,
reference_class_pixel_total, bare_ratio, minimum_bare_ratio, bare_ratio_shortfall,
bare_ratio_threshold_met, dominant_class_ratio, maximum_dominant_class_ratio,
dominance_threshold_met, all_bare_conditions_met,
stored_reference_balance_passed, stored_reference_balance_failures
```

전체 저장 balance 메타 재계산/동일성은 true로 표시한다. 반면 pixels_rechecked·source_manifest_currently_verified·requirements_are_full_gate·새 장면/다운로드량 추정·정확 라벨 요구 인증·정책 변경·47픽셀만으로 ready 보장·공간/원본 독립성 검증·ready/과학/원본진실성/exact binding/수집·학습·등록·실행·정산·자동재개·누출 해결은 모두 false다. refund0/exactly_onceUNKNOWN/source 쓰기0/네트워크0이다.

source_manifest_reference는 보고서에 저장된 선언이며 현재 source 파일을 검증했다는 뜻이 아니다. 미래 자료도 원래 province 고정 분할을 유지하고 기간·품질·경계·라벨·동일 source/영역 중첩·독립성 검사를 통과해야 한다. 이 helper가 그 미래 자료의 적격성을 검사하거나 독립 정답 라벨/운영 승인을 정하는 것은 아니다.

## CLI·실패 정책

```powershell
python scripts/inspect_bare_class_requirements.py `
  --data-root data `
  --expected-report-sha256 847343e1aa4ab9b67fd3bba36a2a9f91d716c2fd411af244e55bbfe1a8414019 `
  --output evidence/integration/<new-bare-requirements>.json
```

출력 옵션이 없으면 전체 ASCII JSON stdout만 반환한다. output이 있으면 repository evidence 안·DATA 밖·입력과 다른 새 경로만 허용하고 크기64KiB를 파일/부모 생성 전에 측정한다. 기존 파일/깨진 symlink/별칭·원격/ADS·장치명·끝점/공백을 거부하고 논리 target/parent를 재검사한다. UTF8 evidence는 exclusive binary로 쓰며 stdout/stderr는 CP949에서도 ASCII로 안전하게 출력한다.

출력 중 예외가 나면 부분 새 파일을 자동 삭제하지 않고 기존 입력·원장·lock도 건드리지 않는다. 역할별 read cap은 누적 IO/RAM/CPU hard cap이 아니다. 전후 SHA/stat 확인과 exclusive write는 다중 파일 OS 원자 snapshot을 보장하지 않는다. 이 CLI는 새로운 후보·수집·학습·배포나 gate 변경을 실행하지 않는다.

## 합성 시험과 인계

최종 관련 시험: **14 PASS /5.019초 /종료0**, `evidence/integration/bare-class-requirements-related-20261017.log`.

```powershell
$env:PYTHONPATH="$PWD\.runtime;$PWD\backend;$PWD\tests"
python -m unittest test_bare_class_requirements -v
```

작은 합성 통계를 사용하여0/47/0와5각 분리·분모/비율·dominance·저장 balance 전체 typed 변조·0분모·bool/float/hugeint/NaN·정책 완화 거부·class 기여 최소픽셀 교차식·같은 patch의 multi-class 양성·47픽셀만으로 조건 충족 안 됨·순수 무IO/입력 불변·pure/reader pin 범위 분리·고정1JSON2open/바이트 보존·외부 pin/크기/strictJSON/stale/remote 참조·새 evidence/한도/Win별칭/CP949를 확인했다. 초기13/14 반복 실행은 최종14건에 중복 합산하지 않는다.

독립 검토도 **14 PASS /5.679초 /종료0**이며 `evidence/integration/bare-class-requirements-independent-20261017.log`에 기록했다. 같은14개 시험의 독립 재실행이므로 관련 시험과 합산하여28개라고 보고하지 않는다.

## 실제 저장 보고서 검증 근거

Root가 고정 후보 QA 보고서의 외부 SHA를 명시하여 CLI를 **1회** 실행했다. CP949 환경에서 종료0이며 새 출력 `evidence/integration/bare-class-requirements-live-20261017.json`은5367바이트, SHA256 `8a0004aa2d67af8c97e32173f90c56c97449e54317ef86420489eb1bbaee7542`다. 실행 로그는 `evidence/integration/bare-class-requirements-live-cli-20261017.log`다. 담당 구현/독립 에이전트는 이 실제 CLI를 중복 실행하지 않았다.

`evidence/integration/bare-class-requirements-live-validation-20261017.json`은 CLI 출력의 선택된 산술 필드가 별도 `evidence/integration/bare-class-requirements-independent-arithmetic-20261017.json`과 타입·값 모두 일치하며, 입력 보고서 SHA가 유지됨을 기록한다. 실제 관측은 위 표의 절대 픽셀 부족0/47/0, 기여 patch 부족5/5/5, 비율 세 split 미달·dominance 세 split 충족과 같다. 현재 저장 조건을 재현했을 뿐 미래 자료량·영상/정답 정확도·누출 해소·전체 gate 통과를 입증하지 않는다.

Root 최종 전체 backend 회귀는775개 중774 PASS·기존 Windows symlink 제약1 SKIP /332.522초/종료0이다. 근거는 `evidence/integration/bare-class-requirements-full-tests-20261017.log`이며 관련/독립14건은 중복 합산하지 않는다. 전체 시험 종료 뒤 보호141참조/기존코어34 SHA·catalog14행 canonical SHA를 다시 확인했고 직전추적 backend/scripts/tests/data/frontend 변경0이다. 새구현/증거추가나문서변경까지없다는뜻/OS원자snapshot보장은아니다. `bare-class-requirements-live-integrity-20261017.json`을 따른다. 다음77은 제출시고정 ordered input binding과 실행기에 전달할 binding의 id/version/SHA/role/index 및 Job/Agent/Trace를 대조할 순수 검증 계약의 PLANNED 검토다. 기존 불변 버전등록·입력해석·제출snapshot/현재계보검사와 구별하며 정확schema/legacy누락처리는 후속설계다. 실제 등록 쓰기나 READY 우회는 계획에 포함하지 않는다. 공개 API/UI를 추가하지 않는 내부 요구 관측 CLI라 이번 직접 화면 변경은 없다. 전체 프로젝트와 나지 부족 데이터 수집/정답 검증 과제는 계속 진행 중이며 이번 요구표가 완료 승인은 아니다.

## 108 집계 기여 patch 수 후속 진단

[108 구현](108_bare_patch_feasibility.md)은 원76을 그대로 사용하고 정수 capacity 모형의 기여 개수 범위와 최소5기여에 필요한 집계량 조건을 별도로 보여준다. 현재0..5/0..0/0..4와 차이0/1071/255는 기존 절대바닥0/47/0을 대체하지 않는다. 실제 분포·라벨/미래 자료 요구량이나 전체gate 통과를 추론하지 않는다. 기존 코드/reader/API/UI를 수정하지 않았고 관련 시험·Root 실제 저장 산술·보존은 `evidence/integration/bare-class-patch-feasibility-live-integrity-20261017.json`을 따른다.
