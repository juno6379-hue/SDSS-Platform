# 227 — 223 남동 수집분을 반영한 새 고정 후보 QA

상태: **VERIFIED_REAL — 고정 원본·후보 QA 및 실제 파일 지문 검산 완료**, **BLOCKED — 나지 대표성3차단·학습 준비 false**. Root가 223 수집과 단일 신규 native 감사 종료를 확인한 뒤 기존164 CLI의 새 실행을 승인했다. 단1회 실행으로 exit0·`PINNED_CANDIDATE_QA_COMPLETED`를 확인했고 실제 적격 후보는 **1,342개**다.

## 쉽게 설명

223은 새 영상16패치 중3개가 품질 적격임을 확인한 수집 작업이다. 227은 이를 기존 자료와 합친 고정 원본 전체에서 학습 후보를 다시 만드는 단계다. 동일 원본 장면이 validation과 test에 함께 들어간 행은 새 후보에서만 제외한다. 원본 split·라벨·모델은 바꾸지 않는다.

기존 게시 후보1,339개는 223보다 앞선 고정 시점이다. 이번 CLI는 새 후보·QA 증거를 만들며 게시 포인터를 바꾸지 않는다. 완료 뒤 Root의 독립 검토·승계·reader·실제 화면 확인을 구분한다. 나지 대표성·독립 정답·학습/운영 승인은 별도 미완료다.

## 선행 종료 감사와 입력 고정

AGENTS/CONT와 [223 완료 문서](223_guarded_southeast_collection.md), `deficit223-native-root-20261018.json`을 확인했다. 신규16개 단일 감사는 `COMPLETED_NATIVE_CHECKED`, native complete=true,3적격·적격 나지0,52개 SHA 검산,7.139초였으며 source/ledger drift=false다. 그 감사를 중복 실행하지 않았다. 이번164 내부의 원본/후보 QA는 서로 다른 고정 코호트의 제품 단계다.

직접 확인한 원본은 `data/first-group-training-esri-v1/annual-window-report.json`, **66,826,849바이트**, SHA256 `9c24eec337a17f95855d190918c9999c25aeb1925a7642b1ade26afa4e20d987`다. cap **64MiB=67,108,864바이트**보다 **282,015바이트 작다**. 상한 변경·자동 재시도는 없다. 이후 수집도 이 상한 안이라고 보장하지 않는다.

정책은 `data/first-group/experiment-esri-v003-2020-2025.json`,1,306바이트·SHA `01991d69bc26487d4ef890de72689da092806bc58cc80ca5f6d6026cf3c79ed7`다. 정확히 필요한 원본·정책 경로만 읽고 지문을 확인했다. Root는 QA 동안 추가 collector를 보류하고 원본을 고정한다. 원장 사전핀 `61161c35eabb593afb5f096c256791871d297b723f82ffc2ac2449b3bd8266e7`은 Root/223 종료 감사의 관측이며164 입력은 source와 policy다.

## 실제 한 번의 실행

```powershell
python -X utf8 -u scripts/prepare_priority_candidate164.py `
  --data-root 'E:/GeoAI–MLOps–SDSS/data' `
  --source 'E:/GeoAI–MLOps–SDSS/data/first-group-training-esri-v1/annual-window-report.json' `
  --source-sha256 9c24eec337a17f95855d190918c9999c25aeb1925a7642b1ade26afa4e20d987 `
  --policy 'E:/GeoAI–MLOps–SDSS/data/first-group/experiment-esri-v003-2020-2025.json' `
  --policy-sha256 01991d69bc26487d4ef890de72689da092806bc58cc80ca5f6d6026cf3c79ed7 `
  --run-id guarded227-20261018
```

실제 wrapper는 `evidence/integration/priority227-runner-20261018.py`, CLI PID는 **38816**이다. 새 DATA/evidence 경로 미존재를 확인하고 로그를 exclusive 생성해 한 번만 실행했다. 명령·PID·지문·기존 후보 보호핀은 `priority227-launch-20261018.json`, 종료는 `priority227-terminal-20261018.json`, CLI 로그는 `priority164-guarded227-20261018.log`에 보존한다. 실패 시 부분 결과 보존·자동 재시도 금지다.

CLI는 snapshot → 원본 native QA → test/val/train 고정 우선순위의 source 충돌 제외 계획 → materialize/stage metadata 검산 → 후보 native QA → 실제 verified file SHA 대조 → summary 순서다. 큰 source/candidate의 strict metadata 왕복 대조 시간과 native QA를 구분한다. 느린 단계를 생략하거나 별도 QA를 동시에 실행하지 않는다.

