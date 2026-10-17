# UI v2.0 계층형 Workspace 구현·검증

## 분석 기능 아이콘 개선

지도·패널·도움말 추가 통일: 각 지도당 확대/축소/전체/영역 표시/선택 범위5개 버튼, 모델별 패널 제목7개, 도움말1개를 공통 SVG로 교체했다. MapLibre 기본 확대/축소 컨트롤은 중복 생성하지 않는다. 보조 지도가 있는 탄소·생물다양성은10개 지도 버튼 모두 적용한다. 도움말 열림 상태/영역 표시 상태를 aria-expanded/aria-pressed로 제공하고 작은 화면에서도 이름 있는 도움말 버튼을 유지한다. 실제 브라우저로6개 모델 SVG 개수를 대조하고 도움말 열기·닫기/영역 전환·확대를 점검했다. `panel-map-help-icons-build.log`, `panel-map-help-icons.jpg`에 근거를 남겼다.

추가 통일: `Icon.tsx`의 공통 SVG frame을 좌측 메뉴·분석 탭·주요 지표·실행/비교/리포트 버튼에 적용했다. 6개 모델의24개 지표는 산림·맹그로브·기온·강수·탄소·서식지·침수·침하·인구·경보 등 지표 의미에 맞는 전용 아이콘이다. 모든 모델을 실제 브라우저로 순회하여 메뉴7/지표4/액션3, 선 굵기1.65를 확인했다. 빌드 로그 `unified-icons-build.log`, 화면 증거 `unified-icons-lcluc.jpg`. 기존 버튼 동작과 접근성 텍스트는 유지한다.

6개 모델의 분석 탭에서 위치 기반 문자기호를 기능 의미에 따른 선형 SVG(`AnalysisIcon.tsx`)로 교체했다. 지도·시계열·변화·행렬·핫스팟·지역비교·내보내기와 모델별 통계/연결성/노출/시나리오 등은 동일24px/1.65px 선 굵기를 사용한다. 아이콘은 장식으로 처리하고 버튼의 텍스트 접근성 이름과 기존 동작을 유지한다. 7개 LCLUC 탭의 실제 SVG 렌더링/정렬을 브라우저에서 확인했다. 화면 증거 `evidence/ui-20261017/analysis-icons.jpg`, 빌드 로그 `icon-build.log`.

## 추가 요청: PNG 6종과 화면 구성 일치

사용자가 2026-10-17 현재 시점에 6개 모델 화면을 제공 PNG와 같게 요청하여, 초기 generic 입력/preview 구조를 PNG별 분석 대시보드로 교체했다. `ModelAnalysisWorkspace.tsx`/`model-workspace.css`가 모델별 필터·분석 탭·지도/지표/요약표·하단 분석 카드 구성을 제공하며 `SDSSChrome.tsx`/`sdss-chrome.css`가 원본 비율의 공통 SDSS 헤더·206px 탐색·footer를 제공한다.

제공된 PNG의 로고/장식/작은 모델 illustration을 재사용하며 실제 탐색·입력·지도·표·탭은 HTML/React다. PNG 전체를 클릭 불가능한 화면으로 대신하지 않는다. PNG의 가상 KPI/차트/분석 overlay는 운영 결과로 복제하지 않고 대기 값·축·범례로 표현한다. 지도 배경은 실제 제공처 지도이며 모델 예측으로 표시하지 않는다. 실제 데이터/모델/검증 API 연결은 유지한다.

공통 검색은 서버 등록 데이터 메타데이터를 실제 필터하고, 알림은 저장 Job, 설정은 실제 연결 설정으로 이동한다. 사용자 이름·가상 알림 수·승인 상태는 시안에서 복사하지 않는다. 이 차이는 과학/운영 근거를 보존하기 위한 의도된 차이다. PNG의 원문 언어는 한국어·인도네시아어가 혼합돼 있어 현재 실행 UI는 한국어 기준으로 통일한다.

PNG 재작업 이후의 최종 build/브라우저 screenshot 증거는 `evidence/ui-20261017/png-*` 파일을 확인한다. 아래는 최초 계층형 UI 구현 기록이다.

최종 확인: production build **47 modules / 11.84초 PASS**, adapter **5/5 PASS**. LCLUC 지표4개/하단카드4개, 6개 전용 화면, 시계열 탭 전환, 실제 위성지도·연구 bbox·축척, 모바일390px 가로 넘침 없음을 브라우저에서 확인했다. LCLUC screenshot은 `png-lcluc.jpg`, 나머지5종은 같은 폴더 `png-climate/carbon/biodiversity/coastal/flood.jpg`다. MapLibre 높이 충돌은 범위 한정 CSS와 ResizeObserver로 수정했다. 예측 수치가 없는 점은 미완성 디자인이 아니라 검증되지 않은 과학결과를 표시하지 않기 위한 상태다.

