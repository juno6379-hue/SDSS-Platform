# 119 — 같은 변화쌍의 전체 래스터 전이행렬과 실제 클래스 범례

상태: **TESTED_SYNTHETIC / 운영 자료 실행 없음**. 118에서 수동 조회한 같은 receipt/raw report와 명시 변화쌍을 로컬 검산하여9×9 전이행렬·클래스별 이전/이후/순변화·보고서 원문 이름과 ID 범례를 표시한다. 새 GET/POST·학습·등록·다운로드·backend/API 변경이 없다. 상단 PNG 지도·KPI·다른5개 모델과116 실행/상태/보고서/다운로드 계약을 그대로 유지한다.

## 계약과 검산

새 pure `lclucTransitionAdapter.ts`의 `workflowTransitionStats(receipt,rawReport,pair)`는118 `workflowChangePair`를 재사용해 같은 성공 receipt/report·연도·pair·GeoJSON artifact pin을 결합한다. 실제 보고서의 class_names9개와 선택 change.class_names 순서가 같아야 한다. 이름을 추정·번역·자동 채움하지 않으며 중복 이름도 각 ID로 구분한다. control/단독 surrogate·빈/공백뿐인 이름·sparse array·잘못된 shape를 거부한다.

transition_pixels와transition_area_m2는 각각9×9다. 픽셀은 정확한0이상 safe integer, 면적은 finite0이상이다. 픽셀0과 면적0의 위치도 같아야 한다. 행은 이전, 열은 이후이며 행합=이전·열합=이후를 계산한다. 픽셀 총합=valid_pixels, 면적 총합=total_area_m2, 비대각 면적합=changed_area_m2, 클래스 순면적=열합−행합이 보고서의 class_net_area_m2와 일치해야 한다. change_rate는 **면적 기준 changed/total**이며 픽셀 비율이 아니다. 총면적0이면 rate=null만 허용한다.

면적 허용오차는 `max(1e-6m²,1e-8×max(1,total_area_m2))`이며 무차원 rate는 별도1e-8 허용오차로 비교한다. 통계 basis는 정확히 `full_valid_raster; vector truncation does not affect statistics`, 면적 방식은 `projected_grid_area_m2` 또는 실제 서비스의 `ellipsoidal_geodesic_m2`다. 지원하지 않는 방법·수치/형/합계/rate/net 불일치는 고정 오류로 거부하고 값을 보정·추정하지 않는다. 반환 배열/클래스 정보는 원본과 분리한다.

## 화면과 단위

새 `LclucTransitionSummary.tsx`는 검산된 stats만 받는다. 기본 pair는118처럼 빈 값이며 사용자가 pair를 고르면 **이미 수동으로 읽은 raw report만 로컬 검사**한다. 이때 행렬/범례가 표시되지만 지도 asset GET은 여전히 명시 지도 읽기 버튼만 실행한다. 통계가 잘못되면 안전 안내를 표시하고 이전 지도는 숨기며 지도 읽기도 비활성화한다.118의 validPixels/changedAreaM2 지도 통계도 검산과 일치한 경우에만 표시된다.

단위 선택은 픽셀/m²/ha다. 픽셀은 transition_pixels와 클래스 pixel 합계를 표시하고 면적은 transition_area_m2와 면적 합계를 사용한다. ha는 m²/10000이다. 픽셀 수를 면적 단위로 이름만 바꾸거나 모든 픽셀에 일정 면적을 가정하지 않는다. 클래스 순변화는 이후−이전으로 음수도 그대로 표시한다. 면적은 소수6자리 반올림이며 작은 값의 표시 반올림과 원래 수치를 구분한다. 상단 유효 픽셀·전체/변화 면적(m²)·면적 기준 변화율(%)은 단위를 명시한다.

9×9 표는 caption·행/열 scope header·행열 합계·키보드 초점 가능한 가로 스크롤 영역을 갖춘다. 클래스 표도 caption/행 header를 사용한다. 작은 폭에서는 표 내부만 가로로 스크롤하고 클래스 이름은 줄바꿈한다. SVG는 기존 공통 matrix/map 아이콘을 사용한다.

## 지도 색상과 수명

지도 fill은 검증된 GeoJSON의 `to_class` ID0..8에 고정 팔레트를 매핑한다. 범례는 **이후 클래스 ID와 실제 raw report class_names 원문**이다. 같은 이름도 ID를 표시한다. 색상은 시각화 선택이며 공식 분류 색상·모델 평가·기관 taxonomy 인증이 아니다. 모든9개 범례를 표시하며 벡터에 보이는 도형 수와 전체 클래스 통계를 혼동하지 않는다.

vector_truncated=true이면 지도는 벡터 일부지만 행렬·클래스 합계·전체 면적은 전체 유효 래스터 기준임을 경고한다. 실제0도형/변화0인 pair는 대각선의 유효 픽셀과 면적을 그대로 표시하며 임의0행렬이나 가짜 도형으로 대체하지 않는다. 과학 정확도/GMAIS 인증 false·source 권위 미검증은 유지한다.