## 완료 증거와 후속

snapshot은 **2026-10-18 15:18:40.450 KST**, 최종 summary는 **15:29:05.226 KST**에 기록됐다. snapshot 이후 약 **10분25초**가 소요됐다. 원본 native QA는 **165.609초**, 후보 QA 함수는 **120.656초**다. 전체 시간과 이 두 함수 시간을 합산하지 않으며, 후보 함수 안의 입력 proof 검산까지 순수 raster 처리 시간으로 단정하지 않는다. materialize/stage는 대형 JSON의 bounded 읽기·지문·exact row 왕복 검증이다. 패키지 receipt와 staging receipt가 순서대로 생성되는 것을 확인했으며 재시작·우회하지 않았다.

| 항목 | 고정 원본 | 새 고정 후보 |
|---|---:|---:|
| manifest 행 | 1,715 | **1,699** |
| 품질 적격 | 1,358 | **1,342** |
| train / val / test 적격 | 816 / 292 / 250 | **816 / 276 / 250** |
| blocker | 4 | **3** |
| 교차 split source 충돌 차단 | 1 | **0** |
| verified file 기록 | 5,376 | **5,326** |

기존1339 후보보다 **3개 증가**했다. 원본의 물리1716개·등록1715행·적격1358개와 후보1699행·적격1342개는 서로 다른 수치다. 원본의 전체 실물 수는223 감사의 선행 관측이며 이번 QA가 전체 실물 디렉터리를 다시 스캔한 것은 아니다. 부적격 자료도 후보 manifest에 남을 수 있어 후보 행수와 적격 수가 다르다.

### 동일 장면과 제외16행

제외 index는 **288~303**, 반텐2021 validation16행이다. source identity는 `S2A_MSIL2A_20210812T025551_R032_T48MXT_20210812T132431`이며, test 우선순위에 따라 같은 원본을 쓰는 서자바 test행을 보존했다. 16개 위성 장면을 없앤 것이 아니라 같은 장면에 연결된16패치를 새 후보에서만 제외한 것이다. source/기존 split을 수정하지 않았다.

계획의 `remaining_source_identity_conflicts=0`과 실제 후보 readiness의 교차 split blocker 부재가 일치했다. 추가 native scan 없이 JSON metadata로 retained row와 원본 해당 index의 정확 일치, retained/excluded 중복0·누락0·전체1715행 partition을 검산했다. 이 결과를 전체 미래자료의 누출 방지나 모든 공간 독립성 인증으로 확대하지 않는다.

### 남은 나지 차단

세 split 모두 `REFERENCE_CLASS_IMBALANCE`이며 detail은 각각 `class7_pixel_ratio`, `class7_patch_representation`이다. 정책은 나지 비율 **0.5% 이상**, 각 패치에 나지 **256픽셀 이상**인 기여 패치 **5개 이상**을 요구한다. Esri source code8은 내부 class7에 대응한다.

| split | 실제 나지 픽셀 | 유효 라벨 픽셀 | 나지 비율 | 기여 패치 / 최소5 |
|---|---:|---:|---:|---:|
| train | 2,562 | 52,026,521 | **0.004924%** | 1 / 5 |
| val | 2,998 | 17,776,457 | **0.016865%** | 2 / 5 |
| test | 1,025 | 16,252,940 | **0.006307%** | 0 / 5 |

나지 픽셀·기여 패치는207과 같다. 새3개가 일반 수량 부족을 줄였으나 나지 대표성을 채우지는 않았다. train의 분모가 늘어 이전 약0.004940%에서 약0.004924%로 비율이 조금 낮아졌다. 나지 자체를 더 확보하고 여러 적격 패치에 분산하는 보완이 필요하다.

### 지문·보존·승계 경계

CLI는 **5,326개 verified file 기록을 실제 파일 SHA로 최종 대조해 불일치0**을 확인했다. 같은 파일을 중복 집계해 원본5376개와 합산하지 않는다. 이후 인계 검산은 새 native QA 없이11개 output의 SHA/bytes, JSON exact row·partition과 기존 게시 자료 지문만 확인했다.