확인일: 2026-10-17 (Asia/Seoul). 적용 범위는 프런트엔드의 탐색·화면 구현과 실제 API 연결이다. 운영·과학적 인수를 의미하지 않는다.

## 참조와 적용

- `UI/SDSS_%EB%A9%94%EB%89%B4_%EA%B3%84%EC%B8%B5%ED%98%95_UX_%EC%84%A4%EA%B3%84%EB%AA%85%EC%84%B8_v2.0.md`를 읽었다.
- `UI/GreenBlue_SDSS_UIUX_v2_*.zip`의 `index.html`과 제공된 LCLUC 화면 PNG를 직접 확인했다. 참조의 지도·수치를 실제 분석 데이터로 복사하지 않았다.
- 네이비·청록 공통 shell, 7개 Global Navigation, 메뉴별 Local Navigation, Breadcrumb, 6개 분야별 Workspace와 반응형 카드를 구현했다.

## 실제 구현

1. Dashboard / Data Catalog / GeoAI Toolbox / WebGIS Analysis / GeoLLM Assistant / Model & MLOps / Reports & RDTR를 분리했다. Data Catalog 선택은 Toolbox로 자동 이동하지 않는다. 분석 도구 찾기 CTA로만 전환한다.
2. Toolbox는 6개 카드에서 LCLUC, Climate Downscaling, Net Carbon Footprint, Biodiversity Mapping, Sea Level & Subsidence, Flood & Drought Workspace로 들어간다. 각 화면에 입력 설정·결과·검증·이력 탭을 제공한다.
3. 분야별 Basic/Expert 입력 초안은 탭 세션에 보관하여 메뉴 전환 후 복원한다. 초안이 실제 Job 계약에 제출됐다고 표시하지 않는다. LCLUC의 기존 실제 API Expert JSON 입력을 유지했다.
4. 기존 CollectionStatus, MapLibre 지도, TemporalCompare, AnalysisReview, ModelReview, AgentCenter, GeoQuery와 데이터 검색·등록·학습·추론·변화분석을 연결했다. 기존 데이터·분석 자산 내보내기를 보존했다.
5. 표준 Job은 Agent readiness `READY`인 경우에만 제출 버튼을 활성화한다. 멱등 키를 유지하며 409 응답에 포함된 실제 Job ID·차단 상태도 보존한다. 활성 Job은 2.5초 폴링하며 이탈 시 해제한다. 실제 상태 기반 취소·Result 조회를 유지한다.
6. `/v1/results/{result_id}/sdss` RFC adapter 응답을 연결했다. 서버의 SHA·lineage 검증과 별개로 브라우저도 Result/Job/Trace 일치, SUCCEEDED, SCIENTIFIC_VALIDATED, INDEPENDENT_SCIENTIFIC, 빈 blockers를 확인한다. 통과한 자산만 인증을 유지하여 내려받는다. GeoJSON은 WebGIS에 표시하고 서버의 검증 bbox로 이동한다. MOCK_ONLY/DEVELOPMENT_ONLY/불일치/차단은 게시하지 않는다.
7. 실제 준비도 보고서의 source_report, manifest 일치, evidence 일치, freshness와 최신 재고의 physical_total/manifest_sha256을 표시한다. 오래된 77패치 준비도와 최신 재고를 구별한다.
8. 메뉴·Workspace·작업 탭 이동 시 페이지 상단으로 이동하고 브라우저 제목을 GreenBlue SDSS로 통일했다.

## 검증

- `npm run build`: TypeScript + Vite production build PASS. 43 modules. MapLibre 포함 큰 JS chunk 경고는 남으며 실패는 아니다.
- `node --test src/integrationAdapter.test.mjs`: 5 PASS. 기존 4건 + Job/Result/Trace 불일치·SHA blocker·MOCK/DEVELOPMENT·독립 검증 미충족의 게시 차단을 검증했다.
- 브라우저 실제 응답·7개 메뉴·6개 Workspace·모바일 검증과 screenshot 증거는 root/integration 담당이 별도 기록한다. 이 문서의 build 결과는 실제 모델 정확도나 실행 성공 증거가 아니다.

## 남은 외부 의존성과 제한

- 외부 5개 모델은 납품 Adapter·Capability·독립 검증이 없으므로 실행·결과를 생성하지 않는다.
- 실제 승인 Result가 없는 현재 게시 경로는 안전 차단 상태다. 테스트용 성공 Result를 운영 Registry에 만들지 않았다.
- RDTR/RTRW 공식 공간계획 데이터, 기관별 보고서 승인·전자서명, 운영 Kubernetes 모니터링과 feedback API는 연결 대기 화면으로 표시한다.
- COG raster 타일링은 아직 지원하지 않으며 검증 자산 다운로드만 제공한다. 지도 표시는 GeoJSON을 지원한다.
- 국제화·공식 기관 RBAC·사용자 UAT와 운영 배포는 후속 인수 범위다.
