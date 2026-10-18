# 153. 우선 수집과 분리된 최신 고정 후보의 동일 장면 누출 제거

## 범위와 상태

사용자는 부족한 주·연도 151개와 나지 보완을 우선 수집하고 동일 장면 누출을 제거하도록 요청했다. 이 담당은 **수집 담당과 독립적으로**, 2026-10-18 10:07:15 KST에 확보된 aggregate 사본을 고정하여 기존 후보 생성·staging·실제 raster QA를 재사용한다. 이후 수집기의 aggregate가 바뀌면 이 결과는 그 신규 행에 대한 검사가 아니다.

원본 1,400행/품질 적격 1,122개와 기존 고정 후보 1,368행/적격 1,095개를 혼동하지 않는다. 구 후보·원본·주별 Train/Validation/Test 정책·원장·모델을 바꾸지 않는다. 파일 삭제나 split 재배정을 통해 누출을 숨기지 않고, 충돌 행을 **새 후보에만 제외**한다.

원본 사본과 새 후보의 실제 raster QA는 **VERIFIED_REAL**로 완료했다. source QA 230.906초, candidate QA 239.188초, runner 종료0이며 최종 후보 QA는 2026-10-18 10:26:57 KST 완료했다. metadata 생성/staging의 반복 bounded JSON 검산에 추가 시간이 걸렸으며 초기 전체 약10분 예상보다 오래 걸렸다. 이 두 raster 시간만 합쳐 전체 실행 시간이라고 표현하지 않는다.

원본 사본 QA는 적격 639/233/250=1,122개와 차단 5건을 확인했다. 동일 source가 검증·시험 분할에 걸친 충돌 1건, 나지 비율·기여 패치 부족 3건, 검증용 나지 절대 픽셀 부족 1건이다. 나지 픽셀은 학습 1,418/검증 209/시험 1,025, 충분한 나지 기여 패치는 모두 0개이며 검증된 파일 기록은 4,385개다. 이것은 새 후보의 최종 결과가 아니다.

## 고정 입력과 재사용 흐름

실행 증거는 `evidence/integration/priority-ml-20261018-runner.py`, `-runner.log`, `-preflight.json`이다. runner는 제품 API·학습·수집기를 변경하는 새 구현이 아니라 이미 검증된 기존 함수를 명시 호출하는 이번 실행의 기록이다.

1. 활성 aggregate를 읽기 전·후 SHA가 같은지 확인하고 `data/priority-ml-snapshot-20261018/annual-window-report.json`에 원바이트 전용 생성한다. 사본 SHA는 `9211524656d92f0fcfcdf11f2ec382965e3aeacbc7f80da5b02f4f59784df1e7`, 54,492,684바이트, 물리 1,400행이다.
2. 모든 image/label/quality 경로가 절대경로임을 확인한다. 사본을 다른 디렉터리에 두어도 원래 실제 raster를 읽으며 상대경로 재해석으로 잘못된 파일을 읽지 않는다.
3. 기존 `readiness.assess(..., connectivity_diagnostics=True)`로 사본의 실제 파일·라벨·공간·클래스·scene 분리 gate를 검사하고 같은 새 snapshot 디렉터리에 readiness를 저장한다. 이전 1,111개용 readiness를 최신 1,122개 입력에 재사용하지 않는다.
4. 기존 `plan_split_repair`와 `write_plan`으로 고정 test → val → train 우선순위 계획을 만든다. 클래스·성능 점수에 따라 보존 split을 고르지 않는다.
5. 71의 `materialize_split_candidate`로 새 evidence package, 72의 `stage_split_candidate`로 새 DATA staging을 생성한다. 동일 SHA·정확 행 계보·exclusive 새 경로 계약을 그대로 적용한다.
6. 73의 `assess_staged_candidate`가 4개 외부 pin을 검사하고 `execute=False`, `resume=False`로 실제 후보 raster QA와 영수증을 생성한다.

고정 정책은 `data/first-group/experiment-esri-v003-2020-2025.json` SHA `01991d69bc26487d4ef890de72689da092806bc58cc80ca5f6d6026cf3c79ed7`이다. 구 후보 SHA `2ff7be093db3930d99f10cdc7687809222ef7f525ec6e9cf6248ec144725d158`도 전후 대조한다. 수집기의 mutable aggregate와 원장은 불변 입력으로 취급하지 않는다.

## 결과 판독과 한계

완료 근거는 `evidence/integration/priority-ml-20261018-summary.json`과 새 DATA QA의 `qa-receipt.json`이다.

