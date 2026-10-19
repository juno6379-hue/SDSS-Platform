# 238 — 235 종료 후 새 고정 후보 QA 준비·인계 계획

상태: **PLANNED / EXECUTION_NOT_STARTED**. 이 문서는 Root가 예약한238의 실행 준비이며 실행 승인이 아니다. 이번 담당은237 코드·운영 source·원장·모델·실제 QA를 읽거나 실행하지 않았고 공유 코드를 수정하지 않았다. HTTP·collector·native·모델 학습·Registry·게시 쓰기는0이다.

## 목적과 실행 조건

235에서 실제 새 패치를 확보한 경우에만 새 고정 원본을 검사하고, 같은 source 장면이 서로 다른 split에 들어간 행을 **새 후보에서만** 제외한다. 기존 게시 후보1,342개는 인계 시점까지 보존한다. 원본1,358적격·부족21·후보1,342는 Root의 기존 기록값이며 현재 실측으로 다시 확인하지 않았다.235의 새 수량·나지·source SHA·원장은 아직 확정값을 넣지 않는다.

다음 조건을 모두 Root가 확인한 뒤238 실행을 별도로 배정한다.

1. 235 실제 terminal과 정산·게시가 끝났고 collector/supervisor 종료 및 execution lock 해제를 확인한다. 기존 미정산 예약은 보존된 상태여야 한다.
2. 전담자의 신규분 단일 bounded native 감사가 완료되고 source가 고정됐으며, **신규 patch 수가0보다 크다**. 새 patch0이면238을 실행하지 않는다. 부적격/미등록 실물만 있는 등 aggregate에 반영할 내용이 불명확하면 QA를 자동 실행하지 않고 Root가 필요성을 판단한다.
3. 237 보완판이 독립 검토·Root의 공유 적용 및 적용 파일 지문 검증을 마쳤다. 단순 격리 시험·230 동결만으로 이 조건을 충족하지 않는다. **이번 준비 담당은237 소스를 읽지 않는다.**
4. Root가 source 절대 경로·현재 SHA·bytes·행수와 정책 실제 SHA, 적용된164/profile helper 코드 지문을 전달한다. QA 동안 새 collector를 시작하지 않고 원본을 고정한다.
5. 실행 담당자가 그 원본과 정책만 직접 재검산하고 새 run-id 산출 경로·로그의 미존재를 확인한다. 미리 사용됐거나 부분 결과가 있으면 같은 경로를 지우거나 재사용하지 않는다.

## profile 선택과 자원 계약

준비 대상은 명시 `bounded128m-3000-v1` 경로다.237 검토·공유 적용 검증이 끝난 뒤 Root가 이 profile을 명시 선택해야 한다. 파일이64MiB를 넘었다는 이유로 자동 선택·상향하지 않는다. profile 미지정은 기존64MiB/v1 계약이며, 명시 경로는128MiB/v2 package·staging·QA receipt의 정확 marker를 요구한다. 두 모드의 artifact를 섞거나 v2를 v1로 바꾸지 않는다.

명시 경로의 고정 제한은 source/candidate JSON **134,217,728바이트**, source의 scenes+history 및 candidate **3000행**, 깊이32, tree 방문4,000,000, 작업 누적 metadata JSON I/O **17,179,869,184바이트**다. 이것은 로컬 JSON 자원 계약이며 원격 추가4GiB·개별 raster/label/header64MiB·품질80%/주내95%·고정 split·나지 gate·물리3000 제한과 별개다. 작은 정책/receipt/report의 역할별 한도는 적용판의 검증된 계약을 유지한다.

node 검사는 decode 이후이므로128MiB byte cap이 모든 메모리 사용을 사전 보장하지 않는다. 실제 rich metadata의 wall/RSS·누적 I/O 충분성도 아직 보장하지 않는다. 어떤 자원 한계나 변경 지문을 만나도 부분 결과를 보존하고 중단한다. cap 증가·자동 재시도·다른 profile로 이어 실행은0이다.

## 고정 run-id와 준비 명령

실행 run-id는 **guarded238-20261018 하나**다. DATA 산출은 `data/priority164-guarded238-20261018/`, 증거는 `evidence/integration/priority164-guarded238-20261018/`, 로그는 `evidence/integration/priority164-guarded238-20261018.log`를 예정한다. 이 세 경로의 현재 존재 여부는 이번 준비에서 확인하지 않았다. **실행 직전** 직접 확인해야 한다.

아래는 실행되지 않은 template다. source SHA placeholder는 미래값이며 실제 명령으로 쓰기 전에 Root의 확정값으로 채운다. 정책 pin은 기존 기록값이며 실행 직전 실제 일치를 확인해야 한다.

