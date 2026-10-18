# 164. 우선 수집 자료의 고정 후보 전처리 명령

## 쉬운 설명과 범위

수집 중인 전체 목록을 그대로 긴 QA에 넣으면 검사 중 목록이 바뀔 수 있다. 새 명령은 사용자가 정한 SHA의 목록을 별도 사본으로 고정하고, 그 사본의 실제 파일 QA·동일 장면 누출 제외·새 후보 저장·후보 실제 QA를 기존 구현으로 연결한다. 뒤에 새로 수집된 자료는 해당 실행에 포함하지 않는다.

소스는 `scripts/prepare_priority_candidate164.py`, 집중 시험은 `tests/test_prepare_priority_candidate164.py`다. 기존159/153 runner를 재사용 가능한 CLI로 정리한 작은 내부 진입점이며 기존71/72/73의 guard나 품질 기준을 바꾸지 않는다. 새 API·수집기·학습기·UI pointer·원장·분할·모델·계정은 수정하지 않는다.

상태: **TESTED_SYNTHETIC** 집중9PASS/1.111초·종료0. 실제 명령은 **VERIFIED_REAL — source QA303.140초·새 후보 QA335.141초·종료0**, **BLOCKED — 나지 균형·학습·독립 정확도 승인**이다. 최종 summary는 2026-10-18 11:29:17 KST 생성했다.

## 명시 입력과 실행

```powershell
python -X utf8 -u scripts/prepare_priority_candidate164.py `
  --data-root E:/GeoAI–MLOps–SDSS/data `
  --source E:/GeoAI–MLOps–SDSS/data/first-group-training-esri-v1/annual-window-report.json `
  --source-sha256 <명시한 현재 원본 SHA256> `
  --policy E:/GeoAI–MLOps–SDSS/data/first-group/experiment-esri-v003-2020-2025.json `
  --policy-sha256 <명시한 기존 정책 SHA256> `
  --run-id cohort-20261018
```

source/policy/DATA는 명시 절대 로컬 경로이며 DATA 안에 있어야 한다. 정책은1MiB, source snapshot은64MiB 상한이다. run-id는 영문 소문자/숫자 시작, 소문자·숫자·하이픈의1~48자만 허용한다. 원본과 정책은 서로 달라야 한다. 제품 CLI의 evidence root는 저장소 `evidence/integration`으로 고정한다. 시험 함수의 evidence_root 인자는 임시 테스트 root용이다.

이 실행은 새 `data/priority164-<run-id>/`와 `evidence/integration/priority164-<run-id>/`만 생성한다. 어느 하나라도 이미 존재하거나 symlink이면 실행을 거부한다. **재실행 안전은 기존 결과·부분 결과를 덮어쓰지 않는다는 뜻이며 자동 resume 기능이 아니다.** 실패한 run의 디렉터리는 자동 삭제·재사용하지 않는다. 운영자가 새 실행을 정당화한 뒤 새 run-id와 새 source SHA를 명시해야 한다.

## 순서와 산출물 계약

1. caller source/policy SHA를 확인하고 새 경로를 exclusive 예약한다.
2. source를1MiB chunk로 읽어 새 source.json에 복사한다. 최대64MiB·원래 크기·원바이트 SHA·device/inode/크기/mtime을 복사 전·후 확인한다. 복사 후 source 또는 snapshot SHA가 달라지면 중단한다.
3. 고정 사본의 행이 비어 있지 않고 image/label/quality 경로가 모두 절대경로인지 확인한다. 다른 디렉터리로 복사된 manifest의 상대경로를 잘못 해석하지 않는다.
4. 사본에 기존 `readiness.assess(..., connectivity_diagnostics=True)`로 실제 파일·라벨·품질·공간·클래스 검사를 수행하고 새 source-readiness.json을 기록한다.
5. 새 source readiness pin으로 기존 `plan_split_repair`/`write_plan`,71 `materialize_split_candidate`,72 `stage_split_candidate`를 호출한다. test → val → train 고정 우선순위와 원본 retained 행 계보를 기존 bounded validator가 검산한다.
6. 새 staged candidate·staging receipt·기존 policy·새 source readiness의4개 pin으로73 `assess_staged_candidate`를 호출한다. execute=False/resume=False이며 실제 candidate readiness/QA receipt를 새 경로에 쓴다.
7. 입력 pin을 다시 확인하고 readiness verified_files의 실제 파일 SHA를 다시 계산한다. 불일치가 없을 때만 새 evidence summary.json을 기록한다.

