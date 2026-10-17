# 대시보드 PNG 참조 UI 구현

기준일: 2026-10-17, Asia/Seoul. 상태: 지속 개발 중. 화면 재현은 전체 플랫폼·과학모델·운영 인수 완료를 뜻하지 않는다.

## 참조·변경 파일

- 사용자 제공 `UI/인도네시아 기후 GeoAI 통합 대시보드.png`를 직접 시각 확인했다. 원본 치수는 **1672×941**이다.
- `frontend/src/DashboardReference.tsx`, `dashboard-reference.css`와 App의 step0 연결을 구현했다. 별도 대시보드 shell이므로 기존 6개 모델 Workspace와 다른 메뉴 레이아웃을 바꾸지 않는다.
- 공통 코드를 카탈로그에서도 재사용하도록 DashboardSidebar, ReferencePanel, ReferenceMap, DashboardIcon을 export한다.
- `public/reference/dashboard-reference.png`는 제공 원본의 복사본이다. 상단의 작은 브랜드 지구 로고와 좌측 해안 사진 영역만 CSS background-size/position으로 잘라 사용한다. 전체 PNG를 UI 한 장으로 표시하지 않는다. 제목·아이콘·수치·지도·패널·버튼은 실제 DOM/SVG와 MapLibre다.

## 화면 구성·실제 동작

- 좌측230px 짙은 사이드바,30px 제목,상태칩4개,KPI6개,지도/모델목록,분포/작업/지역지표3패널,알림/결과3카드를 참조 비율에 맞췄다.
- 대시보드 전용 filled/duotone SVG로 home/database/location/play/cloud/alert/leaf/two-leaf/waves/drop의 형태·크기를 구현했다. 다른 모델 화면의 공통 아이콘은 변경하지 않는다.
- 사이드바·KPI·카드 상세 버튼은 기존 실제 메뉴로 이동한다. 모델6행은 해당 Workspace를 연다. 새로고침은 기존 Registry 읽기와 독립 진단 조회만 수행한다.
- 가벼운 Agent Registry 조회와 무거운 collection-status를 독립 promise로 처리한다. 수집 준비도 응답이 늦어도 등록 Agent6개와 Draft/External 상태를 먼저 표시한다. 수집 진단의 조회 중·조회 실패·응답 조건 없음은 구별한다.

## 지도 근거와 데이터 해석

- 지도는 실제 Esri World Imagery와 `first-group-provinces.geojson`의 실제6주 공개 ADM1 경계만 표시한다. 이름표는 참조 bbox 중심에 연결하며 지역 선택으로 해당 범위를 탐색한다.
- 경계 근거는 `first-group-provinces.source.json`:2017년 OpenStreetMap/Wambacher,geoBoundaries,ODbL1.0,legal_boundary_certification=false. 공개 참조이며 사업상 확정·공식 승인 경계가 아님을 화면에 표시한다. Esri/경계 출처 고지는 유지한다.
- Dataset/모델/Job 등록 수는 실제 API 기록이다. 운영서비스 수·모델 진행률·지역별 산림/홍수/가뭄 지표는—/연결 대기로 표시하며 참조의482개·백분율·위험지수를 복제하지 않는다.
- /collection-status.recorded_at는 조회 시각이므로 데이터 최신성으로 사용하지 않는다. 원본 자료 최신 기준일은 미확인으로 표시하고 조회 시간은 KST로 구분한다.
- 최근 분석 카드는 저장분석·근거검토 진입점이다. 임의 결과 thumbnail·과학모델 위험지도를 만들지 않는다.

## 검증

- production build와 UI adapter 통합 증거: `evidence/integration/dashboard-reference-build-20261017.log`.
- root의1672×941 실제 브라우저에서 sidebar230px,header58px,KPI y75/h96,상단 y180/h339,중단 y528/h215,하단 y752/h173을 확인하여 참조 위치에 가깝게 조정했다. footer 높이14와 하단 padding0으로 불필요한 세로 스크롤을 보완했다.
- 실제6주 경계 feature/ID/source SHA는 읽기 전용으로 검증한다. 실제 과학성능 증거가 아니다.
- 코드·문서 변경은 같은 단위로 기록했다. root가 최종 코드·시험·브라우저 근거를 understanding_agent에 전달하여 설명/발표/FAQ를 갱신한다.

## 최종 검증 결과

- 두 참조 화면·기존 Job/Workflow UI가 포함된 production build **57 modules / 19.20초 / 종료0 PASS**.
- UI adapter **19/19 PASS / 1334.4995ms** (카탈로그6 + 입력/정책/Job snapshot8 + Result5). 큰 MapLibre JS chunk 경고는 남는다.
- 원본 PNG 두 개의1672×941 치수,공개6주6feature·6고유ID,source SHA-256일치,공식경계인증false를 확인했다.
- API8002의 dashboard.datasets=6과 실제 Dataset 목록6행 일치를 읽기 전용으로 확인했다. 데이터·모델·Job 등록/수집/학습을 수행하지 않았다.


## Root 실제 화면 검증

2026-10-17 KST: desktop1672×941에서 전체높이941, mobile390×844에서 전체 수평 넘침 없음. 검색6→1/상세/CSV13열1행/역전기간 오류·0행·다운로드 차단/초기화6 및 모델허브 메뉴 연결을 확인했다. 원본 Catalog/원장/manifest SHA 불변. `evidence/integration/reference-ui-live-20261017.json` 및 `evidence/ui-20261017/*-reference-*.png`를 따른다. 실제 자료 조회/메타데이터 UI 확인이며 독립 과학 정확도나 운영 승인이 아니다.
