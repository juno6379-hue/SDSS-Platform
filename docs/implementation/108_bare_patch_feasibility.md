# 108. 저장 나지 집계의 기여 패치 필요 범위

상태: **TESTED_SYNTHETIC / BLOCKED / STORED_AGGREGATE_NECESSARY_BOUNDS_ONLY**. 기존 76의 저장 집계에 정수 capacity 모형의 필요 범위만 추가한다. 실제 보고서의 pinned CLI 관측은 Root의 별도 근거로 구분한다. 영상·라벨·QA 파일 읽기, readiness assess, 새 수집·학습·등록·배포는 실행하지 않는다.

## 왜 총 픽셀이 있어도 기여 패치가 0인가

기여 패치는 나지 픽셀이 하나라도 있는 패치가 아니라 **한 패치 안에 최소 256픽셀** 있는 경우만 센다. split 전체의 나지 총합과 이 조건을 만족하는 패치 수는 다른 집계다. train의 총합1418이256보다 크더라도 여러 패치에 얇게 나뉘었다면 기여0과 모순되지 않는다. 정확한 분포를 복원한 것은 아니며 저장된 기여0과 총량이 양립 가능한지만 산술로 설명한다.

[76](76_bare_class_requirements.md)은 split 총량256의 부족0/47/0, 기여 패치5개 부족5/5/5, 비율 조건을 이미 구별한다. 108은 이를 다시 구현하지 않고 원 결과를 그대로 embed한다. 추가하는 것은 **해당 총량이 허용하는 기여 수의 하한/상한**과 요구 기여 수를 위한 집계상 필요 총량 조건이다. 어느 것도 충분한 readiness 조건이 아니다.

## 모형·수식과 가정

E는 같은 집계에 사용된 eligible 패치 수, B는 해당 패치들의 저장 class7 픽셀 총합, T는 패치 한 개의 기여 threshold, C는 패치의 픽셀 capacity다. 기존 76이 patch_size256을 검증하므로 C=256²=65536을 사용한다. 정수 모형에서 각 패치의 class7 픽셀은 0..C다. 필요한 최소 기여 수를 R이라 한다.

기여 패치가 k개라면 총량의 최대는 다음과 같다.

```text
B ≤ k*C + (E-k)*(T-1)
L = max(0, ceil((B - E*(T-1)) / (C-T+1)))
U = min(E, floor(B/T))
```

L..U는 이 단일 class 정수 capacity 모형의 기여 수 범위다. 구현은 float 대신 정수 ceil을 사용한다. 실제 QA에는 valid mask·주 경계·다른 class·비율·기간·원본 독립성 등 추가 제약이 있으므로 이 범위 안이라고 전체 QA가 타당하거나 재분배가 가능하다는 뜻이 아니다. 현재 동일 eligible 집계라는 전제와 patch capacity만 이용한 **필요 경계**다.

요구 기여 R개를 위해서는 최소 R*T 픽셀이 필요하고 E≥R이어야 한다. `max(0,R*T-B)`는 이 필요 총량과 현재 저장 총량의 차이다. **미래에 추가로 수집할 픽셀/패치/장면 수가 아니고, 재분배·재라벨링 권고도 아니다.** 새 자료는 E·B·비율 분모·품질 조건을 함께 바꾸므로 이 값을 다운로드나 수집 지시로 사용하지 않는다.

## 저장 예제와 해석

다음은 신규 시험의 합성 집계 예제이며 기존 고정 보고서의 숫자와 같다. Root의 실제 pinned 실행은 별도 증거로 보고한다.

| split | E | B | 저장 기여 수 | L..U | R*T | 필요 총량 차이 | 76의 split floor 차이 |
|---|---:|---:|---:|---|---:|---:|---:|
| train | 628 | 1418 | 0 | 0..5 | 1280 | 0 | 0 |
| val | 217 | 209 | 0 | 0..0 | 1280 | 1071 | 47 |
| test | 250 | 1025 | 0 | 0..4 | 1280 | 255 | 0 |

세 저장 기여0은 모두 이 범위 안이다. val 총량209는 T256보다 작아 모형에서 기여0만 가능하다. test는 총량만으로도 기여5를 만들 수 없다. train은 상한5가 가능하다는 필요 경계일 뿐 **실제 기여5가 있다는 뜻이 아니며** 저장 기여는 여전히0이다. val의1071과 기존47은 서로 다른 필요 조건의 차이라 혼합하지 않는다.

현재 readiness 보고서는 `prepared_payload=null`이며 최종 QA per-patch class histogram을 저장하지 않는다. 참조 candidate의 `sample_class_coverage`는 source taxonomy의 patch 통계이고 `label_first_preview.class_counts`는 확대 원본 예비 분포다. 이를 최종 QA eligible 집계의 정확한 row/mask/label 통계라고 새로 입증하지 않고 가져오지 않는다. 108 reader는 candidate를 열지 않으며 source 코드8→모델 class7과 같은 의미 대응만으로 최종 per-patch 분포를 인증하지 않는다.

## 구현·원 결과와 모순 진단

