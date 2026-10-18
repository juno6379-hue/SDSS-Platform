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


## 2026-10-18 10:54 KST — 4차 수집 완료·159 후보 UI 승계

앞선1464/1164 관측 이후4차 반텐2025 g01/g02가 정상종료했다. 신규32물리/32적격/나지391픽셀로1496물리/1196적격/300부적격,train681/val265/test250이다. 전체1200 부족4·주연도 셀당28 부족97이다. 최초요청대비96물리/74적격을 추가했고 셀 부족151→97,나지추가553픽셀이다. 4차32개 실제래스터·유효/주내·클래스·SHA 및source/worker/원장 정합성을12.7664229초에 재검증했고 기존1464행과pending2전액136314880B를보존했다. 신규총계상2085380105B/한도잔여2209587191B,429false/실행lock정상해제다. 원본검증분할 나지는209→600픽셀,기여0→1개로 개선됐으나0.5%·기여5패치 기준은미달이다. 1200개충족과학습준비는별개다.

159의1432행고정source→누출16행제외후1416행/1125적격 후보는실제QA·4435파일SHA검증후명시receipt로승계했다. 기존153후보/receipt와교체전pointer원바이트를보존하고,새receipt3핀검산·readyfalse/차단4 검산후pointer원바이트가변하지않았는지비교하고os.replace로교체했다. DatasetRegistry/모델/원장/기존분할/학습상태전이0이다. 부가connectivity NOT_CAPTURED_BUDGET 한계는유지한다. 최신1496원본의55적격(23+32)은새1125후보QA범위밖이며sourceSHA불일치경고를유지한다.

실제API8002/프런트5174 소스변경·재시작 없이기존GET·명시수동새로조회로승계됐다. 브라우저응답01:52:31.145480Z에서원본1196(681/265/250)·후보1125(658/217/250)·차단4/미준비·시점불일치·원본검증나지600/기여1을확인했다. console warning/error0,가로넘침0이며분석/학습/배포/등록버튼을실행하지않았다. 전체페이지스크린샷1회timeout은브라우저캡처한계로기록하고실제viewport PNG/DOM/JSON을보존한다. 제품소스변경없으므로기존48관련backend·288격리frontend·build120근거를유지하며새전체회귀통과를주장하지않는다.

5차동자바2021 g02/g03은plan fe20a0b67e5b6215d3f0e4814a07e48b9645a2fb6ba90893b4c3049cd62b8ade,wrapperPID33756으로시작했고완료는미확인이다. 기존budget/2worker/2초/429중단/3000상한/고정split/품질정책을유지한다. 같은collector중복실행금지.157표적은계속집행차단이며160로컬자산영역검사작업은다른채팅소유기록과중복하지않는다. geoai-2 ACTIVE10분보고지속,전체개발미완료다.

근거:evidence/integration/priority-collection-round4-final-20261018.json,priority-collection-independent-round4-20261018.json,priority-collection-round5-launch-20261018.json,priority-ml-next-ui-promote-20261018.py,priority-ml-next-ui-receipt-20261018.json,priority-ml-next-ui-round4-20261018.json,priority-ml-next-ui-round4-20261018.png 및docs/implementation/159_next_collection_candidate_qa.md.


## 2026-10-18 11:00 KST — 5차 완료: 적격1212·셀 부족85, 6차 시작

최신 완료 관측은1512물리/1212적격/300부적격, 학습697·검증265·시험250이다. 최초 요청의1122적격보다90개 늘었고 셀당28 계획 부족은151→85개다. 전체1200 수량 목표 부족은0이지만 나지 균형·독립 검증·학습 승인은 미충족이다. 주별 부족은 South Sulawesi0/Gorontalo17/Southeast Sulawesi45/East Java18/Banten5/West Java0이다.

5차 동자바2021 g02는 COG 범위 오류로0개, g03은16개 모두 적격이었다. 별도9.4286137초 검사로 새16개 실제 배열·품질·SHA, 원본1496행과 기존pending2전액 보존을 확인했다. 감사helper 최초 실행은 worker가 정상 종료했어도 scene이 failed인 경우를 처리하지 못해 멈췄고, scene-level 실패 분기를 추가해 재검사했다. 최초 실패 로그도 보존했다. 수집 제품 코드·품질 가드 변경은0이며 실패 batch를 성과에 포함하지 않는다. 누적 신규계상2106330497B/4GiB 한도 잔여2188636799B,429false/5차 lock 정상해제다. 이후6차 예약·전송으로 잔여량은 바뀔 수 있다.

원본 나지 픽셀은 학습1586/검증600/시험1025,256픽셀 이상 기여 패치는0/1/0이다. 전체 요청 이후 나지 선언559픽셀을 추가했지만 각 split0.5%·기여5개 기준은 미달이다. UI응답01:58:33.471802Z에서 원본1212/후보1125·차단4/미준비·고정1432 source와 현재원본 SHA불일치를 실제 확인했다. 후보에 이후71개 적격을 포함했다고 표시하지 않는다. 콘솔오류/경고0·가로넘침0, 학습/등록/배포 실행0이다.

6차 동자바2024 g01/g02를 plan228a9c72695da9cc4b367f9632456601614d2bc0bac7788a9a6200bedb17ea01, wrapperPID8688로 시작했다. 완료·추가수량은 미확인이다. 단일coordinator·2worker·2초간격·최초429공유중단·기존예산·3000상한·고정split·품질기준을 유지한다. 수량1200을 넘었어도 기존 balanced_coverage의 나지/클래스 gate가 미충족이므로 자동 학습이나 승인으로 전이하지 않는다. 157 표적 집행은 계속 BLOCKED이며 다른채팅160 자산기하 검사 소유와 중복하지 않는다.10분 보고 geoai-2 ACTIVE와 실제 수집·학습 상태를 구분한다.

근거:evidence/integration/priority-collection-round5-final-20261018.json,priority-collection-independent-round5-20261018.json,priority-collection-independent-round5-initial-20261018.log,priority-ml-next-ui-round5-20261018.json,priority-ml-next-ui-round5-20261018.png,priority-collection-round6-launch-20261018.json. 관련 구현/API/UI/인계와 이해자료14개 및161 이해노트를 함께 갱신했다.
