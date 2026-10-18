# 159. 첫 우선 수집 19개 적격 패치를 포함한 새 고정 후보 QA

## 현재 범위와 진행 상태

**VERIFIED_REAL — 고정 cohort 실제 QA 완료, BLOCKED — 학습·독립 정확도 승인.** 2026-10-18 10:30:23 KST의 수집 aggregate **1,432행**을 새 경로에 원바이트로 고정했다. 이전153의 1,400행 사본에서 수행한 후보 QA를 새19개 패치 검증으로 재사용하지 않았다. 이번에는 해당19개를 포함한 사본의 전체 실제 raster QA부터 시작하고, 기존71/72/73의 후보 생성·staging·QA를 다시 수행했다. source QA164.672초, 후보 QA216.0초, runner 종료0, 최종 후보 QA는 10:46:09 KST 완료다. metadata 생성·staging 시간은 이 두 raster 시간 외에 추가 소요됐다.

새 사본은 `data/priority-ml-next-snapshot-20261018/annual-window-report.json`, 55,742,976바이트, SHA `7eac5a54cce152f1f3163e35e8565217b6cbef61b86068150209bb39fa3a9bbe`다. 원본 읽기 전·후 SHA가 같음을 확인하고 새 파일을 exclusive 생성했다. 모든 영상·라벨·품질 artifact 경로가 절대경로이므로 다른 디렉터리의 사본도 같은 실제 raster를 읽는다.

이것은 첫 우선 수집의 남동술라웨시2024/고론탈로2025 신규32물리·19적격을 포함한 cohort다. 이후 round3 수집이 진행되어 원본 aggregate에 추가되는 행은 **이번 고정 사본에 포함되지 않는다**. 최신 수집기 누계와 이 후보의 원본 시점·SHA·계수를 계속 분리해서 표시한다.

## 실행과 소유권

- runner: `evidence/integration/priority-ml-next-20261018-runner.py`
- 실행 로그/고정 입력: `priority-ml-next-20261018-runner.log`, `priority-ml-next-20261018-preflight.json`
- 시작 시 owned Python PID39472, session80310. 프로세스 종료 후에는 실행 중이라고 표현하지 않는다.
- 새 staging: `data/priority-ml-next-stage-20261018/`
- 새 후보 QA: `data/priority-ml-next-readiness-20261018/`
- 새 evidence package: `evidence/integration/priority-ml-next-20261018-candidate-package/`

이 작업자는 위 새 경로와 문서159만 소유한다. 이전153의 원본 사본/후보/QA/문서·기존1,095후보·계정·정책·원본 aggregate·모델·원장·예약·lock·UI pointer를 수정하지 않는다. 네트워크·수집·학습·추론·Registry 등록은 호출하지 않는다. 별도 수집 프로세스가 원본을 갱신하는 동작은 이 QA 작업자의 쓰기와 구분한다.

## 재사용하는 검사

1. 고정 사본에 기존 `readiness.assess(..., connectivity_diagnostics=True)`를 실제 호출한다. 밴드·라벨·품질·공간·클래스·source 분할 조건을 같은 정책으로 검사한다.
2. 새로운 source readiness pin을 사용하여 `plan_split_repair`를 수행한다. 고정 test → val → train 우선순위에 따라 새 후보에서만 충돌 행을 제외하고 원본 행을 삭제하거나 split을 재배정하지 않는다.
3. 기존71의 metadata roundtrip과72의 동일 바이트 staging을 통과한 뒤 기존73 `assess_staged_candidate`를 `execute=False`, `resume=False`로 호출한다.
4. 별도 final-verifier가 원본 retained행·후보 전체행·partition 완전성·scene/source group/image SHA cross-split 충돌과 실제 검증 파일 SHA를 다시 계산한다.

정책 SHA는 `01991d69bc26487d4ef890de72689da092806bc58cc80ca5f6d6026cf3c79ed7`이며 주별4/1/1분할·유효80%·주내95%·나지비율0.5%·256픽셀·기여패치5개·지배90%를 낮추지 않는다. 단일 metadata 검사로 과학적 정확도나 전체 공간 독립성을 승인하지 않는다.

## 결과와 인계 규칙

최종 근거는 새 `priority-ml-next-20261018-summary.json`, 후보 QA의 `qa-receipt.json`, 별도 `-final-verification.json`이다.