- [bare_patch_feasibility.py](../../backend/app/ml/bare_patch_feasibility.py)의 `build_bare_patch_feasibility(report, reference)`는 기존76 build를 정확히1회 호출하고 원 결과를 `stored_requirements`에 그대로 담는다. pure reference의 SHA는 caller 선언이며 실파일 검증이 아니다.
- `inspect_bare_patch_feasibility(data_root, expected_report_sha256)`는 기존76 pinned reader를 정확히1회 호출한다. 같은 report 최초 read+최종 verify의 **2회 읽기**만 사용하고 새 파일 접근을 추가하지 않는다. 기존 source manifest·영상·라벨·candidate를 열지 않는다.
- private `_contribution_bounds`는 E0..3000·C1..65536·T1..C·B0..E*C의 정확한 int만 다룬다. 작은 C/T 시험은 수학 oracle 범위이며 public report 정책의 T256 이상·patch256을 완화하지 않는다.

새 결과는 schema_version1, kind `BARE_CLASS_PATCH_AGGREGATE_FEASIBILITY`, status 항상 `BLOCKED`, scope `STORED_AGGREGATE_NECESSARY_BOUNDS_ONLY`다. `by_split`에는 E/B/저장 기여 수/T/C/R, L/U, 저장 기여의 범위 내 여부, E와 U가 R 이상인지의 필요 조건, R*T와 필요 총량 차이를 담는다.

기존76은 `P*T≤B` 등을 확인하지만 L보다 낮은 저장 P까지 모두 거부하는 기능은 아니다. 새 `observed_count_within_aggregate_bounds`, 전체 `stored_contributing_counts_within_aggregate_bounds`, `inconsistent_splits`는 이런 모순을 추가 관측한다. 모순이 있어도 원76 결과나 gate를 덮어쓰지 않고 읽기 진단으로 표시한다. 예를 들어 E1/B65536/T256/저장P0은 L=U=1이라 모순이다. 진단 반환의 성공이나 CLI exit0은 데이터 승인·학습 준비의 의미가 아니다.

새 결과의 per-patch 복원·픽셀 재검사·eligibility 재산출·ready/과학/실행/수집/학습·미래 장면/다운로드/픽셀 요구량 추정·재분배/재라벨링 권고·full gate·원본/정답/manifest/공간/누출/정책 변경 관련20 flag는 모두 false다. 원76의 false flags·부족/비율/분모·pin 상태도 그대로 보존한다. network_requests/source_files_written은0이다.

## CLI와 안전한 출력

[inspect_bare_patch_feasibility.py](../../scripts/inspect_bare_patch_feasibility.py)는 기존76과 같은 제한을 재사용한다.

```powershell
python scripts/inspect_bare_patch_feasibility.py `
  --data-root data `
  --expected-report-sha256 847343e1aa4ab9b67fd3bba36a2a9f91d716c2fd411af244e55bbfe1a8414019 `
  --output evidence/integration/<new-bare-patch-feasibility>.json
