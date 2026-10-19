# GeoAI Toolbox 메인 화면 시각 개선 — 2026-10-18

## 문제와 변경

텍스트 목록 중심이던 모델 허브를 사용자가 제공한 화면 구성을 참고해 이미지 카드 중심으로 바꿨다. 기존 SDSS 상단·사이드 메뉴와 같은 파란색/흰색 패널을 사용한다. 6개 모델 카드, 대상 6개 주 지도, 실행 흐름, LCLUC 미리보기, 우측 상태 요약·최근 Job·등록 데이터·빠른 이동을 배치했다. 카드 이미지는 기존 `/reference/model-1.png`부터 `model-6.png`의 기능 안내용 화면이며 실제 분석 결과가 아니다.

`GeoAIToolbox.tsx`, `geoai-toolbox.css`, `toolboxAdapter.ts`를 추가하고 `PlatformShell.tsx`의 기존 텍스트 허브를 새 컴포넌트로 연결했다. `App.tsx`는 Toolbox 전용 클래스와 기존 조회 자원/탐색 콜백을 전달한다. 기존 Dashboard의 ReferenceMap과 공개 참조 경계를 재사용한다. 지도 경계는 공식 사업 경계 확정이 아니다.

## API·상태·이동 계약

- 기존 GET `/api/tools`, `/api/datasets`, `/api/models`, `/api/jobs` 결과를 전달받는다. 별도 쓰기 요청·자동 분석 실행은 없다.
- UI 모델 ID `lcluc/climate/carbon/biodiversity/coastal/flood`를 각각 API의 `lcluc/climate-downscaling/net-carbon-footprint/biodiversity/sea-level-subsidence/flood-drought`에 대응한다.
- `implemented`가 엄격한 boolean true/false일 때만 기존 구현/연계 대기로 분류한다. 누락·조회 오류는 미확인이다. 코드 구현은 과학 정확도나 운영 승인이 아니다.
- 조회 실패 시 오래된 데이터셋/모델 건수·실행 이력을 정상값으로 표시하지 않는다. 정상 조회의 빈 오류 문자열은 경고로 처리하지 않는다.
- 실제 관측은 도구6(구현1·대기5), 데이터셋6, 모델1, Job0이다. 참고 이미지의 Ready·완료 이력·가용률을 합성하지 않았다.
- 카드·LCLUC 미리보기는 기존 `/view/24?model=…&tab=input`으로 이동한다. 워크플로우와 빠른 이동은 기존 메뉴를 연다. 실행·승인은 해당 상세 화면의 기존 계약을 따른다.

## 검증 및 실행 서버

집중 adapter 시험5 PASS, 독립 API/계약 검토11 PASS. 전체 프론트 `node --test src/*.test.mjs`는293 PASS, 실패/건너뜀0,43.750초, 종료0이다. 세 집합은 겹치므로 합산하지 않는다. `npm run build`의 TypeScript·Vite 빌드가 종료0으로 통과했다(123모듈, Vite44.32초). 출력 JS1.739MB에 대한 chunk-size 경고는 남아 있다.

실행 중 Vite `127.0.0.1:5174`에서 실제 브라우저로 여섯 카드의 올바른 상세 화면과 허브 복귀, 반텐 지도 선택·전체 복귀, 데이터 카탈로그 바로가기를 확인했다. 기본 화면과390×844 모바일을 확인했고 페이지 가로 넘침은 없다. 모바일은 카드1열, 넓이에 따라2/3열로 배치한다. 최종 새로고침 이후 새 console error는0이다. 중간 연결 시점10:17:10의 HMR 오류1개는 수정 전 이력으로 보존했다.

기존 상세 화면 관련5개 파일은 작업 전 SHA와 동일하다: ModelAnalysisWorkspace.tsx, model-workspace.css, LclucWorkflowPanel.tsx, SDSSChrome.tsx, sdss-chrome.css. 화면 변경은 실제 Vite HMR/새로고침에도 반영됐으며 빌드만 통과한 상태와 구분한다. API/Vite 재시작0, 수집·Registry·학습·인증 변경0이다. 기존 병렬 개발과10분 보고 예약은 계속된다.

