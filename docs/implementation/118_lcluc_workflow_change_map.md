# 118 — 같은 LCLUC 실행의 선택 변화쌍 지도 연결

상태: **TESTED_SYNTHETIC / 운영 자료 실행 없음**. 116·117의 성공 receipt와 수동으로 읽은 raw timeseries 보고서에서 선택한 변화쌍 하나를 기존 인증 asset index API로 읽고 별도 MapLibre 지도에 표시한다. 기존 상단 PNG 기반 지도·KPI·다른5개 모델·공통 Workspace/API는 변경하지 않는다. 표준 GMAIS Result 발행이나 과학 정확도 인증이 아니다.

## 입력·파일·렌더링 계약

`lclucChangeMapAdapter.ts`의 `workflowChangePair(receipt,rawReport,pair)`는 기존 receipt/report parser를 재사용해 같은 workflow ID/Trace·model checkpoint·연도·변화쌍·unique GeoJSON artifact index/SHA를 결합한다. Windows 경로는 검증 시 구분자만 정규화한다. 호출자는 임의 URL/경로를 실행하지 않는다.

지도 선택은 기본 빈 값이며 사용자가 pair를 명시 선택한 뒤 **선택 변화쌍 지도 읽기**를 눌러야 GET `/v1/lcluc/workflows/{id}/assets/{index}`를 호출한다. 보고서 조회·패널 열기·렌더링·pair 변경에서 자동 다운로드하지 않는다. 기존 `geoai_token` 탭 세션 Bearer와 same-server origin을 유지한다.

`workflowGeoJSON`은 새 지도 읽기 전용 client 함수다. Response stream의 Content-Length가8MiB를 초과하거나 실제 누적 바이트가8MiB를 넘으면 reader를 cancel하고 거부한다. 정확히8MiB는 허용한다. bounded byte snapshot의 SHA-256이 선택 receipt의 hash와 정확히 같아야 하며 strict UTF-8 decode/JSON parse 뒤 geometry guard를 호출한다. stale stream도 취소/폐기하고 hash 계산 뒤 세대를 다시 확인한다. 이는 지도 payload 상한이며 HTTP chunk·JSON object·GPU·프로세스 RSS 전체의 하드 상한이나 timeout 보장이 아니다. 취소는 best effort이며 이미 발생한 서버 읽기를 롤백하지 않는다.

`parseWorkflowChangeGeoJSON`은 새로 복사한 FeatureCollection만 반환한다. Polygon/MultiPolygon·2차원 finite WGS84 좌표·닫힌4점 이상 ring·최대5000 features/100000 vertices·9개 class의 from/to/transition code·고정 미검증 quality 표시를 검사한다. 외부 CRS/링크/다른 geometry·잘못된 class·도형 개수 불일치·범위 밖 좌표를 거부한다. 경도 span/edge가180도를 넘어 세계 전체 fit이 모호한 경우 거부한다. MapLibre bounds 순서는 `[[west,south],[east,north]]`다. self-intersection·구멍의 포함 관계 등 실제 위상이나 과학적 정확도를 검증한 것은 아니다.

## 화면과 수명

`LclucWorkflowChangeMap.tsx`는 별도 preview이며 외부 tiles/glyph source를 사용하지 않는 중립 배경이다. 검증된 도형 fill/outline과 공통 SVG 확대·축소·전체 범위 버튼, 로컬 산출물/미인증 attribution을 표시한다. MapLibre load 뒤 source/layer를 추가하고 검증 bounds로만 이동한다. 오류·WebGL 미지원/컨텍스트 소실은 고정 안전 안내를 표시한다. unmount/결과 변경에서 load/error/contextlost listener·ResizeObserver·map instance를 정리하고 늦은 callback을 폐기한다.