```

입력은 고정 report JSON 하나, 외부 SHA 필수, 16MiB/depth32·strict UTF-8/중복/비유한 수·일반 local 파일·DATA confinement·stat/fstat/target 및 전후 SHA 확인을 기존 reader가 책임진다. SHA/stat 확인을 OS 원자 snapshot이나 현재 원본 라벨 검증으로 부르지 않는다.

출력이 있으면 repository evidence 안·DATA 밖의 새 경로만 허용하고 input 별칭·기존 파일·symlink/remote/ADS/장치명·끝점 등을 거부한다. 64KiB output cap은 부모/파일 생성 전에 측정하고 exclusive write한다. stdout은 ASCII JSON, 오류도 CP949에서 ASCII 안전하게 출력한다. 부분 출력 실패 시 자동 삭제·원장/lock 수정·자동 재개하지 않는다. byte cap은 누적 I/O·RAM/CPU hard cap이 아니다.

## 시험·증거

[신규 시험](../../tests/test_bare_patch_feasibility.py)은 실제 영상 없이 작은 합성 저장 통계와 정수 배열을 사용한다.

```powershell
# 프로젝트 루트, PYTHONPATH=.runtime;backend;tests;프로젝트루트
python -m unittest test_bare_patch_feasibility -v
python -m unittest test_bare_patch_feasibility test_bare_class_requirements test_ml_readiness test_split_bounded_io -v
```

- 집중 신규 **12 PASS / 4.474초**: [집중 로그](../../evidence/integration/bare-class-patch-feasibility-focused-20261017.log).
- E0..4/C1..5/T1..C의 모든 작은 정수 배분을 독립 전수 열거해 실제 기여 수의 min/max와 수식을 대조했다. E0·T=C·threshold 직전/직후·full capacity·bool/float/hugeint/범위 오류를 확인했다.
- 0/1071/255와 기존0/47/0 분리·train 상한5에도 관측0/readyfalse·E<R·관측P<L 진단·76 원 결과/1회 호출/strict 오류·pure 무IO/assess0/입력 불변을 확인했다.
- reader는 report2open/원 byte 보존, pin·stale·duplicate/nonfinite·깊이·remote 참조 거부를 확인했다. CLI는 새 evidence·nooverwrite·CP949·별칭/장치명·출력cap 선검사를 확인했다.
- 최초 관련 명령의 `test_readiness`, `test_split_json_io`는 실제 모듈명이 아니어서26개 통과 후 import error2(총28/9.166초)였다. [최초 로그](../../evidence/integration/bare-class-patch-feasibility-related-20261017.log)를 보존했다. 제품/시험 변경 없이 실제 `test_ml_readiness`, `test_split_bounded_io`로 고친 최종 **66 PASS / 24.207초**의 [관련 로그](../../evidence/integration/bare-class-patch-feasibility-related-corrected-20261017.log)를 근거로 사용한다.

신규12개와 관련/독립 묶음은 중복 합산하지 않는다. 기존제품을 수정하지 않는 분리된 메타데이터 관측이므로 이번 전체 backend/frontend·build·브라우저는 재실행하지 않는다. 직전 전체1069건/1068 PASS/기존1 SKIP/354.65초는107의 이전 근거다. Root의 실제 CLI·독립 검토·보존·인계/이해자료 갱신을 별도 기록한다.

## UI·다음 범위

공개 API/UI와 연결하지 않아 새 화면 상태·판정 변화가 없으며 직접 프론트 수정·build·브라우저 재시험이 필요하지 않다. 기존 데이터·모델·분할·gate를 보존한다. 후속 데이터 확보 판단에는 실제 자료 적격성·라벨/픽셀·기간/주 경계·독립성·누출 검사와 승인이 별도로 필요하다. 이 산술표만으로 수집량을 정하거나 정식 학습을 시작하지 않는다.

## 108 — 저장된 나지 기여 패치 수의 산술 진단 완료

기존76 부족 조건을 보존하고 같은 적격 patch 집계의 기여 개수 하한/상한을 계산하는 순수 helper·고정 보고서 reader wrapper·수동 CLI를 추가했다. E개 patch·bare B픽셀·patch상한C65536·기여 문턱T256에서 lower=max(0,ceil((B−E(T−1))/(C−T+1))), upper=min(E,floor(B/T))이다. 이는 정수 capacity 모형이며 실제 분포 재구성·라벨 재배치 권고·미래 수집량 추정이 아니다.

현재 범위는 train0..5/val0..0/test0..4이고 저장된 기여0은 모두 범위 내다. 최소5개 기여에 필요한 집계 총량1280 대비 차이는0/1071/255로 기존76 절대바닥0/47/0과 다르다. train도 총량만으로 실제5개 기여를 보장하지 않는다. 모든 ready/학습/수집/과학·실행 승인 false와 원래 QA차단4를 유지한다.

신규12 PASS/4.474초·관련 정정66 PASS/24.207초·독립26 PASS/10.286초다. 독립 oracle29001분포/1015집계는 추가 시험 건수로 합산하지 않는다. 최초 관련 명령은 존재하지 않는 두 모듈명을 지정해 importerror였으며 최초로그를 보존하고 명령만 정정했다. Root는 실제 고정 report SHA847343…4019로 CLI를 실행해 exit0/9230B를 확인하고 helper없는 독립 산술과 대조했다. 저장 JSON 산술이며 현재 영상·라벨 재QA/과학 검증이 아니다.

기존 코드·프론트 변경0, 보호141·이전 증거791·catalog14·원장/lock/예약136314880B·분할·모델 보존이다. reader는 기존76을1회 사용해 고정 보고서만2회 읽고 영상/candidate/assess·다운로드·운영Job·등록·새운영QA·학습·배포0이다. 독립된 신규 내부 module/CLI라 관련·독립·보존으로 검증했고 전체backend/front/build/browser는 재실행하지 않았다. 이전107 전체1069건/1068PASS/1SKIP/354.650초는 이전 근거다. 새API/UI 경로가 없어 UI 수정은 필요 없다.

구현108과 관련76·인계/원장·이해자료를 함께 갱신했다. 담당 영역별 잔여 핵심 작업은109 재검토 문서로 별도 추적하며 전체 개발 미완료다. 수집2건 terminal누락과 정산/aggregate commit 절차는 후속 후보이고 원장차이가 특정crash를 입증하지 않는다. Git은 사용자 지정 juno6379-hue/SDSS-Platform의 기존main d483d25 기준으로 연결했고 현재 변경분 커밋/푸시 준비 중이다. 원본 데이터·인증/환경파일은 새 커밋에서 제외한다. 예약ACTIVE와 실제 에이전트/수집/학습을 구분하며10분 보고를 유지한다.

근거: `evidence/integration/bare-class-patch-feasibility-live-integrity-20261017.json`, `evidence/integration/bare-class-patch-feasibility-live-20261017.json`, `evidence/integration/bare-class-patch-feasibility-independent-review-20261017.json`, `evidence/integration/bare-class-patch-feasibility-collection-next-review-20261017.json`. 최종 감사/snapshot은 `evidence/integration/bare-class-patch-feasibility-closeout-20261017.json`을 따른다.