| 항목 | 고정 원본 사본 | 새 누출 제외 후보 |
|---|---:|---:|
| 물리 패치 행 | 1,400 | 1,384 |
| 품질 적격 | 1,122 | 1,106 |
| Train / Validation / Test 적격 | 639 / 233 / 250 | 639 / 217 / 250 |
| 실제 QA 차단 | 5 | 4 |
| 동일 source 분할 충돌 차단 | 1 | 0 |
| 나지 픽셀 Train / Validation / Test | 1,418 / 209 / 1,025 | 1,418 / 209 / 1,025 |
| 충분한 나지 기여 패치 | 0 / 0 / 0 | 0 / 0 / 0 |
| 학습 준비 / 과학 정확도 인증 | false / false | false / false |

고정 test → val → train 우선순위에 따라 원본 인덱스 288~303의 반텐16행을 새 후보에서만 제외했다. 동일 장면 `S2A_MSIL2A_20210812T025551_R032_T48MXT_20210812T132431`의 서자바 시험용 행은 보존했다. 반텐2021 적격은58→42이며 칸당28 계획 바닥을 여전히 넘으므로 나머지 부족 셀의 합151개는 이 제외로 늘지 않는다.

계획의 `remaining_source_identity_conflicts=0`은 scene ID/source group/image SHA 연결에 대한 metadata 계산이며 전체 공간 독립성이나 과학적 정확도 인증이 아니다. 실제 후보 raster QA에서도 `SHARED_SOURCE_CROSSES_FIXED_SPLIT` 차단은 관측되지 않았다. 남은4건은 train/val/test 나지 비율·기여 패치 부족3건과 val 나지209/256픽셀 부족1건이다. 독립 현장 라벨이 없으므로 실제 정확도 검증은 미확보다.

| 산출물 | SHA256 |
|---|---|
| 고정 원본 snapshot | `9211524656d92f0fcfcdf11f2ec382965e3aeacbc7f80da5b02f4f59784df1e7` |
| 새 source readiness | `0439acdc66063a4635641d954ec2d4a6aa14d0b3678cdb669a3b3f779a95b261` |
| 새 evidence/staged candidate 동일 바이트 | `6556d3b85ed6d70f5951f430195740e21cb04feacc509c6ce20d726755cb3cf6` |
| 새 후보 readiness | `aa8076a9d09652ae6dbe4cc880d33d7ae8d302b2333e8ce719846df00d432042` |
| 새 QA receipt | `c53112c30e2929b0b822fe9af1ce51cf4866f9e9e0a946ea44f5658d080dc7bf` |

원본 snapshot·정책·구1,095후보의 최종 SHA는 모두 유지됐다. 수집기의 활성 aggregate는 실행 중 `7eac5a54cce152f1f3163e35e8565217b6cbef61b86068150209bb39fa3a9bbe`로 바뀌었다. 이는 관측값이며 이번 입력으로 사용하거나 해당 최신분을 검사했다고 주장하지 않는다. 신규 수집 결과가 확정되면 별도 새snapshot·후보·QA가 필요하다.

별도 `priority-ml-20261018-final-verifier.py`는 기존 planner/validator를 다시 호출하지 않고 원본 retained행과 후보 전체 행의 일치·제외/보존 partition 완전성·scene/source group/image SHA의 분할간 충돌0·산출물9개의 SHA/크기를 검산했다. 실제 QA가 기록한 **4,335개 파일 SHA도 다시 계산하여 불일치0**, **9.125초·종료0**을 확인했다. 근거는 `priority-ml-20261018-final-verification.json`과 `-final-verifier.log`다. 파일 전후 관측은 OS 원자 snapshot이나 독립 현장 정답 인증이 아니다.

나지는 모델 class 7(ESRI 원분류 8)이다. 분할별 절대 256픽셀·0.5% 비율·256픽셀 이상 기여 패치 최소 5개 조건은 유지한다. 누출 제외가 성공해도 나지 부족을 자동 해소하거나 품질 미달 패치를 적격으로 바꾸지 않는다. 독립 현장 정답·모델 승인·운영 학습은 별도 차단이다.

이번 작업자의 네트워크·수집·학습·추론·Registry 등록은 0이며 새 snapshot/계획/package/stage/QA/증거/문서만 기록한다. 실제 운영 수집은 Root와 별도 data 담당의 단일 coordinator가 담당한다. 새 제품 코드·API 계약을 바꾸지 않았으므로 이 단위 자체의 새 UI 구현은 없지만, 완료 통계·출처 SHA·차단·시각은 web_ui와 이해 담당에게 전달해 화면에 반영해야 한다.

공통 10분 보고·인계·이해자료는 Root가 다른 병렬 수집 결과와 통합한다. 이 문서나 단일 QA 완료를 전체 개발 완료로 표현하지 않는다.