118의 pair/input/receipt/report/route/back/unmount 세대 방어·stream8MiB/SHA·WebGL cleanup·명시 GET을 보존한다. pair 변경은 이전 지도를 비우고 같은 report의 새 통계를 검산한다. 단위 변경은 로컬 표시만 바꾸며 지도 GET이나 실행을 만들지 않는다. 새 unit 선호는 다음 pair에도 유지되지만 수치는 항상 해당 pair의 검산 결과로 갱신한다.

## 소유 범위와 시험

- UI: 기존 `LclucWorkflowChangeMap.tsx`/scoped CSS, 새 Summary와 SSR/소스 계약 시험.
- 계약: 새 pure transition adapter와 시험12건. 기존118 adapter/client·backend/main/API/상단 Workspace 변경0.
- Root: 독립8건·실제 브라우저·보존/공통 문서·이해자료·Git.

집중21 PASS/1.681초(UI9+pure12)로 실제 저장된3연도 CPU fixture의1→2 전이256픽셀/25600m²·net±25600m²·ha±2.56, unchanged pair, 실제 ID/이름/팔레트·중복 이름·HTML escape·단위 구별·caption/scope/scroll 계약을 확인했다. UI 시험은 실제 component를 esbuild로 임시 메모리 번들해 React server rendering으로 표/범례 HTML을 검사하며 실제 브라우저 상호작용과 구분한다. 로그 `evidence/integration/lcluc-transition-ui-related-20261018.log`.

최초 build는 동적으로 spread한 MapLibre match 표현식이 최소 tuple 타입을 만족하지 않아 TS2352로 실패했다. 명시9개 ID/color match tuple로 정정했고 최초 로그 `lcluc-transition-ui-build-initial-20261018.log`를 보존했다. 최종 전체 frontend **250 PASS/29.208초**, production build **104 modules/19.37초/exit0**다. 로그는 `lcluc-transition-ui-tests-20261018.log`와 `lcluc-transition-ui-build-20261018.log`이며 기존 큰 bundle 경고는 남는다. Root 독립8 PASS/0.604초(`lcluc-transition-independent-20261018.log`)와 겹치는 계약 사례를 전체 시험 수에 합산하지 않는다.

pure adapter 최초12건 중1건은 선행118의 안전한 오류가119의 고정 오류 문구로 통합되지 않은 계약 불일치로 실패했다. 오류 경계를 통합한 뒤 최종12 PASS/0.427초(`lcluc-transition-adapter-focused-final-20261018.log`)이며 최초 `lcluc-transition-adapter-focused-20261018.log`를 보존한다. 이12건은 위 집중21건과 겹쳐 합산하지 않는다.

## Root 실제 브라우저와 보존

`evidence/integration/lcluc-transition-browser-20261018.json`은 별도 fixture UI5175/API8003에서 최초 pair/행렬이 비어 있음을 확인한다.2020-2021을 선택해 이전 trees 행→이후 grass 열의256픽셀·25600m²를 읽고, ha 전환에서 trees net−2.56/grass net+2.56을 확인했다. 실제 보고서9개 이름+ID와 grass ID2의 rgb(132,204,22), 실제 lime Polygon을 확인했다.2021-2022에서는 변화율0·grass 이전/이후2.56ha·net0과0도형 안내가 공존하고 행렬은 유지됐다.2020-2022로 표가 갱신되며 pair 변경은 이전 지도를 제거하고 뒤로 가기 복귀에서는 이전 행렬/지도가 표시되지 않았다. 사용자 원래 탭은 보존했다.

최종 화면은 `lcluc-transition-matrix-final-20261018.png`, `lcluc-transition-class-map-20261018.png`, DOM은 `lcluc-transition-ha-dom-20261018.txt`, `lcluc-transition-unchanged-dom-20261018.txt`, `lcluc-transition-pixels-dom-20261018.txt`에 있다. 영상과 hand-set 미학습 TinyUNet·승인 metadata는 명시 fixture이며 실제 CPU 추론 결과를 사용했다. 임의 geometry 추가나 실제 독립 평가/승인 자료가 아니다.

모바일 viewport·강제 지연·Bearer 인증 브라우저·손상 행렬/zero-valid null rate·truncated=true 브라우저 fixture는 재현하지 않았다. 해당 음성·zero-valid·단위/오류·인증·세대 근거는 adapter/SSR/mock client 및 이전 API 시험으로 구분한다. 이번 fixture의 unchanged는 유효256픽셀의 변화0이며 유효 픽셀0과 다르다.

`lcluc-transition-live-integrity-20261018.json`은 보호141개·이전 증거952개 불변, 기존 소스269개 중 허용2개 외 변경0·catalog14행 canonical 불변·backend/API 전체 소스 불변을 확인했다. 운영 수집·학습·등록·배포·Workflow dispatch0이다. backend/API 변경이 없어 전체 backend를 다시 실행하지 않았으며118의1170건/1169PASS/기존1SKIP·389.307초를 이전 근거로 구분한다. 원본/원장/예약/lock/분할/실모델을 보존하며 전체 프로젝트 완료로 표현하지 않는다.
