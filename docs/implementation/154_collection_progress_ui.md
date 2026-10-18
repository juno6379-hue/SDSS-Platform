# 154 — 실제 수집 재고·연차 목표·나지 보완·고정 후보 UI

상태: **VERIFIED_REAL(현재 원본 수집 현황의 실서버 UI 읽기) / TESTED_SYNTHETIC(타입·오류·stale 경계) — 고정 후보 발행 뒤 실제 비교 표시도 확인.** 수집 현황 숫자를 하드코딩하지 않고 기존 실제 API의 읽기 응답을 사용한다. 전체 자료 확보·학습·독립 평가·기관 승인은 별개다.

## 실제 화면과 변경 소유권

기존 `/api/data/collection-status`의 `patch_inventory`는 원본 물리/적격/split을 제공했지만 주×연도 적격 건수, 셀 계획 부족, 나지 절대량·비율·기여패치, 별도 누출 제외 후보를 함께 확인하기 어려웠다. Root가 신규 `collection_priority_status.py`와 기존 `collection_status.py`의 응답 필드를 담당한다. UI 담당은 backend/main/API를 수정하지 않는다.

새 `CollectionProgress.tsx`의 표시 뷰를 기존 `CollectionStatus.tsx`에 연결했다. 실제 위치는 **Data Catalog → 품질·정합 감사** (`#/view/10`)이며 대시보드의 같은 기존 수집 현황에도 반영된다. 이 뷰는 부모가 이미 조회한 응답을 전달받아 중복 GET하지 않는다. **모델 & MLOps → 모델 검토** (`#/view/17`, 기존 `#/view/6`도 동일 component)는 독립 읽기 loader를 연결해 모델 선택 전에도 LCLUC 자료 보완 상태를 확인한다. 등록/평가/배포/승인 버튼과 기존 API 흐름은 보존한다.

신규 파일은 component·adapter·client·scoped CSS·집중 시험이며 기존 수정은 CollectionStatus의 import/type/표시와 ModelReview의 import/표시만이다. App·기존 catalog 핵심·공통 api.ts·기존 workflow/연차진단 component·모델 계약·원본 수집 파일은 수정하지 않는다. 기존 파일의 CRLF를 유지한다.

## API·표시 계약

`collection_targets`는 현재 수집 원본 manifest의 `quality_status`와 저장 참조 라벨 집계를 계산한 값이다. 물리/적격/적격 외, 분할 합계, 목표 적격 수와 차이, 주별 연도 적격 수와 셀 계획 바닥의 부족 합을 표시한다. 목표·정책·개수는 모두 응답에서 가져오며 예시/문서 숫자를 데이터로 넣지 않는다. 전체 목표 부족과 셀별 계획 부족은 서로 다른 지표여서 합산하지 않는다. 6주×연도 표본 창 재고를 주 전체 공간 확보로 확대하지 않는다.

adapter는 physical=eligible+ineligible, 행/연도/분할 합계, 목표 gap, 셀 gap을 검산한다. bool을 개수로 받지 않으며 음수·unsafe integer·비유한 비율·중복 province·서로 다른 연도열·오염된 미검증 flags는 닫힌 오류로 처리한다. API의 `native_raster_reverified:false`, `learning_ready:false`, `scientific_accuracy_validated:false`를 확인한다. 이 조회로 영상을 새로 native QA하거나 학습 gate를 통과시키지 않는다.

유효 비율·주 내부 비율·최대 단일 클래스 비중을 실제 정책 값으로 표시한다. 나지(bare)는 split별 최소 절대 픽셀, 유효 참조 중 최소 비율, 패치당 최소 픽셀을 채운 최소 기여패치를 각각 보여준다. 절대 픽셀 부족만 채우면 모든 클래스 조건이 충족되는 것으로 설명하지 않는다. 0은 관측된 값이고 null 비율/자료 부재는 미확인이다.