summary는 source 시점/SHA·물리/적격/분할계수·제외행수·원본/후보 blocker·나지 픽셀/기여패치·관측 gate ready·부가 connectivity capture 상태·파일검증수·산출물 SHA/bytes를 담는다. `observed_gate_ready_for_training`은 실제 gate 관측이고 summary의 `ready_for_training`은 false다. 이 명령 자체는 학습·실행·과학·Registry 승인 권한을 주지 않는다.

성공은 exit0와 `PINNED_CANDIDATE_QA_COMPLETED`, 처리 오류는 exit2와 `PREPROCESSING_INCOMPLETE`다. 진행 JSON에 SNAPSHOT_PINNED/SOURCE_QA_COMPLETE/CANDIDATE_STAGED를 출력한다. source/policy pin·파일/품질/readiness 오류의 부분 산출물은 남기며 rollback·정산·자동 retry·삭제를 주장하지 않는다. argparse의 필수값/형식 오류는 기존 argparse exit2다.

이전 실행의 결과를 검증해 재개하는 기능은 없다. 순차 파일 검사이므로 OS 원자 snapshot·프로세스 간 불변 저장소·TOCTOU 완전 방어·정확히 한 번 실행을 보장하지 않는다. 과도한 전체 backend 회귀 대신 이번 새 경로 안전성 집중 시험과 실제 native QA를 근거로 삼는다.

## 시험 근거

`evidence/integration/priority164-focused-20261018.log`: 집중9PASS/1.111초·종료0. 정확 복사/exclusive 생성·stale pin/잘못된run-id/상대 또는 외부source 거부·기존/부분run 보존·QA중단 뒤 사본 보존/재실행거부·복사 중 원본 변경 검출·byte cap·상대 raster 경로 거부를 임시 파일과 명시 QA mock으로 확인했다. 실제 raster QA의 과학적 성능이나 네트워크 수집을 합성시험으로 검증했다고 표현하지 않는다.

## 실제 실행 관측

2026-10-18 **11:06:45 KST**, source **1,536행/59,763,442B**를 고정했다. SHA는 `0f04a075a599f4ff74f111652c070c33c817ce668ffba2b7fde1df000731d2cf`, 정책 SHA는 기존 `01991d69bc26487d4ef890de72689da092806bc58cc80ca5f6d6026cf3c79ed7`이다. 1,512행 과거누계나159의1,432행 후보를 현재 QA 결과로 재사용하지 않는다.

실행 로그는 `evidence/integration/priority164-actual-20261018.log`, 사전 근거는 `priority164-cohort-20261018/preflight.json`, 프로세스 관측은 `priority164-owned-process-20261018.json`이다. 새 source 사본은 `data/priority164-cohort-20261018/source.json`이다. 실제 owned 실행은 하나이며 별도 collector를 시작하지 않았다.

source 실제 QA는 303.140초로 적격 **1,235개(Train720/Validation265/Test250)**를 확인했다. 차단은 기존 source 분할 충돌1건과 나지 비율·기여패치 부족3건, 총4건이다. 나지 픽셀은1,586/600/1,025이며 충분한 나지 기여패치는0/1/0이다. 검증용 나지600픽셀로 절대256픽셀 바닥 차단은 해소됐지만 각 split비율0.5%·기여5패치 조건은 충족하지 않는다. source verified파일4,811개와 부가connectivity `NOT_CAPTURED_BUDGET`를 기록했다.

| 실제 QA 결과 | 고정 source | 새 후보 |
|---|---:|---:|
| 물리 행 | 1,536 | 1,520 |
| 적격 패치 | 1,235 | 1,219 |
| Train / Validation / Test 적격 | 720 / 265 / 250 | 720 / 249 / 250 |
| QA 차단 | 4 | 3 |
| 동일 source 분할 충돌 차단 | 1 | 0 |
| 나지 픽셀 | 1,586 / 600 / 1,025 | 1,586 / 600 / 1,025 |
| 충분한 나지 기여 패치 | 0 / 1 / 0 | 0 / 1 / 0 |
| 준비 / 과학 인증 | false / false | false / false |