```powershell
python -X utf8 -u scripts/prepare_priority_candidate164.py `
  --data-root 'E:/GeoAI–MLOps–SDSS/data' `
  --source 'E:/GeoAI–MLOps–SDSS/data/first-group-training-esri-v1/annual-window-report.json' `
  --source-sha256 '<ROOT_CONFIRMED_SOURCE_SHA256>' `
  --policy 'E:/GeoAI–MLOps–SDSS/data/first-group/experiment-esri-v003-2020-2025.json' `
  --policy-sha256 01991d69bc26487d4ef890de72689da092806bc58cc80ca5f6d6026cf3c79ed7 `
  --run-id guarded238-20261018 `
  --manifest-profile bounded128m-3000-v1
```

`evidence/integration/priority238-preparation-20261018.json`에도 같은 template와 미확정 필드를 남긴다. 현재 source bytes·rows·SHA·ledger SHA·코드 지문·예상 후보 수량은 **null**이며 미래 결과를 발명하지 않는다. 정책 값은 historical expected pin으로만 표시한다.

## 단 한 번의 실행과 관측

1. 새 wrapper/launch/terminal 파일과 로그를 exclusive 생성한다. 실제 argv·interpreter·코드/source/policy 지문·source bytes·구 게시 pointer/receipt 지문·PID/session을 Root에 전달한다. 원장은 QA 입력이 아니며 Root의235 정산/감사 완료 근거로만 구분한다.
2. 164의 같은 한 실행 안에서 source snapshot→원본 QA→고정 test/val/train 우선순위 계획→materialize/stage→후보 QA→실제 verified_files SHA 검산→summary를 수행한다. 원본·후보 QA는 서로 다른 코호트이며 추가 동일 native 감사를 실행하지 않는다.
3. 기존 누출16행은227의 역사 참조다. 새 실제 plan의 sameScene/source identity·retained/excluded partition을 검증하고, 결과를16에 강제로 맞추지 않는다. 기존 source·split·라벨·모델을 수정/삭제하지 않는다.
4. 실제 monotonic wall과 시작/종료 시각을 기록한다. 원본 QA/후보 함수 시간과 metadata 구간을 전체 wall과 구분한다. RSS는 가능한 경우 OS의 실제 PID 표본을 간격을 두어 관측한다. 표본 최대 RSS와 OS가 제공한 peak working set을 구분하고 관측하지 못하면 null로 둔다. 환경을 다시 실행해 RSS를 확보하거나 과거228 whitespace406MiB를 재사용하지 않는다.
5. 정상 프로세스 활동과 새 로그/receipt 단계를 확인하며 느린 metadata 검증을 건너뛰지 않는다. 오류/부분 결과·실제 종료코드를 보존하고 자동 재시작하지 않는다.10분 보고는 역할·실제 단계·미확정 결과를 구분해 Root가 계속한다.

## 완료 인계·게시·화면 구분

완료 시 source/후보의 manifest행·적격 train/val/test·blocker·동일 source 충돌·나지 픽셀/분모/비율·256픽셀 이상 기여 패치·connectivity capture status를 실제 summary에서 확정한다. 새 수량 증가를 나지 해결이나 독립 정확도 승인으로 확대하지 않는다. 현재 알려진3나지 차단과 NOT_CAPTURED_BUDGET은 역사값이며 미래 결과는 실제 관측대로 기록한다.

실제 파일 SHA 불일치0, output pin/bytes, retained exact row와 전체 partition, 현재 source/정책 지문·선택 profile/v2 marker 일치를 확인한다. 기존1,342 pointer/receipt·이전 QA summary의 사전/사후 지문도 보존해 Root에 인계한다. 추가 native QA 없이 metadata 인계 검산만 수행하고 완료 문서와 지문을 마감한다. 정상 종료라도 readiness가 false면 그 한계를 그대로 보고한다.훈련/Registry/운영 승인은 실행하지 않는다.

**238 CLI 완료는 게시 완료가 아니다.** Root가 독립 입장 검산→기존 pointer 원바이트 archive→새 receipt/pointer 승계→reader/실 API 검증을 별도 수행한다. 실제 브라우저의 표시·console·overflow 확인도 UI 담당 후속이다. 현재234 브라우저 차단 이력이 있어 API200을 브라우저 성공으로 쓰지 않는다. 문서·이해자료(쉬운 설명/이론/코드·데이터/증거/대본/FAQ/INDEX/이력) 마감은 새 실제 결과로 Root가 인계한다.

이 계획 작성은 실제 QA·profile 적용·수집·UI 확인·전체 개발 완료를 뜻하지 않는다. 실행 조건이 갖춰질 때까지 준비 상태를 유지한다.
