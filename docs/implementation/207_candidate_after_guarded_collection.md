# 207 — 보호 수집 이후 새 고정 후보의 누출 제외와 실제 QA

상태: **VERIFIED_REAL — 고정 원본·후보 native QA 및 최종 파일 지문 검산 완료**, **BLOCKED — 나지 대표성 3개 차단·학습 준비 false**. Root가 209 수집 종료와 담당자의 단일 bounded native 감사를 확인한 뒤 207 실행을 승인했다. 기존164 제품 CLI를 단 1회 실행해 exit0으로 완료했다.

## 목적과 범위

이번 작업은 새 수집을 학습 후보에 반영해 검사하는 단계다. 원본의 영상을 삭제하거나 원본 split을 바꾸지 않고, 같은 원본 장면이 서로 다른 split에 들어간 행을 새 후보에서만 제외한다. 후보 수량 증가와 학습 준비 승인은 별도다. 나지 대표성·독립 정답·모델 성능이 확보됐다고 해석하지 않는다.

기존 [193 후보 QA](193_recovered_collection_candidate_qa.md)의 게시 후보 1,317개와 영수증은 보존한다. 이번 CLI는 새 후보와 QA 증거만 만들며 게시 포인터를 바꾸지 않는다. Root의 후속 승계·reader·실제 UI 검증은 별도 작업이다.

## 고정 입력과 한 번의 실행

원본은 `data/first-group-training-esri-v1/annual-window-report.json`이며 **66,166,696바이트**, SHA256 `80eef2d274942c7a7f9bf8ee2483af070a729060d84ceb1a19baacb52ae4976a`다. 실행 전에 직접 SHA와 크기를 확인했다. 기존 cap **64MiB=67,108,864바이트** 이내이며 상한 변경·우회는 없다.

정책은 `data/first-group/experiment-esri-v003-2020-2025.json`이며 **1,306바이트**, SHA256 `01991d69bc26487d4ef890de72689da092806bc58cc80ca5f6d6026cf3c79ed7`다. 원본·정책 모두 명시 절대 경로와 소문자 SHA256으로 전달했다.

```powershell
python -X utf8 -u scripts/prepare_priority_candidate164.py `
  --data-root 'E:/GeoAI–MLOps–SDSS/data' `
  --source 'E:/GeoAI–MLOps–SDSS/data/first-group-training-esri-v1/annual-window-report.json' `
  --source-sha256 80eef2d274942c7a7f9bf8ee2483af070a729060d84ceb1a19baacb52ae4976a `
  --policy 'E:/GeoAI–MLOps–SDSS/data/first-group/experiment-esri-v003-2020-2025.json' `
  --policy-sha256 01991d69bc26487d4ef890de72689da092806bc58cc80ca5f6d6026cf3c79ed7 `
  --run-id guarded207-20261018
```

새 DATA/evidence 경로와 로그가 없음을 확인한 뒤 CLI를 **단 1회**, PID **34492**로 시작했다. 로그는 `evidence/integration/priority164-guarded207-20261018.log`에 exclusive 생성했다. snapshot은 **2026-10-18 14:13:08.134 KST**, **1,699행**으로 고정됐다. 실패 시 부분 결과를 보존하고 자동 재시도하지 않는 계약이다.

Root는 QA 동안 추가 collector를 보류하고 원본을 고정한다. 이 담당은 원장·lock·원본·라벨·정책·모델·기존 포인터를 수정하지 않는다. HTTP·다운로드·훈련·Registry 호출은 없다.

## 검사 순서와 결과 해석

164 CLI 한 번 안에서 고정 원본 native QA → split 계획 → 후보 materialize/stage → 후보 native QA → 검증 파일 SHA 최종 대조를 수행한다. 두 native QA는 원본과 누출 제외 후보라는 서로 다른 코호트의 정상 단계다. 같은 코호트를 추가로 감사하지 않는다.

고정 우선순위는 **test → val → train**이다. 과거 193에서는 반텐2021 validation 16행을 제외했다. 207에서도 같은 수를 예상했지만 결과를 16에 강제로 맞추지 않고, 현재 scene/source identity의 실제 계획과 정확한 retained/excluded partition을 확인했다. 긴 materialize/stage 시간은 metadata 지문·행 바인딩 검증이며 추가 native QA로 세지 않는다.