0 features는 유효한 빈 결과다. map instance나 가짜 도형을 만들지 않고 **표시할 변화 도형0개**와 래스터 통계가 별개임을 표시한다. vector_truncated=true이면 지도가 일부 벡터 도형이며 validPixels/changedAreaM2는 전체 유효 래스터 통계임을 경고한다. polygon 면적을 새로 계산하거나 래스터 통계를 도형 수에서 추정하지 않는다. 과학 정확도/GMAIS 인증 false와 source 권위 미검증을 유지한다.

pair 변경은 지도 결과/오류/세대만 초기화하고 receipt/report를 유지한다. 입력·조회 ID·receipt/report·route/back/unmount 변경은 이전 지도를 제거하고 늦은 응답으로 지도·오류·busy가 되살아나지 않게 한다. 동기 pending guard가 중복 클릭을 제한한다. 상위 report의 WorkflowFlight와 독립된 지도 세대를 사용하며 상위 보고서 재조회 중에는 새 지도 읽기를 비활성화한다. 표시 중단은 실행 취소/DB·파일 rollback이 아니다.

## 변경 범위

- UI 소유: 기존 `LclucWorkflowPanel.tsx`에 검증 raw report 보존·별도 child 슬롯 추가, 기존 client에 bounded GeoJSON 함수 추가, scoped CSS 확장, 새 `LclucWorkflowChangeMap.tsx`/`lclucWorkflowChangeMap.test.mjs`.
- 계약 담당: 새 pure `lclucChangeMapAdapter.ts`와 해당 test.mjs. 기존 요청/receipt adapter의 계약을 변경하지 않는다.
- Root: 실제 nonempty CPU fixture에서 발견한115 report JSON 동치 비교 보완과 별도 회귀·보존·실제 브라우저·공통 문서·이해자료·Git.

운영 Store·원본·원장·lock·예약·분할·실모델의 변경·실자료 학습·수집·배포를 하지 않는다. 실제 Draft/독립 라벨 미확보·6밴드 per_scene 제품/구름 mask 차단을 해제하지 않는다.

## 시험과 실제 브라우저 근거

집중 **23 PASS/16.725초**(pure adapter13 + UI/client10), 전체 frontend **229 PASS/25.048초**, production build **102 modules/21.67초/exit0**다. 로그는 `evidence/integration/lcluc-change-map-ui-related-final-20261018.log`, `lcluc-change-map-ui-tests-20261018.log`, `lcluc-change-map-ui-build-20261018.log`다. 기존 큰 bundle 경고는 남으며 빌드 오류가 아니다. adapter 별도 집중13 PASS/14.751초는 위23건과 겹치므로 합산하지 않는다.

stream 시험은 exact8MiB 허용·Content-Length 초과 선취소·누적 초과 취소·잘못된 SHA/UTF-8/JSON·stale 취소·임의 경로 거부·Bearer/index 요청을 확인했다. adapter는 Windows 경로/receipt/report/pair/SHA 결합·Polygon/MultiPolygon·0도형·부분벡터 통계 구별·geometry 오염·개수/정점 상한·경도180도 모호성 거부·새 객체 복사를 확인했다. 생성16×16 영상·명시 mock 승인 metadata의 실제 CPU empty와 nonempty 결과 및 GeoJSON byte SHA를 검사했다. 학습·운영 자료 실행·독립 과학 평가가 아니다. 수동 버튼/빈 선택·정리/오류 경로의 일부 시험은 소스 계약 검사이며 실제 WebGL/브라우저 수명 재현과 구분한다. 기존 WorkflowFlight의 동기 pending/세대·이동·unmount 응답 폐기 시험도 전체 frontend에 포함된다.

### Root의 실제 nonempty CPU 경로 보완

