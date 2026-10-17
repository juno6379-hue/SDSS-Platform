# 2026-10-17 통합 검증·증거

범위: 내부 로컬 개발. 실제 독립 과학 정확도·기관 UAT·운영 배포와 구분한다.

## 자동시험

- Python 통합 회귀 **197 PASS**: `evidence/integration/resume-tests-final-20261017.log`.
- Result→SDSS **10 PASS**: schema/식별자/Trace/고정 참조·MOCK/DEVELOPMENT/해시·원격/UNC·manifest 교체·원본 변경을 검사한다. 성공 fixture는 임시 디렉터리만 사용한다.
- ML readiness **20 PASS**, ML pipeline **17 PASS**: 별도 상세 [ML 재개 검증](23_ml_readiness_resume_20261017.md).
- collection status **9 PASS**, recovery **5 PASS**, annual budget **4 PASS**: 전체 회귀에도 포함된다.
- UI adapter **5 PASS**, production build **43 modules PASS**. 기존 큰 chunk 경고는 남는다. [UI 구현](23_ui_completion.md).
- 기본 `scripts/test.ps1` 실행 로그: `evidence/integration/resume-tests-script-20261017.log`. 누락 jsonschema 의존성은 `.runtime`에 requirements 범위로 설치했다. temp 의존성 경로를 요구하지 않는다.

## 브라우저

실제 `http://127.0.0.1:5173/`와 로컬 API를 사용했다. 모의 과학결과를 운영 카탈로그에 등록하지 않았다.

- 7개 전역 메뉴의 독립 랜딩 확인. Data Catalog 선택 시 Toolbox로 자동 이동하지 않음.
- 6개 모델 허브→각 전용 Workspace 진입 확인. 외부5 실행 버튼 비활성/연결 대기 확인.
- LCLUC 입력 AOI를 바꾼 뒤 결과 탭→입력 탭 복귀 시 초안 유지 확인.
- 실제 Agent Registry의 LCLUC BLOCKED/DRAFT와 외부5 NOT_IMPLEMENTED 확인. 선택 후 표준 Job 제출 버튼 비활성 확인.
- 1440×1000 데스크톱과 390×844 모바일 확인. 모바일 document scrollWidth 375≤viewport390, 가로 전체 페이지 넘침 없음. 모바일 전역 메뉴는 가로 스크롤이다.
- 점검 시 브라우저 console error 없음. 상용 지도/기관 API/오프라인 상태 전체 조합을 검증한 것은 아니다.
- 증거 `evidence/ui-20261017/toolbox-desktop.jpg`, `lcluc-desktop.jpg`, `toolbox-mobile.jpg`, `toolbox-dom.txt`.

## 실제 자료와 차단

최종 QA는 1,111 적격, train/val/test 628/233/250, 36/36셀. source scene val/test 충돌과 bare 대표성·클래스 coverage 부족으로 5개 blocker를 유지한다. 4,335개 근거 파일 SHA 검사 결과는 ML evidence JSON을 따른다. 학습·운영 승인·성공 표준 Result는 생성하지 않았다.

수집 미완료 2건의 예약/lock은 보존했다. `collection-recovery-20261016T234057781783Z.json`이 중단 근거이며 자동 재개 완료로 해석하지 않는다.

## 남은 검수

실제 승인 Result E2E, COG 타일, 공식 RDTR/기관 ACL·외부5 납품, 독립 현장 평가, 운영 DAG/Kubernetes/rollback·성능·보안/UAT가 남아 있다. [다음 재개 순서](00_next_session_handoff.md).

## PNG 6종 동일 구성 추가 검증

사용자 추가 지시로 ModelAnalysisWorkspace와 SDSSChrome을 구현했다. PNG 6장 각각을 열어 직접 대조했다. 원본1448×1086 크기로 모델별 제목·필터·분야 분석 탭·지도·KPI/표·하단 카드의 실제 DOM을 확인하고 `png-lcluc/climate/carbon/biodiversity/coastal/flood.jpg`에 저장했다. 위성지도만 실제 외부 basemap이며 수치와 과학모델 레이어는 대기 상태다.

LCLUC 시계열 탭에서 큰 빈 데이터 차트로 전환하고 전환행렬은 행렬표를 표시한다. 모델/탭 변경 시 초안을 보존하며 기존 실제 API 근거·Result·Expert 입력에 접근한다. 탄소 기본지역 East Kalimantan, 연안 DKI Jakarta·홍수 Central Java 범위를 확인했다. 모바일390×844에서 문서 너비375≤390을 확인하고 `png-mobile.jpg`를 저장했다.

검증 과정에서 MapLibre의 relative 규칙이 지도 canvas 부모 높이를0으로 만드는 CSS 충돌을 발견했다. 범위 한정 선택자와 ResizeObserver로 수정한 뒤 실제 Esri 영상·축척·bbox 표시를 확인했다. 최종 build47 modules 및 UI adapter5 PASS 로그는 `png-build-final.log`·`png-adapter-tests.log`다. root의197 backend PASS 결과는 UI만 바뀐 이후에도 이전 코드 검증 근거로 유지하며 운영 인수를 뜻하지 않는다.