별도 top-level `candidate_quality`는 명시적으로 발행된 source/candidate/QA 고정 receipt를 따른다. available일 때 고정 source SHA·분할 합계·차단 수·관측 시점·현재 원본 SHA와 일치 여부를 검산하고 원본 표와 나란히 표시한다. 생성 원본과 현재 원본이 다르면 새 수집분이 후보에 자동 포함된 것이 아님을 명시한다. 분할 공유 장면 제거가 완전한 공간 독립성이나 현장 정답 인증은 아니다. 후보가 미제공/오염되면 원본이나 과거 문서 수치로 대체하지 않는다. 나지 표는 현재 원본 집계이며 별도 후보의 실제 나지 재QA로 혼동하지 않는다.

## 읽기·상태 방어

ML loader는 기존 API_BASE의 동일 `/data/collection-status`에 Bearer/sessionStorage 인증을 유지한 GET만 보낸다. no-store·redirect:error·AbortSignal, strict UTF-8/중복 JSON·비유한 수 거부와4MiB stream 한도를 사용한다. HTTP 원문 오류/경로를 화면에 표시하지 않는다. 동기 pending gate와 세대/route 검사로 중복 전송, 편집·이동·뒤로 가기·unmount·표시 중단 후 늦은 결과/error/finally를 폐기한다. 자동 polling·학습/수집/등록/승인·gate 해제는 없다.

UI는 SVG Icon, 키보드 focus, caption·scope header, 좁은 화면의 table 가로 스크롤을 사용한다. 실제 수집 현황·후보와 정식 모델 승인/독립 평가를 함께 확정하지 않는다.

## 시험과 실제 적용 — 후속 결과 추가

집중 초기7건은 후보 연결 전 **7 PASS/515.992ms**였으며 `collection-progress-ui-focused-initial-20261018.log`로 원바이트를 보존했다. 후보 연결 후 집중 **8 PASS/0 SKIP**는 `collection-progress-ui-focused-20261018.log`다. 실제 수집 숫자가 아닌 별도 fixture 값을 바꾸어 응답 변화가 반영됨을 검증하고 합계·gap·flags/타입·미확인/0·후보 분리·사본·동시 클릭/stale/stream 한도·기존 GET 재사용·하드코딩 부재를 확인한다. 실제 수집 자료나 native 영상 QA 시험과 구분한다.

전체 프론트 `collection-progress-ui-frontend-20261018.log`는 **288 PASS/0 SKIP/43.7817264초**다. 초기 타입 검사에서는 신규 adapter의 unknown narrowing 오류를 발견해 신규 guard를 명시적으로 분리했고 최종 noEmit 검사 exit0을 확인했다. 이는 운영 자료나 기존 gate 변경이 아니다. 전체 묶음과 집중 묶음은 겹치므로 합산하지 않는다.

Root는 API8002를 새 응답 코드로 재시작하고 `/api/health`200·catalog14행 SHA 동일을 확인했다. 이는 API 실행 중 반영이며 UI fixture 시험과 별도다. UI 담당은 기존 사용자 탭을 유지하고 별도 Chrome 탭에서 실제5174의 품질·정합 감사 화면을 열어 동적 수치를 확인 중이다. 후보 pointer 발행 뒤 실제 비교 결과는 아래 후속 관측에 추가한다. 모바일 검증은 하지 않았다.

완료 코드·시험·실제 화면과 한계를 Root/이해 담당에게 전달하여 쉬운 설명·발표·FAQ·INDEX·변경 이력을 같은 작업 단위로 갱신한다. 원본·분할·모델·원장·예약을 이 UI가 수정하지 않는다.

## 최종 UI 소스 검증과 실제 서버 관측