최초 실제3연도 nonempty fixture 실행은 CHECKPOINT_SHA_MATCH=True였지만 RUNNER_REPORT_MISMATCH로 실패했다. 진단 로그 `evidence/integration/lcluc-change-map-nonempty-initial-diagnostic-20261018.log`는 Rasterio가 반환한 geometry 좌표 tuple과 저장 JSON의 list 차이를 확인한다. 빈 도형 fixture에서는 드러나지 않았던 문제다. Root는115 core의 report 비교 한 곳만 finite canonical JSON 동치로 바꾸어 정상 직렬화 표현 차이를 수용했다. 값·수치형 차이는 여전히 거부하며 bool/int 변조 거부와 실제 nonempty CPU 성공 회귀2건을 추가했다. 기존 checkpoint/gate/claim/실패 no-retry/파일 보존 정책은 바꾸지 않았다.

core+기존API34 PASS/25.842초(`lcluc-change-map-core-api-final-20261018.log`), Root 독립6 PASS/0.436초(`lcluc-change-map-independent-20261018.log`)를 확인했다. 별도 기존 fixture·실제 운영 모델 승인 증거로 합산하지 않는다. 생성 영상·hand-set 미학습 TinyUNet·명시 fabricated 승인 metadata로 실제 추론한 결과이며 GeoJSON 도형을 임의로 덧붙인 시험이 아니다. 최초 실패 진단과 최종 성공 근거를 모두 보존한다.

### 실제 브라우저

Root는 별도 fixture UI5175/API8003에서 성공3연도 receipt/report를 읽은 뒤2020-2021을 명시 선택·GET해 SHA 확인을 거친 실제 MapLibre Polygon1개(정점5·유효256픽셀·변화25600m²)를 확인했다. pair를2021-2022로 변경한 직후 이전 지도는 제거되고 보고서는 유지됐으며, 다시 명시 읽기 후0도형 안내와 canvas 미생성을 확인했다. 근거는 `lcluc-change-map-nonempty-20261018.png`/`lcluc-change-map-nonempty-dom-20261018.txt`와 `lcluc-change-map-empty-20261018.png`/`lcluc-change-map-empty-dom-20261018.txt`다.

종합 `evidence/integration/lcluc-change-map-browser-20261018.json`은 최초 pair가 빈 값이며 선택만으로 지도를 렌더링하지 않음,2020-2021/2020-2022의 실제 도형 렌더링과2021-2022의0도형,빠른 pair 변경에서 이전 지도 제거·보고서 유지,뒤로 가기 후 이전 지도/보고서 미표시·사용자 원래 탭 보존을 확인한다. 고정 artifact SHA는 `6f318eafc66bce6ebf62a06c96f197a0bdafe18008c6412665759b461ff93ec5`다.

모바일 viewport·강제 네트워크 지연 주입·WebGL 미지원의 실제 브라우저 재현은 수행하지 않았다. 빠른 pair 전환/뒤로 가기 관측과 generation의 단위시험 근거를 구분한다. fixture 브라우저 token은 비어 있었으며 Bearer 보존/오류는 mock client 및 이전 API 시험의 별도 근거다. fixture vector_truncated=false이므로 잘린 도형 경고는 source/단위 계약 근거이며 실제 truncated 브라우저 fixture를 확인한 것으로 표현하지 않는다. 렌더링 구조/범위/hash는 실제 위상·기관 원출처·독립 과학 정확도 인증이 아니다.

### 전체 회귀와 보존

Root 전체 backend는 **1170건 중1169 PASS/기존 Windows1 SKIP/389.307초/exit0**, `evidence/integration/lcluc-change-map-full-backend-20261018.log`다. 신규·관련·독립 묶음을 전체 건수에 중복 합산하지 않는다. `lcluc-change-map-live-integrity-20261018.json`은 보호141개·이전 증거925개 불변, 기존 소스265개 중 위 허용5개 이외 변경0, catalog14행 canonical 불변·main/기존API 불변을 확인한다. 운영 수집·학습·등록·배포·Workflow dispatch0이며 원본/원장/예약/lock/분할/실모델을 보존한다. Node mock stream/geometry 시험, 실제 CPU 추론, 실제 브라우저 관측과 운영 과학 검증을 구분한다. 이 단위 완료는 전체 프로젝트 인수가 아니다.
