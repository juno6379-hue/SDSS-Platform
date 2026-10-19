# 193 — 복구 수집1,666행의 고정 학습 후보 전처리·실제 QA

상태: **VERIFIED_REAL — 고정 source와 후보의 native QA 및 파일 SHA 검산 완료**. **BLOCKED — 나지 비율·기여 패치3차단, 학습·과학 정확도 승인 미완료**. 기존164 제품 CLI를 새 run-id로 단1회 사용했다. 신규 품질 가드·코드 복제·원본 분할/라벨/모델 변경·HTTP·훈련·Registry 호출은 없다.

## 입력과 실행 경계

Root가191 수집/native 감사를 끝내고 source와 ledger를 고정한 뒤 이 실행을 배정했다. 192의190proposal37개에 대한 full179 support 검토는 다른 담당의 별도 검사이며 이193 학습 후보 파이프라인을 중복 실행한 것이 아니다. Root는192/193 완료 동안 새 collector를 시작하지 않았다.

명시 원본은 `data/first-group-training-esri-v1/annual-window-report.json`, **1,666행/64,839,496바이트**, SHA `ab745b908e2e0adce80907554216c0529e950c7e0123a7f85ee664cf26d50d0f`다. source cap **64MiB=67,108,864바이트 이내**임을 확인했으며 상한을 확장·우회하지 않았다. 기존 정책은 `data/first-group/experiment-esri-v003-2020-2025.json`,1,306바이트·SHA `01991d69bc26487d4ef890de72689da092806bc58cc80ca5f6d6026cf3c79ed7`다.

```powershell
python -X utf8 -u scripts/prepare_priority_candidate164.py `
  --data-root E:/GeoAI–MLOps–SDSS/data `
  --source E:/GeoAI–MLOps–SDSS/data/first-group-training-esri-v1/annual-window-report.json `
  --source-sha256 ab745b908e2e0adce80907554216c0529e950c7e0123a7f85ee664cf26d50d0f `
  --policy E:/GeoAI–MLOps–SDSS/data/first-group/experiment-esri-v003-2020-2025.json `
  --policy-sha256 01991d69bc26487d4ef890de72689da092806bc58cc80ca5f6d6026cf3c79ed7 `
  --run-id recovery193-20261018
```

새 `data/priority164-recovery193-20261018/`와 `evidence/integration/priority164-recovery193-20261018/`, 동명 실행 로그만 사용했다. 시작 전 모두 미존재였다.13:05:47.543 KST에 snapshot을 고정했고13:16:59.685 KST에 `PINNED_CANDIDATE_QA_COMPLETED`, exit0로 완료했다. 중단·재실행·기존 부분 결과 덮어쓰기는 없었다.

## 실제 결과

| 항목 | 고정 source | 새 후보 |
|---|---:|---:|
| 물리 행 | 1,666 | 1,650 |
| 품질 적격 | 1,333 | **1,317** |
| Train / Validation / Test 적격 | 791 /292 /250 | **791 /276 /250** |
| 차단 항목 수 | 4 | **3** |
| 교차 split source 충돌 차단 | 1 | **0** |
| 실제 나지 픽셀 train/val/test | 2,562 /2,998 /1,025 | 2,562 /2,998 /1,025 |
| 나지256픽셀 이상 기여 패치 | 1 /2 /0 | **1 /2 /0** |
| 학습 준비/과학 인증 | false /false | **false /false** |

source native QA는 **129.343초**, 후보 native QA는 **133.235초**다. source verified file 기록은5,221개, 후보 최종 실제 파일 SHA 재검산은 **5,171개·불일치0**다. 두 QA의 중복 파일 수를 합산하지 않는다. 이 명령은 실제 영상·라벨·품질·경계·클래스와 기존 gate를 검사했으며 새 모델을 훈련하지 않았다.

## 제외한16행의 정확한 의미

기존 제품의 고정 우선순위 **test → val → train**에 따라 새 후보에서만16행을 제외했다. 제외된 것은 **반텐2021년 validation 패치16개(원본 row index288~303)**이며 모두 같은 원본 scene `S2A_MSIL2A_20210812T025551_R032_T48MXT_20210812T132431`에 연결된다. 서자바 test와 겹치는 기존 source identity를 후보에서 분리한 것이다. **16개 scene을 수리했다는 뜻이 아니다.**

plan의 `remaining_source_identity_conflicts=0`이고 후보 실제 readiness에서도 `SHARED_SOURCE_CROSSES_FIXED_SPLIT` blocker는 없다. 원본1,666행·기존 split·라벨 파일을 수정하거나 삭제한 것은 아니다. Root는 retained row의 exact 일치와 retained/excluded partition 완전성도 후속 검산했다. 이 결과를 독립 현장 정답·전체 공간 독립성·모든 미래 자료 누출 방지 인증으로 확대하지 않는다.

## 나지 차단이 남는 이유

기존 정책은 split마다 나지 비율 **0.5% 이상**, **256픽셀 이상을 가진 기여 패치5개 이상**을 요구한다. 후보의 실제 값은 다음과 같다. source code8을 모델 내부 class7과 구분한다.