| 항목 | 고정 원본 사본 | 새 누출 제외 후보 |
|---|---:|---:|
| 물리 행 | 1,432 | 1,416 |
| 품질 적격 | 1,141 | 1,125 |
| Train / Validation / Test 적격 | 658 / 233 / 250 | 658 / 217 / 250 |
| 실제 QA 차단 | 5 | 4 |
| 동일 source 분할 충돌 차단 | 1 | 0 |
| 나지 픽셀 Train / Validation / Test | 1,432 / 209 / 1,025 | 1,432 / 209 / 1,025 |
| 충분한 나지 기여 패치 | 0 / 0 / 0 | 0 / 0 / 0 |
| 학습 준비 / 과학 정확도 인증 | false / false | false / false |

원본 인덱스288~303의 반텐16행을 새 후보에서만 제외했다. 남은4차단은 train/val/test 나지 비율·기여패치 부족3건과 검증용 나지209/256픽셀 부족1건이다. 첫 추가19적격 패치가 train 나지14픽셀에 기여했음을 실제 raster QA에서 확인했으나 기준 미달을 해소하지 못했다.

| 산출물 | SHA256 |
|---|---|
| 원본 사본 | `7eac5a54cce152f1f3163e35e8565217b6cbef61b86068150209bb39fa3a9bbe` |
| source readiness | `85e4565749818209ebbaaa5f762ebfdf24d8096c78b786c169cdf6c1a42546de` |
| evidence/staged candidate 동일 바이트 | `d8dad13a22278a8cdddfeb56f7fb746e2d51523b01ac866689dde2018a48b01c` |
| 후보 readiness | `cec0666793c8ba9d9e049d8042850f0784edc6ebb7d7996d7432220ddb0f19b4` |
| 후보 QA receipt | `d2c16e6aeeadd5af0de8abd4961c77cf31471175ab5f738b7b6d8e4d29ceff14` |

별도 final-verifier는 기존 planner/validator를 다시 호출하지 않고 retained행 전체가 원본과 정확히 같은지, 보존·제외 partition이 완전한지, scene/source group/image SHA에 교차split 충돌이 없는지 독립 대조했다. 산출물9개 SHA/크기와 실제 QA verified파일 **4,435개 SHA를 다시 계산해 불일치0**, **10.328초·종료0**을 확인했다. 고정 source·정책·기존1,095후보 SHA도 유지됐다.

**부가 connectivity 진단 한계:** source와 후보의 부가 진단은 `NOT_CAPTURED_BUDGET`이며 component mapping/witness는 미수집이다. 기존 한도 max_scenes2000/max_bbox_pairs1,000,000/max_witness_edges10000을 보존했다. 후보1,416행의 bbox pair 수1,001,820이 한도를 넘는다. 이를 전체 native QA 실패나 모든 파일 미검사로 표현하지 않으며, 반대로 부가 component witness도 완성됐다고 표현하지 않는다. 실제 readiness gate는 raster·공간·source 검사를 수행했고 분할충돌 차단은 없으며, 위 독립 대조는 선언된 source identity와 파일 SHA 범위의 검산이다. 완전한 과학적 공간 독립성·현장 정답 승인은 아니다.

실행 종료 시 활성 aggregate SHA는 `c57a1768a87fae7b0fd0c5ec8e451c439d35c65bf54d99f1f7b38dc98928e33e`로 변경 관측됐다. 이후 추가 수집분은 이번 후보·실제 QA에 포함하지 않는다. 새 source snapshot과 새 candidate/readiness를 구별하여 UI에 전달해야 한다.

기존 코드의 반복 bounded JSON 재검산은55MB급 입력에서 시간이 걸렸다. guard 우회나 이전 QA receipt 복사 없이 source/candidate/QA 단계를 새로 수행했다. 코드 변경이 없는 실제 자료 재검사이므로 새 전체 단위시험 대신 실제 QA·기존 guard·독립 파일 재검산이 검증 근거다. 네트워크·수집·학습·추론·Registry 호출0이며 원본·이전153·분할·모델·원장·예약·계정·UI pointer 쓰기0이다.

UI 영향은 새 API 구현이 아니라 검증된 새 cohort 통계·시각·SHA·차단의 게시다. 이 담당은 최신 UI pointer를 바꾸지 않으며 완료 결과를 Root/web_ui에 전달한다. Root가 실제 API·브라우저 반영과 이해 담당 자료를 통합한다. 이번 후보 QA 완료를 전체 학습 준비·운영 승인·프로젝트 완료로 표현하지 않는다.
