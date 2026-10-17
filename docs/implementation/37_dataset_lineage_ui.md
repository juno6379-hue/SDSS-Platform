# Dataset 계보 읽기 진단 UI

기준일: 2026-10-17, Asia/Seoul. 상태: 지속 개발 중. 내부 RFC의 읽기 검사와 결과 표시 범위이며 실제 계보 등록·Dataset 쓰기·기관 권한·과학평가·Job 실행을 하지 않는다.

## 변경 파일·기존 UI 보존

- `frontend/src/DataCatalogReference.tsx`: 기존 데이터 상세 dialog 하단에 접기 영역만 추가했다. 카탈로그 PNG 기본 배치·필터·CSV, 대시보드, 기존6개 모델 Workspace는 그대로 유지한다.
- `DatasetLineageDiagnostics.tsx`, `dataset-lineage-diagnostics.css`: 수동 고정 참조 폼과 검사 범위·노드·연결·차단·한도 결과 카드.
- `lineageVerificationAdapter.ts` 및 `.test.mjs`: 요청 유효성, 고정 신원·계약/승인 불변 검증, 늦은 응답 거부.
- API의 기존 `agentApi`·세션 토큰 처리·동일 출처 개발 proxy를 재사용한다. backend/API/운영 원장/데이터 파일은 UI 담당이 수정하지 않는다.

## 사용법

1. 데이터 카탈로그의 실제 등록행에서 상세보기를 연다.
2. `불변 Dataset 계보 읽기 검증 (내부 RFC)`를 펼친다. 기존 legacy Catalog와 불변 버전 Registry는 별개다. legacy ID에서 버전·SHA를 추정하거나 자동 채우지 않는다.
3. 실제 불변 Registry의 고정 Dataset ID,버전,**자산** SHA-256을 직접 입력한다. SHA는 소문자16진수64자리이며 manifest metadata SHA로 대체하지 않는다. 빈 값,latest/current,unknown/미확인 등의 버전과 잘못된 한도에서는 제출 버튼이 비활성이다.
4. 선택 한도는 기본 깊이32·노드256,허용 깊이0–64/노드1–1024다.
5. `고정 참조의 현재 계보 읽기 검증`을 누르면 `POST /v1/datasets/lineage/verify`로 root_ref와 검사 한도만 보낸다. URI·경로·manifest 원문·자격정보 필드를 추가하지 않는다.
6. 검사 시작·종료 KST,scope,고정 root_ref,현재 자산 확인 시도,노드·부모→자식 연결·차단 코드·깊이/노드 한도를 확인한다. 원본 JSON은 민감 경로·URI를 숨기는 기존 details를 사용한다.

브라우저 자동화용 입력 name은 `lineage-dataset-id`, `lineage-dataset-version`, `lineage-dataset-sha256`이다. 정상 과학결과 fixture를 운영 Registry에 만들지 않는다. 미등록 참조를 이용한 실제 조회는 미등록 BLOCKED 진단을 확인하기 위한 것이며 입력된 임시 SHA가 실제 자료 해시라는 뜻이 아니다.

## 판정 구분과 경합 방지

- HTTP200 `BLOCKED`는 진단 보고서가 반환됐다는 뜻이며 검사 통과가 아니다.
- `current_assets_revalidated:true`는 로컬 참조 resolve를 한 번 이상 시도했다는 뜻이다. **전체 자산 검사 성공으로 표시하지 않는다.**
- `INTEGRITY_VERIFIED`는 동일 고정 root_ref,일관된 무결성 노드·빈 blocker가 확인된 경우에만 표시한다. 무결성 일치도 자료 품질·기관 권한·과학·실행 승인과 별도다. 녹색 운영 승인 배지를 만들지 않는다.
- wrapper의 extension/internal-review/upstream:false/evaluation_scope와 diagnostic scope를 검사한다. wrapper·diagnostic의 authorization_verified/execution_authorized/scientific_approval가 모두false여야 한다. 응답 root_ref의 ID·버전·SHA가 요청과 다르면 표시를 차단한다. 검사 한도는 요청과 같고,부모→자식 방향·network_requests/source_files_written가0이어야 한다.
- HTTP400은 요청 오류,503은 진단/저장소 자원 불가,401/403은 연결 접근 오류,나머지는 별도 조회 실패로 구분한다. 오류에서 임의 파일경로·내부 예외를 표시하지 않는다.
- 폼 입력 변경 시 이전 결과를 즉시 지우고 요청 세대를 무효화한다. 다른 상세 데이터로 이동·dialog 닫기·화면 이탈 뒤 늦게 도착한 응답도 표시하지 않는다. 입력 키와 요청 세대를 함께 확인한다.

## 검증·근거

- 새 adapter6시험:미상/별칭/잘못된 고정참조·한도 거부,HTTP200 BLOCKED와 시도 flag의 성공 오인 방지,root ID/version/SHA 불일치,양쪽 승인 불변,무결성 판정과 노드/차단 일관성,입력·상세 변경 경합 guard.
- 기존 카탈로그6/입력·정책·Job snapshot8/Result5시험과 합계25개를 함께 실행한다. fixture 시험 상태는 TESTED_SYNTHETIC이며 실제 과학모델 결과가 아니다.
- production build 및 UI 시험 로그: `evidence/integration/dataset-lineage-ui-build-20261017.log`.
- API 계약·코어는 문서35와36의 담당 기록이 기준이다. 실제 endpoint 연결·미등록 진단 브라우저 확인은 root/integration이 수행한다.
- root가 완료 소스·최종 로그·이 문서37을 understanding_agent에 전달하여 설명·발표·FAQ·INDEX를 갱신한다. 읽기 UI 단위 완료를 전체 사업/운영 완료로 보거나 보고 예약을 중지하지 않는다.

## 최종 UI 검증 결과

- production build **60 modules / 22.09초 / 종료0 PASS**.
- UI adapter **25/25 PASS / 341.057ms**.
- MapLibre 포함 큰 JS chunk 경고는 남는다. 실제 API/브라우저 결과는 아래 root의 별도 근거를 따른다.
## 실제 API·브라우저 확인

root/integration이 실제 UI/API 환경에서 다음을 확인했다. 이 항목의 VERIFIED_REAL 범위는 **미등록 참조의 읽기 진단과 UI 표시**이며 실제 모델 성능·승인·성공 Dataset 계보를 뜻하지 않는다.

- 명시 미등록 고정 참조를 입력하여 `BLOCKED / DATASET_VERSION_NOT_FOUND`를 확인했다. 현재 자산 확인 시도는 전체 성공과 별도이고 권한·실행·과학 승인 없음이 표시된다.
- 버전을 `latest`로 바꾸면 이전 결과가 즉시 지워지고 제출이 비활성이다. 고정 버전1로 되돌려 재조회했다. 운영 Registry에 성공 fixture를 등록하지 않았다.
- desktop1440×1000과 mobile390×844에서 확인했다. 모바일 dialog351px/document375px로 가로 overflow 없이 표시되며 검증 후 viewport를 복원했다.
- 실제 API 근거: `evidence/integration/dataset-lineage-api-live-20261017.json`.
- 브라우저 이미지: `evidence/ui-20261017/dataset-lineage-blocked-desktop.png`, `dataset-lineage-reason-desktop.png`, `dataset-lineage-reason-mobile.png`.
- root 전체 회귀는298건/297 PASS/1 SKIP/88.188초이며 원본5개 SHA가 불변이었다. 이는 UI25시험 및 해당 읽기 API 검증과 범위가 다르다. 기존표준Job2건보존/신규실행0도 확인했다.