최종 SVG 아이콘을 기존 `clipboard`로 통일한 뒤 집중 **8 PASS/0 SKIP/1.1917267초**, 빌드 **123 modules/41.81초/exit0**를 확인했다. 로그는 `collection-progress-ui-focused-final-20261018.log`, `collection-progress-ui-build-final-20261018.log`다. 초기 빌드 **120 modules/34.65초**도 별도 원본 로그로 보존한다. 최종 빌드에는 다른 담당의 병행 Toolbox 변경이 포함돼 모듈 수가 증가했다. 전체 프론트 **288 PASS**는 그 실행 시점의 소스 범위이며 새 기능의 중복 합산이나 다른 담당 기능의 브라우저 인증으로 해석하지 않는다. 대용량 chunk 경고는 남아 있고 성능 SLA를 측정한 시험이 아니다.

실제5174→API8002 연결에서 첫 화면은 물리1,400/적격1,122/적격 외278·목표 부족78/셀 부족151이었다. 이후 Root의 제한 수집이 정산된 뒤 **수집 상태 조회**를 눌러 물리 **1,432**, 적격 **1,141**, 적격 외 **291**, train/val/test **658/233/250**, 목표 부족 **59**와 셀 부족 **132**가 실제로 갱신되는 것을 확인했다. 이 수치는 코드 상수가 아니라 당시 응답이다. 해당 관측의 manifest SHA는 `4edb8f513e804c1bd6559d82d61395769fa628b54a580a9de275a0fb370b5bac`, 응답 시각은 `2026-10-18T01:20:17.587761+00:00`이다. `collection-progress-ui-browser-dom-20261018.txt`와 `collection-progress-ui-browser-20261018.png`에 보존한다.

모델 검토 화면에서도 모델을 선택하지 않은 상태에서 **수집 현황 새로 조회**를 눌러 같은 집계·정책·표를 확인했다. 저장 근거는 `collection-progress-ui-ml-browser-dom-20261018.txt`와 `collection-progress-ui-ml-browser-20261018.png`다. 해당 조회 시각01:21:54의 원본 SHA는 진행 중 수집 때문에 별도 값이며 DOM에 원형으로 기록했다. 콘솔 error/warn은 관측 범위0건이었다. 실제1573px 화면에서 문서 너비와 scrollWidth가 같아 가로 넘침0이었다. 모바일·브라우저 지연 주입/인증 실패는 이번 실제 화면에서 재현하지 않았고 해당 경계는 단위 시험과 구분한다.

이 시점에는 candidate pointer가 미발행이므로 후보 미확보 안내를 실제 확인했다. 향후 기존1,400 source에서 고정된 후보가 발행돼도 현재 원본과 SHA가 다르면 새 수집분을 포함한 최신 후보라는 표현을 하지 않는다. 후보 실제 비교 결과는 별도 후속 관측을 추가한다. UI 담당은 현황 GET와 화면 이동만 했으며 수집 실행·학습·모델/원장/예약 쓰기를 하지 않았다. Root의 제한 수집 실행은 별도 작업 이력이다.

## 발행된 고정 후보의 실제 비교 — 후속 브라우저

Root가 `priority-ml-ui-receipt-20261018.json`과 명시 pointer를 발행한 뒤 동일 실제5174→8002에서 고정 후보가 표시됨을 확인했다. 이전 임시 검증 탭은 턴 종료 때 정리돼 새 별도 검증 탭에서 관측했으며 사용자 기존 탭은 변경하지 않았다. **현재 원본 적격1,141(train658/val233/test250)**와 **고정 누출 제외 후보1,106(train639/val217/test250)**가 나란히 표시됐다. 후보는 **미충족·차단4건**이며 자동 학습/승인을 제공하지 않는다. 후보 source SHA `9211524656d92f0fcfcdf11f2ec382965e3aeacbc7f80da5b02f4f59784df1e7`는 기존1,400 원본 시점이다. 현재 원본 SHA `7eac5a54cce152f1f3163e35e8565217b6cbef61b86068150209bb39fa3a9bbe`와 달라 **새 수집분을 포함한 최신 후보라고 해석하지 않는다**는 경고를 실제 확인했다.