반텐16행을 새 후보에서만 제외했고 기존 source/분할/모델을 바꾸지 않았다. 후보 실제 QA는335.141초로 완료했고 나지 비율·기여패치3차단이 남았다. metadata 준비·반복 bounded JSON 검산·파일 재검산 시간은 위 두 QA 시간 외에 추가 소요됐다.

| 산출물 | SHA256 |
|---|---|
| 고정 source | `0f04a075a599f4ff74f111652c070c33c817ce668ffba2b7fde1df000731d2cf` |
| source readiness | `51ec2003a90c9dc5a2a2cf72de1708bec6ad1b44f10020e2b04c8aa30e71cd9a` |
| evidence/staged 후보 동일 바이트 | `706dbc0a67b9186c21fa579504c74f58bfdd4930530f09209e8e977c992678c3` |
| 후보 readiness | `03ca6e9786ebb639cf72cbf0ad7335d4e9952aacf3cf429405ec53b0e93b7168` |
| 후보 QA receipt | `79a6cd26bb92f3e2cf1620b9be7e0767bd475202ee8d2a3116b81af575ec3f93` |

entry는 검증된4,761개 파일의 SHA를 최종 재계산해 불일치0을 확인했다. 별도 `priority164-final-verifier-20261018.py`도 entry/planner를 다시 호출하지 않고 후보 전체행과 source retained행·partition 완전성·교차split source identity0·산출물11개pin과 실제4,761개 파일 SHA를 다시 계산했다. **20.922초·종료0·불일치0**, 근거는 `priority164-final-verification-20261018.json`과 `priority164-final-verifier-20261018.log`다.

부가connectivity 진단은 `NOT_CAPTURED_BUDGET`이며 component mapping/witness는 미수집이다. 기존 max_scenes2000/max_bbox_pairs1,000,000/max_witness_edges10000 한도를 보존했다. 후보1,520행의 bbox pair 수1,154,440이1,000,000을 넘는다. 실제native readiness 검사·파일SHA검산을 건너뛴 것이 아니며 부가 witness 완료로도 표현하지 않는다. metadata/source identity 충돌0은 완전한 공간 독립성·독립 현장 라벨 인증을 뜻하지 않는다.

실제 수치·시간·누출/나지/부가진단 한계와 모든 source/candidate/QA pin을 Root에 전달했다. Root/web_ui가 API·실서버·브라우저 반영을, 이해 담당이 설명·대본·FAQ·INDEX/변경이력을 맡는다. 이 내부 명령만 추가했으므로 이번 담당은 UI를 직접 바꾸지 않았다. 원본 source의11:06:45 이후 추가 수집분은 새 실행에서 검사해야 하며 총량1200 달성만으로 학습 준비를 승인하지 않는다. 네트워크·수집·학습·추론·Registry 호출0, 원본/모델/원장/예약/기존153·159/UIpointer/계정 쓰기0이다.

### Root 게시 및 실제 화면 확인

별도 `priority164-ui-promote-20261018.py`가 고정 source/candidate/QA 지문과 최종4761파일 검산 증거를 확인한 뒤 공개 receipt와 pointer를 게시했다. 이전1125 pointer는 `candidate-pointer-before164-20261018.json`으로 원바이트 보존했으며 게시 지문은 `d432cb8ec91bdfe903f751f40d27a83064b91ce0938740fb4ad358e85c595067`이다. Registry/모델/학습 승인은 변경하지 않았다.

`priority170-final-ui-20261018.json/txt/png`의 실제 IAB 관측은 원본1260(744/266/250), 고정후보1219(720/249/250)/차단3/미준비를 구분하고 source SHA 불일치 경고를 표시했다. 후보는1536행 source의 시점에 고정돼 있으므로 이후25개 적격(7차24+표적1)을 포함하지 않는다. 원본과 후보 적격 차이41에는 후보에서 제외한16개도 포함된다. 원본 선언 나지 표를 후보 native QA로 대신하지 않는다.