| 산출물 | SHA256 |
|---|---|
| source readiness | `319493c6e2b18b6f4f970379c3de9a5ce09cb078ba4e75dcd51d9f1f2a70558a` |
| split plan | `26c9cd19b8e9e786ed9f09df792b9d77db0051dea7aad80bdb987d4dd049ecd9` |
| evidence/DATA 후보 동일 바이트 | `4f68794c1b81ddc9f4270d040fe055dd0dcf6041d77e3c132088a45e41619878` |
| staging receipt | `6944da434e1e749bf9b9373370d32a47467c0efbeea7ab917db26761fc05fe7c` |
| candidate readiness | `30d5360bc490e842a68abfebbae7db09e29dfa24540909605c3b7059eb167e98` |
| candidate QA receipt | `adc9cc46109be13dac3d938fe1a81c44772e61a681a7ac3392fb8ea1baea8fed` |
| summary — 4,820바이트 | `99927a8a0e7559feda77191308fe7f51221e1d39796fc4f8685384752d26eb85` |
| handoff-verification | `9c7327cc09b4e26688966f0a7bfea1440fe63b0ad1deda9d99e7af6afb9874f6` |

새 산출물은 `data/priority164-guarded227-20261018/`와 `evidence/integration/priority164-guarded227-20261018/`에 있다. 후자의 `summary.json`에 전체11개 출력핀, `handoff-verification.json`에 exact row·partition·보호핀과 클래스 분모/비율이 보존됐다. 인계 검산기는 `evidence/integration/priority227-handoff-20261018.py`이며 산출물 후보는 **66,206,017바이트**다.

**15:29:34 KST** 인계 검산 시 current source/policy SHA는 고정값과 일치했고, old1339 pointer와 receipt 모두 `ac6827a1841fd657c430c2a4953aae6089dc4322041dfad87b20fbd1e751c12a`,207 summary `d80bad5650ff8c32f4b8a297ac1017b27aaec6cbdb0fc2f110f240f3875a5ec9`로 보존됐다. Root에 보호 검산 종료와 후속 승계 가능 상태를 전달했다. 이후 Root의 독립 검토·old pointer archive·새 receipt/reader·실 UI는 별도 완료 근거로 구분하며 이 담당이 게시한 것으로 쓰지 않는다.

실제 gate와 summary 모두 `ready_for_training=false`, 과학 정확도 미검증이다. 부가 connectivity witness는 **NOT_CAPTURED_BUDGET**이며 실제 파일 QA를 생략했다는 뜻은 아니다. 독립 정답·전체 공간 연결성 인증·모델 학습/운영 승인으로 해석하지 않는다. 이후 자료는 이 고정 후보에 자동 추가되지 않는다.

코드·원본·원장·split·라벨·모델·Registry·게시 포인터 변경과 HTTP·훈련은0이다. 내부 QA라 직접 UI 코드/build/브라우저 변경은 없고, Root의 후속 승계와 UI 담당의 실제 화면 검증이 필요하다. 완료 증거를 Root/이해 담당에 인계해 설명·대본·FAQ·INDEX·변경 이력을 함께 갱신하며 전체 개발·역할별10분보고는 계속한다.


## 227 게시 후 실제 후보·예산 화면 확인

기존 API40492/Chrome view17에서 명시적으로 한 번 새로 조회했다. 실제 재고 응답 시각은 **15:35:03.322120 KST**, 예산 관측은 **15:35:04.252491 KST**다. source SHA `9c24eec337a17f95855d190918c9999c25aeb1925a7642b1ade26afa4e20d987`, ledger SHA `61161c35eabb593afb5f096c256791871d297b723f82ffc2ac2449b3bd8266e7`다.

원본 적격1358(816·292·250)·셀 부족21과 새 고정 후보1342(816·276·250)·차단3건을 분리 표시한다. 후보 생성 source는 현재 원본과 일치하며 후보의 시점 경고는 해제됐다. 기존 두 주 나지 검토37개는 원본 변경 경고·원격 미검사·집행 미승인을 유지한다. source 일치는 학습·배포 승인이 아니다.

225 예산 카드는 한도4294967296·사용2398022341·잔여1896944955·기존미정산2건136314880 bytes를 유지하고 프로세스 실행 미확인·예약 중복 차감 없음·두SHA·관측시각을 표시한다. 콘솔 warning/error0·가로 넘침 없음이다. 서버 재시작·별도 API 요청·추가QA·소스/pointer/운영 쓰기는0이며228 격리 개발의 미반영 코드를 실행 중 서버 기능으로 포함하지 않는다. 증거 `evidence/integration/service227-candidate-final-ui-20261018.*`에 DOM·후보/예산 캡처·검증 JSON을 보존했다.