후보 관측 시각은 `2026-10-18T01:29:17.721777+00:00`, 첫 실제 화면 응답 시각은 `2026-10-18T01:30:31.171530+00:00`이다. 후보 공유 장면0과 원본 공유 장면1을 구분하고 후보의0을 완전한 공간 독립성/현장 정답 인증으로 표현하지 않는다. 나지 표는 현재 원본 집계이며 후보 나지 재QA로 대신 읽지 않는 설명도 함께 표시된다.

근거는 `collection-progress-ui-candidate-browser-dom-20261018.txt`와 `collection-progress-ui-candidate-browser-20261018.png`다. 실제 비교 표의 텍스트·SHA·응답시점,1573px 가로 넘침0 및 관측 콘솔 error/warn0을 확인했다. 첫 GET은 후보3SHA 검산을 포함해 수 분 읽기 상태를 보였으며 중복 호출·임의 재시작을 하지 않았다. 이 관측은 응답시간 SLA 인증이 아니다. 소스/시험은 기존 동결7개 SHA와 불일치0이며 이번 후속은 브라우저와 문서/증거만 추가했다.

명시 **수집 현황 새로 조회**도 눌러 이전 표가 즉시 없어지고 단일 busy로 전환한 뒤 같은 후보/원본 구분이 재표시됨을 확인했다. 최종 응답 시각은 `2026-10-18T01:31:51.731994+00:00`이다. 이 수동 재조회 근거는 `collection-progress-ui-candidate-refresh-dom-20261018.txt`, `collection-progress-ui-candidate-refresh-final-20261018.png`이며 종합 관측은 `collection-progress-ui-candidate-browser-20261018.json`이다. 중간 `candidate-refresh-20261018.png`는 표 아래로 스크롤이 넘어간 뷰포트여서 최종 비교 그림으로 사용하지 않고 원본 그대로 보존했다. 제품7개 SHA 불일치0을 재확인하고 문서154를 최종 동결한다.

## 최종 정산 후 실제 재조회 — 1,464 / 1,164

앞선1,400 및1,432 관측은 당시 이력으로 보존한다. Root의 round3 정산과 최신 API 반영 뒤 별도 검증 탭에서 명시 **수집 현황 새로 조회**를 눌러 물리 **1,464**, 적격 **1,164**, 적격 외 **300**, train/val/test **681/233/250**, 목표 부족 **36**, 셀 계획 부족 **109**를 실제 확인했다. 원본 SHA는 `c57a1768a87fae7b0fd0c5ec8e451c439d35c65bf54d99f1f7b38dc98928e33e`, 응답 시각은 `2026-10-18T01:41:01.686168+00:00`이다. 고정 후보는 기존1,400 source의 **1,106(639/217/250)**·차단4건·준비 미충족으로 그대로 표시되며 현재 원본과 다르다는 경고가 유지됐다. 나지 train1,580/val209/test1,025 픽셀 선언 집계는 여전히 비율 및 최소 기여패치 조건 미달로 표시된다.

최종 근거는 `collection-progress-ui-final1464-browser-20261018.json`, `collection-progress-ui-final1464-dom-20261018.txt`, `collection-progress-ui-final1464-20261018.png`, `collection-progress-ui-final1464-candidate-20261018.png`다. 최초 전용 탭 경로가 외부 조작으로툴박스12로 바뀐 관측은 Root에 알렸고, 본인 탭ID만17로 복구해 수동 조회했다. 다른 탭·제품 코드는 변경하지 않았다. 이후 최종 경로17·응답·콘솔0·가로 넘침0·제품7개 SHA 불일치0을 확인했다.

