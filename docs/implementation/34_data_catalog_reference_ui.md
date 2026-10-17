# 데이터 카탈로그 PNG 참조 UI 구현

기준일: 2026-10-17, Asia/Seoul. 상태: 지속 개발 중. 등록 데이터 조회·화면 필터·메타데이터 CSV 내보내기 범위이며 Dataset 승인·원본 수집·Job 실행을 하지 않는다.

## 참조와 코드

- 사용자 제공 `UI/인도네시아 기후 데이터 카탈로그 대시보드.png`를 직접 확인했다. **1672×941** 기준이다.
- 신규 `frontend/src/DataCatalogReference.tsx`, `data-catalog-reference.css`, `catalogReferenceAdapter.ts`, `catalogReferenceAdapter.test.mjs`와 App의 step1 연결을 구현했다.
- 대시보드의230px shell·작은 브랜드/해안사진 crop·SVG·실제6주 지도·공통 패널을 재사용한다. 원본 전체 이미지를 UI로 표시하지 않는다.
- 기존 위성 검색·다운로드 화면은 step25에서 보존하며 도움말의 명시적인 버튼으로 연다. 기존 quality10/metadata11/registration2/WebGIS14/Toolbox12 경로도 유지한다. 새 수집이나 운영 데이터 등록을 시작하지 않았다.

## 화면과 필터 사용법

1. 실제 Dataset Registry의 등록 수·공개/제한 접근 분류·제공기관 기록·품질 검증 기록을 확인한다. 값이 없는 메타데이터는 미확인이다. 최근 등록 기록은 원본 자료 최신성과 별도다.
2. 텍스트·지역·유형·주제·제공기관·시간·접근 분류·파일 형식 조건을 설정한 뒤 검색을 누른다. 동일 조건 안의 여러 지역은 OR, 서로 다른 필터는 AND다. 시간은 기록된 기간과 겹치는 Dataset만 찾는다. 필터를 제한했을 때 해당 메타데이터가 없는 행은 제외한다.
3. 초기화는 입력 조건·적용 조건·행 선택을 지우고 실제 전체 등록 목록으로 돌아간다. 지도 클릭도 지역 조건 초안에 반영한다.
4. 테이블 행을 선택하거나 데이터명/상세 버튼을 눌러 한국어 필드명의 whitelist 메타데이터를 확인한다. 등록시각은 KST로 표시한다. 표시 항목 설정으로 파일 형식 열을 전환한다.
5. CSV는 선택한 행이 있으면 현재 검색 결과 중 선택행, 없으면 현재 검색 결과 전체를 내보낸다. UTF-8 BOM,쉼표/따옴표/줄바꿈 quoting,=+-@ 및 선행 공백을 이용한 수식 삽입 방지 prefix를 적용한다. 표의 안전한 메타데이터만 내보내며 source URI/path/token을 포함하지 않는다.

## 실제 데이터와 한계

- 참조 예시482개 Dataset·공개312·기관API24·품질92% 등은 실적으로 복사하지 않았다. 현재 /api/datasets의 실제6행처럼 서버가 반환한 목록만 사용한다. API 오류/미응답을0% 분포나 성공으로 표시하지 않는다.
- 품질 패널은 `기본 식별기록`,좌표계·기간·제공기관·명시 품질상태·접근분류의 **기록 존재**를 각각 집계한다. 기록 존재는 무결성 검사·독립 과학평가·기관 권한 승인과 다르다.
- `status:Approved`,파일 경로 확장자,Dataset ID 이름 등으로 품질·형식·지역을 추정하지 않는다. 명시 metadata만 projection한다. 제한자료는 RESTRICTED와 CONFIDENTIAL을 함께 집계한다. 제공기관은 provider 또는 source의 institution/provider 명시 필드만 쓰며 manual-local-registration 같은 등록방식 문자열을 기관으로 계수하지 않는다. 파생 projection과 필터는 원본 입력 객체를 변경하지 않는다.
- 주제·기관 기록이 없는 Dataset에 가짜 분포나 기관 막대를 생성하지 않는다. 경계/기저지도 고지와 라이선스는 대시보드33과 같다.
- 기관별 ACL,원본 파일 다운로드,Dataset 불변버전 Registry HTTP 공개,공식 RDTR·모델 승인은 후속 Gate다. 이 UI가 이를 완료했다고 표시하지 않는다.

## 검증·증거

- 필터 adapter6시험:미확인 분류 보존/복합 검색/다중지역·기간 교차/초기화·원본 불변/안전 CSV/역전·잘못된 연도와 등록방식의 기관 오인 방지.
- 기존 입력·정책·Job snapshot·Result adapter13시험을 함께 실행한다.
- 최종 build/관련 시험 로그: `evidence/integration/data-catalog-reference-build-20261017.log`. 대시보드와 카탈로그가 포함된 같은 production build를 `dashboard-reference-build-20261017.log`에도 기록한다.
- 합성 fixture 시험은 TESTED_SYNTHETIC이다. 실제 Registry 읽기·선택·검색·상세·CSV 브라우저 검증은 root/integration이 별도로 수행한다.
- root가 완료 소스·로그·문서33/34를 understanding_agent에 전달하여 설명/발표/FAQ/INDEX를 갱신한다. UI 단위 완료를 전체 개발 완료로 해석하지 않는다.

- root 실제 브라우저 검증: baseline2021 검색6→1, 정확 ID/version 상세·미확인 필드, 실제 CSV의 UTF8 BOM/13열/1행 확인, 역전기간 오류·0결과·CSV비활성, 초기화6행 복원. CSV 증거는 root가 보관한 catalog-filtered-export.csv다.

## 최종 검증 결과

- 두 참조 화면·기존 Job/Workflow UI가 포함된 production build **57 modules / 19.20초 / 종료0 PASS**.
- UI adapter **19/19 PASS / 1334.4995ms** (카탈로그6 + 입력/정책/Job snapshot8 + Result5). 큰 MapLibre JS chunk 경고는 남는다.
- 원본 PNG 두 개의1672×941 치수,공개6주6feature·6고유ID,source SHA-256일치,공식경계인증false를 확인했다.
- API8002의 dashboard.datasets=6과 실제 Dataset 목록6행 일치를 읽기 전용으로 확인했다. 데이터·모델·Job 등록/수집/학습을 수행하지 않았다.


## Root 실제 화면 검증

2026-10-17 KST: desktop1672×941에서 전체높이941, mobile390×844에서 전체 수평 넘침 없음. 검색6→1/상세/CSV13열1행/역전기간 오류·0행·다운로드 차단/초기화6 및 모델허브 메뉴 연결을 확인했다. 원본 Catalog/원장/manifest SHA 불변. `evidence/integration/reference-ui-live-20261017.json` 및 `evidence/ui-20261017/*-reference-*.png`를 따른다. 실제 자료 조회/메타데이터 UI 확인이며 독립 과학 정확도나 운영 승인이 아니다.