## 완료 후 인계 항목

### 실제 결과

원본 QA는 **183.625초**에 완료됐고 적격 수는 train **813** / val **292** / test **250**, 합 **1,355**다. 원본의 blocker는 교차 split source 충돌 1개와 세 split의 나지 대표성 3개로 총 4개다.

계획은 원본 index **288~303**, 반텐2021 validation 16행만 제외했다. 동일 장면은 `S2A_MSIL2A_20210812T025551_R032_T48MXT_20210812T132431`이며 서자바 test를 보존한다. 16개 장면을 제거했다는 뜻이 아니라 같은 장면에 연결된 16패치를 새 후보에서만 제외한 것이다. 실제 후보 QA도 남은 source identity 충돌 0과 적격 **1,339(813/276/250)**를 확인했다.

| 항목 | 고정 원본 | 새 고정 후보 |
|---|---:|---:|
| manifest 행 | 1,699 | 1,683 |
| 품질 적격 | 1,355 | **1,339** |
| train / val / test 적격 | 813 / 292 / 250 | **813 / 276 / 250** |
| blocker | 4 | **3** |
| 교차 split source 충돌 차단 | 1 | **0** |
| verified file 기록 | 5,326 | **5,276** |

기존 게시 후보1,317 대비 **22개 증가**했다. 209에서 실제 생성한 물리패치32개 중22개가 품질 적격이었다는 결과와 연결되지만, 물리32개를 모두 적격으로 계산하지 않는다. 최종 완료 시각은 **2026-10-18 14:35:00.528 KST**이며 snapshot 이후 약21분52초가 걸렸다. 원본 native QA **183.625초**, 후보 QA 함수 **299.469초**, 그 밖의 시간은 metadata 검증·최종 대조 등이다. 후보 QA 함수 시간에는 staging proof 등 입력 metadata 확인도 포함되므로 전부를 순수 raster 처리 시간으로 단정하지 않는다.

후보 나지 픽셀은 train/val/test **2,562/2,998/1,025**, 256픽셀 이상 기여 패치는 **1/2/0**으로 원본·이전193과 같다. 수량 증가와 별개로 나지 부족은 남는다. 새 22개 적격 패치는 실제 나지 확보 성과가 아니다.

| split | 유효 라벨 픽셀 | 나지 비율 | 기여 패치 / 최소5 |
|---|---:|---:|---:|
| train | 51,859,864 | **0.004940%** | 1 / 5 |
| val | 17,776,457 | **0.016865%** | 2 / 5 |
| test | 16,252,940 | **0.006307%** | 0 / 5 |

정책의 split별 나지 비율 최소 **0.5%**와 기여 패치 최소5개를 모두 충족하지 못했다. 세 split에 `REFERENCE_CLASS_IMBALANCE`가 남고 detail은 각각 `class7_pixel_ratio`, `class7_patch_representation`이다. source code8과 내부 class7은 같은 나지의 서로 다른 코드 체계다. train은 나지 픽셀이 그대로인데 전체 유효 픽셀이 늘어 이전 약0.005073%에서 약0.004940%로 낮아졌다. 일반 자료를 늘리는 것만으로 나지 대표성까지 개선되지는 않는다.

materialization에서는 약 66.2MB source와 약 65.5MB candidate를 여러 번 bounded JSON으로 읽어 saved plan·retained row·source/readiness 지문을 대조한다. 후보 파일 생성과 `candidate-package/receipt.json` 생성 사이에도 metadata 검증이 진행된다. 이번 실행에서는 CPU 사용 증가와 뒤이은 receipt 생성으로 진전을 확인했으며, 느린 단계를 생략하거나 재시작하지 않았다. 이 시간을 native QA 수행 시간으로 합산하지 않는다.

### 최종 지문과 인계 검산

CLI는 후보의 **5,276개 verified file 기록을 실제 파일 SHA로 최종 재대조해 불일치0**을 확인했다. 이후 담당자는 추가 native scan 없이 output11개의 바이트/SHA와 JSON 행 연결만 한 번 대조했다. retained row는 원본 해당 index와 정확히 같고, retained/excluded는 중복 없이 전체1,699행을 완전히 나눈다. 원본 current SHA는 snapshot과 같으며 정책은 summary output pin과 같다.