| split | 실제 나지 픽셀 | 실제 유효 라벨 전체 | 나지 비율 | 기여 패치 /최소5 |
|---|---:|---:|---:|---:|
| train | 2,562 | 50,499,630 | 약 **0.005073%** | **1 /5** |
| val | 2,998 | 17,776,457 | 약 **0.016865%** | **2 /5** |
| test | 1,025 | 16,252,940 | 약 **0.006307%** | **0 /5** |

세 split 모두 `REFERENCE_CLASS_IMBALANCE`이며 detail은 각각 `class7_pixel_ratio`·`class7_patch_representation`이다. 절대256픽셀 부족 차단은 이번 결과에 없지만 비율·분산 조건이 따로 남는다. 반텐 실제2,199픽셀과 남동 실제814픽셀 확보는 성과이나 나지 전체 gate 해결은 아니다. 독립 정답·모델 정확도·학습/운영 승인도 별도다.

## 긴 staging 단계의 의미

source QA 뒤 `CANDIDATE_STAGED`까지는71/72 제품의 strict metadata 검산 단계다. 약64.8MB source·64.2MB candidate를 BoundedJSONIO로 반복 읽어 source/readiness/plan pin, exact retained row, 왕복 검산, 파일 identity·입출력 SHA를 확인한다. 해당 materialize/stage 함수는 `assess`나 전체 raster QA를 다시 수행하지 않는다. 실제 candidate native QA와 최종5,171개 파일 SHA 재검산은 stage 뒤에 수행한다.

관측 당시 PID31056은3초 간격 샘플에서 user CPU가3.4375초 증가했고 입출력 카운터는 같았다. candidate/plan은13:09:15, package receipt는13:11:37, DATA candidate는13:13:56, staging receipt는13:14:39에 생성됐다. 당시 활동과 생성물을 확인하고 건너뛰거나 프로세스를 종료·재실행하지 않았다. 메타데이터 검증 시간을 두 native QA 시간에 포함해 설명하지 않는다.

부가 connectivity capture는 `NOT_CAPTURED_BUDGET`이다. 실제 파일 QA·SHA 검산을 생략한 것이 아니며 부가 component/witness를 확보했다고도 표현하지 않는다. 이 실행이 관측한 gate 준비도도 false다.

## 산출물과 지문

| 산출물 | SHA256 |
|---|---|
| 고정 source | `ab745b908e2e0adce80907554216c0529e950c7e0123a7f85ee664cf26d50d0f` |
| source readiness | `10bec774167335da2305579b5bae0e31494dba266a018e20985038c2006a8aab` |
| split plan | `4c2db8596ad7ca09cf87d5d9a4a53e6dc0efb3869101454a48918a4b8e925804` |
| evidence/staged candidate 동일 bytes | `7f74f3cae27bc1cdbedd994ac56d1e01465dff4308ea4e3d1c7860fced6c3912` |
| candidate readiness | `c20e7322958ea52b4d98f8e842754f5f65c8108d512641178a107af3149058bc` |
| candidate QA receipt | `8fc5c553f1ca27c2a33d2c7f99eed03fb249232d256b329484ef1b736b6fb1b1` |

전체 output11개 지문·byte 수와 source/후보 blocker는 `evidence/integration/priority164-recovery193-20261018/summary.json`에 있다. 원본 source와 기존 policy의 현재 SHA가 종료 후에도 그대로임을 확인했다. 수행자는 원장·기존 후보·pointer·라벨·모델을 수정하지 않았다.

## 실제 브라우저 후속 — 13:18:35 KST

`service193-195-final-ui-20261018.json`과실제PNG/DOM에서 현재 원본1333·셀33과새후보1317(791/276/250)/나지3차단·source현재일치를 확인했다. 나지37보고서도고론탈로·서자바2행/미탐색범위설명/원격품질미검사·집행미승인을표시했다.console0·가로넘침0이다. 이검증뒤Root가target196최대2남동표적을전검사에넣었으므로아래후보는이1666행고정source시점의QA이지196미래성과를포함하지않는다. Registry/학습승인변경은없다.

## Root 후속 게시와 UI 구분

**193 제품 CLI 자체는 pointer를 바꾸지 않았다.** Root가 완료 summary/output pin·retained exact row/partition·충돌0·파일 불일치0을 검산한 뒤13:17:46 KST에 기존1,219 후보 pointer를 원바이트 archive로 보존하고 새 **1,317 후보 pointer**를 승계했다. `evidence/integration/priority193-publication-root-20261018.json`은 `COMPLETED_QA_PUBLISHED_AND_READER_VERIFIED`, source 현재 일치·reader의791/276/250·blocker3·학습false를 기록한다. 게시 pointer SHA는 `3f54fb6cbe098a487a3dcd76cc951a3b713dae9aa14a1f3f0f6ccf6d8304b081`이다.

이 문서 작성 시 실제 브라우저 refresh 검증은 web 담당 후속이다. 제품 코드 시험·후보 QA 완료·pointer/reader 게시·실제 서버/브라우저 반영을 구분한다. 후속 수집 뒤에는 이 후보 source 시점이 다시 고정 과거 시점이 될 수 있다. Root와 이해 담당이 완료 증거로 설명·대본·FAQ·INDEX·변경 이력과 공통 인계를 갱신한다. 전체 프로젝트와 나지 보완·모델 학습/검증은 계속 미완료다.