## 근거·인계

- `evidence/integration/toolbox-ui-preflight-20261018.json`: 작업 전 SHA
- `evidence/integration/toolbox-ui-independent-20261018.json`: 독립11개 검사
- `evidence/integration/toolbox-ui-final-20261018.json`: 최종 SHA/회귀/브라우저 검증
- `evidence/integration/toolbox-ui-desktop-top-20261018.jpg`, `toolbox-ui-desktop-20261018.jpg`, `toolbox-ui-mobile-20261018.jpg`: 실제 브라우저 화면
- `docs/understanding/06_toolbox_visual_hub_20261018.md`: 쉬운 설명·발표 대본·FAQ

UI 담당 구현과 독립 리뷰를 Root가 통합·실제 브라우저 검증했고 이해 담당에게 완료 코드와 시험 증거를 인계했다. 이 작업은 Toolbox 메인 화면 개선 완료이며 전체 프로젝트·학습 준비·운영 배포 완료를 의미하지 않는다.

## 11:12 KST 최신 main 기준 재검증·hover 대비 수정

152–161 완료 main8cf7b94를 기준으로 Toolbox의 App/PlatformShell 연결과 신규4파일을 다시 검토했다. 기존 CollectionProgress/Status/ModelReview 및 adapter/client/css/test7개는 main과 같고 상세5파일은 최초 관측 SHA와 동일하다. 등록 데이터셋6건과 수집 패치1235개는 단위가 달라 바꿔 표시하지 않는다.

실제 Carbon 카드 hover에서 배경rgb18,110,134에 본문rgb6,25,119·제목rgb35,76,105가 겹쳐 대비가 낮아졌다. style.css 후반의 공통 `button:hover:not(:disabled)` 배경 재선언이 원인이었다. Toolbox 범위에 우선순위가 높은 hover 규칙을 추가해 카드의 흰색/연한 블루 gradient와 navy 본문/제목을 유지했다. 미리보기 hover의 이미지와 주요 파란 버튼도 보존했다. 실제 포인터가 카드에 올라간 상태에서 HMR 후 계산 스타일과 스크린샷을 확인했다. 글로벌 CSS와 다른 메뉴는 수정하지 않았다.

현재 전체 frontend293 PASS/0 FAIL/0 SKIP·52.5858786초·exit0을 확인했다. 그 뒤 CSS 전용 수정은 실제 hover 확인과 최종 `npm run build`의 TypeScript/Vite123모듈·32.54초·exit0으로 검증했다. 출력CSS228.17kB/JS1739.26kB이며 기존 chunk-size 경고는 남는다. 수정 전53.49초 build와 최종 build를 구분한다.

실행5174에서 기존 LCLUC Workspace 제목·정확한 모델 URL, 모델 허브 복귀, 가로 넘침false, console error/warn0을 확인했다. 초기 여섯 모델 동선/모바일 검증은10:24 이력이며 이번에 새로 전부 반복했다고 표시하지 않는다. 실제 화면 반영과 배포용 build, 코드시험을 구분한다. API/수집/학습쓰기·서버 재시작0이다.

최종 근거는 `toolbox-ui-current-final-20261018.py/json`, `toolbox-ui-current-frontend-20261018.log`, `toolbox-ui-hover-build-20261018.log`, `toolbox-ui-current-base-review-20261018.json`, `toolbox-ui-hover-before/after-20261018.jpg`, `toolbox-ui-current-browser-20261018.txt/jpg`다. base-review의 CSS핀은 hover 수정 전 관측이며 최종CSS SHA는b962623c6e30844547f5c8942b266cac003180f52415c7ea64dcc8220d2393da다. 관련 이해자료에도 해설·대본·FAQ를 갱신한다.