| 산출물 | SHA256 |
|---|---|
| source readiness | `2a93c85733ab715f490388872d985773a1bbbaca3b84632b9fb5eb5ac108c373` |
| split plan | `fd19c98eb3a829c676f00e0fa62ce9b074aa18484fe3adc9d460f490bde07590` |
| evidence/DATA 후보 동일 바이트 | `b69eff4f7c584fbc423c1003effe3ae67690721640ef558c84faecbb05f20b10` |
| staging receipt | `26cabb4a2aec239f006a8a369b75b7b2a42c3212d7c3c5b904a9540262db3937` |
| candidate readiness | `a2da11ebc02bca78bab860401b6a6fde1e4a01d682488a173583e1f757fd4aa3` |
| candidate QA receipt | `12459a2cbfb2f64414564d8060f40fa76b58df238eef5f002c3692626c694993` |
| summary — 4,820바이트 | `d80bad5650ff8c32f4b8a297ac1017b27aaec6cbdb0fc2f110f240f3875a5ec9` |
| handoff-verification | `6ab00c16e2524eb2254890e5a8e5a872894c2b4339ea33d03b1c06ee35880b78` |

`summary.json`, `split-plan.json`, `handoff-verification.json`, `candidate-package/`는 `evidence/integration/priority164-guarded207-20261018/`에 있고, source/stage/qa는 `data/priority164-guarded207-20261018/`에 있다. 후보는 **65,545,981바이트**다. 기존193 pointer/receipt SHA `3f54fb6cbe098a487a3dcd76cc951a3b713dae9aa14a1f3f0f6ccf6d8304b081`, 이전193 summary SHA `692dccf9a8d50a7466ea39ba6cbb25874226f043f3896ddd8623d4ec3f61bf52`도 그대로다. 이 검산 시점은 **14:36:17 KST**이며 이후 Root의 명시 후속 게시와 구분한다.

후보 실제 gate와 helper summary 모두 `ready_for_training=false`다. 과학 정확도 미검증·훈련/Registry 미호출 경계를 유지한다. 부가 connectivity witness는 `NOT_CAPTURED_BUDGET`이며 전체 공간 독립성이나 독립 정답을 인증한 것이 아니다. 이번 snapshot 이후 새로 수집한 자료는 이 후보에 자동 반영되지 않는다.

내부 데이터 QA이므로 직접 프론트 코드·서버·브라우저 변경은 없다. 완료 증거를 Root에 전달하고, 후속 게시 및 UI 확인과 이해자료·대본·FAQ·INDEX·변경 이력 갱신은 해당 담당에게 인계한다. 전체 개발과 정기 보고는 계속된다.


## 207 게시 후 실제 API·화면 확인

Root의 새 후보 receipt 승계 이후 기존 Chrome view17에서 한 번 새로 조회했다. 실제 응답은 **14:38:19.903033 KST**, source SHA `80eef2d274942c7a7f9bf8ee2483af070a729060d84ceb1a19baacb52ae4976a`다. 원본 적격 1355(813·292·250)·셀 부족 24와 **새 고정 후보 1339(813·276·250)·차단 3건**을 분리 표시한다. 후보 생성 source는 현재 원본과 일치하며 이전 후보의 시점 경고는 해제됐다. 후보 준비 미충족·승인 아님 표시는 유지된다.

기존 나지 검토 37개·고론탈로/서자바 두 행은 그대로이고 검토 source 불일치 경고는 유지된다. 이는 새 후보 QA 게시가 이전 로컬 검토를 자동 갱신하지 않음을 보여준다. 원격 미검사·집행 미승인 및 범위 밖 미탐색 설명도 유지된다. 콘솔 warning/error 0건·가로 넘침 없음이다. 추가 API 요청·중복 갱신·서버 재시작·source/pointer/운영 쓰기는 0이며,211 미래 성과는 포함하지 않는다. 기존1317 관측과 이번1339 게시 후 관측은 별도 시점 근거다. 증거 `evidence/integration/service207-candidate-final-ui-20261018.*`에 DOM·캡처·콘솔·응답 시점을 보존했다.