Root가 HEAD76949 기준에 본 UI7개 파일만 적용하고 다른 담당 Toolbox/App/WIP를 제외한 격리 프런트 검증도 수행했다. 최종 **288 PASS/0 SKIP/36.4999934초**, 빌드 **120 modules/32.33초**이며 `priority-frontend-isolated-tests-20261018.log`, `priority-frontend-isolated-build-20261018.log`, 소스핀 `priority-frontend-isolated-source-20261018.json`에 남겼다. 초기 격리 export fixture 누락193PASS/33FAIL, 부분 fixture254PASS/6FAIL은 환경 구성 중 근거로 보존됐고 최종 fixture 연결 후 통과했으며 제품 코드는 바뀌지 않았다. 이 격리 결과와 앞선 공동 workspace123modules 빌드는 실행 범위가 다르므로 하나의 실행 수치로 혼용하지 않는다. 최종 브라우저 후속은 소스/시험 재편집 없이 문서·증거만 추가했다.


## 2026-10-18 10:54 KST — 4차 수집 완료·159 후보 UI 승계

앞선1464/1164 관측 이후4차 반텐2025 g01/g02가 정상종료했다. 신규32물리/32적격/나지391픽셀로1496물리/1196적격/300부적격,train681/val265/test250이다. 전체1200 부족4·주연도 셀당28 부족97이다. 최초요청대비96물리/74적격을 추가했고 셀 부족151→97,나지추가553픽셀이다. 4차32개 실제래스터·유효/주내·클래스·SHA 및source/worker/원장 정합성을12.7664229초에 재검증했고 기존1464행과pending2전액136314880B를보존했다. 신규총계상2085380105B/한도잔여2209587191B,429false/실행lock정상해제다. 원본검증분할 나지는209→600픽셀,기여0→1개로 개선됐으나0.5%·기여5패치 기준은미달이다. 1200개충족과학습준비는별개다.

159의1432행고정source→누출16행제외후1416행/1125적격 후보는실제QA·4435파일SHA검증후명시receipt로승계했다. 기존153후보/receipt와교체전pointer원바이트를보존하고,새receipt3핀검산·readyfalse/차단4 검산후pointer원바이트가변하지않았는지비교하고os.replace로교체했다. DatasetRegistry/모델/원장/기존분할/학습상태전이0이다. 부가connectivity NOT_CAPTURED_BUDGET 한계는유지한다. 최신1496원본의55적격(23+32)은새1125후보QA범위밖이며sourceSHA불일치경고를유지한다.

실제API8002/프런트5174 소스변경·재시작 없이기존GET·명시수동새로조회로승계됐다. 브라우저응답01:52:31.145480Z에서원본1196(681/265/250)·후보1125(658/217/250)·차단4/미준비·시점불일치·원본검증나지600/기여1을확인했다. console warning/error0,가로넘침0이며분석/학습/배포/등록버튼을실행하지않았다. 전체페이지스크린샷1회timeout은브라우저캡처한계로기록하고실제viewport PNG/DOM/JSON을보존한다. 제품소스변경없으므로기존48관련backend·288격리frontend·build120근거를유지하며새전체회귀통과를주장하지않는다.

5차동자바2021 g02/g03은plan fe20a0b67e5b6215d3f0e4814a07e48b9645a2fb6ba90893b4c3049cd62b8ade,wrapperPID33756으로시작했고완료는미확인이다. 기존budget/2worker/2초/429중단/3000상한/고정split/품질정책을유지한다. 같은collector중복실행금지.157표적은계속집행차단이며160로컬자산영역검사작업은다른채팅소유기록과중복하지않는다. geoai-2 ACTIVE10분보고지속,전체개발미완료다.

근거:evidence/integration/priority-collection-round4-final-20261018.json,priority-collection-independent-round4-20261018.json,priority-collection-round5-launch-20261018.json,priority-ml-next-ui-promote-20261018.py,priority-ml-next-ui-receipt-20261018.json,priority-ml-next-ui-round4-20261018.json,priority-ml-next-ui-round4-20261018.png 및docs/implementation/159_next_collection_candidate_qa.md.
